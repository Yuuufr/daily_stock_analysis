# -*- coding: utf-8 -*-
"""
Weekend Scheduler

周末自动训练调度器
每周六 14:00 自动执行
"""

import logging
from datetime import datetime, time
import threading
import time as time_module
from pathlib import Path

logger = logging.getLogger(__name__)


class WeekendScheduler:
    """
    周末自动训练调度器
    
    工作流程：
    - 每周六 07:00 自动执行周末训练
    - 发送训练报告到配置的通知渠道
    """

    TRAINING_TIME = time(7, 0)
    CHECK_INTERVAL = 60

    def __init__(self, notification_callback=None):
        self.notification_callback = notification_callback
        self.running = False
        self.thread = None

    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("周末训练调度器已启动")

    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("周末训练调度器已停止")

    def _run_loop(self):
        """调度循环"""
        while self.running:
            now = datetime.now()

            if now.weekday() == 5 and now.time().hour == 14 and now.time().minute < 5:
                if self._should_run_today():
                    logger.info("触发周末训练")
                    self._execute_training()

            time_module.sleep(self.CHECK_INTERVAL)

    def _should_run_today(self) -> bool:
        """检查今天是否应该运行"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        last_run_file = Path("data/.last_weekend_training")

        if last_run_file.exists():
            last_date = last_run_file.read_text().strip()
            if last_date == today_str:
                logger.info("今日已运行，跳过")
                return False

        return True

    def _execute_training(self):
        """执行训练并发送通知"""
        try:
            from src.quant.training.trainer import WeekendTrainer

            trainer = WeekendTrainer()
            report = trainer.run_full_training()

            if self.notification_callback:
                message = self._format_report(report)
                self.notification_callback(message)

            today_str = datetime.now().strftime("%Y-%m-%d")
            Path("data/.last_weekend_training").write_text(today_str)

        except Exception as e:
            logger.error(f"周末训练失败: {e}")
            if self.notification_callback:
                self.notification_callback(f"周末训练失败: {e}")

    def _format_report(self, report: Dict) -> str:
        """格式化训练报告"""
        lines = [
            "# 周末训练报告",
            f"\n时间: {report['start_time']}",
            f"状态: {report['status']}\n"
        ]

        if report["status"] == "success":
            for step in report.get("steps", []):
                step_name = step.get("step", "unknown")
                lines.append(f"## {step_name}")

                if step_name == "model_selection":
                    best = step.get("best", {})
                    lines.append(f"- 最佳模型: {best.get('best_model')}")
                    metrics = best.get("metrics", {})
                    for k, v in metrics.items():
                        if isinstance(v, float):
                            lines.append(f"  - {k}: {v:.4f}")
                        else:
                            lines.append(f"  - {k}: {v}")

                lines.append("")

        return "\n".join(lines)

    def trigger_manual_run(self):
        """手动触发一次训练"""
        logger.info("手动触发周末训练")
        self._execute_training()
