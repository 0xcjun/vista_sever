# 内置时序滚动算子 (20)

每个标的独立计算的滚动窗口算子。窗口为 N 时，前 N-1 个值为 NaN（不完整窗口）。

## 统计类

| 算子 | 语法 | 说明 | 算法 |
|------|------|------|------|
| Mean | `Mean($x, window)` | 滚动均值 | 增量 O(n) |
| Sum | `Sum($x, window)` | 滚动求和 | 增量 O(n) |
| Std | `Std($x, window)` | 标准差 (ddof=1) | Welford O(n) |
| Var | `Var($x, window)` | 方差 (ddof=1) | Welford O(n) |
| Count | `Count($x, window)` | 非 NaN 计数 | 增量 O(n) |
| Skew | `Skew($x, window)` | 偏度 (Fisher-Pearson) | O(n) |
| Kurt | `Kurt($x, window)` | 超额峰度 (Fisher) | O(n) |
| Mad | `Mad($x, window)` | 中位数绝对偏差 | O(n×w) |

## 排序/分位类

| 算子 | 语法 | 说明 | 算法 |
|------|------|------|------|
| Rank | `Rank($x, window)` | 滚动排名 [0,1] | 有序Vec O(n log w) |
| Med | `Med($x, window)` | 中位数 | 排序Vec O(n×w) |
| Quantile | `Quantile($x, window, q)` | 分位数 q∈[0,1] | 排序Vec O(n×w) |

## 极值类

| 算子 | 语法 | 说明 | 算法 |
|------|------|------|------|
| Max | `Max($x, window)` | 最大值 | 单调队列 O(n) |
| Min | `Min($x, window)` | 最小值 | 单调队列 O(n) |
| IdxMax | `IdxMax($x, window)` | 最大值位置 (1-based) | O(n) |
| IdxMin | `IdxMin($x, window)` | 最小值位置 (1-based) | O(n) |

## 回归类

| 算子 | 语法 | 说明 |
|------|------|------|
| Slope | `Slope($x, window)` | 线性回归斜率 β |
| Rsquare | `Rsquare($x, window)` | R² 拟合优度 |
| Resi | `Resi($x, window)` | 回归残差 |

## 移动平均类

| 算子 | 语法 | 说明 |
|------|------|------|
| EMA | `EMA($x, n)` | 指数移动平均 α=2/(n+1)，递推 O(n) |
| WMA | `WMA($x, window)` | 加权移动平均，权重 1,2,...,w |

## 示例

```python
cf.compute_factors(data, [
    "Mean($close, 20)",                     # 20日均线
    "Std($close, 20) / Mean($close, 20)",   # 变异系数
    "Rank($close, 60)",                     # 60日排名分位
    "Slope($close, 20)",                    # 趋势斜率
    "EMA($close, 12) - EMA($close, 26)",    # 类MACD
])
```
