# تحلیل کامل فرآیند تولید سیگنال معاملاتی - سیستم جدید (NEW SYSTEM)

## مقدمه

این سند توضیح می‌دهد که در **سیستم جدید ماژولار** وقتی داده‌های چهار تایم‌فریم (5m, 15m, 1h, 4h) برای تحلیل و ایجاد سیگنال معاملاتی دریافت می‌شوند، چه اتفاقاتی می‌افتد. در این سیستم، **سیگنال نهایی بر اساس امتیازدهی (Scoring) با 13 ضریب تولید می‌شود** که ترکیبی از تحلیل‌های مختلف است.

### تفاوت‌های بنیادی با سیستم قدیمی

| جنبه | سیستم قدیمی (OLD) | سیستم جدید (NEW) |
|------|------------------|------------------|
| **معماری** | Monolithic (تک‌بلوکی) | Modular (ماژولار) |
| **نقطه ورود** | SignalGenerator | SignalOrchestrator |
| **تعداد فایل‌ها** | 1 فایل بزرگ | 90+ فایل مستقل |
| **Analyzers** | متدهای درون کلاس | 11 کلاس مستقل |
| **Indicators** | محاسبه پراکنده | IndicatorOrchestrator متمرکز |
| **Patterns** | کد درهم | 35+ الگوی مستقل |
| **Caching** | ندارد | TimeframeScoreCache |
| **Testing** | سخت | آسان (unit test) |
| **Performance** | کندتر | سریع‌تر (با cache) |
| **وزن‌دهی** | ثابت | Per-Timeframe Configurable |

### فلسفه طراحی سیستم جدید

✅ **Separation of Concerns**: هر ماژول یک مسئولیت مشخص دارد
✅ **Single Responsibility**: هر کلاس فقط یک کار انجام می‌دهد
✅ **Dependency Injection**: کامپوننت‌ها از config خارجی استفاده می‌کنند
✅ **Context Sharing**: همه از یک AnalysisContext مشترک استفاده می‌کنند
✅ **Cache-First**: جلوگیری از محاسبات تکراری
✅ **Type Safety**: استفاده از Enums و Constants

### معماری کلی (High-Level Architecture)

```
SignalProcessor (ورودی)
    ↓
SignalOrchestrator (هماهنگ‌کننده اصلی)
    ↓
    ├─→ IndicatorOrchestrator (محاسبه متمرکز 10 اندیکاتور)
    │   └─→ EMA, SMA, RSI, MACD, Stochastic, ATR, Bollinger, OBV, ADX
    │
    ├─→ 11 Analyzers (تحلیلگران مستقل)
    │   ├─→ TrendAnalyzer (548 خط)
    │   ├─→ MomentumAnalyzer (1303 خط)
    │   ├─→ VolumeAnalyzer (596 خط)
    │   ├─→ VolumePatternAnalyzer (583 خط)
    │   ├─→ PatternAnalyzer (464 خط)
    │   │   └─→ PatternOrchestrator → 35+ الگو (کندلی + چارت)
    │   ├─→ SRAnalyzer (Support/Resistance - 781 خط)
    │   ├─→ VolatilityAnalyzer (538 خط)
    │   ├─→ HarmonicAnalyzer (495 خط)
    │   ├─→ ChannelAnalyzer (154 خط)
    │   ├─→ CyclicalAnalyzer (371 خط)
    │   └─→ HTFAnalyzer (Higher Timeframe - 323 خط)
    │
    ├─→ 4 سیستم هوشمند
    │   ├─→ MarketRegimeDetector (تشخیص رژیم بازار)
    │   ├─→ AdaptiveLearningSystem (یادگیری تطبیقی)
    │   ├─→ CorrelationManager (مدیریت همبستگی)
    │   └─→ EmergencyCircuitBreaker (مدار شکن اضطراری)
    │
    ├─→ SignalScorer (امتیازدهی با 13 ضریب - 876 خط)
    ├─→ MultiTimeframeAggregator (ترکیب TF ها - 822 خط)
    └─→ SignalValidator (اعتبارسنجی)
         ↓
SignalInfo (خروجی)
```

### ساختار فایل‌ها

```
signal_generation/
├── orchestrator.py (1275 خط)              # 🎯 نقطه ورود اصلی
├── signal_scorer.py (876 خط)              # ⭐ امتیازدهی
├── signal_validator.py (29001 خط)         # ✅ اعتبارسنجی
├── multi_tf_aggregator.py (822 خط)        # 🔄 ترکیب TF
├── timeframe_score_cache.py (17775 خط)    # 💾 کش
│
├── analyzers/                              # 📊 11 تحلیلگر (6535 خط)
│   ├── base_analyzer.py (350 خط)
│   ├── trend_analyzer.py (548 خط)
│   ├── momentum_analyzer.py (1303 خط)
│   ├── volume_analyzer.py (596 خط)
│   ├── volume_pattern_analyzer.py (583 خط)
│   ├── pattern_analyzer.py (464 خط)
│   ├── sr_analyzer.py (781 خط)
│   ├── volatility_analyzer.py (538 خط)
│   ├── harmonic_analyzer.py (495 خط)
│   ├── channel_analyzer.py (154 خط)
│   ├── cyclical_analyzer.py (371 خط)
│   └── htf_analyzer.py (323 خط)
│
├── analyzers/indicators/                   # 📈 سیستم اندیکاتورها
│   ├── indicator_orchestrator.py (347 خط)
│   ├── base_indicator.py (13694 خط)
│   └── ema.py, sma.py, rsi.py, macd.py, ... (10 اندیکاتور)
│
├── analyzers/patterns/                     # 🕯️ 35+ الگو
│   ├── pattern_orchestrator.py
│   ├── candlestick/ (30+ الگوی کندلی)
│   │   ├── engulfing.py, hammer.py, doji.py, ...
│   │   └── morning_star.py, three_white_soldiers.py, ...
│   └── chart/ (5 الگوی چارت)
│       ├── head_shoulders.py, double_top_bottom.py
│       └── triangle.py, wedge.py, flag_pennant.py
│
└── systems/                                # 🧠 سیستم‌های هوشمند
    ├── market_regime_detector.py
    ├── adaptive_learning_system.py
    ├── correlation_manager.py
    └── emergency_circuit_breaker.py
```

---

## بخش ۱: مسیر ورود داده و شروع تحلیل

### 1.1 نقطه شروع: دریافت داده‌ها

وقتی `SignalProcessor` یک نماد را برای تحلیل انتخاب می‌کند، این کار از متد `process_symbol()` شروع می‌شود:

**محل:** `signal_processor.py:392-560`

```python
async def process_symbol(self, symbol: str, force_refresh: bool = False, priority: bool = False)
```

این متد:
1. داده‌های چند تایم‌فریم را دریافت می‌کند (از `MarketDataFetcher`)
2. آن‌ها را به `SignalOrchestrator.analyze_symbol()` ارسال می‌کند

### 1.2 ورود به SignalOrchestrator

**محل:** `signal_generation/orchestrator.py:872-959`

```python
async def analyze_symbol(
    self,
    symbol: str,
    timeframes_data: Dict[str, Any]
) -> Optional[SignalInfo]:
```

**گام‌های اصلی:**

```python
# خط 894-897: فیلتر تایم‌فریم‌های معتبر
valid_timeframes = {
    tf: df for tf, df in timeframes_data.items()
    if df is not None and not df.empty
}

# خط 904-906: بررسی فعال بودن Multi-TF Aggregation
if not self.use_multi_tf_aggregation:
    return None

# خط 910-933: تولید سیگنال برای هر تایم‌فریم
for timeframe in valid_timeframes.keys():
    result = await self._generate_signal_with_context(symbol, timeframe)
    # ساخت TimeframeSignal برای هر TF

# خط 942-945: ترکیب سیگنال‌ها با MultiTimeframeAggregator
aggregated_signal = self.multi_tf_aggregator.aggregate_timeframe_scores(
    symbol=symbol,
    timeframe_signals=timeframe_signals
)
```

**نکته مهم:** این متد برای **هر تایم‌فریم** به صورت جداگانه سیگنال تولید می‌کند، سپس آن‌ها را ترکیب می‌کند.

---

### 1.3 تولید سیگنال برای یک تایم‌فریم

**محل:** `signal_generation/orchestrator.py:261-513`

```python
async def generate_signal_for_symbol(
    self,
    symbol: str,
    timeframe: str
) -> Optional[SignalInfo]:
```

این متد **7 مرحله اصلی + 7 زیرمرحله** دارد:

#### **مرحله 0: بررسی Circuit Breaker**
**محل:** خطوط 284-292

```python
if self.circuit_breaker.enabled:
    is_active, reason = self.circuit_breaker.check_if_active()
    if is_active:
        logger.warning(f"🚨 Circuit breaker active: {reason}")
        return None
```

**هدف:** جلوگیری از تولید سیگنال در شرایط اضطراری (مثلاً بعد از ضررهای متوالی)

#### **مرحله 1: دریافت داده‌های بازار**
**محل:** خطوط 294-304

```python
df = await self._fetch_market_data(symbol, timeframe)
```

**جزئیات:**
- تعداد کندل‌ها: 500 (قابل تنظیم از config)
- حداقل مورد نیاز: 200 کندل
- ستون‌ها: open, high, low, close, volume, timestamp

#### **مرحله 1.5: بررسی Cache**
**محل:** خطوط 306-326

```python
should_recalc, reason = self.tf_score_cache.should_recalculate(
    symbol, timeframe, df
)

if not should_recalc:
    # استفاده از امتیاز کش شده
    cached_signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
    return cached_signal
```

**شرایط invalidation (محاسبه مجدد):**
1. کندل جدید اضافه شده
2. تنظیمات تغییر کرده
3. کش منقضی شده (TTL)
4. کش خالی است

**مزیت:** جلوگیری از محاسبات تکراری برای همان داده‌ها

#### **مرحله 2: ایجاد AnalysisContext**
**محل:** خطوط 328-335

```python
context = AnalysisContext(
    symbol=symbol,
    timeframe=timeframe,
    df=df
)
```

**AnalysisContext چیست؟**
یک شیء مشترک که تمام اطلاعات تحلیل را نگهداری می‌کند:
- `df`: DataFrame با OHLCV و اندیکاتورها
- `symbol`: نام نماد
- `timeframe`: تایم‌فریم جاری
- `results`: نتایج تمام Analyzer ها
- `metadata`: اطلاعات اضافی

#### **مرحله 3: محاسبه اندیکاتورها**
**محل:** خطوط 337-347

```python
success = self._calculate_indicators(context)
```

**جزئیات در بخش 2 توضیح داده می‌شود.**

#### **مرحله 3.5: تشخیص رژیم بازار**
**محل:** خطوط 350-362

```python
if self.regime_detector.enabled:
    regime_info = self.regime_detector.detect_regime(context.df)
    # ذخیره در context برای استفاده Analyzer ها
    context.metadata['regime_info'] = regime_info
```

**رژیم‌های ممکن:**
- `trending_bullish`: روند صعودی
- `trending_bearish`: روند نزولی
- `ranging`: خنثی
- `high_volatility`: نوسان بالا
- `low_volatility`: نوسان پایین

#### **مرحله 4: اجرای Analyzers**
**محل:** خطوط 365-379

```python
self._run_analyzers(context)

# بررسی Analyzer های ضروری
required = ['trend', 'momentum', 'volume']
missing = [r for r in required if not context.get_result(r)]
if missing:
    return None
```

**Analyzer های اجرا شده (11 عدد):**
1. TrendAnalyzer
2. MomentumAnalyzer
3. VolumeAnalyzer
4. VolumePatternAnalyzer
5. PatternAnalyzer
6. SRAnalyzer
7. VolatilityAnalyzer
8. HarmonicAnalyzer
9. ChannelAnalyzer
10. CyclicalAnalyzer
11. HTFAnalyzer

**جزئیات در بخش 3 توضیح داده می‌شود.**

#### **مرحله 5: تعیین جهت**
**محل:** خطوط 381-390

```python
direction = self._determine_direction(context)
# نتیجه: 'LONG', 'SHORT', یا None
```

**الگوریتم تعیین جهت:**
```python
bullish_score = 0
bearish_score = 0

# Trend (وزن 3x)
if trend == 'bullish':
    bullish_score += trend_strength * 3

# Momentum (وزن 2x)
if momentum == 'bullish':
    bullish_score += momentum_strength * 2

# Volume (bonus +1)
if volume_confirmed:
    bullish_score += 1

# Patterns
for pattern in patterns:
    if pattern.direction == 'bullish':
        bullish_score += pattern.score

# تعیین نهایی
if bullish_score > bearish_score + threshold:
    direction = 'LONG'
elif bearish_score > bullish_score + threshold:
    direction = 'SHORT'
else:
    direction = None  # سیگنال واضحی نیست
```

#### **مرحله 6: محاسبه امتیاز**
**محل:** خطوط 392-412

```python
score = self.signal_scorer.calculate_score(context, direction)
```

**جزئیات کامل در بخش 4 توضیح داده می‌شود.**

این مرحله بسیار پیچیده است و شامل:
- امتیازدهی پایه از 10 Analyzer
- وزن‌دهی با 10 وزن مختلف
- محاسبه confluence (همگرایی)
- اعمال 13 ضریب (multiplier)

#### **مرحله 7: اعتبارسنجی**
**محل:** خطوط 442-462

```python
is_valid, reason = self.signal_validator.validate(signal, context)

if not is_valid:
    logger.info(f"Signal rejected: {reason}")
    return None
```

**موارد بررسی شده:**
1. حداقل امتیاز (min_score)
2. Risk/Reward ratio >= 2.0
3. حجم کافی
4. فاصله از سطوح SR
5. تایید چند Analyzer
6. محدودیت‌های زمانی

#### **نتیجه نهایی:**
**محل:** خطوط 464-489

```python
# ذخیره در Cache
self.tf_score_cache.update_cache(symbol, timeframe, signal, df)

# ذخیره Context برای استفاده بعدی
cache_key = f"{symbol}:{timeframe}"
self._context_cache[cache_key] = (context, time.time())

# ارسال به TradeManager (اختیاری)
if self.send_to_trade_manager:
    await self._send_to_trade_manager(signal)

return signal  # SignalInfo
```

---

**خلاصه بخش 1:**

مسیر ورود داده:
```
SignalProcessor.process_symbol()
    ↓
SignalOrchestrator.analyze_symbol() [برای هر TF]
    ↓
    ├─ generate_signal_for_symbol() → سیگنال تک TF
    │   ├─ [0] Circuit Breaker Check
    │   ├─ [1] Fetch Data (500 candles)
    │   ├─ [1.5] Cache Check
    │   ├─ [2] Create Context
    │   ├─ [3] Calculate Indicators (10 indicators)
    │   ├─ [3.5] Detect Market Regime
    │   ├─ [4] Run Analyzers (11 analyzers)
    │   ├─ [5] Determine Direction
    │   ├─ [6] Calculate Score (13 multipliers)
    │   └─ [7] Validate
    ↓
MultiTimeframeAggregator.aggregate_timeframe_scores()
    ↓
SignalInfo نهایی (ترکیب چند TF)
```

---

