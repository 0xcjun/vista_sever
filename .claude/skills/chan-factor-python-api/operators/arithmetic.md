# 算术算子 (15)

逐元素运算。任意操作数为 NaN 时结果为 NaN。

## 基本运算

| 算子 | 语法 | 说明 |
|------|------|------|
| Add | `$x + $y` 或 `Add($x, $y)` | 加法 |
| Sub | `$x - $y` 或 `Sub($x, $y)` | 减法 |
| Mul | `$x * $y` 或 `Mul($x, $y)` | 乘法 |
| Div | `$x / $y` 或 `Div($x, $y)` | 除法，y=0 返回 NaN |
| Mod | `Mod($x, $y)` | 取模 x mod y |
| Power | `Power($x, n)` | 幂运算 x^n |
| Negate | `-$x` 或 `Negate($x)` | 取反 |

## 数学函数

| 算子 | 语法 | 说明 |
|------|------|------|
| Abs | `Abs($x)` | 绝对值 \|x\| |
| Sqrt | `Sqrt($x)` | 平方根，x<0 返回 NaN |
| Exp | `Exp($x)` | 指数函数 e^x |
| Log | `Log($x)` | 自然对数 ln(x)，x≤0 返回 NaN |
| Log1p | `Log1p($x)` | ln(1+x)，x 接近 0 时精度更高 |
| Sign | `Sign($x)` | 符号函数：正→1，零→0，负→-1 |

## 二元比较取值

| 算子 | 语法 | 说明 |
|------|------|------|
| Greater | `Greater($x, $y)` | max(x, y) |
| Less | `Less($x, $y)` | min(x, y) |

## 示例

```python
cf.compute_factors(data, [
    "$close * 2 + $open",            # 算术组合
    "Power($close / $open, 2)",      # 涨幅平方
    "Log($close) - Log(Ref($close, 1))",  # 对数收益率
    "Sign(Delta($close, 1))",        # 涨跌方向
])
```
