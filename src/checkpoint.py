# -*- coding: utf-8 -*-
"""
断点续传管理器

职责：
1. 在 LLM 分析过程中保存断点，避免中断后重复调用
2. 支持从断点恢复，跳过已完成的分析
3. 断点文件存储在 checkpoints/ 目录，每个股票每天一个 JSON 文件

断点状态：
- in_progress: LLM 调用进行中（刚写入，还未完成）
- completed: LLM 调用已完成（包含完整结果）
- failed: LLM 调用失败（包含错误信息）
"""

import json
import logging
import os
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_VERSION = 1


class CheckpointManager:
    """
    断点续传管理器

    断点文件命名: {stock_code}_{date}.json
    例如: 000001_2026-03-27.json
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        if not self.checkpoint_dir.exists():
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建断点目录: {self.checkpoint_dir}")

    def _get_filepath(self, stock_code: str, date: str) -> Path:
        safe_code = stock_code.replace("/", "_").replace("\\", "_")
        return self.checkpoint_dir / f"{safe_code}_{date}.json"

    def has_checkpoint(self, stock_code: str, date: str) -> bool:
        """检查是否存在未完成或已完成的断点"""
        fp = self._get_filepath(stock_code, date)
        if not fp.exists():
            return False
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            status = data.get("status")
            return status in ("in_progress", "completed", "failed")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"读取断点文件失败 {fp}: {e}，忽略并删除")
            try:
                fp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def get_status(self, stock_code: str, date: str) -> Optional[str]:
        """获取断点状态: in_progress / completed / failed / None"""
        fp = self._get_filepath(stock_code, date)
        if not fp.exists():
            return None
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("status")
        except (json.JSONDecodeError, IOError):
            return None

    def load_checkpoint(self, stock_code: str, date: str) -> Optional[Dict[str, Any]]:
        """
        加载断点数据

        Returns:
            包含以下键的字典:
            - status: str (in_progress / completed / failed)
            - result: dict (AnalysisResult.to_dict(), 仅 completed 时有)
            - raw_response: str (LLM 原始响应, completed/failed 时有)
            - error_message: str (错误信息, 仅 failed 时有)
            - saved_at: str (ISO 时间戳)
            - code: str
            - date: str
            - checkpoint_version: int
            - llm_used: float (LLM 耗时秒数, 仅 completed/failed 时有)
            - model_used: str (使用的模型名, 仅 completed/failed 时有)
            None: 断点不存在
        """
        fp = self._get_filepath(stock_code, date)
        if not fp.exists():
            return None
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("checkpoint_version", 0)
            if version > CHECKPOINT_VERSION:
                logger.warning(
                    f"断点版本过新 ({version} > {CHECKPOINT_VERSION})，忽略: {fp}"
                )
                return None
            logger.info(
                f"[断点续传] 加载断点: {stock_code} {date}, status={data.get('status')}, "
                f"saved_at={data.get('saved_at')}"
            )
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载断点失败 {fp}: {e}")
            return None

    def save_in_progress(
        self,
        stock_code: str,
        date: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        保存进行中状态（LLM 调用刚发起）
        """
        fp = self._get_filepath(stock_code, date)
        data = {
            "checkpoint_version": CHECKPOINT_VERSION,
            "status": "in_progress",
            "code": stock_code,
            "date": date,
            "saved_at": datetime.now().isoformat(),
            "context": context,
        }
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[断点续传] 保存进行中断点: {stock_code} {date}")
        except IOError as e:
            logger.warning(f"保存断点失败 {fp}: {e}")

    def save_completed(
        self,
        stock_code: str,
        date: str,
        result_dict: Dict[str, Any],
        raw_response: str,
        llm_elapsed: float,
        model_used: Optional[str] = None,
    ) -> None:
        """
        保存完成状态（LLM 调用成功）
        """
        fp = self._get_filepath(stock_code, date)
        data = {
            "checkpoint_version": CHECKPOINT_VERSION,
            "status": "completed",
            "code": stock_code,
            "date": date,
            "saved_at": datetime.now().isoformat(),
            "result": result_dict,
            "raw_response": raw_response,
            "llm_elapsed": llm_elapsed,
            "model_used": model_used,
        }
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(
                f"[断点续传] 保存完成断点: {stock_code} {date}, "
                f"elapsed={llm_elapsed:.2f}s"
            )
        except IOError as e:
            logger.warning(f"保存断点失败 {fp}: {e}")

    def save_failed(
        self,
        stock_code: str,
        date: str,
        error_message: str,
        raw_response: Optional[str] = None,
        llm_elapsed: float = 0.0,
        model_used: Optional[str] = None,
    ) -> None:
        """
        保存失败状态（LLM 调用失败）
        """
        fp = self._get_filepath(stock_code, date)
        data = {
            "checkpoint_version": CHECKPOINT_VERSION,
            "status": "failed",
            "code": stock_code,
            "date": date,
            "saved_at": datetime.now().isoformat(),
            "error_message": error_message,
            "raw_response": raw_response,
            "llm_elapsed": llm_elapsed,
            "model_used": model_used,
        }
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.warning(
                f"[断点续传] 保存失败断点: {stock_code} {date}, error={error_message[:100]}"
            )
        except IOError as e:
            logger.warning(f"保存断点失败 {fp}: {e}")

    def clear_checkpoint(self, stock_code: str, date: str) -> None:
        """清除断点（分析结果已成功保存到数据库后调用）"""
        fp = self._get_filepath(stock_code, date)
        if fp.exists():
            try:
                fp.unlink()
                logger.info(f"[断点续传] 清除断点: {stock_code} {date}")
            except OSError as e:
                logger.warning(f"清除断点失败 {fp}: {e}")

    def list_pending(self) -> list:
        """
        列出所有未完成的断点（in_progress 和 failed）
        用于中断后恢复分析
        """
        pending = []
        if not self.checkpoint_dir.exists():
            return pending
        for fp in self.checkpoint_dir.glob("*.json"):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status = data.get("status")
                if status in ("in_progress", "failed"):
                    pending.append({
                        "code": data.get("code"),
                        "date": data.get("date"),
                        "status": status,
                        "saved_at": data.get("saved_at"),
                        "error_message": data.get("error_message"),
                        "path": str(fp),
                    })
            except (json.JSONDecodeError, IOError):
                continue
        return pending


_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


def set_checkpoint_manager(manager: CheckpointManager) -> None:
    global _checkpoint_manager
    _checkpoint_manager = manager
