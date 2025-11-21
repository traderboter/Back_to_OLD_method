"""
CSV Data Loader - خواننده داده‌های تاریخی از فایل‌های CSV
این ماژول وظیفه خواندن، اعتبارسنجی و مدیریت داده‌های کندل از CSV را دارد

🔥 نسخه اصلاح شده - رفع مشکلات:
1. سازگاری با تمام نسخه‌های pandas (ffill/bfill)
2. مدیریت بهتر خطاها در _fill_missing_candles
3. بهبود عملکرد و error handling
4. اضافه شدن تابع _safe_forward_fill
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class CSVDataLoader:
    """
    کلاس مسئول بارگذاری داده‌های OHLCV از فایل‌های CSV
    """

    def __init__(self, config: Dict):
        """
        مقداردهی اولیه CSVDataLoader

        Args:
            config: دیکشنری تنظیمات از بخش backtest.csv_format
        """
        self.config = config
        self.backtest_config = config.get('backtest', {})
        self.csv_config = self.backtest_config.get('csv_format', {})

        # مسیر پایه داده‌ها
        self.data_path = Path(self.backtest_config.get('data_path', './historical_data/'))

        # 🔧 اگر مسیر نسبی است، آن را نسبت به root پروژه resolve کن
        # (root پروژه = parent directory از backtest/)
        if not self.data_path.is_absolute():
            project_root = Path(__file__).parent.parent  # از csv_data_loader.py -> backtest/ -> New/
            self.data_path = (project_root / self.data_path).resolve()
            logger.info(f"Resolved relative data_path to: {self.data_path}")

        # نگاشت تایم‌فریم‌ها به نام فایل
        self.timeframe_files = self.csv_config.get('timeframe_files', {
            '5m': '5min.csv',
            '15m': '15min.csv',
            '1h': '1hour.csv',
            '4h': '4hour.csv'
        })

        # تنظیمات CSV
        self.separator = self.csv_config.get('separator', ',')
        self.encoding = self.csv_config.get('encoding', 'utf-8')
        self.date_format = self.csv_config.get('date_format', '%Y-%m-%d %H:%M:%S')

        # نام ستون‌ها
        self.columns = self.csv_config.get('columns', {
            'timestamp': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })

        # ستون‌های نادیده گرفته شده
        self.ignore_columns = self.csv_config.get('ignore_columns', ['timestamp_unix'])

        # تنظیمات اعتبارسنجی
        self.validate_data = self.csv_config.get('validate_data', True)
        self.fill_missing_data = self.csv_config.get('fill_missing_data', True)
        self.remove_duplicates = self.csv_config.get('remove_duplicates', True)
        self.check_chronological = self.csv_config.get('check_chronological_order', True)

        # کش داده‌ها در حافظه
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)

        # آمار بارگذاری
        self.stats = {
            'files_loaded': 0,
            'total_rows': 0,
            'invalid_rows_removed': 0,
            'duplicates_removed': 0,
            'missing_data_filled': 0
        }

        logger.info(f"CSVDataLoader initialized with data_path: {self.data_path}")

    def load_symbol_data(self, symbol: str, timeframe: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        بارگذاری داده‌های یک نماد و تایم‌فریم خاص

        Args:
            symbol: نام نماد (مثلاً 'BTC-USDT')
            timeframe: تایم‌فریم (مثلاً '5m', '1h', '4h')
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)

        Returns:
            DataFrame حاوی داده‌های OHLCV یا None در صورت خطا
        """
        # چک کش
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self.data_cache[symbol]:
            df = self.data_cache[symbol][cache_key].copy()
            logger.debug(f"Loaded {symbol} {timeframe} from cache")
        else:
            # ساخت مسیر فایل
            file_path = self._get_file_path(symbol, timeframe)

            if not file_path.exists():
                logger.error(f"CSV file not found: {file_path}")
                return None

            try:
                # خواندن CSV
                df = pd.read_csv(
                    file_path,
                    sep=self.separator,
                    encoding=self.encoding
                )

                self.stats['files_loaded'] += 1
                initial_rows = len(df)
                self.stats['total_rows'] += initial_rows

                # پردازش داده‌ها
                df = self._process_dataframe(df, symbol, timeframe)

                if df is None or df.empty:
                    logger.error(f"Failed to process data for {symbol} {timeframe}")
                    return None

                # محاسبه آمار
                rows_removed = initial_rows - len(df)
                if rows_removed > 0:
                    self.stats['invalid_rows_removed'] += rows_removed

                # ذخیره در کش
                self.data_cache[symbol][cache_key] = df.copy()

                logger.info(
                    f"Loaded {len(df)} candles for {symbol} {timeframe} "
                    f"from {df[self.columns['timestamp']].iloc[0]} to {df[self.columns['timestamp']].iloc[-1]}"
                )

            except Exception as e:
                logger.error(f"Error loading CSV {file_path}: {e}", exc_info=True)
                return None

        # فیلتر بر اساس بازه زمانی
        if start_date or end_date:
            df = self._filter_by_date_range(df, start_date, end_date)

        return df

    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """
        ساخت مسیر کامل فایل CSV

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            Path object مسیر فایل
        """
        # دریافت نام فایل از نگاشت
        filename = self.timeframe_files.get(timeframe)
        if not filename:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        # ساخت مسیر: data_path / symbol / filename
        file_path = self.data_path / symbol / filename

        return file_path

    def _process_dataframe(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        پردازش و اعتبارسنجی DataFrame

        Args:
            df: DataFrame خام
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            DataFrame پردازش شده یا None در صورت خطا
        """
        try:
            # حذف ستون‌های نادیده گرفته شده
            for col in self.ignore_columns:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # بررسی وجود ستون‌های ضروری
            required_cols = list(self.columns.values())
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns for {symbol} {timeframe}: {missing_cols}")
                return None

            # تبدیل ستون timestamp به datetime
            timestamp_col = self.columns['timestamp']

            try:
                df[timestamp_col] = pd.to_datetime(
                    df[timestamp_col],
                    format=self.date_format,
                    errors='coerce'
                )
            except Exception as e:
                logger.error(f"Error parsing timestamps for {symbol} {timeframe}: {e}")
                return None

            # حذف رکوردهای با timestamp نامعتبر
            invalid_timestamps = df[timestamp_col].isna().sum()
            if invalid_timestamps > 0:
                logger.warning(f"Removing {invalid_timestamps} rows with invalid timestamps for {symbol} {timeframe}")
                df = df.dropna(subset=[timestamp_col])

            if df.empty:
                logger.error(f"No valid data after timestamp parsing for {symbol} {timeframe}")
                return None

            # تبدیل ستون‌های عددی
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col_key in numeric_cols:
                col_name = self.columns[col_key]
                try:
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                except Exception as e:
                    logger.error(f"Error converting {col_name} to numeric for {symbol} {timeframe}: {e}")
                    return None

            # حذف رکوردهای با مقادیر نامعتبر
            if self.validate_data:
                df = self._validate_ohlcv_data(df, symbol, timeframe)
                if df is None or df.empty:
                    logger.error(f"No valid data after validation for {symbol} {timeframe}")
                    return None

            # حذف تکراری‌ها
            if self.remove_duplicates:
                duplicates = df.duplicated(subset=[timestamp_col]).sum()
                if duplicates > 0:
                    logger.warning(f"Removing {duplicates} duplicate rows for {symbol} {timeframe}")
                    self.stats['duplicates_removed'] += duplicates
                    df = df.drop_duplicates(subset=[timestamp_col], keep='first')

            # مرتب‌سازی بر اساس زمان
            if self.check_chronological:
                df = df.sort_values(by=timestamp_col)
                df = df.reset_index(drop=True)

            # پر کردن داده‌های گمشده
            if self.fill_missing_data:
                df = self._fill_missing_candles(df, timeframe, symbol)

            return df

        except Exception as e:
            logger.error(f"Error processing dataframe for {symbol} {timeframe}: {e}", exc_info=True)
            return None

    def _validate_ohlcv_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        اعتبارسنجی داده‌های OHLCV

        Args:
            df: DataFrame برای اعتبارسنجی
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            DataFrame معتبر
        """
        initial_len = len(df)

        # حذف رکوردهایی که مقادیر NaN دارند
        df = df.dropna(subset=[
            self.columns['open'],
            self.columns['high'],
            self.columns['low'],
            self.columns['close'],
            self.columns['volume']
        ])

        # بررسی شرط: high >= low
        invalid_hl = df[self.columns['high']] < df[self.columns['low']]
        if invalid_hl.any():
            logger.warning(f"Removing {invalid_hl.sum()} rows where high < low for {symbol} {timeframe}")
            df = df[~invalid_hl]

        # بررسی شرط: high >= open, close
        invalid_high = (
            (df[self.columns['high']] < df[self.columns['open']]) |
            (df[self.columns['high']] < df[self.columns['close']])
        )
        if invalid_high.any():
            logger.warning(f"Removing {invalid_high.sum()} rows where high < open/close for {symbol} {timeframe}")
            df = df[~invalid_high]

        # بررسی شرط: low <= open, close
        invalid_low = (
            (df[self.columns['low']] > df[self.columns['open']]) |
            (df[self.columns['low']] > df[self.columns['close']])
        )
        if invalid_low.any():
            logger.warning(f"Removing {invalid_low.sum()} rows where low > open/close for {symbol} {timeframe}")
            df = df[~invalid_low]

        # بررسی حجم منفی
        invalid_volume = df[self.columns['volume']] < 0
        if invalid_volume.any():
            logger.warning(f"Removing {invalid_volume.sum()} rows with negative volume for {symbol} {timeframe}")
            df = df[~invalid_volume]

        # بررسی قیمت‌های صفر یا منفی
        price_cols = ['open', 'high', 'low', 'close']
        for col_key in price_cols:
            col_name = self.columns[col_key]
            invalid_price = df[col_name] <= 0
            if invalid_price.any():
                logger.warning(f"Removing {invalid_price.sum()} rows with invalid {col_key} for {symbol} {timeframe}")
                df = df[~invalid_price]

        rows_removed = initial_len - len(df)
        if rows_removed > 0:
            logger.info(f"Validation removed {rows_removed} invalid rows for {symbol} {timeframe}")

        return df

    def _safe_forward_fill(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🔥 تابع امن برای forward fill که با تمام نسخه‌های pandas کار می‌کند

        Args:
            df: DataFrame با index تنظیم شده

        Returns:
            DataFrame با مقادیر پر شده
        """
        try:
            # روش 1: pandas 2.0+
            return df.ffill().bfill()
        except AttributeError:
            try:
                # روش 2: pandas 1.x
                return df.fillna(method='ffill').fillna(method='bfill')
            except (TypeError, AttributeError):
                try:
                    # روش 3: pandas قدیمی‌تر
                    return df.pad().bfill()
                except Exception:
                    # روش 4: آخرین fallback - forward fill دستی
                    logger.warning("Using manual forward fill fallback")
                    return df.fillna(method='pad').fillna(method='backfill')

    def _fill_missing_candles(self, df: pd.DataFrame, timeframe: str, symbol: str) -> pd.DataFrame:
        """
        🔥 پر کردن کندل‌های گمشده با سازگاری کامل با pandas

        Args:
            df: DataFrame
            timeframe: تایم‌فریم
            symbol: نام نماد (برای لاگ)

        Returns:
            DataFrame با کندل‌های پر شده
        """
        if len(df) == 0:
            return df

        try:
            timestamp_col = self.columns['timestamp']

            # ایجاد رنج کامل زمانی
            start_time = df[timestamp_col].iloc[0]
            end_time = df[timestamp_col].iloc[-1]

            # دریافت فرکانس pandas
            freq = self._timeframe_to_pandas_freq(timeframe)
            if freq is None:
                logger.warning(f"Cannot determine pandas frequency for timeframe: {timeframe}")
                return df

            # ایجاد DatetimeIndex کامل
            try:
                full_range = pd.date_range(
                    start=start_time,
                    end=end_time,
                    freq=freq
                )
            except Exception as e:
                logger.error(f"Error creating date range for {symbol} {timeframe}: {e}")
                return df

            # تنظیم index
            df_indexed = df.set_index(timestamp_col)

            # Reindex با رنج کامل
            df_reindexed = df_indexed.reindex(full_range)

            # شمارش مقادیر گمشده
            missing_count = df_reindexed[self.columns['close']].isna().sum()

            if missing_count > 0:
                logger.info(f"Filling {missing_count} missing candles for {symbol} {timeframe}")
                self.stats['missing_data_filled'] += missing_count

                # 🔥 استفاده از تابع امن forward fill
                df_filled = self._safe_forward_fill(df_reindexed)
            else:
                df_filled = df_reindexed

            # بازگرداندن timestamp به ستون
            df_result = df_filled.reset_index()
            df_result = df_result.rename(columns={'index': timestamp_col})

            return df_result

        except Exception as e:
            logger.error(f"Error filling missing candles for {symbol} {timeframe}: {e}", exc_info=True)
            # در صورت خطا، df اصلی را برگردان
            return df

    def _timeframe_to_timedelta(self, timeframe: str) -> Optional[timedelta]:
        """
        تبدیل رشته تایم‌فریم به timedelta

        Args:
            timeframe: رشته تایم‌فریم (مثلاً '5m', '1h', '4h')

        Returns:
            timedelta object یا None
        """
        mapping = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        return mapping.get(timeframe)

    def _timeframe_to_pandas_freq(self, timeframe: str) -> Optional[str]:
        """
        تبدیل رشته تایم‌فریم به فرکانس pandas

        Args:
            timeframe: رشته تایم‌فریم

        Returns:
            رشته فرکانس pandas یا None
        """
        mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '1h',
            '4h': '4h',
            '1d': '1D'
        }
        return mapping.get(timeframe)

    def _filter_by_date_range(self, df: pd.DataFrame,
                              start_date: Optional[datetime],
                              end_date: Optional[datetime]) -> pd.DataFrame:
        """
        فیلتر DataFrame بر اساس بازه زمانی

        Args:
            df: DataFrame
            start_date: تاریخ شروع
            end_date: تاریخ پایان

        Returns:
            DataFrame فیلتر شده
        """
        if df is None or df.empty:
            return df

        timestamp_col = self.columns['timestamp']

        if start_date:
            df = df[df[timestamp_col] >= start_date]

        if end_date:
            df = df[df[timestamp_col] <= end_date]

        return df

    def get_data_range(self, symbol: str, timeframe: str) -> Optional[Tuple[datetime, datetime]]:
        """
        دریافت بازه زمانی داده‌های موجود

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            Tuple از (start_date, end_date) یا None
        """
        df = self.load_symbol_data(symbol, timeframe)
        if df is None or df.empty:
            return None

        timestamp_col = self.columns['timestamp']
        start_date = df[timestamp_col].iloc[0]
        end_date = df[timestamp_col].iloc[-1]

        return (start_date, end_date)

    def preload_all_data(self, symbols: List[str], timeframes: List[str]) -> bool:
        """
        پیش‌بارگذاری تمام داده‌ها در کش

        Args:
            symbols: لیست نمادها
            timeframes: لیست تایم‌فریم‌ها

        Returns:
            True در صورت موفقیت
        """
        logger.info(f"Preloading data for {len(symbols)} symbols and {len(timeframes)} timeframes")

        success = True
        for symbol in symbols:
            for timeframe in timeframes:
                df = self.load_symbol_data(symbol, timeframe)
                if df is None or df.empty:
                    logger.error(f"Failed to preload {symbol} {timeframe}")
                    success = False
                else:
                    logger.debug(f"Preloaded {symbol} {timeframe}: {len(df)} candles")

        logger.info(f"Preloading complete. Stats: {self.stats}")
        return success

    def get_stats(self) -> Dict:
        """
        دریافت آمار بارگذاری

        Returns:
            دیکشنری حاوی آمار
        """
        return self.stats.copy()

    def clear_cache(self):
        """
        پاک کردن کش داده‌ها
        """
        self.data_cache.clear()
        logger.info("Data cache cleared")


class CSVDataLoader:
    """
    کلاس مسئول بارگذاری داده‌های OHLCV از فایل‌های CSV
    """

    def __init__(self, config: Dict):
        """
        مقداردهی اولیه CSVDataLoader

        Args:
            config: دیکشنری تنظیمات از بخش backtest.csv_format
        """
        self.config = config
        self.backtest_config = config.get('backtest', {})
        self.csv_config = self.backtest_config.get('csv_format', {})

        # مسیر پایه داده‌ها
        self.data_path = Path(self.backtest_config.get('data_path', './historical_data/'))

        # 🔧 اگر مسیر نسبی است، آن را نسبت به root پروژه resolve کن
        # (root پروژه = parent directory از backtest/)
        if not self.data_path.is_absolute():
            project_root = Path(__file__).parent.parent  # از csv_data_loader.py -> backtest/ -> New/
            self.data_path = (project_root / self.data_path).resolve()
            logger.info(f"Resolved relative data_path to: {self.data_path}")

        # نگاشت تایم‌فریم‌ها به نام فایل
        self.timeframe_files = self.csv_config.get('timeframe_files', {
            '5m': '5min.csv',
            '15m': '15min.csv',
            '1h': '1hour.csv',
            '4h': '4hour.csv'
        })

        # تنظیمات CSV
        self.separator = self.csv_config.get('separator', ',')
        self.encoding = self.csv_config.get('encoding', 'utf-8')
        self.date_format = self.csv_config.get('date_format', '%Y-%m-%d %H:%M:%S')

        # نام ستون‌ها
        self.columns = self.csv_config.get('columns', {
            'timestamp': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })

        # ستون‌های نادیده گرفته شده
        self.ignore_columns = self.csv_config.get('ignore_columns', ['timestamp_unix'])

        # تنظیمات اعتبارسنجی
        self.validate_data = self.csv_config.get('validate_data', True)
        self.fill_missing_data = self.csv_config.get('fill_missing_data', True)
        self.remove_duplicates = self.csv_config.get('remove_duplicates', True)
        self.check_chronological = self.csv_config.get('check_chronological_order', True)

        # کش داده‌ها در حافظه
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)

        # آمار بارگذاری
        self.stats = {
            'files_loaded': 0,
            'total_rows': 0,
            'invalid_rows_removed': 0,
            'duplicates_removed': 0,
            'missing_data_filled': 0
        }

        logger.info(f"CSVDataLoader initialized with data_path: {self.data_path}")

    def load_symbol_data(self, symbol: str, timeframe: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        بارگذاری داده‌های یک نماد و تایم‌فریم خاص

        Args:
            symbol: نام نماد (مثلاً 'BTC-USDT')
            timeframe: تایم‌فریم (مثلاً '5m', '1h', '4h')
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)

        Returns:
            DataFrame حاوی داده‌های OHLCV یا None در صورت خطا
        """
        # چک کش
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self.data_cache[symbol]:
            df = self.data_cache[symbol][cache_key].copy()
            logger.debug(f"Loaded {symbol} {timeframe} from cache")
        else:
            # ساخت مسیر فایل
            file_path = self._get_file_path(symbol, timeframe)

            if not file_path.exists():
                logger.error(f"CSV file not found: {file_path}")
                return None

            try:
                # خواندن CSV
                df = pd.read_csv(
                    file_path,
                    sep=self.separator,
                    encoding=self.encoding
                )

                self.stats['files_loaded'] += 1
                initial_rows = len(df)
                self.stats['total_rows'] += initial_rows

                # پردازش داده‌ها
                df = self._process_dataframe(df, symbol, timeframe)

                if df is None or df.empty:
                    logger.error(f"Failed to process data for {symbol} {timeframe}")
                    return None

                # محاسبه آمار
                rows_removed = initial_rows - len(df)
                if rows_removed > 0:
                    self.stats['invalid_rows_removed'] += rows_removed

                # ذخیره در کش
                self.data_cache[symbol][cache_key] = df.copy()

                logger.info(
                    f"Loaded {len(df)} candles for {symbol} {timeframe} "
                    f"from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}"
                )

            except Exception as e:
                logger.error(f"Error loading CSV {file_path}: {e}")
                return None

        # فیلتر بر اساس بازه زمانی
        if start_date or end_date:
            df = self._filter_by_date_range(df, start_date, end_date)

        return df

    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """
        ساخت مسیر کامل فایل CSV

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            Path object مسیر فایل
        """
        # دریافت نام فایل از نگاشت
        filename = self.timeframe_files.get(timeframe)
        if not filename:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        # ساخت مسیر: data_path / symbol / filename
        file_path = self.data_path / symbol / filename

        return file_path

    def _process_dataframe(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        پردازش و اعتبارسنجی DataFrame

        Args:
            df: DataFrame خام
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            DataFrame پردازش شده یا None در صورت خطا
        """
        try:
            # حذف ستون‌های نادیده گرفته شده
            for col in self.ignore_columns:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # بررسی وجود ستون‌های ضروری
            required_cols = list(self.columns.values())
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return None

            # تبدیل ستون timestamp به datetime
            timestamp_col = self.columns['timestamp']
            df[timestamp_col] = pd.to_datetime(
                df[timestamp_col],
                format=self.date_format,
                errors='coerce'
            )

            # حذف رکوردهای با timestamp نامعتبر
            invalid_timestamps = df[timestamp_col].isna().sum()
            if invalid_timestamps > 0:
                logger.warning(f"Removing {invalid_timestamps} rows with invalid timestamps")
                df = df.dropna(subset=[timestamp_col])

            # تبدیل ستون‌های عددی
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col_key in numeric_cols:
                col_name = self.columns[col_key]
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')

            # حذف رکوردهای با مقادیر نامعتبر
            if self.validate_data:
                df = self._validate_ohlcv_data(df)

            # حذف تکراری‌ها
            if self.remove_duplicates:
                duplicates = df.duplicated(subset=[timestamp_col]).sum()
                if duplicates > 0:
                    logger.warning(f"Removing {duplicates} duplicate rows")
                    self.stats['duplicates_removed'] += duplicates
                    df = df.drop_duplicates(subset=[timestamp_col], keep='first')

            # مرتب‌سازی بر اساس زمان
            if self.check_chronological:
                df = df.sort_values(by=timestamp_col)
                df = df.reset_index(drop=True)

            # پر کردن داده‌های گمشده
            if self.fill_missing_data:
                df = self._fill_missing_candles(df, timeframe)

            return df

        except Exception as e:
            logger.error(f"Error processing dataframe: {e}")
            return None

    def _validate_ohlcv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        اعتبارسنجی داده‌های OHLCV

        Args:
            df: DataFrame برای اعتبارسنجی

        Returns:
            DataFrame معتبر
        """
        initial_len = len(df)

        # حذف رکوردهایی که مقادیر NaN دارند
        df = df.dropna(subset=[
            self.columns['open'],
            self.columns['high'],
            self.columns['low'],
            self.columns['close'],
            self.columns['volume']
        ])

        # بررسی شرط: high >= low
        invalid_hl = df[self.columns['high']] < df[self.columns['low']]
        if invalid_hl.any():
            logger.warning(f"Removing {invalid_hl.sum()} rows where high < low")
            df = df[~invalid_hl]

        # بررسی شرط: high >= open, close
        invalid_high = (
            (df[self.columns['high']] < df[self.columns['open']]) |
            (df[self.columns['high']] < df[self.columns['close']])
        )
        if invalid_high.any():
            logger.warning(f"Removing {invalid_high.sum()} rows where high < open/close")
            df = df[~invalid_high]

        # بررسی شرط: low <= open, close
        invalid_low = (
            (df[self.columns['low']] > df[self.columns['open']]) |
            (df[self.columns['low']] > df[self.columns['close']])
        )
        if invalid_low.any():
            logger.warning(f"Removing {invalid_low.sum()} rows where low > open/close")
            df = df[~invalid_low]

        # بررسی حجم منفی
        invalid_volume = df[self.columns['volume']] < 0
        if invalid_volume.any():
            logger.warning(f"Removing {invalid_volume.sum()} rows with negative volume")
            df = df[~invalid_volume]

        # بررسی قیمت‌های صفر یا منفی
        price_cols = ['open', 'high', 'low', 'close']
        for col_key in price_cols:
            col_name = self.columns[col_key]
            invalid_price = df[col_name] <= 0
            if invalid_price.any():
                logger.warning(f"Removing {invalid_price.sum()} rows with invalid {col_key}")
                df = df[~invalid_price]

        rows_removed = initial_len - len(df)
        if rows_removed > 0:
            logger.info(f"Validation removed {rows_removed} invalid rows")

        return df

    def _fill_missing_candles(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        🔥 پر کردن کندل‌های گمشده با سازگاری کامل با pandas

        Args:
            df: DataFrame
            timeframe: تایم‌فریم

        Returns:
            DataFrame با کندل‌های پر شده
        """
        if len(df) == 0:
            return df

        try:
            # تبدیل تایم‌فریم به دلتای زمانی
            timeframe_delta = self._timeframe_to_timedelta(timeframe)
            if timeframe_delta is None:
                logger.warning(f"Cannot determine timedelta for timeframe: {timeframe}")
                return df

            timestamp_col = self.columns['timestamp']

            # ایجاد رنج کامل زمانی
            start_time = df[timestamp_col].iloc[0]
            end_time = df[timestamp_col].iloc[-1]

            # ایجاد DatetimeIndex کامل
            freq = self._timeframe_to_pandas_freq(timeframe)
            if freq is None:
                logger.warning(f"Cannot determine pandas frequency for timeframe: {timeframe}")
                return df

            full_range = pd.date_range(
                start=start_time,
                end=end_time,
                freq=freq
            )

            # تنظیم index
            df = df.set_index(timestamp_col)

            # Reindex با رنج کامل
            df = df.reindex(full_range)

            # شمارش مقادیر گمشده
            missing_count = df[self.columns['close']].isna().sum()

            if missing_count > 0:
                logger.info(f"Filling {missing_count} missing candles with forward fill")
                self.stats['missing_data_filled'] += missing_count

                # 🔥 پر کردن با روش سازگار با همه نسخه‌های pandas
                try:
                    # روش جدید pandas 2.0+
                    df = df.ffill().bfill()
                except AttributeError:
                    # روش قدیمی pandas < 2.0
                    try:
                        df = df.fillna(method='ffill').fillna(method='bfill')
                    except TypeError:
                        # اگر هیچکدام کار نکرد، از forward_fill استفاده کن
                        df = df.pad().bfill()

            # بازگرداندن timestamp به ستون
            df = df.reset_index()
            df = df.rename(columns={'index': timestamp_col})

            return df

        except Exception as e:
            logger.error(f"Error filling missing candles: {e}")
            # در صورت خطا، df اصلی را برگردان
            return df

    def _timeframe_to_timedelta(self, timeframe: str) -> Optional[timedelta]:
        """
        تبدیل رشته تایم‌فریم به timedelta

        Args:
            timeframe: رشته تایم‌فریم (مثلاً '5m', '1h', '4h')

        Returns:
            timedelta object یا None
        """
        mapping = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        return mapping.get(timeframe)

    def _timeframe_to_pandas_freq(self, timeframe: str) -> Optional[str]:
        """
        تبدیل رشته تایم‌فریم به فرکانس pandas

        Args:
            timeframe: رشته تایم‌فریم

        Returns:
            رشته فرکانس pandas یا None
        """
        mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '1h',
            '4h': '4h',
            '1d': '1D'
        }
        return mapping.get(timeframe)

    def _filter_by_date_range(self, df: pd.DataFrame,
                              start_date: Optional[datetime],
                              end_date: Optional[datetime]) -> pd.DataFrame:
        """
        فیلتر DataFrame بر اساس بازه زمانی

        Args:
            df: DataFrame
            start_date: تاریخ شروع
            end_date: تاریخ پایان

        Returns:
            DataFrame فیلتر شده
        """
        timestamp_col = self.columns['timestamp']

        if start_date:
            df = df[df[timestamp_col] >= start_date]

        if end_date:
            df = df[df[timestamp_col] <= end_date]

        return df

    def get_data_range(self, symbol: str, timeframe: str) -> Optional[Tuple[datetime, datetime]]:
        """
        دریافت بازه زمانی داده‌های موجود

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            Tuple از (start_date, end_date) یا None
        """
        df = self.load_symbol_data(symbol, timeframe)
        if df is None or df.empty:
            return None

        timestamp_col = self.columns['timestamp']
        start_date = df[timestamp_col].iloc[0]
        end_date = df[timestamp_col].iloc[-1]

        return (start_date, end_date)

    def preload_all_data(self, symbols: List[str], timeframes: List[str]) -> bool:
        """
        پیش‌بارگذاری تمام داده‌ها در کش

        Args:
            symbols: لیست نمادها
            timeframes: لیست تایم‌فریم‌ها

        Returns:
            True در صورت موفقیت
        """
        logger.info(f"Preloading data for {len(symbols)} symbols and {len(timeframes)} timeframes")

        success = True
        for symbol in symbols:
            for timeframe in timeframes:
                df = self.load_symbol_data(symbol, timeframe)
                if df is None or df.empty:
                    logger.error(f"Failed to preload {symbol} {timeframe}")
                    success = False
                else:
                    logger.debug(f"Preloaded {symbol} {timeframe}: {len(df)} candles")

        logger.info(f"Preloading complete. Stats: {self.stats}")
        return success

    def get_stats(self) -> Dict:
        """
        دریافت آمار بارگذاری

        Returns:
            دیکشنری حاوی آمار
        """
        return self.stats.copy()

    def clear_cache(self):
        """
        پاک کردن کش داده‌ها
        """
        self.data_cache.clear()
        logger.info("Data cache cleared")