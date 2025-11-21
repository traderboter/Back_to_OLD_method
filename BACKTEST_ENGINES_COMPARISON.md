# 🔍 مقایسه دو Backtest Engine

## ⚠️ نکته مهم: این دو فایل جایگزین هم نیستند!

```
run_backtest.py (103 lines)
    ↓
    calls
    ↓
backtest/backtest_engine_v2.py (950 lines)
    ↓
    runs actual backtest
```

---

## 📊 جدول مقایسه سریع

| Feature | `backtest_engine_v2.py` | `run_backtest.py` |
|---------|------------------------|-------------------|
| **نقش** | 🏭 **موتور اصلی** | 🚪 **Entry Point** |
| **خطوط کد** | 950 lines | 103 lines |
| **کلاس اصلی** | `BacktestEngineV2` | هیچ کلاسی ندارد |
| **منطق Backtest** | ✅ کامل | ❌ فقط wrapper |
| **Multi-TF Analysis** | ✅ دارد | ❌ ندارد (استفاده از engine) |
| **Trade Management** | ✅ دارد | ❌ ندارد (استفاده از engine) |
| **Config Merging** | ✅ دارد (3-way merge) | ❌ ندارد (استفاده از engine) |
| **Results Saving** | ✅ دارد (JSON/CSV) | ❌ فقط نمایش |
| **استقلال** | ✅ کامل | ❌ وابسته به engine |
| **استفاده مستقیم** | ✅ قابل import و استفاده | ✅ قابل اجرا با `python` |

---

## 1️⃣ backtest/backtest_engine_v2.py (موتور اصلی)

### 📁 ساختار:

```python
# 950 خطوط کد کامل

class BacktestEngineV2:
    """موتور اصلی Backtest با SignalOrchestrator"""

    def __init__(self, config):
        # مقداردهی اولیه
        # HistoricalDataProvider
        # TimeSimulator
        # TradeManager
        # SignalOrchestrator
        # IndicatorCalculator

    async def initialize(self):
        # راه‌اندازی تمام کامپوننت‌ها

    async def run(self):
        # حلقه اصلی backtest
        # 1. Process symbols
        # 2. Generate signals
        # 3. Open/close trades
        # 4. Update equity

    async def _process_symbol(self, symbol, current_time):
        # Multi-TF Analysis
        # Fetch 4 timeframes
        # Call orchestrator.analyze_symbol()
        # Open trade if signal valid

    async def save_results(self, output_dir):
        # ذخیره نتایج
        # - statistics.json
        # - trades.csv
        # - equity_curve.csv
        # - config.json

# تابع کمکی
def deep_merge_configs(base, override):
    """3-way config merge"""
    # main config + scoring config + backtest config

async def run_backtest_v2(config_path, main_config_path, scoring_method):
    """اجرای backtest با merge configs"""
    # 1. Load main config (config.yaml)
    # 2. Load scoring config (config_scoring_{method}.yaml)
    # 3. Load backtest config (config_backtest_v2.yaml)
    # 4. Merge all three
    # 5. Create engine
    # 6. Run
    # 7. Save results
```

### ✅ مزایا:

1. **کامل و مستقل** - همه منطق backtest در یک جا
2. **Multi-TF Analysis** - پشتیبانی کامل از 4 تایم‌فریم
3. **Config Merging** - 3-way merge (main + scoring + backtest)
4. **SignalOrchestrator Integration** - استفاده از NEW SYSTEM
5. **Detailed Results** - ذخیره کامل نتایج (JSON + CSV)
6. **Trade Metadata** - ذخیره metadata کامل (sl_method, confidence, etc.)
7. **Progress Bar** - نمایش پیشرفت با tqdm
8. **Auto Date Detection** - تشخیص خودکار start/end date
9. **Position Sizing** - محاسبه دقیق حجم پوزیشن
10. **Equity Curve** - ذخیره نمودار سرمایه

### ⚠️ معایب:

1. **پیچیدگی** - 950 خطوط کد (اما سازماندهی خوب)
2. **Dependencies** - نیاز به کامپوننت‌های زیاد
3. **Learning Curve** - نیاز به درک ساختار کامل

---

## 2️⃣ run_backtest.py (Entry Point)

### 📁 ساختار:

```python
# 103 خطوط - فقط wrapper ساده

async def run_simple_backtest():
    """اجرای یک backtest ساده برای تست NEW SYSTEM"""

    # فقط صدا زدن run_backtest_v2()
    engine = await run_backtest_v2(
        scoring_method='new'
    )

    # نمایش نتایج
    print(f"Total trades: {engine.results['statistics']['total_trades']}")
    print(f"Win rate: {engine.results['statistics']['win_rate']:.1f}%")

    # نمایش NEW SYSTEM metadata
    if engine.results['trades']:
        sample_trade = engine.results['trades'][0]
        print(f"SL Method: {sample_trade.get('sl_method')}")
        print(f"Confidence: {sample_trade.get('confidence_level')}")

    return engine

async def run_quick_test():
    """تست سریع با داده‌های کم"""
    # TODO: پیاده‌سازی نشده
    logger.info("Quick test mode not yet implemented")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == 'quick':
        asyncio.run(run_quick_test())
    else:
        asyncio.run(run_simple_backtest())

if __name__ == '__main__':
    main()
```

### ✅ مزایا:

1. **ساده** - فقط 103 خطوط
2. **راحت** - یک فایل برای اجرا (`python run_backtest.py`)
3. **واضح** - برای مبتدی‌ها قابل فهم
4. **Quick Mode** - امکان اضافه کردن تست سریع

### ⚠️ معایب:

1. **ناقص** - خودش هیچ منطقی ندارد
2. **وابسته** - کاملاً وابسته به `backtest_engine_v2.py`
3. **محدود** - فقط نمایش ساده نتایج
4. **بدون ذخیره** - نتایج را ذخیره نمی‌کند
5. **Quick Test** - پیاده‌سازی نشده

---

## 🎯 کدام بهتر است؟

### ❌ سوال اشتباه!

این سوال درست نیست چون:
- `run_backtest.py` **از** `backtest_engine_v2.py` استفاده می‌کند
- یکی موتور است، یکی interface

### ✅ سوال درست:

**"چطور باید backtest اجرا کنم؟"**

---

## 🚀 سه روش اجرای Backtest

### روش 1: استفاده از `run_backtest.py` (ساده‌ترین)

```bash
# اجرای مستقیم
python run_backtest.py

# یا با حالت quick (هنوز پیاده‌سازی نشده)
python run_backtest.py quick
```

**مناسب برای:**
- ✅ مبتدی‌ها
- ✅ تست سریع
- ✅ نمایش نتایج در ترمینال

**محدودیت:**
- ❌ کنترل کم بر config
- ❌ نتایج ذخیره نمی‌شود (فقط engine.results['trades'] در حافظه)

---

### روش 2: استفاده مستقیم از `run_backtest_v2()` (توصیه می‌شود)

```python
import asyncio
from backtest.backtest_engine_v2 import run_backtest_v2

async def my_backtest():
    engine, results_dir = await run_backtest_v2(
        config_path='backtest/config_backtest_v2.yaml',
        main_config_path='config.yaml',
        scoring_method='new'  # یا 'old' یا 'hybrid'
    )

    # نتایج خودکار ذخیره می‌شود در results_dir
    print(f"Results saved to: {results_dir}")

    return engine

asyncio.run(my_backtest())
```

**مناسب برای:**
- ✅ کنترل کامل
- ✅ انتخاب scoring method
- ✅ ذخیره خودکار نتایج
- ✅ استفاده در Jupyter Notebook

---

### روش 3: استفاده از کلاس `BacktestEngineV2` (پیشرفته)

```python
import asyncio
import yaml
from backtest.backtest_engine_v2 import BacktestEngineV2

async def advanced_backtest():
    # بارگذاری config دستی
    with open('config.yaml') as f:
        config = yaml.safe_load(f)

    # تغییر تنظیمات
    config['backtest']['symbols'] = ['BTC/USDT', 'ETH/USDT']
    config['backtest']['start_date'] = '2023-01-01 00:00:00'
    config['backtest']['end_date'] = '2023-12-31 23:59:59'

    # ایجاد engine
    engine = BacktestEngineV2(config)

    # راه‌اندازی
    await engine.initialize()

    # اجرا
    await engine.run()

    # ذخیره نتایج
    results_dir = await engine.save_results()

    # تحلیل سفارشی
    trades = engine.results['trades']
    print(f"Total trades: {len(trades)}")

    return engine

asyncio.run(advanced_backtest())
```

**مناسب برای:**
- ✅ کنترل کامل بر همه جزئیات
- ✅ تغییرات پیشرفته در config
- ✅ تحلیل سفارشی نتایج
- ✅ Optimization loops

---

## 📊 مقایسه کاربرد هر روش

| روش | سادگی | کنترل | ذخیره نتایج | استفاده در کد |
|-----|--------|-------|-------------|---------------|
| **1. run_backtest.py** | ⭐⭐⭐⭐⭐ | ⭐ | ❌ | ❌ |
| **2. run_backtest_v2()** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ✅ |
| **3. BacktestEngineV2** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ✅ |

---

## 💡 توصیه نهایی

### برای اکثریت موارد: **روش 2** (run_backtest_v2)

```python
from backtest.backtest_engine_v2 import run_backtest_v2
import asyncio

async def main():
    engine, results_dir = await run_backtest_v2(
        scoring_method='new'  # NEW SYSTEM
    )
    print(f"Results: {results_dir}")

asyncio.run(main())
```

**چرا؟**
1. ✅ ساده اما قدرتمند
2. ✅ Config merging خودکار (3-way)
3. ✅ ذخیره خودکار نتایج
4. ✅ انتخاب روش scoring
5. ✅ قابل استفاده در script یا notebook

---

### برای Calibration/Optimization: **روش 3** (BacktestEngineV2)

```python
from backtest.backtest_engine_v2 import BacktestEngineV2

async def optimize_params():
    # Grid search example
    for slope_5m in [0.12, 0.15, 0.18]:
        for direction_margin in [1.2, 1.3, 1.4]:
            # تغییر config
            config['signal_generation']['trend_detection']['slope_thresholds']['5m'] = slope_5m
            config['multi_timeframe']['direction_margin'] = direction_margin

            # اجرا
            engine = BacktestEngineV2(config)
            await engine.initialize()
            await engine.run()

            # ذخیره و مقایسه
            results = engine.results['statistics']
            print(f"slope={slope_5m}, margin={direction_margin}: "
                  f"Sharpe={results['sharpe_ratio']:.3f}")
```

---

## 🔧 اصلاح پیشنهادی برای `run_backtest.py`

فایل فعلی **فقط نمایش** می‌دهد، اما **ذخیره نمی‌کند**.

### پیشنهاد:

```python
async def run_simple_backtest():
    """اجرای یک backtest ساده برای تست NEW SYSTEM"""

    # اجرا با run_backtest_v2 که نتایج را ذخیره می‌کند
    engine, results_dir = await run_backtest_v2(  # ✅ دریافت results_dir
        scoring_method='new'
    )

    # نمایش نتایج
    print(f"\n📊 Total trades: {engine.results['statistics']['total_trades']}")
    print(f"💰 Final equity: {engine.results['statistics']['current_equity']:.2f} USDT")
    print(f"📈 Total return: {engine.results['statistics']['total_return']:.2f}%")
    print(f"✅ Win rate: {engine.results['statistics']['win_rate']:.1f}%")

    # ✅ نمایش مسیر ذخیره
    print(f"\n💾 Results saved to: {results_dir}")
    print(f"   - statistics.json")
    print(f"   - trades.csv")
    print(f"   - equity_curve.csv")

    return engine, results_dir  # ✅ برگرداندن هر دو
```

---

## 📝 خلاصه

| سوال | پاسخ |
|------|------|
| **کدام بهتر است؟** | هیچ‌کدام! یکی موتور است، یکی interface |
| **کدام را استفاده کنم؟** | `run_backtest_v2()` برای اکثر موارد |
| **برای optimization؟** | `BacktestEngineV2` کلاس |
| **برای تست سریع؟** | `python run_backtest.py` |
| **برای calibration؟** | کلاس `BacktestEngineV2` با loop |

---

## 🎯 نتیجه‌گیری

```
run_backtest.py          →  Entry point ساده (برای راحتی)
    ↓
run_backtest_v2()        →  تابع اصلی (توصیه برای اکثر موارد)
    ↓
BacktestEngineV2 class   →  موتور کامل (برای کنترل پیشرفته)
```

**توصیه:**
- 🥇 **استفاده روزمره:** `run_backtest_v2()`
- 🥈 **Optimization:** `BacktestEngineV2` class
- 🥉 **تست سریع:** `python run_backtest.py`

**هر دو فایل خوب هستند، اما نقش‌های متفاوتی دارند!**

---

**📅 Version:** 1.0
**🗓️ Date:** 2025-11-21
