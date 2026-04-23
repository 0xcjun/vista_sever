# 扩展时序算子 (53)

TS 前缀算子，使用 Kahan 补偿算法确保与 C# 参考实现数值一致。

## 基础统计（Kahan 补偿版）

| 算子 | 语法 | 说明 |
|------|------|------|
| TSMean | `TSMean($x, window)` | 均值（Kahan 补偿） |
| TSSum | `TSSum($x, window)` | 求和（Kahan 补偿） |
| TSStd | `TSStd($x, window)` | 标准差（Kahan 补偿） |
| TSVar | `TSVar($x, window, ddof)` | 方差，可指定自由度 |
| TSSkew | `TSSkew($x, window)` | 偏度（Kahan 补偿） |
| TSKurt | `TSKurt($x, window)` | 峰度（Kahan 补偿） |
| TSMad | `TSMad($x, window)` | 中位数绝对偏差（Kahan） |
| TSCount | `TSCount($cond, window)` | 窗口内条件为真的个数 |
| TSProd | `TSProd($x, window)` | 滚动乘积 |

## 排序/分位

| 算子 | 语法 | 说明 |
|------|------|------|
| TSRank | `TSRank($x, window)` | 归一化排名 [0,1] |
| TSMedian | `TSMedian($x, window)` | 中位数 |
| TSQuantile | `TSQuantile($x, window, q)` | 分位数 q∈[0,1] |
| TSPercentile | `TSPercentile($x, p, window)` | 第 p 百分位数 |
| TSQuantileDiff | `TSQuantileDiff($x, window, q)` | 分位数与当前值之差 |
| TSMode | `TSMode($x, window)` | 众数 |

## 极值与位置

| 算子 | 语法 | 说明 |
|------|------|------|
| TSMax | `TSMax($x, window)` | 最大值 |
| TSMin | `TSMin($x, window)` | 最小值 |
| TSArgMax | `TSArgMax($x, window)` | 最大值索引 (0-based) |
| TSArgMin | `TSArgMin($x, window)` | 最小值索引 (0-based) |
| TSRollingArgMax | `TSRollingArgMax($x, window)` | 滚动最大值索引 (0-based) |
| TSHighDay | `TSHighDay($x, window)` | 距窗口内最高点的天数 |
| TSLowDay | `TSLowDay($x, window)` | 距窗口内最低点的天数 |

## 收益率与变化

| 算子 | 语法 | 说明 |
|------|------|------|
| TSPctChange | `TSPctChange($x, n)` | 百分比变化 (x[i]-x[i-n])/x[i-n] |
| TSLogRet | `TSLogRet($x)` | 对数收益率 ln(x[i]/x[i-1]) |
| TSPctSigmoid | `TSPctSigmoid($x, a, b)` | 百分比变化经 sigmoid 压缩 |

## 移动平均与平滑

| 算子 | 语法 | 说明 |
|------|------|------|
| TSSma | `TSSma($x, window)` | 简单移动平均 |
| TSDoubleSma | `TSDoubleSma($x, short, long)` | 双均线信号 SMA(fast) - SMA(slow) |
| TSDecayLinear | `TSDecayLinear($x, window)` | 线性衰减加权平均 |
| TSUltimateSmooth | `TSUltimateSmooth($x, fast, slow)` | Ehlers 终极平滑器 |

## 标准化

| 算子 | 语法 | 说明 |
|------|------|------|
| TSZScore | `TSZScore($x, window)` | 时序 Z-score (x-mean)/std |
| TSBias | `TSBias($x, window)` | 偏离度 (x-mean)/mean |

## 波动率

| 算子 | 语法 | 说明 |
|------|------|------|
| TSIv | `TSIv($logret, window)` | 已实现波动率（年化）std×√252 |
| TSRollingGap | `TSRollingGap($x, window)` | 滚动缺口 (max-min)/mean |
| TSSnr | `TSSnr($x, window)` | 信噪比 |

## 布林带

| 算子 | 语法 | 说明 |
|------|------|------|
| TSBbUpper | `TSBbUpper($x, window)` | 上轨 SMA + 2σ |
| TSBbMiddle | `TSBbMiddle($x, window)` | 中轨 SMA |
| TSBbLower | `TSBbLower($x, window)` | 下轨 SMA - 2σ |

## 自相关

| 算子 | 语法 | 说明 |
|------|------|------|
| TSAutoCorr | `TSAutoCorr($x, window)` | 自相关系数 corr(x[t], x[t-1]) |

## 条件与过滤

| 算子 | 语法 | 说明 |
|------|------|------|
| TSFilter | `TSFilter($x, $cond)` | 不满足条件时置 NaN |
| TSSumIf | `TSSumIf($x, window, $cond)` | 窗口内满足条件的值求和 |
| TSSumAcc | `TSSumAcc($x, window)` | 累加和（带 NaN 处理） |

## 排名运算

| 算子 | 语法 | 说明 |
|------|------|------|
| TSRankSub | `TSRankSub($x, $y, window)` | 排名差 rank(x) - rank(y) |
| TSRankDiv | `TSRankDiv($x, $y, window)` | 值除以排名 |

## 技术指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSKdjJ | `TSKdjJ($close, period, k_period)` | KDJ J值 3K-2D |
| TSRsiCompat | `TSRsiCompat($x, window)` | RSI 独立实现 100-100/(1+RS) |
| TSMacdCompat | `TSMacdCompat($x, fast, slow)` | MACD 独立实现 |
| TSDeriv2 | `TSDeriv2($x, window)` | 二阶导数（拐点检测） |
| TSMar | `TSMar($x, window)` | 市场调整收益 |

## 其他

| 算子 | 语法 | 说明 |
|------|------|------|
| TSSequence | `TSSequence(n)` | 生成序号 0,1,...,n-1 |
| TSVwap | `TSVwap($price, $vol, window)` | VWAP 成交量加权平均价 |
| TSXyRsquare | `TSXyRsquare($x, $y, window)` | 双变量 R² |

## 示例

```python
cf.compute_factors(data, [
    "TSZScore($close, 20)",                # 20日Z-score标准化
    "TSPctChange($close, 5)",              # 5日收益率
    "TSRank($close, 60)",                  # 60日排名分位
    "TSBbUpper($close, 20) - $close",      # 距布林上轨距离
    "TSDecayLinear($close, 10)",           # 线性衰减加权
])
```
