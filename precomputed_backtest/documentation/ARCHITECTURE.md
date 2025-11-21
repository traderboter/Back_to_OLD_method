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
│  ┌──────────────────────────────┐  ┌──────────────────────────┐ │
│  │ precompute_indicators.py     │  │ precompute_patterns.py   │ │
│  │                              │  │                          │ │
│  │ 45 اندیکاتور:                │  │ 31 الگو:                 │ │
│  │ • Moving Averages (8)        │  │ • کندلی تک‌کندلی (9)     │ │
│  │ • Momentum (7)               │  │ • کندلی دو‌کندلی (6)     │ │
│  │ • Volatility (4)             │  │ • کندلی سه‌کندلی (4)     │ │
│  │ • Volume (5)                 │  │ • چارت (12)             │ │
│  │ • Trend (6)                  │  │                          │ │
│  │ • Support/Resistance (14)    │  │                          │ │
│  └──────────────────────────────┘  └──────────────────────────┘ │
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
│  • ~8000 کندل/ثانیه                                            │
│  • گزارش‌دهی: MD, CSV, PNG                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## کامپوننت‌ها

### 1. SimpleIndicatorCalculator (45 اندیکاتور)

#### Moving Averages (8)
| اندیکاتور | ستون‌ها |
|-----------|---------|
| EMA | ema_9, ema_20, ema_50, ema_100, ema_200 |
| SMA | sma_20, sma_50, sma_200 |

#### Momentum (7)
| اندیکاتور | ستون‌ها |
|-----------|---------|
| RSI | rsi |
| MACD | macd, macd_signal, macd_hist |
| Stochastic | stoch_k, stoch_d |
| Williams %R | williams_r |
| CCI | cci |

#### Volatility (4)
| اندیکاتور | ستون‌ها |
|-----------|---------|
| ATR | atr |
| Bollinger Bands | bb_upper, bb_mid, bb_lower |

#### Volume (5)
| اندیکاتور | ستون‌ها |
|-----------|---------|
| OBV | obv |
| VWAP | vwap |
| Volume Profile | vp_poc, vp_vah, vp_val |

#### Trend (6)
| اندیکاتور | ستون‌ها |
|-----------|---------|
| ADX | adx |
| Ichimoku Cloud | ichimoku_tenkan, ichimoku_kijun, ichimoku_senkou_a, ichimoku_senkou_b, ichimoku_chikou |

#### Support/Resistance (14)
| اندیکاتور | ستون‌ها |
|-----------|---------|
| Pivot Points | pivot, pivot_r1, pivot_s1, pivot_r2, pivot_s2, pivot_r3, pivot_s3 |
| Fibonacci Retracement | fib_0, fib_236, fib_382, fib_500, fib_618, fib_786, fib_100 |

---

### 2. SimpleCandlePatternDetector (19 الگوی کندلی)

#### تک‌کندلی (9)
```python
patterns_single = [
    'doji',              # بدنه خیلی کوچک - خنثی
    'hammer',            # سایه پایین بلند - صعودی
    'shooting_star',     # سایه بالا بلند - نزولی
    'spinning_top',      # بدنه کوچک، سایه‌های متقارن - خنثی
    'marubozu',          # بدون سایه - قوی
    'inverted_hammer',   # سایه بالا بلند - صعودی (در کف)
    'hanging_man',       # سایه پایین بلند - نزولی (در سقف)
    'dragonfly_doji',    # سایه پایین بلند، بدنه صفر - صعودی
    'gravestone_doji'    # سایه بالا بلند، بدنه صفر - نزولی
]
```

#### دو‌کندلی (6)
```python
patterns_double = [
    'engulfing',         # کندل بزرگتر از قبلی
    'harami',            # کندل داخل کندل قبلی
    'piercing_line',     # الگوی صعودی
    'dark_cloud_cover',  # الگوی نزولی
    'tweezer_top',       # دو قله یکسان - نزولی
    'tweezer_bottom'     # دو کف یکسان - صعودی
]
```

#### سه‌کندلی (4)
```python
patterns_triple = [
    'morning_star',          # الگوی سه‌کندلی صعودی
    'evening_star',          # الگوی سه‌کندلی نزولی
    'three_white_soldiers',  # سه کندل صعودی متوالی
    'three_black_crows'      # سه کندل نزولی متوالی
]
```

---

### 3. SimpleChartPatternDetector (12 الگوی چارت)

با استفاده از `scipy.signal.find_peaks` برای تشخیص قله/کف:

```python
chart_patterns = [
    # Double patterns
    'double_top',             # دو قله هم‌ارتفاع - نزولی
    'double_bottom',          # دو کف هم‌عمق - صعودی

    # Head & Shoulders
    'head_shoulders',         # سر و شانه - نزولی
    'inverse_head_shoulders', # سر و شانه معکوس - صعودی

    # Triangles
    'ascending_triangle',     # مثلث صعودی - صعودی
    'descending_triangle',    # مثلث نزولی - نزولی
    'symmetric_triangle',     # مثلث متقارن - خنثی

    # Flags
    'bull_flag',              # پرچم صعودی - صعودی
    'bear_flag',              # پرچم نزولی - نزولی

    # Other
    'cup_and_handle',         # فنجان و دسته - صعودی
    'rising_wedge',           # گوه صعودی - نزولی
    'falling_wedge'           # گوه نزولی - صعودی
]
```

---

### 4. PrecomputedDataLoader
لود داده‌ها از فایل‌های Parquet:

```python
class PrecomputedDataLoader:
    def load_indicators(symbol, timeframe) -> DataFrame
    def load_patterns(symbol, timeframe) -> DataFrame
    def get_data_at_index(index) -> dict
```

### 5. FastBacktestEngine
موتور بکتست با استفاده از داده‌های پیش‌محاسبه شده:

```python
class FastBacktestEngine:
    def run() -> BacktestResult
    def generate_signal(data) -> Signal
    def execute_trade(signal) -> Trade
    def generate_report() -> str
    def save_equity_curve_chart() -> None
    def save_performance_summary_chart() -> None
```

---

## فرمت داده‌ها

### Indicators Parquet (45+ ستون)
```
timestamp | open | high | low | close | volume |
ema_9 | ema_20 | ... | ema_200 |
sma_20 | sma_50 | sma_200 |
rsi | macd | macd_signal | macd_hist |
atr | bb_upper | bb_mid | bb_lower |
stoch_k | stoch_d | obv | adx |
ichimoku_tenkan | ichimoku_kijun | ichimoku_senkou_a | ichimoku_senkou_b | ichimoku_chikou |
vwap | pivot | pivot_r1 | pivot_s1 | pivot_r2 | pivot_s2 | pivot_r3 | pivot_s3 |
williams_r | cci |
fib_0 | fib_236 | fib_382 | fib_500 | fib_618 | fib_786 | fib_100 |
vp_poc | vp_vah | vp_val
```

### Patterns Parquet (93+ ستون)
برای هر الگو سه ستون: `pattern_X`, `pattern_X_direction`, `pattern_X_score`

```
timestamp | open | high | low | close |
pattern_doji | pattern_doji_direction | pattern_doji_score |
pattern_hammer | ... |
pattern_double_top | pattern_double_top_direction | pattern_double_top_score |
...
```

---

## تایم‌فریم‌ها

| Timeframe | تعداد کندل | سایز فایل |
|-----------|------------|-----------|
| 5m | ~95,000 | ~25 MB |
| 15m | ~34,000 | ~9 MB |
| 1h | ~11,000 | ~3 MB |
| 4h | ~5,000 | ~1.5 MB |

---

## نحوه کار بکتست

1. **لود داده‌ها**: همه فایل‌های parquet به حافظه لود می‌شوند
2. **پیمایش**: کندل به کندل روی تایم‌فریم 5 دقیقه
3. **سیگنال**: بررسی شرایط با داده‌های از پیش محاسبه شده
4. **معامله**: اجرای معامله در صورت وجود سیگنال
5. **نتیجه**: گزارش عملکرد + نمودارها

---

## گزارش‌دهی

| فایل | توضیح |
|------|-------|
| backtest_report.md | گزارش متنی با آمار کامل |
| equity_curve.csv | منحنی equity برای تحلیل |
| trades_list.csv | لیست همه معاملات |
| equity_curve.png | نمودار equity با drawdown |
| performance_summary.png | 4 پنل: PnL, Histogram, Win Rate, Stats |
