# data_provider/ 模块

多数据源适配层，统一不同数据源的接口，实现失败自动降级。

## 结构

```
data_provider/
├── base.py                   # 基类与公共接口
├── akshare_fetcher.py        # AkShare 数据源
├── tushare_fetcher.py        # Tushare Pro
├── yfinance_fetcher.py       # Yahoo Finance（美股）
├── efinance_fetcher.py       # efinance 东方财富
├── pytdx_fetcher.py          # 通达信
├── baostock_fetcher.py       # Baostock
├── tickflow_fetcher.py       # TickFlow
├── us_index_mapping.py       # 美股指数映射
├── fundamental_adapter.py    # 基本面适配器
└── realtime_types.py        # 实时数据类型
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `base.py` | `DataFetcherManager` 统一接口和 fallback 逻辑 |
| `efinance_fetcher.py` | 东方财富数据（最高优先级） |
| `yfinance_fetcher.py` | Yahoo Finance 美股数据 |

## 数据源优先级

1. eFinance（东方财富）
2. AkShare
3. Tushare Pro
4. Pytdx
5. Baostock
6. YFinance（美股专用）

## 规范

### 新增数据源

1. 继承 `BaseFetcher`
2. 实现必要方法
3. 在 `DataFetcherManager.__init__()` 注册优先级

```python
class NewFetcher(BaseFetcher):
    def get_historical_data(self, code: str, days: int = 250):
        # 实现
        pass
```
