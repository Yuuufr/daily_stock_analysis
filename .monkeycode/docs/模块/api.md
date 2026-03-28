# api/ 模块

FastAPI REST API 层，提供 HTTP 接口供前端和外部调用。

## 结构

```
api/
├── app.py              # FastAPI 应用工厂
├── deps.py             # 依赖注入
├── middlewares/        # 中间件
│   ├── auth.py         # 认证中间件
│   └── error_handler.py # 错误处理
└── v1/
    ├── router.py       # 路由汇总
    ├── endpoints/      # API 端点
    │   ├── analysis.py
    │   ├── history.py
    │   ├── portfolio.py
    │   ├── stocks.py
    │   ├── auth.py
    │   ├── backtest.py
    │   ├── agent.py
    │   ├── system_config.py
    │   ├── quant.py
    │   ├── usage.py
    │   └── health.py
    └── schemas/         # Pydantic Schema
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `app.py` | FastAPI 应用创建和配置 |
| `deps.py` | 依赖注入（`get_config_dep`, `get_database_manager`） |
| `v1/endpoints/analysis.py` | 股票分析接口 |

## 端点概览

| 前缀 | 端点数 | 描述 |
|------|--------|------|
| `/api/v1/analysis` | 4 | 股票分析 |
| `/api/v1/history` | 5 | 历史记录 |
| `/api/v1/stocks` | 4 | 股票数据 |
| `/api/v1/portfolio` | 7 | 持仓管理 |
| `/api/v1/backtest` | 4 | 回测 |
| `/api/v1/agent` | 4 | Agent 对话 |
| `/api/v1/system` | 3 | 系统配置 |

## 规范

### 添加新端点

```python
from fastapi import APIRouter, Depends
from api.deps import get_config_dep
from src.config import Config

router = APIRouter()

@router.get("/something")
def get_something(
    config: Config = Depends(get_config_dep)
):
    return {"data": "value"}
```

### 错误处理

```python
from fastapi import HTTPException

if not found:
    raise HTTPException(status_code=404, detail="Not found")
```
