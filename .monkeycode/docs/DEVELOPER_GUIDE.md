# 开发者指南

本文档面向有意参与本项目开发的工程师，涵盖环境搭建、开发工作流、编码规范和常见任务指南。

## 项目目的

Daily Stock Analysis（A股/港股/美股自选股智能分析系统）是一个全功能的股票智能分析平台，用于自动化股票分析和多渠道推送。

**核心职责**：
- 多数据源行情数据获取
- 技术分析与 AI 智能分析
- 新闻搜索与社交舆情整合
- 多渠道通知推送
- Agent 策略对话系统
- 回测验证分析准确性

**相关系统**：
- GitHub Actions - 定时任务调度
- FastAPI - HTTP API 服务
- React/Vite - Web 前端
- Electron - 桌面客户端

---

## 环境搭建

### 前置条件

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | 后端运行时 |
| Node.js | >= 18 | 前端构建 |
| npm / pnpm | 最新版 | 前端包管理 |
| Git | - | 版本控制 |
| Docker | - | 容器化部署（可选） |

### 安装

```bash
# 克隆仓库
git clone https://github.com/Yuuufr/daily_stock_analysis.git
cd daily_stock_analysis

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd apps/dsa-web
npm install

# 回到项目根目录
cd ../..
```

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

**必需配置**：

| 变量 | 描述 | 示例 |
|------|------|------|
| `STOCK_LIST` | 自选股代码，逗号分隔 | `600519,300750,002594` |
| `GEMINI_API_KEY` | Google AI API Key | `AIza...` |
| `WECHAT_WEBHOOK_URL` | 企业微信 Webhook | `https://qyapi.weixin.qq.com/...` |

**可选配置**：

详见 `.env.example` 或 [docs/full-guide.md](./full-guide.md)。

⚠️ **绝不提交密钥**。使用 `.env` 文件，`.env` 已在 `.gitignore` 中忽略。

### 运行

```bash
# 后端服务（开发）
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# Web 前端（开发）
cd apps/dsa-web
npm run dev

# CLI 主程序
python main.py --debug

# 定时任务模式
python main.py --schedule

# 仅 Web UI
python webui.py
```

---

## 开发工作流

### 代码质量工具

| 工具 | 命令 | 目的 |
|------|------|------|
| Python 语法检查 | `./scripts/ci_gate.sh syntax` | 检查 Python 语法 |
| Flake8 | `./scripts/ci_gate.sh flake8` | 代码风格检查 |
| pytest | `./scripts/ci_gate.sh offline-tests` | 离线测试 |
| npm lint | `cd apps/dsa-web && npm run lint` | 前端代码检查 |
| npm build | `cd apps/dsa-web && npm run build` | 前端构建 |

### 提交前检查

这些检查在 `git commit` 时自动运行（通过 pre-commit hooks 或 CI）：

1. Python 语法检查
2. Flake8 静态分析
3. 离线测试套件

手动运行全部检查：

```bash
./scripts/ci_gate.sh all
```

### 分支策略

```
main          # 生产就绪代码
├── develop   # 开发分支（如果存在）
├── feature/* # 新功能
├── fix/*     # Bug 修复
├── refactor/* # 重构
└── chore/*   # 杂项（依赖更新、文档等）
```

### Pull Request 流程

1. 从 `main` 创建功能分支
2. 编写代码和测试
3. 运行验证：`./scripts/ci_gate.sh`
4. 创建 PR 并填写描述
5. 处理审查反馈
6. Squash 合并到 main

---

## 常见任务

### 添加新 API 端点

**需修改的文件**：
1. `api/v1/endpoints/{domain}.py` - 添加路由处理器
2. `api/v1/schemas/{domain}.py` - 添加请求/响应 Schema
3. `api/v1/router.py` - 注册路由（如果需要）
4. `tests/test_api_{domain}.py` - 添加测试

**步骤**：

1. 在 `api/v1/endpoints/` 创建或编辑端点文件
2. 定义 Pydantic Schema
3. 实现路由处理器
4. 添加类型注解
5. 编写测试
6. 更新 API 文档

### 添加新通知渠道

**需修改的文件**：
1. `src/notification_sender/{channel}_sender.py` - 创建发送器
2. `src/notification.py` - 注册新渠道
3. `.env.example` - 添加配置项
4. `tests/test_notification_{channel}.py` - 添加测试

**步骤**：

1. 创建发送器类，继承基础接口
2. 实现 `send()` 方法
3. 在 `NotificationService` 中注册
4. 添加配置项到 `.env.example`
5. 编写测试

### 添加新数据源

**需修改的文件**：
1. `data_provider/{source}_fetcher.py` - 创建数据获取器
2. `data_provider/base.py` - 注册数据源
3. `tests/test_fetcher_{source}.py` - 添加测试

**步骤**：

1. 创建 Fetcher 类，实现统一接口
2. 实现必要方法（获取历史、实时行情、筹码等）
3. 在 `DataFetcherManager` 中添加优先级
4. 处理错误和降级
5. 编写测试

### 添加新 Agent 技能

**需修改的文件**：
1. `strategies/{skill_name}.yaml` - 创建策略定义
2. `src/agent/skills/` - 添加技能实现（如果需要）
3. `src/agent/agents/{agent}.py` - 集成技能

**策略 YAML 结构**：

```yaml
name: bull_trend
description: 多头趋势策略
version: 1.0.0
rules:
  - MA5 > MA10 > MA20
  - bias_rate < 5%
```

### 修复 Bug

**流程**：

1. 编写复现 bug 的失败测试
2. 在代码中定位根因
3. 用最小改动修复
4. 验证测试通过
5. 检查是否有类似问题

**提交示例**：`fix(core): handle None value in stock quote`

### 添加环境变量

**需修改的文件**：
1. `.env.example` - 添加示例值和注释
2. `src/config.py` - 添加配置属性
3. `docs/full-guide.md` - 文档化变量

---

## 编码规范

### Python

**文件组织**：
- 每个模块一个文件
- 相关文件放在同一目录
- 使用 `__init__.py` 导出公共接口

**命名约定**：

| 类型 | 约定 | 示例 |
|------|------|------|
| 文件 | snake_case | `stock_analyzer.py` |
| 类 | PascalCase | `StockAnalysisPipeline` |
| 函数 | snake_case | `fetch_stock_data` |
| 常量 | SCREAMING_SNAKE | `MAX_WORKERS` |
| 私有成员 | `_leading_underscore` | `_internal_method` |

**类型注解**：
- 函数参数和返回值应添加类型注解
- 使用 `Optional[T]` 表示可选参数
- 使用 `List[T]`, `Dict[K, V]` 等集合类型

**错误处理**：

```python
# 推荐：特定异常类型
raise ValueError("Invalid stock code")

# 避免：通用错误
raise Exception("Something went wrong")
```

**日志**：

```python
# 包含上下文
logger.info("Stock analysis completed", {"stock": code, "duration": elapsed})

# 使用适当级别
logger.debug()  # 开发详情
logger.info()   # 正常操作
logger.warning() # 可恢复问题
logger.error()  # 需要关注的故障
```

### TypeScript / React

**命名约定**：

| 类型 | 约定 | 示例 |
|------|------|------|
| 文件 | kebab-case | `stock-chart.tsx` |
| 组件 | PascalCase | `StockChart` |
| 函数/变量 | camelCase | `fetchStockData` |
| 常量 | SCREAMING_SNAKE | `MAX_RETRY_COUNT` |

**组件规范**：
- 使用函数组件 + Hooks
- Props 使用 interface 定义
- 优先使用 Zzustand 管理状态

### 测试

**Python 测试**：
- 测试文件：`tests/test_{module}.py`
- 使用 pytest 框架
- 标记网络测试：`@pytest.mark.network`
- 离线测试：`pytest -m "not network"`

```python
def test_stock_analysis_pipeline():
    """Should return analysis result for valid stock."""
    # Arrange
    pipeline = StockAnalysisPipeline()
    
    # Act
    result = pipeline.analyze("600519")
    
    # Assert
    assert result.stock_code == "600519"
    assert result.decision_type in ("buy", "hold", "sell")
```

**覆盖率目标**：
- 核心业务逻辑：> 80%
- API 端点：> 70%
- 工具函数：> 60%

---

## 项目结构指南

### 目录职责

| 目录 | 职责 | 优先级 |
|------|------|--------|
| `src/core/` | 核心流水线，最关键 | 高 |
| `src/services/` | 业务服务层 | 高 |
| `data_provider/` | 多数据源适配 | 高 |
| `api/v1/endpoints/` | API 端点 | 中 |
| `src/agent/` | Agent 系统 | 中 |
| `src/notification_sender/` | 通知渠道 | 低 |
| `bot/` | Bot 集成 | 低 |

### 高风险区域

修改以下区域需要格外小心，可能影响生产环境：

- `src/core/pipeline.py` - 核心流水线
- `src/analyzer.py` - AI 分析逻辑
- `data_provider/base.py` - 数据源抽象
- `src/notification.py` - 通知发送逻辑
- `.github/workflows/` - CI/CD 配置
