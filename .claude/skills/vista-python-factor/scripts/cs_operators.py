from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from scipy.special import erfinv


def log(x):
    if np.isscalar(x):
        return np.log(x) if x > 0 else np.nan
    else:
        x = x.copy()
        x = x.where(x > 0, np.nan)  # 将非正数替换为 NaN
        return np.log(x).sort_index()


def divide(s1, s2):
    result = s1 / s2
    if isinstance(result, pd.Series):
        return result.sort_index()
    else:
        return result


def arc_cos(x):
    if hasattr(x, "index"):  # 检查是否为Series类型
        # 使用向量化操作
        result = x.copy()
        mask = (x >= -1) & (x <= 1)
        # 对于在有效范围内的值，使用numpy的arccos计算
        result[mask] = np.arccos(x[mask])
        # 对于范围外的值，设置为NaN
        result[~mask] = np.nan
        # 确保返回的Series包含正确的索引并排序
        return result.sort_index()
    else:  # 标量输入
        if -1 <= x <= 1:
            return np.arccos(x)
        else:
            return np.nan


def arc_tan(x):
    if hasattr(x, "index") and hasattr(x, "values"):
        # 向量化处理Series
        result = np.arctan(x)
        return result.sort_index()
    else:
        # 处理标量输入
        return np.arctan(x)


def sqrt(x):
    if isinstance(x, (float, int)):
        # 处理标量值
        if x >= 0:
            return np.sqrt(x)
        else:
            return float("nan")
    else:
        # 处理Series
        # 使用布尔索引直接处理负值
        result = x.copy()
        mask = x < 0
        result[~mask] = np.sqrt(x[~mask])
        result[mask] = float("nan")
        return result.sort_index()


def sigmoid(x):
    if hasattr(x, "index"):  # 检查是否为Series类型
        # 处理数值溢出问题
        result = x.copy()

        # 处理NaN和无穷大值
        mask_large = x > 34
        mask_small = (x <= 34) & np.isfinite(x)

        # 对于x值过大的情况，直接设为1
        result[mask_large] = 1.0
        # 对于NaN或无穷大，保持原值
        # 对于x值过小的情况，使用exp计算
        safe_x = x[mask_small]
        result[mask_small] = 1.0 / (1.0 + np.exp(-safe_x))

        return result.sort_index()
    else:  # 处理标量输入
        # 处理NaN和无穷大值
        if not np.isfinite(x):
            return x  # 保持NaN或无穷大不变
        # 处理数值溢出
        if x > 34:  # 当x很大时，sigmoid接近1
            return 1.0
        else:
            return 1.0 / (1.0 + np.exp(-x))


def reverse(x):
    result = -x
    if hasattr(x, "index"):
        return result.sort_index()
    return result


def adv(s, d=10):
    # 计算过去window天的平均日成交量,输入序列为'vol'
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").rolling(d).mean().droplevel(0).sort_index()


def ts_rank(s, d=6, constant=0):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    constant = int(constant)

    def rolling_rank(x):
        if len(x) < d:
            return pd.Series([np.nan] * len(x), index=x.index)
        return x.rolling(d).rank()

    return s.groupby("symbol").transform(rolling_rank).sort_index() + constant


def ts_std_dev(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return x.groupby("symbol").transform(lambda s: s.rolling(window=d).std(ddof=1).reindex(s.index)).sort_index()


def signed_power(x, y):
    result = np.power(x, y)
    sign_x = np.sign(x)
    sign_result = np.sign(result)
    if isinstance(result, pd.Series):
        error = sign_x != sign_result
        result[error] = -result[error]
        return result.sort_index()
    else:
        if sign_x != sign_result:
            return -result
        else:
            return result


def rank(x, rate=2):
    # Ranks the input among all the instruments and returns an equally distributed number between 0.0 and 1.0. For precise sort, use the rate as 0
    rate = int(rate)
    if rate == 2:
        return x.groupby("dt").rank(pct=True).sort_index()
    else:
        return x.groupby("dt").rank().sort_index()


def ts_delta(s, d=2):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").diff(d).sort_index()


def ts_corr(s1, s2, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    s = pd.concat([s1, s2], axis=1)
    s.columns = columns = ["s1", "s2"]
    return (
        s.reset_index()
        .set_index("dt")
        .groupby("symbol")[columns]
        .rolling(d)
        .corr()
        .droplevel(2)
        .iloc[::2, 1]
        .sort_index()
    )


def ts_covariance(s1, s2, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    s = pd.concat([s1, s2], axis=1)
    columns = s.columns
    return (
        s.reset_index()
        .set_index("dt")
        .groupby("symbol")[columns]
        .rolling(d)
        .cov()
        .droplevel(2)
        .iloc[::2, 1]
        .sort_index()
    )


def ts_delay(s, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").shift(d).sort_index()


def ts_sum(s, d=10):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").rolling(d).sum().droplevel(0).sort_index()


def ts_min(s, d=10):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").rolling(d).min().droplevel(0).sort_index()


def ts_max(s, d=10):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").rolling(d).max().droplevel(0).sort_index()


def ts_scale(x, d=6, constant=0):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def rolling_scale(series):
        if len(series) < d:
            return pd.Series([np.nan] * len(series), index=series.index)
        min_x = series.rolling(d).min()
        max_x = series.rolling(d).max()
        return (series - min_x) / (max_x - min_x).replace(0, np.nan) + constant

    return x.groupby("symbol").transform(rolling_scale).sort_index()


def abs(x):
    if isinstance(x, pd.Series):
        return x.abs().sort_index()
    else:
        return np.abs(x)


def sign(x):
    if hasattr(x, "index"):
        # 处理Series输入
        result = np.sign(x)
        return result.sort_index()
    else:
        # 处理标量输入
        if np.isnan(x):
            return np.nan
        return np.sign(x)


def exp(s):
    if isinstance(s, pd.Series):
        return s.apply(np.exp).sort_index()
    else:
        return np.exp(s)


def arc_sin(s):
    if isinstance(s, pd.Series):
        return s.transform(lambda x: np.arcsin(x) if -1 <= x <= 1 else float("NaN")).sort_index()
    else:
        return np.arcsin(s) if -1 <= s <= 1 else float("NaN")


def max(*args):
    if len(args) < 2:
        raise ValueError("At least 2 inputs are required")

    # 处理第一个参数
    result = args[0]

    # 逐个比较后续参数
    for arg in args[1:]:
        if hasattr(result, "index") and hasattr(arg, "index"):
            # 两个都是Series
            aligned_result, aligned_arg = result.align(arg, fill_value=float("-inf"))
            result = np.maximum(aligned_result, aligned_arg)
        elif hasattr(result, "index"):
            # result是Series，arg是标量
            result = np.maximum(result, arg)
        elif hasattr(arg, "index"):
            # arg是Series，result是标量
            result = np.maximum(arg, result)
        else:
            # 两个都是标量
            result = np.maximum(result, arg)

    # 如果结果是Series，确保排序
    if hasattr(result, "index"):
        return result.sort_index()
    return result


def add(*args, filter=False):
    if filter:
        args = list(args)
        for i, arg in enumerate(args):
            if not isinstance(arg, pd.Series):
                args[i] = 0
            else:
                args[i] = arg.fillna(0)
    result = 0
    for s in args:
        result = result + s
    if isinstance(result, pd.Series):
        return result.sort_index()
    else:
        return result


def subtract(s1, s2, filter=False):
    if filter:
        s1 = 0 if not isinstance(s1, pd.Series) else s1.fillna(0)
        s2 = 0 if not isinstance(s2, pd.Series) else s2.fillna(0)
    result = s1 - s2
    if isinstance(result, pd.Series):
        return result.sort_index()
    else:
        return result


def multiply(*args, filter=False):
    if len(args) < 2:
        raise ValueError("At least 2 inputs are required for multiply.")

    if filter:
        args = list(args)
        for i, arg in enumerate(args):
            if not isinstance(arg, pd.Series):
                args[i] = 1
            else:
                args[i] = arg.fillna(1)
    result = args[0]
    for s in args[1:]:
        result = result * s
    if isinstance(result, pd.Series):
        return result.sort_index()
    else:
        return result


def tanh(s):
    if hasattr(s, "index"):
        return s.apply(np.tanh).sort_index()
    else:
        return np.tanh(s)


def round_down(s, f=1):
    if f == 0:
        raise ValueError("参数 f 不能为零")

    def calculate_round_down(x):
        return (x // f) * f

    if isinstance(s, pd.Series):
        return s.transform(calculate_round_down).sort_index()
    else:
        return calculate_round_down(s)


def inverse(s):
    if isinstance(s, pd.Series):
        return (1 / s).sort_index()
    else:
        return 1 / s


def s_log_1p(s):
    s_arr = np.array([s]) if np.isscalar(s) else s.values if isinstance(s, pd.Series) else np.array(s)
    abs_s = np.abs(s_arr)
    log_abs = np.log(abs_s + 1)
    signed_log = np.sign(s) * log_abs
    result = signed_log / (1 + log_abs)
    if isinstance(s, pd.Series):
        return pd.Series(result, index=s.index)
    elif np.isscalar(s):
        return result.item()


def ts_arg_max(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return (
        x.groupby("symbol")
        .transform(lambda s: s.rolling(window=d, min_periods=d).apply(lambda w: d - 1 - w.argmax(), raw=True))
        .sort_index()
    )


def ts_arg_min(x, d=5):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return (
        x.groupby("symbol")
        .transform(lambda s: s.rolling(window=d, min_periods=d).apply(lambda w: d - 1 - w.argmin(), raw=True))
        .sort_index()
    )


def ts_decay_linear(s, d=6, dense=False):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def rolling_decay(x):
        if len(x) < d:
            return np.nan  # 使用 np.nan
        weights = np.arange(d, 0, -1)
        if not dense:
            x = np.nan_to_num(x, nan=0.0)  # 用numpy替换fillna
        return np.sum(x * weights) / np.sum(weights)

    return (
        s.groupby("symbol").transform(lambda x: x.rolling(d, min_periods=1).apply(rolling_decay, raw=True)).sort_index()
    )


def ts_product(s, d=5):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    return s.groupby("symbol").transform(lambda x: x.rolling(d, min_periods=d).apply(np.prod, raw=True)).sort_index()


def pasteurize(x):
    if isinstance(x, pd.Series):
        result = x.copy()
        # Set INF values to NaN
        result[np.isinf(result)] = np.nan

        return result.sort_index()
    else:
        # For scalar values, check both INF and universe condition
        if np.isinf(x):
            return np.nan
        else:
            return x


def purify(x):
    if hasattr(x, "index") and hasattr(x, "where"):
        result = x.copy()
        # 替换无穷值为NaN
        mask = np.isinf(result)
        result = result.where(~mask, np.nan)

        # 确保返回的Series有正确的索引并排序
        if isinstance(result.index, pd.MultiIndex):
            return result.sort_index()
        else:
            # 处理可能没有MultiIndex的情况
            return result.sort_index()
    else:
        # 处理标量情况
        if np.isinf(x):
            return np.nan
        return x


def to_nan(x, value=0, reverse=False):
    if hasattr(x, "index"):
        result = x.copy()
        # reverse=True 时将 NaN 填回指定值，否则将指定值转为 NaN
        result = result.fillna(value) if reverse else result.replace(value, np.nan)
        return result.sort_index()
    else:
        # 处理标量输入
        if reverse:
            # 如果是NaN则返回指定值，否则返回原值
            return value if np.isnan(x) else x
        else:
            # 如果等于指定值则返回NaN，否则返回原值
            return np.nan if x == value else x


def min(*args):
    if len(args) < 2:
        raise ValueError("At least 2 inputs are required")

    # 处理第一个参数
    result = args[0]

    # 逐个比较后续参数
    for arg in args[1:]:
        if hasattr(result, "index") and hasattr(arg, "index"):
            # 两个都是Series
            aligned_result, aligned_arg = result.align(arg, fill_value=float("inf"))
            result = np.minimum(aligned_result, aligned_arg)
        elif hasattr(result, "index"):
            # result是Series，arg是标量
            result = np.minimum(result, arg)
        elif hasattr(arg, "index"):
            # arg是Series，result是标量
            result = np.minimum(arg, result)
        else:
            # 两个都是标量
            result = np.minimum(result, arg)

    # 处理分组逻辑
    if hasattr(result, "index"):
        result = result.transform(lambda x: x)

    # 如果结果是Series，确保排序
    if hasattr(result, "index"):
        return result.sort_index()
    return result


def nan_mask(x, y):
    # 处理x和y都是Series的情况
    if hasattr(x, "index") and hasattr(y, "index"):
        result = x.copy()
        mask = y < 0
        result[mask] = float("nan")
        return result.sort_index()

    # 处理y是Series，x是标量的情况
    elif hasattr(y, "index") and not hasattr(x, "index"):
        result = pd.Series(x, index=y.index)
        mask = y < 0
        result[mask] = float("nan")
        return result.sort_index()

    # 处理x是Series，y是标量的情况
    elif hasattr(x, "index") and not hasattr(y, "index"):
        if y < 0:
            return pd.Series(float("nan"), index=x.index).sort_index()
        else:
            return x.sort_index()

    # 处理x和y都是标量的情况
    else:
        if y < 0:
            return float("nan")
        else:
            return x


def nan_out(x, lower=None, upper=None):
    # 确保至少提供了一个参数
    if lower is None and upper is None:
        raise ValueError("At least one of 'lower' or 'upper' must be provided")

    # 处理标量输入
    if not isinstance(x, pd.Series):
        if (lower is not None and x < lower) or (upper is not None and x > upper):
            return np.nan
        return x

    # 处理Series输入
    result = x.copy()

    # 创建条件掩码并应用
    mask = pd.Series(False, index=x.index)
    if lower is not None:
        mask = mask | (x < lower)
    if upper is not None:
        mask = mask | (x > upper)

    result = result.mask(mask, np.nan)

    return result.sort_index()


def round(x, n=0):
    n = int(n)
    # 处理标量输入的情况
    if not hasattr(x, "index"):
        return np.round(x, n)
    elif hasattr(x, "index"):
        # 处理普通Series
        result = np.round(x, n)
        return result.sort_index() if hasattr(result, "sort_index") else result
    else:
        # 处理DataFrame
        result = np.round(x, n)
        return result


def replace(x, target="10,20", dest="100,200"):
    # 处理标量输入
    if isinstance(x, (int, float, str)):
        if not isinstance(target, str) or not isinstance(dest, str):
            return x

        target_values = target.strip().split(",")
        dest_values = dest.strip().split(",")

        if len(target_values) != len(dest_values):
            return x

        # 创建替换映射字典
        replace_dict = {}
        for i, target_val in enumerate(target_values):
            try:
                # 使用numpy进行数值转换
                target_numeric = np.float64(target_val)
                dest_numeric = np.float64(dest_values[i])
                replace_dict[target_numeric] = dest_numeric
            except ValueError:
                replace_dict[target_val] = dest_values[i]

        # 处理x的类型，确保类型一致性
        if isinstance(x, str):
            for key, value in replace_dict.items():
                if x == str(key):
                    return value
        else:
            try:
                x_numeric = np.float64(x)
                for key, value in replace_dict.items():
                    if isinstance(key, (int, float)) and x_numeric == key:
                        return value
            except ValueError:
                pass

        return x

    # 处理Series输入
    if not isinstance(target, str) or not isinstance(dest, str):
        raise TypeError("Parameters 'target' and 'dest' must be strings")

    target_values = target.strip().split(",")
    dest_values = dest.strip().split(",")

    if len(target_values) != len(dest_values):
        raise ValueError("Number of target values must match number of destination values")

    # 创建替换映射字典
    replace_dict = {}
    for i, target_val in enumerate(target_values):
        try:
            # 使用numpy进行数值转换
            target_numeric = np.float64(target_val)
            dest_numeric = np.float64(dest_values[i])
            replace_dict[target_numeric] = dest_numeric
        except ValueError:
            replace_dict[target_val] = dest_values[i]

    # 使用字典进行向量化批量替换
    result = x.replace(replace_dict)

    return result.sort_index()


def log_diff(x):
    # 检查输入类型是否为Series
    if not isinstance(x, pd.Series):
        return float("nan")
    # 检查是否有'symbol'索引级别
    if "symbol" not in x.index.names:
        return pd.Series(float("nan"), index=x.index)

    try:
        # 创建副本并处理非正值
        valid_x = x.copy()
        mask = valid_x <= 0
        if mask.any():
            valid_x = valid_x.mask(mask, np.nan)

        log_x = np.log(valid_x)
        # 按symbol分组计算前一个值
        previous_log_x = log_x.groupby(level="symbol").shift(1)
        # 计算对数差分
        result = log_x - previous_log_x

        return result.sort_index()

    except (AttributeError, TypeError):
        return pd.Series(float("nan"), index=x.index)


def power(x, y):
    if not isinstance(x, pd.Series) and not isinstance(y, pd.Series):
        return np.power(x, y)

    result = np.power(x, y)

    if isinstance(result, pd.Series):
        return result.sort_index()

    return result


def fraction(x):
    if hasattr(x, "index"):
        # 处理Series类型输入
        result = x - np.floor(x)
        return result.sort_index()
    else:
        # 处理标量输入
        return x - np.floor(x)


def floor(x):
    if hasattr(x, "index"):
        # 处理Series输入
        result = x.apply(lambda val: np.floor(val))
        return result.sort_index()
    else:
        # 处理标量输入
        return np.floor(x)


def ceiling(x):
    if isinstance(x, (int, float)):
        return np.ceil(x)
    result = np.ceil(x)
    return result.sort_index()


def ts_zscore(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    mean = x.groupby("symbol").transform(lambda s: s.rolling(d, min_periods=d).mean())
    std = x.groupby("symbol").transform(lambda s: s.rolling(d, min_periods=d).std(ddof=1))
    zscore = (x - mean) / std
    zscore = zscore.replace([np.inf, -np.inf], float("nan"))
    return zscore.sort_index()


def ts_returns(x, d=6, mode=1):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    # 处理标量输入
    if not hasattr(x, "index"):
        return float("nan")

    def calculate_returns(group):
        result = np.full_like(group, np.nan, dtype=float)
        if len(group) > d:
            shifted = group.shift(d)
            if mode == 1:
                # 算术收益率
                mask = ~np.isnan(shifted)
                result[mask] = group[mask] / shifted[mask] - 1
            else:
                # 对数收益率
                valid_mask = (group > 0) & (shifted > 0)
                result[valid_mask] = np.log(group[valid_mask]) - np.log(shifted[valid_mask])
        return result

    return x.groupby("symbol").transform(calculate_returns).sort_index()


def ts_entropy(x, d=6):
    """
    以 symbol 分组，对每个分组的 'value' 列计算长度为 d 的滚动窗口信息熵。
    分箱数量为 int(log2(d))。
    """
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    n_bins = max(int(np.log2(d)), 1)  # 确保至少 1 个分箱
    eps = 1e-10

    def _group_entropy(series):
        """
        针对单个 symbol 的 value 序列计算 rolling(d) 的信息熵。
        返回与 series 等长的一个 Series，前 d-1 个值为 NaN。
        """
        values = series.values.astype(float)
        n = len(values)
        # 若数据不足 d 条，直接全 NaN
        if n < d:
            return pd.Series(np.full(n, np.nan), index=series.index)

        # 1) 获取所有窗口视图: (n_windows, d)
        windows = sliding_window_view(values, d)
        n_windows = windows.shape[0]

        # 2) 对每个窗口计算 min, max，并做归一化
        min_vals = np.min(windows, axis=1)
        max_vals = np.max(windows, axis=1)

        # 有效窗口掩码: 如果 max == min，说明窗口内所有值都相等
        valid_mask = max_vals != min_vals

        # 归一化到 [0,1], 再乘 n_bins 得到 [0, n_bins) 的浮点数
        denominator = (max_vals - min_vals + eps)[:, None]
        normalized = (windows - min_vals[:, None]) / denominator
        normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)

        # 做向下取整并 clip 到 [0, n_bins-1]
        bin_indices = np.floor(normalized * n_bins).astype(int)
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        # 3) 统计各分箱频数
        counts = np.zeros((n_windows, n_bins), dtype=int)
        for i in range(n_bins):
            counts[:, i] = np.sum(bin_indices == i, axis=1)

        # 4) 计算概率矩阵 (n_windows, n_bins)，然后向量化地计算熵
        probs = counts / float(d)

        # 对每一行(窗口)做 -sum(p*log(p))，只对 p>0 生效
        # 可以用 np.where(probs>0, ..., 0) 来忽略 p=0
        entropies = -np.sum(np.where(probs > 0, probs * np.log(probs + eps), 0.0), axis=1)

        # 对于无效窗口(所有值都相等)，熵 = 0 (因为分布是单点分布)
        entropies[~valid_mask] = 0.0

        # 5) 拼回原长度，前 d-1 条 NaN
        result_values = np.full(n, np.nan)
        result_values[d - 1 :] = entropies

        return pd.Series(result_values, index=series.index)

    # 按 symbol 分组计算
    # 假设 x 中有列 'symbol' (分组标识) 和 'value' (要计算熵的列)
    # 如果要对多列一起计算，可以在 groupby 后自己调度
    result = x.groupby("symbol").transform(_group_entropy).sort_index()
    return result


def ts_triple_corr(x, y, z, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    result = x.copy()
    result[:] = np.nan

    # 对齐数据
    common_idx = x.index.intersection(y.index).intersection(z.index)
    if len(common_idx) == 0:
        return result.sort_index()

    x_aligned = x.loc[common_idx]
    y_aligned = y.loc[common_idx]
    z_aligned = z.loc[common_idx]

    def calc_triple_corr(x_data, y_data, z_data):
        # 计算滚动相关系数
        xy_corr = x_data.rolling(d, min_periods=d).corr(y_data)
        xz_corr = x_data.rolling(d, min_periods=d).corr(z_data)
        yz_corr = y_data.rolling(d, min_periods=d).corr(z_data)

        # 计算三元皮尔逊相关系数
        numerator = xy_corr**2 + xz_corr**2 - 2 * (xy_corr * xz_corr * yz_corr)
        denominator = 1 - yz_corr**2

        # 处理数值稳定性问题
        denominator = np.where(np.abs(denominator) < 1e-10, np.nan, denominator)
        triple_corr = np.sqrt(numerator / denominator)

        return triple_corr

    # 确保在分组内索引完全对齐
    result_aligned = pd.Series(index=common_idx, dtype=float)

    # 按symbol分组计算
    for _symbol, group in x_aligned.groupby(level="symbol"):
        if len(group) >= d:
            symbol_idx = group.index
            x_symbol = x_aligned.loc[symbol_idx]
            y_symbol = y_aligned.loc[symbol_idx]
            z_symbol = z_aligned.loc[symbol_idx]

            # 确保三个序列完全对齐
            result_aligned.loc[symbol_idx] = calc_triple_corr(x_symbol, y_symbol, z_symbol)

    # 将计算结果填充到原始索引
    result.loc[result_aligned.index] = result_aligned

    return result.sort_index()


def ts_backfill(x, lookback=6, k=1, ignore="NAN"):
    # 选择lookback范围内的第k个有效值对ignore数据填充
    lookback = int(lookback)
    if lookback <= 0:
        raise ValueError("lookback must be greater than or equal to 1")
    k = int(k)

    def backfill_vectorized(series):
        series = series.sort_index()

        # 处理忽略值的情况
        if ignore.upper() == "NAN":
            mask = series.isna()
            valid = series.notna()
        elif ignore == "0":
            mask = series == 0
            valid = series != 0
        else:
            mask = series.isna() | (series == 0)
            valid = ~mask

        result = series.copy()

        # 获取有效值的位置索引
        valid_indices = series.index[valid]

        # 遍历需要填充的位置
        for idx in series.index[mask]:
            # 找到在 `lookback` 时间窗口内的 `k` 个有效值
            valid_within_lookback = valid_indices[valid_indices <= idx][-lookback:]

            if len(valid_within_lookback) >= k:
                chosen_index = valid_within_lookback[-k]  # 取第 `k` 个有效值
                result[idx] = series[chosen_index]

        return result

    return x.groupby(level="symbol").apply(backfill_vectorized).sort_index()


def days_from_last_change(x):
    # 标记每个symbol的变化点（与前一个值不同时为True）
    change_mask = x != x.shift(1)

    def process_group(group):
        # group 为某个symbol下的布尔序列，表示是否发生变化
        # 将第一个元素强制设为True（始终认为首个位置是变化点）
        arr = group.to_numpy()
        arr[0] = True
        result = [0] * len(arr)
        last_change_index = 0  # 记录上一次变化点的位置索引
        for i in range(len(arr)):
            if arr[i]:
                last_change_index = i  # 更新变化点位置
                result[i] = 0
            else:
                result[i] = i - last_change_index  # 计算与上一次变化点的距离（步数差）
        return pd.Series(result, index=group.index)

    # 按symbol分组后，对每个组应用处理函数，保持与原索引一致
    result = change_mask.groupby("symbol").transform(process_group)
    return result.sort_index()


def last_diff_value(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def process_group(group):
        result = group.copy()
        for i in range(len(group)):
            # 取最近 d 天内的数据（不包括当前值）
            start_idx = max(0, i - d)
            search_window = group.iloc[start_idx:i]  # 过去 d 天的数据

            # 找到第一个与当前值不同的值（从后向前遍历）
            diff_values = search_window[search_window != group.iloc[i]]
            result.iloc[i] = diff_values.iloc[-1] if not diff_values.empty else pd.NA

        return result

    return x.groupby("symbol", group_keys=False).apply(process_group)


def ts_vector_neut(x, y, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def ts_vector_proj(x, y, d=6):
        d = int(d)

        def proj_calc(x_series, y_series):
            rolling_xy = (x_series * y_series).rolling(d, min_periods=d).sum()
            rolling_yy = (y_series * y_series).rolling(d, min_periods=d).sum()
            # 使用pandas的内置功能处理零值，避免使用np.nan
            proj_coef = rolling_xy / rolling_yy.replace(0, float("nan"))
            return proj_coef * y_series

        result = x.groupby("symbol").transform(lambda group_x: proj_calc(group_x, y.loc[group_x.index]))

        return result.sort_index()

    projection = ts_vector_proj(x, y, d)

    return (x - projection).sort_index()


def ts_percentage(x, d=6, percentage=0.5):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    if percentage <= 0 or percentage >= 1:
        raise ValueError("percentage must be between 0 and 1")

    def calculate_percentile(group):
        # 直接对rolling对象使用quantile作为聚合函数
        return group.rolling(d, min_periods=1).quantile(percentage)

    result = x.groupby("symbol").transform(calculate_percentile)
    return result.sort_index()


def ts_step(trigger_series):
    """
    模拟 WorldQuant 的 ts_step 操作符。
    trigger_series: pd.Series，布尔或数值序列，代表事件触发（True/非0）的位置。
    返回：从事件开始后的“计时器”序列，每天+1。
    测试代码：
    data = pd.Series([0, 2, 1, 0, 0, 1, 0, 0],
                 index=pd.date_range("2024-01-01", periods=8))
    print("事件触发序列:")
    print(data)

    step = ts_step(data)
    print("\nts_step 序列:")
    print(step)
    """

    def step(series):
        result = np.zeros_like(series, dtype=int)
        counter = 0
        counting = False

        for i in range(len(series)):
            if series.iloc[i]:
                counter = 1
                counting = True
            elif counting:
                counter += 1
            else:
                counter = 0
            result[i] = counter if counting else 0
        return pd.Series(result, index=series.index)

    return trigger_series.groupby("symbol").transform(step)


def ts_co_kurtosis(y, x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calc_windowed_cokurt(group_y, group_x):
        if len(group_y) < d:
            return pd.Series([np.nan] * len(group_y), index=group_y.index)

        y_vals = group_y.values
        x_vals = group_x.values
        idx = group_y.index

        y_windows = sliding_window_view(y_vals, window_shape=d)
        x_windows = sliding_window_view(x_vals, window_shape=d)

        # 计算窗口内均值和标准差
        mean_y = y_windows.mean(axis=1)
        mean_x = x_windows.mean(axis=1)
        std_y = y_windows.std(axis=1, ddof=1)
        std_x = x_windows.std(axis=1, ddof=1)

        # 计算协峰度分子 E[(y-mean_y)*(x-mean_x)^3]
        y_demean = y_windows - mean_y[:, None]
        x_demean = x_windows - mean_x[:, None]
        numerator = np.mean(y_demean * (x_demean**3), axis=1)

        # 计算分母 std_y * std_x^3，避免除零
        denominator = std_y * (std_x**3)
        denominator[denominator == 0] = np.nan

        cokurt = numerator / denominator

        # 填充前 d-1 个 NaN
        full_result = np.full(len(group_y), np.nan)
        full_result[d - 1 :] = cokurt

        return pd.Series(full_result, index=idx)

    # 分组计算
    result = y.groupby(level="symbol").apply(lambda group_y: calc_windowed_cokurt(group_y, x.loc[group_y.index]))

    return result.sort_index()


def ts_partial_corr(x, y, z, d=6):
    """
    计算x,y,z的偏相关系数,控制z的影响，计算x,y的偏相关系数
    """
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    # 确保所有输入具有相同的索引
    common_index = x.index.intersection(y.index).intersection(z.index)
    x_aligned = x.loc[common_index]
    y_aligned = y.loc[common_index]
    z_aligned = z.loc[common_index]

    # 定义用于transform的偏相关计算函数
    def compute_partial_corr(group_x):
        symbol = group_x.name
        group_y = y_aligned[y_aligned.index.get_level_values("symbol") == symbol]
        group_z = z_aligned[z_aligned.index.get_level_values("symbol") == symbol]

        # 确保索引对齐
        common_idx = group_x.index.intersection(group_y.index).intersection(group_z.index)
        if len(common_idx) < d:
            return pd.Series(np.nan, index=group_x.index)

        gx = group_x.loc[common_idx]
        gy = group_y.loc[common_idx]
        gz = group_z.loc[common_idx]

        # 使用向量化操作计算滚动相关系数
        rxy = gx.rolling(d, min_periods=d).corr(gy)
        rxz = gx.rolling(d, min_periods=d).corr(gz)
        ryz = gy.rolling(d, min_periods=d).corr(gz)

        # 使用numpy函数计算偏相关系数
        numerator = rxy - (rxz * ryz)
        denominator = np.sqrt((1 - np.power(rxz, 2)) * (1 - np.power(ryz, 2)))

        result = numerator / denominator

        # 确保结果与原始组索引对齐
        full_result = pd.Series(np.nan, index=group_x.index)
        full_result.loc[common_idx] = result

        return full_result

    # 使用transform而非apply进行分组计算
    result = x_aligned.groupby("symbol").transform(compute_partial_corr)

    # 创建与原始输入索引一致的结果Series
    final_result = pd.Series(np.nan, index=x.index)
    final_result.loc[common_index] = result

    return final_result.sort_index()


def ts_decay_exp_window(x, d=6, factor=0.5):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def decay_window(group):
        # 创建指数衰减权重向量（使用numpy）
        weights = np.power(factor, np.arange(d - 1, -1, -1))
        # 归一化权重
        weights = weights / weights.sum()

        # 使用rolling窗口和向量化操作
        return group.rolling(window=d).apply(lambda x: np.sum(x * weights), raw=True)

    return x.groupby("symbol").transform(decay_window).sort_index()


def ts_av_diff(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def compute_av_diff(group):
        rolling_mean = group.rolling(d, min_periods=1).mean()
        return group - rolling_mean

    return x.groupby("symbol").transform(compute_av_diff).sort_index()


def ts_mean(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_mean(group):
        return group.rolling(d, min_periods=1).mean()

    return x.groupby("symbol").transform(calculate_mean).sort_index()


def ts_rank_gmean_amean_diff(*args, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    if len(args) == 0:
        return pd.Series(dtype=float)

    inputs = args

    if not inputs:
        return pd.Series(dtype=float)

    # 找到第一个Series类型的输入作为基准索引
    base_series = None
    for series in inputs:
        if isinstance(series, pd.Series):
            base_series = series
            break

    if base_series is None:
        return pd.Series(dtype=float)

    # 将所有输入转换为具有相同索引的Series
    processed_inputs = []
    for input_arg in inputs:
        if isinstance(input_arg, pd.Series):
            processed_inputs.append(input_arg)
        else:
            # 将标量转换为与基准Series具有相同索引的Series
            processed_inputs.append(pd.Series(input_arg, index=base_series.index))

    # 计算每个输入的ts_rank
    all_ranks = []
    for series in processed_inputs:
        # 使用transform计算时间序列排名
        ranks = series.groupby(level="symbol").transform(lambda x: x.rolling(d, min_periods=d).rank(pct=True))
        all_ranks.append(ranks)

    # 计算每个时间点的所有序列的算术平均值
    # 将 all_ranks 中的 Series 合并成一个 DataFrame
    all_ranks_df = pd.concat(all_ranks, axis=1)
    amean_at_time = all_ranks_df.mean(axis=1)

    # 计算每个时间点的所有序列的几何平均值
    # 处理可能的零值或负值 (百分比排名在 0 到 1 之间，所以最小值用一个很小的正数代替)
    valid_ranks = [np.maximum(ranks, 1e-10) for ranks in all_ranks]
    log_ranks = [np.log(rank) for rank in valid_ranks]

    # 将对数排名合并成一个 DataFrame
    log_ranks_df = pd.concat(log_ranks, axis=1)
    log_amean_at_time = log_ranks_df.mean(axis=1)
    gmean_at_time = np.exp(log_amean_at_time)

    # 确保结果的索引与原始数据的索引一致
    if not amean_at_time.index.equals(base_series.index):
        amean_at_time = amean_at_time.reindex(base_series.index)
    if not gmean_at_time.index.equals(base_series.index):
        gmean_at_time = gmean_at_time.reindex(base_series.index)

    # 计算几何平均值与算术平均值的差
    result = gmean_at_time - amean_at_time

    return result.sort_index()


def ts_kurtosis(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_kurtosis(group):
        # 使用向量化操作计算滚动窗口
        roll_mean = group.rolling(d, min_periods=d).mean()
        roll_std = group.rolling(d, min_periods=d).std(ddof=1)

        # 计算滚动窗口中每个元素与均值的差，然后除以标准差
        # 使用shift方法创建滞后值矩阵以避免循环
        z_values = np.zeros((len(group), d))

        for i in range(d):
            shifted = group.shift(i)
            valid_mask = ~roll_mean.isna() & (roll_std > 0)
            z_values[:, i] = np.where(valid_mask, (shifted - roll_mean) / np.where(roll_std > 0, roll_std, 1), np.nan)

        # 计算每个窗口内的z值的4次方均值
        z4_mean = np.mean(z_values**4, axis=1)
        # 峰度 = z^4均值 - 3
        result = np.where(~np.isnan(roll_mean), z4_mean - 3, np.nan)
        return result

    return x.groupby("symbol").transform(calculate_kurtosis).sort_index()


def ts_min_max_diff(x, d=6, f=0.5):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_diff(group):
        rolling_min = group.rolling(d, min_periods=1).min()
        rolling_max = group.rolling(d, min_periods=1).max()
        return group - f * (rolling_min + rolling_max)

    return x.groupby("symbol").transform(calculate_diff).sort_index()


def ts_min_max_cps(x, d=6, f=2):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_min_max_cps(group):
        rolling_min = group.rolling(window=d, min_periods=1).min()
        rolling_max = group.rolling(window=d, min_periods=1).max()
        return (rolling_min + rolling_max) - f * group

    return x.groupby("symbol").transform(calculate_min_max_cps).sort_index()


def ts_ir(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_ir(group):
        # 计算滚动平均值
        rolling_mean = group.rolling(d, min_periods=d).mean()
        # 计算滚动标准差
        rolling_std = group.rolling(d, min_periods=d).std(ddof=1)

        # 计算信息比率：均值除以标准差
        ir = rolling_mean / rolling_std
        # 处理标准差为0的情况
        return ir.where(rolling_std != 0, np.nan)

    # 按symbol分组计算
    result = x.groupby("symbol").apply(calculate_ir)
    return result.sort_index()


def ts_theilsen(x, y, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def vectorized_theilsen(group_x, group_y, d):
        d = int(d)
        if d <= 0:
            raise ValueError("参数 d 必须为正整数")
        x_arr = group_x.values
        y_arr = group_y.values
        n = len(x_arr)
        # 若组内数据不足窗口大小，直接返回全为nan
        if n < d:
            return pd.Series(np.full(n, np.nan), index=group_x.index)

        # 利用sliding_window_view构造滚动窗口，得到形状为 (n-d+1, d) 的二维数组
        windows_x = sliding_window_view(x_arr, d)
        windows_y = sliding_window_view(y_arr, d)

        # 计算每个窗口内所有成对点的差值
        # 取上三角（不含对角线）的索引，即所有 i<j 的组合
        idx = np.triu_indices(d, k=1)
        # 对所有窗口同时计算成对差值，结果形状为 (n-d+1, num_pairs)
        diff_x = windows_x[:, idx[0]] - windows_x[:, idx[1]]
        diff_y = windows_y[:, idx[0]] - windows_y[:, idx[1]]

        # 计算各对的斜率
        diff_x[diff_x == 0] = np.nan
        slopes_window = diff_y / diff_x

        # 对每个窗口计算斜率中位数
        medians = np.median(slopes_window, axis=1)

        # 构造结果向量，前 d-1 个点无结果，后续点赋予对应窗口计算出的中位数
        slopes = np.full(n, np.nan)
        slopes[d - 1 :] = medians
        return pd.Series(slopes, index=group_x.index)

    # 对每个 symbol 分组后向量化计算
    result = x.groupby("symbol").apply(lambda grp: vectorized_theilsen(grp, y.loc[grp.index], d))
    # groupby.apply返回多级索引，整理后返回
    result = result.reset_index(level=0, drop=True).sort_index()
    return result


def hump_decay(x, p=0):
    def process_group(group):
        if len(group) <= 1:
            return group

        shifted = group.shift(1)
        diff = group - shifted

        mask = diff != 0 if p == 0 else diff.abs() > p * shifted.abs()

        result = group.copy()
        result.loc[~mask] = float("nan")

        return result

    result = x.groupby("symbol").transform(process_group)
    return result.sort_index()


def ts_weighted_decay(x, k=0.5):
    if k <= 0 or k >= 1:
        raise ValueError("k must be between 0 and 1")

    def weighted_decay(group):
        result = group.copy()
        prev_values = group.shift(1)

        # 对第一个值之后的所有值应用加权平均：k*当天值 + (1-k)*前一天值
        # 使用mask避免对第一个值进行计算
        mask = ~prev_values.isna()
        result[mask] = k * group[mask] + (1 - k) * prev_values[mask]

        return result

    return x.groupby("symbol").transform(weighted_decay).sort_index()


def ts_quantile(x, d=6, driver="gaussian"):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    # 按symbol分组，然后进行向量化操作
    def transform_func(group):
        ranks = group.rolling(d, min_periods=d).rank(pct=True)
        ranks = ranks.clip(lower=1e-8, upper=1 - 1e-8)

        if driver == "uniform":
            return ranks
        elif driver == "cauchy":
            return np.tan(np.pi * (ranks - 0.5))
        else:  # 默认使用gaussian
            return np.sqrt(2) * erfinv(2 * ranks - 1)  # 注意 ranks / d 归一化

    result = x.groupby("symbol").transform(transform_func)

    return result.sort_index()


def ts_count_nans(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def count_nans_in_window(group):
        return group.isna().rolling(d).sum()

    return x.groupby("symbol").transform(count_nans_in_window).sort_index()


def ts_co_skewness(y, x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    result = pd.Series(index=y.index, dtype=float)

    def coskew_func(group_y, group_x, d):
        # 对齐索引
        y_aligned = group_y.reset_index(level="symbol", drop=True)
        x_aligned = group_x.reset_index(level="symbol", drop=True).reindex(y_aligned.index)

        # 转为 numpy 数组
        y_vals = y_aligned.values
        x_vals = x_aligned.values

        n = len(y_vals)
        # 若组内数据不足窗口大小，直接返回全为nan
        if n < d:
            return pd.Series(np.full(n, np.nan), index=group_y.index)

        # 创建滑动窗口
        y_windows = sliding_window_view(y_vals, window_shape=d)
        x_windows = sliding_window_view(x_vals, window_shape=d)

        # 向量化计算每个窗口的 co-skewness
        y_mean = y_windows.mean(axis=1)
        x_mean = x_windows.mean(axis=1)
        y_dev = y_windows - y_mean[:, np.newaxis]
        x_dev = x_windows - x_mean[:, np.newaxis]
        coskew_vals = np.sum(y_dev * (x_dev**2), axis=1) / (d - 1)

        # 调整结果 Series 的索引以匹配原始分组
        start_index = group_y.index[d - 1 :]
        return pd.Series(coskew_vals, index=start_index)

    # 对每个 symbol 分组后向量化计算
    grouped_y = y.groupby("symbol")
    grouped_x = x.groupby("symbol")

    for symbol, group_y in grouped_y:
        if symbol in grouped_x.groups:
            group_x = grouped_x.get_group(symbol)
            coskew_result = coskew_func(group_y, group_x, d)
            result.loc[coskew_result.index] = coskew_result.values
        else:
            # 如果 y 中有 symbol 但 x 中没有，则填充 NaN
            result.loc[group_y.index] = np.nan

    return result.sort_index()


def ts_min_diff(x, d=6):
    if x is None or len(x) == 0:
        return x.copy() if hasattr(x, "copy") else x

    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_min_diff(group):
        # 在transform内部正确使用rolling
        rolling_min = group.rolling(window=d, min_periods=1).min()
        return group - rolling_min

    result = x.groupby("symbol").transform(calculate_min_diff)
    return result.sort_index()


def jump_decay(x, d=6, sensitivity=0.5, force=0.1):
    """
    当当前数据（x）与过去的某个数据点相比（滞后 d 个周期）发生了较大的“跳跃”时,计算跳跃的衰减贡献值。
    用于了解哪些地方发生了突变，由衰减突变值表示，确认时间点的突变程度。
    对序列进行该跳跃衰减处理，能够减少这种突变对因子的干扰，平滑序列。
    """
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    if not isinstance(sensitivity, (int, float)):
        raise ValueError("sensitivity must be a scalar")
    if not isinstance(force, (int, float)):
        raise ValueError("force must be a scalar")
    # 提前计算衰减核，长度为 d
    kernel_full = np.power(1 - force, np.arange(d))

    def calculate_jump_decay(group):
        n = len(group)
        if n <= 1:
            return pd.Series(np.nan, index=group.index)

        diff = group.diff()
        abs_diff = np.abs(diff)
        rolling_std = abs_diff.rolling(d, min_periods=2).std(ddof=1)

        jump_mask = abs_diff > (rolling_std * sensitivity)
        jump_mask = jump_mask.shift(-1)
        jump_mask[jump_mask.isna()] = False

        result = np.zeros(n)
        # 获取所有跳跃的索引
        jump_indices = np.nonzero(jump_mask.values)[0]

        for idx in jump_indices:
            # 确保不会超出序列范围
            if idx + 1 >= n:
                continue
            # 获取跳跃幅度，使用 diff 值（正或负）
            mag = diff.values[idx]
            # 衰减长度为 d 或剩余的步数
            decay_len = min(d, n - idx - 1)
            # 利用预先计算的 kernel_full 的一段进行加权衰减
            result[idx + 1 : idx + 1 + decay_len] += mag * kernel_full[:decay_len]

        return pd.Series(result, index=group.index)

    grouped = x.groupby("symbol")
    result = grouped.transform(calculate_jump_decay)
    return result.sort_index()


def ts_moment(x, d=6, k=0):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    k = int(k)

    def calculate_moment_vectorized(group):
        n = len(group)
        if n < d:
            return pd.Series([np.nan] * n, index=group.index)

        values = group.values.astype(np.float32)
        windows = np.lib.stride_tricks.sliding_window_view(values, window_shape=d)

        if k == 0:
            return pd.Series(np.ones(windows.shape[0]), index=group.index[d - 1 :])
        else:
            means = np.mean(windows, axis=1)
            centered_windows = windows - means[:, np.newaxis]
            moments = np.mean(centered_windows**k, axis=1)
            result = pd.Series([np.nan] * (d - 1), index=group.index[: d - 1])
            result = pd.concat([result, pd.Series(moments, index=group.index[d - 1 :])])
            return result

    return x.groupby("symbol", group_keys=False).apply(calculate_moment_vectorized).sort_index()


def ts_regression(y, x, d=6, lag=0, rettype=0):
    """
    计算y对x的回归，lag表示y的滞后，返回回归系数、截距、相关系数、R平方、t统计量、p值,分别对应rettype=0,1,2,3,4,5
    """
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    lag = int(lag)
    if lag < 0:
        raise ValueError("lag must be greater than 0")
    rettype = int(rettype)
    if rettype < 0 or rettype > 4:
        raise ValueError("rettype must be between 0 and 4")

    # 处理lag
    y_lagged = y.copy()
    if lag != 0:
        y_lagged = y.groupby(level="symbol").shift(-lag)

    # 对每个symbol进行计算
    def regression_calc(group):
        y_vals = group.iloc[:, 0]
        x_vals = group.iloc[:, 1]

        # 滚动统计
        roll_x = x_vals.rolling(d, min_periods=2)
        roll_y = y_vals.rolling(d, min_periods=2)

        mean_x = roll_x.mean()
        mean_y = roll_y.mean()
        var_x = roll_x.var(ddof=1)
        var_y = roll_y.var(ddof=1)

        # 协方差计算
        roll_xy = (x_vals * y_vals).rolling(d, min_periods=2).sum()
        n = roll_x.count()
        cov_xy = (roll_xy - n * mean_x * mean_y) / (n - 1)

        # beta 和 alpha
        beta = cov_xy / var_x
        alpha = mean_y - beta * mean_x

        # 安全标准差和相关系数计算
        std_x = np.sqrt(var_x)
        std_y = np.sqrt(var_y)
        safe_mask = (std_x > 0) & (std_y > 0)
        safe_corr = np.full_like(cov_xy, np.nan)
        safe_corr[safe_mask] = cov_xy[safe_mask] / (std_x[safe_mask] * std_y[safe_mask])

        # 限制值域 [-1, 1] 以防数值超限
        safe_corr = np.clip(safe_corr, -1.0, 1.0)

        # t 值计算（加 sqrt 掩码）
        t_stat = np.full_like(safe_corr, np.nan)
        valid_n = n > 2
        t_mask = valid_n & safe_mask & (np.abs(safe_corr) < 1)

        t_stat[t_mask] = safe_corr[t_mask] * np.sqrt((n[t_mask] - 2) / (1 - np.power(safe_corr[t_mask], 2)))

        # p 值计算
        t_squared = np.power(t_stat, 2)
        p_values = np.full_like(t_stat, np.nan)
        p_values[t_mask] = 2 * (1 - np.abs(t_stat[t_mask]) / np.sqrt(t_squared[t_mask] + n[t_mask] - 2))

        # 返回值类型
        if rettype == 0:
            return alpha
        elif rettype == 1:
            return beta
        elif rettype == 2:
            return pd.Series(safe_corr, index=y_vals.index)
        elif rettype == 3:
            return pd.Series(np.power(safe_corr, 2), index=y_vals.index)
        elif rettype == 4:
            return pd.Series(p_values, index=y_vals.index)

    # 创建包含y和x的Series对
    paired_data = pd.concat([y_lagged, x], axis=1)

    # 对每个symbol应用回归计算
    result = paired_data.groupby(level="symbol").apply(regression_calc)

    # 确保保留双重索引
    if isinstance(result.index, pd.MultiIndex) and result.index.nlevels > 2:
        result = result.droplevel(0)

    return result.sort_index()


def ts_skewness(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_skewness(group):
        windows = sliding_window_view(group.values, window_shape=d)

        mean = windows.mean(axis=1)
        std = windows.std(axis=1, ddof=1)
        z3 = ((windows - mean[:, None]) / std[:, None]) ** 3
        n = d
        skew = (n / ((n - 1) * (n - 2))) * np.sum(z3, axis=1)

        # 构造结果：用 NaN 填充前面不满窗口的部分
        skew_full = np.full(len(group), np.nan)
        skew_full[d - 1 :] = skew

        return pd.Series(skew_full, index=group.index)

    result = x.groupby("symbol").transform(calculate_skewness)
    return result.sort_index()


def ts_max_diff(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    if not isinstance(x, pd.Series):
        return pd.Series(float("nan"), index=x.index) if hasattr(x, "index") else float("nan")
    if x.empty:
        return x.copy()

    def calculate_diff_max(group):
        # 计算包括当前值在内的过去d个周期的最大值
        rolling_max = group.rolling(d, min_periods=1).max()
        # 计算当前值与过去d个周期最大值的差值
        return group - rolling_max

    # 检查是否有symbol索引
    result = x.groupby("symbol").transform(calculate_diff_max) if "symbol" in x.index.names else calculate_diff_max(x)

    return result.sort_index()


def kth_element(x, d=6, k=1):
    """
    在过去 d 天的时间窗口内，按时间逆序找过去d天的第 k 个有效值,当k=1时，此运算符可用于回填缺失数据。
    """
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    k = int(k)
    if k > d:
        raise ValueError("k must be less than or equal to d")

    def get_kth(series):
        def pick_kth(window):
            valid_vals = window[~np.isnan(window)]
            if len(valid_vals) < k:
                return np.nan
            else:
                # 从最新往旧排，倒数第 k 个元素
                return valid_vals[-k]

        return series.rolling(window=d, min_periods=1).apply(pick_kth, raw=True)

    return x.groupby("symbol").transform(get_kth).sort_index()


def hump(x, hump=0.01):
    """
    限制时间序列每个时点的变化幅度不超过 ± hump × 前一个值
    """
    if not isinstance(x, (pd.Series)):
        return x
    if "symbol" not in x.index.names:
        return x
    if hump <= 0:
        raise ValueError("hump must be greater than 0")

    def hump_transform(group):
        if len(group) <= 1:
            return group

        shifted = group.shift(1)
        diff = group - shifted

        # 使用动态阈值：每条数据前一个值乘以 hump 作为上下限
        threshold = shifted.abs() * hump
        limited_diff = diff.clip(lower=-threshold, upper=threshold)

        result = shifted + limited_diff
        result.iloc[0] = group.iloc[0]  # 第一条无前值，保留原始
        return result

    result = x.groupby("symbol").transform(hump_transform)
    return result.sort_index()


def ts_median(x, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def calculate_median(series):
        return series.rolling(d, min_periods=d).median()

    # 处理Series且包含symbol列的情况（如果Series有name属性为'symbol'）
    if isinstance(x, pd.Series) and "symbol" in x.index.names:
        return x.groupby("symbol").transform(calculate_median).sort_index()

    # 默认情况：不分组，直接计算整个序列的滚动中位数
    return x.rolling(d, min_periods=d).median().sort_index()


def ts_poly_regression(y, x, d=6, k=1):
    """
    对每个 symbol，在过去 d 天内使用 x, x^2, ..., x^k 拟合 y，返回残差 y - Ey
    """
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")
    k = int(k)
    if k < 0:
        raise ValueError("k must be greater than 0")

    y, x = y.align(x, join="inner")

    def calculate_residuals(group_y, group_x):
        y_vals = group_y.values
        x_vals = group_x.values
        n = len(y_vals)
        result = np.full(n, np.nan)

        for i in range(d - 1, n):
            window_y = y_vals[i - d + 1 : i + 1]
            window_x = x_vals[i - d + 1 : i + 1]

            valid_mask = ~np.isnan(window_y) & ~np.isnan(window_x)
            if valid_mask.sum() < k + 1:
                continue  # 数据不足拟合

            y_win = window_y[valid_mask]
            x_win = window_x[valid_mask]

            # 构造 Vandermonde 矩阵 [x, x^2, ..., x^k]
            X_poly = np.vander(x_win, N=k + 1, increasing=True)  # shape: (d, k+1)

            # 最小二乘拟合：β = (X^T X)^-1 X^T y
            try:
                beta = np.linalg.lstsq(X_poly, y_win, rcond=None)[0]
                x_now = x_vals[i]
                if np.isnan(x_now):
                    continue
                x_now_poly = np.vander([x_now], N=k + 1, increasing=True)
                y_pred = x_now_poly @ beta
                result[i] = y_vals[i] - y_pred[0]
            except np.linalg.LinAlgError:
                continue

        return pd.Series(result, index=group_y.index)

    # 分组处理
    result = y.groupby("symbol").transform(lambda group_y: calculate_residuals(group_y, x.loc[group_y.index]))

    return result.sort_index()


def ts_vector_proj(x, y, d=6):
    d = int(d)
    if d <= 0:
        raise ValueError("参数 d 必须为正整数")

    def proj_calc(x_series, y_series):
        rolling_xy = (x_series * y_series).rolling(d, min_periods=d).sum()
        rolling_yy = (y_series * y_series).rolling(d, min_periods=d).sum()
        # 使用pandas的内置功能处理零值，避免使用np.nan
        proj_coef = rolling_xy / rolling_yy.replace(0, float("nan"))
        return proj_coef * y_series

    result = x.groupby("symbol").transform(lambda group_x: proj_calc(group_x, y.loc[group_x.index]))

    return result.sort_index()


def ts_delta_limit(x, y, limit_volume=0.1):
    # 处理y为标量的情况
    if not hasattr(y, "index"):
        y = pd.Series(y, index=x.index)
    if limit_volume <= 0:
        raise ValueError("limit_volume must be greater than 0")

    # 计算限制后的变化量的向量化实现
    def limit_changes_vectorized(group_x, group_y):
        if len(group_x) <= 1:
            return group_x
        # 计算原始差值
        shifted = group_x.shift(1)
        delta = group_x - shifted

        # 计算每个时间点的最大允许变化量
        max_change = group_y * limit_volume

        # 限制变化量
        limited_delta = delta.clip(lower=-max_change, upper=max_change)

        result = shifted + limited_delta
        result.iloc[0] = group_x.iloc[0]  # 第一条无前值，保留原始
        return result

    # 使用transform而不是apply进行分组处理
    result = x.groupby(level="symbol").transform(lambda group: limit_changes_vectorized(group, y.loc[group.index]))
    return result.sort_index()


def or_operator(input1, input2):
    """
    逻辑 OR 操作符,使用大写or避免函数冲突：若任意一个值为True则返回True，否则返回False。

    兼容以下情况：
      1) input1, input2 都是数值或布尔标量 (int, float, bool)
      2) input1, input2 至少有一个是 Pandas Series
      3) input1, input2 中可能是 list

    规则：
      - 若是标量：非NaN非0 -> True， NaN或0 -> False；bool 保持原值
      - 若是 list -> 转化为 pd.Series 后再进行运算
      - 若是 Series：非NaN非0 -> True， NaN或0 -> False；bool 保持原值
    """

    # --- 辅助函数：将输入统一转为 "布尔型标量" 或 "布尔型 pd.Series" ---
    def to_bool_series_or_scalar(obj):
        def to_bool_scalar(x):
            if isinstance(x, np.bool_):
                return bool(x)
            elif isinstance(x, bool):
                return x
            elif isinstance(x, (int, float)):
                return not (np.isnan(x) or x == 0)
            else:
                # 字符串或其他类型
                return False

        # 1) 标量: 直接返回一个布尔
        if isinstance(obj, (int, float, bool, np.bool_)):
            return to_bool_scalar(obj)
        # 2) list -> 转成一个 pd.Series
        if isinstance(obj, list):
            obj = pd.Series(obj)
        # 3) pd.Series: 逐元素to_bool_scalar
        if isinstance(obj, pd.Series):
            obj.fillna(False)
            return obj.apply(lambda v: to_bool_scalar(v))
        # 4) 其他情况(比如 str, dict等) -> False
        return False

    # ------------------------------------------------------
    # 将输入统一转换为 bool 标量或 bool Series
    b1 = to_bool_series_or_scalar(input1)
    b2 = to_bool_series_or_scalar(input2)

    # 如果两者都是Python布尔标量 => 直接 or
    if isinstance(b1, bool) and isinstance(b2, bool):
        return b1 or b2
    # 如果有一方是标量 & 另一方是Series => 做广播
    if isinstance(b1, bool) and isinstance(b2, pd.Series):
        return (b2 | b1).sort_index()
    if isinstance(b2, bool) and isinstance(b1, pd.Series):
        return (b1 | b2).sort_index()
    # 否则，两者都应该是 pd.Series => 对齐索引后 OR
    result = (b1 | b2).sort_index()
    return result


def and_operator(input1, input2):
    """
    逻辑 AND 操作符,使用大写and避免函数冲突
    """

    # --- 辅助函数：将输入统一转为 "布尔型标量" 或 "布尔型 pd.Series" ---
    def to_bool_series_or_scalar(obj):
        def to_bool_scalar(x):
            if isinstance(x, np.bool_):
                return bool(x)
            elif isinstance(x, bool):
                return x
            elif isinstance(x, (int, float)):
                return not (np.isnan(x) or x == 0)
            else:
                # 字符串或其他类型
                return False

        # 1) 标量: 直接返回一个布尔
        if isinstance(obj, (int, float, bool, np.bool_)):
            return to_bool_scalar(obj)
        # 2) list -> 转成一个 pd.Series
        if isinstance(obj, list):
            obj = pd.Series(obj)
        # 3) pd.Series: 逐元素 to_bool_scalar
        if isinstance(obj, pd.Series):
            # fillna(False) 可让 NaN 直接视为 False
            obj = obj.fillna(False)
            return obj.apply(lambda v: to_bool_scalar(v))
        # 4) 其他情况(比如 str, dict等) -> False
        return False

    # ------------------------------------------------------
    # 将输入统一转换为 bool 标量或 bool Series
    b1 = to_bool_series_or_scalar(input1)
    b2 = to_bool_series_or_scalar(input2)

    # 如果两者都是Python布尔标量 => 直接 and
    if isinstance(b1, bool) and isinstance(b2, bool):
        return b1 and b2
    # 如果有一方是标量 & 另一方是Series => 做广播
    if isinstance(b1, bool) and isinstance(b2, pd.Series):
        return (b2 & b1).sort_index()
    if isinstance(b2, bool) and isinstance(b1, pd.Series):
        return (b1 & b2).sort_index()
    # 否则，两者都应该是 pd.Series => 对齐索引后 AND
    result = (b1 & b2).sort_index()
    return result


def not_operator(obj):
    """
    逻辑 NOT 操作符,使用大写not避免函数冲突
    """

    def to_bool_scalar(x):
        if isinstance(x, np.bool_):
            return not bool(x)
        elif isinstance(x, bool):
            return not x
        elif isinstance(x, (int, float)):
            return bool(np.isnan(x) or x == 0)
        else:
            # 字符串或其他类型
            return True

    # 1) 标量: 直接返回一个布尔
    if isinstance(obj, (int, float, bool, np.bool_)):
        return to_bool_scalar(obj)
    # 2) list -> 转成一个 pd.Series
    if isinstance(obj, list):
        obj = pd.Series(obj)
    # 3) pd.Series: 逐元素 to_bool_scalar
    if isinstance(obj, pd.Series):
        # fillna(False) 可让 NaN 直接视为 False
        obj = obj.fillna(False)
        return obj.apply(lambda v: to_bool_scalar(v)).sort_index()
    # 4) 其他情况(比如 str, dict等) -> False
    return True


def is_not_finite(input):
    if hasattr(input, "index"):
        # 向量化操作处理Series，不使用pandas特有方法
        result = ((np.isnan(input)) | (np.isinf(input))).astype(int)
        return result.sort_index()
    else:
        # 处理标量值，包括numpy标量类型
        if np.isnan(input) or np.isinf(input):
            return 1
        return 0


def if_else(input1, input2, input3):
    # input1不支持list格式
    if isinstance(input1, list):
        return False

    def to_bool_series_or_scalar(obj):
        def to_bool_scalar(x):
            if isinstance(x, np.bool_):
                return bool(x)
            elif isinstance(x, bool):
                return x
            elif isinstance(x, (int, float)):
                return not (np.isnan(x) or x == 0)
            else:
                # 字符串或其他类型
                return False

        # 1) 标量: 直接返回一个布尔
        if isinstance(obj, (int, float, bool, np.bool_)):
            return to_bool_scalar(obj)
        # 2) pd.Series: 逐元素to_bool_scalar
        if isinstance(obj, pd.Series):
            obj.fillna(False)
            return obj.transform(lambda v: to_bool_scalar(v))
        # 3) 其他情况(比如 str, dict,list等,不支持这些类型) -> False
        return False

    mask = to_bool_series_or_scalar(input1)

    if hasattr(mask, "index"):
        if hasattr(input2, "index") and hasattr(input3, "index"):
            # 所有输入都是Series
            result = pd.Series(np.nan, index=input1.index)
            result = input2.where(mask, input3)
        elif hasattr(input2, "index"):
            # input2是Series，input3是标量
            result = pd.Series(np.nan, index=input1.index)
            result = input2.where(mask, input3)
        elif hasattr(input3, "index"):
            # input3是Series，input2是标量
            result = pd.Series(np.nan, index=input1.index)
            result = pd.Series(input2, index=input1.index).where(mask, input3)
        else:
            # input2和input3都是标量
            result = pd.Series(np.where(mask, input2, input3), index=input1.index)

        return result.sort_index()
    else:
        return input2 if mask else input3


def winsorize(x, std=4):
    if std < 0:
        raise ValueError("std must be greater than or equal to 0")
    mean_by_date = x.groupby(level="dt").mean()
    std_by_date = x.groupby(level="dt").std(ddof=1)

    lower_bounds = mean_by_date - std * std_by_date
    upper_bounds = mean_by_date + std * std_by_date

    # 使用向量化操作直接获取每个日期对应的上下限
    dt_values = x.index.get_level_values("dt")
    lower_bound_values = lower_bounds.loc[dt_values].values
    upper_bound_values = upper_bounds.loc[dt_values].values

    # 使用向量化操作进行截断
    result = x.copy()
    result = np.maximum(result, lower_bound_values)
    result = np.minimum(result, upper_bound_values)

    return result.sort_index()


def vector_neut(x, y):
    dot_product = (x * y).groupby(level="dt").sum()
    squared_norm = (y * y).groupby(level="dt").sum()

    projection_scalar = dot_product / squared_norm

    projection = y.mul(projection_scalar, level="dt")

    orthogonal_vector = x - projection

    return orthogonal_vector.sort_index()


def regression_neut(y, x):
    common_index = y.index.intersection(x.index)
    y_aligned = y.loc[common_index]
    x_aligned = x.loc[common_index]

    result = pd.Series(np.nan, index=y.index)

    y_grouped = y_aligned.groupby(level="dt")
    x_grouped = x_aligned.groupby(level="dt")

    y_mean = y_grouped.mean()
    x_mean = x_grouped.mean()

    y_demean = y_aligned - y_mean.reindex(common_index, level="dt")
    x_demean = x_aligned - x_mean.reindex(common_index, level="dt")

    numerator_vec = (y_demean * x_demean).groupby(level="dt").sum()
    denominator_vec = (x_demean**2).groupby(level="dt").sum()

    beta = numerator_vec / denominator_vec
    beta = beta.replace([np.inf, -np.inf], np.nan)

    beta_expanded = beta.reindex(common_index, level="dt")
    residuals = y_aligned - beta_expanded * x_aligned

    result.loc[common_index] = residuals

    return result.sort_index()


def zscore(x):
    means = x.groupby(level="dt").mean()
    stds = x.groupby(level="dt").std(ddof=1)

    x_mean = x.index.get_level_values("dt").map(means)
    x_std = x.index.get_level_values("dt").map(stds)

    result = (x - x_mean) / x_std
    return result.sort_index()


def scale(x, scale=1, longscale=1, shortscale=1):
    """
    scale 就是控制“你有多少钱分配给多头和空头”，而不是让因子值随意大小起飞。
    参数:
        x: pd.Series，带有MultiIndex（level包含'dt'）
        scale: 总体缩放比例
        longscale: 多头资金占比（权重和）
        shortscale: 空头资金占比（权重和）
    """
    if not isinstance(x, pd.Series):
        if isinstance(x, (int, float, np.number)):
            if x > 0:
                return longscale * scale
            elif x < 0:
                return shortscale * scale
        return False
    if scale <= 0:
        raise ValueError("scale must be greater than 0")
    if longscale < 0:
        raise ValueError("longscale must be greater than or equal to 0")
    if shortscale < 0:
        raise ValueError("shortscale must be greater than or equal to 0")

    # 提取 index
    dt_index = x.index.get_level_values("dt")

    # 多头和空头掩码
    pos_mask = x > 0
    neg_mask = x < 0

    # 分别按 dt 分组求和
    sum_pos = x.where(pos_mask).groupby(dt_index).sum()
    sum_neg_abs = -x.where(neg_mask).groupby(dt_index).sum()

    # 映射回原数据
    factor_long = (longscale / sum_pos).reindex(dt_index).values
    factor_short = (shortscale / sum_neg_abs).reindex(dt_index).values

    # 初始化返回 Series
    result = pd.Series(0, index=x.index, dtype="float64")

    # 分别缩放多头和空头
    result[pos_mask] = x[pos_mask] * factor_long[pos_mask]
    result[neg_mask] = x[neg_mask] * factor_short[neg_mask]

    # 若需要整体缩放
    if scale != 1:
        sum_abs = result.abs().groupby(dt_index).sum()
        factor_all = (scale / sum_abs).reindex(dt_index).values
        result = result * factor_all

    return result.sort_index()


def quantile(x, driver="gaussian", sigma=1.0):
    ranked = x.groupby(level="dt").rank(pct=True)
    ranked = ranked.clip(lower=1e-8, upper=1 - 1e-8)
    if driver == "gaussian":
        z = 2 * ranked - 1
        # 使用numpy的erf函数的逆函数，完全向量化
        result = np.sqrt(2) * sigma * np.arctanh(z)
    elif driver == "cauchy":
        v_minus_half = ranked - 0.5
        pi_times_v = np.pi * v_minus_half
        result = sigma * np.tan(pi_times_v)
    elif driver == "uniform":
        ranked_means = ranked.groupby(level="dt").transform("mean")
        result = ranked - ranked_means
    else:
        result = ranked

    return result.sort_index()


def vec_max(x):
    """
    vec_max(x)：返回每个时间点横截面（即所有 symbol）中 x 的最大值。
    """
    # 处理 MultiIndex（常见情况：['dt', 'symbol']）
    if isinstance(x.index, pd.MultiIndex) and "dt" in x.index.names:
        return x.groupby(level="dt").transform("max").sort_index()

    # 若为单层索引（或无命名的 index），假设为 'dt'
    elif isinstance(x.index, pd.Index):
        # 临时创建 dt 分组标签（这里保守处理）
        level_name = x.index.name if x.index.name else 0
        return x.groupby(level=level_name).transform("max").sort_index()
    else:
        return None


def bucket(x, range=None, buckets=None):
    # 参数互斥性检查
    if range is None and buckets is None:
        return None
    if range is not None and buckets is not None:
        range = None  # 优先使用buckets

    # 处理输入为Series的情况
    if isinstance(x, pd.Series):
        # 准备分桶边界
        if range is not None:
            try:
                if isinstance(range, str):
                    # 处理字符串格式的range
                    parts = [float(part.strip()) for part in range.split(",")]
                    if len(parts) != 3:
                        return pd.Series(np.nan, index=x.index).sort_index()
                    start, end, step = parts
                    bins = np.arange(start, end + step / 2, step)
                else:
                    # 处理元组/列表格式的range
                    if len(range) != 3:
                        return pd.Series(np.nan, index=x.index).sort_index()
                    start, end, step = range
                    bins = np.arange(start, end + step / 2, step)
            except:
                return pd.Series(np.nan, index=x.index).sort_index()
        elif buckets is not None:
            try:
                if isinstance(buckets, str):
                    # 处理字符串格式的buckets
                    bins = np.array([float(b.strip()) for b in buckets.split(",")])
                else:
                    # 处理列表/数组格式的buckets
                    bins = np.array(buckets)
            except:
                return pd.Series(np.nan, index=x.index).sort_index()
        else:
            # 如果既没有range也没有buckets，返回NaN
            return pd.Series(np.nan, index=x.index).sort_index()

        # 使用pd.cut进行分桶
        # 添加无限边界：[-inf, b1, ..., bn, inf]
        bins = np.concatenate(([-np.inf], bins, [np.inf]))
        result = pd.cut(x, bins=bins, labels=False, include_lowest=True)

        return result.sort_index()
    else:
        # 处理非Series输入（标量或数组）
        try:
            if range is not None:
                if isinstance(range, str):
                    parts = [float(part.strip()) for part in range.split(",")]
                    if len(parts) != 3:
                        return np.nan
                    start, end, step = parts
                    bins = np.arange(start, end + step / 2, step)
                else:
                    if len(range) != 3:
                        return np.nan
                    start, end, step = range
                    bins = np.arange(start, end + step / 2, step)
            elif buckets is not None:
                if isinstance(buckets, str):
                    bins = np.array([float(b.strip()) for b in buckets.split(",")])
                else:
                    bins = np.array(buckets)
            else:
                return np.nan

            # 使用pd.cut保持与Series处理一致的分桶逻辑
            x_array = np.atleast_1d(x)
            # 添加无限边界：[-inf, b1, ..., bn, inf]
            bins = np.concatenate(([-np.inf], bins, [np.inf]))
            result = pd.cut(x_array, bins=bins, labels=False, include_lowest=True)
            result = np.nan_to_num(result, nan=-1)
            result = np.clip(result, 0, None)  # 确保结果不小于0

            return result
        except:
            return np.nan if np.isscalar(x) else np.full_like(x, np.nan, dtype=float)


def group_zscore(x, group):
    df = pd.DataFrame({"x": x, "group": group})

    if "dt" not in df.index.names:
        return None

    # 按照 (dt, group) 分组计算均值和标准差
    # groupby 传入一个 list: [df.index.get_level_values('dt'), df['group']]
    df["mean"] = df.groupby([df.index.get_level_values("dt"), df["group"]])["x"].transform("mean")

    df["std"] = df.groupby([df.index.get_level_values("dt"), df["group"]])["x"].transform("std", ddof=1)

    # 计算 zscore
    df["zscore"] = (df["x"] - df["mean"]) / df["std"]

    # 返回与 x 相同索引的 zscore
    # 如果组内只有一个样本，std=0，zscore会是 NaN 或 inf，这里可视情况处理
    return df["zscore"].sort_index()


def trade_when(x, y, z):
    """y是用于保存的Alpha值,这个操作符不就和if_else几乎一样的吗？"""
    # x不支持list格式
    if isinstance(x, list):
        return False

    def to_bool_series_or_scalar(obj):
        def to_bool_scalar(x):
            if isinstance(x, np.bool_):
                return not bool(x)
            elif isinstance(x, bool):
                return not x
            elif isinstance(x, (int, float)):
                return bool(np.isnan(x) or x == 0)
            else:
                # 字符串或其他类型
                return True

        # 1) 标量: 直接返回一个布尔
        if isinstance(obj, (int, float, bool, np.bool_)):
            return to_bool_scalar(obj)
        # 2) pd.Series: 逐元素to_bool_scalar
        if isinstance(obj, pd.Series):
            obj.fillna(False)
            return obj.transform(lambda v: to_bool_scalar(v))
        # 3) 其他情况(比如 str, dict,list等,不支持这些类型) -> False
        return True

    mask = to_bool_series_or_scalar(x)

    if hasattr(mask, "index"):
        if hasattr(y, "index") and hasattr(z, "index"):
            # 所有输入都是Series
            result = pd.Series(np.nan, index=x.index)
            result = y.where(mask, z)
        elif hasattr(y, "index"):
            # y是Series，z是标量
            result = pd.Series(np.nan, index=x.index)
            result = y.where(mask, z)
        elif hasattr(z, "index"):
            # z是Series，y是标量
            result = pd.Series(np.nan, index=x.index)
            result = pd.Series(y, index=x.index).where(mask, z)
        else:
            # y和z都是标量
            result = pd.Series(np.where(mask, y, z), index=x.index)

        return result.sort_index()
    else:
        return y if mask else z


def group_rank(x, group):
    df = pd.DataFrame({"x": x, "group": group})

    df["rank"] = df.groupby([df.index.get_level_values("dt"), df["group"]])["x"].rank(pct=True)

    return df["rank"].sort_index()


def group_normalize(x, group, constantCheck=False, tolerance=0.01, scale=1.0):
    df = pd.DataFrame({"x": x, "group": group})
    """
    sum_abs = df['x'].abs().groupby([df.index.get_level_values('dt'), df['group']]).sum()

    # 将每行对应 (dt, group) 的结果映射回 df（注意多重索引对齐）
    df['abs_sum'] = sum_abs.loc[
        pd.MultiIndex.from_arrays([df.index.get_level_values('dt'), df['group']])
    ].to_numpy()
    """
    df_ = df.copy()
    df_["x"] = df_["x"].abs()
    df["abs_sum"] = df_.groupby([df.index.get_level_values("dt"), df["group"]])["x"].transform("sum")

    if constantCheck:
        # 分组总和若小于 tolerance，就不做归一化（示例：保留原值）
        is_too_small = df["abs_sum"] < tolerance
        df["normalized"] = np.where(is_too_small, df["x"], df["x"] / df["abs_sum"] * scale)  # 也可换成其它特殊处理
    else:
        # 普通归一化
        df["normalized"] = df["x"] / df["abs_sum"] * scale

    # 若 abs_sum=0，则分母为 0，将这部分值置 0 或根据实际需求处理
    df.loc[df["abs_sum"] == 0, "normalized"] = 0

    # 返回结果并按原索引顺序
    return df["normalized"].sort_index()


def group_scale(x, group):
    df = pd.DataFrame({"x": x, "group": group})

    if "dt" not in df.index.names:
        return None

    df["mean"] = df.groupby([df.index.get_level_values("dt"), df["group"]])["x"].transform("mean")
    df["min"] = df.groupby([df.index.get_level_values("dt"), df["group"]])["x"].transform("min")
    df["max"] = df.groupby([df.index.get_level_values("dt"), df["group"]])["x"].transform("max")

    df["zscore"] = (df["x"] - df["mean"]) / (df["max"] - df["min"])

    return df["zscore"].sort_index()


def densify(s):
    # 如果不是Series类型，直接返回
    if not (isinstance(s, pd.Series)):
        return s
    else:
        if "dt" not in s.index.names:
            return s
        else:
            return s.astype("category").cat.codes.sort_index()
