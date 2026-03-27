# -*- coding: utf-8 -*-
"""
Quant Module - Quantitative Research System

模块职责：
1. 自动市场 Regime 判断（牛/熊/震荡）
2. AI 自适应因子权重
3. Top10 胜率实时评分
4. 自动淘汰失效策略
5. 因子版本管理（Quant Research Flow）
6. 周末自动训练模型
"""

from src.quant.regime.regimes import MarketRegime
from src.quant.regime.detector import RegimeDetector

__all__ = [
    "MarketRegime",
    "RegimeDetector",
]
