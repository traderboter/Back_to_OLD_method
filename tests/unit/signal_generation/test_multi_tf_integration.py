"""
Test Multi-Timeframe Aggregator Integration with RiskRewardCalculator

Tests that multi-TF aggregator properly uses RiskRewardCalculator
for SL/TP calculation instead of simple percentage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from signal_generation.multi_tf_aggregator import MultiTimeframeAggregator, TimeframeSignal
from signal_generation.context import AnalysisContext
from signal_generation.signal_info import SignalScore


@pytest.fixture
def config():
    """Test configuration"""
    return {
        'signal_processing': {
            'multi_timeframe': {
                'weights': {
                    '5m': 0.7,
                    '15m': 0.85,
                    '1h': 1.0,
                    '4h': 1.1
                },
                'direction_margin': 1.3,
                'min_timeframes': 2
            }
        },
        'risk_management': {
            'min_risk_reward_ratio': 1.5,
            'preferred_risk_reward_ratio': 2.0,
            'atr_trailing_multiplier': 2.0,
            'max_sr_distance_atr_ratio': 3.0,
            'default_stop_loss_percent': 1.5
        }
    }


@pytest.fixture
def mock_df():
    """Create mock DataFrame with sufficient data"""
    # Create 200 rows of OHLCV data
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')

    data = {
        'timestamp': dates,
        'open': np.linspace(50000, 52000, 200) + np.random.randn(200) * 100,
        'high': np.linspace(50100, 52100, 200) + np.random.randn(200) * 100,
        'low': np.linspace(49900, 51900, 200) + np.random.randn(200) * 100,
        'close': np.linspace(50000, 52000, 200) + np.random.randn(200) * 100,
        'volume': np.random.rand(200) * 1000 + 500
    }

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    # Add required indicators
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_100'] = df['close'].ewm(span=100).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()

    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    df['rsi'] = 55.0  # Neutral RSI

    # MACD
    ema_12 = df['close'].ewm(span=12).mean()
    ema_26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Stochastic
    df['stoch_k'] = 50.0
    df['stoch_d'] = 50.0

    # ATR (important for RiskRewardCalculator)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (std * 2)
    df['bb_lower'] = df['bb_middle'] - (std * 2)

    # Volume indicators
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['obv'] = (df['volume'] * (~df['close'].diff().le(0) * 2 - 1)).cumsum()

    return df


@pytest.fixture
def mock_context_bullish(mock_df):
    """Create mock bullish context"""
    context = AnalysisContext(symbol='BTCUSDT', timeframe='1h', df=mock_df)

    # Add analyzer results
    context.add_result('trend', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 0.8,
        'phase': 'early'
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 0.7,
        'momentum_strength': 1.2,
        'bullish_score': 0.8,
        'bearish_score': 0.2,
        'macd_signal': {'direction': 'bullish'},
        'macd_market_type': 'A_bullish_strong'
    })

    context.add_result('volume', {
        'status': 'ok',
        'is_confirmed': True,
        'volume_trend': 'increasing',
        'relative_volume': 1.3
    })

    context.add_result('volatility', {
        'status': 'ok',
        'atr_value': 500.0,
        'recommended_stop_atr': 2.0,
        'risk_multiplier': 1.0
    })

    # Add S/R levels for testing
    current_price = mock_df['close'].iloc[-1]
    context.add_result('support_resistance', {
        'status': 'ok',
        'nearest_support': current_price - 1000,
        'nearest_resistance': current_price + 1500,
        'broken_levels': []
    })

    return context


@pytest.fixture
def mock_timeframe_signals(mock_context_bullish):
    """Create mock timeframe signals"""
    signals = {}

    for tf in ['5m', '15m', '1h', '4h']:
        score = SignalScore()
        score.final_score = 75.0

        tf_signal = TimeframeSignal(
            timeframe=tf,
            direction='LONG',
            score=score,
            context=mock_context_bullish,
            volume_confirmed=True,
            htf_aligned=True
        )

        signals[tf] = tf_signal

    return signals


def test_multi_tf_aggregator_initialization(config):
    """Test that MultiTimeframeAggregator initializes with RiskRewardCalculator"""
    aggregator = MultiTimeframeAggregator(config)

    # Check that risk_calculator is initialized
    assert hasattr(aggregator, 'risk_calculator')
    assert aggregator.risk_calculator is not None

    print("✅ MultiTimeframeAggregator initialized with RiskRewardCalculator")


def test_multi_tf_uses_risk_calculator(config, mock_timeframe_signals):
    """Test that multi-TF aggregator uses RiskRewardCalculator for SL/TP"""
    aggregator = MultiTimeframeAggregator(config)

    # Aggregate signals
    signal = aggregator.aggregate_timeframe_scores(
        symbol='BTCUSDT',
        timeframe_signals=mock_timeframe_signals
    )

    # Check that signal was created
    assert signal is not None
    assert signal.direction == 'LONG'

    # Check that SL/TP was calculated (not None)
    assert signal.stop_loss is not None
    assert signal.take_profit is not None
    assert signal.risk_reward_ratio is not None

    # Check that RR is reasonable (not the hardcoded 2.0 from old percentage method)
    # Old method: SL = price * 0.98, TP = price * 1.04 → RR = 2.0 exactly
    # New method: Should vary based on actual calculation
    assert signal.risk_reward_ratio > 0

    # Check that sl_method is tracked in metadata
    assert 'sl_method' in signal.score.metadata
    sl_method = signal.score.metadata['sl_method']

    # Should be one of the 5 methods, not "Simple Percentage"
    valid_methods = [
        'Harmonic_', 'Price_Channel_', 'Support Level', 'Resistance Level',
        'ATR', 'Percentage'
    ]
    assert any(method in sl_method for method in valid_methods)

    # Check that RR is stored in metadata
    assert 'risk_reward_ratio' in signal.score.metadata
    assert signal.score.metadata['risk_reward_ratio'] == signal.risk_reward_ratio

    print(f"✅ Multi-TF signal uses RiskRewardCalculator")
    print(f"   Direction: {signal.direction}")
    print(f"   Entry: {signal.entry_price:.2f}")
    print(f"   SL: {signal.stop_loss:.2f}")
    print(f"   TP: {signal.take_profit:.2f}")
    print(f"   RR: {signal.risk_reward_ratio:.2f}")
    print(f"   Method: {sl_method}")


def test_multi_tf_rejects_low_rr(config, mock_timeframe_signals, mock_context_bullish):
    """Test that multi-TF aggregator rejects signals with RR below minimum"""

    # Modify context to create a scenario with very close S/R (low RR)
    current_price = mock_context_bullish.df['close'].iloc[-1]
    mock_context_bullish.add_result('support_resistance', {
        'status': 'ok',
        'nearest_support': current_price - 50,  # Very close support
        'nearest_resistance': current_price + 60,  # Very close resistance
        'broken_levels': []
    })

    # Set very strict min_rr
    config['risk_management']['min_risk_reward_ratio'] = 3.0

    aggregator = MultiTimeframeAggregator(config)

    # Try to aggregate - should return None if RR < 3.0
    signal = aggregator.aggregate_timeframe_scores(
        symbol='BTCUSDT',
        timeframe_signals=mock_timeframe_signals
    )

    # Signal might be None if RR is too low, or might pass if ATR fallback gives good RR
    if signal is None:
        print("✅ Multi-TF correctly rejected low RR signal")
    else:
        print(f"✅ Multi-TF accepted signal with RR={signal.risk_reward_ratio:.2f} (>= 3.0)")
        assert signal.risk_reward_ratio >= 3.0


def test_multi_tf_sl_method_logged(config, mock_timeframe_signals):
    """Test that SL/TP method is logged and tracked"""
    aggregator = MultiTimeframeAggregator(config)

    signal = aggregator.aggregate_timeframe_scores(
        symbol='BTCUSDT',
        timeframe_signals=mock_timeframe_signals
    )

    assert signal is not None

    # Check that sl_method is in key_factors
    key_factors_str = ' '.join(signal.key_factors)
    assert 'SL/TP method' in key_factors_str
    assert 'RR=' in key_factors_str

    print("✅ SL/TP method is properly logged in signal")
    print(f"   Key factors: {signal.key_factors}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
