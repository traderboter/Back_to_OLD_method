# راهنمای پیاده‌سازی Indicator-Level Caching

این سند نحوه پیاده‌سازی Indicator-Level Cache را توضیح می‌دهد.

---

## 🎯 هدف

افزودن یک لایه cache برای محاسبات indicator که:
- ✅ Indicators را cache می‌کند (نه فقط Signals)
- ✅ از DataFrame hash استفاده می‌کند
- ✅ تغییرات config را تشخیص می‌دهد
- ✅ مستقل از Signal Cache کار می‌کند

---

## 📊 معماری دو سطحی Cache

```
┌──────────────────────────────────────────────────┐
│         Request: Generate Signal                 │
└──────────────────────────────────────────────────┘
                     ↓
      ┌──────────────────────────────┐
      │  Level 1: Signal Cache       │ ← موجود است
      │  (TimeframeScoreCache)       │
      └──────────────────────────────┘
                     ↓
              ┌─────┴─────┐
              │   Hit?    │
              └─────┬─────┘
        Yes ←───────┘        No
         ↓                    ↓
    Return Signal      ┌─────────────────┐
                       │ Level 2:        │ ← 🆕 جدید
                       │ Indicator Cache │
                       └─────────────────┘
                              ↓
                       ┌─────┴─────┐
                       │   Hit?    │
                       └─────┬─────┘
                 Yes ←───────┘        No
                  ↓                    ↓
          Skip calculation      Calculate Indicators
          Use cached indicators ────────┘
                  │
                  ↓
          Run Analyzers (50-70% سریع‌تر!)
                  ↓
          Calculate Score
                  ↓
          Update both caches
                  ↓
          Return Signal
```

---

## 🔧 پیاده‌سازی

### 1️⃣ کلاس IndicatorCache

**فایل جدید:** `signal_generation/shared/indicator_cache.py`

```python
"""
Indicator Cache - Cache for technical indicator calculations

این کلاس محاسبات indicator را cache می‌کند تا از محاسبات تکراری
جلوگیری کند.

مزایا:
- کاهش 50-70% زمان محاسبات در سناریوهای خاص
- بهینه برای backtesting و parameter optimization
- مستقل از Signal Cache
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import hashlib
import time
import logging
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class CachedIndicators:
    """Indicators کش شده برای یک DataFrame"""

    # DataFrame با indicator columns
    df_with_indicators: pd.DataFrame

    # Hash of input data (برای تشخیص تغییرات)
    data_hash: str

    # Hash of config (برای تشخیص تغییرات تنظیمات)
    config_hash: str

    # زمان محاسبه
    calculated_at: float = field(default_factory=time.time)

    # آمار
    hit_count: int = 0

    def is_valid(self, data_hash: str, config_hash: str, max_age: float) -> bool:
        """بررسی اعتبار cache"""

        # بررسی تغییر داده
        if data_hash != self.data_hash:
            return False

        # بررسی تغییر config
        if config_hash != self.config_hash:
            return False

        # بررسی عمر cache
        age = time.time() - self.calculated_at
        if age > max_age:
            return False

        return True


class IndicatorCache:
    """
    Cache برای محاسبات indicator

    این کلاس indicators را بر اساس:
    1. Hash of DataFrame (آخرین N کندل)
    2. Hash of config (تنظیمات indicator)

    cache می‌کند.

    مثال:
        >>> cache = IndicatorCache(config)
        >>>
        >>> # اولین بار - محاسبه
        >>> df_with_indicators = cache.get_or_calculate(
        ...     df=raw_df,
        ...     calculator=indicator_calculator,
        ...     context=context
        ... )
        >>> # بار دوم - از cache
        >>> df_with_indicators = cache.get_or_calculate(
        ...     df=same_raw_df,
        ...     calculator=indicator_calculator,
        ...     context=context
        ... )  # سریع! از cache می‌آید
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IndicatorCache

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Cache storage: {cache_key: CachedIndicators}
        self._cache: Dict[str, CachedIndicators] = {}

        # Lock for thread safety
        self._lock = Lock()

        # تنظیمات
        cache_config = self.config.get('indicator_cache', {})
        self.enabled = cache_config.get('enabled', True)
        self.max_cache_age = cache_config.get('max_cache_age_seconds', 3600)  # 1 hour
        self.max_cache_entries = cache_config.get('max_entries', 100)
        self.hash_window = cache_config.get('hash_window', 10)  # آخرین N کندل

        # آمار
        self.total_hits = 0
        self.total_misses = 0
        self.total_calculations = 0

        logger.info(
            f"IndicatorCache initialized "
            f"(enabled={self.enabled}, max_age={self.max_cache_age}s, "
            f"max_entries={self.max_cache_entries})"
        )

    def _compute_data_hash(self, df: pd.DataFrame) -> str:
        """
        محاسبه hash از DataFrame

        فقط آخرین N کندل را در نظر می‌گیرد (برای سرعت)
        """
        # استفاده از آخرین N کندل
        window = min(self.hash_window, len(df))
        recent_data = df[['open', 'high', 'low', 'close', 'volume']].tail(window)

        # تبدیل به bytes و hash
        data_bytes = recent_data.values.tobytes()
        return hashlib.md5(data_bytes).hexdigest()

    def _compute_config_hash(self) -> str:
        """
        محاسبه hash از تنظیمات indicator
        """
        # فقط بخش indicators را در نظر می‌گیریم
        indicators_config = self.config.get('indicators', {})

        # تبدیل به string و hash
        config_str = str(sorted(indicators_config.items()))
        return hashlib.md5(config_str.encode()).hexdigest()

    def _get_cache_key(self, symbol: str, timeframe: str, data_hash: str) -> str:
        """تولید کلید cache"""
        return f"{symbol}_{timeframe}_{data_hash}"

    def get_or_calculate(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        calculator: Any,  # IndicatorCalculator instance
        context: Any  # AnalysisContext instance
    ) -> pd.DataFrame:
        """
        دریافت indicators از cache یا محاسبه

        Args:
            df: DataFrame خام (بدون indicators)
            symbol: نماد
            timeframe: تایم‌فریم
            calculator: IndicatorCalculator instance
            context: AnalysisContext instance

        Returns:
            DataFrame با indicator columns
        """
        if not self.enabled:
            # Cache غیرفعال - محاسبه مستقیم
            calculator.calculate_all(context)
            self.total_calculations += 1
            return context.df

        # محاسبه hashes
        data_hash = self._compute_data_hash(df)
        config_hash = self._compute_config_hash()
        cache_key = self._get_cache_key(symbol, timeframe, data_hash)

        with self._lock:
            # بررسی cache
            if cache_key in self._cache:
                cached = self._cache[cache_key]

                # اعتبارسنجی
                if cached.is_valid(data_hash, config_hash, self.max_cache_age):
                    # Cache hit!
                    cached.hit_count += 1
                    self.total_hits += 1

                    logger.debug(
                        f"✓ Indicator Cache HIT for {symbol} {timeframe} "
                        f"(hits={cached.hit_count}, age={time.time() - cached.calculated_at:.0f}s)"
                    )

                    # بازگرداندن DataFrame از cache
                    context.df = cached.df_with_indicators.copy()
                    return context.df

        # Cache miss - محاسبه مجدد
        self.total_misses += 1
        self.total_calculations += 1

        logger.debug(
            f"✗ Indicator Cache MISS for {symbol} {timeframe} "
            f"(reason: not_found or invalid)"
        )

        # محاسبه indicators
        start_time = time.time()
        calculator.calculate_all(context)
        calc_time = (time.time() - start_time) * 1000  # ms

        logger.debug(f"  Calculated indicators in {calc_time:.0f}ms")

        # ذخیره در cache
        with self._lock:
            self._cache[cache_key] = CachedIndicators(
                df_with_indicators=context.df.copy(),
                data_hash=data_hash,
                config_hash=config_hash,
                calculated_at=time.time(),
                hit_count=0
            )

            # مدیریت حجم cache
            if len(self._cache) > self.max_cache_entries:
                self._evict_old_entries()

        return context.df

    def _evict_old_entries(self):
        """حذف قدیمی‌ترین entries"""
        # حذف 20% قدیمی‌ترین entries
        num_to_remove = int(self.max_cache_entries * 0.2)

        # مرتب‌سازی بر اساس زمان
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].calculated_at
        )

        # حذف
        for key, _ in sorted_entries[:num_to_remove]:
            del self._cache[key]

        logger.debug(f"Evicted {num_to_remove} old cache entries")

    def invalidate_symbol(self, symbol: str):
        """حذف تمام cache های یک symbol"""
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{symbol}_")]
            for key in keys_to_remove:
                del self._cache[key]

            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {symbol}")

    def clear_all(self):
        """پاک کردن کل cache"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared entire indicator cache ({count} entries)")

    def get_statistics(self) -> Dict[str, Any]:
        """آمار cache"""
        with self._lock:
            total_requests = self.total_hits + self.total_misses
            hit_rate = (self.total_hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                'enabled': self.enabled,
                'total_entries': len(self._cache),
                'total_hits': self.total_hits,
                'total_misses': self.total_misses,
                'total_calculations': self.total_calculations,
                'hit_rate': hit_rate,
                'max_entries': self.max_cache_entries,
                'max_age_seconds': self.max_cache_age,
            }

    def log_statistics(self):
        """نمایش آمار در log"""
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("📊 Indicator Cache Statistics")
        logger.info("=" * 60)
        logger.info(f"Enabled: {stats['enabled']}")
        logger.info(f"Cache entries: {stats['total_entries']}/{stats['max_entries']}")
        logger.info(f"Cache hits: {stats['total_hits']}")
        logger.info(f"Cache misses: {stats['total_misses']}")
        logger.info(f"Hit rate: {stats['hit_rate']:.1f}%")
        logger.info(f"Total calculations: {stats['total_calculations']}")
        logger.info("=" * 60)
```

---

## 2️⃣ ادغام با IndicatorCalculator

**فایل:** `signal_generation/shared/indicator_calculator.py`

```python
from signal_generation.shared.indicator_cache import IndicatorCache

class IndicatorCalculator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.orchestrator = IndicatorOrchestrator(config)

        # 🆕 اضافه کردن Indicator Cache
        self.indicator_cache = IndicatorCache(config)

        self._register_indicators()

    def calculate_all(self, context) -> None:
        """
        محاسبه indicators با استفاده از cache
        """
        # 🆕 استفاده از cache
        context.df = self.indicator_cache.get_or_calculate(
            df=context.df,
            symbol=context.symbol,
            timeframe=context.timeframe,
            calculator=self,  # خودش
            context=context
        )

        # اگر از cache آمد، این خط اجرا نمی‌شود
        # اگر cache نبود، get_or_calculate خودش calculate_all را صدا می‌زند
```

---

## 3️⃣ تنظیمات Config

**فایل:** `config.yaml`

```yaml
# تنظیمات Indicator Cache (🆕 جدید)
indicator_cache:
  enabled: true                    # فعال/غیرفعال
  max_cache_age_seconds: 3600      # حداکثر عمر cache (1 ساعت)
  max_entries: 100                 # حداکثر تعداد entries
  hash_window: 10                  # تعداد کندل‌های آخر برای hash

# تنظیمات Signal Cache (موجود)
timeframe_score_cache:
  enabled: true
  max_cache_age_hours: 24
```

---

## 📊 مقایسه عملکرد

### Scenario 1: تغییر تنظیمات scoring

```python
# بدون Indicator Cache
for config_variant in [config1, config2, config3]:
    orchestrator.config = config_variant
    signal = await orchestrator._generate_signal_with_context('BTCUSDT', '1h')
    # هر بار: Indicators (400ms) + Analyzers (100ms) + Score (50ms) = 550ms
    # Total: 550ms × 3 = 1650ms

# با Indicator Cache
for config_variant in [config1, config2, config3]:
    orchestrator.config = config_variant
    signal = await orchestrator._generate_signal_with_context('BTCUSDT', '1h')
    # اولین بار: 550ms
    # بار دوم و سوم: Indicators (5ms) + Analyzers (100ms) + Score (50ms) = 155ms
    # Total: 550ms + 155ms + 155ms = 860ms

# بهبود: 48% سریع‌تر
```

### Scenario 2: Backtesting

```python
# Test 5 استراتژی روی 1000 کندل

# بدون Indicator Cache
for strategy in strategies:
    for candle_set in candle_sets:  # 1000 set
        calculate_indicators()  # 400ms × 1000 × 5 = 2,000,000ms (33 دقیقه!)

# با Indicator Cache
for candle_set in candle_sets:  # 1000 set
    calculate_indicators()  # فقط یکبار: 400ms × 1000 = 400,000ms

for strategy in strategies[1:]:  # 4 استراتژی دیگر
    for candle_set in candle_sets:
        get_from_cache()  # 5ms × 1000 × 4 = 20,000ms

# Total: 400,000ms + 20,000ms = 420,000ms (7 دقیقه)
# بهبود: 79% سریع‌تر! 🚀
```

---

## 🧪 تست

```python
# tests/unit/signal_generation/test_indicator_cache.py

import pytest
from signal_generation.shared.indicator_cache import IndicatorCache

def test_cache_hit_with_same_data(config, sample_df):
    """تست: با داده یکسان، از cache استفاده می‌شود"""
    cache = IndicatorCache(config)

    # اولین بار
    result1 = cache.get_or_calculate(
        df=sample_df, symbol='BTCUSDT', timeframe='1h',
        calculator=mock_calculator, context=mock_context
    )

    # بار دوم با همان داده
    result2 = cache.get_or_calculate(
        df=sample_df, symbol='BTCUSDT', timeframe='1h',
        calculator=mock_calculator, context=mock_context
    )

    # بررسی
    assert cache.total_hits == 1
    assert cache.total_misses == 1
    pd.testing.assert_frame_equal(result1, result2)


def test_cache_miss_with_different_data(config, sample_df):
    """تست: با داده متفاوت، دوباره محاسبه می‌شود"""
    cache = IndicatorCache(config)

    # اولین بار
    result1 = cache.get_or_calculate(
        df=sample_df, symbol='BTCUSDT', timeframe='1h',
        calculator=mock_calculator, context=mock_context
    )

    # بار دوم با داده متفاوت
    different_df = sample_df.copy()
    different_df['close'].iloc[-1] += 100  # تغییر قیمت

    result2 = cache.get_or_calculate(
        df=different_df, symbol='BTCUSDT', timeframe='1h',
        calculator=mock_calculator, context=mock_context
    )

    # بررسی
    assert cache.total_hits == 0
    assert cache.total_misses == 2  # هر دو بار miss


def test_cache_miss_with_different_config(config, sample_df):
    """تست: با config متفاوت، دوباره محاسبه می‌شود"""
    cache = IndicatorCache(config)

    # اولین بار
    result1 = cache.get_or_calculate(
        df=sample_df, symbol='BTCUSDT', timeframe='1h',
        calculator=mock_calculator, context=mock_context
    )

    # تغییر config
    cache.config['indicators']['ema_periods'] = [10, 20]  # تغییر

    # بار دوم با همان داده اما config متفاوت
    result2 = cache.get_or_calculate(
        df=sample_df, symbol='BTCUSDT', timeframe='1h',
        calculator=mock_calculator, context=mock_context
    )

    # بررسی
    assert cache.total_misses == 2  # هر دو بار miss (config تغییر کرد)
```

---

## 📈 نتایج انتظاری

### Hit Rate بر اساس use case:

| Use Case | Hit Rate | بهبود زمان |
|----------|----------|------------|
| Real-time trading (تک symbol) | 30-50% | 20-30% |
| Real-time trading (چند symbol) | 50-70% | 40-50% |
| Backtesting | 80-95% | 70-85% |
| Parameter optimization | 90-98% | 85-95% |

---

## 💡 نکات پیاده‌سازی

### ✅ مزایا:
1. سریع‌تر برای backtesting و optimization
2. کاهش CPU usage
3. مستقل از Signal Cache
4. Thread-safe

### ⚠️ محدودیت‌ها:
1. استفاده حافظه: ~50-100MB برای 100 entries
2. فقط برای DataFrame های یکسان مفید است
3. نیاز به tuning پارامترهای hash_window

### 🎯 کاربردهای اصلی:
- ✅ Backtesting چند استراتژی
- ✅ Parameter optimization (grid search)
- ✅ A/B testing
- ⚠️ Real-time (فایده کمتری دارد - Signal Cache کافی است)

---

## 🚀 گام‌های پیاده‌سازی

1. ✅ ایجاد `indicator_cache.py` (2-3 ساعت)
2. ✅ ادغام با `IndicatorCalculator` (1 ساعت)
3. ✅ نوشتن تست‌ها (1-2 ساعت)
4. ✅ تنظیمات config (30 دقیقه)
5. ✅ مستندات و مثال‌ها (1 ساعت)

**Total: 5-7 ساعت**

---

## 📝 نتیجه‌گیری

Indicator-Level Cache یک بهبود **optional** است که در سناریوهای خاص (backtesting, optimization) بسیار مفید است:

```
✅ Real-time trading: Signal Cache کافی است
✅ Backtesting: Indicator Cache + Signal Cache → 70-85% سریع‌تر
✅ Optimization: Indicator Cache + Signal Cache → 85-95% سریع‌تر
```

---

**آخرین بروزرسانی:** 2025-01-20
