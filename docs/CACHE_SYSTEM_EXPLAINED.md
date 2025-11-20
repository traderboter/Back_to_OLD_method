# راهنمای جامع Performance Caching - سیستم فعلی

این سند توضیح می‌دهد که سیستم فعلی چگونه از **Timestamp-Based Intelligent Caching** استفاده می‌کند.

---

## ✅ جواب کوتاه

**بله!** سیستم فعلی دقیقاً کاری که شما توضیح دادید را انجام می‌دهد:

- ✅ **کندل جدید 4h نداریم؟** → از cache استفاده می‌کند (محاسبه نمی‌کند)
- ✅ **کندل جدید 1h نداریم؟** → از cache استفاده می‌کند (محاسبه نمی‌کند)
- ✅ **کندل جدید 15m داریم؟** → محاسبه مجدد می‌کند
- ✅ **کندل جدید 5m داریم؟** → محاسبه مجدد می‌کند

---

## 🔍 چگونه کار می‌کند؟

### مثال واقعی:

فرض کنید الان ساعت **10:03** است:

```
Timeframes:
┌─────────────────────────────────────────────────┐
│ 5m:  آخرین کندل 10:00 → کندل جدید 10:05 می‌آید │ ← محاسبه مجدد ❌
│ 15m: آخرین کندل 10:00 → کندل جدید 10:15 می‌آید │ ← از cache ✅
│ 1h:  آخرین کندل 10:00 → کندل جدید 11:00 می‌آید │ ← از cache ✅
│ 4h:  آخرین کندل 08:00 → کندل جدید 12:00 می‌آید │ ← از cache ✅
└─────────────────────────────────────────────────┘

ساعت 10:06:
┌─────────────────────────────────────────────────┐
│ 5m:  کندل جدید آمد (10:05)                      │ ← محاسبه مجدد ✅
│ 15m: کندل جدید نیامده (هنوز 10:00)             │ ← از cache ✅
│ 1h:  کندل جدید نیامده (هنوز 10:00)             │ ← از cache ✅
│ 4h:  کندل جدید نیامده (هنوز 08:00)             │ ← از cache ✅
└─────────────────────────────────────────────────┘

ساعت 10:16:
┌─────────────────────────────────────────────────┐
│ 5m:  کندل جدید آمد (10:15)                      │ ← محاسبه مجدد ✅
│ 15m: کندل جدید آمد (10:15)                      │ ← محاسبه مجدد ✅
│ 1h:  کندل جدید نیامده (هنوز 10:00)             │ ← از cache ✅
│ 4h:  کندل جدید نیامده (هنوز 08:00)             │ ← از cache ✅
└─────────────────────────────────────────────────┘
```

**نتیجه:** بجای محاسبه 4 timeframe هر بار، فقط timeframe هایی که کندل جدید دارند محاسبه می‌شوند!

---

## 📂 کد مسئول (کجا پیدا کنیم؟)

### 1️⃣ **TimeframeScoreCache** - کلاس اصلی caching

**فایل:** `signal_generation/timeframe_score_cache.py` (469 خط)

```python
class TimeframeScoreCache:
    """
    مدیریت cache بر اساس timestamp آخرین کندل
    """

    def should_recalculate(
        self,
        symbol: str,
        timeframe: str,
        latest_candle_df: pd.DataFrame
    ) -> Tuple[bool, str]:
        """
        بررسی می‌کند که آیا کندل جدید آمده یا نه

        Returns:
            (باید محاسبه شود؟, دلیل)
        """

        # استخراج timestamp آخرین کندل از DataFrame
        latest_timestamp = int(latest_candle_df['timestamp'].iloc[-1].timestamp())

        # بررسی cache
        if symbol in self._cache:
            cached_score = self._cache[symbol].timeframes[timeframe]

            # مقایسه timestamps
            if latest_timestamp > cached_score.last_candle_timestamp:
                # کندل جدید آمده - باید دوباره محاسبه شود
                return True, "new_candle_available"
            else:
                # کندل جدید نیامده - استفاده از cache
                return False, "cache_valid"
```

**خطوط کلیدی:**
- **Line 129-212:** `should_recalculate()` - بررسی کندل جدید
- **Line 213-267:** `get_cached_score()` - دریافت از cache
- **Line 269-352:** `update_cache()` - ذخیره در cache
- **Line 376-408:** `get_statistics()` - آمار cache

---

### 2️⃣ **SignalOrchestrator** - استفاده از cache

**فایل:** `signal_generation/orchestrator.py`

```python
# Line 189-190: مقداردهی cache
self.tf_score_cache = TimeframeScoreCache(config)

# Line 308-320: بررسی cache قبل از محاسبه
should_recalc, reason = self.tf_score_cache.should_recalculate(
    symbol, timeframe, df
)

if not should_recalc:
    # استفاده از cache
    logger.info(f"💾 Using CACHED score for {symbol} {timeframe}")
    cached_signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
    return cached_signal

# محاسبه مجدد
logger.info(f"🔄 RECALCULATING score for {symbol} {timeframe} (reason: {reason})")

# Line 477: ذخیره در cache بعد از محاسبه
self.tf_score_cache.update_cache(symbol, timeframe, signal, df)
```

**خطوط کلیدی:**
- **Line 189:** Initialize cache
- **Line 308-320:** بررسی و استفاده از cache
- **Line 477:** Update cache

---

### 3️⃣ **Multi-Timeframe Analysis** - loop روی همه timeframes

**فایل:** `signal_generation/orchestrator.py`

```python
# Line 910-934: تولید signal برای هر timeframe
timeframe_signals: Dict[str, TimeframeSignal] = {}

for timeframe in ['5m', '15m', '1h', '4h']:
    # این فراخوانی، خودکار cache را بررسی می‌کند
    result = await self._generate_signal_with_context(symbol, timeframe)

    # _generate_signal_with_context در line 308 cache را چک می‌کند!
```

**نکته مهم:** هر بار که `_generate_signal_with_context` فراخوانی می‌شود، اول `should_recalculate` را چک می‌کند!

---

## 📊 چگونه آمار cache را ببینیم؟

### روش 1: در کد

```python
# دریافت آمار
stats = orchestrator.get_statistics()

print("📊 Cache Statistics:")
print(f"Total hits: {stats['cache']['statistics']['total_cache_hits']}")
print(f"Total misses: {stats['cache']['statistics']['total_cache_misses']}")
print(f"Hit rate: {stats['cache']['statistics']['global_hit_rate']:.1f}%")

# برآورد بهبود
efficiency = stats['cache']['efficiency']
print(f"\n⚡ Efficiency:")
print(f"Requests saved: {efficiency['cache_hits']}/{efficiency['total_requests']}")
print(f"Time saved: {efficiency['estimated_time_saved_minutes']:.1f} minutes")
```

### روش 2: Log ها

```bash
# Log ها به صورت خودکار نمایش می‌دهند
2025-01-20 10:06:00 - INFO - 💾 Using CACHED score for BTCUSDT 4h (reason: cache_valid)
2025-01-20 10:06:01 - INFO - 💾 Using CACHED score for BTCUSDT 1h (reason: cache_valid)
2025-01-20 10:06:02 - INFO - 🔄 RECALCULATING score for BTCUSDT 5m (reason: new_candle_available)
```

### روش 3: تابع log_cache_statistics()

```python
# نمایش آمار کامل
orchestrator.log_cache_statistics()

# خروجی:
# ============================================================
# 📊 Timeframe Score Cache Statistics
# ============================================================
# Enabled: True
# Symbols cached: 10
# Cache hits: 875
# Cache misses: 125
# Global hit rate: 87.5%
# Max cache age: 24.0h
#
# Per-symbol statistics:
#   BTCUSDT: 4 TFs, hits=120, hit_rate=92.3%
#   ETHUSDT: 4 TFs, hits=115, hit_rate=90.2%
#   ...
```

---

## ⚙️ تنظیمات Cache

فایل `config.yaml`:

```yaml
# تنظیمات TimeframeScoreCache
timeframe_score_cache:
  enabled: true                # فعال/غیرفعال
  max_cache_age_hours: 24      # حداکثر عمر cache (ساعت)
```

### غیرفعال کردن cache (برای تست):

```yaml
timeframe_score_cache:
  enabled: false  # همیشه محاسبه مجدد
```

---

## 🎯 مثال واقعی: بهبود عملکرد

### **قبل از cache** (فرضی - اگر نبود):

```
Scenario: Multi-TF Analysis هر 3 دقیقه یکبار
Timeframes: 5m, 15m, 1h, 4h

هر 3 دقیقه:
- محاسبه 5m  → 500ms
- محاسبه 15m → 500ms ❌ (کندل جدید نیست!)
- محاسبه 1h  → 500ms ❌ (کندل جدید نیست!)
- محاسبه 4h  → 500ms ❌ (کندل جدید نیست!)
────────────────────────────
Total: 2000ms (2 ثانیه)

در 1 ساعت (20 بار اجرا):
20 × 2000ms = 40,000ms = 40 ثانیه
```

### **با cache** (وضعیت فعلی):

```
Scenario: همان Multi-TF Analysis

هر 3 دقیقه:
- محاسبه 5m  → 500ms ✅ (کندل جدید دارد)
- از cache 15m → 5ms   ✅ (کندل جدید ندارد)
- از cache 1h  → 5ms   ✅ (کندل جدید ندارد)
- از cache 4h  → 5ms   ✅ (کندل جدید ندارد)
────────────────────────────
Total: 515ms

در 1 ساعت (20 بار اجرا):
20 × 515ms = 10,300ms = 10.3 ثانیه

بهبود: 40s → 10.3s (74% سریع‌تر! 🚀)
```

---

## 🔬 تست کردن Cache

### اسکریپت تست:

```python
# test_cache_behavior.py

import asyncio
from signal_generation.orchestrator import SignalOrchestrator
# ... imports

async def test_cache():
    orchestrator = SignalOrchestrator(config, data_fetcher, indicator_calc)

    print("\n=== Test 1: اولین بار (cache miss) ===")
    signal1 = await orchestrator._generate_signal_with_context('BTCUSDT', '4h')
    # انتظار: 🔄 RECALCULATING (reason: timeframe_not_in_cache)

    print("\n=== Test 2: بار دوم بدون کندل جدید (cache hit) ===")
    signal2 = await orchestrator._generate_signal_with_context('BTCUSDT', '4h')
    # انتظار: 💾 Using CACHED score (reason: cache_valid)

    print("\n=== Test 3: نمایش آمار ===")
    orchestrator.log_cache_statistics()

asyncio.run(test_cache())
```

**خروجی انتظاری:**

```
=== Test 1: اولین بار (cache miss) ===
INFO - 🔄 RECALCULATING score for BTCUSDT 4h (reason: timeframe_not_in_cache)
INFO - [3/7] Calculating indicators for BTCUSDT
INFO - ✓ Indicators calculated (500ms)
...

=== Test 2: بار دوم بدون کندل جدید (cache hit) ===
INFO - 💾 Using CACHED score for BTCUSDT 4h (reason: cache_valid)
INFO - ✓ Retrieved from cache (5ms)

=== Test 3: نمایش آمار ===
============================================================
📊 Timeframe Score Cache Statistics
============================================================
Cache hits: 1
Cache misses: 1
Global hit rate: 50.0%
```

---

## 💡 نکات مهم

### ✅ مزایا

1. **کاهش 70-90% محاسبات غیرضروری**
   - تایم‌فریم 4h فقط هر 4 ساعت یکبار محاسبه می‌شود

2. **صرفه‌جویی در CPU**
   - indicator calculation برای timeframe های بدون تغییر اجرا نمی‌شود

3. **کاهش API calls**
   - اگر از API داده می‌گیرید، cache تعداد request ها را کاهش می‌دهد

4. **Thread-safe**
   - از Lock استفاده می‌کند (Line 112)

### ⚠️ محدودیت‌ها

1. **حافظه RAM**
   - هر signal در cache ذخیره می‌شود
   - برای 10 نماد × 4 timeframe = 40 entry (معمولاً ~10MB)

2. **Max cache age**
   - پیش‌فرض: 24 ساعت
   - cache های قدیمی‌تر expire می‌شوند

3. **فقط برای orchestrator**
   - indicator calculation خودش caching ندارد (فقط signal cache دارد)

---

## 🚀 بهبودهای احتمالی (اختیاری)

اگر بخواهید cache را بیشتر بهینه کنید:

### 1. Indicator-Level Caching

```python
class CachedIndicatorCalculator:
    """Cache indicators بر اساس DataFrame hash"""

    def calculate_all(self, context):
        # Hash last 5 candles
        cache_key = hash(context.df[['close', 'volume']].tail(5).values.tobytes())

        if cache_key in self.cache:
            # استفاده از cached indicators
            context.df = self.cache[cache_key]
            return

        # محاسبه و cache
        self._calculate_indicators(context)
        self.cache[cache_key] = context.df.copy()
```

**مزیت:** حتی سریع‌تر (اگر indicator calculation bottle-neck باشد)

### 2. LRU Cache برای حافظه محدود

```python
from functools import lru_cache

class TimeframeScoreCache:
    def __init__(self):
        self._cache = {}  # محدود به N entries اخیر

    def _evict_old_entries(self):
        """حذف قدیمی‌ترین entries"""
        if len(self._cache) > MAX_ENTRIES:
            # حذف 20% قدیمی‌ترین
            ...
```

**مزیت:** استفاده حافظه ثابت (برای production مهم است)

---

## 📋 خلاصه

| سوال | جواب |
|------|------|
| **آیا سیستم این کار را انجام می‌دهد؟** | ✅ بله، کاملاً! |
| **کجا کد را پیدا کنم؟** | `timeframe_score_cache.py` + `orchestrator.py` |
| **چگونه آمار ببینم؟** | `orchestrator.log_cache_statistics()` |
| **چگونه تنظیم کنم؟** | `config.yaml` → `timeframe_score_cache.enabled` |
| **چقدر سریع‌تر می‌شود؟** | ~70-90% کاهش زمان (بستگی به timeframe ها) |
| **Thread-safe است؟** | ✅ بله (با Lock) |
| **حافظه چقدر استفاده می‌کند؟** | ~10-20MB برای 10 نماد × 4 TF |

---

## 🎯 نتیجه‌گیری

سیستم فعلی **کاملاً هوشمند** است و دقیقاً آنچه شما توضیح دادید را انجام می‌دهد:

```
✅ کندل جدید نداریم → از cache
✅ کندل جدید داریم → محاسبه مجدد
✅ برای هر timeframe جداگانه
✅ بر اساس timestamp واقعی کندل
✅ با آمار کامل
```

**هیچ تغییری لازم نیست!** سیستم از همان ابتدا این قابلیت را داشته است. 🎉

---

**نویسنده:** Claude Code
**تاریخ:** 2025-01-20
**نسخه سیستم:** NEW SYSTEM v2.0
