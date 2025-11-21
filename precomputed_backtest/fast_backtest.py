"""
Fast Backtest Engine - موتور بکتست سریع با استفاده از داده‌های از پیش محاسبه شده

این موتور به جای محاسبه مجدد اندیکاتورها و الگوها در هر گام:
- از فایل‌های parquet از پیش محاسبه شده استفاده می‌کند
- فقط در کندل‌ها پیمایش می‌کند و مقادیر را می‌خواند
- سرعت بکتست چندین برابر افزایش می‌یابد

Usage:
    python fast_backtest.py
    python fast_backtest.py --config config.yaml
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import yaml
import argparse
from tqdm import tqdm
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Trade:
    """یک معامله"""
    id: int
    symbol: str
    direction: TradeDirection
    entry_time: datetime
    entry_price: float
    quantity: float
    sl_price: float
    tp_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    exit_reason: Optional[str] = None

    # اطلاعات سیگنال
    signal_score: float = 0.0
    patterns_found: List[str] = None
    indicators_snapshot: Dict[str, float] = None


class PrecomputedDataLoader:
    """لودر داده‌های از پیش محاسبه شده"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.indicators_dir = base_dir / 'indicators'
        self.patterns_dir = base_dir / 'patterns'

        self._cache: Dict[str, pd.DataFrame] = {}

    def load_indicators(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """لود اندیکاتورها برای یک سیمبل/تایم‌فریم"""
        cache_key = f"ind_{symbol}_{timeframe}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        filepath = self.indicators_dir / symbol / f"{timeframe}_indicators.parquet"
        if not filepath.exists():
            logger.warning(f"Indicators file not found: {filepath}")
            return None

        df = pd.read_parquet(filepath)
        self._cache[cache_key] = df
        return df

    def load_patterns(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """لود الگوها برای یک سیمبل/تایم‌فریم"""
        cache_key = f"pat_{symbol}_{timeframe}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        filepath = self.patterns_dir / symbol / f"{timeframe}_patterns.parquet"
        if not filepath.exists():
            logger.warning(f"Patterns file not found: {filepath}")
            return None

        df = pd.read_parquet(filepath)
        self._cache[cache_key] = df
        return df

    def load_combined(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """لود داده‌های ترکیبی (اندیکاتورها + الگوها)"""
        indicators_df = self.load_indicators(symbol, timeframe)
        patterns_df = self.load_patterns(symbol, timeframe)

        if indicators_df is None:
            return patterns_df
        if patterns_df is None:
            return indicators_df

        # ترکیب - فقط ستون‌های الگو را اضافه کن
        pattern_cols = [c for c in patterns_df.columns if c.startswith('pattern_')]
        for col in pattern_cols:
            if col not in indicators_df.columns:
                indicators_df[col] = patterns_df[col]

        return indicators_df


class FastBacktestEngine:
    """
    موتور بکتست سریع

    این موتور از داده‌های از پیش محاسبه شده استفاده می‌کند
    و نیازی به محاسبه مجدد اندیکاتورها و الگوها ندارد.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backtest_config = config.get('backtest', {})

        # مسیر داده‌های precomputed
        self.data_dir = Path(__file__).parent / 'computed_data'
        self.data_loader = PrecomputedDataLoader(self.data_dir)

        # تنظیمات
        self.symbols = self.backtest_config.get('symbols', ['BTCUSDT'])
        self.initial_balance = self.backtest_config.get('initial_balance', 10000.0)
        self.step_timeframe = self.backtest_config.get('step_timeframe', '5m')
        self.signal_timeframe = config.get('signal_processing', {}).get('primary_timeframe', '1h')

        # تنظیمات معامله
        self.risk_per_trade = config.get('risk_management', {}).get('risk_per_trade', 0.02)
        self.min_signal_score = config.get('signal_processing', {}).get('min_score_threshold', 60)

        # وضعیت
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.open_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.trade_counter = 0

        # نتایج
        self.results = {
            'trades': [],
            'equity_curve': [],
            'statistics': {}
        }

        logger.info(f"FastBacktestEngine initialized")
        logger.info(f"  Symbols: {self.symbols}")
        logger.info(f"  Initial balance: {self.initial_balance}")

    def run(self) -> Dict:
        """اجرای بکتست سریع"""
        logger.info("\n" + "="*60)
        logger.info("Starting Fast Backtest...")
        logger.info("="*60)

        start_time = datetime.now()

        for symbol in self.symbols:
            self._run_symbol(symbol)

        end_time = datetime.now()

        # جمع‌آوری نتایج
        self._calculate_statistics()

        self.results['duration'] = str(end_time - start_time)

        return self.results

    def _run_symbol(self, symbol: str):
        """اجرای بکتست برای یک سیمبل"""
        logger.info(f"\nProcessing {symbol}...")

        # لود داده‌های step timeframe (5m)
        df_step = self.data_loader.load_combined(symbol, self.step_timeframe)
        if df_step is None:
            logger.error(f"No data for {symbol}/{self.step_timeframe}")
            return

        # لود داده‌های signal timeframe (1h)
        df_signal = self.data_loader.load_combined(symbol, self.signal_timeframe)
        if df_signal is None:
            logger.warning(f"No signal timeframe data for {symbol}/{self.signal_timeframe}")
            df_signal = df_step

        logger.info(f"  Step data: {len(df_step)} candles")
        logger.info(f"  Signal data: {len(df_signal)} candles")

        # پیمایش کندل به کندل
        pbar = tqdm(total=len(df_step), desc=f"  {symbol}", unit="candle")

        for i in range(50, len(df_step)):  # شروع از کندل 50
            current_time = df_step.index[i]
            current_row = df_step.iloc[i]

            # 1. به‌روزرسانی معاملات باز
            self._update_open_trades(current_row, current_time)

            # 2. بررسی سیگنال جدید (هر N کندل)
            if i % 12 == 0:  # هر 12 کندل 5 دقیقه‌ای = 1 ساعت
                signal = self._check_signal(df_signal, current_time, symbol)
                if signal:
                    self._open_trade(signal, current_row, current_time, symbol)

            # 3. ثبت equity
            if i % 100 == 0:
                self.results['equity_curve'].append({
                    'time': str(current_time),
                    'equity': self._calculate_equity(current_row)
                })

            pbar.update(1)
            pbar.set_postfix({
                'Balance': f"{self.balance:.0f}",
                'Trades': len(self.closed_trades)
            })

        pbar.close()

    def _check_signal(self, df_signal: pd.DataFrame, current_time: datetime, symbol: str) -> Optional[Dict]:
        """
        بررسی وجود سیگنال در زمان فعلی

        این متد از داده‌های از پیش محاسبه شده استفاده می‌کند.
        """
        # پیدا کردن نزدیک‌ترین کندل signal timeframe
        try:
            mask = df_signal.index <= current_time
            if not mask.any():
                return None

            idx = df_signal.index[mask][-1]
            row = df_signal.loc[idx]
        except:
            return None

        # بررسی الگوها
        patterns_found = []
        pattern_cols = [c for c in df_signal.columns if c.startswith('pattern_') and not c.endswith('_direction') and not c.endswith('_score')]

        for col in pattern_cols:
            if col in row and row[col] == 1:
                pattern_name = col.replace('pattern_', '')
                patterns_found.append(pattern_name)

        if not patterns_found:
            return None

        # محاسبه امتیاز ساده
        score = self._calculate_signal_score(row, patterns_found)

        if score < self.min_signal_score:
            return None

        # تعیین جهت
        direction = self._determine_direction(row, patterns_found)
        if direction is None:
            return None

        return {
            'score': score,
            'direction': direction,
            'patterns': patterns_found,
            'indicators': self._get_indicators_snapshot(row)
        }

    def _calculate_signal_score(self, row: pd.Series, patterns: List[str]) -> float:
        """محاسبه امتیاز سیگنال"""
        score = 0.0

        # امتیاز الگوها
        score += len(patterns) * 15

        # امتیاز RSI
        if 'rsi' in row:
            rsi = row['rsi']
            if rsi < 30 or rsi > 70:
                score += 10

        # امتیاز MACD
        if 'macd' in row and 'macd_signal' in row:
            if row['macd'] > row['macd_signal']:
                score += 5

        # امتیاز روند
        if 'ema_20' in row and 'ema_50' in row:
            if row['close'] > row['ema_20'] > row['ema_50']:
                score += 10
            elif row['close'] < row['ema_20'] < row['ema_50']:
                score += 10

        return min(score, 100)

    def _determine_direction(self, row: pd.Series, patterns: List[str]) -> Optional[TradeDirection]:
        """تعیین جهت معامله"""
        bullish_patterns = ['hammer', 'morning_star', 'engulfing', 'piercing_line', 'three_white_soldiers']
        bearish_patterns = ['shooting_star', 'evening_star', 'dark_cloud_cover', 'three_black_crows', 'hanging_man']

        bullish_count = sum(1 for p in patterns if any(bp in p.lower() for bp in bullish_patterns))
        bearish_count = sum(1 for p in patterns if any(bp in p.lower() for bp in bearish_patterns))

        # بررسی RSI
        if 'rsi' in row:
            if row['rsi'] < 30:
                bullish_count += 1
            elif row['rsi'] > 70:
                bearish_count += 1

        if bullish_count > bearish_count:
            return TradeDirection.LONG
        elif bearish_count > bullish_count:
            return TradeDirection.SHORT

        return None

    def _get_indicators_snapshot(self, row: pd.Series) -> Dict[str, float]:
        """گرفتن snapshot از اندیکاتورها"""
        indicators = {}
        indicator_cols = ['rsi', 'macd', 'macd_signal', 'atr', 'ema_20', 'ema_50', 'bb_upper', 'bb_lower']

        for col in indicator_cols:
            if col in row and pd.notna(row[col]):
                indicators[col] = float(row[col])

        return indicators

    def _open_trade(self, signal: Dict, current_row: pd.Series, current_time: datetime, symbol: str):
        """باز کردن معامله جدید"""
        if len(self.open_trades) >= 3:  # حداکثر 3 معامله همزمان
            return

        entry_price = current_row['close']
        atr = current_row.get('atr', entry_price * 0.02)

        # محاسبه SL و TP
        if signal['direction'] == TradeDirection.LONG:
            sl_price = entry_price - (atr * 2)
            tp_price = entry_price + (atr * 3)
        else:
            sl_price = entry_price + (atr * 2)
            tp_price = entry_price - (atr * 3)

        # محاسبه حجم
        risk_amount = self.balance * self.risk_per_trade
        sl_distance = abs(entry_price - sl_price)
        quantity = risk_amount / sl_distance if sl_distance > 0 else 0

        self.trade_counter += 1

        trade = Trade(
            id=self.trade_counter,
            symbol=symbol,
            direction=signal['direction'],
            entry_time=current_time,
            entry_price=entry_price,
            quantity=quantity,
            sl_price=sl_price,
            tp_price=tp_price,
            signal_score=signal['score'],
            patterns_found=signal['patterns'],
            indicators_snapshot=signal['indicators']
        )

        self.open_trades.append(trade)
        logger.debug(f"Opened {signal['direction'].value} trade at {entry_price:.2f}")

    def _update_open_trades(self, current_row: pd.Series, current_time: datetime):
        """به‌روزرسانی معاملات باز"""
        high = current_row['high']
        low = current_row['low']
        close = current_row['close']

        trades_to_close = []

        for trade in self.open_trades:
            exit_price = None
            exit_reason = None

            if trade.direction == TradeDirection.LONG:
                if low <= trade.sl_price:
                    exit_price = trade.sl_price
                    exit_reason = 'sl_hit'
                elif high >= trade.tp_price:
                    exit_price = trade.tp_price
                    exit_reason = 'tp_hit'
            else:  # SHORT
                if high >= trade.sl_price:
                    exit_price = trade.sl_price
                    exit_reason = 'sl_hit'
                elif low <= trade.tp_price:
                    exit_price = trade.tp_price
                    exit_reason = 'tp_hit'

            if exit_price:
                trade.exit_time = current_time
                trade.exit_price = exit_price
                trade.exit_reason = exit_reason

                # محاسبه PnL
                if trade.direction == TradeDirection.LONG:
                    trade.pnl = (exit_price - trade.entry_price) * trade.quantity
                else:
                    trade.pnl = (trade.entry_price - exit_price) * trade.quantity

                trade.pnl_percent = (trade.pnl / (trade.entry_price * trade.quantity)) * 100

                self.balance += trade.pnl
                trades_to_close.append(trade)

        for trade in trades_to_close:
            self.open_trades.remove(trade)
            self.closed_trades.append(trade)

    def _calculate_equity(self, current_row: pd.Series) -> float:
        """محاسبه equity فعلی"""
        equity = self.balance
        close = current_row['close']

        for trade in self.open_trades:
            if trade.direction == TradeDirection.LONG:
                unrealized = (close - trade.entry_price) * trade.quantity
            else:
                unrealized = (trade.entry_price - close) * trade.quantity
            equity += unrealized

        return equity

    def _calculate_statistics(self):
        """محاسبه آمار نهایی"""
        if not self.closed_trades:
            self.results['statistics'] = {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'current_equity': self.balance
            }
            return

        wins = [t for t in self.closed_trades if t.pnl > 0]
        losses = [t for t in self.closed_trades if t.pnl <= 0]

        total_pnl = sum(t.pnl for t in self.closed_trades)

        self.results['statistics'] = {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / len(self.closed_trades)) * 100 if self.closed_trades else 0,
            'total_pnl': total_pnl,
            'total_return': ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            'current_equity': self.balance,
            'avg_win': sum(t.pnl for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t.pnl for t in losses) / len(losses) if losses else 0,
        }

        # ذخیره معاملات
        self.results['trades'] = [
            {
                'id': t.id,
                'symbol': t.symbol,
                'direction': t.direction.value,
                'entry_time': str(t.entry_time),
                'entry_price': t.entry_price,
                'exit_time': str(t.exit_time),
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'pnl_percent': t.pnl_percent,
                'exit_reason': t.exit_reason,
                'signal_score': t.signal_score,
                'patterns_found': t.patterns_found
            }
            for t in self.closed_trades
        ]


def load_config(config_path: str) -> Dict:
    """لود تنظیمات"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Fast Backtest using pre-computed data')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  FAST BACKTEST ENGINE")
    print("  Using Pre-computed Indicators & Patterns")
    print("="*70 + "\n")

    # لود تنظیمات
    config_path = Path(__file__).parent.parent / args.config
    if not config_path.exists():
        config_path = Path(__file__).parent / 'configs' / 'config.yaml'

    config = load_config(config_path)

    # اجرای بکتست
    engine = FastBacktestEngine(config)
    results = engine.run()

    # نمایش نتایج
    print("\n" + "="*70)
    print("  BACKTEST RESULTS")
    print("="*70)
    stats = results['statistics']
    print(f"\n  Total Trades: {stats['total_trades']}")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    print(f"  Total Return: {stats['total_return']:.2f}%")
    print(f"  Final Equity: {stats['current_equity']:.2f} USDT")
    print(f"  Duration: {results['duration']}")
    print()


if __name__ == '__main__':
    main()
