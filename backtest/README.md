# Backtest System V2.0

سیستم بک‌تست با معماری جدید SignalOrchestrator و **Config Merge System**

## 🆕 ویژگی‌های نسخه 2.0

- ✅ استفاده از SignalOrchestrator به جای SignalGenerator
- ✅ معماری ماژولار signal_generation (11 Analyzers)
- ✅ **Config Merge System** - ترکیب config اصلی با override های backtest
- ✅ Context-Based Architecture
- ✅ IndicatorCalculator مرکزی
- ✅ Single Source of Truth برای patterns و analyzers

---

## 📁 ساختار فایل‌ها

```
backtest/
├── README.md                          # این فایل
├── run_backtest_v2.py                 # اسکریپت اجرای backtest
├── backtest_engine_v2.py              # موتور اصلی backtest
├── config_backtest_minimal.yaml       # ✨ تنظیمات backtest (فقط override)
├── config_backtest_v2.yaml.backup     # کانفیگ قدیمی (backup)
├── historical_data_provider_v2.py     # مدیریت داده‌های تاریخی
├── backtest_trade_manager.py          # مدیریت معاملات backtest
├── time_simulator.py                  # شبیه‌سازی زمان
└── csv_data_loader.py                 # بارگذاری داده‌های CSV
```

---

## 🎯 Config Merge System

### چگونه کار می‌کند؟

```
┌─────────────────────┐
│   config.yaml       │ ← تنظیمات اصلی (patterns, analyzers, etc)
│   (1132 lines)      │
└──────────┬──────────┘
           │
           │  MERGE
           │
           ↓
┌─────────────────────┐
│ config_backtest_    │ ← فقط override/backtest-specific
│ minimal.yaml        │    (132 lines)
│                     │
└──────────┬──────────┘
           │
           │  deep_merge_configs()
           │
           ↓
┌─────────────────────┐
│  Merged Config      │ ← کانفیگ نهایی
│  (Best of both)     │
└─────────────────────┘
```

### مزایا:

1. ✅ **Single Source of Truth** - patterns و analyzers فقط در config.yaml
2. ✅ **DRY Principle** - بدون تکرار تنظیمات
3. ✅ **Easy Maintenance** - تغییر یکبار، تاثیر همه‌جا
4. ✅ **Consistency** - backtest با همان تنظیمات live trading
5. ✅ **Smaller Config** - فقط 132 خط به جای 664 خط

---

## 🚀 نحوه اجرا

### روش 1: اجرای ساده

```bash
cd /home/user/New
python backtest/run_backtest_v2.py
```

### روش 2: اجرا با Python

```python
import asyncio
from backtest.backtest_engine_v2 import run_backtest_v2

# اجرا با تنظیمات پیش‌فرض
engine, results_dir = asyncio.run(
    run_backtest_v2(
        config_path='backtest/config_backtest_minimal.yaml',
        main_config_path='config.yaml'
    )
)

print(f"Results saved to: {results_dir}")
```

---

## ⚙️ تنظیمات

### تنظیمات اصلی (config.yaml)

این تنظیمات به صورت خودکار از `config.yaml` لود می‌شوند:

```yaml
# الگوها با recency scoring
patterns:
  hammer:
    lookback_window: 5
    recency_multipliers: [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
  doji:
    lookback_window: 5
    recency_multipliers: [1.0, 0.7, 0.5, 0.3, 0.15, 0.05]
  # ... 26 الگو

# امتیازدهی الگوها بر اساس تایم‌فریم
pattern_scores:
  hammer:
    '5m': 0.8
    '15m': 1.0
    '1h': 1.2
    '4h': 1.5
  # ... 31 الگو

# تنظیمات Analyzers
analyzers:
  trend:
    ema_periods: [20, 50, 100, 200]
  momentum:
    rsi_period: 14
  # ... و بقیه
```

### تنظیمات Backtest (config_backtest_minimal.yaml)

فقط تنظیمات خاص backtest را تغییر دهید:

```yaml
backtest:
  # داده‌های تاریخی
  data_path: './historical/'
  data_source: 'csv'

  # بازه زمانی
  start_date: 'auto'  # یا '2024-01-01 00:00:00'
  end_date: 'auto'    # یا '2024-12-31 23:59:59'

  # موجودی اولیه
  initial_balance: 10000.0

  # نمادها
  symbols:
    - 'BTC-USDT'
    # - 'ETH-USDT'  # اضافه کردن نمادهای بیشتر

  # تنظیمات شبیه‌سازی
  step_timeframe: '5m'
  process_interval: 180  # هر 3 دقیقه

  # کمیسیون و اسلیپیج
  commission_rate: 0.0006  # 0.06%
  slippage: 0.0005         # 0.05%

# Override تنظیمات
signal_generation:
  minimum_signal_score: 50  # حداقل امتیاز سیگنال
```

---

## 📊 ساختار داده‌های CSV

داده‌های تاریخی باید در این ساختار باشند:

```
historical/
└── BTC-USDT/
    ├── 5min.csv
    ├── 15min.csv
    ├── 1hour.csv
    └── 4hour.csv
```

### فرمت CSV:

```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,42000.0,42100.0,41900.0,42050.0,1234.56
2024-01-01 00:05:00,42050.0,42150.0,42000.0,42100.0,1456.78
...
```

**نکات مهم:**
- ✅ Timestamp به فرمت `YYYY-MM-DD HH:MM:SS`
- ✅ ستون‌ها با `,` جدا شوند
- ✅ بدون ردیف header خالی
- ✅ داده‌ها به ترتیب زمانی (از قدیم به جدید)

---

## 📈 خروجی‌ها

### گزارش در کنسول

```
======================================================================
                    BACKTEST RESULTS V2
======================================================================

📅 Period: 2024-01-01 to 2024-12-31
⏱️  Duration: 365 days, 0:00:00
🚀 Execution Time: 0:15:23

💰 FINANCIAL SUMMARY
Initial Balance: 10,000.00 USDT
Final Equity: 12,345.67 USDT
Total Return: +23.46%
Max Drawdown: -8.32%

📊 TRADE STATISTICS
Total Trades: 142
Winning Trades: 89 (62.7%)
Losing Trades: 53
Win/Loss Ratio: 1.87

💵 PROFIT/LOSS
Total Profit: 4,567.89 USDT
Total Loss: -2,222.22 USDT
Average Win: 51.32 USDT
Average Loss: -41.93 USDT
```

### فایل‌های خروجی

```
backtest_results/20241201_143022/
├── summary.txt              # خلاصه نتایج
├── trades.csv               # لیست تمام معاملات
├── equity_curve.png         # نمودار equity curve
├── statistics.json          # آمار کامل (JSON)
└── config_used.yaml         # کانفیگ استفاده شده
```

---

## 🔧 تنظیمات پیشرفته

### تغییر تایم‌فریم‌های تحلیل

```yaml
# در config.yaml
data_fetching:
  timeframes: ['5m', '15m', '1h', '4h']  # 4 تایم‌فریم اصلی
```

### تغییر حداقل امتیاز سیگنال

```yaml
# در config_backtest_minimal.yaml
signal_generation:
  minimum_signal_score: 60  # فقط سیگنال‌های قوی
```

### غیرفعال کردن Analyzers خاص

```yaml
# در config_backtest_minimal.yaml
orchestrator:
  enabled_analyzers:
    - trend
    - momentum
    - volume
    - patterns
    # - harmonic  # غیرفعال
    # - cyclical  # غیرفعال
```

---

## 🐛 عیب‌یابی

### مشکل: FileNotFoundError برای CSV

```
❌ Error: FileNotFoundError: ./historical/BTC-USDT/5min.csv
```

**راه‌حل:** بررسی کنید:
1. پوشه `historical/` در مسیر صحیح است؟
2. نام پوشه نماد درست است؟ (`BTC-USDT` نه `BTCUSDT`)
3. نام فایل‌ها درست است؟ (`5min.csv` نه `5m.csv`)

### مشکل: No signals generated

```
⚠️ No signals generated during backtest
```

**راه‌حل:**
1. `minimum_signal_score` را کاهش دهید (مثلاً 40)
2. بازه زمانی را بزرگ‌تر کنید
3. لاگ‌ها را بررسی کنید: `logs/backtest_btc.log`

### مشکل: patterns not found warning

```
⚠️ patterns: NOT FOUND (recency scoring will use defaults)
```

**راه‌حل:** این اشکال نیست! patterns از `config.yaml` لود می‌شود. اگر warning می‌بینید:
1. بررسی کنید `config.yaml` در مسیر صحیح باشد
2. بررسی کنید بخش `patterns:` در `config.yaml` موجود باشد

---

## 📝 نکات مهم

### ✅ استفاده صحیح از Config Merge

```python
# ✅ درست
engine, results = asyncio.run(
    run_backtest_v2(
        config_path='backtest/config_backtest_minimal.yaml',
        main_config_path='config.yaml'  # config اصلی
    )
)

# ❌ نادرست (از config قدیمی استفاده نکنید)
engine, results = asyncio.run(
    run_backtest_v2('backtest/config_backtest_v2.yaml')  # deprecated
)
```

### ✅ تغییر تنظیمات Patterns

**فقط در `config.yaml`:**

```yaml
# config.yaml - برای همه (live + backtest)
patterns:
  hammer:
    lookback_window: 7  # تغییر از 5 به 7
    recency_multipliers: [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7]
```

**نه در `config_backtest_minimal.yaml`!**

### ✅ تغییر تنظیمات خاص Backtest

**فقط در `config_backtest_minimal.yaml`:**

```yaml
# config_backtest_minimal.yaml - فقط برای backtest
backtest:
  initial_balance: 20000.0  # افزایش موجودی
  commission_rate: 0.0004   # کاهش کمیسیون
```

---

## 🎓 مثال کامل

```python
import asyncio
from backtest.backtest_engine_v2 import run_backtest_v2

async def run_my_backtest():
    """اجرای backtest سفارشی"""

    # اجرای backtest
    engine, results_dir = await run_backtest_v2(
        config_path='backtest/config_backtest_minimal.yaml',
        main_config_path='config.yaml'
    )

    # دسترسی به نتایج
    stats = engine.results['statistics']

    print(f"Total Return: {stats['total_return']:.2f}%")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
    print(f"Profit Factor: {stats['profit_factor']:.2f}")

    # ذخیره گزارش سفارشی
    with open(f"{results_dir}/my_report.txt", 'w') as f:
        f.write(f"Custom Report\n")
        f.write(f"=============\n")
        f.write(f"Final Equity: ${stats['current_equity']:,.2f}\n")

    return engine, results_dir

if __name__ == "__main__":
    engine, results = asyncio.run(run_my_backtest())
```

---

## 📚 منابع بیشتر

- 📖 [مستندات SignalOrchestrator](../docs/SIGNAL_GENERATION_GUIDE.md)
- 📖 [مقایسه سیستم‌های قدیم و جدید](../docs/SCORING_SYSTEM_COMPARISON.md)
- 📖 [راهنمای Pattern Scoring](../docs/NEW_SYSTEM_SIGNAL_FLOW.md)

---

## 🆘 پشتیبانی

اگر مشکلی دارید:

1. لاگ‌ها را بررسی کنید: `logs/backtest_btc.log`
2. کانفیگ merge را بررسی کنید (در خروجی console)
3. تست کنید که `config.yaml` صحیح لود می‌شود

---

## 📝 Changelog

### v2.0 (2024-12-15)
- ✨ اضافه شدن Config Merge System
- ✨ ایجاد config_backtest_minimal.yaml
- ✨ Single Source of Truth برای patterns
- 🐛 رفع مشکل patterns و analyzers در backtest
- 📝 اضافه شدن README کامل

### v1.0 (2024-10-23)
- ✨ پیاده‌سازی اولیه با SignalOrchestrator
- ✨ پشتیبانی از CSV data
- ✨ گزارش‌دهی کامل

---

**نسخه:** 2.0
**تاریخ:** 2024-12-15
**وضعیت:** ✅ Stable
