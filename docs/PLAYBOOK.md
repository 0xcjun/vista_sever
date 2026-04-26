# Playbook — 生产高可用操作手册

本文档是 P2-12 的一部分，面向运维/SRE。日常告警处置见 [RUNBOOK.md](RUNBOOK.md)。

---

## 1. 灰度 / 别名发布（Gray Alias）

FC3 支持版本 + 别名（alias）。发布流程：

1. 推镜像并部署到 `LATEST` 版本（每次 `s deploy` 都会把最新 qualifier 指向 LATEST）。
2. 用 `s cli fc publish-version --function-name factor-detect --access prod` 创建一个不可变版本 `N`。
3. 创建/更新别名 `stable`（承担 90% 流量）和 `canary`（10%）：

   ```bash
   s cli fc update-alias \
     --function-name factor-detect \
     --alias-name stable \
     --version-id N \
     --additional-version-weight '{"N+1":0.1}' \
     --access prod
   ```

4. FnF 的 resourceArn 指向 alias（而非 LATEST）：

   ```
   acs:fc:cn-hangzhou:{accountId}:functions/factor-detect/aliases/stable
   ```

5. 灰度 24h 无新增告警 → 把 `canary` 吸收进 `stable`：

   ```bash
   s cli fc update-alias --alias-name stable --version-id N+1 --additional-version-weight '{}'
   ```

回滚：`update-alias --version-id <N-1>`，别名切回旧版即可，无需重 build。

---

## 2. Schema 迁移（Envelope / Contract）

契约版本号在 `src/vista_fc/contracts/common.py` 常量 `SCHEMA_VERSION` 和 `EnvelopeOut.schema_version` 字段。

| 变更类型 | 示例 | 版本策略 |
|---------|------|----------|
| 新增可选字段 | 给 `FactorDetectOutput` 加 `cost_seconds` | 不升主版本，老消费者直接忽略 |
| 新增必填字段 | 给 `EnvelopeIn` 加 `schema_version` 必填 | 升主版本 + 灰度别名滚动 |
| 重命名/删除字段 | `total_factors` → `total` | 升主版本 + 双读/双写 2 个版本周期 |
| 字段类型收窄 | `str` → `Literal["a","b"]` | 升主版本 |

迁移操作（以 1.0 → 2.0 为例）：

1. 先发 1.1 兼容中间版本：handler 同时接受 1.0 和 2.0 payload（用 `schema_version` 分支）。
2. 把 `EnvelopeOut.schema_version` 默认值改成 2.0。
3. 观察 FnF 流水线 24h，无 `INPUT_VALIDATION` 告警 → 删除 1.0 代码分支。
4. 升 `SCHEMA_VERSION` 常量到 `"2.0"`。

---

## 3. 幂等 / Checkpoint / DLQ

### 3.1 事件层幂等（handler 级）

- 默认**关**。通过 `VISTA_FC_IDEMPOTENCY=1` 开启（可放 s.yaml 的 environmentVariables）。
- 幂等键：`user_data/{user_hash}/idempotency/{function_name}/{run_id}.json`。
- FnF 重试会沿用同 `run_id`，命中幂等时直接返回缓存 envelope。
- 失败不落 tombstone，可继续重试。

开启前确认：
- 同 `run_id` 的重复调用**确实**期望返回同一结果（对于读写混合的函数，缓存可能漏掉上游更新——此时用 UUID 作 run_id，禁止跨 FnF 复用）。

### 3.2 Dead Letter

- 每个 step 的 `catch.goto` 指向 `deadletter_trap`，该 step 调用 `deadletter` 函数把错误 + 原始 payload 写到：
  ```
  user_data/{user_hash}/deadletter/{run_id}/{failed_function}.json
  ```
- 日常运维批量巡检：
  ```bash
  ossutil ls oss://vista-fc-prod/user_data/*/deadletter/ --recursive | tail -50
  ```
- 人工 triage 后可手动重放（修正 payload 重新 StartExecution）。

### 3.3 Checkpoint Resume

FnF 自带 `Checkpoint` 概念。重跑同名 `executionName` 时，成功过的 step 自动跳过。
配合 §3.1 的 handler 级幂等：同 run_id 重放整个 FnF 执行是安全的。

**不安全的做法**：跨 FnF 执行复用 run_id（例如 cron 定时器固定 payload），会一直命中 idempotency tombstone 返回老结果。定时器场景必须在 payload 里加时间戳做 run_id。

---

## 4. 可观测性（SLS + Metrics）

### 4.1 日志

- `LOG_FORMAT=json`（默认）。
- 每行一条 JSON，字段：`ts level message module function line run_id user_hash workspace_id function_name phase request_id event metric_*`。
- 自动脱敏：`sk-*` / `Bearer *` / JWT / `LTAI*` / `*secret*` / `*password*` / `*token*` 等。

### 4.2 结构化指标

每个 handler 成功/失败都会以 `event=metric` 的 JSON 行发出：

```
{"event":"metric","metric_name":"handler.duration_ms","metric_value":123.4,"metric_unit":"ms","metric_status":"succeeded", ...}
{"event":"metric","metric_name":"handler.status_total","metric_value":1,"metric_status":"succeeded", ...}
{"event":"metric","metric_name":"handler.error_total","metric_value":1,"metric_status":"failed","metric_error_code":"OSS_ETAG_CONFLICT", ...}
```

在 SLS 里配置索引：`event: long, metric_name: text, metric_value: double, metric_status: text, metric_error_code: text`
后，以下查询可以直接做面板：

```
* | where event = 'metric' and metric_name = 'handler.duration_ms'
  | select approx_percentile(metric_value, 0.5) p50,
           approx_percentile(metric_value, 0.95) p95,
           approx_percentile(metric_value, 0.99) p99,
           function_name
  | group by function_name
```

### 4.3 关键告警（SLI）

| SLI | 门限 | 动作 |
|-----|------|------|
| p95 duration_ms > 2× baseline | 持续 5 min | 看 SLS 错误日志 / 回滚镜像 |
| error_rate > 5% | 持续 5 min | 见 RUNBOOK §告警处置 |
| OSS_ETAG_CONFLICT spike | > 10/min | 检查并发执行，考虑加唯一 run_id |
| VISTA_LLM_RATE_LIMIT | any | 看上游 LLM 配额 |

---

## 5. Perf baseline

`tests/perf/` 下存了 `pytest-benchmark` 基线：

```bash
# 建立基线
uv run pytest tests/perf --benchmark-save=main

# 与基线对比
uv run pytest tests/perf --benchmark-compare=main --benchmark-compare-fail=mean:20%
```

当前本地 baseline（供参考，CI 环境会不同）：
- hot path 单次 invoke ≈ 100 µs
- 9 个 handler 模块冷导入 ≈ 10 ms

---

## 6. 回滚决策树

```
  异常告警
     │
     ├─ 代码问题？（VISTA_LOGIC_ERROR / INPUT_VALIDATION 且新版本）
     │    → 切别名回 N-1
     │
     ├─ 数据问题？（factors.duckdb 损坏 / schema 漂移）
     │    → 停 FnF 触发 → 人工修复 → 写 deadletter 重放脚本
     │
     ├─ 容量问题？（LLM rate limit / CH connect 堵）
     │    → 调低 maxConcurrency（foreach step） → 延迟 retry 间隔
     │
     └─ 基础设施？（OSS/CH/NAS）
          → 走阿里云工单，期间别名切到上个稳定版 freeze 流量
```
