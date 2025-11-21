# کارهای باقی‌مانده (TODO)

## اولویت بالا

### 1. بهینه‌سازی منطق سیگنال
- [x] آستانه سیگنال از 60 به 30 کاهش یافت ✓
- [x] امتیازدهی بهتر: الگوها +20، RSI +15، MACD +10، روند +15 ✓
- [x] تشخیص جهت بهتر با دسته‌بندی الگوها ✓
- [ ] بررسی و پیاده‌سازی استراتژی‌های معاملاتی واقعی
- [x] اصلاح position sizing برای نتایج واقعی‌تر (حداکثر 10% بالانس) ✓

### 2. تست صحت نتایج
- [ ] مقایسه نتایج بکتست سریع با بکتست اصلی
- [ ] اطمینان از یکسان بودن محاسبات اندیکاتور
- [ ] اطمینان از یکسان بودن شناسایی الگوها

### 3. مدیریت حافظه
- [ ] پیاده‌سازی لود chunk به chunk برای داده‌های بزرگ
- [ ] بهینه‌سازی نوع داده‌ها (float32 به جای float64)

---

## اولویت متوسط

### 4. اضافه کردن اندیکاتورهای بیشتر
- [x] Ichimoku Cloud ✓
- [ ] Fibonacci Retracement
- [ ] Volume Profile
- [x] VWAP ✓
- [x] Pivot Points ✓
- [x] Williams %R ✓
- [x] CCI (Commodity Channel Index) ✓

### 5. اضافه کردن الگوهای بیشتر
- [x] Spinning Top ✓
- [x] Marubozu ✓
- [x] Inverted Hammer ✓
- [x] Hanging Man ✓
- [x] Tweezer Top/Bottom ✓
- [x] Dragonfly Doji ✓
- [x] Gravestone Doji ✓
- [x] Double Top / Double Bottom (chart pattern) ✓
- [x] Head and Shoulders / Inverse H&S (chart pattern) ✓
- [x] Triangle patterns: Ascending, Descending, Symmetric (chart pattern) ✓
- [x] Flag patterns: Bull Flag, Bear Flag (chart pattern) ✓
- [x] Cup and Handle (chart pattern) ✓
- [x] Wedge patterns: Rising, Falling (chart pattern) ✓

### 6. پشتیبانی از نمادهای بیشتر
- [ ] ETH-USDT
- [ ] BNB-USDT
- [ ] و سایر نمادها

### 7. گزارش‌دهی
- [ ] تولید گزارش PDF
- [x] نمودار equity curve (CSV export) ✓
- [x] آمار معاملات (win rate, profit factor, max drawdown) ✓
- [x] گزارش Markdown ✓
- [x] خروجی CSV معاملات ✓

---

## اولویت پایین

### 8. بهبود عملکرد
- [ ] استفاده از multiprocessing برای محاسبه موازی
- [ ] کش کردن در حافظه با LRU cache
- [ ] استفاده از numba برای محاسبات سنگین

### 9. ابزارهای کمکی
- [ ] اسکریپت آپدیت داده‌ها (فقط کندل‌های جدید)
- [ ] اسکریپت پاکسازی کش
- [ ] اسکریپت بررسی سلامت داده‌ها

### 10. تست‌ها
- [ ] Unit tests برای اندیکاتورها
- [ ] Unit tests برای الگوها
- [ ] Integration tests

---

## انجام شده

- [x] ساختار پوشه‌بندی
- [x] محاسبه اندیکاتورهای پایه (EMA, SMA, RSI, MACD, ATR, BB, Stoch, OBV, ADX)
- [x] شناسایی 11 الگوی کندلی
- [x] موتور بکتست سریع پایه
- [x] استفاده از config محلی
- [x] ذخیره در فرمت Parquet
- [x] پیش‌محاسبه برای 4 تایم‌فریم (5m, 15m, 1h, 4h)
- [x] مستندات
- [x] بهبود منطق سیگنال (آستانه 30، امتیازدهی بهتر)
- [x] تولید معاملات (1453 معامله، 51% win rate)
- [x] سرعت ~8000 کندل/ثانیه
- [x] اصلاح position sizing (نتیجه واقعی: 27% بازده)
- [x] گزارش Markdown با آمار کامل (Profit Factor: 1.52، Max Drawdown: 1.01%)
- [x] خروجی equity curve به CSV
- [x] خروجی لیست معاملات به CSV
- [x] نمودار equity curve با drawdown (matplotlib)
- [x] نمودار خلاصه عملکرد (4 پنل)
- [x] الگوهای چارت: Double Top/Bottom, H&S, Triangle, Flag, Cup&Handle, Wedge

---

## یادداشت‌های فنی

### چرا Parquet؟
- فشرده‌سازی خوب (حجم کمتر)
- لود سریع (columnar format)
- سازگار با pandas

### چرا بدون talib؟
- نصب talib روی بعضی سیستم‌ها مشکل است
- پیاده‌سازی با pandas کافی است
- استقلال از وابستگی‌های خارجی

### محدودیت‌های فعلی
- فقط یک نماد (BTC-USDT)
- منطق سیگنال ساده
- بدون مدیریت ریسک پیشرفته
