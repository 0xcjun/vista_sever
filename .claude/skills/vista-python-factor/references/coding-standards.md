# Vista Python 因子代码规范

本文档定义 Vista 项目 Python 类因子代码的统一编写规范，覆盖 **时序因子(TSE)**、**截面因子(CSE)**、**事件因子(EDE)** 与 **Freedom 因子**。所有生成的因子必须严格遵守。

## 函数签名

```python
def factor_name(df, **kwargs):
    """因子计算函数

    Args:
        df (pd.DataFrame): K线数据 (TSE: 单标的时序; CSE: MultiIndex (dt, symbol); EDE/Freedom: 见各引擎说明)
        **kwargs: 引擎传入的运行时参数

    Returns:
        pd.DataFrame: 包含因子列的 DataFrame
    """
    ...
    return df
```

## 因子命名（**重要变更**）

### 不要手动生成因子名

旧版 SKILL 提供过 `create_factor_name.py`，**已废弃**。

**新规范**：因子名由 `vista.engines.base.update_factor_name(factor)` 在创建 `FactorDescribe` 之后自动生成，格式为 `{ENGINE}_{YYMMDD}_{HASH6}`，例如 `TSE_260406_A3B7F9`、`CSE_260406_3F9CE3`。

```python
from vista.engines.base import update_factor_name
from vista.factor_db.models import FactorDescribe, ComputeEngine

raw_factor = FactorDescribe(
    factor_name="placeholder",  # 占位即可，会被覆盖
    factor_code=factor_code,
    compute_engine=ComputeEngine.TSE,
    description="20 日均线偏离度",
)
factor = update_factor_name(raw_factor)
print(factor.factor_name)  # → TSE_260406_A3B7F9
```

写代码时函数名可以先用占位符（例如与最终一致的格式 `TSE_260406_A3B7F9`），再由调用方在落库前用 `update_factor_name` 重新生成；或者直接在生成 factor_code 时用占位符，由 update 函数根据时间戳和 factor_code 哈希得到最终名。

### 因子列名

```python
# 标准格式（与函数名同步）
factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"
```

## 必须遵守的规则

### 1. 标准导入

```python
import inspect
import numpy as np
import pandas as pd
# import talib as ta  # TSE 可选
```

> ⚠️ **不要写** `from vista.cs_operators import *`、`from vista.operates import ...` 等。算子模块已迁出 vista 包，位于本 SKILL `scripts/` 下，仅作为参考资料；如需在因子代码内部使用相同算法，请将算法**内联实现**或调用 numpy/pandas/talib。

### 2. 因子列命名（与函数名自动一致）

```python
factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"  # ✅
factor_col = "my_factor"                                            # ❌
```

### 3. 异常值处理（必须）

```python
df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
df[factor_col] = df[factor_col].ffill().fillna(0)
```

### 4. 除零保护（必须）

```python
df['ratio'] = df['x'] / df['y'].replace(0, np.nan)   # ✅
df['ratio'] = df['x'] / df['y']                       # ❌ 可能除零
```

### 5. 中间变量清理

```python
df['ma5'] = df['close'].rolling(5).mean()
df['ma20'] = df['close'].rolling(20).mean()
df[factor_col] = df['ma5'] / df['ma20']
del df['ma5'], df['ma20']
```

### 6. 文档字符串

```python
def factor_name(df, **kwargs):
    """因子名称（一句话描述）

    因子公式:
        ...

    因子逻辑:
        ...金融逻辑/市场含义...

    参数:
        df (pd.DataFrame): K线数据
        param1 (type): 参数说明，默认值

    返回值:
        pd.DataFrame: 包含因子列的 DataFrame
    """
```

## 类型专项规则

### 时序因子 (TSE)

**防未来信息泄露** —— 静态校验由 `validate_factor.py --type ts` 强制执行：

```python
df['rank']  = df['close'].rolling(20).rank()  # ✅ rank 必须配合 rolling
df['rank']  = df['close'].rank()              # ❌ 全样本 rank → 未来信息

df['shift'] = df['close'].shift(1)            # ✅ 正参数 = 过去
df['shift'] = df['close'].shift(-1)           # ❌ 负参数 = 未来

df['ma']    = df['close'].rolling(5).mean()   # ✅
df['ma']    = df['close'].rolling(-5).mean()  # ❌
```

### 截面因子 (CSE)

**MultiIndex (dt, symbol)** —— 由 `validate_factor.py --type cs` 校验：

```python
# ✅ 正确：截面操作必须按 dt 分组
df[factor_col] = df['field'].groupby(level='dt').rank(pct=True)
df[factor_col] = df['field'].groupby('dt').rank(pct=True)

# ❌ 错误：按 symbol 分组等同于时序操作
df[factor_col] = df['field'].groupby('symbol').mean()

# 必须 sort_index() 返回
return df.sort_index()
```

### 事件因子 (EDE)

输出为整数 0/1（或 -1/0/1），见 [`operators-events.md`](operators-events.md) 与 [`examples-event.md`](examples-event.md)。

### Freedom 因子

可在因子代码内自由获取外部数据，见 [`freedom-engine.md`](freedom-engine.md)。**没有静态校验**，作者需自行保证防未来信息。

## 代码验证

```bash
# 时序因子
python .claude/skills/vista-python-factor/scripts/validate_factor.py my_factor.py --type ts

# 截面因子
python .claude/skills/vista-python-factor/scripts/validate_factor.py my_factor.py --type cs
```

校验通过后，再用 `vista.engines.base.update_factor_name` 生成正式因子名并落库。
