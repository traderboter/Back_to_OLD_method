# 📖 راهنمای استفاده از Per-Timeframe Configuration

## 🎯 مقدمه

سیستم Per-Timeframe Configuration این امکان را می‌دهد که **هر تایم‌فریم با پارامترهای مخصوص خودش** تحلیل شود.

### چرا این مهم است؟

```
RSI(14) در 5min  = 70 دقیقه داده  → noise زیاد
RSI(14) در 4hour = 56 ساعت داده   → روند واضح

⚠️ پس نمی‌توان از یک threshold برای هر دو استفاده کرد!
```

---

## 🏗️ معماری سیستم

### سه سطح پیکربندی:

```yaml
1️⃣ Level 1: Indicator Calculator (آینده)
   - دوره‌های مختلف برای محاسبه اندیکاتورها
   - مثال: RSI(10) در 5m، RSI(18) در 4h

2️⃣ Level 2: Analyzer Thresholds (✅ فعلی)
   - آستانه‌های مختلف برای هر تایم‌فریم
   - مثال: RSI > 75 در 5m، RSI > 65 در 4h

3️⃣ Level 3: Analyzer Weights (✅ آماده)
   - وزن‌های مختلف برای هر analyzer در هر TF
   - مثال: Trend weight = 0.20 در 5m، 0.35 در 4h
```

---

## 🚀 نحوه استفاده

### 1. فعال‌سازی Per-TF Configuration

در `config.yaml`:

```yaml
signal_generation_v2:
  analyzers:
    momentum_analyzer:
      # تنظیمات پایه (fallback)
      rsi:
        oversold_threshold: 30
        overbought_threshold: 70

      # 🆕 Per-TF configuration
      rsi_per_timeframe:
        enabled: True           # ✅ فعال کردن
        '5m':
          oversold: 25         # سخت‌گیرانه‌تر
          overbought: 75
        '15m':
          oversold: 28
          overbought: 72
        '1h':
          oversold: 30         # استاندارد
          overbought: 70
        '4h':
          oversold: 35         # راحت‌تر
          overbought: 65
```

### 2. استفاده در Analyzer

Analyzer ها به صورت خودکار از per-TF thresholds استفاده می‌کنند:

```python
# در MomentumAnalyzer.analyze()
def analyze(self, context: AnalysisContext) -> None:
    df = context.df
    timeframe = context.timeframe  # مثلاً '5m'

    # دریافت threshold مخصوص این TF
    rsi_overbought = self.get_threshold(
        'rsi_overbought',      # نام پارامتر
        70,                    # مقدار پیش‌فرض
        timeframe              # '5m'
    )
    # برای 5m → برمی‌گرداند: 75
    # برای 4h → برمی‌گرداند: 65

    current_rsi = df['rsi'].iloc[-1]
    if current_rsi >= rsi_overbought:
        # اشباع خرید (با threshold مخصوص این TF)
        ...
```

### 3. Fallback Mechanism

سیستم به صورت هوشمند fallback می‌کند:

```
1. Per-TF Config موجود است؟
   ✅ بله → استفاده از per-TF
   ❌ خیر → برو به گام 2

2. Global Config موجود است؟
   ✅ بله → استفاده از global
   ❌ خیر → برو به گام 3

3. استفاده از default value
```

**مثال:**
```yaml
# اگر فقط این را داشته باشیم:
rsi_per_timeframe:
  enabled: True
  '5m':
    overbought: 75
  # '4h' تعریف نشده!

# نتیجه:
# 5m  → 75 (از per-TF)
# 4h  → 70 (از global یا default)
```

---

## 📊 Analyzers پشتیبانی‌شده

### ✅ MomentumAnalyzer

**پارامترها:**
```yaml
momentum_analyzer:
  rsi_per_timeframe:
    '5m': {oversold: 25, overbought: 75}
    '4h': {oversold: 35, overbought: 65}

  macd_per_timeframe:
    '5m': {histogram_threshold: 0.001}
    '4h': {histogram_threshold: 0.0002}

  stochastic_per_timeframe:
    '5m': {oversold: 15, overbought: 85}
    '4h': {oversold: 25, overbought: 75}
```

**نحوه استفاده در کد:**
```python
# در analyzer:
rsi_oversold = self.get_threshold('rsi_oversold', 30, timeframe)
macd_histogram_threshold = self.get_threshold('macd_histogram_threshold', 0, timeframe)
stoch_oversold = self.get_threshold('stochastic_oversold', 20, timeframe)
```

---

### ✅ VolumeAnalyzer

**پارامترها:**
```yaml
volume_analyzer:
  volume_per_timeframe:
    '5m':
      high_ratio: 2.0          # نیاز به حجم بیشتر
      confirmation_ratio: 1.5
      breakout_ratio: 2.5
    '4h':
      high_ratio: 1.3          # حجم کمتر کافی است
      confirmation_ratio: 1.1
      breakout_ratio: 1.5
```

**نحوه استفاده:**
```python
high_volume_ratio = self.get_threshold('volume_high_ratio', 1.5, timeframe)
confirmation_ratio = self.get_threshold('volume_confirmation_ratio', 1.2, timeframe)
breakout_ratio = self.get_threshold('volume_breakout_ratio', 1.8, timeframe)
```

---

### ✅ TrendAnalyzer

**پارامترها:**
```yaml
trend_analyzer:
  trend_strength_per_timeframe:
    '5m':
      min_strength: 2          # نیاز به قوی‌تر (noise)
      strong_threshold: 4
      min_slope: 0.0002        # حداقل شیب EMA
    '4h':
      min_strength: 1          # روندها واضح‌ترند
      strong_threshold: 2
      min_slope: 0.00005
```

**نحوه استفاده:**
```python
min_slope_threshold = self.get_threshold('trend_min_slope', 0.0001, timeframe)
```

---

### ✅ VolatilityAnalyzer

**پارامترها:**
```yaml
volatility_analyzer:
  volatility_per_timeframe:
    '5m':
      low_threshold: 0.3       # ATR% < 0.3 = low vol
      high_threshold: 1.0      # ATR% > 1.0 = high vol
      extreme_threshold: 2.0
      stop_low: 1.5            # ATR multiples for stops
      stop_normal: 2.0
      stop_high: 3.0
    '4h':
      low_threshold: 0.6
      high_threshold: 2.0
      extreme_threshold: 4.0
      stop_low: 1.3            # Tighter stops
      stop_normal: 1.8
      stop_high: 2.2
```

**نحوه استفاده:**
```python
low_vol_threshold = self.get_threshold('volatility_low_threshold', 0.5, timeframe)
high_vol_threshold = self.get_threshold('volatility_high_threshold', 1.5, timeframe)

# For stops:
param_name = f'volatility_stop_{regime}'  # 'volatility_stop_low'
recommended_stop = self.get_threshold(param_name, 2.0, timeframe)
```

---

## 🎓 مثال‌های کاربردی

### مثال 1: تشخیص اشباع خرید RSI

**سناریو:** RSI = 65

**بدون per-TF:**
```
همه TF ها: 65 < 70 → عادی
```

**با per-TF:**
```python
# 5m
rsi_overbought = get_threshold('rsi_overbought', 70, '5m')  # → 75
65 < 75 → عادی ✅

# 4h
rsi_overbought = get_threshold('rsi_overbought', 70, '4h')  # → 65
65 >= 65 → اشباع خرید! ⚠️
```

**نتیجه:** 4h سیگنال اشباع خرید می‌دهد، اما 5m خیر (درست!)

---

### مثال 2: تایید حجم معامله

**سناریو:** Volume Ratio = 1.4

**بدون per-TF:**
```
همه TF ها: 1.4 < 1.5 → حجم کافی نیست
```

**با per-TF:**
```python
# 5m
high_volume_ratio = get_threshold('volume_high_ratio', 1.5, '5m')  # → 2.0
1.4 < 2.0 → حجم کافی نیست ✅

# 4h
high_volume_ratio = get_threshold('volume_high_ratio', 1.5, '4h')  # → 1.3
1.4 > 1.3 → حجم بالا! ✅
```

**نتیجه:** 4h حجم را تایید می‌کند، 5m خیر (درست!)

---

### مثال 3: تشخیص روند

**سناریو:** EMA20 slope = 0.00012

**بدون per-TF:**
```
همه TF ها: 0.00012 > 0.0001 → روند صعودی
```

**با per-TF:**
```python
# 5m
min_slope = get_threshold('trend_min_slope', 0.0001, '5m')  # → 0.0002
0.00012 < 0.0002 → بدون روند ✅

# 4h
min_slope = get_threshold('trend_min_slope', 0.0001, '4h')  # → 0.00005
0.00012 > 0.00005 → روند صعودی! ✅
```

**نتیجه:** 4h روند را تشخیص می‌دهد، 5m noise تشخیص می‌دهد (درست!)

---

## ⚙️ توصیه‌های تنظیم

### فلسفه تنظیمات:

| Timeframe | Noise Level | Strategy | Example Thresholds |
|-----------|-------------|----------|-------------------|
| **5min** | 🔴 بسیار بالا | محافظه‌کارانه | RSI: 25-75, Vol: 2.0x |
| **15min** | 🟡 متوسط | متعادل | RSI: 28-72, Vol: 1.7x |
| **1hour** | 🟢 پایین | استاندارد | RSI: 30-70, Vol: 1.5x |
| **4hour** | 🔵 خیلی پایین | تهاجمی | RSI: 35-65, Vol: 1.3x |

### نحوه تنظیم بهینه:

1. **استفاده از Optimizer:**
```bash
cd New_backtesting
python optimize_signal_parameters_multitf.py --pair BTC-USDT
```

2. **بررسی نتایج:**
```bash
cat ../results/perfect_trades/BTC-USDT_optimization_multitf_results.json
```

3. **اعمال توصیه‌ها در config.yaml**

4. **تست و تنظیم دقیق**

---

## 🔍 Debugging و Troubleshooting

### چگونه بفهمیم per-TF فعال است؟

در لاگ‌ها دنبال این پیام‌ها بگردید:

```
DEBUG - MomentumAnalyzer: Using per-TF threshold rsi_overbought=75 for 5m
DEBUG - VolumeAnalyzer: Using per-TF threshold volume_high_ratio=2.0 for 5m
DEBUG - TrendAnalyzer: Using per-TF threshold trend_min_slope=0.0002 for 5m
```

اگر این پیام را دیدید، fallback رخ داده:
```
DEBUG - MomentumAnalyzer: Using default threshold rsi_overbought=70
```

### مشکلات رایج:

**1. Per-TF کار نمی‌کند**
```yaml
❌ اشتباه:
rsi_per_timeframe:
  enabled: False    # غیرفعال است!

✅ درست:
rsi_per_timeframe:
  enabled: True
```

**2. Timeframe اشتباه**
```yaml
❌ اشتباه:
'5min': {...}       # باید '5m' باشد

✅ درست:
'5m': {...}
```

**3. نام پارامتر اشتباه**
```python
# در analyzer:
self.get_threshold('rsi_oversold', 30, tf)

# در config باید باشد:
'5m':
  oversold: 25      # نه rsi_oversold!
```

**قاعده:** نام پارامتر را به دو قسمت تقسیم می‌کند:
- `rsi_oversold` → indicator: `rsi`, param: `oversold`
- در config: `rsi_per_timeframe → '5m' → oversold`

---

## 📈 نتایج مورد انتظار

### قبل از per-TF:
```
5m:  ✅ 45 سیگنال، 🔴 30 False Positive (67% دقت)
4h:  ✅ 20 سیگنال، 🔴 2 False Positive (90% دقت)
```

### بعد از per-TF:
```
5m:  ✅ 35 سیگنال، 🔴 10 False Positive (78% دقت) ⬆️ +11%
4h:  ✅ 25 سیگنال، 🔴 2 False Positive (92% دقت) ⬆️ +2%
```

**مزایا:**
- ✅ دقت بیشتر در 5min (کاهش false positives)
- ✅ سیگنال‌های بیشتر در 4hour (افزایش true positives)
- ✅ کاهش noise در تایم‌فریم‌های پایین
- ✅ افزایش حساسیت در تایم‌فریم‌های بالا

---

## 🚀 گام‌های بعدی

### فعلاً پیاده‌سازی شده:
- ✅ BaseAnalyzer (get_threshold, get_weight)
- ✅ MomentumAnalyzer (RSI, MACD, Stochastic)
- ✅ VolumeAnalyzer (volume ratios)
- ✅ TrendAnalyzer (slope thresholds)
- ✅ VolatilityAnalyzer (volatility regimes, stops)

### در دست توسعه:
- ⏳ IndicatorCalculator (Level 1: calculation periods)
- ⏳ Per-TF analyzer weights (Level 3)
- ⏳ Remaining analyzers (Pattern, SR, etc.)

### نحوه مشارکت:

اگر می‌خواهید analyzer دیگری را به‌روزرسانی کنید:

```python
# 1. در analyze() method:
def analyze(self, context: AnalysisContext) -> None:
    df = context.df
    timeframe = context.timeframe  # اضافه کنید

    # 2. در method های داخلی:
    def _your_method(self, ..., timeframe: str = None):
        threshold = self.get_threshold('param_name', default, timeframe)
        # استفاده از threshold

# 3. در config.yaml:
your_analyzer:
  param_per_timeframe:
    enabled: True
    '5m': {param: value}
    '4h': {param: value}
```

---

## 📚 منابع بیشتر

- 📄 **طراحی کامل:** `docs/COMPLETE_PER_TIMEFRAME_DESIGN.md`
- 📄 **طراحی اولیه:** `docs/PER_TIMEFRAME_CONFIG_DESIGN.md`
- 📄 **Optimizer راهنما:** `New_backtesting/README_MULTITF_OPTIMIZER.md`
- 💻 **BaseAnalyzer کد:** `signal_generation/analyzers/base_analyzer.py:221-334`

---

## 💡 نکات نهایی

1. **همیشه با optimizer شروع کنید** - داده‌ها بهترین راهنما هستند
2. **تست کنید** - قبل از production حتماً backtest کنید
3. **تدریجی پیش بروید** - ابتدا یک analyzer، سپس بقیه
4. **لاگ‌ها را بررسی کنید** - DEBUG logs نشان می‌دهد چه اتفاقی می‌افتد
5. **Backward compatible است** - می‌توانید به تدریج فعال کنید

---

**موفق باشید! 🎉**
