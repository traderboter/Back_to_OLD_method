# توضیحات جامع سیستم جدید Signal Generation

## تغییرات اصلی نسبت به سیستم قبلی

### 🔄 معماری ماژولار جدید
سیستم قبلی که در یک فایل `signal_generator.py` قرار داشت، حالا به یک سیستم ماژولار با ساختار زیر تبدیل شده:

```
signal_generation/
├── orchestrator.py          # هماهنگ‌کننده اصلی (جایگزین signal_generator.py)
├── analyzers/               # 10 آنالیزگر مجزا
│   ├── trend_analyzer.py
│   ├── momentum_analyzer.py
│   ├── volume_analyzer.py
│   ├── pattern_analyzer.py
│   ├── sr_analyzer.py
│   ├── volatility_analyzer.py
│   ├── harmonic_analyzer.py
│   ├── channel_analyzer.py
│   ├── cyclical_analyzer.py
│   └── htf_analyzer.py
├── systems/                 # سیستم‌های هوشمند
│   ├── market_regime_detector.py
│   ├── adaptive_learning_system.py
│   ├── correlation_manager.py
│   └── emergency_circuit_breaker.py
├── signal_scorer.py         # امتیازدهی سیگنال
├── signal_validator.py      # اعتبارسنجی سیگنال
├── timeframe_score_cache.py # کش کردن امتیازات
└── shared/
    ├── indicator_calculator.py
    └── data_models.py
```

---

## 📖 توضیحات مرحله به مرحله سیستم جدید

---

## مرحله 1: شروع برنامه و بارگذاری تنظیمات
**همانند سیستم قبلی، بدون تغییر اساسی**

وقتی فایل `main.py` اجرا می‌شود:

### 1. **پردازش آرگومان‌های خط فرمان** (`main.py:168-186`)
آرگومان‌های پشتیبانی شده:
   - `--config` (`-c`): مسیر فایل کانفیگ (پیش‌فرض: `config.yaml`)
   - `--symbols`: لیست نمادها با جداکننده کاما (مثال: `BTC/USDT,ETH/USDT`)
   - `--strategy`: انتخاب استراتژی خاص برای معامله
   - `--no-trading`: حالت شبیه‌سازی (بدون معامله واقعی)
   - `--verbose` (`-v`): فعال‌سازی لاگینگ جزئیات (DEBUG)
   - `--backup`: ایجاد نسخه پشتیبان قبل از شروع
   - `--no-watch-config`: غیرفعال کردن نظارت خودکار بر تغییرات config
   - `--update-config`: به‌روزرسانی بخشی از config با JSON (فرمت: `section:json_value`)

### 2. **بارگذاری فایل تنظیمات** (`main.py:189-210`)
تابع `load_config()` فایل تنظیمات را بارگذاری می‌کند:
   - پشتیبانی از `config.yaml` یا `config.json`
   - بررسی وجود فایل و خطاهای سینتکس
   - ثبت زمان آخرین تغییر فایل (`config_last_modified`)
   - افزودن خودکار بخش `config_management` اگر وجود ندارد:
     ```yaml
     config_management:
       auto_reload: true
       check_interval_seconds: 30
       notify_changes: true
       backup_before_update: true
     ```

تنظیمات شامل:
   - تنظیمات صرافی (API keys, symbols, timeframes)
   - پارامترهای signal generation
   - تنظیمات سیستم‌های جدید (regime detector, adaptive learning, correlation manager)
   - تنظیمات لاگینگ، backup، و storage

### 3. **به‌روزرسانی تنظیمات از خط فرمان** (`main.py:211-248`) 🆕
در صورت استفاده از `--update-config`:
   ```bash
   python main.py --update-config 'trading:{"mode":"simulation","max_positions":5}'
   ```
   - پارس JSON value
   - ادغام یا جایگزینی بخش مربوطه در config
   - ذخیره تغییرات در فایل config

### 4. **تنظیم سیستم لاگینگ** (`main.py:251`)
تابع `setup_logging()` سیستم لاگ را راه‌اندازی می‌کند:
   - **Console Handler**: خروجی به stdout
   - **File Handler** (اختیاری): ذخیره در فایل
   - **Rotating File Handler**: چرخش خودکار لاگ‌ها بر اساس حجم
   - سطوح لاگ: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - فرمت قابل تنظیم از config

### 5. **ایجاد پوشه‌های لازم** (`main.py:203-205`)
تابع `ensure_directory()` پوشه‌های مورد نیاز را ایجاد می‌کند:
   - `data/`: ذخیره database و فایل‌های داده
   - `logs/`: فایل‌های لاگ (در صورت فعال بودن file logging)
   - `backups/`: نسخه‌های پشتیبان

### 6. **ایجاد نسخه پشتیبان اولیه** (`main.py:256-286`) - اختیاری
در صورت استفاده از `--backup`:
   - شناسایی فایل‌های مهم:
     - `config.yaml/json`
     - `data/trades.db`
     - `data/adaptive_learning_data.json`
     - `data/correlation_data.json`
     - `data/performance_metrics.json`
   - فشرده‌سازی با `zipfile` به فرمت ZIP
   - ذخیره با نام `manual_backup_YYYYMMDD_HHMMSS.zip`

### 7. **اعمال تغییرات Command-Line روی Config** (`main.py:288-299`)
پارامترهای خط فرمان بر config غلبه می‌کنند:
   - `--no-trading` → `config['trading']['mode'] = 'simulation'`
   - `--symbols` → `config['exchange']['symbols'] = [list]`
   - `--strategy` → تنظیم در مرحله بعد (بعد از ایجاد bot)

**خلاصه**: برنامه آماده می‌شود، تنظیمات بارگذاری و اعمال می‌شوند، و محیط اجرا راه‌اندازی می‌شود.

---

## مرحله 2: ایجاد نمونه ربات (CryptoTradingBot)

در `main.py:304` ربات ایجاد می‌شود: `bot_instance = CryptoTradingBot(args.config)`

### توالی مقداردهی اولیه در `__init__` (`crypto_trading_bot.py:1190-1252`):

### 1. **ذخیره مسیر و بارگذاری Config** (`1197-1198`)
```python
self.config_path = config_path
self.config = self._load_config(config_path)
```

تابع `_load_config()` (`1264-1320`) شامل:
   - ✅ بررسی وجود فایل config
   - ✅ بارگذاری از YAML یا JSON
   - ✅ **اعتبارسنجی بخش‌های الزامی**:
     ```python
     required_sections = ['exchange', 'data_fetching', 'signal_processing',
                          'trading', 'risk_management']
     ```
   - ✅ افزودن بخش‌های پیش‌فرض (`_add_default_config_sections()`)
   - ✅ **اعتبارسنجی عمیق با `validate_config()`** 🆕:
     ```python
     from signal_generation.config_validator import validate_config
     validate_config(config, strict=False)
     ```
   - ⚠️  در صورت خطا: `SystemExit` (خروج از برنامه)

### 2. **ایجاد ConfigurationManager** (`1201`)
```python
self.config_manager = ConfigurationManager(self.config, config_path)
```

مدیریت تنظیمات با قابلیت:
   - نظارت بر تغییرات فایل config
   - بارگذاری مجدد خودکار
   - اعلان تغییرات به شنوندگان

### 3. **مقداردهی اولیه TradingBrain و MLIntegration** (`1203-1204`)
```python
self.trading_brain: Optional[TradingBrainAI] = None
self.ml_integration: Optional[MLSignalIntegration] = None
```

### 4. **تنظیم سیستم لاگینگ** (`1205`)
```python
self._setup_logging()
```

راه‌اندازی مجدد logging با تنظیمات خاص ربات

### 5. **مقداردهی اولیه کامپوننت‌ها روی None** (`1208-1219`)
```python
self.exchange_client = None
self.data_fetcher = None
self.signal_generator = None
self.signal_processor = None
self.trade_manager = None

# اجزای جدید
self.performance_tracker = None
self.backup_manager = None
self.strategy_manager = None
```

**همه کامپوننت‌ها در این مرحله `None` هستند** - راه‌اندازی واقعی در مرحله 3 انجام می‌شود.

### 6. **مدیریت Shutdown و DB Path** (`1222-1224`) 🆕
```python
self._shutdown_requested = asyncio.Event()  # برای توقف تمیز
self.db_path = self.config.get('storage', {}).get('database_path', 'data/trades.db')
self.active_symbols = []  # لیست نمادهای فعال (خالی)
```

### 7. **تولید شناسه یکتا و زمان شروع** (`1227-1230`)
```python
self.instance_id = str(uuid.uuid4())  # شناسه یکتا برای این اجرا
self.start_time = time.time()         # زمان شروع
```

مثال: `instance_id = "a3f2c8d1-4b9e-4a7c-8f3d-9e2b1c5a6d7f"`

### 8. **ساخت دیکشنری Running Status** (`1233-1242`) 🆕
```python
self.running_status = {
    'state': 'initialized',
    'instance_id': self.instance_id,
    'uptime_seconds': 0,
    'start_time': datetime.now().isoformat(),
    'last_status_update': time.time(),
    'components_status': {},           # وضعیت هر کامپوننت
    'system_info': self._get_system_info(),  # اطلاعات سیستم
    'config_changes': []               # تاریخچه تغییرات config
}
```

تابع `_get_system_info()` (`1255-1262`) اطلاعات سیستم را جمع‌آوری می‌کند:
```python
{
    'os': 'Linux',
    'platform': 'Linux-5.15.0-86-generic-x86_64',
    'python_version': '3.11.4',
    'hostname': 'trading-server'
}
```

### 9. **ثبت شنونده برای تغییرات Config** (`1245`)
```python
self.config_manager.register_update_listener(self._handle_config_changes)
```

هندلر `_handle_config_changes()` (`1338-1378`) 🆕:
   - دریافت اعلان تغییرات از ConfigurationManager
   - شناسایی بخش‌های تغییر یافته
   - ثبت در `running_status['config_changes']`
   - **به‌روزرسانی هوشمند کامپوننت‌های مرتبط**:
     - اگر `logging` تغییر کرده → `_setup_logging()` مجدد
     - اگر `exchange` تغییر کرده → `exchange_client.update_config()`
     - اگر `risk_management/trading` تغییر کرده → بررسی معاملات فعال

### 10. **لاگ‌های اطلاعاتی** (`1247-1248`)
```
logger.info(f"ربات معاملاتی ارز دیجیتال با تنظیمات از {config_path} راه‌اندازی شد")
logger.info(f"شناسه نمونه: {self.instance_id}")
```

### 11. **تنظیم متغیر گلوبال** (`1251-1252`)
```python
global bot_instance
bot_instance = self
```

برای دسترسی در signal handlers (SIGINT, SIGTERM)

---

**خلاصه**:
- ✅ Config بارگذاری و اعتبارسنجی کامل می‌شود
- ✅ ConfigurationManager برای مدیریت تغییرات راه‌اندازی می‌شود
- ✅ ساختار کلی ربات با شناسه یکتا و system info ایجاد می‌شود
- ✅ سیستم مدیریت config changes فعال می‌شود
- ⚠️  **کامپوننت‌ها هنوز راه‌اندازی نشده‌اند** (همه `None` هستند)

---

## مرحله 3: راه‌اندازی کامپوننت‌های اصلی (`initialize_components`)

در `crypto_trading_bot.py:1668-2024` متد `initialize_components()` اجرا می‌شود.

### توالی دقیق راه‌اندازی کامپوننت‌ها:

---

### **0. StrategyManager** (`1679-1687`) 🆕

```python
self.strategy_manager = TradingStrategyManager(self.config)
await self.strategy_manager.initialize()
self.running_status['components_status']['strategy_manager'] = 'initialized'
```

**ویژگی‌ها**:
- مدیریت استراتژی‌های قابل تعویض
- اگر فعال باشد، config از استراتژی انتخاب شده می‌آید:
  ```python
  if self.strategy_manager.enabled:
      self.config = self.strategy_manager.get_current_strategy_config()
  ```

---

### **1. TradingBrainAI** (`1691-1703`) 🆕

```python
ai_config = self.config.get('trading_brain_ai', {})
if ai_config.get('enabled', True):
    self.trading_brain = TradingBrainAI(config=self.config)
```

**ویژگی‌ها**:
- هوش مصنوعی معاملاتی
- فقط اگر در config فعال باشد راه‌اندازی می‌شود
- افزودن متد `update_config` به صورت dynamic

---

### **2. ExchangeClient** (`1706-1734`)

```python
from exchange_client import ExchangeClient
self.exchange_client = ExchangeClient(self.config)
await self.exchange_client._init_session()
```

**ویژگی‌ها**:
- اتصال به صرافی
- راه‌اندازی session
- افزودن متد `update_config` برای به‌روزرسانی API keys و WebSocket settings

---

### **3. MarketDataFetcher** (`1737-1766`)

```python
from market_data_fetcher import MarketDataFetcher
self.data_fetcher = MarketDataFetcher(self.config, self.exchange_client)
await self.data_fetcher.initialize()
```

**ویژگی‌ها**:
- دریافت داده‌های بازار
- مدیریت کش (Redis/Memory)
- افزودن متد `update_config` برای به‌روزرسانی:
  - `max_symbols`, `auto_symbols`, `timeframes`
  - `max_concurrent_fetches`
  - تنظیمات کش

---

### **4. IndicatorCalculator** (`1769-1770`) ✨ جدید

```python
self.indicator_calculator = IndicatorCalculator(self.config)
```

**ویژگی‌ها**:
- محاسبه یکباره همه اندیکاتورها
- جلوگیری از محاسبات تکراری
- **30-40% بهبود عملکرد** نسبت به سیستم قبل

---

### **5. SignalGenerator (Orchestrator)** (`1773-1831`) ✨

```python
self.signal_generator = SignalGenerator(
    self.config,
    self.data_fetcher,
    self.indicator_calculator
)
```

**ساختار داخلی SignalGenerator** (در واقع SignalOrchestrator):
```
SignalGenerator/Orchestrator:
├── 11 Analyzer مجزا (10 اصلی + VolumePattern):
│   ├── TrendAnalyzer
│   ├── MomentumAnalyzer
│   ├── VolumeAnalyzer
│   ├── VolumePatternAnalyzer (🆕)
│   ├── PatternAnalyzer
│   ├── SRAnalyzer
│   ├── VolatilityAnalyzer
│   ├── HarmonicAnalyzer
│   ├── ChannelAnalyzer
│   ├── CyclicalAnalyzer
│   └── HTFAnalyzer
│
├── SignalScorer (امتیازدهی)
├── SignalValidator (اعتبارسنجی)
│
├── سیستم‌های هوشمند:
│   ├── MarketRegimeDetector (تشخیص رژیم بازار)
│   ├── AdaptiveLearningSystem (یادگیری تطبیقی)
│   ├── CorrelationManager (مدیریت همبستگی)
│   └── EmergencyCircuitBreaker (توقف اضطراری)
│
└── TimeframeScoreCache (کش امتیازات)
```

**افزودن متد `update_config`** (`1781-1828`):
- به‌روزرسانی `minimum_signal_score`, `timeframes`, `timeframe_weights`
- به‌روزرسانی `pattern_scores`
- به‌روزرسانی `market_regime_detector`
- به‌روزرسانی `adaptive_learning`
- به‌روزرسانی `correlation_manager`
- به‌روزرسانی `circuit_breaker`

---

### **6. MLSignalIntegration** (`1834-1859`) 🆕

```python
ml_integration_config = self.config.get('ml_signal_integration', {})
if ml_integration_config.get('enabled', True) and self.trading_brain:
    self.ml_integration = MLSignalIntegration(
        signal_generator=self.signal_generator,
        trading_brain=self.trading_brain
    )
```

**ویژگی‌ها**:
- یکپارچه‌سازی ML با سیگنال‌ها
- فقط اگر `enabled=True` و `trading_brain` موجود باشد
- افزودن متد `update_config` برای:
  - `enhance_signals`
  - `register_trade_results`
  - `sync_interval_hours`

---

### **7. PerformanceTracker** (`1862-1864`)

```python
self.performance_tracker = BotPerformanceTracker(self.config, self.db_path)
```

**ویژگی‌ها**:
- ردیابی عملکرد ربات
- ثبت metrics در database

---

### **8. BackupManager** (`1867-1869`)

```python
self.backup_manager = BackupManager(self.config)
```

**ویژگی‌ها**:
- پشتیبان‌گیری خودکار
- مدیریت فایل‌های backup

---

### **9. TradeManager** (`1872-1956`)

```python
from trade_manager import TradeManager
self.trade_manager = TradeManager(self.config, self.db_path)
self.trade_manager.initialize_db()
```

**ویژگی‌ها**:
- مدیریت معاملات
- راه‌اندازی database
- افزودن متد `update_config` (`1878-1909`):
  - به‌روزرسانی `mode`, `auto_update_prices`, `price_update_interval`
  - به‌روزرسانی `multi_tp` settings
  - به‌روزرسانی پارامترهای `risk_management`
  - اعمال تغییرات به معاملات فعال
- افزودن متد `update_trade_parameters` (`1912-1946`):
  - به‌روزرسانی trailing stop parameters در معاملات فعال

**ثبت کالبک‌ها** (`1949-1953`):
```python
self.trade_manager.register_price_fetcher(self._price_fetcher, self.data_fetcher)

if self.ml_integration and ml_integration_config.get('register_trade_results', True):
    self.trade_manager.register_trade_result_callback(self.ml_integration.register_trade_result)
```

---

### **10. SignalProcessor** (`1959-2000`)

```python
from signal_processor import SignalProcessor
self.signal_processor = SignalProcessor(
    config=self.config,
    market_data_fetcher=self.data_fetcher,
    orchestrator=self.signal_generator,
    ml_integration=self.ml_integration  # Pass ML integration
)
await self.signal_processor.initialize()
```

**ویژگی‌ها**:
- پردازش دوره‌ای سیگنال‌ها
- افزودن متد `update_config` (`1970-1991`):
  - `auto_forward_signals`
  - `signal_max_age_minutes`
  - `check_incomplete_interval`
  - `ohlcv_limit_per_tf`
  - `use_ensemble_strategy`

**ثبت کالبک TradeManager** (`1996-1997`):
```python
self.signal_processor.register_trade_manager_callback(self.trade_manager.process_signal)
```

---

### **11. تعیین نمادهای فعال** (`2003`)

```python
await self._fetch_active_symbols()
```

**ویژگی‌ها**:
- دریافت لیست نمادها
- تنظیم در `signal_processor`

---

### **12. فعال‌سازی Auto Forward** (`2006-2009`)

```python
if hasattr(self.signal_processor, 'auto_forward_signals'):
    if not self.signal_processor.auto_forward_signals:
        self.signal_processor.auto_forward_signals = True
```

---

### **13. به‌روزرسانی وضعیت نهایی** (`2011-2012`)

```python
self.running_status['state'] = 'ready'
logger.info("تمام اجزا با موفقیت راه‌اندازی شدند")
```

---

### **مدیریت خطا** (`2015-2024`)

در صورت خطا:
- تنظیم `running_status['state'] = 'error'`
- ثبت در `performance_tracker`
- فراخوانی `shutdown()` برای توقف تمیز

---

**خلاصه**:
- ✅ **11 کامپوننت** به ترتیب دقیق راه‌اندازی می‌شوند
- ✅ همه کامپوننت‌ها متد `update_config` دارند (dynamic یا built-in)
- ✅ کالبک‌ها بین کامپوننت‌ها ثبت می‌شوند
- ✅ وضعیت هر کامپوننت در `running_status` ثبت می‌شود
- ✅ مدیریت خطای جامع با shutdown تمیز

---

## مرحله 4: شروع سرویس‌های پس‌زمینه (`start_services`)

در `crypto_trading_bot.py:2164-2219` متد `start_services()` اجرا می‌شود.

**توجه**: تعیین نمادهای فعال (`_fetch_active_symbols`) در **مرحله 3** (انتهای `initialize_components`) انجام شد.

---

### توالی شروع سرویس‌ها:

### **1. تنظیم وضعیت** (`2173`)
```python
self.running_status['state'] = 'starting_services'
```

---

### **2. TradeManager - به‌روزرسانی دوره‌ای قیمت‌ها** (`2176-2181`)

```python
if self.trade_manager.auto_update_prices:
    await self.trade_manager.start_periodic_price_update()
    self.running_status['components_status']['trade_manager'] = 'running'
else:
    logger.info("به‌روزرسانی خودکار قیمت‌ها غیرفعال است.")
    self.running_status['components_status']['trade_manager'] = 'running_no_updates'
```

**ویژگی‌ها**:
- به‌روزرسانی قیمت معاملات فعال (هر 10 ثانیه پیش‌فرض)
- بررسی شرایط Stop Loss و Take Profit
- فقط اگر `auto_update_prices=True` فعال می‌شود

---

### **3. SignalProcessor - پردازش دوره‌ای سیگنال‌ها** (`2184-2185`)

```python
await self.signal_processor.start_periodic_processing()
self.running_status['components_status']['signal_processor'] = 'running'
```

**ویژگی‌ها**:
- پردازش دوره‌ای همه نمادهای فعال
- فاصله زمانی بر اساس تعداد نمادها:
  - کمتر از 20 نماد → هر 3 دقیقه
  - 20-50 نماد → هر 5 دقیقه
  - 50-100 نماد → هر 10 دقیقه
  - بیش از 100 نماد → هر 15 دقیقه
- بررسی سیگنال‌های ناقص (هر 60 ثانیه)

---

### **4. BackupManager - پشتیبان‌گیری خودکار** (`2188-2190`)

```python
if self.backup_manager and self.backup_manager.enabled:
    await self.backup_manager.start_automated_backup()
    self.running_status['components_status']['backup_manager'] = 'running'
```

**ویژگی‌ها**:
- پشتیبان‌گیری دوره‌ای از database و فایل‌های مهم
- فقط اگر `enabled=True` در config فعال می‌شود

---

### **5. Config Watcher - نظارت بر تغییرات تنظیمات** (`2193-2198`) 🆕

```python
config_watch_enabled = self.config.get('config_management', {}).get('auto_reload', True)
if config_watch_enabled:
    self._config_check_task = asyncio.create_task(self._config_watch_loop())
    logger.info("نظارت بر تغییرات تنظیمات آغاز شد")
    self.running_status['components_status']['config_watcher'] = 'running'
```

**حلقه نظارت** (`_config_watch_loop`, خطوط `2221-2237`):
```python
check_interval = self.config.get('config_management', {}).get('check_interval_seconds', 30)

while not self._shutdown_requested.is_set():
    # بررسی تغییرات در فایل تنظیمات
    self.config_manager.check_for_changes()

    # انتظار تا بررسی بعدی
    await asyncio.sleep(check_interval)
```

**ویژگی‌ها**:
- بررسی دوره‌ای تغییرات در فایل config (پیش‌فرض هر 30 ثانیه)
- بارگذاری مجدد خودکار در صورت تغییر
- فراخوانی `_handle_config_changes()` برای به‌روزرسانی کامپوننت‌های مرتبط
- فقط اگر `auto_reload=True` فعال می‌شود

---

### **6. به‌روزرسانی وضعیت نهایی** (`2201-2202`)

```python
self.running_status['state'] = 'running'
logger.info("سرویس‌های پس‌زمینه شروع شدند")
```

---

### **7. ایجاد پشتیبان اولیه** (`2205-2208`)

```python
if self.backup_manager and self.backup_manager.enabled:
    backup_path = await self.backup_manager.create_backup()
    if backup_path:
        logger.info(f"پشتیبان اولیه در {backup_path} ایجاد شد")
```

**ویژگی‌ها**:
- ایجاد نسخه پشتیبان بلافاصله بعد از شروع
- شامل database و فایل‌های داده

---

### **مدیریت خطا** (`2212-2219`)

در صورت خطا:
- تنظیم `running_status['state'] = 'error'`
- ثبت خطا در `performance_tracker`
- Return False

---

**خلاصه**:
- ✅ **4 سرویس اصلی** شروع می‌شوند: TradeManager, SignalProcessor, BackupManager, ConfigWatcher
- ✅ همه سرویس‌ها به صورت async task در پس‌زمینه اجرا می‌شوند
- ✅ وضعیت هر سرویس در `running_status` ثبت می‌شود
- ✅ پشتیبان اولیه بعد از شروع سرویس‌ها ایجاد می‌شود
- ✅ ConfigWatcher امکان hot-reload تنظیمات را فراهم می‌کند

---

## مرحله 5: حلقه اصلی ربات (`run()`)

در `crypto_trading_bot.py:2436-2517` متد `run()` اجرا می‌شود که حلقه اصلی ربات است.

---

### توالی اجرای `run()`:

### **1. تنظیم وضعیت** (`2442`)
```python
self.running_status['state'] = 'initializing'
```

---

### **2. راه‌اندازی کامپوننت‌ها** (`2445-2447`)
```python
if not await self.initialize_components():
    logger.critical("راه‌اندازی اجزا ناموفق بود. ربات نمی‌تواند شروع شود.")
    return False
```

این قبلاً در **مرحله 3** توضیح داده شد.

---

### **3. آموزش مدل‌های هوش مصنوعی** (`2450-2461`) 🆕 (اختیاری)

```python
initial_training_enabled = self.config.get('trading_brain_ai', {}).get('initial_training_enabled', False)

if self.trading_brain and initial_training_enabled and not hasattr(self, '_ai_training_completed'):
    logger.info("آموزش اولیه مدل‌های هوش مصنوعی فعال است...")
    training_success = await self._train_ai_models()
    self._ai_training_completed = True  # فقط یکبار آموزش

    if not training_success:
        logger.warning("آموزش مدل‌های هوش مصنوعی ناموفق بود، اما ربات با قابلیت‌های محدود ادامه می‌دهد")
```

**ویژگی‌ها**:
- آموزش اولیه مدل‌های ML/AI
- فقط یکبار اجرا می‌شود (با flag `_ai_training_completed`)
- فقط اگر `initial_training_enabled=True` در config
- در صورت شکست، ربات بدون AI ادامه می‌دهد

---

### **4. شروع سرویس‌های پس‌زمینه** (`2464-2467`)
```python
if not await self.start_services():
    logger.critical("شروع سرویس‌های پس‌زمینه ناموفق بود. در حال خاموش شدن.")
    await self.shutdown()
    return False
```

این قبلاً در **مرحله 4** توضیح داده شد.

---

### **5. ورود به حلقه اصلی** (`2469-2488`) ✨

```python
logger.info("ربات در حال اجرا است. Ctrl+C برای خروج.")

# حلقه اصلی با به‌روزرسانی وضعیت
while not self._shutdown_requested.is_set():
    # به‌روزرسانی زمان کارکرد
    self.running_status['uptime_seconds'] = int(time.time() - self.start_time)
    self.running_status['last_status_update'] = time.time()

    # بررسی وضعیت کامپوننت‌ها
    await self._check_component_health()

    # به‌روزرسانی دوره‌ای داده‌های بازار (هر 30 دقیقه)
    if self.running_status['uptime_seconds'] % 1800 < 10:
        try:
            await self._fetch_active_symbols()
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی نمادهای فعال: {e}")

    # انتظار برای سیگنال توقف
    await asyncio.sleep(10)
```

**فعالیت‌های حلقه** (هر 10 ثانیه):

#### **الف) به‌روزرسانی uptime** (`2474-2475`)
- محاسبه زمان کارکرد کل ربات
- به‌روزرسانی timestamp آخرین به‌روزرسانی

#### **ب) بررسی سلامت کامپوننت‌ها** (`2478`) 🆕

متد `_check_component_health()` (`2519-2581`) شامل:

1. **بررسی ExchangeClient** (`2523-2539`):
   ```python
   server_time = await self.exchange_client.get_server_time()
   if server_time is None:
       raise ConnectionError("دریافت زمان سرور ناموفق بود")
   ```
   - در صورت خطا: تلاش برای راه‌اندازی مجدد session

2. **بررسی DataFetcher** (`2542-2549`):
   - بررسی `last_fetch_time`
   - هشدار اگر بیش از 10 دقیقه داده دریافت نشده

3. **بررسی SignalProcessor** (`2552-2558`):
   - بررسی `is_running`
   - تلاش برای راه‌اندازی مجدد در صورت توقف

4. **بررسی TradeManager** (`2561-2567`):
   - بررسی `price_update_running`
   - تلاش برای راه‌اندازی مجدد در صورت توقف

5. **بررسی ConfigWatcher** (`2570-2577`):
   - بررسی task status
   - تلاش برای راه‌اندازی مجدد در صورت done شدن

#### **ج) به‌روزرسانی نمادهای فعال** (`2481-2485`) 🆕
- هر 30 دقیقه (1800 ثانیه)
- دریافت مجدد لیست نمادها از صرافی
- به‌روزرسانی همبستگی‌ها

---

### **6. خروج و Shutdown** (`2491-2493`)

```python
logger.info("سیگنال خاموش شدن دریافت شد. آغاز فرآیند خاموش شدن...")
await self.shutdown()
logger.info("ربات با موفقیت خاموش شد.")
```

---

### **مدیریت خطا** (`2496-2517`)

سه نوع خطا مدیریت می‌شود:

1. **`asyncio.CancelledError`** (`2496-2499`):
   - لغو اجرای ربات
   - فراخوانی shutdown

2. **`SystemExit`** (`2500-2506`):
   - خروج اجباری
   - تلاش برای shutdown

3. **`Exception`** (خطای عمومی) (`2507-2517`):
   - ثبت خطا در `performance_tracker`
   - تلاش برای shutdown
   - Return False

---

**خلاصه**:
- ✅ ربات وارد حلقه اصلی می‌شود که هر 10 ثانیه اجرا می‌شود
- ✅ **بررسی خودکار سلامت** کامپوننت‌ها و راه‌اندازی مجدد در صورت نیاز
- ✅ **به‌روزرسانی دوره‌ای** نمادهای فعال (هر 30 دقیقه)
- ✅ **مدیریت خطای جامع** با shutdown تمیز
- ✅ آموزش اولیه AI (اگر فعال باشد)

**توجه**: پردازش واقعی سیگنال‌ها در `SignalProcessor.periodic_processing()` انجام می‌شود که در پس‌زمینه اجرا می‌شود (شروع شده در مرحله 4)

---

## مرحله 6: پردازش یک نماد - دریافت داده‌ها

### 🔄 تفاوت کلیدی: مسیر فراخوانی تغییر کرده است

#### **سیستم قبلی**:
```
SignalProcessor.process_symbol(symbol)
  └─> MarketDataFetcher.get_multi_timeframe_data()
      └─> SignalGenerator.analyze_symbol(symbol, timeframes_data)
          └─> برای هر timeframe:
              SignalGenerator.analyze_single_timeframe()
```

#### **سیستم جدید**:
```
SignalProcessor.process_symbol(symbol)  [signal_processor.py:392]
  │
  ├─> MarketDataFetcher.get_multi_timeframe_data()  [line 425]
  │
  ├─> (گزینه 1) استراتژی Ensemble (اگر use_ensemble=True):  [line 453]
  │     └─> EnsembleStrategy.generate_ensemble_signal(symbol, timeframes_data)
  │
  ├─> (گزینه 2) Orchestrator استاندارد:  [line 458]
  │     └─> SignalOrchestrator.analyze_symbol(symbol, timeframes_data)  [orchestrator.py:851]
  │           │
  │           ├─> (حالت قدیم) Multi-TF Aggregation (اگر use_multi_tf_aggregation=True):  [line 882]
  │           │     └─> برای هر timeframe:
  │           │         └─> _generate_signal_with_context()
  │           │         └─> multi_tf_aggregator.aggregate_timeframe_scores()
  │           │
  │           └─> (حالت جدید) Best Signal Selection (پیش‌فرض):  [line 934]
  │                 └─> برای هر timeframe:
  │                     └─> generate_signal_for_symbol(symbol, timeframe)  [line 250]
  │                           │
  │                           ├── 0. Circuit Breaker Check  [line 272]
  │                           ├── 1. Fetch Data (MarketDataFetcher)  [line 283]
  │                           ├── 1.5. ✨ Check Cache (TimeframeScoreCache)  [line 295]
  │                           ├── 2. Create Context (AnalysisContext)  [line 317]
  │                           ├── 3. ✨ Calculate Indicators (IndicatorCalculator)  [line 326]
  │                           ├── 3.5. ✨ Detect Market Regime (MarketRegimeDetector)  [line 339]
  │                           ├── 4. ✨ Run 11 Analyzers (10 original + VolumePattern)  [line 354]
  │                           ├── 5. Determine Direction  [line 370]
  │                           ├── 6. Calculate Score (SignalScorer)  [line 381]
  │                           ├── 6.5. Build SignalInfo  [line 403]
  │                           ├── 6.7. ✨ Check Correlation (CorrelationManager)  [line 413]
  │                           ├── 7. Validate (SignalValidator)  [line 431]
  │                           └── 8. ✨ Update Cache & Send to TradeManager  [line 458]
  │                 └─> انتخاب بهترین سیگنال (با بالاترین امتیاز)  [line 953]
  │
  └─> ✨ ML Signal Enhancement (اگر فعال باشد):  [signal_processor.py:462]
        └─> ml_integration.enhance_signal(signal, timeframes_data)
              └─> بررسی و غنی‌سازی سیگنال با یادگیری ماشین
              └─> اگر رد شود، سیگنال None می‌شود  [line 470]
```

### جزئیات دریافت داده (در SignalProcessor):
📍 **کد**: `signal_processor.py:425-427`

برای `BTC/USDT`:
1. **درخواست داده** از `MarketDataFetcher.get_multi_timeframe_data()`
2. **دریافت 500 کندل برای هر تایم‌فریم**: `5m`, `15m`, `1h`, `4h`
3. **استفاده از کش**: فقط کندل‌های جدید دریافت می‌شوند (Delta Updates)
4. **خروجی**:
```python
timeframes_data = {
    '5m': DataFrame با 500 کندل 5 دقیقه‌ای,
    '15m': DataFrame با 500 کندل 15 دقیقه‌ای,
    '1h': DataFrame با 500 کندل 1 ساعته,
    '4h': DataFrame با 500 کندل 4 ساعته
}
```

### 🔀 دو حالت در SignalOrchestrator.analyze_symbol()
📍 **کد**: `orchestrator.py:851-963`

#### **حالت 1: Multi-TF Aggregation (OLD SYSTEM)** 📍 `line 882-931`
```python
if self.use_multi_tf_aggregation and self.multi_tf_aggregator:
    # تولید سیگنال برای هر تایم‌فریم
    for timeframe in timeframes_data.keys():
        result = await self._generate_signal_with_context(symbol, timeframe)
        timeframe_signals[timeframe] = result

    # تجمیع امتیازات تایم‌فریم‌ها
    aggregated_signal = self.multi_tf_aggregator.aggregate_timeframe_scores(
        symbol, timeframe_signals
    )
    return aggregated_signal
```

**ویژگی‌ها**:
- تولید سیگنال جداگانه برای **هر** تایم‌فریم
- **تجمیع** امتیازات تمام تایم‌فریم‌ها با وزن‌دهی
- خروجی: یک سیگنال **ترکیبی** با میانگین وزنی
- مناسب برای: استراتژی‌های Multi-TF که نیاز به همسویی تایم‌فریم‌ها دارند

#### **حالت 2: Best Signal Selection (NEW SYSTEM - پیش‌فرض)** 📍 `line 934-959`
```python
else:
    # تولید سیگنال برای هر تایم‌فریم
    signals = []
    for timeframe in timeframes_data.keys():
        signal = await self.generate_signal_for_symbol(symbol, timeframe)
        if signal:
            signals.append(signal)

    # انتخاب بهترین سیگنال
    best_signal = max(signals, key=lambda s: s.score.final_score)
    return best_signal
```

**ویژگی‌ها**:
- تولید سیگنال جداگانه برای **هر** تایم‌فریم
- **انتخاب بهترین** سیگنال (با بالاترین امتیاز)
- خروجی: یک سیگنال از **یک** تایم‌فریم خاص
- مناسب برای: انتخاب قوی‌ترین فرصت معاملاتی

**تفاوت کلیدی**:
- حالت 1 → سیگنال ترکیبی از همه تایم‌فریم‌ها (consensus)
- حالت 2 → بهترین سیگنال از بین تایم‌فریم‌ها (best opportunity)

**خلاصه**: داده‌های 4 تایم‌فریم دریافت و آماده تحلیل شدند.

---

## مرحله 7: تحلیل و تولید سیگنال - تفاوت‌های کلیدی

### ✨ سیستم جدید: Pipeline کامل در `SignalOrchestrator.generate_signal_for_symbol()`

#### **STEP 0: Circuit Breaker Check** (🆕)
```python
if self.circuit_breaker.enabled:
    is_active, reason = self.circuit_breaker.check_if_active()
    if is_active:
        # توقف تولید سیگنال در صورت ضررهای پیاپی
        return None
```

#### **STEP 1: Fetch Market Data**
```python
df = await self._fetch_market_data(symbol, timeframe)  # 500 کندل
```

#### **STEP 1.5: ✨ Check Cache** (🆕)
```python
should_recalc, reason = self.tf_score_cache.should_recalculate(
    symbol, timeframe, df
)

if not should_recalc:
    # استفاده از امتیاز کش شده (کندل جدیدی نیامده)
    cached_signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
    return cached_signal

# کندل جدید آمده → محاسبه مجدد
```

**مزیت**: در صورتی که کندل جدیدی کامل نشده، از امتیاز کش شده استفاده می‌شود و از محاسبات تکراری جلوگیری می‌شود.

#### **STEP 2: Create Analysis Context** (🆕)
```python
context = AnalysisContext(
    symbol=symbol,
    timeframe=timeframe,
    df=df
)
```

کلاس `AnalysisContext` یک container است که:
- داده‌های OHLCV
- نتایج هر analyzer
- metadata (رژیم بازار، اندیکاتورها)
را نگهداری می‌کند.

#### **STEP 3: ✨ Calculate Indicators** (🆕 - جدا شده از analyzers)
```python
self.indicator_calculator.calculate_all(context)
```

همه اندیکاتورها یکباره محاسبه و به `context.df` اضافه می‌شوند:
- SMA, EMA
- ADX, +DI, -DI (🆕)
- RSI, MACD, Stochastic, MFI
- ATR, Bollinger Bands
- OBV, Volume SMA

**⚡ Performance Optimization**: در سیستم قبلی، هر analyzer اندیکاتورهای خود را محاسبه می‌کرد که باعث **محاسبات تکراری** می‌شد. حالا:
- هر اندیکاتور فقط **یکبار** محاسبه می‌شود
- تمام analyzers از اندیکاتورهای از پیش محاسبه شده استفاده می‌کنند
- **30-40% کاهش زمان** در فاز محاسبه اندیکاتورها

#### **STEP 3.5: ✨ Detect Market Regime** (🆕)
```python
if self.regime_detector.enabled:
    regime_info = self.regime_detector.detect_regime(context.df)
    # خروجی: {'regime': 'trending', 'confidence': 0.85}
    context.metadata['regime_info'] = regime_info
```

تشخیص رژیم بازار:
- **Trending**: روند قوی صعودی/نزولی (ADX > 25)
- **Ranging**: محدوده خنثی (ADX < 20)
- **Volatile**: نوسانات شدید

**⚡ Performance Optimization**: MarketRegimeDetector از اندیکاتورهای از پیش محاسبه شده استفاده می‌کند:
- ADX, +DI, -DI
- ATR
- Bollinger Bands
- RSI
- Volume SMA

در سیستم قبلی، این 5 اندیکاتور دوباره محاسبه می‌شدند → **40-50% کاهش زمان** در regime detection

Analyzers می‌توانند بر اساس رژیم، امتیازات را تنظیم کنند.

#### **STEP 4: ✨ Run 11 Analyzers** (🆕 - قبلاً همه در یک جا بودند)
📍 **کد**: `orchestrator.py:354-368` | `_run_analyzers()` → `orchestrator.py:528-535`

**11 Analyzer** شامل: `orchestrator.py:209-248`
1. TrendAnalyzer
2. MomentumAnalyzer
3. VolumeAnalyzer
4. **VolumePatternAnalyzer** (🆕)
5. PatternAnalyzer
6. SRAnalyzer (Support/Resistance)
7. VolatilityAnalyzer
8. HarmonicAnalyzer
9. ChannelAnalyzer
10. CyclicalAnalyzer
11. HTFAnalyzer (Higher Timeframe)

```python
for analyzer_name, analyzer in self.analyzers.items():
    analyzer.analyze(context)
```

هر analyzer نتیجه خود را در `context` ذخیره می‌کند:

1. **TrendAnalyzer**:
```python
context.results['trend'] = {
    'direction': 'bullish',  # bullish/bearish/neutral
    'strength': 0.75,
    'ema_aligned': True
}
```

2. **MomentumAnalyzer**:
```python
context.results['momentum'] = {
    'direction': 'bullish',
    'strength': 0.68,
    'macd_signal': 'bullish',
    'rsi_value': 58.2,
    'rsi_signal': 'neutral',
    'stochastic_signal': 'bullish'
}
```

3. **VolumeAnalyzer**:
```python
context.results['volume'] = {
    'is_confirmed': True,
    'trend': 'increasing',
    'obv_signal': 'bullish'
}
```

4. **PatternAnalyzer**:
```python
context.results['patterns'] = {
    'candlestick_patterns': [
        {'name': 'Hammer', 'direction': 'bullish', 'strength': 0.82, ...},
        {'name': 'Engulfing', 'direction': 'bullish', 'strength': 0.74, ...}
    ],
    'chart_patterns': [
        {'name': 'Double Bottom', 'direction': 'bullish', ...}
    ]
}
```

5. **SRAnalyzer** (Support/Resistance):
```python
context.results['support_resistance'] = {
    'nearest_support': 67200,
    'nearest_resistance': 69800,
    'price_near_support': False,
    'price_near_resistance': False
}
```

6. **VolatilityAnalyzer**:
```python
context.results['volatility'] = {
    'atr_value': 850.5,
    'bb_position': 'middle',
    'recommended_stop_atr': 2.0
}
```

7-10. **HarmonicAnalyzer**, **ChannelAnalyzer**, **CyclicalAnalyzer**, **HTFAnalyzer**: تحلیل‌های پیشرفته‌تر

#### **STEP 5: Determine Direction**
```python
direction = self._determine_direction(context)
# خروجی: 'LONG', 'SHORT', یا None
```

محاسبه امتیاز صعودی/نزولی بر اساس:
- Trend (وزن 3x)
- Momentum (وزن 2x)
- Volume confirmation (+1 bonus)
- Patterns (وزن 0.5x)
- HTF alignment (+2 bonus)

جهت انتخاب می‌شود اگر یکی از امتیازات 1.2x بیشتر از دیگری باشد.

#### **STEP 6: ✨ Calculate Score** (🆕 - سیستم امتیازدهی پیشرفته‌تر)
```python
score = self.signal_scorer.calculate_score(context, direction)
```

`SignalScorer` امتیاز نهایی را محاسبه می‌کند:
```python
score = SignalScore(
    final_score=72.5,          # امتیاز نهایی 0-100
    signal_strength='strong',  # weak/moderate/strong/very_strong
    confidence=0.78,           # اعتماد 0-1
    detected_patterns=[        # الگوهای تشخیص داده شده
        {'name': 'MACD_bullish', 'score': 15.2},
        {'name': 'Hammer', 'score': 12.8},
        {'name': 'RSI_oversold', 'score': 8.5}
    ],
    contributing_analyzers=['trend', 'momentum', 'patterns', 'volume']
)
```

**تفاوت با سیستم قبلی**:
- امتیازات تفکیک شده‌تر
- ردیابی دقیق الگوهای مؤثر
- لاگ کامل الگوها در خروجی

#### **STEP 6.5: Build SignalInfo**
```python
signal = SignalInfo(
    symbol='BTC/USDT',
    timeframe='1h',
    direction='LONG',
    entry_price=67500.0,
    stop_loss=66800.0,     # بر اساس ATR
    take_profit=69200.0,   # بر اساس resistance
    score=score,
    confidence=0.78
)
signal.calculate_risk_reward()  # RR = 2.43
```

#### **STEP 6.7: ✨ Check Correlation** (🆕)
```python
if self.correlation_manager.enabled:
    correlation_factor = self.correlation_manager.get_correlation_safety_factor(
        symbol, direction
    )

    if correlation_factor < 0.7:
        # کاهش امتیاز به دلیل همبستگی بالا با معاملات فعلی
        score.final_score *= correlation_factor
        score.correlation_safety_factor = correlation_factor
```

**مثال**: اگر قبلاً BTC LONG باز است و الان ETH LONG می‌خواهیم باز کنیم، چون همبستگی بالایی دارند، امتیاز کاهش می‌یابد.

#### **STEP 7: Validate**
```python
is_valid, reason = self.signal_validator.validate(signal, context)

if not is_valid:
    # مثلاً: RR < 1.5, امتیاز پایین، یا نزدیک به معامله قبلی
    return None
```

#### **STEP 8: ✨ Update Cache & Send** (🆕)
```python
# ذخیره امتیاز در کش برای استفاده‌های بعدی
self.tf_score_cache.update_cache(symbol, timeframe, signal, df)

# ارسال به TradeManager
if self.send_to_trade_manager:
    await self._send_to_trade_manager(signal)

return signal
```

### خروجی نهایی برای `BTC/USDT 1h`:
```
✅ Valid signal generated for BTC/USDT LONG!
Score: 72.5 (strong, confidence=0.78)
Entry: 67,500 | SL: 66,800 | TP: 69,200
RR: 2.43

Detected Patterns:
  - MACD_bullish (score: 15.2)
  - Hammer (score: 12.8)
  - RSI_oversold (score: 8.5)
  - Volume_confirmation (score: 6.0)
```

### ✨ STEP 9: ML Signal Enhancement (بازگشت به SignalProcessor)
📍 **کد**: `signal_processor.py:462-470`

پس از بازگشت سیگنال از Orchestrator، اگر `ml_signal_integration` فعال باشد:

```python
if self.ml_integration and self.config.get('ml_signal_integration', {}).get('enhance_signals', True):
    signal = self.ml_integration.enhance_signal(signal, timeframes_data)

    if signal:
        # سیگنال با ML غنی‌سازی شد
        logger.debug(f"امتیاز نهایی پس از ML: {signal.score.final_score:.2f}")
    else:
        # سیگنال توسط ML رد شد
        logger.debug(f"سیگنال در فرآیند غنی‌سازی ML رد شد")
        return None
```

**قابلیت‌های ML Enhancement**:
- **پیش‌بینی موفقیت**: بررسی احتمال موفقیت سیگنال بر اساس داده‌های تاریخی
- **تنظیم امتیاز**: کاهش یا افزایش امتیاز بر اساس مدل ML
- **فیلتر کردن**: رد سیگنال‌های با احتمال موفقیت پایین
- **بهینه‌سازی SL/TP**: پیشنهاد سطوح بهتر برای stop loss و take profit

### ✨ گزینه جایگزین: Ensemble Strategy
📍 **کد**: `signal_processor.py:453-455`

اگر `use_ensemble=True` در تنظیمات:
```python
if self.use_ensemble and self.ensemble_strategy:
    signal = await self.ensemble_strategy.generate_ensemble_signal(symbol, timeframes_data)
```

**Ensemble Strategy**:
- ترکیب چندین استراتژی مختلف برای تولید سیگنال واحد
- رای‌گیری (Voting) یا میانگین‌گیری (Averaging) از نتایج
- قابلیت اطمینان بالاتر از طریق تنوع در تحلیل

---

**خلاصه تفاوت‌ها در مرحله 6 و 7**:
1. ✅ **کش کردن امتیازات**: جلوگیری از محاسبات تکراری
2. ✅ **تشخیص رژیم بازار**: تطبیق استراتژی با شرایط
3. ✅ **IndicatorCalculator مجزا**: جلوگیری از محاسبات تکراری
4. ✅ **11 Analyzer مجزا** (10 قدیمی + VolumePattern): کد تمیزتر و قابل نگهداری‌تر
5. ✅ **Correlation Management**: جلوگیری از معاملات همبسته
6. ✅ **لاگ کامل الگوها**: دیباگ آسان‌تر
7. ✅ **ML Signal Enhancement**: غنی‌سازی و فیلتر هوشمند سیگنال‌ها
8. ✅ **Ensemble Strategy**: ترکیب چند استراتژی برای دقت بالاتر
9. ✅ **دو حالت تجمیع**: Multi-TF Aggregation (قدیم) و Best Signal Selection (جدید)

---

## مرحله 8: ارسال سیگنال به TradeManager

### الف) بررسی اعتبار و ارسال (در SignalProcessor)
📍 **کد**: `signal_processor.py:568-635` | `_forward_signal_if_valid()`

```python
await self.trade_manager_callback(signal)
```

**مراحل در `SignalProcessor._forward_signal_if_valid()`**: [line 568]

1. **بررسی callback**: آیا TradeManager ثبت شده؟ [line 585]
2. **بررسی `minimum_score`**: امتیاز >= حداقل مجاز (مثلاً 50)؟ [line 592]
3. **بررسی اعتبار سیگنال** (`check_signal_still_valid`): [line 600]
   - زمان انقضا: کمتر از حداکثر سن مجاز (مثلاً 30 دقیقه)؟
   - قیمت فعلی: هنوز در محدوده معتبر است؟
4. **ارسال به TradeManager**: [line 613]

### ب) پردازش و ایجاد معامله (در TradeManager)
📍 **کد**: `trade_manager.py:533-870` | `process_signal()`

**مراحل کامل در `TradeManager.process_signal()`**:

#### **1. اعتبارسنجی قیمت‌های سیگنال** [line 567]
```python
if not self._validate_signal_prices(signal):
    return None
```
بررسی معتبر بودن `entry_price`, `stop_loss`, `take_profit`

#### **2. بررسی امکان باز کردن معامله جدید** [line 572]
```python
if not self.can_open_new_trade(signal.symbol, signal.direction):
    return None
```
- محدودیت تعداد معاملات همزمان
- محدودیت معاملات همزمان برای یک نماد
- محدودیت جهت معامله (long/short)

#### **3. ✨ بررسی همبستگی پورتفولیو** (🆕) [line 579]
```python
is_allowed, corr_level, corr_symbols, btc_compatibility_info =
    await self.correlation_manager.check_portfolio_correlation(
        signal.symbol, signal.direction, open_trades_list, self.data_fetcher_instance
    )

if not is_allowed:
    # رد سیگنال به دلیل همبستگی بالا
    return None

# تنظیم امتیاز سیگنال بر اساس همبستگی با بیت‌کوین
if btc_compatibility_info and 'correlation_score' in btc_compatibility_info:
    adjusted_score = original_score + (btc_corr_score * 0.5)
    signal.score.final_score = max(10, min(100, adjusted_score))
```

**قابلیت‌های همبستگی**:
- جلوگیری از معاملات با همبستگی بالا (>0.7) با معاملات فعلی
- تحلیل همبستگی با Bitcoin و تنظیم امتیاز
- افزودن تگ‌های مرتبط (btc_correlated, btc_inverse, btc_independent)

#### **4. دریافت کانفیگ تطبیق‌یافته** [line 636]
```python
adapted_config, adapted_risk_config = self._get_adapted_config(signal)
```
تنظیمات بر اساس رژیم بازار یا شرایط خاص

#### **5. محاسبه اندازه پوزیشن** [line 648]
```python
position_size_info = self.calculate_position_size(signal, stop_distance, adapted_risk_config)
quantity = position_size_info.get('position_size', 0.0)
calculated_risk_amount = position_size_info.get('risk_amount', 0.0)
```

#### **6. تولید شناسه معامله** [line 670]
```python
trade_id = self._generate_trade_id(signal.symbol, signal.direction)
```

#### **7. ایجاد شیء Trade با جزئیات کامل** [line 769]
```python
trade = Trade(
    trade_id=trade_id,
    symbol=signal.symbol,
    direction=signal.direction,
    entry_price=signal.entry_price,
    stop_loss=signal.stop_loss,
    take_profit=signal.take_profit,
    quantity=quantity,
    risk_amount=calculated_risk_amount,
    entry_reasons_json=entry_reasons_json_str,  # 🆕 ذخیره دلایل ورود کامل
    strategy_name=strategy_name,
    timeframe=timeframe,
    signal_quality=signal.score.final_score,
    market_state=market_state,
    tags=tags,
    notes=notes,
    signal_patterns_details=signal_patterns_details,  # 🆕 v3.1.0
    signal_pattern_contributions=signal_pattern_contributions,  # 🆕
    signal_score_breakdown=signal_score_breakdown  # 🆕
)
```

#### **8. تنظیم سطوح Multi-TP** [line 802]
```python
self._setup_multi_tp_levels(trade, adapted_risk_config)
```

#### **9. ذخیره در دیتابیس و فعال‌سازی** [line 806]
```python
with self._trades_lock:
    self.active_trades[trade_id] = trade

save_successful = self.save_trade_to_db(trade)
```

#### **10. به‌روزرسانی آمار و تاریخچه بالانس** [line 820]
```python
self._update_stats()
self._save_balance_history(f"معامله جدید باز شد: {trade.symbol} {trade.direction}")
```

#### **11. ارسال اعلان** [line 852]
```python
await self._send_notification(notif_msg)
```
شامل اطلاعات کامل معامله، سطوح TP، و همبستگی با BTC

#### **12. (در حالت Live) ارسال سفارش به صرافی**
در صورت فعال بودن حالت معاملاتی واقعی، سفارش به صرافی ارسال می‌شود.

---

**خلاصه تفاوت‌ها در مرحله 8**:
1. ✅ **بررسی همبستگی پورتفولیو**: جلوگیری از معاملات مرتبط
2. ✅ **تحلیل همبستگی با Bitcoin**: تنظیم امتیاز بر اساس همبستگی
3. ✅ **ذخیره جزئیات الگوها**: entry_reasons_json با جزئیات کامل
4. ✅ **ذخیره breakdown امتیاز**: pattern_contributions و score_breakdown
5. ✅ **کانفیگ تطبیق‌یافته**: تنظیمات بر اساس شرایط بازار
6. ✅ **Multi-TP**: سطوح تارگت چندگانه

**نتیجه**: معامله `BTC/USDT LONG` با شناسه منحصربفرد باز شد.

---

## مرحله 9: مدیریت معامله باز - به‌روزرسانی و خروج
**همانند سیستم قبلی** + ✨ **ثبت نتیجه در سیستم‌های یادگیری**

### الف) به‌روزرسانی دوره‌ای (هر 10 ثانیه):
```python
current_price = await exchange_client.get_ticker_price("BTC/USDT")
trade.update_current_price(current_price)
```

### ب) بررسی شرایط خروج:
- Stop Loss؟
- Take Profit؟
- Trailing Stop؟
- Multi-TP؟

### ✨ ج) ثبت نتیجه در سیستم‌های یادگیری (🆕):

هنگام بسته شدن معامله:
```python
trade_result = TradeResult(
    symbol='BTC/USDT',
    timeframe='1h',
    direction='LONG',
    entry_price=67500,
    exit_price=69200,
    profit_pct=2.52,
    profit_r=2.43,
    exit_reason='take_profit_hit',
    detected_patterns=['MACD_bullish', 'Hammer', 'RSI_oversold'],
    ...
)

# ثبت در SignalOrchestrator
signal_generator.register_trade_result(trade_result)
```

داخل `SignalOrchestrator.register_trade_result()`:

1. **AdaptiveLearningSystem**:
   - یادگیری الگوهای موفق/ناموفق
   - تنظیم خودکار وزن‌ها
```python
adaptive_learning.add_trade_result(trade_result)
# الگوهای Hammer و MACD در LONG موفق بودند → افزایش وزن
```

2. **EmergencyCircuitBreaker**:
   - ردیابی ضررهای پیاپی
   - فعال‌سازی توقف اضطراری در صورت 5 ضرر متوالی
```python
circuit_breaker.add_trade_result(trade_result)
```

**خلاصه**: سیستم از نتایج معاملات یاد می‌گیرد و خود را بهینه می‌کند.

---

## 🎯 خلاصه کامل تفاوت‌های کلیدی

### سیستم قبلی:
```
1️⃣ دریافت 500 کندل × 4 تایم‌فریم
2️⃣ تحلیل تکنیکال در یک کلاس بزرگ (SignalGenerator)
3️⃣ محاسبه امتیاز (در همان کلاس)
4️⃣ تولید سیگنال
5️⃣ ارسال به TradeManager
6️⃣ باز کردن معامله
7️⃣ مدیریت زنده
8️⃣ بستن معامله
9️⃣ ثبت نتیجه (محدود)
```

### سیستم جدید:
```
1️⃣ دریافت 500 کندل × 4 تایم‌فریم
2️⃣ ✨ بررسی کش (اگر کندل جدید نیامده، استفاده از امتیاز کش شده)
3️⃣ ✨ محاسبه یکباره همه اندیکاتورها (IndicatorCalculator)
4️⃣ ✨ تشخیص رژیم بازار (MarketRegimeDetector)
5️⃣ ✨ تحلیل توسط 11 Analyzer مجزا (10 اصلی + VolumePattern):
   - هر analyzer مسئولیت واضح دارد
   - کد تمیزتر و قابل تست‌تر
6️⃣ ✨ امتیازدهی پیشرفته (SignalScorer):
   - ردیابی دقیق الگوهای مؤثر
   - لاگ کامل الگوها
7️⃣ ✨ بررسی همبستگی (CorrelationManager):
   - جلوگیری از معاملات همبسته
   - کاهش ریسک portfolio
8️⃣ اعتبارسنجی (SignalValidator)
9️⃣ ✨ ذخیره در کش برای استفاده‌های بعدی
🔟 ارسال به TradeManager
1️⃣1️⃣ ✨ بررسی Circuit Breaker قبل از باز کردن معامله
1️⃣2️⃣ باز کردن معامله
1️⃣3️⃣ مدیریت زنده
1️⃣4️⃣ بستن معامله
1️⃣5️⃣ ✨ ثبت نتیجه در سیستم‌های یادگیری:
   - AdaptiveLearningSystem
   - EmergencyCircuitBreaker
   - CorrelationManager
```

---

## 📊 مزایای سیستم جدید

### 1. **کارایی بهتر** ⚡
- **کش کردن امتیازات**: کاهش 60-70% محاسبات تکراری
- **محاسبه یکباره اندیکاتورها**: حذف محاسبات تکراری (30-40% بهبود)
- **⚡ Performance Optimizations (جدید)**:
  - Pre-calculated indicators در HTFAnalyzer: 10-15% کاهش زمان
  - Pre-calculated indicators در MarketRegimeDetector: 40-50% کاهش زمان
  - Context caching در Multi-TF Aggregation: 50-70% کاهش زمان
  - **کل سیستم: 20-30% بهبود عملکرد کلی**

### 2. **معماری تمیزتر** 🏗️
- هر analyzer یک مسئولیت
- کد قابل تست و نگهداری
- افزودن analyzer جدید آسان‌تر

### 3. **هوشمندی بیشتر** 🧠
- یادگیری تطبیقی از نتایج
- تشخیص رژیم بازار
- مدیریت همبستگی
- توقف اضطراری خودکار

### 4. **دیباگ آسان‌تر** 🐛
- لاگ کامل الگوهای تشخیص داده شده
- ردیابی دقیق مسیر تصمیم‌گیری
- آمار کامل کش

### 5. **ایمنی بیشتر** 🛡️
- Circuit Breaker: جلوگیری از ضررهای پیاپی
- Correlation Manager: کاهش ریسک portfolio
- اعتبارسنجی چند لایه

---

## 🔄 نمودار جریان کامل سیستم جدید

```
┌─────────────────────────────────────────────────────────────────┐
│                      MAIN.PY - شروع برنامه                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              CryptoTradingBot.__init__()                        │
│  - بارگذاری config                                             │
│  - ایجاد UUID                                                   │
│  - مقداردهی متغیرها                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           initialize_components() - راه‌اندازی                  │
│                                                                 │
│  1. StrategyManager                                             │
│  2. TradingBrainAI                                              │
│  3. ExchangeClient                                              │
│  4. MarketDataFetcher                                           │
│  5. ✨ IndicatorCalculator                                      │
│  6. ✨ SignalOrchestrator:                                      │
│      ├─ 11 Analyzers (10 اصلی + VolumePattern)                 │
│      ├─ SignalScorer                                            │
│      ├─ SignalValidator                                         │
│      ├─ MarketRegimeDetector                                    │
│      ├─ AdaptiveLearningSystem                                  │
│      ├─ CorrelationManager                                      │
│      ├─ EmergencyCircuitBreaker                                 │
│      └─ TimeframeScoreCache                                     │
│  7. MLSignalIntegration                                         │
│  8. SignalProcessor                                             │
│  9. TradeManager                                                │
│  10. PerformanceTracker                                         │
│  11. BackupManager                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   start_services()                              │
│  - شروع TradeManager.periodic_price_update()                   │
│  - شروع SignalProcessor.periodic_processing()                  │
│  - شروع BackupManager                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          SignalProcessor.periodic_processing()                  │
│          حلقه دوره‌ای (هر 3-15 دقیقه بسته به تعداد نمادها)     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│       SignalProcessor.process_all_symbols()                     │
│       برای هر نماد (مثلاً BTC/USDT):                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│      SignalProcessor.process_symbol('BTC/USDT')                 │
│  1. دریافت داده‌های 4 تایم‌فریم                                 │
│  2. فراخوانی Orchestrator.analyze_symbol()                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│   SignalOrchestrator.analyze_symbol('BTC/USDT', timeframes)     │
│   برای هر timeframe (5m, 15m, 1h, 4h):                         │
│     generate_signal_for_symbol('BTC/USDT', '1h')                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  SignalOrchestrator.generate_signal_for_symbol('BTC/USDT','1h') │
│                                                                 │
│  STEP 0: ✨ Circuit Breaker Check                              │
│           └─> آیا ضررهای پیاپی داریم؟                          │
│                                                                 │
│  STEP 1: Fetch 500 Candles                                      │
│           └─> MarketDataFetcher.get_historical_data()          │
│                                                                 │
│  STEP 1.5: ✨ Check Cache                                       │
│           └─> TimeframeScoreCache.should_recalculate()?        │
│           └─> اگر کندل جدید نیامده → return cached_signal     │
│                                                                 │
│  STEP 2: Create AnalysisContext                                 │
│           └─> AnalysisContext(symbol, timeframe, df)           │
│                                                                 │
│  STEP 3: ✨ Calculate Indicators                                │
│           └─> IndicatorCalculator.calculate_all(context)       │
│           └─> محاسبه یکباره: SMA, EMA, RSI, MACD, ATR, BB, ... │
│                                                                 │
│  STEP 3.5: ✨ Detect Market Regime                              │
│           └─> MarketRegimeDetector.detect_regime(df)           │
│           └─> خروجی: trending/ranging/volatile                 │
│                                                                 │
│  STEP 4: ✨ Run 11 Analyzers                                    │
│           ├─> TrendAnalyzer.analyze(context)                   │
│           ├─> MomentumAnalyzer.analyze(context)                │
│           ├─> VolumeAnalyzer.analyze(context)                  │
│           ├─> VolumePatternAnalyzer.analyze(context) (🆕)      │
│           ├─> PatternAnalyzer.analyze(context)                 │
│           ├─> SRAnalyzer.analyze(context)                      │
│           ├─> VolatilityAnalyzer.analyze(context)              │
│           ├─> HarmonicAnalyzer.analyze(context)                │
│           ├─> ChannelAnalyzer.analyze(context)                 │
│           ├─> CyclicalAnalyzer.analyze(context)                │
│           └─> HTFAnalyzer.analyze(context)                     │
│                                                                 │
│  STEP 5: Determine Direction                                    │
│           └─> _determine_direction(context)                    │
│           └─> محاسبه bullish_score vs bearish_score           │
│           └─> خروجی: 'LONG' / 'SHORT' / None                   │
│                                                                 │
│  STEP 6: ✨ Calculate Score                                     │
│           └─> SignalScorer.calculate_score(context, direction) │
│           └─> خروجی: SignalScore(final_score, patterns, ...)   │
│                                                                 │
│  STEP 6.5: Build SignalInfo                                     │
│           └─> SignalInfo(symbol, entry, SL, TP, score, ...)    │
│           └─> محاسبه RR ratio                                  │
│                                                                 │
│  STEP 6.7: ✨ Check Correlation                                 │
│           └─> CorrelationManager.get_correlation_safety_factor()│
│           └─> اگر همبستگی بالا → کاهش امتیاز                   │
│                                                                 │
│  STEP 7: Validate                                               │
│           └─> SignalValidator.validate(signal, context)        │
│           └─> بررسی RR, امتیاز، فاصله از معاملات قبلی، ...    │
│                                                                 │
│  STEP 8: ✨ Update Cache & Register                             │
│           ├─> TimeframeScoreCache.update_cache()               │
│           └─> SignalValidator.register_signal()                │
│                                                                 │
│  STEP 9: Send to TradeManager                                   │
│           └─> _send_to_trade_manager(signal)                   │
│                                                                 │
│  Return: SignalInfo                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              TradeManager.process_signal(signal)                │
│  1. اعتبارسنجی قیمت‌ها                                          │
│  2. بررسی امکان باز کردن معامله جدید                           │
│  3. ✨ بررسی همبستگی پورتفولیو (جدید)                          │
│  4. دریافت کانفیگ تطبیق‌یافته                                   │
│  5. محاسبه اندازه پوزیشن                                        │
│  6. تولید شناسه معامله                                          │
│  7. ایجاد شیء Trade با جزئیات کامل                             │
│  8. تنظیم سطوح Multi-TP                                         │
│  9. ذخیره در DB و فعال‌سازی                                     │
│  10. به‌روزرسانی آمار                                            │
│  11. ارسال اعلان                                                 │
│  12. (در حالت live) ارسال سفارش به صرافی                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│     TradeManager.periodic_price_update() (هر 10 ثانیه)          │
│  1. دریافت قیمت فعلی                                            │
│  2. به‌روزرسانی معامله                                          │
│  3. بررسی شرایط خروج:                                           │
│     ├─ Stop Loss hit?                                           │
│     ├─ Take Profit hit?                                         │
│     ├─ Trailing Stop triggered?                                 │
│     └─ Multi-TP level reached?                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼ (معامله بسته شد)
┌─────────────────────────────────────────────────────────────────┐
│            TradeManager.close_trade(trade, reason)              │
│  1. محاسبه سود/زیان                                            │
│  2. ذخیره نتیجه در DB                                           │
│  3. ✨ ساخت TradeResult                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│   ✨ SignalOrchestrator.register_trade_result(trade_result)     │
│                                                                 │
│  1. AdaptiveLearningSystem.add_trade_result()                   │
│     └─> یادگیری الگوهای موفق/ناموفق                            │
│     └─> تنظیم خودکار وزن‌ها                                    │
│                                                                 │
│  2. EmergencyCircuitBreaker.add_trade_result()                  │
│     └─> ردیابی ضررهای پیاپی                                    │
│     └─> فعال‌سازی توقف اضطراری در صورت نیاز                    │
│                                                                 │
│  3. CorrelationManager.update_performance()                     │
│     └─> به‌روزرسانی ماتریس همبستگی                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📈 آمار کارایی کش (مثال واقعی)

```
=== Timeframe Score Cache Statistics ===
Enabled: True
Total requests: 1,250
Cache hits: 875 (70.0%)
Cache misses: 375 (30.0%)
Hit rate: 70.0%
Average age of cache entries: 2.3 minutes

=== Efficiency Gains ===
Total requests: 1,250
Requests saved: 875 (70.0%)
Estimated time saved: ~43.8 minutes
(assuming 3 seconds per full analysis)
```

---

## 🎓 خلاصه برای کاربر

### وقتی `main.py` را اجرا می‌کنید:

1. **مراحل 1-5 همانند سیستم قبلی**: بارگذاری config، راه‌اندازی کامپوننت‌ها، شروع سرویس‌ها

2. **✨ تفاوت اصلی در تولید سیگنال**:
   - **قبل**: یک کلاس بزرگ همه کار را انجام می‌داد
   - **حالا**:
     - 11 analyzer مجزا (10 اصلی + VolumePattern) برای وضوح و نگهداری بهتر
     - کش کردن امتیازات برای کارایی بهتر (70% کاهش محاسبات)
     - تشخیص رژیم بازار برای تطبیق با شرایط
     - مدیریت همبستگی برای کاهش ریسک
     - یادگیری تطبیقی از نتایج معاملات
     - توقف اضطراری خودکار

3. **باز و بسته کردن معاملات همانند قبل**

4. **✨ بعد از بسته شدن معامله**:
   - نتیجه در سیستم‌های یادگیری ثبت می‌شود
   - وزن‌های الگوها خودکار تنظیم می‌شوند
   - ماتریس همبستگی به‌روزرسانی می‌شود

---

## ⚡ Performance Optimizations (به‌روزرسانی اخیر)

سیستم اخیراً با بهینه‌سازی‌های عملکردی بهبود یافته تا **محاسبات تکراری** حذف شوند:

### 🎯 مشکلات شناسایی و حل شده:

#### 1. **HTFAnalyzer**
- **قبل**: EMA20 و EMA50 دوباره محاسبه می‌شدند
- **بعد**: از ستون‌های `ema_20` و `ema_50` موجود در DataFrame استفاده می‌کند
- **نتیجه**: ⚡ 10-15% کاهش زمان محاسبات HTF

#### 2. **MarketRegimeDetector**
- **قبل**: 5 اندیکاتور (ADX, ATR, BB, RSI, Volume SMA) دوباره محاسبه می‌شدند
- **بعد**: از اندیکاتورهای از پیش محاسبه شده استفاده می‌کند
- **نتیجه**: ⚡ 40-50% کاهش زمان (بزرگترین بهبود!)

#### 3. **ADXIndicator** (جدید)
- **قبل**: ADX در هر جا که نیاز بود محاسبه می‌شد
- **بعد**: یک کلاس ADXIndicator در IndicatorOrchestrator ثبت شد
- **نتیجه**: ⚡ یکبار محاسبه، در همه جا استفاده

#### 4. **Orchestrator Context Caching**
- **قبل**: در Multi-TF Aggregation، context برای هر timeframe دوباره ساخته می‌شد
- **بعد**: Context با TTL=60s کش می‌شود
- **نتیجه**: ⚡ 50-70% کاهش زمان Multi-TF Aggregation

### 📊 نتیجه کلی:
- **کاهش 20-30% زمان کلی** سیستم تولید سیگنال
- **Backward compatible**: fallback برای محاسبه در صورت عدم وجود
- **Debug friendly**: لاگ‌های واضح برای ردیابی cache usage

**مستندات کامل**: برای جزئیات بیشتر به `docs/SIGNAL_GENERATION_GUIDE.md` بخش 7 مراجعه کنید.

---

**نتیجه**: سیستم جدید باهوش‌تر، سریع‌تر، ایمن‌تر و قابل نگهداری‌تر است! 🚀
