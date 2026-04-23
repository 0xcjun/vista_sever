from __future__ import annotations

talib_ops = [
    # Talib 算子列表：https://docsinchinese.gitbooks.io/talib/content/
    {
        "算子名称": "ATR",
        "算子描述": "Average True Range",
        "伪代码": """
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=timeperiod)
        """,
    },
    {
        # https://zhuanlan.zhihu.com/p/660588750
        "算子名称": "MAMA",
        "算子描述": "MESA Adaptive Moving Average",
        "伪代码": """
        df['mama'], df['fama'] = talib.MAMA(df['close'], fastlimit=0.5, slowlimit=0.05)
        """,
    },
    {
        "算子名称": "RSI",
        "算子描述": "Relative Strength Index, 相对强弱指数",
        "伪代码": """
        df['rsi'] = talib.RSI(df['series'], timeperiod=timeperiod)
        """,
    },
    {
        "算子名称": "AD",
        "算子描述": "Accumulation/Distribution Line, 累积/分配线",
        "伪代码": "df['ad'] = talib.AD(df['high'], df['low'], df['close'], df['vol'])",
    },
    {
        "算子名称": "ADOSC",
        "算子描述": "Accumulation/Distribution Oscillator, 累积/分配振荡器",
        "伪代码": "df['adosc'] = talib.ADOSC(df['high'], df['low'], df['close'], df['vol'], fastperiod=3, slowperiod=10)",
    },
    {
        "算子名称": "OBV",
        "算子描述": "On Balance Volume, 平衡成交量",
        "伪代码": "df['obv'] = talib.OBV(df['close'], df['vol'])",
    },
    {
        "算子名称": "MFI",
        "算子描述": "Money Flow Index, 资金流量指数",
        "伪代码": "df['mfi'] = talib.MFI(df['high'], df['low'], df['close'], df['vol'], timeperiod=14)",
    },
    {"算子名称": "MOM", "算子描述": "Momentum, 动量", "伪代码": "df['mom'] = talib.MOM(df['close'], timeperiod=10)"},
    {
        "算子名称": "ROC",
        "算子描述": "Rate of Change, 变化率",
        "伪代码": "df['roc'] = talib.ROC(df['close'], timeperiod=10)",
    },
    {
        "算子名称": "TRIX",
        "算子描述": "Triple Exponential Moving Average (TRIX), 三重指数平滑移动平均线",
        "伪代码": "df['trix'] = talib.TRIX(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "MACD",
        "算子描述": "Moving Average Convergence Divergence, 移动平均收敛散度",
        "伪代码": "df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)",
    },
    {
        "算子名称": "ADX",
        "算子描述": "Average Directional Movement Index, 平均方向指数",
        "伪代码": "df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)",
    },
    {
        "算子名称": "CCI",
        "算子描述": "Commodity Channel Index, 商品渠道指数",
        "伪代码": "df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)",
    },
    {
        "算子名称": "DX",
        "算子描述": "Directional Movement Index, 方向运动指数",
        "伪代码": "df['dx'] = talib.DX(df['high'], df['low'], df['close'], timeperiod=14)",
    },
    {
        "算子名称": "PLUS_DI",
        "算子描述": "Positive Directional Indicator, 正向方向指标",
        "伪代码": "df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=14)",
    },
    {
        "算子名称": "MINUS_DI",
        "算子描述": "Negative Directional Indicator, 负向方向指标",
        "伪代码": "df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=14)",
    },
    {
        "算子名称": "PLUS_DM",
        "算子描述": "Positive Directional Movement, 正向方向运动",
        "伪代码": "df['plus_dm'] = talib.PLUS_DM(df['high'], df['low'], timeperiod=14)",
    },
    {
        "算子名称": "MINUS_DM",
        "算子描述": "Negative Directional Movement, 负向方向运动",
        "伪代码": "df['minus_dm'] = talib.MINUS_DM(df['high'], df['low'], df['close'], timeperiod=14)",
    },
    {
        "算子名称": "TRANGE",
        "算子描述": "True Range, 真实范围",
        "伪代码": "df['trange'] = talib.TRANGE(df['high'], df['low'], df['close'])",
    },
    {
        "算子名称": "BETA",
        "算子描述": "Beta, 贝塔系数",
        "伪代码": "df['beta'] = talib.BETA(df['high'], df['low'], timeperiod=5)",
    },
    {
        "算子名称": "CORREL",
        "算子描述": "计算两个序列之间的相关系数",
        "伪代码": "df['correl'] = talib.CORREL(df['high'], df['low'], timeperiod=30)",
    },
    {
        "算子名称": "LINEARREG",
        "算子描述": "计算线性回归值",
        "伪代码": "df['linearreg'] = talib.LINEARREG(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "LINEARREG_ANGLE",
        "算子描述": "计算线性回归角度",
        "伪代码": "df['linearreg_angle'] = talib.LINEARREG_ANGLE(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "LINEARREG_INTERCEPT",
        "算子描述": "计算线性回归截距",
        "伪代码": "df['linearreg_intercept'] = talib.LINEARREG_INTERCEPT(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "LINEARREG_SLOPE",
        "算子描述": "计算线性回归斜率",
        "伪代码": "df['linearreg_slope'] = talib.LINEARREG_SLOPE(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "STDDEV",
        "算子描述": "计算标准差",
        "伪代码": "df['stddev'] = talib.STDDEV(df['close'], timeperiod=5)",
    },
    {"算子名称": "VAR", "算子描述": "计算方差", "伪代码": "df['var'] = talib.VAR(df['close'], timeperiod=5)"},
    {
        "算子名称": "BOP",
        "算子描述": "平衡量指标",
        "伪代码": "df['bop'] = talib.BOP(df['open'], df['high'], df['low'], df['close'])",
    },
    {
        "算子名称": "TRIMA",
        "算子描述": "三角移动平均线",
        "伪代码": "df['trima'] = talib.TRIMA(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "TEMA",
        "算子描述": "三重指数平滑移动平均线",
        "伪代码": "df['tema'] = talib.TEMA(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "BBANDS",
        "算子描述": "布林带指标，用于衡量价格的波动范围和趋势。",
        "伪代码": "upperband, middleband, lowerband = talib.BBANDS(df['close'], timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)",
    },
    {
        "算子名称": "SAR",
        "算子描述": "Parabolic SAR, 抛物线止损和反转指标",
        "伪代码": "df['sar'] = talib.SAR(df['high'], df['low'], acceleration=0.02, maximum=0.2)",
    },
    {
        "算子名称": "SAREXT",
        "算子描述": "Parabolic SAR - Extended, 扩展抛物线止损和反转指标",
        "伪代码": "df['sarext'] = talib.SAREXT(df['high'], df['low'])",
    },
    {
        "算子名称": "WMA",
        "算子描述": "Weighted Moving Average, 加权移动平均线",
        "伪代码": "df['wma'] = talib.WMA(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "DEMA",
        "算子描述": "Double Exponential Moving Average, 双指数移动平均线",
        "伪代码": "df['dema'] = talib.DEMA(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "KAMA",
        "算子描述": "Kaufman Adaptive Moving Average, 考夫曼自适应移动平均线",
        "伪代码": "df['kama'] = talib.KAMA(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "TRIMA",
        "算子描述": "Triangular Moving Average, 三角移动平均线",
        "伪代码": "df['trima'] = talib.TRIMA(df['close'], timeperiod=30)",
    },
    {
        "算子名称": "MIDPOINT",
        "算子描述": "MidPoint over period, 期间中点",
        "伪代码": "df['midpoint'] = talib.MIDPOINT(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "MIDPRICE",
        "算子描述": "Midpoint Price over period, 期间中点价格",
        "伪代码": "df['midprice'] = talib.MIDPRICE(df['high'], df['low'], timeperiod=14)",
    },
    {
        "算子名称": "TSF",
        "算子描述": "Time Series Forecast, 时间序列预测",
        "伪代码": "df['tsf'] = talib.TSF(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "BOP",
        "算子描述": "Balance of Power, 力量平衡指标",
        "伪代码": "df['bop'] = talib.BOP(df['open'], df['high'], df['low'], df['close'])",
    },
    {
        "算子名称": "APO",
        "算子描述": "Absolute Price Oscillator, 绝对价格振荡器",
        "伪代码": "df['apo'] = talib.APO(df['close'], fastperiod=12, slowperiod=26, matype=0)",
    },
    {
        "算子名称": "CMO",
        "算子描述": "Chande Momentum Oscillator, 钱德动量振荡器",
        "伪代码": "df['cmo'] = talib.CMO(df['close'], timeperiod=14)",
    },
    {
        "算子名称": "PPO",
        "算子描述": "Percentage Price Oscillator, 百分比价格振荡器",
        "伪代码": "df['ppo'] = talib.PPO(df['close'], fastperiod=12, slowperiod=26, matype=0)",
    },
    {
        "算子名称": "ROCP",
        "算子描述": "Rate of Change Percentage, 变化率百分比",
        "伪代码": "df['rocp'] = talib.ROCP(df['close'], timeperiod=10)",
    },
    {
        "算子名称": "ROCR",
        "算子描述": "Rate of Change Ratio, 变化率比率",
        "伪代码": "df['rocr'] = talib.ROCR(df['close'], timeperiod=10)",
    },
    {
        "算子名称": "AROON",
        "算子描述": "Aroon Indicator, 阿隆指标",
        "伪代码": "df['aroon'] = talib.AROON(df['high'], df['low'], timeperiod=14)",
    },
    {
        "算子名称": "AROONOSC",
        "算子描述": "Aroon Oscillator, 阿隆振荡器",
        "伪代码": "df['aroonosc'] = talib.AROONOSC(df['high'], df['low'], timeperiod=14)",
    },
    {
        "算子名称": "STOCH",
        "算子描述": "Stochastic Oscillator, 随机振荡器",
        "伪代码": "df['stoch'] = talib.STOCH(df['high'], df['low'], df['close'])",
    },
]


custom_ops = [
    # ZB自定义算子列表
    {"算子名称": "add", "算子描述": "加法", "伪代码": "df['x'] = df['series1'] + df['series2']"},
    {"算子名称": "sub", "算子描述": "减法", "伪代码": "df['x'] = df['series1'] - df['series2']"},
    {"算子名称": "mul", "算子描述": "乘法", "伪代码": "df['x'] = df['series1'] * df['series2']"},
    {
        "算子名称": "div",
        "算子描述": "除法",
        "伪代码": "df['x'] = df['series1'] / df['series2'].replace(0, np.nan)",
    },
    {
        "算子名称": "inv",
        "算子描述": "取倒数",
        "伪代码": "df['x'] = 1 / df['series'].replace(0, np.nan)",
    },
    {"算子名称": "rolling_sum", "算子描述": "时间序列求和", "伪代码": "df['sum'] = df['series'].rolling(window).sum()"},
    {
        "算子名称": "rolling_min",
        "算子描述": "时间序列最小值",
        "伪代码": "df['min'] = df['series'].rolling(window).min()",
    },
    {
        "算子名称": "rolling_max",
        "算子描述": "时间序列最大值",
        "伪代码": "df['max'] = df['series'].rolling(window).max()",
    },
    {
        "算子名称": "rolling_rank",
        "算子描述": "时间序列排名，必须结合 rolling 使用",
        "伪代码": "df['rank'] = df['series'].rolling(window).rank()",
    },
    {
        "算子名称": "rolling_rank_sub",
        "算子描述": "时间序列排名，必须结合 rolling 使用",
        "伪代码": "df['rolling_rank_sub'] = df['series1'].rolling(window).rank() - df['series2'].rolling(window).rank()",
    },
    {
        "算子名称": "rolling_rank_div",
        "算子描述": "时间序列排名，必须结合 rolling 使用",
        "伪代码": "df['rolling_rank_div'] = df['series1'].rolling(window).rank() / df['series2'].rolling(window).rank()",
    },
    {
        "算子名称": "ultimate_smoother",
        "算子描述": "终极平滑器，使用高通滤波器从价格曲线中减去高频成分",
        "伪代码": """
        import numpy as np

        def ultimate_smoother(price, period):
            # 初始化变量
            a1 = np.exp(-1.414 * np.pi / period)
            b1 = 2 * a1 * np.cos(1.414 * 180 / period)
            c2 = b1
            c3 = -a1 * a1
            c1 = (1 + c2 - c3) / 4

            # 准备输出结果的序列
            us = np.zeros(len(price))

            # 计算 Ultimate Smoother
            for i in range(len(price)):
                if i < 4:
                    us[i] = price[i]
                else:
                    us[i] = (1 - c1) * price[i] + (2 * c1 - c2) * price[i - 1] \
                            - (c1 + c3) * price[i - 2] + c2 * us[i - 1] + c3 * us[i - 2]

            return us

        df["UltimateSmoother"] = ultimate_smoother(df["close"].values, period)
        """,
    },
    {
        "算子名称": "double_sma",
        "算子描述": "双均线",
        "伪代码": """
        df['fast_sma'] = df['series'].rolling(window=fast).mean()
        df['slow_sma'] = df['series'].rolling(window=slow).mean()
        df['double_ema'] = df['fast_sma'] - df['slow_sma']
        """,
    },
    {
        "算子名称": "kdj",
        "算子描述": "随机指标",
        "伪代码": """
        df['min'] = df['series'].rolling(window_slow).min()
        df['max'] = df['series'].rolling(window_slow).max()
        df['rsv'] = (df['series'] - df['min']) / (df['max'] - df['min'])
        df['k'] = df['rsv'].ewm(com=window_kdj).mean()
        df['d'] = df['k'].ewm(com=window_kdj).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        """,
    },
    {
        "算子名称": "vwap",
        "算子描述": "成交量加权平均价格",
        "伪代码": """
        df['weighted_price'] = (df['series1'] * df['series2']).rolling(window=window).sum()
        df['series2_sum'] = df['series2'].rolling(window=window).sum()
        df['vwap'] = df['weighted_price'] / df['series2_sum'].replace(0, np.nan)
        """,
    },
    {
        "算子名称": "maximum",
        "算子描述": "取最大值",
        "伪代码": "df['maximum'] = np.maximum(df['series1'], df['series2'])",
    },
    {
        "算子名称": "minimum",
        "算子描述": "取最小值",
        "伪代码": "df['minimum'] = np.minimum(df['series1'], df['series2'])",
    },
    {
        "算子名称": "shift",
        "算子描述": "序列移动，shift 中不能是负数",
        "伪代码": "df['shifted'] = df['series'].shift(n)",
    },
    {"算子名称": "diff", "算子描述": "序列差分", "伪代码": "df['diff'] = df['series'].diff()"},
    {"算子名称": "log", "算子描述": "对数运算，使series更接近正态分布", "伪代码": "df['log'] = np.log(df['series'])"},
    {
        "算子名称": "log_return",
        "算子描述": "对数收益率, series 不能有nan值",
        "伪代码": "df['log_return'] = np.log(df['series'] / df['series'].shift(1))",
    },
    {"算子名称": "sqrt", "算子描述": "平方根运算", "伪代码": "df['sqrt'] = np.sqrt(df['series'])"},
    {"算子名称": "pow", "算子描述": "幂运算", "伪代码": "df['pow'] = np.power(df['series'], 2)"},
    {"算子名称": "kurt", "算子描述": "峰度", "伪代码": "df['kurt'] = df['series'].rolling(window).kurt()"},
    {"算子名称": "skew", "算子描述": "偏度", "伪代码": "df['skew'] = df['series'].rolling(window).skew()"},
    {
        "算子名称": "quantile",
        "算子描述": "分位数",
        "伪代码": "df['quantile'] = df['series'].rolling(window).quantile(0.5)",
    },
    {
        "算子名称": "kurt_diff",
        "算子描述": "峰度差",
        "伪代码": "df['kurt_diff'] = df['series'].rolling(window).kurt().diff()",
    },
    {
        "算子名称": "skew_diff",
        "算子描述": "偏度差",
        "伪代码": "df['skew_diff'] = df['series'].rolling(window).skew().diff()",
    },
    {
        "算子名称": "quantile_diff",
        "算子描述": "分位数差",
        "伪代码": "df['quantile_diff'] = df['series'].rolling(window).quantile(q).diff()",
    },
    {
        "算子名称": "median",
        "算子描述": "中位数",
        "伪代码": "df['median'] = df['series'].rolling(window=window).median()",
    },
    {
        "算子名称": "mode",
        "算子描述": "众数",
        "伪代码": "df['mode'] = df['series'].rolling(window=window).apply(lambda x: x.mode()[0], raw=False)",
    },
    {"算子名称": "var", "算子描述": "方差", "伪代码": "df['var'] = df['series'].rolling(window=window).var()"},
    {
        "算子名称": "cov",
        "算子描述": "协方差",
        "伪代码": "df['cov'] = df['series1'].rolling(window=window).cov(df['series2'])",
    },
    {
        "算子名称": "iv",
        "算子描述": "信息比率，一般用于计算策略的风险收益比，window 越大，计算结果越稳定",
        "伪代码": """
        df['mean'] = df['series'].rolling(window=window).mean()
        df['std'] = df['series'].rolling(window=window).std()
        df['iv'] = df['mean'] / df['std'].replace(0, np.nan)
        """,
    },
    {"算子名称": "abs", "算子描述": "绝对值", "伪代码": "df['abs'] = abs(df['series'])"},
    {"算子名称": "sign", "算子描述": "符号函数", "伪代码": "df['sign'] = np.sign(df['series'])"},
    {
        "算子名称": "rolling_argmax",
        "算子描述": "时间序列的局部最大值索引，必须结合 rolling 使用，window 可以视情况调整",
        "伪代码": "df['rolling_argmax'] = df['series'].rolling(window=window).apply(lambda x: np.argmax(x), raw=False)",
    },
    {
        "算子名称": "pct_change_sigmoid",
        "算子描述": "exp 被用于实现Sigmoid函数",
        "伪代码": """
        df['pct_change_sigmoid'] = 1 / (1 + np.exp(-df['series'].pct_change()))
        """,
    },
    {
        "算子名称": "ts_first_derivative",
        "算子描述": "时间序列的线性回归系数（一阶导数）",
        "伪代码": """
        import numpy as np
        first_derivative = lambda x: np.polyfit(range(len(x)), x, 1)[0]
        df['ts_first_derivative'] = df['series'].rolling(window=window).apply(first_derivative, raw=False)
        """,
    },
    {
        "算子名称": "ts_second_derivative",
        "算子描述": "时间序列的二阶导数",
        "伪代码": """
            import numpy as np
            second_derivative = lambda x: np.polyfit(range(len(x)), x, 2)[0]
            df['ts_second_derivative'] = df['series'].rolling(window=window).apply(second_derivative, raw=False)
        """,
    },
    {"算子名称": "sin", "算子描述": "正弦函数", "伪代码": "df['sin'] = np.sin(df['series'])"},
    {"算子名称": "cos", "算子描述": "余弦函数", "伪代码": "df['cos'] = np.cos(df['series'])"},
    {"算子名称": "tan", "算子描述": "正切函数", "伪代码": "df['tan'] = np.tan(df['series'])"},
    {
        "算子名称": "exp",
        "算子描述": "指数函数，容易发生溢出，不要对一个非常大的数求指数",
        "伪代码": "df['exp'] = np.exp(df['series'])",
    },
    {"算子名称": "tanh", "算子描述": "指数函数", "伪代码": "df['tanh'] = np.tanh(df['series'])"},
    {
        "算子名称": "snr",
        "算子描述": "趋势顺畅度，信噪比，在一个时间窗口内，序列的最后一个值和第一个值的绝对差值除以序列的绝对差值之和",
        "伪代码": """
        df['snr'] = df['series'].diff(window) / df['series'].diff().abs().rolling(window=window).sum()
        """,
    },
    {
        "算子名称": "rolling_gap",
        "算子描述": "最大最小值的宽度，在一个时间窗口内，序列的最大值和最小值的差",
        "伪代码": """
        df['rolling_gap'] = df['series'].rolling(window=window).apply(lambda x: np.max(x) - np.min(x), raw=False)
        """,
    },
    {
        "算子名称": "rolling_auto_corr",
        "算子描述": "自相关系数",
        "伪代码": """
        df['auto_corr'] = df['series'].rolling(window=window).apply(lambda x: x.autocorr(lag=1), raw=False)
        """,
    },
    {
        "算子名称": "rolling_rsquared",
        "算子描述": "单变量R平方值，用于衡量时间序列的线性相关性",
        "伪代码": """
        from scipy.stats import linregress
        r_squared = lambda x: linregress(range(len(x)), x).rvalue ** 2
        df['r_squared'] = df['series'].rolling(window=window).apply(r_squared, raw=False)
        """,
    },
    {
        "算子名称": "rolling_xy_rsquared",
        "算子描述": "XY回归R平方值，用于衡量两个时间序列的线性相关性",
        "伪代码": """
        # 注意：确保已经 import numpy as np, pandas as pd
        df['rolling_xy_rsquared'] = df['series1'].rolling(window=window, min_periods=window).corr(df['series2']) ** 2
        """,
    },
    {
        "算子名称": "bias",
        "算子描述": "乖离率，用于衡量series与均线的偏离程度",
        "伪代码": """
        df['ma'] = df['series'].rolling(window=window).mean()
        df['bias'] = (df['series'] - df['ma']) / df['ma'].replace(0, np.nan)
        """,
    },
    {
        "算子名称": "MAR",
        "算子描述": "单均线多空动量",
        "伪代码": """
        import pandas as pd

        def MAR(series: pd.Series, timeperiod: int = 20):
            x = series.rolling(window=timeperiod).mean()
            r = series.pct_change()
            # series 大于均线，返回1；小于均线，返回-1
            p = (series > x).astype(int) * 2 - 1
            m = (p.shift(1) * r).rolling(window=timeperiod).sum().fillna(0)
            return m
        """,
    },
]


# """
# winsorize	Cross Sectional	['COMBO', 'REGULAR']	winsorize(x, std=4)	Winsorizes x to make sure that all values in x are between the lower and upper limits, which are specified as multiple of std. Details can be found on wiki		ALL
# rank	Cross Sectional	['COMBO', 'REGULAR']	rank(x, rate=2)	Ranks the input among all the instruments and returns an equally distributed number between 0.0 and 1.0. For precise sort, use the rate as 0	/operators/rank	ALL
# regression_proj	Cross Sectional	['COMBO', 'REGULAR']	regression_proj(y, x)	Conducts the cross-sectional regression on the stocks with Y as target and X as the independent variable	/operators/regression_proj
# vector_neut	Cross Sectional	['COMBO', 'REGULAR']	vector_neut(x, y)	For given vectors x and y, it finds a new vector x* (output) such that x* is orthogonal to y	/operators/vector_neut
# regression_neut	Cross Sectional	['COMBO', 'REGULAR']	regression_neut(y, x)	Conducts the cross-sectional regression on the stocks with Y as target and X as the independent variable	/operators/regression_neut
# zscore	Cross Sectional	['COMBO', 'REGULAR']	zscore(x)	Z-score is a numerical measurement that describes a value's relationship to the mean of a group of values. Z-score is measured in terms of standard deviations from the mean	/operators/zscore	ALL
# scale_down	Cross Sectional	['COMBO', 'REGULAR']	scale_down(x,constant=0)	Scales all values in each day proportionately between 0 and 1 such that minimum value maps to 0 and maximum value maps to 1. Constant is the offset by which final result is subtracted	/operators/scale_down
# truncate	Cross Sectional	['COMBO', 'REGULAR']	truncate(x,maxPercent=0.01)	Operator truncates all values of x to maxPercent. Here, maxPercent is in decimal notation	/operators/truncate
# scale	Cross Sectional	['COMBO', 'REGULAR']	scale(x, scale=1, longscale=1, shortscale=1)	Scales input to booksize. We can also scale the long positions and short positions to separate scales by mentioning additional parameters to the operator	/operators/scale	ALL
# rank_by_side	Cross Sectional	['COMBO', 'REGULAR']	rank_by_side(x, rate=2,scale=1)	Ranks positive and negative input separately and scale to book. For precise sorting use rate=0	/operators/rank_by_side
# normalize	Cross Sectional	['COMBO', 'REGULAR']	normalize(x, useStd = false, limit = 0.0)	Calculates the mean value of all valid alpha values for a certain date, then subtracts that mean from each element	/operators/normalize	ALL
# generalized_rank	Cross Sectional	['COMBO', 'REGULAR']	generalized_rank(open, m=1)	The idea is that difference between instrument values raised to the power of m is added to the rank of instrument with bigger value and subtracted from the rank of instrument with lesser value. More details in the notes at the end of page	/operators/generalized_rank
# one_side	Cross Sectional	['COMBO', 'REGULAR']	one_side(x , side = long )	Shifts all instruments up or down so that the Alpha becomes long-only or short-only (if side = short), respectively.
# rank_gmean_amean_diff	Cross Sectional	['COMBO', 'REGULAR']	rank_gmean_amean_diff(input1, input2, input3,...)	Operator returns difference of geometric mean and arithmetic mean of cross sectional rank of inputs	/operators/rank_gmean_amean_diff
# quantile	Cross Sectional	['COMBO', 'REGULAR']	quantile(x, driver = gaussian, sigma = 1.0)	Rank the raw vector, shift the ranked Alpha vector, apply distribution (gaussian, cauchy, uniform). If driver is uniform, it simply subtract each Alpha value with the mean of all Alpha values in the Alpha vector	/operators/quantile	ALL
# vector_proj	Cross Sectional	['COMBO', 'REGULAR']	vector_proj(x, y)	Returns vector projection of x onto y. Algebraic and geometric details can be found on wiki
# multi_regression	Cross Sectional	['COMBO', 'REGULAR']	multi_regression(y, x1, x2,..., days=0, lag=0, solver="SVD")	"Perform multivariable regression of multiple independent variables (x1,x2,...) on a dependent variable (y) across number of days.

# If days = n (n >= 0), will include past n days in the regression. Setting days = 0 indicates that we're only using today (x1, x2, ...) to predict y.

# If lag = m (m >= 0), will lag (x1, x2, ...) for m days for prediction.

# Options for solver: ""SVD""(default), ""QR"", ""NORMAL"""
# cross_sectional_ops = [
#     {
#         "算子名称": "winsorize",
#         "算子描述": "缩尾处理，确保x中的所有值都在上下限范围内，上下限通过标准差的倍数指定。详细信息可在wiki上找到",
#         "参数说明": "x: 输入数据, std=4: 标准差倍数",
#         "适用范围": "ALL"
#     },
#     {
#         "算子名称": "rank",
#         "算子描述": "对所有股票进行排名，返回一个在0.0到1.0之间均匀分布的数值。使用rate=0可获得精确排序",
#         "参数说明": "x: 输入数据, rate=2: 排序精度",
#         "适用范围": "ALL"
#     },
#     {
#         "算子名称": "regression_proj",
#         "算子描述": "对股票进行横截面回归，以Y为目标变量，X为自变量",
#         "参数说明": "y: 因变量, x: 自变量"
#     },
#     {
#         "算子名称": "vector_neut",
#         "算子描述": "对于给定向量x和y，找到一个新向量x*（输出），使x*与y正交",
#         "参数说明": "x: 输入向量1, y: 输入向量2"
#     },
#     {
#         "算子名称": "regression_neut",
#         "算子描述": "对股票进行横截面回归，以Y为目标变量，X为自变量",
#         "参数说明": "y: 因变量, x: 自变量"
#     },
#     {
#         "算子名称": "zscore",
#         "算子描述": "Z值标准化，描述数值与群组均值的关系，以标准差为单位衡量",
#         "参数说明": "x: 输入数据",
#         "适用范围": "ALL"
#     },
#     {
#         "算子名称": "scale_down",
#         "算子描述": "将每日数值按比例缩放至0和1之间，最小值映射为0，最大值映射为1。结果减去常数作为偏移",
#         "参数说明": "x: 输入数据, constant=0: 偏移量"
#     },
#     {
#         "算子名称": "truncate",
#         "算子描述": "将x的所有值截断至maxPercent。这里maxPercent使用小数表示",
#         "参数说明": "x: 输入数据, maxPercent=0.01: 最大百分比"
#     },
#     {
#         "算子名称": "scale",
#         "算子描述": "缩放输入至账面规模。可以通过额外参数分别对多头和空头仓位进行缩放",
#         "参数说明": "x: 输入数据, scale=1: 整体缩放, longscale=1: 多头缩放, shortscale=1: 空头缩放",
#         "适用范围": "ALL"
#     },
#     {
#         "算子名称": "rank_by_side",
#         "算子描述": "分别对正负值进行排名并缩放至账面。使用rate=0可获得精确排序",
#         "参数说明": "x: 输入数据, rate=2: 排序精度, scale=1: 缩放比例"
#     },
#     {
#         "算子名称": "normalize",
#         "算子描述": "计算某一日期所有有效alpha值的均值，然后从每个元素中减去该均值",
#         "参数说明": "x: 输入数据, useStd=False: 是否使用标准差, limit=0.0: 限制值",
#         "适用范围": "ALL"
#     },
#     {
#         "算子名称": "generalized_rank",
#         "算子描述": "将工具值的差值的m次方加到较大值的排名上，从较小值的排名中减去",
#         "参数说明": "open: 开盘价, m=1: 幂次"
#     },
#     {
#         "算子名称": "one_side",
#         "算子描述": "上下移动所有工具，使Alpha变为仅多头或仅空头（如果side=short）",
#         "参数说明": "x: 输入数据, side=long: 方向"
#     },
#     {
#         "算子名称": "rank_gmean_amean_diff",
#         "算子描述": "返回输入的横截面排名的几何平均值和算术平均值的差",
#         "参数说明": "input1, input2, input3,...: 多个输入数据"
#     },
#     {
#         "算子名称": "quantile",
#         "算子描述": "对原始向量排名，移动已排名的Alpha向量，应用分布（高斯、柯西、均匀）。如果driver为uniform，则简单地从每个Alpha值中减去Alpha向量中所有Alpha值的均值",
#         "参数说明": "x: 输入数据, driver=gaussian: 分布类型, sigma=1.0: 标准差",
#         "适用范围": "ALL"
#     },
#     {
#         "算子名称": "vector_proj",
#         "算子描述": "返回x在y上的向量投影。代数和几何细节可在wiki上找到",
#         "参数说明": "x: 输入向量1, y: 输入向量2"
#     },
#     {
#         "算子名称": "multi_regression",
#         "算子描述": "对多个自变量(x1,x2,...)和一个因变量(y)进行跨天数的多变量回归。\n如果days=n(n>=0)，将在回归中包含过去n天。\n如果lag=m(m>=0)，将对(x1,x2,...)进行m天的滞后预测。\n求解器选项：SVD(默认)、QR、NORMAL",
#         "参数说明": "y: 因变量, x1,x2,...: 自变量, days=0: 天数, lag=0: 滞后期, solver=SVD: 求解方法"
#     }
# ]
# """

cross_sectional_ops = [
    {
        "算子名称": "winsorize",
        "算子描述": "对数据进行缩尾处理,确保所有值都在上下限范围内,上下限是通过标准差的倍数来指定的",
        "伪代码": """
def winsorize(x, std=4):
    lower_limit = x.quantile(0.01)
    upper_limit = x.quantile(0.99)
    return np.clip(x, lower_limit, upper_limit)
""",
    },
    {
        "算子名称": "rank",
        "算子描述": "将输入数据在所有股票中进行排名,返回一个介于0.0和1.0之间的等分布数值,用于精确排序,使用率=0",
        "伪代码": """
def rank(x, rate=2):
    return x.rank(pct=True, method='dense')
""",
    },
    {
        "算子名称": "regression_proj",
        "算子描述": "对股票进行交叉回归,使用Y作为目标变量,X作为自变量",
        "伪代码": """
def regression_proj(y, x):
    return y.rolling(window=window).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=False)
""",
    },
    {
        "算子名称": "vector_neut",
        "算子描述": "给定向量x和y,找到一个新向量x*,使得x*与y正交",
        "伪代码": """
def vector_neut(x, y):
    return x - np.dot(x, y) / np.dot(y, y) * y
""",
    },
    {
        "算子名称": "regression_neut",
        "算子描述": "对股票进行交叉回归,使用Y作为目标变量,X作为自变量",
        "伪代码": """
def regression_neut(y, x):
    return y.rolling(window=window).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=False)
""",
    },
    {
        "算子名称": "zscore",
        "算子描述": "Z-score是一种数值测量方法,描述一个值相对于一组值的偏离程度,Z-score以标准差为单位衡量偏离程度",
        "伪代码": """
def zscore(x):
    return (x - x.mean()) / x.std()
""",
    },
    {
        "算子名称": "scale_down",
        "算子描述": "将输入数据缩放到0到1之间,最小值映射为0,最大值映射为1,常数是最终结果的偏移量",
        "伪代码": """
def scale_down(x, constant=0):
    return (x - x.min()) / (x.max() - x.min()) - constant
""",
    },
    {
        "算子名称": "truncate",
        "算子描述": "将输入数据截断到指定百分比,最大百分比为1",
        "伪代码": """
def truncate(x, maxPercent=0.01):
    return x.clip(lower=x.quantile(maxPercent), upper=x.quantile(1 - maxPercent))
""",
    },
    {
        "算子名称": "scale",
        "算子描述": "将输入数据缩放到指定范围,常数是最终结果的偏移量",
        "伪代码": """
def scale(x, scale=1, longscale=1, shortscale=1):
    return x.apply(lambda x: x * scale if x > 0 else x * longscale if x < 0 else x * shortscale)
""",
    },
    {
        "算子名称": "rank_by_side",
        "算子描述": "将输入数据分为正负两部分,分别进行排名,然后缩放到指定范围",
        "伪代码": """
def rank_by_side(x, rate=2, scale=1):
    return x.apply(lambda x: x * scale if x > 0 else x * longscale if x < 0 else x * shortscale)
""",
    },
    {
        "算子名称": "normalize",
        "算子描述": "计算每个股票的平均值,然后减去每个元素的平均值",
        "伪代码": """
def normalize(x, useStd=False, limit=0.0):
    return x.apply(lambda x: x - x.mean() if not useStd else x.apply(lambda x: (x - x.mean()) / x.std()))
""",
    },
    {
        "算子名称": "generalized_rank",
        "算子描述": "将输入数据分为正负两部分,分别进行排名,然后缩放到指定范围",
        "伪代码": """
def generalized_rank(x, m=1):
    return x.apply(lambda x: x * m if x > 0 else x * -m if x < 0 else x)
""",
    },
    {
        "算子名称": "one_side",
        "算子描述": "将输入数据分为正负两部分,分别进行排名,然后缩放到指定范围",
        "伪代码": """
def one_side(x, side='long'):
    return x.apply(lambda x: x if x > 0 else x * -1 if x < 0 else x)
""",
    },
    {
        "算子名称": "rank_gmean_amean_diff",
        "算子描述": "计算几何平均值和算术平均值的差值",
        "伪代码": """
def rank_gmean_amean_diff(x):
    return x.apply(lambda x: x.apply(lambda x: np.log(x)).mean() - np.log(x).mean())
""",
    },
    {
        "算子名称": "quantile",
        "算子描述": "计算输入数据的分位数",
        "伪代码": """
def quantile(x, q=0.5):
    return x.quantile(q)
""",
    },
    {
        "算子名称": "vector_proj",
        "算子描述": "计算向量x在向量y上的投影",
        "伪代码": """
def vector_proj(x, y):
    return np.dot(x, y) / np.dot(y, y) * y
""",
    },
    {
        "算子名称": "multi_regression",
        "算子描述": "进行多元回归,使用y作为目标变量,x1,x2,...作为自变量,days参数指定回归的天数,lag参数指定自变量的滞后天数,solver参数指定求解方法",
        "伪代码": """
def multi_regression(y, x1, x2, ..., days=0, lag=0, solver="SVD"):
    if days > 0:
        x1 = x1.shift(days)
        x2 = x2.shift(days)
        ...
    if lag > 0:
        y = y.shift(lag)
        x1 = x1.shift(lag)
        x2 = x2.shift(lag)
        ...
    if solver == "SVD":
        return np.linalg.lstsq(np.column_stack([x1, x2, ...]), y, rcond=None)[0]
    elif solver == "QR":
        return np.linalg.qr(np.column_stack([x1, x2, ...]), mode='full')
    elif solver == "NORMAL":
        return np.linalg.solve(np.column_stack([x1, x2, ...]), y)
""",
    },
]
