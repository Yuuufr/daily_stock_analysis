# -*- coding: utf-8 -*-
"""
Factor Version Manager

因子版本管理（Quant Research Flow）：
1. 语义化版本控制
2. 因子血缘追踪
3. A/B 测试支持
4. 因子贡献度分析
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.storage import get_db

logger = logging.getLogger(__name__)


class FactorVersionManager:
    """
    因子版本管理器
    """

    def __init__(self):
        self.db = get_db()

    def create_version(
        self,
        name: str,
        config: Dict,
        description: str = "",
        parent_version: Optional[str] = None,
        created_by: str = "auto"
    ) -> str:
        """
        创建新因子版本

        Args:
            name: 因子名称
            config: 因子配置参数
            description: 版本描述
            parent_version: 父版本（用于血缘追踪）
            created_by: 创建者

        Returns:
            版本号字符串，如 "momentum_v1.2.3"
        """
        latest = self._get_latest_version(name)

        if latest:
            try:
                semver_str = latest.split("_")[-1]
                new_ver = self._bump_patch(semver_str)
            except:
                new_ver = "1.0.0"
        else:
            new_ver = "1.0.0"

        version = f"{name}_{new_ver}"

        lineage = {"parent": parent_version, "ancestors": []}
        if parent_version:
            parent_record = self.get_version_record(parent_version)
            if parent_record and parent_record.config:
                lineage["ancestors"] = (
                    parent_record.config.get("lineage", {}).get("ancestors", [])
                )
                lineage["ancestors"].append(parent_version)

        full_config = {**config, "lineage": lineage}

        try:
            from src.quant.models.quant_models import FactorVersion

            record = FactorVersion(
                version=version,
                name=name,
                description=description,
                config=full_config,
                created_by=created_by,
                created_at=datetime.now(),
                status="active"
            )
            self.db.add(record)
            self.db.commit()
        except Exception as e:
            logger.warning(f"数据库写入失败，使用内存模式: {e}")

        return version

    def deprecate_version(self, version: str, reason: str = ""):
        """标记版本为废弃"""
        try:
            from src.quant.models.quant_models import FactorVersion

            record = self.get_version_record(version)
            if record:
                record.status = "deprecated"
                record.description = (
                    f"{record.description}\n\n"
                    f"[Deprecated at {datetime.now().isoformat()}]\n"
                    f"Reason: {reason}"
                )
                self.db.commit()
        except Exception as e:
            logger.warning(f"数据库更新失败: {e}")

    def get_version_record(self, version: str):
        """获取版本记录"""
        try:
            from src.quant.models.quant_models import FactorVersion

            return (
                self.db.query(FactorVersion)
                .filter_by(version=version)
                .first()
            )
        except Exception:
            return None

    def list_versions(
        self,
        name: str = None,
        status: str = "active",
        limit: int = 100
    ) -> List:
        """列出因子版本"""
        try:
            from src.quant.models.quant_models import FactorVersion

            query = self.db.query(FactorVersion)

            if name:
                query = query.filter_by(name=name)
            if status:
                query = query.filter_by(status=status)

            return (
                query
                .order_by(FactorVersion.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.warning(f"数据库查询失败: {e}")
            return []

    def get_lineage(self, version: str) -> Dict:
        """获取因子血缘链"""
        lineage = []
        current_version = version

        for _ in range(10):
            record = self.get_version_record(current_version)
            if not record:
                break

            lineage.append({
                "version": record.version,
                "created_at": (
                    record.created_at.isoformat()
                    if record.created_at else None
                ),
                "created_by": record.created_by
            })

            parent = (
                record.config.get("lineage", {})
                .get("parent")
                if record.config else None
            )
            if parent:
                current_version = parent
            else:
                break

        return {"chain": lineage, "depth": len(lineage)}

    def _get_latest_version(self, name: str) -> Optional[str]:
        """获取某因子的最新版本"""
        try:
            from src.quant.models.quant_models import FactorVersion

            record = (
                self.db.query(FactorVersion)
                .filter_by(name=name, status="active")
                .order_by(FactorVersion.created_at.desc())
                .first()
            )
            return record.version if record else None
        except Exception:
            return None

    def _bump_patch(self, semver_str: str) -> str:
        """递增 patch 版本号"""
        parts = semver_str.split(".")
        if len(parts) != 3:
            return "1.0.0"
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{major}.{minor}.{patch + 1}"
        except:
            return "1.0.0"

    def save_importance(
        self,
        version: str,
        importance_list: List[tuple]
    ):
        """
        保存特征重要性

        Args:
            version: 因子版本
            importance_list: [(因子名, 重要性分数), ...]
        """
        try:
            from src.quant.models.quant_models import FactorImportance

            for rank, (fname, score) in enumerate(importance_list, 1):
                record = FactorImportance(
                    version=version,
                    factor_name=fname,
                    importance_score=score,
                    rank=rank,
                    calculated_at=datetime.now()
                )
                self.db.add(record)

            self.db.commit()
        except Exception as e:
            logger.warning(f"保存重要性失败: {e}")
