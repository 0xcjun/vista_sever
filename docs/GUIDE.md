# vista-fc 指南

本仓库把 vista 投研框架的 8 个业务流程封装成阿里云函数计算 (FC 3.0) 函数，由函数工作流 (FnF) 编排。**最终目标：给前端提供一组 HTTP API，前端调用后由阿里云 FC 执行 vista 工作流并返回结构化结果。**

vista 及其私有传递依赖（`chan-factor-rs` / `chanfactor`）从私有源 [`zbczsc-dev`](https://pypi.zbczsc.com/team/dev/+simple/) 解析，无需认证，`pyproject.toml` 的 `[tool.uv.sources]` 已配好路由。

---

## 目录

- [1. 实际开发](#1-实际开发)
- [2. 本地测试](#2-本地测试)
- [3. 模拟真实环境测试](#3-模拟真实环境测试)
- [4. 真实环境部署](#4-真实环境部署)
- [5. 前端接入](#5-前端接入)
  - [5.1 方案 A：FC 3.0 HTTP 触发器（单函数调用）](#51-方案-afc-30-http-触发器单函数调用)
  - [5.2 方案 B：API 网关（统一入口）](#52-方案-b阿里云-api-网关统一入口推荐生产用)
  - [5.3 方案 C：BFF + FnF（全流程调用）](#53-方案-cbff--fnf全流程调用)
  - [5.4 统一调用契约](#54-统一调用契约)
  - [5.5 函数到 HTTP 语义映射](#55-函数到-http-语义映射)
- [附录：仓库结构](#附录仓库结构)

---

## 1. 实际开发

**先决条件**

| 组件 | 安装 |
|---|---|
| Python 3.12 | `uv python install 3.12` |
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop ≥ 28 | 官网 |
| [serverless-devs](https://www.serverless-devs.com/) | `npm i -g @serverless-devs/s`（仅部署/s local 需要） |

### 1.1 首次设置

```bash
# 克隆并装依赖（vista / chan-factor-rs / chanfactor 从 zbczsc-dev 私有源拉，无需认证）
git clone <repo> vista_sever && cd vista_sever
uv sync

# 验证 import 链
uv run python -c "
import vista, wbt, wbt.mock
from vista_fc.services import factor_detect_service, factor_plan_service
from vista_fc.contracts import FactorDetectInput
print('vista + vista-fc import OK')
"

# 本地环境变量
cp .env.example .env.local   # 不再需要改，默认已是本地 MinIO 模式

# pre-commit 钩子
uv run pre-commit install
```

> `requires-python` 锁在 `>=3.12,<3.13`，与生产镜像一致，不要用 3.11。

### 1.2 日常开发循环

```bash
# 起本地外部依赖（MinIO + ClickHouse）
docker compose -f dev/compose.yaml up -d
# → MinIO 控制台:  http://localhost:9001  (dev / devdevdev)
# → ClickHouse:    http://localhost:8123

# 改代码 → 单测（秒级反馈）
uv run pytest tests/unit -v

# 跑完整测试
uv run pytest tests/unit tests/integration

# Lint / Type
uv run ruff check
uv run basedpyright

# 提交前 pre-commit 会自动跑（ruff-format + gitleaks + detect-secrets）
git add <files> && git commit -m "feat: ..."

# 收工
docker compose -f dev/compose.yaml down
```

### 1.3 环境变量矩阵

不同函数对 env 的依赖不同，误配置就是跑通/跑不通的分水岭。本仓库代码路径实际读的变量：

| 变量 | 类别 | plan | builder | detect | duplicate | evaluate | filter | backtest | realtime |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `OSS_REGION` / `OSS_BUCKET` / `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | 存储 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `OSS_ENDPOINT` | 存储 | 本地 | 本地 | 本地 | 本地 | 本地 | 本地 | 本地 | 本地 |
| `OSS_S3_COMPAT` | 存储模式切换 | 本地=true | 本地=true | 本地=true | 本地=true | 本地=true | 本地=true | 本地=true | 本地=true |
| `NAS_CACHE_ROOT` | 缓存目录 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ANTHROPIC_API_KEY` | LLM | **必需** | **必需** | — | — | — | — | — | — |
| `ANTHROPIC_BASE_URL` | LLM 反代 | 反代必填 | 反代必填 | — | — | — | — | — | — |
| `CLAUDE_MODEL` | LLM 模型 | 可选 | 可选 | — | — | — | — | — | — |
| `AGNO_MODEL` | agno 引擎 | — | 可选 | — | — | — | — | — | — |
| `CZSC_TOKEN` | 行情 API | 真数据 | 真数据 | 真数据 | — | — | — | **必需** | **必需** |
| `CZSC_DATA_API` | 行情 API | 可选 | 可选 | 可选 | — | — | — | 可选 | 可选 |
| `VISTA_DB_TYPE` | 因子库模式 | — | — | — | — | — | 可选 | — | — |
| `DUCKDB_PATH` | 本地因子库 | — | ✓ | — | — | — | ✓ | — | — |
| `CLICKHOUSE_DSN` | CH 因子库 | — | CH 模式 | — | — | — | CH 模式 | — | — |
| `VISTA_RESEARCH_PATH` | 研究产物目录 | — | — | — | — | — | — | ✓ | — |

说明：
- **"本地"**：本地开发用 MinIO 时必填；线上 Aliyun OSS 留空。
- **"真数据"**：fixture/mock 数据分支不触发 `vista.data.xy|strategy`；但只要函数真调到这俩模块，未设 token 会在 import 时 `assert` 挂进程（严重故障）。
- **`CLICKHOUSE_URL/USER/PASS`**（注意不是 vista 能读的名字）：仅 `tests/deploy_preflight/08_ch_probe.sh` 用来 curl 健康检查，**不会被 FC 容器内代码消费**。vista 实际读 `CLICKHOUSE_DSN`（或 `CLICKHOUSE_HOST/PORT/DATABASE/USERNAME/PASSWORD`，注意命名差异）。
- **默认模式**：`VISTA_DB_TYPE=duckdb`，`DUCKDB_PATH=/mnt/vista-cache/factor.duckdb`（由 `s.yaml` 默认值兜底）；要走 ClickHouse 必须显式 `VISTA_DB_TYPE=clickhouse` + 填 `CLICKHOUSE_DSN`。

完整默认值看 `.env.example` 和 `s.yaml` 的 `common-env` 块。

### 1.4 修改/新增函数

业务分三层，改动的切入点按层而定：

```
handlers/<name>.py       ← FC 入口，3 行的 thin wrapper
src/vista_fc/services/   ← 业务服务（调 vista 的地方）
src/vista_fc/contracts/  ← pydantic DTO（入参/出参契约）
```

改 DTO 后刷新快照：

```bash
uv run pytest tests/unit/contracts/test_schema_snapshot.py --snapshot-update
```

加新函数的 checklist：
1. `src/vista_fc/contracts/<name>.py` — 定义 `XxxInput` / `XxxOutput`
2. `src/vista_fc/services/<name>.py` — 业务代码，接 `XxxInput` 返 `XxxOutput`
3. `handlers/<name>.py` — 拷贝 `handlers/factor_detect.py` 改 import 和 service 即可
4. `s.yaml` — 加一个 `fc3` 资源块（复制 `factor-plan` 改名）
5. `tests/unit/handlers/test_<name>.py` — 照着现有 handler 单测写

---

## 2. 本地测试

测试金字塔，由快到慢：

| 层 | 位置 | 依赖 | 规模 | 用途 |
|---|---|---|---|---|
| 单测 | `tests/unit/` | 无 | 103 | mock vista，毫秒级，回归核心逻辑 |
| 集成 | `tests/integration/` | docker compose | 4 | 真 vista + 真 MinIO，秒级 |
| 冒烟（线上） | `tests/smoke/` | 真阿里云 FC | 4 | `FC_SMOKE_READY=1` 才跑 |
| 部署 preflight | `tests/deploy_preflight/` | 真阿里云 + RAM 子账号 | 11 步 bash | 隔离命名空间自毁式验证 |

### 2.1 只跑单测（最快，无副作用）

```bash
uv run pytest tests/unit
# → 103 passed in ~4s
```

### 2.2 单测 + 集成

```bash
# 起本地依赖
docker compose -f dev/compose.yaml up -d

# 跑
uv run pytest tests/unit tests/integration
# → 107 passed in ~5s
```

集成测试的关键机制：`OSS_S3_COMPAT=true` 让 `OssClient.from_env()` 走 boto3 后端，同一份代码连本地 MinIO；生产不设这个变量走 `oss2` 直连阿里云 OSS。

### 2.3 覆盖率

```bash
uv run pytest --cov=src/vista_fc --cov=handlers --cov-report=html
open htmlcov/index.html
```

### 2.4 按名字筛选

```bash
uv run pytest -k "factor_detect"
```

---

## 3. 模拟真实环境测试

**目标：在本地跑完整的 FC 协议栈**——构建生产镜像 → 容器里 HTTP POST `/invoke` → 真 vista 读写本地 MinIO 报告。这是部署前的最后一道防线，能抓到单测/集成都抓不到的协议层问题（adapter 启动、env 解析、handler args、镜像层依赖缺失等）。

### 3.1 构建镜像

**只支持 `linux/amd64`**：私有源没发布 `chan-factor-rs` / `chanfactor` 的 linux aarch64 wheel，多 arch 构建解析失败。

```bash
scripts/build_image.sh --dev           # 产出 :dev，约 1.8 GB
scripts/build_image.sh                 # 产出 :<git_sha>（push 用）
```

首次构建 ~6 分钟（apt 走阿里云镜像源已加速）；后续增量构建 ~30 秒（buildx 缓存）。

### 3.2 容器内 smoke

```bash
# import 链
docker run --rm --entrypoint python \
  registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:dev \
  -c "import vista, wbt.mock; print('OK')"

# adapter 启动 + /health
docker run -d --rm --name vc-smoke -p 9878:9000 \
  registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:dev \
  handlers.factor_detect:handler
curl -s http://localhost:9878/health   # → {"status":"ok"}
docker rm -f vc-smoke
```

### 3.3 真 handler 端到端调用

先往 MinIO 塞测试数据：

```bash
docker run --rm --network dev_default \
  -v "$PWD/tests/fixtures/duckdb:/seed:ro" \
  --entrypoint sh minio/mc:latest -c '
    mc alias set l http://minio:9000 dev devdevdev &&
    mc cp /seed/mini_factors.duckdb \
       l/vista-fc-dev/user_data/u_local_dev/research/EXP_LOCAL/factors.duckdb
  '
```

然后用 `docker_run.sh` 起临时容器、POST `/invoke`、自动清理：

```bash
scripts/docker_run.sh factor_detect tests/fixtures/events/factor_detect_min.json
# → 打印响应 JSON，status 应为 "succeeded"
# → 响应落到 /tmp/vista_fc_invoke_resp.json
```

脚本行为：
- 默认宿主端口 `9878`（9000 被 MinIO 占了），`PORT=xxxx` 可覆盖
- 自动把 `.env.local` 里的 `localhost` 改写成 `host.docker.internal`，并 `--add-host` 注入
- 容器退出时自动 `docker rm -f`

### 3.4 `s local invoke`（走 serverless-devs 协议）

```bash
scripts/local_invoke.sh factor-detect                       # 一次性 invoke
scripts/local_invoke.sh factor-detect --server              # 常驻 HTTP server
scripts/local_invoke.sh factor-detect --debug               # 带 debugpy 附加
```

比 `docker_run.sh` 多走一层 `s` CLI（跟真线上 CI 路径最接近），代价是启动慢。

### 3.5 当前 E2E 覆盖

| 函数 | E2E 验证 | 产物上传 | 备注 |
|---|---|---|---|
| factor-plan | ✅（走 LLM）| ✅ `factor_routes.toml` ~3 KB | 本地 `CLAUDE_MODEL=glm-4.7`（智谱反代）已验证 |
| factor-detect | ✅（mini_factors fixture）| ✅ `detect_*.json` 157 B | 空数据，走逻辑分支覆盖，不触 `vista.data.xy` |
| factor-builder | ❌ | — | 需要 ANTHROPIC_API_KEY + `factor_routes.toml` 上游产物，未单独验证 |
| factor-duplicate | ❌ | — | 需要真实 factors.duckdb + route/problem codes，未写 fixture |
| factor-evaluate | ❌ | — | 同上 |
| factor-filter | ❌ | — | 需要 factor_db（duckdb 或 CH），未验证 |
| strategy-backtest | ❌ | — | 需要 `CZSC_TOKEN` + `strategy.toml`，未验证 |
| vista-realtime | ❌ | — | 需要 `CZSC_TOKEN` + `strategy.toml`，未验证 |

**已知 service 层产物上传风险**（检查过源码）：
- `factor_plan.py` — 已修复（原代码找不存在的 `toml_text` 字段，上传 0 字节）
- `factor_builder.py` — `data.get("routes", [])` 依赖 vista `FactorBuilder.run()` 返回有 `routes` 字段；未经真实 LLM 调用验证，潜在风险
- `factor_detect.py` / `factor_duplicate.py` / `factor_evaluate.py` — 直接 `json.dumps(dumped, …)` 落盘，不依赖字段存在性，产物非空

### 3.6 已有 fixture event

`tests/fixtures/events/` 目前提供：`factor_detect_min.json` / `factor_plan_min.json` / `vista_realtime_min.json`。其他函数自己照 `XxxInput` DTO 拼：

```bash
uv run python -c "
from vista_fc.contracts import FactorEvaluateInput
import json
print(json.dumps(FactorEvaluateInput.model_json_schema(), indent=2, ensure_ascii=False))
"
```

---

## 4. 真实环境部署

```
本地 uv sync          阿里云 ACR                 阿里云 FC 3.0
     │                   ▲                         ▲
     ▼                   │                         │
  pytest             build_image → push         s deploy
                                                   │
                                                   ▼
                                      8 FC 函数 + 3 FnF 流上线
```

### 4.1 阿里云资源先决条件

一次性准备：

- 部署账号（RAM 用户）：`AliyunFCFullAccess` + `AliyunContainerRegistryFullAccess`
- ACR 仓库 `vista/vista-fc-base`（个人版或企业版）
- VPC + vswitch + 安全组（FC 函数运行网络）
- NAS 文件系统 + 挂载点（k 线缓存）
- OSS Bucket：至少 `vista-fc-dev` / `vista-fc-preflight` / `vista-fc-prod`
- ClickHouse 对 FC 所在 VPC 可达（8123 入站放通）
- RAM 角色：`fc-vista-role`（函数执行）、`fnf-vista-role`（FnF 调 FC）

### 4.2 配置 serverless-devs 访问

```bash
s config add --access-alias dev   # 输入 AK/SK，用开发账号
s config add --access-alias prod  # 输入 AK/SK，用生产账号
```

### 4.3 推镜像

```bash
# 一次性 login
docker login registry.cn-hangzhou.aliyuncs.com

# 构建 + 推（linux/amd64）
GIT_SHA=$(git rev-parse --short HEAD)
scripts/push_image.sh
# → 产出 :<git_sha> 和 :main 两个 tag
```

### 4.4 环境变量

部署前导出（每环境一份）：

```bash
export FC_REGION=cn-hangzhou
export ALIYUN_ACCOUNT_ID=1234567890
export OSS_BUCKET=vista-fc-dev
export VPC_ID=vpc-xxx
export VSWITCH_ID=vsw-xxx
export SG_ID=sg-xxx
export NAS_MOUNT_TARGET=xxx.cn-hangzhou.nas.aliyuncs.com:/xxx
export LOG_PROJECT=vista-fc
export LOG_STORE=handlers
export CLICKHOUSE_URL=http://ch-internal:8123
export CLICKHOUSE_USER=prod_user
export CLICKHOUSE_PASS=<from secret store>
export ANTHROPIC_API_KEY=<from secret store>
export GIT_SHA=$(git rev-parse --short HEAD)
```

### 4.5 部署

```bash
# 静态校验
s verify
uv run python scripts/validate_flow.py

# 全量部署
s deploy --access dev --assume-yes

# 单资源部署（迭代时更快）
s deploy factor-detect --access dev
s deploy research-pipeline-flow --access dev
```

### 4.6 preflight 隔离验证（部署到 dev 前推荐）

```bash
export FC_ACCESS=dev-preflight
export FC_SUFFIX="-preflight-$(git rev-parse --short HEAD)"
export OSS_BUCKET=vista-fc-preflight

bash tests/deploy_preflight/run_all.sh
# → 11 步：ACR 推拉 / RAM / VPC / NAS / OSS / ClickHouse / flow 执行
# → 任一步失败 exit 1，99_cleanup.sh 最后自动拆资源
```

### 4.7 线上冒烟（部署后）

```bash
FC_SMOKE_READY=1 uv run pytest tests/smoke --access dev
```

### 4.8 回滚

不走 git revert，换镜像 tag：

```bash
git log --oneline | head -5
GIT_SHA=<old_sha> s deploy --access prod --assume-yes
```

---

## 5. 前端接入

**前端最终调用形态：一组 HTTPS API → 阿里云 FC → vista 业务。**

设计原则是**灵活组合**：每个函数都是独立的 HTTP endpoint，FnF 流把常用的端到端串好；前端可以按场景任意选：

| 调用模式 | 用什么 | 典型场景 |
|---|---|---|
| **单函数** | 直接 POST 到 `<fn>` 的 HTTP 触发器 | 只要一个步骤的结果（如只跑 `factor-detect` 体检、只跑 `factor-evaluate` 评估） |
| **全流程** | POST 到 BFF 入口 → FnF `StartExecution` 启动 `research-pipeline` / `research-full` / `backtest-fanout` | 一键从 idea → 策略 TOML |
| **自定义组合** | 前端自己按顺序调多个单函数，用返回的 `artifacts[].oss_uri` 串起来 | UI 想允许用户中途调参、分步审核、局部重跑 |

核心契约：所有函数和 FnF 流的入参都是 `EnvelopeIn<Payload>`、出参都是 `EnvelopeOut<Payload>`（见 [§5.4](#54-统一调用契约)），串起来时只需把上一步 `artifacts[i].oss_uri` 塞到下一步对应字段即可。

目前函数只有内部 SDK 调用（`s cli fc3 invoke`），**对前端开放需要先加触发器或 API 网关**。下面三种方案可任意组合。

### 5.1 方案 A：FC 3.0 HTTP 触发器（单函数调用）

每个函数加一个 HTTP 触发器，FC 生成 `https://<account>.<region>.fcapp.run/<fn>` 形态的 URL。`s.yaml` 在对应资源下加：

```yaml
factor-detect:
  component: fc3
  props:
    function:
      functionName: factor-detect${vars.functionSuffix}
      # ...其它不变
    triggers:
      - name: http
        type: http
        config:
          authType: function   # 前端需带签名或 token
          methods: [POST]
          disableURLInternet: false
```

前端调用（同步短任务）：

```js
const res = await fetch("https://<account>.cn-hangzhou.fcapp.run/factor-detect", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "<FC-signed-token>",   // 见阿里云 FC 签名文档
  },
  body: JSON.stringify({
    tenant: { user_hash, workspace_id, workspace_kind: "research", run_id, requested_at },
    payload: { factors_db_uri: "oss://...", max_workers: 4, timeout: 60 },
  }),
});
const out = await res.json();
// out.status === "succeeded"
// out.payload === FactorDetectOutput
// out.error === null | { code, message, retriable, trace_id }
```

**多个单函数串联调用**（前端/BFF 把 oss_uri 传下去）：

```js
// 步骤 1：挖因子
const plan = await callFn("factor-plan", { tenant, payload: { user_input, plan_model, ...}});

// 步骤 2：基于 plan 的 artifact 继续跑 builder
const build = await callFn("factor-builder", {
  tenant,
  payload: {
    route_codes: plan.payload.route_codes,
    factor_plan_uri: plan.artifacts.find(a => a.kind === "factor_plan_json").oss_uri,
    // ...
  },
});

// 步骤 3：体检
const detect = await callFn("factor-detect", {
  tenant,
  payload: { factors_db_uri: build.payload.factors_db_uri, max_workers: 4 },
});
```

前端可以停在任何一步、回退重跑、修改参数，比调 FnF 更灵活，代价是串联逻辑在前端/BFF 里。

> FnF 流不能直接开 HTTP trigger — 需要前端先调一个 BFF 函数，由 BFF 去 `StartExecution`。见方案 C。

### 5.2 方案 B：阿里云 API 网关（统一入口，推荐生产用）

- 网关统一做**鉴权、限流、CORS、签名验签、字段级审计**
- 对前端暴露干净的 `https://api.example.com/v1/factor-detect`，后端路由到内部 FC 函数
- FnF 流可以走网关的「函数工作流后端」类型，前端统一体验

部署不在本仓库内，参考阿里云 API 网关 → 创建 API → 后端服务类型选「函数计算」即可。

### 5.3 方案 C：BFF + FnF（全流程调用）

长流程（完整 research pipeline / 全量 backtest fanout）必须走 FnF —— FnF 是异步执行引擎，本身不能直接 HTTP 触发，需要一个薄 BFF 函数把 HTTP → `StartExecution` 做桥。

典型布局（新增 2 个 BFF 函数，不动现有 8 个业务函数）：

| BFF 函数 | 作用 | 前端看到的 API |
|---|---|---|
| `flow-start` | 解析 `{flowName, input}`，调 `StartExecution`，立即返回 `executionName` | `POST /flow-start` |
| `flow-status` | 根据 `executionName` 调 `DescribeExecution`，返回 `{status, currentStep, output?}` | `GET /flow-status?id=xxx` |

```
前端
 │   POST /flow-start {"flowName":"research-pipeline","input":{tenant,...}}
 ▼
flow-start (FC)  ── StartExecution ──►  FnF: research-pipeline
                                        │  plan → build → detect → …
                                        ▼
                                        （异步执行，可能几分钟到几小时）
前端
 │   轮询 GET /flow-status?id=<executionName>
 ▼
flow-status (FC) ── DescribeExecution ──►  FnF
                                        ◄── {status, output?}
```

实现参考（BFF 函数大概 30 行 Python，不在本仓库现成代码里，下个迭代加）：

```python
# handlers/flow_start.py（待实现）
from alibabacloud_fnf20190315.client import Client
def handler(event, context):
    fnf = Client(...)
    resp = fnf.start_execution(StartExecutionRequest(
        flow_name=event["payload"]["flowName"] + FC_SUFFIX,
        execution_name=f'{tenant.workspace_id}-{int(time.time())}',
        input=json.dumps(event["payload"]["input"]),
    ))
    return {"executionName": resp.name, "status": "Running", ...}
```

前端调用：

```js
// 启动
const { executionName } = await fetch("/flow-start", {
  method: "POST",
  body: JSON.stringify({
    flowName: "research-pipeline",
    input: { tenant, user_input, plan_model: "claude-opus-4-7", ...fullPipelineArgs },
  }),
}).then(r => r.json());

// 轮询（2-5s 间隔，直到 status ∈ {Succeeded, Failed, Stopped}）
let status = "Running";
while (status === "Running") {
  await sleep(3000);
  const r = await fetch(`/flow-status?id=${executionName}`).then(r => r.json());
  status = r.status;
  updateUI(r.currentStep);
}
```

三个 FnF 流可选：

- `research-pipeline` — `plan → build → detect → duplicate → evaluate → filter`
- `backtest-fanout` — `ForEach` 批量回测多个策略 TOML
- `research-full` — 上面两者合一（factor 挖掘 + 每个入选策略回测）

### 5.4 统一调用契约

```ts
// 入参
type EnvelopeIn<Payload> = {
  tenant: {
    user_hash: string;
    workspace_id: string;
    workspace_kind: "research" | "realtime" | "backtest";
    run_id: string;
    requested_at: string;   // ISO 8601
  };
  payload: Payload;         // 每个函数有自己的 XxxInput DTO
};

// 出参
type EnvelopeOut<Payload> = {
  tenant: EnvelopeIn["tenant"];
  status: "succeeded" | "failed";
  artifacts: Array<{ kind: string; oss_uri: string; size_bytes: number; sha256: string }>;
  metrics: Record<string, number>;
  payload: Payload | null;  // 失败时 null
  error: null | {
    code: string;          // e.g. "INPUT_VALIDATION" / "OSS_READ_FAIL" / "VISTA_LOGIC_ERROR"
    message: string;
    retriable: boolean;
    trace_id: string;
  };
};
```

DTO 的 JSON schema 从代码生成：

```bash
uv run python -c "
from vista_fc.contracts import FactorDetectInput, FactorDetectOutput
import json
print(json.dumps({
  'input':  FactorDetectInput.model_json_schema(),
  'output': FactorDetectOutput.model_json_schema(),
}, indent=2, ensure_ascii=False))
"
```

建议给前端导出一份 `schemas/*.json` 让他们生成 TS 类型。

### 5.5 函数到 HTTP 语义映射

每个函数都同时支持所有三种方案，下表只是**推荐默认值**：

| 函数 | 单独调（A/B） | 作为流水线一步（C） | 典型耗时 |
|---|---|---|---|
| factor-plan | ✅ 同步 HTTP | ✅ `research-pipeline` 首节点 | 10–30 s |
| factor-builder | ⚠️ 超过 HTTP 60s 限，建议异步 | ✅ 必须 | 10 min – 1 h |
| factor-detect | ✅ 同步 HTTP | ✅ | 5–30 s |
| factor-duplicate | ✅ 同步 HTTP | ✅ | 10–60 s |
| factor-evaluate | ⚠️ 可能超时，建议异步 | ✅ | 30 s – 5 min |
| factor-filter | ✅ 同步 HTTP | ✅ | 5–10 s |
| strategy-backtest | ⚠️ 建议异步 | ✅ `backtest-fanout` 的 ForEach body | 1–10 min |
| vista-realtime | timer 触发，不对前端暴露 | — | — |

> HTTP trigger 最大 900 s（FC 3.0）；超过就走 FnF。实际前端体验建议 >10 s 的都加 loading state 或改异步。

---

## 附录：仓库结构

```
vista_sever/
├── src/vista_fc/            业务包
│   ├── contracts/           8 组 pydantic DTO + common envelope
│   ├── storage/             oss_client (oss2 + s3-compat) / workspace / nas_cache / uri
│   ├── runtime/             adapter (HTTP /invoke) / logging / errors / context
│   └── services/            8 个业务服务（调 vista）
├── handlers/                FC 入口 (8 thin handlers) + _base.run_handler
├── flows/                   3 个 FnF FDL
├── tests/
│   ├── unit/                快速单测（103 个）
│   ├── integration/         真 vista + 真 MinIO（4 个）
│   ├── smoke/               线上冒烟（需 FC_SMOKE_READY=1）
│   ├── deploy_preflight/    11 步 bash 脚本
│   └── fixtures/            mini_factors.duckdb / events/*.json
├── dev/
│   ├── compose.yaml         本地 MinIO + ClickHouse
│   └── init/                init.sql + bucket bootstrap
├── scripts/
│   ├── build_image.sh       本地/CI 构建
│   ├── push_image.sh        ACR login + push
│   ├── local_invoke.sh      s local invoke 包装
│   ├── docker_run.sh        直接 docker run（不走 s CLI）
│   └── validate_flow.py     FDL 静态校验器
├── docs/
│   ├── GUIDE.md             本文件
│   ├── RUNBOOK.md           运维 playbook + 故障排除
│   └── superpowers/         设计文档
├── s.yaml                   serverless-devs 主清单（8 函数 + 3 flow）
├── Dockerfile               多阶段构建（python:3.12-slim + linux/amd64）
├── pyproject.toml           依赖 + 工具配置
└── .env.example             本地环境变量模板
```

---

## 参考

- [RUNBOOK.md](RUNBOOK.md) — 运维剧本 + 故障排除 + 告警处置
- [设计文档](superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md) — 完整架构决策
- [Serverless Devs](https://www.serverless-devs.com/)
- [阿里云函数计算 FC 3.0](https://www.aliyun.com/product/fc)
- [函数工作流 FnF](https://www.aliyun.com/product/fnf)
- [API 网关 + FC 集成](https://help.aliyun.com/document_detail/54788.html)
