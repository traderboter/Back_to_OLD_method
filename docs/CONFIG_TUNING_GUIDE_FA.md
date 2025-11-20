# راهنمای جامع تنظیم پارامترهای سیستم 🎯

این راهنما همه چیزی که برای تنظیم پارامترهای اندیکاتورها، الگوها و analyzer ها نیاز دارید را توضیح می‌دهد.

---

## 📋 فهرست مطالب

1. [سطوح تنظیمات (3 Level)](#سطوح-تنظیمات)
2. [Level 1: پارامترهای اندیکاتورها](#level-1-پارامترهای-اندیکاتورها)
3. [Level 2: آستانه‌های Analyzer ها](#level-2-آستانههای-analyzer-ها)
4. [Level 3: وزن‌های Analyzer ها](#level-3-وزنهای-analyzer-ها)
5. [تنظیم الگوها (Patterns)](#تنظیم-الگوها)
6. [نکات کلیدی و Best Practices](#نکات-کلیدی)
7. [مثال‌های عملی](#مثالهای-عملی)

---

## سطوح تنظیمات

سیستم ما 3 سطح تنظیمات مستقل دارد:

### 🎯 Level 1: پارامترهای محاسبه اندیکاتور
- **چیست؟** دوره‌های (periods) محاسبه اندیکاتورها
- **مثال:** RSI period, MACD periods, EMA periods
- **کجا؟** `signal_generation_v2.indicator_calculator.per_timeframe`

### 🎯 Level 2: آستانه‌های Analyzer ها
- **چیست؟** آستانه‌های تشخیص سیگنال
- **مثال:** RSI overbought/oversold, ADX threshold, Volume ratios
- **کجا؟** `momentum.per_timeframe`, `trend.per_timeframe`, etc.

### 🎯 Level 3: وزن‌های Analyzer ها
- **چیست؟** اهمیت هر analyzer در امتیازدهی نهایی
- **مثال:** trend: 0.35, momentum: 0.20
- **کجا؟** `signal_processing.scoring.weights_per_timeframe`

---

## Level 1: پارامترهای اندیکاتورها

### 📍 مکان در config.yaml

```yaml
signal_generation_v2:
  indicator_calculator:
    per_timeframe:
      enabled: True    # ✅ حتماً True کنید

      '5m':           # تنظیمات برای 5 دقیقه
        # ... پارامترها

      '15m':          # تنظیمات برای 15 دقیقه
        # ... پارامترها

      '1h':           # تنظیمات برای 1 ساعت
        # ... پارامترها

      '4h':           # تنظیمات برای 4 ساعت
        # ... پارامترها
```

### 🔧 پارامترهای موجود

#### 1. Momentum Indicators (اندیکاتورهای مومنتوم)

```yaml
'5m':
  # RSI (Relative Strength Index)
  rsi_period: 10              # دوره محاسبه RSI
                              # کوچکتر = سریع‌تر (برای 5m)
                              # بزرگتر = آهسته‌تر (برای 4h)

  # MACD (Moving Average Convergence Divergence)
  macd_fast: 8                # خط سریع MACD
  macd_slow: 17               # خط کند MACD
  macd_signal: 6              # خط سیگنال MACD

  # Stochastic Oscillator
  stoch_k: 10                 # دوره خط K
  stoch_d: 3                  # دوره خط D
  stoch_smooth: 2             # میزان هموارسازی

'4h':
  rsi_period: 18              # دوره بلندتر برای 4h
  macd_fast: 16
  macd_slow: 35
  macd_signal: 12
  stoch_k: 14
  stoch_d: 3
  stoch_smooth: 3
```

**💡 راهنما:**
- **5m:** دوره‌های کوچک (10-12) → واکنش سریع
- **15m:** دوره‌های متوسط (12-14)
- **1h:** دوره‌های استاندارد (14)
- **4h:** دوره‌های بزرگ (18-20) → سیگنال‌های آرام‌تر

#### 2. Trend Indicators (اندیکاتورهای روند)

```yaml
'5m':
  # Exponential Moving Average
  ema_periods: [10, 20, 50]   # لیست دوره‌های EMA
                               # کوچکتر = واکنش سریع‌تر

  # Simple Moving Average
  sma_periods: [10, 20, 50]   # لیست دوره‌های SMA

  # Average Directional Index
  adx_period: 10              # دوره ADX

'4h':
  ema_periods: [30, 75, 150]  # دوره‌های بلندتر برای 4h
  sma_periods: [30, 75, 150]
  adx_period: 18
```

**💡 راهنما:**
- **ema_periods** معمولاً 3 عدد: کوتاه، متوسط، بلند
- نسبت تقریبی: `[1x, 2x, 5x]`
- **5m:** `[10, 20, 50]` یا `[8, 15, 30]`
- **4h:** `[30, 75, 150]` یا `[25, 50, 100]`

#### 3. Volatility Indicators (اندیکاتورهای نوسان)

```yaml
'5m':
  # Average True Range
  atr_period: 10              # دوره ATR

  # Bollinger Bands
  bb_period: 15               # دوره BB
  bb_std: 2.0                 # انحراف معیار BB

'4h':
  atr_period: 18
  bb_period: 25
  bb_std: 2.0                 # معمولاً ثابت می‌ماند
```

**💡 راهنما:**
- **atr_period:** کوچکتر = نوسان سریع‌تر
- **bb_period:** معمولاً 15-25
- **bb_std:** معمولاً 2.0 (می‌تواند 1.5 یا 2.5 هم باشد)

#### 4. Volume Indicators (اندیکاتورهای حجم)

```yaml
'5m':
  volume_sma_period: 20       # دوره میانگین حجم
  obv_enabled: True           # فعال/غیرفعال On-Balance Volume

'4h':
  volume_sma_period: 30
  obv_enabled: True
```

### 📊 مثال کامل Level 1

```yaml
signal_generation_v2:
  indicator_calculator:
    per_timeframe:
      enabled: True

      '5m':                   # 🔴 Scalping - سریع
        # Momentum - واکنش سریع
        rsi_period: 10
        macd_fast: 8
        macd_slow: 17
        macd_signal: 6
        stoch_k: 10
        stoch_d: 3
        stoch_smooth: 2

        # Trend - کوتاه‌مدت
        ema_periods: [10, 20, 50]
        sma_periods: [10, 20, 50]
        adx_period: 10

        # Volatility - حساس
        atr_period: 10
        bb_period: 15
        bb_std: 2.0

      '4h':                   # 🔵 Swing Trading - آرام
        # Momentum - واکنش آهسته
        rsi_period: 18
        macd_fast: 16
        macd_slow: 35
        macd_signal: 12
        stoch_k: 14
        stoch_d: 3
        stoch_smooth: 3

        # Trend - بلندمدت
        ema_periods: [30, 75, 150]
        sma_periods: [30, 75, 150]
        adx_period: 18

        # Volatility - هموار
        atr_period: 18
        bb_period: 25
        bb_std: 2.0
```

---

## Level 2: آستانه‌های Analyzer ها

### 📍 مکان در config.yaml

```yaml
momentum:              # Momentum Analyzer
  per_timeframe:
    enabled: True
    '5m': ...
    '4h': ...

trend:                 # Trend Analyzer
  per_timeframe:
    enabled: True
    '5m': ...
    '4h': ...

volume:                # Volume Analyzer
  per_timeframe:
    enabled: True
    '5m': ...
    '4h': ...

volatility:            # Volatility Analyzer
  per_timeframe:
    enabled: True
    '5m': ...
    '4h': ...
```

### 🔧 پارامترهای موجود

#### 1. Momentum Analyzer

```yaml
momentum:
  # 🌍 Global defaults (برای همه TF ها)
  rsi_overbought: 70          # آستانه اشباع خرید RSI
  rsi_oversold: 30            # آستانه اشباع فروش RSI
  macd_threshold: 1.0         # حداقل قدرت MACD
  stoch_overbought: 80        # آستانه اشباع خرید Stochastic
  stoch_oversold: 20          # آستانه اشباع فروش Stochastic

  # 🎯 Per-Timeframe overrides
  per_timeframe:
    enabled: True

    '5m':                     # 5m = محافظه‌کارانه‌تر
      rsi_overbought: 75      # بالاتر = سیگنال کمتر، دقیق‌تر
      rsi_oversold: 25        # پایین‌تر = سیگنال کمتر، دقیق‌تر
      macd_threshold: 0.5     # کوچکتر = سیگنال بیشتر
      stoch_overbought: 85
      stoch_oversold: 15

    '4h':                     # 4h = حساس‌تر
      rsi_overbought: 65      # پایین‌تر = سیگنال بیشتر
      rsi_oversold: 35        # بالاتر = سیگنال بیشتر
      macd_threshold: 1.5     # بزرگتر = سیگنال کمتر
      stoch_overbought: 75
      stoch_oversold: 25
```

**💡 راهنما:**
- **5m:** آستانه‌های شدید (75/25) → noise را فیلتر می‌کند
- **4h:** آستانه‌های ملایم (65/35) → سیگنال‌های بیشتر
- **rsi_overbought:** معمولاً 65-80
- **rsi_oversold:** معمولاً 20-35

#### 2. Trend Analyzer

```yaml
trend:
  # 🌍 Global defaults
  adx_strong_trend: 25        # آستانه روند قوی ADX
  ema_alignment_threshold: 0.001  # آستانه ترتیب EMA ها

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      adx_strong_trend: 30    # بالاتر = روند قوی‌تر لازم
      ema_alignment_threshold: 0.002

    '4h':
      adx_strong_trend: 20    # پایین‌تر = روند ضعیف‌تر قبول
      ema_alignment_threshold: 0.0008
```

**💡 راهنما:**
- **adx_strong_trend:**
  - 5m: 30-35 (روند کمتر قابل اعتماد)
  - 4h: 20-25 (روند قابل اعتمادتر)
- **ema_alignment_threshold:**
  - کوچک = دقیق‌تر (0.0005-0.001)
  - بزرگ = راحت‌تر (0.001-0.003)

#### 3. Volume Analyzer

```yaml
volume:
  # 🌍 Global defaults
  volume_high_ratio: 1.5      # ضریب حجم بالا
  volume_low_ratio: 0.5       # ضریب حجم پایین

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      volume_high_ratio: 2.0  # حجم بسیار متغیر
      volume_low_ratio: 0.4

    '4h':
      volume_high_ratio: 1.3  # حجم پایدارتر
      volume_low_ratio: 0.6
```

**💡 راهنما:**
- **volume_high_ratio:** حجم > ratio × میانگین → حجم بالا
- **volume_low_ratio:** حجم < ratio × میانگین → حجم پایین
- 5m: تفاوت زیاد (2.0 / 0.4)
- 4h: تفاوت کم (1.3 / 0.6)

#### 4. Volatility Analyzer

```yaml
volatility:
  # 🌍 Global defaults
  atr_high_multiplier: 1.5    # ضریب ATR برای نوسان بالا
  atr_low_multiplier: 0.5     # ضریب ATR برای نوسان پایین
  bb_squeeze_threshold: 0.1   # آستانه BB Squeeze

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      atr_high_multiplier: 2.0
      atr_low_multiplier: 0.4
      bb_squeeze_threshold: 0.08

    '4h':
      atr_high_multiplier: 1.3
      atr_low_multiplier: 0.6
      bb_squeeze_threshold: 0.12
```

#### 5. Support/Resistance Analyzer

```yaml
support_resistance:
  # 🌍 Global defaults
  lookback: 100               # تعداد کندل برای جستجو
  min_touches: 2              # حداقل تعداد touch
  atr_tolerance_multiplier: 0.3

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      lookback: 50            # کوتاه‌تر = S/R نزدیک‌تر
      min_touches: 3          # دقیق‌تر

    '4h':
      lookback: 150           # بلندتر = S/R دورتر
      min_touches: 2          # راحت‌تر
```

#### 6. Pattern Analyzer

```yaml
pattern:
  # 🌍 Global defaults
  min_pattern_strength: 1     # حداقل قدرت الگو

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      min_pattern_strength: 2  # فقط الگوهای قوی

    '4h':
      min_pattern_strength: 1  # الگوهای ضعیف هم قبول
```

#### 7. Harmonic Analyzer

```yaml
harmonic:
  # 🌍 Global defaults
  lookback: 100               # تعداد کندل جستجو
  tolerance: 0.05             # تلرانس تطبیق الگو
  swing_window: 5             # پنجره Swing detection

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      lookback: 50
      tolerance: 0.08         # تلرانس بیشتر
      swing_window: 3         # کوچکتر

    '4h':
      lookback: 150
      tolerance: 0.03         # تلرانس کمتر
      swing_window: 7         # بزرگتر
```

#### 8. Channel Analyzer

```yaml
channel:
  # 🌍 Global defaults
  lookback: 50                # دوره کانال

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      lookback: 30

    '4h':
      lookback: 75
```

#### 9. Cyclical Analyzer

```yaml
cyclical:
  # 🌍 Global defaults
  lookback: 200
  min_cycle: 10
  max_cycle: 100
  min_cycles_for_forecast: 2
  forecast_length: 20

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      lookback: 100
      min_cycle: 5
      max_cycle: 50
      forecast_length: 10

    '4h':
      lookback: 300
      min_cycle: 20
      max_cycle: 150
      forecast_length: 30
```

#### 10. HTF (Higher Timeframe) Analyzer

```yaml
htf:
  # 🌍 Global defaults
  lookback: 50

  # 🎯 Per-Timeframe
  per_timeframe:
    enabled: True

    '5m':
      lookback: 30

    '4h':
      lookback: 75
```

---

## Level 3: وزن‌های Analyzer ها

### 📍 مکان در config.yaml

```yaml
signal_processing:
  scoring:
    # 🌍 وزن‌های global (پیش‌فرض)
    weights:
      trend: 0.30
      momentum: 0.25
      volume: 0.20
      volatility: 0.15
      sr: 0.10
      # ... بقیه analyzers

    # 🎯 وزن‌های per-timeframe
    weights_per_timeframe:
      enabled: True

      '5m': ...
      '4h': ...
```

### 🔧 منطق وزن‌دهی

```yaml
weights_per_timeframe:
  enabled: True

  '5m':                       # 🔴 Scalping
    trend: 0.20               # روند کمتر قابل اعتماد
    momentum: 0.35            # مومنتوم خیلی مهم
    volume: 0.25              # حجم خیلی مهم
    volatility: 0.15          # نوسان مهم
    sr: 0.05                  # S/R کمتر مهم

  '15m':                      # 🟠 Day Trading
    trend: 0.25
    momentum: 0.30
    volume: 0.22
    volatility: 0.15
    sr: 0.08

  '1h':                       # 🟡 Swing Trading
    trend: 0.30               # استاندارد
    momentum: 0.25
    volume: 0.20
    volatility: 0.15
    sr: 0.10

  '4h':                       # 🔵 Position Trading
    trend: 0.35               # روند خیلی مهم
    momentum: 0.20            # مومنتوم کمتر مهم
    volume: 0.18              # حجم کمتر مهم
    volatility: 0.15
    sr: 0.12                  # S/R مهم‌تر
```

**💡 راهنما:**
- مجموع وزن‌ها باید 1.0 باشد
- هر timeframe ویژگی‌های خاصی دارد:
  - **5m:** momentum + volume مهم
  - **15m:** تعادل
  - **1h:** استاندارد
  - **4h:** trend + S/R مهم

---

## تنظیم الگوها

### 📍 مکان در config.yaml

```yaml
patterns:
  # هر الگو 2 پارامتر دارد:

  engulfing:
    lookback_window: 5        # چند کندل به عقب نگاه کنیم
    recency_multipliers: [1.0, 0.95, 0.85, 0.75, 0.6, 0.4]
    # ضرایب decay: [الان, 1کندل قبل, 2کندل قبل, ...]
```

### 🔧 پارامترها

#### 1. lookback_window
- **چیست؟** تعداد کندل‌هایی که به عقب جستجو می‌کنیم
- **مقادیر:** معمولاً 3-10
- **5:** استاندارد
- **10:** جستجوی عمیق‌تر

#### 2. recency_multipliers
- **چیست؟** چقدر الگوهای قدیمی‌تر ارزش کمتری دارند
- **فرمت:** لیست ضرایب از 1.0 شروع می‌شود
- **مثال:** `[1.0, 0.95, 0.85, 0.75, 0.6, 0.4]`
  - کندل فعلی: 100% ارزش
  - 1 کندل قبل: 95% ارزش
  - 2 کندل قبل: 85% ارزش
  - ...

### 📊 دسته‌بندی الگوها

#### الگوهای قوی (Decay کند)
```yaml
engulfing:
  lookback_window: 5
  recency_multipliers: [1.0, 0.95, 0.85, 0.75, 0.6, 0.4]
  # حتی 2-3 کندل بعد هم اعتبار دارند

morning_star:
  lookback_window: 5
  recency_multipliers: [1.0, 0.95, 0.85, 0.75, 0.6, 0.4]

three_white_soldiers:
  lookback_window: 5
  recency_multipliers: [1.0, 0.95, 0.85, 0.75, 0.6, 0.4]
```

#### الگوهای متوسط (Decay معمولی)
```yaml
hammer:
  lookback_window: 5
  recency_multipliers: [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
  # تا 1-2 کندل بعد اعتبار دارند

shooting_star:
  lookback_window: 5
  recency_multipliers: [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
```

#### الگوهای ضعیف (Decay سریع)
```yaml
doji:
  lookback_window: 5
  recency_multipliers: [1.0, 0.7, 0.5, 0.3, 0.15, 0.05]
  # فقط همین الان مهم است

spinning_top:
  lookback_window: 5
  recency_multipliers: [1.0, 0.7, 0.5, 0.3, 0.15, 0.05]
```

### 💡 تنظیم برای تایم‌فریم‌ها

**❌ توجه:** الگوها فعلاً per-timeframe پشتیبانی نمی‌کنند.
اما می‌توانید با تغییر `lookback_window` و `recency_multipliers` رفتار را تنظیم کنید:

```yaml
# برای تایم‌فریم‌های کوتاه (5m, 15m):
# - lookback کوچکتر (3-5)
# - decay سریع‌تر (فقط الگوهای تازه)

hammer:
  lookback_window: 3
  recency_multipliers: [1.0, 0.8, 0.6, 0.4]

# برای تایم‌فریم‌های بلند (1h, 4h):
# - lookback بزرگتر (5-10)
# - decay کندتر (الگوهای قدیمی‌تر هم مفید)

hammer:
  lookback_window: 7
  recency_multipliers: [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7]
```

---

## نکات کلیدی

### ✅ Best Practices

1. **شروع با Global Defaults**
   ```yaml
   # ابتدا global را تنظیم کنید
   momentum:
     rsi_overbought: 70
     rsi_oversold: 30
   ```

2. **فعال کردن Per-TF به تدریج**
   ```yaml
   # ابتدا یک TF را تست کنید
   per_timeframe:
     enabled: True
     '5m':
       rsi_overbought: 75  # فقط 5m
   ```

3. **Override فقط پارامترهای لازم**
   ```yaml
   '5m':
     rsi_overbought: 75    # فقط این را override می‌کنیم
     # بقیه از global استفاده می‌کنند
   ```

4. **مجموع وزن‌ها = 1.0**
   ```yaml
   '5m':
     trend: 0.20
     momentum: 0.35
     volume: 0.25
     # ... بقیه
     # مجموع باید 1.0 شود
   ```

### ⚠️ اشتباهات متداول

❌ **فراموش کردن enabled: True**
```yaml
per_timeframe:
  # enabled: True  ← فراموش شده!
  '5m': ...
```

❌ **وزن‌های نامعتبر**
```yaml
weights_per_timeframe:
  '5m':
    trend: 0.50
    momentum: 0.50
    volume: 0.30      # ← مجموع > 1.0
```

❌ **تایم‌فریم نادرست**
```yaml
per_timeframe:
  '5min':    # ← باید '5m' باشد
```

### 🎯 فلسفه تنظیمات

| Timeframe | Indicator Periods | Thresholds | Weights |
|-----------|------------------|------------|---------|
| **5m** | کوتاه (سریع) | شدید (محافظه‌کار) | Momentum ↑ |
| **15m** | متوسط | متعادل | متعادل |
| **1h** | استاندارد | استاندارد | استاندارد |
| **4h** | بلند (آهسته) | ملایم (حساس) | Trend ↑ |

---

## مثال‌های عملی

### مثال 1: تنظیم برای Scalping (5m)

```yaml
# Level 1: اندیکاتورهای سریع
signal_generation_v2:
  indicator_calculator:
    per_timeframe:
      enabled: True
      '5m':
        rsi_period: 8           # خیلی سریع
        macd_fast: 6
        macd_slow: 13
        ema_periods: [8, 15, 30]
        atr_period: 8

# Level 2: آستانه‌های شدید
momentum:
  per_timeframe:
    enabled: True
    '5m':
      rsi_overbought: 80        # فقط اشباع شدید
      rsi_oversold: 20
      macd_threshold: 0.3       # حساس‌تر

trend:
  per_timeframe:
    enabled: True
    '5m':
      adx_strong_trend: 35      # فقط روندهای قوی

# Level 3: تمرکز روی Momentum
signal_processing:
  scoring:
    weights_per_timeframe:
      enabled: True
      '5m':
        trend: 0.15             # کمتر
        momentum: 0.40          # بیشتر
        volume: 0.30            # بیشتر
        volatility: 0.15
```

### مثال 2: تنظیم برای Swing Trading (4h)

```yaml
# Level 1: اندیکاتورهای آهسته
signal_generation_v2:
  indicator_calculator:
    per_timeframe:
      enabled: True
      '4h':
        rsi_period: 21          # خیلی آهسته
        macd_fast: 18
        macd_slow: 40
        ema_periods: [40, 100, 200]
        atr_period: 21

# Level 2: آستانه‌های ملایم
momentum:
  per_timeframe:
    enabled: True
    '4h':
      rsi_overbought: 60        # حساس‌تر
      rsi_oversold: 40
      macd_threshold: 2.0       # محافظه‌کارتر

trend:
  per_timeframe:
    enabled: True
    '4h':
      adx_strong_trend: 18      # روندهای ضعیف‌تر هم قبول

# Level 3: تمرکز روی Trend
signal_processing:
  scoring:
    weights_per_timeframe:
      enabled: True
      '4h':
        trend: 0.40             # بیشتر
        momentum: 0.15          # کمتر
        volume: 0.15            # کمتر
        sr: 0.15                # بیشتر
        volatility: 0.15
```

### مثال 3: تنظیم Conservative (محافظه‌کارانه)

```yaml
# هدف: سیگنال‌های کمتر، دقیق‌تر

# Level 1: دوره‌های بلند
'5m':
  rsi_period: 14              # بلندتر از معمول
  macd_fast: 12
  macd_slow: 26

# Level 2: آستانه‌های شدید
momentum:
  per_timeframe:
    '5m':
      rsi_overbought: 85      # خیلی شدید
      rsi_oversold: 15
      macd_threshold: 1.0     # بالا

trend:
  per_timeframe:
    '5m':
      adx_strong_trend: 35    # فقط روندهای قوی

# Level 3: تنوع بیشتر
signal_processing:
  scoring:
    weights_per_timeframe:
      '5m':
        trend: 0.25
        momentum: 0.25
        volume: 0.20
        sr: 0.15              # اهمیت به S/R
        volatility: 0.15
```

### مثال 4: تنظیم Aggressive (تهاجمی)

```yaml
# هدف: سیگنال‌های بیشتر، سریع‌تر

# Level 1: دوره‌های کوتاه
'5m':
  rsi_period: 6               # خیلی کوتاه
  macd_fast: 5
  macd_slow: 10
  ema_periods: [5, 10, 20]

# Level 2: آستانه‌های ملایم
momentum:
  per_timeframe:
    '5m':
      rsi_overbought: 65      # آسان
      rsi_oversold: 35
      macd_threshold: 0.2     # پایین

trend:
  per_timeframe:
    '5m':
      adx_strong_trend: 20    # روندهای ضعیف هم قبول

# Level 3: تمرکز روی Momentum
signal_processing:
  scoring:
    weights_per_timeframe:
      '5m':
        momentum: 0.50        # خیلی زیاد
        volume: 0.30
        trend: 0.10           # کم
        volatility: 0.10
```

---

## چک‌لیست تنظیمات

### قبل از شروع
- [ ] Backup از config.yaml گرفته شده
- [ ] محیط test آماده است
- [ ] هدف از تنظیمات مشخص است (scalping/swing/etc)

### Level 1: اندیکاتورها
- [ ] `enabled: True` تنظیم شده
- [ ] تایم‌فریم‌ها صحیح هستند (`'5m'`, `'15m'`, `'1h'`, `'4h'`)
- [ ] دوره‌های اندیکاتورها منطقی هستند
- [ ] نسبت‌ها حفظ شده (مثلاً ema_periods: `[1x, 2x, 5x]`)

### Level 2: آستانه‌ها
- [ ] `enabled: True` برای هر analyzer
- [ ] Global defaults تنظیم شده
- [ ] Per-TF overrides منطقی هستند
- [ ] آستانه‌ها در محدوده معقول (RSI: 0-100, etc)

### Level 3: وزن‌ها
- [ ] `enabled: True` تنظیم شده
- [ ] مجموع وزن‌ها = 1.0
- [ ] وزن‌ها با فلسفه TF سازگار است
- [ ] همه analyzers موردنیاز وزن دارند

### تست
- [ ] `python verify_per_tf_config.py` اجرا شده
- [ ] تمام 3 سطح PASS شده
- [ ] مقایسه 5m vs 4h منطقی است
- [ ] هیچ خطایی وجود ندارد

---

## راهنمای سریع

### برای شروع سریع:

1. **پیدا کردن بخش مورد نظر:**
   ```bash
   grep -n "^momentum:" config.yaml
   grep -n "indicator_calculator:" config.yaml
   ```

2. **تست کردن تنظیمات:**
   ```bash
   python verify_per_tf_config.py
   ```

3. **Backup گرفتن:**
   ```bash
   cp config.yaml config.yaml.backup
   ```

4. **تنظیم کردن:**
   - Level 1: خط 13-200
   - Level 2: خط 1433-1580
   - Level 3: خط 916-968
   - Patterns: خط 1288-1427

5. **Verify کردن:**
   ```bash
   python verify_per_tf_config.py
   ```

---

## کمک و پشتیبانی

### لاگ‌های مفید:

```python
# در لاگ‌ها به دنبال این پیام‌ها باشید:
DEBUG - RSI: Using per-TF parameter rsi_period=10 for 5m
DEBUG - MomentumAnalyzer: Using per-TF threshold rsi_overbought=75 for 5m
DEBUG - SignalScorer: Using per-TF weight trend=0.20 for 5m
```

### خطاهای متداول:

```
⚠ Level 2 per-TF config not found or disabled
→ enabled: True فراموش شده

⚠ Invalid timeframe format
→ باید '5m' باشد نه '5min'

⚠ Weights do not sum to 1.0
→ مجموع وزن‌ها باید دقیقاً 1.0 باشد
```

---

**آخرین بروزرسانی:** 2025-01-17
**نسخه:** 1.0
**وضعیت:** ✅ کامل و آماده استفاده
