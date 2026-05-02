# vista-fc 函数对接文档

vista-fc 把 vista 投研框架的研究步骤 + 实盘函数封装成阿里云 FC3.0 函数,共 **9 个**函数。所有函数共享同一份 envelope 信封协议,本文给出每个函数的请求/响应字段,最后附 key 加密方式。

---

## 目录

- [0. 通用约定](#0-通用约定)
  - [0.1 EnvelopeIn 信封](#01-envelopein-信封)
  - [0.2 EnvelopeOut 信封](#02-envelopeout-信封)
  - [0.3 错误码](#03-错误码)
- [1. factor-plan](#1-factor-plan-) — 想法 → 因子路线
- [2. factor-builder](#2-factor-builder-) — 路线 → 因子代码
- [3. factor-detect](#3-factor-detect) — 因子完整性体检
- [4. factor-duplicate](#4-factor-duplicate) — 同质因子去重
- [5. factor-evaluate](#5-factor-evaluate) — 策略建模评估
- [6. factor-filter](#6-factor-filter) — 正期望筛选
- [7. strategy-backtest](#7-strategy-backtest) — 综合回测
- [8. vista-realtime](#8-vista-realtime) — 实盘调度 tick
- [9. deadletter](#9-deadletter) — FnF 死信落盘
- [附录 A. 字段级加密](#附录-a-字段级加密-anthropic_api_key-等-secretstr-字段)
- [附录 B. 客户端示例](#附录-b-客户端示例)

> 标记 🔐 的字段是 `SecretStr` 类型,**支持加密传输**。具体见[附录 A](#附录-a-字段级加密-anthropic_api_key-等-secretstr-字段)。

---

## 0. 通用约定

### 0.1 EnvelopeIn 信封

每个函数的请求 body 都是 JSON,统一外壳:

```json
{
  "tenant": { ... TenantContext ... },
  "payload": { ... 函数私有参数,见各小节 ... }
}
```

**TenantContext 字段**(所有函数共用):

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `user_hash` | string | ✅ | — | 用户 / 租户标识,用于 OSS 路径前缀 `user_data/<user_hash>/...` |
| `workspace_id` | string | ✅ | — | 工作区 id,如 `EXP_123` |
| `workspace_kind` | `"research"` \| `"realtime"` | ✅ | — | 研究 vs 实盘 |
| `run_id` | string | ✅ | — | 本次调用 id;开启幂等时用作幂等键 |
| `requested_at` | datetime (ISO 8601) | ✅ | — | 客户端发起时刻 |

> 严格 `extra="forbid"`。多传字段会直接 422 `INPUT_VALIDATION`。

### 0.2 EnvelopeOut 信封

```json
{
  "tenant": { ... 原样回传 ... },
  "status": "succeeded" | "failed" | "partial",
  "artifacts": [ { kind, oss_uri, size_bytes, sha256 }, ... ],
  "metrics": { "<标量字段>": <数值/字符串> },
  "payload": { ... 成功时为函数私有 Output;失败为 null ... },
  "error": { "code", "message", "retriable", "trace_id" } | null,
  "schema_version": "1.0"
}
```

`ArtifactRef` 形态:

| 字段 | 类型 | 描述 |
|---|---|---|
| `kind` | `"duckdb"` \| `"toml"` \| `"parquet"` \| `"feather"` \| `"report_json"` \| `"model"` \| `"log"` | 制品类型 |
| `oss_uri` | string | 必须以 `oss://` 起头 |
| `size_bytes` | int ≥ 0 | 字节数 |
| `sha256` | string \| null | 可选指纹 |

### 0.3 错误码

`error.code` 枚举(用于 FnF 重试决策):

| 错误码 | retriable | 触发场景 |
|---|---|---|
| `INPUT_VALIDATION` | false | 入参 schema 不通过 / 解密失败 / 鉴权前校验失败 |
| `VISTA_LOGIC_ERROR` | false | vista 业务异常、未分类异常兜底 |
| `VISTA_COMPUTE_TIMEOUT` | true | `TimeoutError` |
| `VISTA_LLM_RATE_LIMIT` | true | `anthropic.RateLimitError` |
| `OSS_READ_FAIL` | true | OSS 读侧通用失败 |
| `OSS_WRITE_FAIL` | true | OSS 写侧通用失败 |
| `OSS_ETAG_CONFLICT` | true | 幂等 / 条件写碰撞 |
| `CLICKHOUSE_CONNECT` | true | ClickHouse / DNS 连接失败 |
| `WORKSPACE_NOT_FOUND` | false | 工作区不存在 |

---

## 1. factor-plan 🔐

把交易想法 / 市场现象自由文本展开为多条因子路线,落盘 `factor_routes.toml`。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `user_input` | string (≥1 字符) | ✅ | — | 交易想法 / 市场现象自由文本,例 `"动量反转因子挖掘"` |
| `interactive` | bool | | `false` | 是否进入交互模式(FC 上一般保持 false) |
| `skill_path` | string \| null | | `null` | 可选,自定义 plan skill 文件路径 |
| `anthropic_api_key` 🔐 | string \| null | | `null` | 显式 Anthropic API Key,优先级高于函数环境变量 |
| `anthropic_base_url` | string \| null | | `null` | 显式 Anthropic 网关 URL |
| `anthropic_model` | string \| null | | `null` | 显式模型名,如 `"claude-sonnet-4-6"` |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `routes` | `FactorRouteSummary[]` | 路线摘要列表;每项含 `code`/`name`/`compute_engine`/`description` |
| `routes_toml_artifact` | `ArtifactRef` (kind=`toml`) | 落盘 `factor_routes.toml` 在 OSS 的位置 |

---

## 2. factor-builder 🔐

吃 plan 产出的 TOML(或单条 route_code),用 LLM 挖出具体因子代码,落盘 `factors.duckdb`。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `routes_toml_uri` | string \| null | △ | `null` | factor-plan 输出的 TOML 在 OSS 的 URI |
| `route_code` | string \| null | △ | `null` | 单条路线代号(当前未实现,需走 routes_toml_uri) |
| `builder_type` | `"claude"` \| `"agno_agent"` \| `"agno_team"` | | `"claude"` | 挖掘引擎:claude(快但脆)/ agno_agent(单 Agent + 工具)/ agno_team(三 Agent 协作) |
| `factor_numbers` | int [1, 10000] | | `20` | 期望因子数 |
| `batch_size` | int [1, 100] | | `5` | LLM 单批生成数 |
| `max_workers` | int [1, 32] | | `1` | 并行 worker 数 |
| `multi_turn` | bool | | `false` | 是否多轮迭代优化 |
| `max_retries` | int [0, 20] | | `3` | 单因子失败重试次数 |
| `anthropic_api_key` 🔐 | string \| null | | `null` | 显式 Anthropic API Key |
| `anthropic_base_url` | string \| null | | `null` | 显式 Anthropic 网关 URL |
| `anthropic_model` | string \| null | | `null` | 显式模型名 |

> △ `routes_toml_uri` 与 `route_code` **二选一必填**;`extra="forbid"` 仍生效。

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `total_factors` | int ≥ 0 | 累计落库因子数 |
| `per_route` | `RouteBuildStat[]` | 每条路线的 `route_code` + `factor_count` |
| `route_codes` | string[] | `per_route` 投影,FnF JSONPath 直接取 |
| `factors_db_artifact` | `ArtifactRef` (kind=`duckdb`) | `factors.duckdb` 在 OSS 的位置 |

---

## 3. factor-detect

对 `factors.duckdb` 做完整性体检:未来数据 / 逐品种方差 / 增量一致性。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `factors_db_uri` | string | ✅ | — | factor-builder 产出的 `factors.duckdb` URI |
| `problems_map_uri` | string \| null | | `null` | 可选 problem 映射 |
| `research_data_uri` | string \| null | | `null` | 研究数据 OSS URI;生产由 NAS 预置时留空 |
| `max_workers` | int [1, 32] | | `4` | 并行 worker |
| `timeout` | int [1, 3600] | | `60` | 单因子超时秒 |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `total_factors` | int ≥ 0 | 受检因子数 |
| `passed` | int ≥ 0 | 通过数 |
| `failed` | int ≥ 0 | 失败数 |
| `report_artifact` | `ArtifactRef` (kind=`report_json`) | 体检报告 |

---

## 4. factor-duplicate

按 (route × problem) 网格,基于 `wbt.WeightBacktest` 日收益相关性去除冗余因子。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `factors_db_uri` | string | ✅ | — | `factors.duckdb` URI |
| `route_codes` | string[] (≥1) | ✅ | — | 待去重的路线列表 |
| `problem_codes` | string[] (≥1) | ✅ | — | 待去重的问题列表 |
| `model_config_uri` | string \| null | | `null` | 自定义 model config |
| `research_data_uri` | string \| null | | `null` | 研究数据 URI |
| `threshold` | float [0.0, 1.0] | | `0.8` | 相关性删除阈值 |
| `max_workers` | int [1, 32] | | `4` | 并行 worker |
| `timeout` | int [1, 3600] | | `60` | 单组超时秒 |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `total_input` | int ≥ 0 | 所有 problem 输入因子合计 |
| `total_rejected` | int ≥ 0 | 软删除因子数 |
| `total_survived` | int ≥ 0 | 保留因子数 |
| `elapsed_seconds` | float ≥ 0 | 耗时 |
| `report_artifact` | `ArtifactRef` (kind=`report_json`) | 去重报告 |

---

## 5. factor-evaluate

在训练段对存活因子跑策略建模,产出评估报告。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `factors_db_uri` | string | ✅ | — | `factors.duckdb` URI |
| `route_codes` | string[] (≥1) | ✅ | — | 待评估路线 |
| `problem_codes` | string[] (≥1) | ✅ | — | 待评估问题 |
| `models` | string[] \| null | △ | `null` | 模型名列表;与 `models_config_uri` 互斥 |
| `models_config_uri` | string \| null | △ | `null` | 模型 config OSS URI;与 `models` 互斥 |
| `research_data_uri` | string \| null | | `null` | 研究数据 URI |
| `max_workers` | int [1, 32] | | `4` | 并行 worker |
| `timeout` | int [1, 3600] | | `60` | 单组超时秒 |
| `fee_rate` | float [0.0, 0.1] | | `0.0` | 手续费率 |
| `retry_failed` | bool | | `false` | 是否重跑历史失败任务 |

> △ `models` 与 `models_config_uri` 不能同时提供;两者都为 null 时使用 vista 默认模型。

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `total_evaluated` | int ≥ 0 | 总评估数 |
| `n_success` | int ≥ 0 | 成功数 |
| `n_failed` | int ≥ 0 | 失败数 |
| `elapsed_seconds` | float ≥ 0 | 耗时 |
| `report_artifact` | `ArtifactRef` (kind=`report_json`) | 评估报告 |

---

## 6. factor-filter

正期望筛 + top-n 精筛,产出可上实盘的策略 TOML。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `factors_db_uri` | string | ✅ | — | `factors.duckdb` URI |
| `problem_codes` | string[] | | `[]` | 受限 problem 列表;空表示全部 |
| `route_codes` | string[] | | `[]` | 受限 route 列表;空表示全部 |
| `evaluate_methods` | string[] | | `[]` | 评估口径 |
| `filter_methods` | string[] | | `[]` | 过滤方法 |
| `positive_extractor` | string | | `"ratio_across_problems"` | 正期望提取器 |
| `positive_metric` | string | | `"绝对收益"` | 正期望指标 |
| `positive_threshold` | float [0.0, 1.0] | | `0.618` | 正期望阈值 |
| `n` | int [1, 1000] | | `20` | top-n 精筛 |
| `metric_keys` | string[] \| null | | `null` | 自定义指标键 |
| `creator` | string | | `"factor_evaluate"` | 策略 TOML 元信息 |
| `author` | string | | `""` | 策略 TOML 元信息 |
| `outsample_sdt` | string (`YYYYMMDD`) | | `"20250101"` | 样本外开始日 |
| `research_data_uri` | string \| null | | `null` | 研究数据 URI |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `toml_artifacts` | `ArtifactRef[]` (kind=`toml`) | 产出的策略 TOML 列表 |
| `toml_count` | int ≥ 0 | TOML 数量 |

---

## 7. strategy-backtest

吃单个 RealtimeConfig TOML,跑完整回测管线。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `strategy_toml_uri` | string | ✅ | — | 策略 TOML 在 OSS 的 URI |
| `mode` | `"research"` \| `"realtime"` | ✅ | — | 回测口径 |
| `data_mode` | `"train"` \| `"valid"` \| `"total"` | | `"total"` | 数据段 |
| `digits` | int [0, 10] | | `2` | 价格小数位 |
| `fee_rate` | float [0.0, 0.1] | | `0.0` | 手续费率 |
| `n_jobs` | int [1, 32] | | `1` | 并行作业数 |
| `yearly_days` | int [1, 366] | | `252` | 年化交易日 |
| `max_workers` | int [1, 32] | | `1` | 并行 worker |
| `research_data_uri` | string \| null | | `null` | 研究数据 URI |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `strategy` | string | 策略名 |
| `elapsed_s` | float ≥ 0 | 耗时秒 |
| `artifacts` | `dict[str, ArtifactRef]` | 多个产物的命名映射 |

---

## 8. vista-realtime

实盘调度 tick:拉最新 K 线 → 重算因子权重 → 落盘 → 推送。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `strategy_toml_uri` | string | ✅ | — | 实盘策略 TOML URI |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `summary` | `SummaryData` | 策略名 / 最新时间戳 / 标的 / 因子数(成功/失败) |
| `latest_dt` | string \| null | 最新数据时间戳 |
| `weights_artifact` | `ArtifactRef` \| null | 本 tick 落盘的权重文件 |
| `timing` | `TimingEntry[]` | 各阶段耗时 (`stage` + `elapsed_seconds`) |

---

## 9. deadletter

FnF 编排的死信收集器。某 step 重试耗尽 / 命中非重试错误后,FnF 把上游的 `original_payload` + 分类 `error` 投给本函数,落盘到 OSS 供运维排查。**不需要客户端直接调**。

### Input — `payload`

| 字段 | 类型 | 必填 | 默认 | 描述 |
|---|---|---|---|---|
| `failed_function` | string (≥1 字符) | ✅ | — | 失败的上游函数名,如 `"factor-detect"` |
| `original_payload` | object | | `{}` | 上游原始 payload (透传) |
| `error` | `ErrorInfo` | ✅ | — | 上游分类后的错误对象 |

### Output — `payload`

| 字段 | 类型 | 描述 |
|---|---|---|
| `deadletter_artifact` | `ArtifactRef` (kind=`report_json`) | 死信落盘位置 |

---

## 附录 A. 字段级加密 (`anthropic_api_key` 等 SecretStr 字段)

### A.1 为什么加密

HTTPS 只保护链路,FC 调用 payload 会落到 FnF 执行历史 / FC 控制台调用记录。把敏感字段做应用层加密,明文只在 handler 进程内存里短暂存在。

### A.2 受加密保护的字段

由 [handlers/_base.py](../handlers/_base.py) 反射 envelope 中所有 `SecretStr` 字段并自动解密。**新增 `SecretStr` 字段无需改解密逻辑**。

| 函数 | 字段 |
|---|---|
| factor-plan | `anthropic_api_key` |
| factor-builder | `anthropic_api_key` |

### A.3 算法 & 线协议

- **算法**:libsodium `crypto_box_seal` (X25519 + XSalsa20-Poly1305)。每次新 ephemeral key,同明文密文不同,防关联。
- **格式**:

  ```
  enc:v1:<kid>:<base64-standard>(<sealed_box_ciphertext>)
  ```

  - `kid` 与 FC 端环境变量 `VISTA_FC_SEAL_SK_<KID>` 对齐(大小写不敏感)。
  - `sealed_box` 输出 = `ephemeral_pubkey(32B) || nonce(24B) || ct_with_mac`,libsodium 自动处理。
  - 不带前缀的字符串原样透传(向后兼容明文)。

### A.4 部署 5 步

**1) 生成密钥对**(一次性,部署侧)

```bash
./scripts/gen_seal_keypair.py            # 人类可读
./scripts/gen_seal_keypair.py --json     # 机器可读
./scripts/gen_seal_keypair.py --kid v2   # 轮换时换 kid
```

输出:
- `SK_B64`:**私钥**,只在终端打印一次,立即写到密码管理器或 KMS。
- `PK_B64`:**公钥**,可下发给所有客户端,公开无妨。

**2) 配置 FC 函数环境变量**

每个调用敏感字段的函数(`factor-plan` / `factor-builder`)环境变量加:

```
VISTA_FC_SEAL_SK_V1 = <SK_B64>
```

> 更安全:用 FC "环境变量加密" 让阿里云 KMS 托管。

**3) 客户端加密**

Python:

```python
from docs.examples.encrypt_field import encrypt_field

ct = encrypt_field("sk-ant-real-key", PUBLIC_KEY_B64)
# ct == "enc:v1:v1:JRdzKY..."

envelope["payload"]["anthropic_api_key"] = ct
```

JS / 浏览器:

```js
import { encryptField } from "./encrypt_field.mjs";

envelope.payload.anthropic_api_key = await encryptField("sk-ant-real-key", PUBLIC_KEY_B64);
```

**4) 调 FC** —— 调用方式不变,直接 POST envelope。

**5) 轮换**(可选):新增 `VISTA_FC_SEAL_SK_V2` 与 V1 并存 → 客户端切到 `kid=v2` → 迁完后下线 V1。

### A.5 服务端 API 速查 ([src/vista_fc/runtime/crypto.py](../src/vista_fc/runtime/crypto.py))

| 名称 | 签名 | 用途 |
|---|---|---|
| `PREFIX` | `Final[str]` = `"enc:v1:"` | 密文前缀 |
| `decrypt_field(value)` | `(str) -> str` | 主入口。无前缀直通;有前缀解密。失败抛 `FcError("INPUT_VALIDATION", ...)`,`retriable=False` |
| `encrypt_field(plaintext, public_key_b64, *, kid="v1")` | `(str, str) -> str` | 加密辅助(测试 / 客户端) |
| `_load_sk(kid)` | `(str) -> PrivateKey` | LRU 缓存的私钥加载;测试需 `_load_sk.cache_clear()` |

### A.6 客户端 API 速查

**Python** ([docs/examples/encrypt_field.py](examples/encrypt_field.py))

| 名称 | 签名 |
|---|---|
| `encrypt_field(plaintext, public_key_b64, *, kid="v1")` | `(str, str) -> str` |
| `build_envelope(api_key_plain, public_key_b64)` | `(str, str) -> dict` (factor-builder envelope 演示) |

CLI:`SEAL_PK_B64=<公钥> ./encrypt_field.py "sk-ant-..." [--envelope]`

**JS** ([docs/examples/encrypt_field.mjs](examples/encrypt_field.mjs)) — 依赖 `npm i libsodium-wrappers`,Node ≥18 / 浏览器通用

| 名称 | 签名 |
|---|---|
| `encryptField(plaintext, publicKeyB64, kid="v1")` | `async (string, string, string) -> string` |
| `buildEnvelope(apiKeyPlain, publicKeyB64)` | `async (string, string) -> object` |

CLI:`SEAL_PK_B64=<公钥> node encrypt_field.mjs "sk-ant-..." [--envelope]`

### A.7 安全注意

1. **私钥只配在 FC 函数环境变量**。不要 commit / 不进 CI 日志。建议用 FC "环境变量加密" + KMS。
2. **公钥可公开**,但仍走 HTTPS 分发,防中间人替换公钥。
3. **不要拿密文当幂等键** —— 每次密文不同。幂等仍走 `(function_name, user_hash, run_id)`。
4. **解密失败 → `INPUT_VALIDATION` 不可重试**。客户端拿到此码应认为"密钥错位/过期",重发不会变好。
5. **轮换时多 kid 共存**,不要直接覆盖同一 kid 的私钥(在途请求会失败)。
6. **不做重放保护** —— 重放语义由幂等键负责。
7. 其他语言客户端:任何支持 libsodium 的语言(Go/Rust/Java/Swift/C++)都有 `sealed_box` API,产出 `enc:v1:<kid>:<b64>` 即可。

---

## 附录 B. 客户端示例

完整可运行示例代码:

- 密钥生成:[scripts/gen_seal_keypair.py](../scripts/gen_seal_keypair.py)
- Python 客户端:[docs/examples/encrypt_field.py](examples/encrypt_field.py)
- JS / Node 客户端:[docs/examples/encrypt_field.mjs](examples/encrypt_field.mjs)
- 调用所有函数的端到端示例:[scripts/invoke_all.py](../scripts/invoke_all.py)
