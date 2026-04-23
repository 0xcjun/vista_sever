# 时序因子示例

本文档提供完整的时序因子示例，每个示例都符合 Vista 项目规范。

## 工作流程提醒

1. 编写因子代码（函数名可用占位符 `TSE_PLACEHOLDER`）
2. `validate_factor.py --type ts` 静态校验
3. `vista.engines.base.update_factor_name` 自动生成最终因子名（格式 `TSE_YYMMDD_HASH6`）
4. 落库 `FactorDescribe` / 计算

> ⚠️ 不要再手动生成因子名（旧版的 `create_factor_name.py` 已废弃）。

---

## 示例1：趋势因子

### MA趋势因子（占位符示例）

**因子名称**: `TSF_250124_A3B7F9` (示例)

**因子类型**: 趋势因子
**核心逻辑**: 双移动平均线交叉

```python
def TSF_250124_A3B7F9(df, **kwargs):
    """移动平均线趋势因子

    因子公式：
    1. 计算短期移动平均线：MA_short = close.rolling(short_window).mean()
    2. 计算长期移动平均线：MA_long = close.rolling(long_window).mean()
    3. 趋势因子 = (MA_short - MA_long) / MA_long

    因子逻辑：
    当短期均线高于长期均线时，处于上升趋势，因子值为正
    当短期均线低于长期均线时，处于下降趋势，因子值为负
    因子值大小反映趋势强度，绝对值越大趋势越强

    参数：
        df (pd.DataFrame): K线数据，包含 close 字段
        short_window (int): 短期窗口，默认5
        long_window (int): 长期窗口，默认20

    返回值：
        pd.DataFrame: 包含 F#ma_trend#DEFAULT 列的DataFrame

    示例：
        >>> df = ma_trend(df, short_window=5, long_window=20)
        >>> print(df['F#ma_trend#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd

    # 获取参数
    short = kwargs.get('short_window', 5)
    long = kwargs.get('long_window', 20)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 计算移动平均线（使用 min_periods=1 确保初期数据可用）
    df['ma_short'] = df['close'].rolling(short, min_periods=1).mean()
    df['ma_long'] = df['close'].rolling(long, min_periods=1).mean()

    # 计算趋势因子（带除零保护）
    df[factor_col] = (df['ma_short'] - df['ma_long']) / df['ma_long'].replace(0, np.nan)

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].ffill().fillna(0)

    # 清理中间变量
    del df['ma_short'], df['ma_long']

    return df
```

**特点**:
- ✅ 捕捉价格趋势方向和强度
- ✅ 双均线交叉的经典思路
- ✅ 参数可调整（短期/长期窗口）

---

## 示例2：动量因子

### 20日动量因子

```python
def momentum_20d(df, **kwargs):
    """20日动量因子

    因子公式：
    动量 = (当前收盘价 - N日前收盘价) / N日前收盘价

    因子逻辑：
    捕捉价格动量效应：历史上表现好的股票倾向于在短期内继续表现好
    正值表示上涨动量，负值表示下跌动量
    因子绝对值大小反映动量强度

    参数：
        df (pd.DataFrame): K线数据，包含 close 字段
        period (int): 动量周期，默认20天

    返回值：
        pd.DataFrame: 包含 F#momentum_20d#DEFAULT 列的DataFrame

    示例：
        >>> df = momentum_20d(df, period=20)
        >>> print(df['F#momentum_20d#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd

    # 获取参数
    period = kwargs.get('period', 20)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 计算动量（带除零保护）
    close_n_days_ago = df['close'].shift(period)
    df[factor_col] = (df['close'] - close_n_days_ago) / close_n_days_ago.replace(0, np.nan)

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].ffill().fillna(0)

    return df
```

**特点**:
- ✅ 经典的动量效应实现
- ✅ 计算简单高效
- ✅ 参数可调整（动量周期）

---

## 示例3：波动率因子

### ATR波动率因子

```python
def atr_volatility(df, **kwargs):
    """ATR波动率因子

    因子公式：
    TR = max(high-low, |high-close_prev|, |low-close_prev|)
    ATR = TR.rolling(window).mean()
    因子 = ATR / close

    因子逻辑：
    捕捉价格波动程度，高波动率表示风险大/机会大
    归一化处理使不同价格股票可比较

    参数：
        df (pd.DataFrame): K线数据，包含 high/low/close 字段
        window (int): ATR计算窗口，默认14

    返回值：
        pd.DataFrame: 包含 F#atr_volatility#DEFAULT 列的DataFrame

    示例：
        >>> df = atr_volatility(df, window=14)
        >>> print(df['F#atr_volatility#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd

    # 获取参数
    window = kwargs.get('window', 14)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 计算真实波幅（True Range）
    df['high_low'] = df['high'] - df['low']
    df['high_close_prev'] = np.abs(df['high'] - df['close'].shift(1))
    df['low_close_prev'] = np.abs(df['low'] - df['close'].shift(1))

    df['tr'] = df[['high_low', 'high_close_prev', 'low_close_prev']].max(axis=1)

    # 计算ATR
    df['atr'] = df['tr'].rolling(window, min_periods=1).mean()

    # 归一化（带除零保护）
    df[factor_col] = df['atr'] / df['close'].replace(0, np.nan)

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].ffill().fillna(0)

    # 清理中间变量
    del df['high_low'], df['high_close_prev'], df['low_close_prev'], df['tr'], df['atr']

    return df
```

**特点**:
- ✅ 经典的ATR波动率指标
- ✅ 归一化处理，跨股票可比
- ✅ 捕捉市场不确定性

---

## 示例4：成交量因子

### 量价配合因子

```python
def volume_price_trend(df, **kwargs):
    """量价配合因子

    因子公式：
    价格动量 = close.pct_change()
    成交量动量 = vol.pct_change()
    因子 = 价格动量 * 成交量动量

    因子逻辑：
    捕捉量价配合关系：
    - 价格上涨 + 成交量增加 → 量价齐升，因子值为正
    - 价格下跌 + 成交量增加 → 量价齐跌，因子值为负
    - 价格变动 + 成交量减少 → 量价背离，因子值接近0

    参数：
        df (pd.DataFrame): K线数据，包含 close/vol 字段
        price_window (int): 价格动量窗口，默认5
        vol_window (int): 成交量动量窗口，默认5

    返回值：
        pd.DataFrame: 包含 F#volume_price_trend#DEFAULT 列的DataFrame

    示例：
        >>> df = volume_price_trend(df, price_window=5, vol_window=5)
        >>> print(df['F#volume_price_trend#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd

    # 获取参数
    price_window = kwargs.get('price_window', 5)
    vol_window = kwargs.get('vol_window', 5)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 计算价格动量
    df['price_momentum'] = df['close'].pct_change(price_window)

    # 计算成交量动量
    df['vol_momentum'] = df['vol'].pct_change(vol_window)

    # 量价配合因子
    df[factor_col] = df['price_momentum'] * df['vol_momentum']

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].ffill().fillna(0)

    # 清理中间变量
    del df['price_momentum'], df['vol_momentum']

    return df
```

**特点**:
- ✅ 捕捉量价配合关系
- ✅ 识别趋势强度
- ✅ 过滤虚假信号

---

## 示例5：复合因子

### 多因子组合

```python
def composite_trend_momentum(df, **kwargs):
    """趋势-动量复合因子

    因子公式：
    趋势部分 = (MA_short - MA_long) / MA_long
    动量部分 = (close - close_N天前) / close_N天前
    因子 = 0.6 * 标准化(趋势部分) + 0.4 * 标准化(动量部分)

    因子逻辑：
    组合趋势和动量两个维度：
    - 趋势部分反映长期方向
    - 动量部分反映短期力度
    - 加权组合平滑信号

    参数：
        df (pd.DataFrame): K线数据，包含 close/vol 字段
        short_window (int): 短期窗口，默认5
        long_window (int): 长期窗口，默认20
        momentum_period (int): 动量周期，默认10
        trend_weight (float): 趋势权重，默认0.6
        momentum_weight (float): 动量权重，默认0.4

    返回值：
        pd.DataFrame: 包含 F#composite_trend_momentum#DEFAULT 列的DataFrame

    示例：
        >>> df = composite_trend_momentum(df)
        >>> print(df['F#composite_trend_momentum#DEFAULT'].describe())
    """
    import inspect
    import numpy as np
    import pandas as pd

    # 获取参数
    short = kwargs.get('short_window', 5)
    long = kwargs.get('long_window', 20)
    period = kwargs.get('momentum_period', 10)
    w_trend = kwargs.get('trend_weight', 0.6)
    w_momentum = kwargs.get('momentum_weight', 0.4)

    # 因子列名
    factor_col = f"F#{inspect.currentframe().f_code.co_name}#DEFAULT"

    # 计算趋势部分
    df['ma_short'] = df['close'].rolling(short, min_periods=1).mean()
    df['ma_long'] = df['close'].rolling(long, min_periods=1).mean()
    df['trend'] = (df['ma_short'] - df['ma_long']) / df['ma_long'].replace(0, np.nan)

    # 计算动量部分
    close_prev = df['close'].shift(period)
    df['momentum'] = (df['close'] - close_prev) / close_prev.replace(0, np.nan)

    # 标准化（z-score）
    df['trend_norm'] = (df['trend'] - df['trend'].rolling(60).mean()) / df['trend'].rolling(60).std().replace(0, np.nan)
    df['momentum_norm'] = (df['momentum'] - df['momentum'].rolling(60).mean()) / df['momentum'].rolling(60).std().replace(0, np.nan)

    # 组合因子
    df[factor_col] = w_trend * df['trend_norm'] + w_momentum * df['momentum_norm']

    # 异常值处理
    df[factor_col] = df[factor_col].replace([np.inf, -np.inf], np.nan)
    df[factor_col] = df[factor_col].ffill().fillna(0)

    # 清理中间变量
    del df['ma_short'], df['ma_long'], df['trend'], df['momentum']
    del df['trend_norm'], df['momentum_norm']

    return df
```

**特点**:
- ✅ 多维度复合
- ✅ 标准化处理
- ✅ 权重可调整
- ✅ 平滑信号

---

## 使用这些示例

### 完整生成流程

所有因子都遵循以下标准化流程：

```bash
# 1. 编写因子代码（函数名先用占位符 TSE_PLACEHOLDER）

# 2. 验证代码
python .claude/skills/vista-python-factor/scripts/validate_factor.py my_factor.py --type ts

# 3. 用 update_factor_name 生成最终因子名并落库
#    （Python 代码内调用，参考 references/coding-standards.md）
```

### 修改参数

所有因子都支持参数自定义：

```python
# 使用默认参数
df = TSF_250124_A3B7F9(df)

# 自定义参数
df = TSF_250124_A3B7F9(df, short_window=10, long_window=30)
```

### 组合使用

可以组合多个因子：

```python
# 应用多个因子（每个都有唯一名称）
df = TSF_250124_A3B7F9(df)  # MA趋势因子
df = TSF_250124_C8D2E4(df)  # 动量因子
df = TSF_250124_1A9C3D(df)  # 波动率因子

# 查看所有因子列
factor_cols = [c for c in df.columns if c.startswith('F#TSF_')]
print(df[factor_cols].head())
```

### 命名优势

**旧规范** (描述性命名):
```python
def ma_trend(df, **kwargs):
    # 列名: F#ma_trend#DEFAULT
    # ❌ 可能与其他因子冲突
    # ❌ 无法追溯创建时间
```

**新规范** (工具生成唯一命名):
```python
def TSF_250124_A3B7F9(df, **kwargs):
    # 列名: F#TSF_250124_A3B7F9#DEFAULT
    # ✅ 全局唯一，无冲突风险
    # ✅ 包含创建日期 (250124 = 2025年1月24日)
    # ✅ 统一前缀便于管理 (TSF = TimeSeries Factor)
```

---

## 命名规范说明

### 格式解析

```
TSF_250124_A3B7F9
│   │      │
│   │      └─ 6位MD5哈希值（基于时间戳+随机数）
│   └─ 创建日期（YYMMDD格式）
└─ 固定前缀（TSF = TimeSeries Factor）
```

### 优势对比

| 特性 | 旧规范 (ma_trend) | 新规范 (TSF_250124_A3B7F9) |
|------|------------------|---------------------------|
| 唯一性 | ❌ 可能冲突 | ✅ 绝对唯一 |
| 可追溯性 | ❌ 无时间信息 | ✅ 包含创建日期 |
| 可读性 | ✅ 直观易懂 | ⚠️ 需要查看文档 |
| 管理性 | ⚠️ 需要手动管理 | ✅ 自动化管理 |
| 冲突风险 | ❌ 存在风险 | ✅ 无风险 |

### 兼容性

- **新因子**: 必须使用新规范（工具生成名称）
- **旧因子**: 保持不变，向后兼容
- **迁移**: 可选地重命名旧因子
