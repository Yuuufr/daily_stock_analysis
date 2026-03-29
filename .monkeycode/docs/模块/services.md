# src/services/ 模块

业务服务层模块，提供各类业务功能的服务封装。

## 结构

```
src/services/
├── analysis_service.py          # 分析服务
├── history_service.py          # 历史记录服务
├── portfolio_service.py        # 持仓管理服务
├── backtest_service.py         # 回测服务
├── task_queue.py               # 任务队列
├── task_service.py             # 任务服务
├── system_config_service.py    # 系统配置服务
├── portfolio_risk_service.py   # 持仓风控服务
├── portfolio_import_service.py  # 持仓导入服务
├── image_stock_extractor.py    # 图片股票提取
├── import_parser.py            # 导入解析
├── name_to_code_resolver.py    # 名称转代码
├── social_sentiment_service.py # 社交舆情服务
├── stock_code_utils.py         # 股票代码工具
├── stock_service.py            # 股票服务
├── agent_model_service.py       # Agent 模型服务
├── trader_service.py           # LLM 模拟交易员服务
└── report_renderer.py          # 报告渲染
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `history_service.py` | 历史分析记录查询和 Markdown 报告生成 |
| `portfolio_service.py` | 持仓 CRUD 操作 |
| `task_queue.py` | 异步任务队列管理 |
| `image_stock_extractor.py` | 从图片中提取股票代码（Vision LLM） |

## 规范

### 服务模式

```python
class SomeService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    def some_operation(self, param: str) -> Result:
        """业务操作"""
        pass
```

### 错误处理

- 使用自定义异常类
- 记录详细日志
- 返回错误信息而非抛出
