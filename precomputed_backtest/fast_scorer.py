"""
Fast Scorer - سیستم امتیازدهی سریع با پشتیبانی از سه متد

این ماژول سه روش امتیازدهی را پیاده‌سازی می‌کند:
- NEW: 8 ضریب، امتیاز محدود به 300
- OLD: 13 ضریب، امتیاز نامحدود
- HYBRID: ترکیبی از هر دو

Usage:
    scorer = FastScorer(method='new', config={})
    score = scorer.calculate_score(row, direction='LONG')
"""

from enum import Enum
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ScoringMethod(Enum):
    """روش‌های امتیازدهی"""
    NEW = "new"
    OLD = "old"
    HYBRID = "hybrid"


@dataclass
class ScoreResult:
    """نتیجه امتیازدهی"""
    # امتیازهای پایه
    base_score: float = 0.0
    final_score: float = 0.0

    # 13 ضریب
    timeframe_weight: float = 1.0
    trend_alignment: float = 1.0
    volume_confirmation: float = 1.0
    pattern_quality: float = 1.0
    confluence_score: float = 0.0
    symbol_performance_factor: float = 1.0
    correlation_safety_factor: float = 1.0
    macd_analysis_score: float = 1.0
    structure_score: float = 1.0
    volatility_score: float = 1.0
    harmonic_pattern_score: float = 1.0
    price_channel_score: float = 1.0
    cyclical_pattern_score: float = 1.0

    # متادیتا
    method: str = ""
    direction: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class FastScorer:
    """
    سیستم امتیازدهی سریع با استفاده از داده‌های از پیش محاسبه شده

    سه روش پشتیبانی می‌شود:
    - NEW: ساده‌تر، 8 ضریب، محدود به 300
    - OLD: پیچیده‌تر، 13 ضریب، نامحدود
    - HYBRID: ترکیبی
    """

    def __init__(self, method: str = 'new', config: Dict[str, Any] = None):
        """
        Initialize FastScorer

        Args:
            method: 'new', 'old', or 'hybrid'
            config: تنظیمات اضافی
        """
        self.method = ScoringMethod(method.lower())
        self.config = config or {}

        # تنظیمات بر اساس متد
        if self.method == ScoringMethod.NEW:
            self.max_score = 300
            self.use_13_multipliers = False
            self.min_signal_score = 50
            self.strong_threshold = 150
        elif self.method == ScoringMethod.OLD:
            self.max_score = 0  # نامحدود
            self.use_13_multipliers = True
            self.min_signal_score = 200
            self.strong_threshold = 500
        else:  # HYBRID
            self.max_score = 300
            self.use_13_multipliers = True
            self.min_signal_score = 80
            self.strong_threshold = 180

        # وزن‌های NEW system برای base_score
        self.weights = {
            'trend': 0.30,
            'momentum': 0.25,
            'volume': 0.20,
            'patterns': 0.10,
            'support_resistance': 0.08,
            'volatility': 0.05,
            'harmonic': 0.01,
            'channel': 0.005,
        }

        logger.info(f"FastScorer initialized with method: {self.method.value}")
        logger.info(f"  Max score: {self.max_score if self.max_score > 0 else 'unlimited'}")
        logger.info(f"  Use 13 multipliers: {self.use_13_multipliers}")

    def calculate_score(
        self,
        row: pd.Series,
        direction: str,
        htf_row: Optional[pd.Series] = None
    ) -> ScoreResult:
        """
        محاسبه امتیاز سیگنال

        Args:
            row: داده‌های کندل فعلی (شامل اندیکاتورها و الگوها)
            direction: 'LONG' یا 'SHORT'
            htf_row: داده‌های تایم‌فریم بالاتر (اختیاری)

        Returns:
            ScoreResult با تمام اجزا
        """
        result = ScoreResult(method=self.method.value, direction=direction)

        try:
            # 1. محاسبه Base Score
            if self.method == ScoringMethod.OLD:
                result.base_score = self._calculate_base_score_old(row, direction)
            else:  # NEW or HYBRID
                result.base_score = self._calculate_base_score_new(row, direction)

            # 2. محاسبه ضرایب
            result.timeframe_weight = self._calculate_timeframe_weight(row, htf_row, direction)
            result.trend_alignment = self._calculate_trend_alignment(row, direction)
            result.volume_confirmation = self._calculate_volume_confirmation(row)
            result.pattern_quality = self._calculate_pattern_quality(row)
            result.confluence_score = self._calculate_confluence(row, direction)
            result.macd_analysis_score = self._calculate_macd_score(row)
            result.volatility_score = self._calculate_volatility_score(row)

            # 3. ضرایب اضافی (فقط OLD و HYBRID)
            if self.use_13_multipliers:
                result.symbol_performance_factor = self._calculate_symbol_performance()
                result.correlation_safety_factor = self._calculate_correlation_safety()
                result.structure_score = self._calculate_structure_score(row, htf_row, direction)
                result.harmonic_pattern_score = self._calculate_harmonic_score(row)
                result.price_channel_score = self._calculate_channel_score(row)
                result.cyclical_pattern_score = self._calculate_cyclical_score(row)

            # 4. محاسبه امتیاز نهایی
            result.final_score = self._calculate_final_score(result)

            # 5. اعمال محدودیت (فقط NEW و HYBRID)
            if self.max_score > 0:
                result.final_score = min(result.final_score, self.max_score)

            return result

        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return result

    def _calculate_base_score_new(self, row: pd.Series, direction: str) -> float:
        """
        محاسبه Base Score به روش NEW (وزن‌دهی شده، 0-100)
        """
        scores = {}

        # 1. Trend Score (از EMA alignment)
        scores['trend'] = self._get_trend_score(row, direction)

        # 2. Momentum Score (از RSI, MACD)
        scores['momentum'] = self._get_momentum_score(row, direction)

        # 3. Volume Score
        scores['volume'] = self._get_volume_score(row)

        # 4. Pattern Score (از الگوهای کندلی)
        scores['patterns'] = self._get_pattern_score(row, direction)

        # 5. S/R Score
        scores['support_resistance'] = self._get_sr_score(row, direction)

        # 6. Volatility Score
        scores['volatility'] = self._get_volatility_base_score(row)

        # 7. Harmonic Score
        scores['harmonic'] = self._get_harmonic_base_score(row)

        # 8. Channel Score
        scores['channel'] = self._get_channel_base_score(row)

        # محاسبه وزن‌دهی شده
        base_score = sum(
            scores.get(k, 0) * self.weights.get(k, 0)
            for k in self.weights.keys()
        )

        # نرمال‌سازی به 0-100
        return min(100, max(0, base_score))

    def _calculate_base_score_old(self, row: pd.Series, direction: str) -> float:
        """
        محاسبه Base Score به روش OLD (جمع دستی، 50-100)
        """
        base = 0.0

        # 1. Momentum contribution (20-40)
        momentum_score = self._get_momentum_score(row, direction)
        if momentum_score > 70:
            base += 40
        elif momentum_score > 50:
            base += 30
        else:
            base += 20

        # 2. Pattern contribution (20-40)
        pattern_score = self._get_pattern_score(row, direction)
        if pattern_score > 70:
            base += 40
        elif pattern_score > 50:
            base += 30
        else:
            base += 20

        # 3. S/R position (10-20)
        sr_score = self._get_sr_score(row, direction)
        if sr_score > 70:
            base += 20
        elif sr_score > 50:
            base += 15
        else:
            base += 10

        return min(100, max(50, base))

    def _get_trend_score(self, row: pd.Series, direction: str) -> float:
        """امتیاز روند بر اساس EMA alignment"""
        score = 50.0  # پیش‌فرض

        close = row.get('close', 0)
        ema_20 = row.get('ema_20', 0)
        ema_50 = row.get('ema_50', 0)

        if pd.isna(ema_20) or pd.isna(ema_50) or ema_20 == 0:
            return score

        if direction.upper() == 'LONG':
            if close > ema_20 > ema_50:
                score = 100  # Strong uptrend
            elif close > ema_20:
                score = 75
            elif close > ema_50:
                score = 60
        else:  # SHORT
            if close < ema_20 < ema_50:
                score = 100  # Strong downtrend
            elif close < ema_20:
                score = 75
            elif close < ema_50:
                score = 60

        return score

    def _get_momentum_score(self, row: pd.Series, direction: str) -> float:
        """امتیاز مومنتوم بر اساس RSI و MACD"""
        score = 50.0

        rsi = row.get('rsi', 50)
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)

        if pd.isna(rsi):
            rsi = 50
        if pd.isna(macd) or pd.isna(macd_signal):
            macd = macd_signal = 0

        if direction.upper() == 'LONG':
            # RSI در oversold خوب است
            if rsi < 30:
                score += 30
            elif rsi < 45:
                score += 15

            # MACD bullish
            if macd > macd_signal:
                score += 20
        else:  # SHORT
            if rsi > 70:
                score += 30
            elif rsi > 55:
                score += 15

            if macd < macd_signal:
                score += 20

        return min(100, score)

    def _get_volume_score(self, row: pd.Series) -> float:
        """امتیاز حجم"""
        score = 50.0

        # بررسی volume vs average
        if 'volume_ratio' in row and pd.notna(row['volume_ratio']):
            ratio = row['volume_ratio']
            if ratio > 2.0:
                score = 100
            elif ratio > 1.5:
                score = 80
            elif ratio > 1.0:
                score = 60

        return score

    def _get_pattern_score(self, row: pd.Series, direction: str) -> float:
        """امتیاز الگوهای کندلی"""
        score = 0.0
        patterns_found = 0

        # الگوهای bullish
        bullish_patterns = [
            'pattern_hammer', 'pattern_morning_star', 'pattern_piercing_line',
            'pattern_three_white_soldiers', 'pattern_bullish_engulfing',
            'pattern_bullish_harami', 'pattern_dragonfly_doji'
        ]

        # الگوهای bearish
        bearish_patterns = [
            'pattern_shooting_star', 'pattern_evening_star', 'pattern_dark_cloud_cover',
            'pattern_three_black_crows', 'pattern_bearish_engulfing',
            'pattern_bearish_harami', 'pattern_gravestone_doji'
        ]

        patterns_to_check = bullish_patterns if direction.upper() == 'LONG' else bearish_patterns

        for pattern in patterns_to_check:
            if pattern in row and row[pattern] == 1:
                patterns_found += 1
                score += 30

        return min(100, score)

    def _get_sr_score(self, row: pd.Series, direction: str) -> float:
        """امتیاز Support/Resistance"""
        score = 50.0

        close = row.get('close', 0)
        bb_upper = row.get('bb_upper', 0)
        bb_lower = row.get('bb_lower', 0)

        if pd.isna(bb_upper) or pd.isna(bb_lower) or bb_upper == bb_lower:
            return score

        # موقعیت در Bollinger Band
        bb_position = (close - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5

        if direction.upper() == 'LONG':
            # نزدیک به support (lower band) خوب است
            if bb_position < 0.2:
                score = 90
            elif bb_position < 0.4:
                score = 70
        else:  # SHORT
            # نزدیک به resistance (upper band) خوب است
            if bb_position > 0.8:
                score = 90
            elif bb_position > 0.6:
                score = 70

        return score

    def _get_volatility_base_score(self, row: pd.Series) -> float:
        """امتیاز پایه volatility"""
        return 50.0  # پیش‌فرض

    def _get_harmonic_base_score(self, row: pd.Series) -> float:
        """امتیاز پایه harmonic"""
        return 50.0  # پیش‌فرض

    def _get_channel_base_score(self, row: pd.Series) -> float:
        """امتیاز پایه channel"""
        return 50.0  # پیش‌فرض

    def _calculate_timeframe_weight(
        self,
        row: pd.Series,
        htf_row: Optional[pd.Series],
        direction: str
    ) -> float:
        """
        محاسبه Timeframe Weight

        NEW: 0.5-1.8
        OLD: 0.7-1.2
        """
        weight = 1.0

        if htf_row is not None:
            htf_trend = self._get_trend_score(htf_row, direction)
            if htf_trend > 70:
                weight = 1.3 if self.method == ScoringMethod.NEW else 1.2
            elif htf_trend < 40:
                weight = 0.7

        return weight

    def _calculate_trend_alignment(self, row: pd.Series, direction: str) -> float:
        """
        محاسبه Trend Alignment (0.8-1.2)
        """
        trend_score = self._get_trend_score(row, direction)

        if trend_score > 80:
            return 1.2
        elif trend_score > 60:
            return 1.1
        elif trend_score > 40:
            return 1.0
        else:
            return 0.8

    def _calculate_volume_confirmation(self, row: pd.Series) -> float:
        """
        محاسبه Volume Confirmation

        NEW: 1.0-1.1
        OLD: 1.0-1.4
        """
        volume_score = self._get_volume_score(row)

        if self.method == ScoringMethod.OLD:
            if volume_score > 80:
                return 1.4
            elif volume_score > 60:
                return 1.2
            else:
                return 1.0
        else:  # NEW or HYBRID
            if volume_score > 80:
                return 1.1
            else:
                return 1.0

    def _calculate_pattern_quality(self, row: pd.Series) -> float:
        """محاسبه Pattern Quality (1.0-1.5)"""
        # شمارش تعداد الگوها
        pattern_cols = [c for c in row.index if c.startswith('pattern_') and not c.endswith('_direction')]
        pattern_count = sum(1 for c in pattern_cols if c in row and row[c] == 1)

        if pattern_count >= 3:
            return 1.5
        elif pattern_count >= 2:
            return 1.3
        elif pattern_count >= 1:
            return 1.1
        return 1.0

    def _calculate_confluence(self, row: pd.Series, direction: str) -> float:
        """
        محاسبه Confluence Score (0-0.5)

        این bonus به امتیاز اضافه می‌شود: (1 + confluence)
        """
        confluence = 0.0
        confirmations = 0

        # 1. RSI confirmation
        rsi = row.get('rsi', 50)
        if pd.notna(rsi):
            if direction.upper() == 'LONG' and rsi < 40:
                confirmations += 1
            elif direction.upper() == 'SHORT' and rsi > 60:
                confirmations += 1

        # 2. MACD confirmation
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        if pd.notna(macd) and pd.notna(macd_signal):
            if direction.upper() == 'LONG' and macd > macd_signal:
                confirmations += 1
            elif direction.upper() == 'SHORT' and macd < macd_signal:
                confirmations += 1

        # 3. EMA confirmation
        close = row.get('close', 0)
        ema_20 = row.get('ema_20', 0)
        if pd.notna(close) and pd.notna(ema_20):
            if direction.upper() == 'LONG' and close > ema_20:
                confirmations += 1
            elif direction.upper() == 'SHORT' and close < ema_20:
                confirmations += 1

        # 4. Pattern confirmation
        pattern_score = self._get_pattern_score(row, direction)
        if pattern_score > 50:
            confirmations += 1

        # محاسبه confluence bonus
        if confirmations >= 4:
            confluence = 0.5
        elif confirmations >= 3:
            confluence = 0.4
        elif confirmations >= 2:
            confluence = 0.25
        elif confirmations >= 1:
            confluence = 0.1

        return confluence

    def _calculate_macd_score(self, row: pd.Series) -> float:
        """محاسبه MACD Analysis Score (0.85-1.2)"""
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        macd_hist = row.get('macd_hist', 0)

        if pd.isna(macd) or pd.isna(macd_signal):
            return 1.0

        # قدرت MACD
        if abs(macd - macd_signal) > 0:
            if pd.notna(macd_hist) and abs(macd_hist) > abs(macd) * 0.5:
                return 1.2  # Strong MACD momentum
            return 1.1

        return 1.0

    def _calculate_volatility_score(self, row: pd.Series) -> float:
        """
        محاسبه Volatility Score

        NEW: 0.6-1.5
        OLD: 0.5-1.0
        """
        atr = row.get('atr', 0)
        close = row.get('close', 1)

        if pd.isna(atr) or close == 0:
            return 1.0

        atr_percent = (atr / close) * 100

        if self.method == ScoringMethod.OLD:
            if atr_percent > 3:
                return 0.5  # Too volatile
            elif atr_percent > 2:
                return 0.8
            else:
                return 1.0
        else:  # NEW or HYBRID
            if atr_percent > 3:
                return 0.6
            elif atr_percent > 2:
                return 1.0
            elif atr_percent > 1:
                return 1.2
            else:
                return 1.5  # Low volatility can be good for trend following

    # === ضرایب اضافی OLD/HYBRID ===

    def _calculate_symbol_performance(self) -> float:
        """Symbol Performance Factor (0.8-1.3) - از Adaptive Learning"""
        # در بکتست سریع، این مقدار ثابت است
        return 1.0

    def _calculate_correlation_safety(self) -> float:
        """Correlation Safety Factor (0.5-1.0)"""
        # در بکتست سریع، این مقدار ثابت است
        return 1.0

    def _calculate_structure_score(
        self,
        row: pd.Series,
        htf_row: Optional[pd.Series],
        direction: str
    ) -> float:
        """Structure Score (0.8-1.2) - ساختار HTF"""
        if htf_row is None:
            return 1.0

        htf_trend = self._get_trend_score(htf_row, direction)

        if htf_trend > 80:
            return 1.2
        elif htf_trend > 60:
            return 1.1
        elif htf_trend < 40:
            return 0.8

        return 1.0

    def _calculate_harmonic_score(self, row: pd.Series) -> float:
        """Harmonic Pattern Score (1.0-1.2)"""
        # بررسی الگوهای هارمونیک در داده‌های precomputed
        harmonic_patterns = ['pattern_gartley', 'pattern_butterfly', 'pattern_bat', 'pattern_crab']

        for pattern in harmonic_patterns:
            if pattern in row and row[pattern] == 1:
                return 1.2

        return 1.0

    def _calculate_channel_score(self, row: pd.Series) -> float:
        """Price Channel Score (1.0-1.1)"""
        # بررسی موقعیت در کانال قیمتی
        close = row.get('close', 0)
        bb_upper = row.get('bb_upper', 0)
        bb_lower = row.get('bb_lower', 0)

        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return 1.0

        if bb_upper != bb_lower:
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            if 0.2 < bb_position < 0.8:
                return 1.1  # در میانه کانال

        return 1.0

    def _calculate_cyclical_score(self, row: pd.Series) -> float:
        """Cyclical Pattern Score (1.0-1.1)"""
        # در حال حاضر ثابت
        return 1.0

    def _calculate_final_score(self, result: ScoreResult) -> float:
        """محاسبه امتیاز نهایی"""

        if self.use_13_multipliers:
            # OLD/HYBRID: استفاده از 13 ضریب
            final = (
                result.base_score *
                result.timeframe_weight *
                result.trend_alignment *
                result.volume_confirmation *
                result.pattern_quality *
                (1.0 + result.confluence_score) *
                result.symbol_performance_factor *
                result.correlation_safety_factor *
                result.macd_analysis_score *
                result.structure_score *
                result.volatility_score *
                result.harmonic_pattern_score *
                result.price_channel_score *
                result.cyclical_pattern_score
            )
        else:
            # NEW: استفاده از 8 ضریب
            final = (
                result.base_score *
                result.timeframe_weight *
                result.trend_alignment *
                result.volume_confirmation *
                result.pattern_quality *
                (1.0 + result.confluence_score) *
                result.macd_analysis_score *
                result.volatility_score
            )

        return final

    def is_valid_signal(self, score: float) -> bool:
        """بررسی معتبر بودن سیگنال"""
        return score >= self.min_signal_score

    def get_signal_strength(self, score: float) -> str:
        """تعیین قدرت سیگنال"""
        if score >= self.strong_threshold:
            return 'strong'
        elif score >= self.min_signal_score:
            return 'medium'
        else:
            return 'weak'
