# 📊 Check Backtest Method - راهنمای استفاده

## 🎯 هدف / Purpose

این اسکریپت برای **تشخیص روش امتیازدهی (Scoring Method)** استفاده شده در نتایج backtest طراحی شده است.

This script is designed to **detect the scoring method** used in backtest results.

---

## 📍 مسیر فایل / File Path

```
backtest/check_backtest_method.py
```

---

## 🔑 تفاوت اصلی بین روش‌های OLD و NEW

### روش قدیم (OLD Method)
- **Multi-Timeframe Aggregation**: سیگنال‌های همه تایم‌فریم‌ها را ترکیب (aggregate) می‌کند
- **13 ضریب اضافی**: شامل symbol performance، correlation safety، و 6 ضریب دیگر
- **امتیاز نامحدود**: max_final_score = 0 (بدون محدودیت)
- **آستانه بالا**: حداقل امتیاز 200، سیگنال قوی > 500

### روش جدید (NEW Method)
- **Best Signal Selection**: بهترین تایم‌فریم را انتخاب می‌کند (نه aggregate)
- **8 Analyzer ساده**: بدون ضرایب پیچیده
- **امتیاز محدود**: max_final_score = 300
- **آستانه پایین**: حداقل امتیاز 60، سیگنال قوی > 150

---

## 🚀 نحوه استفاده / Usage

### 1️⃣ بررسی یک backtest خاص
Check a specific backtest:

```bash
python backtest/check_backtest_method.py v2_20251120_002427
```

**خروجی نمونه / Sample Output:**
```
======================================================================
📊 BACKTEST METHOD DETECTION
======================================================================
📁 Folder: v2_20251120_002427
📄 Config: /home/user/New/backtest_results/v2_20251120_002427/config.json
======================================================================

🔑 KEY INDICATORS:
  scoring_method:              OLD
  use_multi_tf_aggregation:    True

⚙️  OLD SYSTEM FEATURES:
  symbol_performance_enabled:  True
  correlation_safety_enabled:  True
  use_rr_based_confluence:     True
  max_final_score:             0 (unlimited)

📊 VALIDATION THRESHOLDS:
  min_signal_score:            200
  strong_signal_threshold:     500

======================================================================
⚙️ METHOD DETECTED: OLD
📝 Description: Multi-TF Aggregation + 13 Multipliers
======================================================================
```

---

### 2️⃣ بررسی آخرین backtest
Check the latest backtest automatically:

```bash
python backtest/check_backtest_method.py
```

این دستور به صورت خودکار آخرین فولدر backtest (بر اساس timestamp) را پیدا کرده و بررسی می‌کند.

This command automatically finds and checks the latest backtest folder (based on timestamp).

---

### 3️⃣ لیست همه backtestها
List all backtests with their methods:

```bash
python backtest/check_backtest_method.py --list
# یا
python backtest/check_backtest_method.py -l
```

**خروجی نمونه / Sample Output:**
```
====================================================================================================
📊 ALL BACKTESTS SUMMARY
====================================================================================================
Folder Name                    Method     Multi-TF   Min Score    Date/Time
----------------------------------------------------------------------------------------------------
v2_20251119_183443             NEW        False      60           2025-11-19 18:34:43
v2_20251119_183619             OLD        True       200          2025-11-19 18:36:19
v2_20251119_191447             HYBRID     False      80           2025-11-19 19:14:47
v2_20251120_002407             NEW        False      60           2025-11-20 00:24:07
v2_20251120_002427             OLD        True       200          2025-11-20 00:24:27
====================================================================================================
```

---

### 4️⃣ نمایش راهنما
Show help:

```bash
python backtest/check_backtest_method.py --help
```

---

## 📊 پارامترهای تشخیص / Detection Parameters

اسکریپت پارامترهای زیر را از `config.json` استخراج و بررسی می‌کند:

The script extracts and analyzes the following parameters from `config.json`:

### 🔑 پارامترهای کلیدی / Key Parameters

| Parameter | OLD Method | NEW Method | توضیحات / Description |
|-----------|-----------|-----------|---------------------|
| `scoring_method` | `"old"` | `"new"` | روش امتیازدهی / Scoring method |
| `use_multi_tf_aggregation` | `true` | `false` | ترکیب چند تایم‌فریم / Multi-TF aggregation |
| `min_signal_score` | 200 | 60 | حداقل امتیاز سیگنال / Minimum signal score |
| `strong_signal_threshold` | 500 | 150 | آستانه سیگنال قوی / Strong signal threshold |
| `max_final_score` | 0 (نامحدود) | 300 | محدودیت امتیاز نهایی / Final score limit |

### ⚙️ ویژگی‌های سیستم قدیم / OLD System Features

| Feature | OLD | NEW | توضیحات / Description |
|---------|-----|-----|---------------------|
| `symbol_performance_enabled` | ✅ | ❌ | ضریب عملکرد نماد |
| `correlation_safety_enabled` | ✅ | ❌ | ضریب ایمنی همبستگی |
| `structure_score_enabled` | ✅ | ❌ | امتیاز ساختار |
| `harmonic_separate_multiplier` | ✅ | ❌ | ضریب جداگانه هارمونیک |
| `channel_separate_multiplier` | ✅ | ❌ | ضریب جداگانه کانال |
| `cyclical_separate_multiplier` | ✅ | ❌ | ضریب جداگانه چرخه‌ای |
| `use_rr_based_confluence` | ✅ | ❌ | همگرایی مبتنی بر RR |

---

## 📋 جدول مقایسه / Comparison Table

اسکریپت یک جدول مقایسه دقیق نمایش می‌دهد:

The script displays a detailed comparison table:

```
📋 COMPARISON WITH STANDARD METHODS:
Attribute                           OLD             NEW             Current
--------------------------------------------------------------------------------
scoring_method                      old             new             old
use_multi_tf_aggregation            True            False           True
min_signal_score                    200             60              200
strong_signal_threshold             500             150             500
max_final_score                     0 (unlimited)   300             0
OLD system features enabled         Yes             No              Yes
```

---

## 🔍 نحوه تشخیص / Detection Logic

اسکریپت با بررسی ترکیب پارامترها، روش را تشخیص می‌دهد:

The script detects the method by analyzing parameter combinations:

### ✅ OLD Method
```python
scoring_method == 'old' AND use_multi_tf_aggregation == True
```

### ✅ NEW Method
```python
scoring_method == 'new' AND use_multi_tf_aggregation == False
```

### 🔀 HYBRID Method
```python
scoring_method == 'hybrid'
```

### ❓ UNKNOWN
اگر ترکیب پارامترها با هیچ الگوی شناخته شده‌ای مطابقت نداشته باشد.

If parameter combination doesn't match any known pattern.

---

## 📂 ساختار فایل / File Structure

```
backtest_results/
├── v2_20251119_183443/
│   ├── config.json          ← فایل تنظیمات / Config file
│   ├── trades.csv
│   ├── equity_curve.csv
│   └── statistics.json
├── v2_20251119_183619/
│   └── config.json
└── ...
```

---

## 🛠️ ویژگی‌های اسکریپت / Script Features

### ✨ قابلیت‌ها / Capabilities

1. **تشخیص خودکار روش** / Automatic method detection
   - OLD (Multi-TF Aggregation)
   - NEW (Best Signal Selection)
   - HYBRID (Mixed approach)

2. **نمایش اطلاعات جامع** / Comprehensive information display
   - کلیه پارامترهای کلیدی
   - وضعیت ویژگی‌های OLD system
   - جدول مقایسه با استانداردها

3. **لیست کامل backtestها** / Complete backtest listing
   - مرتب‌سازی بر اساس تاریخ
   - نمایش روش استفاده شده
   - تبدیل timestamp به تاریخ خوانا

4. **انتخاب خودکار آخرین backtest** / Auto-select latest backtest
   - بدون نیاز به ورود نام فولدر
   - مرتب‌سازی بر اساس timestamp

---

## 📖 مثال‌های کاربردی / Use Cases

### مثال 1: مقایسه دو backtest
Compare two backtests:

```bash
# بررسی backtest اول
python backtest/check_backtest_method.py v2_20251120_002407

# بررسی backtest دوم
python backtest/check_backtest_method.py v2_20251120_002427
```

### مثال 2: پیدا کردن همه backtestهای OLD
Find all OLD method backtests:

```bash
python backtest/check_backtest_method.py --list | grep "OLD"
```

### مثال 3: بررسی آخرین نتیجه
Check latest result:

```bash
python backtest/check_backtest_method.py
```

---

## ⚠️ نکات مهم / Important Notes

### 🔴 خطاهای احتمالی / Possible Errors

1. **فولدر یافت نشد**
   ```
   ❌ فولدر backtest_results/v2_xxx یافت نشد!
   ```
   **حل**: نام فولدر را به درستی وارد کنید یا از `--list` استفاده کنید.

2. **config.json موجود نیست**
   ```
   ❌ فایل config.json یافت نشد!
   ```
   **حل**: اطمینان حاصل کنید که backtest کامل شده است.

3. **هیچ backtest یافت نشد**
   ```
   ❌ هیچ فولدر backtest در backtest_results یافت نشد!
   ```
   **حل**: ابتدا یک backtest اجرا کنید.

---

## 🔗 ارتباط با فایل‌های دیگر / Related Files

### فایل‌های مرتبط:

1. **backtest/run_backtest_v2.py**
   - اجرای backtest با روش انتخابی
   - `--method old` یا `--method new`

2. **backtest/config_scoring_old.yaml**
   - تنظیمات روش OLD

3. **backtest/config_scoring_new.yaml**
   - تنظیمات روش NEW

4. **backtest/backtest_engine_v2.py**
   - موتور اصلی اجرای backtest

---

## 💡 نکات پیشرفته / Advanced Tips

### 1. استفاده در اسکریپت‌های خودکار / Use in automation scripts

```bash
#!/bin/bash
# بررسی خودکار آخرین backtest
METHOD=$(python backtest/check_backtest_method.py | grep "METHOD DETECTED" | awk '{print $4}')

if [ "$METHOD" == "OLD" ]; then
    echo "روش قدیم استفاده شده است"
else
    echo "روش جدید استفاده شده است"
fi
```

### 2. استفاده از خروجی JSON (قابلیت آینده)

```python
# می‌توان برای خروجی JSON اضافه کرد:
result = check_backtest_method('v2_20251120_002427')
print(json.dumps(result, indent=2))
```

### 3. فیلتر کردن backtestها

```bash
# فقط backtestهای امروز
python backtest/check_backtest_method.py --list | grep "2025-11-20"

# فقط روش NEW
python backtest/check_backtest_method.py --list | grep "NEW"
```

---

## 🔄 به‌روزرسانی‌های آینده / Future Updates

### قابلیت‌های پیشنهادی:

- [ ] خروجی JSON برای یکپارچه‌سازی با ابزارهای دیگر
- [ ] مقایسه خودکار نتایج چند backtest
- [ ] گزارش آماری از تفاوت‌های عملکرد
- [ ] صادرات به CSV یا Excel
- [ ] نمودار مقایسه‌ای (Chart comparison)

---

## 📞 پشتیبانی / Support

در صورت بروز مشکل یا سوال:

1. بررسی کنید که مسیر فولدر صحیح است
2. از `--list` برای مشاهده فولدرهای موجود استفاده کنید
3. فایل `config.json` را به صورت دستی بررسی کنید

---

## 📝 تاریخچه تغییرات / Changelog

### Version 1.0.0 (2025-11-20)
- ✅ نسخه اولیه
- ✅ تشخیص روش‌های OLD، NEW، HYBRID
- ✅ نمایش جدول مقایسه
- ✅ قابلیت لیست همه backtestها
- ✅ انتخاب خودکار آخرین backtest

---

## 🏷️ کلمات کلیدی / Keywords

`backtest`, `scoring method`, `OLD vs NEW`, `multi-timeframe`, `signal analysis`, `config detection`, `trading bot`, `python script`, `automation`

---

**نوشته شده در:** 2025-11-20
**نسخه:** 1.0.0
**زبان:** Python 3.x
**مخزن:** traderboter/New
