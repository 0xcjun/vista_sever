# vista-fc 指南

把 vista 投研框架的 8 个研究步骤 + 1 个实盘函数封装成阿里云 FC3.0 函数，由 FnF 编排。本文只讲三件事：**怎么测、怎么调、怎么上生产**。

仓库里所有函数共用一个 `vista-fc-base` 镜像，handler 只是 thin wrapper（`handlers/<name>.py`）。业务在 `src/vista_fc/services/`，DTO 在 `src/vista_fc/contracts/`。

---

## 1. 怎么测

### 1.1 起本地依赖

```bash
docker compose -f dev/compose.yaml up -d
# 起 MinIO (替代 OSS) + ClickHouse
# MinIO 控制台 http://localhost:9001  (dev / devdevdev)

cp .env.example .env.local   # 默认值已对准本地 MinIO，不用改
uv sync
```

### 1.2 单测（最快，零外部依赖）

```bash
uv run pytest tests/unit -q
# → 131 passed in ~3s
```

mock vista，验证 handler / contract / runtime 自身的逻辑分支。

### 1.3 集成测试（真 vista + 真 MinIO）

```bash
uv run pytest tests/integration
```

`tests/integration/test_real_vista_chain.py` 用真 vista 跑 detect / duplicate / evaluate 的最小链路，落地 MinIO，秒级。

### 1.4 端到端 FnF 流程（本地容器跑整条 7 步）

```bash
scripts/build_image.sh --dev          # 出 :dev 镜像（首次 ~6min，增量 ~30s）
uv run python scripts/run_flow_local.py \
    flows/research_pipeline.fdl \
    tests/fixtures/events/research_full_input.json
```

会按 fdl 里的 step 顺序起 docker → POST `/invoke` → 串状态。最贴近 FC 真实跑法，能抓 adapter 启动 / env 解析 / 函数间契约对接的问题。

需要：`.env.local` 里有 `ANTHROPIC_API_KEY` 和 `CZSC_TOKEN`；MinIO 在跑；`:dev` 镜像构好。

### 1.5 单函数容器内 invoke

```bash
scripts/docker_run.sh factor_detect tests/fixtures/events/factor_detect_min.json
# → 启容器 → POST /invoke → 打印响应 JSON → 自动清理
```

在生产部署前调单函数最方便的一档。

### 1.6 测试金字塔总览

| 层 | 位置 | 依赖 | 速度 | 何时跑 |
|---|---|---|---|---|
| 单测 | `tests/unit/` | 无 | ~3s | 改代码后 |
| 集成 | `tests/integration/` | docker compose | ~5s | 改 service / contract 后 |
| FnF 本地 | `scripts/run_flow_local.py` | docker + 镜像 + LLM key | 60-200s | 改 fdl / 跨函数契约后 |
| 部署 preflight | `tests/deploy_preflight/run_all.sh` | 真阿里云隔离命名空间 | 5-10min | 第一次部到生产前 |
| 线上冒烟 | `tests/smoke/` (`FC_SMOKE_READY=1`) | 真阿里云 | ~30s | deploy 后 |

---

## 2. 怎么调（API）

所有函数 / 工作流的入参出参都遵循同一个 envelope：

### 2.1 调用契约

**入参（EnvelopeIn）**：

```json
{
  "tenant": {
    "user_hash": "u_xxx",
    "workspace_id": "EXP_001",
    "workspace_kind": "research",
    "run_id": "run-2026042701",
    "requested_at": "2026-04-27T10:00:00Z"
  },
  "payload": { /* 函数特定字段，见 src/vista_fc/contracts/<name>.py */ }
}
```

**出参（EnvelopeOut）**：

```json
{
  "tenant": { /* 原样回填 */ },
  "status": "succeeded" | "failed" | "partial",
  "artifacts": [ {"kind": "duckdb", "oss_uri": "oss://...", "size_bytes": 12345, "sha256": "..."} ],
  "metrics": { "duration_ms": 1234, ... },
  "payload": { /* 函数特定结果，失败时为 null */ },
  "error": null | { "code": "VISTA_LOGIC_ERROR", "message": "...", "retriable": false, "trace_id": "tr-xxx" },
  "schema_version": "1.0"
}
```

每个函数的 `payload` 字段定义见对应 `src/vista_fc/contracts/<name>.py`，例如 [factor_detect.py](src/vista_fc/contracts/factor_detect.py)。

### 2.2 调单函数

#### 一把跑通：`scripts/invoke_all.{sh,py}`

仓库带了两份等价的教程脚本，部署后跑一遍可以验证全部 9 个函数 + FnF flow，也是最直接的客户端代码模板。

**Bash 版**（包 `s cli`，最少配置）：

```bash
FC_ACCESS=prod bash scripts/invoke_all.sh help     # 看命令清单
FC_ACCESS=prod bash scripts/invoke_all.sh plan     # 单步：调 factor-plan
FC_ACCESS=prod bash scripts/invoke_all.sh fnf      # ★ 推荐：启 FnF flow 端到端跑 7 步
FC_ACCESS=prod bash scripts/invoke_all.sh chain    # 按顺序串调每个函数（仅演示）
```

**Python 版**（直接走 alibabacloud SDK，跑通后可直接抠到你的 BFF / 客户端服务里用）：

```bash
ALIYUN_AK=... ALIYUN_SK=... ./scripts/invoke_all.py fnf       # 自动 uv inline-deps 装 SDK
ALIYUN_AK=... ALIYUN_SK=... ./scripts/invoke_all.py plan
```

两个脚本共用同样的 step 名 + 同样的环境变量（`USER_HASH` / `WORKSPACE_ID` / `RUN_ID` / `OSS_BUCKET` / `FC_SUFFIX`），结构对照写。每个 step 函数都展示一个最小 envelope，复制改改就能用。

#### 真到客户端代码里：阿里云 SDK 直调

不需要任何额外 trigger：

```python
from alibabacloud_fc20230330.client import Client
from alibabacloud_fc20230330 import models

client = Client(...)  # 凭据从 RAM 拿
resp = client.invoke_function(
    function_name="factor-detect",       # FC_SUFFIX 环境会带后缀
    request=models.InvokeFunctionRequest(
        body=json.dumps({
            "tenant": {...},
            "payload": {
                "factors_db_uri":    "oss://vista-fc-prod/.../factors.duckdb",
                "research_data_uri": "oss://vista-fc-prod/research_data/future_kline.duckdb",
                "max_workers": 4,
                "timeout": 60,
            },
        }).encode(),
    ),
)
envelope = json.loads(resp.body.read())
assert envelope["status"] == "succeeded"
```

或 serverless-devs CLI（开发期 ad-hoc）：

```bash
s cli fc invoke-function \
  --function-name factor-detect \
  --event "$(cat tests/fixtures/events/factor_detect_min.json)" \
  --access prod
```

需要前端 HTTP 直调？给函数加 HTTP trigger（在 s.yaml 对应资源 `triggers` 块下追加）：

```yaml
triggers:
  - name: http
    type: http
    config:
      authType: function    # 客户端要带 FC 签名头；anonymous 是无鉴权（慎用）
      methods: [POST]
      disableURLInternet: false
```

部署后 FC 给一个 `https://<account>.<region>.fcapp.run/<fn>` URL，POST envelope 进去即可。

### 2.3 调工作流（FnF）

研究全栈（plan→builder→detect→duplicate→evaluate→filter→backtest）通过 `research-pipeline` flow 一键跑：

```python
from alibabacloud_fnf20190315 import models, client as fnf_client

resp = fnf_client.start_execution(
    models.StartExecutionRequest(
        flow_name="research-pipeline",
        execution_name="exp-20260427-momentum",   # 同名重跑会跳过已成功的 step
        input=json.dumps({
            "tenant": {...},
            "user_input": "动量反转因子挖掘",
            "factor_numbers": 20,
            "batch_size": 5,
            "builder_type": "agno_agent",
            "problem_codes": ["FTS_PROBLEM_A504A636"],
            # ...其它参数见 flows/research_pipeline.fdl 顶部注释
        }),
    )
)

# 查执行状态
status = fnf_client.describe_execution(
    models.DescribeExecutionRequest(
        flow_name="research-pipeline",
        execution_name="exp-20260427-momentum",
    )
)
# Status: Running / Succeeded / Failed / Stopped
```

执行失败时的现场会被 `deadletter` 函数 dump 到 `oss://<bucket>/user_data/<u>/deadletter/<run_id>/<failed_function>.json`，含原始 payload + error code，可以人工 triage 后修参数重放。

### 2.4 函数清单与语义

| 函数 | 用途 | 主要入参 | 主要产出 |
|---|---|---|---|
| `factor-plan` | LLM 规划因子挖掘路线 | `user_input` (自然语言) | `routes_toml` (toml 文件 OSS uri) |
| `factor-builder` | LLM 按 plan 生成因子代码 | `routes_toml_uri`, `factor_numbers` | `factors.duckdb` (因子库) |
| `factor-detect` | 真数据评估因子有效性 | `factors_db_uri`, `research_data_uri` | 评估报告 + 标记结果 |
| `factor-duplicate` | 因子去重 / 相关性聚合 | `factors_db_uri`, `route_codes`, `problem_codes` | 去重后的因子集 |
| `factor-evaluate` | 策略建模评估（最重） | `factors_db_uri`, `models`, `problem_codes` | 模型评分 |
| `factor-filter` | 按指标筛选 top-N | `factors_db_uri`, `top_n`, `positive_metric` | 入选因子的 strategy.toml |
| `strategy-backtest` | wbt 综合回测 | `strategy_toml_uri`, `data_mode` | 回测报告 |
| `vista-realtime` | 实盘信号生成 | `strategy_toml_uri`, `update_mode`, `push_targets` | 实时信号 + 推送 |
| `deadletter` | FnF 故障兜底（catch.goto） | 失败 step 的 payload + error | 持久化故障现场到 OSS |

### 2.5 错误码

| code | 含义 | retry 策略 |
|---|---|---|
| `OSS_READ_FAIL` / `OSS_WRITE_FAIL` | OSS 瞬时抽风 | retriable，FnF 会指数退避重试 |
| `OSS_ETAG_CONFLICT` | 并发写冲突 | retriable，让另一边先赢 |
| `CLICKHOUSE_CONNECT` | CH 连不上 | retriable |
| `VISTA_LLM_RATE_LIMIT` | 上游 LLM 限流 | retriable |
| `VISTA_LOGIC_ERROR` | 业务错（数据 / 逻辑） | **non-retriable**，调用方修参数 |
| `INPUT_VALIDATION` | 入参不符合契约 | **non-retriable**，调用方修 payload |

---

## 3. 怎么部到正式环境

### 3.1 阿里云资源先决条件

第一次部署前手工开好（一次性，后面 IaC 化可放 Terraform）：

| 资源 | 用途 | 备注 |
|---|---|---|
| ACR 镜像仓库 | 存 `vista-fc-base` 镜像 | 命名空间 `vista`，仓库名 `vista-fc-base`，**企业版**可启镜像加速 |
| OSS bucket（生产） | 存 artifacts + deadletter | `vista-fc-prod`（或自定）；与 FC 同 region |
| NAS 文件系统 | 存 `factor.duckdb` + 研究产物 | 与 FC 同 VPC；mount target 填到 `NAS_MOUNT_TARGET` |
| VPC + 交换机 + 安全组 | FC 函数走 VPC 才能访问 NAS / CH | ID 填到 `VPC_ID` / `VSWITCH_ID` / `SG_ID` |
| RAM 角色 `fc-vista-role` | FC 执行函数的身份 | 需要 `oss:*`（自家 bucket）+ `nas:*`（自家 NAS）+ `cr:PullArtifact`（ACR） |
| RAM 角色 `fnf-vista-role` | FnF 调函数的身份 | 需要 `fc:InvokeFunction` |
| SLS Project + Logstore | 函数日志 | `LOG_PROJECT` / `LOG_STORE` |
| ClickHouse（可选） | `VISTA_DB_TYPE=clickhouse` 时用 | 走 `CLICKHOUSE_DSN` |

`accountId` 等填到 deploy 时的环境变量（见下）。

### 3.2 部署

```bash
# 1) 配 access — 一次性
cat >> ~/.s/access.yaml <<EOF
prod:
  AccountID: <your-aliyun-account-id>
  AccessKeyID: <ak>
  AccessKeySecret: <sk>
EOF

# 2) 准备环境变量（CI 从 secret store 拉，本地手动 export）
export FC_ACCESS=prod
export ALIYUN_ACCOUNT_ID=<your-account-id>
export FC_REGION=cn-hangzhou
export OSS_BUCKET=vista-fc-prod
export NAS_MOUNT_TARGET=<your-nas-mount>
export VPC_ID=vpc-xxx VSWITCH_ID=vsw-xxx SG_ID=sg-xxx
export LOG_PROJECT=vista-fc LOG_STORE=handlers
export ANTHROPIC_API_KEY=<...>  ANTHROPIC_BASE_URL=<可选>
export CZSC_TOKEN=<...>
export GIT_SHA=$(git rev-parse --short HEAD)

# 3) 推镜像（CI 用 push_image.sh，会先 docker login ACR）
ACR_USER=<...> ACR_PASS=<...> scripts/push_image.sh

# 4) 部署 FC 函数 + FnF flow
s deploy --access prod --assume-yes
# → 读 s.yaml，部 9 个 fc3 函数 + 3 个 fnf 流（其中 backtest-fanout 仅当 research_full
#   被外部调用时才用得上，不调可以从 s.yaml 摘掉）

# 5) 冒烟验证
FC_SMOKE_READY=1 FC_ACCESS=prod uv run pytest tests/smoke -v
```

### 3.3 单函数迭代 / 回滚

`s deploy <资源名>` 只更新一个函数，比全栈 deploy 快很多：

```bash
# 改了 factor-detect 代码 → 推新镜像 → 只 redeploy 这一个
GIT_SHA=$(git rev-parse --short HEAD) scripts/push_image.sh
s deploy factor-detect --access prod --assume-yes

# 回退某个函数到老版本（不动其他函数）
GIT_SHA=<old_sha> s deploy factor-detect --access prod --assume-yes

# 全栈回退
GIT_SHA=<old_sha> s deploy --access prod --assume-yes
```

**回滚不走 git revert**，只换镜像 tag。FnF flow 自带 step checkpoint，重跑同名 executionName 时已成功的 step 自动跳过，配合 deadletter 落盘的 payload 可以人工修 → 重放。

### 3.4 实盘函数（vista-realtime）

实盘有两份 yaml，**独立部署、独立决定要不要开**：

| Yaml | 函数名 | 触发 | 用途 |
|---|---|---|---|
| `s.yaml` 里的 `vista-realtime` | `vista-realtime${suffix}` | 无（SDK / 函数 URL 直调） | 跟其它函数一起 `s deploy` 进来；外部交易系统 push tick 时调用 |
| `s.realtime-cron.yaml` 里的 `vista-realtime-cron` | `vista-realtime-cron${suffix}` | `@every 1m` cron | 自动 tick；想用就单独 `s deploy -t s.realtime-cron.yaml` |

两个函数共用 `handlers.vista_realtime:handler`，只差触发方式。可以同时部署、单独留一个、或都不要。

```bash
# 想要 cron 自动 tick：
s deploy -t s.realtime-cron.yaml --access prod --assume-yes

# 不想了：
s remove -t s.realtime-cron.yaml --access prod --assume-yes

# 临时关掉 cron 但保留函数（方便排错）：
REALTIME_CRON_ENABLE=false s deploy -t s.realtime-cron.yaml --access prod --assume-yes
```

如果 SDK-invoke 路径要 sub-second 响应、且 cron 撑温没用上：给 `s.yaml` 里 `vista-realtime` 资源的 `props` 下追加 `provisionConfig`：

```yaml
provisionConfig:
  qualifier: LATEST
  target: 1
  alwaysAllocateCPU: true
```

约 200-300 元/月（cn-hangzhou 1vCPU+4GB 24×7）；只要交易时段开的话加 `scheduledActions` 定时上下线砍到 ~1/4。

### 3.5 监控

- **日志**：`LOG_FORMAT=json` 默认开，每行一个 JSON 进 SLS。关键字段：`run_id` / `function_name` / `status` / `error.code`。敏感值（`sk-*` / `Bearer *` / `LTAI*` 等）handler 自动脱敏。
- **指标**：每次调用末尾 emit 一行 `event=metric, metric_name=handler.duration_ms, ...`。SLS 上配索引 `metric_name: text, metric_value: double` 后可以直接 P50/P95 查询。
- **告警**：建议挂 (a) `error_rate > 5%` 持续 5min；(b) `metric_value` p95 翻倍；(c) deadletter OSS 路径下有新对象。

### 3.6 第一次上生产前推荐先跑 preflight

```bash
export FC_ACCESS=dev-preflight
export FC_SUFFIX="-preflight-$(git rev-parse --short HEAD)"
export OSS_BUCKET=vista-fc-preflight   # 隔离 bucket
bash tests/deploy_preflight/run_all.sh
# → 11 步：ACR 推 / 凭据 / RAM / VPC / NAS / OSS / CH / 单函数 deploy+invoke /
#   SLS / flow deploy / flow execute；任一失败 exit 1，最后自动拆资源
```
