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

**نتیجه**: سرعت ~4500 کندل در ثانیه

---

## ساختار پوشه‌ها

```
precomputed_backtest/
├── configs/                    # تنظیمات محلی (کپی از تنظیمات اصلی)
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
│           ├── 15m_patterns.parquet
│           ├── 1h_patterns.parquet
│           └── 4h_patterns.parquet
├── documentation/              # مستندات
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

---

## مستندات بیشتر

- [معماری سیستم](ARCHITECTURE.md)
- [راهنمای استفاده](USAGE.md)
- [کارهای باقی‌مانده](TODO.md)

---

## نکات مهم

1. **این سیستم مستقل است** - تغییرات اینجا روی سیستم اصلی تاثیر نمی‌گذارد
2. **تنظیمات محلی** - از `configs/` استفاده می‌شود نه تنظیمات اصلی
3. **بدون وابستگی به talib** - اندیکاتورها با pandas خالص محاسبه می‌شوند
