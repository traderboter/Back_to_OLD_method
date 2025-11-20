# تحلیل کامل فرآیند تولید سیگنال معاملاتی - سیستم جدید

## مقدمه

این سند توضیح می‌دهد که در **سیستم جدید** (معماری ماژولار)، وقتی داده‌های چند تایم‌فریم (5m, 15m, 1h, 4h) برای تحلیل و ایجاد سیگنال معاملاتی دریافت می‌شوند، چه اتفاقاتی می‌افتد.

### 🔄 تفاوت با سیستم قدیم

| جنبه | سیستم قدیم | سیستم جدید |
|------|-----------|-----------|
| **ساختار** | یک فایل بزرگ `signal_generator.py` | معماری ماژولار در `signal_generation/` |
| **نقطه ورود** | کلاس `SignalGenerator` | کلاس `SignalOrchestrator` |
| **Analyzers** | متدهای داخلی در یک کلاس | 11 کلاس مجزا در `analyzers/` |
| **Indicators** | محاسبه چندباره | محاسبه یکباره با `IndicatorCalculator` |
| **امتیازدهی** | داخل `SignalGenerator` | کلاس مجزا `SignalScorer` |
| **اعتبارسنجی** | داخل `SignalGenerator` | کلاس مجزا `SignalValidator` |
| **سیستم‌های هوشمند** | داخل `SignalGenerator` | 4 کلاس مجزا در `systems/` |

### 📦 ساختار سیستم جدید

```
signal_generation/
├── orchestrator.py               # 🎯 نقطه ورود اصلی (جایگزین signal_generator.py)
│
├── analyzers/                    # 📊 11 آنالیزگر مجزا
│   ├── trend_analyzer.py         # تحلیل روند
│   ├── momentum_analyzer.py      # تحلیل مومنتوم
│   ├── volume_analyzer.py        # تحلیل حجم
│   ├── volume_pattern_analyzer.py # الگوهای حجم
│   ├── pattern_analyzer.py       # الگوهای کندلی و چارت
│   ├── sr_analyzer.py            # سطوح حمایت/مقاومت
│   ├── volatility_analyzer.py    # نوسان
│   ├── harmonic_analyzer.py      # الگوهای هارمونیک
│   ├── channel_analyzer.py       # کانال‌ها
│   ├── cyclical_analyzer.py      # چرخه‌های بازار
│   └── htf_analyzer.py           # تایم‌فریم بالاتر
│
├── systems/                      # 🧠 سیستم‌های هوشمند
│   ├── market_regime_detector.py      # تشخیص رژیم بازار
│   ├── adaptive_learning_system.py    # یادگیری تطبیقی
│   ├── correlation_manager.py         # مدیریت همبستگی
│   └── emergency_circuit_breaker.py   # توقف اضطراری
│
├── signal_scorer.py              # ⭐ امتیازدهی سیگنال
├── signal_validator.py           # ✅ اعتبارسنجی سیگنال
├── timeframe_score_cache.py     # 💾 کش امتیازات
├── multi_tf_aggregator.py       # 🔄 ترکیب چند تایم‌فریم
│
└── shared/
    ├── indicator_calculator.py   # 📈 محاسبه یکباره اندیکاتورها
    └── data_models.py            # مدل‌های داده
```

---

## بخش ۱: مسیر ورود داده و شروع تحلیل

### 1.1 نقطه شروع: دریافت داده‌ها

وقتی `SignalProcessor` یک نماد را برای تحلیل انتخاب می‌کند، این کار از متد `process_symbol()` شروع می‌شود:

**محل:** `signal_processor.py:392-560` (همانند سیستم قبل)

```python
async def process_symbol(self, symbol: str, force_refresh: bool = False, priority: bool = False)
```

#### 🔧 مدیریت AsyncIO Tasks و Concurrency

**1. Task Naming برای Debugging:**

سیستم جدید از نام‌گذاری Task های AsyncIO استفاده می‌کند تا مانیتورینگ و debugging آسان‌تر شود:

```python
task = asyncio.create_task(
    self.orchestrator.analyze_symbol(symbol, timeframes_data),
    name=f"analyze_{symbol}_{timeframe}"
)
```

**مزایا:**
- 🔍 ردیابی آسان task ها در لاگ‌ها
- 🐛 debugging سریع‌تر مشکلات
- 📊 مانیتورینگ دقیق‌تر عملکرد

**2. Semaphore برای کنترل همزمانی:**

برای جلوگیری از اجرای همزمان بیش از حد تحلیل‌ها، از Semaphore استفاده می‌شود:

```python
# محدود کردن به حداکثر 5 تحلیل همزمان
self.analysis_semaphore = asyncio.Semaphore(5)

async def process_symbol(self, symbol: str, ...):
    async with self.analysis_semaphore:
        # تحلیل سمبل
        ...
```

**چرا مهم است؟**
- ⚡ جلوگیری از مصرف بیش از حد CPU
- 💾 مدیریت بهتر حافظه
- 🛡️ جلوگیری از Rate Limiting API ها

**3. Thread Safety در محیط Async:**

برای مدیریت لیست سیگنال‌های ناقص، از Lock استفاده می‌شود:

```python
self.incomplete_signals_lock = asyncio.Lock()

async with self.incomplete_signals_lock:
    self.incomplete_signals[symbol] = {
        'timestamp': datetime.now(),
        'reason': 'insufficient_data'
    }
```

**اهمیت:**
- 🔒 جلوگیری از Race Condition
- ✅ اطمینان از consistency داده‌ها
- 🧵 امنیت در دسترسی همزمان

**اتفاقات:**

1. دریافت داده‌های چند تایم‌فریمی از `MarketDataFetcher`:
   ```python
   timeframes_data = await self.market_data_fetcher.get_multi_timeframe_data(
       symbol, self.timeframes, force_refresh, limit_per_tf=limit_needed
   )
   ```

2. **🆕 Graceful Degradation - مدیریت داده‌های ناقص:**

   سیستم جدید می‌تواند با داده‌های ناقص کار کند و هشدار می‌دهد:

   ```python
   valid_timeframes = {
       tf: df for tf, df in timeframes_data.items()
       if df is not None and not df.empty
   }

   if not valid_timeframes:
       # هیچ داده معتبری وجود ندارد
       logger.warning(f"⚠️ No valid data for {symbol}")
       async with self.incomplete_signals_lock:
           self.incomplete_signals[symbol] = {
               'timestamp': datetime.now(timezone.utc),
               'reason': 'no_valid_data'
           }
       return None

   # داده‌های بعضی تایم‌فریم‌ها ناقص است
   missing_tfs = set(self.timeframes) - set(valid_timeframes.keys())
   if missing_tfs:
       logger.warning(
           f"⚠️ Partial data for {symbol}. "
           f"Missing timeframes: {missing_tfs}. "
           f"Continuing with available data: {list(valid_timeframes.keys())}"
       )
   ```

   **مزایا:**
   - ✅ سیستم متوقف نمی‌شود در صورت نقص داده
   - 📊 تحلیل با داده‌های موجود ادامه می‌یابد
   - ⚠️ هشدارهای واضح برای مانیتورینگ
   - 💾 ذخیره سیگنال‌های ناقص برای بررسی بعدی

3. **🆕 فراخوانی Orchestrator** (تفاوت اصلی با سیستم قدیم):
   ```python
   # سیستم جدید
   signal = await self.orchestrator.analyze_symbol(symbol, timeframes_data)

   # سیستم قدیم (برای مقایسه)
   # signal = await self.signal_generator.analyze_symbol(symbol, timeframes_data)
   ```

---

### 1.2 فرآیند تولید سیگنال در SignalOrchestrator

**محل:** `signal_generation/orchestrator.py:854-966`

```python
async def analyze_symbol(self, symbol: str, timeframes_data: Dict[str, Any]) -> Optional[SignalInfo]
```

این متد یک **wrapper** برای تحلیل چند تایم‌فریمی است.

**گام‌های اصلی:**

#### مرحله 1: فیلتر کردن تایم‌فریم‌های معتبر

```python
# محل: orchestrator.py:876-883
valid_timeframes = {
    tf: df for tf, df in timeframes_data.items()
    if df is not None and not df.empty
}
```

#### مرحله 2: انتخاب روش تولید سیگنال

سیستم جدید **دو حالت** پشتیبانی می‌کند:

**🔄 حالت 1: Multi-TF Aggregation (OLD SYSTEM MODE)**

```python
# محل: orchestrator.py:886-934
if self.use_multi_tf_aggregation and self.multi_tf_aggregator:
    # تولید سیگنال برای هر تایم‌فریم
    timeframe_signals: Dict[str, TimeframeSignal] = {}

    for timeframe in valid_timeframes.keys():
        result = await self._generate_signal_with_context(symbol, timeframe)
        if result:
            signal, context = result
            timeframe_signals[timeframe] = TimeframeSignal(...)

    # ترکیب سیگنال‌ها با روش قدیمی
    aggregated_signal = self.multi_tf_aggregator.aggregate_timeframe_scores(
        symbol=symbol,
        timeframe_signals=timeframe_signals
    )
```

**مزایا:**
- ✅ سازگار با سیستم قدیم
- ✅ ترکیب همه تایم‌فریم‌ها
- ✅ امتیازدهی وزن‌دار

**🎯 حالت 2: Best Signal Selection (NEW SYSTEM MODE)**

```python
# محل: orchestrator.py:937-962
else:
    # تولید سیگنال برای هر تایم‌فریم
    signals = []
    for timeframe in valid_timeframes.keys():
        signal = await self.generate_signal_for_symbol(symbol, timeframe)
        if signal:
            signals.append(signal)

    # انتخاب بهترین سیگنال
    best_signal = max(signals, key=lambda s: s.score.final_score)
```

**مزایا:**
- ✅ ساده‌تر و واضح‌تر
- ✅ انتخاب قوی‌ترین سیگنال
- ✅ عملکرد بهتر

---

## بخش ۲: تحلیل یک تایم‌فریم (مثال: 1h)

این بخش **مهم‌ترین بخش** است که در آن تحلیل کامل یک نماد در یک تایم‌فریم انجام می‌شود.

### 2.1 ورودی به generate_signal_for_symbol

**محل:** `signal_generation/orchestrator.py:250-495`

```python
async def generate_signal_for_symbol(
    self,
    symbol: str,
    timeframe: str
) -> Optional[SignalInfo]
```

این متد **هسته اصلی** تولید سیگنال است و **7 مرحله** دارد:

---

### 🚨 مرحله 0: بررسی Circuit Breaker (مدار شکن اضطراری)

**محل:** `orchestrator.py:272-281`

```python
if self.circuit_breaker.enabled:
    is_active, reason = self.circuit_breaker.check_if_active()
    if is_active:
        logger.warning(
            f"🚨 Circuit breaker active: {reason}. "
            f"Skipping signal generation for {symbol}."
        )
        return None
```

**🔧 پیاده‌سازی:** `signal_generation/systems/emergency_circuit_breaker.py`

Circuit Breaker یک سیستم محافظتی است که در شرایط خطرناک، تولید سیگنال را متوقف می‌کند.

#### دو مکانیزم فعال‌سازی:

##### مکانیزم 1: بررسی عملکرد معاملات قبلی

**شرط 1: ضررهای متوالی (Consecutive Losses)**

```python
max_consecutive_losses = 3  # پیش‌فرض

# اگر 3 معامله متوالی ضرر داد
if consecutive_losses >= 3:
    circuit_breaker.trigger()
    # توقف معاملات به مدت 60 دقیقه
```

**مثال:**
```
معامله 1: -1.5R ❌
معامله 2: -0.8R ❌
معامله 3: -1.2R ❌
→ Circuit Breaker فعال می‌شود! 🔴
→ معاملات متوقف می‌شوند برای 60 دقیقه
```

**شرط 2: ضرر کل روزانه (Daily Loss Limit)**

```python
max_daily_losses_r = 5.0  # حداکثر 5R ضرر در روز

# اگر مجموع ضررهای روز از 5R بیشتر شد
if daily_loss_r >= 5.0:
    circuit_breaker.trigger()
```

**مثال:**
```
09:00 - معامله 1: -2.0R ❌
11:30 - معامله 2: +1.5R ✅
14:00 - معامله 3: -1.8R ❌
16:00 - معامله 4: -2.5R ❌
────────────────────────
مجموع ضرر: 2.0 + 1.8 + 2.5 = 6.3R > 5.0R
→ Circuit Breaker فعال می‌شود! 🔴
```

##### مکانیزم 2: تشخیص بی‌ثباتی بازار

Circuit Breaker با بررسی داده‌های بازار، شرایط غیرعادی را تشخیص می‌دهد.

**⚙️ پیکربندی Circuit Breaker:**

**محل:** `config/config.yaml`

```yaml
systems:
  circuit_breaker:
    enabled: true                        # فعال/غیرفعال
    max_consecutive_losses: 3            # حداکثر ضرر متوالی
    max_daily_losses_r: 5.0              # حداکثر ضرر روزانه (R)
    cool_down_period_minutes: 60         # مدت توقف (دقیقه)
    reset_period_hours: 24               # بازنشانی آمار روزانه
```

**⚠️ نکته مهم:** در کد، Circuit Breaker با استفاده از مسیر `systems.circuit_breaker` در config فعال می‌شود:

```python
# signal_generation/systems/emergency_circuit_breaker.py
def __init__(self, config: Optional[Dict] = None):
    # خواندن تنظیمات از بخش systems.circuit_breaker
    cb_config = config.get('systems', {}).get('circuit_breaker', {})

    self.enabled = cb_config.get('enabled', True)
    self.max_consecutive_losses = cb_config.get('max_consecutive_losses', 3)
    self.max_daily_losses_r = cb_config.get('max_daily_losses_r', 5.0)
    self.cool_down_period_minutes = cb_config.get('cool_down_period_minutes', 60)
    self.reset_period_hours = cb_config.get('reset_period_hours', 24)
```

**📋 پارامترهای قابل تنظیم:**

| پارامتر | پیش‌فرض | توضیح |
|---------|---------|-------|
| `enabled` | `true` | فعال/غیرفعال کردن کامل |
| `max_consecutive_losses` | `3` | حداکثر ضرر متوالی قبل از توقف |
| `max_daily_losses_r` | `5.0` | حداکثر ضرر روزانه به R |
| `cool_down_period_minutes` | `60` | مدت زمان توقف معاملات (دقیقه) |
| `reset_period_hours` | `24` | بازه زمانی بازنشانی آمار |

**مثال سفارشی‌سازی:**
```yaml
systems:
  circuit_breaker:
    enabled: true
    max_consecutive_losses: 2        # محافظه‌کارانه‌تر
    max_daily_losses_r: 3.0          # محدودتر
    cool_down_period_minutes: 120    # استراحت بیشتر
    reset_period_hours: 24
```

---

### 📥 مرحله 1: دریافت داده‌های بازار

**محل:** `orchestrator.py:283-293`

```python
logger.info(f"[1/7] Fetching data for {symbol} {timeframe}")

df = await self._fetch_market_data(symbol, timeframe)

if df is None:
    logger.warning(f"No data available for {symbol}")
    return None

logger.info(f"  ✓ Fetched {len(df)} candles")
```

**متد دریافت داده:** `orchestrator.py:497-515`

```python
async def _fetch_market_data(self, symbol: str, timeframe: str):
    """Fetch market data using MarketDataFetcher."""
    try:
        df = await self.market_data_fetcher.get_ohlcv_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=self.ohlcv_limit  # پیش‌فرض: 500 کندل
        )

        if df is None or df.empty:
            return None

        return df

    except Exception as e:
        logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
        return None
```

**ورودی:** نماد (`BTCUSDT`) و تایم‌فریم (`1h`)
**خروجی:** DataFrame با ستون‌های `[open, high, low, close, volume, timestamp]`

#### ⚠️ نکات مهم پیاده‌سازی:

**1. Timezone Correctness (درستی منطقه زمانی):**

سیستم جدید همیشه از timezone-aware datetime استفاده می‌کند:

```python
from datetime import datetime, timezone

# ✅ درست - timezone-aware
timestamp = datetime.now(timezone.utc)
timestamp = some_datetime.astimezone(timezone.utc)

# ❌ غلط - timezone-naive (مشکل‌ساز)
timestamp = datetime.now()
```

**چرا مهم است؟**
- 🌍 سازگاری با داده‌های بین‌المللی
- ⏰ جلوگیری از اشتباهات DST (Daylight Saving Time)
- 🔄 تبدیل صحیح بین timezoneها
- 📊 مقایسه دقیق زمان‌ها

**مثال عملی:**
```python
# ذخیره زمان سیگنال ناقص
async with self.incomplete_signals_lock:
    self.incomplete_signals[symbol] = {
        'timestamp': datetime.now(timezone.utc),  # ✅ UTC
        'reason': 'insufficient_data'
    }

# بررسی کش
last_candle_time = df['timestamp'].iloc[-1].astimezone(timezone.utc)  # ✅
```

**2. Backoff Strategy (استراتژی عقب‌نشینی):**

هنگام بروز خطا در دریافت داده، سیستم به صورت هوشمند تلاش مجدد می‌کند:

```python
async def _fetch_with_retry(self, symbol: str, timeframe: str, max_retries: int = 3):
    """Fetch data with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await self._fetch_market_data(symbol, timeframe)
        except Exception as e:
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                logger.warning(
                    f"Fetch failed for {symbol} {timeframe} "
                    f"(attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {wait_time}s... Error: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Failed to fetch {symbol} {timeframe} "
                    f"after {max_retries} attempts"
                )
                return None
```

**الگوی Backoff:**
```
تلاش 1: خطا → صبر 1 ثانیه → تلاش مجدد
تلاش 2: خطا → صبر 2 ثانیه → تلاش مجدد
تلاش 3: خطا → صبر 4 ثانیه → تلاش مجدد
تلاش 4: خطا → تسلیم شدن
```

**مزایا:**
- 🔄 بازیابی خودکار از خطاهای موقت
- ⚡ کاهش فشار بر API در صورت مشکل
- 📊 افزایش قابلیت اطمینان سیستم

---

### 💾 مرحله 1.5: بررسی کش (🆕 ویژگی جدید)

**محل:** `orchestrator.py:295-315`

یکی از **بهبودهای اصلی** سیستم جدید، استفاده از کش برای جلوگیری از محاسبات تکراری است.

```python
# آیا باید دوباره محاسبه کنیم یا از کش استفاده کنیم؟
should_recalc, reason = self.tf_score_cache.should_recalculate(
    symbol, timeframe, df
)

if not should_recalc:
    # کش معتبر است - استفاده از امتیاز کش شده
    logger.info(
        f"  💾 Using CACHED score for {symbol} {timeframe} "
        f"(reason: {reason}) - Skipping recalculation"
    )
    cached_signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
    if cached_signal:
        return cached_signal

# کندل جدید آمده یا کش invalid است - محاسبه مجدد
logger.info(
    f"  🔄 RECALCULATING score for {symbol} {timeframe} "
    f"(reason: {reason})"
)
```

**🔧 پیاده‌سازی:** `signal_generation/timeframe_score_cache.py`

**لاگ نمونه:**
```
  💾 Using CACHED score for BTCUSDT 1h (reason: same_candle) - Skipping recalculation
```
یا
```
  🔄 RECALCULATING score for BTCUSDT 1h (reason: new_candle_detected)
```

**مزایا:**
- ✅ **30-40% افزایش سرعت** در صورت عدم تغییر کندل
- ✅ کاهش مصرف CPU
- ✅ کاهش تعداد فراخوانی اندیکاتورها

---

### 📦 مرحله 2: ایجاد Context

**محل:** `orchestrator.py:317-324`

```python
logger.info(f"[2/7] Creating context for {symbol}")

context = AnalysisContext(
    symbol=symbol,
    timeframe=timeframe,
    df=df
)
```

**🔧 کلاس AnalysisContext:** `signal_generation/context.py`

`AnalysisContext` یک **ظرف داده** است که:
- اطلاعات نماد، تایم‌فریم، و DataFrame را نگه می‌دارد
- نتایج Analyzers را ذخیره می‌کند
- اندیکاتورها را نگه می‌دارد
- metadata اضافی را ذخیره می‌کند

**ساختار:**
```python
@dataclass
class AnalysisContext:
    symbol: str
    timeframe: str
    df: pd.DataFrame

    # اندیکاتورها (بعد از مرحله 3 پر می‌شوند)
    indicators: Dict[str, Any] = field(default_factory=dict)

    # نتایج Analyzers (بعد از مرحله 4 پر می‌شوند)
    results: Dict[str, Any] = field(default_factory=dict)

    # metadata اضافی
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

### 📈 مرحله 3: محاسبه اندیکاتورها

**محل:** `orchestrator.py:326-336`

```python
logger.info(f"[3/7] Calculating indicators for {symbol}")

success = self._calculate_indicators(context)

if not success:
    logger.error(f"Failed to calculate indicators for {symbol}")
    return None

logger.info(f"  ✓ Indicators calculated")
```

**متد محاسبه:** `orchestrator.py:517-526`

```python
def _calculate_indicators(self, context: AnalysisContext) -> bool:
    """Calculate all indicators using IndicatorCalculator."""
    try:
        # 🆕 استفاده از IndicatorCalculator برای محاسبه یکباره
        context.indicators = self.indicator_calculator.calculate_all(context.df)
        return True

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}", exc_info=True)
        return False
```

**🔧 پیاده‌سازی:** `signal_generation/shared/indicator_calculator.py`

`IndicatorCalculator` همه اندیکاتورها را **یکباره** محاسبه می‌کند:

```python
def calculate_all(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    محاسبه یکباره همه اندیکاتورها.

    Returns:
        Dict با کلیدهای:
        - 'ema': {20, 50, 100, 200}
        - 'sma': {20, 50, 100, 200}
        - 'rsi': {14}
        - 'macd': {fast=12, slow=26, signal=9}
        - 'bbands': {period=20, std=2}
        - 'atr': {14}
        - 'adx': {14}
        - 'stoch': {k=14, d=3}
        - 'obv': {}
    """
```

**مزایا نسبت به سیستم قدیم:**
- ✅ **محاسبه یکباره** به جای محاسبات تکراری
- ✅ **30-40% بهبود عملکرد**
- ✅ کد تمیزتر و قابل نگهداری

**در سیستم قدیم:**
هر Analyzer اندیکاتور مورد نیاز خود را جداگانه محاسبه می‌کرد → تکرار محاسبات

**در سیستم جدید:**
همه اندیکاتورها یکبار محاسبه می‌شوند → همه Analyzers از همان نتایج استفاده می‌کنند

---

### 🌍 مرحله 3.5: تشخیص رژیم بازار (🆕 ویژگی جدید)

**محل:** `orchestrator.py:339-351`

```python
logger.info(f"[3.5/7] Detecting market regime for {symbol}")

regime_info = {'regime': 'unknown', 'confidence': 0.0}

if self.regime_detector.enabled:
    regime_info = self.regime_detector.detect_regime(context.df)
    logger.info(
        f"  ✓ Regime: {regime_info.get('regime')}, "
        f"Confidence: {regime_info.get('confidence', 0):.2f}"
    )

    # Store in context for analyzers to use
    context.metadata['regime_info'] = regime_info
```

**🔧 پیاده‌سازی:** `signal_generation/systems/market_regime_detector.py`

**انواع رژیم‌های بازار:**

| رژیم | توضیح | استراتژی مناسب |
|------|-------|----------------|
| `trending_bullish` | روند صعودی قوی | Trend Following |
| `trending_bearish` | روند نزولی قوی | Trend Following |
| `ranging` | محدوده (Range) | Mean Reversion |
| `volatile` | نوسان بالا | کاهش حجم معامله |
| `low_volatility` | نوسان پایین | صبر برای شکست |
| `breakout` | شکست محدوده | ورود سریع |
| `unknown` | نامشخص | احتیاط |

**لاگ نمونه:**
```
  ✓ Regime: trending_bullish, Confidence: 0.85
```

**تأثیر بر سیگنال:**
- رژیم بازار در **امتیازدهی نهایی** (مرحله 6) استفاده می‌شود
- Analyzers می‌توانند بر اساس رژیم، تحلیل خود را تنظیم کنند

---

### 📊 مرحله 4: اجرای Analyzers

**محل:** `orchestrator.py:354-368`

```python
logger.info(f"[4/7] Running {len(self.analyzers)} analyzers for {symbol}")

self._run_analyzers(context)

# Check minimum required analyzers
required = ['trend', 'momentum', 'volume']
missing = [r for r in required if not context.get_result(r)]

if missing:
    logger.warning(f"Missing required analyzers for {symbol}: {missing}")
    return None

logger.info(f"  ✓ All analyzers completed")
```

**متد اجرای Analyzers:** `orchestrator.py:528-535`

```python
def _run_analyzers(self, context: AnalysisContext) -> None:
    """Run all enabled analyzers."""
    for analyzer_name, analyzer in self.analyzers.items():
        try:
            analyzer.analyze(context)
            logger.debug(f"  ✓ {analyzer_name} completed")
        except Exception as e:
            logger.error(f"  ✗ {analyzer_name} failed: {e}", exc_info=True)
```

**🔧 لیست 11 Analyzer:**

1. **TrendAnalyzer** - تحلیل روند
2. **MomentumAnalyzer** - تحلیل مومنتوم
3. **VolumeAnalyzer** - تحلیل حجم
4. **VolumePatternAnalyzer** - الگوهای حجم 🆕
5. **PatternAnalyzer** - الگوهای کندلی و چارت
6. **SRAnalyzer** - سطوح حمایت/مقاومت
7. **VolatilityAnalyzer** - نوسان
8. **HarmonicAnalyzer** - الگوهای هارمونیک
9. **ChannelAnalyzer** - کانال‌ها
10. **CyclicalAnalyzer** - چرخه‌های بازار
11. **HTFAnalyzer** - تحلیل تایم‌فریم بالاتر

**لاگ نمونه:**
```
  ✓ trend completed
  ✓ momentum completed
  ✓ volume completed
  ✓ patterns completed
  ...
```

---

### 2.2 جزئیات Analyzers (خلاصه)

هر Analyzer از کلاس `BaseAnalyzer` ارث‌بری می‌کند و الگوی مشترکی دارد:

**الگوی استاندارد:**
```python
class SomeAnalyzer(BaseAnalyzer):
    def analyze(self, context: AnalysisContext) -> None:
        # 1. بررسی فعال بودن
        if not self._check_enabled():
            return

        # 2. اعتبارسنجی داده‌ها
        if not self._validate_context(context):
            return

        # 3. انجام تحلیل
        result = self._perform_analysis(context)

        # 4. ذخیره نتیجه
        context.add_result('analyzer_name', result)
```

#### 2.2.1 TrendAnalyzer (تحلیل روند)

**محل:** `signal_generation/analyzers/trend_analyzer.py`

**ورودی:**
- اندیکاتورها: `ema_20`, `ema_50`, `ema_100` (فقط EMA، نه SMA)
- قیمت فعلی: `close`

**📌 نکته:** TrendAnalyzer فقط از **EMAs** استفاده می‌کند، نه SMAها. SMAs توسط IndicatorCalculator محاسبه می‌شوند اما در این analyzer استفاده نمی‌شوند.

**خروجی:**
```python
{
    'status': 'ok',
    'direction': 'bullish' | 'bearish' | 'sideways' | 'neutral',
    'strength': int (1 to 3),  # قدرت ترند
    'phase': 'early' | 'developing' | 'mature' | 'late' | 'pullback' | 'transition' | 'undefined',
    'ema_alignment': 'bullish_aligned' | 'bearish_aligned' | 'neutral',
    'price_position': 'above_all_emas' | 'below_all_emas' | ...,
    'ema_slopes': {
        'ema20': float,
        'ema50': float,
        'ema100': float
    },
    'confidence': float (0-1),
    'details': {
        'close': float,
        'ema20': float,
        'ema50': float,
        'ema100': float
    }
}
```

**نحوه تشخیص:**
- مقایسه قیمت با EMA های مختلف
- محاسبه شیب (slope) EMA ها
- تعیین چیدمان (alignment) EMA ها
- **🆕 تشخیص فاز روند (7 فاز)**

**منطق کلی:**
```
قیمت > EMA20 > EMA50 > EMA100 → ترند صعودی قوی ✅✅✅
قیمت < EMA20 < EMA50 < EMA100 → ترند نزولی قوی 🔴🔴🔴
سایر حالات → ترند ضعیف یا رنج
```

---

##### 🎯 7 فاز ترند (Trend Phases)

TrendAnalyzer علاوه بر جهت و قدرت، **فاز ترند** را نیز تشخیص می‌دهد:

**جدول 7 فاز:**

| Phase | شرایط | توضیح | مناسب معامله |
|-------|-------|-------|--------------|
| **early** | ترند تازه شروع | قیمت تازه از EMA20 عبور کرده | ✅ بهترین نقطه ورود |
| **developing** | ترند در حال توسعه | قیمت > EMA20، EMA20 در حال صعود | ✅ خوب |
| **mature** | ترند بالغ و قوی | همه EMAs مرتب، شیب مثبت | ✅ قابل اعتماد |
| **late** | مراحل پایانی | ترند طولانی، احتمال خستگی | ⚠️ احتیاط |
| **pullback** | اصلاح در روند | قیمت به EMA برگشته | 💡 فرصت ورود مجدد |
| **transition** | در حال تغییر | EMAs در حال کراس | ❌ انتظار |
| **undefined** | نامشخص | رنج یا بی‌روند | ❌ اجتناب |

**کد تشخیص فاز:**
```python
def _determine_trend_phase(self, close: float, ema20: float, ema50: float,
                          ema100: float, slopes: dict) -> str:
    """تشخیص فاز ترند."""

    # محاسبه فاصله قیمت از EMAs
    dist_from_ema20 = (close - ema20) / ema20 * 100
    dist_from_ema50 = (close - ema50) / ema50 * 100

    # بررسی جهت شیب‌ها
    ema20_rising = slopes['ema20'] > 0.0005
    ema50_rising = slopes['ema50'] > 0.0003

    # تشخیص فاز
    if abs(dist_from_ema20) < 0.5:
        return 'early'  # نزدیک EMA20
    elif ema20_rising and ema50_rising and dist_from_ema20 > 1.0:
        return 'mature'  # ترند بالغ
    elif dist_from_ema50 > 5.0:
        return 'late'  # فاصله زیاد از EMA50
    elif dist_from_ema20 < 2.0 and dist_from_ema50 > 0:
        return 'pullback'  # اصلاح
    elif not ema20_rising and not ema50_rising:
        return 'transition'  # تغییر روند
    else:
        return 'developing'  # در حال توسعه
```

**مثال عملی:**

**حالت 1: Early Phase (فاز اولیه)**
```
قیمت: 50100
EMA20: 50000
EMA50: 49500
EMA100: 49000

→ direction: 'bullish'
→ strength: 1
→ phase: 'early'  ← قیمت تازه از EMA20 عبور کرده
→ تفسیر: بهترین نقطه ورود! ✅
```

**حالت 2: Mature Phase (فاز بالغ)**
```
قیمت: 51000
EMA20: 50000
EMA50: 49500
EMA100: 49000
همه شیب‌ها مثبت

→ direction: 'bullish'
→ strength: 3
→ phase: 'mature'  ← ترند قوی و پایدار
→ تفسیر: ترند قابل اعتماد ✅✅✅
```

**حالت 3: Late Phase (فاز پایانی)**
```
قیمت: 52500  ← خیلی بالاتر از EMAs
EMA20: 50000
EMA50: 49500
EMA100: 49000

→ direction: 'bullish'
→ strength: 2
→ phase: 'late'  ← فاصله زیاد، احتمال اصلاح
→ تفسیر: احتیاط! ممکن است اصلاح نزدیک باشد ⚠️
```

**حالت 4: Pullback Phase (اصلاح)**
```
قیمت: 50200  ← برگشته به EMA20
EMA20: 50000
EMA50: 49500
EMA100: 49000

→ direction: 'bullish'
→ strength: 2
→ phase: 'pullback'  ← اصلاح سالم
→ تفسیر: فرصت ورود مجدد در روند صعودی 💡
```

---

#### 2.2.2 MomentumAnalyzer (تحلیل مومنتوم)

**محل:** `signal_generation/analyzers/momentum_analyzer.py`

**ورودی:**
- اندیکاتورها: `rsi`, `macd`, `macd_signal`, `macd_hist`, `stochastic`, `ema_20`, `ema_50`
- قیمت: `close`

**خروجی:**
```python
{
    'direction': 'bullish' | 'bearish' | 'neutral',
    'strength': float (0-3),
    'rsi_analysis': {...},
    'macd_analysis': {...},
    'macd_market_type': 'A_bullish_strong' | 'B_bullish_normal' | ...,  # ✨ جدید
    'advanced_macd_signals': [...],  # ✨ جدید
    'stoch_analysis': {...},
    'divergence': {...},
    'mfi_analysis': {...},  # optional
    'confidence': float (0-1)
}
```

**شاخص‌های بررسی:**
- **RSI**: سطوح oversold/overbought، واگرایی
- **MACD**: تقاطع، هیستوگرام، سیگنال
- **Stochastic**: تقاطع K و D، سطوح اشباع
- **🆕 MACD Market Type Detection**: تشخیص 5 نوع بازار
- **🆕 Advanced MACD Signals**: سیگنال‌های پیشرفته MACD
- **MFI** (optional): Money Flow Index

---

##### 🎯 ویژگی کلیدی: 5 MACD Market Types

یکی از مهم‌ترین ویژگی‌های MomentumAnalyzer، **تشخیص نوع بازار** بر اساس ترکیب MACD و EMA است:

**منطق:** ترکیب 3 فاکتور:
1. **DIF (MACD Line):** بالای/پایین صفر
2. **HIST (Histogram):** مثبت/منفی
3. **EMA Alignment:** EMA20 > EMA50 یا EMA20 < EMA50

**جدول 5 Market Type:**

| Market Type | DIF | HIST | EMA Alignment | شرح | کیفیت سیگنال |
|-------------|-----|------|---------------|-----|---------------|
| **A_bullish_strong** | > 0 | > 0 | EMA20 > EMA50 | صعودی قوی | ✅✅✅ بهترین |
| **B_bullish_normal** | > 0 | < 0 | EMA20 > EMA50 | صعودی عادی | ⚠️ متوسط |
| **C_bearish_strong** | < 0 | < 0 | EMA20 < EMA50 | نزولی قوی | 🔴🔴🔴 قوی |
| **D_bearish_normal** | < 0 | > 0 | EMA20 < EMA50 | نزولی عادی | ⚠️ متوسط |
| **X_transition** | مختلط | مختلط | - | انتقال | ❌ اجتناب |

**کد تشخیص:**
```python
def _detect_macd_market_type(self, df: pd.DataFrame) -> str:
    curr_dif = df['macd'].iloc[-1]
    curr_hist = df['macd_hist'].iloc[-1]

    curr_ema20 = df['ema_20'].iloc[-1]
    curr_ema50 = df['ema_50'].iloc[-1]
    ema_bullish = curr_ema20 > curr_ema50

    if curr_dif > 0 and curr_hist > 0 and ema_bullish:
        return "A_bullish_strong"
    elif curr_dif > 0 and curr_hist < 0 and ema_bullish:
        return "B_bullish_normal"
    elif curr_dif < 0 and curr_hist < 0 and not ema_bullish:
        return "C_bearish_strong"
    elif curr_dif < 0 and curr_hist > 0 and not ema_bullish:
        return "D_bearish_normal"
    else:
        return "X_transition"
```

**مثال عملی:**
```
Market Type = A_bullish_strong:
  DIF = 0.0025 (مثبت ✅)
  HIST = 0.0008 (مثبت ✅)
  EMA20 = 50000, EMA50 = 49500 (EMA20 > EMA50 ✅)

→ بهترین شرایط برای سیگنال خرید!
```

---

##### 🔍 Advanced MACD Signals

سیستم سیگنال‌های پیشرفته‌ای از MACD استخراج می‌کند:

**1. DIF Zero Crosses:**
- **First Zero Cross**: اولین عبور DIF از صفر (سیگنال قوی‌تر)
- **Second Zero Cross**: دومین عبور (تأیید روند)

**2. DIF Trendline Breaks:**
- شکست خطوط روند در DIF
- نشان‌دهنده تغییر احتمالی روند

**3. Histogram Patterns:**
- الگوهای پیشرفته در هیستوگرام MACD
- تشخیص واگرایی‌های پنهان

---

#### 2.2.3 VolumeAnalyzer (تحلیل حجم)

**محل:** `signal_generation/analyzers/volume_analyzer.py`

**ورودی:**
- حجم: `volume`, `volume_sma`
- اندیکاتور: `obv` (On-Balance Volume)
- Context: `trend`, `momentum` (برای اعتبارسنجی)

**خروجی:**
```python
{
    'is_confirmed': bool,  # آیا حجم حرکت قیمت را تأیید می‌کند؟
    'volume_trend': 'increasing' | 'decreasing' | 'stable',
    'volume_ratio': float,  # نسبت به میانگین
    'volume_pattern': 'spike' | 'increasing' | 'decreasing' | ...,  # ✨ 6 الگو
    'breakout_volume': bool,  # آیا breakout است؟
    'obv_trend': 'bullish' | 'bearish' | 'neutral',
    'strength': float (0-3),
    'context_validated': bool,  # ✨ اعتبارسنجی با Trend/Momentum
    'validation_details': {...},
    'confidence': float (0-1)
}
```

**ویژگی‌های کلیدی:**
- **6 Volume Patterns**: طبقه‌بندی الگوی حجم
- **Context-Aware Validation**: هماهنگی با Trend و Momentum
- **Breakout Detection**: تشخیص حجم شکست
- **OBV Analysis**: تحلیل On-Balance Volume

---

##### 📊 6 الگوی حجم (Volume Patterns)

سیستم حجم را به **6 الگو** طبقه‌بندی می‌کند:

**جدول الگوهای حجم:**

| Pattern | شرایط | Volume Ratio | توضیح | اهمیت |
|---------|-------|--------------|-------|--------|
| **spike** | حجم بسیار بالا | > 2.0 | حجم غیرعادی (spike) | ⚡ خیلی بالا |
| **breakout** | حجم بالا + شکست | > 1.5 | شکست سطح با حجم | 🚀 بالا |
| **increasing** | روند صعودی | > 1.2 | حجم در حال افزایش | ✅ متوسط |
| **decreasing** | روند نزولی | < 0.8 | حجم در حال کاهش | ⚠️ متوسط |
| **low** | حجم پایین | < 0.6 | حجم ضعیف | 🔻 پایین |
| **normal** | حجم معمولی | 0.8-1.2 | حجم عادی | ➡️ عادی |

**فرمول محاسبه Volume Ratio:**
```python
volume_ratio = current_volume / volume_sma_20
```

**کد تشخیص الگو:**
```python
def _classify_volume_pattern(self, volume_ratio: float, trend: str) -> str:
    """طبقه‌بندی الگوی حجم."""

    if volume_ratio > 2.0:
        return 'spike'  # حجم غیرعادی بالا
    elif volume_ratio > 1.5:
        return 'breakout'  # احتمال شکست
    elif volume_ratio > 1.2 and trend == 'increasing':
        return 'increasing'  # افزایش تدریجی
    elif volume_ratio < 0.6:
        return 'low'  # حجم خیلی پایین
    elif volume_ratio < 0.8 and trend == 'decreasing':
        return 'decreasing'  # کاهش تدریجی
    else:
        return 'normal'  # حجم عادی
```

**مثال عملی:**
```
current_volume = 2500
volume_sma_20 = 1000

→ volume_ratio = 2500 / 1000 = 2.5
→ volume_pattern = 'spike'
→ تفسیر: حجم غیرعادی بالا، توجه ویژه به حرکت قیمت! ⚡
```

---

##### 🔄 Context-Aware Validation

VolumeAnalyzer نتایج خود را با Trend و Momentum **هماهنگ** می‌کند:

**قانون:**
```
قیمت ↑ (Trend=bullish) + حجم بالا → تأیید صعود ✅✅✅
قیمت ↑ (Trend=bullish) + حجم پایین → صعود ضعیف ⚠️

قیمت ↓ (Trend=bearish) + حجم بالا → تأیید نزول 🔴🔴🔴
قیمت ↓ (Trend=bearish) + حجم پایین → نزول ضعیف ⚠️
```

**کد اعتبارسنجی:**
```python
def _validate_with_context(self, context: AnalysisContext) -> Dict:
    """اعتبارسنجی حجم با Trend و Momentum."""

    trend_result = context.get_result('trend')
    momentum_result = context.get_result('momentum')

    trend_dir = trend_result.get('direction', 'neutral')
    momentum_dir = momentum_result.get('direction', 'neutral')

    # بررسی همسویی
    if self.volume_trend == 'increasing':
        if trend_dir == 'bullish' and momentum_dir == 'bullish':
            return {'validated': True, 'reason': 'volume_confirms_uptrend'}
        elif trend_dir == 'bearish':
            return {'validated': False, 'reason': 'volume_contradicts_trend'}

    # ... بررسی سایر حالات
```

**نحوه تأیید حجم:**
- حجم بالاتر از میانگین 20 روزه
- همراستایی OBV با قیمت
- افزایش حجم در جهت حرکت
- **🆕 هماهنگی با جهت Trend**
- **🆕 هماهنگی با جهت Momentum**

---

#### 2.2.4 PatternAnalyzer (تحلیل الگوها)

**محل:** `signal_generation/analyzers/pattern_analyzer.py`

**ورودی:**
- داده‌های OHLC

**خروجی:**
```python
{
    'candlestick_patterns': [
        {
            'name': 'hammer',
            'direction': 'bullish',
            'strength': 0.8,
            'position': 145  # index
        },
        ...
    ],
    'chart_patterns': [
        {
            'name': 'double_bottom',
            'direction': 'bullish',
            'strength': 0.9,
            'breakout_confirmed': True
        },
        ...
    ]
}
```

**الگوهای پشتیبانی شده:**

**الگوهای کندلی (Candlestick):**
- Hammer, Shooting Star
- Engulfing (Bullish/Bearish)
- Doji, Dragonfly, Gravestone
- Morning Star, Evening Star
- Three White Soldiers, Three Black Crows
- و 20+ الگوی دیگر...

**الگوهای چارت (Chart):**
- Head & Shoulders
- Double Top/Bottom
- Triangle (Ascending, Descending, Symmetrical)
- Wedge (Rising, Falling)

---

#### 2.2.5 SRAnalyzer (سطوح حمایت و مقاومت)

**محل:** `signal_generation/analyzers/sr_analyzer.py`

**ورودی:**
- قیمت‌های High, Low, Close
- حجم

**خروجی:**
```python
{
    'support_levels': [49000, 48500, 48000],
    'resistance_levels': [51000, 51500, 52000],
    'nearest_support': 49500,
    'nearest_resistance': 51000,
    'at_support': bool,
    'at_resistance': bool,
    'quality_score': float (0-1)
}
```

---

#### 2.2.6 سایر Analyzers (خلاصه)

**VolatilityAnalyzer:**
- بررسی ATR، Bollinger Bands
- تشخیص نوسان بالا/پایین
- محاسبه expansion/contraction

**HarmonicAnalyzer:**
- الگوهای Gartley، Butterfly، Bat، Crab
- نسبت‌های فیبوناچی

**ChannelAnalyzer:**
- کانال‌های صعودی/نزولی
- شکست کانال

**CyclicalAnalyzer:**
- چرخه‌های بازار
- الگوهای فصلی

**HTFAnalyzer:**
- تحلیل تایم‌فریم بالاتر
- همراستایی روندها

**VolumePatternAnalyzer:** 🆕
- الگوهای خاص حجم
- Climax، Exhaustion

---

### 🎯 مرحله 5: تعیین جهت سیگنال

**محل:** `orchestrator.py:370-379`

```python
logger.info(f"[5/7] Determining signal direction for {symbol}")

direction = self._determine_direction(context)

if not direction:
    logger.info(f"No clear direction for {symbol}")
    return None

logger.info(f"  ✓ Direction: {direction}")
```

**متد تعیین جهت:** `orchestrator.py:537-615`

```python
def _determine_direction(self, context: AnalysisContext) -> Optional[str]:
    """
    Determine signal direction from analyzer results.

    Returns:
        'LONG', 'SHORT', or None
    """
    bullish_score = 0
    bearish_score = 0

    # 1. Trend (weight 3x)
    trend_result = context.get_result('trend')
    if trend_result:
        direction = trend_result.get('direction', 'neutral')
        strength = abs(trend_result.get('strength', 0))

        if direction in ['bullish', 'bullish_aligned']:
            bullish_score += strength * 3
        elif direction in ['bearish', 'bearish_aligned']:
            bearish_score += strength * 3

    # 2. Momentum (weight 2x)
    momentum_result = context.get_result('momentum')
    if momentum_result:
        direction = momentum_result.get('direction', 'neutral')
        strength = abs(momentum_result.get('strength', 0))

        if direction == 'bullish':
            bullish_score += strength * 2
        elif direction == 'bearish':
            bearish_score += strength * 2

    # 3. Volume confirmation (bonus +1)
    volume_result = context.get_result('volume')
    if volume_result and volume_result.get('is_confirmed'):
        if bullish_score > bearish_score:
            bullish_score += 1
        elif bearish_score > bullish_score:
            bearish_score += 1

    # 4. Patterns (weight 0.5x each)
    pattern_result = context.get_result('patterns')
    if pattern_result:
        patterns = (
            pattern_result.get('candlestick_patterns', []) +
            pattern_result.get('chart_patterns', [])
        )

        for pattern in patterns:
            p_dir = pattern.get('direction', 'neutral')
            p_str = pattern.get('adjusted_strength', 0)

            if p_dir == 'bullish':
                bullish_score += p_str * 0.5
            elif p_dir == 'bearish':
                bearish_score += p_str * 0.5

    # 5. HTF alignment (bonus +2)
    htf_result = context.get_result('htf')
    if htf_result and htf_result.get('alignment'):
        htf_trend = htf_result.get('htf_trend', 'neutral')

        if htf_trend == 'bullish':
            bullish_score += 2
        elif htf_trend == 'bearish':
            bearish_score += 2

    logger.debug(
        f"Direction scores: Bullish={bullish_score:.1f}, "
        f"Bearish={bearish_score:.1f}"
    )

    # Require 1.2x dominance
    if bullish_score > bearish_score * 1.2:
        return 'LONG'
    elif bearish_score > bullish_score * 1.2:
        return 'SHORT'
    else:
        return None
```

**الگوریتم تعیین جهت:**

1. **جمع‌آوری امتیازات:**
   - Trend × 3 (مهم‌ترین)
   - Momentum × 2
   - Volume تأیید: +1
   - Patterns × 0.5
   - HTF alignment: +2

2. **شرط تصمیم:**
   - باید یک جهت **1.2 برابر** قوی‌تر از جهت دیگر باشد
   - اگر نه → بدون جهت واضح

**مثال:**
```
Trend: bullish (strength=3) → +9 bullish
Momentum: bullish (strength=2) → +4 bullish
Volume: confirmed → +1 bullish
Patterns: 2 bullish (avg=0.7) → +0.7 bullish
HTF: bullish → +2 bullish
────────────────────────
Total: Bullish=16.7, Bearish=0

16.7 > 0 × 1.2 → جهت: LONG ✅
```

---

### ⭐ مرحله 6: امتیازدهی سیگنال

**محل:** `orchestrator.py:381-404`

```python
logger.info(f"[6/7] Scoring signal for {symbol} {direction}")

score = self.signal_scorer.calculate_score(context, direction)

if not score:
    logger.warning(f"Failed to calculate score for {symbol}")
    return None

logger.info(
    f"  ✓ Score: {score.final_score:.2f} "
    f"({score.signal_strength}, conf={score.confidence:.2f})"
)
```

**🔧 کلاس SignalScorer:** `signal_generation/signal_scorer.py`

#### 6.1 فرآیند امتیازدهی (12 مرحله)

**متد اصلی:** `signal_scorer.py:95-184`

```python
def calculate_score(
    self,
    context: AnalysisContext,
    direction: str
) -> Optional[SignalScore]:
    """Calculate signal score from analysis context."""

    # 1. Create score object
    score = SignalScore()

    # 2. Calculate base scores from each analyzer
    self._calculate_base_scores(score, context, direction)

    # 3. Apply weights (with per-TF support)
    self._apply_weights(score, context.timeframe)

    # 4. Calculate confluence bonus
    self._calculate_confluence(score, context, direction)

    # 5. Apply timeframe weight
    self._apply_timeframe_weight(score, context.timeframe)

    # 6. Apply HTF multiplier
    self._apply_htf_multiplier(score, context, direction)

    # 7. Apply volatility adjustment
    self._apply_volatility_adjustment(score, context)

    # 8. Apply trend alignment multiplier
    self._apply_trend_alignment(score, context, direction)

    # 9. Apply volume confirmation multiplier
    self._apply_volume_confirmation(score, context, direction)

    # 10. Apply pattern quality multiplier
    self._apply_pattern_quality(score, context)

    # 11. Apply MACD analysis score multiplier
    self._apply_macd_quality(score, context, direction)

    # 12. Finalize score
    self._finalize_score(score)

    return score
```

---

#### 🎯 فرمول امتیازدهی (Multiplicative Formula)

**⚠️ تفاوت کلیدی با سیستم قدیم:** فرمول امتیازدهی **ضربی** است، نه جمعی!

**فرمول کامل:**

```python
final_score = base_score
             × (1.0 + confluence_bonus)       # 1.0-1.5
             × timeframe_weight               # 0.7-1.2
             × trend_alignment                # 0.8-1.2
             × volume_confirmation            # 1.0 or 1.1
             × pattern_quality                # 1.0-1.5
             × macd_analysis_score            # 0.85-1.15
             × htf_multiplier                 # 0.7-1.3
             × volatility_multiplier          # 0.6-1.5

# ✨ سپس در Orchestrator (بعد از Scoring):
if correlation_factor < 0.7:
    final_score *= correlation_factor  # کاهش امتیاز در صورت همبستگی بالا
```

**چرا ضربی؟**
- ✅ تأثیر هم‌افزایی بهتر: وقتی همه فاکتورها قوی باشند، امتیاز نهایی بسیار بالا می‌رود
- ✅ جریمه بیشتر برای ضعف: اگر یک فاکتور ضعیف باشد (مثلاً 0.8)، کل امتیاز کاهش می‌یابد
- ✅ واقع‌گرایانه‌تر: بازارها به صورت غیرخطی عمل می‌کنند

**مثال عملی:**

```python
# فرض کنید:
base_score = 75
confluence_bonus = 0.3  # +30%
timeframe_weight = 1.0  # 1h
trend_alignment = 1.2   # Perfect alignment
volume_confirmation = 1.1  # Confirmed
pattern_quality = 1.2   # 2 patterns
macd_analysis_score = 1.15  # Good
htf_multiplier = 1.3    # HTF aligned
volatility_multiplier = 1.0  # Normal

# محاسبه:
final_score = 75 × 1.3 × 1.0 × 1.2 × 1.1 × 1.2 × 1.15 × 1.3 × 1.0
            = 75 × 2.84
            = 213  # ← خیلی بالاست!

# محدود شدن به 100:
final_score = min(100, 213) = 100  # ✅ very_strong
```

#### 6.2 وزن‌های پیش‌فرض Analyzers

**محل:** `signal_scorer.py:41-52`

```python
DEFAULT_WEIGHTS = {
    'trend': 0.30,          # 30% - مهم‌ترین
    'momentum': 0.25,       # 25%
    'volume': 0.20,         # 20%
    'patterns': 0.10,       # 10%
    'support_resistance': 0.08,  # 8%
    'volatility': 0.05,     # 5%
    'harmonic': 0.01,       # 1%
    'channel': 0.005,       # 0.5%
    'cyclical': 0.003,      # 0.3%
    'htf': 0.002            # 0.2%
}
```

#### 6.3 وزن‌های تایم‌فریم

**محل:** `signal_scorer.py:54-60`

```python
DEFAULT_TIMEFRAME_WEIGHTS = {
    '5m': 0.7,      # -30% اهمیت
    '15m': 0.85,    # -15% اهمیت
    '1h': 1.0,      # مرجع
    '4h': 1.2       # +20% اهمیت
}
```

**معنی:**
- سیگنال 4h → امتیاز × 1.2
- سیگنال 1h → امتیاز × 1.0
- سیگنال 15m → امتیاز × 0.85
- سیگنال 5m → امتیاز × 0.7

#### 6.4 Confluence Bonus (پاداش همگرایی)

**🎯 ترکیب دو روش:**

Confluence Bonus از **2 جزء** تشکیل شده است:

**1. Alignment Bonus (هم‌راستایی Analyzers):**

```python
aligned_count = 0
# بررسی 5 analyzer کلیدی:
if trend_aligned: aligned_count += 1
if momentum_aligned: aligned_count += 1
if volume_confirmed: aligned_count += 1
if patterns_aligned: aligned_count += 1
if htf_aligned: aligned_count += 1

alignment_bonus = (aligned_count / 5) * 0.25  # Max 0.25
```

**2. Risk/Reward Bonus:**

```python
if risk_reward_ratio >= 2.0:
    rr_bonus = min(0.25, (risk_reward_ratio - 2.0) * 0.125)
else:
    rr_bonus = 0
```

**محاسبه کلی:**

```python
confluence_bonus = min(0.5, alignment_bonus + rr_bonus)  # Max 0.5
```

**مثال کامل:**

```python
# ─── Alignment ───
aligned_count = 4  # (Trend, Momentum, Volume, HTF همراستا، Patterns خنثی)
alignment_bonus = (4/5) × 0.25 = 0.20

# ─── Risk/Reward ───
risk_reward_ratio = 3.0  # نسبت سود به ضرر
rr_bonus = (3.0 - 2.0) × 0.125 = 0.125

# ─── کل ───
confluence_bonus = 0.20 + 0.125 = 0.325  # +32.5%

# ─── اعمال به base_score ───
# در فرمول ضربی: base_score × (1.0 + 0.325) = base_score × 1.325
```

**نکات:**
- ✅ حداکثر Alignment Bonus: 0.25 (همه 5 analyzer همراستا)
- ✅ حداکثر RR Bonus: 0.25 (RR بالای 4.0)
- ✅ حداکثر کل Confluence: 0.5 (+50%)
- 🎯 هر دو جزء مستقل هستند و با هم جمع می‌شوند

---

#### 🎵 MACD Analysis Score Multiplier

**محل:** `signal_scorer.py:766-811`

**دامنه:** 0.85 - 1.2

این multiplier بر اساس هماهنگی بین MACD و Momentum analyzer محاسبه می‌شود:

```python
macd_direction = macd_signal.get('direction')  # از momentum_result
mom_direction = momentum_result.get('direction')

if macd_direction == mom_direction and macd_direction != 'neutral':
    macd_analysis_score = 1.2  # Good alignment (حداکثر) ✅
elif macd_direction == 'neutral':
    macd_analysis_score = 1.0  # Neutral ➡️
else:
    macd_analysis_score = 0.85  # Disagreement (حداقل) ⚠️
```

**مثال:**

```python
# حالت 1: هماهنگی کامل
macd_direction = 'bullish'
mom_direction = 'bullish'
→ macd_analysis_score = 1.2  # +20% بونوس

# حالت 2: MACD خنثی
macd_direction = 'neutral'
→ macd_analysis_score = 1.0  # بدون تأثیر

# حالت 3: تضاد
macd_direction = 'bearish'
mom_direction = 'bullish'
→ macd_analysis_score = 0.85  # -15% جریمه
```

**اهمیت:**
- ✅ تأیید مومنتوم با MACD
- ⚠️ جریمه برای سیگنال‌های متناقض
- 🎯 افزایش دقت سیگنال‌ها

---

#### 📊 لاگ الگوهای تشخیص داده شده

**محل در Orchestrator:** `orchestrator.py:396-401`

بعد از محاسبه امتیاز، اگر الگوهای Price Action یا Candlestick تشخیص داده شده باشند، جزئیات آن‌ها log می‌شود:

```python
# ✨ لاگ جزئیات الگوهای تشخیص داده شده
if score.detected_patterns:
    logger.info(
        f"  📊 الگوهای تشخیص داده شده برای {symbol} {direction}:\n"
        f"{score.get_pattern_summary()}"
    )
```

**مثال خروجی لاگ:**

```log
[INFO] ✓ Score: 78.50 (STRONG, conf=0.85)
[INFO] 📊 الگوهای تشخیص داده شده برای BTCUSDT LONG:
  • Engulfing (وزن: 1.15)
  • Morning Star (وزن: 1.20)
  • Support Bounce (وزن: 1.10)
```

**مزایا:**
- 🔍 **Transparency:** مشخص می‌شود چه الگوهایی سیگنال را قوی کرده‌اند
- 📈 **Pattern Quality:** وزن هر الگو نمایش داده می‌شود
- 📝 **Debugging:** در تحلیل بعدی مشخص است کدام الگوها موفق بودند
- 🎓 **Learning:** می‌توان عملکرد الگوها را ارزیابی کرد

---

#### 6.5 خروجی SignalScore

**کلاس:** `signal_generation/signal_score.py`

```python
@dataclass
class SignalScore:
    # امتیازات پایه
    base_scores: Dict[str, float] = field(default_factory=dict)
    weighted_scores: Dict[str, float] = field(default_factory=dict)

    # امتیاز نهایی
    final_score: float = 0.0

    # اطلاعات اضافی
    signal_strength: str = 'weak'  # 'weak' | 'moderate' | 'strong' | 'very_strong'
    confidence: float = 0.0  # 0-1

    # ضرایب اعمال شده
    timeframe_weight: float = 1.0
    confluence_bonus: float = 0.0
    htf_multiplier: float = 1.0
    volatility_adjustment: float = 1.0

    # الگوهای تشخیص داده شده
    detected_patterns: List[Dict] = field(default_factory=list)

    # metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**تعیین قدرت سیگنال:**
```python
if final_score < 40:
    signal_strength = 'weak'
elif final_score < 60:
    signal_strength = 'moderate'
elif final_score < 80:
    signal_strength = 'strong'
else:
    signal_strength = 'very_strong'
```

**لاگ نمونه:**
```
  ✓ Score: 75.3 (strong, conf=0.82)
  📊 الگوهای تشخیص داده شده برای BTCUSDT LONG:
    - hammer (bullish, strength=0.85)
    - double_bottom (bullish, strength=0.92, breakout confirmed)
```

---

### ✅ مرحله 7: اعتبارسنجی سیگنال

**محل:** `orchestrator.py:431-445`

```python
logger.info(f"[7/7] Validating signal for {symbol}")

is_valid, reason = self.signal_validator.validate(signal, context)

if not is_valid:
    logger.info(f"Signal rejected for {symbol}: {reason}")
    self.stats.rejected_signals += 1

    # Track rejection reason
    if reason not in self.stats.rejection_reasons:
        self.stats.rejection_reasons[reason] = 0
    self.stats.rejection_reasons[reason] += 1

    return None
```

**🔧 کلاس SignalValidator:** `signal_generation/signal_validator.py`

#### 7.1 معیارهای اعتبارسنجی (8 بررسی)

**متد اصلی:** `signal_validator.py:109-200`

```python
def validate(
    self,
    signal: SignalInfo,
    context: AnalysisContext
) -> Tuple[bool, str]:
    """Main validation method - runs all validation checks."""

    # 1. Risk/Reward validation
    if not self._validate_risk_reward(signal):
        return False, "risk_reward_too_low"

    # 2. Score threshold
    if not self._validate_score(signal):
        return False, "score_below_minimum"

    # 3. Circuit breaker (rate limiting)
    if not self._validate_circuit_breaker(signal):
        return False, "circuit_breaker_active"

    # 4. Correlation check
    if not self._validate_correlation(signal):
        return False, "high_correlation_exposure"

    # 5. Portfolio exposure limits
    if not self._validate_portfolio_exposure(signal):
        return False, "portfolio_limit_exceeded"

    # 6. Time filters
    if not self._validate_time_filters(signal):
        return False, "time_filter_blocked"

    # 7. Symbol-specific cooldown
    if not self._validate_symbol_cooldown(signal):
        return False, "symbol_cooldown_active"

    # 8. Adaptive threshold (dynamic adjustment)
    if not self._validate_adaptive_threshold(signal):
        return False, "adaptive_threshold_not_met"

    # All checks passed
    return True, "valid"
```

#### 7.2 جزئیات هر بررسی

**1. Risk/Reward Validation:**
```python
min_rr_ratio = 1.8  # پیش‌فرض
preferred_rr_ratio = 2.5

if signal.risk_reward_ratio < min_rr_ratio:
    return False  # رد سیگنال
```

**2. Score Threshold:**
```python
minimum_signal_score = 50  # پیش‌فرض

if signal.score.final_score < minimum_signal_score:
    return False
```

**3. Circuit Breaker (Rate Limiting):**
```python
max_signals_per_hour = 3
max_signals_per_day = 10

# شمارش سیگنال‌های اخیر
recent_signals_1h = count_signals_last_hour()
recent_signals_24h = count_signals_last_day()

if recent_signals_1h >= max_signals_per_hour:
    return False, "too_many_signals_per_hour"

if recent_signals_24h >= max_signals_per_day:
    return False, "too_many_signals_per_day"
```

**4. Correlation Check:**
```python
max_correlation = 0.8

# بررسی همبستگی با موقعیت‌های فعال
for active_position in active_positions:
    correlation = calculate_correlation(signal.symbol, active_position.symbol)

    if correlation > max_correlation:
        return False, "high_correlation_with_active_position"
```

**5. Portfolio Exposure Limits:**
```python
max_total_exposure = 0.5  # 50% کل سرمایه
max_per_symbol = 0.1      # 10% برای هر نماد
max_same_direction = 0.3  # 30% در یک جهت
max_open_positions = 5

# محاسبه exposure فعلی
current_exposure = calculate_total_exposure()
long_exposure = calculate_long_exposure()
short_exposure = calculate_short_exposure()

if current_exposure + signal.position_size > max_total_exposure:
    return False, "total_exposure_exceeded"

if signal.direction == 'LONG' and long_exposure > max_same_direction:
    return False, "long_exposure_exceeded"
```

**6. Time Filters:**
```python
avoid_weekends = True
trading_hours = {'start': 0, 'end': 24}

now = datetime.now()

if avoid_weekends and now.weekday() >= 5:  # Saturday=5, Sunday=6
    return False, "weekend_trading_disabled"

if not (trading_hours['start'] <= now.hour < trading_hours['end']):
    return False, "outside_trading_hours"
```

**7. Symbol Cooldown:**
```python
cooldown_after_loss = 30  # دقیقه

last_trade = get_last_trade_for_symbol(signal.symbol)

if last_trade and last_trade.result == 'loss':
    time_since_loss = (now - last_trade.close_time).total_seconds() / 60

    if time_since_loss < cooldown_after_loss:
        return False, "symbol_cooldown_active"
```

**8. Adaptive Threshold (🆕):**

بر اساس عملکرد اخیر، حد آستانه امتیاز تنظیم می‌شود:

```python
performance_window_days = 7
good_performance_threshold = 0.6  # 60% win rate
poor_performance_threshold = 0.4  # 40% win rate

recent_performance = calculate_recent_performance(days=7)

if recent_performance.win_rate > good_performance_threshold:
    # عملکرد خوب → آستانه کمتر (قبول سیگنال‌های بیشتر)
    adjusted_threshold = minimum_signal_score * 0.9
elif recent_performance.win_rate < poor_performance_threshold:
    # عملکرد ضعیف → آستانه بیشتر (دقت بیشتر)
    adjusted_threshold = minimum_signal_score * 1.2
else:
    adjusted_threshold = minimum_signal_score

if signal.score.final_score < adjusted_threshold:
    return False, "adaptive_threshold_not_met"
```

**لاگ نمونه (رد شده):**
```
Signal rejected for ETHUSDT: risk_reward_too_low
  → RR: 1.5 < minimum 1.8
```

**لاگ نمونه (قبول شده):**
```
✅ Valid signal generated for BTCUSDT LONG! Score: 75.3, RR: 2.8
```

---

## بخش ۳: Multi-Timeframe Analysis

### 3.1 دو روش ترکیب چند تایم‌فریم

همانطور که در بخش 1.2 توضیح داده شد، سیستم جدید **دو حالت** پشتیبانی می‌کند:

#### حالت 1: Multi-TF Aggregation (سازگار با سیستم قدیم)

**محل:** `signal_generation/multi_tf_aggregator.py`

**فرآیند:**
1. تولید سیگنال برای هر تایم‌فریم (5m, 15m, 1h, 4h)
2. جمع‌آوری امتیازات با وزن تایم‌فریم
3. بررسی همراستایی روندها
4. محاسبه امتیاز ترکیبی

**فرمول:**
```python
final_score = Σ (score_tf × weight_tf) + alignment_bonus

alignment_bonus = {
    همه تایم‌فریم‌ها همراستا: +20
    اکثریت همراستا: +10
    مخالف: -15
}
```

**مثال:**
```
5m:  LONG, score=65, weight=0.7  → 45.5
15m: LONG, score=72, weight=0.85 → 61.2
1h:  LONG, score=80, weight=1.0  → 80.0
4h:  LONG, score=75, weight=1.2  → 90.0
────────────────────────────────────
Base = 276.7 / 3.75 = 73.8
Alignment = همه همراستا → +20
────────────────────────────────────
Final Score = 93.8 (very_strong)
```

#### حالت 2: Best Signal Selection (ساده‌تر)

**فرآیند:**
1. تولید سیگنال برای هر تایم‌فریم
2. انتخاب سیگنالی با بالاترین امتیاز
3. بازگشت آن سیگنال

**مثال:**
```
5m:  LONG, score=65
15m: LONG, score=72
1h:  LONG, score=80  ← بهترین
4h:  LONG, score=75
────────────────────
Selected: 1h signal (score=80)
```

**مزایا:**
- ساده‌تر و واضح‌تر
- عملکرد سریع‌تر
- کمتر پیچیده

---

### 3.2 همبستگی و مدیریت ریسک (🆕)

**محل:** `signal_generation/systems/correlation_manager.py`

قبل از قبول سیگنال، همبستگی با موقعیت‌های فعال بررسی می‌شود:

```python
if self.correlation_manager.enabled:
    correlation_factor = self.correlation_manager.get_correlation_safety_factor(
        symbol,
        direction
    )

    if correlation_factor < 0.7:
        logger.info(
            f"High correlation exposure for {symbol} "
            f"(factor: {correlation_factor:.2f}). "
            f"Reducing signal score."
        )
        # کاهش امتیاز
        score.final_score *= correlation_factor
        score.correlation_safety_factor = correlation_factor
```

**مثال:**
```
موقعیت‌های فعال: BTC/USDT LONG, ETH/USDT LONG
سیگنال جدید: LTC/USDT LONG

همبستگی BTC-LTC: 0.85 (بالا)
همبستگی ETH-LTC: 0.78 (بالا)

→ correlation_factor = 0.6
→ امتیاز سیگنال: 80 × 0.6 = 48
→ سیگنال رد می‌شود (زیر حد آستانه 50)
```

---

### 3.3 یادگیری تطبیقی (🆕)

**محل:** `signal_generation/systems/adaptive_learning_system.py`

سیستم از نتایج معاملات قبلی یاد می‌گیرد:

```python
# ثبت نتیجه معامله
self.adaptive_learning.register_trade_result(
    symbol='BTCUSDT',
    timeframe='1h',
    direction='LONG',
    patterns=['hammer', 'double_bottom'],
    result='win',  # یا 'loss'
    pnl=+2.5  # R multiple
)

# بهبود الگوها
# اگر الگوی 'hammer' در BTCUSDT 1h نتیجه خوب داد:
#   → وزن آن الگو افزایش می‌یابد
#   → در معاملات بعدی اولویت بیشتر دارد

# اگر الگوی 'shooting_star' در ETH/USDT نتیجه بد داد:
#   → وزن آن الگو کاهش می‌یابد
#   → در معاملات بعدی احتیاط بیشتر می‌شود
```

---

## خلاصه کامل جریان تولید سیگنال

### مراحل کلی:

```
1. SignalProcessor.process_symbol()
   ↓
2. Orchestrator.analyze_symbol() [Multi-TF wrapper]
   ↓
3. برای هر تایم‌فریم: generate_signal_for_symbol()
   │
   ├─ [0] Circuit Breaker Check
   ├─ [1] Fetch Data
   ├─ [1.5] Cache Check ✨
   ├─ [2] Create Context
   ├─ [3] Calculate Indicators (یکباره) ✨
   ├─ [3.5] Detect Market Regime ✨
   ├─ [4] Run 11 Analyzers
   ├─ [5] Determine Direction
   ├─ [6] Calculate Score (12 مرحله)
   ├─ [7] Validate (8 بررسی)
   └─ [✓] Return SignalInfo
   ↓
4. Aggregate/Select Best
   ↓
5. Send to TradeManager
```

### ویژگی‌های کلیدی سیستم جدید:

✅ **معماری ماژولار**
- جداسازی مسئولیت‌ها
- قابل نگهداری بهتر
- آزمایش آسان‌تر

✅ **عملکرد بهتر**
- محاسبه یکباره اندیکاتورها (30-40% سریع‌تر)
- کش کردن نتایج
- پردازش موازی

✅ **سیستم‌های هوشمند**
- Circuit Breaker
- Market Regime Detector
- Adaptive Learning
- Correlation Manager

✅ **اعتبارسنجی قوی‌تر**
- 8 بررسی مختلف
- Adaptive Threshold
- Risk Management پیشرفته

✅ **قابلیت پیکربندی**
- وزن‌های قابل تنظیم
- آستانه‌های انعطاف‌پذیر
- فعال/غیرفعال کردن ویژگی‌ها

---

## مقایسه نهایی: قدیم vs جدید

| ویژگی | سیستم قدیم | سیستم جدید |
|-------|-----------|-----------|
| **تعداد فایل** | 1 فایل (~5000 خط) | 80+ فایل ماژولار |
| **Analyzers** | 10 متد داخلی | 11 کلاس مجزا |
| **محاسبه Indicators** | چندباره (تکراری) | یکباره (بهینه) |
| **کش** | ❌ ندارد | ✅ دارد (30-40% سریع‌تر) |
| **Market Regime** | ❌ ندارد | ✅ دارد |
| **Adaptive Learning** | ❌ ندارد | ✅ دارد |
| **Correlation Manager** | ❌ ندارد | ✅ دارد |
| **اعتبارسنجی** | 4 بررسی | 8 بررسی |
| **Adaptive Threshold** | ❌ ندارد | ✅ دارد |
| **Type Safety** | کم | بالا (Enums, Dataclasses) |
| **تست‌پذیری** | سخت | آسان |
| **مستندات** | کم | زیاد |

---

## نتیجه‌گیری

سیستم جدید با حفظ منطق اصلی سیستم قدیم:
- **ساختار بهتری** دارد (ماژولار، تمیز)
- **سریع‌تر** است (30-40% بهبود)
- **هوشمندتر** است (Regime Detection, Adaptive Learning)
- **قابل اطمینان‌تر** است (اعتبارسنجی قوی‌تر)
- **قابل توسعه‌تر** است (اضافه کردن Analyzer جدید آسان)

همچنین **سازگاری با گذشته** را حفظ کرده است:
- حالت Multi-TF Aggregation برای سازگاری با سیستم قدیم
- امکان مقایسه مستقیم نتایج
- تنظیمات قابل انتقال
