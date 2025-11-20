# Pattern Recency Scoring System - گزارش پیاده‌سازی

تاریخ: 2025-10-25
نسخه: 1.0.0
وضعیت: ✅ **پیاده‌سازی کامل**

---

## 🎯 خلاصه

سیستم **Recency Scoring** با موفقیت پیاده‌سازی شد. این سیستم به الگوهای تشخیص داده شده در چند کندل اخیر (نه فقط کندل آخر) امتیاز می‌دهد و بر اساس تازگی آن‌ها ضریب اعمال می‌کند.

## 📊 مشکل قبلی vs راه‌حل جدید

### قبل از پیاده‌سازی:
```
❌ فقط آخرین کندل بررسی می‌شد
❌ اگر الگو در 2-3 کندل قبل بود → از دست می‌رفت
❌ امتیازدهی binary بود (وجود دارد/ندارد)
```

### بعد از پیاده‌سازی:
```
✅ 5 کندل آخر بررسی می‌شود (قابل تنظیم)
✅ الگوهای اخیر با ضریب کمتر (0.5-1.0) امتیاز می‌گیرند
✅ امتیازدهی پیوسته و منصفانه
```

---

## 🛠️ تغییرات انجام شده

### 1. فایل‌های جدید:
- ✅ `signal_generation/analyzers/patterns/pattern_config.json` - تنظیمات recency برای همه الگوها
- ✅ `test_recency_scoring.py` - تست سیستم جدید
- ✅ `RECENCY_SCORING_IMPLEMENTATION.md` - این فایل

### 2. فایل‌های به‌روز شده:

#### `signal_generation/analyzers/patterns/base_pattern.py`
```python
# تغییرات در __init__:
- اضافه شدن lookback_window (پیش‌فرض: 5)
- اضافه شدن recency_multipliers (پیش‌فرض: [1.0, 0.9, 0.8, 0.7, 0.6, 0.5])
- اضافه شدن _last_detection_candles_ago (برای cache)

# تغییرات در _get_detection_details:
- برگرداندن recency_multiplier
- برگرداندن candles_ago
- برگرداندن location ('current' یا 'recent')

# تغییرات در get_pattern_info:
- اضافه شدن recency_multiplier به pattern_info
```

#### `signal_generation/analyzers/patterns/candlestick/hammer.py`
```python
# نسخه: 2.0.0 → 3.0.0

# تغییرات در detect():
- حلقه روی lookback_window کندل آخر
- ذخیره _last_detection_candles_ago
- پشتیبانی از multi-candle detection

# تغییرات در _get_detection_details():
- محاسبه recency_multiplier
- اعمال ضریب روی confidence
- برگرداندن اطلاعات کامل recency
```

#### `signal_generation/analyzers/pattern_analyzer.py`
```python
# تغییرات در _apply_context_aware_scoring:
- اعمال recency_multiplier در محاسبه multiplier
- multiplier *= recency_multiplier
```

---

## 📈 فرمول امتیازدهی جدید

### قبلاً:
```
score = base_weight × confidence × context_multiplier
```

### حالا:
```
score = base_weight × confidence × context_multiplier × recency_multiplier
```

### مثال:
```python
# Hammer در کندل آخر
candles_ago = 0
recency_multiplier = 1.0
score = 3 × 0.85 × 1.5 × 1.0 = 3.825

# Hammer در 2 کندل قبل
candles_ago = 2
recency_multiplier = 0.8
score = 3 × 0.85 × 1.5 × 0.8 = 3.060  # کمتر از حالت قبل
```

---

## ⚙️ پیکربندی

### فایل Config: `pattern_config.json`

```json
{
  "patterns": {
    "hammer": {
      "enabled": true,
      "weight": 3,
      "min_candles": 12,
      "lookback_window": 5,
      "recency_multipliers": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
    }
  }
}
```

### توضیحات پارامترها:

| پارامتر | توضیحات | مقدار پیش‌فرض |
|---------|---------|---------------|
| `lookback_window` | چند کندل آخر را بررسی کنیم | 5 |
| `recency_multipliers` | ضریب هر کندل (index 0 = آخرین) | [1.0, 0.9, 0.8, 0.7, 0.6, 0.5] |
| `min_candles` | حداقل کندل برای detection | 12 (بر اساس تحقیق TA-Lib) |

### ضرایب مختلف برای الگوهای مختلف:

#### الگوهای قوی (decay کند):
```json
"engulfing": {
  "recency_multipliers": [1.0, 0.95, 0.85, 0.75, 0.6, 0.4]
}
```

#### الگوهای متوسط (decay معمولی):
```json
"hammer": {
  "recency_multipliers": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
}
```

#### الگوهای ضعیف (decay سریع):
```json
"doji": {
  "recency_multipliers": [1.0, 0.7, 0.5, 0.3, 0.15, 0.05]
}
```

---

## 🧪 نحوه تست

### تست اتوماتیک:
```bash
python test_recency_scoring.py
```

### تست دستی:
```python
from signal_generation.analyzers.patterns.candlestick.hammer import HammerPattern
import json

# Load config
with open('signal_generation/analyzers/patterns/pattern_config.json', 'r') as f:
    config = json.load(f)

# Create detector
detector = HammerPattern(config=config)

# Detect
detected = detector.detect(df)

if detected:
    details = detector._get_detection_details(df)
    print(f"Candles ago: {details['candles_ago']}")
    print(f"Recency multiplier: {details['recency_multiplier']}")
    print(f"Confidence: {details['confidence']}")
```

---

## 📊 خروجی نمونه

```json
{
  "name": "Hammer",
  "candles_ago": 2,
  "recency_multiplier": 0.8,
  "location": "recent",
  "confidence": 0.68,
  "metadata": {
    "recency_info": {
      "candles_ago": 2,
      "multiplier": 0.8,
      "lookback_window": 5,
      "base_confidence": 0.85,
      "adjusted_confidence": 0.68
    }
  }
}
```

---

## 🎯 مزایا

1. **گرفتن الگوهای اخیر:**
   - قبلاً: فقط کندل آخر
   - حالا: 5 کندل آخر

2. **امتیازدهی منصفانه:**
   - الگوهای تازه‌تر → امتیاز بیشتر
   - الگوهای قدیمی‌تر → امتیاز کمتر

3. **قابل تنظیم:**
   - هر الگو multipliers خودش را دارد
   - با backtesting بهینه می‌کنیم

4. **شفافیت:**
   - می‌دانیم چه الگویی در چه زمانی پیدا شده
   - تحلیل معاملات راحت‌تر

---

## 🔄 سازگاری با کد قبلی

✅ **Backward Compatible:**
- اگر config تنظیم نشود، از مقادیر پیش‌فرض استفاده می‌شود
- الگوهای قدیمی بدون تغییر کار می‌کنند (با recency_multiplier = 1.0)
- تمام الگوهای موجود پشتیبانی می‌شوند

---

## 📝 TODO: مراحل بعدی

### مرحله بعدی (اختیاری):
1. ✅ پیاده‌سازی برای سایر الگوها (Shooting Star, Engulfing, etc.)
2. ⏳ Backtesting برای تنظیم ضرایب بهینه
3. ⏳ اضافه کردن logging کامل
4. ⏳ Dashboard برای نمایش candles_ago

### پیشنهادات:
- تست با داده‌های واقعی و تنظیم multipliers
- مقایسه نتایج قبل و بعد از پیاده‌سازی
- بهینه‌سازی lookback_window برای هر الگو

---

## 👥 نویسنده

- Claude AI
- تاریخ: 2025-10-25

## 📄 مراجع

- Design Document: `talib-test/RECENCY_SCORING_DESIGN.md`
- Demo: `talib-test/demo_recency_scoring.py`
- Config Example: `talib-test/pattern_recency_config_example.json`

---

**وضعیت:** ✅ آماده برای استفاده در محیط تولید
