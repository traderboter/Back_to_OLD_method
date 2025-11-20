# تغییرات مورد نیاز برای بازگرداندن منطق سیستم قدیم با ساختار ماژولار جدید

## مقدمه

این سند تمام تغییرات لازم برای بازگرداندن منطق سیستم قدیم (Old_bot) را با حفظ ساختار ماژولار جدید (signal_generation) مستند می‌کند.

**هدف اصلی:** سیستم جدید باید دقیقاً مانند سیستم قدیم کار کند، اما با معماری ماژولار و تمیز.

---

## 🔍 خلاصه تفاوت‌های اصلی

### سیستم قدیم (OLD SYSTEM)

```
Old_bot/signal_generator.py: یک فایل مونولیتیک با 5600+ خط
├─ analyze_symbol(symbol, timeframes_data: Dict[str, DataFrame])
│  ├─ برای هر تایم‌فریم (5m, 15m, 1h, 4h):
│  │  └─ analyze_single_timeframe() → نتایج تحلیل
│  ├─ calculate_multi_timeframe_score() → جمع امتیازهای همه TFها
│  ├─ calculate_risk_reward() → محاسبه SL/TP با 5 روش
│  └─ تولید یک SignalInfo نهایی
```

### سیستم جدید (NEW SYSTEM)

```
signal_generation/ (ماژولار)
├─ orchestrator.py
│  ├─ generate_signal_for_symbol(symbol, timeframe) → تک‌تایم‌فریم
│  └─ analyze_symbol(symbol, timeframes_data) → مولتی‌تایم‌فریم
│     ├─ برای هر TF: _generate_signal_with_context()
│     └─ multi_tf_aggregator.aggregate_timeframe_scores()
├─ analyzers/ (11 ماژول جدا)
├─ signal_scorer.py → امتیازدهی ساده‌تر
└─ orchestrator._build_signal_info() → محاسبه SL/TP با ATR
```

---

## 📋 بخش 1: تغییرات مورد نیاز در Stop-Loss و Take-Profit

### ❌ مشکل فعلی

**کد فعلی** (`signal_generation/orchestrator.py:635-693`):
```python
# فقط ATR-based
volatility_result = context.get_result('volatility')
atr = volatility_result.get('atr_value')
stop_atr_mult = volatility_result.get('recommended_stop_atr', 2.0)

stop_distance = atr * stop_atr_mult

if direction == 'LONG':
    stop_loss = entry - stop_distance
    default_tp = entry + (stop_distance * 2)  # Fixed RR = 2.0
```

**مشکلات:**
1. فقط یک روش ATR-based
2. نادیده گرفتن Harmonic Patterns
3. نادیده گرفتن Price Channels
4. نادیده گرفتن S/R levels برای SL
5. RR ثابت = 2.0 (در سیستم قدیم configurable بود)

### ✅ راه‌حل: پیاده‌سازی سیستم 5 روشی

**فایل جدید پیشنهادی:** `signal_generation/risk_calculator.py`

```python
class RiskRewardCalculator:
    """
    محاسبه SL/TP مشابه سیستم قدیم با 5 روش اولویت‌دار:

    1. Harmonic Pattern-based
    2. Price Channel-based
    3. Support/Resistance-based
    4. ATR-based (fallback)
    5. Percentage-based (final fallback)
    """

    def calculate_sl_tp(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        محاسبه SL/TP با روش اولویت‌دار مانند سیستم قدیم.

        محل در سیستم قدیم: Old_bot/signal_generator.py:4016-4264
        """

        stop_loss = None
        take_profit = None
        calculation_method = "None"

        # روش 1: Harmonic Patterns
        stop_loss, take_profit, method = self._try_harmonic_sl_tp(
            direction, entry_price, context
        )
        if stop_loss:
            calculation_method = method
            return self._finalize_sl_tp(...)

        # روش 2: Price Channels
        stop_loss, take_profit, method = self._try_channel_sl_tp(
            direction, entry_price, context
        )
        if stop_loss:
            calculation_method = method
            return self._finalize_sl_tp(...)

        # روش 3: S/R Levels
        stop_loss, take_profit, method = self._try_sr_sl_tp(
            direction, entry_price, context, config
        )

        # بررسی فاصله: اگر بیش از 3×ATR باشد، رد شود
        if stop_loss:
            atr = context.get_indicator_value('atr')
            sl_dist_atr_ratio = abs(entry_price - stop_loss) / atr
            if sl_dist_atr_ratio > 3.0:
                stop_loss = None  # فاصله زیاد، استفاده از روش بعدی

        if stop_loss:
            calculation_method = method
            # محاسبه TP بر اساس S/R
            take_profit = self._calculate_tp_from_sl(...)
            return self._finalize_sl_tp(...)

        # روش 4: ATR-based
        atr = context.get_indicator_value('atr')
        sl_multiplier = config.get('atr_trailing_multiplier', 2.0)

        if direction == 'long':
            stop_loss = entry_price - (atr * sl_multiplier)
        else:
            stop_loss = entry_price + (atr * sl_multiplier)

        calculation_method = f"ATR x{sl_multiplier}"

        # محاسبه TP
        preferred_rr = config.get('preferred_risk_reward_ratio', 2.0)
        risk_distance = abs(entry_price - stop_loss)

        if direction == 'long':
            take_profit = entry_price + (risk_distance * preferred_rr)
        else:
            take_profit = entry_price - (risk_distance * preferred_rr)

        # تنظیم TP بر اساس S/R نزدیک
        take_profit = self._adjust_tp_with_sr(
            direction, take_profit, entry_price, context, risk_distance, config
        )

        return self._finalize_sl_tp(
            stop_loss, take_profit, calculation_method, entry_price, config
        )

    def _try_harmonic_sl_tp(self, direction, entry, context):
        """
        روش 1: استفاده از Harmonic Pattern
        محل در سیستم قدیم: signal_generator.py:4061-4091
        """
        harmonic_result = context.get_result('harmonic')
        if not harmonic_result or not harmonic_result.get('patterns'):
            return None, None, None

        patterns = harmonic_result['patterns']
        best_pattern = max(patterns, key=lambda p: p.get('confidence', 0))

        pattern_direction = best_pattern.get('direction')
        if (direction == 'LONG' and pattern_direction != 'bullish') or \
           (direction == 'SHORT' and pattern_direction != 'bearish'):
            return None, None, None

        points = best_pattern.get('points', {})
        if 'D' not in points or 'X' not in points:
            return None, None, None

        d_price = points['D']['price']
        x_price = points['X']['price']
        pattern_type = best_pattern.get('type', '')

        if direction == 'LONG':
            sl = d_price * 0.99  # 1% below D point

            # TP based on pattern type
            if 'butterfly' in pattern_type or 'crab' in pattern_type:
                tp = entry + (entry - sl) * 1.618
            else:
                tp = x_price  # Target to X point

        else:  # SHORT
            sl = d_price * 1.01  # 1% above D point

            if 'butterfly' in pattern_type or 'crab' in pattern_type:
                tp = entry - (sl - entry) * 1.618
            else:
                tp = x_price

        method = f"Harmonic_{pattern_type}"
        return sl, tp, method

    def _try_channel_sl_tp(self, direction, entry, context):
        """
        روش 2: استفاده از Price Channel
        محل در سیستم قدیم: signal_generator.py:4093-4125
        """
        channel_result = context.get_result('channel')
        if not channel_result or not channel_result.get('channels'):
            return None, None, None

        channel = channel_result['channels'][0]
        channel_direction = channel.get('direction')

        if direction == 'LONG' and channel_direction in ['ascending', 'horizontal']:
            # SL: below lower channel line
            lower_current = channel['lower_current_price']
            sl = lower_current * 0.99

            # TP: to upper channel line
            upper_current = channel['upper_current_price']
            tp = upper_current * 0.99

            method = f"Price_Channel_{channel_direction}"
            return sl, tp, method

        elif direction == 'SHORT' and channel_direction in ['descending', 'horizontal']:
            # SL: above upper channel line
            upper_current = channel['upper_current_price']
            sl = upper_current * 1.01

            # TP: to lower channel line
            lower_current = channel['lower_current_price']
            tp = lower_current * 1.01

            method = f"Price_Channel_{channel_direction}"
            return sl, tp, method

        return None, None, None

    def _try_sr_sl_tp(self, direction, entry, context, config):
        """
        روش 3: استفاده از Support/Resistance
        محل در سیستم قدیم: signal_generator.py:4127-4147
        """
        sr_result = context.get_result('support_resistance')
        if not sr_result:
            return None, None, None

        nearest_support = sr_result.get('nearest_support')
        nearest_resistance = sr_result.get('nearest_resistance')

        if direction == 'LONG' and nearest_support and nearest_support < entry:
            sl = nearest_support * 0.999
            method = "Support Level"
            return sl, None, method  # TP will be calculated later

        elif direction == 'SHORT' and nearest_resistance and nearest_resistance > entry:
            sl = nearest_resistance * 1.001
            method = "Resistance Level"
            return sl, None, method

        return None, None, None

    def _adjust_tp_with_sr(self, direction, tp, entry, context, risk_dist, config):
        """
        تنظیم TP بر اساس S/R نزدیک
        محل در سیستم قدیم: signal_generator.py:4198-4212
        """
        sr_result = context.get_result('support_resistance')
        if not sr_result:
            return tp

        min_rr = config.get('min_risk_reward_ratio', 1.5)
        nearest_support = sr_result.get('nearest_support')
        nearest_resistance = sr_result.get('nearest_resistance')

        if direction == 'LONG' and nearest_resistance:
            # اگر resistance نزدیک‌تر از TP باشد
            if nearest_resistance < tp:
                # فقط اگر حداقل RR را حفظ کند
                if nearest_resistance > entry + (risk_dist * min_rr):
                    tp = nearest_resistance * 0.999

        elif direction == 'SHORT' and nearest_support:
            if nearest_support > tp:
                if nearest_support < entry - (risk_dist * min_rr):
                    tp = nearest_support * 1.001

        return tp

    def _finalize_sl_tp(self, sl, tp, method, entry, config):
        """
        بررسی‌های نهایی و safety checks
        محل در سیستم قدیم: signal_generator.py:4166-4243
        """
        # محاسبه RR نهایی
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

        return {
            'stop_loss': round(sl, 8),
            'take_profit': round(tp, 8),
            'risk_reward_ratio': round(rr, 2),
            'risk_amount_per_unit': round(risk, 8),
            'sl_method': method
        }
```

**تغییرات لازم در `orchestrator.py`:**

```python
# line ~635
def _build_signal_info(self, context, direction, score):
    """Build SignalInfo with entry/SL/TP."""

    # استفاده از RiskRewardCalculator جدید به جای کد فعلی
    risk_calculator = RiskRewardCalculator(self.config)

    sl_tp_result = risk_calculator.calculate_sl_tp(
        direction=direction,
        entry_price=entry,
        context=context,
        config=self.config.get('risk_management', {})
    )

    stop_loss = sl_tp_result['stop_loss']
    take_profit = sl_tp_result['take_profit']
    risk_reward_ratio = sl_tp_result['risk_reward_ratio']
    sl_method = sl_tp_result['sl_method']

    # بررسی min RR
    min_rr = self.config.get('risk_management', {}).get('min_risk_reward_ratio', 1.5)
    if risk_reward_ratio < min_rr:
        logger.info(
            f"Rejected {symbol}: RR {risk_reward_ratio:.2f} < {min_rr:.2f} "
            f"(SL method: {sl_method})"
        )
        return None

    # ... ادامه ساخت SignalInfo
```

---

## 📋 بخش 2: تغییرات مورد نیاز در Scoring System

### ❌ مشکل فعلی

**سیستم قدیم**: 13 multiplier/coefficient برای امتیازدهی نهایی
```python
# Old_bot/signal_generator.py:5050-5113
score.final_score = (
    score.base_score *
    score.timeframe_weight *         # Higher TF confirmation
    score.trend_alignment *          # Trend alignment
    score.volume_confirmation *      # Volume confirmation
    score.pattern_quality *          # Pattern quality
    (1.0 + score.confluence_score) * # Confluence (includes RR)
    score.symbol_performance_factor * # Symbol history
    score.correlation_safety_factor * # Correlation safety
    score.macd_analysis_score *      # MACD analysis
    score.structure_score *          # HTF structure
    score.volatility_score *         # Volatility
    score.harmonic_pattern_score *   # Harmonic patterns
    score.price_channel_score *      # Price channels
    score.cyclical_pattern_score     # Cyclical patterns
)
```

**سیستم جدید**: ساده‌تر، با confidence metrics
```python
# signal_generation/signal_scorer.py:~200
final_score = (
    base_score *
    trend_multiplier *
    momentum_multiplier *
    volume_multiplier *
    pattern_multiplier
)
```

### ✅ راه‌حل: بازگرداندن سیستم امتیازدهی قدیمی

**تغییرات در `signal_generation/signal_scorer.py`:**

```python
class SignalScorer:
    """
    امتیازدهی سیگنال مشابه سیستم قدیم
    """

    def calculate_score(
        self,
        context: AnalysisContext,
        direction: str,
        timeframe_data: Dict[str, Any] = None  # 🆕 برای multi-TF
    ) -> SignalScore:
        """
        محاسبه امتیاز با روش سیستم قدیم (13 ضریب).

        محل در سیستم قدیم: signal_generator.py:5050-5113
        """
        score = SignalScore()

        # 1. Base Score
        score.base_score = self._calculate_base_score(context, direction)

        # 2. Timeframe Weight (higher TF confirmation)
        if timeframe_data:
            score.timeframe_weight = self._calculate_timeframe_weight(
                timeframe_data, direction
            )
        else:
            score.timeframe_weight = 1.0

        # 3. Trend Alignment
        score.trend_alignment = self._calculate_trend_alignment(
            context, direction, timeframe_data
        )

        # 4. Volume Confirmation
        score.volume_confirmation = self._calculate_volume_confirmation(
            context, timeframe_data
        )

        # 5. Pattern Quality
        score.pattern_quality = self._calculate_pattern_quality(context)

        # 6. Confluence Score (includes RR)
        score.confluence_score = self._calculate_confluence_score(
            context, direction
        )

        # 7. Symbol Performance Factor (از adaptive learning)
        if self.adaptive_learning and self.adaptive_learning.enabled:
            symbol = context.symbol
            score.symbol_performance_factor = \
                self.adaptive_learning.get_symbol_performance_factor(symbol, direction)
        else:
            score.symbol_performance_factor = 1.0

        # 8. Correlation Safety Factor
        if self.correlation_manager and self.correlation_manager.enabled:
            symbol = context.symbol
            score.correlation_safety_factor = \
                self.correlation_manager.get_correlation_safety_factor(symbol, direction)
        else:
            score.correlation_safety_factor = 1.0

        # 9. MACD Analysis Score
        score.macd_analysis_score = self._calculate_macd_score(
            context, timeframe_data
        )

        # 10. HTF Structure Score
        score.structure_score = self._calculate_structure_score(
            context, direction, timeframe_data
        )

        # 11. Volatility Score
        score.volatility_score = self._calculate_volatility_score(context)

        # 12. Harmonic Pattern Score
        score.harmonic_pattern_score = self._calculate_harmonic_score(context)

        # 13. Price Channel Score
        score.price_channel_score = self._calculate_channel_score(context)

        # 14. Cyclical Pattern Score
        score.cyclical_pattern_score = self._calculate_cyclical_score(context)

        # ✅ محاسبه نهایی (مانند سیستم قدیم)
        score.final_score = (
            score.base_score *
            score.timeframe_weight *
            score.trend_alignment *
            score.volume_confirmation *
            score.pattern_quality *
            (1.0 + score.confluence_score) *
            score.symbol_performance_factor *
            score.correlation_safety_factor *
            score.macd_analysis_score *
            score.structure_score *
            score.volatility_score *
            score.harmonic_pattern_score *
            score.price_channel_score *
            score.cyclical_pattern_score
        )

        return score

    def _calculate_timeframe_weight(self, timeframe_data, direction):
        """
        محاسبه timeframe_weight بر اساس تأیید TFهای بالاتر.

        محل در سیستم قدیم: signal_generator.py:5055-5078
        """
        if not timeframe_data:
            return 1.0

        # شناسایی reversal
        is_reversal = timeframe_data.get('is_reversal', False)
        reversal_strength = timeframe_data.get('reversal_strength', 0)

        # محاسبه higher TF confirmations
        primary_tf = timeframe_data['primary_timeframe']
        successful_tfs = timeframe_data['analysis_results']

        primary_tf_weight = self.timeframe_weights.get(primary_tf, 1.0)

        higher_tf_confirmations = 0
        total_higher_tfs = 0

        for tf, result in successful_tfs.items():
            tf_weight = self.timeframe_weights.get(tf, 1.0)

            if tf_weight > primary_tf_weight:
                total_higher_tfs += 1
                trend_dir = result.get('trend', {}).get('trend', 'neutral')

                if (direction == 'LONG' and 'bullish' in trend_dir) or \
                   (direction == 'SHORT' and 'bearish' in trend_dir):
                    higher_tf_confirmations += 1

        higher_tf_ratio = higher_tf_confirmations / total_higher_tfs if total_higher_tfs > 0 else 0

        if is_reversal:
            reversal_modifier = max(0.3, 1.0 - (reversal_strength * 0.7))
            return 1.0 + (higher_tf_ratio * 0.3 * reversal_modifier)
        else:
            return 1.0 + (higher_tf_ratio * 0.5)

    def _calculate_trend_alignment(self, context, direction, timeframe_data):
        """
        محاسبه trend_alignment.

        محل در سیستم قدیم: signal_generator.py:5071-5078
        """
        if not timeframe_data:
            trend_result = context.get_result('trend')
            if not trend_result:
                return 1.0

            strength = abs(trend_result.get('strength', 0))
            return 1.0 + (strength * 0.2)

        # با توجه به reversal
        is_reversal = timeframe_data.get('is_reversal', False)
        reversal_strength = timeframe_data.get('reversal_strength', 0)

        if is_reversal:
            return max(0.5, 1.0 - (reversal_strength * 0.5))

        # Primary trend strength
        primary_tf = timeframe_data['primary_timeframe']
        analysis_results = timeframe_data['analysis_results']

        primary_result = analysis_results.get(primary_tf, {})
        primary_trend_strength = abs(
            primary_result.get('trend', {}).get('strength', 0)
        )

        return 1.0 + (primary_trend_strength * 0.2)

    # ... ادامه پیاده‌سازی بقیه متدها
```

---

## 📋 بخش 3: تغییرات مورد نیاز در Multi-Timeframe Handling

### ❌ مشکل فعلی

**وضعیت فعلی**: سیستم جدید دارای `multi_tf_aggregator.py` است که منطق سیستم قدیم را پیاده می‌کند، اما:

1. ✅ **خبر خوب**: `orchestrator.analyze_symbol()` از multi-TF aggregator استفاده می‌کند
2. ❌ **خبر بد**: سیستم فعلی هر TF را به صورت جداگانه analyze می‌کند، نه داخل یک تحلیل واحد

**تفاوت کلیدی**:

```
سیستم قدیم:
analyze_symbol(symbol, {5m: df, 15m: df, 1h: df, 4h: df})
  ├─ برای هر TF: analyze_single_timeframe()
  ├─ calculate_multi_timeframe_score(all_results)
  └─ یک SignalInfo

سیستم جدید:
analyze_symbol(symbol, {5m: df, 15m: df, 1h: df, 4h: df})
  ├─ برای هر TF: generate_signal_for_symbol(symbol, TF) → SignalInfo جدا
  ├─ multi_tf_aggregator.aggregate_timeframe_scores(signals)
  └─ یک SignalInfo aggregated
```

**مشکل**: در سیستم جدید، هر TF یک SignalInfo کامل (با SL/TP) دارد که بعداً aggregate می‌شوند.
در سیستم قدیم، ابتدا نتایج تحلیل (بدون SL/TP) aggregate می‌شوند، سپس یک SL/TP نهایی محاسبه می‌شود.

### ✅ راه‌حل: بازسازی جریان سیستم قدیم

**گزینه 1 (پیشنهادی): نگه‌داشتن رویکرد فعلی با بهبودها**

```python
# orchestrator.py:analyze_symbol()

async def analyze_symbol(
    self,
    symbol: str,
    timeframes_data: Dict[str, DataFrame]
) -> Optional[SignalInfo]:
    """
    تحلیل multi-timeframe (شبیه سیستم قدیم با ساختار ماژولار).
    """

    # 1. تحلیل هر TF و جمع‌آوری contexts (نه signals)
    timeframe_contexts: Dict[str, AnalysisContext] = {}

    for timeframe, df in timeframes_data.items():
        context = AnalysisContext(symbol, timeframe, df)

        # محاسبه indicators
        self.indicator_calculator.calculate_all(context)

        # اجرای analyzers
        for analyzer in self.analyzers.values():
            analyzer.analyze(context)

        timeframe_contexts[timeframe] = context

    # 2. محاسبه امتیاز multi-timeframe (مانند سیستم قدیم)
    score_result = self._calculate_multi_timeframe_score(
        symbol,
        timeframe_contexts
    )

    final_direction = score_result['final_direction']
    if final_direction == 'NEUTRAL':
        return None

    # 3. انتخاب primary TF (کوچکترین)
    primary_tf = min(timeframe_contexts.keys(), key=self._get_tf_minutes)
    primary_context = timeframe_contexts[primary_tf]

    # 4. محاسبه Score نهایی
    score = self.signal_scorer.calculate_score(
        context=primary_context,
        direction=final_direction,
        timeframe_data={
            'primary_timeframe': primary_tf,
            'analysis_results': {
                tf: self._context_to_analysis_result(ctx)
                for tf, ctx in timeframe_contexts.items()
            },
            'is_reversal': score_result.get('is_reversal', False),
            'reversal_strength': score_result.get('reversal_strength', 0)
        }
    )

    # 5. محاسبه SL/TP (با highest TF context)
    highest_tf = max(timeframe_contexts.keys(), key=lambda tf: self.timeframe_weights.get(tf, 1.0))
    highest_context = timeframe_contexts[highest_tf]

    sl_tp_result = self.risk_calculator.calculate_sl_tp(
        direction=final_direction,
        entry_price=primary_context.df['close'].iloc[-1],
        context=highest_context,  # استفاده از highest TF برای SL/TP
        config=self.config.get('risk_management', {})
    )

    # بررسی min RR
    min_rr = self.config.get('signal_generation', {}).get('min_risk_reward_ratio', 1.5)
    if sl_tp_result['risk_reward_ratio'] < min_rr:
        return None

    # بررسی min score
    min_score = self.config.get('signal_generation', {}).get('minimum_signal_score', 50.0)
    if score.final_score < min_score:
        return None

    # 6. ساخت SignalInfo نهایی
    signal = SignalInfo(
        symbol=symbol,
        timeframe=primary_tf,
        signal_type='multi_timeframe',
        direction=final_direction,
        entry_price=primary_context.df['close'].iloc[-1],
        stop_loss=sl_tp_result['stop_loss'],
        take_profit=sl_tp_result['take_profit'],
        risk_reward_ratio=sl_tp_result['risk_reward_ratio'],
        timestamp=datetime.now(timezone.utc),
        pattern_names=score_result['pattern_names'],
        score=score,
        confirmation_timeframes=list(timeframe_contexts.keys())
    )

    return signal

def _calculate_multi_timeframe_score(
    self,
    symbol: str,
    timeframe_contexts: Dict[str, AnalysisContext]
) -> Dict[str, Any]:
    """
    محاسبه امتیاز multi-timeframe مانند سیستم قدیم.

    محل در سیستم قدیم: signal_generator.py:5197-5434
    """
    bullish_score = 0.0
    bearish_score = 0.0
    all_patterns = []

    for tf, context in timeframe_contexts.items():
        tf_weight = self.timeframe_weights.get(tf, 1.0)

        # 1. Trend scores
        trend_result = context.get_result('trend')
        if trend_result:
            trend_strength = trend_result.get('strength', 0)
            trend_phase = trend_result.get('phase', 'undefined')

            phase_multiplier = self._get_trend_phase_multiplier(trend_phase)

            if trend_strength > 0:
                bullish_score += trend_strength * tf_weight * phase_multiplier
            elif trend_strength < 0:
                bearish_score += abs(trend_strength) * tf_weight * phase_multiplier

        # 2. Momentum scores
        momentum_result = context.get_result('momentum')
        if momentum_result:
            momentum_strength = momentum_result.get('momentum_strength', 1.0)
            bullish_score += momentum_result.get('bullish_score', 0) * tf_weight * momentum_strength
            bearish_score += momentum_result.get('bearish_score', 0) * tf_weight * momentum_strength

        # 3. Pattern scores
        pattern_result = context.get_result('patterns')
        if pattern_result:
            for pattern in pattern_result.get('patterns', []):
                pattern_score = pattern['score'] * tf_weight
                all_patterns.append(pattern['type'])

                if pattern['direction'] == 'bullish':
                    bullish_score += pattern_score
                else:
                    bearish_score += pattern_score

        # 4. Harmonic patterns
        harmonic_result = context.get_result('harmonic')
        if harmonic_result:
            for pattern in harmonic_result.get('patterns', []):
                confidence = pattern.get('confidence', 0.7)
                pattern_score = 4.0 * confidence * tf_weight
                all_patterns.append(pattern['type'])

                if pattern['direction'] == 'bullish':
                    bullish_score += pattern_score
                else:
                    bearish_score += pattern_score

        # ... و غیره (S/R breakouts, channels, cycles)

    # تعیین جهت نهایی (با margin 10%)
    margin = 1.1
    if bullish_score > bearish_score * margin:
        final_direction = 'LONG'
    elif bearish_score > bullish_score * margin:
        final_direction = 'SHORT'
    else:
        final_direction = 'NEUTRAL'

    return {
        'final_bullish_score': round(bullish_score, 2),
        'final_bearish_score': round(bearish_score, 2),
        'final_direction': final_direction,
        'pattern_names': list(set(all_patterns))
    }
```

**گزینه 2 (ساده‌تر): استفاده از multi_tf_aggregator فعلی با بهبود**

multi_tf_aggregator فعلی خوب است، فقط باید:
1. ✅ مطمئن شوید که `use_multi_tf_aggregation=True` در config
2. ✅ SL/TP را بعد از aggregation محاسبه کنید (نه قبل)
3. ✅ از highest TF context برای محاسبه SL/TP استفاده کنید

---

## 📋 بخش 4: تغییرات در Analyzer Outputs

### ❌ مشکل

سیستم قدیم برای هر تحلیل، اطلاعات جزئی بیشتری برمی‌گرداند که در scoring استفاده می‌شود.

مثال: `MACD market_type` در سیستم قدیم:
```python
# Old_bot/signal_generator.py:5258-5269
macd_market_type = macd_data.get('market_type', 'unknown')
macd_type_strength = 1.0
if macd_market_type.startswith('A_'):  # A_bullish_strong
    macd_type_strength = 1.2
elif macd_market_type.startswith('C_'):  # C_bearish_strong
    macd_type_strength = 1.2
else:
    macd_type_strength = 0.8

bullish_score += macd_data['bullish_score'] * tf_weight * macd_type_strength
```

### ✅ راه‌حل

اطمینان از اینکه هر analyzer خروجی‌های مورد نیاز سیستم قدیم را برگرداند:

**1. MomentumAnalyzer** - اضافه کردن `momentum_strength`:
```python
# signal_generation/analyzers/momentum_analyzer.py

def analyze(self, context):
    result = {
        'status': 'ok',
        'direction': direction,
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'momentum_strength': self._calculate_momentum_strength(context),  # 🆕
        'signals': signals
    }
    context.set_result('momentum', result)

def _calculate_momentum_strength(self, context):
    """محاسبه قدرت momentum (0.8 - 1.2)"""
    rsi = context.get_indicator_value('rsi')
    if rsi:
        if rsi > 70 or rsi < 30:
            return 1.2  # Strong momentum
        elif 60 < rsi < 70 or 30 < rsi < 40:
            return 1.1
        elif 40 <= rsi <= 60:
            return 0.9  # Weak momentum
    return 1.0
```

**2. TrendAnalyzer** - اضافه کردن `phase`:
```python
# signal_generation/analyzers/trend_analyzer.py

def analyze(self, context):
    result = {
        'status': 'ok',
        'direction': direction,
        'strength': strength,
        'phase': phase,  # ✅ قبلاً وجود دارد
        'method': 'ema_cross',
        'details': {...}
    }
```

**3. HTFAnalyzer** - بهبود محاسبه `structure_score`:
```python
# signal_generation/analyzers/htf_analyzer.py

def analyze(self, context):
    """
    تحلیل ساختار تایم‌فریم بالاتر.

    باید مانند سیستم قدیم عمل کند:
    محل در سیستم قدیم: signal_generator.py:4292-4446
    """

    result = {
        'status': 'ok',
        'structure_score': structure_score,  # 0.5 - 1.5
        'trends_aligned': trends_aligned,
        'momentum_aligned': momentum_aligned,
        'at_support_zone': at_support_zone,
        'at_resistance_zone': at_resistance_zone,
        'details': {...}
    }
```

---

## 📋 بخش 5: Configuration Changes

برای اینکه سیستم جدید مانند سیستم قدیم کار کند، تنظیمات زیر باید به‌روز شوند:

```yaml
# config.yaml

orchestrator:
  # ✅ فعال کردن multi-TF aggregation
  use_multi_tf_aggregation: true

  # ✅ تعریف تایم‌فریم‌ها و وزن‌ها (مانند سیستم قدیم)
  timeframe_weights:
    5m: 0.15    # 15% weight
    15m: 0.20   # 20% weight
    1h: 0.30    # 30% weight
    4h: 0.35    # 35% weight

signal_generation:
  # ✅ حداقل امتیاز (مانند سیستم قدیم)
  minimum_signal_score: 50.0

  # ✅ حداقل RR (مانند سیستم قدیم)
  min_risk_reward_ratio: 1.5

risk_management:
  # ✅ RR ترجیحی (configurable، نه ثابت)
  preferred_risk_reward_ratio: 2.0

  # ✅ روش‌های محاسبه SL (اولویت‌بندی)
  sl_calculation_priority:
    - harmonic_pattern
    - price_channel
    - support_resistance
    - atr_based
    - percentage

  # ✅ multiplier برای ATR
  atr_trailing_multiplier: 2.0

  # ✅ حداکثر فاصله S/R به ATR
  max_sr_distance_atr_ratio: 3.0

  # ✅ default stop loss percent (fallback)
  default_stop_loss_percent: 1.5

signal_processing:
  multi_timeframe:
    # ✅ margin برای تعیین جهت (10%)
    direction_margin: 1.1

    # ✅ حداقل تایم‌فریم‌ها
    min_timeframes: 2

# ✅ فعال کردن سیستم‌های پشتیبان
adaptive_learning:
  enabled: true

correlation_manager:
  enabled: true

circuit_breaker:
  enabled: true

regime_detector:
  enabled: true
```

---

## 📋 بخش 6: خلاصه تغییرات فایل به فایل

### فایل‌های جدید (باید ایجاد شوند):

1. **`signal_generation/risk_calculator.py`** (جدید)
   - کلاس `RiskRewardCalculator`
   - 5 روش محاسبه SL (harmonic, channel, S/R, ATR, percentage)
   - adjustment TP بر اساس S/R
   - safety checks مانند سیستم قدیم

### فایل‌های موجود (باید تغییر کنند):

1. **`signal_generation/orchestrator.py`**
   - ✅ `analyze_symbol()`: از contexts استفاده کند، نه signals
   - ✅ `_build_signal_info()`: از `RiskRewardCalculator` استفاده کند
   - ✅ `_calculate_multi_timeframe_score()`: منطق سیستم قدیم را پیاده کند

2. **`signal_generation/signal_scorer.py`**
   - ✅ `calculate_score()`: 13 multiplier را پیاده کند
   - ✅ متدهای جدید برای هر multiplier
   - ✅ پارامتر `timeframe_data` برای multi-TF scoring

3. **`signal_generation/analyzers/momentum_analyzer.py`**
   - ✅ اضافه کردن `momentum_strength` به output

4. **`signal_generation/analyzers/htf_analyzer.py`**
   - ✅ بهبود محاسبه `structure_score` مانند سیستم قدیم

5. **`signal_generation/analyzers/channel_analyzer.py`**
   - ✅ اضافه کردن `lower_current_price` و `upper_current_price` به output

6. **`signal_generation/analyzers/harmonic_analyzer.py`**
   - ✅ اطمینان از وجود `points` dictionary در output pattern

7. **`config.yaml`**
   - ✅ به‌روزرسانی تنظیمات بر اساس بخش 5

---

## 📋 بخش 7: مراحل پیاده‌سازی (گام به گام)

### مرحله 1: ایجاد RiskRewardCalculator (روز 1)

```bash
# ایجاد فایل جدید
touch signal_generation/risk_calculator.py
```

**کارهای لازم:**
1. ✅ پیاده‌سازی کلاس `RiskRewardCalculator`
2. ✅ پیاده‌سازی 5 روش SL
3. ✅ پیاده‌سازی adjustment TP با S/R
4. ✅ پیاده‌سازی safety checks
5. ✅ نوشتن unit tests

### مرحله 2: بهبود Analyzers (روز 2)

1. ✅ `momentum_analyzer.py`: اضافه کردن `momentum_strength`
2. ✅ `channel_analyzer.py`: اضافه کردن current prices
3. ✅ `htf_analyzer.py`: بهبود `structure_score`
4. ✅ نوشتن tests

### مرحله 3: بازسازی SignalScorer (روز 3-4)

1. ✅ پیاده‌سازی 13 multiplier در `calculate_score()`
2. ✅ پیاده‌سازی هر متد محاسبه multiplier
3. ✅ اضافه کردن `timeframe_data` parameter
4. ✅ نوشتن tests

### مرحله 4: بهبود Orchestrator (روز 5-6)

1. ✅ بازسازی `analyze_symbol()` برای multi-TF
2. ✅ پیاده‌سازی `_calculate_multi_timeframe_score()`
3. ✅ تغییر `_build_signal_info()` برای استفاده از `RiskRewardCalculator`
4. ✅ نوشتن integration tests

### مرحله 5: به‌روزرسانی Config (روز 7)

1. ✅ به‌روزرسانی `config.yaml`
2. ✅ تست با تنظیمات جدید
3. ✅ مستندسازی تنظیمات

### مرحله 6: تست و Validation (روز 8-10)

1. ✅ مقایسه خروجی سیستم جدید با قدیم (با همان input)
2. ✅ بررسی SL/TP methods
3. ✅ بررسی scoring values
4. ✅ بررسی multi-TF aggregation
5. ✅ backtest برای تأیید عملکرد

---

## 📋 بخش 8: چک‌لیست نهایی

برای اطمینان از اینکه سیستم جدید مانند سیستم قدیم کار می‌کند:

### ✅ Multi-Timeframe Handling
- [ ] تمام 4 تایم‌فریم (5m, 15m, 1h, 4h) همزمان تحلیل می‌شوند
- [ ] وزن‌های تایم‌فریم درست اعمال می‌شوند (15%, 20%, 30%, 35%)
- [ ] Phase multipliers درست کار می‌کنند (early=1.2, mature=0.9, ...)
- [ ] MACD type strength اعمال می‌شود (A_=1.2, C_=1.2, X_=0.8)
- [ ] جهت نهایی با margin 10% تعیین می‌شود

### ✅ Stop-Loss / Take-Profit
- [ ] روش 1: Harmonic Pattern-based کار می‌کند
- [ ] روش 2: Price Channel-based کار می‌کند
- [ ] روش 3: S/R-based کار می‌کند
- [ ] بررسی فاصله max 3×ATR برای S/R
- [ ] روش 4: ATR-based (fallback)
- [ ] روش 5: Percentage-based (final fallback)
- [ ] TP با S/R نزدیک adjust می‌شود
- [ ] min RR check (1.5 پیش‌فرض)
- [ ] safety checks برای SL/TP

### ✅ Scoring System
- [ ] Base score محاسبه می‌شود
- [ ] Timeframe weight (higher TF confirmation)
- [ ] Trend alignment (with reversal handling)
- [ ] Volume confirmation (weighted)
- [ ] Pattern quality
- [ ] Confluence score (RR-based)
- [ ] Symbol performance factor
- [ ] Correlation safety factor
- [ ] MACD analysis score
- [ ] HTF structure score
- [ ] Volatility score
- [ ] Harmonic pattern score
- [ ] Price channel score
- [ ] Cyclical pattern score
- [ ] فرمول نهایی با 13 multiplier

### ✅ Analyzer Outputs
- [ ] Momentum: `momentum_strength` موجود است
- [ ] Trend: `phase` موجود است
- [ ] HTF: `structure_score`, `trends_aligned` موجود است
- [ ] Channel: `lower_current_price`, `upper_current_price` موجود است
- [ ] Harmonic: `points` dictionary موجود است

### ✅ Configuration
- [ ] `use_multi_tf_aggregation: true`
- [ ] Timeframe weights تنظیم شده
- [ ] `minimum_signal_score: 50.0`
- [ ] `min_risk_reward_ratio: 1.5`
- [ ] `preferred_risk_reward_ratio: 2.0`
- [ ] SL calculation priority تعریف شده
- [ ] سیستم‌های پشتیبان فعال هستند

---

## 🎯 نتیجه‌گیری

با اعمال تغییرات بالا، سیستم جدید:

1. ✅ **ساختار ماژولار** را حفظ می‌کند (11 analyzer جدا، orchestrator، scorer، ...)
2. ✅ **منطق سیستم قدیم** را پیاده می‌کند (multi-TF، 5 روش SL، 13 multiplier scoring)
3. ✅ **قابل تست** است (unit tests، integration tests)
4. ✅ **قابل نگهداری** است (separation of concerns، single responsibility)
5. ✅ **عملکرد مشابه** دارد (همان نتایج سیستم قدیم)

**زمان تخمینی پیاده‌سازی:** 7-10 روز کاری

**اولویت تغییرات:**
1. 🔴 بالا: RiskRewardCalculator، Multi-TF scoring
2. 🟡 متوسط: SignalScorer improvements، Analyzer outputs
3. 🟢 پایین: Config updates، Documentation

---

## 📚 منابع مرجع

- **سیستم قدیم**: `Old_bot/signal_generator.py`
  - Multi-TF scoring: خطوط 5197-5434
  - Risk/Reward: خطوط 4016-4264
  - Final scoring: خطوط 5050-5113

- **سیستم جدید**: `signal_generation/`
  - Orchestrator: `orchestrator.py`
  - Multi-TF: `multi_tf_aggregator.py`
  - Scoring: `signal_scorer.py`
  - Analyzers: `analyzers/*.py`

- **مستندات**: `docs/`
  - `Old_bot/Old_signal.md`: مستندات کامل سیستم قدیم
  - `docs/New_method_signal.md`: مستندات سیستم جدید
  - `docs/Comparison_Target_StopLoss.md`: مقایسه SL/TP

---

**تاریخ:** 2025-01-20
**نسخه:** 1.0
**وضعیت:** پیش‌نویس برای بررسی
