---
name: vista-cli
description: >
  Vista 量化因子管理系统统一命令行工具（`vista` CLI）操作指南。
  当需要通过 CLI 操作 Vista 系统时触发，包括：
  (1) 管理因子库 — 列出/查询/删除/标记因子，查看评估历史，数据库维护；
  (2) 规划与挖掘因子 — 使用 `factor plan` 生成路线，`factor build` 批量挖掘；
  (3) 因子质量管线 — `factor detect` 体检、`factor duplicate` 去冗余、`factor evaluate` 策略建模评估；
  (4) 综合回测 — 通过 TOML 配置文件对因子执行 integrated_backtest；
  (5) 管理研究数据 — 列出研究问题、获取 K 线数据、构建/更新数据缓存；
  (6) 查看或初始化 Vista 配置（环境变量、.env 模板）；
  (7) 任何以 "vista <command>" 形式执行的操作；
  (8) 作为 LLM Agent 自主操作 Vista 系统时（应始终使用 --as-json 模式）。
---

# Vista CLI

`vista` 是 Vista 量化因子管理系统的统一命令行入口，四大命令组：
`config` | `factor` | `data` | `problem`

> **历史命令变更**：旧版本曾包含 `vista ui run`（Streamlit），现已移除；如仍在文档/笔记中看到 `vista ui` 请忽略。

## 两条铁律

### 1. 始终使用 `--as-json`（LLM Agent 场景）

```bash
vista <command> [args] --as-json
```

统一输出格式：
- 成功：`{"ok": true, "data": ...}`
- 失败：`{"ok": false, "error": {"type": "ErrorType", "message": "..."}}`

### 2. 访问本地 DuckDB 使用 `--db-path`（优先级最高）

`--db-path` 会**绕过 `CLICKHOUSE_DSN` 等环境变量**，强制走本地 DuckDB。
当 `.env` 已配置 ClickHouse 但临时想读本地因子库时必须显式传入。

```bash
vista factor ls --db-path ./my_factors.duckdb --as-json
```

## 命名约定

- **因子名**：`F#<Name>#<Suffix>` 格式，如 `F#SMA60#DEFAULT`；**前缀 `BETA` 的因子被 `factor rm` 静默跳过**（受保护，不可删）
- **计算引擎 code**：`TSE / CSE / EDE / TSA / CSA / FRE / UNK`（见 [references/commands.md](references/commands.md) 速查表）
- **研究问题 code**：`FTS_*`（期货时序）、`ETS_*`（ETF 时序）、`SAS_*`（股票 Alpha 截面）

## 核心工作流速查

### 探索因子库

```bash
vista factor ls --as-json                                          # 列出全部因子
vista factor ls --tag momentum --db-path ./local.duckdb --as-json # 按标签过滤 + 指定库
vista factor info "F#MyFactor#DEFAULT" --as-json                   # 查看因子详情
vista factor eval ranked --metric "全段-IC" --as-json              # 按 IC 排序（指标名来自评估 results 字典）
vista factor db stats --as-json                                    # 数据库统计
```

### 规划与挖掘因子（需 LLM API）

```bash
# 1. 将交易想法规划为结构化路线（含经济学逻辑，输出 TOML）
vista factor plan "动量反转：成交量放大伴随价格回调时的反转信号" \
                  --output-dir ./routes --as-json

# 2. 从路线文件批量挖掘因子
vista factor build ./routes/plan.toml --factor-numbers 20 --batch-size 5 --as-json

# 3. 直接传 JSON 路线（必须包含 FactorRoute 全部必填字段，见 references/commands.md）
vista factor build --route-json '{...}' --as-json
```

### 因子质量管线（detect → duplicate → evaluate）

挖掘完批量因子后的标准三连，**串行执行**，每步都改写因子库（写 tag / 软删 / 写 evaluations）。

```bash
# 1. 体检：未来信息 / 逐品种方差 / 滚动一致性 三项检查（写 tag，失败的因子会被软删）
vista factor detect --db-path ./factors.duckdb --max-workers 8 --verbose
# → tag 集合：detect_passed / future_info_failed / variance_failed / rolling_failed
#   creator='factor_detect'，幂等：已打 detect_passed 的因子不再重检

# 2. 去冗余：基于 wbt.WeightBacktest 日收益相关性，贪心淘汰 |corr|>threshold 的因子
vista factor duplicate \
    --route ROUTE1 --route ROUTE2 \
    --problem FTS_A504A636 \
    --threshold 0.8 --max-workers 8 --verbose \
    --db-path ./factors.duckdb
# → tag='高相关冗余'，软删被淘汰因子；多 problem 串行，后一轮基于剩余因子继续筛选

# 3. 策略建模评估：每个因子 × 每个 ModelConfig 跑训练集分段回测
vista factor evaluate \
    --route ROUTE1 --route ROUTE2 \
    --problem FTS_A504A636 \
    --models MA001 \              # 不传 --models 时跑 6 个内置 ModelConfig
    --max-workers 8 --verbose \
    --db-path ./factors.duckdb
# → 写入 factor_evaluates 表；evaluate_results 是扁平化 dict
#   key 命名：'<段名>-<kind>-<指标>'，kind ∈ {多空, 多头}，约 60+ 个指标
#   断点续传：已成功的 (factor, problem, method) 三元组自动跳过；--retry-failed 重试 FAILED
```

**6 个内置 ModelConfig**（`vista.models.config.list_builtin_model_configs()`）：
`MA001`（时序）、`CSSorting_equal`、`CSSorting_rank_weighted`、`DirectExposure`、`MaxExpectedReturns`、`MaxFactorExposure`（后 5 个为截面）。
TSA / TSE 因子建议只跑 `MA001`；CSE / CSA 因子配 5 个截面策略。

### 综合回测

```bash
vista factor backtest init-config backtest.toml                   # 生成配置模板
vista factor backtest run backtest.toml --dry-run --as-json       # 预览配置
vista factor backtest run backtest.toml --factor F#SMA60#DEFAULT  # 执行回测
```

### 研究数据与问题

```bash
vista problem ls --as-json                                               # 列出研究问题（含详情）
vista data ls-problems --as-json                                         # 仅列出 code 列表
vista data get --problem FTS_6E98CD77 --mode train --limit 5 --as-json  # 获取数据样本
```

### 配置

```bash
vista config show --as-json   # 检查配置（敏感字段自动脱敏）
vista config init             # 生成 .env 模板
```

## LLM 决策树

| 场景 | 选择 | 理由 |
|------|------|------|
| 需要 code + 名称 + 标的 + 时间段 | `vista problem ls` | 含完整元信息 |
| 仅枚举 problem code（遍历用） | `vista data ls-problems` | 精简数组，减少 token |
| 因子生成想让 LLM 互相补充避免重复 | `--multi-turn` | 同一会话上下文 |
| 因子生成要求多样性且可并行 | `--max-workers > 1` + 默认单轮 | 独立进程 |
| 临时读一次本地 duckdb 文件 | `--db-path PATH` | 不写 env，一次性 |
| 长期切换到本地 duckdb | 改 `.env` 的 `DUCKDB_PATH` | 持久 |
| 想删旧因子 | `factor rm --force --as-json` | JSON 模式免 confirm |
| 需要物理清理已软删除因子 | `factor db cleanup --force` | 仅 ClickHouse 后端有效 |
| 因子库初步检查质量 | `factor detect` | 三项体检 + 写 tag，幂等可重复跑 |
| 一组路线下因子高度同质 | `factor duplicate` | 基于回测日收益相关性贪心淘汰 |
| 想批量评估因子在某 problem 的策略表现 | `factor evaluate` | 多 ModelConfig × 训练集分段；断点续传 |
| 不知道有哪些 metric 可排序 | `factor eval ls <NAME> --limit 1` | 看 `evaluate_results` 字典所有 key |

## 配置诊断与引导

**每次开始前先检查：**

```bash
vista config show --as-json
```

解析 `来源` 字段：
- `env/file` — 已正确设置
- `default` — 使用默认值（通常可接受）
- `unset` — **缺失，需设置**

**收到 `ConfigMissingError` 时的处理流程：**

1. 读取 `error.message` 中列出的变量名
2. 提示用户：
   ```bash
   vista config init                   # 生成 .env.example
   # 编辑 .env 填入缺失变量，或直接 export VAR=value
   vista config show --as-json         # 验证
   ```

### 各操作所需变量速查

| 操作 | 必需变量 | 说明 |
|------|---------|------|
| `vista factor *`（读写本地库） | 无（`DUCKDB_PATH` 有默认值 `~/.vista/factor.duckdb`） | 可用 `--db-path` 显式指定 |
| `vista factor *`（读写线上库） | `CLICKHOUSE_DSN` | `VISTA_DB_TYPE=clickhouse` 可选 |
| `vista factor build/plan` | `CLAUDE_MODEL` 或配套 API 凭证 | 通过 Claude Agent SDK 调用 |
| `vista factor backtest run` | `VISTA_RESEARCH_PATH` | 读 K 线数据做回测 |
| `vista factor detect/duplicate/evaluate` | `VISTA_RESEARCH_PATH` | 加载 problem 训练集做体检/回测 |
| `vista data get` | `VISTA_RESEARCH_PATH` | 同上 |
| `vista data prepare` | `CZSC_TOKEN` + `VISTA_RESEARCH_PATH` | 需拉取原始数据 |

## 详细参考

- **完整命令参考**（所有参数、字段清单、输出示例、枚举值）：[references/commands.md](references/commands.md)
- **LLM 工作流示例**（规划挖掘全流程、错误恢复、Agent 调用模板）：[references/workflows.md](references/workflows.md)
