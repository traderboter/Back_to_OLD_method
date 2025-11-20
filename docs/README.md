# 🤖 ربات معاملاتی کریپتو - سیستم معاملات الگوریتمی پیشرفته

یک سیستم معاملاتی الگوریتمی حرفه‌ای برای بازارهای کریپتو با معماری ماژولار و قابلیت‌های یادگیری تطبیقی.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Private-red.svg)]()
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()

---

## 📋 فهرست مطالب

- [درباره پروژه](#-درباره-پروژه)
- [ویژگی‌های کلیدی](#-ویژگی‌های-کلیدی)
- [معماری سیستم](#-معماری-سیستم)
- [نصب و راه‌اندازی](#-نصب-و-راه‌اندازی)
- [راهنمای سریع](#-راهنمای-سریع)
- [مستندات](#-مستندات)
- [پیکربندی](#-پیکربندی)
- [استراتژی‌های معاملاتی](#-استراتژی‌های-معاملاتی)
- [نکات مهم](#-نکات-مهم)

---

## 🎯 درباره پروژه

این ربات یک سیستم معاملاتی کامل و حرفه‌ای است که با استفاده از تحلیل تکنیکال پیشرفته، یادگیری ماشین و مدیریت ریسک هوشمند، سیگنال‌های معاملاتی تولید و اجرا می‌کند.

### تفاوت‌های کلیدی نسبت به سیستم قدیم:

| ویژگی | سیستم قدیم | سیستم جدید |
|-------|-----------|-----------|
| **معماری** | Monolithic | Modular (10+ Analyzers) |
| **کارایی** | پایه | 60-70% بهبود با Cache System |
| **یادگیری** | محدود | Adaptive Learning System |
| **ایمنی** | اولیه | Circuit Breaker + Correlation Management |
| **نگهداری** | دشوار | آسان با جداسازی مسئولیت‌ها |

---

## ✨ ویژگی‌های کلیدی

### 🔍 تحلیل چند سطحی
- **10 Analyzer مجزا**: Trend, Momentum, Volume, Pattern, SR, Volatility, Harmonic, Channel, Cyclical, HTF
- **تحلیل Multi-Timeframe**: ترکیب هوشمند 4 تایم‌فریم (5m, 15m, 1h, 4h)
- **شناسایی 40+ الگوی کندلی**: با سیستم امتیازدهی دقیق
- **تشخیص الگوهای پیشرفته**: Head & Shoulders, Double Top/Bottom, Triangles, Wedges

### 🧠 هوش مصنوعی و یادگیری
- **Adaptive Learning System**: یادگیری از نتایج معاملات
- **Market Regime Detection**: تشخیص رژیم بازار (Trending/Ranging/Volatile)
- **Pattern Success Tracking**: ردیابی موفقیت هر الگو
- **Dynamic Weight Adjustment**: تنظیم خودکار وزن‌ها

### ⚡ بهینه‌سازی عملکرد
- **Timeframe Score Cache**: کاهش 60-70% محاسبات تکراری
- **Pre-calculated Indicators**: حذف محاسبات اضافی
- **Context Caching**: کش کردن داده‌های تحلیل
- **Delta Updates**: دریافت فقط کندل‌های جدید

### 🛡️ مدیریت ریسک پیشرفته
- **Emergency Circuit Breaker**: توقف خودکار در ضررهای پیاپی
- **Correlation Manager**: جلوگیری از معاملات همبسته
- **Position Sizing**: محاسبه دقیق حجم با توجه به ریسک
- **Multi-TP System**: خروج چندمرحله‌ای با Take Profit
- **Dynamic Stop Loss**: توقف ضرر پویا با ATR

### 📊 مدیریت معاملات
- **Real-time Price Updates**: به‌روزرسانی لحظه‌ای قیمت‌ها
- **Trailing Stop**: توقف ضرر دنباله‌دار
- **Partial Profit Taking**: برداشت سود جزئی
- **Trade Extensions**: توسعه معاملات موفق
- **Emergency Exit**: خروج اضطراری

### 📈 نظارت و گزارش‌دهی
- **Performance Tracking**: ردیابی عملکرد کامل
- **Trade Analytics**: تحلیل دقیق معاملات
- **Pattern Statistics**: آمار الگوها
- **Cache Efficiency**: نمایش کارایی کش
- **Logging System**: سیستم لاگ جامع

---

## 🏗️ معماری سیستم

سیستم با معماری **Modular** و بر اساس اصول **Clean Architecture** طراحی شده است:

```
┌─────────────────────────────────────────────────────┐
│                   Main.py                           │
│              (Entry Point)                          │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│            CryptoTradingBot                         │
│        (Orchestration & Lifecycle)                  │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Market    │ │   Signal    │ │    Trade    │
│    Data     │ │ Generation  │ │  Management │
│   Layer     │ │   Layer     │ │    Layer    │
└─────────────┘ └─────────────┘ └─────────────┘
```

### لایه‌های اصلی:

#### 1️⃣ Market Data Layer
- `ExchangeClient`: اتصال به صرافی (Binance)
- `MarketDataFetcher`: دریافت و کش کردن داده‌ها
- `IndicatorCalculator`: محاسبه اندیکاتورها

#### 2️⃣ Signal Generation Layer
- `SignalOrchestrator`: هماهنگ‌کننده اصلی
- **10 Analyzer**: تحلیل‌گرهای مجزا
- `MarketRegimeDetector`: تشخیص رژیم بازار
- `SignalScorer`: امتیازدهی سیگنال‌ها
- `SignalValidator`: اعتبارسنجی سیگنال‌ها

#### 3️⃣ Trade Management Layer
- `TradeManager`: مدیریت معاملات
- `SignalProcessor`: پردازش سیگنال‌ها
- `PerformanceTracker`: ردیابی عملکرد

#### 4️⃣ Intelligence Layer
- `AdaptiveLearningSystem`: یادگیری تطبیقی
- `CorrelationManager`: مدیریت همبستگی
- `EmergencyCircuitBreaker`: محافظت اضطراری

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها

```bash
Python >= 3.8
pip >= 20.0
```

### نصب وابستگی‌ها

```bash
# نصب پکیج‌های مورد نیاز
pip install -r requirements.txt

# یا نصب دستی پکیج‌های اصلی
pip install ccxt pandas numpy ta-lib pyyaml aiohttp
```

### تنظیمات اولیه

1. **کپی فایل پیکربندی نمونه**:
```bash
cp config.yaml.example config.yaml
```

2. **ویرایش تنظیمات**:
```yaml
# config.yaml
exchange:
  name: "binance"
  api_key: "YOUR_API_KEY"
  api_secret: "YOUR_API_SECRET"
  testnet: true  # برای تست

trading:
  mode: "paper"  # paper/live
  max_positions: 3
  risk_per_trade: 0.02  # 2%
```

3. **تست اتصال**:
```bash
python main.py --config config.yaml --no-trading
```

---

## 🎮 راهنمای سریع

### اجرای ساده (حالت Paper Trading)

```bash
python main.py --config config.yaml --no-trading
```

### اجرا با نمادهای خاص

```bash
python main.py --config config.yaml --symbols BTC/USDT,ETH/USDT
```

### اجرا با فیلتر امتیاز

```bash
python main.py --config config.yaml --min-score 70
```

### بررسی نسخه و کمک

```bash
python main.py --version
python main.py --help
```

### اجرای Backtest

```bash
# Backtest روی داده‌های تاریخی
python backtest/run_backtest.py --symbol BTC/USDT --start 2024-01-01 --end 2024-12-31

# مشاهده نتایج
python backtest/analyze_results.py
```

---

## 📚 مستندات

مستندات جامع در پوشه `docs/` موجود است:

### 📖 مستندات اصلی

| سند | توضیحات | لینک |
|-----|---------|------|
| **معماری سیستم جدید** | توضیحات کامل معماری و مقایسه با سیستم قدیم | [NEW_SYSTEM_ARCHITECTURE_FA.md](docs/NEW_SYSTEM_ARCHITECTURE_FA.md) |
| **راهنمای تولید سیگنال** | راهنمای جامع 3700+ خطی فرآیند تولید سیگنال | [SIGNAL_GENERATION_GUIDE.md](docs/SIGNAL_GENERATION_GUIDE.md) |
| **راهنمای Backtest** | نحوه اجرای بک‌تست و تحلیل نتایج | [BACKTEST_GUIDE.md](BACKTEST_GUIDE.md) |
| **راهنمای Deployment** | آماده‌سازی برای محیط Production | [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md) |

### 📋 مستندات تخصصی

- **[MAIN_PY_WORKFLOW_DOCUMENTATION.md](MAIN_PY_WORKFLOW_DOCUMENTATION.md)**: جریان کامل اجرای main.py
- **[REFACTORING_PROGRESS.md](REFACTORING_PROGRESS.md)**: پیشرفت Refactoring
- **[CACHE_FIX_README.md](CACHE_FIX_README.md)**: سیستم کش و بهینه‌سازی
- **[Pattern Testing Guides](talib-test/)**: راهنماهای تست الگوها

### 🔧 مستندات Troubleshooting

- **[INDICATORS_CODE_REVIEW.md](INDICATORS_CODE_REVIEW.md)**: بررسی کد اندیکاتورها
- **[Mat Hold Fix](docs/MAT_HOLD_FIX_PERSIAN.md)**: رفع مشکل الگوی Mat Hold
- **[Windows Quick Start](WINDOWS_QUICK_START.md)**: راهنمای نصب در Windows

---

## ⚙️ پیکربندی

### ساختار فایل Config.yaml

```yaml
# تنظیمات صرافی
exchange:
  name: "binance"
  api_key: "YOUR_API_KEY"
  api_secret: "YOUR_API_SECRET"
  testnet: true

# نمادها و تایم‌فریم‌ها
symbols:
  active:
    - "BTC/USDT"
    - "ETH/USDT"
    - "BNB/USDT"

  auto_fetch: true
  min_volume_24h: 10000000  # 10M USDT

timeframes:
  primary: "1h"
  secondary: ["5m", "15m", "4h"]

# تنظیمات Signal Generation
signal_generation:
  enabled_analyzers:
    - trend
    - momentum
    - volume
    - pattern
    - support_resistance
    - volatility
    - htf

  min_score: 50
  min_confidence: 0.6

  # تنظیمات کش
  cache:
    enabled: true
    ttl: 300  # 5 minutes

  # سیستم‌های هوشمند
  systems:
    market_regime:
      enabled: true

    adaptive_learning:
      enabled: true
      learning_rate: 0.1

    correlation_manager:
      enabled: true
      max_correlation: 0.7

    circuit_breaker:
      enabled: true
      max_consecutive_losses: 5
      cooldown_minutes: 60

# مدیریت ریسک
risk_management:
  max_positions: 3
  risk_per_trade: 0.02  # 2%
  max_portfolio_risk: 0.06  # 6%

  stop_loss:
    type: "atr"  # atr/percentage/fixed
    atr_multiplier: 2.0
    min_percentage: 0.01  # 1%
    max_percentage: 0.05  # 5%

  take_profit:
    type: "multi"  # single/multi/trailing
    levels:
      - percentage: 0.02  # 2%
        size: 0.3  # 30% position
      - percentage: 0.04  # 4%
        size: 0.4  # 40% position
      - percentage: 0.06  # 6%
        size: 0.3  # 30% position

  trailing_stop:
    enabled: true
    activation_percentage: 0.015  # 1.5%
    trail_percentage: 0.008  # 0.8%

# لاگ و پشتیبان‌گیری
logging:
  level: "INFO"  # DEBUG/INFO/WARNING/ERROR
  file: "logs/trading_bot.log"
  rotation: "daily"
  retention: 30  # days

backup:
  enabled: true
  interval: 3600  # 1 hour
  path: "backups/"
  retention: 7  # days
```

---

## 💡 استراتژی‌های معاملاتی

### استراتژی پیش‌فرض (Multi-Factor)

سیستم از ترکیب 10 analyzer برای تصمیم‌گیری استفاده می‌کند:

1. **Trend Analysis** (وزن: 3x):
   - EMA Crossovers (20/50/200)
   - SuperTrend
   - ADX Strength

2. **Momentum Analysis** (وزن: 2x):
   - MACD Signals
   - RSI Conditions
   - Stochastic Oscillator

3. **Volume Confirmation** (Bonus: +1):
   - Volume Trend
   - OBV Signal
   - Volume Breakout

4. **Pattern Recognition** (وزن: 0.5x):
   - 40+ Candlestick Patterns
   - Chart Patterns
   - Harmonic Patterns

5. **HTF Alignment** (Bonus: +2):
   - Higher Timeframe Trend
   - Multi-TF Confirmation

### استراتژی‌های سفارشی

می‌توانید استراتژی‌های خود را در `strategies/` تعریف کنید:

```python
# strategies/my_strategy.py
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def analyze(self, context):
        # تحلیل سفارشی شما
        return {
            'direction': 'LONG',
            'strength': 0.8,
            'confidence': 0.75
        }
```

---

## 📊 مثال خروجی

```
=== Signal Generated ===
Symbol: BTC/USDT
Timeframe: 1h
Direction: LONG
Entry: 67,500.00
Stop Loss: 66,800.00 (-1.04%)
Take Profit: 69,200.00 (+2.52%)
Risk/Reward: 2.43

Score: 72.5 (Strong)
Confidence: 78%

Detected Patterns:
  ✓ MACD Bullish Crossover (score: 15.2)
  ✓ Hammer Pattern (score: 12.8)
  ✓ RSI Oversold Bounce (score: 8.5)
  ✓ Volume Confirmation (score: 6.0)
  ✓ HTF Alignment (score: 5.5)

Analyzers Contributing:
  • Trend: Bullish (strength: 0.85)
  • Momentum: Bullish (strength: 0.72)
  • Volume: Confirmed
  • Pattern: Strong bullish signals
  • HTF: Aligned with 4h uptrend

Market Regime: Trending
Correlation Safety: 0.92 (Safe)
Circuit Breaker: Inactive
```

---

## ⚠️ نکات مهم

### ⚡ Performance Tips

1. **استفاده از Cache**: همیشه cache را فعال نگه دارید (60-70% بهبود)
2. **محدود کردن نمادها**: شروع با 5-10 نماد برای تست
3. **انتخاب تایم‌فریم مناسب**: 1h برای شروع توصیه می‌شود
4. **Logging سبک**: در production از سطح INFO استفاده کنید

### 🛡️ Safety Tips

1. **شروع با Paper Trading**: حتماً ابتدا در حالت no-trading تست کنید
2. **استفاده از Testnet**: قبل از live trading، روی testnet تست کنید
3. **محدود کردن ریسک**: شروع با 1-2% risk per trade
4. **فعال‌سازی Circuit Breaker**: برای جلوگیری از ضررهای پیاپی
5. **نظارت مداوم**: در روزهای اول به صورت دقیق نظارت کنید

### 📈 Optimization Tips

1. **Backtest**: قبل از استفاده، حتماً backtest کنید
2. **Parameter Tuning**: پارامترها را برای بازار خود تنظیم کنید
3. **Pattern Analysis**: الگوهای موفق را شناسایی و وزن دهی کنید
4. **Regime Adaptation**: از تشخیص رژیم بازار استفاده کنید

### 🔧 Troubleshooting

**مشکل**: سیگنال‌ها تولید نمی‌شوند
- بررسی `min_score` (کاهش دهید برای شروع)
- بررسی فعال بودن analyzers
- بررسی لاگ‌ها برای خطاها

**مشکل**: خطای اتصال به صرافی
- بررسی API Key و Secret
- بررسی محدودیت‌های IP
- بررسی permissions (برای testnet باید جدا باشد)

**مشکل**: کندی سیستم
- فعال کردن cache
- کاهش تعداد نمادها
- افزایش interval پردازش

---

## 🔄 به‌روزرسانی و نگهداری

### نسخه‌های اخیر

- **v2.0.0** (Current): معماری ماژولار جدید + بهینه‌سازی‌های عملکرد
- **v1.5.0**: اضافه شدن Adaptive Learning System
- **v1.0.0**: نسخه اولیه با معماری Monolithic

### Roadmap

- [ ] اضافه کردن ML Model Training
- [ ] Dashboard Web-based
- [ ] Mobile Notifications
- [ ] Multi-Exchange Support
- [ ] Advanced Order Types
- [ ] Portfolio Optimization

---

## 📞 پشتیبانی و ارتباط

- **مستندات**: این Repository
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

## 📄 License

این پروژه Private است و تحت مالکیت خصوصی قرار دارد.

---

## 🙏 تشکر

از تمامی کتابخانه‌های Open Source که استفاده شده:
- **TA-Lib**: Technical Analysis Library
- **CCXT**: Cryptocurrency Exchange Trading Library
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing

---

## 📊 آمار پروژه

```
Lines of Code: 25,000+
Documentation: 7,000+ lines
Analyzers: 10
Indicators: 30+
Patterns: 40+
Test Coverage: 75%
```

---

**⚠️ هشدار**: معاملات کریپتو ریسک بالایی دارند. این ربات صرفاً یک ابزار است و تضمینی برای سود نمی‌دهد. همیشه با احتیاط معامله کنید و فقط پولی را وارد کنید که توانایی از دست دادن آن را دارید.

---

Made with ❤️ by Trading Team
