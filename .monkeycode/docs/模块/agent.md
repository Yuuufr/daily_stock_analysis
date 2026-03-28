# src/agent/ 模块

Agent 策略对话系统，支持自然语言问股和多策略技术分析。

## 结构

```
src/agent/
├── executor.py        # Agent 执行器
├── orchestrator.py    # 多 Agent 编排
├── runner.py          # Agent 运行器
├── llm_adapter.py     # LLM 适配器
├── factory.py         # Agent 工厂
├── memory.py          # Agent 记忆
├── conversation.py    # 对话管理
├── events.py          # 事件监控
├── research.py        # 研究工具
├── protocols.py       # 协议定义
├── agents/            # 多种 Agent
│   ├── base_agent.py
│   ├── technical_agent.py
│   ├── intel_agent.py
│   ├── risk_agent.py
│   ├── decision_agent.py
│   └── portfolio_agent.py
├── skills/            # 策略技能
│   ├── base.py
│   ├── defaults.py
│   ├── aggregator.py
│   ├── router.py
│   └── skill_agent.py
├── strategies/        # 策略路由
└── tools/             # Agent 工具
    ├── analysis_tools.py
    ├── data_tools.py
    ├── backtest_tools.py
    ├── search_tools.py
    ├── market_tools.py
    └── registry.py
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `orchestrator.py` | 多 Agent 协作编排 |
| `agents/technical_agent.py` | 技术分析 Agent |
| `skills/router.py` | 策略路由 |

## 规范

### Agent 实现模式

```python
class BaseAgent:
    async def think(self, context: dict) -> dict:
        """Agent 思考逻辑"""
        pass
        
    async def act(self, thought: dict) -> dict:
        """Agent 行动"""
        pass
```

### 工具注册

```python
@tool_registry.register
async def some_tool(param: str) -> str:
    """工具描述"""
    pass
```
