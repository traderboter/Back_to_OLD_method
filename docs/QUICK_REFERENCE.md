# Quick Reference Guide

**Fast lookup for common tasks in NEW SYSTEM**

---

## 🚀 Quick Start (30 seconds)

```python
from signal_generation.orchestrator import SignalOrchestrator
from signal_generation.shared.indicator_calculator import IndicatorCalculator

# Setup
config = load_config('config.yaml')
indicator_calc = IndicatorCalculator(config)
orchestrator = SignalOrchestrator(config, fetcher, indicator_calc)

# Generate signal
signal = await orchestrator.generate_signal_for_symbol('BTCUSDT', '1h')

# Use signal
if signal:
    print(f"{signal.direction} @ {signal.entry_price}")
    print(f"SL: {signal.stop_loss} | TP: {signal.take_profit}")
```

---

## 📊 Core Components

### SignalOrchestrator
Main coordinator for signal generation.

```python
orchestrator = SignalOrchestrator(
    config=config,
    market_data_fetcher=fetcher,
    indicator_calculator=indicator_calc,
    trade_manager_callback=callback  # Optional
)

# Single TF
signal = await orchestrator.generate_signal_for_symbol(symbol, timeframe)

# Multi-TF
signal = await orchestrator.analyze_symbol(symbol, timeframes_data)
```

### RiskRewardCalculator
5-method priority for SL/TP.

```python
from signal_generation.risk_calculator import RiskRewardCalculator

calculator = RiskRewardCalculator(config)
result = calculator.calculate_sl_tp(
    direction='LONG',
    entry_price=50000.0,
    context=analysis_context,
    adapted_config=risk_config
)

# Returns: {stop_loss, take_profit, risk_reward_ratio, sl_method}
```

**Priority:** Harmonic → Channel → S/R → ATR → Percentage

### SignalScorer
13-multiplier scoring system.

```python
from signal_generation.signal_scorer import SignalScorer

scorer = SignalScorer(config)
score = scorer.calculate_score(context, 'LONG', timeframe_data)

# Access components
print(f"Base: {score.base_score}")
print(f"Final: {score.final_score}")
print(f"TF Weight: {score.timeframe_weight}")
# ... all 13 multipliers
```

**Formula:**
```
final = base × tf_weight × trend × volume × pattern × (1+confluence) ×
        symbol_perf × corr_safety × macd × structure × volatility ×
        harmonic × channel × cyclical
```

### MultiTimeframeAggregator
Aggregate signals from multiple timeframes.

```python
from signal_generation.multi_tf_aggregator import MultiTimeframeAggregator

aggregator = MultiTimeframeAggregator(config)
signal = aggregator.aggregate_timeframe_scores(symbol, timeframe_signals)
```

**Weights:** 5m(15%), 15m(20%), 1h(30%), 4h(35%)

---

## 🔧 Configuration

### Minimal Config

```yaml
indicators:
  ema_periods: [20, 50, 100, 200]
  rsi_period: 14
  atr_period: 14

risk_management:
  min_risk_reward_ratio: 1.5
  preferred_risk_reward_ratio: 2.0
  atr_trailing_multiplier: 2.0

signal_scoring:
  minimum_signal_score: 50.0
```

### Full Config Sections

```yaml
indicators:           # Technical indicators
analyzers:            # Analyzer settings
risk_management:      # SL/TP, RR ratios
signal_scoring:       # Score calculation
signal_processing:    # Multi-TF settings
orchestrator:         # Orchestrator options
```

---

## 📝 Signal Output

```python
signal = SignalInfo(
    symbol='BTCUSDT',
    timeframe='1h',
    direction='LONG',              # 'LONG' or 'SHORT'
    entry_price=50000.0,
    stop_loss=49500.0,
    take_profit=51000.0,
    risk_reward_ratio=2.0,
    score=SignalScore(...),        # 13 multipliers
    key_factors=['...'],           # Top factors
    metadata={...}                 # Additional info
)
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific suite
pytest tests/unit/signal_generation/test_risk_calculator.py -v

# With coverage
pytest tests/ --cov=signal_generation

# Watch mode
pytest-watch tests/
```

**Expected:** 73/73 tests passing ✅

---

## 🎯 Common Tasks

### Task 1: Generate Single Signal

```python
signal = await orchestrator.generate_signal_for_symbol('BTCUSDT', '1h')
if signal and signal.score.final_score > 70:
    # Trade signal
    pass
```

### Task 2: Generate Multi-TF Signal

```python
timeframes_data = {
    '5m': df_5m,
    '15m': df_15m,
    '1h': df_1h,
    '4h': df_4h
}
signal = await orchestrator.analyze_symbol('BTCUSDT', timeframes_data)
```

### Task 3: Get Score Breakdown

```python
score = signal.score
print(f"Base: {score.base_score}")
for attr in ['timeframe_weight', 'trend_alignment', 'volume_confirmation']:
    print(f"{attr}: {getattr(score, attr)}")
```

### Task 4: Check SL/TP Method

```python
sl_method = signal.metadata.get('sl_method')
print(f"Used method: {sl_method}")  # e.g., "ATR x2.0"
```

### Task 5: Validate Signal Quality

```python
if signal.score.final_score > 70 and \
   signal.risk_reward_ratio > 2.0 and \
   signal.metadata.get('confidence_level') == 'HIGH':
    # High quality signal
    pass
```

---

## 🔍 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Analyzer Results

```python
context = signal.metadata.get('context')  # If available
trend = context.get_result('trend')
momentum = context.get_result('momentum')
print(f"Trend: {trend}")
print(f"Momentum: {momentum}")
```

### Trace Score Calculation

```python
score = scorer.calculate_score(context, 'LONG')
print(f"Base: {score.base_score}")
print(f"TF Weight: {score.timeframe_weight}")
# ... check each multiplier
```

### Check SL/TP Methods Tried

```python
# Enable debug logging to see which methods were tried
import logging
logging.getLogger('signal_generation.risk_calculator').setLevel(logging.DEBUG)

result = calculator.calculate_sl_tp(...)
# Logs will show: "Trying Harmonic...", "Trying Channel...", etc.
```

---

## 📊 Performance Tips

### 1. Use Caching

```yaml
orchestrator:
  cache_enabled: true
  cache_ttl_seconds: 60
```

### 2. Batch Processing

```python
signals = await asyncio.gather(*[
    orchestrator.generate_signal_for_symbol(symbol, tf)
    for symbol in symbols
])
```

### 3. Reduce Timeframes

```python
# Use fewer timeframes if acceptable
timeframes = ['15m', '1h', '4h']  # Skip 5m
```

### 4. Skip Validation (Testing Only)

```python
orchestrator = SignalOrchestrator(
    config, fetcher, indicator_calc,
    skip_validation=True  # Faster, testing only
)
```

---

## ⚠️ Common Pitfalls

### ❌ Wrong: Missing Dependencies

```python
orchestrator = SignalOrchestrator(config)  # Missing args!
```

### ✅ Correct: All Dependencies

```python
orchestrator = SignalOrchestrator(config, fetcher, indicator_calc)
```

---

### ❌ Wrong: Wrong Method Name

```python
signal = await orchestrator.analyze_single_timeframe(...)  # OLD
```

### ✅ Correct: NEW Method Name

```python
signal = await orchestrator.generate_signal_for_symbol(...)  # NEW
```

---

### ❌ Wrong: Expecting Exact Scores

```python
assert signal.score.final_score == 75.5  # May differ slightly
```

### ✅ Correct: Allow Tolerance

```python
assert abs(signal.score.final_score - 75.5) < 1.0  # 5% tolerance
```

---

## 📚 Quick Links

- **Full Guide:** [README_NEW_SYSTEM.md](../README_NEW_SYSTEM.md)
- **Migration:** [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- **Details:** [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **Examples:** [examples/basic_usage.py](../examples/basic_usage.py)

---

## 🆘 Help

### Error: "ModuleNotFoundError"

```bash
# Install dependencies
pip install -r requirements.txt
```

### Error: "Missing analyzer output"

```python
# Check analyzer ran successfully
result = context.get_result('momentum')
if result and result.get('status') == 'ok':
    # OK
else:
    # Analyzer failed or not run
```

### Error: "RR below minimum"

```python
# Lower minimum temporarily for testing
config['risk_management']['min_risk_reward_ratio'] = 1.0
```

### Signal is None

Possible reasons:
1. No clear direction (trend neutral)
2. RR below minimum
3. Score below minimum
4. Validation failed

Check orchestrator stats:
```python
stats = orchestrator.get_statistics()
print(stats['rejection_reasons'])
```

---

## 🔢 Key Numbers

| Metric | Value |
|--------|-------|
| **SL Methods** | 5 (Harmonic, Channel, S/R, ATR, %) |
| **Score Multipliers** | 13 |
| **Tests** | 73 (100% pass) |
| **Timeframes** | 4 (5m, 15m, 1h, 4h) |
| **TF Weights** | 15%, 20%, 30%, 35% |
| **Min RR** | 1.5 (default) |
| **Target RR** | 2.0 (default) |
| **Min Score** | 50.0 (default) |

---

## 🎓 Cheat Sheet

```python
# INITIALIZATION
orchestrator = SignalOrchestrator(config, fetcher, indicator_calc)

# SINGLE TF
signal = await orchestrator.generate_signal_for_symbol('BTCUSDT', '1h')

# MULTI-TF
signal = await orchestrator.analyze_symbol('BTCUSDT', timeframes_data)

# CHECK SIGNAL
if signal:
    direction = signal.direction          # 'LONG' or 'SHORT'
    entry = signal.entry_price            # Entry price
    sl = signal.stop_loss                 # Stop loss
    tp = signal.take_profit               # Take profit
    rr = signal.risk_reward_ratio         # Risk/Reward
    score = signal.score.final_score      # Final score
    method = signal.metadata['sl_method'] # SL method used

# SCORE BREAKDOWN
base = signal.score.base_score
tf_weight = signal.score.timeframe_weight
trend = signal.score.trend_alignment
# ... 13 multipliers total

# RUN TESTS
# pytest tests/ -v

# GET STATS
stats = orchestrator.get_statistics()
```

---

**Last Updated:** 2025-01-20
**Version:** 2.0
