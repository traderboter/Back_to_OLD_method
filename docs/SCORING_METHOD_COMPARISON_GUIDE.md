# راهنمای مقایسه روش‌های امتیازدهی (Scoring Methods)

## 🎯 هدف

این راهنما نحوه استفاده از سه روش امتیازدهی مختلف برای **backtest و مقایسه** را توضیح می‌دهد.

---

## 📊 سه روش امتیازدهی

### 1️⃣ NEW SYSTEM (پیش‌فرض)
```yaml
scoring_method: new
```

**ویژگی‌ها:**
- ✅ 8 ضریب (ساده‌تر)
- ✅ base_score وزن‌دهی شده (0-100)
- ✅ امتیاز محدود به 300
- ✅ confluence بر اساس Alignment
- ✅ معماری ماژولار

**فرمول:**
```python
final_score = base_score
    × (1 + confluence_bonus)      # 0-0.5
    × timeframe_weight             # 0.5-1.8
    × trend_alignment              # 0.8-1.2
    × volume_confirmation          # 1.0-1.1
    × pattern_quality              # 1.0-1.5
    × macd_analysis_score          # 0.85-1.2
    × htf_multiplier               # 0.7-1.3
    × volatility_multiplier        # 0.6-1.5

# محدود به 300
final_score = min(final_score, 300)
```

**مثال خروجی:**
- سیگنال ضعیف: 50-80
- سیگنال متوسط: 80-150
- سیگنال قوی: 150-300

---

### 2️⃣ OLD SYSTEM (سازگار با سیستم قدیمی)
```yaml
scoring_method: old
```

**ویژگی‌ها:**
- ⚙️ 13 ضریب (مثل سیستم قبلی)
- ⚙️ base_score جمع دستی
- ⚙️ امتیاز نامحدود (می‌تواند > 1000)
- ⚙️ confluence بر اساس RR (اگر فعال باشد)
- ⚙️ symbol_performance_factor (Adaptive Learning)

**فرمول:**
```python
final_score = base_score
    × (1 + confluence_bonus)       # RR-based
    × timeframe_weight              # 0.7-1.2
    × trend_alignment               # 0.8-1.2
    × volume_confirmation           # 1.0-1.4 (محدوده بیشتر)
    × pattern_quality               # 1.0-1.5
    × symbol_performance_factor     # 0.8-1.3 ✨
    × correlation_safety_factor     # 0.5-1.0 ✨
    × macd_analysis_score           # 0.85-1.15
    × structure_score               # 0.8-1.2 ✨
    × volatility_multiplier         # 0.5-1.0
    × harmonic_multiplier           # 1.0-1.2 ✨
    × channel_multiplier            # 1.0-1.1 ✨
    × cyclical_multiplier           # 1.0-1.1 ✨

# نامحدود (اگر max_final_score = 0)
```

**مثال خروجی:**
- سیگنال ضعیف: 100-250
- سیگنال متوسط: 250-500
- سیگنال قوی: 500-1000+

---

### 3️⃣ HYBRID SYSTEM (ترکیبی)
```yaml
scoring_method: hybrid
```

**ویژگی‌ها:**
- 🔀 NEW base_score (وزن‌دهی منظم)
- 🔀 OLD multipliers (بیشتر)
- 🔀 بهترین از هر دو دنیا
- 🔀 confluence قابل تنظیم (RR یا Alignment)
- 🔀 امتیاز محدود یا نامحدود (قابل تنظیم)

**فرمول:**
```python
final_score = base_score              # NEW: normalized 0-100
    × (1 + confluence_bonus)          # RR or Alignment
    × timeframe_weight                 # 0.5-1.8 (NEW)
    × trend_alignment                  # 0.8-1.2
    × volume_confirmation              # 1.0-1.4 (OLD range)
    × pattern_quality                  # 1.0-1.5
    × symbol_performance_factor        # 0.8-1.3 (if enabled)
    × macd_analysis_score              # 0.85-1.2
    × htf_multiplier                   # 0.7-1.3 (NEW)
    × volatility_multiplier            # 0.6-1.5 (NEW)
```

**مثال خروجی:**
- بین NEW و OLD (بسته به تنظیمات)

---

## ⚙️ نحوه استفاده

### روش 1: Backtest با NEW (پیش‌فرض)

**کانفیگ:**
```yaml
# config.yaml
signal_processing:
  scoring:
    scoring_method: new
```

**اجرای backtest:**
```bash
python main.py backtest --config config.yaml
```

**نتایج:**
- امتیازات 0-300
- ساده‌تر برای تنظیم threshold
- مقایسه آسان بین سیگنال‌ها

---

### روش 2: Backtest با OLD (سازگاری)

**کانفیگ:**
```yaml
# config.yaml
signal_processing:
  scoring:
    scoring_method: old

    old_system:
      # فعال کردن ضرایب OLD
      symbol_performance_enabled: true
      correlation_safety_enabled: true
      structure_score_enabled: true

      # مقادیر پیش‌فرض (اگر داده ندارید)
      symbol_performance_default: 1.0
      correlation_safety_default: 1.0
      structure_score_default: 1.0

      # confluence بر اساس RR
      use_rr_based_confluence: true

      # نامحدود
      max_final_score: 0
```

**اجرای backtest:**
```bash
python main.py backtest --config config_old.yaml
```

**نتایج:**
- امتیازات نامحدود (می‌تواند > 1000)
- سازگار با سیستم قبلی
- برای مقایسه با نتایج قدیمی

---

### روش 3: Backtest با HYBRID (تست ترکیبی)

**کانفیگ:**
```yaml
# config.yaml
signal_processing:
  scoring:
    scoring_method: hybrid

    old_system:
      # فقط symbol_performance فعال
      symbol_performance_enabled: true
      symbol_performance_default: 1.0

      # بقیه غیرفعال
      correlation_safety_enabled: false
      structure_score_enabled: false

      # Alignment-based confluence
      use_rr_based_confluence: false

      # محدود به 300
      max_final_score: 300
```

**اجرای backtest:**
```bash
python main.py backtest --config config_hybrid.yaml
```

**نتایج:**
- امتیازات 0-300 (یا نامحدود)
- base_score بهتر (NEW)
- multipliers بیشتر (OLD)

---

## 📈 مقایسه نتایج Backtest

### مرحله 1: اجرای سه backtest

```bash
# 1. NEW
cp config.yaml config_new.yaml
# تنظیم: scoring_method: new
python main.py backtest --config config_new.yaml --output results_new.json

# 2. OLD
cp config.yaml config_old.yaml
# تنظیم: scoring_method: old
python main.py backtest --config config_old.yaml --output results_old.json

# 3. HYBRID
cp config.yaml config_hybrid.yaml
# تنظیم: scoring_method: hybrid
python main.py backtest --config config_hybrid.yaml --output results_hybrid.json
```

---

### مرحله 2: مقایسه نتایج

**معیارهای مقایسه:**

| معیار | توضیح | بهتر = |
|-------|-------|--------|
| **Win Rate** | نرخ برد | بالاتر ✅ |
| **Average Profit** | میانگین سود | بالاتر ✅ |
| **Max Drawdown** | حداکثر افت | پایین‌تر ✅ |
| **Sharpe Ratio** | نسبت شارپ | بالاتر ✅ |
| **Total Trades** | تعداد معاملات | - |
| **Avg Signal Score** | میانگین امتیاز سیگنال | - |

**مثال نتایج:**
```
NEW SYSTEM:
- Win Rate: 62%
- Avg Profit: 2.8%
- Max Drawdown: -12%
- Sharpe Ratio: 1.8
- Total Trades: 150
- Avg Score: 120 (محدوده: 60-280)

OLD SYSTEM:
- Win Rate: 58%
- Avg Profit: 3.1%
- Max Drawdown: -15%
- Sharpe Ratio: 1.5
- Total Trades: 180
- Avg Score: 380 (محدوده: 150-950)

HYBRID SYSTEM:
- Win Rate: 64%
- Avg Profit: 3.2%
- Max Drawdown: -10%
- Sharpe Ratio: 2.0
- Total Trades: 140
- Avg Score: 150 (محدوده: 70-290)
```

**نتیجه:** HYBRID بهترین است! ✅

---

## 🔧 تنظیمات پیشرفته

### تنظیم Threshold ها بر اساس Method

**NEW:**
```yaml
validation:
  min_signal_score: 60        # حداقل 60 از 300
  strong_signal_threshold: 150 # قوی > 150
```

**OLD:**
```yaml
validation:
  min_signal_score: 200       # حداقل 200 از نامحدود
  strong_signal_threshold: 500 # قوی > 500
```

**HYBRID:**
```yaml
validation:
  min_signal_score: 80        # حداقل 80 از 300
  strong_signal_threshold: 180 # قوی > 180
```

---

### فعال/غیرفعال کردن ضرایب OLD

```yaml
old_system:
  # کنترل دقیق ضرایب OLD
  symbol_performance_enabled: true   # یادگیری تطبیقی
  correlation_safety_enabled: false  # همبستگی
  structure_score_enabled: false     # ساختار HTF
  harmonic_separate_multiplier: false # هارمونیک جدا
  channel_separate_multiplier: false  # کانال جدا
  cyclical_separate_multiplier: false # چرخه‌ای جدا
```

**توصیه برای HYBRID:**
- فقط `symbol_performance_enabled: true` فعال کنید
- بقیه غیرفعال (از NEW استفاده می‌کند)

---

## 📊 نمونه نتایج Backtest

### سناریو: BTC/USDT - 6 ماه - 1h

**NEW:**
```json
{
  "total_trades": 150,
  "win_rate": 62.0,
  "avg_profit": 2.8,
  "max_drawdown": -12.0,
  "sharpe_ratio": 1.8,
  "avg_signal_score": 120,
  "score_range": [60, 280],
  "top_signals": [
    {"score": 280, "profit": 8.2},
    {"score": 260, "profit": 6.5},
    {"score": 240, "profit": 5.1}
  ]
}
```

**OLD:**
```json
{
  "total_trades": 180,
  "win_rate": 58.0,
  "avg_profit": 3.1,
  "max_drawdown": -15.0,
  "sharpe_ratio": 1.5,
  "avg_signal_score": 380,
  "score_range": [150, 950],
  "top_signals": [
    {"score": 950, "profit": 9.5},
    {"score": 820, "profit": 7.2},
    {"score": 760, "profit": 6.8}
  ]
}
```

**HYBRID:**
```json
{
  "total_trades": 140,
  "win_rate": 64.0,
  "avg_profit": 3.2,
  "max_drawdown": -10.0,
  "sharpe_ratio": 2.0,
  "avg_signal_score": 150,
  "score_range": [70, 290],
  "top_signals": [
    {"score": 290, "profit": 8.8},
    {"score": 275, "profit": 7.5},
    {"score": 260, "profit": 6.9}
  ]
}
```

---

## ✅ توصیه‌های نهایی

### 1. برای Production
```yaml
scoring_method: new  # یا hybrid (اگر backtest بهتر بود)
```
- ساده‌تر برای نگهداری
- امتیازات normalized
- کنترل بهتر

### 2. برای مقایسه با قدیم
```yaml
scoring_method: old
```
- سازگاری با سیستم قبلی
- برای validation

### 3. برای بهترین نتیجه
```yaml
scoring_method: hybrid
old_system:
  symbol_performance_enabled: true
  use_rr_based_confluence: false
  max_final_score: 300
```
- NEW base scoring (بهتر)
- symbol_performance (یادگیری)
- محدود به 300 (کنترل)

---

## 🎯 خلاصه

1. **سه روش دارید:** new, old, hybrid
2. **Backtest هر سه را اجرا کنید**
3. **نتایج را مقایسه کنید** (Win Rate, Profit, Drawdown)
4. **بهترین را انتخاب کنید**
5. **Threshold ها را تنظیم کنید**

**هدف:** داده‌محور تصمیم بگیرید، نه حدس! 📊

---

**تاریخ:** 2025-11-18
**نسخه:** 1.0
**نویسنده:** Claude
**وضعیت:** ✅ آماده برای backtest
