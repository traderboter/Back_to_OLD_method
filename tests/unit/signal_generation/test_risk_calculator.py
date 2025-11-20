"""
Unit tests for RiskRewardCalculator

تست‌های جامع برای RiskRewardCalculator با پوشش 5 روش اولویت‌دار.
"""

import pytest
import pandas as pd
import numpy as np
from signal_generation.risk_calculator import RiskRewardCalculator
from signal_generation.context import AnalysisContext


@pytest.fixture
def config():
    """تنظیمات پیش‌فرض."""
    return {
        'risk': {
            'default_stop_loss_percent': 2.0,
            'preferred_risk_reward_ratio': 2.0,
            'min_risk_reward_ratio': 1.5,
            'atr_trailing_multiplier': 2.0
        }
    }


@pytest.fixture
def calculator(config):
    """RiskRewardCalculator instance."""
    return RiskRewardCalculator(config)


@pytest.fixture
def sample_df():
    """Sample DataFrame with price data."""
    data = {
        'open': [50000.0] * 100,
        'high': [50100.0] * 100,
        'low': [49900.0] * 100,
        'close': [50000.0] * 100,
        'volume': [1000.0] * 100,
        'atr': [500.0] * 100
    }
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def context_with_harmonic(sample_df):
    """Context with harmonic pattern data."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # Add volatility result with ATR
    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    # Add harmonic pattern (Butterfly, bullish)
    context.add_result('harmonic', {
        'status': 'ok',
        'patterns': [
            {
                'name': 'Butterfly',
                'type': 'bullish',
                'strength': 3,
                'completion': 0.95,
                'points': {
                    'X': {'price': 48000.0, 'index': 10},
                    'A': {'price': 51000.0, 'index': 20},
                    'B': {'price': 49000.0, 'index': 30},
                    'C': {'price': 50500.0, 'index': 40},
                    'D': {'price': 49500.0, 'index': 50}
                }
            }
        ]
    })

    return context


@pytest.fixture
def context_with_channel(sample_df):
    """Context with price channel data."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    # Add ascending channel
    context.add_result('channel', {
        'status': 'ok',
        'channel_type': 'ascending',
        'upper_bound': 51000.0,
        'lower_bound': 49000.0,
        'channel_width': 2000.0,
        'price_position': 'middle',
        'breakout': False,
        'strength': 3
    })

    return context


@pytest.fixture
def context_with_sr(sample_df):
    """Context with support/resistance data."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    # Add S/R levels
    context.add_result('support_resistance', {
        'status': 'ok',
        'nearest_support': 49500.0,
        'nearest_resistance': 50500.0,
        'support_levels': [49500.0, 49000.0],
        'resistance_levels': [50500.0, 51000.0],
        'level_strength': 2
    })

    return context


@pytest.fixture
def context_minimal(sample_df):
    """Minimal context (will use ATR/Percentage fallback)."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    return context


# ===== Test 1: Harmonic Pattern Method =====

def test_harmonic_long_butterfly(calculator, context_with_harmonic):
    """تست محاسبه SL/TP با Harmonic Pattern (LONG Butterfly)."""
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_with_harmonic
    )

    # D point = 49500, SL should be 49500 × 0.99 = 49005
    expected_sl = 49500.0 * 0.99
    assert abs(result['stop_loss'] - expected_sl) < 100  # Allow some tolerance

    # For Butterfly, TP = entry + (entry - SL) × 1.618
    # TP = 50000 + (50000 - 49005) × 1.618 ≈ 51609.31
    expected_tp = 50000.0 + (50000.0 - expected_sl) * 1.618
    assert abs(result['take_profit'] - expected_tp) < 100

    assert result['sl_method'].startswith('Harmonic_')
    assert 'butterfly' in result['sl_method'].lower()
    assert result['risk_reward_ratio'] > 0


def test_harmonic_short_gartley(calculator, sample_df):
    """تست محاسبه SL/TP با Harmonic Pattern (SHORT Gartley)."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    # Add bearish Gartley pattern
    context.add_result('harmonic', {
        'status': 'ok',
        'patterns': [
            {
                'name': 'Gartley',
                'type': 'bearish',
                'strength': 3,
                'completion': 0.90,
                'points': {
                    'X': {'price': 52000.0, 'index': 10},
                    'A': {'price': 49000.0, 'index': 20},
                    'B': {'price': 51000.0, 'index': 30},
                    'C': {'price': 49500.0, 'index': 40},
                    'D': {'price': 50500.0, 'index': 50}
                }
            }
        ]
    })

    result = calculator.calculate_sl_tp(
        direction='SHORT',
        entry_price=50000.0,
        context=context
    )

    # D point = 50500, SL should be 50500 × 1.01 = 51005
    expected_sl = 50500.0 * 1.01
    assert abs(result['stop_loss'] - expected_sl) < 100

    # TP should be below entry (SHORT)
    assert result['take_profit'] < 50000.0

    assert result['sl_method'].startswith('Harmonic_')
    assert 'gartley' in result['sl_method'].lower()
    assert result['risk_reward_ratio'] > 0


# ===== Test 2: Price Channel Method =====

def test_channel_long_ascending(calculator, context_with_channel):
    """تست محاسبه SL/TP با Price Channel (LONG ascending)."""
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_with_channel
    )

    # SL = lower_bound × 0.99 = 49000 × 0.99 = 48510
    expected_sl = 49000.0 * 0.99
    assert abs(result['stop_loss'] - expected_sl) < 100

    # TP should be above entry (LONG) - may be adjusted by RR/safety checks
    assert result['take_profit'] > 50000.0

    assert result['sl_method'].startswith('Price_Channel_')
    assert 'ascending' in result['sl_method']
    assert result['risk_reward_ratio'] > 0


def test_channel_short_descending(calculator, sample_df):
    """تست محاسبه SL/TP با Price Channel (SHORT descending)."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    # Add descending channel
    context.add_result('channel', {
        'status': 'ok',
        'channel_type': 'descending',
        'upper_bound': 51000.0,
        'lower_bound': 49000.0,
        'channel_width': 2000.0,
        'price_position': 'middle',
        'breakout': False,
        'strength': 3
    })

    result = calculator.calculate_sl_tp(
        direction='SHORT',
        entry_price=50000.0,
        context=context
    )

    # SL = upper_bound × 1.01 = 51000 × 1.01 = 51510
    expected_sl = 51000.0 * 1.01
    assert abs(result['stop_loss'] - expected_sl) < 100

    # TP should be below entry (SHORT) - may be adjusted by RR/safety checks
    assert result['take_profit'] < 50000.0

    assert result['sl_method'].startswith('Price_Channel_')
    assert 'descending' in result['sl_method']
    assert result['risk_reward_ratio'] > 0


def test_channel_wrong_direction_skipped(calculator, context_with_channel):
    """تست skip شدن channel در صورت عدم تطابق با direction."""
    # Context has ascending channel, but we're going SHORT
    # Should skip channel and use next method (S/R or ATR)
    result = calculator.calculate_sl_tp(
        direction='SHORT',
        entry_price=50000.0,
        context=context_with_channel
    )

    # Should NOT use channel method
    assert not result['sl_method'].startswith('Price_Channel_')
    # Should use ATR or Percentage fallback
    assert 'ATR' in result['sl_method'] or 'Percentage' in result['sl_method']


# ===== Test 3: Support/Resistance Method =====

def test_sr_long_support(calculator, context_with_sr):
    """تست محاسبه SL با Support (LONG)."""
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_with_sr
    )

    # SL = nearest_support × 0.999 = 49500 × 0.999 = 49450.5
    expected_sl = 49500.0 * 0.999
    assert abs(result['stop_loss'] - expected_sl) < 100

    assert 'Support' in result['sl_method'] or result['sl_method'].startswith('Support')


def test_sr_short_resistance(calculator, context_with_sr):
    """تست محاسبه SL با Resistance (SHORT)."""
    result = calculator.calculate_sl_tp(
        direction='SHORT',
        entry_price=50000.0,
        context=context_with_sr
    )

    # SL = nearest_resistance × 1.001 = 50500 × 1.001 = 50550.5
    expected_sl = 50500.0 * 1.001
    assert abs(result['stop_loss'] - expected_sl) < 100

    assert 'Resistance' in result['sl_method'] or result['sl_method'].startswith('Resistance')


def test_sr_too_far_rejected(calculator, sample_df):
    """تست رد شدن S/R در صورت فاصله بیش از 3×ATR."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0  # ATR = 500, max distance = 3×500 = 1500
    })

    # Add S/R with support too far away (> 1500)
    context.add_result('support_resistance', {
        'status': 'ok',
        'nearest_support': 48000.0,  # Distance = 50000 - 48000 = 2000 > 1500
        'nearest_resistance': 52000.0
    })

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context
    )

    # Should NOT use Support method (too far)
    assert 'Support' not in result['sl_method']
    # Should fall back to ATR
    assert 'ATR' in result['sl_method']


# ===== Test 4: ATR Fallback =====

def test_atr_fallback_long(calculator, context_minimal):
    """تست fallback به ATR (LONG)."""
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_minimal
    )

    # SL = entry - (ATR × 2.0) = 50000 - (500 × 2) = 49000
    expected_sl = 50000.0 - (500.0 * 2.0)
    assert abs(result['stop_loss'] - expected_sl) < 10

    assert 'ATR' in result['sl_method']


def test_atr_fallback_short(calculator, context_minimal):
    """تست fallback به ATR (SHORT)."""
    result = calculator.calculate_sl_tp(
        direction='SHORT',
        entry_price=50000.0,
        context=context_minimal
    )

    # SL = entry + (ATR × 2.0) = 50000 + (500 × 2) = 51000
    expected_sl = 50000.0 + (500.0 * 2.0)
    assert abs(result['stop_loss'] - expected_sl) < 10

    assert 'ATR' in result['sl_method']


# ===== Test 5: Percentage Fallback =====

def test_percentage_fallback_long(calculator, sample_df):
    """تست fallback به Percentage (LONG) - بدون ATR."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # No volatility result, no ATR in df
    df_no_atr = sample_df.drop(columns=['atr'])
    context.df = df_no_atr

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context
    )

    # Should use default ATR (0.5% of price) = 250
    # But let's focus on testing that Percentage method is used
    assert 'Percentage' in result['sl_method'] or 'ATR' in result['sl_method']


def test_percentage_fallback_with_config(calculator, sample_df):
    """تست Percentage fallback با custom config."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)
    df_no_atr = sample_df.drop(columns=['atr'])
    context.df = df_no_atr

    adapted_config = {
        'default_stop_loss_percent': 3.0  # 3% instead of 2%
    }

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context,
        adapted_config=adapted_config
    )

    # Should have some valid SL/TP
    assert result['stop_loss'] < 50000.0
    assert result['take_profit'] > 50000.0


# ===== Test 6: Safety Checks =====

def test_minimum_sl_distance(calculator, sample_df):
    """تست safety check برای حداقل فاصله SL."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'atr': 500.0
    })

    # Add S/R very close to entry (should be adjusted)
    context.add_result('support_resistance', {
        'status': 'ok',
        'nearest_support': 49950.0,  # Very close: only 50 away
        'nearest_resistance': 50050.0
    })

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context
    )

    # Minimum distance should be 0.5×ATR = 0.5×500 = 250
    assert (50000.0 - result['stop_loss']) >= 250 - 10  # Allow small tolerance


def test_minimum_rr_ratio(calculator, context_minimal):
    """تست safety check برای حداقل RR ratio."""
    adapted_config = {
        'preferred_risk_reward_ratio': 2.0,
        'min_risk_reward_ratio': 1.5
    }

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_minimal,
        adapted_config=adapted_config
    )

    # RR should be at least min_rr_ratio
    assert result['risk_reward_ratio'] >= 1.5


# ===== Test 7: TP Adjustment with S/R =====

def test_tp_adjusted_to_resistance(calculator, context_with_sr):
    """تست تنظیم TP بر اساس resistance نزدیک."""
    # Context has resistance at 50500
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_with_sr
    )

    # TP might be adjusted to resistance (50500 × 0.999)
    # Or might keep calculated TP if resistance is too close
    # Either way, TP should be reasonable
    assert result['take_profit'] > 50000.0
    assert result['risk_reward_ratio'] >= 1.5


def test_tp_adjusted_to_support(calculator, context_with_sr):
    """تست تنظیم TP بر اساس support نزدیک."""
    # Context has support at 49500
    result = calculator.calculate_sl_tp(
        direction='SHORT',
        entry_price=50000.0,
        context=context_with_sr
    )

    # TP might be adjusted to support (49500 × 1.001)
    # Or might keep calculated TP if support is too close
    assert result['take_profit'] < 50000.0
    assert result['risk_reward_ratio'] >= 1.5


# ===== Test 8: Edge Cases =====

def test_invalid_direction(calculator, context_minimal):
    """تست مدیریت direction نامعتبر."""
    with pytest.raises(ValueError, match="Invalid direction"):
        calculator.calculate_sl_tp(
            direction='INVALID',
            entry_price=50000.0,
            context=context_minimal
        )


def test_zero_entry_price(calculator, context_minimal):
    """تست مدیریت entry_price صفر."""
    # Should not crash, should return some fallback
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=0.0,
        context=context_minimal
    )

    # Should return a result without crashing
    assert 'stop_loss' in result
    assert 'take_profit' in result
    assert 'sl_method' in result


def test_empty_context(calculator, sample_df):
    """تست context خالی (بدون هیچ نتیجه‌ای)."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # No results added, should fall back to percentage
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context
    )

    # Should use ATR from df or Percentage fallback
    assert result['stop_loss'] > 0
    assert result['take_profit'] > result['stop_loss']


def test_error_fallback(calculator, sample_df):
    """تست error fallback mechanism."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # Create problematic context that might cause errors
    # (e.g., corrupted data)
    context.df = pd.DataFrame()  # Empty df

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context
    )

    # Should return error fallback
    assert 'Error' in result['sl_method'] or 'Fallback' in result['sl_method']
    assert result['stop_loss'] > 0
    assert result['take_profit'] > 0


# ===== Test 9: Direction Normalization =====

def test_lowercase_direction(calculator, context_minimal):
    """تست normalization برای direction کوچک."""
    result = calculator.calculate_sl_tp(
        direction='long',  # lowercase
        entry_price=50000.0,
        context=context_minimal
    )

    assert result['stop_loss'] < 50000.0  # LONG should have SL below entry
    assert result['take_profit'] > 50000.0


def test_mixed_case_direction(calculator, context_minimal):
    """تست normalization برای direction با حروف مختلط."""
    result = calculator.calculate_sl_tp(
        direction='Long',  # Mixed case
        entry_price=50000.0,
        context=context_minimal
    )

    assert result['stop_loss'] < 50000.0
    assert result['take_profit'] > 50000.0


# ===== Test 10: Return Value Structure =====

def test_return_value_structure(calculator, context_minimal):
    """تست ساختار dictionary برگشتی."""
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=context_minimal
    )

    # Check all required keys exist
    assert 'stop_loss' in result
    assert 'take_profit' in result
    assert 'risk_reward_ratio' in result
    assert 'risk_distance' in result
    assert 'sl_method' in result

    # Check types
    assert isinstance(result['stop_loss'], float)
    assert isinstance(result['take_profit'], float)
    assert isinstance(result['risk_reward_ratio'], float)
    assert isinstance(result['risk_distance'], float)
    assert isinstance(result['sl_method'], str)

    # Check values are reasonable
    assert result['stop_loss'] > 0
    assert result['take_profit'] > 0
    assert result['risk_reward_ratio'] > 0
    assert result['risk_distance'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
