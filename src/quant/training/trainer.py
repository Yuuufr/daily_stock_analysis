# -*- coding: utf-8 -*-
"""
Weekend Trainer

周末自动训练系统
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)


class WeekendTrainer:
    """
    周末自动训练系统
    
    训练流程：
    1. 检测当前市场 Regime
    2. 准备训练数据
    3. 历史因子回测
    4. 特征重要性分析
    5. 训练 sklearn 模型
    6. 训练 PyTorch 模型
    7. 模型选择与保存
    """

    def __init__(self):
        self.data_manager = None
        self.model_manager = None
        self.regime_detector = None

    def run_full_training(self) -> Dict:
        """
        执行完整周末训练流程

        Returns:
            Dict - 训练报告
        """
        logger.info("=" * 50)
        logger.info("开始周末训练")
        logger.info("=" * 50)

        report = {
            "start_time": datetime.now(),
            "steps": [],
            "status": "running"
        }

        try:
            regime, reg_details = self._detect_regime()
            report["steps"].append({
                "step": "regime_detection",
                "result": regime,
                "details": reg_details
            })

            X_train, y_train, feature_names = self._prepare_training_data()
            report["steps"].append({
                "step": "data_preparation",
                "samples": len(X_train) if X_train is not None else 0,
                "features": len(feature_names) if feature_names else 0
            })

            backtest_results = self._run_factor_backtest(X_train, y_train, feature_names)
            report["steps"].append({
                "step": "factor_backtest",
                "results": backtest_results
            })

            importance = self._analyze_feature_importance(X_train, y_train, feature_names)
            report["steps"].append({
                "step": "feature_importance",
                "top_features": importance[:10] if importance else []
            })

            sklearn_metrics = self._train_sklearn_model(X_train, y_train)
            report["steps"].append({
                "step": "sklearn_training",
                "metrics": sklearn_metrics
            })

            pytorch_metrics = self._train_pytorch_model(X_train, y_train)
            report["steps"].append({
                "step": "pytorch_training",
                "metrics": pytorch_metrics
            })

            best_model = self._select_and_save_best_model(
                sklearn_metrics or {},
                pytorch_metrics or {}
            )
            report["steps"].append({
                "step": "model_selection",
                "best": best_model
            })

            report["status"] = "success"
            report["end_time"] = datetime.now()

            logger.info("周末训练完成")

        except Exception as e:
            logger.error(f"训练失败: {e}")
            report["status"] = "failed"
            report["error"] = str(e)
            report["end_time"] = datetime.now()

        self._save_report(report)
        return report

    def _detect_regime(self) -> Tuple[str, Dict]:
        """检测市场 Regime"""
        try:
            from src.quant.regime.detector import RegimeDetector
            detector = RegimeDetector()
            regime, details = detector.detect()
            return regime.value, details
        except Exception as e:
            logger.warning(f"Regime 检测失败: {e}")
            return "neutral", {}

    def _prepare_training_data(self) -> Tuple:
        """准备训练数据"""
        try:
            from src.quant.data import HistoricalDataManager
            from src.quant.factors import FactorRegistry
            from src.quant.factors.builtin_factors import register_builtin_factors

            register_builtin_factors()

            dm = HistoricalDataManager()
            coverage = dm.get_coverage()
            stock_codes = list(coverage.keys())[:100]

            if not stock_codes:
                logger.warning("无本地数据，跳过训练")
                return None, None, []

            all_features = []
            all_labels = []

            for code in stock_codes:
                df = dm.load(code)
                if df is None or len(df) < 100:
                    continue

                for fname, factor in FactorRegistry.list_all().items():
                    try:
                        factor_values = factor.calculate(df).values
                        all_features.append(factor_values[:len(df)])
                    except Exception:
                        pass

                future_return = df["close"].pct_change(5).shift(-5)
                labels = (future_return > 0.02).astype(int).values
                all_labels.extend(labels[:len(df)])

            if not all_features:
                return None, None, []

            X = np.column_stack(all_features)
            y = np.array(all_labels)

            X = np.nan_to_num(X, nan=0.0)

            return X, y, list(FactorRegistry.list_all().keys())

        except Exception as e:
            logger.error(f"准备训练数据失败: {e}")
            return None, None, []

    def _run_factor_backtest(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> Dict:
        """历史因子回测"""
        results = {}

        if X is None or len(X.shape) < 2:
            return results

        for i, fname in enumerate(feature_names):
            if i >= X.shape[1]:
                break

            try:
                factor_values = X[:, i]
                ic = np.corrcoef(factor_values, y)[0, 1] if len(np.unique(factor_values)) > 1 else 0

                n_groups = 5
                quantiles = np.percentile(factor_values, np.linspace(0, 100, n_groups + 1))
                group_returns = []
                for j in range(n_groups):
                    mask = (factor_values >= quantiles[j]) & (factor_values < quantiles[j + 1])
                    if mask.sum() > 0:
                        group_returns.append(y[mask].mean())

                results[fname] = {
                    "ic": float(ic) if not np.isnan(ic) else 0,
                    "group_returns": [float(r) for r in group_returns] if group_returns else []
                }

            except Exception as e:
                logger.debug(f"因子 {fname} 回测失败: {e}")

        return results

    def _analyze_feature_importance(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> List:
        """特征重要性分析"""
        try:
            import sklearn
            from sklearn.ensemble import RandomForestClassifier

            if X is None or y is None or len(X) == 0:
                return []

            n_samples = min(len(X), 1000)
            indices = np.random.choice(len(X), n_samples, replace=False)
            X_sample = X[indices]
            y_sample = y[indices]

            rf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
            rf.fit(X_sample, y_sample)

            importances = rf.feature_importances_
            ranked = sorted(
                zip(feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )

            try:
                from src.quant.factors.versions import FactorVersionManager
                vm = FactorVersionManager()
                vm.save_importance("latest", ranked)
            except Exception:
                pass

            return ranked

        except Exception as e:
            logger.warning(f"特征重要性分析失败: {e}")
            return []

    def _train_sklearn_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """训练 sklearn 模型"""
        results = {}

        try:
            import sklearn
            from sklearn.model_selection import train_test_split
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

            if X is None or y is None or len(X) < 50:
                return results

            n_samples = min(len(X), 2000)
            indices = np.random.choice(len(X), n_samples, replace=False)
            X_sample = X[indices]
            y_sample = y[indices]

            X_train, X_test, y_train, y_test = train_test_split(
                X_sample, y_sample, test_size=0.2, random_state=42, stratify=y_sample
            )

            rf = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            rf.fit(X_train, y_train)
            y_pred = rf.predict(X_test)

            results["random_forest"] = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
                "recall": float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
                "f1": float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
            }

            try:
                mm = self._get_model_manager()
                mm.save_model(
                    rf,
                    model_type="sklearn",
                    model_name="random_forest",
                    metrics=results["random_forest"]
                )
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"sklearn 训练失败: {e}")

        return results

    def _train_pytorch_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """训练 PyTorch 模型"""
        results = {}

        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler

            if X is None or y is None or len(X) < 50:
                return results

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X[:min(len(X), 2000)])
            y_sample = y[:min(len(X), 2000)]

            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_sample, test_size=0.2, random_state=42, stratify=y_sample
            )

            X_train_t = torch.FloatTensor(X_train).to(device)
            y_train_t = torch.LongTensor(y_train).to(device)
            X_test_t = torch.FloatTensor(X_test).to(device)
            y_test_t = torch.LongTensor(y_test).to(device)

            train_dataset = TensorDataset(X_train_t, y_train_t)
            train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)

            class SimpleMLP(nn.Module):
                def __init__(self, input_dim, hidden_dim=32, num_classes=2):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(hidden_dim, num_classes)
                    )

                def forward(self, x):
                    return self.net(x)

            model = SimpleMLP(X_train.shape[1]).to(device)
            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

            model.train()
            for epoch in range(30):
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()

            model.eval()
            with torch.no_grad():
                outputs = model(X_test_t)
                _, predicted = torch.max(outputs, 1)
                accuracy = (predicted == y_test_t).float().mean().item()

            results["mlp"] = {"accuracy": float(accuracy)}

            try:
                mm = self._get_model_manager()
                mm.save_model(
                    model,
                    model_type="pytorch",
                    model_name="mlp",
                    metrics=results["mlp"]
                )
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"PyTorch 训练失败: {e}")

        return results

    def _select_and_save_best_model(
        self,
        sklearn_metrics: Dict,
        pytorch_metrics: Dict
    ) -> Dict:
        """选择最佳模型"""
        all_models = {}

        for name, metrics in sklearn_metrics.items():
            all_models[f"sklearn_{name}"] = metrics

        for name, metrics in pytorch_metrics.items():
            all_models[f"pytorch_{name}"] = metrics

        if not all_models:
            return {"best_model": None, "metrics": {}}

        best_name = max(
            all_models.keys(),
            key=lambda k: all_models[k].get("f1", all_models[k].get("accuracy", 0))
        )
        best_metrics = all_models[best_name]

        return {
            "best_model": best_name,
            "metrics": best_metrics
        }

    def _get_model_manager(self):
        """获取模型管理器"""
        if self.model_manager is None:
            try:
                from src.quant.models.model_manager import ModelManager
                self.model_manager = ModelManager()
            except Exception:
                return None
        return self.model_manager

    def _save_report(self, report: Dict):
        """保存训练报告"""
        try:
            report_dir = Path("data/reports")
            report_dir.mkdir(parents=True, exist_ok=True)

            import json
            filename = f"weekend_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_dir / filename, "w") as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"报告已保存: {filename}")

        except Exception as e:
            logger.warning(f"保存报告失败: {e}")

    def trigger_manual_run(self) -> Dict:
        """手动触发训练"""
        logger.info("手动触发周末训练")
        return self.run_full_training()
