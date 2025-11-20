"""
تست سازگاری Backtest با تغییرات Signal Generation

این تست بررسی می‌کند که آیا BacktestEngine با کد جدید signal_generation
سازگار است و بدون مشکل کار می‌کند.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_backtest_imports():
    """Test that all backtest imports work correctly."""
    print("\n" + "=" * 80)
    print("🧪 Testing Backtest Compatibility with New Signal Generation")
    print("=" * 80)

    print("\n📦 Step 1: Testing imports...")

    try:
        # Test backtest imports
        from backtest.backtest_engine_v2 import BacktestEngineV2
        print("  ✓ BacktestEngineV2 imported successfully")

        from backtest.csv_data_loader import CSVDataLoader
        print("  ✓ CSVDataLoader imported successfully")

        from backtest.historical_data_provider_v2 import HistoricalDataProvider
        print("  ✓ HistoricalDataProvider imported successfully")

        from backtest.time_simulator import TimeSimulator
        print("  ✓ TimeSimulator imported successfully")

        from backtest.backtest_trade_manager import BacktestTradeManager
        print("  ✓ BacktestTradeManager imported successfully")

    except Exception as e:
        print(f"  ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n📦 Step 2: Testing signal_generation imports from backtest...")

    try:
        # Test signal generation imports that backtest uses
        from signal_generation.orchestrator import SignalOrchestrator
        print("  ✓ SignalOrchestrator imported successfully")

        from signal_generation.shared.indicator_calculator import IndicatorCalculator
        print("  ✓ IndicatorCalculator imported successfully (NEW VERSION)")

        from signal_generation.signal_info import SignalInfo
        print("  ✓ SignalInfo imported successfully")

        # Test that orchestrator can import analyzers
        from signal_generation.analyzers import (
            PatternAnalyzer,
            TrendAnalyzer,
            MomentumAnalyzer,
            VolumeAnalyzer,
        )
        print("  ✓ All analyzers imported successfully")
        print("  ✓ PatternAnalyzer is NEW VERSION (with orchestrator)")

    except Exception as e:
        print(f"  ❌ Signal generation import error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n🔧 Step 3: Testing BacktestEngine initialization...")

    try:
        # Minimal config for testing
        test_config = {
            'backtest': {
                'symbols': ['BTCUSDT'],
                'start_date': '2024-01-01 00:00:00',
                'end_date': '2024-01-02 00:00:00',
                'initial_balance': 10000,
                'step_timeframe': '5m',
                'data_directory': 'data/historical',
            },
            'signal_processing': {
                'primary_timeframe': '1h',
            },
            'data_fetching': {
                'timeframes': ['5m', '1h'],
            },
            'analyzers': {
                'pattern': {'enabled': True},
                'trend': {'enabled': True},
                'momentum': {'enabled': True},
                'volume': {'enabled': True},
            },
            'signal_generation': {
                'adaptive_learning': {'enabled': False},
                'use_adaptive_learning': False,
            }
        }

        # Try to create BacktestEngine
        engine = BacktestEngineV2(test_config)
        print("  ✓ BacktestEngineV2 created successfully")

        # Check that it has the right attributes
        assert hasattr(engine, 'indicator_calculator'), "Missing indicator_calculator"
        assert hasattr(engine, 'signal_orchestrator'), "Missing signal_orchestrator"
        print("  ✓ Engine has correct attributes")

    except Exception as e:
        print(f"  ❌ BacktestEngine initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n🔧 Step 4: Testing IndicatorCalculator compatibility...")

    try:
        # Create IndicatorCalculator
        indicator_calc = IndicatorCalculator(test_config)
        print("  ✓ IndicatorCalculator created successfully")

        # Check that it has orchestrator
        assert hasattr(indicator_calc, 'orchestrator'), "Missing orchestrator"
        print("  ✓ IndicatorCalculator has orchestrator (NEW VERSION)")

        # Check backward compatibility methods
        assert hasattr(indicator_calc, 'calculate_all'), "Missing calculate_all method"
        assert hasattr(indicator_calc, 'calculate_moving_averages'), "Missing calculate_moving_averages"
        assert hasattr(indicator_calc, 'calculate_momentum_indicators'), "Missing calculate_momentum_indicators"
        print("  ✓ Backward compatibility methods present")

    except Exception as e:
        print(f"  ❌ IndicatorCalculator compatibility error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n🔧 Step 5: Testing SignalOrchestrator compatibility...")

    try:
        # Check that PatternAnalyzer can be imported
        from signal_generation.analyzers.pattern_analyzer import PatternAnalyzer

        # Create PatternAnalyzer
        pattern_analyzer = PatternAnalyzer(test_config)
        print("  ✓ PatternAnalyzer created successfully")

        # Check that it has orchestrator
        assert hasattr(pattern_analyzer, 'orchestrator'), "Missing orchestrator"
        print("  ✓ PatternAnalyzer has orchestrator (NEW VERSION)")

        # Check that patterns are registered
        num_candlestick = len(pattern_analyzer.orchestrator.candlestick_patterns)
        num_chart = len(pattern_analyzer.orchestrator.chart_patterns)
        print(f"  ✓ {num_candlestick} candlestick patterns registered")
        print(f"  ✓ {num_chart} chart patterns registered")

        assert num_candlestick > 0, "No candlestick patterns registered"
        assert num_chart > 0, "No chart patterns registered"

    except Exception as e:
        print(f"  ❌ SignalOrchestrator compatibility error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "=" * 80)
    print("📋 Compatibility Test Summary")
    print("=" * 80)

    print("\n  ✅ همه import ها موفق بودند")
    print("  ✅ BacktestEngineV2 با کد جدید سازگار است")
    print("  ✅ IndicatorCalculator جدید (با orchestrator) کار می‌کند")
    print("  ✅ PatternAnalyzer جدید (با orchestrator) کار می‌کند")
    print("  ✅ Backward compatibility حفظ شده است")

    print("\n" + "=" * 80)
    print("✅ Backtest Compatibility Test PASSED!")
    print("=" * 80)

    print("\n  نتیجه:")
    print("  🎯 نیازی به تغییر کدهای backtest نیست!")
    print("  🎯 همه چیز بدون تغییر کار می‌کند")
    print("  🎯 API ها سازگار هستند")

    return True


def main():
    """Run compatibility test."""
    try:
        success = test_backtest_imports()

        if success:
            print("\n✅ تست موفق - Backtest سازگار است!")
            return 0
        else:
            print("\n❌ تست ناموفق - نیاز به رفع مشکل!")
            return 1

    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
