---
name: chan-factor-python-api
description: Use when writing Python code that imports chan_factor_rs, calling compute_factors/Engine/get_operators, performing factor computation or IC analysis, or helping users understand chan_factor_rs API usage and expression syntax
---

# chan-factor-rs Python API 参考

## 概述

Rust 因子计算引擎 + Python API，通过 Arrow FFI 零拷贝通信。Python 层管 IO/验证/中文化，Rust 内核只做计算。

## 何时使用

- 编写 `import chan_factor_rs` 的 Python 代码
- 计算因子表达式 (Mean, CSRank, TSRsi 等)
- 执行 IC/RankIC 分析（支持分段 + 中文列名）
- 查询算子语法或可用算子列表
- 排查 `ChanFactorError` 异常

**不适用**: 添加新 Rust 算子 (用 `developing-chan-factor-operators`)，修改 Rust 内部实现。

## 快速参考

```python
from chan_factor_rs import compute_factors, Engine, get_operators, ChanFactorError
```

### 无状态 API

```python
result = cf.compute_factors(
    data,                    # DataFrame | pa.Table | dict | 文件路径 (.feather/.csv)
    factors=["Mean($close, 20)", "CSRank($close)"],
    return_as="pandas",      # "pandas" | "polars" | "pyarrow"
    verbose=True,
)
# data 必须包含 dt + symbol 列。K线字段 (open/close/high/low/vol/amount) 自动检测并透传。
```

### Engine API（加载一次，多次计算）

```python
with Engine() as eng:
    eng.load(data, dt="dt", symbol="symbol")

    # compute — names 注册名称供后续 IC 分析引用
    eng.compute_factors(["Mean($close,20)", "Ref($close,-2)/$close-1"],
                        names=["alpha","label"], fill_na_value=None, output="pandas")

    # 逐日 IC 分析
    atomic = eng.analyze_ic_atomic("alpha", "label", groups=5, zh=False, output="pandas")
    # → dt, ic, rank_ic, cross_section_count, benchmark, qret_g0..gN, q_long_short

    # IC 汇总 + 分段 (每段一行, 31 个指标)
    summary = eng.analyze_ic_summary("alpha", "label", groups=5, output="pandas", zh=True,
        segments={"2017-2019": ["2017-01-01","2020-01-01"], "2020+": ["2020-01-01",None]})
    # → 分段, IC, Rank_IC, 年化收益, 最大回撤, 5层单调性, ...

    # 便捷接口: 表达式 → IC 汇总一步到位
    cis = eng.compute_ic_summary(factor="Mean($close,20)", label="Ref($close,-2)/$close-1",
        factor_name="f", label_name="l", groups=5, segments=segments, output="pandas")
```

### IC 高级参数

`dropna=False, ann_factor=252.0, winsor=0.0, cs_zscore=False, norm="none"|"standard"|"robust", norm_q=0.05, workers=0`

### 表达式语法

```
$close, $open, $high, $low, $vol, $amount    # 字段引用 (大小写不敏感)
$close + $open                                # 中缀运算
Mean($close, 20)                              # 函数调用
CSRank(Mean($close, 20))                      # 嵌套组合
If($close > $open, 1, 0)                      # 条件表达式
Ref($close, -1)                               # 滞后引用 (负数=向前)
```

算子名**大小写不敏感**。滚动算子前 N-1 个值为 NaN。

### 关键默认值差异

| 方法 | 默认 output | 默认 fill_na |
|------|------------|-------------|
| `compute_factors()` (独立函数) | `"pandas"` | 不填充 |
| `Engine.compute_factors()` | `"pyarrow"` | `0.0` |

## 算子索引 (共 187 个)

详细文档在 `operators/` 子目录，需要时读取对应文件。

| 分类 | 数量 | 文件 | 典型算子 |
|------|-----:|------|---------|
| 算术 | 15 | operators/arithmetic.md | Abs, Log, Sqrt, Power, Sign |
| 逻辑/比较 | 10 | operators/logic.md | If, And, Or, Gt, Lt, Eq |
| 位移 | 2 | operators/shift.md | Ref, Delta |
| 内置滚动 | 20 | operators/time-series-core.md | Mean, Std, Max, Min, EMA, Slope, Corr |
| 扩展时序 | 53 | operators/time-series-ext.md | TSZScore, TSRank, TSPctChange, TSDecayLinear |
| 截面 | 23 | operators/cross-section.md | CSRank, CSZScore, CSScale, CSClip, CSFillNa |
| 双变量 | 8 | operators/pair.md | Corr, Cov, TSBeta, TSRegResi |
| TA-Lib | 52 | operators/talib.md | TSRsi, TSMacd, TSAdx, TSAtr, TSCci, TsSar |
| 特殊 | 4 | operators/special.md | ChangeInstrument, Feature, Mask |

## 常见错误

| 错误 | 修正 |
|------|------|
| `analyze_ic_atomic("Mean($close,20)", ...)` 没有先 compute | 用 `compute_ic_summary()` 或先 `compute_factors(names=["alpha"])` 再按名称引用 |
| 期望独立函数 `compute_factors` 输出无 NaN | 独立函数不填充 NaN；用 `Engine.compute_factors(fill_na_value=0.0)` |
| 传入 DataFrame 列名不对 | 必须有 `dt` 和 `symbol` 列 |
| `segments` 结束日期理解为包含 | 实际是半开区间 `[start, end)` — 结束日期用下一天 |

## 错误处理

```python
try:
    cf.compute_factors(data, ["UnknownOp($close)"])
except ChanFactorError as e:  # Rust 内核错误
    print(e)
# Python 侧: ValueError (缺少列), TypeError (输入类型错误)
```
