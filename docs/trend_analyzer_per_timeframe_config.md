# TrendAnalyzer Per-Timeframe Configuration

## Overview

The `TrendAnalyzer` now supports **per-timeframe threshold configuration**, allowing you to fine-tune trend detection sensitivity for different timeframes (5m, 15m, 1h, 4h).

## Key Improvements

### 1. Configurable Slope Thresholds

Each timeframe can have its own minimum slope threshold to filter out noise:

| Timeframe | Threshold | Rationale |
|-----------|-----------|-----------|
| **5m** | 0.0005 (0.05%) | High noise → Higher threshold |
| **15m** | 0.0003 (0.03%) | Moderate noise → Moderate threshold |
| **1h** | 0.0002 (0.02%) | Lower noise → Lower threshold |
| **4h** | 0.0001 (0.01%) | Minimal noise → Lowest threshold |

### 2. Configurable Lookback Period

You can adjust how many candles to look back when calculating EMA slopes.

---

## Configuration in `config.yaml`

### Location

```yaml
signal_generation_v2:
  analyzers:
    trend_analyzer:
      # ... (section starts at line 132)
```

### Structure

```yaml
trend_analyzer:
  enabled: true
  weight: 0.3

  # Global defaults (used when per-TF is disabled or TF not found)
  min_slope_threshold: 0.0002  # 0.02%
  slope_lookback: 5

  # Per-timeframe configuration
  per_timeframe:
    enabled: true  # ⚠️ Must be true to use per-TF thresholds

    5m:
      min_slope: 0.0005      # 0.05% minimum slope
      slope_lookback: 5      # Look back 5 candles

    15m:
      min_slope: 0.0003      # 0.03%
      slope_lookback: 5

    1h:
      min_slope: 0.0002      # 0.02%
      slope_lookback: 5

    4h:
      min_slope: 0.0001      # 0.01%
      slope_lookback: 5
```

---

## How It Works

### 1. Slope Calculation Method

**Old System (Absolute Difference):**
```python
slope = ema20_current - ema20_past  # e.g., 50000 - 49500 = 500
```

**New System (Percentage Change):**
```python
slope = (ema20_current - ema20_past) / ema20_past  # e.g., 500/49500 = 0.0101 (1.01%)
```

✅ **Why percentage is better:**
- Scale-independent (works for BTC, ETH, ADA equally)
- Comparable across assets
- Industry standard (ROC indicator)

### 2. Threshold Application

```python
# In TrendAnalyzer._detect_trend():
min_slope_threshold = self.get_threshold('min_slope', self.min_slope_threshold, timeframe)

# For 5m timeframe:
# - Reads: config.yaml → trend_analyzer → per_timeframe → 5m → min_slope
# - Returns: 0.0005
# - Fallback: If not found, returns global min_slope_threshold (0.0002)

# Trend detection:
if ema20_slope > min_slope_threshold and ema50_slope > min_slope_threshold:
    trend = 'bullish'
    strength = 3
```

### 3. Fallback Chain

```
1. Per-TF Config (if enabled and TF exists)
   ↓
2. Global Config (analyzer-level)
   ↓
3. Default Value (hardcoded in code)
```

---

## Tuning Guide

### When to Adjust Thresholds

**Increase threshold if:**
- Too many false signals (noise)
- Trend detected in ranging market
- Short-lived trends

**Decrease threshold if:**
- Missing real trends
- Late entry (trend already mature)
- Not enough signals

### Recommended Values by Market Condition

| Market | 5m | 15m | 1h | 4h |
|--------|-----|-----|-----|-----|
| **High Volatility** | 0.0008 | 0.0005 | 0.0003 | 0.00015 |
| **Normal** (default) | 0.0005 | 0.0003 | 0.0002 | 0.0001 |
| **Low Volatility** | 0.0003 | 0.0002 | 0.0001 | 0.00005 |

### Testing Your Configuration

```python
# Run backtest to see impact:
python backtest.py --config config.yaml --start-date 2024-01-01 --end-date 2024-12-31

# Check metrics:
# - Number of signals generated
# - Win rate
# - False positive rate
# - Trend detection accuracy
```

---

## Code Changes Summary

### Files Modified

1. **`config.yaml`** (lines 131-156)
   - Changed structure from `trend_strength_per_timeframe` to `per_timeframe`
   - Updated threshold values based on analysis
   - Added comments explaining each threshold

2. **`signal_generation/analyzers/trend_analyzer.py`**
   - Line 71: Read from `trend_analyzer` key (backward compatible)
   - Line 127: Pass `timeframe` to `_calculate_ema_slopes()`
   - Line 198: Accept `timeframe` parameter in `_calculate_ema_slopes()`
   - Line 210: Get per-TF `slope_lookback`
   - Lines 305, 399: Use `'min_slope'` instead of `'trend_min_slope'`

---

## Migration from Old System

### If You Have Custom Thresholds

**Old config structure:**
```yaml
trend_strength_per_timeframe:
  enabled: true
  5m:
    min_slope: 0.0002
```

**New config structure:**
```yaml
per_timeframe:
  enabled: true
  5m:
    min_slope: 0.0005  # ⚠️ Updated value!
```

### Breaking Changes

⚠️ **Threshold values have changed:**
- 5m: 0.0002 → 0.0005 (2.5x stricter)
- 15m: 0.00015 → 0.0003 (2x stricter)
- 1h: 0.0001 → 0.0002 (2x stricter)
- 4h: 0.00005 → 0.0001 (2x stricter)

**Impact:**
- Fewer but higher quality signals
- Better noise filtering
- May need to re-optimize your strategy

---

## Validation

### Check If Configuration Is Loaded Correctly

Enable debug logging in `config.yaml`:
```yaml
logging:
  level: DEBUG
```

Look for log messages:
```
[DEBUG] TrendAnalyzer: Using per-TF threshold min_slope=0.0005 for 5m
```

### Test Cases

**Test 1: Per-TF threshold is used**
```python
# Expected: Different thresholds for different timeframes
# 5m should use 0.0005
# 4h should use 0.0001
```

**Test 2: Fallback to global default**
```python
# If per_timeframe.enabled = false
# Should use global min_slope_threshold = 0.0002
```

**Test 3: Slope calculation is percentage-based**
```python
# BTC (50000 → 50500) and ETH (3000 → 3030)
# Should both get slope ≈ 0.01 (1%)
```

---

## FAQ

### Q: Why did threshold values increase?

**A:** The new system uses **percentage change** instead of **absolute difference**. The old system was biased toward high-priced assets (BTC had artificially higher slopes than ETH). The new thresholds are calibrated to properly filter noise while maintaining sensitivity.

### Q: Can I use old threshold values?

**A:** No. The calculation method changed from absolute to percentage. You must use new percentage-based thresholds (around 0.01% - 0.05%).

### Q: How do I disable per-timeframe config?

**A:** Set `per_timeframe.enabled: false` in config.yaml. The analyzer will use global `min_slope_threshold`.

### Q: Can I add other timeframes (e.g., 30m)?

**A:** Yes! Just add a new entry under `per_timeframe`:
```yaml
per_timeframe:
  enabled: true
  30m:
    min_slope: 0.00025
    slope_lookback: 5
```

---

## See Also

- **Analysis Document:** `analysis_slope_comparison.md` - Technical justification for percentage-based slopes
- **Old System Doc:** `Old_bot/Old_signal.md` - Original trend detection logic
- **New System Doc:** `docs/New_method_signal.md` - Complete signal generation flow

---

**Last Updated:** 2025-11-21
**Version:** 2.0
