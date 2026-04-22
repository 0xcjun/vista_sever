# Vista 服务 · 阿里云函数计算封装设计

- 作者：jun
- 日期：2026-04-22
- 状态：待评审
- 目标仓库：`/Users/0xjun/Documents/vsPro/vista_sever`
- 源 vista 项目：`/Users/0xjun/Documents/cursorPro/vista`（`vista==3.1.1-260418`）
- 本地开发/部署工具：[Serverless Devs](https://www.serverless-devs.com/)（`s` CLI）

## 0. 背景与目标

vista 是一套投研框架（Python 3.11+），已有 CLI 工具 `vista`。现在需要把其中 8 个业务流程作为阿里云函数计算 (FC 3.0) 函数独立部署，由函数工作流 (FnF) 编排串联，以获得弹性伸缩、多租户隔离和事件驱动能力。

**8 个目标流程与对应 vista 内部入口**

| 目标函数 | vista 入口 |
|---|---|
| factor-plan | `vista.agents.factor_plan.plan_factor_routes` |
| factor-builder | `vista.agents.factor_builder.FactorBuilder` |
| factor-detect | `vista.utils.factor_detect.factor_detect` |
| factor-duplicate | `vista.utils.factor_duplicate.factor_duplicate` |
| factor-evaluate | `vista.utils.factor_evaluate.factor_evaluate` |
| factor-filter | `vista.utils.factor_filter.factor_filter` |
| strategy-backtest | `vista.utils.strategy_backtest.run_strategy_backtest` |
| vista-realtime | `vista.realtime.workflow.RealtimeWorkflow`（循环拉取形态） |

**成功标准**
- 上述 8 个流程可独立部署、独立扩缩容、独立配额
- 可用 FnF 编排 `plan→build→detect→duplicate→evaluate→filter` 完整流水线，以及 `filter→backtest` 的扇出回测
- 本地用 `s local invoke` 能完整跑通每个 handler（容器级集成）
- 部署链路有自动化 preflight 校验（s.yaml / RAM / OSS / NAS / FnF / CH 十步）
- 用户数据按 `user_hash` + `workspace_id` 严格隔离
- 冷启动 < 30s（共享镜像），单函数发版回滚 < 5 min（只换 image tag）

**非目标**
- 不重写 vista 内部算法；所有业务逻辑仍在 vista 包里
- 不迁移现有 DuckDB / Faiss 到远端向量服务
- vista-realtime 不承诺支持长连接行情；仅支持"循环拉取 / 小批处理"形态

## 1. 关键决策（brainstorm 结论）

| 决策点 | 选择 | 理由 |
|---|---|---|
| 调用模式 | HTTP 同步 + 异步任务 + Cron + 事件/MQ 并存 | 不同函数有不同触发场景 |
| 编排 | 阿里云函数工作流 FnF | 有 DAG、retry、状态机；避免自建 orchestrator |
| 打包 | Custom Container Image | vista 重依赖（faiss/polars/duckdb/czsc）超 Zip 500MB 上限 |
| 存储 | OSS 主 + NAS 辅 | OSS 按 `user_hash/workspace_id` 隔离；NAS 放 K 线热缓存 + 模型权重 |
| realtime 形态 | 循环拉取 / 小批处理 | 可上 FC timer trigger，不涉及长连接 |
| vista 引用方式 | 消费 vista wheel（zbczsc-dev 私有源） | 清晰边界；便于 CI |
| 实现形态 | Python 函数直调 + pydantic DTO + 共享 base 镜像 | 比 subprocess CLI 代理少一次解释器启动；比 FastAPI 单容器隔离性更好 |
| 租户上下文 | 事件 payload 显式带 `user_hash` + `workspace_id` | 统一、简单；不依赖 JWT/header 约定 |

## 2. 整体拓扑

```
                     调用方（Web/SDK/调度器）
                       │              │
        HTTP trigger   │              │ StartExecution
                       ▼              ▼
                ┌─────────────────────────────────┐
                │  Serverless Workflow (FnF)      │
                │  plan→build→detect→duplicate→   │
                │  evaluate→filter→backtest       │
                └──┬──┬──┬──┬──┬──┬──┬────────────┘
                   │  │  │  │  │  │  │
                   ▼  ▼  ▼  ▼  ▼  ▼  ▼
        ┌─────────────────────────────────────────┐
        │ FC 3.0 · 8 个 function                  │
        │  共享镜像 ACR: vista-fc-base:<git_sha>  │
        │  每个 service 指向自己的 handler:       │
        │   handlers.factor_plan      :handler    │
        │   handlers.factor_builder   :handler    │
        │   handlers.factor_detect    :handler    │
        │   handlers.factor_duplicate :handler    │
        │   handlers.factor_evaluate  :handler    │
        │   handlers.factor_filter    :handler    │
        │   handlers.strategy_backtest:handler    │
        │   handlers.vista_realtime   :handler    │
        │  payload 必带:                          │
        │   { user_hash, workspace_id, run_id,…}  │
        └──┬────┬────┬───────────────────────────┘
           │    │    │
           │    │    └──── 挂载 NAS /mnt/vista-cache
           │    │          ├─ klines/   (ClickHouse 热数据缓存)
           │    │          └─ models/   (ensemble 权重 / 预训练)
           │    │
           │    └─── oss2 SDK 读写 OSS Bucket（工作区数据）
           │          oss://<bucket>/user_data/<user_hash>/
           │            ├─ realtime/FTS_*/…, strategies.duckdb
           │            └─ research/EXP_*/factor_routes.toml, factors.duckdb
           │
           └─── clickhouse-connect 远端查询行情/因子值
```

vista-realtime 不进 FnF：独立 timer trigger，按 workspace 自己的 `FTS_*/strategy.toml` 循环更新，写回 `strategies.duckdb`。

**OSS 数据结构**
```
oss://<bucket>/
└── user_data/
    └── <user_hash>/
        ├── realtime/
        │   ├── FTS_<strategy_id>/         策略配置 + 更新产物
        │   └── strategies.duckdb          用户级持仓总库
        └── research/
            └── EXP_<experiment_id>/       单次完整投研实验
                ├── factor_routes.toml
                └── factors.duckdb         LocalFactorManager 管理
```

**DuckDB 访问模式**：冷启动时从 OSS pull `factors.duckdb` → `/tmp/{workspace_id}/factors.duckdb`，函数退出前 push 回 OSS；同一 workspace 同一时刻只允许一个写者（FnF 保证步骤串行 + OSS 对象版本 ETag 乐观锁兜底）。

## 3. 仓库结构

```
vista_sever/
├── s.yaml                     # serverless-devs 主清单：8 资源 + FnF flow
├── pyproject.toml             # 依赖: vista (私有 wheel), oss2, pydantic, alibabacloud_fc20230330
├── uv.lock
├── .env.example
├── Dockerfile                 # 共享 base 镜像 (python:3.11-slim + uv sync + vista wheel)
├── .dockerignore
│
├── handlers/                  # FC 入口，每个文件 <80 行
│   ├── factor_plan.py
│   ├── factor_builder.py
│   ├── factor_detect.py
│   ├── factor_duplicate.py
│   ├── factor_evaluate.py
│   ├── factor_filter.py
│   ├── strategy_backtest.py
│   └── vista_realtime.py
│
├── src/vista_fc/
│   ├── contracts/             # 每函数 pydantic 输入/输出 DTO
│   │   ├── common.py          # TenantContext / EnvelopeIn / EnvelopeOut / ArtifactRef / ErrorInfo
│   │   ├── factor_plan.py
│   │   ├── …                  # 8 个一一对应
│   │   └── __init__.py
│   ├── storage/
│   │   ├── oss_client.py      # oss2 单例 + 分片上传/下载 + ETag
│   │   ├── workspace.py       # WorkspaceStorage: pull_duckdb / push_duckdb / read_toml
│   │   └── nas_cache.py       # /mnt/vista-cache 的 klines 缓存与模型权重
│   ├── runtime/
│   │   ├── logging.py         # loguru → FC stdout (JSON line)
│   │   ├── context.py         # FC event+context → TenantContext 解析
│   │   ├── errors.py          # FcError(code, retriable) 枚举与映射
│   │   └── adapter/           # FC custom-container HTTP adapter
│   │       └── __main__.py
│   └── services/              # 业务编排层
│       ├── factor_plan.py     # plan_service(FactorPlanInput) → FactorPlanOutput
│       └── …                  # 8 个一一对应
│
├── flows/
│   ├── research_pipeline.fdl
│   ├── backtest_fanout.fdl
│   └── research_full.fdl
│
├── tests/
│   ├── unit/                  # 纯 Python 单测
│   ├── integration/           # s local invoke + minio + clickhouse 容器
│   ├── smoke/                 # 部署后真云调用
│   ├── deploy_preflight/      # 11 步部署链路校验（bash + s）
│   ├── perf/                  # pytest-benchmark 基线
│   ├── fixtures/
│   │   ├── duckdb/
│   │   ├── parquet/
│   │   ├── llm/
│   │   ├── events/
│   │   └── schemas/
│   └── conftest.py
│
├── scripts/
│   ├── build_image.sh
│   ├── push_image.sh
│   ├── local_invoke.sh
│   └── migrations/
│
├── dev/
│   └── compose.yaml           # minio + clickhouse + mock-nas
│
├── docs/superpowers/specs/    # 本设计文档所在
└── README.md
```

## 4. 镜像与依赖管理

**基础镜像**：`python:3.11-slim-bookworm`（vista 要求 3.11+，阿里 FC 官方运行时只到 3.10，必须走 custom-container）

**多阶段 Dockerfile**
```dockerfile
# ---------- Stage 1: builder ----------
FROM python:3.11-slim-bookworm AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN --mount=type=secret,id=uv_index,target=/run/secrets/uv_index \
    --mount=type=cache,target=/root/.cache/uv \
    set -a && . /run/secrets/uv_index && set +a && \
    uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
COPY handlers/ ./handlers/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "vista_fc.runtime.adapter"]  # 默认入口（被函数级 args 覆盖）
```

**每个 FC 函数的 command/args 区分**（s.yaml 里）
```yaml
factor-plan:
  component: fc3
  props:
    region: ${vars.region}
    function:
      functionName: factor-plan
      runtime: custom-container
      customContainerConfig:
        image:   ${vars.imageRegistry}:${vars.imageTag}
        command: ["python", "-m", "vista_fc.runtime.adapter"]
        args:    ["handlers.factor_plan:handler"]
        port:    9000
```

**Adapter 职责**（`vista_fc.runtime.adapter`）
- 解析 `argv[1]` = `<module>:<func>` 动态 import 目标 handler
- 起 HTTP server 监听 `0.0.0.0:9000`
- POST `/invoke` 接收 FC event（body=event、header=FC-Context）
- 调 `handler(event_dict, fc_context)` 返回 200 + JSON
- 异常包装为 FC 标准 500 格式 `{ errorType, errorMessage, stackTrace }`
- 进程启动时预热：`import vista` 减少首次冷启动时间

**私有源认证**
- `zbczsc-dev` index 通过 BuildKit `--mount=type=secret` 注入，不进镜像层
- CI：从 GitHub Actions Secrets 读 `ZBCZSC_DEV_TOKEN`
- 本地：`.env.build`（进 `.gitignore`），或 1Password CLI `op run`

**镜像 tag 规则**
- `vista-fc-base:<git_sha7>`：不可变，部署引用
- `vista-fc-base:main`：最近 main 软指针，仅本地开发
- `vista-fc-base:v<vista_wheel>-<git_sha7>`：可选归档

**预计体积（压缩）**：500–650 MB（未压 1.3–1.6 GB），远低于 FC 10GB 上限。

**依赖 pinning**
- `vista = "==3.1.1-260418"` 精确锁定
- 其余依赖保留上下界，`uv.lock` 进 git
- `chan-factor-rs` / `chanfactor` 通过 `[tool.uv.sources]` 指向 `zbczsc-dev`

**为什么不每个函数独立镜像**
- vista 是共同依赖，拆镜像重复占 ACR
- 更新 vista 只需一次 build/push
- 函数差异只是"跑哪个 handler"，command/args 足够区分

## 5. 函数契约（pydantic DTO）

### 5.1 公共 DTO（`contracts/common.py`）

Python 3.11 兼容写法（用 `Generic[T]` + `TypeVar`，不用 PEP 695）：

```python
from typing import Generic, Literal, TypeVar
from datetime import datetime
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class TenantContext(BaseModel):
    user_hash: str
    workspace_id: str               # EXP_xxx 或 FTS_xxx
    workspace_kind: Literal["research", "realtime"]
    run_id: str
    requested_at: datetime

class ArtifactRef(BaseModel):
    kind: Literal["duckdb", "toml", "parquet", "feather", "report_json", "model", "log"]
    oss_uri: str
    size_bytes: int
    sha256: str | None = None

class ErrorInfo(BaseModel):
    code: str                       # 见下方枚举
    message: str
    retriable: bool
    trace_id: str

class EnvelopeIn(BaseModel, Generic[T]):
    tenant: TenantContext
    payload: T

class EnvelopeOut(BaseModel, Generic[T]):
    tenant: TenantContext
    status: Literal["succeeded", "failed", "partial"]
    artifacts: list[ArtifactRef]
    metrics: dict[str, float | int | str]
    payload: T | None = None
    error: ErrorInfo | None = None
```

**ErrorInfo.code 枚举**（收敛在 `runtime/errors.py`）
- `VISTA_COMPUTE_TIMEOUT` / `VISTA_LLM_RATE_LIMIT` / `VISTA_LOGIC_ERROR`
- `OSS_READ_FAIL` / `OSS_WRITE_FAIL` / `OSS_ETAG_CONFLICT`
- `CLICKHOUSE_CONNECT`
- `WORKSPACE_NOT_FOUND` / `INPUT_VALIDATION`

### 5.2 每函数 Input/Output（摘要）

| 函数 | Input payload 关键字段 | Output payload 关键字段 |
|---|---|---|
| factor-plan | `user_input: str`, `interactive=False`, `model: str\|None`, `skill_path: str\|None` | `routes: list[FactorRouteSummary]`, `routes_toml_artifact: ArtifactRef`（→ `EXP/factor_routes.toml`） |
| factor-builder | `routes_toml_uri` 或 `route_code`, `factor_numbers=20`, `batch_size=5`, `max_workers=1`, `multi_turn=False`, `model`, `max_retries=3` | `total_factors`, `per_route`, `factors_db_artifact`（→ `EXP/factors.duckdb`） |
| factor-detect | `factors_db_uri`, `problems_map_uri: str\|None`, `max_workers=4`, `timeout=60` | `report` 摘要, `report_artifact` |
| factor-duplicate | `factors_db_uri`, `route_codes`, `problem_codes`, `model_config_uri: str\|None`, `threshold=0.8`, `max_workers=4`, `timeout=60` | `report` 摘要, `report_artifact` |
| factor-evaluate | `factors_db_uri`, `route_codes`, `problem_codes`, `models: list[str]\|models_config_uri`, `max_workers=4`, `timeout=60`, `fee_rate=0.0`, `retry_failed=False` | `report` 摘要, `report_artifact` |
| factor-filter | `factors_db_uri`, `problem_codes`, `route_codes`, `evaluate_methods`, `filter_methods`, `positive_extractor`, `positive_metric`, `positive_threshold`, `n=20`, `metric_keys`, `creator`, `author`, `outsample_sdt` | `toml_artifacts: list[ArtifactRef]`（→ `FTS_xxx/strategy.toml`）, `toml_count` |
| strategy-backtest | `strategy_toml_uri`, `mode: Literal["research","realtime"]`, `data_mode: Literal["train","valid","total"]="total"`, `digits=2`, `fee_rate=0.0`, `n_jobs=1`, `yearly_days=252`, `max_workers=1` | `strategy`, `elapsed_s`, `artifacts: dict[str, ArtifactRef]` |
| vista-realtime | `strategy_toml_uri`, `update_mode: Literal["auto","full","incremental"]="auto"`, `push_targets: list[str]=["default"]` | `summary`, `latest_dt`, `weights_artifact`, `timing` |

### 5.3 契约关键约束

1. 大对象（DuckDB / TOML 文件）不在 payload 里传，只传 `oss_uri`
2. 同一 `workspace_id` 的 DuckDB 全对象单写者；ETag 乐观锁防并发写
3. list 字段只传 code（route_code / problem_code），handler 内 `get_problem(code)` 还原
4. 敏感凭据（LLM key / CH 密码）永不进 payload，走 FC 环境变量
5. 每个 Output 必带 `artifacts` + `metrics`，便于 FnF 下游 JSONPath 取值与监控

## 6. FnF 编排

### 6.1 Flow 总览

| Flow | 用途 | 步骤 |
|---|---|---|
| `research-pipeline` | 投研主流水线 | plan → build → detect → duplicate → evaluate → filter |
| `backtest-fanout` | 批量回测 | Map（strategy-backtest × N） |
| `research-full` | 端到端 | research-pipeline → backtest-fanout |

vista-realtime 不进 flow；独立 timer trigger。

### 6.2 研究主流水线（`flows/research_pipeline.fdl`）

节点间数据流：上游 `EnvelopeOut.artifacts[k].oss_uri` → 下游 `EnvelopeIn.payload.*_uri`。完整 FDL 见实现阶段；关键约束写在下面。

**重试策略（按错误码分组）**
- 瞬态错误（OSS 限流/CH 断连/LLM 限流/ETag 冲突）：指数退避 5–10 次
- vista 逻辑错（因子编译失败、评估失败）：fail-fast，不重试
- 输入校验错：不重试

**超时**
| 函数 | FnF Task timeout | FC 函数 timeout |
|---|---|---|
| factor-plan | 600s | 660s |
| factor-builder | 3600s | 3660s |
| factor-detect | 300s | 360s |
| factor-duplicate | 1800s | 1860s |
| factor-evaluate | 3600s | 3660s |
| factor-filter | 300s | 360s |
| strategy-backtest | 1800s | 1860s |
| vista-realtime | 300s | 360s |

FC 函数 timeout 比 FnF Task 多 60s buffer，防止函数先超时返回不完整结果。

### 6.3 编排决策

1. **run_id 贯穿**：调用方 StartExecution 的 `executionName = <workspace_id>-<timestamp>` 就是 run_id，FnF execution history 可追溯
2. **OSS URI 作节点引用**：plan 产出 `routes_toml_artifact.oss_uri` → builder 的 input；build 的 `factors_db_artifact.oss_uri` → 被 detect/duplicate/evaluate/filter 共享
3. **同 workspace 串行保证**：FnF 内部节点天然串行；同一 workspace 的并发 executions 由调用层去重（executionName 唯一 = `<workspace_id>-<run_ts>`）；兜底 OSS ETag 乐观锁
4. **参数与 flow 分离**：业务参数（fee_rate / top_n / batch_size 等）从 StartExecution 的 input 传，不写死在 FDL
5. **监控聚合**：每个函数在 `metrics` 里回报耗时、因子数、失败分片数；execution 结束写 `oss://.../EXP_xxxx/runs/{run_id}/execution_summary.json`

## 7. 本地开发与 serverless-devs 工作流

### 7.1 工具链
- `s`（serverless-devs CLI）：资源编排 + 本地调用（`s local invoke` / `s deploy` / `s logs` / `s cli fc3 invoke` / `s cli fnf ...`）
- `uv`：包管理 + venv
- `docker buildx`：多架构镜像
- `minio`（docker）：本地 OSS
- `clickhouse-server`（docker）：本地 CH

### 7.2 s.yaml 主清单（v3 + fc3，关键片段）

> **关于复用**：YAML merge key (`<<: *anchor`) 只能引用节点别名，无法走点路径深取。下面示例为**可读性**展示完整字段；真正实现时有三种可行的复用方式（实现阶段二选一）：
>
> 1. 顶层多个小 anchor（把 `vpcConfig` / `nasConfig` / `logConfig` / `customContainerConfig` 各自做成独立 anchor），在每个函数节点里 `<<: *vpc-base` 合并
> 2. 把公共片段拆到 `s.yaml.common.yaml`，用 serverless-devs 的 `${file(...)}` 引入
> 3. 接受一定重复（8 个函数 × 每段 ~30 行），clarity 优先

```yaml
edition: 3.0.0
name: vista-fc
access: default

vars:
  region:            ${env.FC_REGION|cn-hangzhou}
  accountId:         ${env.ALIYUN_ACCOUNT_ID}
  ossBucket:         ${env.OSS_BUCKET|vista-fc-dev}
  imageRegistry:     registry.${vars.region}.aliyuncs.com/vista/vista-fc-base
  imageTag:          ${env.GIT_SHA|latest}
  nasMountTarget:    ${env.NAS_MOUNT_TARGET}
  vpcId:             ${env.VPC_ID}
  vswitchId:         ${env.VSWITCH_ID}
  securityGroupId:   ${env.SG_ID}
  logProject:        vista-fc
  logStore:          handlers
  roleArn:           acs:ram::${vars.accountId}:role/fc-vista-role
  functionSuffix:    ${env.FC_SUFFIX|""}       # preflight 时设为 -preflight-<sha>

# 可复用的子块（实现阶段按策略选 1/2/3）
common-vpc: &common-vpc
  vpcId:            ${vars.vpcId}
  vswitchIds:       [${vars.vswitchId}]
  securityGroupId:  ${vars.securityGroupId}

common-nas: &common-nas
  userId:   10003
  groupId:  10003
  mountPoints:
    - serverAddr: ${vars.nasMountTarget}
      mountDir:   /mnt/vista-cache

common-log: &common-log
  project:  ${vars.logProject}
  logstore: ${vars.logStore}
  enableRequestMetrics: true

common-env: &common-env
  OSS_REGION:       ${vars.region}
  OSS_BUCKET:       ${vars.ossBucket}
  NAS_CACHE_ROOT:   /mnt/vista-cache
  CLICKHOUSE_URL:   ${env.CLICKHOUSE_URL}
  CLICKHOUSE_USER:  ${env.CLICKHOUSE_USER}
  # 密钥注入走 serverless-devs 的机密/KMS 扩展（具体占位符按当前插件版本确认，
  # 例如: ${secret(...)} 或 ${env.*} 从 Secret Manager 注入的环境变量）
  CLICKHOUSE_PASS:   ${env.CLICKHOUSE_PASS}
  ANTHROPIC_API_KEY: ${env.ANTHROPIC_API_KEY}
  TZ: Asia/Shanghai
  LOG_FORMAT: json

common-container: &common-container
  image:   ${vars.imageRegistry}:${vars.imageTag}
  command: ["python", "-m", "vista_fc.runtime.adapter"]
  port:    9000

resources:
  factor-plan:
    component: fc3
    props:
      region: ${vars.region}
      function:
        functionName: factor-plan${vars.functionSuffix}
        runtime: custom-container
        timeout: 660
        memorySize: 2048
        cpu: 1
        diskSize: 512
        vpcConfig: *common-vpc
        nasConfig: *common-nas
        logConfig: *common-log
        environmentVariables:
          <<: *common-env
        customContainerConfig:
          <<: *common-container
          args: ["handlers.factor_plan:handler"]

  factor-builder:
    component: fc3
    props:
      region: ${vars.region}
      function:
        functionName: factor-builder${vars.functionSuffix}
        runtime: custom-container
        timeout: 3660
        memorySize: 8192
        cpu: 2
        diskSize: 512
        vpcConfig: *common-vpc
        nasConfig: *common-nas
        logConfig: *common-log
        environmentVariables:
          <<: *common-env
        customContainerConfig:
          <<: *common-container
          args: ["handlers.factor_builder:handler"]

  # factor-detect / factor-duplicate / factor-evaluate / factor-filter /
  # strategy-backtest / vista-realtime 同构，按 §6.2 超时与 §9.7 配额设定

  vista-realtime:
    component: fc3
    props:
      region: ${vars.region}
      function:
        functionName: vista-realtime${vars.functionSuffix}
        runtime: custom-container
        timeout: 360
        memorySize: 4096
        cpu: 1
        diskSize: 512
        vpcConfig: *common-vpc
        nasConfig: *common-nas
        logConfig: *common-log
        environmentVariables:
          <<: *common-env
        customContainerConfig:
          <<: *common-container
          args: ["handlers.vista_realtime:handler"]
      triggers:
        - name: realtime-tick
          type: timer
          config:
            cronExpression: "@every 1m"
            enable: true
            payload: |
              {"tenant":{"user_hash":"<hash>","workspace_id":"FTS_XXX","workspace_kind":"realtime","run_id":"auto","requested_at":"<rfc3339>"},
               "payload":{"strategy_toml_uri":"oss://..."}}

  research-pipeline-flow:
    component: fnf
    props:
      region: ${vars.region}
      name:   research-pipeline
      type:   FDL
      definition: ${file(./flows/research_pipeline.fdl)}
      roleArn:    ${vars.roleArn}

  backtest-fanout-flow:
    component: fnf
    props:
      region: ${vars.region}
      name:   backtest-fanout
      type:   FDL
      definition: ${file(./flows/backtest_fanout.fdl)}
      roleArn: ${vars.roleArn}

  research-full-flow:
    component: fnf
    props:
      region: ${vars.region}
      name:   research-full
      type:   FDL
      definition: ${file(./flows/research_full.fdl)}
      roleArn: ${vars.roleArn}
```

### 7.3 本地开发循环

```
1. 一次性准备
   cp .env.example .env.local
   docker compose -f dev/compose.yaml up -d    # minio + clickhouse
   uv sync

2. 单函数调试（事件模式）
   scripts/build_image.sh --dev                # 本地 tag :dev
   s local invoke factor-detect \
     --event-file tests/fixtures/events/factor_detect_min.json \
     --env-file .env.local

3. 持续调试（server 模式 + 断点）
   s local invoke factor-detect --mode server --debug-port 9000
   s local invoke factor-detect --config vscode --debug-port 9000

4. 单测
   uv run pytest tests/unit

5. 集成测试
   uv run pytest tests/integration -m s_local

6. 部署可行性（preflight）
   export FC_SUFFIX="-preflight-$(git rev-parse --short HEAD)"
   bash tests/deploy_preflight/run_all.sh

7. 部署到 dev
   GIT_SHA=$(git rev-parse --short HEAD) s deploy --access dev --assume-yes

8. 线上调用/日志
   s cli fc3 invoke --function-name factor-detect -e "$(cat tests/fixtures/events/detect_min.json)" --access dev
   s logs factor-detect --tail --access dev
   s cli fnf StartExecution --name research-pipeline --input '<json>'
```

### 7.4 本地外部依赖 mock（`dev/compose.yaml`）

- minio：0.0.0.0:9000 s3 API，环境变量 `OSS_ENDPOINT=http://host.docker.internal:9000` 让 `oss_client.py` 切到它
- clickhouse-server：0.0.0.0:8123，启动时通过 `clickhouse/init.sql` 建库灌 mini 数据
- NAS：本地目录 bind mount（`s local invoke --tmp-dir`）
- LLM：httpx mock，不走真接口

生产不设 `OSS_ENDPOINT`，默认走阿里云 oss 域名 → 同一套代码无分支。

## 8. 测试策略

### 8.1 测试金字塔

| 层 | 数量 | 工具 | 耗时预算 |
|---|---|---|---|
| unit | 150–300 | pytest + mock | < 30s 全量 |
| integration | 30–50 | pytest + s local invoke + minio + ch | 5–10 min |
| preflight | 11 步 | bash + s | 5–8 min |
| smoke | < 10 | pytest + s cli | 5–10 min |
| perf | 少量 | pytest-benchmark | 周级 |

### 8.2 单测重点

| 模块 | 重点 | mock 什么 |
|---|---|---|
| contracts | DTO 校验；pydantic schema 快照（diff 可见） | — |
| runtime | event→TenantContext 解析、错误码映射、JSON 日志 | `sys.stdout` |
| storage | OSS 分片/ETag/断点续传、DuckDB pull-push 往返 | `oss2.Bucket` |
| services.factor_* | 参数装配 → 调 vista 真函数 → 组装 Output | vista 不 mock（用迷你真 duckdb） |
| services.factor_plan / services.factor_builder | 同上，但 LLM 调用 mock | `anthropic` / httpx |
| handlers | 冒烟：event→service→response 装配 | `services.*` |

**关键：用"迷你真数据"而非 mock vista**
- `tests/fixtures/duckdb/mini_factors.duckdb`（~100KB，3 品种 × 50 根 K 线 × 3 因子）
- `tests/fixtures/parquet/mini_klines.parquet`
- 理由：mock vista 内部函数等于不测集成点

**LLM 必须 mock**（plan + builder）
- `tests/fixtures/llm/plan_response.json` / `llm/builder_batch.json`
- 测试关心 vista 侧对响应的解析与编排，不是模型本身

### 8.3 集成测试

- Marker `s_local`，fixture `s_local_runner` 包 subprocess 调 `s local invoke`
- 覆盖：每函数 1 正路径 + 1 OSS 产物回写断言 + 1 错误路径 + 1 OSS 瞬态错误（retriable=True）
- 1 串流水（python 顺序调 3–6 个 handler，不经 FnF）
- LLM 仍 mock（httpx 级别），不烧真 token

### 8.4 部署 preflight（新增独立层）

11 步 bash + s 脚本，在真部署前验证 s.yaml / 凭据 / ACR / 单函数 deploy+invoke / SLS / NAS / OSS / CH / flow deploy / flow execute，全通过才放行 `deploy-dev`。

| 步骤 | 命令 | 检测 |
|---|---|---|
| 00 verify | `s verify` | s.yaml 语法 + 变量解析 |
| 01 credentials | `s cli fc3 list ...` | access 可达 |
| 02 image | `scripts/build_image.sh && push` | ACR 推送 |
| 03 deploy one | `s deploy factor-detect --access dev-preflight` | fc3 创建函数 |
| 04 invoke one | `s cli fc3 invoke ...` | 容器启动 + 返回 200 |
| 05 logs | `s logs factor-detect --tail` | SLS 日志可见 |
| 06 NAS probe | invoke 内部写 `/mnt/vista-cache/ping.txt` | NAS 挂载 |
| 07 OSS probe | invoke 内部 put `oss://.../_probe/<run>.txt` | OSS 授权 |
| 08 CH probe | invoke 内部 `SELECT 1` | VPC+SG+CH |
| 09 deploy flow | `s deploy research-pipeline-flow` | fnf 部署 |
| 10 execute flow | `s cli fnf StartExecution` + 查状态 | flow→函数链路 |

失败即 exit 1；产物输出到 `tests/deploy_preflight/artifacts/<date>/`。preflight 用独立命名后缀（`-preflight-<sha>`），跑完 `s remove` 拆除。

### 8.5 smoke 与 perf

- smoke：部署后真云调每函数一次轻量事件 + 一次 `research-full` flow；失败发告警，不阻断
- perf：detect/duplicate/evaluate 在 mini 数据集上耗时基线，阈值漂移 > 30% 告警；周级

### 8.6 CI 流水

| 阶段 | 跑什么 | 耗时 |
|---|---|---|
| lint | ruff + basedpyright + schema 快照 | < 1 min |
| unit | pytest tests/unit --cov-fail-under=80 | < 1 min |
| integration | pytest tests/integration -m s_local | 5–10 min |
| build-push | docker buildx multi-arch + push ACR | 3–6 min |
| preflight | bash tests/deploy_preflight/run_all.sh | 5–8 min |
| deploy-dev | s deploy --access dev + smoke | 7–13 min |
| deploy-prod | s deploy --access prod + smoke（手动审批） | 7–13 min |

覆盖率：`src/vista_fc/**` line ≥ 80%、branch ≥ 70%；handlers 不计。

## 9. 部署、密钥与运维

### 9.1 环境分层

| 环境 | access | FC 命名 | OSS | 触发者 |
|---|---|---|---|---|
| local | — | — | minio | 开发者 |
| preflight | `dev-preflight` | `*-preflight-<sha>` | `vista-fc-preflight` | CI integration 后 |
| dev | `dev` | `*` | `vista-fc-dev` | CI preflight 后 |
| prod | `prod` | `*` | `vista-fc-prod` | 人工审批 |

### 9.2 RAM 权限（最小权限）

**部署账号**：`fc:*` (限本项目函数) + `cr:Push/Pull`（限 vista-fc-base repo） + `fnf:CreateFlow/UpdateFlow/StartExecution` + `vpc:DescribeVSwitches` + `nas:DescribeMountTargets` + `ram:PassRole`（限函数运行角色） + `log:GetProject/PostLogStoreLogs`。

**函数运行角色**：`oss:Get/Put/Head/Delete/List`（限 `vista-fc-*` bucket） + `nas:DescribeMountTargets` + `log:PostLogStoreLogs` + `kms:Decrypt`。**不给 `fc:*`**（防横向扩权；例外：realtime → backtest 显式窄范围）。

**FnF 流角色**：`fc:InvokeFunction`（限 `{factor-*, strategy-*, vista-*}`） + `log:PostLogStoreLogs`。

### 9.3 密钥管理

- **运行期**：两条可行路径，实现阶段二选一
  1. 阿里云 KMS/Secret Manager + FC 原生集成：函数启动时 FC 把凭据注入环境变量（推荐；具体 s.yaml 占位符按当前 serverless-devs + fc3 组件版本确认）
  2. CI 阶段从公司 Secret store 取出，写入 `s deploy` 时的环境变量（通过 `${env.*}` 传递到函数 env），较简单但轮换要重 deploy
- **构建期私有 PyPI (`ZBCZSC_DEV_TOKEN`)**：Docker BuildKit `--mount=type=secret`，只在构建该层可见不落镜像；CI 从 GitHub Actions Secrets，本地 `.env.build` (`.gitignore`) 或 `op run`
- **pre-commit**：`gitleaks` + `detect-secrets` 双扫
- **严禁**：任何密钥进 `.env.example`、commit、docker layer、日志

### 9.4 CI/CD（GitHub Actions 主干）

```
lint → unit → integration → build-push → preflight → deploy-dev → smoke-dev → [手动] deploy-prod → smoke-prod
```

### 9.5 版本与回滚

- 镜像：每次 main 合入产 `:<git_sha7>` 不可变 tag；环境指针 `:main` / `:prod-current` / `:prod-previous`
- 回滚：`GIT_SHA=<old_sha> s deploy --access prod`，秒级换 image tag，不改 git
- FnF flow：FDL 有版本，`s deploy` 创建新版本；回滚改回老 FDL commit 重 deploy
- DuckDB schema：`scripts/migrations/` + `schema_version` 字段；OSS 产物路径带 schema version，老版本归档 30 天

### 9.6 可观测性

**三条管道**
| 维度 | 目的地 | 工具 |
|---|---|---|
| 结构化日志 | SLS `vista-fc/handlers` | loguru JSON → stdout |
| 指标 | SLS Metricstore + CloudMonitor | handler 在 `metrics` 字段写，runtime 展开成 log + 自定义指标 |
| Trace | ARMS（可选） | OpenTelemetry；FnF 节点边界打 span |

**必记字段**：`run_id / user_hash / workspace_id / function_name / request_id / phase / elapsed_ms / status / 业务量`

**告警**（CloudMonitor，钉钉 + 邮件）
- 函数错误率 > 5%（5min 窗口）
- p95 超阈值（plan 600s / build 3000s / detect 180s / eval 3000s / 其他 600s）
- FnF Failed > 2/hour
- OSS 5xx > 1%
- 函数实例 > 10 连续 3 min

### 9.7 配额与成本

初期 dev：单函数并发 5 / 总实例 20 / FnF 并发 executions 3。

优化点：
- evaluate 预留实例 1 个（可选）
- OSS 走内网 endpoint（0 流量费）
- FC 与 OSS/ClickHouse 同 region 同可用区

### 9.8 Runbook（简）

| 场景 | 处置 |
|---|---|
| 某函数错误率告警 | SLS 按 run_id 拉日志 → 定位 error.code → 瞬态看重试 / 逻辑错回滚 image tag |
| FnF execution 卡住 | `s cli fnf DescribeExecution` 看当前 step；手动 StopExecution + 重启 |
| OSS ETag 冲突反复 | 同 workspace 并发；检查调用层去重；短期手动 abort |
| 依赖 wheel 构建失败 | 检查 `ZBCZSC_DEV_TOKEN` 轮换；本地 `uv sync --reinstall` 复现 |
| 镜像拉不动 | ACR 跨账号权限；重新 `s deploy` 触发拉取 |
| dev 被搞脏 | `s remove --access dev` 全拆，重跑 `s deploy --access dev` |

## 10. 开放问题 / 待决策项

- FnF 的具体 FDL 语法细节：实现阶段需对照阿里云"函数工作流"的最新 FDL 参考校对（本设计按通用 FDL 语义写）
- `fnf` serverless-devs 组件的成熟度：若部署 flow 遇到阻塞，退路是用 `s cli fnf CreateFlow` 直接调 OpenAPI
- 私有源 `chan-factor-rs` 是否提供 manylinux wheel：若只有 source 包，镜像构建需在 builder stage 加 rust toolchain
- 是否需要 `factor-builder` / `strategy-backtest` 的"任务状态查询"接口：当前假设调用方能从 FnF execution 查；若需独立轮询，则加一个 `run-status` 函数
- vista 版本升级策略：先打 wheel 到 `zbczsc-dev`，再 vista_sever 这边 bump `pyproject.toml`；两仓库解耦但需约定 release cadence

## 11. 实现步骤建议（交 writing-plans 细化）

1. 仓库骨架（pyproject、目录、.gitignore、Dockerfile 空架、s.yaml 雏形）
2. contracts/ 8 组 DTO + common
3. storage/oss_client + workspace + nas_cache
4. runtime/logging + context + errors + adapter
5. services/ 8 个业务服务（先 factor-detect 作样板，其余照做）
6. handlers/ 8 个（薄）
7. 单测 + 集成测试 fixture
8. Dockerfile 完整 + build/push 脚本
9. dev/compose.yaml + .env.example
10. flows/ 3 个 FDL
11. s.yaml 完整（按 §7.2）
12. deploy_preflight/ 11 步脚本
13. CI 流水（GitHub Actions）
14. 线上 smoke + Runbook 初版
