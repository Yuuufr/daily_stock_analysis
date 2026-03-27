# -*- coding: utf-8 -*-
"""
Built-in Factors

内置因子实现
"""

import pandas as pd
import numpy as np
from typing import Optional

from src.quant.factors.base import BaseFactor, FactorRegistry


class MomentumFactor(BaseFactor):
    """动量因子"""

    name = "momentum"
    version = "1.0.0"
    description = "N日动量因子（收益率）"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].pct_change(self.period)


class VolatilityFactor(BaseFactor):
    """波动率因子"""

    name = "volatility"
    version = "1.0.0"
    description = "N日收益波动率"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        return returns.rolling(self.period).std()


class TrendFactor(BaseFactor):
    """趋势因子（MA距离）"""

    name = "trend"
    version = "1.0.0"
    description = "收盘价与MA20的距离"

    def __init__(self, ma_period: int = 20):
        super().__init__(ma_period=ma_period)
        self.ma_period = ma_period

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        ma = df["close"].rolling(self.ma_period).mean()
        return (df["close"] - ma) / ma


class VolumeFactor(BaseFactor):
    """量价配合因子"""

    name = "volume_price"
    version = "1.0.0"
    description = "成交量与价格趋势的配合度"

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        price_change = df["close"].pct_change()
        volume_change = df["volume"].pct_change()
        return price_change * volume_change


class RSIFactor(BaseFactor):
    """RSI 因子"""

    name = "rsi"
    version = "1.0.0"
    description = "相对强弱指数"

    def __init__(self, period: int = 14):
        super().__init__(period=period)
        self.period = period

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi


class MACDFactor(BaseFactor):
    """MACD 因子"""

    name = "macd"
    version = "1.0.0"
    description = "MACD 指标（DIF 线）"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(fast=fast, slow=slow, signal=signal)
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        return dif


class BollingerBandFactor(BaseFactor):
    """布林带因子"""

    name = "bollinger"
    version = "1.0.0"
    description = "布林带位置（0-1 之间）"

    def __init__(self, period: int = 20, std_dev: int = 2):
        super().__init__(period=period, std_dev=std_dev)
        self.period = period
        self.std_dev = std_dev

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        ma = df["close"].rolling(self.period).mean()
        std = df["close"].rolling(self.period).std()
        upper = ma + self.std_dev * std
        lower = ma - self.std_dev * std
        return (df["close"] - lower) / (upper - lower)


class VolumeRatioFactor(BaseFactor):
    """量比因子"""

    name = "volume_ratio"
    version = "1.0.0"
    description = "当日成交量与5日均量的比值"

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        vol_ma5 = df["volume"].rolling(5).mean()
        return df["volume"] / vol_ma5


class PriceVolumeCorrelationFactor(BaseFactor):
    """量价相关性因子"""

    name = "pv_correlation"
    version = "1.0.0"
    description = "N日内价格与成交量的相关性"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        corr = returns.rolling(self.period).corr(df["volume"].pct_change())
        return corr


def register_builtin_factors():
    """注册所有内置因子"""
    factors = [
        MomentumFactor(),
        VolatilityFactor(),
        TrendFactor(),
        VolumeFactor(),
        RSIFactor(),
        MACDFactor(),
        BollingerBandFactor(),
        VolumeRatioFactor(),
        PriceVolumeCorrelationFactor(),
    ]

    for factor in factors:
        FactorRegistry.register(factor)

    return [f.name for f in factors]
