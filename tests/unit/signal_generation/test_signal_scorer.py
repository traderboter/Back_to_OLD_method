"""
Unit tests for SignalScorer

تست‌های جامع برای SignalScorer با پوشش تمام 13 ضریب.
"""

import pytest
import pandas as pd
import numpy as np
from signal_generation.signal_scorer import SignalScorer, SignalScore
from signal_generation.context import AnalysisContext


@pytest.fixture
def config():
    """تنظیمات پیش‌فرض."""
    return {
        'scoring': {
            'min_base_score': 50.0,
            'min_final_score': 60.0
        }
    }


@pytest.fixture
def scorer(config):
    """SignalScorer instance."""
    return SignalScorer(config)


@pytest.fixture
def sample_df():
    """Sample DataFrame with price data."""
    data = {
        'open': [50000.0] * 100,
        'high': [50100.0] * 100,
        'low': [49900.0] * 100,
        'close': [50000.0] * 100,
        'volume': [1000.0] * 100,
        'atr': [500.0] * 100,
        'rsi': [50.0] * 100,
        'macd': [10.0] * 100,
        'macd_signal': [8.0] * 100,
        'macd_hist': [2.0] * 100,
        'slowk': [50.0] * 100,
        'slowd': [48.0] * 100
    }
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def context_bullish(sample_df):
    """Context with bullish signals."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # Trend: bullish
    context.add_result('trend', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.5
    })

    # Momentum: bullish
    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.8,
        'momentum_strength': 8.5,
        'macd_market_type': 'A_TREND',
        'advanced_macd_signals': [
            {'type': 'crossover', 'direction': 'bullish'}
        ]
    })

    # Volume: high
    context.add_result('volume', {
        'status': 'ok',
        'signal': 'high',
        'volume_trend': 'increasing'
    })

    # Pattern: strong
    context.add_result('pattern', {
        'status': 'ok',
        'patterns': [
            {'name': 'bullish_engulfing', 'confidence': 0.8}
        ]
    })

    # S/R: strong levels
    context.add_result('support_resistance', {
        'status': 'ok',
        'level_strength': 2.5,
        'nearest_support': 49000.0,
        'nearest_resistance': 51000.0
    })

    # Volatility: normal
    context.add_result('volatility', {
        'status': 'ok',
        'regime': 'normal',
        'atr': 500.0
    })

    # HTF: aligned
    context.add_result('htf', {
        'status': 'ok',
        'htf_trend': 'bullish',
        'structure_score': 1.2,
        'alignment': True
    })

    # Harmonic: found
    context.add_result('harmonic', {
        'status': 'ok',
        'patterns': [
            {'name': 'Gartley', 'strength': 3, 'completion': 0.9}
        ]
    })

    # Channel: ascending
    context.add_result('channel', {
        'status': 'ok',
        'channel_type': 'ascending',
        'strength': 3
    })

    # Cyclical: accumulation
    context.add_result('cyclical', {
        'status': 'ok',
        'phase': 'accumulation',
        'confidence': 0.7
    })

    return context


@pytest.fixture
def context_bearish(sample_df):
    """Context with bearish signals."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # Trend: bearish
    context.add_result('trend', {
        'status': 'ok',
        'direction': 'bearish',
        'strength': 2.3
    })

    # Momentum: bearish
    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bearish',
        'strength': 2.5,
        'momentum_strength': 7.2,
        'macd_market_type': 'C_TREND',
        'advanced_macd_signals': []
    })

    # Volume: low
    context.add_result('volume', {
        'status': 'ok',
        'signal': 'low',
        'volume_trend': 'decreasing'
    })

    # Pattern: weak
    context.add_result('pattern', {
        'status': 'ok',
        'patterns': [
            {'name': 'bearish_harami', 'confidence': 0.5}
        ]
    })

    # S/R: weak levels
    context.add_result('support_resistance', {
        'status': 'ok',
        'level_strength': 1.0,
        'nearest_support': 49500.0,
        'nearest_resistance': 50500.0
    })

    # Volatility: high
    context.add_result('volatility', {
        'status': 'ok',
        'regime': 'high',
        'atr': 800.0
    })

    return context


@pytest.fixture
def context_minimal(sample_df):
    """Minimal context with few results."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    # Only basic results
    context.add_result('trend', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    return context


# ===== Test 1: Basic Score Calculation =====

def test_calculate_score_bullish(scorer, context_bullish):
    """تست محاسبه امتیاز برای سیگنال صعودی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Check that score was calculated
    assert isinstance(score, SignalScore)
    assert score.base_score > 0
    assert score.final_score > 0

    # Base score should be high (bullish + good patterns)
    assert score.base_score >= 70  # High base score

    # Final score should be amplified by multipliers
    assert score.final_score > score.base_score

    # Check metadata
    assert score.details['direction'] == 'LONG'
    assert score.details['symbol'] == 'BTCUSDT'


def test_calculate_score_bearish(scorer, context_bearish):
    """تست محاسبه امتیاز برای سیگنال نزولی."""
    score = scorer.calculate_score(context_bearish, 'SHORT')

    assert isinstance(score, SignalScore)
    assert score.base_score > 0
    assert score.final_score > 0

    # Should have reasonable score
    assert 50 <= score.base_score <= 100


def test_calculate_score_minimal(scorer, context_minimal):
    """تست محاسبه امتیاز با context حداقلی."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    assert isinstance(score, SignalScore)
    # Should have minimal but valid score
    assert score.base_score >= 50  # Minimum base score
    assert score.final_score >= 0


# ===== Test 2: Base Score Calculation =====

def test_base_score_with_strong_momentum(scorer, context_bullish):
    """تست base_score با momentum قوی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Strong aligned momentum should give high base score
    assert score.base_score >= 70


def test_base_score_with_weak_momentum(scorer, context_minimal):
    """تست base_score با momentum ضعیف."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    # Weak momentum should give lower base score
    assert score.base_score <= 70


def test_base_score_against_direction(scorer, context_bullish):
    """تست base_score با جهت مخالف."""
    # Context is bullish, but we're going SHORT
    score = scorer.calculate_score(context_bullish, 'SHORT')

    # Should have lower base score (misaligned)
    assert score.base_score < 70


# ===== Test 3: Timeframe Weight =====

def test_timeframe_weight_with_htf_confirmation(scorer, sample_df):
    """تست timeframe_weight با تأیید HTF."""
    context = AnalysisContext('BTCUSDT', '5m', sample_df)

    # Add basic momentum
    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.0,
        'momentum_strength': 5.0,
        'macd_market_type': 'A_TREND',
        'advanced_macd_signals': []
    })

    # Timeframe data with HTF confirmation
    tf_data = {
        'primary_timeframe': '5m',
        'is_reversal': False,
        'reversal_strength': 0,
        'analysis_results': {
            '5m': {'trend': {'direction': 'bullish'}},
            '15m': {'trend': {'direction': 'bullish'}},
            '1h': {'trend': {'direction': 'bullish'}},
            '4h': {'trend': {'direction': 'bullish'}}
        }
    }

    score = scorer.calculate_score(context, 'LONG', timeframe_data=tf_data)

    # Should have high timeframe weight (HTF confirmation)
    assert score.timeframe_weight > 1.0
    assert score.timeframe_weight <= 1.5


def test_timeframe_weight_reversal(scorer, sample_df):
    """تست timeframe_weight با reversal."""
    context = AnalysisContext('BTCUSDT', '5m', sample_df)

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.0,
        'momentum_strength': 5.0,
        'macd_market_type': 'B_REVERSAL',
        'advanced_macd_signals': []
    })

    # Reversal pattern - HTF is bearish but we're going LONG
    tf_data = {
        'primary_timeframe': '5m',
        'is_reversal': True,
        'reversal_strength': 0.8,
        'analysis_results': {
            '5m': {'trend': {'direction': 'bullish'}},
            '15m': {'trend': {'direction': 'bearish'}},
            '1h': {'trend': {'direction': 'bearish'}}
        }
    }

    score = scorer.calculate_score(context, 'LONG', timeframe_data=tf_data)

    # Reversal should have lower weight (less dependent on HTF)
    assert 0.7 <= score.timeframe_weight <= 1.3


def test_timeframe_weight_no_data(scorer, context_minimal):
    """تست timeframe_weight بدون داده multi-TF."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    # Should default to 1.0
    assert score.timeframe_weight == 1.0


# ===== Test 4: Trend Alignment =====

def test_trend_alignment_with_trend(scorer, context_bullish):
    """تست trend_alignment با ترند همسو."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # LONG with bullish trend → 1.3
    assert score.trend_alignment == 1.3


def test_trend_alignment_against_trend(scorer, context_bullish):
    """تست trend_alignment با ترند مخالف."""
    score = scorer.calculate_score(context_bullish, 'SHORT')

    # SHORT with bullish trend → 0.7
    assert score.trend_alignment == 0.7


def test_trend_alignment_neutral(scorer, context_minimal):
    """تست trend_alignment با ترند خنثی."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    # Neutral trend → 1.0
    assert score.trend_alignment == 1.0


# ===== Test 5: Volume Confirmation =====

def test_volume_confirmation_high(scorer, context_bullish):
    """تست volume_confirmation با حجم بالا."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # High volume + increasing → 1.2
    assert score.volume_confirmation == 1.2


def test_volume_confirmation_low(scorer, context_bearish):
    """تست volume_confirmation با حجم پایین."""
    score = scorer.calculate_score(context_bearish, 'SHORT')

    # Low volume → 0.8
    assert score.volume_confirmation == 0.8


def test_volume_confirmation_normal(scorer, sample_df):
    """تست volume_confirmation با حجم معمولی."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volume', {
        'status': 'ok',
        'signal': 'normal',
        'volume_trend': 'stable'
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # Normal volume → 1.0
    assert score.volume_confirmation == 1.0


# ===== Test 6: Pattern Quality =====

def test_pattern_quality_high_confidence(scorer, context_bullish):
    """تست pattern_quality با confidence بالا."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # High confidence (0.8) → quality should be high
    assert score.pattern_quality > 1.0
    assert score.pattern_quality <= 1.2


def test_pattern_quality_low_confidence(scorer, context_bearish):
    """تست pattern_quality با confidence پایین."""
    score = scorer.calculate_score(context_bearish, 'SHORT')

    # Low confidence (0.5) → quality around 1.0
    assert 0.9 <= score.pattern_quality <= 1.1


def test_pattern_quality_no_patterns(scorer, sample_df):
    """تست pattern_quality بدون الگو."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('pattern', {
        'status': 'ok',
        'patterns': []
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # No patterns → 1.0
    assert score.pattern_quality == 1.0


# ===== Test 7: Confluence Score =====

def test_confluence_multiple_patterns(scorer, sample_df):
    """تست confluence_score با الگوهای متعدد."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('pattern', {
        'status': 'ok',
        'patterns': [
            {'name': 'engulfing', 'confidence': 0.8},
            {'name': 'hammer', 'confidence': 0.7}
        ]
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.0,
        'momentum_strength': 5.0,
        'macd_market_type': 'A_TREND',
        'advanced_macd_signals': []
    })

    context.add_result('trend', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.0
    })

    context.add_result('support_resistance', {
        'status': 'ok',
        'level_strength': 2.5
    })

    score = scorer.calculate_score(context, 'LONG')

    # Multiple patterns (+0.1) + S/R (+0.1) + aligned indicators (+0.15) = 0.35
    assert score.confluence_score >= 0.3


def test_confluence_no_factors(scorer, context_minimal):
    """تست confluence_score بدون فاکتورهای همگرایی."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    # No confluence factors → 0.0
    assert score.confluence_score == 0.0


# ===== Test 8: MACD Analysis Score =====

def test_macd_score_strong_trend(scorer, context_bullish):
    """تست macd_score با trend قوی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # A_TREND market type + advanced signal → > 1.0
    assert score.macd_analysis_score > 1.0
    assert score.macd_analysis_score <= 1.4


def test_macd_score_reversal(scorer, sample_df):
    """تست macd_score با reversal."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 2.0,
        'momentum_strength': 5.0,
        'macd_market_type': 'B_REVERSAL',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # B_REVERSAL → 1.15
    assert score.macd_analysis_score == 1.15


def test_macd_score_weak_market(scorer, context_minimal):
    """تست macd_score با بازار ضعیف."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    # X market type, no signals → 1.0
    assert score.macd_analysis_score == 1.0


# ===== Test 9: HTF Structure Score =====

def test_structure_score_strong(scorer, context_bullish):
    """تست structure_score با ساختار قوی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # HTF has structure_score = 1.2
    assert score.structure_score == 1.2


def test_structure_score_no_htf(scorer, sample_df):
    """تست structure_score بدون HTF."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # No HTF → 1.0
    assert score.structure_score == 1.0


# ===== Test 10: Volatility Score =====

def test_volatility_score_high(scorer, context_bearish):
    """تست volatility_score با نوسان بالا."""
    score = scorer.calculate_score(context_bearish, 'SHORT')

    # High volatility → 1.2
    assert score.volatility_score == 1.2


def test_volatility_score_normal(scorer, context_bullish):
    """تست volatility_score با نوسان معمولی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Normal volatility → 1.0
    assert score.volatility_score == 1.0


def test_volatility_score_low(scorer, sample_df):
    """تست volatility_score با نوسان پایین."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('volatility', {
        'status': 'ok',
        'regime': 'low',
        'atr': 200.0
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # Low volatility → 0.8
    assert score.volatility_score == 0.8


# ===== Test 11: Harmonic Pattern Score =====

def test_harmonic_score_strong_pattern(scorer, context_bullish):
    """تست harmonic_score با الگوی قوی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Strong pattern (strength=3, completion=0.9) → > 1.0
    assert score.harmonic_pattern_score > 1.0
    assert score.harmonic_pattern_score <= 1.3


def test_harmonic_score_no_pattern(scorer, sample_df):
    """تست harmonic_score بدون الگو."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('harmonic', {
        'status': 'ok',
        'patterns': []
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # No pattern → 1.0
    assert score.harmonic_pattern_score == 1.0


# ===== Test 12: Channel Score =====

def test_channel_score_strong_channel(scorer, context_bullish):
    """تست channel_score با کانال قوی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Strong channel (strength=3) → > 1.0
    assert score.price_channel_score > 1.0
    assert score.price_channel_score <= 1.2


def test_channel_score_weak_channel(scorer, sample_df):
    """تست channel_score با کانال ضعیف."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('channel', {
        'status': 'ok',
        'channel_type': 'ascending',
        'strength': 1
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # Weak channel → 1.0
    assert score.price_channel_score == 1.0


def test_channel_score_irregular(scorer, sample_df):
    """تست channel_score با کانال نامنظم."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('channel', {
        'status': 'ok',
        'channel_type': 'irregular',
        'strength': 3
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # Irregular channel → 1.0
    assert score.price_channel_score == 1.0


# ===== Test 13: Cyclical Pattern Score =====

def test_cyclical_score_strong_phase(scorer, context_bullish):
    """تست cyclical_score با فاز قوی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Accumulation phase (confidence=0.7) → > 1.0
    assert score.cyclical_pattern_score > 1.0
    assert score.cyclical_pattern_score <= 1.15


def test_cyclical_score_weak_phase(scorer, sample_df):
    """تست cyclical_score با فاز ضعیف."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('cyclical', {
        'status': 'ok',
        'phase': 'accumulation',
        'confidence': 0.3
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # Low confidence → 1.0
    assert score.cyclical_pattern_score == 1.0


def test_cyclical_score_no_phase(scorer, sample_df):
    """تست cyclical_score بدون فاز."""
    context = AnalysisContext('BTCUSDT', '1h', sample_df)

    context.add_result('cyclical', {
        'status': 'ok',
        'phase': 'unknown',
        'confidence': 0.8
    })

    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'neutral',
        'strength': 0,
        'momentum_strength': 0,
        'macd_market_type': 'X',
        'advanced_macd_signals': []
    })

    score = scorer.calculate_score(context, 'LONG')

    # Unknown phase → 1.0
    assert score.cyclical_pattern_score == 1.0


# ===== Test 14: Final Score Calculation =====

def test_final_score_formula(scorer, context_bullish):
    """تست فرمول نهایی امتیازدهی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # Calculate expected final score manually
    expected = (
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

    # Should match (with rounding tolerance)
    assert abs(score.final_score - expected) < 0.1


def test_final_score_amplification(scorer, context_bullish):
    """تست تقویت امتیاز نهایی."""
    score = scorer.calculate_score(context_bullish, 'LONG')

    # With all positive multipliers, final should be > base
    assert score.final_score > score.base_score


def test_final_score_reduction(scorer, context_bullish):
    """تست کاهش امتیاز نهایی با سیگنال مخالف."""
    # Bullish context but SHORT direction
    score = scorer.calculate_score(context_bullish, 'SHORT')

    # trend_alignment = 0.7 should reduce score
    # Final score might still be positive but less amplified
    assert score.final_score >= 0


# ===== Test 15: Edge Cases =====

def test_error_handling(scorer, sample_df):
    """تست مدیریت خطا."""
    # Context with corrupted data
    context = AnalysisContext('BTCUSDT', '1h', pd.DataFrame())

    score = scorer.calculate_score(context, 'LONG')

    # Should return default fallback score without crashing
    # Even with empty data, gets defaults: 20+25+15 = 60
    assert score.base_score >= 50  # Minimum base score
    assert score.final_score >= 0  # Valid final score


def test_missing_optional_components(scorer, context_minimal):
    """تست بدون component‌های اختیاری."""
    score = scorer.calculate_score(context_minimal, 'LONG')

    # Symbol performance and correlation should default to 1.0
    assert score.symbol_performance_factor == 1.0
    assert score.correlation_safety_factor == 1.0


def test_direction_normalization(scorer, context_bullish):
    """تست normalization جهت."""
    # Test lowercase
    score1 = scorer.calculate_score(context_bullish, 'long')
    assert score1.final_score > 0

    # Test uppercase
    score2 = scorer.calculate_score(context_bullish, 'LONG')
    assert score2.final_score > 0

    # Should be same
    assert score1.final_score == score2.final_score


# ===== Test 16: SignalScore Dataclass =====

def test_signal_score_defaults():
    """تست مقادیر پیش‌فرض SignalScore."""
    score = SignalScore()

    assert score.base_score == 0.0
    assert score.timeframe_weight == 1.0
    assert score.trend_alignment == 1.0
    assert score.volume_confirmation == 1.0
    assert score.pattern_quality == 1.0
    assert score.confluence_score == 0.0
    assert score.symbol_performance_factor == 1.0
    assert score.correlation_safety_factor == 1.0
    assert score.macd_analysis_score == 1.0
    assert score.structure_score == 1.0
    assert score.volatility_score == 1.0
    assert score.harmonic_pattern_score == 1.0
    assert score.price_channel_score == 1.0
    assert score.cyclical_pattern_score == 1.0
    assert score.final_score == 0.0
    assert score.details == {}


def test_signal_score_custom_values():
    """تست SignalScore با مقادیر سفارشی."""
    score = SignalScore(
        base_score=75.0,
        trend_alignment=1.3,
        volume_confirmation=1.2,
        final_score=120.0
    )

    assert score.base_score == 75.0
    assert score.trend_alignment == 1.3
    assert score.volume_confirmation == 1.2
    assert score.final_score == 120.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
