# 特殊算子 (4)

跨标的引用和字段操作。

| 算子 | 语法 | 说明 |
|------|------|------|
| Feature | `Feature('field')` | 引用字段值，等价于 `$field` |
| PFeature | `PFeature('field')` | 引用字段值（兼容别名） |
| ChangeInstrument | `ChangeInstrument('symbol', $x)` | 引用另一标的的值 |
| Mask | `Mask($x, 'symbol')` | 用指定标的的日期掩码过滤当前标的 |

## 示例

```python
cf.compute_factors(data, [
    "ChangeInstrument('000001.SZ', $close)",  # 引用平安银行收盘价
    "$close / ChangeInstrument('000300.SH', $close)",  # 相对指数强弱
])
```
