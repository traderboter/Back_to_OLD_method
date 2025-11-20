# 🎯 Per-Timeframe Configuration Design

## مشکل فعلی

سیستم از **یک مقدار ثابت** برای همه تایم‌فریم‌ها استفاده می‌کند:

```yaml
momentum_analyzer:
  rsi:
    oversold_threshold: 30    # همه TF ها!
    overbought_threshold: 70  # همه TF ها!
```

**چرا این مشکل است؟**

| تایم‌فریم | ویژگی | مشکل با threshold ثابت |
|----------|--------|----------------------|
| **5min** | نوسان زیاد، noise بالا | RSI=60 عادی است، نه خرید! |
| **15min** | نوسان متوسط | RSI=60 کمی صعودی |
| **1hour** | نوسان کم، روندها واضح‌تر | RSI=60 روند قوی |
| **4hour** | نوسان خیلی کم، روندهای قوی | RSI=60 روند خیلی قوی! |

---

## 💡 راه‌حل: Per-TF Thresholds

### طراحی config جدید

```yaml
signal_generation_v2:
  analyzers:

    # ─── Momentum Analyzer ───
    momentum_analyzer:
      enabled: True
      weight: 0.25

      # روش قدیمی (fallback):
      rsi:
        oversold_threshold: 30
        overbought_threshold: 70

      # 🆕 روش جدید (per-timeframe):
      rsi_per_timeframe:
        enabled: True  # فعال کردن per-TF thresholds

        '5m':
          oversold: 25      # سخت‌گیرانه‌تر (noise زیاد)
          overbought: 75    # سخت‌گیرانه‌تر
          extreme_oversold: 15
          extreme_overbought: 85

        '15m':
          oversold: 28
          overbought: 72
          extreme_oversold: 18
          extreme_overbought: 82

        '1h':
          oversold: 30      # استاندارد
          overbought: 70
          extreme_oversold: 20
          extreme_overbought: 80

        '4h':
          oversold: 35      # راحت‌تر (روندها قوی‌تر)
          overbought: 65    # راحت‌تر
          extreme_oversold: 25
          extreme_overbought: 75

      # MACD per-TF
      macd_per_timeframe:
        enabled: True

        '5m':
          histogram_threshold: 0.001  # کوچک‌تر (noise)
          crossover_sensitivity: 0.3

        '15m':
          histogram_threshold: 0.0005
          crossover_sensitivity: 0.4

        '1h':
          histogram_threshold: 0.0003
          crossover_sensitivity: 0.5

        '4h':
          histogram_threshold: 0.0002
          crossover_sensitivity: 0.6

      # Stochastic per-TF
      stochastic_per_timeframe:
        enabled: True

        '5m':
          oversold: 15
          overbought: 85

        '15m':
          oversold: 18
          overbought: 82

        '1h':
          oversold: 20
          overbought: 80

        '4h':
          oversold: 25
          overbought: 75

    # ─── Volume Analyzer ───
    volume_analyzer:
      enabled: True
      weight: 0.15

      # روش قدیمی:
      volume_thresholds:
        high_volume_ratio: 1.5
        confirmation_ratio: 1.2

      # 🆕 per-TF:
      volume_per_timeframe:
        enabled: True

        '5m':
          high_volume_ratio: 2.0      # نیاز به حجم بیشتر (noise)
          confirmation_ratio: 1.5
          low_volume_ratio: 0.6

        '15m':
          high_volume_ratio: 1.7
          confirmation_ratio: 1.3
          low_volume_ratio: 0.7

        '1h':
          high_volume_ratio: 1.5      # استاندارد
          confirmation_ratio: 1.2
          low_volume_ratio: 0.8

        '4h':
          high_volume_ratio: 1.3      # حجم کمتر کافی است
          confirmation_ratio: 1.1
          low_volume_ratio: 0.9

    # ─── Trend Analyzer ───
    trend_analyzer:
      enabled: True
      weight: 0.30

      # 🆕 per-TF:
      trend_strength_per_timeframe:
        enabled: True

        '5m':
          min_strength: 2      # نیاز به قوی‌تر (noise)
          strong_threshold: 4

        '15m':
          min_strength: 1
          strong_threshold: 3

        '1h':
          min_strength: 1
          strong_threshold: 3

        '4h':
          min_strength: 1      # روندها واضح‌ترند
          strong_threshold: 2

    # ─── Pattern Analyzer ───
    pattern_analyzer:
      enabled: True
      weight: 0.10

      # 🆕 الگوها در TF های بالاتر قوی‌ترند:
      pattern_scores_by_timeframe:
        hammer:
          '5m': 0.8
          '15m': 1.0
          '1h': 1.2
          '4h': 1.5

        bullish_engulfing:
          '5m': 1.0
          '15m': 1.25
          '1h': 1.5
          '4h': 1.8

        morning_star:
          '5m': 1.2
          '15m': 1.5
          '1h': 1.8
          '4h': 2.2

        # سایر الگوها...

    # ─── Volatility Analyzer ───
    volatility_analyzer:
      enabled: True
      weight: 0.07

      # 🆕 per-TF ATR thresholds:
      volatility_per_timeframe:
        enabled: True

        '5m':
          low_vol_threshold: 0.3
          high_vol_threshold: 1.0
          extreme_vol_threshold: 2.0

        '15m':
          low_vol_threshold: 0.4
          high_vol_threshold: 1.2
          extreme_vol_threshold: 2.5

        '1h':
          low_vol_threshold: 0.5
          high_vol_threshold: 1.5
          extreme_vol_threshold: 3.0

        '4h':
          low_vol_threshold: 0.6
          high_vol_threshold: 2.0
          extreme_vol_threshold: 4.0
```

---

## 🔧 تغییرات کد لازم

### 1. تغییر در BaseAnalyzer

```python
# signal_generation/analyzers/base_analyzer.py

class BaseAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    def get_threshold(
        self,
        param_name: str,
        default_value: Any,
        timeframe: str = None
    ) -> Any:
        """
        Get threshold value, per-TF if available.

        Args:
            param_name: Name of parameter (e.g., 'rsi_overbought')
            default_value: Fallback value
            timeframe: Current timeframe (e.g., '5m')

        Returns:
            Threshold value (per-TF or default)
        """
        analyzer_config = self.config.get('analyzers', {}).get(
            self.name.lower().replace('analyzer', '_analyzer'),
            {}
        )

        # Check for per-TF config
        per_tf_config_name = f"{param_name}_per_timeframe"
        per_tf_config = analyzer_config.get(per_tf_config_name, {})

        if per_tf_config.get('enabled', False) and timeframe:
            # Per-TF is enabled, get TF-specific value
            tf_value = per_tf_config.get(timeframe, {}).get(param_name.split('_')[-1])
            if tf_value is not None:
                return tf_value

        # Fallback to global config
        return analyzer_config.get(param_name, default_value)
```

### 2. تغییر در MomentumAnalyzer

```python
# signal_generation/analyzers/momentum_analyzer.py

class MomentumAnalyzer(BaseAnalyzer):
    def analyze(self, context: AnalysisContext) -> None:
        """Analyze momentum with per-TF thresholds."""

        # Get timeframe-aware thresholds
        timeframe = context.timeframe

        rsi_overbought = self.get_threshold(
            'rsi_overbought',
            RSI_OVERBOUGHT_THRESHOLD,
            timeframe
        )

        rsi_oversold = self.get_threshold(
            'rsi_oversold',
            RSI_OVERSOLD_THRESHOLD,
            timeframe
        )

        # استفاده:
        current_rsi = df['rsi'].iloc[-1]

        if current_rsi > rsi_overbought:
            # اشباع خرید (با threshold مخصوص این TF)
            ...
        elif current_rsi < rsi_oversold:
            # اشباع فروش
            ...
```

### 3. تغییر در VolumeAnalyzer

```python
# signal_generation/analyzers/volume_analyzer.py

class VolumeAnalyzer(BaseAnalyzer):
    def analyze(self, context: AnalysisContext) -> None:
        """Analyze volume with per-TF thresholds."""

        timeframe = context.timeframe

        high_volume_ratio = self.get_threshold(
            'high_volume_ratio',
            1.5,
            timeframe
        )

        confirmation_ratio = self.get_threshold(
            'confirmation_ratio',
            1.2,
            timeframe
        )

        # استفاده:
        volume_ratio = current_volume / volume_sma

        if volume_ratio >= high_volume_ratio:
            # حجم بالا (با threshold مخصوص این TF)
            ...
```

---

## 📊 مثال کاربرد واقعی

### سناریو: RSI=60

**با threshold ثابت (فعلی):**
```
همه TF ها: RSI=60 → زیر 70 → عادی
```

**با per-TF threshold (جدید):**
```
5m:  RSI=60 < 75 → عادی (noise)
15m: RSI=60 < 72 → کمی صعودی
1h:  RSI=60 < 70 → عادی
4h:  RSI=60 < 65 → نزدیک اشباع خرید! ⚠️
```

### سناریو: حجم معامله

**Volume Ratio = 1.4**

**با threshold ثابت:**
```
همه TF ها: 1.4 < 1.5 → عادی
```

**با per-TF threshold:**
```
5m:  1.4 < 2.0 → کم (noise زیاد، نیاز به حجم بیشتر)
15m: 1.4 < 1.7 → عادی
1h:  1.4 < 1.5 → نزدیک به بالا
4h:  1.4 > 1.3 → حجم بالا! ✅
```

---

## 🎯 مزایا

1. ✅ **دقت بیشتر**: هر TF با معیار مناسب خودش ارزیابی می‌شود
2. ✅ **noise کمتر در 5m**: thresholdهای سخت‌گیرانه‌تر
3. ✅ **سیگنال‌های قوی‌تر در 4h**: thresholdهای راحت‌تر
4. ✅ **قابلیت تنظیم**: می‌توان هر TF را جداگانه tune کرد
5. ✅ **سازگار با Multi-TF Aggregation**: هم threshold و هم weight

---

## 🔄 مراحل پیاده‌سازی

### فاز 1: توسعه کد (2-3 ساعت)
1. اضافه کردن `get_threshold()` به `BaseAnalyzer`
2. تغییر همه analyzers برای استفاده از `get_threshold()`
3. تست واحد

### فاز 2: تنظیمات اولیه (1 ساعت)
1. اضافه کردن per-TF config به `config.yaml`
2. مقادیر اولیه بر اساس نتایج optimizer

### فاز 3: تست و تنظیم دقیق (ongoing)
1. اجرای optimizer روی perfect trades
2. استفاده از نتایج برای fine-tuning
3. backtesting با مقادیر جدید

---

## 📝 یادداشت‌های مهم

1. **Backward Compatibility**:
   - اگر per-TF تنظیم نشده، از مقدار global استفاده می‌شود
   - سیستم قدیمی همچنان کار می‌کند

2. **Performance**:
   - تقریباً بدون overhead (فقط یک lookup)
   - کش می‌شود در هر analyzer

3. **Flexibility**:
   - می‌توان فقط برخی parameterها را per-TF کرد
   - مثلاً فقط RSI per-TF، بقیه global

4. **Optimization**:
   - optimizer جدید (`optimize_signal_parameters_multitf.py`)
   - مستقیماً per-TF thresholds پیشنهاد می‌دهد

---

## 🚀 نتیجه

این تغییر سیستم را **خیلی هوشمندتر** می‌کند:
- 5min: محافظه‌کارانه (noise زیاد)
- 4hour: اعتماد بیشتر (روندهای قوی)

**همراستا با فلسفه Multi-TF Aggregation**: هر TF با ویژگی‌های خودش ارزیابی می‌شود! 🎯
