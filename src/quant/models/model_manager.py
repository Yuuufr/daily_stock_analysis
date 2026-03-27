# -*- coding: utf-8 -*-
"""
Model Version Manager

模型权重文件的保存、加载、切换
模型版本历史追踪
A/B 影子模式
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

from sqlalchemy import select, desc

logger = logging.getLogger(__name__)


def get_db_session():
    """获取数据库 Session 的便捷函数"""
    from src.storage import get_db
    db = get_db()
    return db.get_session()


class ModelManager:
    """
    模型版本管理器
    """

    MODEL_DIR = Path("data/models")
    SKLEARN_DIR = MODEL_DIR / "sklearn"
    PYTORCH_DIR = MODEL_DIR / "pytorch"

    def __init__(self):
        self.current_version: Optional[str] = None
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录结构存在"""
        self.SKLEARN_DIR.mkdir(parents=True, exist_ok=True)
        self.PYTORCH_DIR.mkdir(parents=True, exist_ok=True)

    def save_model(
        self,
        model,
        model_type: str,
        model_name: str,
        config: Dict = None,
        metrics: Dict = None,
        regime_context: str = None
    ) -> Path:
        """
        保存模型到文件系统
        """
        version = self._generate_version(model_type, model_name)

        if model_type == "sklearn":
            save_dir = self.SKLEARN_DIR / version
        else:
            save_dir = self.PYTORCH_DIR / version

        save_dir.mkdir(parents=True, exist_ok=True)

        if model_type == "sklearn":
            try:
                import joblib
                model_path = save_dir / "model.joblib"
                joblib.dump(model, model_path)
            except ImportError:
                logger.warning("joblib not available, skipping sklearn model save")
                model_path = save_dir / "model.pkl"
        else:
            try:
                import torch
                model_path = save_dir / "model.pt"
                torch.save(model.state_dict(), model_path)
            except ImportError:
                logger.warning("torch not available, skipping pytorch model save")
                model_path = save_dir / "model.pth"

        config_path = save_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump({
                "model_type": model_type,
                "model_name": model_name,
                "config": config or {},
                "saved_at": datetime.now().isoformat()
            }, f, indent=2)

        self._save_to_db(
            version=version,
            model_type=model_type,
            model_name=model_name,
            file_path=str(model_path),
            config=config,
            metrics=metrics,
            regime_context=regime_context
        )

        if self.current_version is None:
            self.current_version = version

        return model_path

    def _save_to_db(
        self,
        version: str,
        model_type: str,
        model_name: str,
        file_path: str,
        config: Dict = None,
        metrics: Dict = None,
        regime_context: str = None
    ):
        """保存到数据库"""
        try:
            from src.quant.models.quant_models import ModelVersion

            record = ModelVersion(
                version=version,
                model_type=model_type,
                model_name=model_name,
                file_path=file_path,
                config=config or {},
                metrics=metrics or {},
                created_at=datetime.now(),
                status="active",
                regime_context=regime_context
            )

            session = get_db_session()
            try:
                session.add(record)
                session.commit()
            finally:
                session.close()

        except Exception as e:
            logger.warning(f"数据库保存失败: {e}")

    def load_model(self, version: str, model_type: str):
        """加载模型"""
        if model_type == "sklearn":
            model_path = self.SKLEARN_DIR / version / "model.joblib"
            if not model_path.exists():
                model_path = self.SKLEARN_DIR / version / "model.pkl"
            try:
                import joblib
                return joblib.load(model_path)
            except Exception as e:
                logger.error(f"加载 sklearn 模型失败: {e}")
                return None
        else:
            model_path = self.PYTORCH_DIR / version / "model.pt"
            if not model_path.exists():
                model_path = self.PYTORCH_DIR / version / "model.pth"
            try:
                import torch
                model = self._create_pytorch_model()
                model.load_state_dict(torch.load(model_path))
                return model
            except Exception as e:
                logger.error(f"加载 PyTorch 模型失败: {e}")
                return None

    def list_versions(
        self,
        model_type: str = None,
        status: str = "active"
    ) -> List:
        """列出模型版本"""
        try:
            from src.quant.models.quant_models import ModelVersion

            session = get_db_session()
            try:
                query = select(ModelVersion)

                if model_type:
                    query = query.where(ModelVersion.model_type == model_type)
                if status:
                    query = query.where(ModelVersion.status == status)

                query = query.order_by(desc(ModelVersion.created_at))

                result = session.execute(query)
                return list(result.scalars().all())

            finally:
                session.close()

        except Exception as e:
            logger.warning(f"数据库查询失败: {e}")
            return []

    def switch_version(self, version: str):
        """切换到指定版本"""
        self.current_version = version
        logger.info(f"已切换到模型版本: {version}")

    def deprecate_version(self, version: str, reason: str = ""):
        """废弃指定版本"""
        try:
            from src.quant.models.quant_models import ModelVersion

            session = get_db_session()
            try:
                result = session.execute(
                    select(ModelVersion).where(ModelVersion.version == version)
                )
                record = result.scalar_one_or_none()

                if record:
                    record.status = "deprecated"
                    session.commit()
                    logger.info(f"版本 {version} 已废弃: {reason}")

            finally:
                session.close()

        except Exception as e:
            logger.warning(f"废弃版本失败: {e}")

    def _generate_version(self, model_type: str, model_name: str) -> str:
        """生成版本号"""
        import semver

        latest = None
        try:
            from src.quant.models.quant_models import ModelVersion

            session = get_db_session()
            try:
                result = session.execute(
                    select(ModelVersion)
                    .where(
                        ModelVersion.model_type == model_type,
                        ModelVersion.model_name == model_name,
                        ModelVersion.status.in_(["active", "shadow"])
                    )
                    .order_by(desc(ModelVersion.created_at))
                    .limit(1)
                )
                record = result.scalar_one_or_none()
                if record:
                    latest = record.version

            finally:
                session.close()

        except Exception:
            pass

        if latest:
            try:
                semver_str = latest.split("_")[-1]
                new_ver = semver.bump_patch(semver_str)
            except:
                new_ver = "1.0.0"
        else:
            new_ver = "1.0.0"

        return f"{model_type}_{model_name}_v{new_ver}"

    def _create_pytorch_model(self):
        """创建 PyTorch 模型"""
        try:
            import torch.nn as nn

            class SimpleMLP(nn.Module):
                def __init__(self, input_dim=10, hidden_dim=64, num_classes=2):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(hidden_dim, num_classes)
                    )

                def forward(self, x):
                    return self.net(x)

            return SimpleMLP()
        except ImportError:
            return None
