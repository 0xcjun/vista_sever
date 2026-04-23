# TA-Lib 技术指标算子 (52)

通过 talib-rs 封装的经典技术分析指标。多输出算子（如 MACD、布林带）使用线程本地缓存避免重复计算。

## 动量指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSMom | `TSMom($x, period=10)` | 动量 x[i] - x[i-period] |
| TSRoc | `TSRoc($x, period)` | 变化率 (x-x[n])/x[n]×100 |
| TSRocP | `TSRocP($x, period)` | ROC 百分比 |
| TSRocR | `TSRocR($x, period)` | ROC 比率 x/x[n] |
| TSTrix | `TSTrix($x, period=30)` | 三重 EMA 变化率 |
| TSCmo | `TSCmo($x, period=14)` | Chande 动量振荡器 |
| TSRsi | `TSRsi($x, period=14)` | RSI 相对强弱指数 |

## 振荡器

| 算子 | 语法 | 说明 |
|------|------|------|
| TSApo | `TSApo($x, fast=12, slow=26)` | 绝对价格振荡器 |
| TSPpo | `TSPpo($x, fast=12, slow=26)` | 百分比价格振荡器 |
| TSMacd | `TSMacd($x, fast=12, slow=26, signal=9)` | MACD 线 |
| TSMacdSig | `TSMacdSig($x, fast=12, slow=26, signal=9)` | MACD 信号线 |
| TSMacdHist | `TSMacdHist($x, fast=12, slow=26, signal=9)` | MACD 柱状图 |

## 布林带

| 算子 | 语法 | 说明 |
|------|------|------|
| TSBbUp | `TSBbUp($x, period, nbdevup, nbdevdn, matype)` | 上轨 |
| TSBbMid | `TSBbMid($x, period, nbdevup, nbdevdn, matype)` | 中轨 |
| TSBbLow | `TSBbLow($x, period, nbdevup, nbdevdn, matype)` | 下轨 |

## 趋势指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSAdx | `TSAdx($high, $low, $close, period=14)` | ADX 平均方向指数 |
| TSPlusDi | `TSPlusDi($high, $low, $close, period=14)` | +DI 上升方向指标 |
| TSMinusDi | `TSMinusDi($high, $low, $close, period=14)` | -DI 下降方向指标 |
| TSPlusDm | `TSPlusDm($high, $low, period=14)` | +DM 上升方向移动 |
| TSMinusDm | `TSMinusDm($high, $low, period=14)` | -DM 下降方向移动 |
| TSDx | `TSDx($high, $low, $close, period=14)` | 方向指数 |
| TSAroonUp | `TSAroonUp($high, $low, period=14)` | Aroon Up |
| TSAroonDown | `TSAroonDown($high, $low, period=14)` | Aroon Down |
| TSAroonOsc | `TSAroonOsc($high, $low, period=14)` | Aroon 振荡器 |

## 波动率指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSAtr | `TSAtr($high, $low, $close, period=14)` | ATR 平均真实波幅 |
| TSTrange | `TSTrange($high, $low, $close)` | 真实波幅（单期） |
| TSStdDev | `TSStdDev($x, period=14, nbdev)` | TA-Lib 标准差 |
| TSTaVar | `TsTaVar($x, period=14)` | TA-Lib 方差 |

## 移动平均

| 算子 | 语法 | 说明 |
|------|------|------|
| TSDema | `TsDema($x, period=30)` | DEMA 双重指数移动平均 |
| TSKama | `TsKama($x, period=30)` | KAMA 自适应移动平均 |
| TSTema | `TsTema($x, period=30)` | TEMA 三重指数移动平均 |
| TSTrima | `TsTrima($x, period=30)` | 三角移动平均 |
| TSTaWma | `TsTaWma($x, period=14)` | TA-Lib 加权移动平均 |
| TSMama | `TSMama($x, fast=0.5, slow=0.05)` | MESA 自适应均线 |
| TSFama | `TSFama($x, fast=0.5, slow=0.05)` | MAMA 跟随线 |

## 回归与统计

| 算子 | 语法 | 说明 |
|------|------|------|
| TSLinReg | `TSLinReg($x, period=14)` | 线性回归拟合值 |
| TSLinRegAngle | `TSLinRegAngle($x, period=14)` | 回归角度（度） |
| TSLinRegSlope | `TSLinRegSlope($x, period=14)` | 回归斜率 |
| TSLinRegInt | `TSLinRegInt($x, period=14)` | 回归截距 |
| TSTsf | `TsTsf($x, period=14)` | 时间序列预测 |

## 价格类指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSBop | `TSBop($open, $high, $low, $close)` | 力量平衡 (close-open)/(high-low) |
| TSCci | `TSCci($high, $low, $close, period=14)` | 商品通道指数 |
| TSMidPoint | `TsMidPoint($x, period=14)` | (Max+Min)/2 |
| TSMidPrice | `TSMidPrice($high, $low, period=14)` | (最高+最低)/2 |

## SAR

| 算子 | 语法 | 说明 |
|------|------|------|
| TSSar | `TSSar($high, $low, accel=0.02, max=0.2)` | 抛物线 SAR |
| TSSarExt | `TSSarExt($high, $low, ...)` | 扩展 SAR |

## 成交量指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSAd | `TSAd($high, $low, $close, $vol)` | A/D 累积分配线 |
| TSAdOsc | `TSAdOsc($high, $low, $close, $vol, fast=3, slow=10)` | A/D 振荡器 |
| TSObv | `TSObv($close, $vol)` | OBV 能量潮 |
| TSMfi | `TSMfi($high, $low, $close, $vol, period=14)` | 资金流量指数 |

## 随机指标

| 算子 | 语法 | 说明 |
|------|------|------|
| TSStochK | `TSStochK($high, $low, $close, period, k, k_ma, d, d_ma)` | 随机指标 %K |
| TSStochD | `TSStochD($high, $low, $close, period, k, k_ma, d, d_ma)` | 随机指标 %D |

## 示例

```python
cf.compute_factors(data, [
    "TSRsi($close, 14)",                                  # RSI
    "TSMacd($close, 12, 26, 9)",                          # MACD
    "TSAdx($high, $low, $close, 14)",                     # ADX
    "TSAtr($high, $low, $close, 14)",                     # ATR
    "CSRank(TSRsi($close, 14))",                          # RSI 截面排名
    "TSBbUp($close, 20, 2, 2, 0) - TSBbLow($close, 20, 2, 2, 0)",  # 布林带宽度
])
```
