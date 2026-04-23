---
name: vista-realtime
description: Use when implementing Vista实盘策略执行系统, using vista.realtime模块, configuring RealtimeWorkflow, deploying factor strategies to production, or needing reference for vista/realtime configs and APIs. Covers strategy update workflow, data updaters, factor execution, weight building, and publishers (Feishu/ClickHouse).
---

# Vista Realtime 实盘策略执行系统

## Overview

Vista Realtime 模块是实盘因子策略执行系统，提供端到端的策略更新工作流：增量数据更新 → 因子执行 → 权重构建 → 结果发布。支持多数据源（XY/Tushare）、并行执行、灵活配置和生产就绪的错误处理。

**核心文件**: `vista/realtime/` (configs, workflow, updaters, factors, weighting, publishers, templates)

## Quick Start

```python
from vista.realtime import RealtimeConfig, RealtimeWorkflow

# 1. 加载配置
config = RealtimeConfig.from_toml("runtime/strategy/config.toml")

# 2. 创建工作流（支持并行）
workflow = RealtimeWorkflow(config, max_workers=4)

# 3. 执行更新
result = workflow.update()

# 4. 查看结果
print(result["summary"])           # 更新摘要
print(result["df_weights"].tail()) # 最新权重
```

## Core Concepts

### Architecture Layers

```
配置层 (configs.py)      → RealtimeConfig, DataSourceConfig, StrategyModelConfig
数据层 (updaters.py)     → KlineUpdater: 增量更新K线, Feather缓存
因子层 (factors.py)      → run_factor: TSE/CSE/EDE引擎执行
权重层 (weighting.py)    → build_model_weights: 多种策略模型
发布层 (publishers.py)   → FeishuPublisher, ClickHousePublisher
编排层 (workflow.py)     → RealtimeWorkflow: 统一流程编排
```

### Data Flow

```
RealtimeConfig → KlineUpdater → FactorRunner → WeightBuilder → Publishers
                    ↓              ↓               ↓              ↓
                 增量K线         因子值          权重          飞书/CH/Redis
```

### Supported Components

| 组件 | 支持项 |
|------|--------|
| **数据源** | XY (future/stock/binance), Tushare |
| **因子引擎** | TSE (时序), CSE (截面), EDE (事件驱动) |
| **权重模型** | CSSorting, DirectExposure, EventDriven, 其他 vista.models |
| **发布器** | Feishu (多webhooks), ClickHouse (批量发布) |
| **后处理** | SIGN, WEIGHT, L3C/L5C/L10C/L20C (杠杆) |

## Configuration Reference

### RealtimeConfig Structure

```python
# 必填字段
strategy: str                              # 策略名称
data: DataSourceConfig                     # 数据源配置
model_config: StrategyModelConfig          # 权重模型配置
factors: list[FactorRuntimeConfig]         # 因子列表

# 可选字段
description: str | None = None             # 策略描述
author: str | None = None                  # 作者
outsample_sdt: str | None = None           # 样本外起始日期
post_process: str = "WEIGHT"               # 后处理方式
only_long: bool = False                    # 是否只做多
local_test: bool = False                   # 本地测试模式
runtime: RuntimeConfig = RuntimeConfig()   # 运行时配置
publish: PublishConfig = PublishConfig()   # 发布配置
```

### DataSourceConfig

```python
symbols: list[str] = []                    # 品种列表
freq: str = "15m"                          # K线频率
provider: str = "xy"                       # 数据提供商 ("xy", "ts")
cache_dir: str | None = None               # 缓存目录
query_days: int = 30                       # 查询窗口天数

# Provider-specific 参数（自动验证）
provider_params: dict[str, Any] = {}       # 数据源特定参数
  # xy provider 支持的参数:
  #   - ed_type: 复权类型 ("pre" 前复权, "post" 后复权)
  #   - include_rt: 是否包含实时数据 (bool)
  #   - ttl: 缓存时间（秒） (int > 0)
  #
  # ts provider 支持的参数:
  #   - asset_type: 资产类型 ("stock", "etf", "index", "future", "cb", "option", "hk_stock", "us_stock")
  #   - adj: 复权类型 ("qfq", "hfq", "")
  #   - rt: 是否使用实时数据 (bool)
```

**XY vs Tushare 参数对比**:

| 参数 | XY Provider | Tushare Provider |
|------|-------------|------------------|
| `provider` | `"xy"` | `"ts"` |
| `provider_params.ed_type` | `"pre"` (前复权), `"post"` (后复权) | 不支持 |
| `provider_params.include_rt` | `bool` | 不支持 |
| `provider_params.ttl` | 缓存秒数 (`int > 0`) | 不支持 |
| `provider_params.asset_type` | 不支持 | `"stock"`, `"etf"`, `"index"`, `"future"`, `"cb"`, `"option"`, `"hk_stock"`, `"us_stock"` |
| `provider_params.adj` | 不支持 | `"qfq"` (前复权), `"hfq"` (后复权), `""` (不复权) |
| `provider_params.rt` | 不支持 | `bool` (是否使用实时数据) |

### TOML Configuration Example

**XY 数据源配置**:
```toml
strategy = "FTS_15MIN_P021"
description = "黑色板块期货 15 分钟实盘策略"
author = "曾斌"
post_process = "L3C"
only_long = false

[data]
symbols = ["SQrb9001", "DLi9001"]
freq = "15m"
provider = "xy"
cache_dir = "./runtime/FTS_15MIN_P021/klines"
query_days = 30

[data.provider_params]
ed_type = "post"        # 复权类型: "pre" (前复权), "post" (后复权)
include_rt = true       # 包含实时数据
ttl = 3600              # 缓存 1 小时

[runtime]
symbol_kline_count = -1         # 全量历史
debug_mode = false
factor_failure_policy = "skip"  # 或 "raise"

[model_config]
name = "CSSorting_equal"
model = "CSSorting"
kwargs = { top_pct = 0.2, bottom_pct = 0.2, weighting_method = "equal" }

[publish.feishu]
enabled = true
success_keys = { default = "your-webhook-key" }

[[factors]]
factor_name = "RSM5"
compute_engine = "TSE"
description = "5日相对动量因子"
factor_code = """
def RSM5(df, **kwargs):
    df['F#RSM5#DEFAULT'] = df['close'] / df['close'].rolling(5).mean() - 1
    return df
"""
```

**Tushare 数据源配置**:
```toml
strategy = "STS_15MIN_P021"
description = "股票 15 分钟实盘策略"
author = "曾斌"
post_process = "WEIGHT"
only_long = false

[data]
symbols = ["000001.SZ", "600519.SH"]
freq = "15m"
provider = "ts"
cache_dir = "./runtime/STS_15MIN_P021/klines"
query_days = 365

[data.provider_params]
asset_type = "stock"    # 股票
adj = "qfq"             # 前复权
rt = false              # 不使用实时数据

[runtime]
symbol_kline_count = -1
debug_mode = false
factor_failure_policy = "skip"

[model_config]
name = "CSSorting_equal"
model = "CSSorting"
kwargs = { top_pct = 0.2, bottom_pct = 0.2, weighting_method = "equal" }

[publish.feishu]
enabled = true
success_keys = { default = "your-webhook-key" }

[[factors]]
factor_name = "SMA60"
compute_engine = "TSE"
description = "60日均线因子"
factor_code = """
def SMA60(df, **kwargs):
    df['F#SMA60#DEFAULT'] = df['close'] / df['close'].rolling(60).mean() - 1
    return df
"""
```

## Usage Patterns

### Pattern 1: Basic Strategy Update

```python
from vista.realtime import RealtimeConfig, RealtimeWorkflow

config = RealtimeConfig.from_toml("config.toml")
workflow = RealtimeWorkflow(config, max_workers=4)
result = workflow.update()

# 检查结果
assert result["summary"]["success_factor_count"] > 0
print(result["df_weights"].tail())
```

### Pattern 2: Multiple Factors (Equal Weight)

```python
# 配置多个因子，自动等权聚合
config = create_realtime_config(
    strategy="MULTI_FACTOR",
    symbols=["SQrb9001", "DLi9001"],
    freq="15m",
    model_config={"name": "CSSorting", "model": "CSSorting", "kwargs": {...}},
    factors=[factor1, factor2, factor3],  # 3个因子
)
# 权重 = (w1 + w2 + w3) / 3
```

### Pattern 3: Custom Publisher

```python
class MyPublisher:
    def publish(self, df_weights: pd.DataFrame, config: RealtimeConfig) -> None:
        # 自定义发布逻辑
        pass

workflow = RealtimeWorkflow(config)
workflow.publishers = [MyPublisher()]
result = workflow.update()
```

### Pattern 4: Tushare Data Source

```toml
[data]
symbols = ["000001.SZ", "600519.SH"]
freq = "15m"
provider = "ts"
query_days = 365

[data.provider_params]
asset_type = "stock"    # 股票
adj = "qfq"             # 前复权
rt = false              # 不使用实时数据
```

### Pattern 5: Parameter Validation

**DataSourceConfig 自动验证 `provider_params`**:

```python
from vista.realtime.configs import DataSourceConfig

# XY 数据源 - 有效配置
config = DataSourceConfig(
    provider="xy",
    symbols=["SQrb9001"],
    provider_params={
        "ed_type": "post",      # ✓ 有效值
        "include_rt": True,     # ✓ 布尔值
        "ttl": 3600,           # ✓ 正整数
    }
)

# Tushare 数据源 - 有效配置
config = DataSourceConfig(
    provider="ts",
    symbols=["600519.SH"],
    provider_params={
        "asset_type": "stock",  # ✓ 支持的资产类型
        "adj": "qfq",           # ✓ 有效的复权类型
        "rt": False,            # ✓ 布尔值
    }
)

# 错误示例 - 会抛出 ValidationError
config = DataSourceConfig(
    provider="ts",
    symbols=["600519.SH"],
    provider_params={
        "asset_type": "invalid",  # ❌ 错误: 不支持的资产类型
        "adj": "invalid",         # ❌ 错误: 无效的复权类型
    }
)
# 抛出异常:
# - asset_type 必须是以下值之一: cb, etf, future, hk_stock, index, option, stock, us_stock
# - adj 必须是 'qfq'、'hfq' 或 ''（空字符串）
```

## Output Files

```
runtime/<strategy>/
├── config.toml              # 用户配置（维护）
├── config.snapshot.json     # 归一化配置快照（审计）
├── latest_summary.json      # 最新更新摘要（监控）
├── weights.feather          # 历史权重（增量追加）
├── backtest_report.html     # 自动回测报告
└── klines/                  # K线缓存
    ├── SQrb9001.feather
    └── DLi9001.feather
```

**文件用途**:

| 文件 | 用途 | 格式 |
|------|------|------|
| `config.toml` | 主配置，用户维护 | TOML |
| `config.snapshot.json` | 运行时配置快照，便于审计 | JSON |
| `latest_summary.json` | 最新更新状态，便于监控 | JSON |
| `weights.feather` | 完整权重历史，增量追加 | Feather |
| `backtest_report.html` | 策略回测分析报告 | HTML |
| `klines/*.feather` | 按品种分文件，增量更新 | Feather |

## Extending

### Add New Weight Model

```python
# 1. 在 vista/models/ 中实现
class MyModel(BaseStrategyModel):
    def run(self):
        # 实现逻辑
        pass

# 2. 在配置中使用
[model_config]
name = "MyModel"
model = "MyModel"  # 自动从 vista.models 动态加载
kwargs = { ... }
```

### Add New Data Source

```python
# 1. 实现 MarketDataUpdater 协议
class MyUpdater:
    def update_symbol(self, symbol: str, freq: str, file_klines: Path, **kwargs) -> pd.DataFrame:
        # 实现逻辑
        pass

# 2. 替换工作流的 updater
workflow = RealtimeWorkflow(config)
workflow.updater = MyUpdater()
```

### Add New Publisher

```python
# 1. 实现 Publisher 协议
class MyPublisher:
    def publish(self, df_weights: pd.DataFrame, config: RealtimeConfig) -> None:
        # 实现逻辑
        pass

# 2. 注入到工作流
workflow.publishers = [MyPublisher()]
```

## Common Mistakes

| 错误 | 正确做法 |
|------|----------|
| 直接构造 RealtimeConfig | 使用 `create_realtime_config()` 或 `from_toml()` |
| 忽略 `factor_failure_policy` | 设置为 `"skip"` 或 `"raise"` |
| 发布失败认为主流程失败 | 发布失败不中断主流程，本地文件已保存 |
| 增量更新担心数据重复 | KlineUpdater 自动按 dt 和 symbol 去重 |
| 权重不一致告警惊慌 | 仅记录消息，不阻止流程执行 |
| 只做多不设置 `only_long` | 配置 `only_long = true` |
| **使用旧的 `asset_type` 字段** | **使用 `provider_params.asset_type` (ts)** |
| **使用旧的 `ed_type`/`include_rt` 字段** | **使用 `provider_params.ed_type`/`include_rt` (xy)** |
| **provider_params 参数名错误** | **参考文档确认参数名，DataSourceConfig 会自动验证** |
| **Tushare 使用 `adj=invalid`** | **使用 `"qfq"`, `"hfq"` 或 `""`** |
| **XY provider 使用 `asset_type`** | **XY 不需要 asset_type，使用 provider_params** |

## Best Practices

### Configuration Management

- **版本控制**: config.toml 纳入 git
- **环境隔离**: 开发/生产使用不同配置目录
- **参数调优**: 使用 config.snapshot.json 追踪变更

### Error Handling

- **因子失败**: 设置 `factor_failure_policy = "skip"` 跳过失败因子
- **发布失败**: 自动记录错误，不中断主流程
- **一致性检查**: 权重差异超过容忍度时记录告警

### Performance Optimization

- **并行执行**: 设置 `max_workers > 1` 启用多进程
- **缓存策略**: K线自动缓存，增量更新
- **批量处理**: ClickHouse 发布使用批量插入

## Related Skills

- **vista-tutorial**: Vista 系统整体教程（本 skill 专注于 realtime 实盘执行）
- **vista-ts-factor-generator**: 时序因子生成（本 skill 侧重因子在实盘中的执行）
- **vista-cs-factor-generator**: 截面因子生成（本 skill 侧重因子在实盘中的执行）

## References

- [Vista Realtime 模块文档](vista/realtime/CLAUDE.md) - 完整的模块文档
- [DataSourceConfig 参数验证说明](docs/datasource_config_validation.md) - provider_params 参数验证详细说明
- [create_realtime_config 更新说明](docs/create_realtime_config_update.md) - 函数参数更新说明
- [因子计算引擎](vista/engines/CLAUDE.md) - TimeSeriesEngine/CrossSectionEngine/EventDrivenEngine
- [策略建模](vista/models/CLAUDE.md) - CSSorting/DirectExposure/EventDriven 等
- [多数据源集成实现](docs/plans/multi-provider-implementation-summary.md)
