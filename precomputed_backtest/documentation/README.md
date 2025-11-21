# سیستم پیش‌محاسبه بکتست (Precomputed Backtest System)

## هدف پروژه

این سیستم برای **بهینه‌سازی سرعت بکتست** طراحی شده است.

### مشکل اصلی
در بکتست معمولی، هر بار که بکتست اجرا می‌شود:
- اندیکاتورها (EMA, RSI, MACD, ...) برای هر کندل محاسبه می‌شوند
- الگوهای کندلی (Doji, Hammer, ...) برای هر کندل شناسایی می‌شوند
- این محاسبات تکراری زمان‌بر هستند

### راه‌حل
از آنجا که داده‌های تاریخی **ثابت** هستند، نتیجه محاسبات همیشه یکسان است. بنابراین:
1. یک بار همه محاسبات را انجام می‌دهیم
2. نتایج را در فایل‌های Parquet ذخیره می‌کنیم
3. در بکتست‌های بعدی فقط داده‌ها را می‌خوانیم

**نتیجه**: سرعت ~8000 کندل در ثانیه

---

## وضعیت فعلی پیاده‌سازی

### اندیکاتورها (45 اندیکاتور)
| گروه | اندیکاتورها | وضعیت |
|------|-------------|--------|
| Moving Averages | EMA (9,20,50,100,200), SMA (20,50,200) | ✅ پیاده‌سازی شده |
| Momentum | RSI, MACD, Stochastic K/D, Williams %R, CCI | ✅ پیاده‌سازی شده |
| Volatility | ATR, Bollinger Bands (Upper/Mid/Lower) | ✅ پیاده‌سازی شده |
| Volume | OBV, VWAP, Volume Profile (POC/VAH/VAL) | ✅ پیاده‌سازی شده |
| Trend | ADX, Ichimoku Cloud (5 component) | ✅ پیاده‌سازی شده |
| Support/Resistance | Pivot Points (7 levels), Fibonacci (7 levels) | ✅ پیاده‌سازی شده |

### الگوها (31 الگو)
| گروه | الگوها | وضعیت |
|------|--------|--------|
| الگوهای کندلی تک‌کندلی | Doji, Hammer, Shooting Star, Spinning Top, Marubozu, Inverted Hammer, Hanging Man, Dragonfly Doji, Gravestone Doji | ✅ 9 الگو |
| الگوهای کندلی دو‌کندلی | Engulfing, Harami, Piercing Line, Dark Cloud Cover, Tweezer Top/Bottom | ✅ 6 الگو |
| الگوهای کندلی سه‌کندلی | Morning Star, Evening Star, Three White Soldiers, Three Black Crows | ✅ 4 الگو |
| الگوهای چارت | Double Top/Bottom, Head & Shoulders, Triangles, Flags, Cup & Handle, Wedges | ✅ 12 الگو |

---

## ساختار پوشه‌ها

```
precomputed_backtest/
├── configs/                    # تنظیمات محلی
│   ├── config.yaml
│   └── config_backtest_v2.yaml
├── computed_data/              # داده‌های پیش‌محاسبه شده
│   ├── indicators/
│   │   └── BTC-USDT/
│   │       ├── 5m_indicators.parquet
│   │       ├── 15m_indicators.parquet
│   │       ├── 1h_indicators.parquet
│   │       └── 4h_indicators.parquet
│   └── patterns/
│       └── BTC-USDT/
│           ├── 5m_patterns.parquet
│           └── ...
├── documentation/              # مستندات
├── reports/                    # گزارش‌های بکتست
│   ├── backtest_report.md
│   ├── equity_curve.csv
│   ├── trades_list.csv
│   ├── equity_curve.png
│   └── performance_summary.png
├── precompute_indicators.py    # محاسبه اندیکاتورها
├── precompute_patterns.py      # شناسایی الگوها
├── precompute_all.py           # اجرای همه محاسبات
└── fast_backtest.py            # موتور بکتست سریع
```

---

## شروع سریع

### 1. پیش‌محاسبه داده‌ها (یک بار)
```bash
cd precomputed_backtest
python precompute_indicators.py
python precompute_patterns.py
```

### 2. اجرای بکتست سریع
```bash
python fast_backtest.py
```

### 3. مشاهده گزارش‌ها
```bash
# گزارش متنی
cat reports/backtest_report.md

# نمودار equity curve
open reports/equity_curve.png

# نمودار عملکرد
open reports/performance_summary.png
```

---

## مستندات بیشتر

- [معماری سیستم](ARCHITECTURE.md)
- [راهنمای استفاده](USAGE.md)
- [کارهای باقی‌مانده](TODO.md)

---

## نتایج بکتست نمونه

| متریک | مقدار |
|--------|-------|
| Win Rate | 51% |
| Profit Factor | 1.52 |
| Max Drawdown | 1.01% |
| Total Return | 27% |
| Total Trades | 1453 |
| Speed | ~8000 candles/sec |

---

## نکات مهم

1. **این سیستم مستقل است** - تغییرات اینجا روی سیستم اصلی تاثیر نمی‌گذارد
2. **تنظیمات محلی** - از `configs/` استفاده می‌شود نه تنظیمات اصلی
3. **بدون وابستگی به talib** - اندیکاتورها با pandas خالص محاسبه می‌شوند
