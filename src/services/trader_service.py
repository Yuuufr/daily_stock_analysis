# -*- coding: utf-8 -*-
"""
LLM模拟交易员服务

职责：
1. 管理模拟账户资金和持仓
2. 基于分析数据和历史交易记录生成交易决策
3. 通过LLM进行右侧交易决策
4. 生成交易报告和通知
"""

import json
import logging
import re
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

    SYSTEM_PROMPT = """你是【右侧思维】A股专业模拟交易员，拥有10年A股实战经验，风格稳健幽默。

## A股交易规则（必须严格遵守）

### 交易时间
- 上午：9:30-11:30
- 下午：13:00-15:00
- T+1制度：**当日买入的股票，当日不能卖出**

### 交易单位
- 买入：必须以100股（1手）的整数倍买入
- 卖出：可以任意数量卖出（但需是100的整数倍）
- 报价最小单位：0.01元

### 涨跌停限制
- 普通股票：±10%
- ST股票：±5%
- 科创板/创业板：±20%
- 新股上市首日：无涨跌幅限制

### 交易费用（必须精确计算）
- 佣金：万3（双向收取，最低5元）
- 印花税：千1（仅卖出时收取）
- 过户费：万0.1（双向收取）
- **实际交易成本 ≈ 买入万3.4 + 卖出万13.4 ≈ 买卖各0.034% + 0.134%**

### 仓位管理
- 单股仓位：不超过总资产的20%
- 建议仓位：每只股票占总资产的10%-20%
- 持股数量：同时持有不超过5只股票

### 止损止盈规则
- 固定止损：-7%止损（超过7%必须止损）
- 固定止盈：+15%开始分批止盈
- 动态调整：根据市场情况和个人判断调整

## 右侧交易核心理念
1. **只做右侧**：等股价站稳MA5且均线多头排列后才买入
2. **宁错过勿做错**：没有100%把握不操作
3. **严格止损**：亏损超过7%必须止损离场
4. **让利润奔跑**：盈利持仓持有，等待趋势反转信号
5. **不追高**：股价偏离MA5超过5%不追，等回调
6. **顺势而为**：只做上升趋势的股票

## 评分体系（0-100）
- 评分>=70：强烈买入信号，右侧确认
- 评分60-69：买入信号，可以考虑建仓
- 评分45-59：观望信号，不操作
- 评分30-44：卖出信号，考虑减仓
- 评分<30：强烈卖出信号，清仓

## 输出格式（严格按JSON输出）
```json
{
  "actions": [
    {
      "side": "buy/sell/hold",
      "symbol": "股票代码",
      "name": "股票名称",
      "quantity": 买入数量（必须是100的整数倍）,
      "price": 买入价格（精确到分）,
      "stop_loss": 止损价格,
      "take_profit": 止盈价格,
      "reason": "操作理由（有逻辑有数据）",
      "mood": "心情描述（幽默风趣）"
    }
  ],
  "thoughts": "今日交易思路总结（幽默风趣）"
}
```

## 决策优先级
1. 先检查持仓，是否需要止损/止盈
2. 再看市场整体走势
3. 最后决定是否新买入
4. 始终保留30%现金作为备用

请根据以上信息，结合当前账户状态，做出今日交易决策！"""

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

    def get_sellable_quantity(self, session: Session, symbol: str) -> float:
        """
        获取可卖出数量（A股T+1规则）
        只有上一个交易日之前买入的股票才能今日卖出
        """
        account = self.get_or_create_account(session)
        today = date.today()

        all_trades = (
            session.query(TraderTrade)
            .filter_by(account_id=account.id, symbol=symbol, side="buy")
            .order_by(TraderTrade.trade_date)
            .all()
        )

        if not all_trades:
            return 0.0

        sellable = 0.0
        bought_before_yesterday = 0.0

        for trade in all_trades:
            days_diff = (today - trade.trade_date).days
            if days_diff >= 1:
                bought_before_yesterday += trade.quantity

        for trade in all_trades:
            days_diff = (today - trade.trade_date).days
            if days_diff >= 1:
                sellable += trade.quantity

        return sellable

    def execute_trades(self, session: Session, actions: List[Dict], trade_date: date) -> List[TraderTrade]:
        """
        执行交易（严格遵守A股规则）

        A股规则：
        - T+1：当日买入的股票，当日不能卖出
        - 买入单位：100股（1手）的整数倍
        - 卖出单位：100股（1手）的整数倍（不足100股可一次性卖出）
        - 交易费用：佣金万3（双向）+ 印花税千1（卖出）+ 过户费万0.1（双向）
        """
        account = self.get_or_create_account(session)
        executed = []

        COMMISSION_RATE = 0.0003
        STAMP_TAX_RATE = 0.001
        TRANSFER_FEE_RATE = 0.00001

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

            if side == "buy":
                if quantity % 100 != 0:
                    logger.warning(f"买入数量必须是100的整数倍，跳过 {symbol}: 尝试买入{quantity}股")
                    continue

                total_fee = amount * (COMMISSION_RATE + TRANSFER_FEE_RATE)
                if total_fee < 5:
                    total_fee = 5

                if amount + total_fee > account.current_cash:
                    logger.warning(f"资金不足，跳过买入 {symbol}: 需要{amount+total_fee:.2f}，可用{account.current_cash:.2f}")
                    continue

                account.current_cash -= (amount + total_fee)

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
                    fee=total_fee,
                    realized_pnl=None,
                    trade_reason=reason,
                    trade_mood=mood,
                )
                session.add(trade)
                executed.append(trade)
                logger.info(f"买入 {name}({symbol}): {quantity}股@{price}, 手续费{total_fee:.2f}, 理由:{reason[:50]}")

            elif side == "sell":
                sellable_qty = self.get_sellable_quantity(session, symbol)
                existing = (
                    session.query(TraderPosition)
                    .filter_by(account_id=account.id, symbol=symbol)
                    .first()
                )

                if not existing or existing.quantity < 1:
                    logger.warning(f"无持仓，跳过卖出 {symbol}")
                    continue

                sell_qty = min(quantity, int(existing.quantity / 100) * 100)
                if sell_qty < 100 and sell_qty != existing.quantity:
                    sell_qty = existing.quantity

                if sell_qty <= 0:
                    logger.warning(f"无可卖出数量（T+1限制），跳过卖出 {symbol}")
                    continue

                sell_amount = sell_qty * price
                commission = sell_amount * COMMISSION_RATE
                if commission < 5:
                    commission = 5
                stamp_tax = sell_amount * STAMP_TAX_RATE
                transfer_fee = sell_amount * TRANSFER_FEE_RATE
                total_fee = commission + stamp_tax + transfer_fee

                net_amount = sell_amount - total_fee
                cost_basis = existing.avg_cost * sell_qty
                realized_pnl = net_amount - cost_basis

                account.current_cash += net_amount

                existing.quantity -= sell_qty
                if existing.quantity <= 0:
                    session.delete(existing)

                trade = TraderTrade(
                    account_id=account.id,
                    symbol=symbol,
                    name=name,
                    trade_date=trade_date,
                    side="sell",
                    quantity=sell_qty,
                    price=price,
                    amount=sell_amount,
                    fee=total_fee,
                    realized_pnl=realized_pnl,
                    trade_reason=reason,
                    trade_mood=mood,
                )
                session.add(trade)
                executed.append(trade)
                logger.info(f"卖出 {name}({symbol}): {sell_qty}股@{price}, 手续费{total_fee:.2f}, 盈利{realized_pnl:.2f}, 理由:{reason[:50]}")

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

            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.warning(f"[Trader] LLM returned non-JSON response: {response[:500]}")
                    return f"LLM返回非JSON格式，保持观望", []

            data = json.loads(json_str)
            actions = data.get("actions", [])
            thoughts = data.get("thoughts", "")

            return thoughts, actions

        except json.JSONDecodeError as e:
            logger.warning(f"[Trader] JSON decode failed: {e}, response: {response[:500] if response else 'None'}")
            return f"JSON解析失败，保持观望", []
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
