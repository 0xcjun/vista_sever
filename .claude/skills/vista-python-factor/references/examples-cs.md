# 截面因子示例

本文档提供完整的截面因子示例，每个示例都符合 Vista 项目规范。

## 工作流程提醒

1. 编写因子代码（函数名可用占位符，例如 `CSE_PLACEHOLDER`）
2. 用 `validate_factor.py --type cs` 静态校验
3. 用 `vista.engines.base.update_factor_name` 自动生成最终因子名（格式 `CSE_YYMMDD_HASH6`）
4. 落库 `FactorDescribe` / 计算

> ⚠️ 不要再手动生成因子名（旧版的 `create_factor_name.py` 已废弃）。
> ⚠️ 不要在因子代码中 `from vista.cs_operators import ...`，算子已迁出 vista 包；如需算法请内联实现。

---

## 示例1：排名因子

### 市值排名因子

**因子类型**: 排名因子
**核心逻辑**: 按市值在截面上排名

```python
def CSE_PLACEHOLDER(df, **kwargs):
    """市值排名因子

    因子公式：
    rank = df['market_cap'].groupby(level='dt').rank(pct=True)

    因子逻辑：
    在每个时间点，按市值对所有股票进行排名
    - rank 值接近 1：市值小的股票
    - rank 值接近 0：市值大的股票
    这是典型的截面比较因子，用于相对估值

    参数：
        df (pd.DataFrame): K线数据，必须包含 (dt, symbol) MultiIndex 和 market_cap 字段
        ascending (bool): 排序方向，True=升序（小市值排名高），默认 False

    返回值：
        pd.DataFrame: 包含 F#CSF_250124_A3B7F9#DEFAULT 列的 DataFrame

    示例：
        >>> df = CSF_250124_A3B7F9(df, ascending=False)
        >>> print(df['F#CSF_250124_A3B7F9#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd

    # 获取参数
    ascending = kwargs.get('ascending', False)

    # 因子列名（自动匹配函数名）
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 计算截面排名
    df[factor_col] = df['market_cap'].groupby(level='dt').rank(pct=ascending)

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].fillna(0.5)

    # 返回排序后的结果
    return df.sort_index()
```

**特点**:
- ✅ 横截面比较
- ✅ 值域 [0, 1]，便于解释
- ✅ 参数可调整（排序方向）

---

## 示例2：标准化因子

### PE标准化因子

**因子名称**: `CSF_250124_C8D2E4` (示例)

**因子类型**: 标准化因子
**核心逻辑**: PE值的截面标准化

```python
def CSF_250124_C8D2E4(df, **kwargs):
    """PE标准化因子

    因子公式：
    zscore = (PE - PE_mean) / PE_std
    其中 PE_mean 和 PE_std 是每个时间点的截面均值和标准差

    因子逻辑：
    将PE值进行截面标准化：
    - zscore > 0：PE高于截面平均（估值偏高）
    - zscore < 0：PE低于截面平均（估值偏低）
    - zscore = 0：等于截面平均
    标准化后不同股票可比，消除量纲影响

    参数：
        df (pd.DataFrame): K线数据，必须包含 (dt, symbol) MultiIndex 和 pe_ratio 字段
        with_winsorize (bool): 是否先进行极端值处理，默认 False

    返回值：
        pd.DataFrame: 包含 F#CSF_250124_C8D2E4#DEFAULT 列的 DataFrame

    示例：
        >>> df = CSF_250124_C8D2E4(df, with_winsorize=True)
        >>> print(df['F#CSF_250124_C8D2E4#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd
    # 算子已迁出 vista 包；以下为内联实现示意

    # 获取参数
    with_winsorize = kwargs.get('with_winsorize', False)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 获取 PE 数据
    pe = df['pe_ratio']

    # 可选：极端值处理
    if with_winsorize:
        pe = winsorize(pe)

    # 截面标准化
    df[factor_col] = zscore(pe)

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].fillna(0)

    # 返回排序后的结果
    return df.sort_index()
```

**特点**:
- ✅ 去量纲影响
- ✅ 可组合性强
- ✅ 支持极端值处理

---

## 示例3：缩放因子

### 信号缩放因子

**因子名称**: `CSF_250124_1A9C3D` (示例)

**因子类型**: 缩放因子
**核心逻辑**: 将信号转换为可投资的权重

```python
def CSF_250124_1A9C3D(df, **kwargs):
    """信号缩放因子

    因子公式：
    scaled = scale(signal, scale=1, longscale=1, shortscale=1)

    因子逻辑：
    将任意信号转换为可投资的权重：
    - scale: 总体缩放比例
    - longscale: 多头资金占比
    - shortscale: 空头资金占比
    - 分别归一化多头和空头，确保权重和为 scale

    适用场景：
    - 将 alpha 信号转换为组合权重
    - 控制多头和空头总敞口
    - 资金分配和风险管理

    参数：
        df (pd.DataFrame): K线数据，必须包含 (dt, symbol) MultiIndex 和 signal 字段
        scale (float): 总体缩放比例，默认 1
        longscale (float): 多头资金占比，默认 1
        shortscale (float): 空头资金占比，默认 1

    返回值：
        pd.DataFrame: 包含 F#CSF_250124_1A9C3D#DEFAULT 列的 DataFrame

    示例：
        >>> df = CSF_250124_1A9C3D(df, scale=1, longscale=0.5, shortscale=0.5)
        >>> print(df['F#CSF_250124_1A9C3D#DEFAULT'].groupby('dt').sum())
    """
    import inspect
    import numpy as np
    import pandas as pd
    # 算子已迁出 vista 包；如需 scale 请内联实现或调用 numpy 等价操作

    # 获取参数
    scale_param = kwargs.get('scale', 1)
    longscale = kwargs.get('longscale', 1)
    shortscale = kwargs.get('shortscale', 1)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 获取信号
    signal = df['signal']

    # 应用缩放
    df[factor_col] = scale(signal, scale=scale_param, longscale=longscale, shortscale=shortscale)

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].fillna(0)

    # 返回排序后的结果
    return df.sort_index()
```

**特点**:
- ✅ 资金分配控制
- ✅ 多空平衡
- ✅ 灵活的缩放参数

---

## 使用这些示例

### 修改参数

所有因子都支持参数自定义：

```python
# 使用默认参数
df = CSF_250124_A3B7F9(df)

# 自定义参数
df = CSF_250124_A3B7F9(df, ascending=True)
```

### 组合使用

可以组合多个截面因子：

```python
# 应用多个因子
df = CSF_250124_A3B7F9(df)  # 市值排名
df = CSF_250124_C8D2E4(df)  # PE标准化
df = CSF_250124_1A9C3D(df)  # 信号缩放

# 查看所有因子列
factor_cols = [c for c in df.columns if c.startswith('F#CSF_')]
print(df[factor_cols].head())
```

### 验证代码

生成因子后，使用验证工具检查：

```bash
python .claude/skills/vista-python-factor/scripts/validate_factor.py my_factor.py --type cs
```

## 与时序因子的对比

### 时序因子示例
```python
# 时序：单只股票的历史趋势
def TSF_250124_A3B7F9(df, **kwargs):
    # 在时间维度上操作
    df['ma'] = df['close'].groupby('symbol').rolling(20).mean()
    return df
```

### 截面因子示例
```python
# 截面：同一时刻多只股票的比较
def CSF_250124_A3B7F9(df, **kwargs):
    # 在截面维度上操作
    df['rank'] = df['close'].groupby(level='dt').rank()
    return df.sort_index()
```

### 关键区别

| 特性 | 时序因子 | 截面因子 |
|------|---------|---------|
| **比较对象** | 历史数据 | 不同股票 |
| **分组方式** | `groupby('symbol')` | `groupby(level='dt')` |
| **返回排序** | 可选 | 必须 `sort_index()` |
| **数据要求** | 时间序列 | MultiIndex (dt, symbol) |
