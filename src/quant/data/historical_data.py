# -*- coding: utf-8 -*-
"""
Historical Data Manager

管理 10 年历史数据：
1. 从 data_provider 获取并存储历史数据
2. Parquet 格式存储，按股票代码分区
3. 提供高效的数据加载接口
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class HistoricalDataManager:
    """
    10 年历史数据管理器

    数据流程：
    1. fetch_and_save() - 批量获取并存储
    2. load() - 加载单只股票数据
    3. get_coverage() - 查看本地数据覆盖情况
    """

    DATA_DIR = Path("data/historical")

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else self.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_save(
        self,
        codes: List[str],
        years: int = 10,
        force: bool = False
    ) -> Dict[str, int]:
        """
        批量获取并存储历史数据

        Args:
            codes: 股票代码列表
            years: 获取多少年的数据
            force: 是否强制刷新已有数据

        Returns:
            Dict[str, int] - {"success": N, "failed": M, "skipped": K}
        """
        from data_provider import DataFetcherManager

        fetcher = DataFetcherManager()
        end_date = datetime.now()
        start_date = datetime(end_date.year - years, end_date.month, end_date.day)

        stats = {"success": 0, "failed": 0, "skipped": 0}

        for code in codes:
            try:
                if not force and self._has_recent_data(code):
                    stats["skipped"] += 1
                    logger.debug(f"{code}: 已有最新数据，跳过")
                    continue

                result = fetcher.get_daily_data(
                    code,
                    start_date=start_date,
                    end_date=end_date
                )

                if isinstance(result, tuple):
                    df, error = result
                else:
                    df = result

                if df is not None and len(df) > 0:
                    self._save_parquet(code, df)
                    stats["success"] += 1
                    logger.info(f"{code}: 成功保存 {len(df)} 条数据")
                else:
                    stats["failed"] += 1
                    logger.warning(f"{code}: 无数据返回")

            except Exception as e:
                stats["failed"] += 1
                logger.error(f"{code}: 获取失败 - {e}")

        return stats

    def load(
        self,
        code: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """
        加载单只股票历史数据

        Args:
            code: 股票代码
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            pd.DataFrame - 历史数据
        """
        path = self.data_dir / f"{code}.parquet"

        if not path.exists():
            logger.debug(f"{code}: 本地无数据")
            return pd.DataFrame()

        try:
            df = pd.read_parquet(path)

            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])

            if start_date:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["date"] <= pd.to_datetime(end_date)]

            return df.sort_values("date")

        except Exception as e:
            logger.error(f"{code}: 读取失败 - {e}")
            return pd.DataFrame()

    def save(
        self,
        code: str,
        df: pd.DataFrame,
        if_exists: str = "replace"
    ) -> bool:
        """
        保存股票数据

        Args:
            code: 股票代码
            df: 数据 DataFrame
            if_exists: "replace" | "append"

        Returns:
            bool - 是否成功
        """
        try:
            if if_exists == "append" and self._has_recent_data(code):
                existing = self.load(code)
                if len(existing) > 0:
                    df = pd.concat([existing, df], ignore_index=True)
                    df = df.drop_duplicates(subset=["date"], keep="last")

            self._save_parquet(code, df)
            return True

        except Exception as e:
            logger.error(f"{code}: 保存失败 - {e}")
            return False

    def _save_parquet(self, code: str, df: pd.DataFrame):
        """保存为 Parquet 格式"""
        path = self.data_dir / f"{code}.parquet"

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        df.to_parquet(
            path,
            engine="pyarrow",
            compression="snappy",
            index=False
        )

    def _has_recent_data(self, code: str, days: int = 30) -> bool:
        """检查是否有最近 N 天的数据"""
        path = self.data_dir / f"{code}.parquet"
        if not path.exists():
            return False

        try:
            df = pd.read_parquet(path)
            if "date" not in df.columns or len(df) == 0:
                return False

            df["date"] = pd.to_datetime(df["date"])
            latest_date = df["date"].max()
            cutoff = datetime.now() - timedelta(days=days)

            return latest_date >= pd.to_datetime(cutoff)

        except Exception:
            return False

    def get_coverage(self) -> Dict[str, Dict]:
        """
        获取本地数据覆盖情况

        Returns:
            Dict[str, Dict] - {
                "000001": {"days": 2400, "start": "2014-01-01", "end": "2024-01-01"},
                ...
            }
        """
        coverage = {}

        for path in self.data_dir.glob("*.parquet"):
            code = path.stem
            try:
                df = pd.read_parquet(path)
                if "date" in df.columns and len(df) > 0:
                    df["date"] = pd.to_datetime(df["date"])
                    coverage[code] = {
                        "days": len(df),
                        "start": df["date"].min().strftime("%Y-%m-%d"),
                        "end": df["date"].max().strftime("%Y-%m-%d")
                    }
            except Exception as e:
                logger.debug(f"{code}: 读取元数据失败 - {e}")

        return coverage

    def get_data_summary(self) -> Dict:
        """获取数据总览"""
        coverage = self.get_coverage()

        total_stocks = len(coverage)
        total_records = sum(c["days"] for c in coverage.values())

        return {
            "total_stocks": total_stocks,
            "total_records": total_records,
            "storage_mb": self._estimate_storage_size(),
            "date_range": self._get_global_date_range(coverage)
        }

    def _estimate_storage_size(self) -> float:
        """估算存储大小（MB）"""
        total_bytes = sum(
            f.stat().st_size
            for f in self.data_dir.glob("*.parquet")
            if f.is_file()
        )
        return round(total_bytes / (1024 * 1024), 2)

    def _get_global_date_range(self, coverage: Dict) -> Dict:
        """获取全局日期范围"""
        if not coverage:
            return {"start": None, "end": None}

        starts = []
        ends = []

        for c in coverage.values():
            if c["start"]:
                starts.append(c["start"])
            if c["end"]:
                ends.append(c["end"])

        return {
            "start": min(starts) if starts else None,
            "end": max(ends) if ends else None
        }

    def delete_stock(self, code: str) -> bool:
        """删除单只股票数据"""
        path = self.data_dir / f"{code}.parquet"
        if path.exists():
            path.unlink()
            return True
        return False

    def clear_all(self) -> int:
        """清空所有历史数据"""
        count = 0
        for path in self.data_dir.glob("*.parquet"):
            path.unlink()
            count += 1
        return count

    def load_batch(
        self,
        codes: List[str],
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载多只股票数据

        Returns:
            Dict[str, pd.DataFrame] - {code: df}
        """
        results = {}
        for code in codes:
            df = self.load(code, start_date, end_date)
            if len(df) > 0:
                results[code] = df
        return results
