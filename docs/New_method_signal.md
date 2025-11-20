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

## بخش ۲: سیستم اندیکاتورها (Indicator System)

### 2.1 معماری سیستم اندیکاتورها

سیستم اندیکاتورها در سیستم جدید به صورت **سلسله مراتبی و متمرکز** طراحی شده است:

```
IndicatorCalculator (wrapper)
    ↓
IndicatorOrchestrator (هسته اصلی - 347 خط)
    ↓
BaseIndicator (کلاس abstract)
    ↓
10 اندیکاتور مستقل:
├── EMA (Exponential Moving Average)
├── SMA (Simple Moving Average)
├── RSI (Relative Strength Index)
├── MACD (Moving Average Convergence Divergence)
├── Stochastic
├── ATR (Average True Range)
├── Bollinger Bands
├── OBV (On-Balance Volume)
├── ADX (Average Directional Index)
└── [Future indicators...]
```

### 2.2 IndicatorOrchestrator - مدیر متمرکز

**محل:** `signal_generation/analyzers/indicators/indicator_orchestrator.py:17-347`

**مسئولیت‌ها:**
1. بارگذاری خودکار تمام اندیکاتورها
2. مدیریت وابستگی‌ها (dependencies)
3. محاسبه به ترتیب صحیح
4. پشتیبانی از caching
5. مدیریت خطاها

**ساختار:**

```python
class IndicatorOrchestrator:
    def __init__(self, config):
        # دسته‌بندی اندیکاتورها
        self.trend_indicators = {}      # EMA, SMA, ADX
        self.momentum_indicators = {}   # RSI, MACD, Stochastic
        self.volatility_indicators = {} # ATR, Bollinger
        self.volume_indicators = {}     # OBV

        self.all_indicators = {}  # تمام اندیکاتورها

        self._load_indicators()  # بارگذاری خودکار
```

**متد اصلی محاسبه:**

**محل:** خطوط 143-201

```python
def calculate_all(
    self,
    df: pd.DataFrame,
    indicator_names: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    محاسبه تمام اندیکاتورها به ترتیب صحیح.

    ترتیب محاسبه:
    1. Trend indicators (EMA, SMA, ADX)
    2. Momentum indicators (RSI, MACD, Stochastic)
    3. Volatility indicators (ATR, Bollinger)
    4. Volume indicators (OBV)
    """
```

**چرا این ترتیب مهم است؟**
بعضی اندیکاتورها به خروجی اندیکاتورهای دیگر نیاز دارند. مثلاً MACD به EMA نیاز دارد.

### 2.3 BaseIndicator - کلاس پایه

**محل:** `signal_generation/analyzers/indicators/base_indicator.py:18-350`

هر اندیکاتور باید از این کلاس abstract ارث‌بری کند:

```python
class BaseIndicator(ABC):
    @abstractmethod
    def _get_indicator_name(self) -> str:
        """نام اندیکاتور (مثلاً 'EMA')"""
        pass

    @abstractmethod
    def _get_indicator_type(self) -> str:
        """نوع: 'trend', 'momentum', 'volatility', 'volume'"""
        pass

    @abstractmethod
    def _get_required_columns(self) -> List[str]:
        """ستون‌های ورودی لازم (مثلاً ['close'])"""
        pass

    @abstractmethod
    def _get_output_columns(self) -> List[str]:
        """ستون‌های خروجی (مثلاً ['ema_20', 'ema_50'])"""
        pass

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """محاسبه اصلی اندیکاتور"""
        pass
```

**ویژگی‌های مشترک:**
- ✅ Validation خودکار ورودی
- ✅ Error handling
- ✅ Caching support
- ✅ Per-timeframe configuration

### 2.4 اندیکاتورهای موجود (10 عدد)

#### **2.4.1 EMA (Exponential Moving Average)**

**محل:** `signal_generation/analyzers/indicators/ema.py:15-100`

```python
class EMAIndicator(BaseIndicator):
    default_periods = [20, 50, 100]  # پیش‌فرض
```

**فرمول محاسبه:**
```
alpha = 2 / (period + 1)
EMA[i] = price[i] × alpha + EMA[i-1] × (1 - alpha)
```

**خروجی:**
- `ema_20`: میانگین متحرک نمایی 20 دوره‌ای
- `ema_50`: میانگین متحرک نمایی 50 دوره‌ای
- `ema_100`: میانگین متحرک نمایی 100 دوره‌ای

**استفاده در Analyzers:**
- TrendAnalyzer: تعیین جهت روند
- MomentumAnalyzer: تشخیص کراس‌اورها
- HTFAnalyzer: مقایسه با تایم‌فریم بالاتر

#### **2.4.2 RSI (Relative Strength Index)**

**محل:** `signal_generation/analyzers/indicators/rsi.py:15-120`

```python
class RSIIndicator(BaseIndicator):
    default_period = 14
```

**فرمول محاسبه:**
```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))
```

**خروجی:**
- `rsi_14`: RSI با دوره 14

**سطوح مهم:**
- RSI > 70: Overbought (اشباع خرید)
- RSI < 30: Oversold (اشباع فروش)
- 30-70: Neutral

#### **2.4.3 MACD (Moving Average Convergence Divergence)**

**محل:** `signal_generation/analyzers/indicators/macd.py:15-95`

```python
class MACDIndicator(BaseIndicator):
    default_fast = 12
    default_slow = 26
    default_signal = 9
```

**فرمول محاسبه:**
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD
Histogram = MACD - Signal
```

**خروجی:**
- `macd`: خط MACD
- `macd_signal`: خط سیگنال
- `macd_hist`: هیستوگرام

**سیگنال‌ها:**
- MACD > Signal: صعودی
- MACD < Signal: نزولی
- Histogram > 0: قدرت صعودی
- Histogram < 0: قدرت نزولی

#### **2.4.4 Stochastic**

**محل:** `signal_generation/analyzers/indicators/stochastic.py:15-105`

```python
class StochasticIndicator(BaseIndicator):
    default_k_period = 14
    default_d_period = 3
    default_smooth = 3
```

**فرمول محاسبه:**
```
%K = 100 × (Close - Lowest Low) / (Highest High - Lowest Low)
%D = SMA(%K, 3)
```

**خروجی:**
- `stoch_k`: خط %K
- `stoch_d`: خط %D

**سطوح:**
- K > 80: Overbought
- K < 20: Oversold

#### **2.4.5 ATR (Average True Range)**

**محل:** `signal_generation/analyzers/indicators/atr.py:15-80`

```python
class ATRIndicator(BaseIndicator):
    default_period = 14
```

**فرمول محاسبه:**
```
TR = max(high - low, |high - prev_close|, |low - prev_close|)
ATR = EMA(TR, 14)
```

**خروجی:**
- `atr_14`: ATR با دوره 14

**کاربرد:**
- محاسبه Stop Loss (معمولاً 1.5-2× ATR)
- محاسبه Take Profit
- اندازه‌گیری نوسان بازار

#### **2.4.6 Bollinger Bands**

**محل:** `signal_generation/analyzers/indicators/bollinger_bands.py:15-90`

```python
class BollingerBandsIndicator(BaseIndicator):
    default_period = 20
    default_std_dev = 2
```

**فرمول محاسبه:**
```
Middle Band = SMA(20)
Upper Band = SMA(20) + (2 × σ)
Lower Band = SMA(20) - (2 × σ)
```

**خروجی:**
- `bb_upper`: باند بالایی
- `bb_middle`: باند میانی
- `bb_lower`: باند پایینی

**سیگنال‌ها:**
- قیمت نزدیک Upper Band: احتمال برگشت نزولی
- قیمت نزدیک Lower Band: احتمال برگشت صعودی
- باندها باز می‌شوند: افزایش نوسان

#### **2.4.7 OBV (On-Balance Volume)**

**محل:** `signal_generation/analyzers/indicators/obv.py:15-70`

```python
class OBVIndicator(BaseIndicator):
    # No parameters
```

**فرمول محاسبه:**
```
if close > prev_close:
    OBV = prev_OBV + volume
elif close < prev_close:
    OBV = prev_OBV - volume
else:
    OBV = prev_OBV
```

**خروجی:**
- `obv`: On-Balance Volume

**کاربرد:**
- تایید روند با حجم
- تشخیص divergence

#### **2.4.8 ADX (Average Directional Index)**

**محل:** `signal_generation/analyzers/indicators/adx.py:15-75`

```python
class ADXIndicator(BaseIndicator):
    default_period = 14
```

**خروجی:**
- `adx`: شاخص ADX
- `plus_di`: +DI
- `minus_di`: -DI

**معنی:**
- ADX > 25: روند قوی
- ADX < 20: روند ضعیف/خنثی
- +DI > -DI: روند صعودی
- -DI > +DI: روند نزولی

### 2.5 فرآیند محاسبه در Orchestrator

**محل:** `orchestrator.py:535-544`

```python
def _calculate_indicators(self, context: AnalysisContext) -> bool:
    """محاسبه تمام اندیکاتورها."""
    try:
        # استفاده از IndicatorCalculator (wrapper)
        self.indicator_calculator.calculate_all(context)
        return True
    except Exception as e:
        logger.error(f"Failed to calculate indicators: {e}")
        return False
```

**نتیجه:**
بعد از این مرحله، `context.df` دارای 20+ ستون اندیکاتور است:

```
ema_20, ema_50, ema_100
sma_20, sma_50, sma_100
rsi_14
macd, macd_signal, macd_hist
stoch_k, stoch_d
atr_14
bb_upper, bb_middle, bb_lower
obv
adx, plus_di, minus_di
```

این ستون‌ها توسط Analyzers در مرحله بعدی استفاده می‌شوند.

---

## بخش ۳: تحلیلگران (Analyzers)

### 3.1 معماری تحلیلگران

تحلیلگران در سیستم جدید به صورت **کاملاً مستقل** طراحی شده‌اند:

```
BaseAnalyzer (کلاس abstract - 350 خط)
    ↓
11 Analyzer مستقل:
├── TrendAnalyzer (548 خط)              ← تحلیل روند
├── MomentumAnalyzer (1303 خط)          ← تحلیل مومنتوم
├── VolumeAnalyzer (596 خط)             ← تحلیل حجم
├── VolumePatternAnalyzer (583 خط)      ← الگوهای حجمی
├── PatternAnalyzer (464 خط)            ← الگوهای کندلی و چارت
├── SRAnalyzer (781 خط)                 ← حمایت/مقاومت
├── VolatilityAnalyzer (538 خط)         ← نوسان
├── HarmonicAnalyzer (495 خط)           ← الگوهای هارمونیک
├── ChannelAnalyzer (154 خط)            ← کانال‌ها
├── CyclicalAnalyzer (371 خط)           ← چرخه‌های بازار
└── HTFAnalyzer (323 خط)                ← تایم‌فریم بالاتر
```

### 3.2 BaseAnalyzer - کلاس پایه

**محل:** `signal_generation/analyzers/base_analyzer.py:22-350`

```python
class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, context: AnalysisContext) -> None:
        """
        متد اصلی تحلیل - باید پیاده‌سازی شود.

        الگوی استاندارد:
        1. بررسی enabled
        2. اعتبارسنجی context
        3. انجام تحلیل
        4. ذخیره نتیجه در context
        """
        pass
```

### 3.3 نمونه کامل: TrendAnalyzer

**محل:** `signal_generation/analyzers/trend_analyzer.py:48-548`

این Analyzer مسئول **تشخیص روند بازار** است و یکی از مهم‌ترین Analyzer ها محسوب می‌شود.

#### **3.3.1 ساختار کلی**

```python
class TrendAnalyzer(BaseAnalyzer):
    def __init__(self, config):
        self.min_slope_threshold = 0.0001  # حداقل شیب
        self.slope_lookback = 5            # دوره محاسبه شیب
        self.enabled = True

    def analyze(self, context: AnalysisContext) -> None:
        """
        9 مرحله تحلیل روند
        """
```

#### **3.3.2 فرآیند تحلیل (9 مرحله)**

**محل:** خطوط 83-195

```python
# مرحله 1: بررسی فعال بودن
if not self._check_enabled():
    return

# مرحله 2: اعتبارسنجی
if not self._validate_context(context):
    return

# مرحله 3: خواندن اندیکاتورها
current_close = df['close'].iloc[-1]
current_ema20 = df['ema_20'].iloc[-1]
current_ema50 = df['ema_50'].iloc[-1]
current_ema100 = df['ema_100'].iloc[-1]

# مرحله 4: محاسبه شیب EMA ها
ema_slopes = self._calculate_ema_slopes(df)

# مرحله 5: تعیین چیدمان EMA ها
ema_alignment = self._determine_ema_alignment(
    current_close, current_ema20, current_ema50, current_ema100
)

# مرحله 6: تشخیص جهت و قدرت روند
trend_result = self._detect_trend(...)

# مرحله 7: تعیین فاز روند
trend_phase = self._determine_trend_phase(...)

# مرحله 8: محاسبه اطمینان
confidence = self._calculate_confidence(...)

# مرحله 9: ذخیره نتیجه
context.add_result('trend', result)
```

#### **3.3.3 محاسبه شیب (Slope)**

**محل:** خطوط 197-232

```python
def _calculate_ema_slopes(self, df: pd.DataFrame) -> Dict[str, float]:
    """
    محاسبه نرخ تغییر (Rate of Change) برای هر EMA

    فرمول:
    slope = (current - past) / past
    """
    lookback = 5  # 5 کندل قبل

    ema20_slope = (
        (df['ema_20'].iloc[-1] - df['ema_20'].iloc[-lookback])
        / df['ema_20'].iloc[-lookback]
    )

    # مشابه برای ema_50 و ema_100

    return {
        'ema20': ema20_slope,
        'ema50': ema50_slope,
        'ema100': ema100_slope
    }
```

**مثال:**
- slope = 0.01 → روند صعودی 1%
- slope = -0.01 → روند نزولی 1%
- slope ≈ 0 → خنثی

#### **3.3.4 چیدمان EMA ها (Alignment)**

**محل:** خطوط 234-269

```python
def _determine_ema_alignment(
    self, close, ema20, ema50, ema100
) -> str:
    """
    تشخیص الگوی چیدمان EMA ها
    """
    if ema20 > ema50 > ema100:
        return 'bullish_aligned'      # صعودی کامل

    elif ema20 < ema50 < ema100:
        return 'bearish_aligned'      # نزولی کامل

    elif ema20 > ema50 and ema50 < ema100:
        return 'potential_bullish_reversal'  # احتمال برگشت صعودی

    elif ema20 < ema50 and ema50 > ema100:
        return 'potential_bearish_reversal'  # احتمال برگشت نزولی

    else:
        return 'mixed'  # مختلط
```

#### **3.3.5 تشخیص روند و قدرت**

**محل:** خطوط 271-359

```python
def _detect_trend(...) -> Dict[str, Any]:
    """
    تشخیص جهت و قدرت روند (6 سطح)
    """
    # صعودی قوی (strength = 3)
    if (close > ema20 > ema50 > ema100 and
        ema20_slope > threshold and
        ema50_slope > threshold):
        direction = 'bullish'
        strength = 3

    # صعودی متوسط (strength = 2)
    elif (close > ema20 > ema50 and
          ema20_slope > threshold):
        direction = 'bullish'
        strength = 2

    # صعودی ضعیف (strength = 1)
    elif close > ema20 and ema20_slope > threshold:
        direction = 'bullish'
        strength = 1

    # نزولی قوی (strength = -3)
    elif (close < ema20 < ema50 < ema100 and
          ema20_slope < -threshold and
          ema50_slope < -threshold):
        direction = 'bearish'
        strength = -3

    # نزولی متوسط (strength = -2)
    elif (close < ema20 < ema50 and
          ema20_slope < -threshold):
        direction = 'bearish'
        strength = -2

    # نزولی ضعیف (strength = -1)
    elif close < ema20 and ema20_slope < -threshold:
        direction = 'bearish'
        strength = -1

    # خنثی
    else:
        direction = 'neutral'
        strength = 0

    return {'direction': direction, 'strength': strength}
```

#### **3.3.6 فاز روند (Trend Phase)**

**محل:** خطوط 361-450

```python
def _determine_trend_phase(...) -> str:
    """
    تعیین مرحله روند

    فازهای ممکن:
    - early: شروع روند (بهترین فرصت)
    - developing: در حال توسعه
    - mature: بالغ
    - late: اواخر روند (خطرناک)
    - pullback: اصلاح موقت
    - transition: انتقالی
    """
    if direction == 'bullish':
        if alignment == 'potential_bullish_reversal':
            return 'early'  # شروع روند صعودی

        elif strength == 3:
            return 'mature'  # روند قوی و بالغ

        elif alignment == 'bullish_pullback':
            return 'pullback'  # اصلاح در روند صعودی

    # مشابه برای bearish
```

#### **3.3.7 خروجی TrendAnalyzer**

```python
result = {
    'status': 'ok',
    'direction': 'bullish' | 'bearish' | 'neutral',
    'strength': -3 to +3,
    'phase': 'early' | 'developing' | 'mature' | 'late' | 'pullback' | 'transition',
    'ema_alignment': 'bullish_aligned' | 'bearish_aligned' | ...,
    'price_position': 'above_all' | 'above_ema20' | ...,
    'ema_slopes': {
        'ema20': 0.015,  # +1.5%
        'ema50': 0.008,
        'ema100': 0.005
    },
    'confidence': 0.0 to 1.0,
    'details': {...}
}
```

این نتیجه در `context` ذخیره می‌شود و توسط:
- `_determine_direction()` برای تعیین جهت کلی
- `SignalScorer` برای امتیازدهی
استفاده می‌شود.

### 3.4 خلاصه سایر Analyzers

#### **3.4.1 MomentumAnalyzer (1303 خط)**
**مسئولیت:** تحلیل مومنتوم با RSI, MACD, Stochastic

**خروجی:**
```python
{
    'direction': 'bullish' | 'bearish',
    'strength': 0-3,
    'rsi': {'value': 65, 'state': 'neutral'},
    'macd': {'type': 'A_STRONG', 'histogram': 'increasing'},
    'stochastic': {'state': 'oversold'}
}
```

#### **3.4.2 VolumeAnalyzer (596 خط)**
**مسئولیت:** تحلیل حجم معاملات

**خروجی:**
```python
{
    'is_confirmed': True,  # حجم بالا
    'volume_ratio': 1.5,   # 50% بیشتر از میانگین
    'obv_trend': 'increasing'
}
```

#### **3.4.3 PatternAnalyzer (464 خط)**
**مسئولیت:** تشخیص 35+ الگو (کندلی + چارت)

**خروجی:**
```python
{
    'strongest_pattern': {
        'name': 'Bullish Engulfing',
        'confidence': 0.85,
        'location': 'recent',
        'candles_ago': 1
    },
    'candlestick_patterns': [...],
    'chart_patterns': [...]
}
```

#### **3.4.4 SRAnalyzer (781 خط)**
**مسئولیت:** تشخیص سطوح حمایت/مقاومت

**خروجی:**
```python
{
    'nearest_resistance': 45000,
    'nearest_support': 42000,
    'distance_to_resistance': 200,  # pips
    'zone_strength': 0.8
}
```

### 3.5 اجرای Analyzers در Orchestrator

**محل:** `orchestrator.py:546-553`

```python
def _run_analyzers(self, context: AnalysisContext) -> None:
    """اجرای تمام Analyzer های فعال"""
    for analyzer_name, analyzer in self.analyzers.items():
        try:
            analyzer.analyze(context)
            logger.debug(f"  ✓ {analyzer_name} completed")
        except Exception as e:
            logger.error(f"  ✗ {analyzer_name} failed: {e}")
```

**نتیجه:**
بعد از این مرحله، `context` حاوی نتایج 11 Analyzer است که در مرحله بعد برای امتیازدهی استفاده می‌شوند.

---

## بخش ۴: سیستم امتیازدهی (Scoring System)

### 4.1 SignalScorer - موتور امتیازدهی

**محل:** `signal_generation/signal_scorer.py:27-876`

این کلاس مسئول **ترکیب نتایج 11 Analyzer و محاسبه امتیاز نهایی** است.

### 4.2 فرآیند امتیازدهی (13 مرحله)

**محل:** `signal_scorer.py:100-177`

```python
def calculate_score(
    context: AnalysisContext,
    direction: str  # 'LONG' or 'SHORT'
) -> SignalScore:

    # [1] محاسبه امتیازات پایه (Base Scores)
    self._calculate_base_scores(score, context, direction)

    # [2] اعمال وزن‌ها (Weights)
    self._apply_weights(score, context.timeframe)

    # [3] محاسبه همگرایی (Confluence)
    self._calculate_confluence(score, context, direction)

    # [4] وزن تایم‌فریم (Timeframe Weight)
    self._apply_timeframe_weight(score, context.timeframe)

    # [5] ضریب HTF (HTF Multiplier)
    self._apply_htf_multiplier(score, context, direction)

    # [6] تنظیم نوسان (Volatility Adjustment)
    self._apply_volatility_adjustment(score, context)

    # [7] همراستایی روند (Trend Alignment)
    self._apply_trend_alignment(score, context, direction)

    # [8] تایید حجم (Volume Confirmation)
    self._apply_volume_confirmation(score, context, direction)

    # [9] کیفیت الگو (Pattern Quality)
    self._apply_pattern_quality(score, context)

    # [10] تحلیل MACD (MACD Analysis)
    self._apply_macd_analysis_score(score, context)

    # [11] یادگیری تطبیقی (Adaptive Learning) - در orchestrator
    # [12] مدیریت همبستگی (Correlation) - در orchestrator

    # [13] محاسبه امتیاز نهایی
    score.calculate_final_score(max_score=self.max_final_score)

    return score
```

### 4.3 مرحله 1: امتیازات پایه

**محل:** خطوط 179-262

```python
def _calculate_base_scores(score, context, direction):
    """
    هر Analyzer امتیاز 0-100 می‌دهد
    """
    # 1. Trend Score
    trend_result = context.get_result('trend')
    score.trend_score = self._score_trend(trend_result, direction)

    # 2. Momentum Score
    momentum_result = context.get_result('momentum')
    score.momentum_score = self._score_momentum(momentum_result, direction)

    # 3. Volume Score
    volume_result = context.get_result('volume')
    score.volume_score = self._score_volume(volume_result, direction)

    # 4. Pattern Score
    pattern_result = context.get_result('patterns')
    score.pattern_score = self._score_patterns(pattern_result, direction)

    # 5-10. سایر Analyzer ها
    # SR, Volatility, Harmonic, Channel, Cyclical, HTF
```

**مثال: امتیازدهی Trend**

**محل:** خطوط 263-280

```python
def _score_trend(trend_result, direction) -> float:
    """
    امتیاز بر اساس قدرت و همراستایی
    """
    trend_direction = trend_result.get('direction')
    strength = abs(trend_result.get('strength', 0))

    # بررسی همراستایی
    if direction == 'LONG' and trend_direction == 'bullish':
        # محاسبه امتیاز بر اساس قدرت
        if strength == 3:
            return 100  # روند قوی
        elif strength == 2:
            return 75
        elif strength == 1:
            return 50

    elif direction == 'SHORT' and trend_direction == 'bearish':
        # مشابه بالا

    return 0  # عدم همراستایی
```

### 4.4 مرحله 2: وزن‌دهی

**محل:** خطوط 524-555

**وزن‌های پیش‌فرض:**

```python
DEFAULT_WEIGHTS = {
    'trend': 0.30,          # 30% - بالاترین
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

**محاسبه:**

```python
score.weighted_trend = score.trend_score × 0.30
score.weighted_momentum = score.momentum_score × 0.25
score.weighted_volume = score.volume_score × 0.20
# ...

score.base_score = sum of all weighted scores
```

**مثال:**
```
trend_score = 100 → weighted_trend = 30
momentum_score = 80 → weighted_momentum = 20
volume_score = 90 → weighted_volume = 18
pattern_score = 70 → weighted_pattern = 7
sr_score = 60 → weighted_sr = 4.8

base_score = 30 + 20 + 18 + 7 + 4.8 + ... ≈ 85
```

### 4.5 مرحله 3: همگرایی (Confluence)

**محل:** خطوط 557-630

**دو بخش:**

#### **بخش 1: Alignment Bonus**
```python
# چند Analyzer هم‌جهت هستند؟
aligned_analyzers = 0

if trend == direction: aligned_analyzers += 1
if momentum == direction: aligned_analyzers += 1
if volume_confirmed: aligned_analyzers += 1
if patterns == direction: aligned_analyzers += 1
if htf == direction: aligned_analyzers += 1

alignment_ratio = aligned_analyzers / 5
alignment_bonus = alignment_ratio × 0.25  # max +25%
```

#### **بخش 2: Risk/Reward Bonus**
```python
# نسبت سود به ضرر خوب است؟
if risk_reward_ratio >= 2.0:
    rr_bonus = min(0.25, (rr_ratio - 2.0) × 0.125)
else:
    rr_bonus = 0
```

**ترکیب:**
```python
confluence_bonus = alignment_bonus + rr_bonus
# max: 0.5 (50%)
```

### 4.6 مراحل 4-13: ضرایب (Multipliers)

**محل:** خطوط 630-800

```python
# [4] Timeframe Weight
timeframe_weights = {
    '5m': 0.7,   # -30%
    '15m': 0.85, # -15%
    '1h': 1.0,   # reference
    '4h': 1.2    # +20%
}

# [5] HTF Alignment
if htf_aligned:
    htf_multiplier = 1.3  # +30%
elif htf_misaligned:
    htf_multiplier = 0.7  # -30%
else:
    htf_multiplier = 1.0

# [6] Volatility Adjustment
if volatility == 'high':
    volatility_multiplier = 0.7  # -30%
elif volatility == 'low':
    volatility_multiplier = 1.0
else:
    volatility_multiplier = 0.85

# [7] Trend Alignment
if trend_phase == 'early':
    trend_alignment = 1.2  # +20%
elif trend_phase == 'late':
    trend_alignment = 0.8  # -20%
else:
    trend_alignment = 1.0

# [8] Volume Confirmation
if volume_confirmed:
    volume_confirmation = 1.4  # +40%
else:
    volume_confirmation = 1.0

# [9] Pattern Quality
if strongest_pattern:
    quality = pattern.quality_score / 100
    pattern_quality = 1.0 + (quality × 0.5)  # up to +50%

# [10] MACD Analysis
macd_type = momentum_result.get('macd_type')
if macd_type.startswith('A_'):  # Strong bullish
    macd_analysis = 1.15  # +15%
elif macd_type.startswith('C_'):  # Strong bearish
    macd_analysis = 1.15
else:
    macd_analysis = 1.0
```

### 4.7 فرمول نهایی (13 ضریب)

**محل:** `signal_score.py:89-139`

```python
final_score = (
    base_score
    × (1.0 + confluence_bonus)       # 0-0.5
    × timeframe_weight                # 0.7-1.2
    × trend_alignment                 # 0.8-1.2
    × volume_confirmation             # 1.0-1.4
    × pattern_quality                 # 1.0-1.5
    × symbol_performance_factor       # 0.8-1.3
    × correlation_safety_factor       # 0.5-1.0
    × macd_analysis_score             # 0.85-1.15
    × structure_score                 # 0.8-1.2
    × volatility_multiplier           # 0.5-1.0
    × harmonic_multiplier             # 1.0-1.2
    × channel_multiplier              # 1.0-1.1
    × cyclical_multiplier             # 1.0-1.1
)
```

**مثال محاسبه:**

```
base_score = 85

× (1 + 0.3)           = ×1.3   (confluence: 3/5 aligned + RR=2.5)
× 1.0                 = ×1.0   (timeframe: 1h)
× 1.1                 = ×1.1   (trend: developing phase)
× 1.4                 = ×1.4   (volume confirmed)
× 1.2                 = ×1.2   (pattern quality: 80/100)
× 1.0                 = ×1.0   (symbol performance: neutral)
× 1.0                 = ×1.0   (no correlation issues)
× 1.15                = ×1.15  (MACD: A_STRONG type)
× 1.0                 = ×1.0   (HTF: neutral)
× 0.9                 = ×0.9   (volatility: normal)
× 1.0                 = ×1.0   (no harmonic)
× 1.0                 = ×1.0   (no channel)
× 1.0                 = ×1.0   (no cyclical)

final_score = 85 × 1.3 × 1.0 × 1.1 × 1.4 × 1.2 × 1.0 × 1.0 × 1.15 × 1.0 × 0.9 × 1.0 × 1.0 × 1.0
            = 85 × 2.57
            ≈ 218
```

### 4.8 تعیین قدرت سیگنال

**محل:** `signal_score.py:141-160`

```python
if final_score < 80:
    signal_strength = 'weak'
elif final_score < 150:
    signal_strength = 'medium'
else:
    signal_strength = 'strong'
```

**محدوده‌ها:**
- **weak:** 0-79 (سیگنال ضعیف - ممکن است رد شود)
- **medium:** 80-149 (سیگنال متوسط - قابل قبول)
- **strong:** 150+ (سیگنال قوی - بهترین فرصت)

### 4.9 محاسبه اطمینان (Confidence)

**محل:** `signal_score.py:162-200`

```python
confidence = 0.3  # base

# Aligned Analyzers
if aligned_analyzers >= 7:
    confidence += 0.3
elif aligned_analyzers >= 5:
    confidence += 0.2
elif aligned_analyzers >= 3:
    confidence += 0.1

# Final Score
if final_score >= 150:
    confidence += 0.2
elif final_score >= 100:
    confidence += 0.1

# Confluence
if confluence_bonus >= 0.3:
    confidence += 0.2
elif confluence_bonus >= 0.2:
    confidence += 0.1

confidence = min(1.0, confidence)  # max 1.0
```

---

## بخش ۵: ترکیب Multi-Timeframe

### 5.1 MultiTimeframeAggregator

**محل:** `signal_generation/multi_tf_aggregator.py:44-822`

بعد از اینکه برای هر تایم‌فریم یک سیگنال تولید شد، باید آن‌ها را ترکیب کنیم.

### 5.2 فرآیند ترکیب (8 مرحله)

**محل:** خطوط 112-218

```python
def aggregate_timeframe_scores(
    symbol: str,
    timeframe_signals: Dict[str, TimeframeSignal]
) -> Optional[SignalInfo]:

    # [1] محاسبه امتیازات کل
    bullish_score, bearish_score = self._calculate_aggregate_scores(
        timeframe_signals
    )

    # [2] تعیین جهت نهایی (با margin 30%)
    final_direction = self._determine_direction(
        bullish_score, bearish_score
    )

    # [2.5] بررسی اجماع (consensus)
    has_consensus = self._check_timeframe_consensus(
        timeframe_signals, final_direction, min_consensus=0.75
    )

    # [3] محاسبه alignment factor
    alignment_factor = self._calculate_alignment_factor(
        timeframe_signals, final_direction
    )

    # [4] محاسبه volume factor
    volume_factor = self._calculate_volume_factor(timeframe_signals)

    # [5] محاسبه HTF factor
    htf_factor = self._calculate_htf_factor(timeframe_signals)

    # [6] محاسبه volatility factor
    volatility_factor = self._calculate_volatility_factor(timeframe_signals)

    # [7] محاسبه confidence metrics
    confidence_metrics = self.confidence_calculator.calculate_confidence(...)

    # [8] ساخت سیگنال نهایی
    signal_info = self._build_signal_info(...)

    return signal_info
```

### 5.3 محاسبه امتیازات کل

**محل:** خطوط 220-332

```python
def _calculate_aggregate_scores(
    timeframe_signals
) -> Tuple[float, float]:
    """
    برای هر TF:
        1. دریافت نتایج Analyzer ها
        2. اعمال وزن TF
        3. اعمال Phase multiplier
        4. اعمال MACD strength
        5. جمع در bullish_score یا bearish_score
    """
    bullish_score = 0.0
    bearish_score = 0.0

    for tf, tf_signal in timeframe_signals.items():
        tf_weight = TF_WEIGHTS[tf]  # 5m:0.7, 15m:0.85, 1h:1.0, 4h:1.1

        # Trend
        trend = tf_signal.context.get_result('trend')
        trend_strength = trend['strength']
        trend_phase = trend['phase']

        phase_multiplier = PHASE_MULTIPLIERS[trend_phase]

        if trend['direction'] == 'bullish':
            bullish_score += trend_strength × tf_weight × phase_multiplier

        # Momentum
        momentum = tf_signal.context.get_result('momentum')
        macd_type = momentum['macd_type']

        macd_strength = MACD_TYPE_STRENGTH[macd_type[0]]  # A, B, C, D, X

        bullish_score += momentum['bullish'] × tf_weight × macd_strength
        bearish_score += momentum['bearish'] × tf_weight × macd_strength

        # Volume bonus
        if tf_signal.volume_confirmed:
            if trend['direction'] == 'bullish':
                bullish_score += 1.0 × tf_weight

    return (bullish_score, bearish_score)
```

**Phase Multipliers:**
```python
{
    'early': 1.2,       # +20% - بهترین فرصت
    'developing': 1.1,  # +10%
    'mature': 0.9,      # -10%
    'late': 0.7,        # -30% - خطرناک
    'pullback': 1.1,    # +10%
    'transition': 0.8   # -20%
}
```

**MACD Type Strength:**
```python
{
    'A': 1.2,  # A_ types (strong bullish) +20%
    'C': 1.2,  # C_ types (strong bearish) +20%
    'B': 1.0,  # B_ types (neutral)
    'D': 1.0,  # D_ types (neutral)
    'X': 0.8   # X_ types (transition) -20%
}
```

### 5.4 تعیین جهت نهایی

**محل:** خطوط 334-357

```python
def _determine_direction(
    bullish_score: float,
    bearish_score: float
) -> str:
    """
    با margin 30%
    """
    if bullish_score > bearish_score × 1.3:
        return 'LONG'
    elif bearish_score > bullish_score × 1.3:
        return 'SHORT'
    else:
        return 'NEUTRAL'  # هیچ سیگنالی تولید نمی‌شود
```

**مثال:**
```
bullish_score = 15
bearish_score = 10

15 > 10 × 1.3 = 13?  ✓ YES → LONG

اگر bearish_score = 12 بود:
15 > 12 × 1.3 = 15.6?  ✗ NO → NEUTRAL
```

### 5.5 بررسی اجماع (Consensus Check)

**محل:** خطوط 359-400

```python
def _check_timeframe_consensus(
    timeframe_signals,
    final_direction,
    min_consensus=0.75  # 75%
) -> bool:
    """
    حداقل 75% تایم‌فریم‌ها باید هم‌جهت باشند
    """
    aligned_count = 0
    total_count = len(timeframe_signals)

    for tf_signal in timeframe_signals.values():
        if tf_signal.direction == final_direction:
            aligned_count += 1

    consensus_ratio = aligned_count / total_count

    return consensus_ratio >= min_consensus
```

**مثال:**
```
تایم‌فریم‌ها:
5m: LONG
15m: LONG
1h: LONG
4h: SHORT

final_direction = LONG
aligned = 3/4 = 75%

consensus_ratio >= 0.75?  ✓ YES → قبول
```

### 5.6 Alignment Factor

**محل:** خطوط 402-480

```python
def _calculate_alignment_factor(
    timeframe_signals,
    final_direction
) -> float:
    """
    بررسی همراستایی Trend, Momentum, MACD

    وزن‌ها:
    - Trend: 50%
    - Momentum: 30%
    - MACD: 20%

    محدوده: 0.7 - 1.3
    """
    aligned_trend = 0
    total_trend = 0

    aligned_momentum = 0
    total_momentum = 0

    aligned_macd = 0
    total_macd = 0

    # شمارش همراستایی‌ها
    for tf_signal in timeframe_signals.values():
        trend = tf_signal.context.get_result('trend')
        if trend:
            total_trend += 1
            if (final_direction == 'LONG' and trend['direction'] == 'bullish') or \
               (final_direction == 'SHORT' and trend['direction'] == 'bearish'):
                aligned_trend += 1

        # مشابه برای momentum و macd

    # محاسبه نسبت‌ها
    trend_ratio = aligned_trend / total_trend if total_trend > 0 else 0
    momentum_ratio = aligned_momentum / total_momentum if total_momentum > 0 else 0
    macd_ratio = aligned_macd / total_macd if total_macd > 0 else 0

    # ترکیب با وزن
    weighted_alignment = (
        trend_ratio × 0.5 +
        momentum_ratio × 0.3 +
        macd_ratio × 0.2
    )

    # تبدیل به multiplier (0.7 - 1.3)
    alignment_factor = 0.7 + (weighted_alignment × 0.6)

    return alignment_factor
```

**مثال:**
```
4 TF داریم، direction = LONG

Trend: 4/4 aligned (100%)
Momentum: 3/4 aligned (75%)
MACD: 3/4 aligned (75%)

weighted_alignment = 1.0×0.5 + 0.75×0.3 + 0.75×0.2
                   = 0.5 + 0.225 + 0.15
                   = 0.875

alignment_factor = 0.7 + (0.875 × 0.6)
                 = 0.7 + 0.525
                 = 1.225  (+22.5%)
```

### 5.7 خروجی نهایی

```python
signal_info = SignalInfo(
    symbol=symbol,
    timeframe='MULTI',  # ترکیب چند TF
    direction=final_direction,
    score=final_score,
    confidence=confidence_metrics.overall_confidence,

    # جزئیات
    bullish_score=bullish_score,
    bearish_score=bearish_score,
    alignment_factor=alignment_factor,
    volume_factor=volume_factor,
    htf_factor=htf_factor,

    # تایم‌فریم‌های مشارکت‌کننده
    contributing_timeframes=['5m', '15m', '1h', '4h'],

    # Entry, SL, TP محاسبه شده
    ...
)
```

---

## بخش ۶: خلاصه و جمع‌بندی

### 6.1 مسیر کامل تولید سیگنال

```
[ورودی] SignalProcessor.process_symbol(symbol)
    ↓
[Phase 0] Circuit Breaker Check
    ↓
[Phase 1] Fetch Data (4 timeframes × 500 candles)
    ↓
┌─────────────────────────────────────────────────────┐
│ برای هر تایم‌فریم (5m, 15m, 1h, 4h):                 │
│                                                     │
│   [1.5] Cache Check → اگر valid بود return cached  │
│      ↓                                              │
│   [2] Create AnalysisContext                       │
│      ↓                                              │
│   [3] Calculate Indicators (10 indicators)         │
│      → EMA, SMA, RSI, MACD, Stochastic, ...        │
│      ↓                                              │
│   [3.5] Detect Market Regime                       │
│      ↓                                              │
│   [4] Run 11 Analyzers                             │
│      ├─→ TrendAnalyzer                             │
│      ├─→ MomentumAnalyzer                          │
│      ├─→ VolumeAnalyzer                            │
│      ├─→ PatternAnalyzer (35+ patterns)            │
│      └─→ ... (7 more)                              │
│      ↓                                              │
│   [5] Determine Direction                          │
│      → LONG, SHORT, or None                        │
│      ↓                                              │
│   [6] SignalScorer.calculate_score()               │
│      ├─→ Base scores (10 analyzers)                │
│      ├─→ Apply weights                             │
│      ├─→ Calculate confluence                      │
│      └─→ Apply 13 multipliers                      │
│      ↓                                              │
│   [7] SignalValidator.validate()                   │
│      ↓                                              │
│   [Result] TimeframeSignal                         │
│                                                     │
└─────────────────────────────────────────────────────┘
    ↓
[Phase 2] MultiTimeframeAggregator
    ├─→ Calculate aggregate scores
    ├─→ Determine direction (with 30% margin)
    ├─→ Check consensus (75% agreement)
    ├─→ Calculate alignment factor
    └─→ Build final signal
    ↓
[خروجی] SignalInfo (Final Signal)
```

### 6.2 آمار و ارقام کلیدی

**کد سیستم:**
- **تعداد کل فایل‌ها:** 90+ فایل Python
- **تعداد خطوط کد:** ~50,000+ خط
- **Indicators:** 10 عدد
- **Analyzers:** 11 عدد (6535 خط)
- **Patterns:** 35+ الگو
- **ضرایب امتیازدهی:** 13 ضریب

**عملکرد:**
- **زمان پردازش:** ~2-5 ثانیه per symbol (با cache)
- **تعداد کندل:** 500 per timeframe
- **تعداد ستون اندیکاتور:** 20+
- **تعداد بررسی validation:** 10+

### 6.3 نقاط قوت سیستم جدید

✅ **1. ماژولار بودن:**
- هر بخش مستقل قابل تست است
- تغییرات راحت‌تر و ایمن‌تر
- افزودن Analyzer/Indicator جدید آسان

✅ **2. Cache و Performance:**
- TimeframeScoreCache جلوگیری از محاسبات تکراری
- Context Cache برای Multi-TF
- Indicator caching

✅ **3. وزن‌دهی پیشرفته:**
- Per-Timeframe weights
- 13 ضریب قابل تنظیم
- Confluence bonus

✅ **4. Consensus Check:**
- حداقل 75% تایم‌فریم‌ها باید موافق باشند
- جلوگیری از سیگنال‌های متضاد

✅ **5. Type Safety:**
- استفاده از Enums
- Constants برای magic numbers
- Dataclasses برای structures

✅ **6. Error Handling:**
- Try-catch در تمام سطوح
- Graceful degradation
- Detailed logging

✅ **7. سیستم‌های هوشمند:**
- Circuit Breaker (توقف اضطراری)
- Adaptive Learning (یادگیری از معاملات)
- Correlation Manager (مدیریت همبستگی)
- Market Regime Detector (تشخیص رژیم)

### 6.4 تفاوت کلیدی با سیستم قدیم

| معیار | سیستم قدیم | سیستم جدید |
|-------|-----------|-----------|
| **معماری** | 1 کلاس بزرگ | 90+ ماژول مستقل |
| **تست** | سخت | آسان (unit tests) |
| **Cache** | ❌ ندارد | ✅ چند لایه |
| **Patterns** | کد درهم | 35+ کلاس مستقل |
| **Consensus** | ❌ ندارد | ✅ 75% agreement |
| **Validation** | ساده | پیشرفته (10+ check) |
| **Weights** | ثابت | Per-TF configurable |
| **Error Recovery** | محدود | پیشرفته |

### 6.5 فرمول نهایی امتیازدهی

```python
# برای هر تایم‌فریم:
base_score = Σ(analyzer_score × weight)

final_score_per_tf = (
    base_score
    × (1 + confluence_bonus)    # 0-50%
    × timeframe_weight           # ±30%
    × trend_alignment            # ±20%
    × volume_confirmation        # 0-40%
    × pattern_quality            # 0-50%
    × 9 ضریب دیگر...
)

# ترکیب Multi-TF:
bullish_score = Σ(tf_score × tf_weight × phase_mult × macd_strength)
                for each TF where direction=bullish

bearish_score = Σ(...)

if bullish_score > bearish_score × 1.3:
    direction = LONG
    final_score = bullish_score × alignment_factor × volume_factor × htf_factor
```

### 6.6 حد نصاب‌های مهم

```python
# امتیاز
min_score = 80              # حداقل برای قبول
medium_threshold = 150      # آستانه متوسط/قوی

# Consensus
min_consensus = 0.75        # 75% تایم‌فریم‌ها موافق

# Direction Margin
direction_margin = 1.3      # 30% اختلاف

# Risk/Reward
min_rr_ratio = 2.0          # حداقل 1:2

# Confidence
min_confidence = 0.5        # حداقل اطمینان
high_confidence = 0.8       # اطمینان بالا

# Alignment
min_alignment = 0.7         # حداقل همراستایی
max_alignment = 1.3         # حداکثر همراستایی
```

---

## پیوست: مراجع کد اصلی

برای دسترسی به کد واقعی، به این فایل‌ها مراجعه کنید:

### هسته اصلی:
- `signal_generation/orchestrator.py:98-1275`
- `signal_generation/signal_scorer.py:27-876`
- `signal_generation/multi_tf_aggregator.py:44-822`

### اندیکاتورها:
- `signal_generation/analyzers/indicators/indicator_orchestrator.py:17-347`
- `signal_generation/analyzers/indicators/*.py` (10 فایل)

### تحلیلگران:
- `signal_generation/analyzers/trend_analyzer.py:48-548`
- `signal_generation/analyzers/momentum_analyzer.py:1-1303`
- `signal_generation/analyzers/*.py` (11 فایل، 6535 خط)

### الگوها:
- `signal_generation/analyzers/patterns/pattern_orchestrator.py`
- `signal_generation/analyzers/patterns/candlestick/*.py` (30+ فایل)
- `signal_generation/analyzers/patterns/chart/*.py` (5 فایل)

### سیستم‌های هوشمند:
- `signal_generation/systems/market_regime_detector.py`
- `signal_generation/systems/adaptive_learning_system.py`
- `signal_generation/systems/correlation_manager.py`
- `signal_generation/systems/emergency_circuit_breaker.py`

---

**پایان مستند**

این مستند توضیح کامل سیستم جدید تولید سیگنال را ارائه می‌دهد. برای سوالات بیشتر یا جزئیات فنی، به کد منبع مراجعه کنید.

