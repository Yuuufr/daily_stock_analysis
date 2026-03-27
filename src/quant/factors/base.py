# -*- coding: utf-8 -*-
"""
Factor Base Classes and Registry
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd


class BaseFactor(ABC):
    """
    因子基类

    所有因子都必须继承此类并实现 calculate() 方法
    """

    name: str = "base"
    version: str = "1.0.0"
    description: str = ""

    def __init__(self, **kwargs):
        self.config = kwargs

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算因子值

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            pd.Series: 因子值序列
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """返回因子元数据"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "config": self.config
        }

    def validate_data(self, df: pd.DataFrame) -> bool:
        """验证数据是否包含必需列"""
        required = ["open", "high", "low", "close", "volume"]
        return all(col in df.columns for col in required)


class FactorRegistry:
    """
    因子注册表

    提供因子的注册、获取、列举功能
    """

    _factors: Dict[str, BaseFactor] = {}
    _factor_configs: Dict[str, Dict] = {}

    @classmethod
    def register(cls, factor: BaseFactor, config: Dict = None):
        """
        注册因子

        Args:
            factor: 因子实例
            config: 因子配置
        """
        cls._factors[factor.name] = factor
        if config:
            cls._factor_configs[factor.name] = config

    @classmethod
    def get(cls, name: str) -> Optional[BaseFactor]:
        """获取因子实例"""
        return cls._factors.get(name)

    @classmethod
    def list_all(cls) -> Dict[str, BaseFactor]:
        """列出所有注册的因子"""
        return cls._factors.copy()

    @classmethod
    def list_names(cls) -> List[str]:
        """列出所有因子名称"""
        return list(cls._factors.keys())

    @classmethod
    def unregister(cls, name: str) -> bool:
        """注销因子"""
        if name in cls._factors:
            del cls._factors[name]
            if name in cls._factor_configs:
                del cls._factor_configs[name]
            return True
        return False

    @classmethod
    def get_config(cls, name: str) -> Dict:
        """获取因子配置"""
        return cls._factor_configs.get(name, {})

    @classmethod
    def calculate_factor(
        cls,
        name: str,
        df: pd.DataFrame
    ) -> pd.Series:
        """
        计算指定因子

        Args:
            name: 因子名称
            df: 行情数据

        Returns:
            pd.Series: 因子值
        """
        factor = cls.get(name)
        if factor is None:
            raise ValueError(f"因子 {name} 未注册")
        return factor.calculate(df)

    @classmethod
    def calculate_all(
        cls,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算所有已注册因子

        Returns:
            pd.DataFrame: 因子值 DataFrame，列名为因子名称
        """
        results = {}
        for name, factor in cls._factors.items():
            try:
                results[name] = factor.calculate(df)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"因子 {name} 计算失败: {e}"
                )
        return pd.DataFrame(results)


def register_factor(name: str, description: str = ""):
    """
    因子注册装饰器

    用法:
        @register_factor("momentum", description="动量因子")
        class MomentumFactor(BaseFactor):
            ...
    """
    def decorator(cls):
        if not issubclass(cls, BaseFactor):
            raise ValueError(f"{cls} 必须继承 BaseFactor")
        factor_instance = cls()
        factor_instance.name = name
        factor_instance.description = description
        factor_instance.version = "1.0.0"
        FactorRegistry.register(factor_instance)
        return cls
    return decorator
