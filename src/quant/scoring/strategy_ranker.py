# -*- coding: utf-8 -*-
"""
Strategy Ranker

策略排行榜管理器
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StrategyRanker:
    """策略排行榜管理器"""

    def __init__(self, regime_detector=None):
        try:
            from src.quant.scoring.realtime_scorer import RealtimeScorer
            self.scorer = RealtimeScorer(regime_detector=regime_detector)
        except Exception:
            self.scorer = None

    def get_ranking(
        self,
        regime_filter: Optional[str] = None,
        limit: int = 10
    ) -> List:
        """
        获取策略排行榜

        Returns:
            List[StrategyScore]
        """
        all_history = self._load_all_strategy_history()

        if not all_history or not self.scorer:
            return []

        scores = self.scorer.get_top_strategies(all_history, top_n=limit)

        if regime_filter:
            scores = [s for s in scores if regime_filter in s.strategy_id]

        self._cache_scores(scores)

        return scores

    def _load_all_strategy_history(self) -> Dict[str, any]:
        """
        从数据库加载所有策略历史信号
        
        Returns:
            Dict[strategy_id, DataFrame]
        """
        try:
            from src.storage import get_db
            from src.quant.models.quant_models import StrategySignal, StrategySignalResult

            db = get_db()

            signals = (
                db.query(StrategySignal)
                .filter(StrategySignal.signal_id == StrategySignalResult.signal_id)
                .all()
            )

            history_map = {}
            for signal in signals:
                if signal.strategy_id not in history_map:
                    history_map[signal.strategy_id] = []

                if signal.future_return is not None:
                    history_map[signal.strategy_id].append({
                        "hit": signal.hit if hasattr(signal, "hit") else None,
                        "future_return": signal.future_return,
                        "regime": signal.regime
                    })

            import pandas as pd
            result = {}
            for strategy_id, records in history_map.items():
                if records:
                    result[strategy_id] = pd.DataFrame(records)

            return result

        except Exception as e:
            logger.warning(f"加载策略历史失败: {e}")
            return {}

    def _cache_scores(self, scores: List):
        """缓存评分到数据库"""
        try:
            from src.storage import get_db
            from src.quant.models.quant_models import StrategyPerformance

            db = get_db()

            for score in scores:
                try:
                    regime = "neutral"
                    if "_" in score.strategy_id:
                        parts = score.strategy_id.split("_")
                        if len(parts) > 1:
                            potential_regime = parts[-1]
                            if potential_regime in ["bull", "bear", "neutral"]:
                                regime = potential_regime

                    record = StrategyPerformance(
                        strategy_id=score.strategy_id,
                        regime=regime,
                        win_rate=score.win_rate,
                        avg_return=score.avg_return,
                        max_drawdown=score.max_drawdown,
                        sample_count=score.sample_count,
                        calculated_at=datetime.now(),
                        is_active=1
                    )
                    db.merge(record)
                except Exception as e:
                    logger.debug(f"缓存评分失败: {e}")

            db.commit()

        except Exception as e:
            logger.warning(f"数据库缓存失败: {e}")

    def get_ranking_report(self) -> str:
        """生成排行榜 Markdown 报告"""
        scores = self.get_ranking(limit=10)

        if not scores:
            return "# 策略排行榜\n\n暂无数据"

        lines = [
            "# 策略排行榜",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "| 排名 | 策略 | 胜率 | 平均收益 | 最大回撤 | 样本数 | 综合评分 |",
            "|------|------|------|----------|----------|--------|----------|"
        ]

        for i, s in enumerate(scores, 1):
            lines.append(
                f"| {i} | {s.strategy_name} | "
                f"{s.win_rate:.1%} | {s.avg_return:.2%} | "
                f"{s.max_drawdown:.2%} | {s.sample_count} | {s.composite_score:.4f} |"
            )

        return "\n".join(lines)
