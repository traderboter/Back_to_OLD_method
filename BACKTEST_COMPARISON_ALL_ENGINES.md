# 🚀 مقایسه جامع سه موتور Backtest

## 📊 خلاصه اجرایی

شما **سه موتور backtest** دارید که هر کدام برای کاربرد خاصی طراحی شده‌اند:

| موتور | سرعت | دقت | کاربرد |
|-------|------|-----|--------|
| **Precomputed Backtest** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Optimization & Testing |
| **BacktestEngineV2** | ⭐ | ⭐⭐⭐⭐⭐ | Final Validation |
| **run_backtest.py** | ⭐ | ⭐⭐⭐⭐⭐ | Quick Testing |

---

## Table of Contents

1. [سه موتور Backtest](#1-سه-موتور-backtest)
2. [مقایسه جزئیات فنی](#2-مقایسه-جزئیات-فنی)
3. [مقایسه سرعت](#3-مقایسه-سرعت)
4. [مقایسه دقت](#4-مقایسه-دقت)
5. [چه زمانی از کدام استفاده کنیم](#5-چه-زمانی-از-کدام-استفاده-کنیم)
6. [Workflow پیشنهادی](#6-workflow-پیشنهادی)
7. [مثال‌های کاربردی](#7-مثال-های-کاربردی)

---

## 1️⃣ سه موتور Backtest

### 🚀 Precomputed Backtest (سریع)

**مکان:** `precomputed_backtest/fast_backtest.py`

**فلسفه:** Pre-computation برای سرعت بالا

```python
# مرحله 1: یکبار محاسبه (یک بار فقط)
python precompute_indicators.py  # 45 indicator
python precompute_patterns.py    # 31 pattern

# مرحله 2: backtest سریع (هر بار)
python fast_backtest.py          # ~3500 candles/sec
```

**ویژگی‌های کلیدی:**
- ✅ سرعت فوق‌العاده (1000x سریع‌تر)
- ✅ استقلال کامل (config های محلی)
- ✅ بدون talib (فقط pandas)
- ✅ 45 indicator + 31 pattern
- ✅ ذخیره در Parquet (سریع)
- ⚠️ دقت متوسط (ساده‌سازی شده)
- ⚠️ Multi-TF ساده (1 timeframe اصلی)

**ساختار:**
```
precomputed_backtest/
├── precompute_indicators.py   # محاسبه indicators
├── precompute_patterns.py     # شناسایی patterns
├── fast_backtest.py           # موتور سریع
├── computed_data/             # داده‌های Parquet
│   ├── indicators/
│   └── patterns/
├── configs/                   # تنظیمات محلی
└── reports/                   # گزارش‌ها
```

---

### 🏭 BacktestEngineV2 (دقیق)

**مکان:** `backtest/backtest_engine_v2.py`

**فلسفه:** دقت کامل با SignalOrchestrator

```python
from backtest.backtest_engine_v2 import run_backtest_v2

# اجرای دقیق (کند اما دقیق)
engine, results = await run_backtest_v2(
    scoring_method='new'  # یا 'old'
)
```

**ویژگی‌های کلیدی:**
- ✅ دقت کامل (100% مانند live)
- ✅ SignalOrchestrator واقعی
- ✅ Multi-TF کامل (4 timeframes)
- ✅ 11 Analyzer تخصصی
- ✅ Confidence System
- ✅ Risk Calculator 5-method
- ❌ کند (~1-5 steps/sec)
- ❌ نیاز به talib

**جریان:**
```
CSV Data → IndicatorCalculator → 11 Analyzers →
MultiTF Aggregator → SignalOrchestrator → Trades
```

---

### 🚪 run_backtest.py (Entry Point)

**مکان:** `run_backtest.py`

**فلسفه:** Wrapper ساده برای BacktestEngineV2

```python
# اجرای ساده
python run_backtest.py
```

**ویژگی‌های کلیدی:**
- ✅ راحت برای اجرا
- ✅ فقط 103 خطوط
- ❌ از BacktestEngineV2 استفاده می‌کند (کند)
- ❌ کنترل محدود

**نکته:** این فقط یک wrapper است، موتور واقعی BacktestEngineV2 است.

---

## 2️⃣ مقایسه جزئیات فنی

### جدول مقایسه کامل

| Feature | Precomputed | BacktestEngineV2 | run_backtest.py |
|---------|-------------|------------------|-----------------|
| **خطوط کد** | ~800 | 950 | 103 |
| **سرعت** | ~3500 candles/sec | ~1-5 steps/sec | ~1-5 steps/sec |
| **Speedup** | **1000x** | 1x | 1x |
| **Dependencies** | pandas, numpy, pyarrow | talib, scipy, pandas | همان V2 |
| **Indicators** | 45 (pre-computed) | Dynamic | Dynamic |
| **Patterns** | 31 (pre-computed) | 16 (real-time) | 16 |
| **Analyzers** | ❌ ندارد | ✅ 11 analyzer | ✅ 11 analyzer |
| **Multi-TF** | ⚠️ ساده | ✅ کامل (4 TF) | ✅ کامل |
| **SignalOrchestrator** | ❌ ندارد | ✅ دارد | ✅ دارد |
| **Confidence System** | ❌ ندارد | ✅ دارد | ✅ دارد |
| **Risk Calculator** | ⚠️ ساده | ✅ 5-method | ✅ 5-method |
| **Config** | محلی (configs/) | اصلی (root) | اصلی |
| **Scoring Methods** | NEW/OLD/HYBRID/Strategy | NEW/OLD | NEW/OLD |
| **Results** | MD + CSV + PNG | JSON + CSV | فقط نمایش |

---

### مقایسه Data Flow

#### Precomputed Backtest:
```
┌──────────────┐
│ CSV Files    │
└──────┬───────┘
       ▼
┌──────────────────────────┐
│ Pre-computation (یکبار)  │
│ • 45 indicators          │
│ • 31 patterns            │
└──────┬───────────────────┘
       ▼
┌──────────────────────┐
│ Parquet Files        │ ← سریع!
│ (computed_data/)     │
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ FastBacktestEngine   │
│ • Load از Parquet    │
│ • FastScorer         │
│ • Simple logic       │
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ Results (~9 sec)     │
└──────────────────────┘
```

#### BacktestEngineV2:
```
┌──────────────┐
│ CSV Files    │
└──────┬───────┘
       ▼
┌──────────────────────────┐
│ HistoricalDataProvider   │
└──────┬───────────────────┘
       ▼
┌──────────────────────────┐
│ IndicatorCalculator      │ ← هر بار محاسبه
└──────┬───────────────────┘
       ▼
┌──────────────────────────┐
│ 11 Analyzers             │
│ • Trend                  │
│ • Momentum               │
│ • Pattern (16)           │
│ • S/R                    │
│ • ... (7 more)           │
└──────┬───────────────────┘
       ▼
┌──────────────────────────┐
│ MultiTF Aggregator       │
│ • 4 timeframes           │
│ • Confidence             │
│ • Consensus              │
└──────┬───────────────────┘
       ▼
┌──────────────────────────┐
│ SignalOrchestrator       │
│ • Risk Calculator        │
│ • Signal Validator       │
└──────┬───────────────────┘
       ▼
┌──────────────────────────┐
│ Results (hours)          │
└──────────────────────────┘
```

---

## 3️⃣ مقایسه سرعت

### Benchmark: 33,000 کندل (حدود 115 روز در 5m)

| موتور | زمان | سرعت | Speedup |
|-------|------|------|---------|
| **Precomputed** | ~9 seconds | 3,666 candles/sec | **1000x** |
| **BacktestEngineV2** | ~2-5 hours | 1-5 steps/sec | 1x |
| **run_backtest.py** | ~2-5 hours | 1-5 steps/sec | 1x |

### تجزیه و تحلیل سرعت

**چرا Precomputed اینقدر سریع است؟**

1. **Pre-computation** - indicators و patterns یکبار محاسبه می‌شوند
2. **Parquet Format** - خواندن از Parquet 100x سریعتر از CSV
3. **Simple Logic** - بدون Analyzers پیچیده
4. **Single TF** - فقط یک timeframe اصلی
5. **No talib** - pandas محض (سریعتر)

**چرا BacktestEngineV2 کند است؟**

1. **Real-time Calculation** - هر indicator هر بار محاسبه می‌شود
2. **11 Analyzers** - پردازش پیچیده
3. **Multi-TF** - 4 timeframe همزمان
4. **SignalOrchestrator** - منطق کامل
5. **talib Dependency** - overhead بیشتر

---

### مقایسه زمان Pre-computation

| Task | زمان | تکرار |
|------|------|-------|
| **precompute_indicators.py** | ~2-3 دقیقه | یکبار |
| **precompute_patterns.py** | ~1-2 دقیقه | یکبار |
| **Total Pre-computation** | ~5 دقیقه | یکبار |
| **fast_backtest.py** | ~9 ثانیه | هر بار |

**نتیجه:**
- بار اول: 5 دقیقه (pre-compute) + 9 ثانیه (backtest) = ~5 دقیقه
- بارهای بعد: فقط 9 ثانیه!

**در مقابل BacktestEngineV2:**
- هر بار: 2-5 ساعت

---

## 4️⃣ مقایسه دقت

### دقت Signal Generation

| Aspect | Precomputed | BacktestEngineV2 |
|--------|-------------|------------------|
| **Indicators** | ⚠️ ساده (45 indicator) | ✅ کامل (dynamic) |
| **Patterns** | ⚠️ ساده (31 pattern) | ✅ کامل (16 pattern) |
| **Multi-TF** | ⚠️ ساده (1 TF اصلی) | ✅ کامل (4 TF) |
| **Analyzers** | ❌ ندارد | ✅ 11 analyzer |
| **Confidence** | ❌ ندارد | ✅ دارد |
| **Direction** | ⚠️ Simple scoring | ✅ Multi-TF consensus |
| **Risk Calc** | ⚠️ ساده (ATR/%) | ✅ 5-method priority |

### نتایج Backtest (33K candles)

#### Precomputed (NEW method):
```
Total Trades: 1,548
Win Rate: 39.5%
Total Return: -26.74%
Profit Factor: 0.60
Max Drawdown: 27.70%
Duration: ~9 sec
```

#### Precomputed (OLD method):
```
Total Trades: 6
Win Rate: 50.0%
Total Return: +0.11%
Profit Factor: 2.04
Max Drawdown: 0.12%
Duration: ~9 sec
```

#### BacktestEngineV2:
```
Status: در حال اجرا (چندین ساعت)
Expected Trades: 100-500 (NEW) or 10-50 (OLD)
Expected Win Rate: 55-65% (NEW) or 45-55% (OLD)
```

### تفاوت‌های نتایج

**چرا نتایج متفاوت است؟**

1. **Signal Logic متفاوت**
   - Precomputed: FastScorer (ساده)
   - V2: SignalOrchestrator (کامل)

2. **Multi-TF متفاوت**
   - Precomputed: 1 timeframe
   - V2: 4 timeframes با aggregation

3. **Threshold متفاوت**
   - Precomputed NEW: min_score=50
   - Precomputed OLD: min_score=200
   - V2: dynamic بر اساس confidence

4. **Risk Management متفاوت**
   - Precomputed: ساده (ATR × 2)
   - V2: 5-method priority

---

## 5️⃣ چه زمانی از کدام استفاده کنیم

### 🚀 Precomputed Backtest - برای:

✅ **Parameter Optimization**
```python
# Grid search سریع
for slope_5m in [0.12, 0.15, 0.18]:
    for margin in [1.2, 1.3, 1.4]:
        # Run fast_backtest.py
        # Takes only ~9 seconds per iteration!
```

✅ **Quick Testing**
```python
# تست سریع یک strategy
# نیازی به انتظار ساعت‌ها نیست
```

✅ **Iterative Development**
```python
# تغییر logic → test → تغییر → test
# چرخه سریع توسعه
```

✅ **Initial Exploration**
```python
# بررسی سریع ایده‌های جدید
# قبل از پیاده‌سازی کامل
```

**کاربرد:**
- Calibration (راهنمای `BACKTEST_CALIBRATION_GUIDE.md`)
- A/B Testing
- Strategy Comparison
- Quick Validation

---

### 🏭 BacktestEngineV2 - برای:

✅ **Final Validation**
```python
# تست نهایی قبل از live
# با دقت کامل
```

✅ **Production-Grade Results**
```python
# نتایج قابل اعتماد
# مانند live trading
```

✅ **Multi-TF Strategies**
```python
# strategies که به 4 timeframe نیاز دارند
# با Confidence System
```

✅ **Risk Analysis**
```python
# بررسی دقیق Risk Calculator
# با 5 روش SL/TP
```

**کاربرد:**
- Final Validation
- Walk-Forward Analysis
- Paper Trading Simulation
- Production Deployment Decision

---

### 🚪 run_backtest.py - برای:

✅ **Quick Manual Test**
```bash
# تست دستی سریع
python run_backtest.py
```

✅ **Beginners**
```python
# شروع ساده
# بدون نیاز به کد نوشتن
```

**کاربرد:**
- Manual testing
- Learning
- Demos

**نکته:** از BacktestEngineV2 استفاده می‌کند، پس کند است!

---

## 6️⃣ Workflow پیشنهادی

### Approach 1: Speed First (توصیه برای Optimization)

```
1. Precomputed Backtest (9 sec/run)
   ↓
   Grid Search / Bayesian Optimization
   100-1000 iterations × 9 sec = 15 min - 2.5 hour
   ↓
   بهترین پارامترها

2. BacktestEngineV2 (2-5 hours)
   ↓
   Validation با پارامترهای بهینه
   ↓
   نتایج نهایی
```

**مزیت:**
- سریع (optimization در کمتر از 3 ساعت)
- دقیق (validation با V2)

---

### Approach 2: Accuracy First (توصیه برای Production)

```
1. BacktestEngineV2 (2-5 hours)
   ↓
   Walk-Forward Analysis
   Multiple time periods
   ↓
   نتایج قابل اعتماد

2. Precomputed (optional)
   ↓
   Quick checks
   ↓
   Confirmation
```

**مزیت:**
- دقیق (V2 از ابتدا)
- Safe (بدون risk ساده‌سازی)

---

### Approach 3: Hybrid (Best of Both)

```
1. Precomputed - Initial Exploration (9 sec)
   ↓
   تست سریع 10-20 strategy
   ↓
   انتخاب 2-3 استراتژی برتر

2. BacktestEngineV2 - Deep Validation (2-5 hours)
   ↓
   تست دقیق استراتژی‌های برتر
   ↓
   انتخاب نهایی

3. Precomputed - Fine-tuning (1 hour)
   ↓
   Calibration پارامترهای استراتژی منتخب
   50-100 iterations
   ↓
   پارامترهای بهینه

4. BacktestEngineV2 - Final Check (2-5 hours)
   ↓
   Validation نهایی
   ↓
   ✅ آماده برای Live
```

**مزیت:**
- سریع (exploration با Precomputed)
- دقیق (validation با V2)
- Safe (multi-stage validation)

**⭐ این approach را توصیه می‌کنیم!**

---

## 7️⃣ مثال‌های کاربردی

### مثال 1: Parameter Optimization (سریع)

```python
# استفاده از Precomputed برای Grid Search

import subprocess
import json
from pathlib import Path

# پارامترهای تست
slope_thresholds = [0.12, 0.15, 0.18]
direction_margins = [1.2, 1.3, 1.4]

results = []

for slope in slope_thresholds:
    for margin in direction_margins:
        # 1. تغییر config
        # (edit fast_backtest.py parameters)

        # 2. اجرای backtest
        subprocess.run(['python', 'fast_backtest.py'])

        # 3. خواندن نتایج
        with open('reports/backtest_report.md') as f:
            # Parse results
            result = {
                'slope': slope,
                'margin': margin,
                'win_rate': ...,  # از گزارش
                'profit_factor': ...,
                'sharpe': ...
            }
            results.append(result)

# بهترین پارامتر
best = max(results, key=lambda x: x['sharpe'])
print(f"Best params: slope={best['slope']}, margin={best['margin']}")

# زمان کل: ~100 iterations × 9 sec = 15 دقیقه!
```

---

### مثال 2: Final Validation (دقیق)

```python
# استفاده از BacktestEngineV2 برای Validation نهایی

from backtest.backtest_engine_v2 import run_backtest_v2
import asyncio

async def final_validation():
    # پارامترهای بهینه از Precomputed
    best_params = {
        'slope_5m': 0.15,
        'direction_margin': 1.3,
        'min_score': 50
    }

    # Update config with best_params
    # ...

    # اجرای Backtest دقیق
    print("Running final validation (may take hours)...")
    engine, results_dir = await run_backtest_v2(
        scoring_method='new'
    )

    stats = engine.results['statistics']

    print(f"\n✅ Final Validation Results:")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Profit Factor: {stats['profit_factor']:.2f}")
    print(f"Sharpe Ratio: {stats.get('sharpe_ratio', 0):.3f}")
    print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")

    # تصمیم نهایی
    if (stats['win_rate'] > 50 and
        stats['profit_factor'] > 1.5 and
        stats['max_drawdown'] < 20):
        print("\n🚀 Strategy approved for live trading!")
    else:
        print("\n⚠️ Strategy needs more work")

# اجرا
asyncio.run(final_validation())

# زمان: 2-5 ساعت (اما دقیق!)
```

---

### مثال 3: Hybrid Workflow (توصیه)

```python
import subprocess
import asyncio
from backtest.backtest_engine_v2 import run_backtest_v2

def stage1_exploration():
    """Stage 1: تست سریع strategies مختلف"""
    print("Stage 1: Quick Exploration (Precomputed)")

    strategies = ['aggressive', 'balanced', 'conservative']
    results = {}

    for strategy in strategies:
        print(f"\nTesting {strategy} strategy...")
        # Update config
        # Run fast_backtest.py
        subprocess.run(['python', 'fast_backtest.py'])
        # Parse results
        results[strategy] = {
            'win_rate': ...,
            'profit_factor': ...
        }

    # بهترین strategy
    best = max(results.items(), key=lambda x: x[1]['profit_factor'])
    print(f"\n✅ Best strategy: {best[0]}")
    return best[0]

async def stage2_validation(strategy):
    """Stage 2: Validation دقیق با V2"""
    print(f"\nStage 2: Deep Validation for {strategy} (BacktestEngineV2)")

    # Setup config for strategy
    # ...

    engine, results = await run_backtest_v2(scoring_method='new')

    stats = engine.results['statistics']
    print(f"\nValidation Results:")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    print(f"  Profit Factor: {stats['profit_factor']:.2f}")

    return stats

def stage3_calibration(strategy, baseline_stats):
    """Stage 3: Fine-tuning با Precomputed"""
    print(f"\nStage 3: Parameter Calibration (Precomputed)")

    # Grid search on parameters
    # Similar to Example 1
    # ...

    print(f"✅ Calibration complete")
    return best_params

async def stage4_final_check(strategy, params):
    """Stage 4: Final check با V2"""
    print(f"\nStage 4: Final Validation (BacktestEngineV2)")

    # Update config with calibrated params
    # Run V2 again
    engine, results = await run_backtest_v2(scoring_method='new')

    stats = engine.results['statistics']

    if stats['profit_factor'] > 1.5:
        print(f"\n🎉 Strategy ready for live!")
        return True
    else:
        print(f"\n❌ Strategy failed final check")
        return False

# ===== Main Workflow =====
async def main():
    # Stage 1: Quick exploration (15 دقیقه)
    best_strategy = stage1_exploration()

    # Stage 2: Deep validation (2-5 ساعت)
    baseline = await stage2_validation(best_strategy)

    # Stage 3: Calibration (1 ساعت)
    best_params = stage3_calibration(best_strategy, baseline)

    # Stage 4: Final check (2-5 ساعت)
    approved = await stage4_final_check(best_strategy, best_params)

    if approved:
        print("\n🚀 Ready for production!")

# اجرا
asyncio.run(main())

# زمان کل: ~5-10 ساعت (اما comprehensive!)
```

---

## 8️⃣ محدودیت‌ها و توصیه‌ها

### Precomputed Backtest

**محدودیت‌ها:**
1. ⚠️ Simplified logic (not 100% like live)
2. ⚠️ Single timeframe primary (not full Multi-TF)
3. ⚠️ No Confidence System
4. ⚠️ Simple Risk Calculator
5. ⚠️ Results may differ from V2

**توصیه‌ها:**
1. ✅ برای optimization استفاده کنید
2. ✅ نتایج را با V2 validate کنید
3. ✅ فقط برای relative comparison (نه absolute)
4. ❌ مستقیماً برای live decision استفاده نکنید

---

### BacktestEngineV2

**محدودیت‌ها:**
1. ⚠️ بسیار کند (2-5 ساعت)
2. ⚠️ نیاز به talib
3. ⚠️ Resource intensive

**توصیه‌ها:**
1. ✅ برای final validation استفاده کنید
2. ✅ قبل از live حتماً اجرا کنید
3. ✅ Walk-forward analysis
4. ✅ نتایج قابل اعتماد

---

## 9️⃣ خلاصه نهایی

### جدول تصمیم‌گیری

| هدف شما | موتور توصیه شده | زمان | دقت |
|---------|-----------------|------|-----|
| **Optimization (100+ tests)** | 🚀 Precomputed | ~15-60 min | ⭐⭐⭐ |
| **Strategy Comparison** | 🚀 Precomputed | ~1-5 min | ⭐⭐⭐ |
| **Quick Testing** | 🚀 Precomputed | ~10 sec | ⭐⭐⭐ |
| **Final Validation** | 🏭 BacktestEngineV2 | 2-5 hours | ⭐⭐⭐⭐⭐ |
| **Production Decision** | 🏭 BacktestEngineV2 | 2-5 hours | ⭐⭐⭐⭐⭐ |
| **Walk-Forward** | 🏭 BacktestEngineV2 | 10-20 hours | ⭐⭐⭐⭐⭐ |
| **Manual Test** | 🚪 run_backtest.py | 2-5 hours | ⭐⭐⭐⭐⭐ |

---

### پیشنهاد نهایی: Hybrid Workflow

```
1. 🚀 Precomputed: Exploration (15 min)
   ├─ تست 10-20 strategy
   └─ انتخاب top 2-3

2. 🏭 BacktestEngineV2: Validation (3-5 hours)
   ├─ تست دقیق top strategies
   └─ انتخاب بهترین

3. 🚀 Precomputed: Calibration (1 hour)
   ├─ Grid search پارامترها
   └─ پارامترهای بهینه

4. 🏭 BacktestEngineV2: Final (3-5 hours)
   ├─ Validation با پارامترهای بهینه
   └─ تصمیم نهایی

Total: ~8-12 hours
```

**این approach بهترین balance بین سرعت و دقت است!** ⭐

---

## 🔟 مستندات مرتبط

| مستند | موضوع |
|-------|-------|
| `BACKTEST_ENGINES_COMPARISON.md` | مقایسه run_backtest و backtest_engine_v2 |
| `SCORING_METHODS_COMPARISON.md` | مقایسه NEW vs OLD vs HYBRID |
| `BACKTEST_CALIBRATION_GUIDE.md` | راهنمای Calibration پارامترها |
| `precomputed_backtest/documentation/README.md` | راهنمای Precomputed |
| `precomputed_backtest/documentation/ARCHITECTURE.md` | معماری Precomputed |
| `precomputed_backtest/documentation/COMPARISON_REPORT.md` | گزارش مقایسه |

---

**📅 Version:** 1.0
**🗓️ Date:** 2025-11-21
**✍️ Author:** Claude Analysis
