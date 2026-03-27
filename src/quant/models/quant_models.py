# -*- coding: utf-8 -*-
"""
Quant Module Database Models

量化模块数据库模型定义
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Text, Boolean

try:
    from src.storage import Base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class QuantRunHistory(Base):
    """量化训练历史表"""
    __tablename__ = "quant_run_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime)
    status = Column(String(32), default="running")
    regime_before = Column(String(32))
    regime_after = Column(String(32))
    models_trained = Column(JSON)
    best_model = Column(String(128))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class FactorVersion(Base):
    """因子版本表"""
    __tablename__ = "factor_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(64))
    status = Column(String(32), default="active")


class FactorImportance(Base):
    """特征重要性表"""
    __tablename__ = "factor_importance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(64), nullable=False)
    factor_name = Column(String(128), nullable=False)
    importance_score = Column(Float)
    rank = Column(Integer)
    sample_count = Column(Integer)
    calculated_at = Column(DateTime, default=datetime.now)


class ModelVersion(Base):
    """模型版本表"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(64), unique=True, nullable=False)
    model_type = Column(String(32), nullable=False)
    model_name = Column(String(128), nullable=False)
    file_path = Column(String(256), nullable=False)
    config = Column(JSON)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(32), default="active")
    regime_context = Column(String(32))


class StrategyPerformance(Base):
    """策略表现表"""
    __tablename__ = "strategy_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(128), nullable=False)
    regime = Column(String(32), nullable=False)
    win_rate = Column(Float)
    avg_return = Column(Float)
    max_drawdown = Column(Float)
    sample_count = Column(Integer)
    calculated_at = Column(DateTime, default=datetime.now)
    is_active = Column(Integer, default=1)


class StrategySignal(Base):
    """策略信号表"""
    __tablename__ = "strategy_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(128), nullable=False)
    stock_code = Column(String(32))
    signal_date = Column(DateTime)
    signal_type = Column(String(32))
    regime = Column(String(32))
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.now)


class StrategySignalResult(Base):
    """策略信号结果表"""
    __tablename__ = "strategy_signal_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, nullable=False)
    stock_code = Column(String(32))
    future_return = Column(Float)
    hit = Column(Boolean)
    hit_stop_loss = Column(Boolean)
    hit_take_profit = Column(Boolean)
    evaluated_at = Column(DateTime, default=datetime.now)


class FactorBacktestResult(Base):
    """因子回测结果表"""
    __tablename__ = "factor_backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_name = Column(String(128), nullable=False)
    factor_version = Column(String(64))
    ic = Column(Float)
    ir = Column(Float)
    top_group_return = Column(Float)
    bottom_group_return = Column(Float)
    sample_count = Column(Integer)
    calculated_at = Column(DateTime, default=datetime.now)


class RegimeHistory(Base):
    """Regime 历史记录表"""
    __tablename__ = "regime_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detected_at = Column(DateTime, default=datetime.now)
    regime = Column(String(32), nullable=False)
    index_code = Column(String(32))
    total_score = Column(Float)
    ma_score = Column(Float)
    trend_score = Column(Float)
    vol_score = Column(Float)
    momentum_score = Column(Float)


class WeightAdjustmentLog(Base):
    """权重调整日志表"""
    __tablename__ = "weight_adjustment_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    adjusted_at = Column(DateTime, default=datetime.now)
    trigger_reason = Column(String(128))
    regime_before = Column(String(32))
    regime_after = Column(String(32))
    old_weights = Column(JSON)
    new_weights = Column(JSON)
