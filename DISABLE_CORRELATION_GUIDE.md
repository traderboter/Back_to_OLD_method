# 🔧 راهنمای غیرفعال‌سازی Correlation Systems
## چگونه Symbol و BTC Correlation را موقتاً غیرفعال کنیم؟

---

## 📋 خلاصه سریع

در فایل **`config.yaml`** دو نوع Correlation وجود دارد که می‌توانید غیرفعال کنید:

| نوع Correlation | محل در Config | پارامتر کلیدی | پیش‌فرض |
|----------------|---------------|----------------|---------|
| **Symbol Correlation** | `signal_generation.filters` | `check_correlation` | `true` |
| **BTC Correlation** | `risk_management.btc_correlation` | `consider_btc_trend` | `true` |

---

## 1️⃣ Symbol Correlation (همبستگی بین symbols)

### 📍 محل در Config

**فایل:** `config.yaml`
**خط:** ~428

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: true  # ⬅️ این را تغییر دهید
      max_correlation: 0.7
      max_correlated_trades: 2
```

---

### ✅ غیرفعال کردن Symbol Correlation

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: false  # ❌ غیرفعال
      max_correlation: 0.7  # نادیده گرفته می‌شود
      max_correlated_trades: 2  # نادیده گرفته می‌شود
```

**تاثیر:**
- ✅ سیستم دیگر همبستگی بین symbols را بررسی نمی‌کند
- ✅ می‌توانید هر تعداد position در symbols همبسته داشته باشید
- ⚠️ **خطر:** احتمال تمرکز ریسک در یک گروه همبسته

---

### 🎛️ تنظیم جزئی‌تر (بدون غیرفعال کردن کامل)

اگر نمی‌خواهید کاملاً غیرفعال کنید، می‌توانید threshold را تنظیم کنید:

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: true  # ✅ فعال بماند
      max_correlation: 0.9  # 0.7 → 0.9 (سخت‌گیری کمتر)
      max_correlated_trades: 5  # 2 → 5 (تعداد بیشتر مجاز)
```

**مثال:**
```
قبل (max_correlation: 0.7):
- BTC و ETH همبستگی 0.75 → همبسته محسوب می‌شوند

بعد (max_correlation: 0.9):
- BTC و ETH همبستگی 0.75 → همبسته محسوب نمی‌شوند ✅
```

---

## 2️⃣ BTC Correlation (همبستگی با بیت‌کوین)

### 📍 محل در Config

**فایل:** `config.yaml`
**خط:** ~1121

```yaml
risk_management:
  btc_correlation:
    consider_btc_trend: true  # ⬅️ این را تغییر دهید
    btc_symbol: BTCUSDT

    correlation_timeframes:
    - 15m
    - 1h
    - 4h
    - 1d

    correlation_timeframe_weights:
    - 0.1
    - 0.2
    - 0.3
    - 0.4

    primary_correlation_timeframe: 1h
    correlation_period: 100

    inverse_correlation_threshold: -0.2
    zero_correlation_threshold: 0.2
    strong_correlation_threshold: 0.4

    analyze_lag_correlation: true
    max_lag_periods: 5

    # BTC Trend settings
    btc_trend_timeframe: 4h
    btc_trend_period: 50
    btc_trend_ema_fast: 20
    btc_trend_ema_slow: 50
    btc_trend_strength_threshold: 0.01

    # Volume analysis
    analyze_btc_volume: true
    btc_volume_timeframe: 1d
    btc_volume_period: 20
    btc_high_volume_threshold: 1.5

    # Cache settings
    correlation_cache_expiry_seconds: 3600
    btc_trend_cache_expiry: 1800
    btc_volume_cache_expiry: 1800
```

---

### ✅ غیرفعال کردن BTC Correlation

**روش 1: غیرفعال کردن کامل**

```yaml
risk_management:
  btc_correlation:
    consider_btc_trend: false  # ❌ غیرفعال کامل
    # بقیه تنظیمات نادیده گرفته می‌شوند
```

**تاثیر:**
- ✅ سیستم روند بیت‌کوین را نادیده می‌گیرد
- ✅ سیگنال‌ها بدون توجه به BTC تولید می‌شوند
- ⚠️ **خطر:** ممکن است در برابر BTC معامله کنید

---

**روش 2: تنظیم threshold (سخت‌گیری کمتر)**

```yaml
risk_management:
  btc_correlation:
    consider_btc_trend: true  # ✅ فعال بماند
    strong_correlation_threshold: 0.8  # 0.4 → 0.8 (سخت‌گیری کمتر)
```

**مثال:**
```
قبل (strong_correlation_threshold: 0.4):
- ETH با BTC همبستگی 0.6 → سیگنال SHORT رد می‌شود ❌

بعد (strong_correlation_threshold: 0.8):
- ETH با BTC همبستگی 0.6 → سیگنال SHORT قبول می‌شود ✅
```

---

## 3️⃣ غیرفعال کردن همزمان هر دو

اگر می‌خواهید هر دو را موقتاً غیرفعال کنید:

```yaml
# ========== Symbol Correlation ==========
signal_generation:
  validation:
    filters:
      check_correlation: false  # ❌ غیرفعال

# ========== BTC Correlation ==========
risk_management:
  btc_correlation:
    consider_btc_trend: false  # ❌ غیرفعال
```

**تاثیر کلی:**
- ✅ هیچ بررسی همبستگی انجام نمی‌شود
- ✅ سیگنال‌ها فقط بر اساس تحلیل تکنیکال تولید می‌شوند
- ⚠️ **خطر:** تمرکز ریسک بالا + معامله برخلاف BTC

---

## 4️⃣ تنظیمات پیشنهادی برای سناریوهای مختلف

### 🎯 سناریو 1: Backtest (همه correlation ها غیرفعال)

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: false  # غیرفعال

risk_management:
  btc_correlation:
    consider_btc_trend: false  # غیرفعال
```

**چرا؟** در backtest معمولاً single symbol تست می‌شود.

---

### 🎯 سناریو 2: Paper Trading (فعال با تنظیمات ملایم)

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: true  # ✅ فعال
      max_correlation: 0.8  # سخت‌گیری کمتر
      max_correlated_trades: 4  # تعداد بیشتر

risk_management:
  btc_correlation:
    consider_btc_trend: true  # ✅ فعال
    strong_correlation_threshold: 0.7  # سخت‌گیری کمتر
```

**چرا؟** یادگیری بدون ریسک واقعی.

---

### 🎯 سناریو 3: Live Trading (فعال با تنظیمات محافظه‌کارانه)

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: true  # ✅ فعال
      max_correlation: 0.7  # پیش‌فرض
      max_correlated_trades: 2  # پیش‌فرض

risk_management:
  btc_correlation:
    consider_btc_trend: true  # ✅ فعال
    strong_correlation_threshold: 0.4  # پیش‌فرض
```

**چرا؟** محافظت از سرمایه واقعی.

---

### 🎯 سناریو 4: BTC Only Trading (فقط Symbol Correlation)

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: true  # ✅ فعال (برای diversification)

risk_management:
  btc_correlation:
    consider_btc_trend: false  # ❌ غیرفعال (BTC خودش است!)
```

**چرا؟** BTC با خودش همبستگی ندارد!

---

### 🎯 سناریو 5: Alt Season (BTC Correlation ملایم‌تر)

```yaml
signal_generation:
  validation:
    filters:
      check_correlation: true  # ✅ فعال

risk_management:
  btc_correlation:
    consider_btc_trend: true  # ✅ فعال
    strong_correlation_threshold: 0.8  # ملایم‌تر
    analyze_lag_correlation: true  # Altها با تاخیر حرکت می‌کنند
    max_lag_periods: 10  # 5 → 10 (تاخیر بیشتر)
```

**چرا؟** در Alt Season، altها ممکن است با تاخیر از BTC حرکت کنند.

---

## 5️⃣ چک کردن وضعیت فعلی

برای دیدن اینکه Correlation ها فعال هستند یا خیر، در لاگ‌ها دنبال این پیام‌ها باشید:

### Symbol Correlation:

```log
# اگر فعال باشد:
INFO - CorrelationManager initialized. Enabled: True, Correlation threshold: 0.7

# اگر غیرفعال باشد:
INFO - CorrelationManager initialized. Enabled: False
```

### BTC Correlation:

```log
# اگر فعال باشد:
INFO - BTC correlation check enabled with threshold: 0.4

# اگر غیرفعال باشد:
INFO - BTC correlation check disabled
```

---

## 6️⃣ ریستارت سیستم

**⚠️ مهم:** بعد از تغییر config، حتماً سیستم را ریستارت کنید:

```bash
# متوقف کردن
Ctrl+C

# اجرای مجدد
python main.py
```

---

## 7️⃣ مثال‌های عملی

### مثال 1: غیرفعال کردن موقت Symbol Correlation

**قبل:**
```yaml
check_correlation: true
```

**بعد:**
```yaml
check_correlation: false
```

**نتیجه:**
```
قبل:
- BTC position × 3 active
- ETH signal → امتیاز کاهش 50% (correlation penalty)

بعد:
- BTC position × 3 active
- ETH signal → امتیاز کاهش نمی‌شود ✅
```

---

### مثال 2: غیرفعال کردن موقت BTC Correlation

**قبل:**
```yaml
consider_btc_trend: true
strong_correlation_threshold: 0.4
```

**بعد:**
```yaml
consider_btc_trend: false
```

**نتیجه:**
```
قبل:
- BTC روند صعودی
- ETH همبستگی 0.6 با BTC
- سیگنال SHORT ETH → رد می‌شود ❌

بعد:
- BTC روند صعودی
- ETH همبستگی 0.6 با BTC
- سیگنال SHORT ETH → قبول می‌شود ✅
```

---

## 8️⃣ هشدارها و توصیه‌ها

### ⚠️ هشدار 1: تمرکز ریسک

```
اگر Symbol Correlation را غیرفعال کنید:
→ ممکن است 10 position long در symbols همبسته داشته باشید
→ اگر بازار سقوط کند، همه ضرر می‌کنند
→ ریسک portfolio بسیار بالا می‌رود
```

**توصیه:** فقط برای backtest یا تست غیرفعال کنید.

---

### ⚠️ هشدار 2: معامله برخلاف BTC

```
اگر BTC Correlation را غیرفعال کنید:
→ ممکن است SHORT altcoin وقتی BTC صعودی است
→ احتمال ضرر بالاست (95% altها با BTC حرکت می‌کنند)
```

**توصیه:** فقط اگر استراتژی خاصی دارید (مثلاً inverse correlation).

---

### ✅ توصیه کلی

**برای Production:**
```yaml
# فعال نگه دارید، فقط threshold را تنظیم کنید
check_correlation: true
max_correlation: 0.7  # یا 0.8 برای ملایم‌تر

consider_btc_trend: true
strong_correlation_threshold: 0.4  # یا 0.6 برای ملایم‌تر
```

**برای Backtest:**
```yaml
# غیرفعال کنید
check_correlation: false
consider_btc_trend: false
```

---

## 9️⃣ خلاصه دستورات سریع

### غیرفعال کردن Symbol Correlation

```bash
# در config.yaml، خط ~428
sed -i 's/check_correlation: true/check_correlation: false/' config.yaml
```

### غیرفعال کردن BTC Correlation

```bash
# در config.yaml، خط ~1122
sed -i 's/consider_btc_trend: true/consider_btc_trend: false/' config.yaml
```

### فعال کردن مجدد

```bash
# Symbol Correlation
sed -i 's/check_correlation: false/check_correlation: true/' config.yaml

# BTC Correlation
sed -i 's/consider_btc_trend: false/consider_btc_trend: true/' config.yaml
```

---

## 🔟 جدول خلاصه

| Correlation | پارامتر | مقدار پیش‌فرض | غیرفعال | ملایم‌تر |
|------------|---------|--------------|---------|----------|
| **Symbol** | `check_correlation` | `true` | `false` | `true` |
| | `max_correlation` | `0.7` | - | `0.8-0.9` |
| | `max_correlated_trades` | `2` | - | `4-5` |
| **BTC** | `consider_btc_trend` | `true` | `false` | `true` |
| | `strong_correlation_threshold` | `0.4` | - | `0.6-0.8` |

---

## ✅ نتیجه‌گیری

**برای غیرفعال کردن موقت:**

1. باز کنید: `config.yaml`

2. **Symbol Correlation** (خط ~428):
   ```yaml
   check_correlation: false
   ```

3. **BTC Correlation** (خط ~1122):
   ```yaml
   consider_btc_trend: false
   ```

4. ذخیره و ریستارت کنید

**⚠️ توجه:** فقط برای تست! در production فعال نگه دارید.

---

**پایان راهنما** ✅
