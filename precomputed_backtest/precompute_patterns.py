"""
Pre-compute Patterns - محاسبه و ذخیره الگوها برای همه تایم‌فریم‌ها

این اسکریپت یک بار روی همه داده‌های تاریخی اجرا می‌شود و:
1. همه الگوهای کندلی را تشخیص می‌دهد (Hammer, Engulfing, ...)
2. همه الگوهای چارتی را تشخیص می‌دهد (Head & Shoulders, Triangle, ...)
3. نتایج را در فایل‌های parquet ذخیره می‌کند

Usage:
    python precompute_patterns.py --symbol BTCUSDT --config config.yaml
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
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.csv_data_loader import CSVDataLoader
from signal_generation.shared.indicator_calculator import IndicatorCalculator
from signal_generation.analyzers.pattern_analyzer import PatternAnalyzer
from signal_generation.context import AnalysisContext

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatternPrecomputer:
    """
    کلاس محاسبه و ذخیره الگوها
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: تنظیمات از config.yaml
        """
        self.config = config
        self.backtest_config = config.get('backtest', {})

        # مسیر ذخیره فایل‌های precomputed
        self.output_dir = Path(__file__).parent / 'computed_data' / 'patterns'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # مسیر اندیکاتورهای از پیش محاسبه شده
        self.indicators_dir = Path(__file__).parent / 'computed_data' / 'indicators'

        # تایم‌فریم‌ها
        self.timeframes = config.get('data_fetching', {}).get('timeframes', ['5m', '15m', '1h', '4h'])

        # سیمبل‌ها
        self.symbols = self.backtest_config.get('symbols', ['BTCUSDT'])

        # لودر داده‌ها
        self.data_loader = CSVDataLoader(config)

        # محاسبه‌گر اندیکاتورها (نیاز الگوها)
        self.indicator_calculator = IndicatorCalculator(config)

        # آنالایزر الگوها
        self.pattern_analyzer = PatternAnalyzer(config)

        logger.info(f"PatternPrecomputer initialized")
        logger.info(f"  Symbols: {self.symbols}")
        logger.info(f"  Timeframes: {self.timeframes}")
        logger.info(f"  Output dir: {self.output_dir}")

    def load_indicators_or_compute(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        لود اندیکاتورهای از پیش محاسبه شده یا محاسبه جدید

        Args:
            symbol: نماد
            timeframe: تایم‌فریم

        Returns:
            DataFrame با اندیکاتورها
        """
        # اول سعی کن از فایل precomputed لود کنی
        indicators_file = self.indicators_dir / symbol / f"{timeframe}_indicators.parquet"
        if indicators_file.exists():
            logger.info(f"    Loading pre-computed indicators from {indicators_file}")
            return pd.read_parquet(indicators_file)

        # اگر نبود، محاسبه کن
        logger.info(f"    Computing indicators (no pre-computed file found)")
        df = self.data_loader.load_symbol_timeframe(symbol, timeframe)

        if df is None or df.empty:
            return None

        context = AnalysisContext(
            symbol=symbol,
            timeframe=timeframe,
            df=df.copy(),
            config=self.config
        )

        self.indicator_calculator.calculate_all(context)
        return context.df

    def precompute_all(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        محاسبه الگوها برای همه سیمبل‌ها و تایم‌فریم‌ها

        Returns:
            Dict[symbol][timeframe] = DataFrame with pattern columns
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
                    # 1. لود داده‌ها با اندیکاتورها
                    df = self.load_indicators_or_compute(symbol, tf)

                    if df is None or df.empty:
                        logger.warning(f"    No data for {symbol}/{tf}")
                        continue

                    logger.info(f"    Loaded {len(df)} candles")

                    # 2. ساخت Context
                    context = AnalysisContext(
                        symbol=symbol,
                        timeframe=tf,
                        df=df.copy(),
                        config=self.config
                    )

                    # 3. تشخیص همه الگوها (کندل به کندل)
                    pattern_data = self._detect_patterns_for_all_candles(context)

                    # 4. ذخیره نتیجه
                    results[symbol][tf] = pattern_data

                    # آمار
                    pattern_cols = [c for c in pattern_data.columns if c.startswith('pattern_')]
                    total_patterns = sum(pattern_data[col].sum() for col in pattern_cols)
                    logger.info(f"    Found {total_patterns} pattern occurrences in {len(pattern_cols)} pattern types")

                except Exception as e:
                    logger.error(f"    Error processing {symbol}/{tf}: {e}", exc_info=True)

        return results

    def _detect_patterns_for_all_candles(self, context: AnalysisContext) -> pd.DataFrame:
        """
        تشخیص الگوها برای هر کندل

        این متد به ازای هر کندل، الگوهایی که در آن نقطه وجود دارند را ثبت می‌کند.

        Args:
            context: کانتکست تحلیل

        Returns:
            DataFrame با ستون‌های الگو (هر ستون = یک الگو، مقدار = امتیاز الگو)
        """
        df = context.df.copy()
        n_candles = len(df)

        # دیکشنری برای ذخیره نتایج الگوها
        pattern_results = {}

        # لیست الگوها از pattern_analyzer
        all_patterns = list(self.pattern_analyzer.orchestrator.all_patterns.keys())

        # مقداردهی اولیه ستون‌های الگو
        for pattern_name in all_patterns:
            pattern_results[f'pattern_{pattern_name}'] = np.zeros(n_candles)
            pattern_results[f'pattern_{pattern_name}_direction'] = ['none'] * n_candles
            pattern_results[f'pattern_{pattern_name}_score'] = np.zeros(n_candles)

        # پردازش کندل به کندل (با پنجره مناسب)
        min_lookback = 50  # حداقل کندل برای تحلیل

        for i in range(min_lookback, n_candles):
            # ساخت DataFrame محدود تا کندل فعلی
            df_window = df.iloc[:i+1].copy()

            # ساخت context جدید با پنجره محدود
            window_context = AnalysisContext(
                symbol=context.symbol,
                timeframe=context.timeframe,
                df=df_window,
                config=context.config
            )

            # تشخیص الگوها
            try:
                analysis_result = self.pattern_analyzer.analyze(window_context)

                # ذخیره نتایج
                if analysis_result and hasattr(analysis_result, 'patterns'):
                    for pattern in analysis_result.patterns:
                        pattern_name = pattern.get('name', pattern.get('pattern_name', 'unknown'))
                        col_name = f'pattern_{pattern_name}'

                        if col_name in pattern_results:
                            pattern_results[col_name][i] = 1
                            pattern_results[f'{col_name}_direction'][i] = pattern.get('direction', 'none')
                            pattern_results[f'{col_name}_score'][i] = pattern.get('score', 0)

            except Exception as e:
                # ادامه بده حتی اگر خطا بود
                pass

            # نمایش پیشرفت
            if (i + 1) % 1000 == 0:
                logger.info(f"      Processed {i+1}/{n_candles} candles...")

        # ساخت DataFrame نهایی
        result_df = df.copy()
        for col_name, values in pattern_results.items():
            result_df[col_name] = values

        return result_df

    def save_results(self, results: Dict[str, Dict[str, pd.DataFrame]], format: str = 'parquet'):
        """
        ذخیره نتایج در فایل
        """
        for symbol, timeframes_data in results.items():
            symbol_dir = self.output_dir / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)

            for tf, df in timeframes_data.items():
                if format == 'parquet':
                    filepath = symbol_dir / f"{tf}_patterns.parquet"
                    df.to_parquet(filepath)
                elif format == 'pickle':
                    filepath = symbol_dir / f"{tf}_patterns.pkl"
                    df.to_pickle(filepath)

                logger.info(f"  Saved: {filepath} ({len(df)} rows)")

        # ذخیره metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'symbols': list(results.keys()),
            'timeframes': self.timeframes,
            'format': format,
        }

        metadata_path = self.output_dir / 'metadata.yaml'
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)


def load_config(config_path: str) -> Dict:
    """لود تنظیمات از فایل YAML"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Pre-compute patterns for backtest')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--format', type=str, default='parquet', choices=['parquet', 'pickle'],
                       help='Output format')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  PATTERN PRE-COMPUTATION")
    print("="*70 + "\n")

    # لود تنظیمات
    config_path = Path(__file__).parent.parent / args.config
    if not config_path.exists():
        config_path = Path(__file__).parent / 'configs' / 'config.yaml'

    logger.info(f"Loading config from: {config_path}")
    config = load_config(config_path)

    # ساخت precomputer و اجرا
    precomputer = PatternPrecomputer(config)

    # محاسبه الگوها
    results = precomputer.precompute_all()

    # ذخیره نتایج
    precomputer.save_results(results, format=args.format)

    print("\n" + "="*70)
    print("  PATTERN PRE-COMPUTATION COMPLETED!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
