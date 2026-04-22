# vista-fc 使用与部署指南

本仓库把 [vista](../../cursorPro/vista) 投研框架的 8 个业务流程封装为阿里云函数计算 (FC 3.0) 函数，由函数工作流 (FnF) 编排，使用 [serverless-devs](https://www.serverless-devs.com/) 管理部署。

---

## 目录

- [1. 架构速览](#1-架构速览)
- [2. 先决条件](#2-先决条件)
- [3. 本地开发](#3-本地开发)
  - [3.1 首次设置](#31-首次设置)
  - [3.2 日常开发循环](#32-日常开发循环)
  - [3.3 运行测试](#33-运行测试)
  - [3.4 本地 MinIO 集成（OSS_S3_COMPAT）](#34-本地-minio-集成oss_s3_compat)
- [4. 镜像与部署](#4-镜像与部署)
  - [4.1 构建 Docker 镜像](#41-构建-docker-镜像)
  - [4.2 推送到 ACR](#42-推送到-acr)
  - [4.3 部署到阿里云 FC](#43-部署到阿里云-fc)
  - [4.4 preflight 部署链路校验](#44-preflight-部署链路校验)
- [5. 调用函数](#5-调用函数)
- [6. 监控与日志](#6-监控与日志)
- [7. 故障排除](#7-故障排除)
- [8. 已知阻塞项](#8-已知阻塞项)

---

## 1. 架构速览

```
调用方 ─→ HTTP / StartExecution ─→ Serverless Workflow (FnF)
                                        │
                                        ▼
                              FC 3.0 · 8 functions
                              (共享镜像 vista-fc-base:<git_sha>)
                                        │
                              ┌─────────┼─────────┐
                              ▼         ▼         ▼
                              OSS      NAS     ClickHouse
                         (用户数据)  (热缓存)   (行情/因子值)
```

**8 个函数**（`src/vista_fc/services/` + `handlers/`）：

| FC 函数 | vista 入口 | 作用 |
|---|---|---|
| factor-plan | `vista.agents.factor_plan.plan_factor_routes` | 交易想法 → 因子路线 |
| factor-builder | `vista.agents.factor_builder.FactorBuilder` | LLM 批量挖因子 |
| factor-detect | `vista.utils.factor_detect.factor_detect` | 未来数据 / 方差体检 |
| factor-duplicate | `vista.utils.factor_duplicate.factor_duplicate` | 相关性去冗余 |
| factor-evaluate | `vista.utils.factor_evaluate.factor_evaluate` | 策略建模评估 |
| factor-filter | `vista.utils.factor_filter.factor_filter` | top-n 精筛 → 策略 TOML |
| strategy-backtest | `vista.utils.strategy_backtest.run_strategy_backtest` | 单份 TOML 完整回测 |
| vista-realtime | `vista.realtime.workflow.RealtimeWorkflow` | 实盘定时更新 |

**3 个 FnF 流**（`flows/`）：

- `research_pipeline.fdl` — `plan → build → detect → duplicate → evaluate → filter`
- `backtest_fanout.fdl` — `ForEach` 批量回测
- `research_full.fdl` — 上述两者组合

设计细节见 [docs/superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md](superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md)。

---

## 2. 先决条件

### 本地开发

| 组件 | 用途 | 安装 |
|---|---|---|
| Python 3.12 | 运行时 | `uv python install 3.12` |
| [uv](https://docs.astral.sh/uv/) | 包管理 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop ≥ 28 | 本地 MinIO / ClickHouse + 镜像构建 | 官网 |
| [serverless-devs](https://www.serverless-devs.com/) | FC 部署 + 本地调用 | `npm i -g @serverless-devs/s` |
| vista 源代码 | 业务逻辑 | 克隆到 `../cursorPro/vista` 并在其中 `uv sync` |

### 阿里云（部署时）

- 账号 + RAM 用户（部署账号）带 `AliyunFCFullAccess` + `AliyunContainerRegistryFullAccess`
- ACR 个人版 / 企业版命名空间 `vista` + 仓库 `vista-fc-base`
- VPC + 交换机 + 安全组（FC 函数所处网络）
- NAS 文件系统 + 挂载点（用于 k 线缓存 / 模型权重）
- OSS Bucket 至少 3 个：`vista-fc-dev` / `vista-fc-preflight` / `vista-fc-prod`
- ClickHouse 服务可达 FC 所在 VPC
- 两个函数运行角色：`fc-vista-role`（FC 执行角色）、`fnf-vista-role`（FnF 调用 FC 的角色）

---

## 3. 本地开发

### 3.1 首次设置

```bash
# 1. 克隆并进入
git clone <repo> vista_sever && cd vista_sever

# 2. 确保 vista 源代码在 ../cursorPro/vista 且已 uv sync 过（本地有 darwin wheel 缓存）
ls ../cursorPro/vista/.venv  # 应该存在

# 3. 安装依赖（会从本地 path 引 vista）
uv sync

# 4. 验证 import 链
uv run python -c "
from vista.utils.factor_detect import factor_detect
from vista_fc.services import factor_detect_service, factor_plan_service
from vista_fc.contracts import FactorDetectInput, TenantContext
print('vista + vista-fc import OK')
"

# 5. 本地环境变量
cp .env.example .env.local
# 编辑 .env.local：
#   OSS_S3_COMPAT=true                        # 本地 MinIO 模式
#   OSS_ENDPOINT=http://localhost:9000
#   OSS_ACCESS_KEY_ID=dev
#   OSS_ACCESS_KEY_SECRET=devdevdev
#   OSS_BUCKET=vista-fc-dev
#   OSS_REGION=us-east-1                      # MinIO 默认
#   CLICKHOUSE_URL=http://localhost:8123
#   CLICKHOUSE_USER=dev
#   CLICKHOUSE_PASS=dev
#   NAS_CACHE_ROOT=/tmp/vista-cache

# 6. 安装 pre-commit 钩子
uv run pre-commit install
```

### 3.2 日常开发循环

```bash
# 起本地外部依赖（MinIO + ClickHouse）
docker compose -f dev/compose.yaml up -d
# → MinIO 面板: http://localhost:9001  (dev / devdevdev)
# → ClickHouse HTTP: http://localhost:8123

# 改代码 → 跑单测（秒级）
uv run pytest tests/unit -v

# 跑集成测试（真 vista + 真 MinIO）
uv run pytest tests/integration -v

# 全量 + 覆盖率
uv run pytest --cov=src/vista_fc --cov=handlers --cov-report=term

# Lint / Type
uv run ruff check
uv run basedpyright

# 提交前 pre-commit 会自动跑（ruff-format + gitleaks + detect-secrets）
git add <files>
git commit -m "feat: ..."

# 收工
docker compose -f dev/compose.yaml down
```

### 3.3 运行测试

测试金字塔（共 **107 个测试**）：

| 层 | 位置 | 规模 | 特性 |
|---|---|---|---|
| 单测 | `tests/unit/` | ~104 | 纯 Python，mock vista，毫秒级 |
| 集成 | `tests/integration/` | 3 | 真 vista + 真 MinIO（需 docker compose） |
| 部署 preflight | `tests/deploy_preflight/` | 11 步 bash | 真阿里云隔离部署（需凭据） |
| 冒烟 | `tests/smoke/` | 4 | 真线上 FC 调用（需 `FC_SMOKE_READY=1`） |
| 性能基线 | `tests/perf/` | — | 预留目录 |

```bash
# 只跑单测（最快）
uv run pytest tests/unit

# 跑单测 + 集成（需 minio + vista 可用）
uv run pytest tests/unit tests/integration

# 只跑一个函数的所有测试
uv run pytest -k "factor_detect"

# 刷新 DTO 快照（改了 pydantic 模型后）
uv run pytest tests/unit/contracts/test_schema_snapshot.py --snapshot-update

# 生成覆盖率 HTML
uv run pytest --cov=src/vista_fc --cov-report=html
open htmlcov/index.html
```

### 3.4 本地 MinIO 集成（OSS_S3_COMPAT）

**为什么需要这个开关**：`oss2` 走阿里云 OSS 签名协议，MinIO 只认 AWS S3 sigv4 — 两者不兼容。开 `OSS_S3_COMPAT=true` 让 `OssClient.from_env()` 切到 boto3 后端，同样的公共 API，换一套网络协议。

```bash
# 本地（.env.local）
OSS_S3_COMPAT=true
OSS_ENDPOINT=http://localhost:9000

# 生产（FC 环境变量）— 不要设置 OSS_S3_COMPAT
# 留空 → 走 oss2 → 走阿里云真 OSS
```

代码里**无条件**用 `OssClient.from_env()`，同一份代码，环境自动切换。

测试里也通过 env var 切换：

```python
# tests/integration/test_minio_real.py
@pytest.fixture
def minio_env(monkeypatch):
    monkeypatch.setenv("OSS_S3_COMPAT", "true")
    monkeypatch.setenv("OSS_ENDPOINT", "http://localhost:9000")
    # ...
```

---

## 4. 镜像与部署

### 4.1 构建 Docker 镜像

**⚠️ 已知阻塞**：生产镜像需要 `vista` 可安装到 linux 容器内。当前 `pyproject.toml` 用本地 path 引 vista，在 docker build context 里路径不存在。解锁方案见 §8。

**本地构建**（单平台，快）：

```bash
scripts/build_image.sh --dev
# → 产出 registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:dev (约 482 MB)
```

**冒烟镜像本身（不需 vista）**：

```bash
# 起容器 + 指定一个无害的 callable 作为 handler
docker run -d --rm --name vc-smoke -p 9877:9000 \
  registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:dev \
  vista_fc.contracts.common:TenantContext

sleep 2
curl -s http://localhost:9877/health  # → {"status":"ok"}
docker rm -f vc-smoke
```

### 4.2 推送到 ACR

先 `docker login` 一次：

```bash
docker login registry.cn-hangzhou.aliyuncs.com
# user / password 来自阿里云 ACR 控制台 → 访问凭证
```

然后：

```bash
GIT_SHA=$(git rev-parse --short HEAD)
scripts/push_image.sh
# → 产出 multi-arch 镜像 :<git_sha> 和 :main
```

### 4.3 部署到阿里云 FC

1. 配置 `s` 访问凭证：

```bash
s config add --access-alias dev  # 按提示输入 AK/SK
s config add --access-alias prod
```

2. 设置环境变量（每个环境一份）：

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

3. 部署：

```bash
# 校验 s.yaml 语法 + 引用
s verify

# 静态校验 FDL
uv run python scripts/validate_flow.py

# 部署（按选择的 access 别名）
s deploy --access dev --assume-yes

# 只部署某一个资源
s deploy factor-detect --access dev
s deploy research-pipeline-flow --access dev
```

### 4.4 preflight 部署链路校验

在部署到正式 dev 之前，用**隔离命名空间**跑 11 步校验（ACR 推拉 / RAM / VPC / NAS / OSS / ClickHouse / flow 执行）：

```bash
export FC_ACCESS=dev-preflight        # 独立的低权限子账号
export FC_SUFFIX="-preflight-$(git rev-parse --short HEAD)"
export OSS_BUCKET=vista-fc-preflight

bash tests/deploy_preflight/run_all.sh
# → 11 步每一步的输出写到 tests/deploy_preflight/artifacts/<date>/
# → 任一步失败即 exit 1，最后一步是 99_cleanup.sh 自动拆资源
```

---

## 5. 调用函数

### 5.1 同步调用（`factor-detect` 类短任务）

```bash
# 本地 MinIO 已有 factors.duckdb 的前提下：
EVENT='{
  "tenant": {
    "user_hash": "u_abc",
    "workspace_id": "EXP_001",
    "workspace_kind": "research",
    "run_id": "run-20260422-001",
    "requested_at": "2026-04-22T10:00:00Z"
  },
  "payload": {
    "factors_db_uri": "oss://vista-fc-dev/user_data/u_abc/research/EXP_001/factors.duckdb",
    "max_workers": 4,
    "timeout": 60
  }
}'

# 线上调用
s cli fc3 invoke \
  --region cn-hangzhou \
  --function-name factor-detect \
  -e "$EVENT" \
  --access dev
```

### 5.2 启动完整流水线（FnF）

```bash
# plan → build → detect → duplicate → evaluate → filter
INPUT='{
  "tenant": {...},
  "user_input": "动量反转类因子挖掘",
  "plan_model": "claude-opus-4-7",
  "factor_numbers": 20,
  "batch_size": 5,
  "build_workers": 2,
  "detect_workers": 4,
  "dup_workers": 4,
  "eval_workers": 8,
  "route_codes": ["R001", "R002"],
  "problem_codes": ["P001"],
  "eval_models": ["MA001", "CSSorting_equal"],
  "fee_rate": 0.0,
  "evaluate_methods": [],
  "filter_methods": [],
  "positive_extractor": "ratio_across_problems",
  "top_n": 20,
  "author": "jun",
  "outsample_sdt": "20250101"
}'

s cli fnf StartExecution \
  --name research-pipeline \
  --execution-name "run-$(date +%s)" \
  --input "$INPUT" \
  --access dev

# 查进度
s cli fnf DescribeExecution \
  --name research-pipeline \
  --execution-name "run-..." \
  --access dev
```

### 5.3 vista-realtime 定时触发

`vista-realtime` 函数默认有 timer trigger，每分钟自动执行。启用/禁用通过 s.yaml 变量：

```bash
export REALTIME_TRIGGER_ENABLE=true
s deploy vista-realtime --access prod
```

---

## 6. 监控与日志

**日志**（SLS）：

```bash
# 跟踪某函数最近日志
s logs factor-detect --tail --access dev

# 按 run_id 过滤（每条 log 都带这些字段）
# 在 SLS 控制台执行：
# * | where function_name='factor-evaluate' and run_id='run-20260422-001' | order by __time__ desc
```

**指标**：
- 每个 handler 在 `EnvelopeOut.metrics` 里回报：`elapsed_s`、`total_factors`、`passed/failed` 等
- FC 原生 p99 耗时、错误率、并发、Instance 数
- CloudMonitor 告警规则见 `docs/RUNBOOK.md`

**FnF 执行历史**：
```bash
s cli fnf ListExecutions --name research-pipeline --access dev
```

---

## 7. 故障排除

### 单测全红

```bash
# 清 venv 重装
rm -rf .venv uv.lock
uv sync
uv run pytest
```

### `uv sync` 找不到 chan-factor-rs

vista 的传递依赖 `chan-factor-rs` 在 `zbczsc-dev` 私有源，无 token 默认拉不到。确认 `../cursorPro/vista/.venv` 已经装过（该 venv 触发 uv 把 wheel 缓存到 `~/.cache/uv/`）。

### MinIO 集成测试失败 "XMinioStorageFull"

主机磁盘空间不足（<1 GB）。清理后重试：

```bash
docker compose -f dev/compose.yaml down -v
# 释放宿主机磁盘
```

### `s local invoke` 失败 "image not found"

需要先 build + 推镜像（`scripts/build_image.sh --dev`），或先 pull：

```bash
docker pull registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:dev
```

### 函数返回 `{"status":"failed","error":{"code":"INPUT_VALIDATION"}}`

payload 不符合 pydantic DTO。检查 `EnvelopeIn[<Input>].model_json_schema()`：

```bash
uv run python -c "
from vista_fc.contracts import FactorDetectInput
import json
print(json.dumps(FactorDetectInput.model_json_schema(), indent=2, ensure_ascii=False))
"
```

### `OSS_ETAG_CONFLICT`

同一 workspace 被并发调用。调用层必须用 `executionName = <workspace_id>-<timestamp>` 强唯一。短期可手动 Stop 其中一个 execution。

### ClickHouse 连不上

FC 函数需要在和 CH 同一个 VPC / 可达的 vswitch / 安全组放通 8123 入站。`08_ch_probe.sh` 可以单独测。

### 回滚

不走 git revert，只换镜像 tag：

```bash
# 找上一个正常版本
git log --oneline | head -5

# 用老 sha 部署
GIT_SHA=<old_sha> s deploy --access prod --assume-yes
```

---

## 8. 已知阻塞项

### 8.1 Docker 镜像里装 vista（影响 `s local invoke` 的完整 FC 协议测试）

`pyproject.toml` 的 `vista = { path = "../../cursorPro/vista", editable = true }` 相对路径在 docker build context 里解析不到；且生产 linux 容器需要 linux 版 `chan-factor-rs` wheel，只存 `zbczsc-dev` 私有源。

**解锁路径**：

**方案 A（推荐）**：CI 注入 `UV_INDEX_ZBCZSC_DEV_{USERNAME,PASSWORD}`，改回私有索引

```toml
# pyproject.toml
[tool.uv.sources]
vista = { index = "zbczsc-dev" }
```

Docker 构建脚本已有 `--secret id=uv_index,src=.env.build` 能注入，只需把凭据放 `.env.build`（gitignored）。

**方案 B**：在 docker build 之前先 `uv build` vista + 私有依赖成 wheel，拷进 build context

```bash
# 需要私有源 token 才能 pip download 私有 wheel
uv build --wheel --out-dir dist/ ../cursorPro/vista
uv pip download chan-factor-rs chanfactor czsc wbt --python-platform linux -d dist/ \
  --index-url $PRIVATE_INDEX

# Dockerfile 改为：
# COPY dist/*.whl /tmp/wheels/
# RUN uv sync --frozen --no-dev --find-links /tmp/wheels
```

### 8.2 无线上凭据

`tests/deploy_preflight/` 和 `tests/smoke/` 需要真阿里云资源。当前没有这些凭据时两者都会跳过。开通后：

1. 创建前述所有资源（RAM 角色、VPC、NAS、OSS、ACR、SLS）
2. 填 GitHub Secrets（CI 用）或 `~/.s/access.yaml`（本地用）
3. 跑 preflight 做一次完整校验
4. 跑 smoke 验证部署活着

---

## 附录：仓库结构

```
vista_sever/
├── src/vista_fc/            业务包
│   ├── contracts/           8 组 pydantic DTO + common envelope
│   ├── storage/             oss_client (含 s3-compat) / workspace / nas_cache / uri
│   ├── runtime/             adapter (HTTP /invoke) / logging / errors / context
│   └── services/            8 个业务服务（调 vista）
├── handlers/                FC 入口 (8 thin handlers) + _base.run_handler
├── flows/                   3 个 FnF FDL
├── tests/
│   ├── unit/                快速单测（~104 个）
│   ├── integration/         真 vista + 真 MinIO
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
│   ├── RUNBOOK.md           运维 playbook
│   └── superpowers/         设计文档 + 实现计划
├── s.yaml                   serverless-devs 主清单（8 函数 + 3 flow）
├── Dockerfile               多阶段构建
├── pyproject.toml           依赖 + 工具配置
└── .env.example             环境变量模板
```

---

## 参考

- [设计文档](superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md) — 完整架构决策
- [RUNBOOK.md](RUNBOOK.md) — 运维剧本
- [Serverless Devs 文档](https://www.serverless-devs.com/)
- [阿里云函数计算 FC 3.0](https://www.aliyun.com/product/fc)
- [函数工作流 FnF](https://www.aliyun.com/product/fnf)
