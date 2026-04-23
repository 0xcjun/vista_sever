# 事件因子代码示例

事件因子（EventDrivenEngine）的完整 `factor_code` 示例。事件信号统一为 0/1 整数列，可与 `EventDriven` 策略模型搭配开平仓。

## 示例 1：20 日新高放量突破

```python
def EVT_260406_A3B7F9(df, **kwargs):
    """20 日新高 + 放量 2 倍 双重确认事件。

    Logic
    -----
    1. 收盘价突破前 20 日（含今日除外）的最高价
    2. 当日成交量 > 前 20 日均量的 2 倍
    3. 同时满足时输出 1，否则 0
    """
    import pandas as pd

    df = df.sort_values("dt").copy()

    rolling_max = df["close"].shift(1).rolling(20).max()
    breakout = df["close"] > rolling_max

    avg_vol = df["vol"].shift(1).rolling(20).mean()
    spike = df["vol"] > 2.0 * avg_vol

    df["F#EVT_260406_A3B7F9#DEFAULT"] = (breakout & spike).fillna(False).astype(int)
    return df
```

## 示例 2：跳空高开追涨

```python
def EVT_260406_B2C8E1(df, **kwargs):
    """跳空 2% 高开且当日上涨事件。"""
    import pandas as pd

    df = df.sort_values("dt").copy()
    prev_close = df["close"].shift(1)
    gap = (df["open"] - prev_close) / prev_close
    intraday_up = df["close"] > df["open"]

    df["F#EVT_260406_B2C8E1#DEFAULT"] = ((gap > 0.02) & intraday_up).fillna(False).astype(int)
    return df
```

## 示例 3：极端跌幅反转候选

```python
def EVT_260406_C9D2F4(df, **kwargs):
    """单日下跌 5% 后第二天的反转候选事件。"""
    import pandas as pd

    df = df.sort_values("dt").copy()
    ret = df["close"].pct_change()
    crash = ret < -0.05
    df["F#EVT_260406_C9D2F4#DEFAULT"] = crash.shift(1).fillna(False).astype(int)
    return df
```

## 示例 4：均线金叉 + 多头排列

```python
def EVT_260406_D8E5A2(df, **kwargs):
    """5 日均线上穿 20 日均线，且 60 日均线向上的复合事件。"""
    import pandas as pd

    df = df.sort_values("dt").copy()
    ma5 = df["close"].rolling(5).mean()
    ma20 = df["close"].rolling(20).mean()
    ma60 = df["close"].rolling(60).mean()

    cross = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
    long_arrange = ma60 > ma60.shift(5)

    df["F#EVT_260406_D8E5A2#DEFAULT"] = (cross & long_arrange).fillna(False).astype(int)
    return df
```

## 公共注意事项

1. **rolling 必须 `shift(1)`**：避免使用当前 bar 自身参与统计
2. **NaN 兜底**：所有事件触发表达式末尾使用 `.fillna(False)` 再 `astype(int)`
3. **整数输出**：列必须是 `int`，禁止保留 bool / float
4. **不要 groupby('symbol')**：EventDrivenEngine 已按 symbol 分组传入，函数内不要重复
5. **命名前缀**：建议使用 `EVT_` 前缀以便后续检索
