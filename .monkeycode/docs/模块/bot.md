# bot/ 模块

机器人平台集成模块，支持钉钉、飞书、Discord 等平台的命令处理。

## 结构

```
bot/
├── dispatcher.py      # 命令分发器
├── handler.py         # 消息处理器
├── models.py          # Bot 数据模型
├── commands/          # Bot 命令
│   ├── analyze.py     # 分析命令
│   ├── ask.py         # 问股命令
│   ├── chat.py        # 对话命令
│   ├── batch.py       # 批量分析
│   ├── history.py     # 历史记录
│   ├── market.py      # 大盘行情
│   ├── research.py    # 研究报告
│   ├── status.py      # 系统状态
│   ├── strategies.py  # 策略列表
│   └── help.py        # 帮助
└── platforms/         # 平台适配
    ├── dingtalk.py
    ├── dingtalk_stream.py
    ├── feishu_stream.py
    └── discord.py
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `dispatcher.py` | 命令路由和分发 |
| `handler.py` | 消息处理主逻辑 |
| `platforms/feishu_stream.py` | 飞书 Stream 模式适配 |

## 支持平台

| 平台 | 类型 | 配置 |
|------|------|------|
| 钉钉 | Webhook / Stream | `DINGTALK_APP_KEY`, `DINGTALK_APP_SECRET` |
| 飞书 | Webhook / Stream | `FEISHU_WEBHOOK_URL`, `FEISHU_APP_ID`, `FEISHU_APP_SECRET` |
| Discord | Webhook / Bot | `DISCORD_WEBHOOK_URL`, `DISCORD_BOT_TOKEN` |

## 命令格式

| 命令 | 格式 | 示例 |
|------|------|------|
| `/analyze` | `/analyze <股票代码>` | `/analyze 600519` |
| `/ask` | `/ask <问题>` | `/ask 贵州茅台可以买吗` |
| `/batch` | `/batch <代码1>,<代码2>` | `/batch 600519,000001` |
| `/history` | `/history <股票代码>` | `/history 600519` |
| `/help` | `/help [命令]` | `/help analyze` |

## 规范

### 添加新命令

1. 在 `commands/` 创建 `{command}.py`
2. 定义命令处理函数
3. 在 `dispatcher.py` 注册路由

```python
# commands/newcmd.py
from bot.models import BotMessage

async def handle_newcmd(message: BotMessage) -> str:
    """处理新命令"""
    return "result"
```
