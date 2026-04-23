# FreedomEngine 用法

`vista.engines.freedom.FreedomEngine` 是 Vista 的"自由"因子计算引擎，相比 TSE/CSE/EDE，它**不强制**输入数据形态，允许在 `factor_code` 内执行任意的多步计算流程，包括：

- 拉取外部数据（财务、宏观、资金流、舆情等）
- 多次合并/转置/重采样
- 调用第三方库（autogluon、scikit-learn 等）做模型推理类因子
- 跨频率融合（日线 + 分钟线）

## 何时选用 FreedomEngine

| 需求 | 是否适合 |
|------|---------|
| 单步技术指标 | ❌ 用 TSE |
| 单步截面排名 | ❌ 用 CSE |
| 0/1 事件信号 | ❌ 用 EDE |
| 需要外部数据接入 | ✅ FreedomEngine |
| 需要多步骤组合 + 外部库 | ✅ FreedomEngine |
| 需要 ML 模型推理生成因子 | ✅ FreedomEngine |

## 与 tushare skill 配合

如果用户**未指定**外部数据获取方式，可参考 [tushare skill](../../tushare/SKILL.md) 调用 tushare 数据接口（财务报表、资金流、行业分类、龙虎榜等）。

> **优先级规则**：如果用户在对话中提供了自己的数据获取函数 / API / 文件路径，**优先使用用户指定的方式**，不要默认套用 tushare。

### 使用模板

```python
def FRD_260406_A3B7F9(df, **kwargs):
    """融合 K 线 + 个股资金流入数据的复合因子。

    数据源：tushare moneyflow_dc 接口
    逻辑：5 日动量 × 5 日资金净流入标准化分数
    """
    import pandas as pd
    import tushare as ts

    # 1) 拉取外部数据
    pro = ts.pro_api()
    sdt = pd.Timestamp(df["dt"].min()).strftime("%Y%m%d")
    edt = pd.Timestamp(df["dt"].max()).strftime("%Y%m%d")
    flow_frames = []
    for symbol in df["symbol"].unique():
        ts_code = symbol.split("#")[0]  # vista symbol -> tushare ts_code
        flow = pro.moneyflow(ts_code=ts_code, start_date=sdt, end_date=edt)
        flow["symbol"] = symbol
        flow["dt"] = pd.to_datetime(flow["trade_date"])
        flow_frames.append(flow[["dt", "symbol", "net_mf_amount"]])
    flow_df = pd.concat(flow_frames, ignore_index=True)

    # 2) 合并
    merged = df.merge(flow_df, on=["dt", "symbol"], how="left")
    merged = merged.sort_values(["symbol", "dt"])

    # 3) 计算因子
    grouped = merged.groupby("symbol", group_keys=False)
    momentum = grouped["close"].apply(lambda s: s.pct_change(5))
    flow_score = grouped["net_mf_amount"].apply(
        lambda s: s.rolling(5).sum() / s.rolling(20).std()
    )
    merged["F#FRD_260406_A3B7F9#DEFAULT"] = momentum * flow_score
    return merged
```

## 用户自定义数据源

如果用户提供了 `data` 字典，FreedomEngine 会原样传入：

```python
data = {
    "klines": klines_df,           # 主数据（标准K线）
    "fundamental": fund_df,        # 用户附加：基本面
    "news_sentiment": news_df,     # 用户附加：舆情打分
}

engine = FreedomEngine(data=data, factor=factor)
```

在 `factor_code` 中通过 `kwargs.get("fundamental")` 等方式访问。

## 性能建议

- FreedomEngine 不再自动并行——多步流程需要因子作者自己控制 joblib 调度
- 拉取外部数据时务必加缓存（disk_cache / functools.lru_cache），避免重复 I/O
- 中间 DataFrame 用完显式 `del`，避免内存累积

## 防未来信息

FreedomEngine 因为流程自由，**没有静态检查保障**，作者必须自己保证：
- 任何 rolling/shift 都使用正向参数
- 外部数据按 dt 对齐时使用 `<=` 切片，不引入未来截面
- ML 模型训练数据严格按时间窗口切分（walk-forward）
