# 事件化算子模板（EventDrivenEngine 用）

EventDrivenEngine 的因子代码输出 0/1（或 -1/0/1）信号列，用于标记市场上发生的"事件"。本文提供常用事件算子的 Python 实现模板，可直接复制到 `factor_code` 中使用。

> 这些算子是 SKILL 内可复用代码片段，**不**作为 Python 模块导出，避免污染 vista 包。

## 1. 突破类

### N 日新高突破

```python
def breakout_up(close: pd.Series, n: int = 20) -> pd.Series:
    rolling_max = close.shift(1).rolling(n).max()
    return (close > rolling_max).astype(int)
```

### N 日新低跌破

```python
def breakdown(close: pd.Series, n: int = 20) -> pd.Series:
    rolling_min = close.shift(1).rolling(n).min()
    return (close < rolling_min).astype(int)
```

## 2. 跳空类

### 跳空高开

```python
def gap_up(open_: pd.Series, prev_close: pd.Series, threshold: float = 0.02) -> pd.Series:
    gap = (open_ - prev_close) / prev_close
    return (gap > threshold).astype(int)
```

### 跳空低开

```python
def gap_down(open_: pd.Series, prev_close: pd.Series, threshold: float = 0.02) -> pd.Series:
    gap = (open_ - prev_close) / prev_close
    return (gap < -threshold).astype(int)
```

## 3. 成交量异动

### 放量（高于 N 日均量 K 倍）

```python
def volume_spike(vol: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    avg = vol.shift(1).rolling(n).mean()
    return (vol > k * avg).astype(int)
```

### 缩量

```python
def volume_dry(vol: pd.Series, n: int = 20, k: float = 0.5) -> pd.Series:
    avg = vol.shift(1).rolling(n).mean()
    return (vol < k * avg).astype(int)
```

## 4. 极端波动

### 极端涨幅事件

```python
def extreme_gain(close: pd.Series, threshold: float = 0.05) -> pd.Series:
    ret = close.pct_change()
    return (ret > threshold).astype(int)
```

### 极端跌幅事件

```python
def extreme_loss(close: pd.Series, threshold: float = -0.05) -> pd.Series:
    ret = close.pct_change()
    return (ret < threshold).astype(int)
```

## 5. 形态类

### 长上影线

```python
def upper_shadow(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, ratio: float = 2.0) -> pd.Series:
    body = (close - open_).abs()
    upper = high - close.where(close > open_, open_)
    return ((upper > ratio * body) & (body > 0)).astype(int)
```

### 长下影线

```python
def lower_shadow(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, ratio: float = 2.0) -> pd.Series:
    body = (close - open_).abs()
    lower = open_.where(close > open_, close) - low
    return ((lower > ratio * body) & (body > 0)).astype(int)
```

## 6. 趋势反转类

### 均线金叉

```python
def ma_golden_cross(close: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()
    cross = (ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))
    return cross.astype(int)
```

### 均线死叉

```python
def ma_death_cross(close: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()
    cross = (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))
    return cross.astype(int)
```

## 使用示例：组合事件

事件因子的 `factor_code` 通常将多个事件叠加为综合信号：

```python
def EVT_260406_A3B7F9(df, **kwargs):
    """20 日新高 + 放量 复合事件。"""
    df = df.sort_values("dt").copy()

    # 突破
    rolling_max = df["close"].shift(1).rolling(20).max()
    breakout = (df["close"] > rolling_max).astype(int)

    # 放量
    avg_vol = df["vol"].shift(1).rolling(20).mean()
    spike = (df["vol"] > 2.0 * avg_vol).astype(int)

    # 复合：两者都成立才算事件
    df["F#EVT_260406_A3B7F9#DEFAULT"] = (breakout & spike).astype(int)
    return df
```

## 关键约束

1. **不得使用未来信息**：所有 rolling/shift 必须使用 `shift(1)` 错开当前 bar
2. **信号必须为整数**：0/1 或 -1/0/1，禁止浮点
3. **NaN 处理**：rolling 计算前期会产生 NaN，可使用 `.fillna(0)` 但要在所有运算之后
4. **多 symbol 数据**：在 EventDrivenEngine 中数据按 symbol 分组传入，函数内不需要再 `groupby('symbol')`
