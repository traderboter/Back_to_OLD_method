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

# Import strategies and scorer
from strategies import StrategyEnsemble, SignalDirection
from fast_scorer import FastScorer, ScoringMethod

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
    signal_reason: str = ""
    strategies_triggered: List[str] = None

    # Trailing Stop
    highest_price: float = 0.0  # برای LONG
    lowest_price: float = float('inf')  # برای SHORT
    trailing_sl_price: Optional[float] = None


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

        # تنظیمات - سیمبل‌ها از چند جا
        self.symbols = (
            self.backtest_config.get('symbols') or
            config.get('signal_processing', {}).get('symbols') or
            ['BTC-USDT']
        )
        self.initial_balance = self.backtest_config.get('initial_balance', 10000.0)
        self.step_timeframe = self.backtest_config.get('step_timeframe', '5m')
        self.signal_timeframe = config.get('signal_processing', {}).get('primary_timeframe', '1h')

        # 🆕 Date filtering (start_date and end_date)
        self.start_date = None
        self.end_date = None
        if 'start_date' in self.backtest_config:
            self.start_date = pd.to_datetime(self.backtest_config['start_date'])
            logger.info(f"  Start date filter: {self.start_date}")
        if 'end_date' in self.backtest_config:
            self.end_date = pd.to_datetime(self.backtest_config['end_date'])
            logger.info(f"  End date filter: {self.end_date}")

        # 🆕 Process interval (how often to check for signals in step candles)
        self.process_interval = self.backtest_config.get('process_interval', 1)
        logger.info(f"  Process interval: every {self.process_interval} candles")

        # تنظیمات معامله
        self.risk_per_trade = config.get('risk_management', {}).get('risk_per_trade', 0.02)
        self.min_signal_score = 30  # آستانه پایین‌تر برای تولید سیگنال بیشتر

        # تنظیمات واقعی‌تر
        self.commission_rate = self.backtest_config.get('commission_rate', 0.001)  # 0.1% کمیسیون
        self.slippage_rate = self.backtest_config.get('slippage_rate', 0.0005)  # 0.05% slippage

        # Trailing Stop تنظیمات
        self.trailing_stop_enabled = self.backtest_config.get('trailing_stop_enabled', True)
        self.trailing_stop_activation = self.backtest_config.get('trailing_stop_activation', 1.5)  # فعال شدن بعد از 1.5R سود
        self.trailing_stop_distance = self.backtest_config.get('trailing_stop_distance', 1.0)  # فاصله 1R از قیمت

        # tracking برای drawdown دقیق
        self.peak_equity = self.initial_balance
        self.max_drawdown = 0.0
        self.drawdown_history = []

        # === روش امتیازدهی: new, old, hybrid, strategy ===
        self.scoring_method = self.backtest_config.get('scoring_method', 'strategy')

        if self.scoring_method in ['new', 'old', 'hybrid']:
            # استفاده از FastScorer (سه روش امتیازدهی)
            self.fast_scorer = FastScorer(method=self.scoring_method, config=config)
            self.min_signal_score = self.fast_scorer.min_signal_score
            self.use_strategy_ensemble = False
            logger.info(f"Using FastScorer with method: {self.scoring_method}")
        else:
            # استفاده از StrategyEnsemble (روش قبلی)
            self.strategy_ensemble = StrategyEnsemble({
                'voting_threshold': 0.5,
                'min_agreement': 2,
                'min_score': self.min_signal_score
            })
            self.use_strategy_ensemble = True
            logger.info("Using StrategyEnsemble for signal generation")

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
            'statistics': {},
            'per_symbol': {}  # آمار هر سیمبل جداگانه
        }

        logger.info(f"FastBacktestEngine initialized")
        logger.info(f"  Symbols: {self.symbols}")
        logger.info(f"  Initial balance: {self.initial_balance}")
        logger.info(f"  Scoring method: {self.scoring_method}")
        logger.info(f"  Min signal score: {self.min_signal_score}")
        logger.info(f"  Trailing Stop: {'Enabled' if self.trailing_stop_enabled else 'Disabled'}")

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

            # 🆕 Date filtering: Skip candles outside date range
            if self.start_date and current_time < self.start_date:
                continue
            if self.end_date and current_time > self.end_date:
                break  # No more candles after end_date

            # 1. به‌روزرسانی معاملات باز
            self._update_open_trades(current_row, current_time)

            # 2. بررسی سیگنال جدید (با رعایت process_interval)
            # 🆕 Only check signal every N candles (process_interval)
            if (i - 50) % self.process_interval == 0:
                signal = self._check_signal(df_signal, current_time, symbol)
                if signal:
                    # 🆕 Deduplication: Don't open if already have open trade for this symbol
                    open_for_symbol = [t for t in self.open_trades if t.symbol == symbol]
                    max_trades_per_symbol = self.config.get('risk_management', {}).get('max_trades_per_symbol', 1)

                    if len(open_for_symbol) < max_trades_per_symbol:
                        self._open_trade(signal, current_row, current_time, symbol)

            # 3. ثبت equity و محاسبه drawdown (هر 10 کندل برای دقت بیشتر)
            if i % 10 == 0:
                current_equity = self._calculate_equity(current_row)

                # به‌روزرسانی peak و drawdown
                if current_equity > self.peak_equity:
                    self.peak_equity = current_equity

                if self.peak_equity > 0:
                    current_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100
                    if current_drawdown > self.max_drawdown:
                        self.max_drawdown = current_drawdown

                # ثبت در equity curve (هر 50 کندل برای کاهش حجم داده)
                if i % 50 == 0:
                    self.results['equity_curve'].append({
                        'time': str(current_time),
                        'equity': current_equity,
                        'drawdown': current_drawdown if self.peak_equity > 0 else 0
                    })

            pbar.update(1)
            pbar.set_postfix({
                'Balance': f"{self.balance:.0f}",
                'Trades': len(self.closed_trades)
            })

        pbar.close()

        # ثبت آمار این سیمبل
        symbol_trades = [t for t in self.closed_trades if t.symbol == symbol]
        if symbol_trades:
            symbol_wins = [t for t in symbol_trades if t.pnl > 0]
            symbol_losses = [t for t in symbol_trades if t.pnl <= 0]
            self.results['per_symbol'][symbol] = {
                'total_trades': len(symbol_trades),
                'winning_trades': len(symbol_wins),
                'losing_trades': len(symbol_losses),
                'win_rate': (len(symbol_wins) / len(symbol_trades)) * 100,
                'total_pnl': sum(t.pnl for t in symbol_trades),
                'avg_pnl': sum(t.pnl for t in symbol_trades) / len(symbol_trades),
                'trailing_sl_count': len([t for t in symbol_trades if t.exit_reason == 'trailing_sl']),
            }
            logger.info(f"  {symbol}: {len(symbol_trades)} trades, {self.results['per_symbol'][symbol]['win_rate']:.1f}% win rate")

    def _check_signal(self, df_signal: pd.DataFrame, current_time: datetime, symbol: str) -> Optional[Dict]:
        """
        بررسی وجود سیگنال در زمان فعلی

        بر اساس scoring_method از یکی از دو روش استفاده می‌شود:
        - strategy: استفاده از StrategyEnsemble
        - new/old/hybrid: استفاده از FastScorer
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

        if self.use_strategy_ensemble:
            # === روش Strategy Ensemble ===
            direction, score, reason, details = self.strategy_ensemble.analyze(row)

            if direction is None or score < self.min_signal_score:
                return None

            if direction == SignalDirection.LONG:
                trade_direction = TradeDirection.LONG
            elif direction == SignalDirection.SHORT:
                trade_direction = TradeDirection.SHORT
            else:
                return None

            strategies = details.get('long_strategies', []) if direction == SignalDirection.LONG else details.get('short_strategies', [])

        else:
            # === روش FastScorer (NEW/OLD/HYBRID) ===
            # ابتدا جهت را تعیین می‌کنیم
            direction = self._determine_direction_for_scorer(row)
            if direction is None:
                return None

            # محاسبه امتیاز با FastScorer
            score_result = self.fast_scorer.calculate_score(row, direction)
            score = score_result.final_score

            if not self.fast_scorer.is_valid_signal(score):
                return None

            trade_direction = TradeDirection.LONG if direction == 'LONG' else TradeDirection.SHORT
            reason = f"{self.scoring_method.upper()} Score: {score:.1f}"
            strategies = [self.scoring_method]

        # جمع‌آوری الگوهای پیدا شده
        patterns_found = []
        pattern_cols = [c for c in df_signal.columns if c.startswith('pattern_') and not c.endswith('_direction') and not c.endswith('_score')]
        for col in pattern_cols:
            if col in row and row[col] == 1:
                patterns_found.append(col.replace('pattern_', ''))

        return {
            'score': score,
            'direction': trade_direction,
            'patterns': patterns_found,
            'indicators': self._get_indicators_snapshot(row),
            'reason': reason,
            'strategies': strategies
        }

    def _determine_direction_for_scorer(self, row: pd.Series) -> Optional[str]:
        """
        تعیین جهت سیگنال برای FastScorer

        این متد بر اساس اندیکاتورها جهت سیگنال را تعیین می‌کند.
        """
        bullish_score = 0
        bearish_score = 0

        # 1. RSI
        rsi = row.get('rsi', 50)
        if pd.notna(rsi):
            if rsi < 35:
                bullish_score += 2  # Oversold
            elif rsi < 45:
                bullish_score += 1
            elif rsi > 65:
                bearish_score += 2  # Overbought
            elif rsi > 55:
                bearish_score += 1

        # 2. MACD
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        if pd.notna(macd) and pd.notna(macd_signal):
            if macd > macd_signal:
                bullish_score += 1
            elif macd < macd_signal:
                bearish_score += 1

        # 3. EMA Trend
        close = row.get('close', 0)
        ema_20 = row.get('ema_20', 0)
        ema_50 = row.get('ema_50', 0)
        if pd.notna(close) and pd.notna(ema_20) and pd.notna(ema_50):
            if close > ema_20 > ema_50:
                bullish_score += 2
            elif close > ema_20:
                bullish_score += 1
            elif close < ema_20 < ema_50:
                bearish_score += 2
            elif close < ema_20:
                bearish_score += 1

        # 4. Patterns
        bullish_patterns = ['pattern_hammer', 'pattern_morning_star', 'pattern_bullish_engulfing', 'pattern_piercing_line']
        bearish_patterns = ['pattern_shooting_star', 'pattern_evening_star', 'pattern_bearish_engulfing', 'pattern_dark_cloud_cover']

        for p in bullish_patterns:
            if p in row and row[p] == 1:
                bullish_score += 2
        for p in bearish_patterns:
            if p in row and row[p] == 1:
                bearish_score += 2

        # تصمیم نهایی
        if bullish_score > bearish_score and bullish_score >= 3:
            return 'LONG'
        elif bearish_score > bullish_score and bearish_score >= 3:
            return 'SHORT'

        return None

    def _calculate_signal_score(self, row: pd.Series, patterns: List[str]) -> float:
        """محاسبه امتیاز سیگنال"""
        score = 0.0

        # امتیاز الگوها - هر الگو 20 امتیاز
        score += len(patterns) * 20

        # امتیاز RSI
        if 'rsi' in row and pd.notna(row['rsi']):
            rsi = row['rsi']
            if rsi < 30:
                score += 15  # oversold - bullish
            elif rsi > 70:
                score += 15  # overbought - bearish
            elif 40 < rsi < 60:
                score += 5   # neutral zone

        # امتیاز MACD
        if 'macd' in row and 'macd_signal' in row:
            if pd.notna(row['macd']) and pd.notna(row['macd_signal']):
                if abs(row['macd'] - row['macd_signal']) > 0:
                    score += 10

        # امتیاز روند (EMA alignment)
        if 'ema_20' in row and 'ema_50' in row and 'close' in row:
            if pd.notna(row['ema_20']) and pd.notna(row['ema_50']):
                if row['close'] > row['ema_20'] > row['ema_50']:
                    score += 15  # uptrend
                elif row['close'] < row['ema_20'] < row['ema_50']:
                    score += 15  # downtrend

        return min(score, 100)

    def _determine_direction(self, row: pd.Series, patterns: List[str]) -> Optional[TradeDirection]:
        """تعیین جهت معامله بر اساس الگوها و اندیکاتورها"""
        bullish_patterns = ['hammer', 'morning_star', 'piercing_line', 'three_white_soldiers', 'harami']
        bearish_patterns = ['shooting_star', 'evening_star', 'dark_cloud_cover', 'three_black_crows']

        bullish_score = 0
        bearish_score = 0

        # بررسی الگوها
        for p in patterns:
            p_lower = p.lower()
            if any(bp in p_lower for bp in bullish_patterns):
                bullish_score += 2
            elif any(bp in p_lower for bp in bearish_patterns):
                bearish_score += 2
            elif 'engulfing' in p_lower:
                # engulfing می‌تواند هر دو جهت باشد - بررسی با کندل
                if row['close'] > row['open']:
                    bullish_score += 2
                else:
                    bearish_score += 2
            elif 'doji' in p_lower:
                # doji نشان‌دهنده بلاتکلیفی - بررسی روند قبلی
                pass

        # بررسی RSI
        if 'rsi' in row and pd.notna(row['rsi']):
            if row['rsi'] < 30:
                bullish_score += 1  # oversold
            elif row['rsi'] > 70:
                bearish_score += 1  # overbought

        # بررسی MACD
        if 'macd' in row and 'macd_signal' in row:
            if pd.notna(row['macd']) and pd.notna(row['macd_signal']):
                if row['macd'] > row['macd_signal']:
                    bullish_score += 1
                else:
                    bearish_score += 1

        # بررسی روند EMA
        if 'ema_20' in row and 'ema_50' in row:
            if pd.notna(row['ema_20']) and pd.notna(row['ema_50']):
                if row['close'] > row['ema_20'] > row['ema_50']:
                    bullish_score += 1
                elif row['close'] < row['ema_20'] < row['ema_50']:
                    bearish_score += 1

        # تصمیم نهایی
        if bullish_score > bearish_score and bullish_score >= 2:
            return TradeDirection.LONG
        elif bearish_score > bullish_score and bearish_score >= 2:
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

        base_price = current_row['close']

        # اعمال slippage (قیمت بدتر برای ورود)
        if signal['direction'] == TradeDirection.LONG:
            entry_price = base_price * (1 + self.slippage_rate)  # خرید با قیمت بالاتر
        else:
            entry_price = base_price * (1 - self.slippage_rate)  # فروش با قیمت پایین‌تر

        atr = current_row.get('atr', entry_price * 0.02)

        # اگر ATR نامعتبر بود
        if pd.isna(atr) or atr <= 0:
            atr = entry_price * 0.02

        # محاسبه SL و TP
        if signal['direction'] == TradeDirection.LONG:
            sl_price = entry_price - (atr * 2)
            tp_price = entry_price + (atr * 3)
        else:
            sl_price = entry_price + (atr * 2)
            tp_price = entry_price - (atr * 3)

        # محاسبه حجم با محدودیت‌های واقعی
        risk_amount = self.balance * self.risk_per_trade  # 2% risk
        sl_distance = abs(entry_price - sl_price)

        if sl_distance <= 0:
            return

        # حجم بر اساس ریسک
        quantity = risk_amount / sl_distance

        # محدودیت حداکثر حجم معامله (10% از بالانس)
        max_position_value = self.balance * 0.10
        max_quantity = max_position_value / entry_price
        quantity = min(quantity, max_quantity)

        # حداقل حجم معامله
        min_quantity = 0.001  # برای BTC
        if quantity < min_quantity:
            return

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
            indicators_snapshot=signal['indicators'],
            signal_reason=signal.get('reason', ''),
            strategies_triggered=signal.get('strategies', []),
            highest_price=entry_price,  # برای trailing stop
            lowest_price=entry_price,   # برای trailing stop
        )

        self.open_trades.append(trade)
        strategies_str = ', '.join(signal.get('strategies', []))
        logger.debug(f"Opened {signal['direction'].value} trade at {entry_price:.2f} | Strategies: {strategies_str}")

    def _update_open_trades(self, current_row: pd.Series, current_time: datetime):
        """به‌روزرسانی معاملات باز"""
        high = current_row['high']
        low = current_row['low']
        close = current_row['close']

        trades_to_close = []

        for trade in self.open_trades:
            exit_price = None
            exit_reason = None

            # محاسبه R (فاصله SL اولیه)
            initial_sl_distance = abs(trade.entry_price - trade.sl_price)

            # به‌روزرسانی Trailing Stop
            if self.trailing_stop_enabled and initial_sl_distance > 0:
                if trade.direction == TradeDirection.LONG:
                    # به‌روزرسانی highest price
                    if high > trade.highest_price:
                        trade.highest_price = high

                    # محاسبه سود فعلی به R
                    current_profit_r = (trade.highest_price - trade.entry_price) / initial_sl_distance

                    # اگر سود به حد فعال‌سازی رسید
                    if current_profit_r >= self.trailing_stop_activation:
                        new_trailing_sl = trade.highest_price - (initial_sl_distance * self.trailing_stop_distance)
                        # فقط اگر trailing SL بالاتر از SL فعلی باشد
                        if trade.trailing_sl_price is None or new_trailing_sl > trade.trailing_sl_price:
                            trade.trailing_sl_price = new_trailing_sl

                else:  # SHORT
                    # به‌روزرسانی lowest price
                    if low < trade.lowest_price:
                        trade.lowest_price = low

                    # محاسبه سود فعلی به R
                    current_profit_r = (trade.entry_price - trade.lowest_price) / initial_sl_distance

                    # اگر سود به حد فعال‌سازی رسید
                    if current_profit_r >= self.trailing_stop_activation:
                        new_trailing_sl = trade.lowest_price + (initial_sl_distance * self.trailing_stop_distance)
                        # فقط اگر trailing SL پایین‌تر از SL فعلی باشد
                        if trade.trailing_sl_price is None or new_trailing_sl < trade.trailing_sl_price:
                            trade.trailing_sl_price = new_trailing_sl

            # تعیین SL فعال (trailing یا اصلی)
            active_sl = trade.trailing_sl_price if trade.trailing_sl_price else trade.sl_price

            if trade.direction == TradeDirection.LONG:
                if low <= active_sl:
                    exit_price = active_sl
                    exit_reason = 'trailing_sl' if trade.trailing_sl_price else 'sl_hit'
                elif high >= trade.tp_price:
                    exit_price = trade.tp_price
                    exit_reason = 'tp_hit'
            else:  # SHORT
                if high >= active_sl:
                    exit_price = active_sl
                    exit_reason = 'trailing_sl' if trade.trailing_sl_price else 'sl_hit'
                elif low <= trade.tp_price:
                    exit_price = trade.tp_price
                    exit_reason = 'tp_hit'

            if exit_price:
                trade.exit_time = current_time

                # اعمال slippage بر قیمت خروج (قیمت بدتر)
                if trade.direction == TradeDirection.LONG:
                    # برای LONG، فروش با قیمت پایین‌تر
                    actual_exit_price = exit_price * (1 - self.slippage_rate)
                else:
                    # برای SHORT، خرید با قیمت بالاتر
                    actual_exit_price = exit_price * (1 + self.slippage_rate)

                trade.exit_price = actual_exit_price
                trade.exit_reason = exit_reason

                # محاسبه PnL خام
                if trade.direction == TradeDirection.LONG:
                    gross_pnl = (actual_exit_price - trade.entry_price) * trade.quantity
                else:
                    gross_pnl = (trade.entry_price - actual_exit_price) * trade.quantity

                # محاسبه کمیسیون (برای ورود و خروج)
                entry_commission = trade.entry_price * trade.quantity * self.commission_rate
                exit_commission = actual_exit_price * trade.quantity * self.commission_rate
                total_commission = entry_commission + exit_commission

                # PnL خالص (بعد از کسر کمیسیون)
                trade.pnl = gross_pnl - total_commission
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
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0

        # Profit Factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # استفاده از max_drawdown ردیابی شده (دقیق‌تر)
        max_drawdown = self.max_drawdown

        # محاسبه کل کمیسیون پرداخت شده
        total_commission = sum(
            (t.entry_price * t.quantity * self.commission_rate * 2)  # ورود + خروج
            for t in self.closed_trades
        )

        self.results['statistics'] = {
            'scoring_method': self.scoring_method,
            'total_trades': len(self.closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / len(self.closed_trades)) * 100 if self.closed_trades else 0,
            'total_pnl': total_pnl,
            'total_return': ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            'current_equity': self.balance,
            'avg_win': sum(t.pnl for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t.pnl for t in losses) / len(losses) if losses else 0,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'total_commission': total_commission,
            'commission_rate': self.commission_rate * 100,  # درصد
            'slippage_rate': self.slippage_rate * 100,  # درصد
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
                'patterns_found': t.patterns_found,
                'signal_reason': t.signal_reason,
                'strategies_triggered': t.strategies_triggered
            }
            for t in self.closed_trades
        ]

    def save_report(self, output_path: str = None):
        """ذخیره گزارش بکتست"""
        if output_path is None:
            output_path = Path(__file__).parent / 'reports'
            output_path.mkdir(exist_ok=True)
            output_path = output_path / f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        stats = self.results['statistics']

        report = f"""# گزارش بکتست
تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## خلاصه عملکرد

| معیار | مقدار |
|-------|-------|
| سرمایه اولیه | {self.initial_balance:,.2f} USDT |
| سرمایه نهایی | {stats['current_equity']:,.2f} USDT |
| بازده کل | {stats['total_return']:.2f}% |
| سود/زیان خالص | {stats['total_pnl']:,.2f} USDT |

## آمار معاملات

| معیار | مقدار |
|-------|-------|
| تعداد کل معاملات | {stats['total_trades']} |
| معاملات برنده | {stats['winning_trades']} |
| معاملات بازنده | {stats['losing_trades']} |
| نرخ برد | {stats['win_rate']:.1f}% |
| میانگین سود | {stats['avg_win']:.2f} USDT |
| میانگین ضرر | {stats['avg_loss']:.2f} USDT |
| Profit Factor | {stats['profit_factor']:.2f} |
| حداکثر Drawdown | {stats['max_drawdown']:.2f}% |

## توزیع معاملات

- سود ناخالص: {stats['gross_profit']:,.2f} USDT
- ضرر ناخالص: {stats['gross_loss']:,.2f} USDT

## نمونه معاملات (10 معامله اول)

| # | جهت | ورود | خروج | سود/زیان | دلیل |
|---|-----|------|------|----------|------|
"""
        for t in self.results['trades'][:10]:
            report += f"| {t['id']} | {t['direction']} | {t['entry_price']:.2f} | {t['exit_price']:.2f} | {t['pnl']:.2f} | {t['exit_reason']} |\n"

        report += f"\n---\n*مدت اجرا: {self.results.get('duration', 'N/A')}*\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Report saved to: {output_path}")
        return output_path

    def save_equity_curve(self, output_dir: str = None):
        """ذخیره نمودار equity curve"""
        if output_dir is None:
            output_dir = Path(__file__).parent / 'reports'
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # ذخیره به CSV
        equity_data = self.results.get('equity_curve', [])
        if not equity_data:
            logger.warning("No equity curve data available")
            return None

        csv_path = output_dir / f"equity_curve_{timestamp}.csv"
        with open(csv_path, 'w') as f:
            f.write("time,equity\n")
            for point in equity_data:
                f.write(f"{point['time']},{point['equity']:.2f}\n")

        logger.info(f"Equity curve saved to: {csv_path}")

        # تلاش برای رسم نمودار
        try:
            import matplotlib.pyplot as plt

            times = [p['time'] for p in equity_data]
            equities = [p['equity'] for p in equity_data]

            # نمودار اصلی با drawdown
            fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})

            # Equity Curve
            ax1 = axes[0]
            ax1.plot(equities, 'b-', linewidth=1.2, label='Equity')
            ax1.axhline(y=self.initial_balance, color='gray', linestyle='--', alpha=0.5, label='Initial Balance')
            ax1.fill_between(range(len(equities)), self.initial_balance, equities,
                           where=[e >= self.initial_balance for e in equities],
                           alpha=0.3, color='green', label='Profit')
            ax1.fill_between(range(len(equities)), self.initial_balance, equities,
                           where=[e < self.initial_balance for e in equities],
                           alpha=0.3, color='red', label='Loss')
            ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Equity (USDT)')
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)

            # Drawdown
            ax2 = axes[1]
            peak = self.initial_balance
            drawdowns = []
            for equity in equities:
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100
                drawdowns.append(dd)

            ax2.fill_between(range(len(drawdowns)), 0, drawdowns, color='red', alpha=0.5)
            ax2.set_title('Drawdown %', fontsize=12)
            ax2.set_xlabel('Time')
            ax2.set_ylabel('Drawdown %')
            ax2.grid(True, alpha=0.3)
            ax2.invert_yaxis()

            plt.tight_layout()

            chart_path = output_dir / f"equity_curve_{timestamp}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Equity chart saved to: {chart_path}")
            return chart_path

        except ImportError:
            logger.info("matplotlib not available, skipping chart generation")
            return csv_path

    def save_performance_summary(self, output_dir: str = None):
        """ذخیره نمودار خلاصه عملکرد"""
        if output_dir is None:
            output_dir = Path(__file__).parent / 'reports'
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            import matplotlib.pyplot as plt

            stats = self.results['statistics']
            trades = self.results.get('trades', [])

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            # 1. توزیع سود/زیان
            ax1 = axes[0, 0]
            pnls = [t['pnl'] for t in trades]
            colors = ['green' if p > 0 else 'red' for p in pnls]
            ax1.bar(range(len(pnls)), pnls, color=colors, alpha=0.7, width=1.0)
            ax1.axhline(y=0, color='black', linewidth=0.5)
            ax1.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
            ax1.set_xlabel('Trade #')
            ax1.set_ylabel('PnL (USDT)')

            # 2. هیستوگرام سود/زیان
            ax2 = axes[0, 1]
            ax2.hist(pnls, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
            ax2.axvline(x=0, color='red', linestyle='--', linewidth=1)
            ax2.axvline(x=np.mean(pnls), color='green', linestyle='--', linewidth=1, label=f'Mean: {np.mean(pnls):.2f}')
            ax2.set_title('PnL Histogram', fontsize=12, fontweight='bold')
            ax2.set_xlabel('PnL (USDT)')
            ax2.set_ylabel('Frequency')
            ax2.legend()

            # 3. نرخ برد/باخت
            ax3 = axes[1, 0]
            win_rate = stats['win_rate']
            loss_rate = 100 - win_rate
            ax3.pie([win_rate, loss_rate], labels=['Wins', 'Losses'],
                   colors=['green', 'red'], autopct='%1.1f%%', startangle=90)
            ax3.set_title(f"Win Rate: {win_rate:.1f}%", fontsize=12, fontweight='bold')

            # 4. آمار کلیدی
            ax4 = axes[1, 1]
            ax4.axis('off')
            summary_text = f"""
            PERFORMANCE SUMMARY
            ═══════════════════════════════════

            Total Trades:       {stats['total_trades']}
            Win Rate:           {stats['win_rate']:.1f}%

            Total Return:       {stats['total_return']:.2f}%
            Profit Factor:      {stats['profit_factor']:.2f}
            Max Drawdown:       {stats['max_drawdown']:.2f}%

            Average Win:        {stats['avg_win']:.2f} USDT
            Average Loss:       {stats['avg_loss']:.2f} USDT

            Gross Profit:       {stats['gross_profit']:,.2f} USDT
            Gross Loss:         {stats['gross_loss']:,.2f} USDT
            Net Profit:         {stats['total_pnl']:,.2f} USDT
            """
            ax4.text(0.1, 0.5, summary_text, fontsize=11, fontfamily='monospace',
                    verticalalignment='center', transform=ax4.transAxes)

            plt.suptitle('Backtest Performance Summary', fontsize=16, fontweight='bold', y=1.02)
            plt.tight_layout()

            summary_path = output_dir / f"performance_summary_{timestamp}.png"
            plt.savefig(summary_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Performance summary saved to: {summary_path}")
            return summary_path

        except ImportError:
            logger.info("matplotlib not available, skipping summary chart")
            return None

    def export_trades_csv(self, output_dir: str = None):
        """صادر کردن معاملات به CSV"""
        if output_dir is None:
            output_dir = Path(__file__).parent / 'reports'
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_dir / f"trades_{timestamp}.csv"

        with open(csv_path, 'w') as f:
            f.write("id,symbol,direction,entry_time,entry_price,exit_time,exit_price,pnl,pnl_percent,exit_reason,patterns,strategies\n")
            for t in self.results.get('trades', []):
                patterns = '|'.join(t.get('patterns_found', []) or [])
                strategies = '|'.join(t.get('strategies_triggered', []) or [])
                f.write(f"{t['id']},{t['symbol']},{t['direction']},{t['entry_time']},{t['entry_price']:.2f},{t['exit_time']},{t['exit_price']:.2f},{t['pnl']:.2f},{t.get('pnl_percent', 0):.2f},{t['exit_reason']},{patterns},{strategies}\n")

        logger.info(f"Trades exported to: {csv_path}")
        return csv_path


def load_config(config_path: str) -> Dict:
    """لود تنظیمات"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
    """ترکیب دو config"""
    result = base_config.copy()
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description='Fast Backtest using pre-computed data')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--method', type=str, default=None,
                        choices=['new', 'old', 'hybrid', 'strategy'],
                        help='Scoring method: new (8 multipliers, capped), old (13 multipliers, unlimited), hybrid (mix), strategy (ensemble)')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  FAST BACKTEST ENGINE")
    print("  Using Pre-computed Indicators & Patterns")
    print("  Scoring Methods: new | old | hybrid | strategy")
    print("="*70 + "\n")

    # لود config از فولدر محلی (precomputed_backtest/configs/)
    local_config_path = Path(__file__).parent / 'configs' / 'config.yaml'
    local_backtest_config_path = Path(__file__).parent / 'configs' / 'config_backtest_v2.yaml'

    config = load_config(local_config_path)

    # لود backtest config و merge
    if local_backtest_config_path.exists():
        backtest_config = load_config(local_backtest_config_path)
        config = merge_configs(config, backtest_config)

    # Override scoring method از command line
    if args.method:
        if 'backtest' not in config:
            config['backtest'] = {}
        config['backtest']['scoring_method'] = args.method
        print(f"  Scoring method: {args.method} (from command line)")

    # اجرای بکتست
    engine = FastBacktestEngine(config)
    results = engine.run()

    # نمایش نتایج
    print("\n" + "="*70)
    print("  BACKTEST RESULTS")
    print("="*70)
    stats = results['statistics']
    print(f"\n  Scoring Method: {stats.get('scoring_method', 'strategy').upper()}")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Winning: {stats.get('winning_trades', 0)} | Losing: {stats.get('losing_trades', 0)}")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    print(f"  Total Return: {stats['total_return']:.2f}%")
    print(f"  Final Equity: {stats['current_equity']:.2f} USDT")
    print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
    print(f"  Max Drawdown: {stats.get('max_drawdown', 0):.2f}%")
    print(f"  Duration: {results['duration']}")
    print(f"\n  --- Realistic Costs ---")
    print(f"  Commission: {stats.get('commission_rate', 0):.2f}% per trade")
    print(f"  Slippage: {stats.get('slippage_rate', 0):.3f}% per trade")
    print(f"  Total Commission Paid: {stats.get('total_commission', 0):.2f} USDT")

    # آمار هر سیمبل
    per_symbol = results.get('per_symbol', {})
    if len(per_symbol) > 1:
        print(f"\n  --- Per Symbol Stats ---")
        for sym, sym_stats in per_symbol.items():
            print(f"  {sym}: {sym_stats['total_trades']} trades, {sym_stats['win_rate']:.1f}% win, PnL: {sym_stats['total_pnl']:.2f}")

    # ذخیره گزارش‌ها
    print("\n  Saving reports...")
    report_path = engine.save_report()
    print(f"  - Report: {report_path}")

    equity_path = engine.save_equity_curve()
    if equity_path:
        print(f"  - Equity curve: {equity_path}")

    summary_path = engine.save_performance_summary()
    if summary_path:
        print(f"  - Performance summary: {summary_path}")

    trades_path = engine.export_trades_csv()
    print(f"  - Trades CSV: {trades_path}")
    print()


if __name__ == '__main__':
    main()
