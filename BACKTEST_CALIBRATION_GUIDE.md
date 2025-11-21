# 🎯 راهنمای Calibration پارامترها با Backtest

## 📋 مقدمه

این راهنما لیست کامل پارامترهایی که **باید** یا **می‌توانند** با backtest کالیبره شوند را ارائه می‌دهد.

**⚠️ هشدار مهم:** Over-fitting می‌تواند منجر به نتایج بسیار بد در live trading شود. همیشه:
- از validation set جداگانه استفاده کنید
- Walk-forward analysis انجام دهید
- در market regimes مختلف تست کنید

---

## 📊 Table of Contents

1. [پارامترهای حیاتی (Priority 1)](#1-پارامترهای-حیاتی-priority-1)
2. [پارامترهای مهم (Priority 2)](#2-پارامترهای-مهم-priority-2)
3. [پارامترهای پیشرفته (Priority 3)](#3-پارامترهای-پیشرفته-priority-3)
4. [پارامترهایی که نباید تغییر کنند](#4-پارامترهایی-که-نباید-تغییر-کنند)
5. [روش‌های Calibration](#5-روش-های-calibration)
6. [Backtest Strategy](#6-backtest-strategy)
7. [Walk-Forward Analysis](#7-walk-forward-analysis)
8. [Optimization Tips](#8-optimization-tips)

---

## 1️⃣ پارامترهای حیاتی (Priority 1)

این پارامترها **بیشترین تأثیر** را بر عملکرد سیستم دارند و **حتماً** باید calibrate شوند.

### 1.1 ⭐ Per-Timeframe Slope Thresholds (TrendAnalyzer)

**مکان:** `config.yaml > signal_generation > trend_detection > slope_thresholds`

**پارامترهای فعلی:**
```yaml
slope_thresholds:
  '5m': 0.15    # 15%
  '15m': 0.12   # 12%
  '1h': 0.10    # 10%
  '4h': 0.08    # 8%
```

**چرا مهم است؟**
- مستقیماً تشخیص trend را تعیین می‌کند
- threshold بالا → سیگنال‌های کمتر اما قوی‌تر
- threshold پایین → سیگنال‌های بیشتر اما ضعیف‌تر

**روش Calibration:**
```python
# Test ranges
slope_ranges = {
    '5m': [0.10, 0.12, 0.15, 0.18, 0.20],   # تست 5 مقدار
    '15m': [0.08, 0.10, 0.12, 0.14, 0.16],
    '1h': [0.06, 0.08, 0.10, 0.12, 0.14],
    '4h': [0.05, 0.06, 0.08, 0.10, 0.12]
}

# Metric to optimize
# - Win rate
# - Profit factor
# - Sharpe ratio
# - Max drawdown
```

**نتیجه مورد انتظار:**
- Timeframe‌های کوچک (5m, 15m): threshold بالاتر
- Timeframe‌های بزرگ (4h): threshold پایین‌تر
- هر ارز ممکن است threshold متفاوتی نیاز داشته باشد

**⚠️ خطر Over-fitting:**
- هر ارز را جداگانه optimize **نکنید** (احتمال over-fitting بالا)
- یک threshold global برای هر TF پیدا کنید که برای اکثریت ارزها کار کند

---

### 1.2 ⭐ Direction Determination Margin

**مکان:** `config.yaml > multi_timeframe > direction_margin`

**مقدار فعلی:** `1.3` (30% margin)

**چرا مهم است؟**
- تعیین می‌کند چه زمانی سیگنال LONG/SHORT صادر شود
- margin بالا → سیگنال‌های قوی‌تر اما کمتر
- margin پایین → سیگنال‌های بیشتر اما ضعیف‌تر

**روش Calibration:**
```python
# Test range
margins = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
# 1.1 = 10% margin (مانند OLD)
# 1.3 = 30% margin (فعلی NEW)
# 1.5 = 50% margin (بسیار محافظه‌کارانه)

# For each margin:
# - Count signals
# - Calculate win rate
# - Calculate profit factor
# - Calculate max drawdown

# Goal: Best balance between quantity and quality
```

**نتیجه مورد انتظار:**
- Market trending: margin پایین‌تر (1.1-1.2)
- Market choppy/ranging: margin بالاتر (1.4-1.5)
- **بهترین راه:** Adaptive margin بر اساس market regime

**💡 پیشنهاد پیشرفته:**
```yaml
# Adaptive margin based on regime
direction_margin:
  trending: 1.2      # در بازار trend دار
  ranging: 1.5       # در بازار range
  volatile: 1.4      # در بازار volatile
  default: 1.3       # پیش‌فرض
```

---

### 1.3 ⭐ Minimum Signal Score

**مکان:** `config.yaml > signal_generation > minimum_signal_score`

**مقدار فعلی:** `180.0`

**چرا مهم است؟**
- حداقل امتیاز برای صدور سیگنال
- تأثیر مستقیم بر تعداد و کیفیت سیگنال‌ها

**روش Calibration:**
```python
# Test range
min_scores = [140, 150, 160, 170, 180, 190, 200, 210, 220]

# برای هر مقدار:
# 1. تعداد سیگنال‌های تولید شده
# 2. Win rate
# 3. Average profit per trade
# 4. Max drawdown
# 5. Sharpe ratio

# Goal: Sweet spot between quantity and quality
```

**نمودار مورد انتظار:**
```
Signal Count vs Min Score

Count
  ^
  |  ●●●●
  |      ●●●●
  |          ●●●●
  |              ●●●
  |                  ●●●
  +----------------------> Min Score
    140  160  180  200  220

Win Rate vs Min Score

Rate
  ^
  |                  ●●●
  |              ●●●
  |          ●●●
  |      ●●●
  |  ●●●
  +----------------------> Min Score
    140  160  180  200  220

# Sweet spot: حدود 170-190
```

---

### 1.4 ⭐ Timeframe Weights

**مکان:** `config.yaml > signal_generation > timeframe_weights`

**مقادیر فعلی:**
```yaml
timeframe_weights:
  '5m': 0.7
  '15m': 0.85
  '1h': 1.0
  '4h': 1.1   # کاهش یافته از 1.2
```

**چرا مهم است؟**
- تعیین می‌کند هر TF چقدر در final score تأثیر دارد
- تأثیر مستقیم بر direction و score نهایی

**روش Calibration:**
```python
# Approach 1: Grid Search
weights_4h = [0.9, 1.0, 1.1, 1.2, 1.3]
weights_5m = [0.6, 0.7, 0.8, 0.9]

# Approach 2: Ratio-based
# همه weights را نسبت به 1h تنظیم کنید
base = 1.0  # 1h (reference)
ratios = {
    '5m': [0.6, 0.7, 0.8],
    '15m': [0.8, 0.85, 0.9],
    '4h': [1.0, 1.1, 1.2, 1.3]
}

# Test all combinations
# Metric: Weighted win rate across all TFs
```

**💡 Approach 3: Market Regime Adaptive**
```yaml
# در market trending، HTF مهم‌تر است
trending:
  '4h': 1.3
  '1h': 1.0
  '15m': 0.8
  '5m': 0.6

# در market choppy، LTF بهتر عمل می‌کند
ranging:
  '4h': 0.9
  '1h': 1.0
  '15m': 1.0
  '5m': 0.9
```

---

### 1.5 ⭐ Risk/Reward Ratios

**مکان:** `config.yaml > risk`

**پارامترهای فعلی:**
```yaml
risk:
  default_stop_loss_percent: 2.0        # SL پیش‌فرض
  preferred_risk_reward_ratio: 2.0      # RR ترجیحی
  min_risk_reward_ratio: 1.5            # حداقل RR
  atr_trailing_multiplier: 2.0          # ضریب ATR
```

**چرا مهم است؟**
- تعیین SL/TP و در نتیجه سود/ضرر هر معامله
- تأثیر مستقیم بر profit factor

**روش Calibration:**
```python
# Test combinations
sl_percents = [1.5, 2.0, 2.5, 3.0]
rr_ratios = [1.5, 2.0, 2.5, 3.0]
atr_multipliers = [1.5, 2.0, 2.5, 3.0]

# برای هر combination:
for sl in sl_percents:
    for rr in rr_ratios:
        for atr_mult in atr_multipliers:
            backtest_with_params(sl, rr, atr_mult)
            calculate_metrics()

# Metrics:
# - Win rate (کاهش با افزایش RR)
# - Average win/loss ratio
# - Profit factor
# - Max consecutive losses
```

**نتیجه مورد انتظار:**
```
# Market Trending
- SL: 2.5-3.0% (بزرگتر برای دادن فضا به trend)
- RR: 2.5-3.0 (target های بزرگتر)

# Market Ranging
- SL: 1.5-2.0% (کوچکتر برای حفاظت)
- RR: 1.5-2.0 (target های واقع‌بینانه)
```

---

### 1.6 ⭐ Circuit Breaker Thresholds

**مکان:** `config.yaml > circuit_breaker`

**پارامترهای فعلی:**
```yaml
circuit_breaker:
  max_consecutive_losses: 3      # تعداد ضرر متوالی
  max_daily_losses_r: 5.0        # حداکثر ضرر روزانه (R)
  cool_down_period_minutes: 60   # مدت توقف
```

**چرا مهم است؟**
- محافظت از سرمایه در بازار غیرعادی
- جلوگیری از ضررهای سنگین

**روش Calibration:**
```python
# Simulate on historical data
consecutive_losses = [2, 3, 4, 5]
daily_loss_r = [3.0, 4.0, 5.0, 6.0, 7.0]
cool_down_periods = [30, 60, 90, 120]  # minutes

# برای هر combination:
# 1. Count circuit breaker triggers
# 2. Analyze if they prevented losses
# 3. Analyze if they missed good opportunities
# 4. Calculate ROI with/without circuit breaker

# Goal: Minimize false positives while catching real crashes
```

**💡 Historical Analysis:**
```python
# بررسی crash های واقعی گذشته
crashes = [
    '2021-05-19',  # China ban
    '2022-06-18',  # UST/LUNA collapse
    '2022-11-09',  # FTX collapse
]

# آیا circuit breaker با تنظیمات فعلی trigger می‌شد؟
# آیا ضررها را کاهش می‌داد؟
```

---

## 2️⃣ پارامترهای مهم (Priority 2)

این پارامترها تأثیر متوسط دارند اما calibration آنها می‌تواند نتایج را بهبود دهد.

### 2.1 📊 Momentum Thresholds

**مکان:** `signal_generation/analyzers/momentum_analyzer.py`

**پارامترهای فعلی:**
```python
# خط 70-75 تقریباً
MOMENTUM_THRESHOLDS = {
    'strong': 0.6,     # 60% of bars in one direction
    'moderate': 0.45,  # 45%
    'weak': 0.3        # 30%
}
```

**روش Calibration:**
```python
# Test ranges
strong_thresholds = [0.55, 0.60, 0.65, 0.70]
moderate_thresholds = [0.40, 0.45, 0.50]
weak_thresholds = [0.25, 0.30, 0.35]

# Per timeframe calibration
MOMENTUM_THRESHOLDS_PER_TF = {
    '5m': {'strong': 0.65, 'moderate': 0.50, 'weak': 0.35},
    '15m': {'strong': 0.62, 'moderate': 0.47, 'weak': 0.32},
    '1h': {'strong': 0.60, 'moderate': 0.45, 'weak': 0.30},
    '4h': {'strong': 0.58, 'moderate': 0.43, 'weak': 0.28}
}
```

---

### 2.2 📊 MACD Market Type Strengths

**مکان:** `signal_generation/multi_tf_aggregator.py:78-85`

**مقادیر فعلی:**
```python
MACD_TYPE_STRENGTH = {
    'A': 1.2,  # A_ types (strong bullish) +20%
    'C': 1.2,  # C_ types (strong bearish) +20%
    'B': 1.0,  # B_ types (neutral)
    'D': 1.0,  # D_ types (neutral)
    'X': 0.8   # X_ types (transition) -20%
}
```

**روش Calibration:**
```python
# Test ranges
a_c_strengths = [1.1, 1.15, 1.2, 1.25, 1.3]
x_strengths = [0.6, 0.7, 0.8, 0.9]

# Analyze historical data:
# برای هر market type، win rate چقدر است؟
for market_type in ['A', 'B', 'C', 'D', 'X']:
    signals = filter_signals_by_macd_type(market_type)
    win_rate = calculate_win_rate(signals)
    # اگر win rate بالاست، strength را افزایش دهید
```

**💡 پیشنهاد:**
```python
# Separate bullish and bearish
MACD_TYPE_STRENGTH = {
    # Bullish types
    'A1': 1.3, 'A2': 1.25, 'A3': 1.2,
    'B1': 1.1, 'B2': 1.0, 'B3': 0.9,

    # Bearish types
    'C1': 1.3, 'C2': 1.25, 'C3': 1.2,
    'D1': 1.1, 'D2': 1.0, 'D3': 0.9,

    # Transition
    'X1': 0.9, 'X2': 0.8, 'X3': 0.7
}
```

---

### 2.3 📊 Pattern Scores Per Timeframe

**مکان:** `config.yaml > signal_generation > pattern_recognition > pattern_scores`

**مقادیر فعلی:**
```yaml
pattern_scores:
  '5m': 8
  '15m': 12
  '1h': 15
  '4h': 20
```

**روش Calibration:**
```python
# Analyze pattern effectiveness per TF
for tf in ['5m', '15m', '1h', '4h']:
    patterns_in_tf = get_patterns_in_timeframe(tf)

    # برای هر الگو:
    for pattern in patterns_in_tf:
        win_rate = calculate_pattern_win_rate(pattern, tf)
        avg_profit = calculate_pattern_avg_profit(pattern, tf)

    # اگر الگوها در یک TF بهتر عمل می‌کنند، score آن TF را افزایش دهید

# Test ranges
scores = {
    '5m': [6, 8, 10, 12],
    '15m': [10, 12, 14, 16],
    '1h': [13, 15, 17, 19],
    '4h': [18, 20, 22, 24]
}
```

**💡 پیشنهاد پیشرفته:**
```yaml
# Per-pattern scores per TF
pattern_scores_advanced:
  '5m':
    'engulfing': 10
    'hammer': 8
    'doji': 5
    # ...
  '1h':
    'engulfing': 18
    'hammer': 15
    'doji': 10
```

---

### 2.4 📊 Phase Multipliers

**مکان:** `signal_generation/multi_tf_aggregator.py:68-76`

**مقادیر فعلی:**
```python
PHASE_MULTIPLIERS = {
    'early': 1.2,       # +20% - Best opportunity
    'developing': 1.1,  # +10%
    'mature': 0.9,      # -10% - Caution
    'late': 0.7,        # -30% - Risky
    'pullback': 1.1,    # +10%
    'transition': 0.8,  # -20%
    'undefined': 1.0    # No change
}
```

**روش Calibration:**
```python
# Historical analysis
for phase in PHASE_MULTIPLIERS.keys():
    signals_in_phase = filter_signals_by_phase(phase)
    win_rate = calculate_win_rate(signals_in_phase)
    avg_rr = calculate_avg_rr(signals_in_phase)

    # اگر win rate بالا → multiplier را افزایش دهید
    # اگر win rate پایین → multiplier را کاهش دهید

# Test ranges
early_mults = [1.1, 1.15, 1.2, 1.25, 1.3]
late_mults = [0.5, 0.6, 0.7, 0.8]
```

---

### 2.5 📊 Confidence Score Thresholds

**مکان:** `signal_generation/systems/confidence_calculator.py` (احتمالاً)

**پارامترهای پیشنهادی:**
```yaml
confidence_thresholds:
  very_high: 0.85    # بسیار مطمئن
  high: 0.75         # مطمئن
  medium: 0.60       # متوسط
  low: 0.45          # کم

min_confidence_to_trade: 0.60  # حداقل confidence برای معامله
```

**روش Calibration:**
```python
# Backtest با confidence filtering
min_confidences = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]

for min_conf in min_confidences:
    signals = filter_signals_by_confidence(min_conf)

    metrics = {
        'count': len(signals),
        'win_rate': calculate_win_rate(signals),
        'profit_factor': calculate_profit_factor(signals),
        'sharpe': calculate_sharpe(signals)
    }

# Goal: بهترین balance بین تعداد و کیفیت
```

**نتیجه مورد انتظار:**
```
Confidence vs Win Rate

Win %
  ^
  |                      ●●●
  |                  ●●●
  |              ●●●
  |          ●●●
  |      ●●●
  |  ●●●
  +-----------------------> Min Confidence
    0.45  0.55  0.65  0.75  0.85

# Sweet spot: حدود 0.60-0.65
```

---

### 2.6 📊 Correlation Safety Thresholds

**مکان:** `config.yaml > correlation_management`

**پارامترهای فعلی:**
```yaml
correlation_management:
  correlation_threshold: 0.7        # حداقل برای گروه‌بندی
  max_exposure_per_group: 3         # حداکثر پوزیشن در گروه
```

**روش Calibration:**
```python
# Test ranges
corr_thresholds = [0.6, 0.65, 0.7, 0.75, 0.8]
max_exposures = [2, 3, 4, 5]

# برای هر combination:
for threshold in corr_thresholds:
    for max_exp in max_exposures:
        # تعداد گروه‌های ایجاد شده
        # تعداد سیگنال‌های رد شده به دلیل correlation
        # تأثیر بر drawdown
        # تأثیر بر diversification

# Goal: کاهش drawdown بدون از دست دادن سیگنال‌های خوب
```

---

## 3️⃣ پارامترهای پیشرفته (Priority 3)

این پارامترها تأثیر کمتری دارند اما fine-tuning آنها می‌تواند تفاوت ایجاد کند.

### 3.1 🔬 الگوهای کندلی فعال

**مکان:** `config.yaml > signal_generation > pattern_recognition > enabled_patterns`

**روش Calibration:**
```python
# Test each pattern individually
patterns = [
    'engulfing', 'hammer', 'shooting_star', 'doji',
    'morning_star', 'evening_star', 'three_white_soldiers',
    # ... all 16 patterns
]

for pattern in patterns:
    # فقط این الگو را فعال کنید
    signals = backtest_with_pattern(pattern)

    metrics = {
        'frequency': len(signals),
        'win_rate': calculate_win_rate(signals),
        'avg_profit': calculate_avg_profit(signals),
        'false_signals': count_false_signals(signals)
    }

# الگوهایی که win rate < 45% را غیرفعال کنید
# الگوهایی که win rate > 60% را score بالاتری دهید
```

---

### 3.2 🔬 Minimum Pattern Quality

**مکان:** `config.yaml > signal_generation > pattern_recognition > min_pattern_quality`

**مقدار فعلی:** `0.7`

**روش Calibration:**
```python
# Test range
min_qualities = [0.5, 0.6, 0.7, 0.8, 0.9]

for min_qual in min_qualities:
    signals = filter_patterns_by_quality(min_qual)

    # تعداد الگوهای باقی مانده
    # Win rate of remaining patterns
    # Average profit

# Higher quality → fewer but better patterns
```

---

### 3.3 🔬 Divergence Lookback Period

**مکان:** `config.yaml > signal_generation > momentum_analysis > divergence_lookback`

**مقدار فعلی:** `5`

**روش Calibration:**
```python
# Test ranges
lookbacks = [3, 4, 5, 6, 7, 8, 10]

for lookback in lookbacks:
    divergences = detect_divergences(lookback)

    # تعداد divergence های شناسایی شده
    # Win rate divergence signals
    # False positives

# Shorter lookback → more signals, more noise
# Longer lookback → fewer signals, more reliable
```

---

### 3.4 🔬 Anomaly Score Thresholds

**مکان:** `signal_generation/systems/emergency_circuit_breaker.py`

**Thresholds فعلی:**
```python
# Volume spike
vol_ratio > 3  # حجم 3 برابر میانگین

# Price change
price_change_pct > 3  # تغییر قیمت بیش از 3%

# High-Low range
hl_ratio > typical_hl * 2  # 2 برابر معمول
```

**روش Calibration:**
```python
# Test thresholds
vol_thresholds = [2.5, 3.0, 3.5, 4.0]
price_thresholds = [2.0, 2.5, 3.0, 3.5, 4.0]
hl_multipliers = [1.5, 2.0, 2.5, 3.0]

# Analyze historical anomalies
anomalies = detect_historical_anomalies()

for anomaly in anomalies:
    # آیا واقعاً یک crash بود؟
    # آیا circuit breaker باید trigger می‌شد؟
    # آیا false positive بود؟
```

---

### 3.5 🔬 ATR Period

**مکان:** مختلف (ATR calculation ها)

**مقدار فعلی:** `14` (استاندارد)

**روش Calibration:**
```python
# Test ranges
atr_periods = [10, 12, 14, 16, 18, 20]

for period in atr_periods:
    # تأثیر بر SL/TP calculations
    # تأثیر بر volatility detection
    # تأثیر بر anomaly detection

# Shorter period → more reactive
# Longer period → smoother, less noise
```

---

## 4️⃣ پارامترهایی که نباید تغییر کنند

این پارامترها **اصول منطق** سیستم هستند و تغییر آنها می‌تواند سیستم را خراب کند.

### ❌ نباید تغییر کنند:

1. **5-candle lookback** برای الگوها و divergence
   - این یک اصل منطقی است که الگوها تا 5 کندل قبل معتبرند

2. **13-multiplier formula** در final scoring
   - این فرمول اصل سیستم است

3. **Correlation calculation method** (np.corrcoef)
   - استاندارد آماری

4. **Timeframe list** (`['5m', '15m', '1h', '4h']`)
   - تغییر این لیست نیاز به تغییرات گسترده دارد

5. **منطق MACD Market Types** (A, B, C, D, X)
   - الگوریتم پایه

6. **Circuit breaker reset period** (24 hours)
   - استاندارد روزانه

---

## 5️⃣ روش‌های Calibration

### 5.1 Grid Search

**برای:** پارامترهایی با فضای جستجوی کوچک

```python
from itertools import product

# Define parameter ranges
param_grid = {
    'slope_5m': [0.12, 0.15, 0.18],
    'slope_1h': [0.08, 0.10, 0.12],
    'direction_margin': [1.2, 1.3, 1.4],
    'min_score': [170, 180, 190]
}

# Generate all combinations
combinations = list(product(*param_grid.values()))

# Test each combination
best_params = None
best_sharpe = -999

for combo in combinations:
    params = dict(zip(param_grid.keys(), combo))

    # Run backtest
    results = backtest(params)

    # Evaluate
    if results['sharpe'] > best_sharpe:
        best_sharpe = results['sharpe']
        best_params = params

print(f"Best params: {best_params}")
print(f"Best Sharpe: {best_sharpe}")
```

**⚠️ خطر:** Combinatorial explosion - تعداد combinations خیلی زیاد می‌شود.

---

### 5.2 Random Search

**برای:** پارامترهایی با فضای جستجوی بزرگ

```python
import random

# Define parameter ranges
param_ranges = {
    'slope_5m': (0.10, 0.20),
    'slope_15m': (0.08, 0.16),
    'slope_1h': (0.06, 0.14),
    'slope_4h': (0.05, 0.12),
    'direction_margin': (1.1, 1.6),
    'min_score': (140, 220),
    # ... more params
}

# Random sampling
n_iterations = 500
best_params = None
best_metric = -999

for i in range(n_iterations):
    # Sample random parameters
    params = {
        name: random.uniform(*range_)
        for name, range_ in param_ranges.items()
    }

    # Backtest
    results = backtest(params)

    # Track best
    if results['sharpe'] > best_metric:
        best_metric = results['sharpe']
        best_params = params

    if i % 50 == 0:
        print(f"Iteration {i}/{n_iterations}, Best Sharpe: {best_metric:.3f}")

print(f"Best params found: {best_params}")
```

**مزیت:** کارآمدتر از grid search برای فضای بزرگ.

---

### 5.3 Bayesian Optimization

**برای:** پارامترهای پیچیده (recommended)

```python
from skopt import gp_minimize
from skopt.space import Real, Integer

# Define search space
space = [
    Real(0.10, 0.20, name='slope_5m'),
    Real(0.08, 0.16, name='slope_15m'),
    Real(0.06, 0.14, name='slope_1h'),
    Real(0.05, 0.12, name='slope_4h'),
    Real(1.1, 1.6, name='direction_margin'),
    Integer(140, 220, name='min_score'),
]

# Objective function
def objective(params):
    param_dict = {
        'slope_5m': params[0],
        'slope_15m': params[1],
        'slope_1h': params[2],
        'slope_4h': params[3],
        'direction_margin': params[4],
        'min_score': params[5],
    }

    # Run backtest
    results = backtest(param_dict)

    # Return negative Sharpe (minimize)
    return -results['sharpe']

# Optimize
result = gp_minimize(
    objective,
    space,
    n_calls=100,  # number of evaluations
    random_state=42,
    verbose=True
)

print(f"Best params: {result.x}")
print(f"Best Sharpe: {-result.fun}")
```

**مزیت:** Intelligent search - یاد می‌گیرد کدام نواحی بهتر هستند.

---

### 5.4 Genetic Algorithm

**برای:** Optimization پیچیده با constraint ها

```python
from deap import base, creator, tools, algorithms
import random

# Define fitness and individual
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

# Individual: [slope_5m, slope_15m, slope_1h, slope_4h, margin, min_score]
def create_individual():
    return [
        random.uniform(0.10, 0.20),  # slope_5m
        random.uniform(0.08, 0.16),  # slope_15m
        random.uniform(0.06, 0.14),  # slope_1h
        random.uniform(0.05, 0.12),  # slope_4h
        random.uniform(1.1, 1.6),    # direction_margin
        random.randint(140, 220)     # min_score
    ]

# Evaluation function
def evaluate(individual):
    params = {
        'slope_5m': individual[0],
        'slope_15m': individual[1],
        'slope_1h': individual[2],
        'slope_4h': individual[3],
        'direction_margin': individual[4],
        'min_score': individual[5],
    }

    results = backtest(params)
    return (results['sharpe'],)  # tuple

# Setup genetic algorithm
toolbox = base.Toolbox()
toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("evaluate", evaluate)
toolbox.register("mate", tools.cxBlend, alpha=0.5)
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)

# Run
population = toolbox.population(n=50)
algorithms.eaSimple(population, toolbox, cxpb=0.7, mutpb=0.2, ngen=40, verbose=True)

# Best individual
best = tools.selBest(population, k=1)[0]
print(f"Best params: {best}")
print(f"Best Sharpe: {best.fitness.values[0]}")
```

---

## 6️⃣ Backtest Strategy

### 6.1 Data Split

```python
# CRITICAL: جلوگیری از over-fitting

# 1. Training Set (60%)
train_start = '2020-01-01'
train_end = '2022-12-31'

# 2. Validation Set (20%)
val_start = '2023-01-01'
val_end = '2023-08-31'

# 3. Test Set (20%)
test_start = '2023-09-01'
test_end = '2024-06-30'

# Process:
# 1. Optimize on Training Set
# 2. Validate on Validation Set
# 3. Final evaluation on Test Set (NEVER optimize on this!)
```

**⚠️ هشدار مهم:**
- **NEVER** optimize on test set
- Test set فقط برای ارزیابی نهایی است
- اگر optimization روی test set انجام دهید = over-fitting

---

### 6.2 Cross-Validation

```python
# Time Series Cross-Validation
from sklearn.model_selection import TimeSeriesSplit

# 5-fold time series split
tscv = TimeSeriesSplit(n_splits=5)

results = []

for train_index, val_index in tscv.split(data):
    train_data = data.iloc[train_index]
    val_data = data.iloc[val_index]

    # Optimize on train
    best_params = optimize(train_data)

    # Evaluate on validation
    metrics = backtest(val_data, best_params)
    results.append(metrics)

# Average metrics across folds
avg_sharpe = np.mean([r['sharpe'] for r in results])
std_sharpe = np.std([r['sharpe'] for r in results])

print(f"Average Sharpe: {avg_sharpe:.3f} ± {std_sharpe:.3f}")
```

---

### 6.3 Market Regime Separation

```python
# بهتر است optimization را در regime های مختلف انجام دهید

# Detect market regimes
regimes = detect_market_regimes(data)

# Separate data
trending_data = data[regimes == 'trending']
ranging_data = data[regimes == 'ranging']
volatile_data = data[regimes == 'volatile']

# Optimize separately
trending_params = optimize(trending_data)
ranging_params = optimize(ranging_data)
volatile_params = optimize(volatile_data)

# Create regime-adaptive config
config_adaptive = {
    'trending': trending_params,
    'ranging': ranging_params,
    'volatile': volatile_params
}
```

---

## 7️⃣ Walk-Forward Analysis

**بهترین روش برای جلوگیری از over-fitting**

```python
# Walk-Forward Optimization
# مثال: Optimize هر 3 ماه، Test 1 ماه

optimization_window = 90  # days
test_window = 30  # days

all_results = []
param_history = []

start_date = '2020-01-01'
end_date = '2024-06-30'

current_date = start_date

while current_date < end_date:
    # 1. Optimization period
    opt_start = current_date
    opt_end = opt_start + timedelta(days=optimization_window)
    opt_data = data[opt_start:opt_end]

    # Optimize parameters
    best_params = optimize(opt_data)
    param_history.append({
        'date': current_date,
        'params': best_params
    })

    # 2. Test period (out-of-sample)
    test_start = opt_end
    test_end = test_start + timedelta(days=test_window)
    test_data = data[test_start:test_end]

    # Test with optimized params
    results = backtest(test_data, best_params)
    all_results.append(results)

    # Move forward
    current_date = test_end

# Aggregate results
total_return = np.sum([r['return'] for r in all_results])
avg_sharpe = np.mean([r['sharpe'] for r in all_results])

print(f"Walk-Forward Results:")
print(f"Total Return: {total_return:.2f}%")
print(f"Average Sharpe: {avg_sharpe:.3f}")

# Visualize parameter stability
plot_parameter_evolution(param_history)
```

**نکته مهم:** اگر پارامترها خیلی زیاد تغییر می‌کنند = over-fitting

---

## 8️⃣ Optimization Tips

### 8.1 ✅ Do's

1. **همیشه از validation set استفاده کنید**
   ```python
   # GOOD
   params = optimize(train_data)
   results = evaluate(val_data, params)
   ```

2. **Metric های متنوع را بررسی کنید**
   ```python
   metrics = {
       'sharpe_ratio': ...,
       'profit_factor': ...,
       'max_drawdown': ...,
       'win_rate': ...,
       'avg_trade': ...,
       'recovery_factor': ...,
   }
   ```

3. **در market regime های مختلف تست کنید**
   ```python
   # Bull market
   # Bear market
   # Ranging market
   # High volatility
   # Low volatility
   ```

4. **پایداری پارامترها را بررسی کنید**
   ```python
   # اگر تغییر کوچک در پارامتر تأثیر بزرگ دارد = over-fitting

   # Test sensitivity
   for delta in [-10%, -5%, 0%, +5%, +10%]:
       param_perturbed = base_param * (1 + delta)
       results = backtest(param_perturbed)
   ```

5. **از Occam's Razor استفاده کنید**
   ```
   "ساده‌ترین راه حل معمولاً بهترین است"

   # بین دو مدل با عملکرد مشابه، ساده‌تر را انتخاب کنید
   ```

---

### 8.2 ❌ Don'ts

1. **روی test set optimize نکنید**
   ```python
   # BAD - NEVER DO THIS
   params = optimize(test_data)
   ```

2. **تعداد زیاد parameter را همزمان optimize نکنید**
   ```python
   # BAD - Too many parameters
   optimize_simultaneously([
       'slope_5m', 'slope_15m', 'slope_1h', 'slope_4h',
       'momentum_5m', 'momentum_15m', 'momentum_1h', 'momentum_4h',
       'pattern_scores_5m', 'pattern_scores_15m', ...
       # 50+ parameters!
   ])

   # GOOD - Optimize in stages
   # Stage 1: Slope thresholds
   # Stage 2: Momentum thresholds
   # Stage 3: Pattern scores
   ```

3. **فقط روی یک نماد optimize نکنید**
   ```python
   # BAD - Over-fit to BTC
   params = optimize(btc_data)

   # GOOD - Optimize on multiple symbols
   params = optimize([btc_data, eth_data, bnb_data, ...])
   ```

4. **فقط به Sharpe نگاه نکنید**
   ```python
   # BAD - Single metric
   best = max(results, key=lambda x: x['sharpe'])

   # GOOD - Multi-objective
   best = find_pareto_optimal(results, metrics=['sharpe', 'max_dd', 'win_rate'])
   ```

5. **فراموش نکنید که شرایط بازار تغییر می‌کند**
   ```python
   # پارامترهای 2020 ممکن است در 2024 کار نکنند
   # نیاز به re-optimization دوره‌ای دارید
   ```

---

## 9️⃣ Practical Example - Complete Workflow

```python
#!/usr/bin/env python3
"""
Complete Backtest Calibration Workflow
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from skopt import gp_minimize
from skopt.space import Real, Integer
import yaml

# ============================================================
# 1. Load Data
# ============================================================

def load_data(symbols, start, end, timeframe='1h'):
    """Load historical OHLCV data"""
    data = {}
    for symbol in symbols:
        df = fetch_ohlcv(symbol, timeframe, start, end)
        data[symbol] = df
    return data

# ============================================================
# 2. Split Data
# ============================================================

def split_data(data, train_ratio=0.6, val_ratio=0.2):
    """Split into train/val/test sets"""
    total_len = len(data)
    train_end = int(total_len * train_ratio)
    val_end = int(total_len * (train_ratio + val_ratio))

    return {
        'train': data[:train_end],
        'val': data[train_end:val_end],
        'test': data[val_end:]
    }

# ============================================================
# 3. Define Optimization Space
# ============================================================

# پارامترهای Priority 1
PARAM_SPACE = [
    # Slope thresholds
    Real(0.12, 0.20, name='slope_5m'),
    Real(0.10, 0.16, name='slope_15m'),
    Real(0.08, 0.14, name='slope_1h'),
    Real(0.05, 0.12, name='slope_4h'),

    # Direction margin
    Real(1.1, 1.6, name='direction_margin'),

    # Minimum signal score
    Integer(150, 210, name='min_signal_score'),

    # Timeframe weights
    Real(0.6, 0.9, name='weight_5m'),
    Real(0.8, 1.0, name='weight_15m'),
    Real(1.0, 1.3, name='weight_4h'),

    # Risk parameters
    Real(1.5, 3.0, name='default_sl_percent'),
    Real(1.5, 3.0, name='preferred_rr_ratio'),
    Real(1.5, 2.5, name='atr_multiplier'),
]

# ============================================================
# 4. Backtest Function
# ============================================================

def run_backtest(data, params):
    """Run backtest with given parameters"""

    # Create config from params
    config = {
        'signal_generation': {
            'minimum_signal_score': params['min_signal_score'],
            'timeframe_weights': {
                '5m': params['weight_5m'],
                '15m': params['weight_15m'],
                '1h': 1.0,
                '4h': params['weight_4h']
            },
            'trend_detection': {
                'slope_thresholds': {
                    '5m': params['slope_5m'],
                    '15m': params['slope_15m'],
                    '1h': params['slope_1h'],
                    '4h': params['slope_4h']
                }
            }
        },
        'multi_timeframe': {
            'direction_margin': params['direction_margin']
        },
        'risk': {
            'default_stop_loss_percent': params['default_sl_percent'],
            'preferred_risk_reward_ratio': params['preferred_rr_ratio'],
            'atr_trailing_multiplier': params['atr_multiplier']
        }
    }

    # Initialize backtest engine
    from backtest.backtest_engine_v2 import BacktestEngineV2
    engine = BacktestEngineV2(config)

    # Run backtest
    results = engine.run(data)

    return results

# ============================================================
# 5. Objective Function
# ============================================================

def objective(params_list):
    """Objective function to minimize (negative Sharpe)"""

    # Convert params list to dict
    params = {
        'slope_5m': params_list[0],
        'slope_15m': params_list[1],
        'slope_1h': params_list[2],
        'slope_4h': params_list[3],
        'direction_margin': params_list[4],
        'min_signal_score': params_list[5],
        'weight_5m': params_list[6],
        'weight_15m': params_list[7],
        'weight_4h': params_list[8],
        'default_sl_percent': params_list[9],
        'preferred_rr_ratio': params_list[10],
        'atr_multiplier': params_list[11],
    }

    # Run backtest on training data
    results = run_backtest(train_data, params)

    # Calculate composite score
    sharpe = results['sharpe_ratio']
    max_dd = results['max_drawdown']
    profit_factor = results['profit_factor']

    # Multi-objective: Maximize Sharpe, Minimize DD, Maximize PF
    score = sharpe - (max_dd / 10) + (profit_factor / 2)

    # Return negative (for minimization)
    return -score

# ============================================================
# 6. Main Optimization Loop
# ============================================================

def main():
    print("=" * 60)
    print("BACKTEST CALIBRATION - Priority 1 Parameters")
    print("=" * 60)

    # Load data
    print("\n1. Loading data...")
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    data = load_data(symbols, start='2020-01-01', end='2024-06-30')

    # Split data
    print("2. Splitting data...")
    global train_data, val_data, test_data
    splits = split_data(data)
    train_data = splits['train']
    val_data = splits['val']
    test_data = splits['test']

    print(f"   Train: {len(train_data)} days")
    print(f"   Val:   {len(val_data)} days")
    print(f"   Test:  {len(test_data)} days")

    # Optimize on training data
    print("\n3. Optimizing parameters...")
    print("   (This may take several hours...)")

    result = gp_minimize(
        objective,
        PARAM_SPACE,
        n_calls=100,  # 100 iterations
        random_state=42,
        verbose=True,
        n_jobs=-1  # Use all CPU cores
    )

    # Extract best parameters
    best_params = {
        'slope_5m': result.x[0],
        'slope_15m': result.x[1],
        'slope_1h': result.x[2],
        'slope_4h': result.x[3],
        'direction_margin': result.x[4],
        'min_signal_score': result.x[5],
        'weight_5m': result.x[6],
        'weight_15m': result.x[7],
        'weight_4h': result.x[8],
        'default_sl_percent': result.x[9],
        'preferred_rr_ratio': result.x[10],
        'atr_multiplier': result.x[11],
    }

    print("\n4. Best parameters found:")
    for key, value in best_params.items():
        print(f"   {key}: {value:.4f}")

    # Validate on validation set
    print("\n5. Validating on validation set...")
    val_results = run_backtest(val_data, best_params)

    print(f"   Sharpe Ratio: {val_results['sharpe_ratio']:.3f}")
    print(f"   Max Drawdown: {val_results['max_drawdown']:.2f}%")
    print(f"   Profit Factor: {val_results['profit_factor']:.3f}")
    print(f"   Win Rate: {val_results['win_rate']:.2f}%")

    # Final test on test set
    print("\n6. Final test on test set...")
    test_results = run_backtest(test_data, best_params)

    print(f"   Sharpe Ratio: {test_results['sharpe_ratio']:.3f}")
    print(f"   Max Drawdown: {test_results['max_drawdown']:.2f}%")
    print(f"   Profit Factor: {test_results['profit_factor']:.3f}")
    print(f"   Win Rate: {test_results['win_rate']:.2f}%")

    # Save optimized config
    print("\n7. Saving optimized config...")
    save_config(best_params, 'config_optimized.yaml')

    print("\n✅ Calibration complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
```

---

## 🔟 Summary & Priority Roadmap

### Phase 1: Quick Wins (Week 1-2)

**Focus:** پارامترهای حیاتی با تأثیر بالا

1. ✅ **Direction Margin** - یک پارامتر، تأثیر زیاد
2. ✅ **Minimum Signal Score** - یک پارامتر، تأثیر زیاد
3. ✅ **Risk/Reward Ratios** - 3 پارامتر، تأثیر مستقیم بر سود

**زمان تخمینی:** 2-5 روز (بسته به سرعت backtest)

---

### Phase 2: Core Optimization (Week 3-4)

**Focus:** Trend & Momentum thresholds

4. ✅ **Per-TF Slope Thresholds** - 4 پارامتر
5. ✅ **Timeframe Weights** - 4 پارامتر
6. ✅ **Momentum Thresholds** - در صورت نیاز

**زمان تخمینی:** 1-2 هفته

---

### Phase 3: Fine-Tuning (Week 5-6)

**Focus:** Pattern scores & advanced

7. ✅ **Pattern Scores per TF**
8. ✅ **MACD Type Strengths**
9. ✅ **Phase Multipliers**
10. ✅ **Confidence Thresholds**

**زمان تخمینی:** 1-2 هفته

---

### Phase 4: Protection Systems (Week 7-8)

**Focus:** Circuit breaker & correlation

11. ✅ **Circuit Breaker Thresholds**
12. ✅ **Correlation Thresholds**

**زمان تخمینی:** 1 هفته

---

### Phase 5: Validation (Week 9-10)

13. ✅ **Walk-Forward Analysis**
14. ✅ **Cross-Validation**
15. ✅ **Regime-based Testing**

**زمان تخمینی:** 2 هفته

---

## ⚠️ Final Warnings

1. **Over-fitting is the enemy**
   - همیشه validation set جداگانه داشته باشید
   - هرگز روی test set optimize نکنید
   - پارامترها باید در regime های مختلف کار کنند

2. **Start simple**
   - ابتدا پارامترهای Priority 1 را calibrate کنید
   - بعد به Priority 2 و 3 بروید
   - همه چیز را همزمان optimize نکنید

3. **Market changes**
   - پارامترهای بهینه امروز ممکن است فردا بهینه نباشند
   - نیاز به re-calibration دوره‌ای دارید (مثلاً هر 3-6 ماه)

4. **Domain knowledge matters**
   - از backtest استفاده کنید اما منطق را فراموش نکنید
   - اگر پارامتری منطقی به نظر نمی‌رسد، احتمالاً over-fit است

5. **Document everything**
   - همه optimization ها را document کنید
   - دلایل تغییرات را یادداشت کنید
   - نتایج را ذخیره کنید

---

**📅 Document Version:** 1.0
**🗓️ Last Updated:** 2025-11-21
**✍️ Author:** Claude (AI Analysis)

**Good luck with your calibration! 🚀📈**
