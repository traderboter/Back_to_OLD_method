# Level 3: Per-Timeframe Analyzer Weights

**Status:** ✅ Implemented
**Date:** 2025-01-17
**Branch:** `claude/document-signal-flow-01JEHFsFPycMqHqkoZRRWSrt`

---

## 📋 Overview

Level 3 implements **per-timeframe analyzer weights**, allowing each timeframe to assign different importance to each analyzer in the final signal scoring.

### The Problem

Different timeframes have different characteristics:

```
5min timeframe:
  - High noise in trend detection
  - Momentum and volume are more reliable
  - S/R levels less meaningful (too many minor levels)

4hour timeframe:
  - Strong, clear trends
  - Momentum less volatile
  - S/R levels are major and significant
```

Using the same analyzer weights across all timeframes means:
- **5m**: Over-weighting unreliable trend signals
- **4h**: Under-weighting important trend information

### The Solution

**Per-timeframe analyzer weights** allow each timeframe to use optimized weights:

```yaml
weights_per_timeframe:
  '5m':
    trend: 0.20        # Lower (noisy)
    momentum: 0.35     # Higher (more reliable)
    volume: 0.25       # Higher (confirmation critical)

  '4h':
    trend: 0.35        # Higher (strong trends)
    momentum: 0.20     # Lower (less volatile)
    volume: 0.18       # Lower (less critical)
```

Now each timeframe weights analyzers according to their reliability!

---

## 🏗️ Architecture

### 1. SignalScorer Enhancement

**File:** `signal_generation/signal_scorer.py`

Added two key features:

#### a) Per-TF Configuration Loading
```python
def __init__(self, config: Dict[str, Any]):
    # ... existing code ...

    # Load per-timeframe analyzer weights configuration
    self.weights_per_tf_config = scoring_config.get('weights_per_timeframe', {})
    self.weights_per_tf_enabled = self.weights_per_tf_config.get('enabled', False)
```

#### b) get_weight() Method
```python
def get_weight(
    self,
    analyzer_name: str,
    default_weight: float,
    timeframe: str = None
) -> float:
    """
    Get analyzer weight with per-timeframe support.

    Fallback chain:
    1. Per-TF weight (if enabled and TF exists)
    2. Global weight
    3. Default weight
    """
    # Check if per-TF weights are enabled
    if self.weights_per_tf_enabled and timeframe:
        # Try to get timeframe-specific weight
        tf_weights = self.weights_per_tf_config.get(timeframe, {})
        if analyzer_name in tf_weights:
            logger.debug(
                f"Using per-TF weight {analyzer_name}={tf_weights[analyzer_name]} for {timeframe}"
            )
            return tf_weights[analyzer_name]

    # Fallback to global weight
    if analyzer_name in self.weights:
        return self.weights[analyzer_name]

    # Final fallback to default
    return default_weight
```

**Fallback Chain:**
```
weights_per_timeframe['5m'].trend
  ↓ (if not found)
weights.trend
  ↓ (if not found)
default_weight (0.30)
```

### 2. Modified _apply_weights()

**Before:**
```python
def _apply_weights(self, score: SignalScore) -> None:
    score.weighted_trend = score.trend_score * self.weights.get('trend', 0.30)
    # ... always uses global weights
```

**After:**
```python
def _apply_weights(self, score: SignalScore, timeframe: str = None) -> None:
    score.weighted_trend = score.trend_score * self.get_weight('trend', 0.30, timeframe)
    score.weighted_momentum = score.momentum_score * self.get_weight('momentum', 0.25, timeframe)
    score.weighted_volume = score.volume_score * self.get_weight('volume', 0.20, timeframe)
    # ... uses per-TF weights if available
```

### 3. Integration in calculate_score()

```python
def calculate_score(self, context: AnalysisContext, direction: str) -> Optional[SignalScore]:
    # ...
    # Apply weights (with per-TF support)
    self._apply_weights(score, context.timeframe)  # Pass timeframe!
    # ...
```

### 4. Data Flow

```
AnalysisContext (contains timeframe='5m')
  ↓
SignalScorer.calculate_score(context, 'LONG')
  ↓
_apply_weights(score, '5m')
  ↓
get_weight('trend', 0.30, '5m')
  ↓ (checks per-TF config)
Returns 0.20 (instead of 0.30)
  ↓
weighted_trend = trend_score * 0.20
```

---

## ⚙️ Configuration

### config.yaml Structure

```yaml
signal_processing:
  scoring:
    # Global fallback weights
    weights:
      trend: 0.30
      momentum: 0.25
      volume: 0.20
      patterns: 0.10
      support_resistance: 0.08
      volatility: 0.05
      harmonic: 0.01
      channel: 0.005
      cyclical: 0.003
      htf: 0.002

    # Timeframe multipliers (separate concept)
    timeframe_weights:
      '5m': 0.7      # -30% overall importance
      '15m': 0.85    # -15% overall importance
      '1h': 1.0      # Reference
      '4h': 1.2      # +20% overall importance

    # 🆕 Per-Timeframe Analyzer Weights
    weights_per_timeframe:
      enabled: True

      '5m':
        trend: 0.20                    # 20% (down from 30%)
        momentum: 0.35                 # 35% (up from 25%)
        volume: 0.25                   # 25% (up from 20%)
        patterns: 0.10                 # 10% (same)
        support_resistance: 0.05       # 5% (down from 8%)
        volatility: 0.05               # 5% (same)

      '15m':
        trend: 0.25                    # 25% (down from 30%)
        momentum: 0.30                 # 30% (up from 25%)
        volume: 0.23                   # 23% (up from 20%)
        patterns: 0.10                 # 10% (same)
        support_resistance: 0.07       # 7% (down from 8%)
        volatility: 0.05               # 5% (same)

      '1h':
        # Use standard weights (can omit, will fallback)
        trend: 0.30
        momentum: 0.25
        volume: 0.20
        patterns: 0.10
        support_resistance: 0.08
        volatility: 0.05
        harmonic: 0.01
        channel: 0.005
        cyclical: 0.003
        htf: 0.002

      '4h':
        trend: 0.35                    # 35% (up from 30%)
        momentum: 0.20                 # 20% (down from 25%)
        volume: 0.18                   # 18% (down from 20%)
        patterns: 0.12                 # 12% (up from 10%)
        support_resistance: 0.10       # 10% (up from 8%)
        volatility: 0.05               # 5% (same)
```

### Philosophy Behind Values

| Timeframe | Trend | Momentum | Volume | S/R | Reasoning |
|-----------|-------|----------|--------|-----|-----------|
| **5m** | 0.20 ↓ | 0.35 ↑ | 0.25 ↑ | 0.05 ↓ | High noise → trust momentum & volume more |
| **15m** | 0.25 ↓ | 0.30 ↑ | 0.23 ↑ | 0.07 ↓ | Medium noise → balanced with volume focus |
| **1h** | 0.30 = | 0.25 = | 0.20 = | 0.08 = | Standard (reference timeframe) |
| **4h** | 0.35 ↑ | 0.20 ↓ | 0.18 ↓ | 0.10 ↑ | Clear trends → trust trend & S/R more |

**Key Insights:**
- **Short TF (5m, 15m)**: Momentum + Volume are kings (0.35 + 0.25 = 60%)
- **Long TF (4h)**: Trend + S/R are kings (0.35 + 0.10 = 45%)

---

## 🔄 Backward Compatibility

**100% compatible with existing code!**

### If per-TF weights disabled:
```yaml
weights_per_timeframe:
  enabled: False  # Uses global weights
```

### If per-TF weight not defined:
```yaml
weights_per_timeframe:
  enabled: True
  '5m':
    trend: 0.20         # Defined
    # momentum: NOT defined → uses global (0.25)
```

### Fallback Examples

```python
# Scenario 1: per-TF enabled and weight exists
get_weight('trend', 0.30, '5m')
→ Returns: 0.20 (from weights_per_timeframe['5m'].trend)

# Scenario 2: per-TF enabled but weight not defined
get_weight('harmonic', 0.01, '5m')  # Not in 5m config
→ Returns: 0.01 (from weights.harmonic)

# Scenario 3: per-TF disabled
get_weight('trend', 0.30, '5m')  # enabled: False
→ Returns: 0.30 (from weights.trend)

# Scenario 4: Nothing configured
get_weight('new_analyzer', 0.15, '5m')
→ Returns: 0.15 (default value)
```

---

## 📊 Expected Results

### Scoring Impact

**Example Signal - Same conditions, different TFs:**

```
Analyzer Scores (base):
  trend_score = 80
  momentum_score = 70
  volume_score = 60
  patterns_score = 50

5m weighting:
  weighted_trend = 80 * 0.20 = 16
  weighted_momentum = 70 * 0.35 = 24.5
  weighted_volume = 60 * 0.25 = 15
  base_score = 16 + 24.5 + 15 + ... ≈ 62

4h weighting:
  weighted_trend = 80 * 0.35 = 28
  weighted_momentum = 70 * 0.20 = 14
  weighted_volume = 60 * 0.18 = 10.8
  base_score = 28 + 14 + 10.8 + ... ≈ 68
```

**Same raw scores, different final scores based on TF characteristics!**

### Signal Quality Improvements

**Before Level 3:**
```
5m:  High false positives from noisy trends
4h:  Missing signals from underweighted trends
```

**After Level 3:**
```
5m:  Reduced false positives (trend weight 0.20 instead of 0.30)
4h:  More signals caught (trend weight 0.35 instead of 0.30)
```

**Expected Improvements:**
- ✅ Better signal quality in 5m (less trend noise)
- ✅ Better signal quality in 4h (more trend emphasis)
- ✅ More balanced scoring across all TFs
- ✅ Each TF uses its "strengths"

---

## 🧪 Testing

### Manual Testing

```bash
# 1. Run signal generation with debug logging
python -m signal_generation.main --pair BTC-USDT --debug

# 2. Check logs for per-TF weight usage
# Should see:
# DEBUG - Using per-TF weight trend=0.20 for 5m
# DEBUG - Using per-TF weight momentum=0.35 for 5m
```

### Verification Checklist

- [ ] Timeframe is passed from context to _apply_weights()
- [ ] get_weight() uses per-TF config when enabled
- [ ] Fallback chain works correctly
- [ ] Weighted scores use correct weights for each TF
- [ ] Backward compatibility: works with `enabled: False`
- [ ] Backward compatibility: works without per-TF config

---

## 📝 Usage Example

### Code Example

```python
# This happens automatically in the system:

# 1. Context contains timeframe
context = AnalysisContext(
    symbol='BTC-USDT',
    timeframe='5m',
    df=price_data
)

# 2. Analyzers run and populate results
# trend_score = 80, momentum_score = 70, volume_score = 60

# 3. Scorer applies weights
scorer = SignalScorer(config)
score = scorer.calculate_score(context, 'LONG')

# 4. Weights are per-TF:
# trend: 80 * 0.20 = 16.0    (5m weight)
# momentum: 70 * 0.35 = 24.5 (5m weight)
# volume: 60 * 0.25 = 15.0   (5m weight)

# If same signal on 4h:
# trend: 80 * 0.35 = 28.0    (4h weight - higher!)
# momentum: 70 * 0.20 = 14.0 (4h weight - lower!)
# volume: 60 * 0.18 = 10.8   (4h weight - lower!)
```

### Log Output

```
DEBUG - Using per-TF weight trend=0.20 for 5m
DEBUG - Using per-TF weight momentum=0.35 for 5m
DEBUG - Using per-TF weight volume=0.25 for 5m
DEBUG - Using per-TF weight patterns=0.10 for 5m
DEBUG - Using per-TF weight support_resistance=0.05 for 5m
INFO - Signal score for BTC-USDT 5m: 62.5 (before TF multiplier)
```

---

## 🎓 Weight Selection Guidelines

### How to Choose Weights

1. **Identify Timeframe Characteristics**
   ```
   5m:  High noise, quick moves
   4h:  Strong trends, major levels
   ```

2. **Assess Analyzer Reliability**
   ```
   5m trend:  Unreliable (noise) → Lower weight (0.20)
   4h trend:  Very reliable → Higher weight (0.35)
   ```

3. **Ensure Sum = 1.0**
   ```
   Must always sum to 1.0 for consistency
   ```

4. **Test with Backtesting**
   ```bash
   cd New_backtesting
   python optimize_signal_parameters_multitf.py --pair BTC-USDT
   ```

### Common Patterns

**Short Timeframes (≤15m):**
- ↓ Trend weight (noise)
- ↑ Momentum weight (more reliable)
- ↑ Volume weight (confirmation critical)
- ↓ S/R weight (too many levels)

**Long Timeframes (≥4h):**
- ↑ Trend weight (clear trends)
- ↓ Momentum weight (less volatile)
- ↓ Volume weight (less critical)
- ↑ S/R weight (major levels)
- ↑ Patterns weight (more significant)

---

## 🔗 Relationship with Other Levels

### Level 1 + Level 2 + Level 3 Combined

```
Level 1 (Indicator Parameters):
  5m: RSI(10), MACD(8,17,6)
  4h: RSI(18), MACD(16,35,12)
  ↓ Calculate indicators with TF-specific periods

Level 2 (Analyzer Thresholds):
  5m: RSI > 75 = overbought
  4h: RSI > 65 = overbought
  ↓ Analyze with TF-specific thresholds

Level 3 (Analyzer Weights):
  5m: trend=0.20, momentum=0.35
  4h: trend=0.35, momentum=0.20
  ↓ Score with TF-specific weights

RESULT: Fully optimized per-timeframe signal generation!
```

### Synergy Example

```python
# 5min signal generation (all 3 levels active):

# Level 1: Calculate RSI with period=10
rsi = calculate_rsi(df, period=10)  # 50 minutes

# Level 2: Check overbought with threshold=75
if rsi > 75:  # Stricter for 5m
    is_overbought = True

# Level 3: Weight momentum higher (0.35 vs 0.25)
momentum_score = 80
weighted_momentum = 80 * 0.35  # 28.0 (vs 20.0 with global weight)

# Final score reflects all 3 levels!
```

---

## 🐛 Known Limitations

### Not Implemented (Future Work)

1. **Dynamic Weight Adjustment**
   - Currently static per-TF values
   - Future: Auto-adjust based on market conditions

2. **ML-Based Optimization**
   - Current values are manually set
   - Future: ML to find optimal weights

3. **Market Regime Adaptation**
   - Same weights in trending vs ranging markets
   - Future: Adjust weights based on market regime

---

## 🔜 Next Steps

### Short-term:
1. ✅ Level 3 complete
2. ⏳ Testing in production
3. ⏳ Monitor signal quality per TF

### Medium-term:
1. ⏳ Add per-TF weights to remaining analyzers
2. ⏳ Optimize weights using backtesting
3. ⏳ A/B test different weight configurations

### Long-term:
1. ⏳ Dynamic weight adjustment
2. ⏳ ML-based weight optimization
3. ⏳ Market regime-aware weighting

---

## 📚 Related Documentation

- `docs/LEVEL1_INDICATOR_PARAMETERS.md` - Level 1 guide
- `docs/PER_TIMEFRAME_USAGE_GUIDE.md` - Level 2 usage guide
- `docs/PER_TIMEFRAME_RELEASE_NOTES.md` - Release notes (all levels)
- `docs/COMPLETE_PER_TIMEFRAME_DESIGN.md` - Complete 3-level design

---

## 💡 Key Insights

### Why This Matters

1. **Timeframe-Specific Reliability**: Each analyzer has different reliability in different TFs
2. **Better Signal Quality**: Weight analyzers based on their TF-specific strengths
3. **Optimal Resource Allocation**: Put scoring "power" where it's most valuable
4. **Holistic Optimization**: Combined with L1+L2, creates fully optimized per-TF system

### Design Patterns Used

1. **Strategy Pattern**: get_weight() encapsulates weight selection logic
2. **Chain of Responsibility**: Fallback chain for weight values
3. **Template Method**: _apply_weights() defines structure, get_weight() provides specifics

---

## 🎓 Examples

### Example 1: Momentum-Heavy Signal on 5m

```python
# Analyzer scores:
trend = 60        # Medium trend (noisy)
momentum = 90     # Strong momentum
volume = 80       # Good volume

# 5m weights (momentum-focused):
weighted_trend = 60 * 0.20 = 12.0
weighted_momentum = 90 * 0.35 = 31.5  # High!
weighted_volume = 80 * 0.25 = 20.0
base_score = 12.0 + 31.5 + 20.0 = 63.5

# If same scores on 4h (trend-focused):
weighted_trend = 60 * 0.35 = 21.0     # Higher!
weighted_momentum = 90 * 0.20 = 18.0  # Lower!
weighted_volume = 80 * 0.18 = 14.4
base_score = 21.0 + 18.0 + 14.4 = 53.4

# Result: 5m scores higher (63.5 vs 53.4) because
# momentum is more important in 5m!
```

### Example 2: Trend-Heavy Signal on 4h

```python
# Analyzer scores:
trend = 95        # Very strong trend
momentum = 60     # Medium momentum
volume = 65       # Medium volume

# 4h weights (trend-focused):
weighted_trend = 95 * 0.35 = 33.25   # High!
weighted_momentum = 60 * 0.20 = 12.0
weighted_volume = 65 * 0.18 = 11.7
base_score = 33.25 + 12.0 + 11.7 = 56.95

# If same scores on 5m (momentum-focused):
weighted_trend = 95 * 0.20 = 19.0    # Lower!
weighted_momentum = 60 * 0.35 = 21.0
weighted_volume = 65 * 0.25 = 16.25
base_score = 19.0 + 21.0 + 16.25 = 56.25

# Result: 4h scores slightly higher (56.95 vs 56.25) because
# trend is more important in 4h!
```

---

**Implementation Complete! ✅**

All 3 levels of per-timeframe configuration are now complete:
- ✅ Level 1: Per-TF Indicator Parameters
- ✅ Level 2: Per-TF Analyzer Thresholds
- ✅ Level 3: Per-TF Analyzer Weights
