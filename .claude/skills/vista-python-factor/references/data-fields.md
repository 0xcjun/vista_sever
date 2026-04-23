# 数据字段定义

本文档定义 Vista 项目截面因子计算所需的标准数据字段。

## MultiIndex 索引要求（核心）

截面因子**必须**使用 `(dt, symbol)` MultiIndex：

```python
# ✅ 正确的数据结构
df.index.names == ['dt', 'symbol']

# 示例数据
# dt                      symbol  open   close    vol
# 2024-01-02  000001.SZ  10.5   10.8    1000
# 2024-01-02  000002.SZ  20.3   20.1    2000
# 2024-01-02  600000.SH  300.2  299.5   5000
# 2024-01-03  000001.SZ  10.8   11.0    1100
# ...
```

**关键要求**:

- **dt**: 日期时间，DataFrame 的第一级索引
- **symbol**: 标的代码，DataFrame 的第二级索引
- 两者共同构成 MultiIndex

## 价格相关字段

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| open | float64 | 开盘价 | 10.50 | 开盘位置分析 |
| close | float64 | 收盘价 | 10.80 | 收盘位置分析 |
| high | float64 | 最高价 | 10.95 | 波动率分析 |
| low | float64 | 最低价 | 10.20 | 波动率分析 |

**注意**: 截面因子中，价格字段通常用于计算衍生指标（如振幅），而非直接比较。

## 成交量相关字段

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| vol | float64 | 成交量 | 1000000 | 换手率分析 |
| amount | float64 | 成交额 | 10800000 | 资金流分析 |

**截面应用示例**:

```python
# 截面换手率排名
df['turnover_rank'] = (df['vol'] / df['vol'].groupby('dt').sum()).groupby(level='dt').rank()
```

## 市值相关字段

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| market_cap | float64 | 总市值 | 1000000000 | 规模因子 |
| circulating_cap | float64 | 流通市值 | 800000000 | 流通盘因子 |

**典型截面因子**:
```python
# 市值排名（最常用）
df['factor'] = df['market_cap'].groupby(level='dt').rank(pct=True)
```

## 估值相关字段

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| pe_ratio | float64 | 市盈率 | 15.5 | 估值因子 |
| pb_ratio | float64 | 市净率 | 2.3 | 估值因子 |
| ps_ratio | float64 | 市销率 | 3.5 | 估值因子 |

**典型截面因子**:
```python
# PE排名（相对估值）
df['factor'] = df['pe_ratio'].groupby(level='dt').rank(pct=True)

# PE标准化
df['factor'] = (df['pe_ratio'] - df['pe_ratio'].groupby('dt').mean()) / df['pe_ratio'].groupby('dt').std()
```

## 财务相关字段

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| roe | float64 | 净资产收益率 | 0.15 | 质量因子 |
| roa | float64 | 总资产收益率 | 0.08 | 质量因子 |
| gross_margin | float64 | 毛利率 | 0.45 | 质量因子 |
| net_margin | float64 | 净利率 | 0.12 | 质量因子 |

**典型截面因子**:
```python
# ROE排名（质量因子）
df['factor'] = df['roe'].groupby(level='dt').rank(pct=True)
```

## 行业分类字段

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| industry | str | 行业分类 | "银行" | 行业中性化 |
| sector | str | 板块分类 | "金融" | 板块中性化 |
| concept | str | 概念标签 | "人工智能" | 主题投资 |

**典型截面因子**:
```python
# 行业内PE排名
df['factor'] = group_rank(df['pe_ratio'], df['industry'])
```

## 技术指标字段

这些字段通常由时序因子预先计算好：

| 字段名 | 类型 | 说明 | 示例 | 用途 |
|--------|------|------|------|------|
| momentum_20d | float64 | 20日动量 | 0.05 | 截面动量 |
| volatility_60d | float64 | 60日波动率 | 0.20 | 风险因子 |
| rs_score | float64 | 相对强弱评分 | 60.0 | 技术面因子 |

**典型截面因子**:
```python
# 动量排名
df['factor'] = df['momentum_20d'].groupby(level='dt').rank(pct=True)

# 波动率排名
df['factor'] = df['volatility_60d'].groupby(level='dt').rank(pct=True)
```

## 数据质量要求

### 1. 完整性

```python
# ✅ 检查必需字段
required_fields = ['dt', 'symbol', 'close']
assert all(field in df.columns for field in required_fields)
```

### 2. MultiIndex 结构

```python
# ✅ 检查 MultiIndex
assert isinstance(df.index, pd.MultiIndex)
assert df.index.names == ['dt', 'symbol']
```

### 3. 无缺失值

```python
# ✅ 关键字段不应缺失
assert df['close'].notna().all()  # 如果允许缺失，需处理
```

### 4. 数据类型正确

```python
# ✅ 价格字段应为浮点数
assert df['close'].dtype == np.float64

# ✅ 行业字段应为字符串
assert df['industry'].dtype == object
```

## 数据获取

### Vista 数据准备

```python
from vista.engines import TimeSeriesEngine

# 计算基础K线数据
df = TimeSeriesEngine.quick_compute(
    klines=raw_data,
    factor_code='...'
)
```

### 添加衍生字段

```python
# 添加市值字段
df['market_cap'] = df['close'] * df['total_shares']

# 添加估值字段
df['pe_ratio'] = df['market_cap'] / df['net_profit_12m']

# 添加行业字段
df = df.merge(industry_data, on=['dt', 'symbol'], how='left')
```

## 数据预处理

### 1. 过滤无效数据

```python
# 过滤停牌股票
df = df[df['vol'] > 0]

# 过滤新股
df = df[df['list_days'] > 252]

# 过滤ST股票
df = df[~df['symbol'].str.contains('ST')]
```

### 2. 填充缺失值

```python
# 前向填充（对于基本面数据）
df['pe_ratio'] = df['pe_ratio'].groupby('symbol').ffill()

# 用中位数填充（截面）
df['pe_ratio'] = df['pe_ratio'].groupby('dt').fillna(df['pe_ratio'].groupby('dt').median())
```

### 3. 极端值处理

```python
# 4倍标准差截尾（内联实现，不再依赖 vista.cs_operators）
def winsorize(series, n_std=4):
    mean, std = series.mean(), series.std()
    return series.clip(mean - n_std * std, mean + n_std * std)

df['pe_ratio'] = winsorize(df['pe_ratio'], n_std=4)
```

## 使用示例

### 基础数据检查

```python
# 检查数据结构
print(df.index.names)  # 应输出 ['dt', 'symbol']
print(df.head())      # 查看前几行
print(df.describe())   # 查看统计信息
```

### 数据质量检查

```python
# 检查缺失值
print(df.isnull().sum())

# 检查每个时间点的股票数量
stocks_per_date = df.groupby('dt').size()
print(stocks_per_date.describe())
```

### 可视化

```python
import matplotlib.pyplot as plt

# 某个时间点的因子分布
df.loc['2024-01-02', 'factor'].hist(bins=50)
plt.title('Factor Distribution on 2024-01-02')
plt.show()
```
