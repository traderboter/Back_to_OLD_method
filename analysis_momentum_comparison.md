# مقایسه جامع: MomentumAnalyzer جدید vs analyze_momentum_indicators() قدیمی

## مقدمه

این سند به مقایسه دقیق بین سیستم تحلیل momentum در دو نسخه قدیم و جدید می‌پردازد.

---

## 📊 خلاصه کلی

| جنبه | سیستم قدیمی | سیستم جدید | وضعیت |
|------|------------|-----------|--------|
| **محاسبه اندیکاتورها** | درون تابع (با کش) | IndicatorCalculator جداگانه | ✅ بهبود معماری |
| **تعداد سیگنال‌ها** | 6 نوع سیگنال | 6 نوع + Advanced MACD | ✅ افزایش یافته |
| **Divergence Detection** | ساده (rolling window) | پیشرفته (peak finding) | ⚠️ **تغییر روش** |
| **Per-TF Thresholds** | ❌ ندارد | ✅ دارد | ✅ بهبود |
| **Context-Aware** | ❌ مستقل از trend | ✅ با trend هماهنگ | ✅ بهبود |
| **Market Type Detection** | ❌ ندارد | ✅ دارد (A/B/C/D/X) | ✅ ویژگی جدید |
| **امتیازات Pattern** | یکسان همه TF ها | Per-TF قابل تنظیم | ✅ بهبود |

---

## بخش 1: مقایسه محاسبه اندیکاتورها

### 1.1 RSI (Relative Strength Index)

#### محاسبه RSI

**قدیمی:**
```python
# signal_generator.py:3538
rsi = talib.RSI(close_prices, timeperiod=14)
# محاسبه درون تابع با cache
```

**جدید:**
```python
# از IndicatorCalculator پیش‌محاسبه شده
current_rsi = df['rsi'].iloc[-1]
# RSI قبلاً توسط IndicatorCalculator محاسبه شده
```

✅ **نتیجه:** هر دو از `talib.RSI` با period=14 استفاده می‌کنند → **یکسان**

---

#### شرایط RSI Signals

**قدیمی:**
```python
# خط 3610-3619
# Oversold Reversal:
if curr_rsi < 30 and curr_rsi > prev_rsi:
    signal = 'rsi_oversold_reversal'
    score = 2.3

# Overbought Reversal:
elif curr_rsi > 70 and curr_rsi < prev_rsi:
    signal = 'rsi_overbought_reversal'
    score = 2.3
```

**جدید:**
```python
# momentum_analyzer.py:308-312
# Oversold Reversal:
oversold_reversal = current_rsi < rsi_oversold and current_rsi > prev_rsi
overbought_reversal = current_rsi > rsi_overbought and current_rsi < prev_rsi

# با per-TF thresholds:
rsi_overbought = self.get_threshold('rsi_overbought', 70, timeframe)
rsi_oversold = self.get_threshold('rsi_oversold', 30, timeframe)
```

✅ **نتیجه:** منطق دقیقاً یکسان است، اما جدید از **per-timeframe thresholds** پشتیبانی می‌کند

**مقادیر در config.yaml:**
```yaml
5m:  oversold=39, overbought=60
15m: oversold=42, overbought=57
1h:  oversold=41, overbought=59
4h:  oversold=44, overbought=55
```

⚠️ **نکته مهم:** threshold های جدید با سیستم قدیمی (30/70) متفاوت است!

---

### 1.2 MACD (Moving Average Convergence Divergence)

#### محاسبه MACD

**قدیمی:**
```python
# خط 3532
macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
```

**جدید:**
```python
# از IndicatorCalculator:
current_macd = df['macd'].iloc[-1]
current_macd_signal = df['macd_signal'].iloc[-1]
current_macd_hist = df['macd_hist'].iloc[-1]
```

✅ **نتیجه:** هر دو از `talib.MACD(12, 26, 9)` استفاده می‌کنند → **یکسان**

---

#### MACD Signals

**سیگنال 1: MACD Crossover**

**قدیمی:**
```python
# خط 3586-3595
if curr_macd > curr_sig and prev_macd <= prev_sig:
    signal = 'macd_bullish_crossover'
    score = 2.2
elif curr_macd < curr_sig and prev_macd >= prev_sig:
    signal = 'macd_bearish_crossover'
    score = 2.2
```

**جدید:**
```python
# momentum_analyzer.py:343-346
bullish_crossover = (prev_macd <= prev_signal and current_macd > current_signal)
bearish_crossover = (prev_macd >= prev_signal and current_macd < current_signal)
```

✅ **نتیجه:** منطق دقیقاً یکسان است

---

**سیگنال 2: MACD Zero Line Cross**

**قدیمی:**
```python
# خط 3598-3607
if curr_macd > 0 and prev_macd <= 0:
    signal = 'macd_bullish_zero_cross'
    score = 1.8
elif curr_macd < 0 and prev_macd >= 0:
    signal = 'macd_bearish_zero_cross'
    score = 1.8
```

**جدید:**
```python
# momentum_analyzer.py (متد جداگانه: _check_macd_zero_cross)
# همان شرایط با امتیاز یکسان
```

✅ **نتیجه:** منطق و امتیازات یکسان است

---

### 1.3 Stochastic Oscillator

#### محاسبه Stochastic

**قدیمی:**
```python
# خط 3546
slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
```

**جدید:**
```python
# از IndicatorCalculator:
current_slowk = df['slowk'].iloc[-1]
current_slowd = df['slowd'].iloc[-1]
```

✅ **نتیجه:** هر دو از `talib.STOCH(14, 3, 3)` استفاده می‌کنند → **یکسان**

---

#### Stochastic Signals

**قدیمی:**
```python
# خط 3622-3631
# Oversold Bullish Cross:
if curr_k < 20 and curr_d < 20 and curr_k > curr_d and prev_k <= prev_d:
    signal = 'stochastic_oversold_bullish_cross'
    score = 2.5

# Overbought Bearish Cross:
elif curr_k > 80 and curr_d > 80 and curr_k < curr_d and prev_k >= prev_d:
    signal = 'stochastic_overbought_bearish_cross'
    score = 2.5
```

**جدید:**
```python
# momentum_analyzer.py (متد _analyze_stochastic)
# همان شرایط اما با per-TF thresholds:
stoch_overbought = self.get_threshold('stoch_overbought', 80, timeframe)
stoch_oversold = self.get_threshold('stoch_oversold', 20, timeframe)
```

✅ **نتیجه:** منطق یکسان، اما threshold ها per-TF قابل تنظیم هستند

---

### 1.4 MFI (Money Flow Index)

#### محاسبه MFI

**قدیمی:**
```python
# خط 3557
mfi = talib.MFI(high, low, close, volume, timeperiod=14)
```

**جدید:**
```python
# از IndicatorCalculator (اگر volume موجود باشد)
current_mfi = df['mfi'].iloc[-1] if 'mfi' in df.columns else None
```

✅ **نتیجه:** هر دو از `talib.MFI(14)` استفاده می‌کنند → **یکسان**

---

#### MFI Signals

**قدیمی:**
```python
# خط 3634-3644
if curr_mfi < 20 and curr_mfi > prev_mfi:
    signal = 'mfi_oversold_reversal'
    score = 2.4
elif curr_mfi > 80 and curr_mfi < prev_mfi:
    signal = 'mfi_overbought_reversal'
    score = 2.4
```

**جدید:**
```python
# momentum_analyzer.py (متد _check_mfi_signals)
# همان منطق با همان thresholds (20/80)
```

✅ **نتیجه:** منطق و threshold ها یکسان است

---

## بخش 2: مقایسه Divergence Detection

این بخش **مهم‌ترین تفاوت** است!

### 2.1 روش قدیمی (Simple Rolling Window)

**قدیمی:**
```python
# signal_generator.py:2873-2920
# خط 3649
rsi_divergences = self._detect_divergence_generic(close_s, rsi_s, 'rsi')

# الگوریتم:
# 1. محاسبه peaks و valleys با find_peaks_and_valleys()
# 2. استفاده از scipy.signal.find_peaks
# 3. پارامترها:
#    - distance=5
#    - prominence_factor=0.05 (برای قیمت)
#    - prominence_factor=0.1 (برای اندیکاتور)
```

**نحوه کار:**
```python
# 1. یافتن قله‌ها و دره‌ها با scipy
price_peaks_idx, price_valleys_idx = find_peaks_and_valleys(price, ...)
ind_peaks_idx, ind_valleys_idx = find_peaks_and_valleys(indicator, ...)

# 2. مقایسه آخرین قله/دره با قبلی
if len(price_valleys_idx) >= 2 and len(ind_valleys_idx) >= 2:
    # Bullish Divergence: price LL but RSI HL
    if price[valleys[-1]] < price[valleys[-2]] and \
       indicator[valleys[-1]] > indicator[valleys[-2]]:
        divergence = 'rsi_bullish_divergence'
        score = 3.5
```

**امتیازات:**
- `rsi_bullish_divergence`: **3.5** (بالاترین امتیاز!)
- `rsi_bearish_divergence`: **3.5**

---

### 2.2 روش جدید (Rolling Window با Center=True)

**جدید:**
```python
# momentum_analyzer.py:500-560
def _detect_divergences(self, df: pd.DataFrame):
    lookback = min(self.divergence_lookback, len(df))  # default: 14
    recent_df = df.tail(lookback)

    # یافتن lows/highs با rolling window (center=True)
    price_lows = recent_df['low'].rolling(window=3, center=True).min()
    price_highs = recent_df['high'].rolling(window=3, center=True).max()
    rsi_lows = recent_df['rsi'].rolling(window=3, center=True).min()
    rsi_highs = recent_df['rsi'].rolling(window=3, center=True).max()

    # Bullish Divergence:
    if len(price_lows) >= 6:
        price_lower_low = price_lows.iloc[-1] < price_lows.iloc[-5]
        rsi_higher_low = rsi_lows.iloc[-1] > rsi_lows.iloc[-5]

        if price_lower_low and rsi_higher_low:
            return {
                'type': 'bullish',
                'strength': 'strong' if rsi_lows.iloc[-1] < 40 else 'moderate'
            }
```

---

### 2.3 مقایسه دو روش

| جنبه | روش قدیمی | روش جدید | تفاوت |
|------|----------|---------|-------|
| **الگوریتم** | scipy.signal.find_peaks | rolling().min/max() | 🔴 **متفاوت** |
| **Lookback** | 20+ کندل | 14 کندل | 🟡 کوتاه‌تر |
| **Peak Detection** | پیچیده (prominence-based) | ساده (window-based) | 🔴 **متفاوت** |
| **مقایسه** | آخرین با قبلی | iloc[-1] با iloc[-5] | 🟡 فاصله ثابت |
| **Strength** | ❌ ندارد | 'strong' / 'moderate' | ✅ جدید |
| **امتیازدهی** | مستقیماً 3.5 | در _generate_signals | 🟡 متفاوت |

**⚠️ نتیجه:** روش‌های divergence detection کاملاً متفاوت است!

**تأثیر:**
- روش قدیمی **حساس‌تر** است (prominence-based)
- روش جدید **ساده‌تر** و **سریع‌تر** است
- ممکن است divergence های متفاوتی تشخیص دهند!

---

## بخش 3: ویژگی‌های جدید (موجود در سیستم جدید)

### 3.1 Advanced MACD Analysis

**سیستم جدید دارای تحلیل‌های پیشرفته MACD است:**

#### 1. Market Type Detection (A/B/C/D/X)

```python
# momentum_analyzer.py (متد _detect_macd_market_type)
# تشخیص نوع بازار بر اساس MACD:
# - Type A: قوی صعودی (MACD > 0, DIF > DEA)
# - Type B: ضعیف صعودی (MACD < 0, DIF > DEA)
# - Type C: ضعیف نزولی (MACD > 0, DIF < DEA)
# - Type D: قوی نزولی (MACD < 0, DIF < DEA)
# - Type X: نامشخص
```

❌ **در سیستم قدیمی موجود نیست!**

---

#### 2. DIF Zero Cross Counting

```python
# momentum_analyzer.py (متد _detect_dif_zero_crosses)
# شمارش تعداد دفعات عبور DIF از خط صفر:
# - first_bullish_zero_cross
# - second_bullish_zero_cross
# - first_bearish_zero_cross
# - second_bearish_zero_cross
```

❌ **در سیستم قدیمی موجود نیست!**

---

#### 3. DIF Trendline Breaks

```python
# momentum_analyzer.py (متد _detect_dif_trendline_breaks)
# تشخیص شکست trendline روی DIF:
# - dif_bullish_trendline_break
# - dif_bearish_trendline_break
```

❌ **در سیستم قدیمی موجود نیست!**

---

#### 4. Advanced Histogram Analysis

```python
# momentum_analyzer.py (متد _analyze_macd_histogram_advanced)
# تحلیل پیشرفته هیستوگرام:
# - macd_hist_bullish_reversal (3 کندل متوالی افزایش)
# - macd_hist_bearish_reversal (3 کندل متوالی کاهش)
```

❌ **در سیستم قدیمی موجود نیست!**

---

### 3.2 Context-Aware Scoring

```python
# momentum_analyzer.py:197-203
# هماهنگی با trend:
trend_context = context.get_result('trend')
if trend_context:
    momentum_result = self._adjust_for_trend_alignment(
        momentum_result,
        trend_context
    )

# اگر momentum با trend همراستا باشد → امتیاز بیشتر
# اگر مخالف باشد → امتیاز کمتر
```

❌ **در سیستم قدیمی موجود نیست!** (momentum مستقل از trend تحلیل می‌شود)

---

### 3.3 Per-Timeframe Thresholds

**جدید:**
```python
# استفاده از BaseAnalyzer.get_threshold()
rsi_overbought = self.get_threshold('rsi_overbought', 70, timeframe)
rsi_oversold = self.get_threshold('rsi_oversold', 30, timeframe)
```

**مقادیر در config.yaml:**
```yaml
momentum_analyzer:
  per_timeframe:
    enabled: true
    5m:
      rsi_oversold: 39
      rsi_overbought: 60
    4h:
      rsi_oversold: 44
      rsi_overbought: 55
```

❌ **در سیستم قدیمی ندارد** (همیشه 30/70 استفاده می‌شود)

---

## بخش 4: مقایسه امتیازدهی (Scoring)

### 4.1 سیگنال‌های مشترک و امتیازات

| سیگنال | امتیاز قدیمی | امتیاز جدید | یکسان؟ |
|--------|------------|-----------|-------|
| `macd_bullish_crossover` | 2.2 | 2.2 | ✅ |
| `macd_bearish_crossover` | 2.2 | 2.2 | ✅ |
| `macd_bullish_zero_cross` | 1.8 | 1.8 | ✅ |
| `macd_bearish_zero_cross` | 1.8 | 1.8 | ✅ |
| `rsi_oversold_reversal` | 2.3 | 2.3 | ✅ |
| `rsi_overbought_reversal` | 2.3 | 2.3 | ✅ |
| `rsi_bullish_divergence` | **3.5** | **3.5** | ✅ |
| `rsi_bearish_divergence` | **3.5** | **3.5** | ✅ |
| `stochastic_oversold_bullish_cross` | 2.5 | 2.5 | ✅ |
| `stochastic_overbought_bearish_cross` | 2.5 | 2.5 | ✅ |
| `mfi_oversold_reversal` | 2.4 | 2.4 | ✅ |
| `mfi_overbought_reversal` | 2.4 | 2.4 | ✅ |

✅ **نتیجه:** تمام امتیازات یکسان است!

---

### 4.2 محاسبه Direction و Strength

**قدیمی:**
```python
# خط 3655-3666
bullish_score = sum(s['score'] for s in signals if 'bullish' in s['type'])
bearish_score = sum(s['score'] for s in signals if 'bearish' in s['type'])

if bullish_score > bearish_score:
    direction = 'bullish'
elif bearish_score > bullish_score:
    direction = 'bearish'
else:
    direction = 'neutral'

# ⚠️ توجه: strength محاسبه نمی‌شود!
```

**جدید:**
```python
# momentum_analyzer.py (متد _calculate_momentum)
bullish_score = sum(signal['score'] for signal in all_signals if signal['direction'] == 'bullish')
bearish_score = sum(signal['score'] for signal in all_signals if signal['direction'] == 'bearish')

net_score = bullish_score - bearish_score
direction = 'bullish' if net_score > 0 else 'bearish' if net_score < 0 else 'neutral'

# محاسبه strength (capped at 3):
strength = min(abs(net_score) / 3.0, 3.0)
```

✅ **نتیجه:** منطق مشابه، اما جدید `strength` محاسبه می‌کند

---

## بخش 5: خلاصه تفاوت‌های کلیدی

### ✅ موارد یکسان (حفظ شده)

1. ✅ **محاسبه اندیکاتورها** (RSI, MACD, Stochastic, MFI) دقیقاً یکسان
2. ✅ **شرایط تشخیص سیگنال‌ها** (6 سیگنال اصلی) یکسان
3. ✅ **امتیازات pattern** یکسان (2.2, 2.3, 2.5, 3.5)
4. ✅ **منطق کلی** (bullish/bearish scoring) مشابه

---

### 🔴 تفاوت‌های حیاتی (Critical Differences)

#### 1️⃣ **Divergence Detection - تفاوت اساسی!**

| جنبه | قدیمی | جدید |
|------|-------|------|
| الگوریتم | scipy.signal.find_peaks | rolling().min/max() |
| پیچیدگی | پیشرفته | ساده |
| حساسیت | بالا | متوسط |
| سرعت | کندتر | سریع‌تر |

**تأثیر:** ممکن است divergence های متفاوتی تشخیص دهند!

---

#### 2️⃣ **Per-Timeframe Thresholds**

**قدیمی:**
- RSI: همیشه 30/70
- Stochastic: همیشه 20/80

**جدید:**
- RSI در 5m: 39/60 (سخت‌تر!)
- RSI در 4h: 44/55 (خیلی سخت‌تر!)
- Stochastic هم per-TF

**تأثیر:** سیگنال‌های کمتری در 4h، سیگنال‌های بیشتری در 5m

---

#### 3️⃣ **Advanced MACD Signals**

سیستم جدید دارای **6+ سیگنال اضافی** است:
- Market Type (A/B/C/D/X)
- DIF zero crosses (first/second)
- DIF trendline breaks
- Advanced histogram analysis

**تأثیر:** امتیازدهی momentum در سیستم جدید پیچیده‌تر است

---

#### 4️⃣ **Context-Aware Scoring**

**قدیمی:** momentum به صورت مستقل تحلیل می‌شود
**جدید:** momentum با trend هماهنگ می‌شود

**مثال:**
```
Trend: bearish (strength=-3)
Momentum: bullish (score=5)

قدیمی: سیگنال Long با امتیاز 5
جدید: سیگنال Long با امتیاز کاهش یافته (مثلاً 3)
```

**تأثیر:** سیگنال‌های مخالف روند penalty می‌گیرند

---

## بخش 6: تأثیر بر نتایج نهایی

### چرا نتایج دو سیستم متفاوت است؟

**دلیل 1: Threshold های RSI متفاوت**
```
قدیمی: RSI < 30 → oversold
جدید (5m): RSI < 39 → oversold

نتیجه: در 5m سیستم جدید سریع‌تر oversold تشخیص می‌دهد
```

**دلیل 2: Divergence Detection متفاوت**
```
قدیمی: از scipy.find_peaks (حساس‌تر)
جدید: از rolling window (ساده‌تر)

نتیجه: تعداد divergence های تشخیص داده شده متفاوت است
```

**دلیل 3: Context-Aware Scoring**
```
قدیمی: momentum مستقل
جدید: momentum با trend ترکیب می‌شود

نتیجه: سیگنال‌های مخالف روند امتیاز کمتری می‌گیرند
```

**دلیل 4: Advanced MACD Signals**
```
جدید: 6+ سیگنال اضافی MACD
نتیجه: امتیاز momentum کلی بالاتر می‌رود
```

---

## بخش 7: توصیه‌ها

### برای حفظ رفتار سیستم قدیمی:

#### 1️⃣ اصلاح RSI Thresholds

در `config.yaml`:
```yaml
momentum_analyzer:
  per_timeframe:
    enabled: false  # غیرفعال کردن per-TF
  rsi_oversold: 30  # global threshold
  rsi_overbought: 70
  stoch_oversold: 20
  stoch_overbought: 80
```

#### 2️⃣ استفاده از Divergence Detection قدیمی

کد فعلی جدید ساده‌تر است. برای رفتار مشابه قدیمی:
- باید متد `_detect_divergences` را با `scipy.signal.find_peaks` بازنویسی کنید
- یا threshold divergence را تنظیم کنید

#### 3️⃣ غیرفعال کردن Context-Aware Scoring

در کد:
```python
# اگر نمی‌خواهید momentum با trend ترکیب شود:
# خط 197-203 را کامنت کنید
```

#### 4️⃣ غیرفعال کردن Advanced MACD

سیگنال‌های Advanced MACD را در امتیازدهی نهایی نادیده بگیرید.

---

### برای بهره‌برداری از بهبودهای جدید:

✅ **Threshold های Per-TF را Calibrate کنید:**
- در backtest ببینید کدام threshold ها بهتر عمل می‌کنند
- برای هر تایم‌فریم مقادیر بهینه را پیدا کنید

✅ **از Advanced MACD Signals استفاده کنید:**
- Market Type Detection می‌تواند در strategy مفید باشد
- DIF zero crosses سیگنال‌های قوی هستند

✅ **Context-Aware Scoring را حفظ کنید:**
- این یکی از بهبودهای واقعی است
- سیگنال‌های با روند همراستا موفق‌ترند

---

## خلاصه نهایی

| معیار | قدیمی | جدید | توصیه |
|-------|-------|------|-------|
| **محاسبات پایه** | ✅ درست | ✅ درست | حفظ شود |
| **Divergence** | پیچیده | ساده | ⚠️ نیاز به بررسی backtest |
| **Thresholds** | ثابت (30/70) | Per-TF (متفاوت) | 🔧 calibrate شود |
| **Context-Aware** | ❌ ندارد | ✅ دارد | ✅ حفظ شود |
| **Advanced MACD** | ❌ ندارد | ✅ دارد | ✅ حفظ شود |

---

**تاریخ:** 2025-11-21
**نسخه:** 1.0
