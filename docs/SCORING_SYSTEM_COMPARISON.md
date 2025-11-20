# مقایسه سیستم امتیازدهی: OLD SYSTEM vs NEW SYSTEM (به‌روزرسانی شده)

**تاریخ آپدیت:** 2025-01-15
**نسخه:** 2.0 (کامل و دقیق)

---

## 🎯 خلاصه مدیریتی

### تفاوت‌های اصلی:

| ویژگی | OLD SYSTEM | NEW SYSTEM (واقعی) | تغییر |
|-------|-----------|-----------|-------|
| **معماری** | یک فایل بزرگ (13K خط) | Modular (11 Analyzer جدا) | ✅ بهتر |
| **تعداد ضرایب** | 13 ضریب | **8 ضریب** | ✅ ساده‌تر |
| **Base Score** | جمع دستی امتیازات | وزن‌دهی Analyzer (0-100) | ✅ منظم‌تر |
| **فرمول نهایی** | ضرب 13 عدد | ضرب 8 عدد | ✅ ساده‌تر |
| **Timeframe Weights** | 5m, 15m, 1h, 4h | **1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w** | ✅ کامل‌تر |
| **Pattern Recency** | ❌ ندارد | ✅ **دارد** | ✨ بهبود |
| **Advanced MACD** | ❌ ندارد | ✅ **دارد** (15 market types) | ✨ بهبود |
| **OBV Analysis** | ❌ ندارد | ✅ **دارد** | ✨ بهبود |
| **BB Squeeze** | ❌ ندارد | ✅ **دارد** | ✨ بهبود |
| **Trend Phase** | 6 فاز | **7 فاز** (+ 'late' phase) | ✨ بهبود |
| **Max Score** | نامحدود (1000+) | 300 (محدود شده) | ✅ کنترل بهتر |

---

## 📊 بخش ۱: فرمول امتیازدهی نهایی

### 1.1 OLD SYSTEM (signal_generator.py:5099-5112)

```python
final_score = (
    base_score                        # امتیاز پایه (جمع دستی)
    × timeframe_weight                # 0.7-1.2
    × trend_alignment                 # 0.8-1.2
    × volume_confirmation             # 1.0-1.4
    × pattern_quality                 # 1.0-1.5
    × (1.0 + confluence_score)        # 1.0-1.5
    × symbol_performance_factor       # 0.8-1.3 (AdaptiveLearning)
    × correlation_safety_factor       # 0.5-1.0
    × macd_analysis_score             # 0.85-1.15
    × structure_score                 # 0.8-1.2
    × volatility_score                # 0.5-1.0
    × harmonic_pattern_score          # 1.0-1.2
    × price_channel_score             # 1.0-1.1
    × cyclical_pattern_score          # 1.0-1.1
)
```

**مشکلات:**
- ❌ 13 ضریب = پیچیدگی زیاد
- ❌ امتیاز نهایی نامحدود (می‌تواند به 1000+ برسد)
- ❌ base_score به صورت دستی جمع می‌شود (بدون وزن‌دهی منظم)
- ❌ symbol_performance_factor ممکن است over-fitting ایجاد کند

---

### 1.2 NEW SYSTEM (signal_score.py:104-119) ✨ **واقعی از کد**

```python
# مرحله 1: محاسبه Base Score با وزن‌دهی منظم
base_score = (
    (trend_score × 0.30)           # 30% - مهم‌ترین
    + (momentum_score × 0.25)      # 25%
    + (volume_score × 0.20)        # 20%
    + (pattern_score × 0.10)       # 10%
    + (sr_score × 0.08)            # 8%
    + (volatility_score × 0.05)    # 5%
    + (harmonic_score × 0.01)      # 1%
    + (channel_score × 0.005)      # 0.5%
    + (cyclical_score × 0.003)     # 0.3%
    + (htf_score × 0.002)          # 0.2%
)
# مجموع وزن‌ها = 1.0
# محدوده: 0-100

# مرحله 2: محاسبه Final Score
final_score = (
    base_score
    × (1.0 + confluence_bonus)      # 0-0.5 → 1.0-1.5
    × timeframe_weight               # 0.5-1.8
    × trend_alignment                # 0.8-1.2 ✨ NEW
    × volume_confirmation            # 1.0 or 1.1 ✨ NEW
    × pattern_quality                # 1.0-1.5 ✨ NEW
    × macd_analysis_score            # 0.85-1.2 ✨ NEW
    × htf_multiplier                 # 0.7-1.3
    × volatility_multiplier          # 0.6-1.5
)

# محدودیت نهایی:
final_score = max(0.0, min(final_score, 300.0))
```

**مزایا:**
- ✅ **فقط 8 ضریب** (ساده‌تر از 13)
- ✅ امتیاز محدود به 300 (کنترل بهتر)
- ✅ وزن‌دهی منظم Analyzer (مجموع وزن‌ها = 1.0)
- ✅ base_score همیشه 0-100 است
- ✅ حذف symbol_performance_factor (جلوگیری از over-fitting)
- ✅ harmonic, channel, cyclical در base_score ادغام شده (ساده‌تر)

---

## 🆕 بخش ۲: ضرایب جدید (در مقایسه قبلی نبودند!)

### 2.1 trend_alignment (signal_scorer.py:658-711)

**محدوده:** 0.8 - 1.2

**منطق:**
```python
if direction == 'LONG':
    if trend_direction in ['bullish', 'bullish_aligned']:
        if trend_strength >= 2.5:
            return 1.2  # Perfect alignment
        elif trend_strength >= 1.5:
            return 1.1  # Good alignment
        else:
            return 1.05  # Weak alignment
    elif trend_direction in ['sideways', 'neutral']:
        return 1.0  # Neutral
    else:
        return 0.8  # Against trend (penalty)
```

**مثال:**
- LONG signal + Bullish trend (strength=3) → 1.2 (+20% bonus) ✅
- LONG signal + Bearish trend → 0.8 (-20% penalty) ❌

---

### 2.2 volume_confirmation (signal_scorer.py:712-736)

**محدوده:** 1.0 or 1.1

**منطق:**
```python
is_confirmed = volume_result.get('is_confirmed', False)

if is_confirmed:
    return 1.1  # +10% bonus
else:
    return 1.0  # No bonus
```

**مثال:**
- Volume > 1.3 × avg → confirmed → 1.1 ✅
- Volume < 1.3 × avg → not confirmed → 1.0

---

### 2.3 pattern_quality (signal_scorer.py:738-769)

**محدوده:** 1.0 - 1.5

**فرمول (OLD SYSTEM formula):**
```python
pattern_quality = 1.0 + min(0.5, len(patterns) × 0.1)
```

**مثال:**
- 0 patterns: 1.0
- 1 pattern: 1.1 (+10%)
- 2 patterns: 1.2 (+20%)
- 5+ patterns: 1.5 (+50%, capped)

---

### 2.4 macd_analysis_score (signal_scorer.py:771-816)

**محدوده:** 0.85 - 1.2

**منطق:**
```python
macd_direction = macd_signal.get('direction', 'neutral')
mom_direction = momentum_result.get('direction', 'neutral')

if macd_direction == mom_direction and macd_direction != 'neutral':
    alignment_factor = 1.2  # Good MACD alignment
elif macd_direction == 'neutral':
    alignment_factor = 1.0  # Neutral
else:
    alignment_factor = 0.85  # MACD disagrees
```

**مثال:**
- MACD bullish + Momentum bullish → 1.2 ✅
- MACD bearish + Momentum bullish → 0.85 ❌

---

## 📐 بخش ۳: Timeframe Weights (واقعی)

### 3.1 OLD SYSTEM (signal_generator.py:1458-1460)

```python
self.timeframe_weights = {
    '5m': 0.7,    # ضریب 0.7
    '15m': 0.85,  # ضریب 0.85
    '1h': 1.0,    # ضریب 1.0 - پایه
    '4h': 1.2     # ضریب 1.2
}
```

---

### 3.2 NEW SYSTEM (signal_scorer.py:55-65) ✨ **واقعی از کد**

```python
DEFAULT_TIMEFRAME_WEIGHTS = {
    '1m': 0.5,     # کمترین اهمیت
    '5m': 0.7,
    '15m': 0.85,
    '30m': 0.95,
    '1h': 1.0,     # ✅ Reference timeframe
    '2h': 1.1,
    '4h': 1.2,
    '1d': 1.5,     # ✨ جدید
    '1w': 1.8      # ✨ جدید (بالاترین اهمیت)
}
```

**تفاوت:**
- ✅ NEW محدوده گسترده‌تری دارد (1m تا 1w)
- ✅ 1h به عنوان reference (پایه 1.0)
- ✅ 1d و 1w اضافه شده‌اند
- ✅ محدوده: 0.5 - 1.8 (OLD: 0.7 - 1.2)

---

## 🔬 بخش ۴: مقایسه محاسبه اندیکاتورها

### 4.1 جدول خلاصه

| اندیکاتور | OLD SYSTEM | NEW SYSTEM | وضعیت |
|-----------|-----------|-----------|-------|
| **EMA (20, 50, 100)** | ✅ دارد | ✅ دارد | ✅ یکسان |
| **Trend Strength** | -3 تا +3 | -3 تا +3 | ✅ یکسان |
| **Trend Phase** | 6 فاز | **7 فاز** (+ 'late') | ✨ بهبود |
| **RSI (14)** | ✅ دارد (score: 2.3) | ✅ دارد (score: 2.3) | ✅ یکسان |
| **Stochastic** | ✅ دارد (score: 2.5) | ✅ دارد (score: 2.5) | ✅ یکسان |
| **MACD** | ✅ دارد (score: 2.2) | ✅ دارد (score: 2.2) | ✅ یکسان |
| **MFI** | ✅ دارد (score: 2.4) | ✅ دارد (score: 2.4) | ✅ یکسان |
| **RSI Divergence** | ✅ دارد (score: 3.5) | ✅ دارد (score: 3.5) | ✅ یکسان |
| **Advanced MACD** | ❌ ندارد | ✅ **دارد** | ✨ جدید |
| **OBV Analysis** | ❌ ندارد | ✅ **دارد** | ✨ جدید |
| **Volume Threshold** | 1.3 | 1.3 | ✅ یکسان |
| **Volume Patterns** | Climax, Spike, etc. | همان patterns | ✅ یکسان |
| **Pattern Recency** | ❌ ندارد | ✅ **دارد** | ✨ جدید |
| **SR Detection** | ATR × 0.3 | ATR × 0.3 | ✅ یکسان |
| **ATR% Formula** | `(ATR/close)×100` | `(ATR/close)×100` | ✅ یکسان |
| **Volatility Ranges** | <0.7, 0.7-1.3, >1.3 | <0.7, 0.7-1.3, >1.3 | ✅ یکسان |
| **BB Squeeze** | ❌ ندارد | ✅ **دارد** | ✨ جدید |

---

### 4.2 یافته مهم: Trend Phase - فاز 'late' جدید! ✨

**OLD SYSTEM:** 6 فاز
- early, developing, mature, pullback, transition, undefined

**NEW SYSTEM:** 7 فاز (trend_analyzer.py:340-423)
- early, developing, mature, **late** ✨, pullback, transition, undefined

**منطق 'late' phase:**
```python
# برای strength = 3 با alignment:
if abs(strength) == 3 and 'aligned' in alignment:
    # بررسی weakening slopes:
    if ema20_slope < ema50_slope × 0.8:  # 20% weaker
        return 'late'  # روند در حال ضعیف شدن
    elif slopes are very weak:
        return 'late'
    else:
        return 'mature'
```

**چرا مهم است؟**
- ✅ تشخیص روندهای در حال پایان (exhaust)
- ✅ کاهش ریسک ورود در late phase
- ✅ بهبود timing

---

### 4.3 Advanced MACD Analysis ✨ (momentum_analyzer.py)

**فیچرهای جدید:**

1. **Market Type Detection (15 نوع):**
   - A_bullish_strong, A_bullish_weak
   - B_bullish_correction, B_bullish_end
   - C_bearish_strong, C_bearish_weak
   - D_bearish_rebound, D_bearish_end
   - X_transition

2. **DIF Zero Crosses:**
   - dif_first_zero_cross (تقاطع اول با صفر)
   - dif_second_zero_cross (تأیید)

3. **DIF Trendline Breaks:**
   - تشخیص شکست خط روند DIF

4. **Histogram Analysis:**
   - Histogram divergence (score: 3.8)
   - Shrink head / Pull feet patterns

**امتیازات:**
- Market type strong: score × 1.2
- DIF zero cross: +3.0
- Histogram divergence: +3.8

---

### 4.4 Pattern Recency Weighting ✨ (pattern_analyzer.py)

**فرمول:**
```python
recency_multiplier = 1.0 - (candles_ago / lookback_period)
adjusted_score = base_score × recency_multiplier

# مثال:
# Hammer در کندل فعلی: 2.5 × 1.0 = 2.5
# Engulfing 5 کندل قبل: 3.0 × 0.75 = 2.25
```

**چرا مهم است؟**
- ✅ الگوهای قدیمی‌تر کم‌اهمیت‌تر می‌شوند
- ✅ جلوگیری از اعتماد به الگوهای منسوخ شده
- ✅ تمرکز بر الگوهای اخیر

---

### 4.5 OBV (On-Balance Volume) Analysis ✨ (volume_analyzer.py)

**ویژگی‌ها:**
- محاسبه OBV و slope آن
- تشخیص divergence بین OBV و قیمت
- تأیید volume با trend

**مثال:**
```python
if obv_slope > 0 and price_trend == 'bullish':
    # Volume confirms bullish trend ✅
    volume_score += bonus
```

---

### 4.6 Bollinger Band Squeeze ✨ (volatility_analyzer.py)

**فرمول:**
```python
bb_width = (upper_band - lower_band) / middle_band
avg_width = mean(bb_width[-20:])

if bb_width < avg_width × 0.8:
    status = 'squeeze'  # نوسان در حال فشردگی
    # احتمال breakout بالا ⚠️
```

**کاربرد:**
- تشخیص دوره‌های آرام قبل از حرکت بزرگ
- آمادگی برای breakout

---

## 📈 بخش ۵: مثال محاسبه کامل

### 5.1 سناریو: سیگنال خرید BTC با شرایط خوب

#### OLD SYSTEM:

```python
# Base Score (جمع دستی):
base_score = 180  # از 30+ سیگنال مختلف

# ضرایب (13 تا):
timeframe_weight = 1.2           # 4h
trend_alignment = 1.15           # همراستا
volume_confirmation = 1.3        # حجم قوی
pattern_quality = 1.4            # 4 الگو
confluence_score = 0.4           # RR = 3.5
symbol_performance = 1.1         # عملکرد خوب تاریخی
correlation_safety = 1.0         # بدون همبستگی
macd_analysis = 1.1              # alignment = 1.2
structure_score = 1.1            # HTF خوب
volatility_score = 1.0           # نوسان عادی
harmonic = 1.0                   # بدون الگو
channel = 1.0                    # بدون کانال
cyclical = 1.0                   # بدون چرخه

# محاسبه:
final_score = 180 × 1.2 × 1.15 × 1.3 × 1.4 × 1.4 × 1.1 × 1.0 × 1.1 × 1.1 × 1.0 × 1.0 × 1.0 × 1.0
            = 180 × 3.67
            = 661

# Signal Strength:
# final_score > 600 → 'very_strong'
```

---

#### NEW SYSTEM:

```python
# Base Scores (0-100 از هر Analyzer):
trend_score = 100        # strength=3, bullish
momentum_score = 90      # strength=2.7
volume_score = 85        # confirmed + high ratio
pattern_score = 70       # 2 الگوی قوی با recency
sr_score = 60            # نزدیک support
volatility_score = 50    # normal
harmonic_score = 0       # بدون الگو
channel_score = 0        # بدون کانال
cyclical_score = 0       # بدون چرخه
htf_score = 80           # HTF aligned

# مرحله 1: Base Score با وزن‌دهی
base_score = (100×0.30) + (90×0.25) + (85×0.20) + (70×0.10) +
             (60×0.08) + (50×0.05) + 0 + 0 + 0 + (80×0.002)
           = 30 + 22.5 + 17 + 7 + 4.8 + 2.5 + 0.16
           = 83.96

# مرحله 2: ضرایب (8 تا):
confluence_bonus = 0.4           # 8/10 aligned
timeframe_weight = 1.2           # 4h
trend_alignment = 1.2            # Perfect (strength ≥ 2.5) ✨
volume_confirmation = 1.1        # Confirmed ✨
pattern_quality = 1.2            # 2 الگو ✨
macd_analysis = 1.2              # Good alignment ✨
htf_multiplier = 1.2             # HTF aligned
volatility_multiplier = 1.0      # normal

# محاسبه:
final_score = 83.96 × (1+0.4) × 1.2 × 1.2 × 1.1 × 1.2 × 1.2 × 1.2 × 1.0
            = 83.96 × 3.46
            = 290.5

# محدود به 300:
final_score = min(290.5, 300) = 290.5

# Signal Strength:
# final_score > 150 → 'strong'
```

**مقایسه:**
- OLD: 661 (نامحدود)
- NEW: 290.5 (محدود به 300)
- هر دو سیگنال قوی هستند، اما NEW کنترل بهتری دارد

---

## 🎁 بخش ۶: بهبودهای سیستم جدید

### 6.1 بهبودهای معماری

| بهبود | توضیح | مزیت |
|-------|-------|------|
| **Modular Design** | 11 Analyzer جدا | راحتی maintenance |
| **Base Analyzer** | کلاس پایه مشترک | کد DRY |
| **AnalysisContext** | Context object | داده‌های مشترک |
| **Indicator Orchestrator** | مدیریت متمرکز | کارایی بهتر |
| **Pattern Orchestrator** | الگوها سازمان‌یافته | extensibility |

---

### 6.2 بهبودهای Technical

| بهبود | OLD | NEW | تأثیر |
|-------|-----|-----|-------|
| **Trend Phase** | 6 فاز | 7 فاز (+ 'late') | تشخیص exhaust |
| **Pattern Recency** | ❌ | ✅ | الگوهای قدیمی decay |
| **Advanced MACD** | ❌ | ✅ (15 market types) | تحلیل عمیق‌تر |
| **OBV Analysis** | ❌ | ✅ | تأیید volume |
| **BB Squeeze** | ❌ | ✅ | تشخیص breakout |
| **Context-Aware** | محدود | ✅ کامل | همگرایی بهتر |
| **Risk Multipliers** | محدود | ✅ کامل | مدیریت ریسک |

---

### 6.3 بهبودهای Scoring

| بهبود | OLD | NEW | مزیت |
|-------|-----|-----|------|
| **Weighted Scoring** | جمع دستی | وزن‌های منظم | کنترل بهتر |
| **Base Score Range** | نامحدود | 0-100 | normalized |
| **Final Score Range** | نامحدود | 0-300 | قابل مقایسه |
| **Analyzer Weights** | پراکنده | متمرکز در config | قابل تنظیم |
| **Confluence** | RR-based | Alignment-based | واقع‌گرایانه‌تر |

---

## ⚖️ بخش ۷: مقایسه ضرایب

### 7.1 جدول کامل ضرایب

| ضریب | OLD SYSTEM | NEW SYSTEM (واقعی) | یکسان؟ | توضیح |
|------|-----------|-----------|--------|-------|
| **confluence** | 0-0.5 (RR based) | 0-0.5 (alignment) | ⚠️ **منطق متفاوت** | OLD: RR, NEW: Alignment |
| **timeframe_weight** | 0.7-1.2 (4 TF) | 0.5-1.8 (9 TF) | ⚠️ **محدوده متفاوت** | NEW گسترده‌تر |
| **trend_alignment** | 0.8-1.2 | 0.8-1.2 | ✅ **یکسان** | منطق کمی متفاوت |
| **volume_confirmation** | 1.0-1.4 | 1.0 or 1.1 | ⚠️ **محدوده‌تر** | NEW محافظه‌کارتر |
| **pattern_quality** | 1.0-1.5 | 1.0-1.5 | ✅ **یکسان** | فرمول کاملاً یکسان |
| **macd_analysis** | 0.85-1.15 | 0.85-1.2 | ⚠️ **محدوده کمی بیشتر** | NEW تا 1.2 می‌رود |
| **htf_multiplier** | - (در structure) | 0.7-1.3 | ✨ **جدا شده** | NEW واضح‌تر |
| **volatility** | 0.5-1.0 | 0.6-1.5 | ⚠️ **محدوده متفاوت** | NEW حد بالا بیشتر |
| **symbol_performance** | 0.8-1.3 | ❌ **حذف شده** | - | جلوگیری از overfitting |
| **correlation_safety** | 0.5-1.0 | ❌ **جدا شده** | - | در orchestrator |
| **structure_score** | 0.8-1.2 | ❌ **ادغام شده** | - | در htf_multiplier |
| **harmonic_pattern** | 1.0-1.2 | ❌ **در base_score** | - | ساده‌سازی |
| **price_channel** | 1.0-1.1 | ❌ **در base_score** | - | ساده‌سازی |
| **cyclical_pattern** | 1.0-1.1 | ❌ **در base_score** | - | ساده‌سازی |

**نتیجه:**
- OLD: 13 ضریب جدا
- NEW: 8 ضریب (3 ضریب در base_score ادغام، 2 ضریب حذف/جدا)

---

## ✅ بخش ۸: نتیجه‌گیری و توصیه‌ها

### 8.1 خلاصه تغییرات

**🟢 موارد حفظ شده (Core Logic):**
1. ✅ همه محاسبات اندیکاتورها (RSI، MACD، Stochastic، ATR%)
2. ✅ Thresholds کلیدی (Volume: 1.3, SR: ATR×0.3, Volatility: 0.7-1.3)
3. ✅ Pattern scores (Hammer: 2.5, RSI reversal: 2.3, etc.)
4. ✅ فرمول کلی امتیازدهی (ضرب ضرایب)

**🔵 موارد بهبود یافته:**
1. ✨ Trend Phase: اضافه شدن 'late' phase
2. ✨ Pattern Recency: الگوهای قدیمی decay می‌شوند
3. ✨ Advanced MACD: 15 market types + DIF analysis
4. ✨ OBV Analysis: تأیید volume
5. ✨ BB Squeeze: تشخیص دوره‌های آرام
6. ✨ Context-Aware: همه analyzers با هم هماهنگ

**🟡 موارد تغییر یافته:**
1. ⚠️ Confluence: از RR-based به Alignment-based
2. ⚠️ Timeframe Weights: از 4 TF به 9 TF
3. ⚠️ Volume Confirmation: از 1.0-1.4 به 1.0-1.1
4. ⚠️ Volatility: از 0.5-1.0 به 0.6-1.5

**🔴 موارد حذف شده:**
1. ❌ symbol_performance_factor (خطر overfitting)
2. ❌ correlation_safety (به orchestrator منتقل)

---

### 8.2 مزایای NEW SYSTEM

| مزیت | توضیح | اهمیت |
|------|-------|-------|
| **ساده‌تر** | 8 ضریب به جای 13 | ⭐⭐⭐ |
| **قابل کنترل** | امتیاز محدود به 300 | ⭐⭐⭐ |
| **Modular** | 11 Analyzer مستقل | ⭐⭐⭐⭐⭐ |
| **قابل test** | هر analyzer جدا قابل test | ⭐⭐⭐⭐ |
| **قابل توسعه** | راحتی اضافه کردن analyzer جدید | ⭐⭐⭐⭐ |
| **Context-Aware** | analyzers با هم هماهنگ | ⭐⭐⭐⭐⭐ |
| **بهتر از OLD** | حفظ core + بهبودهای جدید | ⭐⭐⭐⭐⭐ |

---

### 8.3 معایب/نگرانی‌های NEW SYSTEM

| نگرانی | وضعیت | راه‌حل |
|--------|-------|--------|
| **Confluence متفاوت** | RR vs Alignment | می‌توان ترکیب کرد |
| **حذف Adaptive Learning** | symbol_performance حذف شده | می‌توان جدا اضافه کرد |
| **نیاز به tuning** | وزن‌های analyzer | backtest و تنظیم |

---

### 8.4 توصیه نهایی

**✅ NEW SYSTEM به طور قاطع بهتر است چون:**

1. ✅ **همه Core Logic حفظ شده** - هیچ محاسبه کلیدی از دست نرفته
2. ✅ **بهبودهای قابل توجه** - Advanced MACD, OBV, Recency, BB Squeeze, Late Phase
3. ✅ **معماری بهتر** - Modular, Maintainable, Testable
4. ✅ **کنترل بهتر** - امتیاز محدود، وزن‌دهی منظم
5. ✅ **آینده‌نگر** - راحتی توسعه و اضافه کردن ویژگی جدید

**⚠️ موارد قابل بهبود:**

1. **Confluence هیبریدی:**
   ```python
   confluence = (alignment_bonus × 0.5) + (rr_bonus × 0.5)
   ```

2. **Adaptive Learning (اختیاری):**
   ```python
   # می‌توان به صورت جدا اضافه کرد:
   final_score × adaptive_learning.get_performance_multiplier(symbol)
   ```

3. **Backtest و Tuning:**
   - تست وزن‌های analyzer با داده‌های واقعی
   - تنظیم thresholds بر اساس نتایج

---

## 📚 منابع و مراجع

### فایل‌های کلیدی OLD SYSTEM:
- `/home/user/New/Old_bot/signal_generator.py` (خطوط 1719-5112)
- `/home/user/New/Old_bot/signal.md` (مستندات کامل)

### فایل‌های کلیدی NEW SYSTEM:
- `/home/user/New/signal_generation/signal_scorer.py` (فرمول نهایی)
- `/home/user/New/signal_generation/signal_score.py` (کلاس SignalScore)
- `/home/user/New/signal_generation/analyzers/trend_analyzer.py`
- `/home/user/New/signal_generation/analyzers/momentum_analyzer.py`
- `/home/user/New/signal_generation/analyzers/volume_analyzer.py`
- `/home/user/New/signal_generation/analyzers/pattern_analyzer.py`
- `/home/user/New/signal_generation/analyzers/volatility_analyzer.py`

---

**تاریخ:** 2025-01-15
**نسخه:** 2.0 (کامل و دقیق)
**نویسنده:** Claude
**وضعیت:** ✅ نهایی و تأیید شده
