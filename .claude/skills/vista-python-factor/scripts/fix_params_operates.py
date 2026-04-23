"""
TALIB 算子无参化配置模块

本模块定义固定参数的 TALIB 算子，通过参数空间搜索和聚类分析得到最具代表性的参数组合，
降低参数选择复杂性，提高因子稳健性。

基于: examples/zengbin/TALIB算子无参化.md
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FixedOperator(BaseModel):
    """
    固定参数算子配置模型

    用于定义经过无参化处理的 TALIB 算子，包含算子名称、描述、使用示例和分类标签。

    Attributes:
        name: 算子唯一标识，如 "ADX001"、"APO002"
        desc: 算子描述，如 "平均趋向指数-5日周期"
        code: 计算代码示例，展示如何使用该算子
        tags: 算子标签列表，用于分类和检索，如 ["时序", "趋势", "短期"]
    """

    name: str = Field(..., min_length=1, description="算子唯一标识")
    desc: str = Field(..., description="算子描述")
    code: str = Field(..., description="计算代码示例")
    tags: list[str] = Field(default_factory=list, description="算子标签")

    def model_post_init(self, __context: Any) -> None:
        """模型初始化后处理，确保标签去重"""
        if self.tags:
            object.__setattr__(self, "tags", list(set(self.tags)))

    def to_dict(self, keys: list[str] | None = None) -> dict:
        """
        转换为字典表示，支持选择性字段输出

        Args:
            keys: 可选，指定要包含的字段列表。如果为 None，返回所有字段

        Returns:
            dict: 包含指定字段的字典

        Examples:
            >>> op = FixedOperator(name="TEST001", desc="测试", code="print('test')", tags=["测试"])
            >>> op.to_dict()
            {'name': 'TEST001', 'desc': '测试', 'code': "print('test')", 'tags': ['测试']}
            >>> op.to_dict(keys=['name', 'desc'])
            {'name': 'TEST001', 'desc': '测试'}
        """
        data = self.model_dump()
        if keys:
            return {k: data[k] for k in keys if k in data}
        return data


# ============================================================================
# ADX (Average Directional Index) - 平均趋向指数
# ============================================================================

ADX_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="ADX001",
        desc="平均趋向指数-超短期(5日),衡量趋势强度",
        code="df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=5)",
        tags=["时序", "趋势", "超短期", "动量"],
    ),
    FixedOperator(
        name="ADX002",
        desc="平均趋向指数-短期(21日),衡量趋势强度",
        code="df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=21)",
        tags=["时序", "趋势", "短期", "动量"],
    ),
    FixedOperator(
        name="ADX003",
        desc="平均趋向指数-中期(55日),衡量趋势强度",
        code="df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=55)",
        tags=["时序", "趋势", "中期", "动量"],
    ),
    FixedOperator(
        name="ADX004",
        desc="平均趋向指数-长期(144日),衡量趋势强度",
        code="df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=144)",
        tags=["时序", "趋势", "长期", "动量"],
    ),
    FixedOperator(
        name="ADX005",
        desc="平均趋向指数-超长期(233日),衡量趋势强度",
        code="df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=233)",
        tags=["时序", "趋势", "超长期", "动量"],
    ),
]


# ============================================================================
# APO (Absolute Price Oscillator) - 绝对价格振荡器
# ============================================================================

APO_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="APO001",
        desc="绝对价格振荡器-快21慢144,中长周期动量",
        code="df['apo'] = talib.APO(df['close'], fastperiod=21, slowperiod=144, matype=0)",
        tags=["时序", "动量", "震荡", "中长周期"],
    ),
    FixedOperator(
        name="APO002",
        desc="绝对价格振荡器-快89慢144,长周期动量",
        code="df['apo'] = talib.APO(df['close'], fastperiod=89, slowperiod=144, matype=0)",
        tags=["时序", "动量", "震荡", "长周期"],
    ),
    FixedOperator(
        name="APO003",
        desc="绝对价格振荡器-快21慢89,中周期动量",
        code="df['apo'] = talib.APO(df['close'], fastperiod=21, slowperiod=89, matype=0)",
        tags=["时序", "动量", "震荡", "中周期"],
    ),
    FixedOperator(
        name="APO004",
        desc="绝对价格振荡器-快55慢144,中长期周期动量",
        code="df['apo'] = talib.APO(df['close'], fastperiod=55, slowperiod=144, matype=0)",
        tags=["时序", "动量", "震荡", "中长期"],
    ),
    FixedOperator(
        name="APO005",
        desc="绝对价格振荡器-快5慢55,短中期周期动量",
        code="df['apo'] = talib.APO(df['close'], fastperiod=5, slowperiod=55, matype=0)",
        tags=["时序", "动量", "震荡", "短中期"],
    ),
]


# ============================================================================
# CCI (Commodity Channel Index) - 商品通道指数
# ============================================================================

CCI_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="CCI001",
        desc="商品通道指数-14日,衡量价格偏离统计平均值程度",
        code="df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)",
        tags=["时序", "震荡", "超短期", "超买超卖"],
    ),
    FixedOperator(
        name="CCI002",
        desc="商品通道指数-34日,衡量价格偏离统计平均值程度",
        code="df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=34)",
        tags=["时序", "震荡", "短期", "超买超卖"],
    ),
    FixedOperator(
        name="CCI003",
        desc="商品通道指数-89日,衡量价格偏离统计平均值程度",
        code="df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=89)",
        tags=["时序", "震荡", "中期", "超买超卖"],
    ),
    FixedOperator(
        name="CCI004",
        desc="商品通道指数-144日,衡量价格偏离统计平均值程度",
        code="df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=144)",
        tags=["时序", "震荡", "长期", "超买超卖"],
    ),
    FixedOperator(
        name="CCI005",
        desc="商品通道指数-233日,衡量价格偏离统计平均值程度",
        code="df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=233)",
        tags=["时序", "震荡", "超长期", "超买超卖"],
    ),
]


# ============================================================================
# MACD (Moving Average Convergence Divergence) - 异同移动平均线
# ============================================================================

MACD_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="MACD001",
        desc="异同移动平均线-快12慢26信号9,标准参数",
        code='"""macd, signal, hist = talib.MACD(df[\'close\'], fastperiod=12, slowperiod=26, signalperiod=9); df[\'macd\'] = macd"""',
        tags=["时序", "趋势", "动量", "标准"],
    ),
    FixedOperator(
        name="MACD002",
        desc="异同移动平均线-快89慢233信号9,长周期",
        code='"""macd, signal, hist = talib.MACD(df[\'close\'], fastperiod=89, slowperiod=233, signalperiod=9); df[\'macd\'] = macd"""',
        tags=["时序", "趋势", "动量", "长周期"],
    ),
    FixedOperator(
        name="MACD003",
        desc="异同移动平均线-快5慢55信号9,短中期",
        code='"""macd, signal, hist = talib.MACD(df[\'close\'], fastperiod=5, slowperiod=55, signalperiod=9); df[\'macd\'] = macd"""',
        tags=["时序", "趋势", "动量", "短中期"],
    ),
    FixedOperator(
        name="MACD004",
        desc="异同移动平均线-快55慢233信号9,中长期",
        code='"""macd, signal, hist = talib.MACD(df[\'close\'], fastperiod=55, slowperiod=233, signalperiod=9); df[\'macd\'] = macd"""',
        tags=["时序", "趋势", "动量", "中长期"],
    ),
    FixedOperator(
        name="MACD005",
        desc="异同移动平均线-快13慢89信号9,中长期",
        code='"""macd, signal, hist = talib.MACD(df[\'close\'], fastperiod=13, slowperiod=89, signalperiod=9); df[\'macd\'] = macd"""',
        tags=["时序", "趋势", "动量", "中长期"],
    ),
]


# ============================================================================
# RSI (Relative Strength Index) - 相对强弱指数
# ============================================================================

RSI_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="RSI001",
        desc="相对强弱指数-13日,衡量价格变动速度和变化",
        code="df['rsi001'] = talib.RSI(df['close'], timeperiod=13)",
        tags=["时序", "动量", "超短期", "超买超卖"],
    ),
    FixedOperator(
        name="RSI002",
        desc="相对强弱指数-34日,衡量价格变动速度和变化",
        code="df['rsi002'] = talib.RSI(df['close'], timeperiod=34)",
        tags=["时序", "动量", "短期", "超买超卖"],
    ),
    FixedOperator(
        name="RSI003",
        desc="相对强弱指数-89日,衡量价格变动速度和变化",
        code="df['rsi003'] = talib.RSI(df['close'], timeperiod=89)",
        tags=["时序", "动量", "中期", "超买超卖"],
    ),
    FixedOperator(
        name="RSI004",
        desc="相对强弱指数-144日,衡量价格变动速度和变化",
        code="df['rsi004'] = talib.RSI(df['close'], timeperiod=144)",
        tags=["时序", "动量", "长期", "超买超卖"],
    ),
    FixedOperator(
        name="RSI005",
        desc="相对强弱指数-233日,衡量价格变动速度和变化",
        code="df['rsi005'] = talib.RSI(df['close'], timeperiod=233)",
        tags=["时序", "动量", "超长期", "超买超卖"],
    ),
]


# ============================================================================
# ATR (Average True Range) - 平均真实波动范围
# ============================================================================

ATR_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="ATR001",
        desc="平均真实波动范围-13日,衡量市场波动性",
        code="df['atr13'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=13)",
        tags=["时序", "波动率", "超短期"],
    ),
    FixedOperator(
        name="ATR002",
        desc="平均真实波动范围-21日,衡量市场波动性",
        code="df['atr21'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=21)",
        tags=["时序", "波动率", "短期"],
    ),
    FixedOperator(
        name="ATR003",
        desc="平均真实波动范围-55日,衡量市场波动性",
        code="df['atr55'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=55)",
        tags=["时序", "波动率", "中期"],
    ),
]


# ============================================================================
# MOM (Momentum) - 动量指标
# ============================================================================

MOM_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="MOM001",
        desc="动量指标-8日,衡量x变量当前与8周期前的变化比例",
        code="df['mom001'] = talib.MOM(df['x'], timeperiod=8)",
        tags=["时序", "动量", "超短期"],
    ),
    FixedOperator(
        name="MOM002",
        desc="动量指标-21日,衡量x变量当前与21周期前的变化比例",
        code="df['mom002'] = talib.MOM(df['x'], timeperiod=21)",
        tags=["时序", "动量", "短期"],
    ),
    FixedOperator(
        name="MOM003",
        desc="动量指标-89日,衡量x变量当前与89周期前的变化比例",
        code="df['mom003'] = talib.MOM(df['x'], timeperiod=89)",
        tags=["时序", "动量", "中期"],
    ),
    FixedOperator(
        name="MOM004",
        desc="动量指标-144日,衡量x变量当前与144周期前的变化比例",
        code="df['mom004'] = talib.MOM(df['x'], timeperiod=144)",
        tags=["时序", "动量", "长期"],
    ),
    FixedOperator(
        name="MOM005",
        desc="动量指标-233日,衡量x变量当前与233周期前的变化比例",
        code="df['mom005'] = talib.MOM(df['x'], timeperiod=233)",
        tags=["时序", "动量", "超长期"],
    ),
]


# ============================================================================
# BBANDS (Bollinger Bands) - 布林带
# ============================================================================

BBANDS_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="BBANDS001",
        desc="布林带-13日±1.5倍标准差,动态交易通道",
        code="\"\"\"upper, middle, lower = talib.BBANDS(df['close'], timeperiod=13, nbdevup=1.5, nbdevdn=1.5, matype=0); df['bbands_pctb'] = (df['close'] - lower) / (upper - lower)\"\"\"",
        tags=["时序", "波动率", "超短期", "震荡"],
    ),
    FixedOperator(
        name="BBANDS002",
        desc="布林带-21日±1.5倍标准差,动态交易通道",
        code="\"\"\"upper, middle, lower = talib.BBANDS(df['close'], timeperiod=21, nbdevup=1.5, nbdevdn=1.5, matype=0); df['bbands_pctb'] = (df['close'] - lower) / (upper - lower)\"\"\"",
        tags=["时序", "波动率", "短期", "震荡"],
    ),
    FixedOperator(
        name="BBANDS003",
        desc="布林带-34日±1.5倍标准差,动态交易通道",
        code="\"\"\"upper, middle, lower = talib.BBANDS(df['close'], timeperiod=34, nbdevup=1.5, nbdevdn=1.5, matype=0); df['bbands_pctb'] = (df['close'] - lower) / (upper - lower)\"\"\"",
        tags=["时序", "波动率", "中期", "震荡"],
    ),
    FixedOperator(
        name="BBANDS004",
        desc="布林带-55日±1.5倍标准差,动态交易通道",
        code="\"\"\"upper, middle, lower = talib.BBANDS(df['close'], timeperiod=55, nbdevup=1.5, nbdevdn=1.5, matype=0); df['bbands_pctb'] = (df['close'] - lower) / (upper - lower)\"\"\"",
        tags=["时序", "波动率", "长期", "震荡"],
    ),
    FixedOperator(
        name="BBANDS005",
        desc="布林带-89日±1.5倍标准差,动态交易通道",
        code="\"\"\"upper, middle, lower = talib.BBANDS(df['close'], timeperiod=89, nbdevup=1.5, nbdevdn=1.5, matype=0); df['bbands_pctb'] = (df['close'] - lower) / (upper - lower)\"\"\"",
        tags=["时序", "波动率", "超长期", "震荡"],
    ),
]


# ============================================================================
# PLUS_DI - 正向方向指标
# ============================================================================

PLUS_DI_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="PLUS_DI001",
        desc="正向方向指标-8日,反映上涨方向强度",
        code="df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=8)",
        tags=["时序", "趋势", "超短期", "动量"],
    ),
    FixedOperator(
        name="PLUS_DI002",
        desc="正向方向指标-21日,反映上涨方向强度",
        code="df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=21)",
        tags=["时序", "趋势", "短期", "动量"],
    ),
    FixedOperator(
        name="PLUS_DI003",
        desc="正向方向指标-89日,反映上涨方向强度",
        code="df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=89)",
        tags=["时序", "趋势", "中期", "动量"],
    ),
    FixedOperator(
        name="PLUS_DI004",
        desc="正向方向指标-144日,反映上涨方向强度",
        code="df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=144)",
        tags=["时序", "趋势", "长期", "动量"],
    ),
    FixedOperator(
        name="PLUS_DI005",
        desc="正向方向指标-233日,反映上涨方向强度",
        code="df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=233)",
        tags=["时序", "趋势", "超长期", "动量"],
    ),
]


# ============================================================================
# MINUS_DI - 负向方向指标
# ============================================================================

MINUS_DI_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="MINUS_DI001",
        desc="负向方向指标-13日,反映下跌方向强度",
        code="df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=13)",
        tags=["时序", "趋势", "超短期", "动量"],
    ),
    FixedOperator(
        name="MINUS_DI002",
        desc="负向方向指标-34日,反映下跌方向强度",
        code="df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=34)",
        tags=["时序", "趋势", "短期", "动量"],
    ),
    FixedOperator(
        name="MINUS_DI003",
        desc="负向方向指标-89日,反映下跌方向强度",
        code="df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=89)",
        tags=["时序", "趋势", "中期", "动量"],
    ),
    FixedOperator(
        name="MINUS_DI004",
        desc="负向方向指标-144日,反映下跌方向强度",
        code="df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=144)",
        tags=["时序", "趋势", "长期", "动量"],
    ),
    FixedOperator(
        name="MINUS_DI005",
        desc="负向方向指标-233日,反映下跌方向强度",
        code="df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=233)",
        tags=["时序", "趋势", "超长期", "动量"],
    ),
]


# ============================================================================
# PLUS_DM - 正向方向移动
# ============================================================================

PLUS_DM_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="PLUS_DM001",
        desc="正向方向移动-8日,反映价格上涨幅度",
        code="df['plus_dm'] = talib.PLUS_DM(df['high'], df['low'], timeperiod=8)",
        tags=["时序", "动量", "超短期"],
    ),
    FixedOperator(
        name="PLUS_DM002",
        desc="正向方向移动-21日,反映价格上涨幅度",
        code="df['plus_dm'] = talib.PLUS_DM(df['high'], df['low'], timeperiod=21)",
        tags=["时序", "动量", "短期"],
    ),
    FixedOperator(
        name="PLUS_DM003",
        desc="正向方向移动-89日,反映价格上涨幅度",
        code="df['plus_dm'] = talib.PLUS_DM(df['high'], df['low'], timeperiod=89)",
        tags=["时序", "动量", "中期"],
    ),
    FixedOperator(
        name="PLUS_DM004",
        desc="正向方向移动-144日,反映价格上涨幅度",
        code="df['plus_dm'] = talib.PLUS_DM(df['high'], df['low'], timeperiod=144)",
        tags=["时序", "动量", "长期"],
    ),
    FixedOperator(
        name="PLUS_DM005",
        desc="正向方向移动-233日,反映价格上涨幅度",
        code="df['plus_dm'] = talib.PLUS_DM(df['high'], df['low'], timeperiod=233)",
        tags=["时序", "动量", "超长期"],
    ),
]


# ============================================================================
# MINUS_DM - 负向方向移动
# ============================================================================

MINUS_DM_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="MINUS_DM001",
        desc="负向方向移动-13日,反映价格下跌幅度",
        code="df['minus_dm'] = talib.MINUS_DM(df['high'], df['low'], timeperiod=13)",
        tags=["时序", "动量", "超短期"],
    ),
    FixedOperator(
        name="MINUS_DM002",
        desc="负向方向移动-34日,反映价格下跌幅度",
        code="df['minus_dm'] = talib.MINUS_DM(df['high'], df['low'], timeperiod=34)",
        tags=["时序", "动量", "短期"],
    ),
    FixedOperator(
        name="MINUS_DM003",
        desc="负向方向移动-89日,反映价格下跌幅度",
        code="df['minus_dm'] = talib.MINUS_DM(df['high'], df['low'], timeperiod=89)",
        tags=["时序", "动量", "中期"],
    ),
    FixedOperator(
        name="MINUS_DM004",
        desc="负向方向移动-144日,反映价格下跌幅度",
        code="df['minus_dm'] = talib.MINUS_DM(df['high'], df['low'], timeperiod=144)",
        tags=["时序", "动量", "长期"],
    ),
    FixedOperator(
        name="MINUS_DM005",
        desc="负向方向移动-233日,反映价格下跌幅度",
        code="df['minus_dm'] = talib.MINUS_DM(df['high'], df['low'], timeperiod=233)",
        tags=["时序", "动量", "超长期"],
    ),
]


# ============================================================================
# BETA - 贝塔系数
# ============================================================================

BETA_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="BETA001",
        desc="贝塔系数-34日,衡量资产相对市场波动敏感性",
        code="df['beta'] = talib.BETA(df['high'], df['low'], timeperiod=34)",
        tags=["时序", "统计", "短期"],
    ),
    FixedOperator(
        name="BETA002",
        desc="贝塔系数-55日,衡量资产相对市场波动敏感性",
        code="df['beta'] = talib.BETA(df['high'], df['low'], timeperiod=55)",
        tags=["时序", "统计", "中期"],
    ),
    FixedOperator(
        name="BETA003",
        desc="贝塔系数-89日,衡量资产相对市场波动敏感性",
        code="df['beta'] = talib.BETA(df['high'], df['low'], timeperiod=89)",
        tags=["时序", "统计", "中期"],
    ),
    FixedOperator(
        name="BETA004",
        desc="贝塔系数-144日,衡量资产相对市场波动敏感性",
        code="df['beta'] = talib.BETA(df['high'], df['low'], timeperiod=144)",
        tags=["时序", "统计", "长期"],
    ),
    FixedOperator(
        name="BETA005",
        desc="贝塔系数-233日,衡量资产相对市场波动敏感性",
        code="df['beta'] = talib.BETA(df['high'], df['low'], timeperiod=233)",
        tags=["时序", "统计", "超长期"],
    ),
]


# ============================================================================
# CORREL - 皮尔逊相关系数
# ============================================================================

CORREL_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="CORREL001",
        desc="相关系数-34日,衡量高低价线性相关程度",
        code="df['correl'] = talib.CORREL(df['high'], df['low'], timeperiod=34)",
        tags=["时序", "统计", "短期"],
    ),
    FixedOperator(
        name="CORREL002",
        desc="相关系数-55日,衡量高低价线性相关程度",
        code="df['correl'] = talib.CORREL(df['high'], df['low'], timeperiod=55)",
        tags=["时序", "统计", "中期"],
    ),
    FixedOperator(
        name="CORREL003",
        desc="相关系数-89日,衡量高低价线性相关程度",
        code="df['correl'] = talib.CORREL(df['high'], df['low'], timeperiod=89)",
        tags=["时序", "统计", "中期"],
    ),
    FixedOperator(
        name="CORREL004",
        desc="相关系数-144日,衡量高低价线性相关程度",
        code="df['correl'] = talib.CORREL(df['high'], df['low'], timeperiod=144)",
        tags=["时序", "统计", "长期"],
    ),
    FixedOperator(
        name="CORREL005",
        desc="相关系数-233日,衡量高低价线性相关程度",
        code="df['correl'] = talib.CORREL(df['high'], df['low'], timeperiod=233)",
        tags=["时序", "统计", "超长期"],
    ),
]


# ============================================================================
# SMA (Simple Moving Average) - 简单移动平均线
# ============================================================================

SMA_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="SMA001",
        desc="简单移动平均线-21日,平滑价格波动识别趋势",
        code="df['sma'] = talib.SMA(df['close'], timeperiod=21)",
        tags=["时序", "趋势", "短期", "均线"],
    ),
    FixedOperator(
        name="SMA002",
        desc="简单移动平均线-34日,平滑价格波动识别趋势",
        code="df['sma'] = talib.SMA(df['close'], timeperiod=34)",
        tags=["时序", "趋势", "中期", "均线"],
    ),
    FixedOperator(
        name="SMA003",
        desc="简单移动平均线-55日,平滑价格波动识别趋势",
        code="df['sma'] = talib.SMA(df['close'], timeperiod=55)",
        tags=["时序", "趋势", "中期", "均线"],
    ),
    FixedOperator(
        name="SMA004",
        desc="简单移动平均线-89日,平滑价格波动识别趋势",
        code="df['sma'] = talib.SMA(df['close'], timeperiod=89)",
        tags=["时序", "趋势", "长期", "均线"],
    ),
    FixedOperator(
        name="SMA005",
        desc="简单移动平均线-144日,平滑价格波动识别趋势",
        code="df['sma'] = talib.SMA(df['close'], timeperiod=144)",
        tags=["时序", "趋势", "超长期", "均线"],
    ),
]


# ============================================================================
# STOCH (Stochastic Oscillator) - 随机振荡器
# ============================================================================

STOCH_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="STOCH001",
        desc="随机振荡器-快K40慢K5慢D19,衡量收盘价相对位置",
        code="\"\"\"slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'], fastk_period=40, slowk_period=5, slowk_matype=0, slowd_period=19, slowd_matype=0); df['stoch_kd'] = slowk - slowd\"\"\"",
        tags=["时序", "震荡", "动量", "超买超卖"],
    ),
    FixedOperator(
        name="STOCH002",
        desc="随机振荡器-快K5慢K3慢D17,衡量收盘价相对位置",
        code="\"\"\"slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'], fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=17, slowd_matype=0); df['stoch_kd'] = slowk - slowd\"\"\"",
        tags=["时序", "震荡", "动量", "超买超卖"],
    ),
    FixedOperator(
        name="STOCH003",
        desc="随机振荡器-快K15慢K15慢D11,衡量收盘价相对位置",
        code="\"\"\"slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'], fastk_period=15, slowk_period=15, slowk_matype=0, slowd_period=11, slowd_matype=0); df['stoch_kd'] = slowk - slowd\"\"\"",
        tags=["时序", "震荡", "动量", "超买超卖"],
    ),
    FixedOperator(
        name="STOCH004",
        desc="随机振荡器-快K20慢K5慢D13,衡量收盘价相对位置",
        code="\"\"\"slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'], fastk_period=20, slowk_period=5, slowk_matype=0, slowd_period=13, slowd_matype=0); df['stoch_kd'] = slowk - slowd\"\"\"",
        tags=["时序", "震荡", "动量", "超买超卖"],
    ),
    FixedOperator(
        name="STOCH005",
        desc="随机振荡器-快K40慢K17慢D11,衡量收盘价相对位置",
        code="\"\"\"slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'], fastk_period=40, slowk_period=17, slowk_matype=0, slowd_period=11, slowd_matype=0); df['stoch_kd'] = slowk - slowd\"\"\"",
        tags=["时序", "震荡", "动量", "超买超卖"],
    ),
]


# ============================================================================
# SAR (Parabolic SAR) - 抛物线转向指标
# ============================================================================

SAR_OPERATORS: list[FixedOperator] = [
    FixedOperator(
        name="SAR001",
        desc="抛物线转向-加速0.055最大0.3,跟踪趋势并设置止损",
        code="df['sar'] = talib.SAR(df['high'], df['low'], acceleration=0.055, maximum=0.3)",
        tags=["时序", "趋势", "标准", "止损"],
    ),
    FixedOperator(
        name="SAR002",
        desc="抛物线转向-加速0.025最大0.2,慢速参数",
        code="df['sar'] = talib.SAR(df['high'], df['low'], acceleration=0.025, maximum=0.2)",
        tags=["时序", "趋势", "慢速", "止损"],
    ),
    FixedOperator(
        name="SAR003",
        desc="抛物线转向-加速0.005最大0.2,超慢速参数",
        code="df['sar'] = talib.SAR(df['high'], df['low'], acceleration=0.005, maximum=0.2)",
        tags=["时序", "趋势", "超慢速", "止损"],
    ),
    FixedOperator(
        name="SAR004",
        desc="抛物线转向-加速0.14最大0.3,快速参数",
        code="df['sar'] = talib.SAR(df['high'], df['low'], acceleration=0.14, maximum=0.3)",
        tags=["时序", "趋势", "快速", "止损"],
    ),
    FixedOperator(
        name="SAR005",
        desc="抛物线转向-加速0.135最大0.2,快速参数",
        code="df['sar'] = talib.SAR(df['high'], df['low'], acceleration=0.135, maximum=0.2)",
        tags=["时序", "趋势", "快速", "止损"],
    ),
]


# ============================================================================
# 导出接口
# ============================================================================

FIXED_OPERATORS: list[FixedOperator] = (
    ADX_OPERATORS
    + APO_OPERATORS
    + CCI_OPERATORS
    + MACD_OPERATORS
    + RSI_OPERATORS
    + ATR_OPERATORS
    + MOM_OPERATORS
    + BBANDS_OPERATORS
    + PLUS_DI_OPERATORS
    + MINUS_DI_OPERATORS
    + PLUS_DM_OPERATORS
    + MINUS_DM_OPERATORS
    + BETA_OPERATORS
    + CORREL_OPERATORS
    + SAR_OPERATORS
    + SMA_OPERATORS
    + STOCH_OPERATORS
)


def get_operator(name: str) -> FixedOperator | None:
    """
    根据算子名称获取算子配置

    Args:
        name: 算子名称，如 "ADX001"、"APO002"

    Returns:
        FixedOperator: 算子配置对象，如果未找到则返回 None

    Examples:
        >>> op = get_operator("ADX001")
        >>> assert op.name == "ADX001"
        >>> print(op.code)
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=5)
    """
    for op in FIXED_OPERATORS:
        if op.name == name:
            return op
    return None


def get_operators_by_tag(tag: str) -> list[FixedOperator]:
    """
    根据标签获取算子列表

    Args:
        tag: 算子标签，如 "趋势"、"动量"、"短期"

    Returns:
        List[FixedOperator]: 包含该标签的所有算子

    Examples:
        >>> ops = get_operators_by_tag("趋势")
        >>> len(ops) > 0
        True
    """
    return [op for op in FIXED_OPERATORS if tag in op.tags]


def get_all_operator_names() -> list[str]:
    """
    获取所有算子名称列表

    Returns:
        List[str]: 所有算子的名称列表

    Examples:
        >>> names = get_all_operator_names()
        >>> "ADX001" in names
        True
        >>> "APO001" in names
        True
    """
    return [op.name for op in FIXED_OPERATORS]


def get_operators_by_prefix(prefix: str) -> list[FixedOperator]:
    """
    根据名称前缀获取算子列表

    Args:
        prefix: 算子名称前缀，如 "ADX"、"APO"

    Returns:
        List[FixedOperator]: 匹配前缀的所有算子

    Examples:
        >>> ops = get_operators_by_prefix("ADX")
        >>> len(ops) == 5
        True
    """
    return [op for op in FIXED_OPERATORS if op.name.startswith(prefix)]


__all__ = [
    "FixedOperator",
    "ADX_OPERATORS",
    "APO_OPERATORS",
    "CCI_OPERATORS",
    "MACD_OPERATORS",
    "RSI_OPERATORS",
    "ATR_OPERATORS",
    "MOM_OPERATORS",
    "BBANDS_OPERATORS",
    "PLUS_DI_OPERATORS",
    "MINUS_DI_OPERATORS",
    "PLUS_DM_OPERATORS",
    "MINUS_DM_OPERATORS",
    "BETA_OPERATORS",
    "CORREL_OPERATORS",
    "SAR_OPERATORS",
    "SMA_OPERATORS",
    "STOCH_OPERATORS",
    "FIXED_OPERATORS",
    "get_operator",
    "get_operators_by_tag",
    "get_all_operator_names",
    "get_operators_by_prefix",
]
