# src/core/ 模块

核心分析流水线模块，包含股票分析的主流程编排和市场分析功能。

## 结构

```
src/core/
├── pipeline.py          # 股票分析主流水线
├── market_review.py     # 大盘复盘
├── trading_calendar.py  # 交易日历
├── market_strategy.py   # 市场策略
├── market_profile.py    # 市场概况
├── backtest_engine.py   # 回测引擎
├── config_manager.py    # 配置管理
└── config_registry.py   # 配置注册表
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `pipeline.py` | 核心调度器，协调数据获取、技术分析、AI 分析、通知推送 |
| `market_review.py` | 大盘复盘分析 |
| `backtest_engine.py` | 回测引擎，验证分析准确性 |

## 依赖

**本模块依赖**：
- `data_provider/` - 多数据源适配
- `src/analyzer.py` - AI 分析器
- `src/search_service.py` - 搜索服务
- `src/notification.py` - 通知服务
- `src/storage.py` - 数据库存储

**依赖本模块的**：
- `main.py` - CLI 入口
- `api/v1/endpoints/analysis.py` - API 端点

## 核心类

### StockAnalysisPipeline

```python
class StockAnalysisPipeline:
    def __init__(self, config=None, max_workers=None):
        """初始化调度器"""
        
    def analyze_stocks(self, stock_codes, force_refresh=False):
        """分析多只股票"""
        
    def run_market_review(self, region="cn"):
        """运行大盘复盘"""
```

## 规范

### 错误处理

- 单股失败不影响整体流程
- 使用 `logger.error()` 记录错误
- 异常应向上抛出不捕获
