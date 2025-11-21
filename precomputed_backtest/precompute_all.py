"""
Pre-compute All - اسکریپت اصلی برای محاسبه و ذخیره همه داده‌ها

این اسکریپت همه اندیکاتورها و الگوها را برای همه سیمبل‌ها و تایم‌فریم‌ها محاسبه می‌کند.

Usage:
    python precompute_all.py
    python precompute_all.py --indicators-only
    python precompute_all.py --patterns-only
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from precomputed_backtest.precompute_indicators import IndicatorPrecomputer, load_config
from precomputed_backtest.precompute_patterns import PatternPrecomputer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Pre-compute all data for fast backtest')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--indicators-only', action='store_true', help='Only compute indicators')
    parser.add_argument('--patterns-only', action='store_true', help='Only compute patterns')
    parser.add_argument('--format', type=str, default='parquet', help='Output format')
    args = parser.parse_args()

    start_time = datetime.now()

    print("\n" + "="*70)
    print("  PRE-COMPUTATION SYSTEM")
    print("  Fast Backtest Data Generator")
    print("="*70)

    # لود تنظیمات
    config_path = Path(__file__).parent.parent / args.config
    if not config_path.exists():
        config_path = Path(__file__).parent / 'configs' / 'config.yaml'

    logger.info(f"\nLoading config from: {config_path}")
    config = load_config(config_path)

    # === STEP 1: Indicators ===
    if not args.patterns_only:
        print("\n" + "-"*70)
        print("  STEP 1: Computing Indicators")
        print("-"*70)

        indicator_precomputer = IndicatorPrecomputer(config)
        indicator_results = indicator_precomputer.precompute_all()
        indicator_precomputer.save_results(indicator_results, format=args.format)

        print(f"\n  Indicators completed!")

    # === STEP 2: Patterns ===
    if not args.indicators_only:
        print("\n" + "-"*70)
        print("  STEP 2: Computing Patterns")
        print("-"*70)

        pattern_precomputer = PatternPrecomputer(config)
        pattern_results = pattern_precomputer.precompute_all()
        pattern_precomputer.save_results(pattern_results, format=args.format)

        print(f"\n  Patterns completed!")

    # === Summary ===
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*70)
    print("  PRE-COMPUTATION COMPLETED!")
    print("="*70)
    print(f"\n  Total time: {duration}")
    print(f"  Output directory: {Path(__file__).parent / 'computed_data'}")
    print("\n  You can now run fast backtest using:")
    print("    python fast_backtest.py")
    print()


if __name__ == '__main__':
    main()
