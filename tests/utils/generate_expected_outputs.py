"""
Script for generating expected outputs from old system.

این اسکریپت سیستم قدیم را با داده‌های تست اجرا می‌کند و
خروجی‌ها را به عنوان expected outputs ذخیره می‌کند.

Usage:
    python tests/utils/generate_expected_outputs.py --symbol BTCUSDT --test-case default
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.comparison import save_expected_signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_data(symbol: str, timeframes: list) -> Dict[str, pd.DataFrame]:
    """
    بارگذاری داده‌های تست از CSV files.

    Args:
        symbol: نماد (مثلاً 'BTCUSDT')
        timeframes: لیست تایم‌فریم‌ها

    Returns:
        Dictionary of {timeframe: DataFrame}
    """
    test_data_path = project_root / "tests" / "data" / "sample_ohlcv"
    timeframes_data = {}

    timeframe_map = {
        '5m': '5min.csv',
        '15m': '15min.csv',
        '1h': '1hour.csv',
        '4h': '4hour.csv'
    }

    for tf in timeframes:
        filename = timeframe_map.get(tf)
        if not filename:
            logger.warning(f"Unknown timeframe: {tf}")
            continue

        filepath = test_data_path / filename

        if not filepath.exists():
            logger.error(f"Test data file not found: {filepath}")
            continue

        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            # محدود کردن به آخرین N کندل برای سرعت
            df = df.tail(500)

            timeframes_data[tf] = df
            logger.info(f"Loaded {len(df)} candles for {tf}")

        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")

    return timeframes_data


async def generate_signal_with_old_system(
    symbol: str,
    timeframes_data: Dict[str, pd.DataFrame],
    config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    تولید سیگنال با سیستم قدیم.

    Args:
        symbol: نماد
        timeframes_data: داده‌های تایم‌فریم‌ها
        config: تنظیمات

    Returns:
        Dictionary حاوی اطلاعات سیگنال یا None
    """
    try:
        # Import old system
        from Old_bot.signal_generator import SignalGenerator

        logger.info("Initializing old system SignalGenerator...")

        # Initialize old system
        signal_generator = SignalGenerator(config)

        logger.info(f"Generating signal for {symbol}...")

        # Generate signal
        signal_info = await signal_generator.analyze_symbol(symbol, timeframes_data)

        if signal_info is None:
            logger.warning(f"No signal generated for {symbol}")
            return None

        # Convert SignalInfo to dictionary
        signal_dict = {
            'symbol': signal_info.symbol,
            'timeframe': signal_info.timeframe,
            'signal_type': signal_info.signal_type,
            'direction': signal_info.direction,
            'entry_price': signal_info.entry_price,
            'stop_loss': signal_info.stop_loss,
            'take_profit': signal_info.take_profit,
            'risk_reward_ratio': signal_info.risk_reward_ratio,
            'timestamp': signal_info.timestamp.isoformat() if signal_info.timestamp else None,
            'pattern_names': signal_info.pattern_names,
            'score': {
                'final_score': signal_info.score.final_score,
                'base_score': signal_info.score.base_score,
                'timeframe_weight': signal_info.score.timeframe_weight,
                'trend_alignment': signal_info.score.trend_alignment,
                'volume_confirmation': signal_info.score.volume_confirmation,
                'pattern_quality': signal_info.score.pattern_quality,
                'confluence_score': signal_info.score.confluence_score,
                'symbol_performance_factor': signal_info.score.symbol_performance_factor,
                'correlation_safety_factor': signal_info.score.correlation_safety_factor,
                'macd_analysis_score': signal_info.score.macd_analysis_score,
                'structure_score': signal_info.score.structure_score,
                'volatility_score': signal_info.score.volatility_score,
                'harmonic_pattern_score': signal_info.score.harmonic_pattern_score,
                'price_channel_score': signal_info.score.price_channel_score,
                'cyclical_pattern_score': signal_info.score.cyclical_pattern_score,
            },
            'confirmation_timeframes': signal_info.confirmation_timeframes,
            'regime': signal_info.regime,
            'is_reversal': signal_info.is_reversal
        }

        # Add sl_method if available
        if hasattr(signal_info, 'sl_method'):
            signal_dict['sl_method'] = signal_info.sl_method
        elif signal_info.adapted_config:
            signal_dict['sl_method'] = signal_info.adapted_config.get('sl_method', 'Unknown')

        logger.info(f"✅ Signal generated: {signal_dict['direction']}, "
                   f"score={signal_dict['score']['final_score']:.2f}")

        return signal_dict

    except ImportError as e:
        logger.error(f"Failed to import old system: {e}")
        logger.error("Make sure Old_bot/ is in the project root")
        return None
    except Exception as e:
        logger.error(f"Error generating signal: {e}", exc_info=True)
        return None


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Generate expected outputs from old system'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTCUSDT',
        help='Symbol to test (default: BTCUSDT)'
    )
    parser.add_argument(
        '--test-case',
        type=str,
        default='default',
        help='Test case name (default: default)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("GENERATING EXPECTED OUTPUTS FROM OLD SYSTEM")
    logger.info("=" * 60)
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Test case: {args.test_case}")
    logger.info(f"Config: {args.config}")
    logger.info("=" * 60)

    # Load config
    try:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.info("Using default config...")
        config = {}

    # Load test data
    timeframes = ['5m', '15m', '1h', '4h']
    logger.info(f"\nLoading test data for {args.symbol}...")
    timeframes_data = load_test_data(args.symbol, timeframes)

    if not timeframes_data:
        logger.error("No test data loaded. Exiting.")
        return 1

    # Generate signal
    logger.info("\nGenerating signal with old system...")
    signal = await generate_signal_with_old_system(
        symbol=args.symbol,
        timeframes_data=timeframes_data,
        config=config
    )

    if signal is None:
        logger.error("Failed to generate signal")
        return 1

    # Save expected output
    logger.info("\nSaving expected output...")
    output_path = save_expected_signal(
        signal=signal,
        symbol=args.symbol,
        test_case=args.test_case
    )

    logger.info(f"✅ Expected output saved to: {output_path}")
    logger.info("\n" + "=" * 60)
    logger.info("SUCCESS!")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
