"""
Backtest Trade Manager - مدیریت معاملات در حالت Backtest
این ماژول نسخه شبیه‌سازی شده TradeManager است که بدون اتصال به صرافی کار می‌کند

🔥 نسخه اصلاح شده - رفع مشکلات:
1. ✅ محاسبه صحیح PnL با توجه به position_size به عنوان USDT
2. مدیریت دقیق کمیسیون و اسلیپیج
3. بهبود trailing stop
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """وضعیت معامله"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeDirection(Enum):
    """جهت معامله"""
    LONG = "long"
    SHORT = "short"


class ExitReason(Enum):
    """دلیل خروج از معامله"""
    TAKE_PROFIT = "take_profit_hit"
    STOP_LOSS = "stop_loss_hit"
    TRAILING_STOP = "trailing_stop_hit"
    TIME_BASED = "time_based_exit"
    SIGNAL_EXIT = "signal_exit"
    MANUAL = "manual_exit"


@dataclass
class BacktestTrade:
    """کلاس داده برای یک معامله در Backtest"""
    trade_id: str
    symbol: str
    direction: TradeDirection
    entry_price: float
    entry_time: datetime
    position_size: float  # به USDT
    stop_loss: float
    take_profit: float
    status: TradeStatus = TradeStatus.OPEN

    # قیمت‌های خروج
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None

    # Trailing stop
    trailing_stop_active: bool = False
    trailing_stop_price: Optional[float] = None

    # آمار
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0  # MAE
    commission_paid: float = 0.0
    slippage_cost: float = 0.0

    # اطلاعات اضافی
    signal_score: float = 0.0
    timeframe: str = ""
    metadata: Dict = field(default_factory=dict)  # 🆕 Complete analysis metadata from signal

    def calculate_pnl(self, current_price: float) -> float:
        """
        ✅ محاسبه سود/زیان فعلی (اصلاح شده)

        فرمول: PnL = (تغییر قیمت درصدی) × سرمایه سرمایه‌گذاری شده
        """
        if self.entry_price == 0:
            return 0.0

        if self.direction == TradeDirection.LONG:
            # محاسبه تغییر قیمت درصدی
            price_change_percent = (current_price - self.entry_price) / self.entry_price
            # اعمال بر روی سرمایه سرمایه‌گذاری شده
            pnl = price_change_percent * self.position_size
        else:  # SHORT
            price_change_percent = (self.entry_price - current_price) / self.entry_price
            pnl = price_change_percent * self.position_size

        return pnl - self.commission_paid - self.slippage_cost

    def calculate_pnl_percent(self, current_price: float) -> float:
        """محاسبه درصد سود/زیان"""
        if self.entry_price == 0:
            return 0.0

        if self.direction == TradeDirection.LONG:
            return ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - current_price) / self.entry_price) * 100

    def update_mfe_mae(self, current_price: float):
        """به‌روزرسانی MFE و MAE"""
        current_pnl = self.calculate_pnl(current_price)

        if current_pnl > self.max_favorable_excursion:
            self.max_favorable_excursion = current_pnl

        if current_pnl < self.max_adverse_excursion:
            self.max_adverse_excursion = current_pnl


class BacktestTradeManager:
    """
    مدیر معاملات برای Backtest
    شبیه‌سازی کامل معاملات بدون اتصال به صرافی
    """

    def __init__(self, config: Dict, initial_balance: float = 10000.0):
        """
        مقداردهی اولیه

        Args:
            config: تنظیمات ربات
            initial_balance: موجودی اولیه (USDT)
        """
        self.config = config
        self.initial_balance = initial_balance
        self.balance = initial_balance

        # تنظیمات Backtest
        backtest_config = config.get('backtest', {})
        self.commission_rate = backtest_config.get('commission_rate', 0.0006)  # 0.06%
        self.slippage = backtest_config.get('slippage', 0.0005)  # 0.05%

        # تنظیمات ریسک
        risk_config = config.get('risk_management', {})
        self.max_open_trades = risk_config.get('max_open_trades', 5)
        self.max_trades_per_symbol = risk_config.get('max_trades_per_symbol', 1)
        self.max_risk_per_trade_percent = risk_config.get('max_risk_per_trade_percent', 2.0)

        # معاملات
        self.active_trades: Dict[str, BacktestTrade] = {}
        self.closed_trades: List[BacktestTrade] = []

        # آمار
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'total_commission': 0.0,
            'total_slippage': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'peak_balance': initial_balance,
            'lowest_balance': initial_balance,
            'max_drawdown': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0
        }

        # ردیابی Equity Curve
        self.equity_curve: List[Dict] = []

        logger.info(f"BacktestTradeManager initialized with balance: {initial_balance} USDT")

    def can_open_trade(self, symbol: str) -> Tuple[bool, str]:
        """
        بررسی امکان باز کردن معامله جدید

        Args:
            symbol: نماد

        Returns:
            (can_open, reason)
        """
        # بررسی تعداد معاملات باز
        if len(self.active_trades) >= self.max_open_trades:
            return False, f"Max open trades limit reached ({self.max_open_trades})"

        # بررسی تعداد معاملات روی این نماد
        symbol_trades = [t for t in self.active_trades.values() if t.symbol == symbol]
        if len(symbol_trades) >= self.max_trades_per_symbol:
            return False, f"Max trades per symbol limit reached ({self.max_trades_per_symbol})"

        # بررسی موجودی کافی
        min_balance_needed = self.initial_balance * 0.1  # حداقل 10% موجودی اولیه
        if self.balance < min_balance_needed:
            return False, f"Insufficient balance (current: {self.balance:.2f}, required: {min_balance_needed:.2f})"

        return True, "OK"

    def open_trade(self, symbol: str, direction: str, entry_price: float,
                   stop_loss: float, take_profit: float, position_size: float,
                   entry_time: datetime, signal_score: float = 0.0,
                   timeframe: str = "", metadata: Dict = None) -> Optional[BacktestTrade]:
        """
        باز کردن معامله جدید

        Args:
            symbol: نماد
            direction: جهت ('long' یا 'short')
            entry_price: قیمت ورود
            stop_loss: حد ضرر
            take_profit: حد سود
            position_size: حجم معامله (USDT)
            entry_time: زمان ورود
            signal_score: امتیاز سیگنال
            timeframe: تایم‌فریم سیگنال
            metadata: اطلاعات اضافی

        Returns:
            شیء BacktestTrade یا None در صورت خطا
        """
        # بررسی امکان باز کردن
        can_open, reason = self.can_open_trade(symbol)
        if not can_open:
            logger.warning(f"Cannot open trade for {symbol}: {reason}")
            return None

        # محاسبه کمیسیون و اسلیپیج ورود
        notional_value = position_size
        entry_commission = notional_value * self.commission_rate
        entry_slippage = notional_value * self.slippage

        # بررسی موجودی کافی برای هزینه‌های ورود
        total_cost = entry_commission + entry_slippage
        if self.balance < total_cost:
            logger.warning(
                f"Insufficient balance for entry costs: "
                f"balance={self.balance:.2f}, needed={total_cost:.2f}"
            )
            return None

        # کسر position_size + هزینه‌ها
        self.balance -= (position_size + total_cost)

        # ایجاد ID یکتا
        trade_id = f"{symbol}_{direction}_{int(entry_time.timestamp())}"

        # تبدیل direction به Enum
        trade_direction = TradeDirection.LONG if direction.lower() == 'long' else TradeDirection.SHORT

        # ایجاد شیء Trade
        trade = BacktestTrade(
            trade_id=trade_id,
            symbol=symbol,
            direction=trade_direction,
            entry_price=entry_price,
            entry_time=entry_time,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_score=signal_score,
            timeframe=timeframe,
            metadata=metadata or {},
            commission_paid=entry_commission,
            slippage_cost=entry_slippage
        )

        # ذخیره معامله
        self.active_trades[trade_id] = trade
        self.stats['total_trades'] += 1
        self.stats['total_commission'] += entry_commission
        self.stats['total_slippage'] += entry_slippage

        logger.info(
            f"✅ Opened {direction.upper()} trade: {symbol} @ {entry_price:.2f} "
            f"(size: {position_size:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f})"
        )

        return trade

    def update_trade_price(self, trade_id: str, current_price: float, current_time: datetime):
        """
        به‌روزرسانی قیمت معامله

        Args:
            trade_id: شناسه معامله
            current_price: قیمت فعلی
            current_time: زمان فعلی
        """
        if trade_id not in self.active_trades:
            return

        trade = self.active_trades[trade_id]
        trade.current_price = current_price

        # محاسبه PnL فعلی
        trade.unrealized_pnl = trade.calculate_pnl(current_price)

        # به‌روزرسانی MFE/MAE
        trade.update_mfe_mae(current_price)

        # 🔥 به‌روزرسانی Trailing Stop
        if trade.trailing_stop_active or self._should_activate_trailing_stop(trade):
            self._update_trailing_stop(trade, current_price)

        # بررسی شرایط خروج
        exit_reason = self._check_exit_conditions(trade, current_price, current_time)

        if exit_reason:
            self.close_trade(trade_id, current_price, current_time, exit_reason)

    def _check_exit_conditions(self, trade: BacktestTrade,
                               current_price: float,
                               current_time: datetime) -> Optional[ExitReason]:
        """
        بررسی شرایط خروج از معامله

        Args:
            trade: معامله
            current_price: قیمت فعلی
            current_time: زمان فعلی

        Returns:
            دلیل خروج یا None
        """
        if trade.direction == TradeDirection.LONG:
            # بررسی Take Profit
            if current_price >= trade.take_profit:
                return ExitReason.TAKE_PROFIT

            # بررسی Stop Loss
            if current_price <= trade.stop_loss:
                return ExitReason.STOP_LOSS

            # بررسی Trailing Stop
            if trade.trailing_stop_active and trade.trailing_stop_price:
                if current_price <= trade.trailing_stop_price:
                    return ExitReason.TRAILING_STOP

        else:  # SHORT
            # بررسی Take Profit
            if current_price <= trade.take_profit:
                return ExitReason.TAKE_PROFIT

            # بررسی Stop Loss
            if current_price >= trade.stop_loss:
                return ExitReason.STOP_LOSS

            # بررسی Trailing Stop
            if trade.trailing_stop_active and trade.trailing_stop_price:
                if current_price >= trade.trailing_stop_price:
                    return ExitReason.TRAILING_STOP

        # بررسی خروج بر اساس زمان
        time_config = self.config.get('risk_management', {})
        if time_config.get('use_time_based_stops', False):
            max_duration = time_config.get('max_trade_duration_hours', 48)
            duration = current_time - trade.entry_time
            if duration >= timedelta(hours=max_duration):
                return ExitReason.TIME_BASED

        return None

    def close_trade(self, trade_id: str, exit_price: float,
                    exit_time: datetime, exit_reason: ExitReason):
        """
        ✅ بستن معامله با محاسبه صحیح balance (اصلاح شده)

        Args:
            trade_id: شناسه معامله
            exit_price: قیمت خروج
            exit_time: زمان خروج
            exit_reason: دلیل خروج
        """
        if trade_id not in self.active_trades:
            logger.warning(f"Trade {trade_id} not found in active trades")
            return

        trade = self.active_trades[trade_id]

        # محاسبه کمیسیون و اسلیپیج خروج
        exit_commission = trade.position_size * self.commission_rate
        exit_slippage = trade.position_size * self.slippage

        # ✅ محاسبه PnL با فرمول صحیح
        if trade.entry_price == 0:
            gross_pnl = 0.0
        else:
            if trade.direction == TradeDirection.LONG:
                # تغییر قیمت درصدی × سرمایه سرمایه‌گذاری شده
                price_change_percent = (exit_price - trade.entry_price) / trade.entry_price
                gross_pnl = price_change_percent * trade.position_size
            else:  # SHORT
                price_change_percent = (trade.entry_price - exit_price) / trade.entry_price
                gross_pnl = price_change_percent * trade.position_size

        # 🔥 محاسبه PnL خالص (با کسر تمام هزینه‌ها)
        # هزینه‌های ورود قبلاً از balance کسر شده
        # پس فقط هزینه‌های خروج را کسر می‌کنیم
        net_pnl = gross_pnl - exit_commission - exit_slippage

        # ثبت هزینه‌های خروج
        trade.commission_paid += exit_commission
        trade.slippage_cost += exit_slippage
        trade.realized_pnl = net_pnl

        # 🔥 بازگشت سرمایه اصلی + سود/زیان به موجودی
        self.balance += (trade.position_size + net_pnl)

        # به‌روزرسانی آمار هزینه‌ها
        self.stats['total_commission'] += exit_commission
        self.stats['total_slippage'] += exit_slippage

        # تنظیم وضعیت
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = exit_reason
        trade.status = TradeStatus.CLOSED

        # به‌روزرسانی آمار
        self._update_statistics(trade)

        # انتقال به معاملات بسته
        self.closed_trades.append(trade)
        del self.active_trades[trade_id]

        # ذخیره در Equity Curve
        self._record_equity_point(exit_time)

        pnl_emoji = "🟢" if net_pnl > 0 else "🔴"
        logger.info(
            f"{pnl_emoji} Closed {trade.direction.value.upper()} trade: {trade.symbol} @ {exit_price:.2f} | "
            f"PnL: {net_pnl:+.2f} USDT ({trade.calculate_pnl_percent(exit_price):+.2f}%) | "
            f"Reason: {exit_reason.value}"
        )

    def _update_statistics(self, trade: BacktestTrade):
        """به‌روزرسانی آمار کلی"""
        pnl = trade.realized_pnl

        # سود/زیان
        if pnl > 0:
            self.stats['winning_trades'] += 1
            self.stats['total_profit'] += pnl
            self.stats['consecutive_wins'] += 1
            self.stats['consecutive_losses'] = 0

            if pnl > self.stats['largest_win']:
                self.stats['largest_win'] = pnl

            if self.stats['consecutive_wins'] > self.stats['max_consecutive_wins']:
                self.stats['max_consecutive_wins'] = self.stats['consecutive_wins']

        else:
            self.stats['losing_trades'] += 1
            self.stats['total_loss'] += abs(pnl)
            self.stats['consecutive_losses'] += 1
            self.stats['consecutive_wins'] = 0

            if pnl < self.stats['largest_loss']:
                self.stats['largest_loss'] = pnl

            if self.stats['consecutive_losses'] > self.stats['max_consecutive_losses']:
                self.stats['max_consecutive_losses'] = self.stats['consecutive_losses']

        # به‌روزرسانی Peak و Drawdown
        if self.balance > self.stats['peak_balance']:
            self.stats['peak_balance'] = self.balance

        if self.balance < self.stats['lowest_balance']:
            self.stats['lowest_balance'] = self.balance

        # محاسبه Drawdown
        if self.stats['peak_balance'] > 0:
            current_drawdown = ((self.stats['peak_balance'] - self.balance) /
                                self.stats['peak_balance']) * 100

            if current_drawdown > self.stats['max_drawdown']:
                self.stats['max_drawdown'] = current_drawdown

    def _record_equity_point(self, timestamp: datetime):
        """ذخیره نقطه در Equity Curve"""
        equity = self.get_total_equity()

        self.equity_curve.append({
            'timestamp': timestamp,
            'balance': self.balance,
            'equity': equity,
            'drawdown': self.get_current_drawdown()
        })

    def update_all_trades(self, prices: Dict[str, float], current_time: datetime):
        """
        به‌روزرسانی تمام معاملات باز

        Args:
            prices: دیکشنری {symbol: price}
            current_time: زمان فعلی
        """
        trades_to_update = list(self.active_trades.keys())

        for trade_id in trades_to_update:
            trade = self.active_trades.get(trade_id)
            if trade and trade.symbol in prices:
                self.update_trade_price(trade_id, prices[trade.symbol], current_time)

    def _should_activate_trailing_stop(self, trade: BacktestTrade) -> bool:
        """
        بررسی اینکه آیا باید trailing stop فعال شود

        Args:
            trade: معامله

        Returns:
            True اگر باید فعال شود
        """
        if trade.trailing_stop_active:
            return False

        # دریافت تنظیمات
        risk_config = self.config.get('risk_management', {})
        if not risk_config.get('use_trailing_stop', False):
            return False

        activation_percent = risk_config.get('trailing_stop_activation_percent', 3.0)

        # محاسبه سود فعلی
        pnl_percent = trade.calculate_pnl_percent(trade.current_price)

        return pnl_percent >= activation_percent

    def _update_trailing_stop(self, trade: BacktestTrade, current_price: float):
        """
        🔥 به‌روزرسانی قیمت Trailing Stop

        Args:
            trade: معامله
            current_price: قیمت فعلی
        """
        # دریافت تنظیمات
        risk_config = self.config.get('risk_management', {})

        # چک کردن که trailing stop فعال است یا خیر
        if not risk_config.get('use_trailing_stop', False):
            return

        activation_percent = risk_config.get('trailing_stop_activation_percent', 3.0)
        distance_percent = risk_config.get('trailing_stop_distance_percent', 2.25)

        # محاسبه سود فعلی
        pnl_percent = trade.calculate_pnl_percent(current_price)

        # فعال‌سازی اگر هنوز فعال نشده
        if not trade.trailing_stop_active:
            if pnl_percent >= activation_percent:
                trade.trailing_stop_active = True

                # محاسبه قیمت اولیه trailing stop
                if trade.direction == TradeDirection.LONG:
                    trade.trailing_stop_price = current_price * (1 - distance_percent / 100)
                else:  # SHORT
                    trade.trailing_stop_price = current_price * (1 + distance_percent / 100)

                logger.info(
                    f"✨ Trailing stop activated for {trade.symbol} at {pnl_percent:.2f}% profit "
                    f"(stop: {trade.trailing_stop_price:.2f})"
                )
            return

        # به‌روزرسانی اگر فعال است
        if trade.direction == TradeDirection.LONG:
            # برای LONG: trailing stop باید فقط بالا بیاید
            new_stop = current_price * (1 - distance_percent / 100)

            # فقط اگر stop جدید بالاتر از stop قبلی است
            if new_stop > trade.trailing_stop_price:
                old_stop = trade.trailing_stop_price
                trade.trailing_stop_price = new_stop

                logger.debug(
                    f"📈 Trailing stop updated for {trade.symbol}: "
                    f"{old_stop:.2f} → {new_stop:.2f} "
                    f"(current: {current_price:.2f}, profit: {pnl_percent:.2f}%)"
                )

        else:  # SHORT
            # برای SHORT: trailing stop باید فقط پایین بیاید
            new_stop = current_price * (1 + distance_percent / 100)

            # فقط اگر stop جدید پایین‌تر از stop قبلی است
            if new_stop < trade.trailing_stop_price:
                old_stop = trade.trailing_stop_price
                trade.trailing_stop_price = new_stop

                logger.debug(
                    f"📉 Trailing stop updated for {trade.symbol}: "
                    f"{old_stop:.2f} → {new_stop:.2f} "
                    f"(current: {current_price:.2f}, profit: {pnl_percent:.2f}%)"
                )

    def get_total_equity(self) -> float:
        """محاسبه کل Equity (موجودی + PnL باز)"""
        open_pnl = sum(t.unrealized_pnl for t in self.active_trades.values())
        return self.balance + open_pnl

    def get_current_drawdown(self) -> float:
        """محاسبه Drawdown فعلی"""
        if self.stats['peak_balance'] == 0:
            return 0.0

        equity = self.get_total_equity()
        drawdown = ((self.stats['peak_balance'] - equity) /
                    self.stats['peak_balance']) * 100

        return max(0.0, drawdown)

    def get_statistics(self) -> Dict:
        """دریافت آمار کامل"""
        stats = self.stats.copy()

        # محاسبه Win Rate
        total = self.stats['total_trades']
        if total > 0:
            stats['win_rate'] = (self.stats['winning_trades'] / total) * 100
        else:
            stats['win_rate'] = 0.0

        # محاسبه Average Win/Loss
        if self.stats['winning_trades'] > 0:
            stats['average_win'] = self.stats['total_profit'] / self.stats['winning_trades']
        else:
            stats['average_win'] = 0.0

        if self.stats['losing_trades'] > 0:
            stats['average_loss'] = self.stats['total_loss'] / self.stats['losing_trades']
        else:
            stats['average_loss'] = 0.0

        # محاسبه Profit Factor
        if self.stats['total_loss'] > 0:
            stats['profit_factor'] = self.stats['total_profit'] / self.stats['total_loss']
        else:
            stats['profit_factor'] = float('inf') if self.stats['total_profit'] > 0 else 0.0

        # اطلاعات موجودی
        stats['current_balance'] = self.balance
        stats['current_equity'] = self.get_total_equity()
        stats['total_return'] = ((self.get_total_equity() - self.initial_balance) /
                                 self.initial_balance) * 100
        stats['current_drawdown'] = self.get_current_drawdown()

        # معاملات باز
        stats['open_trades_count'] = len(self.active_trades)
        stats['total_closed_trades'] = len(self.closed_trades)

        return stats

    def get_equity_curve(self) -> List[Dict]:
        """دریافت Equity Curve"""
        return self.equity_curve.copy()

    def get_trade_history(self) -> List[BacktestTrade]:
        """دریافت تاریخچه معاملات"""
        return self.closed_trades.copy()

    def reset(self):
        """بازنشانی به وضعیت اولیه"""
        self.balance = self.initial_balance
        self.active_trades.clear()
        self.closed_trades.clear()
        self.equity_curve.clear()

        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'total_commission': 0.0,
            'total_slippage': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'peak_balance': self.initial_balance,
            'lowest_balance': self.initial_balance,
            'max_drawdown': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0
        }

        logger.info("BacktestTradeManager reset to initial state")