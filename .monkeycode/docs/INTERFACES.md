# 接口文档

本文档涵盖项目的所有公开接口，包括 HTTP API 端点、CLI 命令、Bot 命令和内部模块接口。

## 目录

- [FastAPI HTTP API](#fastapi-http-api)
- [CLI 命令](#cli-命令)
- [Bot 命令](#bot-命令)

---

## FastAPI HTTP API

基础 URL：`http://{host}:{port}/api/v1`

### 认证

API 支持可选的运行时认证（通过 WebUI 设置页面启用/关闭）。认证方式使用 Cookie Session。

### 端点列表

| 标签 | 前缀 | 描述 |
|------|------|------|
| [Auth](#auth) | `/api/v1/auth` | 认证接口 |
| [Agent](#agent) | `/api/v1/agent` | Agent 策略对话 |
| [Analysis](#analysis) | `/api/v1/analysis` | 股票分析 |
| [History](#history) | `/api/v1/history` | 历史记录 |
| [Stocks](#stocks) | `/api/v1/stocks` | 股票数据 |
| [Backtest](#backtest) | `/api/v1/backtest` | 回测接口 |
| [SystemConfig](#systemconfig) | `/api/v1/system` | 系统配置 |
| [Usage](#usage) | `/api/v1/usage` | 用量查询 |
| [Portfolio](#portfolio) | `/api/v1/portfolio` | 持仓管理 |

---

### Auth

认证接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/auth/login` | 用户登录 |
| POST | `/auth/logout` | 用户登出 |
| GET | `/auth/status` | 获取认证状态 |

---

### Agent

Agent 策略对话接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/agent/chat` | 发送对话消息 |
| GET | `/agent/history/{session_id}` | 获取对话历史 |
| DELETE | `/agent/history/{session_id}` | 删除对话历史 |
| GET | `/agent/sessions` | 获取会话列表 |

---

### Analysis

股票分析接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/analysis/analyze` | 触发股票分析（异步） |
| GET | `/analysis/status/{task_id}` | 查询任务状态 |
| GET | `/analysis/tasks` | 获取任务列表 |
| GET | `/analysis/tasks/stream` | SSE 实时推送任务状态 |

#### POST /analysis/analyze

**请求体**：

```json
{
  "stocks": ["600519", "000001"],
  "force_refresh": false,
  "report_type": "simple",
  "report_language": "zh"
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `stocks` | `string[]` | 是 | 股票代码列表 |
| `force_refresh` | `boolean` | 否 | 是否强制刷新数据（默认 false） |
| `report_type` | `string` | 否 | 报告类型：`simple` / `full` / `brief`（默认 `simple`） |
| `report_language` | `string` | 否 | 报告语言：`zh` / `en`（默认 `zh`） |

**响应**：

```json
{
  "task_id": "abc123",
  "message": "分析任务已接受",
  "stocks_count": 2
}
```

---

### History

历史记录接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/history` | 获取历史分析列表 |
| GET | `/history/{query_id}` | 获取历史详情 |
| DELETE | `/history/{query_id}` | 删除历史记录 |
| GET | `/history/{query_id}/report` | 获取 Markdown 报告 |
| POST | `/history/intel` | 获取新闻情报 |

#### GET /history

**查询参数**：

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `stock_code` | `string` | 否 | 股票代码筛选 |
| `start_date` | `string` | 否 | 开始日期 (YYYY-MM-DD) |
| `end_date` | `string` | 否 | 结束日期 (YYYY-MM-DD) |
| `page` | `integer` | 否 | 页码，从 1 开始（默认 1） |
| `limit` | `integer` | 否 | 每页数量，1-100（默认 20） |

---

### Stocks

股票数据接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/stocks/extract-from-image` | 从图片提取股票代码 |
| POST | `/stocks/parse-import` | 解析 CSV/Excel/剪贴板 |
| GET | `/stocks/{code}/quote` | 获取实时行情 |
| GET | `/stocks/{code}/history` | 获取历史行情 |

#### GET /stocks/{code}/quote

**响应**：

```json
{
  "code": "600519",
  "name": "贵州茅台",
  "price": 1850.00,
  "change_pct": 2.5,
  "volume": 3000000,
  "turnover": 15000000000,
  "high": 1860.00,
  "low": 1820.00,
  "open": 1825.00,
  "prev_close": 1805.00,
  "timestamp": "2024-01-15 14:30:00"
}
```

---

### Backtest

回测接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/backtest/run` | 运行回测 |
| GET | `/backtest/results` | 获取回测结果列表 |
| GET | `/backtest/results/{backtest_id}` | 获取回测详情 |
| DELETE | `/backtest/results/{backtest_id}` | 删除回测结果 |

---

### SystemConfig

系统配置接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/system/config` | 获取系统配置 |
| PUT | `/system/config` | 更新系统配置 |
| GET | `/system/config/schema` | 获取配置 schema |

---

### Usage

用量查询接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/usage/summary` | 获取用量汇总 |
| GET | `/usage/daily` | 获取每日用量 |
| GET | `/usage/models` | 获取模型使用统计 |

---

### Portfolio

持仓管理接口。

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/portfolio` | 获取持仓列表 |
| POST | `/portfolio` | 添加持仓 |
| PUT | `/portfolio/{id}` | 更新持仓 |
| DELETE | `/portfolio/{id}` | 删除持仓 |
| POST | `/portfolio/import` | 批量导入持仓 |
| GET | `/portfolio/risks` | 获取持仓风险分析 |

---

## CLI 命令

### 主入口

```bash
python main.py              # 正常运行
python main.py --debug      # 调试模式
python main.py --dry-run    # 仅获取数据不分析
python main.py --stocks 600519,000001  # 指定分析特定股票
python main.py --no-notify  # 不发送推送通知
python main.py --single-notify  # 单股推送模式
python main.py --schedule   # 定时任务模式
python main.py --market-review  # 仅运行大盘复盘
python main.py --webui      # 启动 Web 管理界面
python main.py --webui-only  # 仅启动 Web 服务
```

### 参数说明

| 参数 | 描述 |
|------|------|
| `--debug` | 启用调试模式，输出详细日志 |
| `--dry-run` | 仅获取数据，不进行 AI 分析 |
| `--stocks` | 指定要分析的股票代码，逗号分隔 |
| `--no-notify` | 不发送推送通知 |
| `--single-notify` | 单股推送模式（每分析完一只立即推送） |
| `--workers` | 并发线程数（默认使用配置值） |
| `--schedule` | 启用定时任务模式 |
| `--no-run-immediately` | 定时任务启动时不立即执行一次 |
| `--market-review` | 仅运行大盘复盘分析 |
| `--no-market-review` | 跳过大盘复盘分析 |
| `--force-run` | 跳过交易日检查，强制执行 |
| `--webui` | 启动 Web 管理界面 |
| `--webui-only` | 仅启动 Web 服务 |

### 服务启动

```bash
# FastAPI 服务
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# Web UI 独立启动
python webui.py
```

---

## Bot 命令

Bot 支持多种命令格式。

### 命令列表

| 命令 | 描述 | 示例 |
|------|------|------|
| `/analyze` | 分析指定股票 | `/analyze 600519` |
| `/ask` | 自然语言问股 | `/ask 贵州茅台现在可以买吗` |
| `/batch` | 批量分析 | `/batch 600519,000001` |
| `/chat` | 与 Agent 对话 | `/chat 今天大盘怎么样` |
| `/history` | 查看历史分析 | `/history 600519` |
| `/market` | 大盘行情 | `/market` |
| `/research` | 研究报告 | `/research 600519` |
| `/status` | 系统状态 | `/status` |
| `/strategies` | 查看可用策略 | `/strategies` |
| `/help` | 帮助信息 | `/help` |

### 平台支持

| 平台 | 类型 | 配置 |
|------|------|------|
| 钉钉 | Webhook / Stream | `DINGTALK_APP_KEY`, `DINGTALK_APP_SECRET` |
| 飞书 | Webhook / Stream | `FEISHU_WEBHOOK_URL`, `FEISHU_APP_ID`, `FEISHU_APP_SECRET` |
| Discord | Webhook / Bot | `DISCORD_WEBHOOK_URL`, `DISCORD_BOT_TOKEN` |

---

## 数据模型

### AnalysisResult

分析结果数据结构。

```python
@dataclass
class AnalysisResult:
    stock_code: str              # 股票代码
    stock_name: str              # 股票名称
    decision_type: str            # 决策类型：buy / hold / sell /观望
    operation_advice: str        # 操作建议
    analysis_summary: str        # 分析摘要
    sentiment_score: int         # 情绪分数 0-100
    confidence_level: str        # 置信度：high / medium / low
    trend_prediction: str         # 趋势预测
    target_price: Optional[float]  # 目标价
    stop_loss: Optional[float]    # 止损价
    keyRisks: List[str]          # 关键风险
    momentum_indicators: Dict     # 动量指标
    support_resistance: Dict      # 支撑阻力位
    dashboard: Dict              # 仪表盘数据
```

### StockData

股票数据模型。

```python
@dataclass
class StockData:
    code: str                    # 股票代码
    name: str                    # 股票名称
    market: str                  # 市场：cn / hk / us
    current_price: float         # 当前价格
    change_pct: float            # 涨跌幅
    volume: float                # 成交量
    turnover: float             # 成交额
    high: float                  # 最高价
    low: float                   # 最低价
    open: float                  # 开盘价
    prev_close: float            # 昨收
    timestamp: datetime          # 数据时间
```

### Portfolio

持仓数据结构。

```python
@dataclass
class Portfolio:
    id: int                      # 持仓 ID
    stock_code: str              # 股票代码
    stock_name: str              # 股票名称
    shares: float                # 持股数量
    avg_cost: float              # 平均成本
    current_price: float         # 当前价格
    market_value: float          # 市值
    profit_loss: float           # 盈亏金额
    profit_loss_pct: float       # 盈亏比例
    updated_at: datetime         # 更新时间
```
