---
name: vista-ast-factor
description: 指导大模型编写适用于 AST 引擎的因子表达式（chan_factor_rs 0.3.0+）。支持 TimeSeriesAstEngine (TSA) 和 CrossSectionAstEngine (CSA)。触发场景：用户要求生成 AST 因子、AST 表达式因子、使用 TimeSeriesAstEngine 或 CrossSectionAstEngine 计算的因子；因子代码为纯表达式字符串（非 Python 函数）；使用 chan_factor_rs.get_operators() 算子清单；或在 AstFactorBuilder 中生成因子。不适用于：Python 函数因子（用 vista-ts-factor-generator）、横截面 Python 函数因子（用 vista-cs-factor-generator）。
---

# AST 因子生成器

生成可直接由 `TimeSeriesAstEngine` / `CrossSectionAstEngine` 执行的 AST 表达式因子，表达式由 `chan_factor_rs` 0.3.0+ (Rust) 高性能执行。

## 引擎选择

| 引擎 | 枚举值 | 因子类型 | CS 算子 | 命名前缀 |
|------|--------|---------|---------|---------|
| `TimeSeriesAstEngine` | `ComputeEngine.TSA` | 时序（自己跟自己比） | 禁止 | `TSF_` |
| `CrossSectionAstEngine` | `ComputeEngine.CSA` | 截面（跟别人比） | 允许 | `CSF_` |

判断口诀：
- "自己跟自己比"（趋势、动量、波动率）→ TSA
- "跟别人比"（排名、标准化、相对估值）→ CSA

## 语法糖（0.3.0 新增）

chan-factor-rs 0.3.0 支持多种语法糖，**默认使用多行变量绑定格式**以提高可读性：

### 多行变量绑定（默认格式）

将嵌套表达式拆解为带语义的中间变量，最后一行为输出：

```
ma = Mean($close, 20)
sd = Std($close, 20)
Div(Sub($close, ma), Add(sd, 1e-6))
```

**规则**：
- 变量名支持：字母/下划线/数字，如 `ma`、`close_std`、`v1`
- 保留字不可用作变量名：`nan`、`inf`、`true`、`false`
- 最后一行为因子输出（可以是赋值 `result = expr` 或裸表达式）
- 变量可复用（同一 NodeId，只计算一次）
- 空行被忽略

### 中缀运算符

在表达式和变量绑定中均可使用中缀运算符：

```
# 纯函数调用
Div(Sub($close, Mean($close, 20)), Add(Std($close, 20), 1e-6))

# 等价的中缀写法
($close - Mean($close, 20)) / (Std($close, 20) + 1e-6)

# 混合：变量绑定 + 中缀（推荐）
ma = Mean($close, 20)
sd = Std($close, 20)
($close - ma) / (sd + 1e-6)
```

**支持的中缀运算符**：`+` `-` `*` `/` `**` `>` `>=` `<` `<=` `==` `!=` `&` `|` `~`（按位非=逻辑非）

### 特殊字面量

`nan`、`inf` 可直接作为值使用：`If($close > $open, $close, nan)`

## 单一事实源

算子规范来自 `chan_factor_rs`，**不要硬编码算子名称**：

```python
import chan_factor_rs as cf
ops = cf.get_operators()  # 返回 187 个算子，每个包含 name, type, desc

# 按类型筛选
ts_ops = [op for op in ops if op["type"] == "ts"]        # 时序算子
cs_ops = [op for op in ops if op["type"] == "cs"]        # 横截面算子
talib_ops = [op for op in ops if op["type"] == "talib"]  # TA-Lib 算子
arith_ops = [op for op in ops if op["type"] == "arithmetic"]  # 算术
logic_ops = [op for op in ops if op["type"] == "logical"]     # 逻辑
pair_ops = [op for op in ops if op["type"] == "pair"]    # 双变量
```

**引擎算子约束**：
- **TSA**：允许 ts + talib + arithmetic + logical + pair，**禁止** cs
- **CSA**：允许全部类型

## 常用算子速查（0.3.0，187 个算子）

> 注意：核心滚动算子无 `TS` 前缀（`Mean`/`Std`/`Var` 等），扩展算子有 `TS` 前缀（`TSMean`/`TSStd` 等）。两者功能等价，优先使用核心算子（更简洁）。

### 核心滚动算子（无 TS 前缀）
- `Mean($x, n)` - 时序均值 | `Std($x, n)` - 标准差 | `Var($x, n)` - 方差
- `Sum($x, n)` - 时序求和 | `Max($x, n)` / `Min($x, n)` - 最小/最大值
- `EMA($x, n)` - 指数移动平均 | `WMA($x, n)` - 加权移动平均
- `Delta($x, n)` - 差分 | `Slope($x, n)` - 线性回归斜率
- `Rank($x, n)` - 时序排名 | `Count($x, n)` - 非空计数
- `Ref($x, n)` - 延迟引用 | `Quantile($x, n, q)` - 分位数
- `Skew($x, n)` - 偏度 | `Kurt($x, n)` - 峰度 | `Mad($x, n)` - 平均绝对偏差
- `Corr($x, $y, n)` - 相关性 | `Cov($x, $y, n)` - 协方差
- `IdxMax($x, n)` / `IdxMin($x, n)` - 最大/最小值位置
- `Rsquare($x, n)` - R² | `Resi($x, n)` - 回归残差
- `Med($x, n)` - 中位数

### 扩展时序算子（TS 前缀）
- `TSZScore($x, n)` - Z-score 标准化 | `TSRank($x, n)` - 时序排名
- `TSPctChange($x, n)` - 百分比变化 | `TSLogRet($x)` - 对数收益率
- `TSBias($x, n)` - 乖离率 | `TSSnr($x, n)` - 信噪比
- `TSVwap($x, $y, n)` - 成交量加权均价 | `TSIv($x, n)` - 已实现波动率
- `TSSumIf($x, n, cond)` - 条件求和 | `TSCount(cond, n)` - 条件计数
- `TSPercentile($x, q, n)` - 时序百分位 | `TSSequence(n)` - 生成序列 1..n
- `TSRegBeta($x, $y, n)` - 回归 beta | `TSRegResi($x, $y, n)` - 回归残差
- `TSQuantileDiff($x, n, q)` - 分位差
- `TSAutoCorr($x, n)` - 自相关 | `TSXyRsquare($x, $y, n)` - R²
- `TSRollingGap($x, n)` - 滚动缺口 | `TSMar($x, n)` - MAR 比率
- `TSDecayLinear($x, n)` - 线性衰减加权 | `TSProd($x, n)` - 累积乘积
- `TSArgMax($x, n)` / `TSArgMin($x, n)` - 最大/最小值位置
- `TSHighDay($x, n)` / `TSLowDay($x, n)` - 距最高/最低天数
- `TSBbUpper($x, n)` / `TSBbMiddle($x, n)` / `TSBbLower($x, n)` - 布林带
- `TSSma($x, n)` - SMA 均线 | `TSDoubleSma($x, fast, slow)` - 双 SMA
- `TSKdjJ($x, n, m)` - KDJ-J 值 | `TSMacdCompat($x, fast, slow)` - MACD
- `TSRsiCompat($x, n)` - RSI（兼容模式）
- `TSRankSub($x, $y, n)` / `TSRankDiv($x, $y, n)` - 排名差/比
- `TSUltimateSmooth($x, n)` - 终极平滑 | `TSMode($x, n)` - 众数
- `TSRollingArgMax($x, n)` - 滚动最大值位置 | `TSDeriv2($x, n)` - 二阶导数

### 横截面算子 (cs) — 仅 CSA
- `CSRank($x)` - 截面排名 [0,1] | `CSMean($x)` - 截面均值
- `CSStd($x)` - 截面标准差 | `CSZScore($x)` - Z-score 标准化
- `CSScale($x, a)` - 缩放到 [-a, a] | `CSMedian($x)` - 截面中位数
- `CSSkew($x)` - 截面偏度 | `CSKurt($x)` - 截面峰度
- `CSClip($x, lo, hi)` - 截断 | `CSFillNa($x, val)` - 填充 NaN
- `CSInv($x)` - 取倒数 | `CSMaxN($x, $y)` / `CSMinN($x, $y)` - 逐元最大/最小
- `CSSqrt($x)` - 截面平方根 | `CSPow($x, n)` - 截面幂次
- `CSFloor($x)` - 向下取整 | `CSLog1P($x)` - log(1+x)
- `CSSin/CSCos/CSTan/CSExp/CSTanh($x)` - 三角/指数函数

### 基础运算 (arithmetic/logical)
- `Add(x, y)` / `Sub(x, y)` / `Mul(x, y)` / `Div(x, y)` / `Power(x, y)`
- `Abs(x)` / `Log(x)` / `Sign(x)` / `Exp(x)` / `Sqrt(x)`
- `Gt(x, y)` / `Ge(x, y)` / `Lt(x, y)` / `Le(x, y)` / `Eq(x, y)` / `Ne(x, y)`
- `If(cond, then, else)` / `And(x, y)` / `Or(x, y)` / `Not(x)`

### TA-Lib 算子（TS 前缀）
- `TSRsi($x, n)` - RSI | `TSMom($x, n)` - 动量 | `TSRoc($x, n)` - 变化率
- `TSMacd($x, f, s, sig)` - MACD | `TSMacdSig($x, f, s, sig)` / `TSMacdHist(...)`
- `TSAtr($h, $l, $c, n)` - ATR | `TSAdx($h, $l, $c, n)` - ADX
- `TSTrix($x, n)` | `TSCci($h, $l, $c, n)` | `TSSar($h, $l, af, maxaf)`
- `TSLinReg($x, n)` | `TSLinRegSlope($x, n)` | `TSLinRegAngle($x, n)`
- 以及其他 52 个 TA-Lib 算子（详见 `cf.get_operators()`）

## 工作流程

### 1. 选择算子
从 `cf.get_operators()` 返回的算子中选择，TSA 排除 `type=cs`。

### 2. 生成表达式（默认：多行变量绑定）
产物是 AST 表达式字符串，不是 Python 函数。**默认使用多行变量绑定格式**，提高可读性。

**格式规则**：
- 使用语义化变量名（如 `ma`、`sd`、`ret`、`vol_ratio`）
- 每行一个变量绑定或最终表达式
- 最后一行为因子输出
- 组合 2-4 个算子，参数用稳健默认值（5/10/20/30/60）

### 3. 试跑验证
```python
cf.compute_factors(data=test_df, factors=[expression], return_as="pandas")
```
若报错必须重新生成。

## 强制校验（每条必过）

1. **算子合法性**：表达式中所有算子必须存在于 `cf.get_operators()` 的 `name` 集合
2. **引擎算子约束**：TSA 不得包含 `type=cs` 算子
3. **无未来引用**：不得出现 `Ref($x, -k)`（k > 0，向前引用）
4. **试跑通过**：`cf.compute_factors` 最小样本试跑无报错

任一校验失败必须重新生成。

## 硬约束

1. 只输出 AST 表达式，不输出 `def ...` 函数体
2. 不输出 `if __name__`、`print(...)`、脚本测试代码
3. 不输出 `df[...] = ...` 赋值语句
4. 只使用 `$open/$high/$low/$close/$vol/$amount` 作为基础字段
5. 禁止未来引用：`Ref($x, -k)`（k > 0）不能出现在表达式中
6. 除法做分母保护：`Div(num, Add(den, 1e-6))` 或 `num / (den + 1e-6)`
7. 单表达式不超过 5 个算子嵌套

## 输出格式（固定 6 字段 JSON）

**`factor_code` 字段默认使用多行变量绑定格式**：

```json
{
  "engine_mode": "ast",
  "compute_engine": "ComputeEngine.TSA",
  "factor_code": "ma10 = Mean($close, 10)\nma30 = Mean($close, 30)\nDiv(Sub(ma10, ma30), Add(ma30, 1e-6))",
  "formula_explanation": "使用10日和30日均线差衡量短期趋势强度，并做比例归一化",
  "data_fields_used": ["close"],
  "future_leakage_check": {"status": "pass", "notes": "使用 Mean 和 Div/Sub 算子，无未来函数引用"}
}
```

## 正确示例

### TSA - 动量因子（多行变量绑定）
```
engine_mode: ast
compute_engine: ComputeEngine.TSA
factor_code: |
  TSRoc($close, 20)
formula_explanation: 20日价格变化率，衡量动量方向
data_fields_used: [close]
```

### TSA - 波动率因子（多行变量绑定）
```
engine_mode: ast
compute_engine: ComputeEngine.TSA
factor_code: |
  sd = Std($close, 20)
  ma = Mean($close, 20)
  Div(sd, Add(ma, 1e-6))
formula_explanation: 20日变异系数，标准化波动率
data_fields_used: [close]
```

### TSA - 均线交叉信号（多行变量绑定）
```
engine_mode: ast
compute_engine: ComputeEngine.TSA
factor_code: |
  ema5 = EMA($close, 5)
  ema20 = EMA($close, 20)
  Gt(ema5, ema20)
formula_explanation: 短期EMA是否大于长期EMA，判断趋势方向
data_fields_used: [close]
```

### CSA - 相对波动率排名（多行变量绑定）
```
engine_mode: ast
compute_engine: ComputeEngine.CSA
factor_code: |
  sd = Std($close, 20)
  ma = Mean($close, 20)
  cv = Div(sd, Add(ma, 1e-6))
  CSRank(cv)
formula_explanation: 截面排名的变异系数，识别相对波动最大的标的
data_fields_used: [close]
```

### CSA - 截面动量（多行变量绑定）
```
engine_mode: ast
compute_engine: ComputeEngine.CSA
factor_code: |
  mom = Sub($close, Ref($close, 20))
  sd = Std($close, 20)
  CSRank(Div(mom, Add(sd, 1e-6)))
formula_explanation: 标准化20日动量的截面排名
data_fields_used: [close]
```

### CSA - 量价因子（多行变量绑定 + 变量复用）
```
engine_mode: ast
compute_engine: ComputeEngine.CSA
factor_code: |
  vol_ma = Mean($vol, 20)
  vol_ratio = Div($vol, Add(vol_ma, 1e-6))
  bias = TSBias($close, 20)
  CSRank(Mul(bias, vol_ratio))
formula_explanation: 乖离率与量比的截面排名交叉因子
data_fields_used: [close, vol]
```

## 错误示例（避免）

```yaml
# 下划线命名（应用 Mean）
factor_code: TS_Mean($close, 20)

# 缺少前缀（应用 TSRoc）
factor_code: ROC($close, 20)

# TSA 中使用了 CS 算子
factor_code: CSRank($close)  # TSA 禁止 CS 算子

# 自创算子名（应用 Ref）
factor_code: TS_Delay($close, 5)

# 嵌套过深，不使用变量绑定（可读性差）
factor_code: Div(Sub(Mean($close,10),Mean($close,30)),Add(Std($close,20),1e-6))
```

## 自检清单

- [ ] 算子是否存在于 `cf.get_operators()` 返回列表
- [ ] 参数是否符合算子 desc 中的签名约束
- [ ] TSA 因子是否包含 `CS*` 算子（禁止）
- [ ] 是否出现未来引用 `Ref($x, -k)`（k > 0）
- [ ] 是否通过 `cf.compute_factors` 试跑
- [ ] `engine_mode` 是否固定为 `ast`
- [ ] `compute_engine` 是否为 `ComputeEngine.TSA` 或 `ComputeEngine.CSA`
- [ ] 输出是否严格为 6 字段（无 factor_name）
- [ ] `factor_code` 是否使用多行变量绑定格式（3+ 算子嵌套时必须）
- [ ] 变量名是否有语义（避免 `v1`/`v2`，用 `ma`/`sd`/`ret` 等）
