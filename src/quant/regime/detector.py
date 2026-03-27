# -*- coding: utf-8 -*-
"""
Market Regime Detector

自动市场 Regime 判断（牛/熊/震荡）
多因子综合评分：
1. 均线族方向（MA5/MA10/MA20/MA60）
2. 趋势强度（ADX）
3. 波动率（布林带宽度）
4. 动量（RSI）
5. 成交量变化
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

from src.quant.regime.regimes import MarketRegime, RegimeMetadata

logger = logging.getLogger(__name__)


@dataclass
class RegimeDetectionResult:
    """Regime 检测结果"""
    regime: MarketRegime
    total_score: float
    ma_score: float
    trend_score: float
    vol_score: float
    momentum_score: float
    volume_score: float
    interpretation: str
    details: Dict


class RegimeDetector:
    """市场 Regime 自动检测器"""

    DEFAULT_LOOKBACK_DAYS = 60
    INDEX_CODE_CN = "000001"  # 上证指数
    INDEX_CODE_US = "SPY"     # 美股 SPY ETF

    def __init__(self, lookback_days: int = None):
        self.lookback_days = lookback_days or self.DEFAULT_LOOKBACK_DAYS

    def detect(self, index_code: str = None) -> Tuple[MarketRegime, Dict]:
        """
        检测当前市场 Regime

        Args:
            index_code: 指数代码，默认使用上证指数

        Returns:
            Tuple[MarketRegime, Dict] - (regime, details)
        """
        index_code = index_code or self.INDEX_CODE_CN

        try:
            df = self._load_index_data(index_code)
            if df is None or len(df) < 20:
                logger.warning(f"数据不足，无法准确判断 Regime")
                return MarketRegime.NEUTRAL, {
                    "reason": "数据不足",
                    "total_score": 0.0
                }

            df = df.tail(self.lookback_days)

            ma_score = self._ma_direction_score(df)
            trend_score = self._adx_score(df)
            vol_score = self._volatility_score(df)
            momentum_score = self._momentum_score(df)
            volume_score = self._volume_score(df)

            total_score = (
                ma_score * 0.25 +
                trend_score * 0.20 +
                vol_score * 0.15 +
                momentum_score * 0.25 +
                volume_score * 0.15
            )

            regime = self._score_to_regime(total_score)
            interpretation = RegimeMetadata.DESCRIPTIONS.get(
                regime,
                "市场状态未知"
            )

            result = RegimeDetectionResult(
                regime=regime,
                total_score=round(total_score, 4),
                ma_score=round(ma_score, 4),
                trend_score=round(trend_score, 4),
                vol_score=round(vol_score, 4),
                momentum_score=round(momentum_score, 4),
                volume_score=round(volume_score, 4),
                interpretation=interpretation,
                details={
                    "index_code": index_code,
                    "data_points": len(df),
                    "bull_signals": self._count_bull_signals(df),
                    "bear_signals": self._count_bear_signals(df)
                }
            )

            return regime, {
                "total_score": result.total_score,
                "ma_score": result.ma_score,
                "trend_score": result.trend_score,
                "vol_score": result.vol_score,
                "momentum_score": result.momentum_score,
                "volume_score": result.volume_score,
                "interpretation": result.interpretation,
                "details": result.details
            }

        except Exception as e:
            logger.error(f"Regime 检测失败: {e}")
            return MarketRegime.NEUTRAL, {
                "reason": str(e),
                "total_score": 0.0
            }

    def _load_index_data(self, index_code: str) -> Optional[pd.DataFrame]:
        """加载指数数据"""
        try:
            from src.quant.data import HistoricalDataManager

            dm = HistoricalDataManager()
            df = dm.load(index_code)
            return df
        except Exception as e:
            logger.debug(f"无法从本地加载指数数据，尝试实时获取: {e}")

        try:
            from data_provider import DataFetcherManager
            from datetime import datetime, timedelta

            fetcher = DataFetcherManager()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days * 2)

            result = fetcher.get_daily_data(
                index_code,
                start_date=start_date,
                end_date=end_date
            )

            if isinstance(result, tuple):
                df, _ = result
                return df
            return result

        except Exception as e:
            logger.error(f"无法获取指数数据: {e}")
            return None

    def _ma_direction_score(self, df: pd.DataFrame) -> float:
        """
        均线方向得分

        逻辑：
        - MA5 > MA10 > MA20 > MA60: 看多 (+1)
        - MA5 < MA10 < MA20 < MA60: 看空 (-1)
        - 其他: 震荡 (0)
        """
        if "close" not in df.columns:
            return 0.0

        close = df["close"]
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        if ma60.iloc[-1] != ma60.iloc[-1]:  # NaN check
            ma60 = close.rolling(min(60, len(close))).mean()

        latest = {
            "ma5_ma10": (ma5.iloc[-1] - ma10.iloc[-1]) / ma10.iloc[-1] if ma10.iloc[-1] != 0 else 0,
            "ma10_ma20": (ma10.iloc[-1] - ma20.iloc[-1]) / ma20.iloc[-1] if ma20.iloc[-1] != 0 else 0,
            "ma20_ma60": (ma20.iloc[-1] - ma60.iloc[-1]) / ma60.iloc[-1] if ma60.iloc[-1] != 0 else 0,
        }

        score = 0.0
        for diff_pct in latest.values():
            if abs(diff_pct) < 0.001:
                score += 0.0
            elif diff_pct > 0:
                score += 0.33
            else:
                score -= 0.33

        return max(-1.0, min(1.0, score))

    def _adx_score(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        ADX 趋势强度得分

        - ADX > 25: 趋势明确
        - ADX > 40: 趋势强劲
        - ADX < 20: 震荡
        """
        if "high" not in df.columns or "low" not in df.columns:
            return 0.0

        high = df["high"]
        low = df["low"]
        close = df["close"]

        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period * 2).mean()

        adx_val = adx.iloc[-1] if not adx.empty else 20
        price_trend = close.iloc[-1] / close.iloc[-20] - 1 if len(close) >= 20 else 0

        if adx_val > 40:
            return 0.8 if price_trend > 0 else -0.8
        elif adx_val > 25:
            return 0.5 if price_trend > 0 else -0.5
        elif adx_val < 20:
            return 0.0
        else:
            return 0.3 if price_trend > 0 else -0.3

    def _volatility_score(self, df: pd.DataFrame) -> float:
        """
        波动率得分

        - 低波动（布林带收窄）: 震荡
        - 高波动（布林带扩张）: 注意趋势转换
        """
        if "close" not in df.columns:
            return 0.0

        close = df["close"]
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()

        upper_band = ma20 + 2 * std20
        lower_band = ma20 - 2 * std20

        bandwidth = (upper_band - lower_band) / ma20
        latest_bandwidth = bandwidth.iloc[-1] if not bandwidth.empty else 0.1

        volatility_pct = latest_bandwidth * 100

        if volatility_pct < 5:
            return 0.0
        elif volatility_pct > 15:
            return -0.2
        else:
            return 0.1

    def _momentum_score(self, df: pd.DataFrame) -> float:
        """
        RSI 动量得分

        - RSI > 70: 超买 (-0.3)
        - RSI < 30: 超卖 (+0.3)
        - 50 < RSI < 70 / 30 < RSI < 50: 中性
        """
        if "close" not in df.columns:
            return 0.0

        close = df["close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1] if not rsi.empty else 50

        if rsi_val > 75:
            return -0.4
        elif rsi_val > 65:
            return -0.2
        elif rsi_val < 25:
            return 0.4
        elif rsi_val < 35:
            return 0.2
        else:
            return (rsi_val - 50) / 100

    def _volume_score(self, df: pd.DataFrame) -> float:
        """
        成交量得分

        - 放量上涨: +0.3
        - 缩量上涨: -0.1
        - 放量下跌: -0.3
        - 缩量下跌: +0.1
        """
        if "volume" not in df.columns or "close" not in df.columns:
            return 0.0

        volume = df["volume"]
        close = df["close"]

        vol_ma5 = volume.rolling(5).mean()
        vol_ma20 = volume.rolling(20).mean()

        latest_vol_ratio = volume.iloc[-1] / vol_ma20.iloc[-1] if vol_ma20.iloc[-1] != 0 else 1
        price_change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0

        if latest_vol_ratio > 1.5:
            if price_change > 0.02:
                return 0.4
            elif price_change < -0.02:
                return -0.4
            else:
                return 0.0
        elif latest_vol_ratio < 0.7:
            if price_change > 0:
                return -0.1
            else:
                return 0.1
        else:
            return 0.2 if price_change > 0 else -0.2

    def _score_to_regime(self, score: float) -> MarketRegime:
        """综合得分转换为 Regime"""
        if score > 0.25:
            return MarketRegime.BULL
        elif score < -0.25:
            return MarketRegime.BEAR
        return MarketRegime.NEUTRAL

    def _count_bull_signals(self, df: pd.DataFrame) -> int:
        """统计看多信号数量"""
        signals = 0
        if "close" in df.columns:
            ma5 = df["close"].rolling(5).mean()
            ma10 = df["close"].rolling(10).mean()
            if ma5.iloc[-1] > ma10.iloc[-1]:
                signals += 1
        return signals

    def _count_bear_signals(self, df: pd.DataFrame) -> int:
        """统计看空信号数量"""
        signals = 0
        if "close" in df.columns:
            ma5 = df["close"].rolling(5).mean()
            ma10 = df["close"].rolling(10).mean()
            if ma5.iloc[-1] < ma10.iloc[-1]:
                signals += 1
        return signals

    def get_adaptive_strategy(self) -> Dict:
        """
        根据当前 Regime 返回自适应策略配置

        供 Agent 系统和 Pipeline 使用
        """
        regime, details = self.detect()

        strategy = {
            "bull": {
                "name": "牛市进攻策略",
                "description": "偏多趋势，顺势而为",
                "risk_level": "medium",
                "position_preference": 0.7,
                "indicators": ["MA5>MA10>MA20", "MACD金叉", "RSI<70"],
                "factor_weights": {
                    "momentum": 0.4,
                    "trend": 0.3,
                    "volume": 0.15,
                    "volatility": 0.15
                }
            },
            "bear": {
                "name": "熊市防守策略",
                "description": "偏空或观望，严格止损",
                "risk_level": "high",
                "position_preference": 0.2,
                "indicators": ["MA5<MA10<MA20", "MACD死叉", "RSI>30"],
                "factor_weights": {
                    "momentum": 0.2,
                    "trend": 0.2,
                    "volume": 0.2,
                    "volatility": 0.4
                }
            },
            "neutral": {
                "name": "震荡市策略",
                "description": "高抛低吸，快进快出",
                "risk_level": "medium",
                "position_preference": 0.5,
                "indicators": ["布林带上下轨", "KDJ超买超卖", "量能变化"],
                "factor_weights": {
                    "momentum": 0.25,
                    "trend": 0.25,
                    "volume": 0.25,
                    "volatility": 0.25
                }
            }
        }

        return strategy.get(regime.value, strategy["neutral"])
