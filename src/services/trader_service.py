# -*- coding: utf-8 -*-
"""
LLM模拟交易员服务

职责：
1. 管理模拟账户资金和持仓
2. 基于分析数据和历史交易记录生成交易决策
3. 通过LLM进行右侧交易决策
4. 生成交易报告和通知
"""

import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.storage import DatabaseManager, TraderAccount, TraderPosition, TraderTrade
from src.analyzer import GeminiAnalyzer

logger = logging.getLogger(__name__)

INITIAL_CASH = 50000.0
TRADE_FEE_RATE = 0.0003


@dataclass
class TraderPositionInfo:
    symbol: str
    name: str
    quantity: float
    avg_cost: float
    last_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float]
    take_profit: Optional[float]


@dataclass
class TraderTradeInfo:
    symbol: str
    name: str
    trade_date: date
    side: str
    quantity: float
    price: float
    amount: float
    fee: float
    realized_pnl: Optional[float]
    trade_reason: str
    trade_mood: str


@dataclass
class TraderAccountInfo:
    total_equity: float
    current_cash: float
    total_market_value: float
    total_return_pct: float
    month_return_pct: float
    positions: List[TraderPositionInfo]
    recent_trades: List[TraderTradeInfo]


class TraderService:
    """LLM模拟交易员服务"""

    SYSTEM_PROMPT = """你是【右侧思维】专业模拟交易员，拥有10年A股交易经验，风格稳健幽默。

## 铁律（永不动摇）
1. **只做右侧交易**：只在趋势确认后买入，不抄底不逃顶
2. **宁错过勿做错**：没有100%确认信号坚决不买入
3. **止损永远正确**：亏损时不幻想，果断止损离场
4. **让利润奔跑**：盈利持仓可以持有，等待趋势反转
5. **仓位管理**：单股仓位不超总资产的20%，分散持仓
6. **不追高**：股价在MA5上方过远不追，等回调

## 交易规则
- 初始资金：5万元
- 目标：用炒股赚1个亿（不现实但要追求）
- 止损位：-5% 止损，或LLM根据个股情况设定
- 止盈位：+10% 止盈，或LLM根据个股情况动态调整
- 仓位：由LLM根据评分和风险自行决定（建议10%-20%）
- 手续费：万3（买卖都收）

## 输出格式
必须严格按以下JSON格式输出，不要添加任何解释：
```json
{
  "actions": [
    {
      "side": "buy/sell/hold",
      "symbol": "股票代码",
      "name": "股票名称",
      "quantity": 买入数量（手，整数）,
      "price": 买入价格,
      "stop_loss": 止损价（可为空）,
      "take_profit": 止盈价（可为空）,
      "reason": "操作理由（幽默有理）",
      "mood": "心情描述（滑稽幽默）"
    }
  ],
  "thoughts": "内心独白（幽默有趣）"
}
```

## 评分体系参考
- 评分>65：强势信号，可考虑买入
- 评分45-65：中性信号，谨慎观望
- 评分<45：弱势信号，不参与

请根据以上信息做出今日交易决策。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager.get_instance()
        self.analyzer = GeminiAnalyzer()

    def get_or_create_account(self, session: Session) -> TraderAccount:
        """获取或创建交易账户"""
        account = session.query(TraderAccount).first()
        if not account:
            account = TraderAccount(
                name="模拟账户",
                initial_cash=INITIAL_CASH,
                current_cash=INITIAL_CASH,
                total_market_value=0.0,
                total_equity=INITIAL_CASH,
                total_return_pct=0.0,
                month_return_pct=0.0,
                month_start_equity=INITIAL_CASH,
            )
            session.add(account)
            session.commit()
            logger.info(f"创建LLM交易账户，初始资金: {INITIAL_CASH}")
        return account

    def get_account_info(self, session: Session) -> TraderAccountInfo:
        """获取账户信息"""
        account = self.get_or_create_account(session)
        positions = session.query(TraderPosition).filter_by(account_id=account.id).all()
        recent_trades = (
            session.query(TraderTrade)
            .filter_by(account_id=account.id)
            .order_by(desc(TraderTrade.trade_date))
            .limit(10)
            .all()
        )

        position_infos = [
            TraderPositionInfo(
                symbol=p.symbol,
                name=p.name or p.symbol,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                last_price=p.last_price,
                market_value=p.market_value,
                unrealized_pnl=p.unrealized_pnl,
                unrealized_pnl_pct=p.unrealized_pnl_pct,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
            )
            for p in positions if p.quantity > 0
        ]

        trade_infos = [
            TraderTradeInfo(
                symbol=t.symbol,
                name=t.name or t.symbol,
                trade_date=t.trade_date,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                amount=t.amount,
                fee=t.fee,
                realized_pnl=t.realized_pnl,
                trade_reason=t.trade_reason or "",
                trade_mood=t.trade_mood or "",
            )
            for t in recent_trades
        ]

        return TraderAccountInfo(
            total_equity=account.total_equity,
            current_cash=account.current_cash,
            total_market_value=account.total_market_value,
            total_return_pct=account.total_return_pct,
            month_return_pct=account.month_return_pct,
            positions=position_infos,
            recent_trades=trade_infos,
        )

    def get_positions(self, session: Session) -> List[TraderPosition]:
        """获取当前持仓"""
        account = self.get_or_create_account(session)
        return (
            session.query(TraderPosition)
            .filter_by(account_id=account.id)
            .filter(TraderPosition.quantity > 0)
            .all()
        )

    def get_trade_history(self, session: Session, symbol: Optional[str] = None) -> List[TraderTrade]:
        """获取交易历史"""
        account = self.get_or_create_account(session)
        query = session.query(TraderTrade).filter_by(account_id=account.id)
        if symbol:
            query = query.filter_by(symbol=symbol)
        return query.order_by(desc(TraderTrade.trade_date)).all()

    def format_trade_history_for_llm(self, session: Session) -> str:
        """格式化交易历史供LLM参考"""
        trades = self.get_trade_history(session)
        if not trades:
            return "暂无交易历史"

        lines = []
        for t in trades[:20]:
            pnl_str = f"+{t.realized_pnl:.2f}" if t.realized_pnl and t.realized_pnl > 0 else f"{t.realized_pnl:.2f}"
            lines.append(
                f"- {t.trade_date}: {t.side.upper()} {t.name}({t.symbol}) "
                f"{t.quantity}股@{t.price} 盈亏:{pnl_str} 理由:{t.trade_reason[:30] if t.trade_reason else '无'}"
            )
        return "\n".join(lines)

    def format_positions_for_llm(self, session: Session) -> str:
        """格式化持仓供LLM参考"""
        positions = self.get_positions(session)
        if not positions:
            return "当前空仓"

        lines = []
        for p in positions:
            pnl_pct = f"+{p.unrealized_pnl_pct:.2f}" if p.unrealized_pnl_pct > 0 else f"{p.unrealized_pnl_pct:.2f}"
            lines.append(
                f"- {p.name}({p.symbol}): {p.quantity}股 "
                f"成本{p.avg_cost:.2f} 现价{p.last_price:.2f} "
                f"盈亏{p.unrealized_pnl:.2f}({pnl_pct}%) "
                f"止盈{str(p.take_profit) if p.take_profit else 'N/A'} "
                f"止损{str(p.stop_loss) if p.stop_loss else 'N/A'}"
            )
        return "\n".join(lines)

    def update_position_prices(self, session: Session, price_map: Dict[str, float]) -> None:
        """更新持仓价格"""
        positions = self.get_positions(session)
        for p in positions:
            if p.symbol in price_map:
                p.last_price = price_map[p.symbol]
                p.market_value = p.quantity * p.last_price
                p.unrealized_pnl = (p.last_price - p.avg_cost) * p.quantity
                p.unrealized_pnl_pct = ((p.last_price - p.avg_cost) / p.avg_cost * 100) if p.avg_cost > 0 else 0
                p.updated_at = datetime.now()
        self._recalculate_account(session)
        session.commit()

    def execute_trades(self, session: Session, actions: List[Dict], trade_date: date) -> List[TraderTrade]:
        """执行交易"""
        account = self.get_or_create_account(session)
        executed = []

        for action in actions:
            if action.get("side") == "hold":
                continue

            symbol = action.get("symbol")
            name = action.get("name", symbol)
            side = action.get("side", "buy")
            quantity = int(action.get("quantity", 0))
            price = float(action.get("price", 0))
            stop_loss = action.get("stop_loss")
            take_profit = action.get("take_profit")
            reason = action.get("reason", "")
            mood = action.get("mood", "")

            if quantity <= 0 or price <= 0:
                continue

            amount = quantity * price
            fee = amount * TRADE_FEE_RATE

            if side == "buy":
                if amount + fee > account.current_cash:
                    logger.warning(f"资金不足，跳过买入 {symbol}: 需要{amount+fee:.2f}，可用{account.current_cash:.2f}")
                    continue

                account.current_cash -= (amount + fee)

                existing = (
                    session.query(TraderPosition)
                    .filter_by(account_id=account.id, symbol=symbol)
                    .first()
                )

                if existing and existing.quantity > 0:
                    total_qty = existing.quantity + quantity
                    existing.avg_cost = (existing.avg_cost * existing.quantity + amount) / total_qty
                    existing.quantity = total_qty
                    existing.last_price = price
                    existing.market_value = existing.quantity * price
                    existing.unrealized_pnl = (price - existing.avg_cost) * existing.quantity
                    existing.unrealized_pnl_pct = ((price - existing.avg_cost) / existing.avg_cost * 100) if existing.avg_cost > 0 else 0
                else:
                    position = TraderPosition(
                        account_id=account.id,
                        symbol=symbol,
                        name=name,
                        quantity=quantity,
                        avg_cost=price,
                        last_price=price,
                        market_value=amount,
                        unrealized_pnl=0,
                        unrealized_pnl_pct=0,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                    )
                    session.add(position)

                trade = TraderTrade(
                    account_id=account.id,
                    symbol=symbol,
                    name=name,
                    trade_date=trade_date,
                    side="buy",
                    quantity=quantity,
                    price=price,
                    amount=amount,
                    fee=fee,
                    realized_pnl=None,
                    trade_reason=reason,
                    trade_mood=mood,
                )
                session.add(trade)
                executed.append(trade)
                logger.info(f"买入 {name}({symbol}): {quantity}股@{price}, 理由:{reason[:50]}")

            elif side == "sell":
                existing = (
                    session.query(TraderPosition)
                    .filter_by(account_id=account.id, symbol=symbol)
                    .first()
                )

                if not existing or existing.quantity < quantity:
                    logger.warning(f"持仓不足，跳过卖出 {symbol}")
                    continue

                sell_amount = amount - fee
                account.current_cash += sell_amount

                cost_basis = existing.avg_cost * quantity
                realized_pnl = sell_amount - cost_basis

                existing.quantity -= quantity
                if existing.quantity <= 0:
                    session.delete(existing)

                trade = TraderTrade(
                    account_id=account.id,
                    symbol=symbol,
                    name=name,
                    trade_date=trade_date,
                    side="sell",
                    quantity=quantity,
                    price=price,
                    amount=amount,
                    fee=fee,
                    realized_pnl=realized_pnl,
                    trade_reason=reason,
                    trade_mood=mood,
                )
                session.add(trade)
                executed.append(trade)
                logger.info(f"卖出 {name}({symbol}): {quantity}股@{price}, 盈利{realized_pnl:.2f}, 理由:{reason[:50]}")

        self._recalculate_account(session)
        session.commit()
        return executed

    def _recalculate_account(self, session: Session) -> None:
        """重新计算账户总额"""
        account = self.get_or_create_account(session)

        positions = self.get_positions(session)
        account.total_market_value = sum(p.market_value for p in positions)
        account.total_equity = account.current_cash + account.total_market_value
        account.total_return_pct = ((account.total_equity - INITIAL_CASH) / INITIAL_CASH * 100) if INITIAL_CASH > 0 else 0

        month_start = account.month_start_equity
        account.month_return_pct = ((account.total_equity - month_start) / month_start * 100) if month_start > 0 else 0

        account.updated_at = datetime.now()

    def check_month_reset(self, session: Session) -> None:
        """检查是否需要重置月收益统计"""
        account = self.get_or_create_account(session)
        now = datetime.now()

        if account.updated_at and account.updated_at.month != now.month:
            account.month_start_equity = account.total_equity
            account.month_return_pct = 0.0
            logger.info(f"新月份开始，月收益重置，起点: {account.month_start_equity:.2f}")
            session.commit()

    def decide_trades(
        self,
        session: Session,
        analysis_results: List[Dict],
        trade_date: date,
    ) -> Tuple[str, List[Dict]]:
        """
        让LLM根据分析结果和历史交易记录决定交易

        Returns:
            (thoughts, actions) - LLM内心独白和操作列表
        """
        account_info = self.get_account_info(session)
        positions_text = self.format_positions_for_llm(session)
        history_text = self.format_trade_history_for_llm(session)

        analysis_text = "\n".join([
            f"- {r.get('name', r.get('code'))}({r.get('code')}): "
            f"评分{r.get('sentiment_score', 'N/A')} "
            f"建议{r.get('operation_advice', 'N/A')} "
            f"现价{r.get('current_price', 'N/A')} "
            f"MA5{r.get('ma5', 'N/A')} MA10{r.get('ma10', 'N/A')} MA20{r.get('ma20', 'N/A')}"
            for r in analysis_results
        ]) if analysis_results else "今日无分析数据"

        user_prompt = f"""## 今日分析数据
{analysis_text}

## 当前账户状态
- 总资产: {account_info.total_equity:.2f}元
- 可用资金: {account_info.current_cash:.2f}元
- 持仓市值: {account_info.total_market_value:.2f}元
- 总收益率: {account_info.total_return_pct:+.2f}%
- 月收益率: {account_info.month_return_pct:+.2f}%

## 当前持仓
{positions_text}

## 历史交易记录
{history_text}

## 今日日期
{trade_date}

请做出交易决策！"""

        try:
            response = self.analyzer.generate_text(
                prompt=f"{self.SYSTEM_PROMPT}\n\n{user_prompt}",
                max_tokens=2048,
                temperature=0.3,
            )

            if not response:
                return "LLM未返回有效响应，保持观望", []

            import json
            import re

            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return "无法解析LLM响应", []

            data = json.loads(json_str)
            actions = data.get("actions", [])
            thoughts = data.get("thoughts", "")

            return thoughts, actions

        except Exception as e:
            logger.error(f"LLM交易决策失败: {e}")
            return f"LLM决策出错: {str(e)[:100]}", []

    def format_trader_report(self, account_info: TraderAccountInfo, thoughts: str = "") -> str:
        """格式化交易员报告"""
        lines = [
            "**🤖 LLM模拟交易员**",
            "",
            f"💰 总资产: {account_info.total_equity:,.0f}元 | "
            f"📈 总收益: {account_info.total_return_pct:+.2f}% | "
            f"📅 月收益: {account_info.month_return_pct:+.2f}%",
            f"🏧 可用: {account_info.current_cash:,.0f}元 | "
            f"🏦 市值: {account_info.total_market_value:,.0f}元",
            "",
        ]

        if account_info.positions:
            lines.append("**📋 持仓情况**")
            for p in account_info.positions:
                pnl_pct_str = f"+{p.unrealized_pnl_pct:.2f}%" if p.unrealized_pnl_pct >= 0 else f"{p.unrealized_pnl_pct:.2f}%"
                pnl_str = f"+{p.unrealized_pnl:.0f}" if p.unrealized_pnl >= 0 else f"{p.unrealized_pnl:.0f}"
                lines.append(
                    f"• {p.name}({p.symbol}) | {p.quantity}股 | "
                    f"成本{p.avg_cost:.2f} | 现价{p.last_price:.2f} | "
                    f"盈亏{pnl_str}({pnl_pct_str})"
                )
            lines.append("")

        if thoughts:
            lines.append(f"**💭 {thoughts[:100]}**")
            lines.append("")

        return "\n".join(lines)


def get_trader_service() -> TraderService:
    """获取TraderService单例"""
    return TraderService()
