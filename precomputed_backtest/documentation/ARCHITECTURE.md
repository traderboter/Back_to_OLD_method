# معماری سیستم (System Architecture)

## دیاگرام کلی

```
┌─────────────────────────────────────────────────────────────────┐
│                     داده‌های تاریخی                              │
│                  historical/BTC-USDT/                           │
│         (5m.csv, 15m.csv, 1h.csv, 4h.csv)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    مرحله پیش‌محاسبه                              │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │ precompute_         │    │ precompute_         │            │
│  │ indicators.py       │    │ patterns.py         │            │
│  │                     │    │                     │            │
│  │ • EMA (9,20,50,     │    │ • Doji              │            │
│  │   100,200)          │    │ • Hammer            │            │
│  │ • SMA (20,50,200)   │    │ • Shooting Star     │            │
│  │ • RSI               │    │ • Engulfing         │            │
│  │ • MACD              │    │ • Morning Star      │            │
│  │ • ATR               │    │ • Evening Star      │            │
│  │ • Bollinger Bands   │    │ • Three White       │            │
│  │ • Stochastic        │    │   Soldiers          │            │
│  │ • OBV               │    │ • Three Black Crows │            │
│  │ • ADX               │    │ • Harami            │            │
│  └─────────────────────┘    │ • Piercing Line     │            │
│                             │ • Dark Cloud Cover  │            │
│                             └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   داده‌های پیش‌محاسبه شده                         │
│                    computed_data/                               │
│         (indicators/*.parquet, patterns/*.parquet)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     بکتست سریع                                  │
│                   fast_backtest.py                              │
│                                                                 │
│  • PrecomputedDataLoader: لود داده‌های parquet                  │
│  • FastBacktestEngine: اجرای بکتست                             │
│  • ~4500 کندل/ثانیه                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## کامپوننت‌ها

### 1. SimpleIndicatorCalculator
محاسبه اندیکاتورها بدون وابستگی به talib:

| اندیکاتور | فرمول |
|-----------|-------|
| EMA | Exponential Moving Average با span مشخص |
| SMA | Simple Moving Average |
| RSI | Relative Strength Index (14 دوره) |
| MACD | خط MACD, Signal, Histogram |
| ATR | Average True Range (14 دوره) |
| Bollinger | باندهای بالا، میانی، پایین |
| Stochastic | %K و %D |
| OBV | On Balance Volume |
| ADX | Average Directional Index |

### 2. PatternDetector
شناسایی 11 الگوی کندلی:

```python
patterns = [
    'doji',              # بدنه خیلی کوچک
    'hammer',            # سایه پایین بلند، صعودی
    'shooting_star',     # سایه بالا بلند، نزولی
    'engulfing',         # کندل بزرگتر از قبلی
    'morning_star',      # الگوی سه‌کندلی صعودی
    'evening_star',      # الگوی سه‌کندلی نزولی
    'three_white_soldiers',  # سه کندل صعودی متوالی
    'three_black_crows',     # سه کندل نزولی متوالی
    'harami',            # کندل داخل کندل قبلی
    'piercing_line',     # الگوی صعودی
    'dark_cloud_cover'   # الگوی نزولی
]
```

### 3. PrecomputedDataLoader
لود داده‌ها از فایل‌های Parquet:

```python
class PrecomputedDataLoader:
    def load_indicators(symbol, timeframe) -> DataFrame
    def load_patterns(symbol, timeframe) -> DataFrame
    def get_data_at_index(index) -> dict
```

### 4. FastBacktestEngine
موتور بکتست با استفاده از داده‌های پیش‌محاسبه شده:

```python
class FastBacktestEngine:
    def run() -> BacktestResult
    def generate_signal(data) -> Signal
    def execute_trade(signal) -> Trade
```

---

## فرمت داده‌ها

### Indicators Parquet
```
timestamp | open | high | low | close | volume | ema_9 | ema_20 | ... | adx
```

### Patterns Parquet
```
timestamp | open | high | low | close | doji | hammer | shooting_star | ...
```

---

## تایم‌فریم‌ها

| Timeframe | تعداد کندل | سایز فایل |
|-----------|------------|-----------|
| 5m | 94,816 | ~21 MB |
| 15m | 33,529 | ~7.3 MB |
| 1h | 10,543 | ~2.3 MB |
| 4h | 4,796 | ~1.1 MB |

---

## نحوه کار بکتست

1. **لود داده‌ها**: همه فایل‌های parquet به حافظه لود می‌شوند
2. **پیمایش**: کندل به کندل روی تایم‌فریم 5 دقیقه
3. **سیگنال**: بررسی شرایط با داده‌های از پیش محاسبه شده
4. **معامله**: اجرای معامله در صورت وجود سیگنال
5. **نتیجه**: گزارش عملکرد
