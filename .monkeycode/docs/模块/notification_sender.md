# notification_sender/ 模块

通知发送器模块，支持 12+ 种通知渠道。

## 结构

```
notification_sender/
├── base.py                      # 发送器基类
├── email_sender.py              # 邮件发送
├── wechat_sender.py            # 企业微信
├── feishu_sender.py            # 飞书
├── telegram_sender.py          # Telegram
├── discord_sender.py           # Discord
├── slack_sender.py             # Slack
├── pushover_sender.py          # Pushover
├── pushplus_sender.py          # PushPlus
├── serverchan3_sender.py       # Server酱3
├── astrbot_sender.py           # AstrBot
└── custom_webhook_sender.py    # 自定义 Webhook
```

## 关键文件

| 文件 | 渠道 | 配置项 |
|------|------|--------|
| `email_sender.py` | 邮件 | `EMAIL_SENDER`, `EMAIL_PASSWORD` |
| `wechat_sender.py` | 企业微信 | `WECHAT_WEBHOOK_URL` |
| `feishu_sender.py` | 飞书 | `FEISHU_WEBHOOK_URL` |
| `telegram_sender.py` | Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| `discord_sender.py` | Discord | `DISCORD_WEBHOOK_URL` |
| `slack_sender.py` | Slack | `SLACK_BOT_TOKEN` |

## 发送器接口

```python
class NotificationSender(ABC):
    @property
    def channel(self) -> str:
        """返回渠道名称"""
        
    def send(
        self,
        content: str,
        title: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """
        发送通知
        
        Returns:
            Tuple[是否成功, 错误信息]
        """
```

## 规范

### 添加新渠道

1. 创建 `{channel}_sender.py`
2. 继承 `NotificationSender`
3. 实现 `send()` 方法
4. 在 `notification.py` 注册

```python
class NewChannelSender(NotificationSender):
    @property
    def channel(self) -> str:
        return "new_channel"
        
    def send(self, content: str, title=None, **kwargs):
        # 实现发送逻辑
        return True, None
```
