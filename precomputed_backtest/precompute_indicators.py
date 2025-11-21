"""
Pre-compute Indicators - محاسبه و ذخیره اندیکاتورها برای همه تایم‌فریم‌ها

این اسکریپت یک بار روی همه داده‌های تاریخی اجرا می‌شود و:
1. همه اندیکاتورها را محاسبه می‌کند (RSI, MACD, ATR, ...)
2. نتایج را در فایل‌های parquet ذخیره می‌کند
3. بعداً بکتست می‌تواند از این فایل‌ها استفاده کند (بدون محاسبه مجدد)

Usage:
    python precompute_indicators.py --symbol BTCUSDT --config config.yaml
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import yaml
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.csv_data_loader import CSVDataLoader
from signal_generation.shared.indicator_calculator import IndicatorCalculator
from signal_generation.context import AnalysisContext

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndicatorPrecomputer:
    """
    کلاس محاسبه و ذخیره اندیکاتورها
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: تنظیمات از config.yaml
        """
        self.config = config
        self.backtest_config = config.get('backtest', {})

        # مسیر ذخیره فایل‌های precomputed
        self.output_dir = Path(__file__).parent / 'computed_data' / 'indicators'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # تایم‌فریم‌ها
        self.timeframes = config.get('data_fetching', {}).get('timeframes', ['5m', '15m', '1h', '4h'])

        # سیمبل‌ها
        self.symbols = self.backtest_config.get('symbols', ['BTCUSDT'])

        # لودر داده‌ها
        self.data_loader = CSVDataLoader(config)

        # محاسبه‌گر اندیکاتورها
        self.indicator_calculator = IndicatorCalculator(config)

        logger.info(f"IndicatorPrecomputer initialized")
        logger.info(f"  Symbols: {self.symbols}")
        logger.info(f"  Timeframes: {self.timeframes}")
        logger.info(f"  Output dir: {self.output_dir}")

    def precompute_all(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        محاسبه اندیکاتورها برای همه سیمبل‌ها و تایم‌فریم‌ها

        Returns:
            Dict[symbol][timeframe] = DataFrame with indicators
        """
        results = {}

        for symbol in self.symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing symbol: {symbol}")
            logger.info(f"{'='*60}")

            results[symbol] = {}

            for tf in self.timeframes:
                logger.info(f"\n  Processing timeframe: {tf}")

                try:
                    # 1. لود داده‌های CSV
                    df = self.data_loader.load_symbol_timeframe(symbol, tf)

                    if df is None or df.empty:
                        logger.warning(f"    No data for {symbol}/{tf}")
                        continue

                    logger.info(f"    Loaded {len(df)} candles")
                    logger.info(f"    Date range: {df.index[0]} to {df.index[-1]}")

                    # 2. ساخت Context برای محاسبه اندیکاتورها
                    context = AnalysisContext(
                        symbol=symbol,
                        timeframe=tf,
                        df=df.copy(),
                        config=self.config
                    )

                    # 3. محاسبه همه اندیکاتورها
                    self.indicator_calculator.calculate_all(context)

                    # 4. ذخیره نتیجه
                    results[symbol][tf] = context.df

                    # نمایش ستون‌های اضافه شده
                    original_cols = set(df.columns)
                    new_cols = set(context.df.columns) - original_cols
                    logger.info(f"    Added {len(new_cols)} indicator columns")
                    logger.debug(f"    New columns: {sorted(new_cols)}")

                except Exception as e:
                    logger.error(f"    Error processing {symbol}/{tf}: {e}", exc_info=True)

        return results

    def save_results(self, results: Dict[str, Dict[str, pd.DataFrame]], format: str = 'parquet'):
        """
        ذخیره نتایج در فایل

        Args:
            results: نتایج از precompute_all
            format: فرمت ذخیره‌سازی ('parquet', 'pickle', 'csv')
        """
        for symbol, timeframes_data in results.items():
            symbol_dir = self.output_dir / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)

            for tf, df in timeframes_data.items():
                if format == 'parquet':
                    filepath = symbol_dir / f"{tf}_indicators.parquet"
                    df.to_parquet(filepath)
                elif format == 'pickle':
                    filepath = symbol_dir / f"{tf}_indicators.pkl"
                    df.to_pickle(filepath)
                elif format == 'csv':
                    filepath = symbol_dir / f"{tf}_indicators.csv"
                    df.to_csv(filepath)
                else:
                    raise ValueError(f"Unknown format: {format}")

                logger.info(f"  Saved: {filepath} ({len(df)} rows, {len(df.columns)} cols)")

        # ذخیره metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'symbols': list(results.keys()),
            'timeframes': self.timeframes,
            'format': format,
            'files': {}
        }

        for symbol in results:
            metadata['files'][symbol] = {}
            for tf in results[symbol]:
                df = results[symbol][tf]
                metadata['files'][symbol][tf] = {
                    'rows': len(df),
                    'columns': list(df.columns),
                    'date_start': str(df.index[0]) if len(df) > 0 else None,
                    'date_end': str(df.index[-1]) if len(df) > 0 else None
                }

        metadata_path = self.output_dir / 'metadata.yaml'
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"\nMetadata saved to: {metadata_path}")

    def load_precomputed(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        لود کردن داده‌های از پیش محاسبه شده

        Args:
            symbol: نماد
            timeframe: تایم‌فریم

        Returns:
            DataFrame با اندیکاتورها یا None
        """
        # امتحان فرمت‌های مختلف
        for ext in ['parquet', 'pkl', 'csv']:
            filepath = self.output_dir / symbol / f"{timeframe}_indicators.{ext}"
            if filepath.exists():
                if ext == 'parquet':
                    return pd.read_parquet(filepath)
                elif ext == 'pkl':
                    return pd.read_pickle(filepath)
                elif ext == 'csv':
                    return pd.read_csv(filepath, index_col=0, parse_dates=True)

        return None


def load_config(config_path: str) -> Dict:
    """لود تنظیمات از فایل YAML"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Pre-compute indicators for backtest')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--format', type=str, default='parquet', choices=['parquet', 'pickle', 'csv'],
                       help='Output format')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  INDICATOR PRE-COMPUTATION")
    print("="*70 + "\n")

    # لود تنظیمات
    config_path = Path(__file__).parent.parent / args.config
    if not config_path.exists():
        config_path = Path(__file__).parent / 'configs' / 'config.yaml'

    logger.info(f"Loading config from: {config_path}")
    config = load_config(config_path)

    # ساخت precomputer و اجرا
    precomputer = IndicatorPrecomputer(config)

    # محاسبه اندیکاتورها
    results = precomputer.precompute_all()

    # ذخیره نتایج
    precomputer.save_results(results, format=args.format)

    print("\n" + "="*70)
    print("  PRE-COMPUTATION COMPLETED!")
    print("="*70)

    # خلاصه
    total_rows = sum(
        len(df)
        for symbol_data in results.values()
        for df in symbol_data.values()
    )
    print(f"\n  Total candles processed: {total_rows:,}")
    print(f"  Output directory: {precomputer.output_dir}")
    print()


if __name__ == '__main__':
    main()
