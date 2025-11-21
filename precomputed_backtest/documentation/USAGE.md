# راهنمای استفاده (Usage Guide)

## پیش‌نیازها

```bash
pip install pandas numpy pyarrow pyyaml
```

---

## مرحله 1: پیش‌محاسبه اندیکاتورها

```bash
cd /home/user/Back_to_OLD_method/precomputed_backtest
python precompute_indicators.py
```

**خروجی مورد انتظار:**
```
Loading local config: .../configs/config.yaml
Loading local backtest config: .../configs/config_backtest_v2.yaml
Processing symbol: BTC-USDT
Processing 5m timeframe...
  Loaded 94816 candles
  Calculated indicators
  Saved to computed_data/indicators/BTC-USDT/5m_indicators.parquet
Processing 15m timeframe...
...
```

---

## مرحله 2: پیش‌محاسبه الگوها

```bash
python precompute_patterns.py
```

**خروجی مورد انتظار:**
```
Processing patterns for BTC-USDT
Processing 5m patterns...
  Loaded indicators with 94816 rows
  Detected patterns: doji=X, hammer=Y, ...
  Saved to computed_data/patterns/BTC-USDT/5m_patterns.parquet
...
```

---

## مرحله 3: اجرای بکتست سریع

```bash
python fast_backtest.py
```

**خروجی مورد انتظار:**
```
Loading precomputed data...
  Loaded 5m: 94816 rows
  Loaded 15m: 33529 rows
  ...
Running fast backtest...
  Processing candle 1000/94816
  Processing candle 2000/94816
  ...
Backtest completed in X.XX seconds
Speed: ~4500 candles/second
```

---

## تنظیمات

### تغییر نماد معاملاتی
فایل `configs/config_backtest_v2.yaml`:
```yaml
backtest:
  symbols:
    - "BTC-USDT"    # تغییر به نماد دلخواه
```

### تغییر آستانه سیگنال
فایل `fast_backtest.py`:
```python
# خط ~180
if signal_strength > 60:  # کاهش برای بیشتر شدن سیگنال‌ها
```

### اضافه کردن اندیکاتور جدید
فایل `precompute_indicators.py`:
```python
class SimpleIndicatorCalculator:
    def calculate_all(self, df):
        # اضافه کردن اندیکاتور جدید
        df['my_indicator'] = ...
        return df
```

---

## عیب‌یابی

### خطا: فایل داده پیدا نشد
```
FileNotFoundError: historical/BTC-USDT/5m.csv not found
```
**راه‌حل**: مسیر داده‌ها در `configs/config_backtest_v2.yaml` را بررسی کنید.

### خطا: هیچ معامله‌ای انجام نشد
```
Total trades: 0
```
**راه‌حل**: آستانه سیگنال در `fast_backtest.py` را کاهش دهید.

### خطا: حافظه کافی نیست
```
MemoryError
```
**راه‌حل**: داده‌ها را به صورت chunk لود کنید یا تعداد کندل‌ها را محدود کنید.

---

## تست عملکرد

### مقایسه سرعت
```python
import time

# روش قدیم
start = time.time()
# run_backtest.py اصلی
old_time = time.time() - start

# روش جدید
start = time.time()
# fast_backtest.py
new_time = time.time() - start

print(f"Speedup: {old_time / new_time:.1f}x")
```

### بررسی صحت داده‌ها
```python
import pandas as pd

# لود داده‌های پیش‌محاسبه شده
df = pd.read_parquet('computed_data/indicators/BTC-USDT/5m_indicators.parquet')

# بررسی NaN
print(df.isnull().sum())

# بررسی محدوده RSI (باید 0-100 باشد)
print(f"RSI range: {df['rsi'].min():.2f} - {df['rsi'].max():.2f}")
```

---

## اجرای کامل (همه مراحل)

```bash
# یک‌جا همه کارها
python precompute_all.py
python fast_backtest.py
```

یا به صورت جداگانه:
```bash
python precompute_indicators.py && python precompute_patterns.py && python fast_backtest.py
```
