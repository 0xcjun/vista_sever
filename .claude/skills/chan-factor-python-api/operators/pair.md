# 双变量算子 (8)

需要两个序列作为输入的滚动窗口算子。

## 相关性与协方差

| 算子 | 语法 | 说明 |
|------|------|------|
| Corr | `Corr($x, $y, window)` | 滚动 Pearson 相关系数 |
| Cov | `Cov($x, $y, window)` | 滚动协方差 |
| TSCorr | `TSCorr($x, $y, window)` | 相关系数（Kahan 补偿） |
| TSCovariance | `TSCovariance($x, $y, window)` | 协方差（Kahan 补偿） |
| TSCorrel | `TSCorrel($x, $y, period=30)` | TA-Lib 相关系数 |

## 回归

| 算子 | 语法 | 说明 |
|------|------|------|
| TSBeta | `TSBeta($x, $y, period=5)` | Beta 系数 cov(x,y)/var(y) |
| TSRegBeta | `TSRegBeta($x, $y, window)` | 回归斜率 β = cov(x,y)/var(y) |
| TSRegResi | `TSRegResi($x, $y, window)` | 回归残差 x - (α + β·y) |

## 示例

```python
cf.compute_factors(data, [
    "Corr($close, $vol, 20)",              # 量价相关性
    "TSBeta($close, $open, 20)",           # Beta 系数
    "TSRegResi($close, $vol, 20)",         # 剥离成交量后的残差
    "CSRank(Corr($close, $vol, 60))",      # 量价相关性截面排名
])
```
