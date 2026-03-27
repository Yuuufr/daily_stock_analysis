# -*- coding: utf-8 -*-
"""
Quant API Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

router = APIRouter(prefix="/api/v1/quant", tags=["量化模块"])


class RegimeResponse(BaseModel):
    regime: str
    score: float
    details: Dict
    detected_at: datetime


class StrategyScoreResponse(BaseModel):
    strategy_id: str
    strategy_name: str
    win_rate: float
    avg_return: float
    max_drawdown: float
    composite_score: float
    rank: int


@router.get("/regime", response_model=RegimeResponse)
async def get_current_regime():
    """获取当前市场 Regime"""
    try:
        from src.quant.regime.detector import RegimeDetector

        detector = RegimeDetector()
        regime, details = detector.detect()

        return RegimeResponse(
            regime=regime.value,
            score=details.get("total_score", 0),
            details=details,
            detected_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking", response_model=List[StrategyScoreResponse])
async def get_strategy_ranking(limit: int = 10):
    """获取策略排行榜"""
    try:
        from src.quant.scoring.strategy_ranker import StrategyRanker

        ranker = StrategyRanker()
        scores = ranker.get_ranking(limit=limit)

        return [
            StrategyScoreResponse(
                strategy_id=s.strategy_id,
                strategy_name=s.strategy_name,
                win_rate=s.win_rate,
                avg_return=s.avg_return,
                max_drawdown=s.max_drawdown,
                composite_score=s.composite_score,
                rank=i + 1
            )
            for i, s in enumerate(scores)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring/weights")
async def get_current_weights():
    """获取当前评分权重"""
    try:
        from src.quant.scoring.realtime_scorer import RealtimeScorer

        scorer = RealtimeScorer()
        return {"weights": scorer.get_weights()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/trigger")
async def trigger_training():
    """手动触发训练"""
    try:
        from src.quant.training.trainer import WeekendTrainer

        trainer = WeekendTrainer()
        import threading
        thread = threading.Thread(target=trainer.trigger_manual_run)
        thread.start()

        return {"status": "triggered", "message": "训练任务已在后台启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/history")
async def get_training_history(limit: int = 10):
    """获取历史训练报告"""
    try:
        import json
        from pathlib import Path

        reports = []
        report_dir = Path("data/reports")

        if report_dir.exists():
            for f in sorted(
                report_dir.glob("weekend_training_*.json"),
                reverse=True
            )[:limit]:
                with open(f) as fp:
                    data = json.load(fp)
                    reports.append(data)

        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors/list")
async def list_factors():
    """列出所有注册的因子"""
    try:
        from src.quant.factors.base import FactorRegistry

        factors = FactorRegistry.list_all()
        return {
            "factors": [
                {"name": name, "version": f.version, "description": f.description}
                for name, f in factors.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/versions")
async def list_model_versions():
    """列出模型版本"""
    try:
        from src.quant.models.model_manager import ModelManager

        manager = ModelManager()
        versions = manager.list_versions()

        return {
            "versions": [
                {
                    "version": v.version,
                    "model_type": v.model_type,
                    "model_name": v.model_name,
                    "status": v.status,
                    "created_at": v.created_at.isoformat() if v.created_at else None
                }
                for v in versions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/coverage")
async def get_data_coverage():
    """获取本地数据覆盖情况"""
    try:
        from src.quant.data import HistoricalDataManager

        dm = HistoricalDataManager()
        coverage = dm.get_coverage()
        summary = dm.get_data_summary()

        return {
            "stocks": coverage,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
