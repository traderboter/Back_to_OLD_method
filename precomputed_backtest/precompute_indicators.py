"""
Pre-compute Indicators - محاسبه و ذخیره اندیکاتورها (نسخه مستقل)

این اسکریپت بدون وابستگی به سیستم اصلی، اندیکاتورها را محاسبه می‌کند.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import yaml
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleIndicatorCalculator:
    """محاسبه‌گر ساده اندیکاتورها (بدون وابستگی به talib)"""

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return series.rolling(window=period).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
        """Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3):
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return k, d

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        return (volume * direction).cumsum()

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average Directional Index (simplified)"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return adx

    @staticmethod
    def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
                 tenkan: int = 9, kijun: int = 26, senkou_b: int = 52):
        """
        Ichimoku Cloud
        Returns: tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span
        """
        # Tenkan-sen (Conversion Line)
        tenkan_high = high.rolling(window=tenkan).max()
        tenkan_low = low.rolling(window=tenkan).min()
        tenkan_sen = (tenkan_high + tenkan_low) / 2

        # Kijun-sen (Base Line)
        kijun_high = high.rolling(window=kijun).max()
        kijun_low = low.rolling(window=kijun).min()
        kijun_sen = (kijun_high + kijun_low) / 2

        # Senkou Span A (Leading Span A) - shifted 26 periods ahead
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)

        # Senkou Span B (Leading Span B) - shifted 26 periods ahead
        senkou_b_high = high.rolling(window=senkou_b).max()
        senkou_b_low = low.rolling(window=senkou_b).min()
        senkou_span_b = ((senkou_b_high + senkou_b_low) / 2).shift(kijun)

        # Chikou Span (Lagging Span) - shifted 26 periods back
        chikou_span = close.shift(-kijun)

        return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap

    @staticmethod
    def pivot_points(high: pd.Series, low: pd.Series, close: pd.Series):
        """
        Pivot Points (Standard)
        Returns: pivot, r1, s1, r2, s2, r3, s3
        """
        # استفاده از کندل قبلی برای محاسبه pivot
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)

        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = (2 * pivot) - prev_low
        s1 = (2 * pivot) - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)
        r3 = prev_high + 2 * (pivot - prev_low)
        s3 = prev_low - 2 * (prev_high - pivot)

        return pivot, r1, s1, r2, s2, r3, s3

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        wr = -100 * (highest_high - close) / (highest_high - lowest_low)
        return wr

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (typical_price - sma) / (0.015 * mean_deviation)
        return cci

    @staticmethod
    def fibonacci_retracement(high: pd.Series, low: pd.Series, period: int = 50):
        """
        Fibonacci Retracement Levels
        محاسبه سطوح فیبوناچی بر اساس swing high/low در پنجره مشخص
        Returns: fib_0, fib_236, fib_382, fib_500, fib_618, fib_786, fib_100
        """
        # پیدا کردن swing high و swing low در پنجره
        swing_high = high.rolling(window=period).max()
        swing_low = low.rolling(window=period).min()

        # محاسبه رنج
        price_range = swing_high - swing_low

        # سطوح فیبوناچی (از بالا به پایین)
        fib_0 = swing_high  # 0%
        fib_236 = swing_high - (price_range * 0.236)  # 23.6%
        fib_382 = swing_high - (price_range * 0.382)  # 38.2%
        fib_500 = swing_high - (price_range * 0.500)  # 50%
        fib_618 = swing_high - (price_range * 0.618)  # 61.8%
        fib_786 = swing_high - (price_range * 0.786)  # 78.6%
        fib_100 = swing_low  # 100%

        return fib_0, fib_236, fib_382, fib_500, fib_618, fib_786, fib_100

    @staticmethod
    def volume_profile(high: pd.Series, low: pd.Series, close: pd.Series,
                       volume: pd.Series, period: int = 50, num_bins: int = 10):
        """
        Volume Profile
        محاسبه پروفایل حجم و سطوح کلیدی
        Returns: poc (Point of Control), vah (Value Area High), val (Value Area Low)
        """
        n = len(close)
        poc = pd.Series(index=close.index, dtype=float)
        vah = pd.Series(index=close.index, dtype=float)
        val = pd.Series(index=close.index, dtype=float)

        for i in range(period, n):
            # داده‌های پنجره
            window_high = high.iloc[i-period:i].values
            window_low = low.iloc[i-period:i].values
            window_close = close.iloc[i-period:i].values
            window_volume = volume.iloc[i-period:i].values

            # رنج قیمت
            price_min = window_low.min()
            price_max = window_high.max()

            if price_max == price_min:
                poc.iloc[i] = price_max
                vah.iloc[i] = price_max
                val.iloc[i] = price_min
                continue

            # تقسیم به bins
            bin_edges = np.linspace(price_min, price_max, num_bins + 1)
            bin_volumes = np.zeros(num_bins)

            # محاسبه حجم در هر bin (بر اساس typical price)
            for j in range(period):
                tp = (window_high[j] + window_low[j] + window_close[j]) / 3
                bin_idx = min(int((tp - price_min) / (price_max - price_min) * num_bins), num_bins - 1)
                bin_volumes[bin_idx] += window_volume[j]

            # POC: سطح قیمتی با بیشترین حجم
            poc_bin = np.argmax(bin_volumes)
            poc.iloc[i] = (bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2

            # Value Area: 70% حجم
            total_volume = bin_volumes.sum()
            target_volume = total_volume * 0.70

            # شروع از POC و گسترش
            included = np.zeros(num_bins, dtype=bool)
            included[poc_bin] = True
            current_volume = bin_volumes[poc_bin]

            while current_volume < target_volume:
                # پیدا کردن bin‌های همسایه
                candidates = []
                for b in range(num_bins):
                    if not included[b]:
                        # بررسی همسایگی
                        if any(included[max(0, b-1):min(num_bins, b+2)]):
                            candidates.append((b, bin_volumes[b]))

                if not candidates:
                    break

                # اضافه کردن bin با بیشترین حجم
                best_bin = max(candidates, key=lambda x: x[1])[0]
                included[best_bin] = True
                current_volume += bin_volumes[best_bin]

            # VAH و VAL
            included_bins = np.where(included)[0]
            if len(included_bins) > 0:
                vah.iloc[i] = bin_edges[included_bins.max() + 1]
                val.iloc[i] = bin_edges[included_bins.min()]
            else:
                vah.iloc[i] = poc.iloc[i]
                val.iloc[i] = poc.iloc[i]

        return poc, vah, val


class SimpleCSVLoader:
    """لودر ساده CSV"""

    def __init__(self, config: Dict):
        self.config = config
        self.backtest_config = config.get('backtest', {})

        # مسیر داده‌ها (از backtest config)
        data_path = self.backtest_config.get('data_path', './historical/')
        self.data_path = Path(__file__).parent.parent / data_path

        logger.info(f"  Data path: {self.data_path}")

        # نگاشت تایم‌فریم به فایل
        csv_config = self.backtest_config.get('csv_format', {})
        self.timeframe_files = csv_config.get('timeframe_files', {
            '5m': '5min.csv',
            '15m': '15min.csv',
            '1h': '1hour.csv',
            '4h': '4hour.csv'
        })

    def load(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """لود داده‌های یک سیمبل/تایم‌فریم"""
        filename = self.timeframe_files.get(timeframe)
        if not filename:
            logger.error(f"Unknown timeframe: {timeframe}")
            return None

        filepath = self.data_path / symbol / filename
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return None

        try:
            df = pd.read_csv(filepath)

            # تبدیل timestamp به index
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)

            # حذف ستون‌های اضافی
            if 'timestamp_unix' in df.columns:
                df.drop('timestamp_unix', axis=1, inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return None


class IndicatorPrecomputer:
    """محاسبه و ذخیره اندیکاتورها"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backtest_config = config.get('backtest', {})

        # مسیر خروجی
        self.output_dir = Path(__file__).parent / 'computed_data' / 'indicators'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # تایم‌فریم‌ها و سیمبل‌ها
        self.timeframes = config.get('data_fetching', {}).get('timeframes', ['5m', '15m', '1h', '4h'])

        # سیمبل‌ها از چند جا ممکنه باشن
        self.symbols = (
            self.backtest_config.get('symbols') or
            config.get('signal_processing', {}).get('symbols') or
            ['BTC-USDT']
        )

        # لودر و محاسبه‌گر
        self.data_loader = SimpleCSVLoader(config)
        self.calculator = SimpleIndicatorCalculator()

        logger.info(f"IndicatorPrecomputer initialized")
        logger.info(f"  Symbols: {self.symbols}")
        logger.info(f"  Timeframes: {self.timeframes}")

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """محاسبه همه اندیکاتورها روی DataFrame"""
        result = df.copy()

        # EMAs
        for period in [9, 20, 50, 100, 200]:
            result[f'ema_{period}'] = self.calculator.ema(result['close'], period)

        # SMAs
        for period in [20, 50, 200]:
            result[f'sma_{period}'] = self.calculator.sma(result['close'], period)

        # RSI
        result['rsi'] = self.calculator.rsi(result['close'], 14)

        # MACD
        macd, signal, hist = self.calculator.macd(result['close'])
        result['macd'] = macd
        result['macd_signal'] = signal
        result['macd_hist'] = hist

        # ATR
        result['atr'] = self.calculator.atr(result['high'], result['low'], result['close'], 14)

        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = self.calculator.bollinger_bands(result['close'], 20, 2)
        result['bb_upper'] = bb_upper
        result['bb_mid'] = bb_mid
        result['bb_lower'] = bb_lower

        # Stochastic
        stoch_k, stoch_d = self.calculator.stochastic(result['high'], result['low'], result['close'])
        result['stoch_k'] = stoch_k
        result['stoch_d'] = stoch_d

        # OBV
        if 'volume' in result.columns:
            result['obv'] = self.calculator.obv(result['close'], result['volume'])

        # ADX
        result['adx'] = self.calculator.adx(result['high'], result['low'], result['close'], 14)

        # Ichimoku Cloud
        tenkan, kijun, senkou_a, senkou_b, chikou = self.calculator.ichimoku(
            result['high'], result['low'], result['close']
        )
        result['ichimoku_tenkan'] = tenkan
        result['ichimoku_kijun'] = kijun
        result['ichimoku_senkou_a'] = senkou_a
        result['ichimoku_senkou_b'] = senkou_b
        result['ichimoku_chikou'] = chikou

        # VWAP
        if 'volume' in result.columns:
            result['vwap'] = self.calculator.vwap(
                result['high'], result['low'], result['close'], result['volume']
            )

        # Pivot Points
        pivot, r1, s1, r2, s2, r3, s3 = self.calculator.pivot_points(
            result['high'], result['low'], result['close']
        )
        result['pivot'] = pivot
        result['pivot_r1'] = r1
        result['pivot_s1'] = s1
        result['pivot_r2'] = r2
        result['pivot_s2'] = s2
        result['pivot_r3'] = r3
        result['pivot_s3'] = s3

        # Williams %R
        result['williams_r'] = self.calculator.williams_r(
            result['high'], result['low'], result['close'], 14
        )

        # CCI
        result['cci'] = self.calculator.cci(
            result['high'], result['low'], result['close'], 20
        )

        # Fibonacci Retracement
        fib_0, fib_236, fib_382, fib_500, fib_618, fib_786, fib_100 = self.calculator.fibonacci_retracement(
            result['high'], result['low'], 50
        )
        result['fib_0'] = fib_0
        result['fib_236'] = fib_236
        result['fib_382'] = fib_382
        result['fib_500'] = fib_500
        result['fib_618'] = fib_618
        result['fib_786'] = fib_786
        result['fib_100'] = fib_100

        # Volume Profile
        if 'volume' in result.columns:
            poc, vah, val = self.calculator.volume_profile(
                result['high'], result['low'], result['close'], result['volume'], 50, 10
            )
            result['vp_poc'] = poc
            result['vp_vah'] = vah
            result['vp_val'] = val

        return result

    def precompute_all(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """محاسبه برای همه سیمبل‌ها و تایم‌فریم‌ها"""
        results = {}

        for symbol in self.symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {symbol}")
            logger.info(f"{'='*60}")

            results[symbol] = {}

            for tf in self.timeframes:
                logger.info(f"\n  Timeframe: {tf}")

                # لود داده
                df = self.data_loader.load(symbol, tf)
                if df is None or df.empty:
                    logger.warning(f"    No data for {symbol}/{tf}")
                    continue

                logger.info(f"    Loaded {len(df)} candles")
                logger.info(f"    Range: {df.index[0]} to {df.index[-1]}")

                # محاسبه اندیکاتورها
                df_with_indicators = self.calculate_indicators(df)

                # ذخیره
                results[symbol][tf] = df_with_indicators

                # آمار
                indicator_cols = [c for c in df_with_indicators.columns if c not in df.columns]
                logger.info(f"    Added {len(indicator_cols)} indicators")

        return results

    def save_results(self, results: Dict, format: str = 'parquet'):
        """ذخیره نتایج"""
        for symbol, tf_data in results.items():
            symbol_dir = self.output_dir / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)

            for tf, df in tf_data.items():
                if format == 'parquet':
                    filepath = symbol_dir / f"{tf}_indicators.parquet"
                    df.to_parquet(filepath)
                else:
                    filepath = symbol_dir / f"{tf}_indicators.csv"
                    df.to_csv(filepath)

                logger.info(f"  Saved: {filepath}")

        # Metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'symbols': list(results.keys()),
            'timeframes': self.timeframes,
            'indicators': [
                'ema_9', 'ema_20', 'ema_50', 'ema_100', 'ema_200',
                'sma_20', 'sma_50', 'sma_200',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'atr', 'bb_upper', 'bb_mid', 'bb_lower',
                'stoch_k', 'stoch_d', 'obv', 'adx',
                'ichimoku_tenkan', 'ichimoku_kijun', 'ichimoku_senkou_a',
                'ichimoku_senkou_b', 'ichimoku_chikou',
                'vwap', 'pivot', 'pivot_r1', 'pivot_s1', 'pivot_r2',
                'pivot_s2', 'pivot_r3', 'pivot_s3',
                'williams_r', 'cci',
                'fib_0', 'fib_236', 'fib_382', 'fib_500', 'fib_618', 'fib_786', 'fib_100',
                'vp_poc', 'vp_vah', 'vp_val'
            ]
        }

        with open(self.output_dir / 'metadata.yaml', 'w') as f:
            yaml.dump(metadata, f)


def load_config(config_path: str) -> Dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
    """ترکیب دو config (override روی base)"""
    result = base_config.copy()
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description='Pre-compute indicators')
    parser.add_argument('--config', type=str, default='config.yaml')
    parser.add_argument('--format', type=str, default='parquet', choices=['parquet', 'csv'])
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  INDICATOR PRE-COMPUTATION")
    print("="*70 + "\n")

    # لود config از فولدر محلی (precomputed_backtest/configs/)
    local_config_path = Path(__file__).parent / 'configs' / 'config.yaml'
    local_backtest_config_path = Path(__file__).parent / 'configs' / 'config_backtest_v2.yaml'

    logger.info(f"Loading local config: {local_config_path}")
    config = load_config(local_config_path)

    # لود backtest config و merge
    if local_backtest_config_path.exists():
        logger.info(f"Loading local backtest config: {local_backtest_config_path}")
        backtest_config = load_config(local_backtest_config_path)
        config = merge_configs(config, backtest_config)

    # اجرا
    precomputer = IndicatorPrecomputer(config)
    results = precomputer.precompute_all()
    precomputer.save_results(results, format=args.format)

    print("\n" + "="*70)
    print("  COMPLETED!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
