# 位移算子 (2)

时间维度上的数据位移。i < n 时返回 NaN。

| 算子 | 语法 | 说明 |
|------|------|------|
| Ref | `Ref($x, n)` | 滞后 n 期，取 x[i-n] 的值 |
| Delta | `Delta($x, n)` | n 期变化量：x[i] - x[i-n]，等价于 `$x - Ref($x, n)` |

## 示例

```python
cf.compute_factors(data, [
    "Ref($close, 1)",                           # 昨日收盘价
    "Delta($close, 5)",                         # 5日变化量
    "Delta($close, 1) / Ref($close, 1)",        # 日收益率
    "$close / Ref($close, 20) - 1",             # 20日涨幅
])
```
