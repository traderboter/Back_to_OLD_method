"""
Historical Data Provider - ارائه‌دهنده داده‌های تاریخی برای Backtest
این ماژول جایگزین ExchangeClient در حالت Backtest می‌شود
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from backtest.csv_data_loader import CSVDataLoader

logger = logging.getLogger(__name__)


class HistoricalDataProvider:
    """
    کلاس ارائه‌دهنده داده‌های تاریخی برای Backtest
    این کلاس جایگزین ExchangeClient می‌شود و رابط یکسانی ارائه می‌دهد
    """

    def __init__(self, config: Dict, current_time: Optional[datetime] = None):
        """
        مقداردهی اولیه HistoricalDataProvider

        Args:
            config: دیکشنری تنظیمات
            current_time: زمان فعلی شبیه‌سازی (برای محدود کردن داده‌ها)
        """
        self.config = config
        self.current_time = current_time

        # ایجاد CSVDataLoader
        self.csv_loader = CSVDataLoader(config)

        # لیست نمادها و تایم‌فریم‌ها
        self.symbols = config.get('backtest', {}).get('symbols', [])
        self.timeframes = config.get('data_fetching', {}).get('timeframes', ['5m', '15m', '1h', '4h'])

        # پیش‌بارگذاری داده‌ها اگر فعال باشد
        if config.get('backtest', {}).get('preload_all_data', True):
            self.preload_data()

        logger.info(f"HistoricalDataProvider initialized for {len(self.symbols)} symbols")

    def preload_data(self):
        """
        پیش‌بارگذاری تمام داده‌ها در کش
        """
        logger.info("Preloading historical data...")
        success = self.csv_loader.preload_all_data(self.symbols, self.timeframes)
        if success:
            logger.info("All historical data preloaded successfully")
        else:
            logger.warning("Some data failed to preload")

    def set_current_time(self, current_time: datetime):
        """
        تنظیم زمان فعلی شبیه‌سازی

        Args:
            current_time: زمان فعلی
        """
        self.current_time = current_time
        logger.debug(f"Current simulation time set to: {current_time}")

    async def fetch_ohlcv(self, symbol: str, timeframe: str,
                          limit: int = 500,
                          since: Optional[int] = None) -> Optional[List[List]]:
        """
        دریافت داده‌های OHLCV (سازگار با API صرافی)

        Args:
            symbol: نام نماد (مثلاً 'BTC-USDT')
            timeframe: تایم‌فریم (مثلاً '5m', '1h')
            limit: تعداد کندل درخواستی
            since: timestamp شروع (milliseconds)

        Returns:
            لیستی از لیست‌ها به فرمت: [timestamp, open, high, low, close, volume]
        """
        try:
            # بارگذاری داده‌های کامل از CSV
            df = self.csv_loader.load_symbol_data(symbol, timeframe)

            if df is None or df.empty:
                logger.error(f"No data available for {symbol} {timeframe}")
                return None

            # محدود کردن به زمان فعلی شبیه‌سازی
            if self.current_time:
                timestamp_col = self.csv_loader.columns['timestamp']
                df = df[df[timestamp_col] <= self.current_time]

            # اگر since داده شده، فیلتر از آن زمان به بعد
            if since:
                since_dt = datetime.fromtimestamp(since / 1000)
                timestamp_col = self.csv_loader.columns['timestamp']
                df = df[df[timestamp_col] >= since_dt]

            # محدود کردن به تعداد limit
            if len(df) > limit:
                df = df.tail(limit)

            if df.empty:
                logger.warning(f"No data found for {symbol} {timeframe} up to {self.current_time}")
                return []

            # تبدیل DataFrame به فرمت API صرافی
            result = self._dataframe_to_ohlcv_list(df)

            logger.debug(
                f"Fetched {len(result)} candles for {symbol} {timeframe} "
                f"(up to {self.current_time})"
            )

            return result

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
            return None

    def _dataframe_to_ohlcv_list(self, df: pd.DataFrame) -> List[List]:
        """
        تبدیل DataFrame به فرمت لیست OHLCV

        Args:
            df: DataFrame حاوی داده‌های کندل

        Returns:
            لیستی از [timestamp_ms, open, high, low, close, volume]
        """
        cols = self.csv_loader.columns

        result = []
        for _, row in df.iterrows():
            # تبدیل timestamp به milliseconds
            timestamp_ms = int(row[cols['timestamp']].timestamp() * 1000)

            candle = [
                timestamp_ms,
                float(row[cols['open']]),
                float(row[cols['high']]),
                float(row[cols['low']]),
                float(row[cols['close']]),
                float(row[cols['volume']])
            ]
            result.append(candle)

        return result

    async def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        دریافت قیمت فعلی نماد در زمان شبیه‌سازی

        Args:
            symbol: نام نماد

        Returns:
            قیمت close آخرین کندل
        """
        if not self.current_time:
            logger.error("Current time not set for simulation")
            return None

        try:
            # استفاده از کوچک‌ترین تایم‌فریم برای دقت بیشتر
            smallest_tf = self._get_smallest_timeframe()

            df = self.csv_loader.load_symbol_data(symbol, smallest_tf)
            if df is None or df.empty:
                return None

            # فیلتر تا زمان فعلی
            timestamp_col = self.csv_loader.columns['timestamp']
            df = df[df[timestamp_col] <= self.current_time]

            if df.empty:
                logger.warning(f"No price data for {symbol} at {self.current_time}")
                return None

            # آخرین قیمت close
            close_col = self.csv_loader.columns['close']
            price = float(df[close_col].iloc[-1])

            return price

        except Exception as e:
            logger.error(f"Error getting ticker price for {symbol}: {e}")
            return None

    def _get_smallest_timeframe(self) -> str:
        """
        دریافت کوچک‌ترین تایم‌فریم موجود

        Returns:
            رشته تایم‌فریم
        """
        tf_order = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        for tf in tf_order:
            if tf in self.timeframes:
                return tf
        return self.timeframes[0]  # fallback

    async def get_account_balance(self) -> Dict[str, float]:
        """
        دریافت موجودی حساب (در Backtest ثابت است)

        Returns:
            دیکشنری موجودی
        """
        initial_balance = self.config.get('backtest', {}).get('initial_balance', 10000.0)

        return {
            'USDT': {
                'free': initial_balance,
                'used': 0.0,
                'total': initial_balance
            }
        }

    async def create_order(self, symbol: str, order_type: str, side: str,
                           amount: float, price: Optional[float] = None,
                           params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        شبیه‌سازی ساخت سفارش (در Backtest فقط لاگ می‌کند)

        Args:
            symbol: نام نماد
            order_type: نوع سفارش ('limit', 'market')
            side: جهت ('buy', 'sell')
            amount: مقدار
            price: قیمت (برای limit order)
            params: پارامترهای اضافی

        Returns:
            دیکشنری اطلاعات سفارش
        """
        logger.info(
            f"[BACKTEST] Order simulation: {side.upper()} {amount} {symbol} "
            f"at {price if price else 'market'}"
        )

        # شبیه‌سازی پاسخ صرافی
        order = {
            'id': f"backtest_{int(datetime.now().timestamp())}",
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'price': price,
            'timestamp': int(self.current_time.timestamp() * 1000) if self.current_time else 0,
            'status': 'closed',  # در Backtest فوراً fill می‌شود
            'filled': amount,
            'remaining': 0.0
        }

        return order

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        شبیه‌سازی لغو سفارش

        Args:
            order_id: شناسه سفارش
            symbol: نام نماد

        Returns:
            True در صورت موفقیت
        """
        logger.info(f"[BACKTEST] Order cancellation simulation: {order_id}")
        return True

    async def fetch_markets(self) -> List[Dict]:
        """
        دریافت لیست بازارهای موجود

        Returns:
            لیست بازارها
        """
        markets = []
        for symbol in self.symbols:
            markets.append({
                'id': symbol.replace('-', ''),
                'symbol': symbol,
                'base': symbol.split('-')[0],
                'quote': symbol.split('-')[1],
                'active': True,
                'type': 'futures'
            })

        return markets

    def get_data_range(self, symbol: str, timeframe: str) -> Optional[tuple]:
        """
        دریافت بازه زمانی داده‌های موجود

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم

        Returns:
            (start_date, end_date) یا None
        """
        return self.csv_loader.get_data_range(symbol, timeframe)

    def get_earliest_date(self) -> Optional[datetime]:
        """
        دریافت قدیمی‌ترین تاریخ موجود در داده‌ها

        Returns:
            datetime قدیمی‌ترین داده
        """
        earliest = None

        for symbol in self.symbols:
            for timeframe in self.timeframes:
                date_range = self.get_data_range(symbol, timeframe)
                if date_range:
                    start_date = date_range[0]
                    if earliest is None or start_date < earliest:
                        earliest = start_date

        return earliest

    def get_latest_date(self) -> Optional[datetime]:
        """
        دریافت جدیدترین تاریخ موجود در داده‌ها

        Returns:
            datetime جدیدترین داده
        """
        latest = None

        for symbol in self.symbols:
            for timeframe in self.timeframes:
                date_range = self.get_data_range(symbol, timeframe)
                if date_range:
                    end_date = date_range[1]
                    if latest is None or end_date > latest:
                        latest = end_date

        return latest

    def get_candle_at_time(self, symbol: str, timeframe: str,
                           target_time: datetime) -> Optional[Dict]:
        """
        دریافت کندل در یک زمان مشخص

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم
            target_time: زمان هدف

        Returns:
            دیکشنری حاوی اطلاعات کندل یا None
        """
        try:
            df = self.csv_loader.load_symbol_data(symbol, timeframe)
            if df is None or df.empty:
                return None

            timestamp_col = self.csv_loader.columns['timestamp']

            # پیدا کردن نزدیک‌ترین کندل قبل یا برابر با target_time
            df = df[df[timestamp_col] <= target_time]

            if df.empty:
                return None

            # آخرین ردیف
            row = df.iloc[-1]
            cols = self.csv_loader.columns

            candle = {
                'timestamp': row[cols['timestamp']],
                'open': float(row[cols['open']]),
                'high': float(row[cols['high']]),
                'low': float(row[cols['low']]),
                'close': float(row[cols['close']]),
                'volume': float(row[cols['volume']])
            }

            return candle

        except Exception as e:
            logger.error(f"Error getting candle at time {target_time}: {e}")
            return None

    def validate_data_availability(self, start_date: datetime,
                                   end_date: datetime) -> Dict[str, Dict[str, bool]]:
        """
        بررسی در دسترس بودن داده‌ها برای بازه زمانی مشخص

        Args:
            start_date: تاریخ شروع
            end_date: تاریخ پایان

        Returns:
            دیکشنری نتایج بررسی
        """
        results = {}

        for symbol in self.symbols:
            results[symbol] = {}
            for timeframe in self.timeframes:
                date_range = self.get_data_range(symbol, timeframe)

                if date_range is None:
                    results[symbol][timeframe] = False
                    logger.error(f"No data available for {symbol} {timeframe}")
                else:
                    data_start, data_end = date_range

                    # بررسی اینکه بازه درخواستی در محدوده داده‌های موجود است
                    is_available = (data_start <= start_date and data_end >= end_date)

                    results[symbol][timeframe] = is_available

                    if not is_available:
                        logger.warning(
                            f"Insufficient data for {symbol} {timeframe}: "
                            f"requested {start_date} to {end_date}, "
                            f"available {data_start} to {data_end}"
                        )

        return results

    def get_statistics(self) -> Dict:
        """
        دریافت آمار بارگذاری داده‌ها

        Returns:
            دیکشنری حاوی آمار
        """
        stats = self.csv_loader.get_stats()

        # اضافه کردن اطلاعات بازه زمانی
        stats['earliest_date'] = str(self.get_earliest_date())
        stats['latest_date'] = str(self.get_latest_date())
        stats['symbols'] = self.symbols
        stats['timeframes'] = self.timeframes

        return stats

    async def close(self):
        """
        بستن اتصالات (در Backtest نیازی نیست ولی برای سازگاری با API)
        """
        logger.info("HistoricalDataProvider closed")
        self.csv_loader.clear_cache()


# Wrapper برای سازگاری با MarketDataFetcher
class BacktestMarketDataFetcher:
    """
    Wrapper برای HistoricalDataProvider که سازگار با MarketDataFetcher است
    """

    def __init__(self, historical_provider: HistoricalDataProvider):
        """
        مقداردهی اولیه

        Args:
            historical_provider: نمونه HistoricalDataProvider
        """
        self.provider = historical_provider
        self.config = historical_provider.config
        logger.info("BacktestMarketDataFetcher initialized")

    def set_current_time(self, current_time: datetime):
        """
        تنظیم زمان فعلی شبیه‌سازی

        Args:
            current_time: زمان فعلی
        """
        self.provider.set_current_time(current_time)

    async def fetch_ohlcv(self, symbol: str, timeframe: str,
                          limit: int = 500,
                          since: Optional[int] = None) -> Optional[List[List]]:
        """
        دریافت داده‌های OHLCV (wrapper برای provider)

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم
            limit: تعداد کندل درخواستی
            since: timestamp شروع (milliseconds)

        Returns:
            لیستی از لیست‌ها به فرمت: [timestamp, open, high, low, close, volume]
        """
        return await self.provider.fetch_ohlcv(symbol, timeframe, limit, since)

    async def fetch_ohlcv_multi_timeframe(self, symbol: str,
                                          timeframes: List[str],
                                          limit: int = 500) -> Dict[str, pd.DataFrame]:
        """
        دریافت داده‌های چند تایم‌فریم

        Args:
            symbol: نام نماد
            timeframes: لیست تایم‌فریم‌ها
            limit: تعداد کندل

        Returns:
            دیکشنری از {timeframe: DataFrame}
        """
        result = {}

        for tf in timeframes:
            ohlcv_list = await self.provider.fetch_ohlcv(symbol, tf, limit=limit)

            if ohlcv_list:
                # تبدیل لیست به DataFrame
                df = pd.DataFrame(
                    ohlcv_list,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )

                # تبدیل timestamp از milliseconds به datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

                result[tf] = df
            else:
                logger.warning(f"No data for {symbol} {tf}")
                result[tf] = pd.DataFrame()

        return result

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        دریافت قیمت فعلی

        Args:
            symbol: نام نماد

        Returns:
            قیمت فعلی
        """
        return await self.provider.get_ticker_price(symbol)

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        دریافت داده‌های تاریخی به فرمت DataFrame (سازگار با MarketDataFetcher)

        Args:
            symbol: نام نماد
            timeframe: تایم‌فریم
            limit: تعداد کندل درخواستی
            force_refresh: نادیده گرفته می‌شود (برای سازگاری با API)

        Returns:
            DataFrame حاوی ستون‌های: timestamp, open, high, low, close, volume
        """
        try:
            # دریافت داده‌ها از provider
            ohlcv_list = await self.provider.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )

            if not ohlcv_list:
                logger.warning(f"No data available for {symbol} {timeframe}")
                return None

            # تبدیل لیست به DataFrame
            df = pd.DataFrame(
                ohlcv_list,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            # تبدیل timestamp از milliseconds به datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            logger.debug(f"Fetched {len(df)} candles for {symbol} {timeframe}")

            return df

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol} {timeframe}: {e}")
            return None