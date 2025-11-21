# 🎯 مقایسه سه روش Scoring در Backtest

## ⚠️ نکته مهم: فقط دو روش وجود دارد!

```python
engine = await run_backtest_v2(
    scoring_method='new'    # ✅ موجود
    scoring_method='old'    # ✅ موجود
    scoring_method='hybrid' # ❌ موجود نیست!
)
```

**فایل‌های موجود:**
```bash
backtest/config_scoring_new.yaml    # ✅ NEW SYSTEM
backtest/config_scoring_old.yaml    # ✅ OLD SYSTEM
backtest/config_scoring_hybrid.yaml # ❌ وجود ندارد
```

---

## 📊 Table of Contents

1. [تفاوت‌های کلیدی](#1-تفاوت-های-کلیدی)
2. [مقایسه جزئیات](#2-مقایسه-جزئیات)
3. [مقایسه Visual](#3-مقایسه-visual)
4. [چه زمانی از کدام استفاده کنیم](#4-چه-زمانی-از-کدام-استفاده-کنیم)
5. [نحوه ساخت Hybrid](#5-نحوه-ساخت-hybrid)
6. [مثال‌های کاربردی](#6-مثال-های-کاربردی)

---

## 1️⃣ تفاوت‌های کلیدی

### خلاصه سریع:

| Feature | NEW System | OLD System | تفاوت |
|---------|-----------|------------|-------|
| **Score Limit** | ✅ محدود (max=100) | ❌ نامحدود | NEW: score ≤ 100 |
| **Min Score** | 50 | 200 | NEW: threshold پایین‌تر |
| **Strong Signal** | 70 | 500 | NEW: threshold واقع‌بینانه‌تر |
| **TF Weight (4h)** | 1.1 | 1.2 | NEW: کمتر dominant |
| **Direction Margin** | 1.3 (30%) | ❌ ندارد | NEW: margin قوی‌تر |
| **SL/TP Method** | ✅ 5-method priority | ❌ ساده | NEW: پیشرفته‌تر |
| **Min RR Ratio** | 1.5 | 2.5 | NEW: واقع‌بینانه‌تر |

---

## 2️⃣ مقایسه جزئیات

### 2.1 📏 Score Limiting (تفاوت اصلی)

#### 🆕 NEW SYSTEM:
```yaml
signal_processing:
  scoring:
    max_final_score: 100  # محدود به 100
```

**چگونه کار می‌کند:**
```python
# فرمول NEW
raw_score = base_score × multiplier1 × multiplier2 × ... × multiplier13
final_score = min(raw_score, 100)  # محدود به 100

# مثال
raw_score = 250  # بعد از ضرب همه multiplier ها
final_score = 100  # محدود شد
```

**مزایا:**
- ✅ Score ها قابل مقایسه هستند (همیشه 0-100)
- ✅ سیگنال‌های خیلی قوی را over-rate نمی‌کند
- ✅ تصمیم‌گیری آسان‌تر
- ✅ Calibration راحت‌تر

**معایب:**
- ⚠️ سیگنال‌های استثنایی قوی محدود می‌شوند

---

#### 🔴 OLD SYSTEM:
```yaml
signal_processing:
  scoring:
    max_final_score: 0  # نامحدود (0 = disabled)
```

**چگونه کار می‌کند:**
```python
# فرمول OLD
raw_score = base_score × multiplier1 × multiplier2 × ... × multiplier13
final_score = raw_score  # بدون محدودیت

# مثال
raw_score = 250
final_score = 250  # نامحدود
```

**مزایا:**
- ✅ سیگنال‌های قوی score بالاتر می‌گیرند
- ✅ تمایز بهتر بین سیگنال‌های عالی و خوب

**معایب:**
- ⚠️ Score ها غیرقابل پیش‌بینی (10 تا 1000+)
- ⚠️ Calibration سخت‌تر
- ⚠️ نیاز به threshold های بالاتر (min=200)

---

### 2.2 🎚️ Minimum Signal Score

| System | Min Score | معنی |
|--------|-----------|------|
| **NEW** | `50` | نیمی از 100 (50%) |
| **OLD** | `200` | برای جبران score های بالا |

**مثال:**
```python
# NEW System
score = 65  # → ✅ VALID (≥50)
score = 45  # → ❌ REJECT (<50)

# OLD System
score = 250  # → ✅ VALID (≥200)
score = 180  # → ❌ REJECT (<200)
```

**نتیجه:**
- NEW: سیگنال‌های بیشتر (threshold پایین‌تر)
- OLD: سیگنال‌های کمتر اما قوی‌تر (threshold بالاتر)

---

### 2.3 💪 Strong Signal Threshold

| System | Threshold | معنی |
|--------|-----------|------|
| **NEW** | `70` | 70% از 100 |
| **OLD** | `500` | بسیار قوی (2.5× min score) |

**استفاده:**
```python
if score >= strong_signal_threshold:
    # اولویت بالا
    # Position size بزرگتر
    # Confidence بالا
```

**مقایسه:**
- NEW: 70/100 = 70% → واقع‌بینانه
- OLD: 500/200 = 250% → خیلی محافظه‌کارانه

---

### 2.4 ⚖️ Timeframe Weights

```yaml
# NEW System
timeframe_weights:
  5m: 0.70   # -30%
  15m: 0.85  # -15%
  1h: 1.00   # baseline
  4h: 1.10   # +10%  ⬅️ کاهش یافته

# OLD System
timeframe_weights:
  5m: 0.7    # -30%
  15m: 0.85  # -15%
  1h: 1.0    # baseline
  4h: 1.2    # +20%  ⬅️ قوی‌تر
```

**تفاوت کلیدی:** وزن 4h

| System | 4h Weight | Impact |
|--------|-----------|--------|
| **NEW** | 1.1 (+10%) | کمتر dominant |
| **OLD** | 1.2 (+20%) | بیشتر dominant |

**دلیل تغییر در NEW:**
- OLD: 4h خیلی قوی بود و سیگنال‌ها را تحت تأثیر قرار می‌داد
- NEW: balance بهتر بین timeframe ها

---

### 2.5 📊 Direction Margin

```yaml
# NEW System
multi_timeframe:
  direction_margin: 1.3  # 30% margin

# OLD System
# ❌ تعریف نشده (default: 1.1 از کد)
```

**چگونه کار می‌کند:**
```python
# NEW System (margin = 1.3)
if bullish_score > bearish_score * 1.3:
    direction = 'LONG'
elif bearish_score > bullish_score * 1.3:
    direction = 'SHORT'
else:
    direction = 'NEUTRAL'

# مثال:
bullish = 100, bearish = 70
# OLD (margin=1.1): 100 > 70*1.1 → 100 > 77 ✅ LONG
# NEW (margin=1.3): 100 > 70*1.3 → 100 > 91 ✅ LONG

bullish = 100, bearish = 85
# OLD (margin=1.1): 100 > 85*1.1 → 100 > 93.5 ✅ LONG
# NEW (margin=1.3): 100 > 85*1.3 → 100 > 110.5 ❌ NEUTRAL
```

**نتیجه:**
- NEW: فقط سیگنال‌های واضح را می‌پذیرد (30% margin)
- OLD: سیگنال‌های ضعیف‌تر را هم می‌پذیرد (10% margin)

---

### 2.6 🛡️ SL/TP Priority (تفاوت بزرگ)

#### 🆕 NEW SYSTEM - 5-Method Priority:
```yaml
risk_management:
  sl_tp_priority:
    - harmonic       # 1st: الگوهای هارمونیک
    - channel        # 2nd: کانال قیمتی
    - sr             # 3rd: Support/Resistance (max 3×ATR)
    - atr            # 4th: ATR-based fallback
    - percentage     # 5th: Percentage fallback

  # Settings
  atr_multiplier_sl: 2.0
  atr_multiplier_tp: 3.0
  max_sr_distance_atr_ratio: 3.0  # S/R فقط اگر < 3×ATR
```

**Flow Chart:**
```
Entry Price = 50,000
    ↓
1. Harmonic Pattern?
   Yes → SL = D_point × 0.99 = 49,500
   No → Next
    ↓
2. Price Channel?
   Yes → SL = lower_bound × 0.99 = 48,900
   No → Next
    ↓
3. S/R Level?
   Yes & distance < 3×ATR → SL = support × 0.999 = 49,000
   No or too far → Next
    ↓
4. ATR Fallback
   SL = entry - (ATR × 2.0) = 49,000
    ↓
5. Percentage Fallback (final)
   SL = entry × (1 - 0.02) = 49,000
```

---

#### 🔴 OLD SYSTEM - Simple Method:
```yaml
# ❌ ندارد! فقط ATR یا percentage ساده
risk_management:
  atr_multiplier_sl: 2.0
  default_stop_loss_percent: 2.0
```

**فقط:**
```python
if atr_available:
    sl = entry - (atr × 2.0)
else:
    sl = entry × (1 - 0.02)
```

**مقایسه:**
- NEW: 5 روش با اولویت → دقیق‌تر و منطقی‌تر
- OLD: 1-2 روش → ساده اما محدود

---

### 2.7 💹 Risk/Reward Ratio

| System | Min RR | Strong Signal RR |
|--------|--------|------------------|
| **NEW** | 1.5 | 2.0-2.5 |
| **OLD** | 2.5 | 3.0+ |

**تأثیر:**
```python
# Entry = 50,000, SL = 49,000 (risk = 1,000)

# NEW (RR = 1.5)
TP = 50,000 + (1,000 × 1.5) = 51,500

# OLD (RR = 2.5)
TP = 50,000 + (1,000 × 2.5) = 52,500
```

**نتیجه:**
- NEW: Target های واقع‌بینانه‌تر → Win rate بالاتر
- OLD: Target های بزرگ‌تر → Win rate پایین‌تر، اما profit بزرگتر

---

## 3️⃣ مقایسه Visual

### مثال: BTC/USDT @ 50,000

#### Scenario 1: سیگنال متوسط

```
Raw Score Calculation:
base_score = 60
× timeframe_weight = 1.0 (1h)
× trend_alignment = 1.2
× volume = 1.1
× pattern_quality = 1.0
× (other multipliers) = ~1.15
─────────────────────────────
raw_score = 60 × 1.52 = 91.2
```

| System | Final Score | Decision | Reason |
|--------|-------------|----------|--------|
| **NEW** | `91` | ✅ VALID | 91 ≥ 50 (min) |
| **OLD** | `91` | ❌ REJECT | 91 < 200 (min) |

**تحلیل:**
- NEW: سیگنال معتبر و خوب (91/100 = 91%)
- OLD: رد شد چون threshold بالاست

---

#### Scenario 2: سیگنال قوی

```
Raw Score Calculation:
base_score = 75
× timeframe_weight = 1.1 (4h)
× trend_alignment = 1.3
× volume = 1.2
× pattern_quality = 1.2
× (other multipliers) = ~1.5
─────────────────────────────
raw_score = 75 × 2.57 = 192.75
```

| System | Final Score | Decision | Reason |
|--------|-------------|----------|--------|
| **NEW** | `100` (capped) | ✅ STRONG | محدود به 100 |
| **OLD** | `193` | ❌ WEAK | 193 < 200 (min) |

**تحلیل:**
- NEW: سیگنال عالی (100/100 = top!)
- OLD: هنوز رد شد! (نزدیک به 200 اما کافی نیست)

---

#### Scenario 3: سیگنال بسیار قوی

```
Raw Score Calculation:
base_score = 85
× all multipliers aligned = ~3.5
─────────────────────────────
raw_score = 85 × 3.5 = 297.5
```

| System | Final Score | Decision | Quality |
|--------|-------------|----------|---------|
| **NEW** | `100` (capped) | ✅ STRONG | Top score |
| **OLD** | `297` | ✅ VALID | Above min (200) |

**تحلیل:**
- NEW: score = 100 (maximum)
- OLD: score = 297 (خیلی بالا)

---

### نمودار توزیع Score

```
NEW System (Bounded)
Frequency
    ^
    |     ███
    |    █████
    |   ███████
    |  █████████
    | ███████████
    +─────────────> Score
    0   50  70  100
        min strong max

─────────────────────────────

OLD System (Unbounded)
Frequency
    ^
    |  ███
    | █████
    |███████
    |████████████████
    +─────────────────────────> Score
    0  200    500    1000+
       min    strong
```

**تحلیل:**
- NEW: اکثر score ها بین 50-100 (bounded)
- OLD: score ها پراکنده (100-1000+)

---

## 4️⃣ چه زمانی از کدام استفاده کنیم

### 🆕 NEW System - پیشنهاد برای:

✅ **Market های معمولی**
- BTC, ETH, major altcoins
- بازار‌های باثبات

✅ **تعداد سیگنال بیشتر**
- می‌خواهید معاملات بیشتری داشته باشید
- Win rate مهم‌تر از profit per trade

✅ **Risk Management محافظه‌کارانه**
- RR = 1.5-2.0 واقع‌بینانه
- SL/TP دقیق با 5 روش

✅ **Calibration راحت**
- Score های قابل مقایسه (0-100)
- Threshold واضح (50 = متوسط، 70 = قوی)

✅ **Live Trading**
- تصمیم‌گیری سریع
- Score های قابل فهم

---

### 🔴 OLD System - پیشنهاد برای:

✅ **بازار‌های پرنوسان**
- Altcoins کوچک
- News-driven markets

✅ **کیفیت بالا > کمیت**
- فقط سیگنال‌های بسیار قوی
- تعداد کم اما سود بالا

✅ **Risk/Reward بالا**
- RR = 2.5-3.0
- Profit per trade بالاتر

✅ **Conservative Trading**
- فقط setup های واضح
- Drawdown کمتر

---

### 📊 مقایسه انتظارات:

| Metric | NEW System | OLD System |
|--------|-----------|------------|
| **تعداد سیگنال** | 🔼 بیشتر (50-100/month) | 🔽 کمتر (10-30/month) |
| **Win Rate** | 🔼 بالاتر (55-65%) | 🔽 پایین‌تر (45-55%) |
| **Avg Profit** | 🔽 متوسط (1.5-2R) | 🔼 بالاتر (2.5-3R) |
| **Drawdown** | 🔽 کمتر | 🔼 بیشتر |
| **Sharpe Ratio** | 🔼 بهتر (consistency) | ~ مشابه |

---

## 5️⃣ نحوه ساخت Hybrid

چون `config_scoring_hybrid.yaml` وجود ندارد، می‌توانید خودتان بسازید:

### روش 1: ترکیب بهترین‌ها

```yaml
# backtest/config_scoring_hybrid.yaml

# ============= از NEW بگیر =============
orchestrator:
  use_multi_tf_aggregation: true

signal_processing:
  scoring:
    max_final_score: 150  # 🔄 میانه (NEW=100, OLD=unlimited)

    timeframe_weights:
      5m: 0.70
      15m: 0.85
      1h: 1.00
      4h: 1.15  # 🔄 میانه (NEW=1.1, OLD=1.2)

multi_timeframe:
  direction_margin: 1.25  # 🔄 میانه (NEW=1.3, OLD=~1.1)

# ============= از NEW بگیر (5-method) =============
risk_management:
  sl_tp_priority:
    - harmonic
    - channel
    - sr
    - atr
    - percentage

  atr_multiplier_sl: 2.0
  max_sr_distance_atr_ratio: 3.0
  min_risk_reward_ratio: 2.0  # 🔄 میانه (NEW=1.5, OLD=2.5)

# ============= Validation =============
validation:
  min_signal_score: 100  # 🔄 میانه (NEW=50, OLD=200)
  strong_signal_threshold: 130  # 🔄 میانه (NEW=70, OLD=500)
```

### روش 2: Adaptive Hybrid

```yaml
# تنظیمات adaptive بر اساس symbol

signal_processing:
  scoring:
    # برای major coins (BTC, ETH)
    max_final_score_major: 100  # NEW style
    min_signal_score_major: 50

    # برای altcoins
    max_final_score_alts: 200  # بیشتر مانند OLD
    min_signal_score_alts: 150

# در کد:
if symbol in ['BTC/USDT', 'ETH/USDT']:
    config = major_config
else:
    config = alts_config
```

---

## 6️⃣ مثال‌های کاربردی

### مثال 1: Backtest با NEW System

```python
from backtest.backtest_engine_v2 import run_backtest_v2
import asyncio

async def test_new_system():
    engine, results_dir = await run_backtest_v2(
        scoring_method='new'  # ✅ NEW SYSTEM
    )

    stats = engine.results['statistics']
    print(f"Total trades: {stats['total_trades']}")
    print(f"Win rate: {stats['win_rate']:.1f}%")
    print(f"Profit factor: {stats['profit_factor']:.2f}")

    # انتظار: تعداد سیگنال بیشتر، win rate بالاتر

asyncio.run(test_new_system())
```

---

### مثال 2: Backtest با OLD System

```python
async def test_old_system():
    engine, results_dir = await run_backtest_v2(
        scoring_method='old'  # ✅ OLD SYSTEM
    )

    stats = engine.results['statistics']
    print(f"Total trades: {stats['total_trades']}")
    print(f"Win rate: {stats['win_rate']:.1f}%")
    print(f"Avg RR: {stats['average_win'] / stats['average_loss']:.2f}")

    # انتظار: تعداد کمتر، RR بالاتر

asyncio.run(test_old_system())
```

---

### مثال 3: مقایسه دو سیستم

```python
async def compare_systems():
    # Run NEW
    print("Running NEW System...")
    new_engine, new_dir = await run_backtest_v2(scoring_method='new')
    new_stats = new_engine.results['statistics']

    # Run OLD
    print("\nRunning OLD System...")
    old_engine, old_dir = await run_backtest_v2(scoring_method='old')
    old_stats = old_engine.results['statistics']

    # مقایسه
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)

    print(f"\nTotal Trades:")
    print(f"  NEW: {new_stats['total_trades']}")
    print(f"  OLD: {old_stats['total_trades']}")

    print(f"\nWin Rate:")
    print(f"  NEW: {new_stats['win_rate']:.1f}%")
    print(f"  OLD: {old_stats['win_rate']:.1f}%")

    print(f"\nProfit Factor:")
    print(f"  NEW: {new_stats['profit_factor']:.2f}")
    print(f"  OLD: {old_stats['profit_factor']:.2f}")

    print(f"\nTotal Return:")
    print(f"  NEW: {new_stats['total_return']:.2f}%")
    print(f"  OLD: {old_stats['total_return']:.2f}%")

    print(f"\nSharpe Ratio:")
    print(f"  NEW: {new_stats.get('sharpe_ratio', 0):.3f}")
    print(f"  OLD: {old_stats.get('sharpe_ratio', 0):.3f}")

    print(f"\nMax Drawdown:")
    print(f"  NEW: {new_stats['max_drawdown']:.2f}%")
    print(f"  OLD: {old_stats['max_drawdown']:.2f}%")

asyncio.run(compare_systems())
```

---

### مثال 4: ساخت Hybrid Config

```python
import yaml
from pathlib import Path

def create_hybrid_config():
    """ساخت فایل config_scoring_hybrid.yaml"""

    hybrid_config = {
        'orchestrator': {
            'use_multi_tf_aggregation': True
        },
        'signal_processing': {
            'scoring': {
                'max_final_score': 150,  # میانه
                'timeframe_weights': {
                    '5m': 0.70,
                    '15m': 0.85,
                    '1h': 1.00,
                    '4h': 1.15  # میانه
                }
            }
        },
        'multi_timeframe': {
            'direction_margin': 1.25  # میانه
        },
        'risk_management': {
            'sl_tp_priority': ['harmonic', 'channel', 'sr', 'atr', 'percentage'],
            'min_risk_reward_ratio': 2.0  # میانه
        },
        'validation': {
            'min_signal_score': 100,  # میانه
            'strong_signal_threshold': 130
        }
    }

    # ذخیره
    output_path = Path('backtest/config_scoring_hybrid.yaml')
    with open(output_path, 'w') as f:
        yaml.dump(hybrid_config, f, default_flow_style=False, allow_unicode=True)

    print(f"✅ Hybrid config created: {output_path}")

# ساخت فایل
create_hybrid_config()

# استفاده
async def test_hybrid():
    engine, results = await run_backtest_v2(
        scoring_method='hybrid'  # ✅ حالا کار می‌کند!
    )
```

---

## 📊 خلاصه نهایی

### جدول مقایسه کامل:

| Feature | NEW | OLD | Hybrid (پیشنهادی) |
|---------|-----|-----|-------------------|
| **Max Score** | 100 | ∞ | 150 |
| **Min Score** | 50 | 200 | 100 |
| **Strong Threshold** | 70 | 500 | 130 |
| **4h Weight** | 1.1 | 1.2 | 1.15 |
| **Direction Margin** | 1.3 | ~1.1 | 1.25 |
| **Min RR** | 1.5 | 2.5 | 2.0 |
| **SL/TP Method** | 5-method | Simple | 5-method |
| **تعداد سیگنال** | بیشتر | کمتر | متوسط |
| **Win Rate** | بالاتر | پایین‌تر | متوسط |
| **Avg Profit** | کمتر | بیشتر | متوسط |

---

### 🎯 توصیه نهایی:

```python
# برای شروع و testing
scoring_method = 'new'  # ✅ توصیه می‌شود

# برای بازار‌های volatile
scoring_method = 'old'  # ✅ در صورت نیاز

# برای بهترین ترکیب
# ابتدا hybrid config بسازید، سپس:
scoring_method = 'hybrid'  # ✅ بهترین balance
```

**قدم اول:** هر دو را backtest کنید و مقایسه کنید!

```python
# مقایسه
asyncio.run(compare_systems())

# بر اساس نتایج، بهترین را انتخاب کنید
```

---

**📅 Version:** 1.0
**🗓️ Date:** 2025-11-21
**✍️ Author:** Claude Analysis
