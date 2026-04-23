---
name: vista-python-factor
description: Python 因子构建器（合并自 vista-cs-factor-generator 和 vista-ts-factor-generator）。专门用于使用纯 Python 函数编写的量价因子，覆盖 TimeSeriesEngine（时序）/CrossSectionEngine（截面）/EventDrivenEngine（事件驱动）/FreedomEngine（自由）四个 Vista 因子计算引擎。使用场景：用户请求"生成时序因子"、"生成截面因子"、"生成事件因子"、"用 Python 写一个因子"、"自定义因子计算流程"时；不涉及 chan_factor_rs 表达式因子（请改用 vista-ast-factor）。
---

# Vista Python Factor

合并自 `vista-cs-factor-generator` + `vista-ts-factor-generator`，统一覆盖 Vista 全部 Python 类因子计算引擎。算子代码已物理迁移到本 SKILL `scripts/`，作为唯一事实来源。

## 适用引擎

| 引擎 | 类型 | 数据视角 | 用途 |
|------|------|---------|------|
| **TimeSeriesEngine** (TSE) | 时序 | 单标的时间序列 | 趋势/动量/波动率/成交量等技术因子 |
| **CrossSectionEngine** (CSE) | 截面 | 同一时刻多标的横切 | 排名/标准化/分组比较/中性化 |
| **EventDrivenEngine** (EDE) | 事件 | 信号点 | 突破/跳空/放量/极端波动等事件信号 |
| **FreedomEngine** (FRE) | 自由 | 用户自定义 | 灵活拼接数据/计算流程，支持外部数据接入 |

四个引擎的因子代码均使用纯 Python 函数 `def factor_name(df, **kwargs) -> df` 编写。

## 标准工作流

1. **选择目标引擎** —— 参考 [`references/engines.md`](references/engines.md)
2. **挑选算子组合**（可选）

   ```bash
   uv run python .claude/skills/vista-python-factor/scripts/get_operators.py --type ts --num 10
   uv run python .claude/skills/vista-python-factor/scripts/get_operators.py --type ts --tag 趋势 --num 5
   uv run python .claude/skills/vista-python-factor/scripts/get_operators.py --type cs --num 10
   uv run python .claude/skills/vista-python-factor/scripts/get_operators.py --type cs --list
   ```

3. **编写因子代码** —— 严格遵循 [`references/coding-standards.md`](references/coding-standards.md) 与 [`references/factor-principles.md`](references/factor-principles.md)。
   - 时序示例：[`references/examples-ts.md`](references/examples-ts.md)
   - 截面示例：[`references/examples-cs.md`](references/examples-cs.md)
   - 事件示例 + 算子模板：[`references/examples-event.md`](references/examples-event.md) / [`references/operators-events.md`](references/operators-events.md)
   - Freedom 示例 + tushare 集成：[`references/freedom-engine.md`](references/freedom-engine.md)

4. **代码验证**

   ```bash
   uv run python .claude/skills/vista-python-factor/scripts/validate_factor.py my_factor.py --type ts
   uv run python .claude/skills/vista-python-factor/scripts/validate_factor.py my_factor.py --type cs
   ```

5. **生成正式因子名 + 落库**

   ```python
   from vista.engines.base import update_factor_name
   from vista.factor_db.models import FactorDescribe, ComputeEngine

   raw = FactorDescribe(
       factor_name="placeholder",      # 占位即可
       factor_code=factor_code,
       compute_engine=ComputeEngine.TSE,
       description="...",
   )
   factor = update_factor_name(raw)    # → TSE_260406_A3B7F9
   ```

   > ⚠️ 不要再手动生成因子名（旧版的 `create_factor_name.py` 已废弃删除）。

## 算子库（物理位置）

`scripts/` 目录包含算子代码本身，**唯一事实来源**：

| 文件 | 内容 |
|------|------|
| [`scripts/operates.py`](scripts/operates.py) | TA-Lib 算子注册表 + 自定义算子注册表 + 工具函数 |
| [`scripts/cs_operators.py`](scripts/cs_operators.py) | 横截面算子函数实现（rank/zscore/group_*/winsorize/scale/neutralize 等） |
| [`scripts/fix_params_operates.py`](scripts/fix_params_operates.py) | 固定参数（预优化）TA-Lib 算子集，附标签和编号 |

> ⚠️ 这些文件**不再被 vista 包 import**，也**不要在因子代码内 `from vista.cs_operators import *`**。需要使用其中的算法时，请直接将算法**内联实现**或调用 numpy/pandas/talib。

## 工具脚本（共 5 个）

| 脚本 | 用途 |
|------|------|
| `scripts/operates.py` / `cs_operators.py` / `fix_params_operates.py` | 算子代码本身（可被 import 也可被读取） |
| `scripts/get_operators.py` | 统一算子获取（`--type ts/cs`，支持 `--tag/--prefix/--list`） |
| `scripts/validate_factor.py` | 统一因子代码校验（`--type ts/cs`） |

## 数据字段

可用 K 线字段：见 [`references/data-fields.md`](references/data-fields.md)
- 必备：`dt`, `symbol`, `open`, `high`, `low`, `close`, `vol`, `amount`
- 可选：`market_cap`, `pe_ratio`, `oi`（期货持仓量）等

## 与 vista-ast-factor 的区别

| 维度 | vista-python-factor（本 SKILL） | vista-ast-factor |
|------|--------------------------------|------------------|
| 因子载体 | Python 函数字符串 (`factor_code`) | 表达式字符串 (`"ts_mean(close, 20)"`) |
| 引擎 | TSE / CSE / EDE / Freedom | TimeSeriesAstEngine / CrossSectionAstEngine |
| 算子来源 | 本 skill `scripts/` + TA-Lib | `chan_factor_rs.get_operators()` |
| 适用场景 | 复杂逻辑/多步计算/外部数据 | 简洁表达式/批量挖掘 |

## 输出约定

生成的因子必须：
1. ✅ 函数签名：`def factor_name(df, **kwargs)`
2. ✅ 输出列：`F#{factor_name}#DEFAULT`
3. ✅ 处理 NaN/Inf
4. ✅ 包含文档字符串
5. ✅ 时序因子：通过未来信息泄露检查（`validate_factor.py --type ts`）
6. ✅ 截面因子：MultiIndex (dt, symbol) 正确，`groupby('dt')` 正确，`sort_index()` 返回
7. ✅ 事件因子：信号列为 0/1（或 -1/0/1）整数，无前视
8. ✅ 因子名由 `vista.engines.base.update_factor_name` 自动生成
