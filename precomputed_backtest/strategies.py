"""
Trading Strategies - استراتژی‌های معاملاتی

این ماژول شامل استراتژی‌های مختلف معاملاتی است که از اندیکاتورهای
از پیش محاسبه شده استفاده می‌کنند.

استراتژی‌ها:
1. TrendFollowing - پیروی از روند
2. MeanReversion - بازگشت به میانگین
3. Breakout - شکست سطوح
4. Momentum - مومنتوم
5. RangeTrading - معامله در رنج
6. StrategyEnsemble - ترکیب استراتژی‌ها
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SignalDirection(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class StrategySignal:
    """نتیجه یک استراتژی"""
    direction: SignalDirection
    score: float  # 0-100
    confidence: float  # 0-1
    reason: str
    indicators_used: List[str]


class BaseStrategy:
    """کلاس پایه برای استراتژی‌ها"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = "base"
        self.weight = 1.0

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        """تحلیل و تولید سیگنال"""
        raise NotImplementedError


class TrendFollowingStrategy(BaseStrategy):
    """
    استراتژی پیروی از روند

    سیگنال‌ها:
    - LONG: قیمت > EMA20 > EMA50 > EMA200 + ADX > 25
    - SHORT: قیمت < EMA20 < EMA50 < EMA200 + ADX > 25

    از Ichimoku Cloud هم برای تأیید استفاده می‌شود.
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.name = "trend_following"
        self.weight = 1.2  # وزن بالاتر برای روندها
        self.adx_threshold = 25
        self.ema_periods = [20, 50, 200]

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        indicators = []

        close = row.get('close', 0)

        # 1. EMA Alignment
        ema_20 = row.get('ema_20')
        ema_50 = row.get('ema_50')
        ema_200 = row.get('ema_200')

        if all(pd.notna([ema_20, ema_50, ema_200, close])):
            indicators.append('EMA')
            if close > ema_20 > ema_50 > ema_200:
                bullish_signals += 3
                score += 30
            elif close < ema_20 < ema_50 < ema_200:
                bearish_signals += 3
                score += 30
            elif close > ema_20 > ema_50:
                bullish_signals += 2
                score += 20
            elif close < ema_20 < ema_50:
                bearish_signals += 2
                score += 20

        # 2. ADX (قدرت روند)
        adx = row.get('adx')
        if pd.notna(adx):
            indicators.append('ADX')
            if adx > 40:  # روند قوی
                score += 25
            elif adx > self.adx_threshold:  # روند معتبر
                score += 15
            elif adx < 20:  # بدون روند
                score -= 10

        # 3. Ichimoku Cloud
        tenkan = row.get('ichimoku_tenkan')
        kijun = row.get('ichimoku_kijun')
        senkou_a = row.get('ichimoku_senkou_a')
        senkou_b = row.get('ichimoku_senkou_b')

        if all(pd.notna([tenkan, kijun, senkou_a, senkou_b, close])):
            indicators.append('Ichimoku')
            cloud_top = max(senkou_a, senkou_b)
            cloud_bottom = min(senkou_a, senkou_b)

            if close > cloud_top and tenkan > kijun:
                bullish_signals += 2
                score += 20
            elif close < cloud_bottom and tenkan < kijun:
                bearish_signals += 2
                score += 20

        # 4. MACD Trend Confirmation
        macd = row.get('macd')
        macd_signal = row.get('macd_signal')

        if pd.notna(macd) and pd.notna(macd_signal):
            indicators.append('MACD')
            if macd > macd_signal and macd > 0:
                bullish_signals += 1
                score += 10
            elif macd < macd_signal and macd < 0:
                bearish_signals += 1
                score += 10

        # تعیین جهت
        if bullish_signals > bearish_signals and bullish_signals >= 3:
            direction = SignalDirection.LONG
            confidence = min(bullish_signals / 6, 1.0)
            reason = f"Uptrend: EMA aligned, ADX={adx:.1f}" if pd.notna(adx) else "Uptrend confirmed"
        elif bearish_signals > bullish_signals and bearish_signals >= 3:
            direction = SignalDirection.SHORT
            confidence = min(bearish_signals / 6, 1.0)
            reason = f"Downtrend: EMA aligned, ADX={adx:.1f}" if pd.notna(adx) else "Downtrend confirmed"
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0
            reason = "No clear trend"

        return StrategySignal(
            direction=direction,
            score=min(score, 100),
            confidence=confidence,
            reason=reason,
            indicators_used=indicators
        )


class MeanReversionStrategy(BaseStrategy):
    """
    استراتژی بازگشت به میانگین

    سیگنال‌ها:
    - LONG: RSI < 30 + قیمت زیر BB Lower
    - SHORT: RSI > 70 + قیمت بالای BB Upper

    از Williams %R و CCI هم استفاده می‌شود.
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.name = "mean_reversion"
        self.weight = 1.0
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.cci_oversold = -100
        self.cci_overbought = 100

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        indicators = []

        close = row.get('close', 0)

        # 1. RSI
        rsi = row.get('rsi')
        if pd.notna(rsi):
            indicators.append('RSI')
            if rsi < self.rsi_oversold:
                bullish_signals += 2
                score += 25
            elif rsi < 40:
                bullish_signals += 1
                score += 10
            elif rsi > self.rsi_overbought:
                bearish_signals += 2
                score += 25
            elif rsi > 60:
                bearish_signals += 1
                score += 10

        # 2. Bollinger Bands
        bb_upper = row.get('bb_upper')
        bb_lower = row.get('bb_lower')
        bb_mid = row.get('bb_mid')

        if all(pd.notna([bb_upper, bb_lower, bb_mid, close])):
            indicators.append('BB')
            bb_width = (bb_upper - bb_lower) / bb_mid if bb_mid > 0 else 0

            if close < bb_lower:
                bullish_signals += 2
                score += 25
            elif close > bb_upper:
                bearish_signals += 2
                score += 25
            elif close < bb_mid:
                bullish_signals += 1
                score += 5
            else:
                bearish_signals += 1
                score += 5

        # 3. Williams %R
        williams_r = row.get('williams_r')
        if pd.notna(williams_r):
            indicators.append('Williams%R')
            if williams_r < -80:
                bullish_signals += 1
                score += 15
            elif williams_r > -20:
                bearish_signals += 1
                score += 15

        # 4. CCI
        cci = row.get('cci')
        if pd.notna(cci):
            indicators.append('CCI')
            if cci < self.cci_oversold:
                bullish_signals += 1
                score += 15
            elif cci > self.cci_overbought:
                bearish_signals += 1
                score += 15

        # 5. Stochastic
        stoch_k = row.get('stoch_k')
        stoch_d = row.get('stoch_d')
        if pd.notna(stoch_k) and pd.notna(stoch_d):
            indicators.append('Stochastic')
            if stoch_k < 20 and stoch_d < 20:
                bullish_signals += 1
                score += 10
            elif stoch_k > 80 and stoch_d > 80:
                bearish_signals += 1
                score += 10

        # تعیین جهت
        if bullish_signals > bearish_signals and bullish_signals >= 3:
            direction = SignalDirection.LONG
            confidence = min(bullish_signals / 5, 1.0)
            reason = f"Oversold: RSI={rsi:.1f}" if pd.notna(rsi) else "Oversold conditions"
        elif bearish_signals > bullish_signals and bearish_signals >= 3:
            direction = SignalDirection.SHORT
            confidence = min(bearish_signals / 5, 1.0)
            reason = f"Overbought: RSI={rsi:.1f}" if pd.notna(rsi) else "Overbought conditions"
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0
            reason = "No reversal signal"

        return StrategySignal(
            direction=direction,
            score=min(score, 100),
            confidence=confidence,
            reason=reason,
            indicators_used=indicators
        )


class BreakoutStrategy(BaseStrategy):
    """
    استراتژی شکست سطوح

    سیگنال‌ها:
    - LONG: شکست Pivot R1/R2 + حجم بالا + الگوی صعودی
    - SHORT: شکست Pivot S1/S2 + حجم بالا + الگوی نزولی

    از Fibonacci و Volume Profile هم استفاده می‌شود.
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.name = "breakout"
        self.weight = 1.1

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        indicators = []

        close = row.get('close', 0)
        high = row.get('high', 0)
        low = row.get('low', 0)

        # 1. Pivot Points Breakout
        pivot = row.get('pivot')
        r1 = row.get('pivot_r1')
        r2 = row.get('pivot_r2')
        s1 = row.get('pivot_s1')
        s2 = row.get('pivot_s2')

        if all(pd.notna([pivot, r1, r2, s1, s2])):
            indicators.append('Pivot')
            if close > r2:
                bullish_signals += 3
                score += 30
            elif close > r1:
                bullish_signals += 2
                score += 20
            elif close < s2:
                bearish_signals += 3
                score += 30
            elif close < s1:
                bearish_signals += 2
                score += 20

        # 2. Fibonacci Levels
        fib_618 = row.get('fib_618')
        fib_382 = row.get('fib_382')
        fib_0 = row.get('fib_0')
        fib_100 = row.get('fib_100')

        if all(pd.notna([fib_618, fib_382, fib_0, fib_100])):
            indicators.append('Fibonacci')
            if close > fib_0:  # بالاتر از swing high
                bullish_signals += 2
                score += 20
            elif close < fib_100:  # پایین‌تر از swing low
                bearish_signals += 2
                score += 20
            elif close > fib_382:
                bullish_signals += 1
                score += 10
            elif close < fib_618:
                bearish_signals += 1
                score += 10

        # 3. Volume Profile
        vp_poc = row.get('vp_poc')
        vp_vah = row.get('vp_vah')
        vp_val = row.get('vp_val')

        if all(pd.notna([vp_poc, vp_vah, vp_val])):
            indicators.append('VolumeProfile')
            if close > vp_vah:
                bullish_signals += 1
                score += 15
            elif close < vp_val:
                bearish_signals += 1
                score += 15

        # 4. Bollinger Band Breakout
        bb_upper = row.get('bb_upper')
        bb_lower = row.get('bb_lower')

        if pd.notna(bb_upper) and pd.notna(bb_lower):
            indicators.append('BB_Breakout')
            if high > bb_upper:
                bullish_signals += 1
                score += 10
            elif low < bb_lower:
                bearish_signals += 1
                score += 10

        # 5. Chart Pattern Confirmation
        pattern_cols = [c for c in row.index if c.startswith('pattern_')
                       and not c.endswith('_direction') and not c.endswith('_score')]

        for col in pattern_cols:
            if row.get(col) == 1:
                pattern_name = col.replace('pattern_', '')
                direction_col = f'{col}_direction'
                if direction_col in row.index:
                    pattern_dir = row.get(direction_col, 'none')
                    if pattern_dir == 'bullish':
                        bullish_signals += 1
                        score += 10
                    elif pattern_dir == 'bearish':
                        bearish_signals += 1
                        score += 10

        # تعیین جهت
        if bullish_signals > bearish_signals and bullish_signals >= 3:
            direction = SignalDirection.LONG
            confidence = min(bullish_signals / 6, 1.0)
            reason = "Bullish breakout detected"
        elif bearish_signals > bullish_signals and bearish_signals >= 3:
            direction = SignalDirection.SHORT
            confidence = min(bearish_signals / 6, 1.0)
            reason = "Bearish breakout detected"
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0
            reason = "No breakout"

        return StrategySignal(
            direction=direction,
            score=min(score, 100),
            confidence=confidence,
            reason=reason,
            indicators_used=indicators
        )


class MomentumStrategy(BaseStrategy):
    """
    استراتژی مومنتوم

    سیگنال‌ها:
    - LONG: MACD صعودی + RSI > 50 + OBV صعودی
    - SHORT: MACD نزولی + RSI < 50 + OBV نزولی
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.name = "momentum"
        self.weight = 1.0

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        indicators = []

        # 1. MACD Momentum
        macd = row.get('macd')
        macd_signal = row.get('macd_signal')
        macd_hist = row.get('macd_hist')

        if all(pd.notna([macd, macd_signal, macd_hist])):
            indicators.append('MACD')
            if macd > macd_signal:
                bullish_signals += 1
                score += 15
                if macd_hist > 0:
                    bullish_signals += 1
                    score += 10
            else:
                bearish_signals += 1
                score += 15
                if macd_hist < 0:
                    bearish_signals += 1
                    score += 10

        # 2. RSI Momentum
        rsi = row.get('rsi')
        if pd.notna(rsi):
            indicators.append('RSI')
            if rsi > 60:
                bullish_signals += 1
                score += 15
            elif rsi < 40:
                bearish_signals += 1
                score += 15

        # 3. Price vs VWAP
        close = row.get('close', 0)
        vwap = row.get('vwap')

        if pd.notna(vwap) and close > 0:
            indicators.append('VWAP')
            if close > vwap * 1.01:  # 1% بالای VWAP
                bullish_signals += 1
                score += 15
            elif close < vwap * 0.99:  # 1% زیر VWAP
                bearish_signals += 1
                score += 15

        # 4. Stochastic Momentum
        stoch_k = row.get('stoch_k')
        stoch_d = row.get('stoch_d')

        if pd.notna(stoch_k) and pd.notna(stoch_d):
            indicators.append('Stochastic')
            if stoch_k > stoch_d and stoch_k > 50:
                bullish_signals += 1
                score += 10
            elif stoch_k < stoch_d and stoch_k < 50:
                bearish_signals += 1
                score += 10

        # 5. ADX for momentum strength
        adx = row.get('adx')
        if pd.notna(adx):
            indicators.append('ADX')
            if adx > 25:
                score += 15  # مومنتوم قوی
            elif adx < 20:
                score -= 10  # مومنتوم ضعیف

        # تعیین جهت
        if bullish_signals > bearish_signals and bullish_signals >= 3:
            direction = SignalDirection.LONG
            confidence = min(bullish_signals / 5, 1.0)
            reason = f"Bullish momentum, MACD hist={macd_hist:.4f}" if pd.notna(macd_hist) else "Bullish momentum"
        elif bearish_signals > bullish_signals and bearish_signals >= 3:
            direction = SignalDirection.SHORT
            confidence = min(bearish_signals / 5, 1.0)
            reason = f"Bearish momentum, MACD hist={macd_hist:.4f}" if pd.notna(macd_hist) else "Bearish momentum"
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0
            reason = "No clear momentum"

        return StrategySignal(
            direction=direction,
            score=min(score, 100),
            confidence=confidence,
            reason=reason,
            indicators_used=indicators
        )


class RangeTradingStrategy(BaseStrategy):
    """
    استراتژی معامله در رنج

    سیگنال‌ها:
    - LONG: قیمت نزدیک حمایت + ADX < 20
    - SHORT: قیمت نزدیک مقاومت + ADX < 20
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.name = "range_trading"
        self.weight = 0.8
        self.adx_range_threshold = 20

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        indicators = []

        close = row.get('close', 0)

        # بررسی اینکه آیا در رنج هستیم
        adx = row.get('adx')
        is_ranging = pd.notna(adx) and adx < self.adx_range_threshold

        if not is_ranging:
            return StrategySignal(
                direction=SignalDirection.NEUTRAL,
                score=0,
                confidence=0,
                reason="Market not ranging",
                indicators_used=['ADX']
            )

        indicators.append('ADX')

        # 1. Bollinger Band Range
        bb_upper = row.get('bb_upper')
        bb_lower = row.get('bb_lower')
        bb_mid = row.get('bb_mid')

        if all(pd.notna([bb_upper, bb_lower, bb_mid])):
            indicators.append('BB')
            bb_range = bb_upper - bb_lower
            upper_zone = bb_upper - (bb_range * 0.2)
            lower_zone = bb_lower + (bb_range * 0.2)

            if close < lower_zone:
                bullish_signals += 2
                score += 25
            elif close > upper_zone:
                bearish_signals += 2
                score += 25

        # 2. Pivot Point Range
        pivot = row.get('pivot')
        r1 = row.get('pivot_r1')
        s1 = row.get('pivot_s1')

        if all(pd.notna([pivot, r1, s1])):
            indicators.append('Pivot')
            if close < pivot:
                bullish_signals += 1
                score += 15
            elif close > pivot:
                bearish_signals += 1
                score += 15

        # 3. RSI in Range
        rsi = row.get('rsi')
        if pd.notna(rsi):
            indicators.append('RSI')
            if 30 < rsi < 40:
                bullish_signals += 1
                score += 15
            elif 60 < rsi < 70:
                bearish_signals += 1
                score += 15

        # 4. Stochastic in Range
        stoch_k = row.get('stoch_k')
        if pd.notna(stoch_k):
            indicators.append('Stochastic')
            if stoch_k < 30:
                bullish_signals += 1
                score += 15
            elif stoch_k > 70:
                bearish_signals += 1
                score += 15

        # تعیین جهت
        if bullish_signals > bearish_signals and bullish_signals >= 2:
            direction = SignalDirection.LONG
            confidence = min(bullish_signals / 4, 1.0)
            reason = f"Buy at support, ADX={adx:.1f}"
        elif bearish_signals > bullish_signals and bearish_signals >= 2:
            direction = SignalDirection.SHORT
            confidence = min(bearish_signals / 4, 1.0)
            reason = f"Sell at resistance, ADX={adx:.1f}"
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0
            reason = "No range signal"

        return StrategySignal(
            direction=direction,
            score=min(score, 100),
            confidence=confidence,
            reason=reason,
            indicators_used=indicators
        )


class PatternStrategy(BaseStrategy):
    """
    استراتژی مبتنی بر الگوها

    سیگنال‌ها بر اساس الگوهای کندلی و چارت تشخیص داده شده
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.name = "pattern"
        self.weight = 1.0

        # امتیاز الگوها
        self.pattern_scores = {
            # الگوهای قوی
            'head_shoulders': 30,
            'inverse_head_shoulders': 30,
            'double_top': 25,
            'double_bottom': 25,
            'morning_star': 25,
            'evening_star': 25,
            'three_white_soldiers': 25,
            'three_black_crows': 25,

            # الگوهای متوسط
            'cup_and_handle': 20,
            'engulfing': 20,
            'hammer': 15,
            'shooting_star': 15,
            'bull_flag': 15,
            'bear_flag': 15,
            'ascending_triangle': 15,
            'descending_triangle': 15,

            # الگوهای ضعیف‌تر
            'doji': 10,
            'harami': 10,
            'piercing_line': 10,
            'dark_cloud_cover': 10,
            'marubozu': 10,
            'spinning_top': 5,
        }

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> StrategySignal:
        score = 0
        bullish_score = 0
        bearish_score = 0
        patterns_found = []

        # بررسی همه ستون‌های الگو
        pattern_cols = [c for c in row.index if c.startswith('pattern_')
                       and not c.endswith('_direction') and not c.endswith('_score')]

        for col in pattern_cols:
            if row.get(col) == 1:
                pattern_name = col.replace('pattern_', '')
                direction_col = f'{col}_direction'
                score_col = f'{col}_score'

                # دریافت جهت و امتیاز
                pattern_dir = row.get(direction_col, 'none')
                pattern_score = row.get(score_col, 0.5)

                # محاسبه امتیاز
                base_score = self.pattern_scores.get(pattern_name, 10)
                weighted_score = base_score * pattern_score

                if pattern_dir == 'bullish':
                    bullish_score += weighted_score
                    patterns_found.append(f"{pattern_name}(+)")
                elif pattern_dir == 'bearish':
                    bearish_score += weighted_score
                    patterns_found.append(f"{pattern_name}(-)")
                elif pattern_dir == 'neutral':
                    # الگوهای خنثی نیاز به بررسی بیشتر دارند
                    patterns_found.append(f"{pattern_name}(~)")

        total_score = bullish_score + bearish_score

        # تعیین جهت
        if bullish_score > bearish_score and bullish_score >= 20:
            direction = SignalDirection.LONG
            confidence = min(bullish_score / 50, 1.0)
            reason = f"Bullish patterns: {', '.join([p for p in patterns_found if '(+)' in p])}"
        elif bearish_score > bullish_score and bearish_score >= 20:
            direction = SignalDirection.SHORT
            confidence = min(bearish_score / 50, 1.0)
            reason = f"Bearish patterns: {', '.join([p for p in patterns_found if '(-)' in p])}"
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0
            reason = "No strong pattern signal"

        return StrategySignal(
            direction=direction,
            score=min(total_score, 100),
            confidence=confidence,
            reason=reason,
            indicators_used=patterns_found if patterns_found else ['No patterns']
        )


class StrategyEnsemble:
    """
    ترکیب استراتژی‌ها برای تولید سیگنال نهایی

    از رأی‌گیری وزن‌دار بین استراتژی‌ها استفاده می‌کند.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # ایجاد استراتژی‌ها
        self.strategies = [
            TrendFollowingStrategy(config),
            MeanReversionStrategy(config),
            BreakoutStrategy(config),
            MomentumStrategy(config),
            RangeTradingStrategy(config),
            PatternStrategy(config),
        ]

        # تنظیمات
        self.voting_threshold = config.get('voting_threshold', 0.5)
        self.min_agreement = config.get('min_agreement', 2)
        self.min_score = config.get('min_score', 40)

    def analyze(self, row: pd.Series, df: pd.DataFrame = None, idx: int = None) -> Tuple[Optional[SignalDirection], float, str, Dict]:
        """
        تحلیل با همه استراتژی‌ها و ترکیب نتایج

        Returns:
            Tuple[direction, score, reason, details]
        """
        results = []

        for strategy in self.strategies:
            try:
                signal = strategy.analyze(row, df, idx)
                results.append({
                    'name': strategy.name,
                    'weight': strategy.weight,
                    'signal': signal
                })
            except Exception as e:
                logger.debug(f"Strategy {strategy.name} error: {e}")

        # جمع‌آوری رأی‌ها
        long_score = 0
        short_score = 0
        total_weight = 0
        long_strategies = []
        short_strategies = []

        for r in results:
            weight = r['weight']
            signal = r['signal']
            total_weight += weight

            if signal.direction == SignalDirection.LONG:
                long_score += weight * signal.score * signal.confidence
                long_strategies.append(r['name'])
            elif signal.direction == SignalDirection.SHORT:
                short_score += weight * signal.score * signal.confidence
                short_strategies.append(r['name'])

        # نرمال‌سازی
        if total_weight > 0:
            long_score /= total_weight
            short_score /= total_weight

        # تصمیم نهایی
        details = {
            'long_score': long_score,
            'short_score': short_score,
            'long_strategies': long_strategies,
            'short_strategies': short_strategies,
            'all_results': results
        }

        if long_score > short_score and long_score >= self.min_score and len(long_strategies) >= self.min_agreement:
            return SignalDirection.LONG, long_score, f"Ensemble LONG: {', '.join(long_strategies)}", details
        elif short_score > long_score and short_score >= self.min_score and len(short_strategies) >= self.min_agreement:
            return SignalDirection.SHORT, short_score, f"Ensemble SHORT: {', '.join(short_strategies)}", details
        else:
            return None, 0, "No ensemble signal", details
