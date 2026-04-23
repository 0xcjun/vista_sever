# Vista CLI 完整命令参考

## 全局选项

```bash
vista [--config FILE] [--as-json] [--quiet/-q] [--verbose/-v] <command>
```

| 选项 | 说明 |
|------|------|
| `--config FILE` | 指定自定义 .env 文件路径 |
| `--as-json` | 全局 JSON 模式（也可在子命令级别指定，二者等效） |
| `--quiet/-q` | 静默模式，仅输出错误 |
| `--verbose/-v` | 详细模式 |

## 关键枚举速查

### ComputeEngine（计算引擎）

所有 7 个 code 及完整名称：

| code | 引擎名 | 说明 |
|------|--------|------|
| `TSE` | `TimeSeriesEngine` | 时序因子（最常用） |
| `CSE` | `CrossSectionEngine` | 截面因子 |
| `EDE` | `EventDrivenEngine` | 事件驱动因子 |
| `TSA` | `TimeSeriesAstEngine` | 时序 AST 表达式因子 |
| `CSA` | `CrossSectionAstEngine` | 截面 AST 表达式因子 |
| `FRE` | `FreedomEngine` | 自由格式因子（内部自取数据，默认 120s 超时） |
| `UNK` | `Unknown` | 未知（默认值，不应主动使用） |

**注意：** `factor ls --engine` **接受完整名称**（如 `TimeSeriesEngine`），不是 code。
`FactorRoute.compute_engine` 接受 code（如 `TSE`）。

### MarketMechanism（市场机制）

`FactorRoute.market_mechanism` 必填，5 个合法值：

| 中文值 | 含义 |
|--------|------|
| `错误定价` | Mispricing |
| `风险补偿` | Risk Premium |
| `行为偏差` | Behavioral Bias |
| `流动性溢价` | Liquidity Premium |
| `制度性套利` | Institutional Arbitrage |

---

## `vista config`

### `vista config show`

展示当前所有配置项的值和来源（敏感字段脱敏）。

```bash
vista config show [--as-json]
```

**JSON 输出示例：**
```json
{
  "ok": true,
  "data": [
    {"变量名": "CZSC_TOKEN", "值": "***", "来源": "env/file", "说明": "czsc DataClient token"},
    {"变量名": "DUCKDB_PATH", "值": "~/.vista/factor.duckdb", "来源": "default", "说明": "factor_db duckdb 文件路径"},
    {"变量名": "CLICKHOUSE_DSN", "值": "", "来源": "unset", "说明": "ClickHouse 连接串"}
  ]
}
```

`来源` 字段值：`env/file`（已设置）、`default`（使用默认值）、`unset`（未设置且无默认值）。

**实际返回的变量清单：**
`CZSC_TOKEN / CZSC_DATA_API / VISTA_RESEARCH_PATH / VISTA_DB_TYPE / DUCKDB_PATH / CLICKHOUSE_DSN / CLICKHOUSE_HOST / CLICKHOUSE_PORT / CLICKHOUSE_DATABASE / CLICKHOUSE_USERNAME / CLICKHOUSE_PASSWORD / VISTA_DB_VERBOSE / VISTA_USER_MODELS_DIR`

### `vista config init`

在指定目录生成 `.env.example` 模板文件。

```bash
vista config init [--output-dir DIR]
```

---

## `vista factor`

**所有 `factor` 子命令**（除 `plan` 外）**均支持 `--db-path/-d` 选项：**

| 选项 | 说明 |
|------|------|
| `--db-path/-d PATH` | 指定本地 DuckDB 文件路径，**优先级最高**，覆盖 `DUCKDB_PATH` 环境变量，并绕过 `CLICKHOUSE_DSN` 配置 |

### `vista factor ls`

列出因子库中的因子。

```bash
vista factor ls [--tag TAG] [--engine ENGINE] [--creator CREATOR] [--limit N] [--db-path PATH] [--as-json]
```

- `--engine` 传完整引擎名（如 `TimeSeriesEngine`），不是 `TSE`
- `--limit` 默认 20

**JSON 输出字段：** `factor_name / factor_code / compute_engine / description / is_deleted / creator / create_time / route`

> 注意：`creator` / `description` 可能为 `null`；`compute_engine` 返回的是完整名称（`TimeSeriesEngine`），不是 code。

### `vista factor info`

查看单个因子的详细信息（含完整 `factor_code`）。

```bash
vista factor info <NAME> [--db-path PATH] [--as-json]
```

**JSON 输出字段（实际全部 8 个字段）：**
```json
{
  "ok": true,
  "data": {
    "factor_name": "F#SMA60#DEFAULT",
    "factor_code": "def SMA60(df, **kwargs):\n    ...",
    "compute_engine": "TimeSeriesEngine",
    "description": "60日均线偏离度",
    "is_deleted": false,
    "creator": null,
    "create_time": "2026-04-15T21:09:35.791432",
    "route": "42d655f89480"
  }
}
```

### `vista factor plan`

将交易想法规划为结构化因子路线（调用 LLM Agent，输出含经济学逻辑的 `FactorRoute`）。

```bash
vista factor plan <USER_INPUT> [--interactive] [--output-dir DIR] [--model MODEL] [--skill-path PATH] [--as-json]
```

| 选项 | 说明 |
|------|------|
| `USER_INPUT` | 交易想法描述（必填）— **建议至少 10 字**，提供市场现象和初步逻辑，过短会导致规划质量差 |
| `--interactive/-i` | 启用多轮确认模式（CLI 对话式） |
| `--output-dir/-o DIR` | 保存结果为 TOML 文件到指定目录 |
| `--model MODEL` | 指定模型名称（默认读 `CLAUDE_MODEL` 环境变量） |
| `--skill-path PATH` | 自定义 factor planning skill 路径（默认 `.claude/skills/vista-factor-planning`） |

**注意：** `factor plan` 不支持 `--db-path`，规划不涉及数据库。

**JSON 输出（实际返回 `FactorPlanResult` 结构）：**
```json
{
  "ok": true,
  "data": {
    "user_input": "动量反转：...",
    "confirmed_details": "",
    "routes": [
      {
        "code": "42d655f89480",
        "name": "量价动量时序因子",
        "compute_engine": "TSE",
        "key_inspect": "成交量与价格动量的共振信号",
        "economic_logic": "资金集中流入时价量共振反映机构行为...",
        "why_effective": "行为金融学中的羊群效应...",
        "market_mechanism": "行为偏差",
        "failure_scenarios": ["流动性极端骤降时..."],
        "description": "...",
        "tags": [],
        "creator": null,
        "create_time": "2026-04-15T21:09:35"
      }
    ],
    "created_at": "2026-04-15T21:09:35"
  }
}
```

### `vista factor build`

根据一条或多条 FactorRoute 批量挖掘因子（调用 LLM Agent）。

```bash
vista factor build [ROUTE_FILE] [--route-json JSON] [--factor-numbers N] [--batch-size N]
                   [--max-workers N] [--multi-turn] [--model MODEL] [--max-retries N]
                   [--db-path PATH] [--as-json]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `ROUTE_FILE` | 单条路线或规划结果文件（TOML/JSON） | — |
| `--route-json` | 内联 FactorRoute 或 routes 容器的 JSON 字符串 | — |
| `--factor-numbers` | 期望挖掘的因子总数 | 20 |
| `--batch-size` | 单次请求 LLM 生成的因子数 | 5 |
| `--max-workers` | 并行进程数 | 1 |
| `--multi-turn` | 复用同一会话上下文进行互补挖掘 | false |
| `--max-retries` | 单次 LLM 调用失败时的重试次数 | 3 |

**限制：** `ROUTE_FILE` 与 `--route-json` 只能二选一。

**`--route-json` 必填字段（`FactorRoute` 模型要求）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 路线名称 |
| `compute_engine` | str | 引擎 code（`TSE/CSE/EDE/TSA/CSA/FRE`） |
| `key_inspect` | str | 一句话核心思路（≤ 100 字） |
| `economic_logic` | str | 经济学解释（必填） |
| `why_effective` | str | 行为/风险解释（必填） |
| `market_mechanism` | str | 主导市场机制（见上方枚举） |
| `failure_scenarios` | list[str] | 失效场景列表（**至少 1 个**） |

> 不要手填 `code`，它由所有业务字段自动 SHA-256 哈希生成（前 12 位）。
> `description / tags` 为可选。

**完整 `--route-json` 示例：**
```json
{
  "name": "量价背离反转",
  "compute_engine": "TSE",
  "key_inspect": "成交量与价格走势背离时的短期反转信号",
  "economic_logic": "量价背离反映机构出货或吸筹的不一致性",
  "why_effective": "基于行为金融学中的过度反应理论",
  "market_mechanism": "行为偏差",
  "failure_scenarios": ["流动性极端骤降时成交量失真"]
}
```

**JSON 输出示例：**
```json
{
  "ok": true,
  "data": {
    "total_routes": 1,
    "total_factors": 10,
    "factor_numbers": 20,
    "batch_size": 5,
    "items": [
      {
        "route_name": "量价背离反转",
        "route_code": "a1b2c3d4e5f6",
        "compute_engine": "TSE",
        "factor_count": 10,
        "factors": [
          {"factor_name": "F#VPD_MOM_01#DEFAULT", "factor_code": "...", "compute_engine": "TimeSeriesEngine", ...}
        ]
      }
    ]
  }
}
```

### `vista factor rm`

软删除因子（统一标记 ``is_deleted=1``，保留 tag 与 evaluation 历史）；可用 `vista factor db cleanup` 在 ClickHouse 后端做物理清理。

```bash
vista factor rm <NAME>... [--force] [--db-path PATH] [--as-json]
```

- 不带 `--force`：提示 confirm；**`--as-json` 模式下不需要 `--force`**（JSON 模式自动跳过 confirm）
- **`BETA*` 前缀因子受保护，会被静默跳过**（`count` 不含跳过的因子，但 `names` 保留全部请求列表）

**JSON 输出：** `{"ok": true, "data": {"deleted": 3, "names": ["F#A#DEFAULT", "BETA001", ...]}}`

### `vista factor add`

从 JSON/TOML 文件批量导入因子定义（调用 `add_factor(s)`）。文件支持单条或包含 `factors` 列表；UPSERT 命中已软删除因子时自动恢复 `is_deleted=0`。

```bash
vista factor add [FACTOR_FILE] [--factor-json JSON] [--batch-size N=500] [--db-path PATH] [--as-json]
```

| 参数 | 说明 |
|------|------|
| `FACTOR_FILE` | 因子定义文件（JSON/TOML），单条或 `{factors: [...]}` |
| `--factor-json` | 内联 JSON 字符串；与文件二选一 |
| `--batch-size` | 批量写入大小，默认 500 |

### `vista factor detect`

对 DuckDB 因子库批量体检：**未来数据 / 逐品种方差 / 滚动增量一致性** 三项检查。

```bash
vista factor detect [--problems-map FILE] [--max-workers N=4] [--timeout SEC=60]
                    [--verbose] [--db-path PATH] [--as-json]
```

**默认 problems_map**（`vista.utils.factor_detect.get_default_problems_map()`）：

| 引擎 | 默认 problem |
|------|-------------|
| `TSE` / `TSA`（时序 + 时序 AST） | `FTS_A504A636`（股指-30分钟-量价择时） |
| `CSE` / `CSA`（截面 + 截面 AST） | `CS_COMMODITY_D`（商品期货主力-D-截面多空） |
| `EDE` / `FRE` / `UNK` | `None` → 跳过并打 `unsupported_engine_skip` |

可用 `--problems-map` 传 JSON/TOML 覆盖。

**写入约定**（`creator='factor_detect'`）：

| tag | 触发条件 | 副作用 |
|-----|---------|--------|
| `detect_passed` | 三项检查全部通过 | — |
| `future_info_failed` | 未来信息泄露 | 同时 `del_factor` 软删 |
| `variance_failed` | >1/3 品种方差为 0 | 同时 `del_factor` 软删 |
| `rolling_failed` | 任一窗口（默认 1000/2000/3000）增量与全量不一致 | 同时 `del_factor` 软删 |
| `errored` | worker 抛异常 | — |
| `unsupported_engine_skip` | 引擎在 problems_map 里映射为 None | — |

**幂等**：已打 `detect_passed` 的因子自动跳过，可重复运行。

**必需环境变量：** `VISTA_RESEARCH_PATH`（加载 problem 训练集 K 线）

### `vista factor duplicate`

按 routes + problems 批量去冗余因子（基于 `wbt.WeightBacktest` 日收益相关性）。

```bash
vista factor duplicate --route CODE... --problem CODE...
                       [--model-config FILE] [--threshold 0.8]
                       [--max-workers N=4] [--timeout SEC=60]
                       [--verbose] [--db-path PATH] [--as-json]
```

| 参数 | 说明 |
|------|------|
| `--route` | `FactorRoute.code`，可重复；只处理 `factor.route in routes` 且 `is_deleted=0` 的因子 |
| `--problem` | 研究问题 code，可重复；**多 problem 串行**，后一轮自动排除前一轮软删的因子 |
| `--model-config` | ModelConfig 的 JSON/TOML 文件；不传时使用 `MA001` 默认 |
| `--threshold` | 相关性阈值，默认 `0.8`（`|Pearson| > threshold` 判为高相关） |

**流程**：每个 problem 内部 — 并行 `compute_factor → model_weights → wbt.WeightBacktest → daily_return`，聚合后用 `greedy_eliminate` 贪心淘汰。

**写入**（`creator='factor_duplicate'`，单 problem 内）：

| tag | 触发条件 | 副作用 |
|-----|---------|--------|
| `高相关冗余` | 与某 survivor 相关性超阈 | 同时 `del_factor` 软删，`detail` 含 `{problem_code, matched_survivor, corr_value}` |

### `vista factor evaluate`

批量策略建模评估因子表现（**仅训练集分段**）。两阶段并行：阶段 1 计算因子值（缓存），阶段 2 跑 `(factor × model_config)` 训练集分段回测。

```bash
vista factor evaluate --route CODE... --problem CODE...
                      [--models NAME[,NAME...]] [--models-config FILE]
                      [--max-workers N=4] [--timeout SEC=60] [--fee-rate 0.0]
                      [--retry-failed] [--verbose] [--db-path PATH] [--as-json]
```

| 参数 | 说明 |
|------|------|
| `--route` / `--problem` | 同 duplicate；多 problem 串行 |
| `--models` | 逗号分隔的内置 ModelConfig name；与 `--models-config` 互斥 |
| `--models-config` | ModelConfig 列表的 JSON/TOML；与 `--models` 互斥 |
| `--retry-failed` | 先清理已有 FAILED 评估记录再执行（FAILED 默认视为已处理而跳过） |

**6 个内置 ModelConfig** —— 都不传时默认全跑：

| name | model | 用途（kwargs 摘要） |
|------|-------|---------------------|
| `MA001` | `MA001` | 时序均线集成（`only_long=False, factor_direction=positive`） |
| `CSSorting_equal` | `CSSorting` | 截面排序 + 等权（`top_pct=0.2, bottom_pct=0.2`） |
| `CSSorting_rank_weighted` | `CSSorting` | 截面排序 + rank 加权 |
| `DirectExposure` | `DirectExposure` | 直接暴露 |
| `MaxExpectedReturns` | `MaxExpectedReturns` | 凸优化最大化期望收益（CLARABEL） |
| `MaxFactorExposure` | `MaxFactorExposure` | 最大化因子暴露 |

> TSA / TSE 因子建议只跑 `MA001`；CSE / CSA 因子配 5 个截面策略。

**断点续传**：`(factor_name, problem_code, evaluate_method)` 三元组若已有 `SUCCESS`/`FAILED` 记录则自动跳过（`creator='factor_evaluate'`）。`--retry-failed` 会先清掉 FAILED。

**evaluate_results schema**：扁平化 dict，键格式 `<段名>-<kind>-<指标>`：
- 段名：`训练集A段` / `训练集B段` / `训练集C段` / `训练集`（取自 `problem.time_segments` 中 `name.startswith("训练集")` 的段）
- kind：`多空` / `多头`
- 指标：`绝对收益` / `年化收益` / `夏普比率` / `卡玛比率` / `最大回撤` / `年化波动率` / `下行波动率` / `日胜率` / `周胜率` / `月胜率` / `季胜率` / `年胜率` / `交易次数` / `年化交易次数` / `单笔收益` / `单笔盈亏比` / `持仓K线数` / `新高占比` / `新高间隔` / `交易胜率`

→ 单因子可达 60+ 个 metric key（3 段 × 2 kind × 20+ 指标）。`vista factor eval ranked --metric <key>` 可按其中任意键排序。

**必需环境变量：** `VISTA_RESEARCH_PATH`

### `vista factor filter`

按"正收益预期 + 精筛 top-n"批量从 `factor_evaluates` 生成 realtime 策略 TOML。常用于评估完成后的实盘策略组装。

```bash
vista factor filter [OUTPUT_DIR] [--metric KEY...] [--positive-metric SUFFIX="绝对收益"]
                    [--positive-threshold 0.618] [--n 20]
                    [--top-strategy ratio_across_problems|...]
                    [--creator factor_evaluate] [--author NAME]
                    [--outsample-sdt 20250101] [--verbose] [--db-path PATH] [--as-json]
```

> 仅在已经执行过 `factor evaluate` 的因子库上有意义；`--metric` 不传时使用内置 160 个 DEFAULT_METRIC_KEYS。

### `vista factor summary`

因子库状态总览：路线数 / 因子数 / 软删数 / 评估数 / top 路线。

```bash
vista factor summary [--top-routes 3] [--db-path PATH] [--as-json]
```

### `vista factor eval ls`

查看因子的评估历史记录（含 `evaluate_results` 字典）。

```bash
vista factor eval ls <NAME> [--limit N] [--db-path PATH] [--as-json]
```

**JSON 输出字段：** `factor_name / evaluate_method / input_data / evaluate_results / elapsed / memory_usage / warnings / errors / status / creator / create_time`

`evaluate_results` 为字典或字符串，内部键即 `eval ranked --metric` 的候选值。

### `vista factor eval ranked`

按指定指标对成功评估记录排序（Python 层排序，只读 `status=success`）。

```bash
vista factor eval ranked --metric <METRIC> [--order abs_desc|abs_asc|desc|asc] [--limit N] [--db-path PATH] [--as-json]
```

- `--metric` 是 `evaluate_results` 字典中的任意键名，**没有固定清单**，命名由评估方法决定
- 常见值示例（取决于评估方法）：`IC / ICIR / 全段-IC / 训练集-IC / 验证集-IC / sharpe / long_ret / short_ret`
- `--order` 默认 `abs_desc`；可选 `abs_desc / abs_asc / desc / asc`

**查找可用 metric：** 先 `vista factor eval ls <NAME>` 取回一条记录，在 `evaluate_results` 里看有哪些键。

### `vista factor tag add`

为因子添加标签。

```bash
vista factor tag add <NAME> <TAG>... [--db-path PATH] [--as-json]
```

### `vista factor tag remove`

移除因子的某个标签。

```bash
vista factor tag remove <NAME> <TAG> [--db-path PATH] [--as-json]
```

### `vista factor tag ls`

列出标签。不指定 `--name` 时返回所有标签；指定时返回该因子的标签列表。

```bash
vista factor tag ls [--name NAME] [--creator CREATOR] [--db-path PATH] [--as-json]
```

### `vista factor db stats`

显示因子数据库统计信息。

```bash
vista factor db stats [--db-path PATH] [--as-json]
```

**JSON 输出（中文键）：**
```json
{"ok": true, "data": {"总因子数": 42, "评估记录数": 128, "独立标签数": 15}}
```

### `vista factor db cleanup`

物理删除已软删除的因子。

```bash
vista factor db cleanup [--dry-run] [--force] [--db-path PATH] [--as-json]
```

> **仅 `OnlineFactorManager`（ClickHouse 后端）支持**。若当前是本地 DuckDB 会抛 `RuntimeError`。
> `--dry-run` 仅提示"预览模式"，不列出实际待删条目。

---

## `vista factor route`

管理 `factor_route` 表（保存 `factor plan` 输出的 FactorRoute 元信息）。

### `vista factor route ls`

```bash
vista factor route ls [--engine ENGINE] [--mechanism MECHANISM] [--creator NAME]
                      [--limit N=50] [--db-path PATH] [--as-json]
```

`--engine` 接受引擎 code（`TSE/CSE/EDE/TSA/CSA/FRE`）；`--mechanism` 接受 5 个 `MarketMechanism` 中文枚举值。

### `vista factor route info`

```bash
vista factor route info <CODE> [--db-path PATH] [--as-json]
```

### `vista factor route add`

```bash
vista factor route add [ROUTE_FILE] [--route-json JSON] [--db-path PATH] [--as-json]
```

UPSERT 写入；文件支持单条或 `{routes: [...]}`。`code` 由业务字段哈希生成，无需手填。

### `vista factor route rm`

物理删除（不可逆）。受影响因子的 `factor.route` 字段不会被自动清理。

```bash
vista factor route rm <CODE>... [--force] [--db-path PATH] [--as-json]
```

---

## `vista factor backtest`

通过 CLI 暴露 `vista.models.backtest.integrated_backtest`（多 problem × 多模型批量回测）。

### `vista factor backtest init-config`

生成带注释的 TOML 配置模板。

```bash
vista factor backtest init-config [OUTPUT] [--force] [--as-json]
```

- `OUTPUT` 默认 `./backtest.toml`
- 文件已存在且未加 `--force` 时抛 `ValueError`

### `vista factor backtest run`

执行综合回测。

```bash
vista factor backtest run <CONFIG> [--factor F] [--output-dir DIR] [--fee-rate FLOAT]
                          [--mode train|valid|total] [--dry-run] [--as-json]
```

| 选项 | 类型 | 说明 |
|------|------|------|
| `CONFIG` | PATH（必填） | TOML 配置文件路径 |
| `--factor/-f` | str | 覆盖 TOML 中的因子名 |
| `--output-dir/-o` | str | 覆盖输出目录 |
| `--fee-rate` | float | 覆盖手续费率（如 `0.0003`） |
| `--mode/-m` | str | 覆盖数据模式（`train` / `valid` / `total`） |
| `--dry-run` | flag | 仅预览解析后的配置 |

**必需环境变量：** `VISTA_RESEARCH_PATH`

**TOML 模板结构：**
```toml
# 因子（两种方式二选一）
factor = "F#YourFactor#DEFAULT"          # 方式 A：因子库中已有
# [factor_describe]                      # 方式 B：内联代码
# factor_name = "F#SMA60#DEFAULT"
# compute_engine = "TSE"
# factor_code = "def SMA60(df, **kwargs): ..."

output_dir = "./backtest_results"
fee_rate = 0.0003
mode = "total"                           # train | valid | total

problems = ["FTS_IC_IH_IF_D"]

[[models]]
name = "CSSorting_equal"                 # 输出目录名（必填，任意标识符）
model = "CSSorting"                      # vista.models 中的类名
[models.kwargs]
top_pct = 0.2
weighting_method = "equal"
```

**`model` 字段可选类名**（来自 `vista.models`）：

| 类名 | 来源模块 | 典型用途 |
|------|---------|---------|
| `CSSorting` | `sorting.py` | 截面分组（按因子值 top_pct 排序后等权/波动率加权）|
| `DirectExposure` | `direct_exposure.py` | 直接暴露（因子标准化后作为权重）|
| `MaxExpectedReturns` | `max_expected_returns.py` | 最大化期望收益（带权重约束的凸优化）|
| `MaxFactorExposure` | `max_factor_exposure.py` | 最大化因子暴露 |
| `EventDriven` | `event.py` | 事件驱动策略 |
| `MA001` / `MA002` | `moving_average.py` | 移动均线策略样例 |

自定义模型：设置 `VISTA_USER_MODELS_DIR` 指向用户策略目录，内部类可直接按名引用。

**dry-run JSON 输出：**
```json
{
  "ok": true,
  "dry_run": true,
  "config": {
    "factor": "F#SMA60#DEFAULT",
    "problems": ["FTS_IC_IH_IF_D"],
    "models": [{"name": "CSSorting_equal", "model": "CSSorting", "kwargs": {"top_pct": 0.2}}],
    "output_dir": "./backtest_results",
    "fee_rate": 0.0003,
    "mode": "total"
  }
}
```

**输出目录结构：** `output_dir/<problem_code>/<model_name>/weights.feather + report.html`

---

## `vista problem`

### `vista problem ls`

列出所有已注册的研究问题（含完整详情）。

```bash
vista problem ls [--as-json]
```

**JSON 输出字段顺序：** `code / name / description / freq / dataset / time_segments / symbols`（或 `domains`）

```json
{
  "ok": true,
  "data": [
    {
      "code": "FTS_IC_IH_IF_D",
      "name": "股指期货日线",
      "description": "IC/IH/IF 日线时序策略",
      "freq": "D",
      "dataset": "future",
      "time_segments": [
        {"name": "train", "sdt": "20180101", "edt": "20231231"},
        {"name": "valid", "sdt": "20240101", "edt": "20251231"}
      ],
      "symbols": ["IC9999.CCFX", "IH9999.CCFX", "IF9999.CCFX"]
    }
  ]
}
```

截面问题返回 `domains`（分域列表）代替 `symbols`。

### `vista problem get`

查看单个研究问题的完整信息。

```bash
vista problem get <CODE> [--as-json]
```

---

## `vista data`

### `vista data ls-problems`

仅列出所有研究问题的 code（精简版，适合快速枚举）。

```bash
vista data ls-problems [--as-json]
```

**JSON 输出：** `{"ok": true, "data": ["FTS_A504A636", "CS_COMMODITY_D", ...]}`

### `vista data get`

获取研究问题对应的 K 线数据。

```bash
vista data get --problem <CODE> [--mode train|valid|total] [--limit N] [--as-json]
```

**必需环境变量：** `VISTA_RESEARCH_PATH`

**数据字段：** `dt / symbol / open / close / high / low / vol / amount`

### `vista data prepare`

构建研究数据缓存（全量或指定数据集）。

```bash
vista data prepare [--datasets cs etf future stock] [--continue-on-error] [--as-json]
```

- `--datasets` 可多选，空格分隔；不传时构建全部 4 个数据集
- **必需环境变量：** `CZSC_TOKEN` + `VISTA_RESEARCH_PATH`

> `vista data` 仅有 `ls-problems / get / prepare` 三个子命令，**没有** `prepare-cs/etf/future/stock`。

---

## 已移除命令

- **`vista ui run`**：旧版本提供 Streamlit UI（默认 `localhost:8588`），现已移除。如需可视化交互，使用项目内 Jupyter notebook 或独立 Streamlit 应用。

---

## 错误处理

所有命令在 `--as-json` 模式下，错误统一输出到 stdout：

```json
{
  "ok": false,
  "error": {
    "type": "ConfigMissingError",
    "message": "缺少必填配置项：CZSC_TOKEN\n请在当前目录创建 .env 文件并设置对应变量。\n运行 `vista config init` 可生成 .env 模板。"
  }
}
```

| type | 常见原因 | 解决方案 |
|------|---------|---------|
| `ConfigMissingError` | 缺少必填环境变量 | `vista config init` + 编辑 `.env` |
| `ValueError` | 参数值非法（如 `order` 超出 4 值域）、TOML 缺 `problems`/`models`、文件已存在未加 `--force` | 按 message 修正 |
| `KeyError` | 因子/问题 code 不存在 | 先用 `ls` 命令确认 |
| `FileNotFoundError` | 路线文件或配置文件不存在 | 检查路径；用 `init-config` / `plan --output-dir` 生成 |
| `RuntimeError` | 本地 DuckDB 后端调用 `db cleanup` 等仅 ClickHouse 支持的接口 | 切换后端，或放弃该操作 |
| `ValidationError` | `--route-json` 缺必填字段（如 `market_mechanism`） | 按 FactorRoute 必填清单补全 |
| `IO Error: Cannot open file` | `--db-path` 指向的 DuckDB 父目录不存在 | 检查路径或先 `mkdir` |
