# Daily Stock Analysis 文档

A股/港股/美股自选股智能分析系统官方文档。

本文档涵盖系统架构、API 接口、开发指南和核心概念，帮助开发者理解、使用和扩展本系统。

---

## 核心文档

### [架构](./ARCHITECTURE.md)

系统设计、技术栈、组件结构和数据流程。从这里开始了解系统如何运作。

### [接口](./INTERFACES.md)

公开 API、CLI 命令、Bot 命令和数据模型。集成或使用此系统的参考。

### [开发者指南](./DEVELOPER_GUIDE.md)

环境搭建、开发工作流、编码规范和常见任务。贡献者必读。

---

## 模块

| 模块 | 描述 | 文档 |
|------|------|------|
| `src/core/` | 核心分析流水线 | [README](./模块/core.md) |
| `src/services/` | 业务服务层 | [README](./模块/services.md) |
| `src/agent/` | Agent 策略对话系统 | [README](./模块/agent.md) |
| `data_provider/` | 多数据源适配层 | [README](./模块/data_provider.md) |
| `api/` | FastAPI REST API | [README](./模块/api.md) |
| `bot/` | 机器人平台集成 | [README](./模块/bot.md) |
| `notification_sender/` | 通知发送器 | [README](./模块/notification_sender.md) |

---

## 核心概念

理解这些领域概念有助于导航代码库：

| 概念 | 描述 |
|------|------|
| [分析流水线](./专有概念/分析流水线.md) | 股票分析的完整流程编排 |
| [数据源适配](./专有概念/数据源适配.md) | 多数据源 fallback 机制 |
| [通知服务](./专有概念/通知服务.md) | 多渠道通知发送 |
| [Agent 系统](./专有概念/Agent系统.md) | 多 Agent 编排策略 |
| [配置管理](./专有概念/配置管理.md) | 环境变量与运行时配置 |

---

## 入门指南

### 项目新人？

按此路径学习：
1. **[架构](./ARCHITECTURE.md)** - 了解全局
2. **[核心概念](#核心概念)** - 学习领域术语
3. **[开发者指南](./DEVELOPER_GUIDE.md)** - 搭建环境
4. **[接口](./INTERFACES.md)** - 探索公开 API

### 需要集成？

1. **[接口](./INTERFACES.md)** - API 契约和认证
2. **[架构](./ARCHITECTURE.md)** - 系统边界和数据流

### 首次贡献？

1. **[开发者指南](./DEVELOPER_GUIDE.md)** - 搭建和工作流
2. **[模块文档](#模块)** - 查看具体模块
3. **[常见任务](./DEVELOPER_GUIDE.md#常见任务)** - 分步指南

---

## 快速参考

### 命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行后端服务
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# 运行 CLI
python main.py --debug

# 运行测试
./scripts/ci_gate.sh offline-tests

# 前端构建
cd apps/dsa-web && npm install && npm run build
```

### 重要文件

| 文件 | 目的 |
|------|------|
| `main.py` | CLI 主入口 |
| `server.py` | FastAPI 服务入口 |
| `src/core/pipeline.py` | 核心分析流水线 |
| `src/analyzer.py` | AI 分析器 |
| `src/config.py` | 配置管理 |
| `.env.example` | 环境变量模板 |
| `docs/full-guide.md` | 完整配置指南 |
