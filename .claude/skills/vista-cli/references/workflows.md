# Vista CLI LLM 工作流示例

## 目录

1. [探索现有因子库](#1-探索现有因子库)
2. [因子规划与挖掘全流程](#2-因子规划与挖掘全流程)
3. [因子质量管线（detect → duplicate → evaluate）](#3-因子质量管线detect--duplicate--evaluate)
4. [因子质量分析与回测](#4-因子质量分析与回测)
5. [研究问题与数据探索](#5-研究问题与数据探索)
6. [因子库维护](#6-因子库维护)
7. [数据准备与更新](#7-数据准备与更新)
8. [错误恢复流程](#8-错误恢复流程)

---

## 1. 探索现有因子库

**场景：** 了解当前有哪些因子，找出质量最好的。

```bash
# Step 1: 数据库概况
vista factor db stats --as-json

# Step 2: 列出因子（默认 limit=20）
vista factor ls --as-json
vista factor ls --engine TimeSeriesEngine --limit 50 --as-json  # 按引擎过滤（完整名）

# Step 3: 查看单因子的评估历史，读出 evaluate_results 里有哪些 metric 键
vista factor eval ls "F#SomeFactor#DEFAULT" --limit 1 --as-json

# Step 4: 按发现的指标名排序
vista factor eval ranked --metric "全段-IC" --order abs_desc --limit 10 --as-json

# Step 5: 查看排名第一的因子详情
vista factor info "F#TopFactor#DEFAULT" --as-json
```

**指定本地 DuckDB（绕过 CLICKHOUSE_DSN）：**

```bash
vista factor ls --db-path ./my_factors.duckdb --as-json
```

---

## 2. 因子规划与挖掘全流程

**场景：** 从交易想法出发，自动规划路线并批量挖掘因子。

### 2a. 规划路线（`factor plan`）

输入要 **详细** 描述市场现象 + 初步逻辑，太短会导致规划质量差：

```bash
# 非交互式规划（单次直出）
vista factor plan "放量上涨后的短期动量：当日成交量相对10日EMA显著放大，且近5日价格上涨，\
反映资金集中流入，预期短期惯性延续" --output-dir ./routes --as-json

# 交互式规划（多轮确认，适合需要细化的场景）
vista factor plan "量价背离反转" --interactive --output-dir ./routes --as-json
```

输出 TOML 文件结构（`FactorPlanResult` → TOML）：
```toml
[plan]
user_input = "放量上涨后的短期动量..."
confirmed_details = ""
created_at = "2026-04-15T21:09:35"

[[routes]]
code = "a1b2c3d4e5f6"          # 自动哈希
name = "量价动量时序因子"
compute_engine = "TSE"
key_inspect = "..."
economic_logic = "..."
why_effective = "..."
market_mechanism = "行为偏差"
failure_scenarios = ["流动性极端骤降..."]
```

### 2b. 批量挖掘因子（`factor build`）

```bash
# 从 plan 输出的 TOML 挖掘（推荐）
vista factor build ./routes/plan.toml --factor-numbers 20 --batch-size 5 --as-json

# 写入指定 DuckDB
vista factor build ./routes/plan.toml --db-path ./my_factors.duckdb --as-json

# 多轮互补挖掘（同一会话上下文，避免因子重复）
vista factor build ./routes/plan.toml --factor-numbers 30 --multi-turn --as-json

# 并行多进程（独立会话，提升吞吐）
vista factor build ./routes/plan.toml --factor-numbers 50 --max-workers 4 --as-json
```

**直接传 JSON 路线**（必须含 FactorRoute 全部必填字段；不要手填 `code`）：

```bash
vista factor build --route-json '{
  "name": "量价背离反转",
  "compute_engine": "TSE",
  "key_inspect": "量价背离时的短期反转信号",
  "economic_logic": "量价背离反映机构出货或吸筹的不一致性",
  "why_effective": "基于行为金融学的过度反应理论",
  "market_mechanism": "行为偏差",
  "failure_scenarios": ["流动性极端骤降时成交量失真"]
}' --factor-numbers 10 --as-json
```

### 2c. 验证挖掘结果

```bash
# 按 route_code 或 creator 过滤新因子
vista factor ls --db-path ./my_factors.duckdb --as-json

# 查看因子详情（确认代码逻辑）
vista factor info "F#NewFactor#DEFAULT" --db-path ./my_factors.duckdb --as-json
```

---

## 3. 因子质量管线（detect → duplicate → evaluate）

**场景：** 用 `factor build` 批量挖掘了几百个因子后，做完整质量管线得到一组可上线候选。

### 3a. 体检：剔除有 bug 的因子

```bash
vista factor detect --db-path ./factors.duckdb --max-workers 8 --verbose
```

- 三项检查：未来信息 / 逐品种方差（>1/3 品种方差为 0 判 fail）/ 滚动增量一致性
- 失败的因子会被 `del_factor`（软删 `is_deleted=1`）+ 打 tag (`future_info_failed` / `variance_failed` / `rolling_failed`)
- 通过的打 `detect_passed`，幂等可重跑（已打 passed 的会跳过）
- 默认 problems_map：`TSE/TSA → FTS_A504A636`，`CSE/CSA → CS_COMMODITY_D`，`EDE/FRE/UNK → 跳过`

### 3b. 去冗余：剔除高度同质的因子

```bash
vista factor duplicate \
    --route ROUTE1 --route ROUTE2 \
    --problem FTS_A504A636 \
    --threshold 0.8 --max-workers 8 --verbose \
    --db-path ./factors.duckdb
```

- 仅处理 `factor.route in routes` 且 `is_deleted=0` 的因子（detect 失败的自动排除）
- 多 problem 串行；后一轮基于剩余因子继续（前一轮软删的因子不会再参与）
- 内部：`compute_factor → MA001（默认）→ wbt.WeightBacktest → daily_return → greedy_eliminate(threshold)`
- 被淘汰因子：`del_factor` 软删 + tag `高相关冗余`，detail 含 `{problem_code, matched_survivor, corr_value}`

> **撤销某轮的 duplicate 软删**（如发现阈值选错想重跑）：
> ```sql
> UPDATE factor_describe SET is_deleted=0
>   WHERE factor_name IN (SELECT factor_name FROM factor_tags WHERE tag='高相关冗余');
> DELETE FROM factor_tags WHERE tag='高相关冗余';
> ```
> 然后重跑 `factor duplicate`。

### 3c. 评估：策略建模分段回测

```bash
# TSA / TSE 因子建议只跑 MA001
vista factor evaluate \
    --route ROUTE1 --route ROUTE2 \
    --problem FTS_A504A636 \
    --models MA001 \
    --max-workers 8 --verbose \
    --db-path ./factors.duckdb

# CSE / CSA 因子配 5 个截面策略
vista factor evaluate --route ROUTE3 --problem CS_COMMODITY_D \
    --models CSSorting_equal,CSSorting_rank_weighted,DirectExposure,MaxExpectedReturns,MaxFactorExposure \
    --db-path ./factors.duckdb --verbose

# 不传 --models / --models-config 则跑 6 个内置默认
```

- 阶段 1（并行）：`compute_factor → 内存缓存`
- 阶段 2（并行）：`(factor × model_config) → model_weights → backtest_with_segments → FactorEvaluate`
- 写入 `factor_evaluates` 表；`(factor, problem, method)` 三元组幂等（已 SUCCESS 跳过；FAILED 默认也跳过，加 `--retry-failed` 重试）
- 每条 evaluation 含 60+ 个扁平化指标 key：`<段名>-<kind>-<指标>`（段 ∈ 训练集A/B/C/训练集，kind ∈ 多空/多头）

### 3d. 按指标排序、找出 top 因子

```bash
# 先看一条已评估因子的 evaluate_results 字典里有哪些 key
vista factor eval ls F#SOME_FACTOR --limit 1 --db-path ./factors.duckdb --as-json

# 按其中任意 key 排序（abs_desc 同时考虑做空因子）
vista factor eval ranked --metric "训练集-多空-夏普比率" --order abs_desc --limit 10 \
    --db-path ./factors.duckdb --as-json
```

### 3e. 一键生成实盘策略组合（可选）

```bash
vista factor filter ./realtime_configs/ \
    --positive-metric 绝对收益 --positive-threshold 0.618 \
    --n 20 \
    --db-path ./factors.duckdb --verbose
```

> 仅在已经执行过 `factor evaluate` 的因子库上有意义；生成的 TOML 可被 `vista.realtime` 模块消费。

---

## 4. 因子质量分析与回测

**场景：** 评估因子表现，执行综合回测。

### 3a. 评估历史与排序

```bash
# 查看因子评估历史
vista factor eval ls "F#MyFactor#DEFAULT" --limit 10 --as-json

# 按 metric 排序（metric 键需来自 evaluate_results 字典）
vista factor eval ranked --metric ICIR --order abs_desc --limit 10 --as-json
```

### 3b. 综合回测（`factor backtest`）

```bash
# Step 1: 生成配置模板
vista factor backtest init-config backtest.toml

# Step 2: 列出可用的 problem code
vista data ls-problems --as-json

# Step 3: 编辑 backtest.toml，选择 problems 和 models（参见 commands.md 的模型清单）

# Step 4: 预览配置
vista factor backtest run backtest.toml --factor F#MyFactor#DEFAULT --dry-run --as-json

# Step 5: 执行回测
vista factor backtest run backtest.toml --factor F#MyFactor#DEFAULT
```

**常用 models 组合：**

```toml
[[models]]
name = "CSSorting_equal"
model = "CSSorting"
[models.kwargs]
top_pct = 0.2
weighting_method = "equal"

[[models]]
name = "DirectExposure_zscore"
model = "DirectExposure"
[models.kwargs]
normalize_method = "zscore"
leverage = 1.0

[[models]]
name = "MaxExpectedReturns_l2"
model = "MaxExpectedReturns"
[models.kwargs]
risk_aversion = 1.5
weight_bounds = [-0.8, 0.8]
```

---

## 5. 研究问题与数据探索

**场景：** 了解可用研究问题，获取数据做分析。

```bash
# 方式 A：列出全部研究问题（含详情）
vista problem ls --as-json
# → 返回 code / name / description / freq / dataset / time_segments / symbols(或 domains)

# 方式 B：仅列出 code（精简枚举）
vista data ls-problems --as-json

# 查看单个问题详情
vista problem get FTS_IC_IH_IF_D --as-json

# 获取 K 线数据样本
vista data get --problem FTS_IC_IH_IF_D --mode train --limit 5 --as-json
# → 数据字段：dt / symbol / open / close / high / low / vol / amount

# 获取验证集 / 全量
vista data get --problem FTS_IC_IH_IF_D --mode valid --as-json
vista data get --problem FTS_IC_IH_IF_D --mode total --as-json
```

**Code 前缀含义：**
- `FTS_*`：期货时序（Future Time Series）
- `ETS_*`：ETF 时序
- `SAS_*`：股票 Alpha（截面，返回字段为 `domains` 而非 `symbols`）

---

## 6. 因子库维护

**场景：** 清理废弃因子，整理标签。

### 5a. 删除因子（注意 `BETA` 保护）

```bash
# 基本删除（JSON 模式自动跳过 confirm，不需要 --force）
vista factor rm "F#OldFactor#DEFAULT" --as-json

# 批量删除
vista factor rm "F#A#DEFAULT" "F#B#DEFAULT" "BETA001" --as-json
# → deleted: 2, 因 "BETA001" 受保护被静默跳过
# → names 仍返回全部 3 个请求名称

# 强制删除（非 JSON 模式下必需）
vista factor rm "F#C#DEFAULT" --force
```

### 5b. ClickHouse 物理清理

```bash
# 仅 ClickHouse 后端支持；DuckDB 本地库会抛 RuntimeError
vista factor db cleanup --dry-run --as-json    # 预览（仅文本提示，不列明细）
vista factor db cleanup --force --as-json      # 执行
```

### 5c. 标签管理

```bash
vista factor tag add "F#SMA60#DEFAULT" trend moving_average --as-json
vista factor tag remove "F#SMA60#DEFAULT" trend --as-json
vista factor tag ls --name "F#SMA60#DEFAULT" --as-json
vista factor tag ls --as-json                  # 列出全部标签
```

---

## 7. 数据准备与更新

**场景：** 定期更新研究数据缓存。

```bash
# 全量更新所有 4 个数据集
vista data prepare --as-json

# 仅更新指定数据集（cs / etf / future / stock 可多选）
vista data prepare --datasets future --as-json
vista data prepare --datasets cs etf --as-json

# 遇到错误继续处理其余数据集
vista data prepare --datasets cs etf future stock --continue-on-error --as-json
```

> `vista data` 只有 `ls-problems / get / prepare` 三个子命令，不存在 `prepare-cs` 这类独立子命令。

---

## 8. 错误恢复流程

### 配置缺失（`ConfigMissingError`）

```bash
vista data get --problem FTS_IC_IH_IF_D --as-json
# → {"ok": false, "error": {"type": "ConfigMissingError",
#     "message": "缺少必填配置项：VISTA_RESEARCH_PATH\n..."}}
```

**处理：** 读取 `error.message` → 引导用户 `vista config init` → 编辑 `.env` → 再验证 `vista config show --as-json`。

### 因子不存在（`KeyError`）

```bash
vista factor info "F#NonExistent#DEFAULT" --as-json
# → {"ok": false, "error": {"type": "KeyError", ...}}
```

**处理：** 先 `vista factor ls --as-json` 获取实际因子名。

### --route-json 缺字段（`ValidationError`）

```bash
vista factor build --route-json '{"name": "x", "compute_engine": "TSE"}' --as-json
# → {"ok": false, "error": {"type": "ValidationError",
#     "message": "...key_inspect, economic_logic, why_effective, market_mechanism, failure_scenarios..."}}
```

**处理：** 按 [`FactorRoute` 必填字段清单](commands.md#vista-factor-build) 补齐。

### 想用本地 DuckDB 但走了 ClickHouse

当 `.env` 配置了 `CLICKHOUSE_DSN` 但需要读本地 DuckDB：

```bash
# 错误：走 ClickHouse，读不到本地库
vista factor ls --as-json

# 正确：显式指定本地路径，绕过 CLICKHOUSE_DSN
vista factor ls --db-path ./local.duckdb --as-json
```

### DuckDB 路径无效（`IO Error`）

```bash
vista factor ls --db-path /nonexistent/foo.duckdb --as-json
# → {"ok": false, "error": {"type": "IOException",
#     "message": "Cannot open file ..."}}
```

**处理：** 检查父目录是否存在，必要时 `mkdir -p`。

### 本地库调用 ClickHouse 专属接口（`RuntimeError`）

```bash
vista factor db cleanup --force --as-json    # 本地 DuckDB 后端
# → {"ok": false, "error": {"type": "RuntimeError",
#     "message": "当前后端不支持 remove_deleted_factors..."}}
```

**处理：** 本地 DuckDB 同样使用软删除（`is_deleted=1`），但 `db cleanup` 只在 ClickHouse 后端实现。如需"清理"已软删因子，可：
- 直接 SQL 物理删：`DELETE FROM factor_describe WHERE is_deleted=1`
- 或通过 `add_factor` UPSERT 已存在因子时自动复活（`is_deleted=0`），按需保留即可

---

## 通用 Agent 调用模板

```python
import json
import subprocess
from typing import Any

def vista(args: list[str], db_path: str | None = None) -> Any:
    """执行 vista CLI 并返回解析后的 data 字段。

    Args:
        args: 去掉 "vista" 和 "--as-json" 的参数列表。
        db_path: 可选，显式指定本地 DuckDB（绕过 CLICKHOUSE_DSN）。
    """
    cmd = ["vista"] + args
    if db_path and args and args[0] == "factor" and args[1] != "plan":
        cmd += ["--db-path", db_path]
    cmd += ["--as-json"]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    payload = json.loads(result.stdout)
    if not payload["ok"]:
        err = payload["error"]
        raise RuntimeError(f"vista {' '.join(args)} 失败 [{err['type']}]: {err['message']}")
    return payload["data"]


# 使用示例
problems = vista(["data", "ls-problems"])                       # list[str]
stats = vista(["factor", "db", "stats"])                        # dict
factors = vista(["factor", "ls"])                               # list[dict]
top_ic = vista(["factor", "eval", "ranked",
                "--metric", "全段-IC", "--limit", "10"])         # list[dict]
local_factors = vista(["factor", "ls"], db_path="./local.duckdb")

# 挖掘因子
build_result = vista([
    "factor", "build", "./routes/plan.toml",
    "--factor-numbers", "20", "--batch-size", "5",
])
print(f"共挖掘 {build_result['total_factors']} 个因子")
```
