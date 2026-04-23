# Vista 因子计算引擎接口

四个 Python 类因子计算引擎的接口签名、数据形态与典型用法对照。所有引擎均位于 `vista.engines` 包，因子代码以 `factor_code` 字符串的形式传入，由引擎在隔离命名空间内 `exec` 后调用 `factor_name(df, **kwargs)`。

## 共同约定

- **数据形态**：标准 K 线 DataFrame，必备列 `dt, symbol, open, high, low, close, vol, amount`
- **因子函数签名**：`def {factor_name}(df: pd.DataFrame, **kwargs) -> pd.DataFrame`
- **输出列命名**：`F#{factor_name}#DEFAULT`（多输出时可使用 `F#{factor_name}#{suffix}`）
- **必须**：处理 NaN/Inf；不得引入未来信息（rank/rolling 不允许负参数；shift/diff/pct_change 不允许负参数）

## 1. TimeSeriesEngine (TSE)

**类**：`vista.engines.time_series.TimeSeriesEngine`
**适用**：单标的时间序列上的趋势/动量/波动率/成交量等技术因子。

```python
from vista.engines import TimeSeriesEngine
from vista.factor_db.models import FactorDescribe, ComputeEngine

factor = FactorDescribe(
    factor_name="TSF_260406_A3B7F9",
    factor_code='''
def TSF_260406_A3B7F9(df, **kwargs):
    df = df.sort_values("dt")
    df["F#TSF_260406_A3B7F9#DEFAULT"] = df["close"] / df["close"].rolling(20).mean() - 1
    return df
''',
    compute_engine=ComputeEngine.TSE,
)

engine = TimeSeriesEngine(data={"klines": klines_df}, factor=factor, n_jobs=-1, verbose=True)
results = engine.results
```

特性：自动按 symbol 分组并行；分批处理；失败回退单线程；性能/内存监控。

## 2. CrossSectionEngine (CSE)

**类**：`vista.engines.cross_section.CrossSectionEngine`
**适用**：同一时刻多标的横截面比较——排名、标准化、分组中性化、相对估值。

```python
factor_code = '''
def CSF_260406_A3B7F9(df, **kwargs):
    # 截面因子约定：MultiIndex (dt, symbol) 或扁平 dt 列 + groupby("dt")
    df = df.copy()
    df["F#CSF_260406_A3B7F9#DEFAULT"] = df.groupby("dt")["amount"].rank(pct=True) - 0.5
    return df
'''
```

特性：以日（或更细粒度）为切片，截面操作必须用 `groupby("dt")`，禁止 `groupby("symbol")`。

## 3. EventDrivenEngine (EDE)

**类**：`vista.engines.event_driven.EventDrivenEngine`
**适用**：事件信号生成——突破、跳空、放量、极端波动等。输出为 0/1 信号列。

```python
factor_code = '''
def EVT_260406_A3B7F9(df, **kwargs):
    """20 日新高突破事件因子。"""
    df = df.sort_values("dt")
    rolling_max = df["close"].rolling(20).max()
    df["F#EVT_260406_A3B7F9#DEFAULT"] = (df["close"] >= rolling_max).astype(int)
    return df
'''
```

事件算子模板：见 [operators-events.md](operators-events.md)。

## 4. FreedomEngine

**类**：`vista.engines.freedom.FreedomEngine`
**适用**：自由计算流程，允许在因子代码内自定义数据获取与多步处理逻辑。可结合 [tushare skill](../../tushare/SKILL.md) 拉取财务/分钟线/资金流等扩展数据。

```python
factor_code = '''
def FRD_260406_A3B7F9(df, **kwargs):
    """组合 K 线 + 外部资金流数据生成融合因子。"""
    import pandas as pd
    from tushare_helper import get_moneyflow  # 用户自备的数据获取函数

    money = get_moneyflow(df["symbol"].unique().tolist(), df["dt"].min(), df["dt"].max())
    merged = df.merge(money, on=["dt", "symbol"], how="left")
    merged["F#FRD_260406_A3B7F9#DEFAULT"] = (
        merged["close"].pct_change(5) * merged["net_inflow"].rolling(5).sum().pipe(lambda s: s / s.abs().mean())
    )
    return merged
'''
```

参考：[freedom-engine.md](freedom-engine.md)。

## 引擎选择决策树

```
是单标的时序计算？  → TimeSeriesEngine
是同一时刻横截面比较？  → CrossSectionEngine
输出是 0/1 事件信号？  → EventDrivenEngine
需要外部数据 / 多步流程 / 自定义形态？  → FreedomEngine
表达式而非 Python 函数？  → 改用 vista-ast-factor skill
```
