# Comparison Report: Fast Backtest vs Original Backtest

Generated: 2025-11-21

## Executive Summary

This document compares the two backtest systems available in this project.

## Systems Overview

### Fast Backtest (`precomputed_backtest/fast_backtest.py`)

| Feature | Value |
|---------|-------|
| Data Source | Pre-computed Parquet files |
| Speed | ~3,000-3,500 candles/second |
| Dependencies | pandas, numpy, pyarrow |
| Scoring Methods | new, old, hybrid, strategy |
| Multi-TF Analysis | Simplified (1 signal timeframe) |

### Original Backtest (`backtest/backtest_engine_v2.py`)

| Feature | Value |
|---------|-------|
| Data Source | CSV files (real-time calculation) |
| Speed | ~1-5 steps/second (estimated) |
| Dependencies | talib, scipy, pandas, numpy |
| Scoring Methods | new, old, hybrid |
| Multi-TF Analysis | Full (4 timeframes with aggregation) |
| Analyzers | 11 specialized analyzers |

## Test Results

### Fast Backtest (OLD Scoring Method)
```
Date: 2025-11-21
Symbol: BTC-USDT
Candles Processed: 33,529
Duration: ~9 seconds

Results:
- Total Trades: 6
- Win Rate: 50.0%
- Total Return: 0.11%
- Profit Factor: 2.04
- Max Drawdown: 0.12%
- Final Equity: 10,010.79 USDT
```

### Original Backtest (OLD Scoring Method)
```
Status: Very slow (~31,588 steps required)
Duration: 329 days of historical data
Timeframes: 5m, 15m, 1h, 4h
Analyzers: 11 (Trend, Momentum, Volume, Pattern, SR, etc.)

Could not complete within reasonable time for this comparison.
```

## Key Differences

### 1. Signal Generation Logic

| Aspect | Fast Backtest | Original Backtest |
|--------|---------------|-------------------|
| Direction Detection | Simple indicator-based | Multi-analyzer consensus |
| Score Calculation | FastScorer (direct) | Full SignalOrchestrator |
| Timeframe Usage | Single primary TF | 4 TF aggregation |
| Pattern Detection | Pre-computed | Real-time calculation |

### 2. Trade Count Difference

The fast backtest produces significantly fewer trades (6 vs expected hundreds) because:

1. **Min Signal Score**: Fast backtest uses `min_signal_score = 200` (OLD method)
2. **Direction Determination**: Uses simplified bullish/bearish scoring (`_determine_direction_for_scorer`)
3. **Signal Frequency**: Only checks every 12 candles (1 hour intervals)

### 3. Speed Comparison

| Metric | Fast Backtest | Original Backtest |
|--------|---------------|-------------------|
| Processing Speed | ~3,500 candles/sec | ~1-5 steps/sec |
| Total Time (33K candles) | ~9 seconds | ~5+ hours (estimated) |
| Speed Factor | **~1000x faster** | Baseline |

## Validation Status

| Check | Status | Notes |
|-------|--------|-------|
| Indicator Calculation | ⚠️ Different | Pre-computed vs real-time |
| Pattern Detection | ⚠️ Different | Simplified vs full |
| Signal Generation | ⚠️ Different | FastScorer vs SignalOrchestrator |
| Trade Execution | ✅ Similar | Same SL/TP logic |
| Position Sizing | ✅ Similar | Same risk management |

## Recommendations

### To Achieve Better Comparison:

1. **Lower min_signal_score in fast_backtest** to generate more trades
2. **Align signal generation logic** between both systems
3. **Run original backtest fully** and compare specific trades
4. **Compare indicator values** at specific timestamps

### For Production Use:

1. Use **Fast Backtest** for quick parameter optimization
2. Use **Original Backtest** for final validation
3. Results may differ - fast backtest is an approximation

## Files Created

- `compare_backtests.py` - Automated comparison script
- This report (`COMPARISON_REPORT.md`)

## Next Steps

1. [ ] Run original backtest fully (may take hours)
2. [ ] Compare specific trade timestamps
3. [ ] Calibrate fast_backtest scoring to match original
4. [ ] Add Sharpe Ratio to both backtests
5. [ ] Add Walk-Forward validation
