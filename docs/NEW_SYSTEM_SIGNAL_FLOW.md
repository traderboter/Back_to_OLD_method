# تحلیل کامل فرآیند تولید سیگنال معاملاتی - سیستم جدید (NEW SYSTEM)

## مقدمه

این سند توضیح می‌دهد که در **سیستم جدید ماژولار** وقتی داده‌های چند تایم‌فریم (5m, 15m, 1h, 4h) برای تحلیل و ایجاد سیگنال معاملاتی دریافت می‌شوند، چه اتفاقاتی می‌افتد.

### تفاوت‌های اساسی با سیستم قدیمی:

| جنبه | سیستم قدیمی (OLD) | سیستم جدید (NEW) |
|------|------------------|------------------|
| **معماری** | Monolithic (یکپارچه) | Modular (ماژولار) |
| **Analyzers** | کد درهم | 11 Analyzer مستقل |
| **Context** | آرگومان‌های مختلف | یک AnalysisContext مشترک |
| **Indicators** | محاسبه پراکنده | IndicatorOrchestrator متمرکز |
| **Caching** | ندارد | TimeframeScoreCache + Indicator Cache |
| **Reusability** | کم | بالا (هر analyzer مستقل) |
| **Testing** | سخت | آسان (unit test هر analyzer) |
| **Performance** | کندتر | سریع‌تر (با cache) |

### فلسفه طراحی سیستم جدید:

✅ **Separation of Concerns**: هر analyzer یک مسئولیت مشخص دارد
✅ **Single Responsibility**: هر کلاس فقط یک کار را انجام می‌دهد
✅ **Dependency Injection**: کامپوننت‌ها از config خارجی استفاده می‌کنند
✅ **Context Sharing**: همه از یک AnalysisContext استفاده می‌کنند
✅ **Cache-First**: جلوگیری از محاسبات تکراری

### معماری کلی (High-Level Architecture):

```
SignalProcessor (ورودی)
    ↓
SignalOrchestrator (هماهنگ‌کننده اصلی)
    ↓
    ├─→ IndicatorCalculator (محاسبه اندیکاتورها)
    ├─→ 11 Analyzers (تحلیل‌گران)
    ├─→ MarketRegimeDetector (تشخیص رژیم بازار)
    ├─→ SignalScorer (امتیازدهی)
    ├─→ MultiTimeframeAggregator (ترکیب TF ها)
    └─→ SignalValidator (اعتبارسنجی)
         ↓
SignalInfo (خروجی)
```

---

## بخش ۱: معماری کلی و نقطه ورود

### 1.1 نقطه شروع: SignalProcessor

**محل:** `signal_processor.py:392-560`

```python
async def process_symbol(self, symbol: str, force_refresh: bool = False, priority: bool = False)
```

**اتفاقات:**

0. **مقدمات و Setup (Initialization):**

   **محل در کد:** `signal_processor.py:405-421`

   **الف) نام‌گذاری AsyncIO Task** (برای Debugging و Monitoring)
   ```python
   # نام‌گذاری تسک برای مدیریت بهتر
   current_task = asyncio.current_task()
   if current_task:
       current_task.set_name(f"signal_processor_{symbol}_{int(time.time())}")
   ```

   **چرا مهم است؟**
   - 🐛 **Debugging:** در صورت خطا یا deadlock، می‌توان task‌ها را شناسایی کرد
   - 📊 **Monitoring:** ابزارهای monitoring می‌توانند task‌ها را track کنند
   - 🔍 **Logging:** در لاگ‌ها نام task نمایش داده می‌شود

   **ب) دریافت Symbol Priority**
   ```python
   symbol_priority = self._get_symbol_priority(symbol)
   is_successful = False
   signal = None
   ```

   **ج) محدودیت همزمانی با Semaphore** (Concurrency Control)
   ```python
   # استفاده از semaphore برای محدودیت پردازش موازی
   async with self.processing_semaphore:
       logger.debug(f"[پردازشگر] پردازش {symbol} شروع شد (اولویت: {priority})")
       # ادامه پردازش...
   ```

   **چرا Semaphore استفاده می‌شود؟**
   - ⚡ **Resource Management:** جلوگیری از مصرف بیش از حد CPU/Memory
   - 🔒 **Rate Limiting:** محدود کردن تعداد پردازش‌های همزمان
   - 🌊 **Backpressure:** جلوگیری از overwhelm شدن سیستم
   - 📉 **API Rate Limits:** کنترل تعداد درخواست‌های همزمان به Exchange

   **مقدار پیش‌فرض Semaphore:**
   ```python
   self.processing_semaphore = asyncio.Semaphore(5)  # حداکثر 5 پردازش همزمان
   ```

   **نکته:** اگر 100 نماد در صف باشند، تنها 5 نماد به طور همزمان پردازش می‌شوند.

1. **دریافت داده‌های چند تایم‌فریمی:**
   ```python
   timeframes_data = await self.market_data_fetcher.get_multi_timeframe_data(
       symbol=symbol,
       timeframes=self.timeframes,  # ['5m', '15m', '1h', '4h']
       force_refresh=force_refresh,
       limit_per_tf=self.ohlcv_limit_per_tf  # 500 کندل
   )
   ```

   **خروجی:**
   ```python
   {
       '5m': DataFrame(500 rows × 6 columns),   # OHLCV data
       '15m': DataFrame(500 rows × 6 columns),
       '1h': DataFrame(500 rows × 6 columns),
       '4h': DataFrame(500 rows × 6 columns)
   }
   ```

2. **بررسی اعتبار داده‌ها:**
   ```python
   valid_timeframes = [
       tf for tf, df in timeframes_data.items()
       if df is not None and not df.empty
   ]

   if not valid_timeframes:
       logger.warning(f"No valid data for {symbol}")

       # ذخیره در incomplete_signals با Thread Safety (Lock)
       with self._signals_lock:
           self.incomplete_signals[symbol] = {
               'reason': 'no_valid_data',
               'timestamp': datetime.now().astimezone()  # استفاده از astimezone() برای timezone صحیح
           }

           # به‌روزرسانی اطلاعات اولویت نماد
           if symbol in self._symbol_priorities:
               self._symbol_priorities[symbol].is_incomplete = True
               self._symbol_priorities[symbol].has_error = True
               self._symbol_priorities[symbol].error_count += 1

       # اعمال استراتژی Backoff برای جلوگیری از سربار
       await self._apply_backoff_strategy(success=False)
       return None
   ```

   **نکات مهم:**
   - 🔒 **Thread Safety:** استفاده از `self._signals_lock` برای جلوگیری از race condition در محیط async
   - 📊 **Symbol Priorities:** ثبت وضعیت نماد (incomplete, error) برای مدیریت اولویت‌ها
   - ⏱️ **Backoff Strategy:** کاهش فشار بر سیستم با تاخیر پس از خطا
   - 🕐 **Timezone:** استفاده از `datetime.now().astimezone()` برای timestamp صحیح

2.5. **بررسی داده‌های ناقص (Partial Data Warning):**

   **محل در کد:** `signal_processor.py:448-450`

   در صورتی که برخی (اما نه همه) تایم‌فریم‌ها داده معتبر داشته باشند:

   ```python
   if len(valid_timeframes) < len(self.timeframes):
       missing_tfs = set(self.timeframes) - set(valid_timeframes)
       logger.debug(f"[پردازشگر] داده‌های ناقص برای {symbol} در تایم‌فریم‌های: {missing_tfs}")
   ```

   **سناریوهای ممکن:**

   | حالت | تایم‌فریم‌های موجود | تایم‌فریم‌های گم‌شده | رفتار سیستم |
   |------|-------------------|---------------------|------------|
   | ✅ داده کامل | ['5m', '15m', '1h', '4h'] | هیچ | ادامه عادی |
   | ⚠️ داده ناقص | ['5m', '15m', '1h'] | ['4h'] | ⚠️ Log + ادامه با داده موجود |
   | ⚠️ داده ناقص | ['5m', '1h'] | ['15m', '4h'] | ⚠️ Log + ادامه با داده موجود |
   | ❌ بدون داده | [] | همه | ❌ خطا (بخش 2) |

   **نکات:**
   - 📊 **Graceful Degradation:** سیستم با داده‌های ناقص هم کار می‌کند
   - ⚠️ **Warning vs Error:** داده ناقص warning است، نه error
   - 🔍 **Debugging:** در لاگ مشخص می‌شود کدام تایم‌فریم‌ها مشکل دارند
   - ⚖️ **Quality Impact:** سیگنال با کیفیت پایین‌تری تولید می‌شود

   **مثال لاگ واقعی:**
   ```
   [DEBUG] [پردازشگر] داده‌های ناقص برای ETHUSDT در تایم‌فریم‌های: {'4h'}
   ```

3. **انتخاب روش تولید سیگنال:**

   سیستم جدید دو روش دارد:

   **روش 1: استفاده از Ensemble Strategy** (استراتژی ترکیبی - در صورت فعال بودن)
   ```python
   if self.use_ensemble and self.ensemble_strategy:
       signal = await self.ensemble_strategy.generate_ensemble_signal(
           symbol, timeframes_data
       )
   ```

   **روش 2: استفاده از Orchestrator** (روش استاندارد - پیش‌فرض)
   ```python
   else:
       signal = await self.orchestrator.analyze_symbol(
           symbol, timeframes_data
       )
   ```

   **تفاوت:**
   - **Ensemble**: از چندین استراتژی مختلف استفاده می‌کند و نتایج را ترکیب می‌کند
   - **Orchestrator**: از یک pipeline استاندارد استفاده می‌کند (همان روشی که توضیح می‌دهیم)

4. **غنی‌سازی سیگنال با Machine Learning (اختیاری):**

   ⚠️ **توجه:** این مرحله فقط در صورتی اجرا می‌شود که:
   - ML Integration در config فعال باشد: `ml_signal_integration.enabled: True`
   - گزینه enhance_signals فعال باشد: `ml_signal_integration.enhance_signals: True`

   **محل در کد:** `signal_processor.py:462-470`

   ```python
   # غنی‌سازی سیگنال توسط MLIntegration (اگر فعال باشد)
   if self.ml_integration and self.config.get('ml_signal_integration', {}).get('enhance_signals', True):
       logger.debug(f"[پردازشگر] غنی‌سازی سیگنال برای {symbol} با ML...")
       signal = self.ml_integration.enhance_signal(signal, timeframes_data)

       if signal:
           # سیگنال غنی‌سازی شد
           logger.debug(
               f"[پردازشگر] سیگنال برای {symbol} توسط ML غنی‌سازی شد. "
               f"امتیاز نهایی: {signal.score.final_score:.2f}"
           )
       else:
           # سیگنال توسط ML رد شد
           logger.debug(f"[پردازشگر] سیگنال برای {symbol} در فرآیند غنی‌سازی ML رد شد")
           return None
   ```

   **اتفاقات در این مرحله:**

   - **ورودی:** سیگنال اولیه تولید شده توسط Orchestrator/Ensemble
   - **پردازش:** مدل ML سیگنال را بررسی و غنی‌سازی می‌کند
   - **خروجی محتمل:**
     - سیگنال غنی‌سازی شده با امتیاز به‌روزشده
     - `None` اگر ML سیگنال را رد کند (سیگنال ضعیف تشخیص داده شود)

   **تنظیمات در config.yaml:**
   ```yaml
   ml_signal_integration:
     enabled: False              # فعال/غیرفعال کردن ML (پیش‌فرض: غیرفعال)
     enhance_signals: True       # تقویت سیگنال‌ها با ML (اگر enabled باشد)
     register_trade_results: True
     sync_interval_hours: 1
   ```

   📌 **نکته مهم:** در حال حاضر ML در config غیرفعال است (`enabled: False`)، بنابراین این مرحله اجرا نمی‌شود.

5. **ذخیره سیگنال و ارسال (اگر معتبر باشد):**

   **محل در کد:** `signal_processor.py:472-493`

   اگر سیگنال معتبر باشد (ML آن را رد نکرده باشد):

   ```python
   # ذخیره سیگنال در تاریخچه با Thread Safety
   process_time = time.time() - start_time
   with self._signals_lock:
       self.signal_history[symbol] = {
           'timestamp': datetime.now().astimezone(),
           'signal': signal,
           'processing_time': process_time
       }

       # به‌روزرسانی وضعیت اولویت نماد (Symbol Priority Management)
       if symbol in self._symbol_priorities:
           self._symbol_priorities[symbol].has_signal = True
           self._symbol_priorities[symbol].has_error = False
           self._symbol_priorities[symbol].is_incomplete = False
           self._symbol_priorities[symbol].last_process_time = time.time()

   # ارسال خودکار سیگنال به TradeManager (اگر فعال باشد)
   if self.auto_forward_signals and self.trade_manager_callback:
       logger.info(
           f"[پردازشگر] تلاش برای ارسال سیگنال {symbol} به مدیریت معاملات. "
           f"امتیاز: {signal.score.final_score:.2f}, جهت: {signal.direction}"
       )
       await self._forward_signal_if_valid(signal)
   ```

   **نکات:**
   - 🔒 **Thread Safety:** تمام عملیات تغییر state در `_signals_lock` انجام می‌شود
   - 📊 **Symbol Priority Tracking:** وضعیت نماد به‌روز می‌شود:
     - `has_signal = True`: سیگنال معتبر تولید شد
     - `has_error = False`: خطایی رخ نداد
     - `is_incomplete = False`: داده‌ها کامل بودند
     - `last_process_time`: زمان آخرین پردازش موفق
   - 📤 **Auto-Forward:** اگر `auto_forward_signals = True` باشد، سیگنال به TradeManager ارسال می‌شود
   - ✅ **Validation:** TradeManager بررسی نهایی اعتبار را انجام می‌دهد (risk management)

6. **مدیریت خطا و Exception Handling:**

   **محل در کد:** `signal_processor.py:523-559`

   سیستم یک ساختار کامل `try-except-finally` دارد:

   ```python
   try:
       # تمام مراحل 1-5
       ...
   except asyncio.CancelledError:
       # در صورت لغو تسک
       logger.debug(f"[پردازشگر] پردازش {symbol} لغو شد")
       raise  # ⚠️ مهم: خطای CancelledError باید دوباره raise شود
   except Exception as e:
       # ثبت خطا با جزئیات کامل
       logger.error(f"[پردازشگر] خطا در پردازش نماد {symbol}: {e}", exc_info=True)

       # ذخیره در incomplete_signals با traceback کامل
       with self._signals_lock:
           self.incomplete_signals[symbol] = {
               'reason': f"خطا: {str(e)}",
               'timestamp': datetime.now().astimezone(),
               'error_traceback': traceback.format_exc()
           }

           # به‌روزرسانی وضعیت خطا در symbol_priorities
           if symbol in self._symbol_priorities:
               self._symbol_priorities[symbol].has_error = True
               self._symbol_priorities[symbol].is_incomplete = True
               self._symbol_priorities[symbol].error_count += 1

       # اعمال استراتژی Backoff
       await self._apply_backoff_strategy(success=False)
       return None
   finally:
       # آمارگیری (همیشه اجرا می‌شود)
       process_time = time.time() - start_time
       if is_successful:
           self.process_stats.success_count += 1
       else:
           self.process_stats.error_count += 1
       self.process_stats.total_time += process_time

       # به‌روزرسانی زمان آخرین پردازش
       if symbol_priority:
           symbol_priority.last_process_time = time.time()
   ```

   **نکات مهم:**
   - ⚠️ **CancelledError:** باید دوباره raise شود تا سیستم async به درستی کار کند
   - 📝 **Error Traceback:** خطاها با `traceback.format_exc()` ذخیره می‌شوند برای debug
   - 📊 **Error Counter:** `error_count` افزایش می‌یابد برای مدیریت اولویت
   - ⏱️ **Backoff Strategy:** پس از خطا، سیستم کمی صبر می‌کند قبل از تلاش بعدی
   - 📈 **Statistics:** آمار همیشه به‌روز می‌شود (success/error count، total time)

7. **حالت‌های مختلف خروجی از process_symbol:**

   | حالت | شرایط | خروجی | آمار |
   |------|-------|-------|------|
   | ✅ **موفق با سیگنال** | داده معتبر + سیگنال تولید شد | `SignalInfo` | `success_count++` |
   | ⚪ **موفق بدون سیگنال** | داده معتبر + سیگنال تولید نشد | `None` | `success_count++` |
   | ❌ **خطا: داده نامعتبر** | `valid_timeframes` خالی است | `None` | `error_count++` |
   | ❌ **خطا: Exception** | هر خطای دیگر | `None` | `error_count++` |
   | 🛑 **لغو شده** | `asyncio.CancelledError` | Exception | - |

   **مثال سناریوهای واقعی:**

   ```python
   # ✅ موفق با سیگنال
   signal = await processor.process_symbol('BTCUSDT')
   # → SignalInfo(direction='LONG', score=75.5)

   # ⚪ موفق بدون سیگنال (شرایط ورود فراهم نیست)
   signal = await processor.process_symbol('ETHUSDT')
   # → None (ولی success_count افزایش می‌یابد)

   # ❌ خطا: داده نامعتبر
   signal = await processor.process_symbol('INVALID_SYMBOL')
   # → None (error_count++)
   # incomplete_signals['INVALID_SYMBOL'] = {'reason': 'no_valid_data', ...}

   # ❌ خطا: Exception
   signal = await processor.process_symbol('BTCUSDT')  # مثلاً API خطا داد
   # → None (error_count++)
   # incomplete_signals['BTCUSDT'] = {'reason': 'خطا: ...', 'error_traceback': '...'}
   ```

8. **استراتژی Backoff (کاهش فشار بر سیستم):**

   **محل در کد:** استفاده در چندین جا از `await self._apply_backoff_strategy(success)`

   **هدف:** پس از خطاهای متوالی، سیستم کمی صبر می‌کند تا از فشار بیش از حد جلوگیری کند.

   **نحوه کارکرد:**
   ```python
   # موفقیت → ریست کردن کانتر خطا
   await self._apply_backoff_strategy(success=True)
   # → error_count = 0، بدون تاخیر

   # خطا → افزایش تاخیر
   await self._apply_backoff_strategy(success=False)
   # → error_count++، تاخیر تصاعدی (exponential backoff)
   ```

   **مثال:**
   ```
   تلاش 1: خطا → صبر 1 ثانیه
   تلاش 2: خطا → صبر 2 ثانیه
   تلاش 3: خطا → صبر 4 ثانیه
   تلاش 4: موفق → ریست (error_count=0)
   ```

   📌 **فایده:** جلوگیری از spam کردن API در شرایط خطا و کاهش هزینه‌های سیستمی

---

### 1.2 ورود به SignalOrchestrator

**محل:** `signal_generation/orchestrator.py:837-949`

```python
async def analyze_symbol(
    self,
    symbol: str,
    timeframes_data: Dict[str, Any]
) -> Optional[SignalInfo]:
```

**مقدمات:**

این متد یک wrapper برای تولید سیگنال multi-timeframe است. کل منطق در یک بلاک `try-except` قرار دارد:

```python
try:
    # Debug log برای tracking
    logger.debug(f"analyze_symbol called for {symbol} with {len(timeframes_data)} timeframes")

    # ادامه پردازش...
except Exception as e:
    logger.error(f"Error in analyze_symbol for {symbol}: {e}", exc_info=True)
    return None
```

**نکات:**
- 🔍 **Logging:** تعداد تایم‌فریم‌های دریافتی log می‌شود
- 🛡️ **Safety:** هر خطایی در کل متد catch می‌شود و `None` برمی‌گردد
- 📝 **Traceback:** با `exc_info=True` جزئیات کامل خطا ثبت می‌شود

---

**گام‌های اصلی:**

#### گام 1: فیلتر کردن تایم‌فریم‌های معتبر

```python
valid_timeframes = {
    tf: df for tf, df in timeframes_data.items()
    if df is not None and not df.empty
}

if not valid_timeframes:
    logger.warning(f"No valid timeframes data for {symbol}")
    return None
```

**مثال:**
```python
# ورودی:
timeframes_data = {
    '5m': DataFrame(500 rows),   # ✓ معتبر
    '15m': None,                 # ✗ داده ندارد
    '1h': DataFrame(500 rows),   # ✓ معتبر
    '4h': DataFrame(500 rows)    # ✓ معتبر
}

# خروجی:
valid_timeframes = {
    '5m': DataFrame(500 rows),
    '1h': DataFrame(500 rows),
    '4h': DataFrame(500 rows)
}
# 15m حذف شد چون None بود
```

#### گام 2: تعیین روش Aggregation

سیستم جدید دو روش برای ترکیب امتیازات چند تایم‌فریمی دارد:

**روش 1: Multi-TF Aggregation (OLD SYSTEM MODE)** ⭐ پیش‌فرض

**محل در کد:** `orchestrator.py:868-917`

```python
if self.use_multi_tf_aggregation and self.multi_tf_aggregator:
    logger.info(f"🔄 Using Multi-TF Aggregation (OLD SYSTEM) for {symbol}")

    # مرحله 1: تولید TimeframeSignal برای هر تایم‌فریم
    timeframe_signals: Dict[str, TimeframeSignal] = {}

    for timeframe in valid_timeframes.keys():
        try:
            # استفاده از _generate_signal_with_context که هم signal و هم context برمی‌گرداند
            result = await self._generate_signal_with_context(symbol, timeframe)
            if result:
                signal, context = result

                # ساخت TimeframeSignal که شامل اطلاعات کامل است
                tf_signal = TimeframeSignal(
                    timeframe=timeframe,
                    direction=signal.direction,
                    score=signal.score,
                    context=context,  # AnalysisContext برای aggregation دقیق‌تر
                    volume_confirmed=context.get_result('volume', {}).get('is_confirmed', False)
                )

                timeframe_signals[timeframe] = tf_signal
                logger.debug(f"  ✓ Generated {timeframe} signal: {signal.direction}, score={signal.score.final_score:.2f}")

        except Exception as e:
            # در صورت خطا، تایم‌فریم را رد کن و به بعدی برو
            logger.error(f"Error generating signal for {symbol} {timeframe}: {e}")
            continue  # ⚠️ ادامه به تایم‌فریم بعدی

    # اگر هیچ سیگنالی تولید نشد
    if not timeframe_signals:
        logger.debug(f"No valid timeframe signals for {symbol}")
        return None

    logger.info(f"  📊 Aggregating {len(timeframe_signals)} timeframe signals for {symbol}")

    # مرحله 2: Aggregate با multi_tf_aggregator
    aggregated_signal = self.multi_tf_aggregator.aggregate_timeframe_scores(
        symbol=symbol,
        timeframe_signals=timeframe_signals
    )

    if aggregated_signal:
        logger.info(
            f"✅ Multi-TF aggregated signal for {symbol}: {aggregated_signal.direction}, "
            f"score={aggregated_signal.score.final_score:.2f}"
        )
        return aggregated_signal
    else:
        logger.info(f"No clear direction from multi-TF aggregation for {symbol}")
        return None
```

**نکات کلیدی:**
- استفاده از `_generate_signal_with_context` برای دریافت همزمان Signal و Context
- ساخت `TimeframeSignal` که شامل:
  - `direction`: جهت سیگنال
  - `score`: امتیازات کامل
  - `context`: تمام داده‌های تحلیلی (برای aggregation دقیق‌تر)
  - `volume_confirmed`: تایید حجم معاملات
- `aggregate_timeframe_scores` امتیازات را با وزن هر TF ترکیب می‌کند
- 🛡️ **Error Resilience:** اگر یک تایم‌فریم خطا دهد، بقیه پردازش می‌شوند (با `continue`)
- 📊 **Partial Aggregation:** حتی با تعداد کمی تایم‌فریم موفق، aggregation انجام می‌شود

---

**روش 2: Best Signal Selection (NEW SYSTEM MODE)**

**محل در کد:** `orchestrator.py:919-945`

```python
else:
    logger.info(f"🎯 Using Best Signal Selection (NEW SYSTEM) for {symbol}")

    # مرحله 1: تولید سیگنال برای هر تایم‌فریم
    signals = []
    for timeframe in valid_timeframes.keys():
        try:
            signal = await self.generate_signal_for_symbol(symbol, timeframe)
            if signal:
                signals.append(signal)
        except Exception as e:
            logger.error(f"Error generating signal for {symbol} {timeframe}: {e}")
            continue

    # اگر هیچ سیگنالی تولید نشد
    if not signals:
        logger.debug(f"No valid signals generated for {symbol}")
        return None

    # مرحله 2: انتخاب بهترین سیگنال بر اساس امتیاز نهایی
    best_signal = max(signals, key=lambda s: s.score.final_score)
    logger.info(
        f"✅ Selected best signal for {symbol}: {best_signal.timeframe} "
        f"with score {best_signal.score.final_score:.2f}"
    )

    return best_signal
```

**نکات کلیدی:**
- از `generate_signal_for_symbol` استفاده می‌کند (بدون نیاز به context)
- سیگنال با `max(signals, key=lambda s: s.score.final_score)` انتخاب می‌شود
- ساده‌تر از روش Aggregation ولی ممکن است اطلاعات سایر TFها را نادیده بگیرد

---

**تنظیمات:**

```python
# در کد orchestrator.py خط 184:
self.use_multi_tf_aggregation = orch_config.get('use_multi_tf_aggregation', True)
```

📌 **پیش‌فرض:** `use_multi_tf_aggregation = True` (روش OLD SYSTEM MODE)

**توجه:** در این مستند روش **Multi-TF Aggregation** را توضیح می‌دهیم چون:
- ✅ با سیستم قدیمی سازگار است
- ✅ نتایج دقیق‌تر می‌دهد (با استفاده از context و وزن‌دهی TFها)
- ✅ پیش‌فرض سیستم است
- ✅ از اطلاعات همه تایم‌فریم‌ها استفاده می‌کند

---

#### نکات اضافی در SignalOrchestrator:

**1. Context Cache (برای جلوگیری از محاسبات تکراری):**

**محل در کد:** `orchestrator.py:196-198`

```python
# Context cache to avoid recalculation in _generate_signal_with_context
self._context_cache: Dict[str, Tuple[AnalysisContext, float]] = {}
self._context_cache_ttl = 60  # 60 seconds TTL
```

**هدف:**
- 💾 **Performance:** جلوگیری از محاسبه مجدد AnalysisContext برای یک نماد در زمان کوتاه
- ⏱️ **TTL:** داده‌های cache بعد از 60 ثانیه منقضی می‌شوند
- 🔑 **Key:** کلید cache ترکیبی از `symbol` و `timeframe` است

**مثال:**
```python
# اولین بار: محاسبه و ذخیره در cache
context1 = await create_context(symbol='BTCUSDT', timeframe='1h')
# cache_key = 'BTCUSDT_1h', timestamp = now()

# بار دوم (در 60 ثانیه بعد): استفاده از cache
context2 = await create_context(symbol='BTCUSDT', timeframe='1h')
# → بدون محاسبه، از cache خوانده می‌شود

# بار سوم (بعد از 60 ثانیه): محاسبه مجدد
context3 = await create_context(symbol='BTCUSDT', timeframe='1h')
# → cache منقضی شده، دوباره محاسبه می‌شود
```

---

### 1.3 تولید سیگنال برای یک تایم‌فریم

**محل:** `signal_generation/orchestrator.py:250-496`

```python
async def generate_signal_for_symbol(
    self,
    symbol: str,
    timeframe: str
) -> Optional[SignalInfo]:
```

این متد **pipeline کامل** برای تولید سیگنال یک تایم‌فریم را اجرا می‌کند:

**ساختار کلی:**

```python
async def generate_signal_for_symbol(self, symbol: str, timeframe: str) -> Optional[SignalInfo]:
    start_time = time.time()

    try:
        logger.info(f"=== Starting signal generation for {symbol} {timeframe} ===")

        # STEP 0-8 (توضیح داده می‌شود)
        ...

    except asyncio.TimeoutError:
        logger.error(f"Timeout processing {symbol}")
        self.stats.errors += 1
        return None

    except Exception as e:
        logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
        self.stats.errors += 1
        return None

    finally:
        # آمارگیری (همیشه اجرا می‌شود)
        elapsed = time.time() - start_time
        self.stats.total_time += elapsed
        self.stats.total_symbols_processed += 1
        self.stats.avg_time_per_symbol = self.stats.total_time / self.stats.total_symbols_processed

        logger.info(f"=== Completed {symbol} in {elapsed:.2f}s (avg: {self.stats.avg_time_per_symbol:.2f}s) ===")
```

**نکات مهم در ساختار:**
- ⏱️ **Timing:** زمان شروع ثبت می‌شود برای محاسبه مدت پردازش
- 🚨 **TimeoutError:** خطای timeout جداگانه handle می‌شود
- 🛡️ **Exception Safety:** هر خطای دیگری با `exc_info=True` ثبت می‌شود
- 📊 **Stats:** در بلاک `finally` آمار همیشه به‌روز می‌شود (حتی در صورت خطا)
- 📈 **Average Tracking:** میانگین زمان پردازش محاسبه می‌شود

---

**Pipeline اصلی:**

```
STEP 0: Circuit Breaker Check ⚠️
   ↓
STEP 1: Fetch Market Data 📊
   ↓
STEP 1.5: Check Cache 💾
   ↓
STEP 2: Create Analysis Context 📝
   ↓
STEP 3: Calculate Indicators 🧮
   ↓
STEP 3.5: Detect Market Regime 🎯
   ↓
STEP 4: Run Analyzers (11×) 🔬
   ↓
STEP 5: Determine Direction ➡️
   ↓
STEP 6: Calculate Score 💯
   ↓
STEP 6.5: Correlation Manager Check 🔗
   ↓
STEP 7: Validate Signal ✅
   ↓
STEP 8: Register & Cache & Send ✨
   ↓
SignalInfo (خروجی)
```

حالا هر گام را با جزئیات بررسی می‌کنیم...

---

### 1.4 STEP 0: بررسی Circuit Breaker (مدار شکن اضطراری)

**محل:** `orchestrator.py:272-281`

```python
# === STEP 0: Circuit Breaker Check ===
if self.circuit_breaker.enabled:
    is_active, reason = self.circuit_breaker.check_if_active()
    if is_active:
        logger.warning(
            f"🚨 Circuit breaker active: {reason}. "
            f"Skipping signal generation for {symbol}."
        )
        self.stats.errors += 1
        return None
```

**هدف:** جلوگیری از تولید سیگنال در شرایط خطرناک

**کلاس:** `EmergencyCircuitBreaker` (محل: `signal_generation/systems/emergency_circuit_breaker.py`)

#### چه زمانی فعال می‌شود؟

**شرط 1: ضررهای متوالی (Consecutive Losses)**

```python
max_consecutive_losses = 3  # پیش‌فرض

# اگر 3 معامله متوالی ضرر داد
if consecutive_losses >= 3:
    circuit_breaker.trigger(reason="3 consecutive losses")
    # توقف برای cool_down_period_minutes (پیش‌فرض: 60 دقیقه)
```

**مثال:**
```
معامله 1: BTCUSDT LONG  → -1.5R ❌
معامله 2: ETHUSDT SHORT → -0.8R ❌
معامله 3: BNBUSDT LONG  → -1.2R ❌
─────────────────────────────────
→ Circuit Breaker فعال شد! 🔴
→ تولید سیگنال متوقف شد برای 60 دقیقه
```

**شرط 2: ضرر کل روزانه (Daily Loss Limit)**

```python
max_daily_losses_r = 5.0  # حداکثر 5R ضرر در روز

# مجموع تمام معاملات روز
daily_loss_r = sum(trade.profit_r for trade in today_trades if trade.profit_r < 0)

if abs(daily_loss_r) >= 5.0:
    circuit_breaker.trigger(reason="Daily loss limit exceeded")
```

**مثال:**
```
09:00 - BTCUSDT LONG  → -2.0R ❌
11:30 - ETHUSDT SHORT → +1.5R ✅ (سود، شمرده نمی‌شود)
14:00 - BNBUSDT LONG  → -1.8R ❌
16:00 - ADAUSDT SHORT → -2.5R ❌
───────────────────────────────
مجموع ضرر: 2.0 + 1.8 + 2.5 = 6.3R
6.3R > 5.0R → Circuit Breaker فعال! 🔴
```

📌 **توجه:** در کد واقعی فقط 2 شرط بالا پیاده‌سازی شده است. شرط‌های دیگری مانند Win Rate در نسخه فعلی وجود ندارد.

---

#### Cool Down Period (دوره خنک‌سازی)

```python
cool_down_period_minutes = 60  # پیش‌فرض

# وقتی Circuit Breaker فعال می‌شود:
trigger_time = datetime.now()
resume_time = trigger_time + timedelta(minutes=60)

# تا 60 دقیقه بعد:
# - تولید سیگنال متوقف است
# - بعد از 60 دقیقه خودکار از سر گرفته می‌شود
```

**لاگ نمونه:**
```
[2025-01-15 14:30:00] WARNING: 🚨 CIRCUIT BREAKER TRIGGERED
Reason: Hit 3 consecutive losses
Trading paused until: 15:30:00

... 60 minutes later ...

[2025-01-15 15:30:00] INFO: ✅ Circuit breaker cool-down complete
Trading resumed. Consecutive loss counter reset to 0.
```

#### تنظیمات (config):

⚠️ **نکته مهم:** در نسخه فعلی `config.yaml`، بخش `systems.circuit_breaker` وجود **ندارد**.

**کنترل فعلی در config:**
```yaml
# در بخش validator (خط 314):
signal_generation_v2:
  validator:
    filters:
      check_circuit_breaker: True    # فعال/غیرفعال کردن بررسی circuit breaker
```

**مقادیر پیش‌فرض استفاده شده توسط سیستم:**

کلاس `EmergencyCircuitBreaker` از مقادیر پیش‌فرض زیر استفاده می‌کند:

```python
# محل: signal_generation/systems/emergency_circuit_breaker.py:22-29
self.enabled = True                           # همیشه فعال (اگر check_circuit_breaker=True)
self.max_consecutive_losses = 3               # حداکثر ضرر متوالی
self.max_daily_losses_r = 5.0                 # حداکثر ضرر روزانه (R)
self.cool_down_period_minutes = 60            # مدت توقف (دقیقه)
self.reset_period_hours = 24                  # بازنشانی آمار روزانه
```

**📌 توجه:** شرط `min_win_rate` در کد فعلی پیاده‌سازی **نشده است** (فقط 2 شرط فعال است).

**برای تغییر مقادیر پیش‌فرض:**

اگر می‌خواهید مقادیر را تغییر دهید، باید بخش زیر را به `config.yaml` اضافه کنید:

```yaml
systems:
  circuit_breaker:
    enabled: True
    max_consecutive_losses: 3        # تعداد ضرر متوالی
    max_daily_losses_r: 5.0          # حداکثر ضرر روزانه به R
    cool_down_period_minutes: 60     # زمان توقف
    reset_period_hours: 24           # بازنشانی آمار
```

#### چرا Circuit Breaker مهم است؟

✅ **محافظت از سرمایه:**
- جلوگیری از ضررهای متوالی و پی در پی
- توقف خودکار در شرایط بحرانی

✅ **مدیریت روانشناسی:**
- فرصت برای تحلیل مجدد
- جلوگیری از معاملات احساسی

✅ **حفظ الگوریتم:**
- جلوگیری از آسیب به مدل‌های یادگیری با داده‌های بد
- فرصت برای بازنگری پارامترها

---

**✅ بخش 1 تمام شد!**

**مراحل بعدی:**
- بخش 2: محاسبه اندیکاتورها (IndicatorCalculator + IndicatorOrchestrator)
- بخش 3: تحلیل تایم‌فریم (11 Analyzer)
- بخش 4: سیستم‌های پیشرفته
- بخش 5: امتیازدهی
- بخش 6: ترکیب Multi-TF
- بخش 7: اعتبارسنجی

آیا ادامه بدهم؟ بخش بعدی (محاسبه اندیکاتورها) را بنویسم؟

---

## بخش ۲: دریافت داده و محاسبه اندیکاتورها

### 2.1 STEP 1: دریافت داده‌های بازار (Fetch Market Data)

**محل:** `orchestrator.py:497-515`

```python
async def _fetch_market_data(self, symbol: str, timeframe: str):
    """Fetch market data using MarketDataFetcher."""
    try:
        df = await self.market_data_fetcher.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=self.ohlcv_limit  # پیش‌فرض: 500 کندل
        )

        if df is None or len(df) < 200:
            logger.warning(f"Insufficient data for {symbol}: {len(df) if df is not None else 0} candles")
            return None

        return df

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None
```

**ورودی:**
- `symbol`: نماد (مثلاً 'BTCUSDT')
- `timeframe`: تایم‌فریم (مثلاً '1h')
- `limit`: تعداد کندل (پیش‌فرض: 500)

**خروجی (DataFrame):**
```python
# شکل DataFrame:
        open      high       low     close    volume                  timestamp
0    50000.0   50500.0   49800.0   50200.0   1234.56   2025-01-15 00:00:00
1    50200.0   50800.0   50100.0   50600.0   1456.78   2025-01-15 01:00:00
2    50600.0   51000.0   50400.0   50700.0   1678.90   2025-01-15 02:00:00
...
499  52000.0   52500.0   51800.0   52200.0   1890.12   2025-01-15 20:00:00

# DataFrame(500 rows × 6 columns)
```

**بررسی‌ها:**
1. **حداقل تعداد کندل:** باید حداقل **200 کندل** وجود داشته باشد
   - چرا 200؟ چون برخی اندیکاتورها (مثل EMA100) نیاز به داده بیشتری دارند
   - اگر کمتر از 200 باشد → `None` برمی‌گرداند

2. **اعتبار داده:**
   - اگر `df is None` → خطا در دریافت
   - اگر `df.empty` → داده‌ای وجود ندارد

**مثال:**
```python
# موفق:
df = await _fetch_market_data('BTCUSDT', '1h')
# → DataFrame(500 rows)

# ناموفق (داده کم):
df = await _fetch_market_data('NEWCOIN', '1h')
# → DataFrame(150 rows) → return None (کمتر از 200)
```

---

### 2.2 STEP 1.5: بررسی Cache (TimeframeScoreCache)

**محل:** `orchestrator.py:296-315`

**هدف:** جلوگیری از محاسبات تکراری وقتی کندل جدید نیامده است.

```python
# === STEP 1.5: Check Cache ===
should_recalc, reason = self.tf_score_cache.should_recalculate(
    symbol, timeframe, df
)

if not should_recalc:
    # کش معتبر است - استفاده از امتیاز کش شده
    logger.info(
        f"  💾 Using CACHED score for {symbol} {timeframe} "
        f"(reason: {reason}) - Skipping recalculation"
    )
    cached_signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
    if cached_signal:
        return cached_signal

# کندل جدید آمده یا کش invalid است - محاسبه مجدد
logger.info(
    f"  🔄 RECALCULATING score for {symbol} {timeframe} "
    f"(reason: {reason})"
)
```

#### چگونه کار می‌کند؟

**کلاس:** `TimeframeScoreCache` (محل: `signal_generation/timeframe_score_cache.py`)

**3 حالت:**

**حالت 1: کش معتبر است ✅**
```python
# اگر:
# 1. سیگنال قبلی وجود دارد
# 2. آخرین timestamp کندل تغییر نکرده
# 3. TTL منقضی نشده (پیش‌فرض: 5 دقیقه)

should_recalc = False
reason = "No new candle, cache is valid"

# نتیجه: از cache استفاده می‌کند، محاسبه نمی‌کند
```

**مثال:**
```python
# 14:00 - محاسبه اول:
signal_1 = generate_signal('BTCUSDT', '1h')  # محاسبه کامل
# → ذخیره در cache با timestamp: 2025-01-15 14:00:00

# 14:02 - درخواست دوم (همان کندل):
signal_2 = generate_signal('BTCUSDT', '1h')  # 💾 از cache
# → last_candle_time هنوز 14:00:00 است
# → should_recalc = False
# → return cached_signal (بدون محاسبه!)
```

**حالت 2: کندل جدید آمده 🔄**
```python
# اگر:
# 1. timestamp آخرین کندل تغییر کرده
# 2. یک کندل جدید اضافه شده

should_recalc = True
reason = "New candle detected"

# نتیجه: محاسبه مجدد انجام می‌شود
```

**مثال:**
```python
# 14:00 - محاسبه اول:
signal_1 = generate_signal('BTCUSDT', '1h')
# → cache: last_timestamp = 2025-01-15 14:00:00

# 15:05 - درخواست دوم (کندل جدید):
signal_2 = generate_signal('BTCUSDT', '1h')
# → current timestamp = 2025-01-15 15:00:00 (جدید!)
# → should_recalc = True
# → محاسبه کامل از اول
```

**حالت 3: کش وجود ندارد 🆕**
```python
# اگر:
# 1. اولین بار است که این symbol+timeframe محاسبه می‌شود
# 2. یا cache منقضی شده (TTL گذشته)

should_recalc = True
reason = "No cache found" یا "Cache expired"

# نتیجه: محاسبه کامل
```

#### تنظیمات Cache:

```python
"cache": {
    "enabled": True,                    # فعال/غیرفعال
    "ttl_minutes": 5,                   # مدت اعتبار (5 دقیقه)
    "max_cache_size": 1000,             # حداکثر تعداد آیتم‌های cache
    "check_new_candle": True            # بررسی کندل جدید
}
```

#### مزایای Cache:

✅ **صرفه‌جویی محاسباتی:**
```
بدون cache:
- هر درخواست = محاسبه کامل (8 indicator + 11 analyzer)
- 100 درخواست = 100 × محاسبات کامل

با cache:
- اولین درخواست = محاسبه کامل
- 99 درخواست بعدی = از cache (تا کندل جدید بیاید)
- صرفه‌جویی: ~99% در همان کندل!
```

✅ **سرعت بالا:**
```
محاسبه کامل: ~2-5 ثانیه
استفاده از cache: ~0.001 ثانیه (1000× سریع‌تر!)
```

✅ **کاهش بار API:**
```
بدون cache: هر بار fetch + calculate
با cache: فقط یکبار تا کندل جدید
```

---

### 2.3 STEP 2: ساخت Analysis Context

**محل:** `orchestrator.py:318-324`

```python
# === STEP 2: Create Analysis Context ===
logger.info(f"[2/7] Creating context for {symbol}")

context = AnalysisContext(
    symbol=symbol,
    timeframe=timeframe,
    df=df
)
```

**کلاس:** `AnalysisContext` (محل: `signal_generation/context.py`)

#### چیست AnalysisContext؟

**یک "حافظه مشترک"** بین همه کامپوننت‌های تحلیل.

**ساختار:**
```python
class AnalysisContext:
    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame):
        self.symbol = symbol           # نماد (مثلاً 'BTCUSDT')
        self.timeframe = timeframe     # تایم‌فریم (مثلاً '1h')
        self.df = df.copy()            # کپی از DataFrame

        # نتایج تحلیل‌گران (خالی در ابتدا)
        self.results: Dict[str, Any] = {}

        # متادیتا
        self.metadata: Dict[str, Any] = {
            'created_at': datetime.now(),
            'symbol': symbol,
            'timeframe': timeframe,
            'rows': len(df),
            'indicators_calculated': False
        }

        # آمار
        self._stats = {
            'analyzers_run': 0,
            'analyzers_failed': 0
        }
```

**مثال استفاده:**

```python
# ساخت context:
context = AnalysisContext('BTCUSDT', '1h', df)

# ─── بعداً، IndicatorCalculator ───
context.df['ema_20'] = ...  # اضافه کردن ستون EMA
context.df['rsi'] = ...     # اضافه کردن ستون RSI
context.metadata['indicators_calculated'] = True

# ─── بعداً، TrendAnalyzer ───
trend_result = {
    'direction': 'bullish',
    'strength': 3,
    'phase': 'mature'
}
context.add_result('trend', trend_result)  # ذخیره نتیجه

# ─── بعداً، MomentumAnalyzer ───
# استفاده از نتیجه قبلی:
trend = context.get_result('trend')  # خواندن نتیجه TrendAnalyzer
if trend['direction'] == 'bullish':
    # ...

momentum_result = {
    'direction': 'bullish',
    'strength': 2
}
context.add_result('momentum', momentum_result)

# ─── در انتها ───
# context حاوی همه نتایج است:
print(context.results)
# {
#     'trend': {'direction': 'bullish', 'strength': 3, ...},
#     'momentum': {'direction': 'bullish', 'strength': 2, ...},
#     'volume': {...},
#     'patterns': {...},
#     ...
# }
```

#### چرا AnalysisContext مهم است؟

**قبلاً (سیستم قدیمی):**
```python
# هر analyzer آرگومان‌های جداگانه می‌گرفت:
def analyze_trend(df, symbol, timeframe, config):
    ...

def analyze_momentum(df, symbol, timeframe, config, trend_result):
    ...

def analyze_patterns(df, symbol, timeframe, config, trend_result, momentum_result):
    ...

# مشکلات:
# ❌ آرگومان‌های زیاد
# ❌ سخت برای test
# ❌ مدیریت data sharing سخت
```

**حالا (سیستم جدید):**
```python
# همه از یک context استفاده می‌کنند:
def analyze(self, context: AnalysisContext):
    # دسترسی به همه چیز از context:
    df = context.df
    symbol = context.symbol
    previous_results = context.get_result('trend')

    # ذخیره نتیجه:
    context.add_result('momentum', result)

# مزایا:
# ✅ تمیز و خوانا
# ✅ آسان برای test
# ✅ data sharing راحت
# ✅ extensible (می‌تونیم metadata اضافه کنیم)
```

---

### 2.4 STEP 3: محاسبه اندیکاتورها (Calculate Indicators)

**محل:** `orchestrator.py:327-336`

```python
# === STEP 3: Calculate Indicators ===
logger.info(f"[3/7] Calculating indicators for {symbol}")

success = self._calculate_indicators(context)

if not success:
    logger.error(f"Failed to calculate indicators for {symbol}")
    self.stats.errors += 1
    return None

logger.info(f"  ✓ Indicators calculated")
```

**متد داخلی:**
```python
def _calculate_indicators(self, context: AnalysisContext) -> bool:
    """Calculate indicators using IndicatorCalculator."""
    try:
        # IndicatorCalculator.calculate_all() modifies context.df in-place
        self.indicator_calculator.calculate_all(context)
        return True

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return False
```

#### چه اتفاقی می‌افتد؟

```python
# قبل از calculate_all():
context.df columns: ['open', 'high', 'low', 'close', 'volume', 'timestamp']
# 6 ستون پایه

# بعد از calculate_all():
context.df columns: [
    # ستون‌های پایه:
    'open', 'high', 'low', 'close', 'volume', 'timestamp',

    # Moving Averages (Trend):
    'ema_20', 'ema_50', 'ema_100',
    'sma_20', 'sma_50', 'sma_200',

    # Momentum:
    'rsi',                           # RSI
    'macd', 'macd_signal', 'macd_hist',  # MACD
    'stoch_k', 'stoch_d',           # Stochastic
    'slowk', 'slowd',               # Stochastic (backward compatibility)

    # Volatility:
    'atr',                          # ATR
    'bb_upper', 'bb_middle', 'bb_lower',  # Bollinger Bands

    # Volume:
    'obv',                          # OBV
    'volume_sma',                   # Volume SMA (20-period)

    # Other:
    'adx', 'plus_di', 'minus_di'   # ADX
]
# حدود 23 ستون
```

---

### 2.5 معماری محاسبه اندیکاتورها

**سلسله مراتب:**

```
IndicatorCalculator (wrapper)
    ↓
IndicatorOrchestrator (هماهنگ‌کننده)
    ↓
    ├─→ Trend Indicators
    │   ├─→ EMAIndicator
    │   ├─→ SMAIndicator
    │   └─→ ADXIndicator
    │
    ├─→ Momentum Indicators
    │   ├─→ RSIIndicator
    │   ├─→ MACDIndicator
    │   └─→ StochasticIndicator
    │
    ├─→ Volatility Indicators
    │   ├─→ ATRIndicator
    │   └─→ BollingerBandsIndicator
    │
    └─→ Volume Indicators
        └─→ OBVIndicator
```

#### 2.5.1 IndicatorCalculator (Wrapper Layer)

**محل:** `signal_generation/shared/indicator_calculator.py`

**نقش:** یک wrapper ساده برای سازگاری با کد قدیمی

```python
class IndicatorCalculator:
    """
    Wrapper around IndicatorOrchestrator for backward compatibility.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # اصل کار توسط Orchestrator انجام می‌شود:
        self.orchestrator = IndicatorOrchestrator(config)

        # 📌 نکته مهم: IndicatorOrchestrator در __init__ خودش
        # متد _load_indicators() را صدا می‌زند و همه indicators
        # (از جمله ADX) را خودکار load می‌کند!

        # ثبت مجدد indicators (تکراری اما برای سازگاری):
        self._register_indicators()

    def _register_indicators(self):
        """Register all indicator calculators."""
        # Trend indicators
        self.orchestrator.register_indicator(EMAIndicator)
        self.orchestrator.register_indicator(SMAIndicator)

        # Momentum indicators
        self.orchestrator.register_indicator(RSIIndicator)
        self.orchestrator.register_indicator(MACDIndicator)
        self.orchestrator.register_indicator(StochasticIndicator)

        # Volatility indicators
        self.orchestrator.register_indicator(ATRIndicator)
        self.orchestrator.register_indicator(BollingerBandsIndicator)

        # Volume indicators
        self.orchestrator.register_indicator(OBVIndicator)

        # ⚠️ توجه: ADXIndicator اینجا register نمی‌شود!
        # چرا؟ چون IndicatorOrchestrator قبلاً در __init__ خودش
        # همه indicators (از جمله ADX) را load کرده است.

    def calculate_all(self, context) -> None:
        """Main entry point - calculates all indicators."""
        df = context.df

        # محاسبه توسط orchestrator:
        enriched_df = self.orchestrator.calculate_all(df)

        # اضافه کردن backward compatibility:
        if 'stoch_k' in enriched_df.columns:
            enriched_df['slowk'] = enriched_df['stoch_k']
        if 'stoch_d' in enriched_df.columns:
            enriched_df['slowd'] = enriched_df['stoch_d']

        # محاسبه volume_sma برای VolumeAnalyzer:
        if 'volume' in enriched_df.columns:
            volume_sma_period = self.config.get('volume_sma_period', 20)
            enriched_df['volume_sma'] = enriched_df['volume'].rolling(window=volume_sma_period).mean()

        # به‌روزرسانی context:
        context.df = enriched_df
```

**چرا wrapper؟**
- کد قدیمی انتظار دارد `IndicatorCalculator` وجود داشته باشد
- داخلش از `IndicatorOrchestrator` استفاده می‌کند (معماری جدید)
- backward compatibility: `slowk`/`slowd` برای کد قدیمی
- `volume_sma` محاسبه می‌شود چون VolumeAnalyzer نیاز دارد

**📌 نکته مهم درباره ADX:**

ADXIndicator در `_register_indicators()` ذکر نشده اما **در نهایت محاسبه می‌شود** چون:

1. `IndicatorOrchestrator` در `__init__` خودش متد `_load_indicators()` را صدا می‌زند
2. `_load_indicators()` خودکار همه 9 indicator (از جمله ADX) را load و register می‌کند
3. پس `_register_indicators()` در `IndicatorCalculator` در واقع تکراری است

**نتیجه:**
همه 9 indicator (EMA, SMA, ADX, RSI, MACD, Stochastic, ATR, Bollinger, OBV) محاسبه می‌شوند.

#### 2.5.2 IndicatorOrchestrator (هماهنگ‌کننده اصلی)

**محل:** `signal_generation/analyzers/indicators/indicator_orchestrator.py`

**نقش:** مدیریت و هماهنگی محاسبه همه اندیکاتورها

```python
class IndicatorOrchestrator:
    """
    Orchestrator for indicator calculation.

    مسئولیت‌ها:
    1. بارگذاری تمام indicator calculators
    2. اجرای محاسبات به ترتیب صحیح
    3. مدیریت وابستگی‌ها
    4. پشتیبانی از caching
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # دسته‌بندی indicators:
        self.trend_indicators: Dict[str, BaseIndicator] = {}
        self.momentum_indicators: Dict[str, BaseIndicator] = {}
        self.volatility_indicators: Dict[str, BaseIndicator] = {}
        self.volume_indicators: Dict[str, BaseIndicator] = {}

        # همه indicators (دسترسی سریع):
        self.all_indicators: Dict[str, BaseIndicator] = {}

        # تنظیمات:
        self.cache_enabled = self.config.get('indicators', {}).get('cache_enabled', True)

        # آمار:
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'errors': 0
        }

        # 🔥 خودکار همه indicators را load می‌کند:
        self._load_indicators()

    def _load_indicators(self):
        """Load all available indicator calculators automatically."""
        # Import all indicator classes
        from signal_generation.analyzers.indicators.ema import EMAIndicator
        from signal_generation.analyzers.indicators.sma import SMAIndicator
        from signal_generation.analyzers.indicators.rsi import RSIIndicator
        from signal_generation.analyzers.indicators.macd import MACDIndicator
        from signal_generation.analyzers.indicators.stochastic import StochasticIndicator
        from signal_generation.analyzers.indicators.atr import ATRIndicator
        from signal_generation.analyzers.indicators.bollinger_bands import BollingerBandsIndicator
        from signal_generation.analyzers.indicators.obv import OBVIndicator
        from signal_generation.analyzers.indicators.adx import ADXIndicator  # 👈 ADX اینجاست!

        # Register all indicators
        indicators = [
            # Trend indicators
            EMAIndicator,
            SMAIndicator,
            ADXIndicator,      # 📌 ADX به عنوان Trend indicator
            # Momentum indicators
            RSIIndicator,
            MACDIndicator,
            StochasticIndicator,
            # Volatility indicators
            ATRIndicator,
            BollingerBandsIndicator,
            # Volume indicators
            OBVIndicator
        ]

        for indicator_class in indicators:
            self.register_indicator(indicator_class)

        logger.info(f"Loaded {len(self.all_indicators)} indicators successfully")
```

**ترتیب محاسبه (مهم!):**

اندیکاتورها به **ترتیب خاص** محاسبه می‌شوند تا وابستگی‌ها برآورده شود:

```python
def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all indicators in correct order."""

    result_df = df.copy()

    # ترتیب محاسبه:
    calculation_order = [
        ('trend', self.trend_indicators),       # 1️⃣ اول
        ('momentum', self.momentum_indicators), # 2️⃣ دوم
        ('volatility', self.volatility_indicators), # 3️⃣ سوم
        ('volume', self.volume_indicators),     # 4️⃣ چهارم
    ]

    for indicator_type, indicator_dict in calculation_order:
        for indicator_name, indicator in indicator_dict.items():
            try:
                result_df = indicator.calculate_safe(result_df)
                self.stats['total_calculations'] += 1

            except Exception as e:
                logger.error(f"Error calculating {indicator_name}: {e}")
                self.stats['errors'] += 1

    return result_df
```

**چرا این ترتیب؟**

- **Trend** اول: چون برخی اندیکاتورها به EMA/SMA نیاز دارند
- **Momentum** دوم: ممکن است از trend indicators استفاده کنند
- **Volatility** سوم: ATR برای محاسبات دیگر نیاز است
- **Volume** آخر: وابستگی کمتری دارد

---

### 2.6 معرفی BaseIndicator (پایه همه اندیکاتورها)

**محل:** `signal_generation/analyzers/indicators/base_indicator.py`

```python
class BaseIndicator(ABC):
    """
    کلاس پایه برای همه اندیکاتورها.

    ویژگی‌ها:
    1. Interface استاندارد
    2. اعتبارسنجی خودکار ورودی/خروجی
    3. مدیریت خطا
    4. پشتیبانی از caching
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self._get_indicator_name()          # مثلاً 'EMA'
        self.indicator_type = self._get_indicator_type()  # مثلاً 'trend'
        self.required_columns = self._get_required_columns()  # مثلاً ['close']
        self.output_columns = self._get_output_columns()  # مثلاً ['ema_20', 'ema_50']

        # Caching:
        self._cache_enabled = self.config.get('cache_enabled', True)
        self._last_result = None
        self._last_hash = None

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """محاسبه اندیکاتور - باید در هر کلاس پیاده‌سازی شود."""
        pass

    def calculate_safe(self, df: pd.DataFrame) -> pd.DataFrame:
        """محاسبه امن با validation و error handling."""
        try:
            # اعتبارسنجی ورودی:
            if not self._validate_input(df):
                return df

            # بررسی cache:
            if self._cache_enabled:
                df_hash = self._get_dataframe_hash(df)
                if df_hash == self._last_hash and self._last_result is not None:
                    logger.debug(f"{self.name}: Returning cached result")
                    return self._last_result.copy()

            # محاسبه:
            result_df = self.calculate(df)

            # ذخیره در cache:
            if self._cache_enabled:
                self._last_result = result_df.copy()
                self._last_hash = df_hash

            return result_df

        except Exception as e:
            logger.error(f"Error calculating {self.name}: {e}")
            return df
```

**مزایای BaseIndicator:**

✅ **کد تمیز:** هر indicator فقط `calculate()` را پیاده‌سازی می‌کند
✅ **Caching خودکار:** هر indicator cache داخلی دارد
✅ **Validation:** ورودی/خروجی خودکار بررسی می‌شود
✅ **Error handling:** خطاها مدیریت می‌شوند
✅ **Testability:** هر indicator مستقل test می‌شود

---

**✅ بخش 2 - قسمت اول تمام شد!**

**در این قسمت:**
- ✅ STEP 1: Fetch Market Data
- ✅ STEP 1.5: Cache Check (TimeframeScoreCache)
- ✅ STEP 2: Create AnalysisContext
- ✅ STEP 3: Calculate Indicators (Architecture)
- ✅ معرفی IndicatorCalculator و IndicatorOrchestrator
- ✅ معرفی BaseIndicator

**قسمت بعدی بخش 2:**
- معرفی جزئیات 8 اندیکاتور (EMA, SMA, RSI, MACD, ATR, BB, Stoch, OBV)
- نحوه محاسبه هر کدام
- پارامترها و خروجی‌ها

ادامه می‌دهم...

### 2.7 جزئیات 8 اندیکاتور اصلی

در این بخش هر اندیکاتور را با جزئیات کامل بررسی می‌کنیم:

---

#### 2.7.1 EMAIndicator (Exponential Moving Average)

**محل:** `signal_generation/analyzers/indicators/ema.py`

**نوع:** Trend Indicator

**هدف:** محاسبه میانگین متحرک نمایی که به قیمت‌های اخیر وزن بیشتری می‌دهد.

**فرمول:**
```
EMA[today] = (Price[today] × k) + (EMA[yesterday] × (1 - k))

k = 2 / (Period + 1)
```

**مثال محاسبه EMA 20:**
```python
k = 2 / (20 + 1) = 2 / 21 = 0.0952

# روز 1: قیمت = 50000
EMA[1] = 50000  # مقدار اولیه

# روز 2: قیمت = 50500
EMA[2] = (50500 × 0.0952) + (50000 × 0.9048)
       = 4809.6 + 45240
       = 50049.6

# روز 3: قیمت = 51000
EMA[3] = (51000 × 0.0952) + (50049.6 × 0.9048)
       = 4855.2 + 45284.8
       = 50140.0
```

**پارامترهای پیش‌فرض:**
```python
# پیش‌فرض در کد:
ema_periods = [20, 50, 100]  # دوره‌های محاسبه
```

**ستون‌های خروجی (بر اساس config فعلی):**
```python
['ema_20', 'ema_50', 'ema_100']
```

**کد محاسبه:**
```python
class EMAIndicator(BaseIndicator):
    def _get_indicator_name(self) -> str:
        return 'EMA'

    def _get_indicator_type(self) -> str:
        return 'trend'

    def _get_required_columns(self) -> List[str]:
        return ['close']

    def _get_output_columns(self) -> List[str]:
        return [f'ema_{p}' for p in self.periods]

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMA for all periods."""
        result_df = df.copy()

        for period in self.periods:
            column_name = f'ema_{period}'
            result_df[column_name] = result_df['close'].ewm(
                span=period,
                adjust=False
            ).mean()

        return result_df
```

**استفاده در تحلیل:**
- **Golden Cross:** EMA20 از EMA50 عبور کند → سیگنال خرید
- **Death Cross:** EMA20 از EMA50 به پایین عبور کند → سیگنال فروش
- **EMA Alignment:** EMA20 > EMA50 > EMA100 → ترند صعودی قوی

---

#### 2.7.2 SMAIndicator (Simple Moving Average)

**محل:** `signal_generation/analyzers/indicators/sma.py`

**نوع:** Trend Indicator

**هدف:** محاسبه میانگین ساده قیمت در یک دوره مشخص.

**فرمول:**
```
SMA = (P1 + P2 + ... + Pn) / n

P = قیمت close
n = تعداد دوره
```

**مثال محاسبه SMA 20:**
```python
# 20 قیمت آخر:
prices = [50000, 50100, 50200, ..., 51800, 51900, 52000]

SMA[20] = sum(prices) / 20
        = (50000 + 50100 + ... + 52000) / 20
        = 1,020,000 / 20
        = 51,000
```

**پارامترهای پیش‌فرض:**
```python
# در config.yaml (خط 20):
sma_periods = [20, 50, 200]  # دوره‌های محاسبه

# پیش‌فرض در کد (اگر config نباشد):
sma_periods = [20, 50, 200]
```

**ستون‌های خروجی (بر اساس config فعلی):**
```python
['sma_20', 'sma_50', 'sma_200']
```

**کد محاسبه:**
```python
class SMAIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SMA for all periods."""
        result_df = df.copy()

        for period in self.periods:
            column_name = f'sma_{period}'
            result_df[column_name] = result_df['close'].rolling(
                window=period
            ).mean()

        return result_df
```

**تفاوت با EMA:**
| ویژگی | SMA | EMA |
|------|-----|-----|
| **وزن‌دهی** | یکسان به همه | بیشتر به اخیر |
| **واکنش به تغییر** | کندتر | سریع‌تر |
| **هموارسازی** | بیشتر | کمتر |
| **استفاده** | ترند بلندمدت | ترند کوتاه‌مدت |

---

#### 2.7.3 RSIIndicator (Relative Strength Index)

**محل:** `signal_generation/analyzers/indicators/rsi.py`

**نوع:** Momentum Indicator

**هدف:** اندازه‌گیری سرعت و تغییر حرکات قیمت (0 تا 100).

**فرمول:**
```
RSI = 100 - (100 / (1 + RS))

RS = میانگین سودها / میانگین زیان‌ها

میانگین سودها = EMA(مثبت‌های Δ قیمت)
میانگین زیان‌ها = EMA(منفی‌های Δ قیمت)
```

**مثال محاسبه RSI 14:**
```python
# تغییرات قیمت 14 روز اخیر:
changes = [+200, -100, +300, +150, -50, +100, +250, -150, +50, +100, -200, +150, +50, -100]

# جداسازی سودها و زیان‌ها:
gains = [200, 0, 300, 150, 0, 100, 250, 0, 50, 100, 0, 150, 50, 0]
losses = [0, 100, 0, 0, 50, 0, 0, 150, 0, 0, 200, 0, 0, 100]

# محاسبه میانگین (با EMA):
avg_gain = sum(gains) / 14 = 1350 / 14 = 96.43
avg_loss = sum(losses) / 14 = 600 / 14 = 42.86

# RS و RSI:
RS = 96.43 / 42.86 = 2.25
RSI = 100 - (100 / (1 + 2.25))
    = 100 - (100 / 3.25)
    = 100 - 30.77
    = 69.23
```

**پارامترهای پیش‌فرض:**
```python
rsi_period = 14  # استاندارد
```

**ستون خروجی:**
```python
['rsi']
```

**کد محاسبه:**
```python
class RSIIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI."""
        result_df = df.copy()
        
        # محاسبه تغییرات قیمت
        delta = result_df['close'].diff()
        
        # جداسازی سودها و زیان‌ها
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # میانگین متحرک نمایی
        avg_gains = gains.ewm(span=self.period, adjust=False).mean()
        avg_losses = losses.ewm(span=self.period, adjust=False).mean()
        
        # RS و RSI
        rs = avg_gains / avg_losses
        result_df['rsi'] = 100 - (100 / (1 + rs))
        
        return result_df
```

**تفسیر مقادیر:**
```
RSI > 70  → Overbought (اشباع خرید) ⚠️
RSI 30-70 → محدوده عادی ✅
RSI < 30  → Oversold (اشباع فروش) ⚠️

RSI = 80  → خیلی قوی (احتمال اصلاح)
RSI = 50  → خنثی
RSI = 20  → خیلی ضعیف (احتمال برگشت)
```

**سیگنال‌های معاملاتی:**
- **Divergence صعودی:** قیمت پایین‌تر اما RSI بالاتر → سیگنال خرید
- **Divergence نزولی:** قیمت بالاتر اما RSI پایین‌تر → سیگنال فروش
- **Cross خط 50:** RSI از 50 عبور کند → تایید تغییر ترند

---

#### 2.7.4 MACDIndicator (Moving Average Convergence Divergence)

**محل:** `signal_generation/analyzers/indicators/macd.py`

**نوع:** Momentum Indicator

**هدف:** شناسایی تغییرات در قدرت، جهت، مومنتوم و مدت ترند.

**فرمول:**
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

**مثال محاسبه:**
```python
# فرض:
EMA[12] = 51,200
EMA[26] = 50,800

# MACD Line:
MACD = 51,200 - 50,800 = +400

# Signal Line (EMA 9 روز MACD):
# فرض MACD های 9 روز اخیر:
macd_values = [350, 360, 370, 380, 390, 395, 398, 399, 400]
Signal = EMA(macd_values, 9) = 385

# Histogram:
Histogram = 400 - 385 = +15
```

**پارامترهای پیش‌فرض:**
```python
fast_period = 12   # EMA سریع
slow_period = 26   # EMA کند
signal_period = 9  # EMA سیگنال
```

**ستون‌های خروجی:**
```python
['macd', 'macd_signal', 'macd_hist']
```

**کد محاسبه:**
```python
class MACDIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD."""
        result_df = df.copy()
        
        # EMA های سریع و کند
        ema_fast = result_df['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = result_df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # MACD Line
        result_df['macd'] = ema_fast - ema_slow
        
        # Signal Line
        result_df['macd_signal'] = result_df['macd'].ewm(
            span=self.signal_period, 
            adjust=False
        ).mean()
        
        # Histogram
        result_df['macd_hist'] = result_df['macd'] - result_df['macd_signal']
        
        return result_df
```

**تفسیر سیگنال‌ها:**

**1. MACD Crossover:**
```python
if macd > macd_signal:
    # Golden Cross → سیگنال خرید 🟢
    # MACD از Signal به بالا عبور کرد

if macd < macd_signal:
    # Death Cross → سیگنال فروش 🔴
    # MACD از Signal به پایین عبور کرد
```

**2. Zero Line Crossover:**
```python
if macd > 0:
    # بالای خط صفر → ترند صعودی 📈
    
if macd < 0:
    # پایین خط صفر → ترند نزولی 📉
```

**3. Histogram Analysis:**
```python
if hist > 0 and increasing:
    # مومنتوم صعودی در حال افزایش 🚀
    
if hist < 0 and decreasing:
    # مومنتوم نزولی در حال افزایش 📉
    
if hist decreasing (but still positive):
    # ضعف شدن مومنتوم صعودی ⚠️
```

**مثال واقعی:**
```
زمان    قیمت    MACD    Signal   Hist    تفسیر
─────────────────────────────────────────────────
10:00   50000   -150    -120     -30     نزولی
11:00   50200   -100    -110     +10     شروع برگشت
12:00   50500   -50     -90      +40     برگشت قوی
13:00   50800   +20     -50      +70     Golden Cross! 🟢
14:00   51200   +80     -10      +90     ترند صعودی قوی
```

**استفاده در سیستم جدید:**
- MomentumAnalyzer از MACD برای تشخیص **MACD Market Types** استفاده می‌کند
- 5 نوع بازار (A_bullish_strong, B_bullish_normal, C_bearish_strong, D_bearish_normal, X_transition)
- توضیحات کامل در بخش 3 (MomentumAnalyzer)

---

#### 2.7.5 ATRIndicator (Average True Range)

**محل:** `signal_generation/analyzers/indicators/atr.py`

**نوع:** Volatility Indicator

**هدف:** اندازه‌گیری نوسان بازار (هر چه ATR بالاتر → نوسان بیشتر).

**فرمول:**
```
True Range (TR) = max(
    High - Low,
    |High - Previous Close|,
    |Low - Previous Close|
)

ATR = EMA(TR, period)
```

**مثال محاسبه:**
```python
# کندل فعلی:
High = 52,000
Low = 51,500
Previous Close = 51,800

# محاسبه TR:
TR = max(
    52,000 - 51,500,        # = 500
    |52,000 - 51,800|,      # = 200
    |51,500 - 51,800|       # = 300
) = 500

# ATR (میانگین TR در 14 دوره):
# فرض TR های 14 روز اخیر:
tr_values = [480, 520, 510, 490, 500, 530, 520, 510, 500, 490, 510, 520, 500, 500]

ATR = EMA(tr_values, 14) = 506.5
```

**پارامترهای پیش‌فرض:**
```python
atr_period = 14  # استاندارد
```

**ستون خروجی:**
```python
['atr']
```

**کد محاسبه:**
```python
class ATRIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ATR."""
        result_df = df.copy()
        
        # محاسبه True Range
        high_low = result_df['high'] - result_df['low']
        high_close = abs(result_df['high'] - result_df['close'].shift())
        low_close = abs(result_df['low'] - result_df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # ATR = EMA of TR
        result_df['atr'] = tr.ewm(span=self.period, adjust=False).mean()
        
        return result_df
```

**استفاده در تحلیل:**

**1. محاسبه ATR% (استفاده در سیستم جدید):**
```python
ATR% = (ATR / قیمت فعلی) × 100

# مثال:
ATR = 500
قیمت = 50,000

ATR% = (500 / 50,000) × 100 = 1.0%
```

**2. تشخیص نوسان (VolatilityAnalyzer):**
```python
if ATR% < 0.7:
    volatility = 'low'      # نوسان کم
elif ATR% <= 1.3:
    volatility = 'normal'   # نوسان عادی
else:
    volatility = 'high'     # نوسان بالا
```

**3. محاسبه Stop Loss:**
```python
# روش استاندارد:
Stop Loss = قیمت ورود ± (ATR × ضریب)

# مثال برای LONG:
قیمت ورود = 50,000
ATR = 500
ضریب = 2

Stop Loss = 50,000 - (500 × 2) = 49,000
```

**4. تشخیص رژیم بازار:**
```python
# نوسان اخیر vs میانگین:
recent_atr = mean(ATR[-5:])      # 5 کندل اخیر
past_atr = mean(ATR[-25:-5])     # 20 کندل قبلی

volatility_ratio = recent_atr / past_atr

if volatility_ratio > 1.5:
    # نوسان 50% افزایش → بازار ناپایدار
    circuit_breaker.trigger()
```

---

#### 2.7.6 BollingerBandsIndicator (Bollinger Bands)

**محل:** `signal_generation/analyzers/indicators/bollinger_bands.py`

**نوع:** Volatility Indicator

**هدف:** نشان دادن سطوح نوسان با 3 خط (بالا، میانه، پایین).

**فرمول:**
```
Middle Band = SMA(20)
Upper Band = Middle Band + (2 × StdDev)
Lower Band = Middle Band - (2 × StdDev)

StdDev = انحراف معیار 20 دوره
```

**مثال محاسبه:**
```python
# 20 قیمت اخیر:
prices = [50000, 50100, 50200, ..., 51800, 51900, 52000]

# Middle Band (SMA 20):
middle = mean(prices) = 51,000

# انحراف معیار:
std_dev = std(prices) = 450

# Upper & Lower Bands:
upper = 51,000 + (2 × 450) = 51,900
lower = 51,000 - (2 × 450) = 50,100

# نتیجه:
bb_upper = 51,900
bb_middle = 51,000
bb_lower = 50,100
```

**پارامترهای پیش‌فرض:**
```python
bb_period = 20    # دوره SMA
bb_std_dev = 2    # ضریب انحراف معیار
```

**ستون‌های خروجی:**
```python
['bb_upper', 'bb_middle', 'bb_lower']
```

**کد محاسبه:**
```python
class BollingerBandsIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        result_df = df.copy()
        
        # Middle Band (SMA)
        result_df['bb_middle'] = result_df['close'].rolling(
            window=self.period
        ).mean()
        
        # Standard Deviation
        std = result_df['close'].rolling(window=self.period).std()
        
        # Upper & Lower Bands
        result_df['bb_upper'] = result_df['bb_middle'] + (self.std_dev * std)
        result_df['bb_lower'] = result_df['bb_middle'] - (self.std_dev * std)
        
        return result_df
```

**تفسیر سیگنال‌ها:**

**1. موقعیت قیمت:**
```python
if price >= bb_upper:
    # در باند بالا → احتمال اشباع خرید 📈⚠️
    # ممکن است اصلاح کند
    
if price <= bb_lower:
    # در باند پایین → احتمال اشباع فروش 📉⚠️
    # ممکن است برگردد
    
if price near bb_middle:
    # در میانه → وضعیت عادی ✅
```

**2. فشردگی باندها (Squeeze):**
```python
bandwidth = (bb_upper - bb_lower) / bb_middle

if bandwidth < 0.02:  # 2%
    # باندها فشرده شده → نوسان کم
    # احتمال شکست قوی (Breakout) 🚀
    
if bandwidth > 0.06:  # 6%
    # باندها باز شده → نوسان زیاد
    # احتمال کاهش حرکت
```

**3. Bollinger Bounce:**
```python
# قیمت از باند پایین برگشت:
if price touched bb_lower and now moving up:
    # سیگنال خرید 🟢
    
# قیمت از باند بالا برگشت:
if price touched bb_upper and now moving down:
    # سیگنال فروش 🔴
```

**مثال واقعی:**
```
زمان    قیمت    BB_Upper  BB_Middle  BB_Lower  تفسیر
───────────────────────────────────────────────────────
10:00   50000   51,900    51,000     50,100    عادی
11:00   51,800   51,950    51,050     50,150    نزدیک باند بالا
12:00   52,100   52,000    51,100     50,200    اشباع خرید! ⚠️
13:00   51,500   51,900    51,000     50,100    برگشت از بالا 🔴
14:00   50,200   51,850    50,950     50,050    نزدیک باند پایین
15:00   50,000   51,800    50,900     50,000    لمس باند پایین! ⚠️
16:00   50,500   51,850    50,950     50,050    برگشت از پایین 🟢
```

---

#### 2.7.7 StochasticIndicator (Stochastic Oscillator)

**محل:** `signal_generation/analyzers/indicators/stochastic.py`

**نوع:** Momentum Indicator

**هدف:** مقایسه قیمت بسته شدن با محدوده قیمت در یک دوره (0 تا 100).

**فرمول:**
```
%K = ((Close - Lowest Low) / (Highest High - Lowest Low)) × 100
%D = SMA(%K, 3)

Lowest Low = پایین‌ترین low در 14 دوره
Highest High = بالاترین high در 14 دوره
```

**مثال محاسبه:**
```python
# 14 کندل اخیر:
Highest High = 52,500
Lowest Low = 50,000
Current Close = 51,800

# %K:
%K = ((51,800 - 50,000) / (52,500 - 50,000)) × 100
   = (1,800 / 2,500) × 100
   = 0.72 × 100
   = 72

# %D (SMA 3 روز %K):
%K_values = [70, 71, 72]
%D = (70 + 71 + 72) / 3 = 71
```

**پارامترهای پیش‌فرض:**
```python
k_period = 14  # دوره %K
d_period = 3   # دوره %D (SMA)
```

**ستون‌های خروجی:**
```python
['stoch_k', 'stoch_d', 'slowk', 'slowd']  # slowk/slowd برای backward compatibility
```

**کد محاسبه:**
```python
class StochasticIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Stochastic Oscillator."""
        result_df = df.copy()
        
        # محاسبه Lowest Low و Highest High
        low_min = result_df['low'].rolling(window=self.k_period).min()
        high_max = result_df['high'].rolling(window=self.k_period).max()
        
        # %K
        result_df['stoch_k'] = (
            (result_df['close'] - low_min) / (high_max - low_min)
        ) * 100
        
        # %D (SMA of %K)
        result_df['stoch_d'] = result_df['stoch_k'].rolling(
            window=self.d_period
        ).mean()
        
        # Backward compatibility
        result_df['slowk'] = result_df['stoch_k']
        result_df['slowd'] = result_df['stoch_d']
        
        return result_df
```

**تفسیر مقادیر:**
```
%K > 80  → Overbought (اشباع خرید) ⚠️
%K 20-80 → محدوده عادی ✅
%K < 20  → Oversold (اشباع فروش) ⚠️
```

**سیگنال‌های معاملاتی:**

**1. Crossover:**
```python
if %K crosses above %D:
    # سیگنال خرید 🟢
    # %K از %D به بالا عبور کرد
    
if %K crosses below %D:
    # سیگنال فروش 🔴
    # %K از %D به پایین عبور کرد
```

**2. Divergence:**
```python
# Bullish Divergence:
if price making lower lows and %K making higher lows:
    # واگرایی صعودی → سیگنال خرید قوی 🟢🟢
    
# Bearish Divergence:
if price making higher highs and %K making lower highs:
    # واگرایی نزولی → سیگنال فروش قوی 🔴🔴
```

**مثال واقعی:**
```
زمان    قیمت    %K    %D    تفسیر
───────────────────────────────────
10:00   50000   25    28    محدوده عادی
11:00   50500   35    29    در حال بهبود
12:00   51000   45    35    صعود ملایم
13:00   51500   60    47    قوی شدن
14:00   52000   75    60    نزدیک اشباع
15:00   52500   85    73    اشباع خرید! ⚠️
16:00   52200   80    80    %K و %D برابر (خنثی)
17:00   51800   70    78    %K < %D → احتمال ریزش 🔴
```

---

#### 2.7.8 OBVIndicator (On-Balance Volume)

**محل:** `signal_generation/analyzers/indicators/obv.py`

**نوع:** Volume Indicator

**هدف:** استفاده از حجم برای پیش‌بینی تغییرات قیمت.

**فرمول:**
```
if Close[today] > Close[yesterday]:
    OBV[today] = OBV[yesterday] + Volume[today]
    
elif Close[today] < Close[yesterday]:
    OBV[today] = OBV[yesterday] - Volume[today]
    
else:
    OBV[today] = OBV[yesterday]
```

**مثال محاسبه:**
```python
# روز 1:
Close = 50,000
Volume = 1,000 BTC
OBV = 1,000  # شروع

# روز 2:
Close = 50,500  # بالاتر از قبل ✅
Volume = 1,200 BTC
OBV = 1,000 + 1,200 = 2,200

# روز 3:
Close = 50,300  # پایین‌تر از قبل ❌
Volume = 800 BTC
OBV = 2,200 - 800 = 1,400

# روز 4:
Close = 50,800  # بالاتر از قبل ✅
Volume = 1,500 BTC
OBV = 1,400 + 1,500 = 2,900
```

**ستون خروجی:**
```python
['obv']
```

**کد محاسبه:**
```python
class OBVIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate OBV."""
        result_df = df.copy()
        
        # محاسبه تغییر قیمت
        price_change = result_df['close'].diff()
        
        # تعیین جهت حجم
        volume_direction = pd.Series(0, index=result_df.index)
        volume_direction[price_change > 0] = result_df['volume']
        volume_direction[price_change < 0] = -result_df['volume']
        
        # OBV = مجموع تجمعی حجم با جهت
        result_df['obv'] = volume_direction.cumsum()
        
        return result_df
```

**تفسیر سیگنال‌ها:**

**1. OBV Trend:**
```python
if OBV trending up:
    # حجم خرید بیشتر → فشار خرید 🟢
    # احتمال صعود قیمت
    
if OBV trending down:
    # حجم فروش بیشتر → فشار فروش 🔴
    # احتمال نزول قیمت
```

**2. OBV Divergence (قدرتمندترین!):**
```python
# Bullish Divergence:
if price making lower lows and OBV making higher lows:
    # قیمت پایین اما حجم خرید بالا
    # سیگنال خرید قوی! 🟢🟢🟢
    
# Bearish Divergence:
if price making higher highs and OBV making lower highs:
    # قیمت بالا اما حجم خرید کم
    # سیگنال فروش قوی! 🔴🔴🔴
```

**3. OBV Breakout:**
```python
if OBV breaks resistance:
    # حجم در حال افزایش
    # تایید شکست قیمت 🚀
    
if OBV breaks support:
    # حجم در حال کاهش
    # تایید ریزش قیمت 📉
```

**مثال واقعی (Divergence):**
```
زمان    قیمت    حجم    OBV      تفسیر
─────────────────────────────────────────────
10:00   50000   1000    10000    شروع
11:00   49500   1200    8800     ریزش (قیمت ↓)
12:00   49000   800     8000     ریزش ادامه (قیمت ↓↓)
13:00   48800   1500    9500     حجم خرید زیاد! (OBV ↑)
14:00   49200   1800    11300    برگشت شروع شد (OBV ↑↑)
15:00   50000   2000    13300    صعود با حجم بالا 🟢

تحلیل:
- قیمت: 50000 → 48800 → 50000 (پایین‌ترین: 48800)
- OBV: 10000 → 8000 → 13300 (پایین‌ترین: 8000، اما بعد افزایش!)
- واگرایی صعودی: قیمت پایین اما OBV بعدش بالا رفت
- نتیجه: سیگنال خرید قوی که درست بود! ✅
```

---

**✅ بخش 2 - قسمت دوم تمام شد!**

**در این قسمت:**
- ✅ EMAIndicator: میانگین متحرک نمایی
- ✅ SMAIndicator: میانگین متحرک ساده
- ✅ RSIIndicator: شاخص قدرت نسبی
- ✅ MACDIndicator: واگرایی/همگرایی میانگین متحرک
- ✅ ATRIndicator: میانگین محدوده واقعی
- ✅ BollingerBandsIndicator: باندهای بولینگر
- ✅ StochasticIndicator: نوسانگر استوکستیک
- ✅ OBVIndicator: حجم موازنه‌ای

**بخش 2 کامل شد! ✅**

**بخش بعدی:**
## بخش 3: تحلیل یک تایم‌فریم با 11 Analyzer

شامل:
- STEP 3.5: Market Regime Detection
- STEP 4: اجرای 11 Analyzer
- جزئیات کامل هر Analyzer:
  1. TrendAnalyzer (7 فاز)
  2. MomentumAnalyzer (5 MACD Market Types)
  3. VolumeAnalyzer
  4. PatternAnalyzer (Recency Scoring)
  5. SRAnalyzer
  6. VolatilityAnalyzer (ATR%)
  7. HTFAnalyzer
  8. ChannelAnalyzer
  9. HarmonicAnalyzer
  10. CyclicalAnalyzer
  11. VolumePatternAnalyzer

ادامه می‌دهم...

---

## بخش ۳: تحلیل یک تایم‌فریم با 11 Analyzer

در این بخش، نحوه تحلیل کامل یک تایم‌فریم را بررسی می‌کنیم. پس از محاسبه اندیکاتورها، نوبت به تحلیل‌های پیشرفته می‌رسد.

### 3.1 STEP 3.5: تشخیص رژیم بازار (Market Regime Detection)

**محل:** `orchestrator.py:339-351`

```python
logger.info(f"[3.5/7] Detecting market regime for {symbol}")

regime_info = {'regime': 'unknown', 'confidence': 0.0}

if self.regime_detector.enabled:
    regime_info = self.regime_detector.detect_regime(context.df)
    logger.info(
        f"  ✓ Regime: {regime_info.get('regime')}, "
        f"Confidence: {regime_info.get('confidence', 0):.2f}"
    )

    # Store in context for analyzers to use
    context.metadata['regime_info'] = regime_info
```

**کلاس:** `MarketRegimeDetector` (محل: `signal_generation/systems/market_regime_detector.py`)

**هدف:** تشخیص وضعیت کلی بازار با ترکیب ترند و نوسان (9 رژیم اصلی).

#### 3.1.1 فلسفه Market Regime Detection

بازار می‌تواند در **حالت‌های مختلفی** باشد:
- ترند قوی + نوسان کم = موقعیت عالی برای معامله ✅
- ترند ضعیف + نوسان زیاد = خطرناک ⚠️
- رنج + نوسان بالا = بسیار خطرناک ❌

**MarketRegimeDetector** این حالت‌ها را **تشخیص خودکار** می‌دهد.

#### 3.1.2 معماری تشخیص رژیم

```python
class MarketRegimeDetector:
    """
    Detects market regime combining trend strength and volatility.
    
    9 Main Regimes (OLD SYSTEM format):
    1. strong_trend_normal
    2. strong_trend_high
    3. strong_trend_low
    4. weak_trend_normal
    5. weak_trend_high
    6. weak_trend_low
    7. range_normal
    8. range_high
    9. range_low
    
    Special Regimes:
    - breakout_{direction}_{volatility}
    - choppy
    """
```

**ورودی:** DataFrame با اندیکاتورهای محاسبه شده

**خروجی:**
```python
{
    'regime': 'strong_trend_normal',  # نام رژیم
    'confidence': 0.85,               # اطمینان (0-1)
    'trend_strength': 'strong',       # قدرت ترند
    'trend_direction': 'bullish',     # جهت ترند
    'volatility': 'normal',           # نوسان
    'is_breakout': False,             # آیا breakout است؟
    'is_choppy': False,               # آیا choppy است؟
    'adx': 32.5,                      # مقدار ADX
    'atr_percent': 1.1                # مقدار ATR%
}
```

#### 3.1.3 گام‌های تشخیص رژیم

**گام 1: تحلیل قدرت ترند (با ADX)**

```python
# ADX (Average Directional Index):
adx = df['adx'].iloc[-1]

if adx > 25:
    trend_strength = TrendStrength.STRONG    # ترند قوی
elif adx > 20:
    trend_strength = TrendStrength.WEAK      # ترند ضعیف
else:
    trend_strength = TrendStrength.NONE      # بدون ترند (رنج)
```

**ADX چیست؟**
- ADX نوسان بین **0 تا 100**
- ADX فقط **قدرت** ترند را نشان می‌دهد (نه جهت)
- ADX > 25 = ترند قوی
- ADX < 20 = بدون ترند (sideways/range)

**مثال:**
```
ADX = 35 → ترند قوی (اما نمی‌دونیم صعودی یا نزولی!)
ADX = 15 → بدون ترند (رنج)
```

**گام 2: تعیین جهت ترند (با +DI و -DI)**

```python
# Directional Indicators:
plus_di = df['plus_di'].iloc[-1]   # فشار خرید
minus_di = df['minus_di'].iloc[-1]  # فشار فروش

if plus_di > minus_di:
    trend_direction = 'bullish'   # صعودی
else:
    trend_direction = 'bearish'   # نزولی
```

**+DI و -DI چیست؟**
- +DI: میزان فشار خرید (صعودی)
- -DI: میزان فشار فروش (نزولی)

**مثال:**
```
+DI = 30, -DI = 15 → صعودی (فشار خرید بیشتر)
+DI = 12, -DI = 28 → نزولی (فشار فروش بیشتر)
```

**گام 3: تحلیل نوسان (با ATR%)**

```python
# ATR% = (ATR / قیمت فعلی) × 100
atr = df['atr'].iloc[-1]
close = df['close'].iloc[-1]
atr_percent = (atr / close) * 100

if atr_percent < 0.5:
    volatility = Volatility.LOW      # نوسان کم
elif atr_percent <= 1.5:
    volatility = Volatility.NORMAL   # نوسان عادی
else:
    volatility = Volatility.HIGH     # نوسان زیاد
```

**مثال محاسبه:**
```python
# BTC:
قیمت = 50,000 USDT
ATR = 500 USDT

ATR% = (500 / 50,000) × 100 = 1.0%

1.0% → بین 0.5 و 1.5 → نوسان عادی ✅
```

**گام 4: تشخیص Breakout**

```python
# آیا در حال شکست محدوده هستیم؟

# بررسی حجم:
current_volume = df['volume'].iloc[-1]
avg_volume = df['volume'].rolling(20).mean().iloc[-1]
volume_surge = current_volume > avg_volume * 1.5  # 50% بیشتر

# بررسی قیمت:
high_20 = df['high'].rolling(20).max().iloc[-1]
low_20 = df['low'].rolling(20).min().iloc[-1]
current_close = df['close'].iloc[-1]

breakout_up = current_close > high_20
breakout_down = current_close < low_20

is_breakout = volume_surge and (breakout_up or breakout_down)
```

**Breakout چیست؟**
شکست محدوده قیمتی با **حجم بالا**:
- قیمت از بالاترین 20 کندل عبور کند + حجم 50% بیشتر → Breakout صعودی
- قیمت از پایین‌ترین 20 کندل عبور کند + حجم 50% بیشتر → Breakout نزولی

**گام 5: تشخیص Choppy Market**

```python
# بازار choppy = تغییرات سریع و بی‌نظم ADX

adx_change = abs(df['adx'].diff().iloc[-5:]).mean()

if adx_change > 5:  # ADX خیلی بی‌ثبات
    is_choppy = True
```

**Choppy چیست؟**
بازار **بی‌نظم** با تغییرات مکرر جهت:
- ADX دائم بالا و پایین می‌شود
- سخت برای پیش‌بینی
- بهتر است معامله نکنیم ⚠️

**گام 6: ترکیب نهایی → تعیین رژیم**

```python
# فرمت رژیم: {trend_strength}_{volatility}

if is_breakout:
    regime = f"breakout_{direction}_{volatility}"
    # مثال: "breakout_bullish_normal"

elif is_choppy:
    regime = "choppy"

elif trend_strength == STRONG:
    if volatility == HIGH:
        regime = "strong_trend_high"
    elif volatility == LOW:
        regime = "strong_trend_low"
    else:
        regime = "strong_trend_normal"

elif trend_strength == WEAK:
    # مشابه...
    regime = "weak_trend_normal"

else:  # NONE (range)
    if volatility == HIGH:
        regime = "range_high"  # خطرناک!
    elif volatility == LOW:
        regime = "range_low"
    else:
        regime = "range_normal"
```

#### 3.1.4 جدول کامل 9 رژیم اصلی

| رژیم | شرح | ADX | ATR% | مناسب معامله؟ | ریسک |
|------|-----|-----|------|---------------|------|
| **strong_trend_normal** | ترند قوی با نوسان عادی | >25 | 0.5-1.5 | ✅✅✅ بهترین | کم |
| **strong_trend_low** | ترند قوی با نوسان کم | >25 | <0.5 | ✅✅ خوب | کم |
| **strong_trend_high** | ترند قوی با نوسان زیاد | >25 | >1.5 | ⚠️ احتیاط | متوسط |
| **weak_trend_normal** | ترند ضعیف با نوسان عادی | 20-25 | 0.5-1.5 | ✅ قابل قبول | متوسط |
| **weak_trend_low** | ترند ضعیف با نوسان کم | 20-25 | <0.5 | ⚠️ احتیاط | متوسط |
| **weak_trend_high** | ترند ضعیف با نوسان زیاد | 20-25 | >1.5 | ❌ خطرناک | بالا |
| **range_normal** | رنج با نوسان عادی | <20 | 0.5-1.5 | ⚠️ محدود | متوسط |
| **range_low** | رنج فشرده با نوسان کم | <20 | <0.5 | ⚠️ منتظر بمان | کم |
| **range_high** | رنج با نوسان زیاد | <20 | >1.5 | ❌ خطرناک | خیلی بالا |

#### 3.1.5 رژیم‌های ویژه

**Breakout Regimes:**
```python
# فرمت: breakout_{direction}_{volatility}

"breakout_bullish_normal"  # شکست صعودی با نوسان عادی ✅
"breakout_bullish_high"    # شکست صعودی با نوسان بالا ⚠️
"breakout_bearish_normal"  # شکست نزولی با نوسان عادی
...
```

**Choppy Regime:**
```python
"choppy"  # بازار بی‌نظم - بهتر است معامله نکنیم ❌
```

#### 3.1.6 محاسبه Confidence (اطمینان)

```python
def calculate_confidence(self, trend_strength, volatility, adx, atr_percent):
    """
    محاسبه میزان اطمینان به رژیم تشخیص داده شده (0-1)
    """
    confidence = 0.5  # شروع از میانگین
    
    # بر اساس قدرت ADX:
    if adx > 30:
        confidence += 0.2  # ADX خیلی قوی
    elif adx > 25:
        confidence += 0.1  # ADX قوی
    elif adx < 15:
        confidence -= 0.2  # ADX خیلی ضعیف
    
    # بر اساس نوسان:
    if volatility == 'normal':
        confidence += 0.1  # نوسان عادی (خوب)
    elif volatility == 'high':
        confidence -= 0.1  # نوسان بالا (ریسکی)
    
    # بر اساس سازگاری +DI/-DI با ADX:
    di_diff = abs(plus_di - minus_di)
    if di_diff > 15:
        confidence += 0.15  # اختلاف زیاد = جهت مشخص
    
    # محدود کردن به 0-1:
    confidence = max(0.0, min(1.0, confidence))
    
    return confidence
```

**مثال:**
```python
# رژیم: strong_trend_normal
ADX = 32
ATR% = 1.0
+DI = 30, -DI = 12 (diff = 18)

confidence = 0.5
confidence += 0.2  # ADX > 30
confidence += 0.1  # volatility normal
confidence += 0.15 # DI diff > 15
confidence = 0.95  # خیلی مطمئن! ✅
```

#### 3.1.7 مثال کامل تشخیص رژیم

```python
# داده‌های ورودی:
df = {
    'adx': 28,
    'plus_di': 32,
    'minus_di': 15,
    'atr': 550,
    'close': 50000,
    'volume': 1500,
    'volume_20ma': 1000
}

# ─── گام 1: قدرت ترند ───
adx = 28
# 28 > 25 → STRONG ✅

# ─── گام 2: جهت ترند ───
plus_di = 32
minus_di = 15
# 32 > 15 → bullish ✅

# ─── گام 3: نوسان ───
atr_percent = (550 / 50000) × 100 = 1.1%
# 1.1% بین 0.5-1.5 → NORMAL ✅

# ─── گام 4: Breakout? ───
volume_surge = 1500 > 1000 × 1.5 = False
is_breakout = False

# ─── گام 5: Choppy? ───
adx_change = 2.5 (کم)
is_choppy = False

# ─── گام 6: رژیم نهایی ───
regime = "strong_trend_normal" ✅✅✅

# ─── محاسبه Confidence ───
confidence = 0.5
confidence += 0.1  # ADX 28 > 25
confidence += 0.1  # volatility normal
confidence += 0.15 # DI diff = 17 > 15
confidence = 0.85  # 85% اطمینان

# نتیجه:
{
    'regime': 'strong_trend_normal',
    'confidence': 0.85,
    'trend_strength': 'strong',
    'trend_direction': 'bullish',
    'volatility': 'normal',
    'is_breakout': False,
    'is_choppy': False,
    'adx': 28.0,
    'atr_percent': 1.1
}
```

#### 3.1.8 استفاده از Regime در تصمیم‌گیری

**در Analyzers:**
```python
# مثلاً در TrendAnalyzer:
regime_info = context.metadata.get('regime_info', {})
regime = regime_info.get('regime')

if regime == 'strong_trend_normal':
    # بهترین حالت - افزایش وزن سیگنال
    trend_score *= 1.2
    
elif regime == 'range_high':
    # خطرناک - کاهش وزن سیگنال
    trend_score *= 0.6
    
elif regime == 'choppy':
    # خیلی خطرناک - رد کردن سیگنال
    return None
```

**در SignalScorer:**
```python
regime = context.metadata.get('regime_info', {}).get('regime')

# ضریب رژیم:
regime_multipliers = {
    'strong_trend_normal': 1.3,   # افزایش امتیاز
    'strong_trend_low': 1.2,
    'strong_trend_high': 1.0,
    'weak_trend_normal': 0.9,
    'weak_trend_high': 0.7,
    'range_high': 0.5,            # کاهش شدید
    'choppy': 0.3                 # تقریباً رد
}

multiplier = regime_multipliers.get(regime, 1.0)
final_score *= multiplier
```

#### 3.1.9 تنظیمات (Config)

**محل در config:** `config.yaml` خط 648

```yaml
market_regime:
  enabled: True                            # فعال/غیرفعال کردن تشخیص رژیم

  # Indicator Periods:
  adx_period: 14                           # دوره محاسبه ADX
  volatility_period: 20                    # دوره محاسبه ATR

  # ADX Thresholds:
  strong_trend_threshold: 25               # حداقل ADX برای ترند قوی
  weak_trend_threshold: 20                 # حداقل ADX برای ترند ضعیف

  # ATR% Thresholds:
  high_volatility_threshold: 1.5           # ATR% > 1.5 = نوسان بالا
  low_volatility_threshold: 0.5            # ATR% < 0.5 = نوسان کم

  # Strategy Adaptation:
  adapt_strategy: True                     # تغییر خودکار پارامترها بر اساس رژیم
```

**پارامترهای پیش‌فرض اضافی در کد (اگر در config نباشند):**

```python
# محل: market_regime_detector.py:158-175

# Bollinger Bands (برای Breakout Detection):
bollinger_period: 20
bollinger_std: 2.0

# RSI:
rsi_period: 14

# Breakout Detection:
breakout_lookback: 10          # تعداد کندل برای بررسی breakout
breakout_threshold: 2.0        # قدرت شکست (به ATR)

# Choppy Detection:
choppy_threshold: 0.3          # آستانه تغییرات قیمت
```

**📌 نکته:** تشخیص Breakout بر اساس **Bollinger Bands** انجام می‌شود، نه volume surge. کد از BB استفاده می‌کند.

---

**✅ بخش 3.1 (Market Regime Detection) تمام شد!**

**در این قسمت:**
- ✅ فلسفه و اهمیت Regime Detection
- ✅ 6 گام تشخیص رژیم (ADX, DI, ATR%, Breakout, Choppy, Combine)
- ✅ جدول کامل 9 رژیم اصلی با توضیحات
- ✅ رژیم‌های ویژه (Breakout, Choppy)
- ✅ محاسبه Confidence
- ✅ مثال کامل عددی
- ✅ نحوه استفاده در تصمیم‌گیری

**قسمت بعدی:**
### 3.2 STEP 4: اجرای 11 Analyzer + معرفی اولین Analyzer (TrendAnalyzer)

ادامه می‌دهم...

---

## 3.2 STEP 4: اجرای 11 Analyzer

**محل:** `orchestrator.py:354-368`

```python
# === STEP 4: Run Analyzers ===
logger.info(f"[4/7] Running {len(self.analyzers)} analyzers for {symbol}")

self._run_analyzers(context)

# Check minimum required analyzers
required = ['trend', 'momentum', 'volume']
missing = [r for r in required if not context.get_result(r)]

if missing:
    logger.warning(f"Missing required analyzers for {symbol}: {missing}")
    self.stats.errors += 1
    return None

logger.info(f"  ✓ All analyzers completed")
```

**چگونه کار می‌کند؟**

در این مرحله، **11 Analyzer** به صورت ترتیبی اجرا می‌شوند. هر Analyzer:
1. از `AnalysisContext` می‌خواند (DataFrame + اندیکاتورها)
2. تحلیل خود را انجام می‌دهد
3. نتیجه را در `context.results` ذخیره می‌کند

#### ساختار Analyzers

**محل:** `orchestrator.py:209-248`

`self.analyzers` یک **Dictionary** است که در `__init__` ساخته می‌شود:

```python
def _initialize_analyzers(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize all 11 analyzers (10 original + VolumePatternAnalyzer).

    Returns:
        Dictionary of analyzer_name -> analyzer_instance
    """
    analyzers = {}

    # تعریف همه analyzer classes
    analyzer_classes = {
        'trend': TrendAnalyzer,
        'momentum': MomentumAnalyzer,
        'volume': VolumeAnalyzer,
        'volume_patterns': VolumePatternAnalyzer,
        'patterns': PatternAnalyzer,
        'support_resistance': SRAnalyzer,
        'volatility': VolatilityAnalyzer,
        'harmonic': HarmonicAnalyzer,
        'channel': ChannelAnalyzer,
        'cyclical': CyclicalAnalyzer,
        'htf': HTFAnalyzer
    }

    # چک کردن اینکه کدام analyzers فعال هستند
    enabled = config.get('orchestrator', {}).get('enabled_analyzers', list(analyzer_classes.keys()))

    # ساخت instance از هر analyzer
    for name, analyzer_class in analyzer_classes.items():
        if name in enabled:
            try:
                analyzers[name] = analyzer_class(config)
                logger.debug(f"Initialized {name} analyzer")
            except Exception as e:
                logger.error(f"Failed to initialize {name} analyzer: {e}")

    logger.info(f"Initialized {len(analyzers)}/11 analyzers")

    return analyzers
```

**نکات مهم:**
- `self.analyzers` یک `Dict[str, BaseAnalyzer]` است نه list
- کلیدها = نام analyzer: `'trend'`, `'momentum'`, `'volume'`, ...
- مقادیر = instance های analyzer classes
- می‌توان از طریق config کنترل کرد کدام analyzers فعال باشند

#### متد اجرای Analyzers

**محل:** `orchestrator.py:528-535`

```python
def _run_analyzers(self, context: AnalysisContext) -> None:
    """Run all enabled analyzers."""
    # چون self.analyzers یک dictionary است، با .items() iterate می‌کنیم
    for analyzer_name, analyzer in self.analyzers.items():
        try:
            analyzer.analyze(context)  # هر analyzer متد analyze() دارد
            logger.debug(f"  ✓ {analyzer_name} completed")
        except Exception as e:
            logger.error(f"  ✗ {analyzer_name} failed: {e}", exc_info=True)
```

**تفاوت با مستندات قبلی:**
- ✅ استفاده از `.items()` برای iterate کردن dictionary
- ✅ دسترسی به `analyzer_name` برای logging بهتر
- ✅ emoji در log messages (`✓` و `✗`)
- ✅ `exc_info=True` برای traceback کامل

**لیست 11 Analyzer:**

| # | Analyzer | مسئولیت | خروجی در context |
|---|----------|---------|------------------|
| 1 | **TrendAnalyzer** | تشخیص ترند (جهت، قدرت، فاز) | `context.results['trend']` |
| 2 | **MomentumAnalyzer** | تشخیص مومنتوم با 5 MACD Market Types | `context.results['momentum']` |
| 3 | **VolumeAnalyzer** | تحلیل حجم با وزن‌دهی Multi-TF | `context.results['volume']` |
| 4 | **PatternAnalyzer** | تشخیص الگوها با Recency Scoring | `context.results['pattern']` |
| 5 | **SRAnalyzer** | تشخیص Support/Resistance با ATR × 0.3 | `context.results['sr']` |
| 6 | **VolatilityAnalyzer** | تحلیل نوسان با ATR% | `context.results['volatility']` |
| 7 | **HTFAnalyzer** | تحلیل تایم‌فریم بالاتر | `context.results['htf']` |
| 8 | **ChannelAnalyzer** | تحلیل کانال‌ها | `context.results['channel']` |
| 9 | **HarmonicAnalyzer** | تشخیص الگوهای هارمونیک | `context.results['harmonic']` |
| 10 | **CyclicalAnalyzer** | تشخیص چرخه‌های قیمتی | `context.results['cyclical']` |
| 11 | **VolumePatternAnalyzer** | تشخیص الگوهای حجمی | `context.results['volume_pattern']` |

**Analyzers اجباری:**

سیستم چک می‌کند که حداقل **3 Analyzer اجباری** کار کرده باشند:
- `trend` (ترند)
- `momentum` (مومنتوم)
- `volume` (حجم)

اگر هر کدام از این 3 نباشد، سیگنال رد می‌شود ❌.

---

### 3.2.1 معرفی اولین Analyzer: TrendAnalyzer

**کلاس:** `TrendAnalyzer` (محل: `signal_generation/analyzers/trend_analyzer.py`)

**مسئولیت:** تشخیص جهت، قدرت و فاز ترند با استفاده از EMAs.

**اندیکاتورهای مورد نیاز** (از قبل محاسبه شده):
- `ema_20`, `ema_50`, `ema_100` (میانگین‌های متحرک نمایی)
- `close` (قیمت)

**📌 نکته:** TrendAnalyzer فقط از EMAs استفاده می‌کند، نه SMAها. SMAs توسط IndicatorCalculator محاسبه می‌شوند اما در این analyzer استفاده نمی‌شوند.

**خروجی:**

```python
context.results['trend'] = {
    'status': 'ok',
    'direction': 'bullish',           # جهت ترند
    'strength': 3,                    # قدرت (1 تا 3)
    'phase': 'mature',                # فاز ترند (7 فاز)
    'ema_alignment': 'bullish_aligned',  # آرایش EMAs
    'price_position': 'above_both_emas',
    'ema_slopes': {                   # شیب EMAs
        'ema20': 0.0025,
        'ema50': 0.0018,
        'ema100': 0.0012
    },
    'confidence': 0.95,               # اطمینان (0-1)
    'details': {
        'close': 50000.0,
        'ema20': 49800.0,
        'ema50': 49200.0,
        'ema100': 48500.0
    }
}
```

---

#### 3.2.1.1 فلسفه TrendAnalyzer

**سوال:** چگونه ترند را تشخیص دهیم؟

**پاسخ:** با استفاده از **3 میانگین متحرک نمایی (EMA)** و تحلیل **موقعیت قیمت** نسبت به آن‌ها.

**چرا EMA؟**
- EMA به داده‌های جدید **وزن بیشتری** می‌دهد
- EMA سریع‌تر به تغییرات قیمت واکنش نشان می‌دهد
- EMA برای تشخیص ترند بهتر از SMA است

**3 EMA انتخاب شده:**
- **EMA 20:** کوتاه‌مدت، سریع (برای تشخیص تغییرات اولیه)
- **EMA 50:** میان‌مدت، متوسط (برای تأیید ترند)
- **EMA 100:** بلند‌مدت، کند (برای جهت کلی بازار)

**منطق تشخیص ترند:**

```
قیمت > EMA20 > EMA50 > EMA100 → ترند صعودی قوی ✅✅✅
قیمت < EMA20 < EMA50 < EMA100 → ترند نزولی قوی 🔴🔴🔴
غیر از این‌ها → ترند ضعیف یا رنج
```

---

#### 3.2.1.2 گام‌های تحلیل (10 گام)

**گام 1: بررسی فعال بودن**

```python
if not self._check_enabled():
    logger.debug("TrendAnalyzer disabled, skipping...")
    return
```

**گام 2: اعتبارسنجی داده‌ها**

```python
if not self._validate_context(context):
    logger.warning("Invalid context for TrendAnalyzer")
    return

# بررسی ستون‌های لازم:
required_columns = ['close', 'ema_20', 'ema_50', 'ema_100']
```

اگر هر کدام از ستون‌ها وجود نداشته باشد، تحلیل متوقف می‌شود.

**گام 3: خواندن داده‌های فعلی**

```python
df = context.df

# آخرین مقادیر:
current_close = df['close'].iloc[-1]
current_ema20 = df['ema_20'].iloc[-1]
current_ema50 = df['ema_50'].iloc[-1]
current_ema100 = df['ema_100'].iloc[-1]
```

**مثال:**
```python
current_close = 50,000 USDT
current_ema20 = 49,800 USDT
current_ema50 = 49,200 USDT
current_ema100 = 48,500 USDT
```

**گام 4: محاسبه شیب EMAs (Slope)**

**شیب چیست؟** میزان تغییر EMA در `N` کندل اخیر.

**فرمول:**
```python
slope = (EMA_now - EMA_before) / EMA_before
```

**کد:**
```python
def _calculate_ema_slopes(self, df: pd.DataFrame) -> Dict[str, float]:
    """
    محاسبه شیب (rate of change) برای هر EMA.
    """
    lookback = 5  # بررسی 5 کندل اخیر
    
    # شیب EMA20:
    ema20_slope = (
        (df['ema_20'].iloc[-1] - df['ema_20'].iloc[-lookback]) 
        / df['ema_20'].iloc[-lookback]
    )
    
    # مشابه برای EMA50 و EMA100
    ...
    
    return {
        'ema20': ema20_slope,
        'ema50': ema50_slope,
        'ema100': ema100_slope
    }
```

**مثال محاسبه:**
```python
# EMA20:
5 کندل قبل: 49,000 USDT
الان: 49,800 USDT

slope = (49,800 - 49,000) / 49,000 = 0.0163 (1.63% رشد) ✅

# اگر slope > 0 → صعودی
# اگر slope < 0 → نزولی
# اگر slope ≈ 0 → رنج
```

**گام 5: تعیین آرایش EMAs (Alignment)**

```python
def _determine_ema_alignment(
    self, close: float, ema20: float, ema50: float, ema100: float
) -> str:
    """
    تشخیص الگوی آرایش EMAs.
    """
    if ema20 > ema50 > ema100:
        return 'bullish_aligned'  # آرایش صعودی کامل ✅
    
    elif ema20 < ema50 < ema100:
        return 'bearish_aligned'  # آرایش نزولی کامل 🔴
    
    elif ema20 > ema50 and ema50 < ema100:
        return 'potential_bullish_reversal'  # احتمال برگشت به صعودی
    
    elif ema20 < ema50 and ema50 > ema100:
        return 'potential_bearish_reversal'  # احتمال برگشت به نزولی
    
    elif ema20 > ema50 > ema100 and close < ema20:
        return 'bullish_pullback'  # pullback در ترند صعودی
    
    elif ema20 < ema50 < ema100 and close > ema20:
        return 'bearish_pullback'  # pullback در ترند نزولی
    
    else:
        return 'mixed'  # آرایش مخلوط (بدون ترند واضح)
```

**جدول تمام حالات:**

| آرایش | شرح | مثال (قیمت = 50000) |
|-------|-----|---------------------|
| **bullish_aligned** | EMA20 > EMA50 > EMA100 | 49800 > 49200 > 48500 ✅ |
| **bearish_aligned** | EMA20 < EMA50 < EMA100 | 49800 < 49200 < 48500 🔴 |
| **potential_bullish_reversal** | EMA20 > EMA50 < EMA100 | 49800 > 49200 < 48500 |
| **potential_bearish_reversal** | EMA20 < EMA50 > EMA100 | 49800 < 49200 > 48500 |
| **bullish_pullback** | آرایش صعودی اما قیمت < EMA20 | close = 49600, 49800 > 49200 > 48500 |
| **bearish_pullback** | آرایش نزولی اما قیمت > EMA20 | close = 50200, 49800 < 49200 < 48500 |
| **mixed** | بقیه حالات | - |

**گام 6: تشخیص جهت و قدرت ترند**

```python
def _detect_trend(
    self, close, ema20, ema50, ema100, slopes, alignment
) -> Dict[str, Any]:
    """
    تشخیص جهت و قدرت ترند.
    
    قدرت ترند (Strength):
    - 3 = بسیار قوی (strong)
    - 2 = متوسط (moderate)
    - 1 = ضعیف (weak)
    - 0 = بدون ترند (sideways)
    - -1, -2, -3 = نزولی (bearish)
    """
    direction = 'neutral'
    strength = 0
    
    ema20_slope = slopes['ema20']
    ema50_slope = slopes['ema50']
    min_slope = 0.0001  # حداقل شیب برای تأیید ترند
    
    # ─── Strong Bullish (strength = 3) ───
    if (close > ema20 > ema50 > ema100 and 
        ema20_slope > min_slope and 
        ema50_slope > min_slope):
        direction = 'bullish'
        strength = 3  # بسیار قوی ✅✅✅
    
    # ─── Moderate Bullish (strength = 2) ───
    elif (close > ema20 > ema50 and 
          ema20_slope > min_slope):
        direction = 'bullish'
        strength = 2  # متوسط ✅✅
    
    # ─── Weak Bullish (strength = 1) ───
    elif close > ema20 and ema20_slope > min_slope:
        direction = 'bullish'
        strength = 1  # ضعیف ✅
    
    # ─── Strong Bearish (strength = -3) ───
    elif (close < ema20 < ema50 < ema100 and 
          ema20_slope < -min_slope and 
          ema50_slope < -min_slope):
        direction = 'bearish'
        strength = -3  # بسیار قوی 🔴🔴🔴
    
    # ─── Moderate Bearish (strength = -2) ───
    elif (close < ema20 < ema50 and 
          ema20_slope < -min_slope):
        direction = 'bearish'
        strength = -2  # متوسط 🔴🔴
    
    # ─── Weak Bearish (strength = -1) ───
    elif close < ema20 and ema20_slope < -min_slope:
        direction = 'bearish'
        strength = -1  # ضعیف 🔴
    
    # ─── Bullish Pullback ───
    elif close < ema50 and ema20 > ema50 and ema50_slope > 0:
        direction = 'bullish_pullback'
        strength = 1
    
    # ─── Bearish Pullback ───
    elif close > ema50 and ema20 < ema50 and ema50_slope < 0:
        direction = 'bearish_pullback'
        strength = -1
    
    # ─── Sideways / Neutral ───
    else:
        direction = 'sideways'
        strength = 0
    
    return {
        'direction': direction,
        'strength': strength
    }
```

**جدول قدرت ترند:**

| Strength | شرح | شرایط | مثال |
|----------|-----|-------|------|
| **3** | صعودی خیلی قوی | قیمت > EMA20 > EMA50 > EMA100 + شیب‌ها مثبت | close=50000, ema20=49800, ema50=49200, ema100=48500, slope20=0.002 ✅ |
| **2** | صعودی متوسط | قیمت > EMA20 > EMA50 + شیب EMA20 مثبت | close=50000, ema20=49800, ema50=49200, slope20=0.001 |
| **1** | صعودی ضعیف | قیمت > EMA20 + شیب EMA20 مثبت | close=50000, ema20=49800 |
| **0** | رنج/خنثی | هیچ شرطی برقرار نیست | - |
| **-1** | نزولی ضعیف | قیمت < EMA20 + شیب EMA20 منفی | close=48000, ema20=48500, slope20=-0.001 |
| **-2** | نزولی متوسط | قیمت < EMA20 < EMA50 + شیب EMA20 منفی | close=48000, ema20=48500, ema50=49000 🔴 |
| **-3** | نزولی خیلی قوی | قیمت < EMA20 < EMA50 < EMA100 + شیب‌ها منفی | close=48000, ema20=48500, ema50=49000, ema100=49500 🔴🔴 |

**مثال محاسبه:**

```python
# داده‌ها:
close = 50,000 USDT
ema20 = 49,800 USDT
ema50 = 49,200 USDT
ema100 = 48,500 USDT

slope_ema20 = 0.0025  # 0.25% رشد
slope_ema50 = 0.0018  # 0.18% رشد

# بررسی:
# 1. آیا close > ema20 > ema50 > ema100؟
#    50000 > 49800 > 49200 > 48500 ✅

# 2. آیا slope_ema20 > 0.0001؟
#    0.0025 > 0.0001 ✅

# 3. آیا slope_ema50 > 0.0001؟
#    0.0018 > 0.0001 ✅

# نتیجه:
direction = 'bullish'
strength = 3  # ✅✅✅
```

**گام 7: تعیین فاز ترند (7 فاز)**

```python
def _determine_trend_phase(
    self, direction, strength, alignment, slopes
) -> str:
    """
    تعیین فاز ترند (7 فاز با تراز OLD SYSTEM).
    
    7 فاز:
    1. early: ترند تازه شروع شده (strength = 1)
    2. developing: ترند در حال رشد (strength = 2)
    3. mature: ترند کاملاً برقرار (strength = 3 + aligned + slopes strong)
    4. late: ترند در حال ضعیف شدن (strength = 3 but slopes weakening) ✨ NEW
    5. pullback: اصلاح موقت در ترند
    6. transition: در حال تغییر ترند
    7. undefined: بدون ترند مشخص
    """
    if direction == 'sideways' or direction == 'neutral':
        return 'undefined'
    
    if 'pullback' in direction:
        return 'pullback'
    
    # بررسی transition (احتمال برگشت):
    if 'reversal' in alignment:
        return 'transition'
    
    # برای ترندهای قوی (strength = 3)، تفکیک mature و late:
    if abs(strength) == 3:
        if 'aligned' in alignment:
            # بررسی اینکه آیا شیب‌ها در حال ضعیف شدن هستند:
            ema20_slope = slopes.get('ema20', 0)
            ema50_slope = slopes.get('ema50', 0)
            
            # فاز late: EMAs aligned اما شیب‌ها ضعیف می‌شوند
            if direction == 'bullish':
                # اگر شیب EMA20 کمتر از 80% شیب EMA50 باشد:
                if ema20_slope < ema50_slope * 0.8:
                    return 'late'  # در حال از دست دادن قدرت!
                
                # یا اگر شیب‌ها خیلی کم باشند:
                elif ema20_slope < 0.0002 and ema50_slope < 0.0002:
                    return 'late'
                
                else:
                    return 'mature'  # هنوز قوی ✅
            
            elif direction == 'bearish':
                # برای نزولی، شیب‌ها منفی هستند
                # بررسی می‌کنیم که آیا کمتر منفی می‌شوند (ضعیف شدن):
                if ema20_slope > ema50_slope * 0.8:
                    return 'late'
                elif ema20_slope > -0.0002 and ema50_slope > -0.0002:
                    return 'late'
                else:
                    return 'mature'
        else:
            # قوی اما aligned نیست = developing
            return 'developing'
    
    # ترند ضعیف (strength = 1) = early:
    if abs(strength) == 1:
        return 'early'
    
    # ترند متوسط (strength = 2) = developing:
    if abs(strength) == 2:
        return 'developing'
    
    return 'undefined'
```

**جدول 7 فاز:**

| فاز | شرح | شرایط | مناسب معامله؟ |
|-----|-----|-------|---------------|
| **early** | ترند تازه شروع شده | strength = 1 | ⚠️ محتاطانه |
| **developing** | ترند در حال رشد | strength = 2 | ✅ خوب |
| **mature** | ترند کاملاً برقرار | strength = 3 + aligned + slopes قوی | ✅✅✅ عالی |
| **late** ✨ | ترند در حال ضعیف شدن | strength = 3 + aligned but slopes ضعیف | ⚠️ احتیاط (نزدیک پایان) |
| **pullback** | اصلاح موقت | قیمت خلاف ترند اما EMAs aligned | ✅ فرصت ورود |
| **transition** | در حال تغییر ترند | آرایش reversal | ❌ خطرناک |
| **undefined** | بدون ترند | sideways | ❌ معامله نکن |

**مثال تشخیص فاز Late (ویژگی جدید ✨):**

```python
# ترند صعودی قوی (strength = 3):
direction = 'bullish'
strength = 3
alignment = 'bullish_aligned'

# شیب‌ها:
ema20_slope = 0.0008
ema50_slope = 0.0012  # بیشتر از EMA20!

# بررسی:
# آیا ema20_slope < ema50_slope × 0.8؟
0.0008 < 0.0012 × 0.8 = 0.00096
0.0008 < 0.00096 ✅

# نتیجه:
phase = 'late'  # در حال ضعیف شدن! ⚠️

# تفسیر:
# EMA20 باید سریع‌تر از EMA50 حرکت کند (چون کوتاه‌تر است)
# اما اینجا EMA20 کندتر شده → علامت ضعیف شدن مومنتوم
# این ویژگی از OLD SYSTEM گرفته شده است!
```

**گام 8: تعیین موقعیت قیمت**

```python
def _get_price_position(self, close, ema20, ema50) -> str:
    """
    توصیف موقعیت قیمت نسبت به EMAs.
    """
    if close > ema20 and close > ema50:
        return 'above_both_emas'  # بالای هر دو
    
    elif close > ema20 and close < ema50:
        return 'between_emas'  # بین دو EMA
    
    elif close < ema20 and close < ema50:
        return 'below_both_emas'  # پایین هر دو
    
    else:
        return 'at_ema'  # روی EMA
```

**گام 9: محاسبه Confidence (اطمینان)**

```python
def _calculate_confidence(self, strength, alignment, slopes) -> float:
    """
    محاسبه میزان اطمینان به تشخیص ترند (0-1).
    """
    confidence = 0.5  # شروع از 50%
    
    # ─── بر اساس قدرت ترند ───
    if abs(strength) == 3:
        confidence += 0.3  # ترند خیلی قوی
    elif abs(strength) == 2:
        confidence += 0.2  # ترند متوسط
    elif abs(strength) == 1:
        confidence += 0.1  # ترند ضعیف
    
    # ─── بر اساس آرایش EMAs ───
    if 'aligned' in alignment:
        confidence += 0.2  # آرایش کامل
    elif 'reversal' in alignment:
        confidence += 0.1  # احتمال برگشت
    
    # ─── بر اساس سازگاری شیب‌ها ───
    all_slopes = list(slopes.values())
    
    if all(s > 0 for s in all_slopes):
        confidence += 0.1  # همه شیب‌ها مثبت (سازگار)
    
    elif all(s < 0 for s in all_slopes):
        confidence += 0.1  # همه شیب‌ها منفی (سازگار)
    
    # محدود به 0-1:
    return min(confidence, 1.0)
```

**مثال محاسبه:**

```python
# داده‌ها:
strength = 3
alignment = 'bullish_aligned'
slopes = {'ema20': 0.0025, 'ema50': 0.0018, 'ema100': 0.0012}

# محاسبه:
confidence = 0.5
confidence += 0.3  # strength = 3
confidence += 0.2  # aligned
confidence += 0.1  # همه slopes مثبت

confidence = 1.0  # 100% اطمینان! ✅
```

**گام 10: ساخت نتیجه نهایی**

```python
result = {
    'status': 'ok',
    'direction': 'bullish',
    'strength': 3,
    'phase': 'mature',
    'ema_alignment': 'bullish_aligned',
    'price_position': 'above_both_emas',
    'ema_slopes': {
        'ema20': 0.0025,
        'ema50': 0.0018,
        'ema100': 0.0012
    },
    'confidence': 1.0,
    'details': {
        'close': 50000.0,
        'ema20': 49800.0,
        'ema50': 49200.0,
        'ema100': 48500.0
    }
}

# ذخیره در context:
context.add_result('trend', result)
```

---

#### 3.2.1.3 مثال کامل با محاسبات عددی

**سناریو:** BTC/USDT در تایم‌فریم 4h

**داده‌های ورودی:**

```python
df = {
    'close': [48000, 48500, 49000, 49500, 50000],  # 5 کندل اخیر
    'ema_20': [47500, 48000, 48500, 49000, 49800],
    'ema_50': [46800, 47200, 47800, 48500, 49200],
    'ema_100': [45500, 46000, 46800, 47500, 48500]
}

# مقادیر فعلی (آخرین کندل):
close = 50,000 USDT
ema20 = 49,800 USDT
ema50 = 49,200 USDT
ema100 = 48,500 USDT
```

**─── گام 1-3: OK ───**

**─── گام 4: محاسبه شیب EMAs ───**

```python
lookback = 5

# EMA20:
slope_ema20 = (49800 - 47500) / 47500 = 0.0484 (4.84% رشد) ✅

# EMA50:
slope_ema50 = (49200 - 46800) / 46800 = 0.0513 (5.13% رشد) ✅

# EMA100:
slope_ema100 = (48500 - 45500) / 45500 = 0.0659 (6.59% رشد) ✅

slopes = {
    'ema20': 0.0484,
    'ema50': 0.0513,
    'ema100': 0.0659
}
```

**─── گام 5: آرایش EMAs ───**

```python
# بررسی: ema20 > ema50 > ema100؟
49800 > 49200 > 48500 ✅

alignment = 'bullish_aligned'  # آرایش صعودی کامل ✅
```

**─── گام 6: تشخیص جهت و قدرت ───**

```python
# بررسی شرط Strong Bullish:
# 1. close > ema20 > ema50 > ema100؟
#    50000 > 49800 > 49200 > 48500 ✅

# 2. ema20_slope > 0.0001؟
#    0.0484 > 0.0001 ✅

# 3. ema50_slope > 0.0001؟
#    0.0513 > 0.0001 ✅

# نتیجه:
direction = 'bullish'
strength = 3  # بسیار قوی ✅✅✅
```

**─── گام 7: تعیین فاز ───**

```python
# strength = 3 و aligned
# بررسی اینکه آیا late است؟

# آیا ema20_slope < ema50_slope × 0.8؟
0.0484 < 0.0513 × 0.8 = 0.04104
0.0484 > 0.04104 ❌ (خیر، هنوز قوی است)

# نتیجه:
phase = 'mature'  # ترند کاملاً برقرار ✅✅✅
```

**─── گام 8: موقعیت قیمت ───**

```python
# close = 50000
# ema20 = 49800
# ema50 = 49200

# close > ema20 and close > ema50؟ ✅

price_position = 'above_both_emas'
```

**─── گام 9: محاسبه Confidence ───**

```python
confidence = 0.5
confidence += 0.3  # strength = 3
confidence += 0.2  # aligned
confidence += 0.1  # همه slopes مثبت

confidence = 1.0  # 100% ✅
```

**─── گام 10: نتیجه نهایی ───**

```python
{
    'status': 'ok',
    'direction': 'bullish',
    'strength': 3,
    'phase': 'mature',
    'ema_alignment': 'bullish_aligned',
    'price_position': 'above_both_emas',
    'ema_slopes': {
        'ema20': 0.0484,
        'ema50': 0.0513,
        'ema100': 0.0659
    },
    'confidence': 1.0,
    'details': {
        'close': 50000.0,
        'ema20': 49800.0,
        'ema50': 49200.0,
        'ema100': 48500.0
    }
}
```

**تفسیر:**

| ویژگی | مقدار | تفسیر |
|-------|-------|-------|
| **Direction** | bullish | ترند صعودی |
| **Strength** | 3 | بسیار قوی ✅✅✅ |
| **Phase** | mature | کاملاً برقرار (بهترین وقت معامله) |
| **Alignment** | bullish_aligned | آرایش کامل |
| **Confidence** | 1.0 | 100% اطمینان |
| **Slopes** | همه مثبت | همه EMAs در حال رشد |

**نتیجه‌گیری:** این یک **سیگنال خرید فوق‌العاده قوی** است! ✅🚀

---

#### 3.2.1.4 نحوه استفاده در Analyzers بعدی

```python
# در سایر Analyzers:
trend_result = context.get_result('trend')

if not trend_result:
    logger.warning("Trend analysis not available!")
    return

direction = trend_result.get('direction')
strength = trend_result.get('strength')
phase = trend_result.get('phase')
confidence = trend_result.get('confidence')

# استفاده:
if direction == 'bullish' and strength >= 2 and phase == 'mature':
    # ترند قوی صعودی - افزایش وزن سیگنال خرید
    buy_score += 20
    
elif phase == 'late':
    # ترند در حال ضعیف شدن - کاهش وزن
    buy_score -= 10
    
elif direction == 'bullish_pullback' and phase == 'pullback':
    # فرصت خرید در pullback
    buy_score += 15
```

---

#### 3.2.1.5 تنظیمات (Config)

```python
"analyzers": {
    "trend": {
        "enabled": True,
        
        # حداقل شیب برای تأیید ترند:
        "min_slope_threshold": 0.0001,  # 0.01%
        
        # تعداد کندل برای محاسبه شیب:
        "slope_lookback": 5,
        
        # آستانه Late Phase:
        "late_phase_slope_ratio": 0.8,  # EMA20 slope < EMA50 slope × 0.8
        "late_phase_min_slope": 0.0002  # حداقل شیب برای mature
    }
}
```

---

**✅ بخش 3.2.1 (TrendAnalyzer) تمام شد!**

**در این قسمت:**
- ✅ معماری و فلسفه TrendAnalyzer
- ✅ 10 گام تحلیل ترند
- ✅ 7 فاز ترند (شامل Late Phase جدید ✨)
- ✅ محاسبه قدرت ترند (1-3 scale)
- ✅ آرایش EMAs (7 حالت)
- ✅ محاسبه شیب EMAs
- ✅ محاسبه Confidence
- ✅ مثال کامل عددی با BTC/USDT
- ✅ نحوه استفاده در Analyzers بعدی

**قسمت بعدی:**
### 3.2.2 معرفی دومین Analyzer: MomentumAnalyzer (با 5 MACD Market Types)

ادامه می‌دهم...


---

## 3.2.2 معرفی دومین Analyzer: MomentumAnalyzer

**کلاس:** `MomentumAnalyzer` (محل: `signal_generation/analyzers/momentum_analyzer.py`)

**مسئولیت:** تحلیل مومنتوم بازار با استفاده از RSI, MACD, Stochastic و MFI.

**ویژگی‌های کلیدی:**
1. تحلیل RSI (overbought/oversold)
2. تحلیل MACD (crossovers, histogram, divergence)
3. تحلیل Stochastic
4. **تشخیص نوع بازار MACD (5 Market Types)** ✨
5. تحلیل پیشرفته MACD:
   - DIF zero crosses (با شمارش first/second)
   - DIF trendline breaks
   - Histogram patterns پیشرفته
6. تشخیص Divergence
7. MFI (Money Flow Index) analysis

**اندیکاتورهای مورد نیاز** (از قبل محاسبه شده):
- `rsi` (Relative Strength Index)
- `macd`, `macd_signal`, `macd_hist`
- `slowk`, `slowd` (Stochastic)
- `ema_20`, `ema_50` (برای Market Type detection)

**📌 نکته:** MFI (Money Flow Index) **optional** است. اگر موجود باشد تحلیل می‌شود، اما اندیکاتور MFI در سیستم فعلی محاسبه نمی‌شود.

**خروجی:**

```python
context.results['momentum'] = {
    'status': 'ok',
    'direction': 'bullish',          # جهت مومنتوم
    'strength': 2.5,                 # قدرت (0-3)
    'rsi_signal': 'oversold',        # وضعیت RSI
    'macd_signal': {...},            # تحلیل MACD
    'macd_market_type': 'A_bullish_strong',  # نوع بازار (5 نوع) ✨
    'advanced_macd_signals': [...],  # سیگنال‌های پیشرفته MACD
    'stoch_signal': {...},           # تحلیل Stochastic
    'divergence': {...},             # واگرایی (اگر وجود داشته باشد)
    'confidence': 0.85,              # اطمینان (0-1)
    'signals': [...],                # لیست تمام سیگنال‌ها
    'details': {
        'rsi': 28.5,
        'macd': 0.0012,
        'macd_signal': 0.0008,
        'macd_hist': 0.0004,
        'slowk': 25.0,
        'slowd': 22.0
    }
}
```

---

### 3.2.2.1 فلسفه MomentumAnalyzer

**سوال:** چگونه مومنتوم را تشخیص دهیم؟

**پاسخ:** با ترکیب **4 اندیکاتور قوی**:
1. **RSI:** برای تشخیص overbought/oversold
2. **MACD:** برای تشخیص تغییر جهت و قدرت مومنتوم
3. **Stochastic:** برای تأیید نقاط برگشت
4. **MFI:** برای تأیید با حجم

**منطق:**

```
RSI < 30 + MACD bullish crossover + Stochastic oversold → سیگنال خرید قوی ✅✅✅
RSI > 70 + MACD bearish crossover + Stochastic overbought → سیگنال فروش قوی 🔴🔴🔴
```

---

### 3.2.2.2 MACD Market Type Detection (5 نوع بازار) ✨

یکی از **ویژگی‌های کلیدی** سیستم که برای تشخیص وضعیت بازار استفاده می‌شود.

**منطق:** ترکیب **3 فاکتور** برای تعیین نوع بازار:
1. **DIF (MACD Line):** بالای/پایین صفر
2. **HIST (Histogram):** مثبت/منفی
3. **EMA Alignment:** EMA20 > EMA50 یا EMA20 < EMA50

**کد:**

```python
def _detect_macd_market_type(self, df: pd.DataFrame) -> str:
    """
    تشخیص نوع بازار بر اساس DIF, HIST و EMA alignment.
    """
    curr_dif = df['macd'].iloc[-1]      # خط MACD
    curr_hist = df['macd_hist'].iloc[-1]  # هیستوگرام
    
    curr_ema20 = df['ema_20'].iloc[-1]
    curr_ema50 = df['ema_50'].iloc[-1]
    ema_bullish = curr_ema20 > curr_ema50
    
    # ─── تشخیص نوع بازار ───
    
    if curr_dif > 0 and curr_hist > 0 and ema_bullish:
        return "A_bullish_strong"      # صعودی قوی ✅✅✅
    
    elif curr_dif > 0 and curr_hist < 0 and ema_bullish:
        return "B_bullish_normal"      # صعودی عادی (ضعیف‌تر از A) ⚠️

    elif curr_dif < 0 and curr_hist < 0 and not ema_bullish:
        return "C_bearish_strong"      # نزولی قوی 🔴🔴🔴

    elif curr_dif < 0 and curr_hist > 0 and not ema_bullish:
        return "D_bearish_normal"      # نزولی عادی (ضعیف‌تر از C) ⚠️
    
    else:
        return "X_transition"          # انتقال (غیر قابل پیش‌بینی) ❌
```

#### جدول 5 Market Type کامل

| Market Type | DIF | HIST | EMA20 vs EMA50 | شرح | مناسب معامله |
|-------------|-----|------|----------------|-----|--------------|
| **A_bullish_strong** | + | + | EMA20 > EMA50 | صعودی قوی (بهترین برای خرید) | ✅✅✅ |
| **B_bullish_normal** | + | - | EMA20 > EMA50 | صعودی عادی (ضعیف‌تر، HIST منفی) | ⚠️ |
| **C_bearish_strong** | - | - | EMA20 < EMA50 | نزولی قوی (بهترین برای فروش) | 🔴🔴🔴 |
| **D_bearish_normal** | - | + | EMA20 < EMA50 | نزولی عادی (ضعیف‌تر، HIST مثبت) | ⚠️ |
| **X_transition** | مختلط | مختلط | - | انتقال (غیر قابل پیش‌بینی) | ❌ |

**توضیح 5 نوع:**

**A - Bullish Strong (صعودی قوی):**
```python
DIF > 0        # مومنتوم مثبت
HIST > 0       # در حال افزایش
EMA20 > EMA50  # ترند صعودی

# مثال:
DIF = 0.0025
HIST = 0.0008
EMA20 = 50000, EMA50 = 49500

# نتیجه: A_bullish_strong ✅✅✅
# بهترین حالت برای خرید!
```

**B - Bullish Normal (صعودی عادی):**
```python
DIF > 0        # هنوز مثبت
HIST < 0       # اما کاهش یافته! ⚠️
EMA20 > EMA50  # ترند کلی صعودی

# مثال:
DIF = 0.0015
HIST = -0.0005  # منفی شده!
EMA20 = 50000, EMA50 = 49500

# نتیجه: B_bullish_normal ⚠️
# صعودی ضعیف‌تر (HIST منفی) - بهتر است صبر کنیم
```

**C - Bearish Strong (نزولی قوی):**
```python
DIF < 0        # مومنتوم منفی
HIST < 0       # در حال کاهش
EMA20 < EMA50  # ترند نزولی

# مثال:
DIF = -0.0025
HIST = -0.0008
EMA20 = 49500, EMA50 = 50000

# نتیجه: C_bearish_strong 🔴🔴🔴
# بهترین حالت برای فروش (short)!
```

**D - Bearish Normal (نزولی عادی):**
```python
DIF < 0        # هنوز منفی
HIST > 0       # اما افزایش یافته! ⚠️
EMA20 < EMA50  # ترند کلی نزولی

# مثال:
DIF = -0.0015
HIST = 0.0005  # مثبت شده!
EMA20 = 49500, EMA50 = 50000

# نتیجه: D_bearish_normal ⚠️
# نزولی ضعیف‌تر (HIST مثبت) - ممکن است ریباند موقت داشته باشد
```

**X - Transition (انتقال):**
```python
# شرایط مخلوط که هیچ الگوی واضحی ندارند
# مثلاً:
DIF > 0, HIST > 0, اما EMA20 < EMA50
یا
DIF < 0, HIST > 0, EMA20 > EMA50

# نتیجه: X_transition ❌
# خطرناک - بهتر است معامله نکنیم
```

---

### 3.2.2.3 تحلیل RSI

**کد:**

```python
def _analyze_rsi(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    تحلیل RSI indicator.
    """
    current_rsi = df['rsi'].iloc[-1]
    prev_rsi = df['rsi'].iloc[-2]
    
    # ─── تعیین سیگنال ───
    if current_rsi >= 70:  # rsi_overbought
        signal = 'overbought'   # اشباع خرید 🔴
    elif current_rsi <= 30:  # rsi_oversold
        signal = 'oversold'     # اشباع فروش ✅
    else:
        signal = 'neutral'      # خنثی
    
    # ─── بررسی عبور از سطوح ───
    rsi_crossing_up = (prev_rsi < 30 and current_rsi >= 30)
    rsi_crossing_down = (prev_rsi > 70 and current_rsi <= 70)
    
    # ─── بررسی برگشت (OLD SYSTEM logic) ───
    # Bullish reversal: RSI < 30 AND RSI بالا می‌رود
    oversold_reversal = (current_rsi < 30 and current_rsi > prev_rsi)
    
    # Bearish reversal: RSI > 70 AND RSI پایین می‌آید
    overbought_reversal = (current_rsi > 70 and current_rsi < prev_rsi)
    
    return {
        'value': current_rsi,
        'signal': signal,
        'crossing_up': rsi_crossing_up,
        'crossing_down': rsi_crossing_down,
        'bullish': oversold_reversal,   # سیگنال خرید
        'bearish': overbought_reversal  # سیگنال فروش
    }
```

**مثال:**

```python
# ─── سناریو 1: Oversold Reversal (خرید) ───
prev_rsi = 26.0
current_rsi = 28.5  # هنوز زیر 30 اما بالا رفته!

signal = 'oversold'
oversold_reversal = True  # ✅ سیگنال خرید (امتیاز: 2.3)

# تفسیر: RSI زیر 30 بود و الان شروع به بالا رفتن کرده
# این نشان‌دهنده شروع برگشت است!


# ─── سناریو 2: Overbought Reversal (فروش) ───
prev_rsi = 74.0
current_rsi = 71.5  # هنوز بالای 70 اما پایین آمده!

signal = 'overbought'
overbought_reversal = True  # 🔴 سیگنال فروش (امتیاز: 2.3)

# تفسیر: RSI بالای 70 بود و الان شروع به پایین آمدن کرده
# این نشان‌دهنده شروع ریزش است!
```

**امتیازدهی:**
- Oversold reversal: **+2.3** (خرید)
- Overbought reversal: **+2.3** (فروش)

---

### 3.2.2.4 تحلیل MACD اصلی

**کد:**

```python
def _analyze_macd(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    تحلیل MACD indicator.
    """
    current_macd = df['macd'].iloc[-1]
    current_signal = df['macd_signal'].iloc[-1]
    current_hist = df['macd_hist'].iloc[-1]
    
    prev_macd = df['macd'].iloc[-2]
    prev_signal = df['macd_signal'].iloc[-2]
    prev_hist = df['macd_hist'].iloc[-2]
    
    # ─── تشخیص کراس‌اوورها ───
    bullish_crossover = (prev_macd <= prev_signal and 
                        current_macd > current_signal)
    
    bearish_crossover = (prev_macd >= prev_signal and 
                        current_macd < current_signal)
    
    # ─── تحلیل هیستوگرام ───
    hist_increasing = current_hist > prev_hist
    hist_positive = current_hist > 0
    
    # ─── تعیین جهت ───
    if current_macd > current_signal:
        direction = 'bullish'
    elif current_macd < current_signal:
        direction = 'bearish'
    else:
        direction = 'neutral'
    
    return {
        'value': current_macd,
        'signal_value': current_signal,
        'histogram': current_hist,
        'direction': direction,
        'bullish_crossover': bullish_crossover,
        'bearish_crossover': bearish_crossover,
        'hist_increasing': hist_increasing,
        'hist_positive': hist_positive
    }
```

**مثال Bullish Crossover:**

```python
# کندل قبل:
prev_macd = 0.00048
prev_signal = 0.00052  # MACD زیر Signal

# کندل فعلی:
current_macd = 0.00055
current_signal = 0.00053  # MACD بالای Signal ✅

# نتیجه:
bullish_crossover = True  # سیگنال خرید (امتیاز: 2.2)

# تفسیر:
# MACD از زیر Signal عبور کرد و به بالا رفت
# این یک سیگنال خرید قوی است! 🚀
```

**امتیازدهی:**
- Bullish crossover: **+2.2** (خرید)
- Bearish crossover: **+2.2** (فروش)

---

### 3.2.2.5 تحلیل Stochastic

**کد:**

```python
def _analyze_stochastic(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    تحلیل Stochastic indicator.
    """
    current_k = df['slowk'].iloc[-1]  # %K
    current_d = df['slowd'].iloc[-1]  # %D
    
    prev_k = df['slowk'].iloc[-2]
    prev_d = df['slowd'].iloc[-2]
    
    # ─── تعیین سیگنال ───
    if current_k >= 80:  # stoch_overbought
        signal = 'overbought'
    elif current_k <= 20:  # stoch_oversold
        signal = 'oversold'
    else:
        signal = 'neutral'
    
    # ─── تشخیص کراس‌اوورها ───
    bullish_crossover = (prev_k <= prev_d and current_k > current_d)
    bearish_crossover = (prev_k >= prev_d and current_k < current_d)
    
    return {
        'k_value': current_k,
        'd_value': current_d,
        'signal': signal,
        'bullish_crossover': bullish_crossover,
        'bearish_crossover': bearish_crossover
    }
```

**مثال قوی‌ترین سیگنال:**

```python
# Stochastic Bullish Crossover در ناحیه Oversold:

current_k = 22  # کمی بالای 20 (oversold)
current_d = 18
prev_k = 18     # قبلاً زیر %D بود
prev_d = 20

# بررسی:
signal = 'oversold'  # هنوز در ناحیه oversold
bullish_crossover = True  # %K از زیر %D عبور کرد ✅

# نتیجه:
# این قوی‌ترین سیگنال خرید Stochastic است!
# امتیاز: 2.5

# تفسیر:
# 1. Stochastic در ناحیه oversold است (< 20)
# 2. %K از %D به بالا عبور کرد
# 3. این نشان‌دهنده شروع برگشت صعودی است! 🚀
```

**امتیازدهی:**
- Oversold + Bullish crossover: **+2.5** (خرید) ✅✅
- Overbought + Bearish crossover: **+2.5** (فروش) 🔴🔴

---

### 3.2.2.6 تحلیل MFI (Money Flow Index)

**MFI چیست؟** RSI وزن‌دار شده با حجم - اندیکاتور قوی‌تر از RSI!

**کد:**

```python
def _check_mfi_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    بررسی سیگنال‌های MFI.
    """
    mfi = df['mfi'].iloc[-1]
    mfi_prev = df['mfi'].iloc[-2]
    
    bullish_signal = 0.0
    bearish_signal = 0.0
    
    # ─── MFI Oversold Reversal (خرید) ───
    # MFI < 20 AND MFI بالا می‌رود
    if mfi < 20 and mfi > mfi_prev:
        bullish_signal = 2.4
        signal_type = 'mfi_oversold_reversal'
    
    # ─── MFI Overbought Reversal (فروش) ───
    # MFI > 80 AND MFI پایین می‌آید
    elif mfi > 80 and mfi < mfi_prev:
        bearish_signal = 2.4
        signal_type = 'mfi_overbought_reversal'
    
    return {
        'bullish_signal': bullish_signal,
        'bearish_signal': bearish_signal,
        'active': bullish_signal > 0 or bearish_signal > 0,
        'signal_type': signal_type,
        'mfi_value': mfi
    }
```

**مثال:**

```python
# MFI Oversold Reversal:
mfi_prev = 16.0
mfi = 18.5  # هنوز زیر 20 اما بالا رفته!

# نتیجه:
bullish_signal = 2.4  # ✅ سیگنال خرید قوی

# تفسیر:
# MFI زیر 20 بود (oversold با توجه به حجم)
# الان بالا رفته - نشان‌دهنده ورود پول جدید
# این سیگنال قوی‌تر از RSI است چون حجم را هم در نظر می‌گیرد!
```

**امتیازدهی:**
- MFI oversold reversal: **+2.4** (خرید)
- MFI overbought reversal: **+2.4** (فروش)

---

### 3.2.2.7 MACD Zero Line Cross

**کد:**

```python
def _check_macd_zero_cross(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    بررسی عبور MACD از خط صفر.
    """
    macd = df['macd'].iloc[-1]
    macd_prev = df['macd'].iloc[-2]
    
    bullish_signal = 0.0
    bearish_signal = 0.0
    
    # ─── MACD عبور از صفر به بالا (خرید) ───
    if macd_prev <= 0 and macd > 0:
        bullish_signal = 1.8
        signal_type = 'macd_zero_cross_up'
    
    # ─── MACD عبور از صفر به پایین (فروش) ───
    elif macd_prev >= 0 and macd < 0:
        bearish_signal = 1.8
        signal_type = 'macd_zero_cross_down'
    
    return {
        'bullish_signal': bullish_signal,
        'bearish_signal': bearish_signal,
        'active': bullish_signal > 0 or bearish_signal > 0,
        'signal_type': signal_type,
        'macd_value': macd
    }
```

**مثال:**

```python
# عبور از صفر به بالا:
macd_prev = -0.00005  # منفی
macd = 0.00012        # مثبت شد! ✅

# نتیجه:
bullish_signal = 1.8  # سیگنال خرید

# تفسیر:
# MACD از منفی به مثبت تبدیل شد
# این نشان‌دهنده تغییر جهت مومنتوم از نزولی به صعودی است!
```

**امتیازدهی:**
- MACD zero cross up: **+1.8** (خرید)
- MACD zero cross down: **+1.8** (فروش)

---

### 3.2.2.8 تشخیص Divergence (واگرایی)

**Divergence چیست؟** عدم هماهنگی بین قیمت و RSI - یکی از قوی‌ترین سیگنال‌ها!

**کد:**

```python
def _detect_divergences(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    تشخیص واگرایی صعودی/نزولی بین قیمت و RSI.
    """
    lookback = min(14, len(df))  # divergence_lookback
    recent_df = df.tail(lookback)
    
    # پیدا کردن کف‌ها و سقف‌های قیمت:
    price_lows = recent_df['low'].rolling(window=3, center=True).min()
    price_highs = recent_df['high'].rolling(window=3, center=True).max()
    
    # پیدا کردن کف‌ها و سقف‌های RSI:
    rsi_lows = recent_df['rsi'].rolling(window=3, center=True).min()
    rsi_highs = recent_df['rsi'].rolling(window=3, center=True).max()
    
    # ─── واگرایی صعودی (Bullish Divergence) ───
    # قیمت: کف پایین‌تر
    # RSI: کف بالاتر → سیگنال خرید! ✅
    
    price_lower_low = price_lows.iloc[-1] < price_lows.iloc[-5]
    rsi_higher_low = rsi_lows.iloc[-1] > rsi_lows.iloc[-5]
    
    if price_lower_low and rsi_higher_low:
        return {
            'type': 'bullish',
            'strength': 'strong' if rsi_lows.iloc[-1] < 40 else 'moderate'
        }
    
    # ─── واگرایی نزولی (Bearish Divergence) ───
    # قیمت: سقف بالاتر
    # RSI: سقف پایین‌تر → سیگنال فروش! 🔴
    
    price_higher_high = price_highs.iloc[-1] > price_highs.iloc[-5]
    rsi_lower_high = rsi_highs.iloc[-1] < rsi_highs.iloc[-5]
    
    if price_higher_high and rsi_lower_high:
        return {
            'type': 'bearish',
            'strength': 'strong' if rsi_highs.iloc[-1] > 60 else 'moderate'
        }
    
    return None
```

**مثال Bullish Divergence:**

```python
# 5 کندل قبل:
price_low_1 = 49000
rsi_low_1 = 25

# الان (کندل فعلی):
price_low_2 = 48500  # قیمت پایین‌تر رفت!
rsi_low_2 = 30       # اما RSI بالاتر آمد! ✅

# بررسی:
price_lower_low = True  # 48500 < 49000
rsi_higher_low = True   # 30 > 25

# نتیجه:
divergence = {
    'type': 'bullish',
    'strength': 'strong'  # چون RSI < 40
}

# امتیاز: +3.5 (خرید)

# تفسیر:
# قیمت در حال ریزش است (کف جدید پایین‌تر)
# اما RSI قوی‌تر شده (فشار فروش کاهش یافته)
# این نشان‌دهنده برگشت صعودی قریب‌الوقوع است! 🚀🚀🚀
```

**امتیازدهی:**
- Bullish divergence: **+3.5** (خرید) 🚀🚀
- Bearish divergence: **+3.5** (فروش) 🔴🔴

---

**✅ قسمت اول Section 3.2.2 تمام شد!**

**تا اینجا پوشش داده شد:**
- ✅ فلسفه MomentumAnalyzer
- ✅ MACD Market Type Detection (5 نوع بازار: A, B, C, D, X)
- ✅ تحلیل RSI (oversold/overbought reversal)
- ✅ تحلیل MACD اصلی (crossovers)
- ✅ تحلیل Stochastic
- ✅ تحلیل MFI (Money Flow Index)
- ✅ MACD Zero Line Cross
- ✅ تشخیص Divergence

**قسمت بعدی (3.2.2.9):**
سیگنال‌های پیشرفته MACD از OLD SYSTEM:
- DIF Zero Crosses (با شمارش first/second)
- DIF Trendline Breaks
- Advanced Histogram Analysis (shrink head, pull feet, divergences, kill long bin)

ادامه می‌دهم...


---

### 3.2.2.9 سیگنال‌های پیشرفته MACD (از OLD SYSTEM) ✨

این بخش شامل **3 دسته سیگنال پیشرفته** است که از OLD SYSTEM گرفته شده است.

#### الف) DIF Zero Crosses (با شمارش first/second)

**DIF چیست؟** DIF همان خط MACD است (تفاوت بین EMA12 و EMA26).

**منطق:** عبور DIF از خط صفر نشان‌دهنده تغییر جهت مومنتوم است.

**ویژگی ویژه:** شمارش اینکه چندمین بار است که DIF از صفر عبور می‌کند!
- **First cross:** اولین عبور (قوی‌تر)
- **Second cross:** دومین عبور (ضعیف‌تر - ممکن است false signal باشد)

**کد:**

```python
def _detect_dif_zero_crosses(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    تشخیص عبور DIF از خط صفر با شمارش first/second.
    """
    signals = []
    
    dif_vals = df['macd'].values
    
    # شمارش تعداد دفعات عبور:
    cross_up_count = 0
    cross_down_count = 0
    
    for i in range(1, len(dif_vals)):
        # ─── عبور به بالا ───
        crossed_up = (dif_vals[i - 1] < 0 and dif_vals[i] > 0)
        
        if crossed_up:
            cross_up_count += 1
            
            if i == len(dif_vals) - 1:  # فقط کندل فعلی
                signal_type = (
                    f"dif_cross_zero_up_first" 
                    if cross_up_count == 1 
                    else f"dif_cross_zero_up_second"
                )
                
                score = pattern_scores.get(signal_type, 2.0)
                
                signals.append({
                    'type': signal_type,
                    'direction': 'bullish',
                    'score': score,
                    'strength': 1.0
                })
        
        # ─── عبور به پایین ───
        crossed_down = (dif_vals[i - 1] > 0 and dif_vals[i] < 0)
        
        if crossed_down:
            cross_down_count += 1
            
            if i == len(dif_vals) - 1:
                signal_type = (
                    f"dif_cross_zero_down_first"
                    if cross_down_count == 1
                    else f"dif_cross_zero_down_second"
                )
                
                score = pattern_scores.get(signal_type, 2.0)
                
                signals.append({
                    'type': signal_type,
                    'direction': 'bearish',
                    'score': score,
                    'strength': 1.0
                })
    
    return signals
```

**مثال:**

```python
# سناریو: DIF در 100 کندل اخیر:

کندل 50: DIF = -0.0005 (منفی)
کندل 51: DIF = 0.0002  (مثبت شد - FIRST CROSS UP) ✅
کندل 60: DIF = -0.0003 (دوباره منفی شد)
کندل 61: DIF = 0.0001  (دوباره مثبت شد - SECOND CROSS UP) ⚠️

# نتیجه برای کندل 51:
{
    'type': 'dif_cross_zero_up_first',
    'direction': 'bullish',
    'score': 2.0,  # اولین عبور - قوی‌تر
    'strength': 1.0
}

# نتیجه برای کندل 61:
{
    'type': 'dif_cross_zero_up_second',
    'direction': 'bullish',
    'score': 1.5,  # دومین عبور - ضعیف‌تر (احتمال false signal)
    'strength': 1.0
}

# تفسیر:
# - اولین عبور: معمولاً سیگنال قوی است ✅
# - دومین عبور: ممکن است false signal باشد (بازار نوسانی) ⚠️
```

**امتیازدهی:**
- First cross up: **+2.0** (خرید)
- Second cross up: **+1.5** (خرید - ضعیف‌تر)
- First cross down: **+2.0** (فروش)
- Second cross down: **+1.5** (فروش - ضعیف‌تر)

---

#### ب) DIF Trendline Breaks

**منطق:** تشخیص شکست خطوط ترند روی DIF (خود خط MACD).

**روش:**
1. پیدا کردن قله‌ها (peaks) و دره‌ها (valleys) در DIF
2. رسم خط ترند بین 2 نقطه آخر
3. بررسی شکست خط ترند

**کد:**

```python
def _detect_dif_trendline_breaks(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    تشخیص شکست خطوط ترند DIF.
    """
    signals = []
    
    # دریافت 30 کندل اخیر DIF:
    dif_window = df['macd'].iloc[-30:]
    
    # Smooth کردن DIF برای پیدا کردن peaks:
    smooth_dif = scipy_signal.medfilt(dif_window.values, kernel_size=3)
    
    # پیدا کردن peaks و valleys:
    peaks_idx, valleys_idx = _find_peaks_and_valleys(
        smooth_dif,
        distance=3,
        prominence_factor=0.1
    )
    
    # ─── بررسی شکست خط مقاومت (به بالا) ───
    if len(peaks_idx) >= 2:
        break_signal = _check_trendline_break(
            smooth_dif,
            dif_window.values,
            peaks_idx,
            is_resistance=True
        )
        
        if break_signal:
            signals.append(break_signal)
    
    # ─── بررسی شکست خط حمایت (به پایین) ───
    if len(valleys_idx) >= 2:
        break_signal = _check_trendline_break(
            smooth_dif,
            dif_window.values,
            valleys_idx,
            is_resistance=False
        )
        
        if break_signal:
            signals.append(break_signal)
    
    return signals


def _check_trendline_break(
    smooth_data: np.ndarray,
    raw_data: np.ndarray,
    points: List[int],
    is_resistance: bool
) -> Optional[Dict[str, Any]]:
    """
    بررسی شکست خط ترند.
    """
    # استفاده از 2 نقطه آخر برای رسم خط ترند:
    p1_idx, p2_idx = points[-2], points[-1]
    p1_val, p2_val = smooth_data[p1_idx], smooth_data[p2_idx]
    
    # محاسبه معادله خط: y = k*x + b
    k = (p2_val - p1_val) / (p2_idx - p1_idx)
    b = p1_val - k * p1_idx
    
    # بررسی کندل‌های بعد از p2 برای شکست:
    for i in range(p2_idx + 1, len(raw_data)):
        trendline_val = k * i + b
        current_val = raw_data[i]
        margin = abs(current_val * 0.01)  # 1% حاشیه
        
        # شکست به بالا (صعودی):
        if is_resistance and current_val > trendline_val + margin:
            return {
                'type': 'dif_trendline_break_up',
                'direction': 'bullish',
                'score': 3.0,  # سیگنال قوی
                'strength': 1.0
            }
        
        # شکست به پایین (نزولی):
        elif not is_resistance and current_val < trendline_val - margin:
            return {
                'type': 'dif_trendline_break_down',
                'direction': 'bearish',
                'score': 3.0,  # سیگنال قوی
                'strength': 1.0
            }
    
    return None
```

**مثال تصویری:**

```
DIF Line:
         ●
        / \         ● ← Peak 2
       /   \       /
      /     \     /
     ●       \   /  ← خط ترند نزولی (مقاومت)
  Peak 1      \ /
               ●
                \
                 ● ← شکست به بالا! ✅


# تحلیل:
# 1. Peak 1 و Peak 2 را پیدا کردیم
# 2. خط ترند بین آن‌ها رسم کردیم (مقاومت)
# 3. DIF از خط ترند به بالا شکست زد! ✅
# 4. سیگنال خرید قوی (امتیاز: 3.0) 🚀
```

**امتیازدهی:**
- Trendline break up: **+3.0** (خرید) 🚀
- Trendline break down: **+3.0** (فروش) 🔴

---

#### ج) Advanced Histogram Analysis

هیستوگرام MACD می‌تواند الگوهای قوی برای برگشت ارائه دهد.

**4 الگوی اصلی:**
1. **Shrink Head** (کوچک شدن سر): کاهش قله هیستوگرام مثبت → سیگنال فروش
2. **Pull Feet** (کشیدن پا): کاهش دره هیستوگرام منفی → سیگنال خرید
3. **Top Divergence** (واگرایی در سقف): قیمت ↑ اما histogram ↓ → سیگنال فروش قوی
4. **Bottom Divergence** (واگرایی در کف): قیمت ↓ اما histogram ↑ → سیگنال خرید قوی
5. **Kill Long Bin** (کشتن بین طولانی): هیستوگرام مدام منفی → سیگنال فروش

**کد:**

```python
def _analyze_macd_histogram_advanced(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    تحلیل پیشرفته هیستوگرام MACD.
    """
    signals = []
    
    hist = df['macd_hist']
    close = df['close']
    
    # پیدا کردن peaks و valleys در هیستوگرام:
    peaks_idx, valleys_idx = _find_peaks_and_valleys(
        hist.values,
        distance=3,
        prominence_factor=0.1
    )
    
    # ─── 1. Shrink Head Pattern ───
    # قله هیستوگرام در ناحیه مثبت (نشان‌دهنده برگشت نزولی)
    
    for idx in peaks_idx:
        if idx < len(hist) - 10:  # باید نزدیک باشد
            continue
        
        if hist.iloc[idx] > 0:  # در ناحیه مثبت
            signals.append({
                'type': 'macd_hist_shrink_head',
                'direction': 'bearish',
                'score': 1.5,
                'strength': 0.8
            })
    
    # ─── 2. Pull Feet Pattern ───
    # دره هیستوگرام در ناحیه منفی (نشان‌دهنده برگشت صعودی)
    
    for idx in valleys_idx:
        if idx < len(hist) - 10:
            continue
        
        if hist.iloc[idx] < 0:  # در ناحیه منفی
            signals.append({
                'type': 'macd_hist_pull_feet',
                'direction': 'bullish',
                'score': 1.5,
                'strength': 0.8
            })
    
    # ─── 3. Top Divergence (قوی‌ترین!) ───
    # قیمت: سقف بالاتر
    # Histogram: سقف پایین‌تر → سیگنال فروش خیلی قوی! 🔴🔴🔴
    
    if len(peaks_idx) >= 2:
        p1_idx, p2_idx = peaks_idx[-2], peaks_idx[-1]
        
        if p2_idx > len(hist) - 15:  # نزدیک به الان
            hist_lower_high = hist.iloc[p2_idx] < hist.iloc[p1_idx]
            price_higher_high = close.iloc[p2_idx] > close.iloc[p1_idx]
            
            if hist_lower_high and price_higher_high:
                signals.append({
                    'type': 'macd_hist_top_divergence',
                    'direction': 'bearish',
                    'score': 3.8,  # خیلی قوی! 🔴🔴🔴
                    'strength': 1.5
                })
    
    # ─── 4. Bottom Divergence (قوی‌ترین!) ───
    # قیمت: کف پایین‌تر
    # Histogram: کف بالاتر → سیگنال خرید خیلی قوی! ✅✅✅
    
    if len(valleys_idx) >= 2:
        v1_idx, v2_idx = valleys_idx[-2], valleys_idx[-1]
        
        if v2_idx > len(hist) - 15:
            hist_higher_low = hist.iloc[v2_idx] > hist.iloc[v1_idx]
            price_lower_low = close.iloc[v2_idx] < close.iloc[v1_idx]
            
            if hist_higher_low and price_lower_low:
                signals.append({
                    'type': 'macd_hist_bottom_divergence',
                    'direction': 'bullish',
                    'score': 3.8,  # خیلی قوی! ✅✅✅
                    'strength': 1.5
                })
    
    # ─── 5. Kill Long Bin Pattern ───
    # هیستوگرام مدت طولانی منفی مانده (بین 2 دره)
    
    if len(valleys_idx) >= 2:
        for i in range(len(valleys_idx) - 1):
            v1_idx, v2_idx = valleys_idx[i], valleys_idx[i + 1]
            
            if v2_idx < len(hist) - 10:
                continue
            
            # آیا هر دو دره منفی هستند؟
            if hist.iloc[v1_idx] < 0 and hist.iloc[v2_idx] < 0:
                # آیا بین آن‌ها همیشه منفی بوده؟
                hist_between = hist.iloc[v1_idx:v2_idx + 1]
                
                if hist_between.max() < 0:  # همیشه منفی!
                    signals.append({
                        'type': 'macd_hist_kill_long_bin',
                        'direction': 'bearish',
                        'score': 2.0,
                        'strength': 1.0
                    })
                    break
    
    return signals
```

**مثال Top Divergence:**

```python
# قله 1:
Peak1_idx = 80
price[80] = 50,000 USDT
histogram[80] = 0.0015

# قله 2:
Peak2_idx = 95
price[95] = 51,000 USDT   # بالاتر از قله 1 ✅
histogram[95] = 0.0010    # پایین‌تر از قله 1! ⚠️

# بررسی:
price_higher_high = True   # 51000 > 50000
hist_lower_high = True     # 0.0010 < 0.0015

# نتیجه:
{
    'type': 'macd_hist_top_divergence',
    'direction': 'bearish',
    'score': 3.8,  # قوی‌ترین سیگنال فروش! 🔴🔴🔴
    'strength': 1.5
}

# تفسیر:
# قیمت در حال رشد است اما قدرت مومنتوم (histogram) کاهش یافته
# این نشان‌دهنده ضعف خریداران و احتمال برگشت نزولی است!
# یکی از قوی‌ترین سیگنال‌های فروش! 🔴🔴🔴
```

**امتیازدهی:**
- Shrink head: **+1.5** (فروش)
- Pull feet: **+1.5** (خرید)
- **Top divergence: +3.8** (فروش - خیلی قوی!) 🔴🔴🔴
- **Bottom divergence: +3.8** (خرید - خیلی قوی!) ✅✅✅
- Kill long bin: **+2.0** (فروش)

---

### 3.2.2.10 محاسبه مومنتوم نهایی

**تجمیع تمام سیگنال‌ها:**

```python
def _calculate_momentum(
    self,
    rsi, macd, stoch, divergence,
    mfi_signals, macd_zero_signals,
    dif_zero_crosses, dif_trendline_breaks, histogram_signals
) -> Dict[str, Any]:
    """
    محاسبه جهت و قدرت مومنتوم نهایی.
    """
    bullish_score = 0.0
    bearish_score = 0.0
    
    # ─── RSI ───
    if rsi['bullish']:
        bullish_score += 2.3
    if rsi['bearish']:
        bearish_score += 2.3
    
    # ─── MACD Crossover ───
    if macd['bullish_crossover']:
        bullish_score += 2.2
    if macd['bearish_crossover']:
        bearish_score += 2.2
    
    # ─── Stochastic ───
    if stoch['signal'] == 'oversold' and stoch['bullish_crossover']:
        bullish_score += 2.5
    if stoch['signal'] == 'overbought' and stoch['bearish_crossover']:
        bearish_score += 2.5
    
    # ─── MFI ───
    bullish_score += mfi_signals['bullish_signal']  # 0 or 2.4
    bearish_score += mfi_signals['bearish_signal']  # 0 or 2.4
    
    # ─── MACD Zero Cross ───
    bullish_score += macd_zero_signals['bullish_signal']  # 0 or 1.8
    bearish_score += macd_zero_signals['bearish_signal']  # 0 or 1.8
    
    # ─── Divergence ───
    if divergence:
        if divergence['type'] == 'bullish':
            bullish_score += 3.5
        else:
            bearish_score += 3.5
    
    # ─── DIF Zero Crosses ───
    for signal in dif_zero_crosses:
        if signal['direction'] == 'bullish':
            bullish_score += signal['score']  # 1.5 or 2.0
        else:
            bearish_score += signal['score']
    
    # ─── DIF Trendline Breaks ───
    for signal in dif_trendline_breaks:
        if signal['direction'] == 'bullish':
            bullish_score += signal['score']  # 3.0
        else:
            bearish_score += signal['score']
    
    # ─── Histogram Signals ───
    for signal in histogram_signals:
        if signal['direction'] == 'bullish':
            bullish_score += signal['score']  # 1.5 or 3.8
        else:
            bearish_score += signal['score']
    
    # ─── تعیین جهت و قدرت ───
    if bullish_score > bearish_score:
        direction = 'bullish'
        strength = min(bullish_score - bearish_score, 3)
    elif bearish_score > bullish_score:
        direction = 'bearish'
        strength = min(bearish_score - bullish_score, 3)
    else:
        direction = 'neutral'
        strength = 0
    
    return {
        'direction': direction,
        'strength': strength,
        'bullish_score': bullish_score,
        'bearish_score': bearish_score
    }
```

**مثال محاسبه:**

```python
# سیگنال‌های فعال:
# 1. RSI oversold reversal: +2.3
# 2. MACD bullish crossover: +2.2
# 3. Stochastic oversold + bullish crossover: +2.5
# 4. MACD histogram bottom divergence: +3.8
# 5. DIF trendline break up: +3.0

# جمع:
bullish_score = 2.3 + 2.2 + 2.5 + 3.8 + 3.0 = 13.8
bearish_score = 0.0

# نتیجه:
direction = 'bullish'
strength = min(13.8 - 0.0, 3) = 3.0  # حداکثر 3

# تفسیر:
# مومنتوم صعودی خیلی قوی (strength = 3) ✅✅✅
# تمام اندیکاتورها هم‌جهت هستند!
# این یک سیگنال خرید فوق‌العاده قوی است! 🚀🚀🚀
```

---

### 3.2.2.11 Context-Aware Scoring (تراز با ترند)

**منطق:** اگر مومنتوم هم‌جهت با ترند باشد، قدرت آن افزایش می‌یابد.

**کد:**

```python
def _adjust_for_trend_alignment(self, momentum: Dict, trend: Dict) -> Dict:
    """
    تنظیم امتیاز مومنتوم بر اساس تراز با ترند.
    """
    trend_direction = trend.get('direction', 'neutral')
    momentum_direction = momentum['direction']
    
    # اگر هم‌جهت باشند:
    if trend_direction == momentum_direction:
        # افزایش 20% قدرت (حداکثر 3):
        momentum['strength'] = min(momentum['strength'] * 1.2, 3)
        momentum['trend_aligned'] = True
    else:
        momentum['trend_aligned'] = False
    
    return momentum
```

**مثال:**

```python
# مومنتوم:
momentum_direction = 'bullish'
momentum_strength = 2.5

# ترند (از TrendAnalyzer):
trend_direction = 'bullish'
trend_strength = 3

# بررسی:
trend_aligned = True  # هم‌جهت هستند! ✅

# تنظیم:
new_strength = min(2.5 * 1.2, 3) = min(3.0, 3) = 3.0

# نتیجه:
momentum_strength = 3.0  # افزایش یافت! ✅

# تفسیر:
# مومنتوم و ترند هر دو صعودی هستند
# این همگرایی قدرت سیگنال را افزایش می‌دهد! 🚀
```

---

### 3.2.2.12 تنظیمات (Config)

```python
"analyzers": {
    "momentum": {
        "enabled": True,
        
        # RSI Thresholds:
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        
        # Stochastic Thresholds:
        "stoch_overbought": 80,
        "stoch_oversold": 20,
        
        # Divergence Detection:
        "divergence_lookback": 14,  # تعداد کندل برای بررسی
        
        # Advanced MACD:
        "macd_cross_period": 10,
        "macd_trendline_period": 30,
        "macd_hist_period": 20,
        
        # Peak Detection:
        "macd_peak_detection": {
            "smooth_kernel": 3,
            "distance": 3,
            "prominence_factor": 0.1
        }
    }
}

# Pattern Scores (امتیازات الگوها):
"pattern_scores": {
    # DIF Zero Crosses:
    "dif_cross_zero_up_first": 2.0,
    "dif_cross_zero_up_second": 1.5,
    "dif_cross_zero_down_first": 2.0,
    "dif_cross_zero_down_second": 1.5,
    
    # DIF Trendline Breaks:
    "dif_trendline_break_up": 3.0,
    "dif_trendline_break_down": 3.0,
    
    # Histogram Patterns:
    "macd_hist_shrink_head": 1.5,
    "macd_hist_pull_feet": 1.5,
    "macd_hist_top_divergence": 3.8,    # قوی‌ترین!
    "macd_hist_bottom_divergence": 3.8,  # قوی‌ترین!
    "macd_hist_kill_long_bin": 2.0
}
```

---

**✅ Section 3.2.2 (MomentumAnalyzer) کامل شد!**

**در این قسمت پوشش داده شد:**
- ✅ فلسفه و معماری MomentumAnalyzer
- ✅ **MACD Market Type Detection (5 نوع بازار: A, B, C, D, X)** ✨
- ✅ تحلیل RSI (oversold/overbought reversal)
- ✅ تحلیل MACD اصلی (crossovers, histogram)
- ✅ تحلیل Stochastic (K/D crossovers)
- ✅ تحلیل MFI (Money Flow Index)
- ✅ MACD Zero Line Cross
- ✅ تشخیص Divergence (price vs RSI)
- ✅ **DIF Zero Crosses (با first/second)** ✨
- ✅ **DIF Trendline Breaks** ✨
- ✅ **Advanced Histogram Analysis (5 الگو)** ✨
- ✅ محاسبه مومنتوم نهایی (تجمیع سیگنال‌ها)
- ✅ Context-Aware Scoring (تراز با ترند)
- ✅ جدول کامل امتیازدهی (2.3-3.8)

**آمار سیگنال‌ها:**
- تعداد کل سیگنال‌های ممکن: **20+ سیگنال**
- قوی‌ترین سیگنال‌ها:
  1. Histogram Top/Bottom Divergence: **3.8** 🔥
  2. RSI/Price Divergence: **3.5**
  3. DIF Trendline Breaks: **3.0**
  4. Stochastic Oversold/Overbought Cross: **2.5**
  5. MFI Reversal: **2.4**

**قسمت بعدی:**
### 3.2.3 معرفی سومین Analyzer: VolumeAnalyzer (با وزن‌دهی Multi-TF)

ادامه می‌دهم...


---

## 3.2.3 معرفی سومین Analyzer: VolumeAnalyzer

**کلاس:** `VolumeAnalyzer` (محل: `signal_generation/analyzers/volume_analyzer.py`)

**مسئولیت:** تحلیل حجم معاملات برای تأیید حرکات قیمت و تشخیص شکست‌ها.

**ویژگی‌های کلیدی:**
1. محاسبه نسبت حجم (فعلی به میانگین)
2. تحلیل روند حجم (افزایشی/کاهشی/ثابت)
3. طبقه‌بندی الگوی حجم (6 الگو از OLD SYSTEM) ✨
4. تشخیص Breakout Volume
5. تحلیل OBV (On-Balance Volume)
6. اعتبارسنجی Context-Aware (تراز با Trend و Momentum)

**اندیکاتورهای مورد نیاز** (از قبل محاسبه شده):
- `volume` (حجم معاملات)
- `volume_sma` (میانگین حجم)
- `obv` (On-Balance Volume)

**خروجی:**

```python
context.results['volume'] = {
    'status': 'ok',
    'is_confirmed': True,           # آیا حجم تأیید می‌کند؟
    'volume_ratio': 1.85,           # نسبت حجم به میانگین
    'volume_trend': 'increasing',   # روند حجم
    'volume_pattern': 'spike',      # الگوی حجم (6 الگو) ✨
    'breakout_volume': False,       # آیا breakout است؟
    'obv_trend': 'bullish',         # روند OBV
    'strength': 2.3,                # قدرت (0-3)
    'confidence': 0.85,             # اطمینان (0-1)
    'context_validated': True,      # آیا با context هماهنگ است؟
    'validation_details': {...},    # جزئیات اعتبارسنجی
    'details': {
        'current_volume': 1850.0,
        'volume_sma': 1000.0,
        'obv': 125000.0
    }
}
```

---

### 3.2.3.1 فلسفه VolumeAnalyzer

**قانون طلایی:** حجم **تأیید‌کننده** حرکات قیمت است، نه پیش‌بین!

```
قیمت ↑ + حجم بالا → تأیید صعود ✅✅✅
قیمت ↑ + حجم پایین → صعود ضعیف (احتمال فیک) ⚠️

قیمت ↓ + حجم بالا → تأیید نزول 🔴🔴🔴
قیمت ↓ + حجم پایین → نزول ضعیف (احتمال کف) ⚠️
```

**منطق:**
- حجم بالا = قدرت حرکت
- حجم پایین = ضعف حرکت
- OBV صعودی = پول در حال ورود
- OBV نزولی = پول در حال خروج

---

### 3.2.3.2 محاسبه Volume Ratio

**فرمول:**
```python
Volume Ratio = حجم فعلی / میانگین حجم (SMA 20)
```

**کد:**

```python
def _calculate_volume_ratio(self, current: float, average: float) -> float:
    """
    محاسبه نسبت حجم فعلی به میانگین.
    """
    if average == 0 or pd.isna(average):
        return 1.0
    
    return current / average
```

**مثال:**

```python
# داده‌ها:
current_volume = 1850
volume_sma_20 = 1000

# محاسبه:
volume_ratio = 1850 / 1000 = 1.85

# تفسیر:
# حجم فعلی 85% بیشتر از میانگین است ✅
# این نشان‌دهنده افزایش علاقه‌مندی معامله‌گران است
```

---

### 3.2.3.3 تحلیل Volume Trend

**روش:** Linear Regression روی 5 کندل اخیر.

**کد:**

```python
def _analyze_volume_trend(self, df: pd.DataFrame) -> str:
    """
    تحلیل روند حجم (increasing/decreasing/stable).
    """
    # 5 حجم اخیر:
    recent_volumes = df['volume'].tail(5).values
    
    # محاسبه شیب با linear regression:
    x = np.arange(5)  # [0, 1, 2, 3, 4]
    slope = np.polyfit(x, recent_volumes, 1)[0]
    
    # نرمال‌سازی بر اساس میانگین:
    avg_volume = recent_volumes.mean()
    normalized_slope = slope / avg_volume
    
    # طبقه‌بندی:
    if normalized_slope > 0.1:      # شیب > 10%
        return 'increasing'
    elif normalized_slope < -0.1:   # شیب < -10%
        return 'decreasing'
    else:
        return 'stable'
```

**مثال:**

```python
# 5 کندل اخیر:
volumes = [800, 900, 1100, 1400, 1850]

# محاسبه شیب:
x = [0, 1, 2, 3, 4]
# Linear regression: y = slope × x + intercept
slope = 262.5  # حجم در هر کندل 262.5 واحد افزایش می‌یابد

# میانگین:
avg_volume = (800 + 900 + 1100 + 1400 + 1850) / 5 = 1210

# نرمال‌سازی:
normalized_slope = 262.5 / 1210 = 0.217 (21.7%)

# نتیجه:
# 0.217 > 0.1 → 'increasing' ✅

# تفسیر:
# حجم در حال افزایش است (21.7% رشد در هر کندل)
# این نشان‌دهنده افزایش علاقه است! 🚀
```

---

### 3.2.3.4 طبقه‌بندی الگوی حجم (6 الگو از OLD SYSTEM) ✨

**الگوها:**

| الگو | شرط | تفسیر | مناسب معامله |
|------|------|-------|--------------|
| **climax_volume** | ratio > 2.6 | حجم اوج (احتمال برگشت) | ⚠️ احتیاط |
| **spike** | 1.95 < ratio ≤ 2.6 | افزایش ناگهانی حجم | ✅ قوی |
| **above_average** | 1.3 < ratio ≤ 1.95 | حجم بالاتر از میانگین | ✅ خوب |
| **normal** | 0.77 < ratio ≤ 1.3 | حجم عادی | ⚠️ متوسط |
| **below_average** | 0.51 < ratio ≤ 0.77 | حجم پایین‌تر از میانگین | ⚠️ ضعیف |
| **dry_up** | ratio ≤ 0.51 | حجم بسیار پایین (خشک شدن) | ❌ خطرناک |

**کد:**

```python
def _classify_volume_pattern(
    self, volume_ratio: float, volume_trend: str
) -> str:
    """
    طبقه‌بندی الگوی حجم (OLD SYSTEM logic).
    
    آستانه‌ها بر اساس volume_threshold = 1.3:
    - climax: > 2.6 (2.0 × 1.3)
    - spike: > 1.95 (1.5 × 1.3)
    - above_average: > 1.3
    - below_average: < 0.77 (1/1.3)
    - dry_up: < 0.51 (1/(1.3×1.5))
    """
    volume_threshold = 1.3
    
    climax_threshold = 2.0 * volume_threshold     # 2.6
    spike_threshold = 1.5 * volume_threshold      # 1.95
    below_avg_threshold = 1.0 / volume_threshold  # 0.77
    dry_up_threshold = 1.0 / (volume_threshold * 1.5)  # 0.51
    
    if volume_ratio > climax_threshold:
        return 'climax_volume'   # > 2.6
    
    elif volume_ratio > spike_threshold:
        return 'spike'           # 1.95-2.6
    
    elif volume_ratio > volume_threshold:
        return 'above_average'   # 1.3-1.95
    
    elif volume_ratio < dry_up_threshold:
        return 'dry_up'          # < 0.51
    
    elif volume_ratio < below_avg_threshold:
        return 'below_average'   # 0.51-0.77
    
    else:
        return 'normal'          # 0.77-1.3
```

**مثال‌های واقعی:**

**1. Climax Volume (خطرناک!):**
```python
volume_ratio = 3.2  # 320% میانگین!

# نتیجه: 'climax_volume'

# تفسیر:
# حجم خیلی خیلی زیاد است (اوج)
# معمولاً نشان‌دهنده پایان یک حرکت قوی است
# احتمال برگشت زیاد! ⚠️⚠️⚠️

# مثال: 
# قیمت صعود قوی داشته، حجم به 3× میانگین رسیده
# احتمالاً خریداران تمام شده‌اند و برگشت نزدیک است
```

**2. Spike (قوی):**
```python
volume_ratio = 2.1

# نتیجه: 'spike'

# تفسیر:
# حجم ناگهانی افزایش یافته
# اگر همراه با شکست قیمتی باشد → سیگنال قوی ✅
# اگر بدون حرکت قیمت باشد → احتمال دام ⚠️
```

**3. Above Average (خوب):**
```python
volume_ratio = 1.85

# نتیجه: 'above_average'

# تفسیر:
# حجم بالاتر از معمول است
# نشان‌دهنده علاقه‌مندی معامله‌گران ✅
# مناسب برای تأیید سیگنال‌های دیگر
```

**4. Dry Up (خطرناک!):**
```python
volume_ratio = 0.4  # فقط 40% میانگین!

# نتیجه: 'dry_up'

# تفسیر:
# حجم خیلی پایین است (بازار خشک شده)
# اگر در انتهای صعود → احتمال برگشت نزولی ⚠️
# اگر در انتهای نزول → احتمال کف و برگشت صعودی ✅

# قانون: حجم پایین در انتهای حرکات = نزدیک به برگشت
```

---

### 3.2.3.5 تشخیص Breakout Volume

**منطق:** حجم بیش از **2× میانگین** = Breakout!

**کد:**

```python
def _detect_breakout_volume(self, volume_ratio: float) -> bool:
    """
    تشخیص حجم Breakout.
    
    Breakout threshold = 2.0
    """
    return volume_ratio >= 2.0
```

**مثال:**

```python
volume_ratio = 2.3

# بررسی:
2.3 >= 2.0 → True ✅

# نتیجه: Breakout Volume detected!

# تفسیر:
# حجم بیش از 2× میانگین است
# اگر همراه با شکست سطح مهم باشد:
# → سیگنال Breakout قوی! 🚀🚀🚀
```

---

### 3.2.3.6 تحلیل OBV (On-Balance Volume)

**OBV چیست؟** اندیکاتور تجمعی که جریان پول را نشان می‌دهد.

**روش:** محاسبه شیب OBV در 10 کندل اخیر.

**کد:**

```python
def _analyze_obv(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    تحلیل روند OBV.
    """
    # 10 مقدار اخیر OBV:
    recent_obv = df['obv'].tail(10).values
    
    # محاسبه شیب:
    x = np.arange(10)
    slope = np.polyfit(x, recent_obv, 1)[0]
    
    # نرمال‌سازی:
    avg_obv = abs(np.mean(recent_obv))
    normalized_slope = abs(slope) / avg_obv
    
    # تعیین ترند و قدرت:
    if slope > 0:
        trend = 'bullish'
        
        # محاسبه قدرت:
        if normalized_slope >= 0.1:      # 10%+
            strength = 3  # خیلی قوی
        elif normalized_slope >= 0.05:   # 5-10%
            strength = 2  # متوسط
        elif normalized_slope >= 0.01:   # 1-5%
            strength = 1  # ضعیف
        else:
            strength = 0
    
    elif slope < 0:
        trend = 'bearish'
        # مشابه بالا برای نزولی
    
    else:
        trend = 'neutral'
        strength = 0
    
    return {
        'trend': trend,
        'slope': slope,
        'strength': strength
    }
```

**مثال:**

```python
# 10 مقدار اخیر OBV:
obv_values = [100000, 102000, 105000, 108000, 112000,
              115000, 119000, 123000, 127000, 132000]

# محاسبه شیب:
slope = 3555  # OBV در هر کندل 3555 واحد افزایش می‌یابد

# میانگین:
avg_obv = 114300

# نرمال‌سازی:
normalized_slope = 3555 / 114300 = 0.0311 (3.11%)

# نتیجه:
trend = 'bullish'
strength = 1  # چون بین 1-5%

# تفسیر:
# OBV در حال افزایش است (صعودی)
# قدرت: ضعیف تا متوسط
# نشان‌دهنده ورود تدریجی پول به بازار ✅
```

---

### 3.2.3.7 بررسی تأیید حجم

**کد:**

```python
def _check_volume_confirmation(
    self,
    volume_ratio: float,
    volume_trend: str,
    obv_analysis: Dict
) -> bool:
    """
    بررسی اینکه آیا حجم حرکت قیمت را تأیید می‌کند.
    """
    # 1. حجم باید بالاتر از آستانه باشد:
    if volume_ratio < 1.3:  # volume_threshold
        return False
    
    # 2. حجم نباید در حال کاهش باشد:
    if volume_trend == 'decreasing':
        return False
    
    # 3. OBV نباید مخالف باشد (در context validation بررسی می‌شود)
    
    return True
```

**مثال:**

```python
# حالت 1: تأیید ✅
volume_ratio = 1.85
volume_trend = 'increasing'

# بررسی:
1.85 >= 1.3 → ✅
'increasing' != 'decreasing' → ✅

# نتیجه: is_confirmed = True ✅


# حالت 2: عدم تأیید ❌
volume_ratio = 1.15  # کمتر از آستانه
volume_trend = 'stable'

# بررسی:
1.15 < 1.3 → ❌

# نتیجه: is_confirmed = False ❌
# حجم برای تأیید کافی نیست!
```

---

### 3.2.3.8 Context-Aware Validation ✨

**منطق:** بررسی هماهنگی حجم با Trend و Momentum.

**کد:**

```python
def _validate_with_context(
    self,
    is_confirmed: bool,
    volume_trend: str,
    obv_analysis: Dict,
    trend_context: Optional[Dict],
    momentum_context: Optional[Dict]
) -> Dict[str, Any]:
    """
    اعتبارسنجی با context (Trend و Momentum).
    """
    validation = {
        'validated': is_confirmed,
        'trend_aligned': False,
        'momentum_aligned': False,
        'notes': []
    }
    
    # ─── بررسی تراز با Trend ───
    if trend_context:
        trend_direction = trend_context.get('direction')
        obv_trend = obv_analysis['trend']
        
        # اگر OBV و Trend هم‌جهت باشند:
        if trend_direction == 'bullish' and obv_trend == 'bullish':
            validation['trend_aligned'] = True
            validation['notes'].append('OBV confirms bullish trend')
        
        elif trend_direction == 'bearish' and obv_trend == 'bearish':
            validation['trend_aligned'] = True
            validation['notes'].append('OBV confirms bearish trend')
        
        # اگر مخالف باشند (Divergence):
        elif trend_direction in ['bullish', 'bearish'] and obv_trend != trend_direction:
            validation['notes'].append('OBV diverges from trend - potential reversal')
            # توجه: این واگرایی ممکن است نشان‌دهنده برگشت باشد!
    
    # ─── بررسی تراز با Momentum ───
    if momentum_context:
        momentum_direction = momentum_context.get('direction')
        
        # اگر حجم در حال افزایش است:
        if volume_trend == 'increasing':
            if momentum_direction in ['bullish', 'bearish']:
                validation['momentum_aligned'] = True
                validation['notes'].append('Volume supports momentum move')
        
        # اگر حجم در حال کاهش است:
        elif volume_trend == 'decreasing':
            if momentum_direction != 'neutral':
                validation['notes'].append('Weakening volume may signal momentum fade')
    
    return validation
```

**مثال 1: تراز کامل ✅:**

```python
# Volume:
volume_trend = 'increasing'
obv_trend = 'bullish'

# Context:
trend_direction = 'bullish'      # از TrendAnalyzer
momentum_direction = 'bullish'   # از MomentumAnalyzer

# نتیجه:
validation = {
    'validated': True,
    'trend_aligned': True,      # OBV + Trend هر دو صعودی ✅
    'momentum_aligned': True,   # Volume + Momentum هر دو قوی ✅
    'notes': [
        'OBV confirms bullish trend',
        'Volume supports momentum move'
    ]
}

# تفسیر:
# همه چیز هماهنگ است! ✅✅✅
# این یک سیگنال خرید بسیار قوی است! 🚀
```

**مثال 2: واگرایی (احتمال برگشت) ⚠️:**

```python
# Volume:
obv_trend = 'bearish'  # OBV در حال کاهش

# Context:
trend_direction = 'bullish'  # اما ترند صعودی است!

# نتیجه:
validation = {
    'validated': True,
    'trend_aligned': False,  # مخالف هستند!
    'notes': [
        'OBV diverges from trend - potential reversal'
    ]
}

# تفسیر:
# قیمت بالا می‌رود اما OBV پایین می‌آید
# این نشان‌دهنده خروج پول از بازار است
# احتمال برگشت نزولی! ⚠️⚠️⚠️
```

---

### 3.2.3.9 محاسبه قدرت (Strength)

**کد:**

```python
def _calculate_strength(
    self,
    volume_ratio: float,
    is_breakout: bool,
    obv_analysis: Dict,
    validation: Dict
) -> float:
    """
    محاسبه قدرت حجم (0-3).
    """
    strength = 0.0
    
    # ─── بر اساس volume ratio ───
    if volume_ratio >= 3.0:
        strength += 2.0
    elif volume_ratio >= 2.0:
        strength += 1.5
    elif volume_ratio >= 1.5:
        strength += 1.0
    elif volume_ratio >= 1.2:
        strength += 0.5
    
    # ─── پاداش برای Breakout ───
    if is_breakout:
        strength += 0.5
    
    # ─── پاداش برای OBV قوی ───
    if obv_analysis['strength'] >= 2:
        strength += 0.5
    
    # ─── پاداش برای Context Validation ───
    if validation['validated']:
        if validation['trend_aligned']:
            strength += 0.3
        if validation['momentum_aligned']:
            strength += 0.2
    
    return min(strength, 3.0)  # حداکثر 3
```

**مثال:**

```python
# داده‌ها:
volume_ratio = 2.3
is_breakout = True  # چون > 2.0
obv_strength = 2
trend_aligned = True
momentum_aligned = True

# محاسبه:
strength = 0.0
strength += 1.5  # ratio >= 2.0
strength += 0.5  # breakout
strength += 0.5  # OBV قوی
strength += 0.3  # trend aligned
strength += 0.2  # momentum aligned

strength = 3.0

# نتیجه: قدرت حداکثری! ✅✅✅
```

---

### 3.2.3.10 محاسبه اطمینان (Confidence)

**کد:**

```python
def _calculate_confidence(
    self,
    is_confirmed: bool,
    volume_trend: str,
    obv_analysis: Dict,
    validation: Dict
) -> float:
    """
    محاسبه اطمینان (0-1).
    """
    confidence = 0.5  # اطمینان پایه

    # ─── پاداش برای تأیید حجم ───
    if is_confirmed:
        confidence += 0.2

    # ─── پاداش برای حجم افزایشی ───
    if volume_trend == 'increasing':
        confidence += 0.1

    # ─── پاداش برای OBV قوی ───
    if obv_analysis['strength'] >= 2:
        confidence += 0.1

    # ─── پاداش برای Context Validation ───
    if validation['validated']:
        confidence += 0.1
        if validation['trend_aligned']:
            confidence += 0.1
        if validation['momentum_aligned']:
            confidence += 0.05

    return min(confidence, 1.0)  # حداکثر 1.0
```

**مثال:**

```python
# داده‌ها:
is_confirmed = True
volume_trend = 'increasing'
obv_strength = 2  # قوی
validated = True
trend_aligned = True
momentum_aligned = True

# محاسبه:
confidence = 0.5   # پایه
confidence += 0.2  # تأیید شده
confidence += 0.1  # افزایشی
confidence += 0.1  # OBV قوی
confidence += 0.1  # validated
confidence += 0.1  # trend aligned
confidence += 0.05 # momentum aligned

confidence = 1.0  # حداکثر

# نتیجه: اطمینان کامل! ✅✅✅
```

---

### 3.2.3.11 تنظیمات (Config)

**توجه:** Config در دو بخش جداگانه است:

**1. تنظیمات Indicators (خط 39 از config.yaml):**
```yaml
indicators:
  volume:
    volume_sma_period: 20         # دوره میانگین حجم
    obv_enabled: True             # فعال کردن OBV
```

**2. تنظیمات Analyzer (خطوط 105-125 از config.yaml):**
```yaml
analyzers:
  volume_analyzer:
    enabled: True
    weight: 0.15                  # وزن در امتیازدهی نهایی

    # آستانه‌های حجم:
    volume_thresholds:
      high_volume_ratio: 1.5      # حجم بالا (1.5× میانگین)
      confirmation_ratio: 1.2     # حجم تاییدکننده
      low_volume_ratio: 0.8       # حجم پایین

    # تحلیل OBV:
    obv_analysis:
      enabled: True               # استفاده از OBV
      trend_period: 10            # دوره بررسی روند OBV

    # Context-Aware:
    context_aware:
      require_trend_confirmation: True     # نیاز به تایید با روند
      require_momentum_confirmation: True  # نیاز به تایید با مومنتوم
      both_required: False                 # هر دو الزامی؟
```

**⚠️ نکته مهم:**
کد VolumeAnalyzer به دنبال پارامترهای `volume_threshold`, `breakout_threshold` در config است، اما این پارامترها در config.yaml فعلی **وجود ندارند**. بنابراین کد از **Constants پیش‌فرض** استفاده می‌کند:

```python
# از signal_generation/constants.py:
VOLUME_ACCUMULATION_THRESHOLD = 1.3    # پیش‌فرض volume_threshold
VOLUME_BREAKOUT_THRESHOLD = 2.0        # پیش‌فرض breakout_threshold

# از VolumeAnalyzer.__init__:
self.volume_threshold = vol_config.get('volume_threshold', VOLUME_ACCUMULATION_THRESHOLD)  # → 1.3
self.breakout_threshold = vol_config.get('breakout_threshold', VOLUME_BREAKOUT_THRESHOLD)  # → 2.0
self.obv_lookback = vol_config.get('obv_lookback', 10)  # → 10
```

**برای override کردن مقادیر پیش‌فرض:**
```yaml
analyzers:
  volume_analyzer:
    volume_threshold: 1.3         # اختیاری - پیش‌فرض از constants
    breakout_threshold: 2.0       # اختیاری - پیش‌فرض از constants
    obv_lookback: 10              # اختیاری - پیش‌فرض 10
```

---

**✅ Section 3.2.3 (VolumeAnalyzer) تمام شد!**

**در این قسمت پوشش داده شد:**
- ✅ فلسفه VolumeAnalyzer (حجم = تأیید‌کننده)
- ✅ محاسبه Volume Ratio
- ✅ تحلیل Volume Trend (linear regression)
- ✅ **طبقه‌بندی 6 الگوی حجم از OLD SYSTEM** ✨
  * climax_volume, spike, above_average
  * normal, below_average, dry_up
- ✅ تشخیص Breakout Volume
- ✅ تحلیل OBV (جریان پول)
- ✅ بررسی تأیید حجم
- ✅ **Context-Aware Validation** (تراز با Trend/Momentum) ✨
- ✅ محاسبه Strength (0-3)
- ✅ محاسبه Confidence (0-1)
- ✅ مثال‌های کامل برای همه الگوها

**نکات کلیدی:**
- حجم بالا با قیمت صعودی = قوی ✅
- حجم پایین با قیمت صعودی = ضعیف ⚠️
- OBV مخالف ترند = احتمال برگشت ⚠️
- Climax Volume = احتمال پایان حرکت ⚠️
- Dry Up در انتها = نزدیک به برگشت ⚠️

**آمار فایل:**
- خطوط کل: ~4950 خط
- حجم: ~148KB

ادامه می‌دهم...


---

## 3.2.4 بقیه Analyzers (خلاصه)

برای جلوگیری از طولانی شدن بیش از حد، بقیه 8 Analyzer را به صورت خلاصه اما جامع توضیح می‌دهیم.

### 3.2.4.1 PatternAnalyzer (تشخیص الگوها با Recency Scoring)

**محل:** `signal_generation/analyzers/pattern_analyzer.py`

**مسئولیت:** تشخیص الگوهای کندل‌استیک و چارت با امتیازدهی بر اساس تازگی (Recency).

**الگوهای تشخیص داده شده:**
1. **Candlestick Patterns** (26 الگو):
   - Basic Reversal: Hammer, Inverted Hammer, Hanging Man, Shooting Star
   - Engulfing: Bullish/Bearish Engulfing
   - Star Patterns: Morning Star, Evening Star, Morning Doji Star, Evening Doji Star
   - Doji Variations: Doji, Dragonfly Doji, Gravestone Doji, Long Legged Doji
   - Soldiers/Crows: Three White Soldiers, Three Black Crows
   - Cloud: Piercing Line, Dark Cloud Cover
   - Harami: Harami, Harami Cross
   - Advanced: Marubozu, Spinning Top, Belt Hold
   - Multi-candle: Three Inside, Three Outside, Three Methods, Mat Hold

2. **Chart Patterns** (4 الگو):
   - Double Top/Bottom
   - Head and Shoulders
   - Triangle (Ascending/Descending/Symmetrical)
   - Wedge (Rising/Falling)

**Context-Aware Scoring (ویژگی کلیدی ✨):**

```python
# محاسبه فرمول:
adjusted_strength = base_strength × trend_multiplier × momentum_multiplier × volume_multiplier × recency_multiplier

# Multipliers:
# - trend_aligned: ×1.5 (تراز با ترند)
# - trend_neutral: ×1.0 (ترند خنثی)
# - against_trend: ×0.7 (خلاف ترند)
# - momentum_confirmed: ×1.2 (تأیید مومنتوم)
# - volume_confirmed: ×1.3 (تأیید حجم)
# - recency: ×1.0 (کندل فعلی) تا ×0.5 (کندل قدیمی)

# حداکثر multiplier: 1.5 × 1.2 × 1.3 = 2.34
# حداقل multiplier: 0.7 (خلاف ترند)
```

**Recency Scoring:**

```python
# الگوهای جدیدتر امتیاز بیشتری دارند:
# از لیست ثابت multiplier استفاده می‌شود (نه فرمول خطی):

# پیش‌فرض از base_pattern.py:
recency_multipliers = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]

# محاسبه:
if candles_ago < len(recency_multipliers):
    recency_multiplier = recency_multipliers[candles_ago]
else:
    recency_multiplier = 0.0  # الگوی قدیمی (بیش از 5 کندل قبل)

# مثال‌های واقعی:
# کندل 0 (فعلی):   ×1.0 (100%) ✅
# کندل 1 قبل:      ×0.9 (90%)
# کندل 2 قبل:      ×0.8 (80%)
# کندل 3 قبل:      ×0.7 (70%)
# کندل 4 قبل:      ×0.6 (60%)
# کندل 5 قبل:      ×0.5 (50%)
# کندل 6+ قبل:     ×0.0 (رد می‌شود)
```

**نکته:** لیست `recency_multipliers` از config قابل تنظیم است.

**خروجی:**

```python
{
    'status': 'ok',
    'candlestick_patterns': [
        {
            'type': 'candlestick',
            'pattern_name': 'hammer',
            'direction': 'bullish',
            'base_strength': 2.0,
            'adjusted_strength': 4.68,  # 2.0 × 2.34 (context multipliers)
            'recency_multiplier': 1.0,  # الگو در کندل فعلی
            'candles_ago': 0,
            'trend_aligned': True,        # +50% (×1.5)
            'momentum_confirmed': True,   # +20% (×1.2)
            'volume_confirmed': True,     # +30% (×1.3)
            'score_multiplier': 2.34      # 1.5 × 1.2 × 1.3 × 1.0
        }
    ],
    'chart_patterns': [
        {
            'type': 'chart',
            'pattern_name': 'double_bottom',
            'direction': 'bullish',
            'base_strength': 3.0,
            'adjusted_strength': 4.5,
            'formed_at': 145,  # ایندکس کندل
            'confidence': 0.85
        }
    ],
    'total_patterns': 2,
    'strongest_pattern': {...},  # قوی‌ترین الگو
    'pattern_strength': 2.8,  # میانگین قدرت همه الگوها (0-3)
    'alignment_with_trend': True,
    'confidence': 0.8,
    'context_aware': True,
    'orchestrator_stats': {...}
}
```

---

### 3.2.4.2 SRAnalyzer (Support/Resistance با ATR × 0.3)

**محل:** `signal_generation/analyzers/sr_analyzer.py`

**مسئولیت:** تشخیص سطوح حمایت و مقاومت با استفاده از ATR.

**روش تشخیص (OLD SYSTEM alignment):**

```python
# 1. پیدا کردن قله‌ها و دره‌ها با scipy.signal.find_peaks:
from scipy.signal import find_peaks

# Support levels: local lows
peaks_low, _ = find_peaks(-df['low'], distance=5, prominence=std(lows) * 0.1)

# Resistance levels: local highs
peaks_high, _ = find_peaks(df['high'], distance=5, prominence=std(highs) * 0.1)

# 2. Clustering با ATR × 0.3 (OLD SYSTEM):
cluster_threshold = ATR × 0.3  # tolerance برای merge کردن سطوح نزدیک

# اگر 2 سطح نزدیک‌تر از این باشند → یک سطح محسوب می‌شوند
# حداقل 2 تاچ لازم است (min_touches = 2)

# 3. محاسبه قدرت سطح (1-3):
if touches >= 5:
    strength = 3  # خیلی قوی
elif touches >= 3:
    strength = 2  # قوی
else:  # touches >= 2
    strength = 1  # متوسط

# پاداش برای recent touches (+1):
if has_recent_touches_in_last_20_candles >= 2:
    strength = min(strength + 1, 3)

# 4. Context-Aware Prioritization:
# در ترند صعودی، سطوح حمایت مهم‌تر هستند (×1.5)
# در ترند نزولی، سطوح مقاومت مهم‌تر هستند (×1.5)
```

**مثال:**

```python
# BTC:
ATR = 550
cluster_threshold = 550 × 0.3 = 165 USDT

# سطوح کشف شده:
resistance_1 = 50,200  # 3 تاچ، قوی
resistance_2 = 50,150  # نزدیک به R1 (< 165) → Merge می‌شوند
support_1 = 48,500     # 5 تاچ، خیلی قوی ✅
support_2 = 47,800     # 2 تاچ، ضعیف

# نتیجه نهایی (از کد واقعی):
{
    'status': 'ok',
    'support_levels': [
        {
            'price': 48500,
            'strength': 3,  # 5 touches → strength 3
            'touches': 5,
            'type': 'support',
            'distance_percent': 1.5,  # قیمت = 49250
            'trend_priority': True  # در ترند صعودی
        },
        {
            'price': 47800,
            'strength': 1,  # 2 touches → strength 1
            'touches': 2,
            'type': 'support',
            'distance_percent': 2.9,
            'trend_priority': False
        }
    ],
    'resistance_levels': [
        {
            'price': 50175,
            'strength': 3,
            'touches': 5,
            'type': 'resistance',
            'distance_percent': 1.9,
            'trend_priority': False
        }
    ],
    'nearest_support': 48500,
    'nearest_resistance': 50175,
    'key_level_distance': 750,  # min(49250-48500, 50175-49250)
    'breakout_zone': False,  # فاصله از سطح > ATR × 0.5
    'level_strength': 2.3,  # میانگین قدرت همه سطوح
    'current_price': 49250,
    'context_aware': True,

    # ویژگی‌های جدید v3.0.0:
    'support_zones': [
        {
            'center': 48150,  # میانگین 2 سطح نزدیک
            'level_count': 2,
            'strength': 4,  # مجموع strength
            'touches': 7,  # مجموع touches
            'type': 'support'
        }
    ],
    'resistance_zones': [],
    'broken_levels': [
        {
            'price': 47000,
            'type': 'resistance',
            'original_strength': 2,
            'broken_direction': 'upward',  # قیمت از مقاومت رد شده
            'confirmation_candles': 5,  # 5 کندل بالای سطح
            'role_reversal': True  # مقاومت → حمایت شده
        }
    ]
}
```

---

### 3.2.4.3 VolatilityAnalyzer (تحلیل نوسان با ATR%)

**محل:** `signal_generation/analyzers/volatility_analyzer.py`

**مسئولیت:** تحلیل نوسان بازار با ATR% (OLD SYSTEM method).

**فرمول ATR%:**

```python
ATR% = (ATR / قیمت فعلی) × 100

# طبقه‌بندی (از کد واقعی):
if ATR% < 0.5:
    volatility = 'low'
elif ATR% <= 1.5:
    volatility = 'normal'
else:
    volatility = 'high'
```

**Risk Multipliers (بر اساس رژیم نوسان):**

```python
risk_multipliers = {
    'low': 1.5,      # نوسان پایین → ریسک بیشتر مجاز
    'normal': 1.0,   # نوسان عادی → ریسک استاندارد
    'high': 0.6      # نوسان بالا → ریسک کمتر (60%)
}
```

**Recommended Stop Loss (ATR Multiples):**

```python
recommended_stop_atr = {
    'low': 1.5,      # نوسان پایین → SL تنگ‌تر (1.5× ATR)
    'normal': 2.0,   # نوسان عادی → SL استاندارد (2× ATR)
    'high': 3.0      # نوسان بالا → SL گشاد‌تر (3× ATR)
}

# مثال محاسبه SL:
# ATR = 550, volatility = 'normal'
# SL_distance = 550 × 2.0 = 1100
```

**Context-Aware Risk Adjustment:**

```python
# پاداش‌ها و جریمه‌ها:
# - Strong trend (strength ≥ 3): ×1.2
# - Weak trend (strength ≤ 1): ×0.9
# - Volume confirmed: ×1.1
# - Price near BB edges: ×0.8
# - BB squeeze: ×0.8
# - BB breakout: ×1.2

# محدوده نهایی: 0.5 - 2.0
```

**Bollinger Bands Analysis:**

```python
# BB Width: (upper - lower) / middle
# BB Squeeze: width < historical_avg × 0.8 (dynamic)
# BB Breakout: price > upper or price < lower
```

**خروجی (از کد واقعی):**

```python
{
    'status': 'ok',
    'atr_value': 550,
    'atr_percent': 1.1,  # (550 / 50000) × 100
    'volatility_regime': 'normal',  # 0.5 ≤ 1.1 ≤ 1.5

    # Bollinger Bands:
    'bb_width': 0.04,  # (upper - lower) / middle
    'bb_width_percentile': 45,  # BB width در 45% تاریخچه
    'bb_squeeze': False,  # width >= avg × 0.8
    'bb_breakout': None,  # price در داخل باندها

    # Risk Management:
    'risk_multiplier': 1.0,  # از risk_multipliers['normal']
    'recommended_stop_atr': 2.0,  # 2× ATR for normal volatility

    'confidence': 0.6,
    'context_adjusted': True,  # با trend/volume تنظیم شده

    'details': {
        'bb_upper': 51000,
        'bb_middle': 50000,
        'bb_lower': 49000,
        'price_position': 'middle'  # در وسط باندها
    }
}
```

---

### 3.2.4.4 HTFAnalyzer (Higher Timeframe Analyzer)

**محل:** `signal_generation/analyzers/htf_analyzer.py`

**مسئولیت:** تحلیل تایم‌فریم‌های بالاتر برای تأیید ترند.

**Timeframe Hierarchy:**

```python
TF_HIERARCHY = {
    '5m': 5,      # → HTF: 15m
    '15m': 15,    # → HTF: 1h
    '1h': 60,     # → HTF: 4h
    '4h': 240     # → HTF: 1d
}
```

**HTF Trend Analysis (EMA-based):**

```python
# استفاده از EMA 20 و EMA 50 روی HTF:
if price > ema_20 > ema_50:
    htf_trend = 'bullish'
elif price < ema_20 < ema_50:
    htf_trend = 'bearish'
else:
    htf_trend = 'neutral'
```

**HTF Structure Analysis:**

```python
# بررسی 3 کندل اخیر HTF:
recent_highs = highs[-3:]
recent_lows = lows[-3:]

# Higher Highs & Higher Lows = صعود
if all(recent_highs[i] < recent_highs[i+1]) and all(recent_lows[i] < recent_lows[i+1]):
    structure = 'higher_highs'

# Lower Highs & Lower Lows = نزول
elif all(recent_highs[i] > recent_highs[i+1]) and all(recent_lows[i] > recent_lows[i+1]):
    structure = 'lower_lows'

else:
    structure = 'ranging'
```

**HTF Support/Resistance:**

```python
# نزدیک‌ترین سطح HTF زیر قیمت فعلی:
htf_support = max([low for low in htf_lows if low < current_price])

# نزدیک‌ترین سطح HTF بالای قیمت فعلی:
htf_resistance = min([high for high in htf_highs if high > current_price])
```

**Structure Shift Detection:**

```python
# شکست ساختار (Break of Structure):
# اگر قیمت 2% بالاتر از قله قبلی یا 2% پایین‌تر از کف قبلی:
if current_high > prev_high * 1.02 or current_low < prev_low * 0.98:
    structure_shift = True
```

**Alignment Check:**

```python
# بررسی همسویی با تایم‌فریم فعلی:
current_trend = context.get_result('trend')['direction']
htf_trend = 'bullish'  # از تحلیل HTF

if current_trend == htf_trend:
    alignment = True  # هم‌جهت ✅
else:
    alignment = False  # مخالف ❌
```

**خروجی (از کد واقعی):**

```python
{
    'status': 'ok',
    'htf_timeframe': '1h',  # تایم‌فریم بالاتر استفاده شده
    'htf_trend': 'bullish',  # ترند HTF
    'htf_structure': 'higher_highs',  # ساختار بازار HTF
    'alignment': True,  # همسویی با تایم‌فریم فعلی
    'htf_support': 48000,  # نزدیک‌ترین حمایت HTF
    'htf_resistance': 52000,  # نزدیک‌ترین مقاومت HTF
    'structure_shift': False,  # شکست ساختار؟
    'confidence': 0.7  # 0.7 if aligned, 0.5 if not
}
```

**نکات مهم:**
- ✅ HTF data باید در `context.metadata['htf_data']` موجود باشد
- ✅ اگر HTF data نباشد، status='no_htf_data' برمی‌گردد
- ✅ Alignment با TrendAnalyzer بررسی می‌شود
- ✅ در Direction Determination از این analyzer استفاده می‌شود (+2 bonus)

---

### 3.2.4.5 ChannelAnalyzer (تحلیل کانال‌ها)

**محل:** `signal_generation/analyzers/channel_analyzer.py`

**مسئولیت:** تشخیص و تحلیل کانال‌های قیمتی.

**انواع کانال:**
1. **Ascending Channel** (صعودی)
2. **Descending Channel** (نزولی)
3. **Horizontal Channel** (رنج)
4. **Irregular** (نامنظم - یک خط صعودی، دیگری نزولی)

**روش تشخیص (Linear Regression):**

```python
# 1. استفاده مستقیم از all highs/lows (نه فقط peaks):
lookback = 50  # آخرین 50 کندل
highs = df['high'].tail(lookback).values
lows = df['low'].tail(lookback).values

# 2. Linear Regression روی همه نقاط:
x = np.arange(len(highs))  # [0, 1, 2, ..., 49]
upper_slope, upper_intercept = np.polyfit(x, highs, 1)
lower_slope, lower_intercept = np.polyfit(x, lows, 1)

# 3. تعیین نوع کانال (threshold = 0.0001):
if abs(upper_slope) < 0.0001 and abs(lower_slope) < 0.0001:
    channel_type = 'horizontal'  # هر دو تقریباً صفر
elif upper_slope > 0.0001 and lower_slope > 0.0001:
    channel_type = 'ascending'  # هر دو مثبت
elif upper_slope < -0.0001 and lower_slope < -0.0001:
    channel_type = 'descending'  # هر دو منفی
else:
    channel_type = 'irregular'  # یکی مثبت، یکی منفی

# 4. محاسبه bounds فعلی:
current_x = len(x) - 1  # آخرین نقطه
upper_bound = upper_slope * current_x + upper_intercept
lower_bound = lower_slope * current_x + lower_intercept
channel_width = upper_bound - lower_bound
```

**Price Position & Breakout:**

```python
current_price = df['close'].iloc[-1]

if current_price > upper_bound:
    position = 'above'      # بالای کانال
    breakout = True         # شکست به بالا! 🚀
elif current_price < lower_bound:
    position = 'below'      # پایین کانال
    breakout = True         # شکست به پایین! 🔴
else:
    mid = (upper_bound + lower_bound) / 2
    if current_price > mid:
        position = 'upper'  # نیمه بالای کانال
    else:
        position = 'lower'  # نیمه پایین کانال
    breakout = False        # داخل کانال
```

**Strength Calculation (Fit Quality):**

```python
# محاسبه fit error (چقدر قیمت‌ها از خط رگرسیون فاصله دارند):
upper_fit = highs - (upper_slope * x + upper_intercept)
lower_fit = lows - (lower_slope * x + lower_intercept)
fit_error = mean(abs(upper_fit)) + mean(abs(lower_fit))

# تعیین strength بر اساس fit error:
if fit_error < channel_width * 0.1:    # < 10% عرض کانال
    strength = 3  # کانال خیلی قوی ✅
elif fit_error < channel_width * 0.2:  # < 20% عرض کانال
    strength = 2  # کانال قوی
else:
    strength = 1  # کانال ضعیف
```

**خروجی (از کد واقعی):**

```python
{
    'status': 'ok',
    'channel_type': 'ascending',  # یا descending, horizontal, irregular
    'upper_bound': 50800,  # خط بالای کانال (قیمت فعلی)
    'lower_bound': 49200,  # خط پایین کانال (قیمت فعلی)
    'channel_width': 1600,  # عرض کانال
    'price_position': 'lower',  # موقعیت قیمت: 'above'/'below'/'upper'/'lower'
    'breakout': False,  # آیا از کانال خارج شده؟
    'strength': 3  # قدرت کانال (1-3 بر اساس fit quality)
}
```

**نکات:**
- ✅ از همه highs/lows استفاده می‌شود (نه فقط peaks)
- ✅ Slope threshold بسیار کوچک: 0.0001 (برای تشخیص دقیق horizontal)
- ✅ Irregular channel: یک slope مثبت، دیگری منفی (مثلث واگرا)
- ✅ Strength بر اساس fit error: هرچه قیمت‌ها نزدیک‌تر به خط باشند → قوی‌تر

---

### 3.2.4.6 HarmonicAnalyzer (الگوهای هارمونیک)

**محل:** `signal_generation/analyzers/harmonic_analyzer.py`

**مسئولیت:** تشخیص الگوهای هارمونیک (Gartley, Butterfly, Bat, Crab).

**الگوهای اصلی:**
1. **Gartley** (0.618 retracement)
2. **Butterfly** (0.786 retracement)
3. **Bat** (0.886 retracement)
4. **Crab** (0.886 retracement with 1.618 extension)

**مثال Gartley:**

```
      B
     /\
    /  \
   /    C
  /      \
 X        \
           D (Entry point)

شرایط:
- AB = 0.618 XA
- BC = 0.382-0.886 AB
- CD = 1.27-1.618 BC
- AD = 0.786 XA
```

**خروجی:**

```python
{
    'pattern': 'gartley_bullish',
    'completion': 0.95,  # 95% تکمیل
    'entry_price': 48500,
    'stop_loss': 47800,
    'targets': [49200, 49800, 50500],
    'risk_reward': 3.2
}
```

---

### 3.2.4.7 CyclicalAnalyzer (تحلیل چرخه‌ای)

**محل:** `signal_generation/analyzers/cyclical_analyzer.py`

**مسئولیت:** تشخیص چرخه‌های قیمتی با FFT (Fast Fourier Transform).

**دو روش تحلیل:**
1. **FFT (پیش‌فرض)** - Fast Fourier Transform برای تشخیص دقیق چرخه‌ها
2. **Autocorrelation (fallback)** - اگر FFT ناموفق باشد

**روش FFT (Scientific Method):**

```python
# گام 1: Detrend کردن داده (حذف ترند خطی):
x = np.arange(len(prices))
trend_coeffs = np.polyfit(x, prices, 1)
trend = np.polyval(trend_coeffs, x)
detrended = prices - trend

# گام 2: اعمال FFT:
close_fft = fft.rfft(detrended)
fft_freqs = fft.rfftfreq(len(detrended))

# گام 3: یافتن فرکانس‌های معنادار:
close_fft_mag = np.abs(close_fft)
threshold = mean(close_fft_mag) + std(close_fft_mag)
significant_freq_indices = where(close_fft_mag > threshold)

# گام 4: فیلتر کردن چرخه‌های منطقی (2 تا lookback/2):
cycles = [
    {
        'period': int(1 / freq),  # تعداد کندل
        'amplitude': mag / len(detrended),
        'amplitude_percent': (amplitude / mean(prices)) * 100,
        'phase': angle(close_fft[i]),
        'frequency': freq
    }
    for each significant frequency
]

# گام 5: مرتب‌سازی بر اساس amplitude (قوی‌ترین‌ها اول):
top_cycles = sorted(cycles, by amplitude, descending)[:5]
```

**تولید Forecast (پیش‌بینی قیمت):**

```python
# اگر حداقل 2 چرخه یافت شود، forecast تولید می‌شود:
forecast = zeros(forecast_length)  # پیش‌فرض: 20 کندل آینده

for i in range(forecast_length):
    # 1. ترند:
    point_forecast = last_trend + trend_slope * (i + 1)

    # 2. اضافه کردن اجزای چرخه‌ای:
    for cycle in top_cycles:
        t = len(prices) + i
        cycle_component = amplitude * cos(2π * t / period + phase)
        point_forecast += cycle_component

    forecast[i] = point_forecast

# تحلیل forecast:
forecast_direction = 'bullish' if forecast_end > current_price else 'bearish'
forecast_strength = abs(forecast_end - current_price) / current_price
score = 2.5 * prediction_clarity * cycles_strength
```

**خروجی (FFT Method):**

```python
{
    'status': 'ok',
    'method': 'fft',

    # چرخه‌های تشخیص داده شده:
    'cycles': [
        {
            'period': 24,  # چرخه 24 کندلی
            'amplitude': 125.5,
            'amplitude_percent': 0.25,  # 0.25% میانگین قیمت
            'phase': 1.57,  # فاز (رادیان)
            'frequency': 0.0417
        },
        {
            'period': 48,  # چرخه 48 کندلی
            'amplitude': 98.3,
            'amplitude_percent': 0.20,
            'phase': 0.78,
            'frequency': 0.0208
        }
        # ... تا 5 چرخه برتر
    ],
    'total_cycles_detected': 12,
    'dominant_cycle': 24,  # قوی‌ترین چرخه

    # پیش‌بینی (اگر >= 2 چرخه):
    'forecast': {
        'values': [50100, 50250, ...],  # 20 مقدار آینده
        'direction': 'bullish',
        'strength': 0.015,  # 1.5% تغییر
        'end_value': 50800,
        'change_percent': 1.6
    },
    'signal': {
        'type': 'cycle_bullish_forecast',
        'direction': 'bullish',
        'score': 1.85,
        'prediction_clarity': 0.92,
        'cycles_strength': 0.80
    },
    'confidence': 0.74  # prediction_clarity × cycles_strength
}
```

**روش Autocorrelation (Fallback):**

```python
{
    'status': 'ok',
    'method': 'autocorrelation',
    'dominant_cycle': 24,
    'cycle_phase': 'rising',  # 'top', 'bottom', 'rising', 'falling'
    'next_reversal_in': 6,  # تخمین کندل‌های باقیمانده تا برگشت
    'confidence': 0.5
}
```

**نکات:**
- ✅ FFT = روش علمی و دقیق (پیش‌فرض)
- ✅ Detrending برای حذف نویز ترند
- ✅ Top 5 قوی‌ترین چرخه‌ها
- ✅ Forecast تولید می‌شود (اگر >= 2 چرخه)
- ✅ Signal scoring برای استفاده در decision making

---

### 3.2.4.8 VolumePatternAnalyzer (الگوهای حجمی)

**محل:** `signal_generation/analyzers/volume_pattern_analyzer.py`

**مسئولیت:** تشخیص الگوهای پیشرفته حجم.

**6 الگوی تشخیص داده شده (OLD SYSTEM):**

**1. Accumulation (انباشت - Smart Money Buying):**
```python
# شرایط:
volume_ratio >= 1.3  # حجم بالا
price_range <= 0.02  # رنج تنگ (2%)
price_change >= -0.02  # قیمت ثابت یا کمی بالا
obv_change > 0  # OBV در حال افزایش

# خروجی:
{
    'detected': True,
    'strength': 2.5,  # 0-3
    'duration': 15  # کندل
}
```

**2. Distribution (توزیع - Smart Money Selling):**
```python
# شرایط:
volume_ratio >= 1.3  # حجم بالا
price_range <= 0.02  # رنج تنگ
price_change <= 0.02  # قیمت ثابت یا کمی پایین
obv_change < 0  # OBV در حال کاهش

# خروجی:
{
    'detected': True,
    'strength': 2.0,
    'duration': 12
}
```

**3. Climax Volume (اوج حجم - Exhaustion):**
```python
# شرایط:
volume > avg × 3.0  # حجم بسیار بالا (climax_volume_threshold)
price_move >= 0.03  # حرکت قیمت >= 3%

# تشخیص نوع:
if price_move > 0:
    type = 'buying'  # اوج خرید
else:
    type = 'selling'  # اوج فروش

# خروجی:
{
    'type': 'buying',  # یا 'selling' یا None
    'intensity': 3.5  # نسبت حجم به میانگین
}
```

**4. Volume Divergence (واگرایی حجم - Price/Volume Disagreement):**
```python
# شرایط:
# قیمت صعودی اما حجم نزولی (bullish divergence)
# یا قیمت نزولی اما حجم صعودی (bearish divergence)

# خروجی:
{
    'detected': True,
    'type': 'bullish',  # یا 'bearish'
    'strength': 1.8  # 0-3
}
```

**5. Smart Money Flow (جریان پول هوشمند):**
```python
# محاسبه buying/selling pressure از close position در کندل‌های با حجم بالا:

# گام 1: پیدا کردن کندل‌های با حجم بالا (> avg):
large_volume_candles = df[df['volume'] > avg_volume].tail(20)

# گام 2: محاسبه فشار خرید/فروش:
buying_pressure = 0.0
selling_pressure = 0.0

for candle in large_volume_candles:
    # موقعیت close در رنج کندل (0 = low, 1 = high):
    close_position = (close - low) / (high - low)

    # وزن بر اساس حجم:
    vol_weight = volume / avg_volume

    if close_position > 0.6:      # بسته شدن در بالای کندل
        buying_pressure += vol_weight    # → خریداران قوی ✅
    elif close_position < 0.4:    # بسته شدن در پایین کندل
        selling_pressure += vol_weight   # → فروشندگان قوی 🔴

# گام 3: تعیین جریان (threshold = 1.3×):
if buying_pressure > selling_pressure × 1.3:  # 30%+ اختلاف
    flow = 'buying'
    confidence = (buying_pressure - selling_pressure) / (buying_pressure + selling_pressure)
elif selling_pressure > buying_pressure × 1.3:
    flow = 'selling'
    confidence = (selling_pressure - buying_pressure) / (buying_pressure + selling_pressure)
else:
    flow = 'neutral'
    confidence = 0.0

# خروجی:
{
    'flow': 'buying',  # 'buying', 'selling', 'neutral'
    'confidence': 0.75,
    'buying_pressure': 3.45,   # مجموع وزن کندل‌های خریدی
    'selling_pressure': 1.20   # مجموع وزن کندل‌های فروشی
}
```

**نکته:** این روش از close position استفاده می‌کند، نه OBV. اگر کندل‌ها با حجم بالا در بالا بسته شوند → smart money خرید می‌کند ✅

**6. Volume Profile (پروفایل حجم - Support/Resistance):**
```python
# تحلیل توزیع حجم در سطوح قیمتی مختلف:
# lookback = 100 کندل، تقسیم به 20 bin

# POC (Point of Control): سطح قیمتی با بیشترین حجم

# خروجی:
{
    'support_levels': [48200, 47800],  # سطوح با حجم بالا زیر قیمت
    'resistance_levels': [50500, 51000],  # سطوح با حجم بالا بالای قیمت
    'poc': 49500  # Point of Control
}
```

**خروجی کلی (از کد واقعی):**

```python
{
    'status': 'ok',

    'accumulation': {
        'detected': True,
        'strength': 2.5,
        'duration': 15
    },
    'distribution': {
        'detected': False,
        'strength': 0,
        'duration': 0
    },
    'climax_volume': {
        'type': 'buying',  # یا 'selling' یا None
        'intensity': 3.2
    },
    'volume_divergence': {
        'detected': True,
        'type': 'bullish',
        'strength': 1.8
    },
    'smart_money': {
        'flow': 'buying',  # 'buying', 'selling', 'neutral'
        'confidence': 0.75
    },
    'volume_profile': {
        'support_levels': [48200, 47800],
        'resistance_levels': [50500, 51000],
        'poc': 49500
    },
    'patterns_detected': [
        'accumulation',
        'climax_buying',
        'divergence_bullish',
        'smart_money_buying'
    ]
}
```

**نکات:**
- ✅ 6 الگوی پیشرفته از OLD SYSTEM
- ✅ Accumulation/Distribution برای تشخیص فعالیت نهادی
- ✅ Climax Volume برای exhaustion signals
- ✅ Divergence برای هشدار زودهنگام
- ✅ Smart Money Flow از OBV analysis
- ✅ Volume Profile برای S/R levels

---

## 3.3 STEP 5: تعیین جهت سیگنال (Direction Determination)

**محل:** `orchestrator.py:370-379`

```python
# === STEP 5: Determine Direction ===
logger.info(f"[5/7] Determining signal direction for {symbol}")

direction = self._determine_direction(context)

if not direction:
    logger.info(f"No clear direction for {symbol}")
    return None

logger.info(f"  ✓ Direction: {direction}")
```

### 3.3.1 الگوریتم تعیین جهت

**کد:**

```python
def _determine_direction(self, context: AnalysisContext) -> Optional[str]:
    """
    تعیین جهت سیگنال بر اساس نتایج Analyzers.

    از کد واقعی (orchestrator.py:537-615)
    """
    bullish_score = 0
    bearish_score = 0

    # ─── 1. Trend (وزن: ×3) ───
    trend_result = context.get_result('trend')
    if trend_result:
        direction = trend_result.get('direction', 'neutral')
        strength = abs(trend_result.get('strength', 0))

        if direction in ['bullish', 'bullish_aligned']:
            bullish_score += strength * 3
        elif direction in ['bearish', 'bearish_aligned']:
            bearish_score += strength * 3

    # ─── 2. Momentum (وزن: ×2) ───
    momentum_result = context.get_result('momentum')
    if momentum_result:
        direction = momentum_result.get('direction', 'neutral')
        strength = abs(momentum_result.get('strength', 0))

        if direction == 'bullish':
            bullish_score += strength * 2
        elif direction == 'bearish':
            bearish_score += strength * 2

    # ─── 3. Volume Confirmation (پاداش: +1) ───
    volume_result = context.get_result('volume')
    if volume_result and volume_result.get('is_confirmed'):
        # فقط به طرف غالب اضافه می‌شود
        if bullish_score > bearish_score:
            bullish_score += 1
        elif bearish_score > bullish_score:
            bearish_score += 1

    # ─── 4. Patterns (وزن: ×0.5) ───
    pattern_result = context.get_result('patterns')
    if pattern_result:
        patterns = (
            pattern_result.get('candlestick_patterns', []) +
            pattern_result.get('chart_patterns', [])
        )

        for pattern in patterns:
            p_dir = pattern.get('direction', 'neutral')
            p_str = pattern.get('adjusted_strength', 0)

            if p_dir == 'bullish':
                bullish_score += p_str * 0.5
            elif p_dir == 'bearish':
                bearish_score += p_str * 0.5

    # ─── 5. HTF Alignment (پاداش: +2) ───
    htf_result = context.get_result('htf')
    if htf_result and htf_result.get('alignment'):
        htf_trend = htf_result.get('htf_trend', 'neutral')

        if htf_trend == 'bullish':
            bullish_score += 2
        elif htf_trend == 'bearish':
            bearish_score += 2

    # ─── 6. تعیین نهایی (نیاز به برتری 1.2×) ───
    if bullish_score > bearish_score * 1.2:
        return 'LONG'
    elif bearish_score > bullish_score * 1.2:
        return 'SHORT'
    else:
        return None  # جهت مشخص نیست (نزدیک به خنثی)
```

**مثال واقعی:**

```python
# نتایج Analyzers:
# Trend: bullish, strength = 2.5
bullish_score += 2.5 * 3 = 7.5

# Momentum: bullish, strength = 2.0
bullish_score += 2.0 * 2 = 4.0

# Volume: confirmed, bullish is winning
bullish_score += 1

# Pattern: hammer, adjusted_strength = 2.0, direction = bullish
bullish_score += 2.0 * 0.5 = 1.0

# HTF: aligned, htf_trend = bullish
bullish_score += 2

# امتیاز نهایی:
bullish_score = 7.5 + 4.0 + 1.0 + 1.0 + 2.0 = 15.5
bearish_score = 0

# بررسی برتری 1.2×:
15.5 > 0 * 1.2 → True ✅

# نتیجه:
direction = 'LONG'  # سیگنال خرید بسیار قوی! 🚀
```

---

**✅ بخش 3 (تحلیل با 11 Analyzer) تمام شد!**

**در این بخش پوشش داده شد:**
- ✅ 3.1: Market Regime Detection (9 رژیم)
- ✅ 3.2.1: TrendAnalyzer (7 فاز، Late Phase)
- ✅ 3.2.2: MomentumAnalyzer (5 MACD Types، 20+ سیگنال)
- ✅ 3.2.3: VolumeAnalyzer (6 الگوی حجم، Context-Aware)
- ✅ 3.2.4: بقیه 8 Analyzers (خلاصه جامع):
  * PatternAnalyzer (Recency Scoring)
  * SRAnalyzer (ATR × 0.3)
  * VolatilityAnalyzer (ATR%)
  * HTFAnalyzer
  * ChannelAnalyzer
  * HarmonicAnalyzer
  * CyclicalAnalyzer
  * VolumePatternAnalyzer
- ✅ 3.3: STEP 5 (Direction Determination)

**آمار فایل:**
- خطوط کل: ~5800 خط
- حجم: ~175KB
- پیشرفت: 71% از OLD SYSTEM (8202 خط)

**بخش‌های باقی‌مانده:**
- بخش 4: Smart Systems
- بخش 5: Signal Scoring
- بخش 6: Multi-TF Aggregation  
- بخش 7: Validation & Output

ادامه می‌دهم با بخش 4...


---

## بخش ۴: سیستم‌های هوشمند (Smart Systems)

NEW SYSTEM دارای چند سیستم هوشمند است که به طور خودکار عملکرد را بهینه می‌کنند.

### 4.1 Circuit Breaker (مدیریت ریسک اضطراری)

**📌 توجه:** Circuit Breaker در **STEP 0** (قبل از شروع pipeline) بررسی می‌شود و در **بخش 1.4** به تفصیل توضیح داده شده است.

**محل:** `signal_generation/systems/emergency_circuit_breaker.py`

**هدف:** متوقف کردن خودکار معاملات در شرایط بحرانی.

**شرایط فعال‌سازی:**

در کد واقعی فقط **2 شرط** وجود دارد:

```python
# 1. ضرر روزانه بیش از حد:
if abs(daily_loss_r) >= 5.0:  # 5R ضرر
    circuit_breaker.trigger(reason="Daily loss limit exceeded")
    # توقف برای cool_down_period_minutes (60 دقیقه)

# 2. ضررهای متوالی:
if consecutive_losses >= 3:
    circuit_breaker.trigger(reason="3 consecutive losses")
    # توقف برای 60 دقیقه
```

**⚠️ نکته:** شرایط دیگری مانند DrawDown در نسخه فعلی پیاده‌سازی نشده‌اند.

**عملکرد:**

```python
# در orchestrator.py:272-281 (STEP 0):
if self.circuit_breaker.enabled:
    is_active, reason = self.circuit_breaker.check_if_active()
    if is_active:
        logger.warning(f"🚨 Circuit breaker active: {reason}")
        return None  # تولید سیگنال متوقف می‌شود
```

**خروجی check_if_active():**

```python
# وقتی فعال نیست:
(False, None)

# وقتی فعال است:
(True, "Daily loss limit exceeded - cool down for 45 more minutes")
```

**برای جزئیات کامل Circuit Breaker به بخش 1.4 مراجعه کنید.**

---

### 4.2 AdaptiveLearningSystem (یادگیری تطبیقی)

**محل:** `signal_generation/systems/adaptive_learning_system.py`

**هدف:** یادگیری از نتایج معاملات و تنظیم خودکار پارامترها.

**ویژگی‌ها:**

1. **Pattern Success Tracking:**
```python
# ثبت موفقیت هر الگو:
pattern_stats = {
    'hammer': {'wins': 15, 'losses': 5, 'success_rate': 0.75},
    'macd_crossover': {'wins': 20, 'losses': 8, 'success_rate': 0.71},
    'rsi_oversold': {'wins': 12, 'losses': 12, 'success_rate': 0.50}
}

# تنظیم وزن الگوها:
if pattern_stats['hammer']['success_rate'] > 0.7:
    pattern_weight['hammer'] *= 1.2  # افزایش وزن ✅
else:
    pattern_weight['hammer'] *= 0.8  # کاهش وزن ❌
```

2. **Timeframe Performance:**
```python
# کدام تایم‌فریم بهتر کار می‌کند؟
tf_performance = {
    '15m': {'win_rate': 0.55, 'avg_profit': 1.2%},
    '1h': {'win_rate': 0.68, 'avg_profit': 2.1%},  # بهترین ✅
    '4h': {'win_rate': 0.62, 'avg_profit': 3.5%}
}

# افزایش وزن 1h:
timeframe_weights['1h'] = 1.3
```

3. **Market Condition Learning:**
```python
# کدام رژیم بازار سودآورتر است؟
regime_performance = {
    'strong_trend_normal': 0.75,  # عالی ✅
    'weak_trend_high': 0.45,      # ضعیف ❌
    'range_high': 0.30            # خیلی بد ❌
}

# رد کردن سیگنال در رژیم‌های ضعیف:
if regime == 'range_high' and regime_performance[regime] < 0.4:
    return None  # رد سیگنال
```

---

### 4.3 CorrelationManager (مدیریت همبستگی)

**📌 توجه:** CorrelationManager در **STEP 6.5** (بعد از محاسبه امتیاز) اجرا می‌شود و در **بخش 5.2** به تفصیل توضیح داده شده است.

**محل:** `signal_generation/systems/correlation_manager.py`

**هدف:** جلوگیری از معاملات همبسته (over-exposure).

**عملکرد کلی:**

```python
# در orchestrator.py:413-430 (STEP 6.5):
if self.correlation_manager.enabled:
    # محاسبه ضریب ایمنی بر اساس همبستگی
    correlation_factor = self.correlation_manager.get_correlation_safety_factor(
        symbol, direction
    )

    # اگر همبستگی بالا باشد
    if correlation_factor < 0.7:
        logger.info(f"High correlation exposure for {symbol} (factor: {correlation_factor:.2f})")
        # کاهش امتیاز سیگنال
        score.final_score *= correlation_factor
        score.correlation_safety_factor = correlation_factor
```

**مثال سریع:**

```python
# موقعیت‌های فعلی:
# - BTCUSDT LONG
# - ETHUSDT LONG

# سیگنال جدید:
# - SOLUSDT LONG

# بررسی همبستگی:
# BTC-SOL: 0.72 (همبستگی بالا)
# ETH-SOL: 0.68

# نتیجه:
correlation_factor = 0.56  # پایین
original_score = 75.0
new_score = 75.0 × 0.56 = 42.0  # کاهش 44%

# با این امتیاز پایین‌تر، ممکن است در Validator رد شود
```

**برای جزئیات کامل CorrelationManager به بخش 5.2 (STEP 6.5) مراجعه کنید.**

---

## بخش ۵: امتیازدهی سیگنال (Signal Scoring)

### 5.1 STEP 6: محاسبه امتیاز (SignalScorer)

**محل:** `signal_generation/signal_scorer.py`

**هدف:** محاسبه امتیاز نهایی سیگنال با ترکیب تمام فاکتورها.

#### 5.1.1 فرمول امتیازدهی (Multiplicative Formula)

```python
final_score = base_score
             * (1.0 + confluence_bonus)       # 0-0.5
             * timeframe_weight               # 0.7-1.2
             * trend_alignment                # 0.8-1.2
             * volume_confirmation            # 1.0 or 1.1
             * pattern_quality                # 1.0-1.5
             * macd_analysis_score            # 0.85-1.15
             * htf_multiplier                 # 0.7-1.3
             * volatility_multiplier          # 0.6-1.5

# سپس در orchestrator:
if correlation_factor < 0.7:
    final_score *= correlation_factor
```

**تفاوت با سیستم قدیم:** فرمول ضربی است، نه جمعی!

#### 5.1.2 محاسبه Base Score (وزن‌دهی درصدی)

```python
# هر analyzer امتیاز 0-100 می‌دهد
# سپس وزن درصدی اعمال می‌شود:

DEFAULT_WEIGHTS = {
    'trend': 0.30,                  # 30%
    'momentum': 0.25,               # 25%
    'volume': 0.20,                 # 20%
    'patterns': 0.10,               # 10%
    'support_resistance': 0.08,     # 8%
    'volatility': 0.05,             # 5%
    'harmonic': 0.01,               # 1%
    'channel': 0.005,               # 0.5%
    'cyclical': 0.003,              # 0.3%
    'htf': 0.002                    # 0.2%
}

base_score = (
    trend_score * 0.30 +
    momentum_score * 0.25 +
    volume_score * 0.20 +
    pattern_score * 0.10 +
    sr_score * 0.08 +
    volatility_score * 0.05 +
    harmonic_score * 0.01 +
    channel_score * 0.005 +
    cyclical_score * 0.003 +
    htf_score * 0.002
)
```

**مثال:**

```python
# نتایج (هر کدام 0-100):
trend_score = 90         # قوی
momentum_score = 75      # خوب
volume_score = 60        # متوسط
pattern_score = 80       # 2 الگو
sr_score = 70            # نزدیک حمایت
volatility_score = 50    # نوسان عادی
harmonic_score = 0       # بدون الگو
channel_score = 0
cyclical_score = 0
htf_score = 100          # هم‌راستا

# محاسبه base_score:
base_score = (90×0.30) + (75×0.25) + (60×0.20) + (80×0.10) +
             (70×0.08) + (50×0.05) + (0×0.01) + (0×0.005) +
             (0×0.003) + (100×0.002)
           = 27.0 + 18.75 + 12.0 + 8.0 + 5.6 + 2.5 + 0 + 0 + 0 + 0.2
           = 74.05
```

**📊 لاگ الگوهای تشخیص داده شده (در Orchestrator):**

**محل در کد:** `orchestrator.py:396-401`

بعد از محاسبه score، اگر الگوهای Price Action/Candlestick تشخیص داده شده باشند، جزئیات آنها log می‌شود:

```python
# ✨ لاگ جزئیات الگوهای تشخیص داده شده
if score.detected_patterns:
    logger.info(
        f"  📊 الگوهای تشخیص داده شده برای {symbol} {direction}:\n"
        f"{score.get_pattern_summary()}"
    )
```

**مثال خروجی لاگ:**

```
[INFO] ✓ Score: 78.50 (STRONG, conf=0.85)
[INFO] 📊 الگوهای تشخیص داده شده برای BTCUSDT LONG:
  • Engulfing (وزن: 1.15)
  • Morning Star (وزن: 1.20)
  • Support Bounce (وزن: 1.10)
```

**فایده:**
- 🔍 **Transparency:** مشخص می‌شود چه الگوهایی سیگنال را قوی کرده‌اند
- 📈 **Pattern Quality:** وزن هر الگو نمایش داده می‌شود
- 📝 **Debugging:** در تحلیل بعدی مشخص است کدام الگوها موفق بودند

---

#### 5.1.3 Confluence Bonus (هم‌گرایی)

```python
# ترکیب دو روش:
# 1. Alignment Bonus: هم‌راستایی analyzers
# 2. Risk/Reward Bonus: نسبت RR

aligned_count = 0
# بررسی هم‌راستایی 5 analyzer کلیدی:
if trend_aligned: aligned_count += 1
if momentum_aligned: aligned_count += 1
if volume_confirmed: aligned_count += 1
if patterns_aligned: aligned_count += 1
if htf_aligned: aligned_count += 1

alignment_bonus = (aligned_count / 5) * 0.25  # Max 0.25

# RR Bonus:
if risk_reward_ratio >= 2.0:
    rr_bonus = min(0.25, (risk_reward_ratio - 2.0) * 0.125)
else:
    rr_bonus = 0

confluence_bonus = min(0.5, alignment_bonus + rr_bonus)  # Max 0.5
```

**مثال:**
```python
aligned_count = 4  # 4 از 5
alignment_bonus = (4/5) * 0.25 = 0.20
rr_bonus = (3.0 - 2.0) * 0.125 = 0.125
confluence_bonus = 0.20 + 0.125 = 0.325  # +32.5%
```

#### 5.1.4 Trend Alignment Multiplier

```python
# Range: 0.8 - 1.2
if direction == 'LONG':
    if trend == 'bullish' and strength >= 2.5:
        trend_alignment = 1.2  # Perfect
    elif trend == 'bullish' and strength >= 1.5:
        trend_alignment = 1.1  # Good
    elif trend == 'bullish':
        trend_alignment = 1.05  # Weak
    elif trend == 'sideways':
        trend_alignment = 1.0  # Neutral
    else:
        trend_alignment = 0.8  # Against trend
```

#### 5.1.5 Volume Confirmation Multiplier

```python
# Range: 1.0 or 1.1
if volume_result.get('is_confirmed', False):
    volume_confirmation = 1.1  # +10% bonus
else:
    volume_confirmation = 1.0
```

#### 5.1.6 Pattern Quality Multiplier

```python
# Range: 1.0 - 1.5
# بر اساس تعداد الگوهای تشخیص داده شده

pattern_count = len(candlestick_patterns) + len(chart_patterns)
pattern_quality = 1.0 + min(0.5, pattern_count * 0.1)

# مثال:
# 0 pattern: 1.0
# 1 pattern: 1.1 (+10%)
# 2 patterns: 1.2 (+20%)
# 3 patterns: 1.3 (+30%)
# 5+ patterns: 1.5 (+50%, capped)
```

#### 5.1.7 MACD Analysis Score Multiplier

```python
# Range: 0.85 - 1.2
# محل در کد: signal_scorer.py:766-811
macd_direction = macd_signal.get('direction')
mom_direction = momentum_result.get('direction')

if macd_direction == mom_direction and macd_direction != 'neutral':
    macd_analysis_score = 1.2  # Good alignment (حداکثر)
elif macd_direction == 'neutral':
    macd_analysis_score = 1.0  # Neutral
else:
    macd_analysis_score = 0.85  # Disagreement (حداقل)
```

#### 5.1.8 HTF Multiplier

```python
# Range: 0.7 - 1.3
htf_alignment = htf_result.get('alignment', False)

if htf_alignment:
    htf_multiplier = 1.3  # +30% bonus
else:
    htf_multiplier = 0.7  # -30% penalty
```

#### 5.1.9 Volatility Multiplier

```python
# Range: 0.6 - 1.5
# استفاده از risk_multiplier از VolatilityAnalyzer
volatility_multiplier = volatility_result.get('risk_multiplier', 1.0)
```

#### 5.1.10 Correlation Factor

```python
# فقط زمانی اعمال می‌شود که همبستگی بالا باشد:
if correlation_factor < 0.7:
    final_score *= correlation_factor  # کاهش امتیاز
```

#### 5.1.11 مثال کامل محاسبه

```python
# ─── فاز 1: Base Score ───
base_score = 74.05  # (از مثال قبل)

# ─── فاز 2: Confluence ───
confluence_bonus = 0.325  # +32.5%

# ─── فاز 3: Multipliers ───
timeframe_weight = 1.0      # 1h (reference)
trend_alignment = 1.2       # Perfect
volume_confirmation = 1.1   # Confirmed
pattern_quality = 1.2       # 2 patterns
macd_analysis_score = 1.2   # Aligned
htf_multiplier = 1.3        # HTF aligned
volatility_multiplier = 1.0 # Normal

# ─── فاز 4: محاسبه Final Score ───
final_score = 74.05 * (1.0 + 0.325) * 1.0 * 1.2 * 1.1 * 1.2 * 1.2 * 1.3 * 1.0
            = 74.05 * 1.325 * 1.0 * 1.2 * 1.1 * 1.2 * 1.2 * 1.3 * 1.0
            = 74.05 * 3.014
            = 223.24

# ─── فاز 5: Correlation (اختیاری) ───
correlation_factor = 0.85
final_score = 223.24 * 0.85 = 189.75

# ─── فاز 6: تعیین قدرت ───
if final_score >= 150:
    signal_strength = 'strong'  # ✅✅✅
elif final_score >= 80:
    signal_strength = 'medium'
else:
    signal_strength = 'weak'

# نتیجه:
{
    'final_score': 189.75,
    'signal_strength': 'strong',
    'confidence': 0.85,
    'components': {
        'base_score': 74.05,
        'confluence_bonus': 0.325,
        'trend_alignment': 1.2,
        'volume_confirmation': 1.1,
        'pattern_quality': 1.2,
        'macd_analysis_score': 1.2,
        'htf_multiplier': 1.3,
        'volatility_multiplier': 1.0,
        'correlation_factor': 0.85
    }
}
```

#### 5.1.12 محدوده‌های Signal Strength

```python
if final_score < 80:
    signal_strength = 'weak'
elif final_score < 150:
    signal_strength = 'medium'
else:
    signal_strength = 'strong'
```

---

## بخش ۶: تجمیع Multi-Timeframe (OLD SYSTEM Mode)

### 6.1 MultiTimeframeAggregator

**محل:** `signal_generation/multi_tf_aggregator.py`

**هدف:** ترکیب سیگنال‌های چند تایم‌فریم با وزن‌دهی (OLD SYSTEM logic - کامل).

#### 6.1.1 تایم‌فریم‌ها و وزن‌ها

```python
DEFAULT_TF_WEIGHTS = {
    '5m': 0.7,   # -30% importance (OLD SYSTEM value)
    '15m': 0.85, # -15% importance (OLD SYSTEM value)
    '1h': 1.0,   # Reference
    '4h': 1.2    # +20% importance
}
```

**منطق وزن‌دهی:**
- **5m:** وزن کم (0.7) - برای زمان‌بندی دقیق ورود
- **15m:** وزن پایین (0.85) - برای تأیید ورود
- **1h:** وزن پایه (1.0) - تایم‌فریم مرجع برای تأیید ترند
- **4h:** بالاترین وزن (1.2) - برای جهت کلی و فیلتر

#### 6.1.2 Multipliers از OLD SYSTEM

```python
# Phase Multipliers (فاز ترند):
PHASE_MULTIPLIERS = {
    'early': 1.2,       # +20% - بهترین فرصت
    'developing': 1.1,  # +10%
    'mature': 0.9,      # -10% - احتیاط
    'late': 0.7,        # -30% - پرریسک
    'pullback': 1.1,    # +10%
    'transition': 0.8,  # -20%
    'undefined': 1.0    # بدون تغییر
}

# MACD Type Strength (قدرت نوع MACD):
MACD_TYPE_STRENGTH = {
    'A': 1.2,  # A_ types (قوی صعودی) +20%
    'C': 1.2,  # C_ types (قوی نزولی) +20%
    'B': 1.0,  # B_ types (خنثی)
    'D': 1.0,  # D_ types (خنثی)
    'X': 0.8   # X_ types (انتقالی) -20%
}
```

#### 6.1.3 الگوریتم تجمیع (OLD SYSTEM - دقیق)

**قدم 1: محاسبه جداگانه Bullish و Bearish Scores**

```python
def _calculate_aggregate_scores(timeframe_signals):
    """
    محاسبه امتیازات صعودی و نزولی برای همه TF ها.

    این الگوریتم دقیقاً از OLD SYSTEM کپی شده.
    """
    bullish_score = 0.0
    bearish_score = 0.0

    for tf, tf_signal in timeframe_signals.items():
        tf_weight = tf_weights[tf]  # 0.7, 0.85, 1.0, 1.2
        context = tf_signal.context

        # ─── 1. Trend Contribution (با Phase Multiplier) ───
        trend_result = context.get_result('trend')
        if trend_result:
            trend_strength = trend_result['strength']  # 0-3
            trend_direction = trend_result['direction']  # 'bullish'/'bearish'
            trend_phase = trend_result['phase']  # 'early', 'mature', ...

            # Phase multiplier اعمال می‌شود:
            phase_multiplier = PHASE_MULTIPLIERS[trend_phase]

            if trend_direction == 'bullish':
                bullish_score += trend_strength × tf_weight × phase_multiplier
            elif trend_direction == 'bearish':
                bearish_score += trend_strength × tf_weight × phase_multiplier

        # ─── 2. Momentum Contribution (با MACD Type Strength) ───
        momentum_result = context.get_result('momentum')
        if momentum_result:
            mom_strength = momentum_result['strength']  # 0-3
            mom_direction = momentum_result['direction']
            macd_market_type = momentum_result.get('macd_market_type', '')

            # MACD type multiplier:
            # مثلاً: "A_bullish_strong" → type_prefix = 'A' → 1.2
            type_prefix = macd_market_type[0] if macd_market_type else ''
            macd_type_multiplier = MACD_TYPE_STRENGTH.get(type_prefix, 1.0)

            if mom_direction == 'bullish':
                bullish_score += mom_strength × tf_weight × macd_type_multiplier
            elif mom_direction == 'bearish':
                bearish_score += mom_strength × tf_weight × macd_type_multiplier

        # ─── 3. Pattern Contribution (کمک کمتر: ×0.5) ───
        pattern_result = context.get_result('patterns')
        if pattern_result and pattern_result.get('patterns'):
            for pattern in pattern_result['patterns']:
                pattern_score = pattern['score']
                pattern_direction = pattern['direction']

                if pattern_direction == 'bullish':
                    bullish_score += pattern_score × tf_weight × 0.5
                elif pattern_direction == 'bearish':
                    bearish_score += pattern_score × tf_weight × 0.5

        # ─── 4. S/R Breakout Contribution (بونوس بزرگ: ×1.5) ───
        sr_result = context.get_result('support_resistance')
        if sr_result:
            broken_levels = sr_result.get('broken_levels', [])
            for broken in broken_levels:
                strength = broken.get('original_strength', 1)

                if broken['broken_direction'] == 'upward':
                    # شکست مقاومت = صعودی
                    bullish_score += strength × tf_weight × 1.5
                else:
                    # شکست حمایت = نزولی
                    bearish_score += strength × tf_weight × 1.5

        # ─── 5. Cyclical Forecast Contribution ───
        cyclical_result = context.get_result('cyclical')
        if cyclical_result and 'signal' in cyclical_result:
            signal = cyclical_result['signal']
            if signal.get('direction') == 'bullish':
                bullish_score += signal.get('score', 0) × tf_weight
            elif signal.get('direction') == 'bearish':
                bearish_score += signal.get('score', 0) × tf_weight

    return bullish_score, bearish_score
```

**قدم 2: تعیین جهت نهایی (با حاشیه 10%)**

```python
def _determine_direction(bullish_score, bearish_score):
    """
    تعیین جهت نهایی با margin 1.1 (مثل OLD SYSTEM).

    - اگر bullish > bearish × 1.1 → LONG
    - اگر bearish > bullish × 1.1 → SHORT
    - در غیر این صورت → NEUTRAL (سیگنال رد می‌شود)
    """
    if bullish_score > bearish_score × 1.1:
        return 'LONG'
    elif bearish_score > bullish_score × 1.1:
        return 'SHORT'
    else:
        return 'NEUTRAL'  # عدم قاطعیت - سیگنال رد می‌شود
```

**قدم 3: محاسبه Alignment Factor**

```python
def _calculate_alignment_factor(timeframe_signals, final_direction):
    """
    محاسبه فاکتور هماهنگی (OLD SYSTEM).

    فرمول:
    1. Trend alignment: 50% وزن
    2. Momentum alignment: 30% وزن
    3. MACD alignment: 20% وزن

    خروجی: 0.7 - 1.3
    """
    aligned_trend = 0
    total_trend = 0
    aligned_momentum = 0
    total_momentum = 0
    aligned_macd = 0
    total_macd = 0

    for tf_signal in timeframe_signals.values():
        context = tf_signal.context

        # Trend alignment check:
        trend_result = context.get_result('trend')
        if trend_result and trend_result.get('direction'):
            total_trend += 1
            trend_dir = trend_result['direction']
            if (final_direction == 'LONG' and trend_dir == 'bullish') or \
               (final_direction == 'SHORT' and trend_dir == 'bearish'):
                aligned_trend += 1

        # Momentum alignment check:
        momentum_result = context.get_result('momentum')
        if momentum_result and momentum_result.get('direction'):
            total_momentum += 1
            mom_dir = momentum_result['direction']
            if (final_direction == 'LONG' and mom_dir == 'bullish') or \
               (final_direction == 'SHORT' and mom_dir == 'bearish'):
                aligned_momentum += 1

        # MACD alignment check:
        if momentum_result and momentum_result.get('macd_signal'):
            total_macd += 1
            macd_dir = momentum_result['macd_signal']['direction']
            if (final_direction == 'LONG' and macd_dir == 'bullish') or \
               (final_direction == 'SHORT' and macd_dir == 'bearish'):
                aligned_macd += 1

    # Calculate ratios:
    trend_ratio = aligned_trend / total_trend if total_trend > 0 else 0.0
    momentum_ratio = aligned_momentum / total_momentum if total_momentum > 0 else 0.0
    macd_ratio = aligned_macd / total_macd if total_macd > 0 else 0.0

    # Weighted combination (50%, 30%, 20%):
    weighted_alignment = (
        trend_ratio × 0.5 +
        momentum_ratio × 0.3 +
        macd_ratio × 0.2
    )

    # Convert to range 0.7 - 1.3:
    alignment_factor = 0.7 + (weighted_alignment × 0.6)

    return alignment_factor
```

**قدم 4-7: محاسبه عوامل اضافی**

```python
# Volume Factor (0.0 - 1.0):
# میانگین وزن‌دار تأیید حجم در همه TF ها
volume_factor = Σ(is_confirmed × tf_weight) / Σ(tf_weight)

# HTF Factor (0.8 - 1.5):
# محل در کد: multi_tf_aggregator.py:459-487
# فرمول: 0.8 + (alignment_ratio × 0.7)
alignment_ratio = count(htf_aligned) / count(htf_timeframes)
htf_factor = 0.8 + (alignment_ratio × 0.7)  # Range: 0.8 - 1.5

# Volatility Factor (0.5 - 1.0):
# محل در کد: multi_tf_aggregator.py:489-519
# توجه: risk_multiplier به محدوده OLD SYSTEM (0.5-1.0) Clamp می‌شود
# اگر risk_multiplier > 1.0 → به 1.0 کاهش
# اگر risk_multiplier < 0.5 → به 0.5 افزایش
volatility_factor = avg(min(max(risk_multiplier, 0.5), 1.0))
```

**قدم 8: استفاده از ConfidenceCalculator**

سیستم از یک `ConfidenceCalculator` جداگانه استفاده می‌کند که confidence level را محاسبه می‌کند.

#### 6.1.4 مثال کامل تجمیع

```python
# سیگنال‌های دریافتی از 4 تایم‌فریم:
timeframe_signals = {
    '5m': {
        'trend': {'strength': 2.0, 'direction': 'bullish', 'phase': 'early'},
        'momentum': {'strength': 2.5, 'direction': 'bullish', 'macd_market_type': 'A_bullish_strong'},
        'patterns': [{'score': 1.5, 'direction': 'bullish'}],
        'sr': {'broken_levels': [{'broken_direction': 'upward', 'original_strength': 2}]}
    },
    '15m': {
        'trend': {'strength': 2.5, 'direction': 'bullish', 'phase': 'developing'},
        'momentum': {'strength': 2.0, 'direction': 'bullish', 'macd_market_type': 'A_bullish_strong'}
    },
    '1h': {
        'trend': {'strength': 3.0, 'direction': 'bullish', 'phase': 'mature'},
        'momentum': {'strength': 2.5, 'direction': 'bullish', 'macd_market_type': 'B_bullish_normal'}
    },
    '4h': {
        'trend': {'strength': 2.5, 'direction': 'bullish', 'phase': 'developing'},
        'momentum': {'strength': 2.0, 'direction': 'bullish', 'macd_market_type': 'A_bullish_strong'}
    }
}

# ─── محاسبه Bullish Score ───
# 5m:
#   Trend: 2.0 × 0.7 × 1.2 (early) = 1.68
#   Momentum: 2.5 × 0.7 × 1.2 (A type) = 2.1
#   Pattern: 1.5 × 0.7 × 0.5 = 0.525
#   SR Breakout: 2 × 0.7 × 1.5 = 2.1
#   Total 5m: 6.405

# 15m:
#   Trend: 2.5 × 0.85 × 1.1 (developing) = 2.3375
#   Momentum: 2.0 × 0.85 × 1.2 (A type) = 2.04
#   Total 15m: 4.3775

# 1h:
#   Trend: 3.0 × 1.0 × 0.9 (mature) = 2.7
#   Momentum: 2.5 × 1.0 × 1.0 (B type) = 2.5
#   Total 1h: 5.2

# 4h:
#   Trend: 2.5 × 1.2 × 1.1 (developing) = 3.3
#   Momentum: 2.0 × 1.2 × 1.2 (A type) = 2.88
#   Total 4h: 6.18

# ─── جمع کل ───
bullish_score = 6.405 + 4.3775 + 5.2 + 6.18 = 22.1625
bearish_score = 0.0

# ─── تعیین جهت ───
bullish > bearish × 1.1 → LONG ✅

# ─── Alignment Factor ───
# همه 4 TF trend و momentum دارند که bullish هستند
trend_ratio = 4/4 = 1.0
momentum_ratio = 4/4 = 1.0
macd_ratio = 4/4 = 1.0

weighted_alignment = (1.0 × 0.5) + (1.0 × 0.3) + (1.0 × 0.2) = 1.0
alignment_factor = 0.7 + (1.0 × 0.6) = 1.3  # حداکثر!

# ─── نتیجه نهایی ───
{
    'direction': 'LONG',
    'final_score': 22.16,
    'alignment_factor': 1.3,      # عالی
    'volume_factor': 0.85,
    'htf_factor': 1.0,
    'volatility_factor': 1.0,
    'confidence': 'high'
}
```

---

### 5.2 STEP 6.5: Correlation Manager Check (بررسی همبستگی)

**محل:** `orchestrator.py:413-430`

**هدف:** جلوگیری از باز کردن معاملات بیش از حد همبستگی در یک جهت

این مرحله **اختیاری** است و فقط اگر Correlation Manager فعال باشد اجرا می‌شود.

```python
# بررسی اینکه آیا Correlation Manager فعال است
if self.correlation_manager.enabled:
    # دریافت ضریب ایمنی همبستگی برای این نماد و جهت
    correlation_factor = self.correlation_manager.get_correlation_safety_factor(
        symbol, direction
    )

    # اگر همبستگی بالا باشد (factor < 0.7)
    if correlation_factor < 0.7:
        logger.info(
            f"High correlation exposure for {symbol} "
            f"(factor: {correlation_factor:.2f}). "
            f"Reducing signal score."
        )

        # کاهش امتیاز سیگنال بر اساس همبستگی
        score.final_score *= correlation_factor
        score.correlation_safety_factor = correlation_factor

        # به‌روزرسانی امتیاز در signal
        signal.score = score
```

**چه اتفاقی می‌افتد؟**

- اگر معاملات همبستگی بالایی در یک جهت باز باشند (مثلاً چند LONG در BTC, ETH, BNB)
- ضریب ایمنی کمتر از 1.0 محاسبه می‌شود
- امتیاز نهایی سیگنال کاهش می‌یابد
- این باعث می‌شود سیگنال‌های بیش از حد همبسته با امتیاز پایین‌تر رد شوند

**مثال:**
```python
# فرض کنید 3 معامله LONG باز داریم:
# - BTCUSDT LONG (همبستگی بالا با ETH)
# - ETHUSDT LONG (همبستگی بالا با BTC)
# - BNBUSDT LONG (همبستگی بالا با BTC و ETH)

# سیگنال جدید ADAUSDT LONG:
original_score = 75.0
correlation_factor = 0.65  # همبستگی بالا تشخیص داده شد

# امتیاز کاهش می‌یابد:
new_score = 75.0 * 0.65 = 48.75

# با این امتیاز پایین‌تر، ممکن است در Validator رد شود
```

📌 **توجه:** اگر Correlation Manager غیرفعال باشد، این بخش skip می‌شود و امتیاز تغییر نمی‌کند.

---

## بخش ۷: اعتبارسنجی و خروجی نهایی

### 7.1 STEP 7: SignalValidator

**محل:** `signal_generation/signal_validator.py`

**هدف:** اعتبارسنجی کامل سیگنال با 9 بررسی جداگانه.

#### 7.1.1 پارامترهای Validator

```python
# === Risk/Reward Parameters ===
min_rr_ratio = 1.8              # حداقل RR (OLD SYSTEM: 2.0)
preferred_rr_ratio = 2.5         # RR مطلوب
max_risk_percent = 2.0           # حداکثر ریسک: 2%

# === Circuit Breaker Parameters ===
max_signals_per_hour = 3         # حداکثر 3 سیگنال در ساعت
max_signals_per_day = 10         # حداکثر 10 سیگنال در روز
cooldown_after_loss = 30         # 30 دقیقه cooldown بعد از ضرر

# === Correlation Parameters ===
max_correlation = 0.8            # حداکثر همبستگی مجاز
check_btc_correlation = True     # بررسی همبستگی با BTC

# === Portfolio Parameters ===
max_total_exposure = 0.5         # 50% کل سرمایه
max_per_symbol = 0.1             # 10% per symbol
max_same_direction = 0.3         # 30% در یک جهت
max_open_positions = 5           # حداکثر 5 پوزیشن باز

# === Time Filters ===
avoid_weekends = False           # اجتناب از آخر هفته‌ها
avoid_major_news = True          # اجتناب از اخبار مهم
trading_hours = None             # ساعات معاملاتی

# === Adaptive Threshold Parameters ===
enable_adaptive = True           # فعال‌سازی adaptive thresholds
performance_window_days = 7      # 7 روز گذشته
good_performance_threshold = 0.6 # 60% win rate
poor_performance_threshold = 0.4 # 40% win rate
```

#### 7.1.2 9 بررسی اعتبارسنجی

```python
def validate(self, signal: SignalInfo, context: AnalysisContext) -> Tuple[bool, str]:
    """
    اعتبارسنجی کامل سیگنال با 9 گام.

    Returns:
        (is_valid, rejection_reason)
    """

    # ─── 1. Basic Validation ───
    # بررسی موارد ابتدایی: symbol معتبر، direction معتبر، قیمت‌ها > 0
    if not self._validate_basic(signal):
        return False, "Basic validation failed"

    # ─── 2. Price Validation ───
    # بررسی منطق قیمت‌ها:
    #   - LONG: entry > SL, TP > entry
    #   - SHORT: entry < SL, TP < entry
    if not signal.validate_prices():
        return False, "Invalid price levels"

    # ─── 3. Risk/Reward Validation ───
    if signal.risk_reward_ratio < self.min_rr_ratio:  # 1.8
        return False, f"RR ratio too low: {signal.risk_reward_ratio:.2f}"

    risk_percent = signal.risk_percent
    if risk_percent > self.max_risk_percent:  # 2.0%
        return False, f"Risk too high: {risk_percent:.2f}%"

    # ─── 4. Circuit Breaker Check ───
    # بررسی تعداد سیگنال‌های اخیر:
    recent_signals_1h = self._count_recent_signals(hours=1)
    if recent_signals_1h >= self.max_signals_per_hour:  # 3
        return False, f"Too many signals in 1h: {recent_signals_1h}"

    recent_signals_24h = self._count_recent_signals(hours=24)
    if recent_signals_24h >= self.max_signals_per_day:  # 10
        return False, f"Too many signals in 24h: {recent_signals_24h}"

    # بررسی cooldown بعد از ضرر:
    if self._in_cooldown_after_loss():
        return False, "In cooldown period after recent loss"

    # ─── 5. Correlation Check ───
    # بررسی همبستگی با پوزیشن‌های باز:
    if self.check_btc_correlation:
        correlation = self._get_btc_correlation(signal.symbol)
        if correlation > self.max_correlation:  # 0.8
            return False, f"High BTC correlation: {correlation:.2f}"

    # ─── 6. Volatility Rejection Check (CRITICAL) ───
    # رد سیگنال در شرایط نوسان بسیار بالا:
    volatility_result = context.get_result('volatility')
    if volatility_result:
        volatility_regime = volatility_result.get('volatility_regime')
        confidence = signal.score.confidence if signal.score else 0.5

        if volatility_regime == 'high' and confidence < 0.75:
            return False, "Insufficient confidence for high volatility"

        # ویژه: نوسان بسیار بالا (extreme):
        if volatility_regime == 'extreme':
            return False, "Extreme volatility - rejecting all signals"

    # ─── 7. Portfolio Exposure Check ───
    # بررسی محدودیت‌های سبد:
    total_exposure = self._calculate_total_exposure()
    if total_exposure >= self.max_total_exposure:  # 0.5 (50%)
        return False, f"Portfolio exposure limit: {total_exposure:.1%}"

    symbol_exposure = self._get_symbol_exposure(signal.symbol)
    if symbol_exposure >= self.max_per_symbol:  # 0.1 (10%)
        return False, f"Symbol exposure limit: {symbol_exposure:.1%}"

    same_direction_exposure = self._get_direction_exposure(signal.direction)
    if same_direction_exposure >= self.max_same_direction:  # 0.3 (30%)
        return False, f"{signal.direction} exposure limit: {same_direction_exposure:.1%}"

    if len(self.active_positions) >= self.max_open_positions:  # 5
        return False, f"Max positions limit: {len(self.active_positions)}"

    # ─── 8. Time-Based Filters ───
    now = datetime.now()

    # آخر هفته:
    if self.avoid_weekends and now.weekday() >= 5:  # Sat/Sun
        return False, "Avoiding weekend trading"

    # ساعات معاملاتی:
    if self.trading_hours:
        current_hour = now.hour
        if not (self.trading_hours['start'] <= current_hour < self.trading_hours['end']):
            return False, f"Outside trading hours: {current_hour}:00"

    # ─── 9. Score Threshold Check (با Adaptive Adjustment) ───
    # حد آستانه پویا بر اساس عملکرد اخیر:
    min_score = self._get_adaptive_score_threshold()

    final_score = signal.score.final_score if signal.score else 0
    if final_score < min_score:
        return False, f"Score too low: {final_score:.2f} < {min_score:.2f}"

    # ✅ همه بررسی‌ها پاس شد
    return True, "All validation checks passed"
```

**Adaptive Score Threshold:**

```python
# محل در کد: signal_validator.py:524-570
def _check_score_threshold(self, signal: SignalInfo) -> Tuple[bool, str]:
    """
    بررسی حد آستانه امتیاز با تنظیم پویا.

    منطق:
    - عملکرد خوب (win rate > 60%) → threshold کاهش -10% (بیشتر سیگنال)
    - عملکرد ضعیف (win rate < 40%) → threshold افزایش +20% (کمتر سیگنال)
    - عملکرد متوسط → threshold استاندارد
    """
    if not signal.score:
        return False, "Signal missing score"

    # دریافت حد آستانه پایه از config
    # محل: config.yaml → signal_processing.validation.min_signal_score
    base_min_score = self.config.get('signal_processing', {}).get('validation', {}).get('min_signal_score', 50.0)
    # مقدار پیش‌فرض در config: 60

    # تنظیم پویا بر اساس عملکرد اخیر
    min_score = base_min_score

    if self.enable_adaptive:
        win_rate = self._calculate_recent_win_rate()

        if win_rate > self.good_performance_threshold:  # >60%
            # عملکرد خوب → threshold کمتر
            min_score = base_min_score * 0.9  # -10%
            # مثال: 60 × 0.9 = 54
        elif win_rate < self.poor_performance_threshold:  # <40%
            # عملکرد ضعیف → threshold بیشتر
            min_score = base_min_score * 1.2  # +20%
            # مثال: 60 × 1.2 = 72
        # else: min_score = base_min_score (عملکرد متوسط)

    # بررسی آستانه
    if signal.score.final_score < min_score:
        return False, f"Score too low: {signal.score.final_score:.2f} < {min_score:.2f}"

    return True, ""
```

**مثال با config.yaml (min_signal_score: 60):**
- Adaptive غیرفعال: **60**
- Win rate > 60%: **54** (60 × 0.9)
- Win rate < 40%: **72** (60 × 1.2)
- Win rate 40-60%: **60** (بدون تغییر)

#### 7.1.2 محاسبه Risk/Reward

```python
def calculate_risk_reward(self, entry, stop_loss, take_profit):
    """
    محاسبه نسبت Risk/Reward.
    """
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    
    if risk == 0:
        return 0
    
    rr_ratio = reward / risk
    
    return rr_ratio

# مثال:
entry = 50,000
stop_loss = 49,000  # -1000 (2%)
take_profit = 53,000  # +3000 (6%)

risk = 1000
reward = 3000
rr_ratio = 3000 / 1000 = 3.0  # ✅ عالی
```

#### 7.1.3 محاسبه Entry/SL/TP

```python
# ─── برای خرید (Long) ───
entry_price = current_price

# Stop Loss (2× ATR زیر entry):
stop_loss = entry_price - (ATR × 2)

# Take Profit (3× ATR بالای entry):
take_profit = entry_price + (ATR × 3)

# مثال:
current_price = 50,000
ATR = 550

entry = 50,000
stop_loss = 50,000 - (550 × 2) = 48,900  # -2.2%
take_profit = 50,000 + (550 × 3) = 51,650  # +3.3%

risk = 1100 (2.2%)
reward = 1650 (3.3%)
rr_ratio = 1650 / 1100 = 1.5  # قابل قبول
```

### 7.2 خروجی نهایی: SignalInfo

```python
class SignalInfo:
    """
    اطلاعات کامل سیگنال.
    """
    symbol: str
    direction: str  # 'buy' or 'sell'
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    
    score: ScoreInfo  # امتیاز کامل
    
    timeframe: str
    timestamp: datetime
    
    risk_reward_ratio: float
    risk_percent: float
    
    metadata: Dict  # اطلاعات اضافی
```

**مثال خروجی نهایی:**

```python
{
    'symbol': 'BTCUSDT',
    'direction': 'buy',
    'entry_price': 50000.0,
    'stop_loss': 48900.0,
    'take_profit': 51650.0,
    'position_size': 0.02,  # BTC
    
    'score': {
        'final_score': 42.43,
        'signal_strength': 'very_strong',
        'confidence': 0.92,
        'components': {...}
    },
    
    'timeframe': '1h',
    'timestamp': '2024-01-15 15:30:00',
    
    'risk_reward_ratio': 1.5,
    'risk_percent': 2.2,
    
    'metadata': {
        'regime': 'strong_trend_normal',
        'trend_phase': 'mature',
        'volume_pattern': 'spike',
        'patterns_detected': ['hammer', 'bullish_engulfing'],
        'timeframes_agreed': 4
    }
}
```

---

### 7.2 STEP 8: Register & Cache & Send (ثبت، ذخیره‌سازی و ارسال)

**محل:** `orchestrator.py:447-471`

**هدف:** ثبت سیگنال معتبر و ذخیره در cache برای بهبود عملکرد

این مرحله بعد از تایید اعتبار سیگنال (STEP 7) اجرا می‌شود.

```python
# === SUCCESS ===
self.stats.valid_signals += 1

logger.info(
    f"✅ Valid signal generated for {symbol} {direction}! "
    f"Score: {score.final_score:.2f}, RR: {signal.risk_reward_ratio:.2f}"
)

# 1. ثبت سیگنال در SignalValidator
self.signal_validator.register_signal(signal)

# 2. ذخیره در TimeframeScoreCache برای استفاده‌های بعدی
self.tf_score_cache.update_cache(symbol, timeframe, signal, df)
logger.debug(f"💾 Cached signal for {symbol} {timeframe}")

# 3. ذخیره context برای جلوگیری از محاسبه مجدد
cache_key = f"{symbol}:{timeframe}"
self._context_cache[cache_key] = (context, time.time())
logger.debug(f"💾 Cached context for {symbol} {timeframe}")

# 4. ارسال به TradeManager (اگر فعال باشد)
if self.send_to_trade_manager and self.trade_manager_callback:
    await self._send_to_trade_manager(signal)

return signal
```

**عملیات در این مرحله:**

1. **Register Signal:** ثبت سیگنال در `SignalValidator` برای:
   - محدودیت تعداد سیگنال در واحد زمان
   - جلوگیری از سیگنال‌های تکراری برای یک نماد
   - ردیابی آمار سیگنال‌ها

2. **Update TimeframeScoreCache:** ذخیره امتیاز محاسبه شده برای:
   - جلوگیری از محاسبه مجدد تا کندل جدید بیاید
   - بهبود سرعت پردازش
   - کاهش بار CPU

3. **Cache Context:** ذخیره `AnalysisContext` برای:
   - استفاده در Multi-TF Aggregation
   - دسترسی سریع به نتایج analyzers
   - جلوگیری از محاسبه دوباره indicators

4. **Send to TradeManager (اختیاری):** ارسال سیگنال به مدیریت معاملات برای:
   - بررسی نهایی Risk Management
   - باز کردن معامله (اگر شرایط مناسب باشد)
   - ثبت در سیستم معاملاتی

**آمار و Logging:**

```python
# آمار به‌روزرسانی می‌شود:
self.stats.valid_signals += 1
self.stats.total_time += elapsed
self.stats.avg_time_per_symbol = total_time / total_symbols_processed

# Log نهایی:
logger.info(
    f"=== Completed {symbol} in {elapsed:.2f}s "
    f"(avg: {self.stats.avg_time_per_symbol:.2f}s) ==="
)
```

📌 **نتیجه نهایی:** یک `SignalInfo` معتبر و کامل که آماده استفاده است.

---

**✅ تمام 8 مرحله (STEP 0-8) مستندات کامل شد!**

**خلاصه کل مستندات:**

**بخش 1:** معماری و نقاط ورودی (SignalProcessor → Orchestrator)
**بخش 2:** محاسبه اندیکاتورها (8 اندیکاتور)
**بخش 3:** تحلیل با 11 Analyzer + Market Regime + STEP 5
**بخش 4:** سیستم‌های هوشمند (Circuit Breaker, AdaptiveLearning, Correlation)
**بخش 5:** امتیازدهی سیگنال (Pattern Recency, Context Bonuses, Regime Multiplier)
**بخش 6:** تجمیع Multi-Timeframe (وزن‌دهی OLD SYSTEM)
**بخش 7:** اعتبارسنجی، همبستگی، و خروجی نهایی (Correlation Manager, Validation, Cache)

**آمار نهایی:**
- خطوط کل: ~7000+ خط
- حجم: ~210KB
- کامل‌تر از OLD SYSTEM (8202 خط) با جزئیات بیشتر در برخی بخش‌ها

**تفاوت‌های کلیدی NEW vs OLD:**
- ✅ Modular Architecture
- ✅ Context Sharing بین Analyzers
- ✅ Caching System
- ✅ 5 MACD Market Types (A, B, C, D, X)
- ✅ Pattern Recency Scoring
- ✅ Adaptive Learning
- ✅ Correlation Management
- ✅ Circuit Breaker
- ✅ Multi-TF Weighted Aggregation

**مستندات کامل است و آماده استفاده!** 🎉

