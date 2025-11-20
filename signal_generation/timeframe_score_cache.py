"""
TimeframeScoreCache - کش امتیازات تایم‌فریم برای جلوگیری از محاسبات تکراری

این ماژول امتیازات هر تایم‌فریم برای هر جفت ارز را کش می‌کند و فقط زمانی که
کندل جدیدی در تایم‌فریم ایجاد شده، دوباره محاسبه می‌کند.

مزایا:
- کاهش 70-90% محاسبات غیرضروری
- صرفه‌جویی در مصرف CPU و API calls
- افزایش سرعت پردازش
- حفظ دقت تحلیل

مثال:
    تایم‌فریم 4h فقط هر 4 ساعت یکبار دوباره محاسبه می‌شود، نه هر 3 دقیقه!
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import pandas as pd
from threading import Lock
import time

logger = logging.getLogger(__name__)


@dataclass
class TimeframeScore:
    """امتیاز کش شده برای یک تایم‌فریم خاص"""

    # امتیاز سیگنال
    signal_score: Optional[Any]  # SignalInfo or SignalScore

    # timestamp آخرین کندل (مهم‌ترین فیلد برای تشخیص کندل جدید)
    last_candle_timestamp: int  # Unix timestamp در ثانیه

    # زمان محاسبه امتیاز
    calculated_at: float = field(default_factory=time.time)

    # داده‌های اضافی
    direction: Optional[str] = None  # 'LONG' or 'SHORT'
    final_score: float = 0.0

    # آمار
    hit_count: int = 0  # تعداد دفعاتی که از کش استفاده شده

    def __repr__(self):
        age = time.time() - self.calculated_at
        return (
            f"TimeframeScore(score={self.final_score:.2f}, "
            f"direction={self.direction}, age={age:.0f}s, hits={self.hit_count})"
        )


@dataclass
class SymbolTimeframeCache:
    """کش امتیازات همه تایم‌فریم‌های یک جفت ارز"""

    symbol: str
    timeframes: Dict[str, TimeframeScore] = field(default_factory=dict)

    # آمار کل
    total_hits: int = 0
    total_misses: int = 0

    @property
    def hit_rate(self) -> float:
        """نرخ موفقیت کش"""
        total = self.total_hits + self.total_misses
        return (self.total_hits / total * 100) if total > 0 else 0.0

    def __repr__(self):
        return (
            f"SymbolCache({self.symbol}: {len(self.timeframes)} TFs, "
            f"hits={self.total_hits}, hit_rate={self.hit_rate:.1f}%)"
        )


class TimeframeScoreCache:
    """
    مدیریت کش امتیازات تایم‌فریم‌ها برای همه جفت ارزها

    این کلاس:
    1. امتیازات هر تایم‌فریم را ذخیره می‌کند
    2. بررسی می‌کند که آیا کندل جدیدی آمده
    3. فقط در صورت وجود کندل جدید، محاسبه مجدد را درخواست می‌کند
    4. در غیر این صورت، امتیاز کش شده را برمی‌گرداند
    """

    # فواصل زمانی تایم‌فریم‌ها به ثانیه - Aligned with OLD SYSTEM
    TIMEFRAME_INTERVALS = {
        '5m': 300,      # 5 minutes in seconds
        '15m': 900,     # 15 minutes in seconds
        '1h': 3600,     # 1 hour in seconds
        '4h': 14400     # 4 hours in seconds
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        مقداردهی اولیه کش

        Args:
            config: تنظیمات (اختیاری)
        """
        self.config = config or {}

        # کش اصلی: {symbol: SymbolTimeframeCache}
        self._cache: Dict[str, SymbolTimeframeCache] = {}

        # قفل برای thread safety
        self._lock = Lock()

        # تنظیمات
        cache_config = self.config.get('timeframe_score_cache', {})
        self.enabled = cache_config.get('enabled', True)
        self.max_cache_age = cache_config.get('max_cache_age_hours', 24) * 3600  # به ثانیه

        # آمار کلی
        self.total_cache_hits = 0
        self.total_cache_misses = 0
        self.total_recalculations = 0

        logger.info(
            f"TimeframeScoreCache initialized "
            f"(enabled={self.enabled}, max_age={self.max_cache_age/3600:.1f}h)"
        )

    def should_recalculate(
        self,
        symbol: str,
        timeframe: str,
        latest_candle_df: pd.DataFrame
    ) -> Tuple[bool, Optional[str]]:
        """
        بررسی می‌کند که آیا باید تایم‌فریم را دوباره تحلیل کرد یا نه

        Args:
            symbol: نماد (مثلاً 'BTCUSDT')
            timeframe: تایم‌فریم (مثلاً '4h')
            latest_candle_df: DataFrame حاوی داده‌های جدید

        Returns:
            (باید محاسبه شود؟, دلیل)

        مثال:
            >>> should_recalc, reason = cache.should_recalculate('BTCUSDT', '4h', df)
            >>> if should_recalc:
            >>>     # محاسبه مجدد امتیاز
            >>> else:
            >>>     # استفاده از امتیاز کش شده
        """
        if not self.enabled:
            return True, "cache_disabled"

        if latest_candle_df is None or latest_candle_df.empty:
            return True, "no_data"

        # استخراج timestamp آخرین کندل
        try:
            # فرض: DataFrame دارای ستون 'timestamp' یا index datetime است
            if 'timestamp' in latest_candle_df.columns:
                ts_value = latest_candle_df['timestamp'].iloc[-1]
                # Handle pandas Timestamp objects
                if isinstance(ts_value, pd.Timestamp):
                    latest_timestamp = int(ts_value.timestamp())
                else:
                    latest_timestamp = int(ts_value)
            elif 'time' in latest_candle_df.columns:
                ts_value = latest_candle_df['time'].iloc[-1]
                # Handle pandas Timestamp objects
                if isinstance(ts_value, pd.Timestamp):
                    latest_timestamp = int(ts_value.timestamp())
                else:
                    latest_timestamp = int(ts_value)
            elif isinstance(latest_candle_df.index, pd.DatetimeIndex):
                latest_timestamp = int(latest_candle_df.index[-1].timestamp())
            else:
                logger.warning(
                    f"Cannot extract timestamp from DataFrame for {symbol} {timeframe}"
                )
                return True, "no_timestamp"
        except Exception as e:
            logger.error(f"Error extracting timestamp: {e}")
            return True, "timestamp_error"

        with self._lock:
            # آیا این symbol در کش وجود دارد؟
            if symbol not in self._cache:
                return True, "symbol_not_in_cache"

            symbol_cache = self._cache[symbol]

            # آیا این timeframe در کش وجود دارد؟
            if timeframe not in symbol_cache.timeframes:
                return True, "timeframe_not_in_cache"

            cached_score = symbol_cache.timeframes[timeframe]

            # آیا کندل جدیدی آمده؟
            if latest_timestamp > cached_score.last_candle_timestamp:
                # کندل جدید آمده - باید دوباره محاسبه شود
                return True, "new_candle_available"

            # آیا کش خیلی قدیمی شده؟
            cache_age = time.time() - cached_score.calculated_at
            if cache_age > self.max_cache_age:
                return True, f"cache_expired({cache_age/3600:.1f}h)"

            # کش معتبر است
            return False, "cache_valid"

    def get_cached_score(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[Any]:
        """
        دریافت امتیاز کش شده (اگر معتبر باشد)

        Args:
            symbol: نماد
            timeframe: تایم‌فریم

        Returns:
            SignalInfo کش شده یا None
        """
        if not self.enabled:
            return None

        with self._lock:
            if symbol not in self._cache:
                self.total_cache_misses += 1
                return None

            symbol_cache = self._cache[symbol]

            if timeframe not in symbol_cache.timeframes:
                self.total_cache_misses += 1
                symbol_cache.total_misses += 1
                return None

            cached_score = symbol_cache.timeframes[timeframe]

            # بررسی اعتبار (عمر کش)
            cache_age = time.time() - cached_score.calculated_at
            if cache_age > self.max_cache_age:
                logger.debug(
                    f"Cache expired for {symbol} {timeframe} "
                    f"(age={cache_age/3600:.1f}h)"
                )
                self.total_cache_misses += 1
                symbol_cache.total_misses += 1
                return None

            # Cache hit!
            cached_score.hit_count += 1
            symbol_cache.total_hits += 1
            self.total_cache_hits += 1

            logger.debug(
                f"✓ Cache HIT for {symbol} {timeframe} "
                f"(score={cached_score.final_score:.2f}, age={cache_age:.0f}s, "
                f"hits={cached_score.hit_count})"
            )

            return cached_score.signal_score

    def update_cache(
        self,
        symbol: str,
        timeframe: str,
        signal_score: Any,  # SignalInfo or SignalScore
        latest_candle_df: pd.DataFrame
    ) -> None:
        """
        به‌روزرسانی کش با امتیاز جدید

        Args:
            symbol: نماد
            timeframe: تایم‌فریم
            signal_score: SignalInfo یا SignalScore محاسبه شده
            latest_candle_df: DataFrame حاوی داده‌های جدید
        """
        if not self.enabled:
            return

        if latest_candle_df is None or latest_candle_df.empty:
            logger.warning(f"Cannot cache without data for {symbol} {timeframe}")
            return

        # استخراج timestamp آخرین کندل
        try:
            if 'timestamp' in latest_candle_df.columns:
                ts_value = latest_candle_df['timestamp'].iloc[-1]
                # Handle pandas Timestamp objects
                if isinstance(ts_value, pd.Timestamp):
                    latest_timestamp = int(ts_value.timestamp())
                else:
                    latest_timestamp = int(ts_value)
            elif 'time' in latest_candle_df.columns:
                ts_value = latest_candle_df['time'].iloc[-1]
                # Handle pandas Timestamp objects
                if isinstance(ts_value, pd.Timestamp):
                    latest_timestamp = int(ts_value.timestamp())
                else:
                    latest_timestamp = int(ts_value)
            elif isinstance(latest_candle_df.index, pd.DatetimeIndex):
                latest_timestamp = int(latest_candle_df.index[-1].timestamp())
            else:
                logger.warning(f"Cannot extract timestamp for caching {symbol} {timeframe}")
                return
        except Exception as e:
            logger.error(f"Error extracting timestamp for cache: {e}")
            return

        # استخراج اطلاعات از signal
        direction = None
        final_score = 0.0

        if signal_score:
            if hasattr(signal_score, 'direction'):
                direction = signal_score.direction
            if hasattr(signal_score, 'score'):
                if hasattr(signal_score.score, 'final_score'):
                    final_score = signal_score.score.final_score
            elif hasattr(signal_score, 'final_score'):
                final_score = signal_score.final_score

        with self._lock:
            # ایجاد symbol cache در صورت نیاز
            if symbol not in self._cache:
                self._cache[symbol] = SymbolTimeframeCache(symbol=symbol)

            symbol_cache = self._cache[symbol]

            # ذخیره امتیاز
            symbol_cache.timeframes[timeframe] = TimeframeScore(
                signal_score=signal_score,
                last_candle_timestamp=latest_timestamp,
                calculated_at=time.time(),
                direction=direction,
                final_score=final_score,
                hit_count=0
            )

            self.total_recalculations += 1

            logger.debug(
                f"✓ Cached score for {symbol} {timeframe} "
                f"(score={final_score:.2f}, candle_ts={latest_timestamp})"
            )

    def invalidate_symbol(self, symbol: str) -> None:
        """حذف تمام کش‌های یک جفت ارز"""
        with self._lock:
            if symbol in self._cache:
                del self._cache[symbol]
                logger.info(f"Invalidated cache for {symbol}")

    def invalidate_timeframe(self, symbol: str, timeframe: str) -> None:
        """حذف کش یک تایم‌فریم خاص"""
        with self._lock:
            if symbol in self._cache:
                if timeframe in self._cache[symbol].timeframes:
                    del self._cache[symbol].timeframes[timeframe]
                    logger.debug(f"Invalidated cache for {symbol} {timeframe}")

    def clear_all(self) -> None:
        """پاک کردن کل کش"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared entire cache ({count} symbols)")

    def get_statistics(self) -> Dict[str, Any]:
        """
        آمار کش

        Returns:
            دیکشنری حاوی آمار کامل
        """
        with self._lock:
            total_requests = self.total_cache_hits + self.total_cache_misses
            hit_rate = (
                self.total_cache_hits / total_requests * 100
                if total_requests > 0 else 0.0
            )

            symbol_stats = {}
            for symbol, cache in self._cache.items():
                symbol_stats[symbol] = {
                    'timeframes': len(cache.timeframes),
                    'total_hits': cache.total_hits,
                    'total_misses': cache.total_misses,
                    'hit_rate': cache.hit_rate,
                }

            return {
                'enabled': self.enabled,
                'total_symbols': len(self._cache),
                'total_cache_hits': self.total_cache_hits,
                'total_cache_misses': self.total_cache_misses,
                'total_recalculations': self.total_recalculations,
                'global_hit_rate': hit_rate,
                'symbols': symbol_stats,
                'max_cache_age_hours': self.max_cache_age / 3600,
            }

    def log_statistics(self) -> None:
        """نمایش آمار در لاگ"""
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("📊 Timeframe Score Cache Statistics")
        logger.info("=" * 60)
        logger.info(f"Enabled: {stats['enabled']}")
        logger.info(f"Symbols cached: {stats['total_symbols']}")
        logger.info(f"Cache hits: {stats['total_cache_hits']}")
        logger.info(f"Cache misses: {stats['total_cache_misses']}")
        logger.info(f"Recalculations: {stats['total_recalculations']}")
        logger.info(f"Global hit rate: {stats['global_hit_rate']:.1f}%")
        logger.info(f"Max cache age: {stats['max_cache_age_hours']:.1f}h")

        if stats['symbols']:
            logger.info("\nPer-symbol statistics:")
            for symbol, sym_stats in sorted(
                stats['symbols'].items(),
                key=lambda x: x[1]['hit_rate'],
                reverse=True
            )[:10]:  # Top 10
                logger.info(
                    f"  {symbol}: {sym_stats['timeframes']} TFs, "
                    f"hits={sym_stats['total_hits']}, "
                    f"hit_rate={sym_stats['hit_rate']:.1f}%"
                )

        logger.info("=" * 60)

    def estimate_efficiency_gain(self) -> Dict[str, Any]:
        """
        تخمین بهبود کارایی

        Returns:
            دیکشنری حاوی تخمین‌های بهبود
        """
        total_requests = self.total_cache_hits + self.total_cache_misses

        if total_requests == 0:
            return {
                'requests_saved': 0,
                'percentage_saved': 0.0,
                'estimated_time_saved_seconds': 0.0,
            }

        # فرض: هر محاسبه امتیاز ~0.5 ثانیه طول می‌کشد
        avg_calculation_time = 0.5

        time_saved = self.total_cache_hits * avg_calculation_time

        return {
            'total_requests': total_requests,
            'cache_hits': self.total_cache_hits,
            'requests_saved_percentage': (self.total_cache_hits / total_requests * 100),
            'estimated_time_saved_seconds': time_saved,
            'estimated_time_saved_minutes': time_saved / 60,
            'estimated_time_saved_hours': time_saved / 3600,
        }
