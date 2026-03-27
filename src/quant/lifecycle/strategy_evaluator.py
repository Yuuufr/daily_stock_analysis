# -*- coding: utf-8 -*-
"""
Strategy Evaluator

策略评估与自动淘汰
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """
    策略评估与自动淘汰器
    
    淘汰条件：
    1. 胜率低于阈值
    2. 连续亏损次数过多
    3. 近期表现大幅下滑
    """

    MIN_WIN_RATE = 0.40
    MIN_SAMPLE_COUNT = 20
    CONSECUTIVE_LOSS_THRESHOLD = 5
    DECAY_WEIGHT_HALF_LIFE = 30

    def __init__(self):
        self.death_list: List[Dict] = []

    def evaluate_and_adapt(
        self,
        strategy_id: str,
        history_df
    ) -> Tuple[bool, str]:
        """
        评估策略是否需要淘汰或调整

        Returns:
            Tuple[bool, str] - (is_alive, reason)
        """
        if history_df is None or len(history_df) < self.MIN_SAMPLE_COUNT:
            return True, "样本不足，暂时保留"

        recent_perf = self._calc_decay_weighted_perf(history_df)
        consecutive_losses = self._count_consecutive_losses(history_df)

        win_rate = 0.0
        if "hit" in history_df.columns:
            win_rate = history_df["hit"].mean()

        death_reasons = []

        if win_rate < self.MIN_WIN_RATE and len(history_df) > 50:
            death_reasons.append(
                f"胜率{win_rate:.1%}低于阈值{self.MIN_WIN_RATE:.1%}"
            )

        if consecutive_losses >= self.CONSECUTIVE_LOSS_THRESHOLD:
            death_reasons.append(f"连续亏损{consecutive_losses}次")

        if recent_perf < -0.05:
            death_reasons.append(f"近期表现{recent_perf:.2%}大幅下滑")

        if len(death_reasons) >= 2:
            self._record_death(strategy_id, history_df, death_reasons)
            return False, "; ".join(death_reasons)

        if consecutive_losses >= 3:
            return True, f"警告：连续亏损{consecutive_losses}次，建议降低仓位"

        return True, "正常"

    def _calc_decay_weighted_perf(self, history_df, days: int = 30) -> float:
        """计算指数衰减加权收益"""
        if "future_return" not in history_df.columns:
            return 0.0

        recent = history_df.tail(days)
        returns = recent["future_return"].tolist()

        if not returns:
            return 0.0

        decay_factor = np.exp(-np.log(2) / self.DECAY_WEIGHT_HALF_LIFE * 1)
        weights = np.array([decay_factor ** i for i in range(len(returns))])

        weighted_return = np.sum(weights * np.array(returns))
        return weighted_return

    def _count_consecutive_losses(self, history_df) -> int:
        """计算最近连续亏损次数"""
        if "hit" not in history_df.columns:
            return 0

        consecutive = 0
        for hit in reversed(history_df["hit"].values):
            if not hit:
                consecutive += 1
            else:
                break
        return consecutive

    def _record_death(
        self,
        strategy_id: str,
        history_df,
        reasons: List[str]
    ):
        """记录策略淘汰事件"""
        win_rate = 0.0
        avg_return = 0.0

        if "hit" in history_df.columns:
            win_rate = history_df["hit"].mean()
        if "future_return" in history_df.columns:
            avg_return = history_df["future_return"].mean()

        self.death_list.append({
            "strategy_id": strategy_id,
            "death_time": datetime.now(),
            "reasons": reasons,
            "final_win_rate": win_rate,
            "final_return": avg_return
        })

    def get_death_report(self) -> str:
        """生成淘汰报告"""
        if not self.death_list:
            return "# 策略淘汰报告\n\n本期无策略淘汰"

        lines = ["# 策略淘汰报告\n"]

        for death in self.death_list:
            lines.extend([
                f"## {death['strategy_id']}\n",
                f"- 淘汰时间: {death['death_time']}\n",
                f"- 原因: {'; '.join(death['reasons'])}\n",
                f"- 最终胜率: {death['final_win_rate']:.1%}\n",
                f"- 最终收益: {death['final_return']:.2%}\n",
                "\n"
            ])

        return "\n".join(lines)

    def get_alive_strategies(
        self,
        all_strategies: Dict[str, any]
    ) -> List[str]:
        """获取存活的策略列表"""
        alive = []

        for strategy_id, history_df in all_strategies.items():
            is_alive, _ = self.evaluate_and_adapt(strategy_id, history_df)
            if is_alive:
                alive.append(strategy_id)

        return alive
