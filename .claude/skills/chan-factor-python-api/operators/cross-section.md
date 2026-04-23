# 截面算子 (23)

每个日期横截面（跨所有标的）计算。在 Pass 2 中通过 DateIndex 并行处理。

## 排名与标准化

| 算子 | 语法 | 说明 |
|------|------|------|
| CSRank | `CSRank($x)` | 截面排名 [0,1]，稳定归并排序 |
| CSZscore | `CSZscore($x)` | 截面 Z-score (x-mean)/std |
| CSScale | `CSScale($x, target_sum)` | 截面归一化，使 sum = target_sum |

## 统计量

| 算子 | 语法 | 说明 |
|------|------|------|
| CSMean | `CSMean($x)` | 截面均值 |
| CSStd | `CSStd($x)` | 截面标准差 |
| CSMedian | `CSMedian($x)` | 截面中位数 |
| CSSkew | `CSSkew($x)` | 截面偏度 |
| CSKurt | `CSKurt($x)` | 截面峰度 |

## 数据清洗

| 算子 | 语法 | 说明 |
|------|------|------|
| CSClip | `CSClip($x, lower, upper)` | 截断到 [lower, upper] 区间，NaN 保持 |
| CSFillNa | `CSFillNa($x, fill_value)` | 将 NaN 替换为指定值 |

## 数学函数

| 算子 | 语法 | 说明 |
|------|------|------|
| CSExp | `CSExp($x)` | e^x |
| CSLog1P | `CSLog1P($x)` | ln(1+x) |
| CSSqrt | `CSSqrt($x)` | √x |
| CSPow | `CSPow($x, n)` | x^n |
| CSInv | `CSInv($x)` | 1/x，x=0 返回 NaN |
| CSFloor | `CSFloor($x)` | 向下取整 |

## 三角函数

| 算子 | 语法 | 说明 |
|------|------|------|
| CSSin | `CSSin($x)` | sin(x) |
| CSCos | `CSCos($x)` | cos(x) |
| CSTan | `CSTan($x)` | tan(x) |
| CSTanh | `CSTanh($x)` | tanh(x)，输出∈(-1,1)，天然归一化 |

## 二元运算

| 算子 | 语法 | 说明 |
|------|------|------|
| CSMaxN | `CSMaxN($x, $y)` | max(x, y) |
| CSMinN | `CSMinN($x, $y)` | min(x, y) |

## 特殊

| 算子 | 语法 | 说明 |
|------|------|------|
| CSExtFeature | `CSExtFeature('field')` | 引用扩展字段 |

## 示例

```python
cf.compute_factors(data, [
    "CSRank(Mean($close, 20))",               # 20日均值的截面排名
    "CSZscore($close)",                       # 截面标准化
    "CSClip(CSZscore($close), -3, 3)",        # 截面标准化后去极值
    "CSScale(CSRank($close), 1)",             # 排名后归一化到sum=1
])
```
