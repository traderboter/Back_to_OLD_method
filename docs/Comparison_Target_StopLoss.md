# مقایسه جامع روش‌های محاسبه Target و Stop-Loss

## مقدمه

این سند یک مقایسه **دقیق و کامل** بین روش‌های محاسبه Target و Stop-Loss در سیستم قدیم و جدید ارائه می‌دهد.

### هدف

✅ بررسی فرمول‌های محاسبه در هر سیستم
✅ مقایسه رویکردها و منطق پشت هر روش
✅ شناسایی مزایا و معایب هر روش
✅ ارائه توصیه‌ها

---

## فهرست مطالب

1. [مقایسه کلی رویکردها](#section-1)
2. [سیستم قدیم: محاسبه Stop-Loss](#section-2)
3. [سیستم قدیم: محاسبه Take-Profit](#section-3)
4. [سیستم جدید: محاسبه Stop-Loss](#section-4)
5. [سیستم جدید: محاسبه Take-Profit](#section-5)
6. [مقایسه جدول‌وار](#section-6)
7. [مثال‌های عملی](#section-7)
8. [نتیجه‌گیری](#section-8)

---

<a name="section-1"></a>
## بخش ۱: مقایسه کلی رویکردها

### 1.1 نمای کلی

| جنبه | سیستم قدیمی (OLD) | سیستم جدید (NEW) |
|------|------------------|------------------|
| **رویکرد کلی** | Pattern-Based + Fallback | ATR-Based + SR Enhancement |
| **اولویت SL** | 1. Pattern, 2. S/R, 3. ATR, 4. % | 1. ATR × Volatility, 2. S/R (optional) |
| **اولویت TP** | 1. Pattern, 2. S/R, 3. RR-based | 1. RR-based (2.0), 2. S/R (enhancement) |
| **RR پیش‌فرض** | قابل تنظیم (معمولاً 2.0) | ثابت 2.0 |
| **پیچیدگی** | بالا (5 روش SL) | متوسط (1 روش اصلی + enhancement) |
| **Safety Checks** | 6 بررسی | 2 بررسی (در SignalInfo) |

### 1.2 فلسفه طراحی

#### سیستم قدیمی:
```
🎯 Pattern-First Approach
→ هر pattern خودش SL/TP بهینه‌اش را تعیین می‌کند
→ اگر pattern نبود → S/R استفاده می‌شود
→ اگر S/R نبود یا خیلی دور بود → ATR
→ اگر همه شکست خورد → % ثابت (fallback نهایی)

✅ مزایا: دقیق‌تر برای patterns خاص
❌ معایب: پیچیده، احتمال خطا بیشتر
```

#### سیستم جدید:
```
🎯 Volatility-First Approach
→ همیشه از ATR استفاده می‌کند (با توجه به volatility regime)
→ S/R فقط برای بهبود TP استفاده می‌شود (اختیاری)
→ RR ثابت 2.0

✅ مزایا: ساده، ثابت، قابل اعتماد
❌ معایب: کمتر به context های خاص توجه می‌کند
```

---

<a name="section-2"></a>
## بخش ۲: سیستم قدیم - محاسبه Stop-Loss

### 2.1 الگوریتم کامل (5 روش)

**محل:** `signal_generator.py:4029-4269`

```
[1] Harmonic Pattern
     ↓ (اگر نبود)
[2] Price Channel
     ↓ (اگر نبود)
[3] Support/Resistance
     ↓ (اگر نبود یا > 3×ATR دور بود)
[4] ATR-based
     ↓ (اگر ATR نبود)
[5] Percentage-based (Fallback)
```

### 2.2 روش ۱: Harmonic Pattern Stop-Loss

```python
# signal_generator.py:4074-4089
if direction == 'long':
    stop_loss = d_point_price * 0.99  # 1% زیر نقطه D
else:
    stop_loss = d_point_price * 1.01  # 1% بالای نقطه D
```

**منطق:**
- نقطه D نقطه کامل شدن pattern است
- اگر قیمت از D عبور کند = pattern شکست
- Buffer 1% برای noise

**مثال (Bullish Gartley):**
```
D Point Price = 50,000
SL = 50,000 × 0.99 = 49,500
```

### 2.3 روش ۲: Price Channel Stop-Loss

```python
# signal_generator.py:4101-4123
if direction == 'long':
    stop_loss = lower_channel_line * 0.99
else:
    stop_loss = upper_channel_line * 1.01
```

**منطق:**
- کانال = محدوده حرکت قیمت
- شکست کانال = تغییر جهت احتمالی
- Buffer 1%

**مثال:**
```
Lower Channel = 49,800
SL = 49,800 × 0.99 = 49,302
```

### 2.4 روش ۳: Support/Resistance Stop-Loss

```python
# signal_generator.py:4126-4138
if direction == 'long' and nearest_support and nearest_support < current_price:
    stop_loss = nearest_support * 0.999  # 0.1% زیر support
elif direction == 'short' and nearest_resist and nearest_resist > current_price:
    stop_loss = nearest_resist * 1.001  # 0.1% بالای resistance
```

**بررسی اضافی: فاصله از S/R نباید > 3×ATR باشد**

```python
# signal_generator.py:4140-4146
if stop_loss is not None and atr > 0:
    sl_dist_atr_ratio = abs(current_price - stop_loss) / atr
    if sl_dist_atr_ratio > 3.0:
        stop_loss = None  # رد می‌شود، به روش بعدی می‌رویم
```

**منطق:**
- S/R سطوح قوی قیمتی هستند
- قیمت معمولاً از S/R واکنش نشان می‌دهد
- اگر خیلی دور باشد (> 3×ATR) = غیرعملی

**مثال:**
```
Current Price = 50,000
Nearest Support = 49,500
ATR = 300

Distance = 50,000 - 49,500 = 500
Ratio = 500 / 300 = 1.67 < 3.0 ✅ قبول

SL = 49,500 × 0.999 = 49,450.5
```

### 2.5 روش ۴: ATR-based Stop-Loss

```python
# signal_generator.py:4148-4155
if stop_loss is None and atr > 0:
    sl_multiplier = adapted_risk_config.get('atr_trailing_multiplier', 2.0)

    if direction == 'long':
        stop_loss = current_price - (atr * sl_multiplier)
    else:
        stop_loss = current_price + (atr * sl_multiplier)
```

**منطق:**
- ATR = میانگین محدوده واقعی (نوسان)
- 2×ATR = فضای کافی برای noise
- قابل تنظیم توسط Adaptive Learning

**مثال:**
```
Current Price = 50,000
ATR = 300
Multiplier = 2.0

SL = 50,000 - (300 × 2.0) = 49,400
```

### 2.6 روش ۵: Percentage-based (Fallback)

```python
# signal_generator.py:4157-4163
default_sl_percent = adapted_risk_config.get('default_stop_loss_percent', 1.5)

if direction == 'long':
    stop_loss = current_price * (1 - default_sl_percent/100)
else:
    stop_loss = current_price * (1 + default_sl_percent/100)
```

**منطق:**
- آخرین راه (اگر همه روش‌های قبلی شکست خوردند)
- ثابت و قابل پیش‌بینی
- معمولاً 1.5%

**مثال:**
```
Current Price = 50,000
SL% = 1.5%

SL = 50,000 × (1 - 0.015) = 49,250
```

### 2.7 Safety Checks برای Stop-Loss

#### Check 1: حداقل فاصله

```python
# signal_generator.py:4165-4174
min_sl_distance = atr * 0.5 if atr > 0 else current_price * 0.001

if direction == 'long' and (current_price - stop_loss) < min_sl_distance:
    stop_loss = current_price - min_sl_distance
```

**چرا؟**
- SL خیلی نزدیک = احتمال Hit شدن به خاطر noise
- حداقل: 0.5×ATR یا 0.1%

#### Check 2: جلوگیری از صفر

```python
# signal_generator.py:4176-4185
risk_distance = abs(current_price - stop_loss)
if risk_distance <= 1e-6:
    risk_distance = current_price * (default_sl_percent / 100)
    stop_loss = current_price - risk_distance  # یا +
```

#### Check 3: Precision

```python
# signal_generator.py:4238-4245
precision = 8  # 8 رقم اعشار
stop_loss = round(stop_loss, precision)
```

---

<a name="section-3"></a>
## بخش ۳: سیستم قدیم - محاسبه Take-Profit

### 3.1 الگوریتم کامل

```python
# signal_generator.py:4187-4211

if take_profit is None:  # اگر از Pattern نیامده باشد
    # محاسبه بر اساس RR
    risk_distance = abs(current_price - stop_loss)
    reward_distance = risk_distance * preferred_rr  # معمولاً 2.0

    if direction == 'long':
        take_profit = current_price + reward_distance
    else:
        take_profit = current_price - reward_distance
```

### 3.2 تنظیم TP بر اساس S/R

```python
# signal_generator.py:4197-4211

if direction == 'long' and nearest_resist and nearest_resist < take_profit:
    # فقط اگر هنوز RR حداقلی را برآورده کند
    if nearest_resist > current_price + (risk_distance * min_rr):
        take_profit = nearest_resist * 0.999
```

**منطق:**
- اگر resistance نزدیک‌تر از TP محاسبه‌شده باشد
- و هنوز RR حداقلی (معمولاً 1.5) را برآورده کند
- TP را روی resistance قرار بده (با 0.1% buffer)

**مثال:**
```
Current Price = 50,000
Risk = 600 (SL = 49,400)
Preferred RR = 2.0
Min RR = 1.5

Calculated TP = 50,000 + (600 × 2.0) = 51,200
Nearest Resistance = 50,800

Check: 50,800 > 50,000 + (600 × 1.5) = 50,900? NO
→ TP = 51,200 (مقاومت رد می‌شود چون RR را پایین می‌آورد)
```

### 3.3 Safety Checks برای Take-Profit

#### Check 1: اطمینان از RR حداقلی

```python
# signal_generator.py:4213-4223
if direction == 'long' and take_profit <= current_price + (risk_distance * min_rr * 0.9):
    take_profit = current_price + (risk_distance * min_rr)
```

#### Check 2: جلوگیری از صفر

```python
# signal_generator.py:4229-4236
if abs(take_profit) < 1e-6:
    take_profit = current_price * (1.05 if direction == 'long' else 0.95)
```

### 3.4 محاسبه RR نهایی

```python
# signal_generator.py:4246-4252
final_rr = abs(take_profit - current_price) / abs(current_price - stop_loss)

return {
    'stop_loss': round(stop_loss, 8),
    'take_profit': round(take_profit, 8),
    'risk_reward_ratio': round(final_rr, 2),
    'risk_amount_per_unit': round(risk_distance, 8),
    'sl_method': calculation_method
}
```

---

<a name="section-4"></a>
## بخش ۴: سیستم جدید - محاسبه Stop-Loss

### 4.1 رویکرد ساده و ثابت

**محل:** `signal_generation/orchestrator.py:635-693`

```python
# Get volatility
volatility_result = context.get_result('volatility')
atr = volatility_result.get('atr_value')
stop_atr_mult = volatility_result.get('recommended_stop_atr', 2.0)

# Calculate stop distance
stop_distance = atr * stop_atr_mult

# Apply based on direction
if direction == 'LONG':
    stop_loss = entry - stop_distance
else:
    stop_loss = entry + stop_distance
```

### 4.2 تعیین ATR Multiplier بر اساس Volatility Regime

**محل:** `signal_generation/analyzers/volatility_analyzer.py:422-453`

```python
def _calculate_recommended_stop(
    volatility_regime: str,
    current_atr: float,
    timeframe: str = None
) -> float:
    # Base ATR multiples for different regimes
    base_stops = {
        'low': 1.5,      # Tighter stops in low volatility
        'normal': 2.0,   # Standard stops
        'high': 3.0      # Wider stops in high volatility
    }

    default_stop = base_stops.get(volatility_regime, 2.0)
    return default_stop
```

**منطق:**
- نوسان پایین → SL محکم‌تر (1.5×ATR)
- نوسان عادی → SL استاندارد (2.0×ATR)
- نوسان بالا → SL گسترده‌تر (3.0×ATR)

### 4.3 مثال محاسبه

```
Current Price = 50,000
ATR = 300
Volatility Regime = 'normal'
→ ATR Multiplier = 2.0

Stop Distance = 300 × 2.0 = 600
SL (LONG) = 50,000 - 600 = 49,400
```

### 4.4 مقایسه با سیستم قدیم

| جنبه | سیستم قدیمی | سیستم جدید |
|------|------------|------------|
| **تعداد روش** | 5 روش (Pattern, Channel, S/R, ATR, %) | 1 روش (ATR-based) |
| **پیچیدگی** | بالا | پایین |
| **قابل پیش‌بینی** | متوسط | بالا |
| **Context-Aware** | بله (pattern-specific) | بله (volatility-aware) |
| **Fallback** | بله (5 سطح) | خیر (همیشه ATR) |

---

<a name="section-5"></a>
## بخش ۵: سیستم جدید - محاسبه Take-Profit

### 5.1 RR ثابت 2.0

```python
# orchestrator.py:663-693

if direction == 'LONG':
    entry = current_price
    stop_loss = entry - stop_distance
    default_tp = entry + (stop_distance * 2)  # RR = 2.0
```

**منطق:**
- ساده و ثابت
- RR همیشه 2:1
- قابل پیش‌بینی

### 5.2 Enhancement با S/R (اختیاری)

```python
# orchestrator.py:668-677

if sr_result and sr_result.get('nearest_resistance'):
    sr_tp = sr_result['nearest_resistance']

    # Check: SR must be above entry AND provide better RR than default
    if sr_tp > entry and (sr_tp - entry) >= (default_tp - entry) * 0.8:
        take_profit = sr_tp
    else:
        take_profit = default_tp
```

**منطق:**
- اگر مقاومت نزدیک وجود دارد
- و حداقل 80% RR پیش‌فرض را حفظ می‌کند
- TP را روی مقاومت قرار بده

**مثال:**
```
Entry = 50,000
Stop Distance = 600
Default TP = 50,000 + (600 × 2) = 51,200

Nearest Resistance = 50,900

Check:
1. 50,900 > 50,000? ✅
2. (50,900 - 50,000) >= (51,200 - 50,000) × 0.8?
   900 >= 1,200 × 0.8?
   900 >= 960? ❌

→ TP = 51,200 (default) - مقاومت رد می‌شود
```

### 5.3 مقایسه با سیستم قدیم

| جنبه | سیستم قدیمی | سیستم جدید |
|------|------------|------------|
| **RR پیش‌فرض** | قابل تنظیم (معمولاً 2.0) | ثابت 2.0 |
| **Pattern-based TP** | بله (Harmonic, H&S, etc.) | خیر |
| **S/R Enhancement** | بله (با min RR check) | بله (با 80% RR check) |
| **پیچیدگی** | متوسط | پایین |

---

<a name="section-6"></a>
## بخش ۶: مقایسه جدول‌وار کامل

### 6.1 جدول مقایسه Stop-Loss

| روش محاسبه | سیستم قدیمی | سیستم جدید | برنده |
|-----------|------------|------------|-------|
| **Harmonic Pattern** | ✅ D Point ± 1% | ❌ ندارد | قدیمی |
| **Price Channel** | ✅ Channel Line ± 1% | ❌ ندارد | قدیمی |
| **Support/Resistance** | ✅ S/R ± 0.1% (if < 3×ATR) | ❌ ندارد (فقط در TP) | قدیمی |
| **ATR-based** | ✅ ATR × 2.0 (fallback) | ✅ ATR × (1.5-3.0) بر اساس regime | **جدید** |
| **Percentage** | ✅ 1.5% (fallback) | ❌ ندارد | قدیمی |
| **Volatility-Aware** | ❌ فقط در تنظیم ATR multiplier | ✅ Regime-based multiplier | **جدید** |
| **Safety Checks** | ✅ 6 بررسی | ✅ 2 بررسی (در SignalInfo) | قدیمی |

### 6.2 جدول مقایسه Take-Profit

| روش محاسبه | سیستم قدیمی | سیستم جدید | برنده |
|-----------|------------|------------|-------|
| **RR-based** | ✅ RR × Risk (قابل تنظیم) | ✅ 2.0 × Risk (ثابت) | برابر |
| **Pattern-based** | ✅ Fibonacci, Height, etc. | ❌ ندارد | قدیمی |
| **S/R Enhancement** | ✅ با min RR check | ✅ با 80% RR check | برابر |
| **Flexibility** | بالا (RR قابل تنظیم) | پایین (RR ثابت) | قدیمی |
| **Simplicity** | متوسط | بالا | **جدید** |

### 6.3 ویژگی‌های کلی

| ویژگی | سیستم قدیمی | سیستم جدید | برنده |
|-------|------------|------------|-------|
| **تعداد روش SL** | 5 | 1 | جدید (سادگی) |
| **Context-Awareness** | بالا (Pattern, S/R, ATR) | متوسط (Volatility) | قدیمی |
| **قابل پیش‌بینی** | متوسط | بالا | **جدید** |
| **پیچیدگی کد** | بالا (~240 خط) | پایین (~60 خط) | **جدید** |
| **احتمال خطا** | متوسط | پایین | **جدید** |
| **Adaptive** | بله (Learning System) | بله (Volatility Regime) | برابر |
| **Safety** | عالی (6 check) | خوب (2 check) | قدیمی |

---

<a name="section-7"></a>
## بخش ۷: مثال‌های عملی

### 7.1 سناریو ۱: سیگنال LONG ساده (بدون Pattern)

#### سیستم قدیمی:

```python
Current Price = 50,000
ATR = 300
Nearest Support = 49,500
Nearest Resistance = 51,000

# Stop-Loss
# روش 1 (Harmonic): N/A
# روش 2 (Channel): N/A
# روش 3 (S/R): Support = 49,500
Distance = 50,000 - 49,500 = 500
Ratio = 500 / 300 = 1.67 < 3.0 ✅
SL = 49,500 × 0.999 = 49,450.5

# Take-Profit
Risk = 50,000 - 49,450.5 = 549.5
RR = 2.0
Reward = 549.5 × 2.0 = 1,099
TP (default) = 50,000 + 1,099 = 51,099

# S/R Check
Resistance = 51,000
51,000 > 50,000 + (549.5 × 1.5)? → 51,000 > 50,824.25? ✅
TP (final) = 51,000 × 0.999 = 50,949

RR نهایی = (50,949 - 50,000) / 549.5 = 1.73
```

#### سیستم جدید:

```python
Current Price = 50,000
ATR = 300
Volatility Regime = 'normal'
→ ATR Multiplier = 2.0

# Stop-Loss
Stop Distance = 300 × 2.0 = 600
SL = 50,000 - 600 = 49,400

# Take-Profit
Default TP = 50,000 + (600 × 2.0) = 51,200

# S/R Check
Resistance = 51,000
51,000 > 50,000? ✅
(51,000 - 50,000) >= (51,200 - 50,000) × 0.8?
1,000 >= 960? ✅
TP (final) = 51,000

RR نهایی = (51,000 - 50,000) / 600 = 1.67
```

**مقایسه:**
- SL قدیمی: 49,450.5 (نزدیک‌تر به S/R)
- SL جدید: 49,400 (محافظه‌کارانه‌تر - ATR-based)
- TP قدیمی: 50,949
- TP جدید: 51,000
- RR قدیمی: 1.73
- RR جدید: 1.67

### 7.2 سناریو ۲: Bullish Gartley Pattern

#### سیستم قدیمی:

```python
D Point = 50,000
X Point = 52,000
Current Price = 50,100

# Stop-Loss (Pattern-based)
SL = 50,000 × 0.99 = 49,500

# Take-Profit (Pattern-based با Fibonacci)
Risk = 50,100 - 49,500 = 600
TP = 50,100 + (600 × 1.618) = 51,070.8

RR = 1.62
```

#### سیستم جدید:

```python
Current Price = 50,100
ATR = 300
Volatility = 'normal'

# Stop-Loss (ATR-based - pattern ignored!)
SL = 50,100 - (300 × 2.0) = 49,500

# Take-Profit (RR 2.0)
TP = 50,100 + (600 × 2.0) = 51,300

RR = 2.00
```

**مقایسه:**
- SL: یکسان (تصادفاً!)
- TP قدیمی: 51,070.8 (Pattern-specific Fibonacci)
- TP جدید: 51,300 (RR ثابت)
- RR قدیمی: 1.62 (Fibonacci-based)
- RR جدید: 2.00 (ثابت)

**⚠️ نکته مهم:** سیستم جدید اطلاعات Pattern را نادیده می‌گیرد!

### 7.3 سناریو ۳: نوسان بالا

#### سیستم قدیمی:

```python
Current Price = 50,000
ATR = 800 (نوسان بالا!)
Support = 48,500

# Stop-Loss
# S/R Check:
Distance = 50,000 - 48,500 = 1,500
Ratio = 1,500 / 800 = 1.875 < 3.0 ✅
SL = 48,500 × 0.999 = 48,451.5

# Take-Profit
Risk = 1,548.5
TP = 50,000 + (1,548.5 × 2.0) = 53,097

RR = 2.00
```

#### سیستم جدید:

```python
Current Price = 50,000
ATR = 800
Volatility Regime = 'high'
→ ATR Multiplier = 3.0

# Stop-Loss
Stop Distance = 800 × 3.0 = 2,400
SL = 50,000 - 2,400 = 47,600

# Take-Profit
TP = 50,000 + (2,400 × 2.0) = 54,800

RR = 2.00
```

**مقایسه:**
- SL قدیمی: 48,451.5 (S/R-based)
- SL جدید: 47,600 (گسترده‌تر - ATR × 3.0)
- TP قدیمی: 53,097
- TP جدید: 54,800
- سیستم جدید در نوسان بالا **محافظه‌کارانه‌تر** است

---

<a name="section-8"></a>
## بخش ۸: نتیجه‌گیری و توصیه‌ها

### 8.1 نقاط قوت و ضعف

#### سیستم قدیمی:

✅ **نقاط قوت:**
1. Context-Aware (Pattern, S/R, Volatility)
2. دقت بالا برای patterns خاص
3. Fallback محکم (5 سطح)
4. Safety checks عالی (6 بررسی)
5. RR قابل تنظیم

❌ **نقاط ضعف:**
1. پیچیدگی بالا
2. احتمال خطا بیشتر
3. سخت برای debug
4. قابل پیش‌بینی کمتر

#### سیستم جدید:

✅ **نقاط قوت:**
1. ساده و واضح
2. قابل پیش‌بینی
3. Volatility-aware
4. کد تمیز و کوتاه
5. کمتر مستعد خطا

❌ **نقاط ضعف:**
1. Pattern info را نادیده می‌گیرد
2. S/R فقط برای TP (نه SL)
3. RR ثابت (انعطاف کمتر)
4. Safety checks کمتر

### 8.2 جدول امتیازدهی

| معیار | سیستم قدیمی | سیستم جدید | برنده |
|-------|------------|------------|-------|
| **دقت (Accuracy)** | 9/10 | 7/10 | **قدیمی** |
| **سادگی (Simplicity)** | 4/10 | 9/10 | **جدید** |
| **قابل اعتماد (Reliability)** | 7/10 | 9/10 | **جدید** |
| **Context-Awareness** | 9/10 | 6/10 | **قدیمی** |
| **نگهداری (Maintenance)** | 5/10 | 9/10 | **جدید** |
| **Safety** | 9/10 | 7/10 | **قدیمی** |
| **Performance** | 7/10 | 9/10 | **جدید** |

**امتیاز کلی:**
- سیستم قدیمی: **50/70** = 71%
- سیستم جدید: **56/70** = **80%**

### 8.3 توصیه‌ها

#### برای بهبود سیستم جدید:

1. **اضافه کردن Pattern-based SL/TP** (اختیاری)
   ```python
   # اگر Harmonic Pattern قوی یافت شد
   if harmonic_pattern and pattern.quality > 0.8:
       use_pattern_sl_tp = True
   ```

2. **استفاده از S/R برای SL** (نه فقط TP)
   ```python
   # اگر S/R نزدیک و معتبر بود
   if nearest_support and distance < 2 * atr:
       sl = nearest_support * 0.999
   ```

3. **RR قابل تنظیم بر اساس regime**
   ```python
   rr_multipliers = {
       'trending': 2.5,
       'ranging': 1.5,
       'volatile': 2.0
   }
   ```

4. **افزودن Safety Checks بیشتر**

#### برای حفظ مزایای سیستم قدیم:

1. **ماژولار کردن روش‌های SL/TP**
   ```python
   class StopLossCalculator:
       def calculate_from_pattern(...)
       def calculate_from_sr(...)
       def calculate_from_atr(...)
   ```

2. **Testing و Validation بیشتر**

### 8.4 نتیجه نهایی

**برنده کلی: سیستم جدید (80% vs 71%)**

با این حال، **سیستم قدیم در context-awareness برتر است**.

**توصیه ترکیبی:**
```
Base: سیستم جدید (ATR-based)
+
Enhancement: Pattern-specific SL/TP (از سیستم قدیم)
=
بهترین ترکیب!
```

این ترکیب می‌تواند:
- سادگی سیستم جدید را حفظ کند
- دقت سیستم قدیم را اضافه کند
- قابل اعتماد و نگهداری آسان باشد

---

**پایان مقایسه**

برای اطلاعات بیشتر:
- سیستم قدیمی: `Old_bot/Old_signal.md` (بخش 6.2)
- سیستم جدید: `signal_generation/orchestrator.py` (خطوط 635-693)
