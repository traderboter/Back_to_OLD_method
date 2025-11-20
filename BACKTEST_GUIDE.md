# راهنمای اجرای Backtest

این راهنما نحوه اجرای backtest با NEW SYSTEM را توضیح می‌دهد.

---

## 📋 پیش‌نیازها

### 1. نصب Dependencies

```bash
pip install -r requirements.txt
```

### 2. فایل‌های مورد نیاز

مطمئن شوید این فایل‌ها موجود هستند:

- ✅ `config.yaml` - تنظیمات اصلی سیستم
- ✅ `backtest/config_backtest.yaml` - تنظیمات backtest
- ✅ `backtest/config_scoring_new.yaml` - تنظیمات scoring برای NEW SYSTEM
- ✅ داده‌های تاریخی (CSV files) در `data/historical/`

---

## 🚀 روش‌های اجرای Backtest

### روش 1️⃣: اجرای ساده با Python Script

استفاده از `run_backtest.py` که ساختیم:

```bash
# اجرای backtest کامل
python run_backtest.py

# اجرای تست سریع (فعلاً پیاده‌سازی نشده)
python run_backtest.py quick
```

### روش 2️⃣: اجرا در Python Interactive

```python
import asyncio
from backtest.backtest_engine_v2 import run_backtest_from_config

# اجرای backtest
engine, results_dir = await run_backtest_from_config(
    config_path='backtest/config_backtest.yaml',
    main_config_path='config.yaml',
    scoring_method='new'  # استفاده از NEW SYSTEM
)

# مشاهده نتایج
print(f"Results saved to: {results_dir}")
print(f"Total trades: {engine.results['statistics']['total_trades']}")
print(f"Win rate: {engine.results['statistics']['win_rate']:.1f}%")
```

### روش 3️⃣: اجرا با Jupyter Notebook

```python
# در یک Jupyter cell
import asyncio
from backtest.backtest_engine_v2 import run_backtest_from_config

async def run_backtest():
    engine, results_dir = await run_backtest_from_config(
        config_path='backtest/config_backtest.yaml',
        main_config_path='config.yaml',
        scoring_method='new'
    )
    return engine, results_dir

# اجرا
engine, results_dir = await run_backtest()
```

---

## 📊 تحلیل نتایج Backtest

### 1. بارگذاری نتایج

```python
import pandas as pd
import json

# بارگذاری trades
trades_df = pd.read_csv('backtest_results_v2/.../trades.csv')

# بارگذاری statistics
with open('backtest_results_v2/.../statistics.json') as f:
    stats = json.load(f)

# بارگذاری equity curve
equity_df = pd.read_csv('backtest_results_v2/.../equity_curve.csv')
```

### 2. تحلیل SL/TP Methods (🆕 NEW SYSTEM)

```python
# مقایسه روش‌های مختلف SL/TP
sl_method_analysis = trades_df.groupby('sl_method').agg({
    'realized_pnl': ['count', 'mean', 'sum'],
    'exit_reason': lambda x: (x == 'take_profit_hit').sum()
})

print("\n📊 SL/TP Method Performance:")
print(sl_method_analysis)

# بهترین روش
best_method = trades_df.groupby('sl_method')['realized_pnl'].mean().idxmax()
print(f"\n🏆 Best SL/TP Method: {best_method}")
```

### 3. تحلیل Confidence Levels (🆕 NEW SYSTEM)

```python
# مقایسه سطوح confidence
confidence_analysis = trades_df.groupby('confidence_level').agg({
    'realized_pnl': ['count', 'mean'],
    'exit_reason': lambda x: (x == 'take_profit_hit').sum() / len(x) * 100
})

print("\n📊 Confidence Level Performance:")
print(confidence_analysis)

# فقط HIGH confidence signals
high_conf = trades_df[trades_df['confidence_level'] == 'HIGH']
print(f"\n🎯 HIGH Confidence Win Rate: {(high_conf['realized_pnl'] > 0).mean():.1%}")
```

### 4. تحلیل Multi-TF vs Single-TF (🆕 NEW SYSTEM)

```python
# مقایسه Multi-TF و Single-TF
multi_tf = trades_df[trades_df['timeframes_count'] > 1]
single_tf = trades_df[trades_df['timeframes_count'] == 1]

print("\n📊 Multi-TF vs Single-TF:")
print(f"Multi-TF Trades: {len(multi_tf)}")
print(f"Multi-TF Win Rate: {(multi_tf['realized_pnl'] > 0).mean():.1%}")
print(f"Multi-TF Avg PnL: {multi_tf['realized_pnl'].mean():.2f} USDT")

print(f"\nSingle-TF Trades: {len(single_tf)}")
print(f"Single-TF Win Rate: {(single_tf['realized_pnl'] > 0).mean():.1%}")
print(f"Single-TF Avg PnL: {single_tf['realized_pnl'].mean():.2f} USDT")
```

### 5. تحلیل Score Breakdown (🆕 NEW SYSTEM)

```python
# استخراج score breakdown از metadata
import json

def extract_score_breakdown(metadata_json):
    """استخراج score breakdown از metadata JSON"""
    if pd.isna(metadata_json) or metadata_json == '{}':
        return {}
    try:
        metadata = json.loads(metadata_json)
        return metadata.get('score_breakdown', {})
    except:
        return {}

# اضافه کردن score components به DataFrame
trades_df['base_score_from_metadata'] = trades_df['metadata_json'].apply(
    lambda x: extract_score_breakdown(x).get('base_score', 0)
)

# همبستگی score components با PnL
print("\n📊 Score Components Correlation with PnL:")
print(f"Base Score vs PnL: {trades_df['base_score'].corr(trades_df['realized_pnl']):.3f}")
print(f"Alignment Factor vs PnL: {trades_df['alignment_factor'].corr(trades_df['realized_pnl']):.3f}")
```

### 6. رسم نمودارها

```python
import matplotlib.pyplot as plt

# نمودار Equity Curve
plt.figure(figsize=(12, 6))
equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
plt.plot(equity_df['timestamp'], equity_df['equity'])
plt.title('Equity Curve')
plt.xlabel('Time')
plt.ylabel('Equity (USDT)')
plt.grid(True)
plt.tight_layout()
plt.savefig('equity_curve.png')
plt.show()

# نمودار توزیع PnL
plt.figure(figsize=(10, 6))
trades_df['realized_pnl'].hist(bins=50, edgecolor='black')
plt.title('PnL Distribution')
plt.xlabel('Realized PnL (USDT)')
plt.ylabel('Frequency')
plt.axvline(x=0, color='red', linestyle='--', label='Break-even')
plt.legend()
plt.tight_layout()
plt.savefig('pnl_distribution.png')
plt.show()

# نمودار SL Method Performance
plt.figure(figsize=(10, 6))
sl_method_pnl = trades_df.groupby('sl_method')['realized_pnl'].mean()
sl_method_pnl.plot(kind='bar', color='skyblue', edgecolor='black')
plt.title('Average PnL by SL/TP Method')
plt.xlabel('SL/TP Method')
plt.ylabel('Average PnL (USDT)')
plt.xticks(rotation=45, ha='right')
plt.axhline(y=0, color='red', linestyle='--')
plt.tight_layout()
plt.savefig('sl_method_performance.png')
plt.show()
```

---

## 🔧 تنظیمات Backtest

### ویرایش `backtest/config_backtest.yaml`

```yaml
# دوره زمانی
start_date: '2024-01-01'
end_date: '2024-12-31'

# نمادهای مورد نظر
symbols:
  - BTCUSDT
  - ETHUSDT
  - BNBUSDT

# تایم‌فریم‌ها
timeframes:
  - 5m
  - 15m
  - 1h
  - 4h

# موجودی اولیه
initial_balance: 10000.0

# کمیسیون و slippage
commission_rate: 0.0006  # 0.06%
slippage: 0.0001  # 0.01%

# مدیریت ریسک
risk_management:
  max_risk_per_trade_percent: 2.0
  max_open_trades: 5
  max_trades_per_symbol: 2
```

---

## ⚡ اجرای تست‌های Unit

برای اطمینان از صحت کد قبل از backtest:

```bash
# همه تست‌ها
pytest tests/ -v

# فقط تست‌های مهم
pytest tests/unit/signal_generation/test_risk_calculator.py -v
pytest tests/unit/signal_generation/test_signal_scorer.py -v
pytest tests/unit/signal_generation/test_multi_tf_integration.py -v
pytest tests/integration/test_signal_pipeline_e2e.py -v
```

انتظار: **82/82 تست موفق ✅**

---

## 📝 نکات مهم

### ✅ چیزهایی که باید بررسی کنید:

1. **داده‌های تاریخی**: مطمئن شوید CSV files در `data/historical/` موجود هستند
2. **فایل‌های config**: همه 3 فایل config باید موجود باشند
3. **Dependencies**: همه کتابخانه‌ها نصب شده باشند
4. **حافظه**: برای backtest طولانی، حافظه کافی داشته باشید

### ⚠️ مشکلات رایج:

**مشکل 1: FileNotFoundError**
```bash
# راه حل: مطمئن شوید در مسیر اصلی پروژه هستید
cd /path/to/Back_to_OLD_method
python run_backtest.py
```

**مشکل 2: ModuleNotFoundError**
```bash
# راه حل: نصب dependencies
pip install -r requirements.txt
```

**مشکل 3: No data found**
```bash
# راه حل: بررسی مسیر داده‌ها در config_backtest.yaml
data_path: 'data/historical/'
```

---

## 🎯 مثال کامل

```bash
# 1. نصب dependencies
pip install -r requirements.txt

# 2. اجرای تست‌ها برای اطمینان
pytest tests/ -v

# 3. اجرای backtest
python run_backtest.py

# 4. تحلیل نتایج
python -c "
import pandas as pd
trades = pd.read_csv('backtest_results_v2/latest/trades.csv')
print(trades.groupby('sl_method')['realized_pnl'].mean())
"
```

---

## 📚 منابع بیشتر

- [README_NEW_SYSTEM.md](README_NEW_SYSTEM.md) - راهنمای کامل NEW SYSTEM
- [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) - راهنمای مهاجرت
- [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - مرجع سریع

---

**آخرین بروزرسانی:** 2025-01-20
