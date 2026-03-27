# -*- coding: utf-8 -*-
"""
Realtime Strategy Scorer

Top10 胜率实时评分
AI 自适应因子权重
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StrategyScore:
    """策略评分"""
    strategy_id: str
    strategy_name: str
    win_rate: float
    avg_return: float
    max_drawdown: float
    sample_count: int
    regime_fit: float
    composite_score: float
    updated_at: datetime


class RealtimeScorer:
    """
    Top10 胜率实时评分器
    
    评分因子：
    1. 胜率 (win_rate)
    2. 平均收益 (avg_return)
    3. 最大回撤 (max_drawdown)
    4. 样本数量 (sample_count)
    5. Regime 适应性 (regime_fit)
    """

    DEFAULT_WEIGHTS = {
        "win_rate": 0.35,
        "avg_return": 0.25,
        "max_drawdown": 0.20,
        "sample_count": 0.10,
        "regime_fit": 0.10
    }

    def __init__(self, regime_detector=None):
        self.regime_detector = regime_detector
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self._score_history: List[Dict] = []

    def update_weights(self, market_data: Dict = None):
        """
        AI 自适应因子权重调整

        根据当前市场特征动态调整各因子权重
        """
        try:
            if self.regime_detector:
                current_regime, _ = self.regime_detector.detect()
                regime_value = current_regime.value if current_regime else "neutral"
            else:
                regime_value = "neutral"
        except Exception:
            regime_value = "neutral"

        old_weights = self.weights.copy()

        if regime_value == "bull":
            self.weights["win_rate"] = 0.30
            self.weights["avg_return"] = 0.35
            self.weights["max_drawdown"] = 0.15
        elif regime_value == "bear":
            self.weights["max_drawdown"] = 0.35
            self.weights["win_rate"] = 0.30
            self.weights["avg_return"] = 0.10
        else:
            self.weights = self.DEFAULT_WEIGHTS.copy()

        self._score_history.append({
            "timestamp": datetime.now(),
            "regime": regime_value,
            "weights": self.weights.copy(),
            "old_weights": old_weights
        })

    def score_strategy(
        self,
        strategy_id: str,
        history_df,
        regime: str
    ) -> Optional[StrategyScore]:
        """
        计算单一策略评分

        Args:
            strategy_id: 策略 ID
            history_df: 历史信号 DataFrame，需包含：
                - hit: 是否盈利
                - future_return: 未来收益
            regime: 当前市场 Regime

        Returns:
            StrategyScore
        """
        if history_df is None or len(history_df) < 10:
            return None

        total = len(history_df)
        wins = history_df["hit"].sum() if "hit" in history_df.columns else 0
        win_rate = wins / total if total > 0 else 0

        avg_return = 0.0
        if "future_return" in history_df.columns:
            avg_return = history_df["future_return"].mean()

        max_drawdown = self._calc_max_drawdown(
            history_df["future_return"].tolist() if "future_return" in history_df.columns else [0]
        )

        recent = history_df.tail(min(30, len(history_df)))
        recent_regime = recent[recent.get("regime", None) == regime]
        regime_fit = len(recent_regime) / len(recent) if len(recent) > 0 else 0.5

        composite = (
            self.weights["win_rate"] * win_rate +
            self.weights["avg_return"] * min(max(avg_return, 0), 0.1) * 10 +
            self.weights["max_drawdown"] * (1 - min(max_drawdown, 1)) +
            self.weights["sample_count"] * min(total / 100, 1) +
            self.weights["regime_fit"] * regime_fit
        )

        return StrategyScore(
            strategy_id=strategy_id,
            strategy_name=strategy_id,
            win_rate=round(win_rate, 4),
            avg_return=round(avg_return, 4),
            max_drawdown=round(max_drawdown, 4),
            sample_count=total,
            regime_fit=round(regime_fit, 4),
            composite_score=round(composite, 4),
            updated_at=datetime.now()
        )

    def get_top_strategies(
        self,
        all_history: Dict[str, any],
        top_n: int = 10
    ) -> List[StrategyScore]:
        """获取 Top N 策略"""
        self.update_weights({})

        regime_value = "neutral"
        try:
            if self.regime_detector:
                current_regime, _ = self.regime_detector.detect()
                regime_value = current_regime.value if current_regime else "neutral"
        except Exception:
            pass

        scores = []
        for strategy_id, history_df in all_history.items():
            score = self.score_strategy(strategy_id, history_df, regime_value)
            if score:
                scores.append(score)

        scores.sort(key=lambda x: x.composite_score, reverse=True)
        return scores[:top_n]

    def _calc_max_drawdown(self, returns: List[float]) -> float:
        """计算最大回撤"""
        if not returns:
            return 0.0

        cumulative = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0

    def get_weights(self) -> Dict:
        """获取当前权重"""
        return self.weights.copy()

    def reset_weights(self):
        """重置为默认权重"""
        self.weights = self.DEFAULT_WEIGHTS.copy()
