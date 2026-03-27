# -*- coding: utf-8 -*-
"""
Quant Integration Module

量化模块与现有系统的集成
"""

import logging

logger = logging.getLogger(__name__)


class QuantIntegration:
    """
    量化模块与现有系统的集成
    
    集成点：
    1. data_provider - 提供历史数据
    2. notification.py - 发送训练报告和评分通知
    3. main.py - 周末定时训练触发
    4. Web UI - 量化模块页面
    """

    @staticmethod
    def setup_weekend_training():
        """
        在 main.py 中调用，设置周末训练调度器
        
        用法:
            if __name__ == "__main__":
                QuantIntegration.setup_weekend_training()
                main()
        """
        try:
            from src.quant.lifecycle.weekend_scheduler import WeekendScheduler
            from src.notification import NotificationService

            def send_training_notification(message: str):
                try:
                    notifier = NotificationService()
                    notifier.send_text(message)
                except Exception as e:
                    logger.warning(f"发送训练通知失败: {e}")

            scheduler = WeekendScheduler(notification_callback=send_training_notification)
            scheduler.start()
            logger.info("周末训练调度器已启动")

            return scheduler
        except Exception as e:
            logger.error(f"启动周末训练调度器失败: {e}")
            return None

    @staticmethod
    def enrich_analysis_with_regime(code: str, context: Dict) -> Dict:
        """
        在 StockAnalysisPipeline 中调用，
        用当前 Regime 自适应调整分析参数
        
        位置: src/core/pipeline.py - _enhance_context 方法
        
        用法:
            context = QuantIntegration.enrich_analysis_with_regime(code, context)
        """
        try:
            from src.quant.regime.detector import RegimeDetector

            detector = RegimeDetector()
            regime, details = detector.detect()

            if regime.value == "bull":
                context["factor_weights"] = {
                    "momentum": 0.4,
                    "trend": 0.3,
                    "volume": 0.15,
                    "volatility": 0.15
                }
            elif regime.value == "bear":
                context["factor_weights"] = {
                    "momentum": 0.2,
                    "trend": 0.2,
                    "volume": 0.2,
                    "volatility": 0.4
                }
            else:
                context["factor_weights"] = {
                    "momentum": 0.25,
                    "trend": 0.25,
                    "volume": 0.25,
                    "volatility": 0.25
                }

            context["current_regime"] = regime.value
            context["regime_details"] = details

        except Exception as e:
            logger.warning(f"Regime 检测失败: {e}")

        return context

    @staticmethod
    def get_adaptive_strategy() -> Dict:
        """
        根据当前 Regime 返回自适应策略配置
        
        供 Agent 系统使用
        
        用法:
            strategy = QuantIntegration.get_adaptive_strategy()
        """
        try:
            from src.quant.regime.detector import RegimeDetector

            detector = RegimeDetector()
            return detector.get_adaptive_strategy()

        except Exception as e:
            logger.warning(f"获取自适应策略失败: {e}")
            return {
                "name": "默认策略",
                "risk_level": "medium",
                "position_preference": 0.5
            }

    @staticmethod
    def get_strategy_ranking(top_n: int = 10) -> list:
        """
        获取策略排行榜
        
        用法:
            ranking = QuantIntegration.get_strategy_ranking(top_n=10)
        """
        try:
            from src.quant.scoring.strategy_ranker import StrategyRanker

            ranker = StrategyRanker()
            return ranker.get_ranking(limit=top_n)

        except Exception as e:
            logger.warning(f"获取策略排行失败: {e}")
            return []

    @staticmethod
    def trigger_weekend_training() -> Dict:
        """
        手动触发周末训练
        
        用法:
            report = QuantIntegration.trigger_weekend_training()
        """
        try:
            from src.quant.training.trainer import WeekendTrainer

            trainer = WeekendTrainer()
            return trainer.trigger_manual_run()

        except Exception as e:
            logger.error(f"触发训练失败: {e}")
            return {"status": "failed", "error": str(e)}


def initialize_quant_module():
    """
    初始化量化模块
    
    在应用启动时调用一次
    """
    try:
        from src.quant.factors.builtin_factors import register_builtin_factors

        register_builtin_factors()
        logger.info("量化模块初始化完成")

    except Exception as e:
        logger.warning(f"量化模块初始化失败: {e}")
