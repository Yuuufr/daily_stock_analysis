# -*- coding: utf-8 -*-
"""
Market Regime Definitions
"""

from enum import Enum


class MarketRegime(Enum):
    """市场状态枚举"""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    
    BULL_CONFIRM = "bull_confirm"
    BULL_EXHAUSTED = "bull_exhausted"
    BEAR_CONFIRM = "bear_confirm"
    BEAR_EXHAUSTED = "bear_exhausted"
    NEUTRAL_LOW_VOL = "neutral_low_vol"
    NEUTRAL_HIGH_VOL = "neutral_high_vol"


class RegimeMetadata:
    """Regime 元数据"""
    
    DESCRIPTIONS = {
        MarketRegime.BULL: "市场处于上涨趋势，建议偏多策略",
        MarketRegime.BEAR: "市场处于下跌趋势，建议偏空或防守策略",
        MarketRegime.NEUTRAL: "市场处于震荡格局，建议高抛低吸或观望",
        MarketRegime.BULL_CONFIRM: "强势多头格局，趋势明确，顺势而为",
        MarketRegime.BULL_EXHAUSTED: "牛市末期，警惕顶部信号，注意利润保护",
        MarketRegime.BEAR_CONFIRM: "强势空头格局，下跌趋势明确，严控仓位",
        MarketRegime.BEAR_EXHAUSTED: "熊市末期，警惕超跌反弹机会",
        MarketRegime.NEUTRAL_LOW_VOL: "低波动震荡，区间整理为主",
        MarketRegime.NEUTRAL_HIGH_VOL: "高波动震荡，择机交易，波段操作",
    }
    
    DEFAULT_STRATEGY = {
        MarketRegime.BULL: {
            "name": "牛市进攻策略",
            "risk_level": "medium",
            "position_preference": 0.7,
        },
        MarketRegime.BEAR: {
            "name": "熊市防守策略", 
            "risk_level": "high",
            "position_preference": 0.2,
        },
        MarketRegime.NEUTRAL: {
            "name": "震荡市策略",
            "risk_level": "medium",
            "position_preference": 0.5,
        },
    }
