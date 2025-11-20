"""
Tests for comparison utilities.
"""

import pytest
from tests.utils.comparison import (
    compare_signals,
    ComparisonResult,
    load_expected_signal,
    save_expected_signal
)
from pathlib import Path
import tempfile
import json


def test_compare_signals_exact_match():
    """تست مقایسه دو سیگنال یکسان."""
    signal = {
        'direction': 'long',
        'entry_price': 50000.0,
        'stop_loss': 49500.0,
        'take_profit': 51000.0,
        'risk_reward_ratio': 2.0,
        'score': {'final_score': 75.5},
        'sl_method': 'Harmonic_butterfly',
        'pattern_names': ['harmonic_butterfly', 'rsi_divergence']
    }

    result = compare_signals(signal, signal)

    assert result.matches is True
    assert len(result.differences) == 0
    assert result.passed_checks == result.total_checks


def test_compare_signals_direction_mismatch():
    """تست مقایسه با direction متفاوت."""
    old_signal = {'direction': 'long', 'stop_loss': 49500, 'take_profit': 51000}
    new_signal = {'direction': 'short', 'stop_loss': 50500, 'take_profit': 49000}

    result = compare_signals(old_signal, new_signal)

    assert result.matches is False
    assert any(d['field'] == 'direction' for d in result.differences)


def test_compare_signals_with_tolerance():
    """تست مقایسه با tolerance."""
    old_signal = {
        'direction': 'long',
        'stop_loss': 50000.0,
        'take_profit': 52000.0,
        'risk_reward_ratio': 2.0,
        'score': {'final_score': 75.0}
    }

    # 2% تفاوت - باید قبول شود با tolerance 5%
    new_signal = {
        'direction': 'long',
        'stop_loss': 51000.0,  # +2%
        'take_profit': 52500.0,  # +0.96%
        'risk_reward_ratio': 2.05,  # +2.5%
        'score': {'final_score': 76.5}  # +2%
    }

    result = compare_signals(old_signal, new_signal, tolerance=0.05)

    # باید match کند چون تفاوت‌ها کمتر از 5% هستند
    assert result.matches is True or result.passed_checks >= 5


def test_compare_signals_exceeds_tolerance():
    """تست مقایسه که از tolerance بیشتر است."""
    old_signal = {
        'direction': 'long',
        'stop_loss': 50000.0,
        'take_profit': 52000.0,
        'score': {'final_score': 75.0}
    }

    # 10% تفاوت - نباید قبول شود با tolerance 5%
    new_signal = {
        'direction': 'long',
        'stop_loss': 55000.0,  # +10%
        'take_profit': 57200.0,  # +10%
        'score': {'final_score': 82.5}  # +10%
    }

    result = compare_signals(old_signal, new_signal, tolerance=0.05)

    assert result.matches is False
    assert result.sl_diff_percentage > 5.0
    assert result.tp_diff_percentage > 5.0


def test_compare_signals_pattern_difference():
    """تست مقایسه patterns."""
    old_signal = {
        'direction': 'long',
        'pattern_names': ['harmonic_butterfly', 'rsi_divergence', 'macd_cross']
    }

    new_signal = {
        'direction': 'long',
        'pattern_names': ['harmonic_butterfly', 'volume_surge']
    }

    result = compare_signals(old_signal, new_signal)

    # باید تفاوت در patterns را تشخیص دهد
    pattern_diff = next((d for d in result.differences if d['field'] == 'pattern_names'), None)
    assert pattern_diff is not None
    assert 'rsi_divergence' in pattern_diff['missing_in_new']
    assert 'volume_surge' in pattern_diff['extra_in_new']


def test_save_and_load_expected_signal():
    """تست ذخیره و بارگذاری expected signal."""
    signal = {
        'symbol': 'BTCUSDT',
        'direction': 'long',
        'stop_loss': 49500.0,
        'take_profit': 51000.0,
        'score': {'final_score': 75.5}
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # ذخیره
        saved_path = save_expected_signal(
            signal,
            symbol='BTCUSDT',
            test_case='test1',
            base_path=base_path
        )

        assert saved_path.exists()

        # بارگذاری
        loaded_signal = load_expected_signal(
            symbol='BTCUSDT',
            test_case='test1',
            base_path=base_path
        )

        assert loaded_signal == signal


def test_load_expected_signal_not_found():
    """تست بارگذاری فایل ناموجود."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        with pytest.raises(FileNotFoundError):
            load_expected_signal(
                symbol='NONEXISTENT',
                test_case='test1',
                base_path=base_path
            )


def test_comparison_result_to_dict():
    """تست تبدیل ComparisonResult به dictionary."""
    result = ComparisonResult(
        matches=False,
        differences=[{'field': 'direction', 'old': 'long', 'new': 'short'}],
        score_diff_percentage=10.5,
        total_checks=5,
        passed_checks=3,
        failed_checks=2
    )

    result_dict = result.to_dict()

    assert result_dict['matches'] is False
    assert result_dict['score_diff_percentage'] == 10.5
    assert result_dict['pass_rate'] == "60.0%"


def test_comparison_result_str():
    """تست string representation."""
    result = ComparisonResult(
        matches=True,
        score_diff_percentage=2.5,
        sl_diff_percentage=1.5,
        tp_diff_percentage=3.0,
        total_checks=5,
        passed_checks=5,
        failed_checks=0
    )

    result_str = str(result)

    assert "✅ MATCH" in result_str
    assert "5/5" in result_str
    assert "100.0%" in result_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
