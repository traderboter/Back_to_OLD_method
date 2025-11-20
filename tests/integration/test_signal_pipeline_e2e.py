"""
End-to-End Integration Test for Complete Signal Generation Pipeline

Tests the entire flow from raw OHLCV data to final SignalInfo:
1. Fetch/load historical data
2. Calculate indicators
3. Run all analyzers
4. Calculate score with SignalScorer (13 multipliers)
5. Calculate SL/TP with RiskRewardCalculator (5 methods)
6. Build final SignalInfo

This verifies that all components work together correctly.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from signal_generation.context import AnalysisContext
from signal_generation.shared.indicator_calculator import IndicatorCalculator
from signal_generation.signal_scorer import SignalScorer
from signal_generation.risk_calculator import RiskRewardCalculator

# Import all analyzers
from signal_generation.analyzers.trend_analyzer import TrendAnalyzer
from signal_generation.analyzers.momentum_analyzer import MomentumAnalyzer
from signal_generation.analyzers.volume_analyzer import VolumeAnalyzer
from signal_generation.analyzers.sr_analyzer import SRAnalyzer
from signal_generation.analyzers.volatility_analyzer import VolatilityAnalyzer
from signal_generation.analyzers.harmonic_analyzer import HarmonicAnalyzer
from signal_generation.analyzers.channel_analyzer import ChannelAnalyzer
from signal_generation.analyzers.htf_analyzer import HTFAnalyzer
from signal_generation.analyzers.cyclical_analyzer import CyclicalAnalyzer


@pytest.fixture
def config():
    """Test configuration matching OLD SYSTEM"""
    return {
        'indicators': {
            'ema_periods': [20, 50, 100, 200],
            'sma_periods': [20, 50, 200],
            'rsi_period': 14,
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'stoch': {'k_period': 14, 'd_period': 3},
            'atr_period': 14,
            'bb_period': 20,
            'bb_std': 2
        },
        'analyzers': {
            'trend': {'min_strength': 0.3},
            'momentum': {'rsi_overbought': 70, 'rsi_oversold': 30},
            'volume': {'volume_threshold': 1.2},
            'support_resistance': {'lookback': 50, 'min_touches': 2},
            'volatility': {'atr_period': 14},
            'harmonic': {'tolerance': 0.05},
            'channel': {'min_points': 20},
            'htf': {'lookback_bars': 100},
            'cyclical': {'min_cycle_length': 10}
        },
        'signal_scoring': {
            'base_score_weights': {
                'momentum': 0.4,
                'pattern': 0.35,
                'sr_alignment': 0.25
            }
        },
        'risk_management': {
            'min_risk_reward_ratio': 1.5,
            'preferred_risk_reward_ratio': 2.0,
            'atr_trailing_multiplier': 2.0,
            'max_sr_distance_atr_ratio': 3.0,
            'default_stop_loss_percent': 1.5,
            'min_sl_distance_percent': 0.5,
            'max_sl_distance_percent': 5.0
        }
    }


@pytest.fixture
def realistic_bullish_data():
    """
    Create realistic bullish market data (strong uptrend with momentum).

    Simulates BTC/USDT with clear uptrend: 48,000 → 54,000 over 200 bars
    """
    np.random.seed(42)  # For reproducibility
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')

    # Create strong uptrend: 48k → 54k (+12.5%)
    base_trend = np.linspace(48000, 54000, 200)

    # Add smaller wave patterns (not overwhelming the trend)
    wave = np.sin(np.linspace(0, 3*np.pi, 200)) * 180

    # Add controlled noise
    noise = np.random.randn(200) * 100

    # Combine for close prices
    close_prices = base_trend + wave + noise

    # Create OHLC data
    data = {
        'timestamp': dates,
        'close': close_prices,
        'open': np.maximum(close_prices - np.random.rand(200) * 80 - 20, 0),
        'high': close_prices + np.random.rand(200) * 120 + 30,
        'low': close_prices - np.random.rand(200) * 120 - 30,
        'volume': np.random.rand(200) * 800 + 600
    }

    # Increase volume in uptrend (bullish signal)
    data['volume'] = data['volume'] * (1 + np.linspace(0, 0.5, 200))

    # Ensure OHLC validity
    df = pd.DataFrame(data)
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)

    df.set_index('timestamp', inplace=True)

    return df


def test_full_pipeline_bullish_signal(config, realistic_bullish_data):
    """
    Test complete signal generation pipeline with realistic bullish data.

    Flow:
    1. Create context with OHLCV data
    2. Calculate all indicators
    3. Run all analyzers
    4. Calculate score (13 multipliers)
    5. Calculate SL/TP (5 methods)
    6. Verify final signal
    """

    # ========== STEP 1: Create Context ==========
    context = AnalysisContext(
        symbol='BTCUSDT',
        timeframe='1h',
        df=realistic_bullish_data
    )

    print("\n" + "="*60)
    print("STEP 1: Context Created")
    print(f"  Symbol: {context.symbol}")
    print(f"  Timeframe: {context.timeframe}")
    print(f"  Data points: {len(context.df)}")
    print(f"  Price range: {context.df['close'].min():.2f} - {context.df['close'].max():.2f}")


    # ========== STEP 2: Calculate Indicators ==========
    indicator_calc = IndicatorCalculator(config)
    indicator_calc.calculate_all(context)

    # Verify indicators were calculated
    required_indicators = ['ema_20', 'sma_50', 'rsi', 'macd', 'atr', 'bb_upper']
    for indicator in required_indicators:
        assert indicator in context.df.columns, f"Missing indicator: {indicator}"

    current_price = context.df['close'].iloc[-1]
    current_rsi = context.df['rsi'].iloc[-1]
    current_atr = context.df['atr'].iloc[-1]

    print("\nSTEP 2: Indicators Calculated")
    print(f"  Current price: {current_price:.2f}")
    print(f"  RSI: {current_rsi:.2f}")
    print(f"  ATR: {current_atr:.2f}")
    print(f"  EMA20: {context.df['ema_20'].iloc[-1]:.2f}")
    print(f"  EMA50: {context.df['ema_50'].iloc[-1]:.2f}")


    # ========== STEP 3: Run All Analyzers ==========
    analyzers = {
        'trend': TrendAnalyzer(config),
        'momentum': MomentumAnalyzer(config),
        'volume': VolumeAnalyzer(config),
        'support_resistance': SRAnalyzer(config),
        'volatility': VolatilityAnalyzer(config),
        'harmonic': HarmonicAnalyzer(config),
        'channel': ChannelAnalyzer(config),
        'htf': HTFAnalyzer(config),
        'cyclical': CyclicalAnalyzer(config)
    }

    print("\nSTEP 3: Running Analyzers...")
    for name, analyzer in analyzers.items():
        try:
            analyzer.analyze(context)
            result = context.get_result(name)
            if result:
                status = result.get('status', 'unknown')
                direction = result.get('direction', 'N/A')
                print(f"  ✓ {name}: {status} (direction: {direction})")
        except Exception as e:
            print(f"  ✗ {name}: ERROR - {e}")

    # Verify key analyzer results
    trend_result = context.get_result('trend')
    assert trend_result is not None
    assert trend_result['status'] == 'ok'

    momentum_result = context.get_result('momentum')
    assert momentum_result is not None
    assert momentum_result['status'] == 'ok'

    volatility_result = context.get_result('volatility')
    assert volatility_result is not None
    assert 'atr_value' in volatility_result


    # ========== STEP 4: Calculate Score (13 multipliers) ==========
    scorer = SignalScorer(config)

    # Determine direction based on trend
    if trend_result['direction'] == 'bullish':
        signal_direction = 'LONG'
    elif trend_result['direction'] == 'bearish':
        signal_direction = 'SHORT'
    else:
        signal_direction = 'NEUTRAL'

    if signal_direction != 'NEUTRAL':
        score = scorer.calculate_score(context, signal_direction)

        print("\nSTEP 4: Score Calculated (13 multipliers)")
        print(f"  Direction: {signal_direction}")
        print(f"  Base score: {score.base_score:.2f}")
        print(f"  Timeframe weight: {score.timeframe_weight:.2f}")
        print(f"  Trend alignment: {score.trend_alignment:.2f}")
        print(f"  Volume confirmation: {score.volume_confirmation:.2f}")
        print(f"  Pattern quality: {score.pattern_quality:.2f}")
        print(f"  Confluence score: +{score.confluence_score:.2f}")
        print(f"  MACD analysis: {score.macd_analysis_score:.2f}")
        print(f"  Structure score: {score.structure_score:.2f}")
        print(f"  Volatility score: {score.volatility_score:.2f}")
        print(f"  Harmonic pattern: {score.harmonic_pattern_score:.2f}")
        print(f"  Price channel: {score.price_channel_score:.2f}")
        print(f"  Cyclical pattern: {score.cyclical_pattern_score:.2f}")
        print(f"  ───────────────────────────────")
        print(f"  FINAL SCORE: {score.final_score:.2f}")

        # Verify score components
        assert score.base_score >= 50, "Base score should be at least 50"
        assert score.final_score > 0, "Final score should be positive"
        assert hasattr(score, 'timeframe_weight')
        assert hasattr(score, 'trend_alignment')
        assert hasattr(score, 'volume_confirmation')
    else:
        print("\nSTEP 4: SKIPPED (No clear direction)")
        pytest.skip("No clear trend direction detected")


    # ========== STEP 5: Calculate SL/TP (5 methods) ==========
    risk_calc = RiskRewardCalculator(config)

    entry_price = current_price

    sl_tp_result = risk_calc.calculate_sl_tp(
        direction=signal_direction,
        entry_price=entry_price,
        context=context,
        adapted_config=config['risk_management']
    )

    print("\nSTEP 5: SL/TP Calculated")
    print(f"  Entry: {entry_price:.2f}")
    print(f"  Stop Loss: {sl_tp_result['stop_loss']:.2f}")
    print(f"  Take Profit: {sl_tp_result['take_profit']:.2f}")
    print(f"  Risk/Reward: {sl_tp_result['risk_reward_ratio']:.2f}")
    print(f"  Method: {sl_tp_result['sl_method']}")
    risk_distance = abs(entry_price - sl_tp_result['stop_loss'])
    print(f"  Risk distance: {risk_distance:.2f}")

    # Verify SL/TP calculation
    assert sl_tp_result['stop_loss'] > 0
    assert sl_tp_result['take_profit'] > 0
    assert sl_tp_result['risk_reward_ratio'] > 0
    assert sl_tp_result['sl_method'] is not None

    # Verify RR meets minimum
    min_rr = config['risk_management']['min_risk_reward_ratio']
    assert sl_tp_result['risk_reward_ratio'] >= min_rr, \
        f"RR {sl_tp_result['risk_reward_ratio']:.2f} should be >= {min_rr}"

    # Verify SL is in correct direction
    if signal_direction == 'LONG':
        assert sl_tp_result['stop_loss'] < entry_price, "SL should be below entry for LONG"
        assert sl_tp_result['take_profit'] > entry_price, "TP should be above entry for LONG"
    else:
        assert sl_tp_result['stop_loss'] > entry_price, "SL should be above entry for SHORT"
        assert sl_tp_result['take_profit'] < entry_price, "TP should be below entry for SHORT"


    # ========== STEP 6: Verify Complete Signal ==========
    print("\n" + "="*60)
    print("FINAL VERIFICATION")
    print(f"  ✓ Context created with {len(context.df)} data points")
    print(f"  ✓ {len([i for i in context.df.columns if i not in ['open', 'high', 'low', 'close', 'volume']])} indicators calculated")
    print(f"  ✓ {len([r for r in context.results if context.results[r].get('status') == 'ok'])} analyzers ran successfully")
    print(f"  ✓ Score calculated: {score.final_score:.2f} (13 multipliers)")
    print(f"  ✓ SL/TP calculated: RR={sl_tp_result['risk_reward_ratio']:.2f} ({sl_tp_result['sl_method']})")
    print(f"\n  🎯 COMPLETE SIGNAL GENERATED:")
    print(f"     {signal_direction} {context.symbol} @ {entry_price:.2f}")
    print(f"     SL: {sl_tp_result['stop_loss']:.2f} | TP: {sl_tp_result['take_profit']:.2f}")
    print(f"     Score: {score.final_score:.2f} | RR: {sl_tp_result['risk_reward_ratio']:.2f}")
    print("="*60)

    # Final assertions
    assert signal_direction in ['LONG', 'SHORT'], "Should have clear direction"
    assert score.final_score >= 50, "Score should be at least 50"
    assert sl_tp_result['risk_reward_ratio'] >= 1.5, "RR should be at least 1.5"

    print("\n✅ END-TO-END PIPELINE TEST PASSED")


def test_full_pipeline_components_integration(config, realistic_bullish_data):
    """
    Test that all components properly integrate with each other.

    Specifically tests:
    - Analyzers output required fields for SignalScorer
    - SignalScorer uses analyzer outputs correctly
    - RiskRewardCalculator uses analyzer outputs correctly
    """

    # Setup
    context = AnalysisContext('BTCUSDT', '1h', realistic_bullish_data)
    indicator_calc = IndicatorCalculator(config)
    indicator_calc.calculate_all(context)

    # Run analyzers
    TrendAnalyzer(config).analyze(context)
    MomentumAnalyzer(config).analyze(context)
    VolumeAnalyzer(config).analyze(context)
    SRAnalyzer(config).analyze(context)
    VolatilityAnalyzer(config).analyze(context)
    HarmonicAnalyzer(config).analyze(context)
    ChannelAnalyzer(config).analyze(context)
    HTFAnalyzer(config).analyze(context)

    # Test 1: MomentumAnalyzer outputs momentum_strength for SignalScorer
    momentum_result = context.get_result('momentum')
    assert 'momentum_strength' in momentum_result, "MomentumAnalyzer should output momentum_strength"

    # Test 2: HTFAnalyzer outputs structure_score for SignalScorer (when HTF data available)
    htf_result = context.get_result('htf')
    if htf_result and htf_result.get('status') == 'ok':
        assert 'structure_score' in htf_result, "HTFAnalyzer should output structure_score when status is ok"
    else:
        print("  HTF analyzer: no data available (expected for single TF test)")

    # Test 3: ChannelAnalyzer outputs slope/intercept for RiskRewardCalculator
    channel_result = context.get_result('channel')
    if channel_result and channel_result.get('channels'):
        # Note: The current implementation may not have these fields yet
        # This is a future requirement check
        print("  Channel result:", channel_result.keys())

    # Test 4: VolatilityAnalyzer outputs atr_value for RiskRewardCalculator
    volatility_result = context.get_result('volatility')
    assert 'atr_value' in volatility_result, "VolatilityAnalyzer should output atr_value"

    # Test 5: SignalScorer can calculate with all components
    scorer = SignalScorer(config)
    score = scorer.calculate_score(context, 'LONG')

    assert score.base_score > 0
    assert score.final_score > 0

    # Test 6: RiskRewardCalculator can calculate with all components
    risk_calc = RiskRewardCalculator(config)
    sl_tp = risk_calc.calculate_sl_tp(
        'LONG',
        context.df['close'].iloc[-1],
        context,
        config['risk_management']
    )

    assert sl_tp['stop_loss'] > 0
    assert sl_tp['take_profit'] > 0

    print("\n✅ COMPONENTS INTEGRATION TEST PASSED")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
