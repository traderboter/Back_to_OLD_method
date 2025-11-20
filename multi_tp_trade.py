"""
ماژول multi_tp_trade.py: پیاده‌سازی کلاس Trade با پشتیبانی از حد سود چند مرحله‌ای
این ماژول قابلیت‌های پیشرفته مدیریت پوزیشن شامل خروج چندمرحله‌ای را فراهم می‌کند.
بهینه‌سازی شده با قابلیت به‌روزرسانی پارامترها در حین اجرا.
"""

import logging
import math
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union, TypedDict
from decimal import Decimal
import json  # برای پردازش JSON

logger = logging.getLogger(__name__)


class PortionDict(TypedDict, total=False):
    """تایپ دیکشنری برای نگهداری اطلاعات بخش‌های بسته شده معامله"""
    exit_price: float
    exit_quantity: float
    exit_time: datetime
    exit_reason: str
    profit_loss: float
    profit_loss_percent: float
    commission: float
    net_pnl: float


class TrailingStopParams(TypedDict, total=False):
    """تایپ دیکشنری برای نگهداری پارامترهای حد ضرر متحرک"""
    enabled: bool
    activation_percent: float  # درصد سود لازم برای فعال شدن
    distance_percent: float    # فاصله از قیمت فعلی (درصد)
    use_atr: bool              # استفاده از ATR برای تنظیم فاصله
    atr_multiplier: float      # ضریب ATR
    atr_period: int            # دوره زمانی ATR
    current_stop_price: float  # قیمت فعلی حد ضرر متحرک
    is_active: bool            # وضعیت فعال بودن


class Trade:
    """کلاس نگهداری اطلاعات یک معامله با پشتیبانی از حد سود چند مرحله‌ای و به‌روزرسانی پارامترها"""

    def __init__(
            self,
            trade_id: str,
            symbol: str,
            direction: str,
            entry_price: float,
            stop_loss: float,
            take_profit: float,
            quantity: float,
            risk_amount: float,
            timestamp: datetime,
            status: str = 'pending',  # وضعیت اولیه
            exit_price: Optional[float] = None,
            exit_time: Optional[datetime] = None,
            exit_reason: Optional[str] = None,
            profit_loss: Optional[float] = None,
            profit_loss_percent: Optional[float] = None,
            commission_paid: float = 0.0,
            initial_stop_loss: Optional[float] = None,
            risk_reward_ratio: Optional[float] = None,
            max_favorable_excursion: float = 0.0,
            max_adverse_excursion: float = 0.0,
            # --- Multi-TP Fields ---
            is_multitp_enabled: bool = False,
            take_profit_levels: List[Tuple[float, float]] = None,
            current_tp_level_index: int = 0,
            closed_portions: List[PortionDict] = None,
            remaining_quantity: Optional[float] = None,
            # --- Current Status Fields ---
            current_price: Optional[float] = None,
            last_update_time: Optional[datetime] = None,
            # --- New Fields ---
            entry_reasons_json: Optional[str] = None,
            tags: List[str] = None,
            strategy_name: Optional[str] = None,
            timeframe: Optional[str] = None,
            signal_quality: Optional[float] = None,
            stop_moved_count: int = 0,
            market_state: Optional[str] = None,
            notes: Optional[str] = None,
            trade_stats: Optional[Dict[str, Any]] = None,
            max_duration_days: Optional[float] = None,
            partial_tp_percent: Optional[float] = None,
            partial_tp_size: Optional[float] = None,
            # --- Trailing Stop Parameters ---
            trailing_stop_params: Optional[Dict[str, Any]] = None,
            signal_id: Optional[str] = None,  # شناسه سیگنال مرتبط با معامله
            # 🆕 NEW in v3.1.0: Detailed pattern tracking from signal
            signal_patterns_details: Optional[List[Dict[str, Any]]] = None,  # جزئیات الگوهای تشخیص داده شده
            signal_pattern_contributions: Optional[Dict[str, float]] = None,  # سهم هر الگو در امتیاز
            signal_score_breakdown: Optional[Dict[str, Any]] = None  # breakdown کامل امتیاز سیگنال
    ):
        """
        مقداردهی اولیه معامله
        """
        self.trade_id = trade_id
        self.symbol = symbol
        self.direction = direction
        self.entry_price = self._sanitize_float(entry_price)
        self.stop_loss = self._sanitize_float(stop_loss)
        self.take_profit = self._sanitize_float(take_profit)
        self.quantity = self._sanitize_float(quantity)
        self.risk_amount = self._sanitize_float(risk_amount) if risk_amount is not None else 0.0
        self.timestamp = timestamp
        self.status = status
        self.signal_id = signal_id

        self.exit_price = self._sanitize_float(exit_price)
        self.exit_time = exit_time
        self.exit_reason = exit_reason
        self.profit_loss = self._sanitize_float(profit_loss)
        self.profit_loss_percent = self._sanitize_float(profit_loss_percent)
        self.commission_paid = self._sanitize_float(commission_paid) if commission_paid is not None else 0.0

        # تنظیم حد ضرر اولیه اگر مشخص نشده باشد
        self.initial_stop_loss = self._sanitize_float(initial_stop_loss if initial_stop_loss is not None else stop_loss)
        self.risk_reward_ratio = self._sanitize_float(risk_reward_ratio)

        if self.risk_reward_ratio is None or self.risk_reward_ratio <= 0:
            self.risk_reward_ratio = self._calculate_initial_rr()

        self.max_favorable_excursion = self._sanitize_float(max_favorable_excursion) if max_favorable_excursion is not None else 0.0
        self.max_adverse_excursion = self._sanitize_float(max_adverse_excursion) if max_adverse_excursion is not None else 0.0

        self.is_multitp_enabled = is_multitp_enabled
        self.take_profit_levels = take_profit_levels or []
        self.current_tp_level_index = current_tp_level_index
        self.closed_portions = closed_portions or []
        self.remaining_quantity = self._sanitize_float(remaining_quantity if remaining_quantity is not None else quantity)

        self.current_price = self._sanitize_float(current_price if current_price is not None else entry_price)
        self.last_update_time = last_update_time if last_update_time is not None else timestamp

        # --- تخصیص مقادیر فیلدهای جدید ---
        self.entry_reasons_json = entry_reasons_json
        self.tags = tags or []
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.signal_quality = self._sanitize_float(signal_quality)
        self.stop_moved_count = stop_moved_count
        self.market_state = market_state
        self.notes = notes
        self.trade_stats = trade_stats
        self.max_duration_days = max_duration_days
        self.partial_tp_percent = partial_tp_percent
        self.partial_tp_size = partial_tp_size

        # 🆕 NEW in v3.1.0: ذخیره جزئیات الگوهای سیگنال
        self.signal_patterns_details = signal_patterns_details or []
        self.signal_pattern_contributions = signal_pattern_contributions or {}
        self.signal_score_breakdown = signal_score_breakdown or {}

        # --- اضافه کردن ساختار مدیریت حد ضرر متحرک ---
        self.trailing_stop_params = trailing_stop_params or TrailingStopParams(
            enabled=False,
            activation_percent=3.0,
            distance_percent=2.25,
            use_atr=False,
            atr_multiplier=2.0,
            atr_period=14,
            current_stop_price=self.stop_loss,
            is_active=False
        )

        # اطمینان از صحت مقدار باقی‌مانده
        if self.remaining_quantity is not None and self.remaining_quantity < 0:
            self.remaining_quantity = 0.0
        if self.remaining_quantity is not None and self.remaining_quantity == 0 and self.status != 'closed':
            self.status = 'closed'
            if not self.exit_time: self.exit_time = datetime.now().astimezone()
            if not self.exit_reason: self.exit_reason = 'quantity_zeroed'
            if self.profit_loss is None: self._calculate_final_pnl()

        # اعتبارسنجی داده‌های معامله
        self._validate_trade_data()

    def _calculate_initial_rr(self) -> Optional[float]:
        """محاسبه نسبت ریسک به ریوارد اولیه."""
        if self.entry_price and self.initial_stop_loss and self.take_profit:
            risk_dist = abs(self.entry_price - self.initial_stop_loss)
            reward_dist = abs(self.take_profit - self.entry_price)  # استفاده از TP نهایی
            if risk_dist > 1e-9:
                return self._sanitize_float(reward_dist / risk_dist)
        return None

    def _validate_trade_data(self):
        """بررسی صحت داده‌های معامله و رفع مشکلات احتمالی"""
        try:
            if self.entry_price is not None and self.entry_price <= 0:
                logger.warning(f"قیمت ورود نامعتبر {self.entry_price} برای معامله {self.trade_id}. تنظیم به None.")
                self.entry_price = None

            # بررسی حد ضرر و حد سود نسبت به قیمت ورود
            if self.stop_loss is not None and self.entry_price is not None:
                if self.direction == 'long' and self.stop_loss >= self.entry_price:
                    logger.warning(
                        f"حد ضرر نامعتبر {self.stop_loss} >= قیمت ورود {self.entry_price} برای معامله خرید {self.trade_id}. تنظیم به 99% قیمت ورود.")
                    self.stop_loss = self.entry_price * 0.99
                elif self.direction == 'short' and self.stop_loss <= self.entry_price:
                    logger.warning(
                        f"حد ضرر نامعتبر {self.stop_loss} <= قیمت ورود {self.entry_price} برای معامله فروش {self.trade_id}. تنظیم به 101% قیمت ورود.")
                    self.stop_loss = self.entry_price * 1.01

            if self.take_profit is not None and self.entry_price is not None:
                if self.direction == 'long' and self.take_profit <= self.entry_price:
                    logger.warning(
                        f"حد سود نامعتبر {self.take_profit} <= قیمت ورود {self.entry_price} برای معامله خرید {self.trade_id}. تنظیم بر اساس حد ضرر.")
                    if self.stop_loss: self.take_profit = self.entry_price + abs(
                        self.entry_price - self.stop_loss) * 1.5  # RR پیش‌فرض 1.5
                elif self.direction == 'short' and self.take_profit >= self.entry_price:
                    logger.warning(
                        f"حد سود نامعتبر {self.take_profit} >= قیمت ورود {self.entry_price} برای معامله فروش {self.trade_id}. تنظیم بر اساس حد ضرر.")
                    if self.stop_loss: self.take_profit = self.entry_price - abs(
                        self.stop_loss - self.entry_price) * 1.5  # RR پیش‌فرض 1.5

            if self.status == 'open' and self.remaining_quantity is not None and self.remaining_quantity <= 1e-9:
                logger.warning(f"معامله باز {self.trade_id} با مقدار صفر. تصحیح وضعیت.")
                self.status = 'closed'
                if not self.exit_time: self.exit_time = datetime.now().astimezone()
                if not self.exit_reason: self.exit_reason = 'quantity_zeroed_validation'
                if self.profit_loss is None: self._calculate_final_pnl()

            # بررسی مقادیر حد ضرر متحرک
            if self.trailing_stop_params:
                if not isinstance(self.trailing_stop_params, dict):
                    logger.warning(f"پارامترهای حد ضرر متحرک نامعتبر برای معامله {self.trade_id}. بازنشانی به مقادیر پیش‌فرض.")
                    self.trailing_stop_params = TrailingStopParams(
                        enabled=False,
                        activation_percent=3.0,
                        distance_percent=2.25,
                        use_atr=False,
                        atr_multiplier=2.0,
                        atr_period=14,
                        current_stop_price=self.stop_loss,
                        is_active=False
                    )

        except Exception as e:
            logger.error(f"خطا در اعتبارسنجی معامله {self.trade_id}: {str(e)}")

    @staticmethod
    def _sanitize_float(value: Optional[Union[float, int, Decimal, str]]) -> Optional[float]:
        """تبدیل مقدار عددی به float معتبر یا None."""
        if value is None: return None
        try:
            float_val = float(value)
            if math.isnan(float_val) or math.isinf(float_val): return None
            return float_val
        except (ValueError, TypeError):
            return None

    def _dt_to_iso(self, dt_obj):
        """
        تبدیل ایمن datetime به رشته ISO یا بازگرداندن مقدار اصلی.

        Args:
            dt_obj: شیء datetime یا هر مقدار دیگر

        Returns:
            رشته ISO یا مقدار اصلی در صورت نامعتبر بودن
        """
        if isinstance(dt_obj, datetime):
            try:
                # اطمینان از timezone-aware بودن قبل از isoformat
                if dt_obj.tzinfo is None:
                    # اضافه کردن timezone برای اطمینان از سازگاری
                    try:
                        import pytz
                        dt_obj = pytz.utc.localize(dt_obj)
                    except ImportError:
                        # اگر pytz نصب نیست، از timezone محلی استفاده کنیم
                        dt_obj = dt_obj.astimezone()
                return dt_obj.isoformat()
            except Exception as e:
                logger.warning(f"خطا در تبدیل datetime {dt_obj} به ISO: {e}")
                return str(dt_obj)  # بازگرداندن رشته به عنوان fallback
        return dt_obj  # بازگرداندن None یا مقادیر دیگر

    def _serialize_closed_portions(self) -> List[Dict[str, Any]]:
        """سریال‌سازی لیست closed_portions برای ذخیره‌سازی."""
        serialized = []
        for p_dict in self.closed_portions:
            item = {}
            for k, v in p_dict.items():
                if isinstance(v, datetime):
                    item[k] = self._dt_to_iso(v)
                elif isinstance(v, (float, int, Decimal)):
                    item[k] = self._sanitize_float(v)
                else:
                    item[k] = v
            serialized.append(item)
        return serialized

    def to_dict(self) -> Dict[str, Any]:
        """تبدیل کامل به دیکشنری برای ذخیره‌سازی."""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'quantity': self.quantity,
            'risk_amount': self.risk_amount,
            'timestamp': self._dt_to_iso(self.timestamp),
            'status': self.status,
            'exit_price': self.exit_price,
            'exit_time': self._dt_to_iso(self.exit_time),
            'exit_reason': self.exit_reason,
            'profit_loss': self.profit_loss,
            'profit_loss_percent': self.profit_loss_percent,
            'commission_paid': self.commission_paid,
            'is_multitp_enabled': self.is_multitp_enabled,
            'take_profit_levels': self.take_profit_levels,
            'current_tp_level_index': self.current_tp_level_index,
            'closed_portions': self._serialize_closed_portions(),
            'remaining_quantity': self.remaining_quantity,
            'current_price': self.current_price,
            'last_update_time': self._dt_to_iso(self.last_update_time),
            'initial_stop_loss': self.initial_stop_loss,
            'risk_reward_ratio': self.risk_reward_ratio,
            'max_favorable_excursion': self.max_favorable_excursion,
            'max_adverse_excursion': self.max_adverse_excursion,
            # --- New Fields ---
            'entry_reasons_json': self.entry_reasons_json,
            'tags': self.tags,
            'strategy_name': self.strategy_name,
            'timeframe': self.timeframe,
            'signal_quality': self.signal_quality,
            'stop_moved_count': self.stop_moved_count,
            'market_state': self.market_state,
            'notes': self.notes,
            'trade_stats': self.trade_stats,
            'max_duration_days': self.max_duration_days,
            'partial_tp_percent': self.partial_tp_percent,
            'partial_tp_size': self.partial_tp_size,
            'trailing_stop_params': self.trailing_stop_params,
            'signal_id': self.signal_id,
            # 🆕 v3.1.0: Pattern tracking fields
            'signal_patterns_details': self.signal_patterns_details,
            'signal_pattern_contributions': self.signal_pattern_contributions,
            'signal_score_breakdown': self.signal_score_breakdown
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """ایجاد معامله از دیکشنری."""
        # تبدیل رشته‌های ISO به datetime
        timestamp = datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None
        exit_time = datetime.fromisoformat(data['exit_time']) if data.get('exit_time') else None
        last_update_time = datetime.fromisoformat(data['last_update_time']) if data.get('last_update_time') else None

        # دیسریالایز بخش‌های بسته شده
        closed_portions_raw = data.get('closed_portions', [])
        closed_portions_deserialized = []
        if isinstance(closed_portions_raw, list):
            for portion_dict in closed_portions_raw:
                # ایجاد PortionDict با ایمنی
                portion = PortionDict()
                for key, value in portion_dict.items():
                    if key == 'exit_time' and isinstance(value, str):
                        try:
                            portion[key] = datetime.fromisoformat(value)
                        except (ValueError, TypeError):
                            portion[key] = None
                    elif isinstance(value, (float, int, Decimal, str)):  # بررسی رشته هم
                        sanitized_val = cls._sanitize_float(value)  # فراخوانی استاتیک
                        if sanitized_val is not None:
                            portion[key] = sanitized_val  # type: ignore
                    elif value is not None:
                        portion[key] = value  # type: ignore

                if portion:  # اضافه کردن فقط در صورت خالی نبودن
                    closed_portions_deserialized.append(portion)

        # ایجاد نمونه معامله
        trade = cls(
            trade_id=data.get('trade_id', ''),
            symbol=data.get('symbol', ''),
            direction=data.get('direction', ''),
            entry_price=data.get('entry_price', 0.0),
            stop_loss=data.get('stop_loss', 0.0),
            take_profit=data.get('take_profit', 0.0),
            quantity=data.get('quantity', 0.0),
            risk_amount=data.get('risk_amount', 0.0),
            timestamp=timestamp or datetime.now().astimezone(),
            status=data.get('status', 'pending'),
            exit_price=data.get('exit_price'),
            exit_time=exit_time,
            exit_reason=data.get('exit_reason'),
            profit_loss=data.get('profit_loss'),
            profit_loss_percent=data.get('profit_loss_percent'),
            commission_paid=data.get('commission_paid', 0.0),
            initial_stop_loss=data.get('initial_stop_loss'),
            risk_reward_ratio=data.get('risk_reward_ratio'),
            max_favorable_excursion=data.get('max_favorable_excursion', 0.0),
            max_adverse_excursion=data.get('max_adverse_excursion', 0.0),
            is_multitp_enabled=data.get('is_multitp_enabled', False),
            take_profit_levels=data.get('take_profit_levels', []),
            current_tp_level_index=data.get('current_tp_level_index', 0),
            closed_portions=closed_portions_deserialized,
            remaining_quantity=data.get('remaining_quantity'),  # تخصیص اولیه
            current_price=data.get('current_price'),
            last_update_time=last_update_time,
            entry_reasons_json=data.get('entry_reasons_json'),
            tags=data.get('tags', []),
            strategy_name=data.get('strategy_name'),
            timeframe=data.get('timeframe'),
            signal_quality=data.get('signal_quality'),
            stop_moved_count=data.get('stop_moved_count', 0),
            market_state=data.get('market_state'),
            notes=data.get('notes'),
            trade_stats=data.get('trade_stats'),
            max_duration_days=data.get('max_duration_days'),
            partial_tp_percent=data.get('partial_tp_percent'),
            partial_tp_size=data.get('partial_tp_size'),
            trailing_stop_params=data.get('trailing_stop_params'),
            signal_id=data.get('signal_id'),
            # 🆕 v3.1.0: Pattern tracking fields
            signal_patterns_details=data.get('signal_patterns_details', []),
            signal_pattern_contributions=data.get('signal_pattern_contributions', {}),
            signal_score_breakdown=data.get('signal_score_breakdown', {})
        )

        # تنظیم remaining_quantity بعد از مقداردهی اولیه اگر None باشد
        if trade.remaining_quantity is None:
            trade.remaining_quantity = trade.quantity if trade.status != 'closed' else 0.0

        # اطمینان از تنظیم current_price اگر None باشد
        if trade.current_price is None:
            trade.current_price = trade.entry_price

        return trade

    def update_current_price(self, price: float, validate_change: bool = True):
        """به‌روزرسانی قیمت فعلی و محاسبه سود/ضرر شناور و MFE/MAE."""
        price = self._sanitize_float(price)
        if price is None or price <= 0:
            logger.warning(f"قیمت نامعتبر {price} برای به‌روزرسانی معامله {self.trade_id}")
            return

        previous_price = self.current_price
        self.current_price = price
        self.last_update_time = datetime.now().astimezone()

        if self.status != 'closed':
            self._update_excursion_metrics()  # به‌روزرسانی MFE/MAE
            self._update_trailing_stop()  # به‌روزرسانی حد ضرر متحرک

        return previous_price

    def _update_excursion_metrics(self) -> None:
        """به‌روزرسانی متریک‌های حداکثر جابجایی مطلوب/نامطلوب"""
        if self.current_price is None or self.entry_price is None:
            return

        if self.direction == 'long':
            price_diff = self.current_price - self.entry_price
        else:  # short
            price_diff = self.entry_price - self.current_price

        # بررسی حداکثر جابجایی مطلوب (MFE)
        if price_diff > 0:
            if self.max_favorable_excursion is None or price_diff > self.max_favorable_excursion:
                self.max_favorable_excursion = price_diff
        # بررسی حداکثر جابجایی نامطلوب (MAE)
        elif price_diff < 0:
            abs_diff = abs(price_diff)
            if self.max_adverse_excursion is None or abs_diff > self.max_adverse_excursion:
                self.max_adverse_excursion = abs_diff

    def _update_trailing_stop(self) -> None:
        """به‌روزرسانی حد ضرر متحرک بر اساس قیمت فعلی"""
        if not self.trailing_stop_params or not self.trailing_stop_params.get('enabled', False):
            return

        if self.current_price is None or self.entry_price is None or self.stop_loss is None:
            return

        # محاسبه تغییر قیمت به صورت درصد
        price_change_percent = 0
        if self.entry_price > 0:
            if self.direction == 'long':
                price_change_percent = (self.current_price - self.entry_price) / self.entry_price * 100
            else:  # short
                price_change_percent = (self.entry_price - self.current_price) / self.entry_price * 100

        activation_percent = self.trailing_stop_params.get('activation_percent', 3.0)
        distance_percent = self.trailing_stop_params.get('distance_percent', 2.25)
        is_active = self.trailing_stop_params.get('is_active', False)
        current_stop_price = self.trailing_stop_params.get('current_stop_price', self.stop_loss)

        # بررسی فعال‌سازی trailing stop
        if not is_active and price_change_percent >= activation_percent:
            self.trailing_stop_params['is_active'] = True
            is_active = True
            logger.info(f"حد ضرر متحرک برای معامله {self.trade_id} فعال شد. تغییر قیمت: {price_change_percent:.2f}%")

        # اگر trailing stop فعال است، آن را به‌روزرسانی کنیم
        if is_active:
            new_stop_price = None

            if self.direction == 'long':
                # محاسبه حد ضرر جدید: قیمت فعلی - (فاصله درصدی * قیمت فعلی / 100)
                calculated_stop = self.current_price * (1 - distance_percent / 100)
                # حد ضرر متحرک فقط در صورتی جابجا می‌شود که بالاتر از حد ضرر فعلی باشد
                if calculated_stop > current_stop_price:
                    new_stop_price = calculated_stop
            else:  # short
                # محاسبه حد ضرر جدید: قیمت فعلی + (فاصله درصدی * قیمت فعلی / 100)
                calculated_stop = self.current_price * (1 + distance_percent / 100)
                # حد ضرر متحرک فقط در صورتی جابجا می‌شود که پایین‌تر از حد ضرر فعلی باشد
                if calculated_stop < current_stop_price:
                    new_stop_price = calculated_stop

            # اگر نیاز به به‌روزرسانی حد ضرر باشد
            if new_stop_price is not None:
                old_stop = self.stop_loss
                self.stop_loss = new_stop_price
                self.trailing_stop_params['current_stop_price'] = new_stop_price
                self.stop_moved_count += 1
                logger.info(f"حد ضرر متحرک معامله {self.trade_id} به‌روزرسانی شد: {old_stop:.6f} -> {new_stop_price:.6f}")

    def get_realized_pnl(self) -> float:
        """محاسبه مجموع سود/ضرر خالص تحقق یافته از بخش‌های بسته شده."""
        if not self.closed_portions:
            return 0.0
        return sum(self._sanitize_float(p.get('net_pnl', 0.0)) or 0.0 for p in self.closed_portions)

    def get_floating_pnl(self) -> float:
        """محاسبه سود/ضرر شناور بخش باقی‌مانده."""
        if self.status == 'closed' or self.current_price is None or self.entry_price is None or self.remaining_quantity is None or self.remaining_quantity <= 1e-9:
            return 0.0
        try:
            pnl_per_unit = (self.current_price - self.entry_price) if self.direction == 'long' else (
                        self.entry_price - self.current_price)
            return pnl_per_unit * self.remaining_quantity
        except TypeError:
            return 0.0  # اگر قیمت‌ها None باشند

    def get_net_pnl(self) -> float:
        """محاسبه کل سود/زیان شامل بخش‌های تحقق یافته و شناور."""
        return self.get_realized_pnl() + self.get_floating_pnl()

    def get_net_pnl_percent(self) -> float:
        """محاسبه درصد کل سود/زیان شامل بخش‌های تحقق یافته و شناور."""
        net_pnl = self.get_net_pnl()
        if self.entry_price and self.quantity and self.quantity > 0:
            initial_cost = self.entry_price * self.quantity
            return (net_pnl / initial_cost) * 100 if initial_cost > 0 else 0.0
        return 0.0

    def partial_close(self, exit_price: float, exit_quantity: float, exit_reason: str, commission_rate: float = 0.0) -> \
    Optional[PortionDict]:
        """بستن بخشی از معامله با بررسی‌های بیشتر."""
        exit_price = self._sanitize_float(exit_price)
        exit_quantity = self._sanitize_float(exit_quantity)
        remaining_qty = self._sanitize_float(self.remaining_quantity)

        if exit_price is None or exit_price <= 0:
            logger.error(f"قیمت خروج نامعتبر ({exit_price}) برای بستن بخشی از معامله {self.trade_id}.")
            return None
        if exit_quantity is None or exit_quantity <= 1e-9:
            logger.error(f"مقدار خروج نامعتبر ({exit_quantity}) برای بستن بخشی از معامله {self.trade_id}.")
            return None
        if remaining_qty is None or exit_quantity > remaining_qty + 1e-9:
            logger.error(f"مقدار خروج {exit_quantity:.8f} > مقدار باقی‌مانده {remaining_qty:.8f} برای معامله {self.trade_id}.")
            return None

        actual_exit_quantity = min(exit_quantity, remaining_qty)
        if actual_exit_quantity <= 1e-9: return None

        entry_price = self.entry_price
        if entry_price is None:
            logger.error(f"عدم امکان محاسبه سود/زیان برای بستن بخشی: قیمت ورود None است برای معامله {self.trade_id}")
            return None

        # محاسبه سود/زیان این بخش
        pnl_per_unit = (exit_price - entry_price) if self.direction == 'long' else (entry_price - exit_price)
        portion_pnl = pnl_per_unit * actual_exit_quantity

        # محاسبه کارمزد برای هر دو سمت (ورود و خروج این بخش)
        entry_commission = (entry_price * actual_exit_quantity * commission_rate)
        exit_commission = (exit_price * actual_exit_quantity * commission_rate)
        portion_commission = entry_commission + exit_commission
        portion_net_pnl = portion_pnl - portion_commission

        # ثبت بخش بسته شده
        now_time = datetime.now().astimezone()
        new_closed_portion: PortionDict = {
            'exit_price': exit_price,
            'exit_quantity': actual_exit_quantity,
            'exit_time': now_time,
            'exit_reason': exit_reason,
            'profit_loss': portion_pnl,
            'commission': portion_commission,
            'net_pnl': portion_net_pnl,  # سود/زیان خالص برای این بخش
            'profit_loss_percent': ((exit_price - entry_price) / entry_price * 100) if self.direction == 'long' else (
                        (entry_price - exit_price) / entry_price * 100)
        }
        self.closed_portions.append(new_closed_portion)

        # به‌روزرسانی مقدار باقی‌مانده و کارمزد کل
        self.remaining_quantity -= actual_exit_quantity
        self.commission_paid += portion_commission

        # به‌روزرسانی وضعیت و سطح TP
        if self.remaining_quantity <= 1e-9:
            self.status = 'closed'
            self.exit_price = exit_price  # قیمت آخرین خروج
            self.exit_time = now_time
            self.exit_reason = exit_reason
            self._calculate_final_pnl()  # محاسبه سود/زیان نهایی فقط در صورت بسته شدن کامل
        else:
            self.status = 'partially_closed'

        logger.info(
            f"بخش {actual_exit_quantity:.8f} از معامله {self.trade_id} در قیمت {exit_price:.8f} بسته شد. "
            f"دلیل: {exit_reason}. باقی‌مانده: {self.remaining_quantity:.8f}. وضعیت جدید: {self.status}")

        # حرکت SL پس از دستیابی به اولین TP
        if self.is_multitp_enabled and 'take_profit_level' in exit_reason:
            self.current_tp_level_index += 1
            # در اینجا می‌توان منطق حرکت SL پس از TP را پیاده‌سازی کرد

        return new_closed_portion

    def _calculate_final_pnl(self):
        """محاسبه سود/ضرر و درصد نهایی فقط پس از بسته شدن کامل."""
        if self.status != 'closed':
            logger.debug(f"محاسبه سود/زیان میانی برای معامله {self.trade_id}، نه نهایی.")
            self.profit_loss = self.get_net_pnl()
            self.profit_loss_percent = self.get_net_pnl_percent()
            return

        # محاسبه مجموع سود خالص از تمام بخش‌های بسته شده
        total_net_pnl = sum(self._sanitize_float(p.get('net_pnl', 0.0)) or 0.0 for p in self.closed_portions)
        self.profit_loss = total_net_pnl

        # محاسبه درصد سود/ضرر بر اساس هزینه اولیه کل پوزیشن
        if self.entry_price and self.quantity and self.quantity > 0:
            initial_cost = self.entry_price * self.quantity
            self.profit_loss_percent = (total_net_pnl / initial_cost) * 100 if initial_cost > 0 else 0.0
        else:
            self.profit_loss_percent = 0.0

        logger.info(
            f"سود/زیان نهایی برای معامله بسته شده {self.trade_id} محاسبه شد: {self.profit_loss:.5f} ({self.profit_loss_percent:.2f}%)")

        # محاسبه آمار معامله (مدت زمان، ضریب R و...)
        total_duration_hours = 0
        if self.timestamp and self.exit_time:
            total_duration_hours = (self.exit_time - self.timestamp).total_seconds() / 3600

        avg_exit_price = 0
        if self.quantity and self.quantity > 0:
            total_exit_value = sum(
                (p.get('exit_price', 0) or 0) * (p.get('exit_quantity', 0) or 0) for p in self.closed_portions)
            total_exit_qty = sum(p.get('exit_quantity', 0) or 0 for p in self.closed_portions)
            if total_exit_qty > 0: avg_exit_price = total_exit_value / total_exit_qty

        self.trade_stats = {
            'total_duration_hours': total_duration_hours,
            'avg_exit_price': avg_exit_price,
            'r_multiple': (self.profit_loss / self.risk_amount) if self.risk_amount and self.risk_amount > 0 else 0,
            'max_favorable_excursion_percent': (
                        self.max_favorable_excursion / self.entry_price * 100) if self.entry_price and self.entry_price > 0 else 0,
            'max_adverse_excursion_percent': (
                        self.max_adverse_excursion / self.entry_price * 100) if self.entry_price and self.entry_price > 0 else 0,
            'stop_loss_hit': self.exit_reason == 'stop_loss',
            'take_profit_hit': 'take_profit' in (self.exit_reason or ''),
            'stop_moved_count': self.stop_moved_count
        }

    def set_multi_take_profit(self, levels: List[Tuple[float, float]]) -> bool:
        """
        تنظیم استراتژی حد سود چند مرحله‌ای با بررسی‌های بیشتر.

        Args:
            levels: لیست [(price, percentage)] برای مراحل TP

        Returns:
            bool: آیا تنظیم موفقیت‌آمیز بود
        """
        if not levels:
            logger.warning(f"سطوح TP خالی برای معامله {self.trade_id}")
            return False

        # مرتب‌سازی بر اساس قیمت (long: صعودی, short: نزولی)
        is_long = self.direction == 'long'
        sorted_levels = sorted(levels, key=lambda x: x[0], reverse=not is_long)

        # بررسی معتبر بودن قیمت‌ها (صفر نبودن)
        EPSILON = 1e-6  # حداقل مقدار معتبر برای قیمت
        has_zero_price = any(abs(price) < EPSILON for price, _ in sorted_levels)
        if has_zero_price:
            logger.error(f"قیمت صفر یا نزدیک به صفر در سطوح TP برای معامله {self.trade_id}. غیرفعال‌سازی Multi-TP.")
            self._disable_multitp()
            return False

        # بررسی اعتبار سطوح - مجموع درصدها باید 100 باشد
        total_percentage = sum(level[1] for level in sorted_levels)
        if not math.isclose(total_percentage, 100.0, abs_tol=0.5):  # با 0.5 تلرانس
            logger.warning(
                f"درصدهای Multi-TP برای معامله {self.trade_id} جمعشان 100% نیست (مجموع={total_percentage}). تنظیم خودکار.")
            # تنظیم خودکار درصدها
            factor = 100.0 / total_percentage
            sorted_levels = [(price, pct * factor) for price, pct in sorted_levels]

        # بررسی سطوح قیمت (باید در جهت درست باشند)
        entry_price = self.entry_price

        if is_long:
            for i, (price, _) in enumerate(sorted_levels):
                if price <= entry_price:
                    logger.error(
                        f"سطح TP نامعتبر برای معامله خرید {self.trade_id}: {price} <= قیمت ورود {entry_price}. غیرفعال‌سازی Multi-TP.")
                    self._disable_multitp()
                    return False

                # اطمینان از فاصله معنادار بین سطوح
                if i > 0 and price < sorted_levels[i - 1][0] * 1.001:
                    logger.error(f"سطوح TP خیلی نزدیک برای معامله {self.trade_id}. غیرفعال‌سازی Multi-TP.")
                    self._disable_multitp()
                    return False
        else:  # short
            for i, (price, _) in enumerate(sorted_levels):
                if price >= entry_price:
                    logger.error(
                        f"سطح TP نامعتبر برای معامله فروش {self.trade_id}: {price} >= قیمت ورود {entry_price}. غیرفعال‌سازی Multi-TP.")
                    self._disable_multitp()
                    return False

                # اطمینان از فاصله معنادار بین سطوح
                if i > 0 and price > sorted_levels[i - 1][0] * 0.999:
                    logger.error(f"سطوح TP خیلی نزدیک برای معامله {self.trade_id}. غیرفعال‌سازی Multi-TP.")
                    self._disable_multitp()
                    return False

        # تنظیم سطوح TP
        self.take_profit_levels = sorted_levels
        self.is_multitp_enabled = True
        # حد سود نهایی معامله برابر با آخرین سطح TP است
        self.take_profit = sorted_levels[-1][0] if sorted_levels else self.take_profit
        logger.info(f"Multi-TP برای معامله {self.trade_id} تنظیم شد: {self.take_profit_levels}")
        return True

    def _disable_multitp(self) -> None:
        """غیرفعال کردن حالت چند مرحله‌ای"""
        self.is_multitp_enabled = False
        self.take_profit_levels = []
        self.current_tp_level_index = 0

    def check_exit_conditions(self, current_price: float) -> Tuple[bool, Optional[str], float]:
        """
        بررسی شرایط خروج معامله با منطق دقیق و سازگار با تنظیمات.

        Args:
            current_price: قیمت فعلی

        Returns:
            tuple (آیا باید خارج شود، دلیل خروج، مقدار خروج)
        """
        # به‌روزرسانی قیمت فعلی و MFE/MAE
        self.update_current_price(current_price)

        # بررسی اینکه آیا معامله قبلاً بسته شده یا مقداری برای خروج ندارد
        EPSILON = 1e-9  # مقدار بسیار کوچک برای مقایسه اعداد اعشاری
        if self.status == 'closed' or self.remaining_quantity <= EPSILON:
            return False, "Already closed", 0.0

        # اطمینان از معتبر بودن قیمت‌ها
        invalid_prices = []
        # بررسی None بودن یا نزدیک به صفر بودن
        if self.stop_loss is None or abs(self.stop_loss) < EPSILON:
            invalid_prices.append("stop_loss")

        if self.take_profit is None or abs(self.take_profit) < EPSILON:
            # فقط اگر Multi-TP فعال نیست یا تمام شده، TP نهایی را چک کن
            if not self.is_multitp_enabled or self.current_tp_level_index >= len(self.take_profit_levels):
                invalid_prices.append("final_take_profit")

        if invalid_prices:
            logger.error(f"مقادیر قیمت نامعتبر برای معامله {self.trade_id}: {', '.join(invalid_prices)}")
            return False, "Invalid price values", 0.0

        # 1. بررسی حد ضرر (روی تمام مقدار باقی‌مانده اعمال می‌شود)
        if (self.direction == 'long' and current_price <= self.stop_loss) or \
                (self.direction == 'short' and current_price >= self.stop_loss):
            logger.info(f"حد ضرر برای معامله {self.trade_id} در قیمت {current_price} فعال شد (SL: {self.stop_loss})")
            return True, "stop_loss", self.remaining_quantity

        # 2. بررسی حد سود (چند مرحله‌ای یا نهایی)
        if self.is_multitp_enabled and self.take_profit_levels and self.current_tp_level_index < len(self.take_profit_levels):
            # بررسی Multi-TP
            tp_price, tp_percentage = self.take_profit_levels[self.current_tp_level_index]

            # اطمینان از معتبر بودن قیمت TP
            if abs(tp_price) < EPSILON:
                logger.error(
                    f"قیمت TP نامعتبر (نزدیک صفر) برای سطح {self.current_tp_level_index} در معامله {self.trade_id}")
                return False, "Invalid TP price", 0.0

            should_hit_tp = (self.direction == 'long' and current_price >= tp_price) or \
                            (self.direction == 'short' and current_price <= tp_price)

            if should_hit_tp:
                exit_reason = f"take_profit_level_{self.current_tp_level_index + 1}"
                # محاسبه مقدار دقیق برای این سطح (بر اساس درصد * مقدار اولیه)
                exit_quantity_target = (tp_percentage / 100.0) * self.quantity
                # مقدار واقعی برای خروج، حداکثر برابر با مقدار باقی‌مانده است
                actual_exit_quantity = min(exit_quantity_target, self.remaining_quantity)

                # اگر این آخرین سطح TP است، تمام مقدار باقی‌مانده را ببند
                if self.current_tp_level_index == len(self.take_profit_levels) - 1:
                    actual_exit_quantity = self.remaining_quantity

                # اطمینان از اینکه مقدار خروج مثبت است
                if actual_exit_quantity <= EPSILON:
                    logger.warning(
                        f"مقدار خروج محاسبه شده صفر یا منفی است برای {exit_reason} در معامله {self.trade_id}. رد کردن خروج.")
                    return False, None, 0.0

                logger.info(
                    f"{exit_reason} برای معامله {self.trade_id} در قیمت {current_price} فعال شد (TP: {tp_price}). مقدار خروج: {actual_exit_quantity}")
                return True, exit_reason, actual_exit_quantity
        else:
            # بررسی TP نهایی (اگر Multi-TP فعال نیست یا تمام شده)
            should_hit_final_tp = (self.direction == 'long' and current_price >= self.take_profit) or \
                                  (self.direction == 'short' and current_price <= self.take_profit)
            if should_hit_final_tp:
                # فقط اگر مقداری باقی مانده است
                if self.remaining_quantity > EPSILON:
                    logger.info(
                        f"حد سود نهایی برای معامله {self.trade_id} در قیمت {current_price} فعال شد (TP: {self.take_profit})")
                    return True, "take_profit", self.remaining_quantity

        # 3. افزودن شرط خروج زمانی - اگر معامله بیش از X روز باز بوده‌است
        if hasattr(self, 'max_duration_days') and self.max_duration_days and self.max_duration_days > 0:
            current_time = datetime.now().astimezone()
            trade_duration = (current_time - self.timestamp).total_seconds() / (24 * 3600)  # تبدیل به روز

            if trade_duration > self.max_duration_days:
                logger.info(f"خروج زمان‌محور برای معامله {self.trade_id} پس از {trade_duration:.1f} روز")
                return True, "time_exit", self.remaining_quantity

        # 4. افزودن شرط خروج پس از رسیدن به درصد مشخصی از TP نهایی
        if hasattr(self, 'partial_tp_percent') and self.partial_tp_percent and self.partial_tp_percent > 0:
            if self.take_profit is not None and self.entry_price is not None:
                total_distance = abs(self.take_profit - self.entry_price)
                current_distance = abs(current_price - self.entry_price)
                reached_percent = (current_distance / total_distance) * 100 if total_distance > 0 else 0

                if reached_percent >= self.partial_tp_percent:
                    exit_portion = self.partial_tp_size if hasattr(self, 'partial_tp_size') and self.partial_tp_size else 0.5
                    exit_quantity = self.remaining_quantity * exit_portion
                    logger.info(f"خروج TP بخشی برای معامله {self.trade_id} در {reached_percent:.1f}% هدف")
                    return True, f"partial_tp_{reached_percent:.0f}_percent", exit_quantity

        # هیچ شرط خروجی فعال نشد
        return False, None, 0.0

    def close_trade(self, exit_price: float, exit_reason: str, commission_rate: float = 0.0) -> Optional[PortionDict]:
        """
        بستن کامل مقدار باقی‌مانده معامله.

        Args:
            exit_price: قیمت خروج
            exit_reason: دلیل خروج
            commission_rate: نرخ کارمزد (اختیاری)

        Returns:
            بخش بسته شده یا None در صورت خطا
        """
        if self.status == 'closed' or self.remaining_quantity <= 1e-9:
            logger.warning(f"عدم امکان بستن معامله {self.trade_id}: قبلاً بسته شده یا مقدار باقی‌مانده ندارد.")
            return None

        # استفاده از partial_close برای بستن کل مقدار باقی‌مانده
        closed_portion = self.partial_close(exit_price, self.remaining_quantity, exit_reason, commission_rate)

        # اطمینان از اینکه وضعیت معامله به درستی به 'closed' تغییر کرده است
        if self.remaining_quantity <= 1e-9 and self.status != 'closed':
            self.status = 'closed'
            self.exit_time = datetime.now().astimezone()
            self.exit_reason = exit_reason
            self._calculate_final_pnl()

        logger.info(f"معامله {self.trade_id} کاملاً در قیمت {exit_price:.8f} بسته شد. دلیل: {exit_reason}")
        return closed_portion

    def get_age(self) -> float:
        """
        محاسبه مدت زمان باز بودن معامله بر حسب ساعت.
        """
        if self.status == 'closed' and self.exit_time:
            end_time = self.exit_time
        elif self.last_update_time:
            end_time = self.last_update_time
        else:
            end_time = datetime.now().astimezone()  # Fallback به زمان فعلی

        if self.timestamp:
            duration = end_time - self.timestamp
            return duration.total_seconds() / 3600  # تبدیل به ساعت
        else:
            return 0.0  # اگر زمان شروع مشخص نباشد

    # --- متد جدید برای به‌روزرسانی پارامترهای معامله در حین اجرا ---
    def update_parameters(self, config: Dict[str, Any]) -> bool:
        """
        به‌روزرسانی پارامترهای معامله بر اساس تنظیمات جدید.

        Args:
            config: پیکربندی جدید (بخش مربوطه)

        Returns:
            bool: آیا به‌روزرسانی موفقیت‌آمیز بود
        """
        try:
            changes_made = []  # لیست تغییرات انجام شده

            # به‌روزرسانی پارامترهای مدیریت ریسک
            risk_config = config.get('risk_management', {})
            if risk_config:
                # به‌روزرسانی پارامترهای حد ضرر متحرک
                trailing_config = {
                    'enabled': risk_config.get('use_trailing_stop', self.trailing_stop_params.get('enabled', True)),
                    'activation_percent': risk_config.get('trailing_stop_activation_percent',
                                                       self.trailing_stop_params.get('activation_percent', 3.0)),
                    'distance_percent': risk_config.get('trailing_stop_distance_percent',
                                                      self.trailing_stop_params.get('distance_percent', 2.25)),
                    'use_atr': risk_config.get('use_atr_based_trailing',
                                              self.trailing_stop_params.get('use_atr', False)),
                    'atr_multiplier': risk_config.get('atr_trailing_multiplier',
                                                     self.trailing_stop_params.get('atr_multiplier', 2.0)),
                    'atr_period': risk_config.get('atr_trailing_period',
                                                 self.trailing_stop_params.get('atr_period', 14)),
                }

                # اعمال تغییرات به پارامترهای trailing stop
                old_enabled = self.trailing_stop_params.get('enabled', False)
                old_distance = self.trailing_stop_params.get('distance_percent', 2.25)

                # ادغام تنظیمات جدید با تنظیمات فعلی (با حفظ مقادیر فعلی)
                for key, value in trailing_config.items():
                    if key in self.trailing_stop_params and self.trailing_stop_params[key] != value:
                        self.trailing_stop_params[key] = value
                        changes_made.append(f"trailing_stop.{key}")

                # اگر وضعیت فعال بودن تغییر کرده، گزارش دهیم
                if old_enabled != self.trailing_stop_params.get('enabled'):
                    new_status = "فعال" if self.trailing_stop_params.get('enabled') else "غیرفعال"
                    logger.info(f"وضعیت حد ضرر متحرک برای معامله {self.trade_id} به {new_status} تغییر کرد")

                # به‌روزرسانی پارامترهای زمان‌محور
                if 'max_trade_duration_hours' in risk_config:
                    new_max_days = risk_config.get('max_trade_duration_hours') / 24.0
                    if self.max_duration_days != new_max_days:
                        self.max_duration_days = new_max_days
                        changes_made.append("max_duration_days")

                # به‌روزرسانی سایر پارامترهای مدیریت ریسک
                if 'preferred_risk_reward_ratio' in risk_config:
                    new_rr = self._sanitize_float(risk_config.get('preferred_risk_reward_ratio'))
                    if new_rr and new_rr != self.risk_reward_ratio:
                        self.risk_reward_ratio = new_rr
                        changes_made.append("risk_reward_ratio")

            # به‌روزرسانی تنظیمات حد سود چندمرحله‌ای
            trading_config = config.get('trading', {})
            if trading_config:
                multi_tp_config = trading_config.get('multi_tp', {})
                if multi_tp_config:
                    new_multi_tp_enabled = multi_tp_config.get('enabled', False)
                    if self.is_multitp_enabled != new_multi_tp_enabled:
                        self.is_multitp_enabled = new_multi_tp_enabled
                        changes_made.append("multi_tp_enabled")
                        logger.info(f"وضعیت حد سود چندمرحله‌ای برای معامله {self.trade_id} به {'فعال' if new_multi_tp_enabled else 'غیرفعال'} تغییر کرد")

            # به‌روزرسانی تنظیمات خروج بخشی
            if 'partial_tp_percent' in risk_config:
                new_partial_tp_percent = risk_config.get('partial_tp_percent')
                if new_partial_tp_percent != self.partial_tp_percent:
                    self.partial_tp_percent = new_partial_tp_percent
                    changes_made.append("partial_tp_percent")

            if 'partial_tp_size' in risk_config:
                new_partial_tp_size = risk_config.get('partial_tp_size')
                if new_partial_tp_size != self.partial_tp_size:
                    self.partial_tp_size = new_partial_tp_size
                    changes_made.append("partial_tp_size")

            # اگر تغییراتی انجام شده، گزارش کنیم
            if changes_made:
                logger.info(f"پارامترهای معامله {self.trade_id} به‌روزرسانی شد: {', '.join(changes_made)}")
                return True
            else:
                logger.debug(f"هیچ تغییری در پارامترهای معامله {self.trade_id} انجام نشد")
                return False

        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی پارامترهای معامله {self.trade_id}: {e}")
            return False

    def update_entry_reasons(self, reasons_dict: Dict[str, Any]) -> bool:
        """
        به‌روزرسانی دلایل ورود به معامله و ذخیره آنها به صورت JSON.

        Args:
            reasons_dict: دیکشنری دلایل ورود

        Returns:
            bool: آیا به‌روزرسانی موفقیت‌آمیز بود
        """
        try:
            if not reasons_dict:
                return False

            # تبدیل دیکشنری به JSON
            reasons_json = json.dumps(reasons_dict, ensure_ascii=False, default=str)
            self.entry_reasons_json = reasons_json

            # به‌روزرسانی برچسب‌ها بر اساس دلایل
            if 'tags' in reasons_dict and isinstance(reasons_dict['tags'], list):
                new_tags = reasons_dict['tags']
                # ترکیب برچسب‌های جدید با برچسب‌های موجود
                self.tags = list(set(self.tags + new_tags))

            logger.info(f"دلایل ورود به معامله {self.trade_id} به‌روزرسانی شد")
            return True

        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی دلایل ورود به معامله {self.trade_id}: {e}")
            return False

    def get_entry_reasons(self) -> Optional[Dict[str, Any]]:
        """
        بازیابی دلایل ورود از JSON ذخیره شده.

        Returns:
            Dict[str, Any] یا None: دلایل ورود به صورت دیکشنری
        """
        if not self.entry_reasons_json:
            return None

        try:
            return json.loads(self.entry_reasons_json)
        except Exception as e:
            logger.error(f"خطا در تجزیه JSON دلایل ورود برای معامله {self.trade_id}: {e}")
            return None