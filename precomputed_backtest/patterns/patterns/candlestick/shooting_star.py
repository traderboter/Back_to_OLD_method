"""
Shooting Star Pattern Detector

Detects Shooting Star candlestick pattern using TA-Lib CDLSHOOTINGSTAR.
Shooting Star is a bearish reversal pattern (opposite of Hammer).

Version: 4.0.0 (2025-10-26) - Simplified Architecture
- 🔥 REMOVED: Trend checking (now handled by separate Trend Analyzer)
- ✅ KEPT: TA-Lib CDLSHOOTINGSTAR detection
- ✅ KEPT: Multi-candle lookback (checks last 11 candles)
- ✅ KEPT: Recency-based scoring
- ✅ KEPT: Quality scoring system
- 📐 Architecture: Pattern detection separated from trend analysis

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 11 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-11 candles ago)

Version: 2.0.0 (2025-10-25) - MAJOR CHANGE
- 🔄 BREAKING: بازگشت به استفاده از TA-Lib CDLSHOOTINGSTAR
- 🔬 بر اساس تحقیقات در talib-test/:
  * TA-Lib نیاز به حداقل 12 کندل دارد (11 قبلی + 1 فعلی)
  * TA-Lib فقط کندل‌های BULLISH را تشخیص می‌دهد (close > open)
  * TA-Lib ترند را چک نمی‌کند
- 📊 Detection rate در BTC 1-hour data: 75/10543 = 0.71%
- ✅ نگه‌داری quality scoring system
- ⚠️ حذف manual physics detection (جایگزین با TA-Lib)

Why TA-Lib?
- مشکل قبلی: فقط 1 کندل به TA-Lib می‌دادیم → 0 detection
- حل: کل DataFrame (یا حداقل 12 کندل) → 75 detection ✅
- TA-Lib استاندارد صنعت و قابل اعتمادتر است

Quality Score:
- هرچه upper_shadow بلندتر → Quality بیشتر
- lower_shadow کوچکتر → Quality بیشتر
- Body position در پایین → Quality بیشتر
"""

SHOOTING_STAR_PATTERN_VERSION = "4.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class ShootingStarPattern(BasePattern):
    """
    Shooting Star candlestick pattern detector using TA-Lib.

    Characteristics (based on TA-Lib and research):
    - Bearish reversal pattern (opposite of Hammer)
    - BULLISH candle only (close > open) - TA-Lib limitation
    - Small body at bottom of candle
    - Long upper shadow (TA-Lib average: 62.8% of range)
    - Little to no lower shadow (TA-Lib average: 5.9% of range)

    Strength: 2/3 (Medium-Strong)

    TA-Lib Requirements:
    - Minimum 12 candles (11 previous + 1 current)
    - Upper shadow: ~35-95% of range (mean: 62.8%)
    - Body: ~2-50% of range (mean: 31.3%)
    - Lower shadow: ~0-33% of range (mean: 5.9%)
    - Detection rate on BTC 1-hour: 75/10543 = 0.71%

    Architecture Note:
    - This detector ONLY identifies Shooting Star patterns
    - Trend analysis is handled separately by Trend Analyzer
    - Final decision (LONG/SHORT) is made by orchestrator combining both

    Note: min_upper_shadow_pct, max_lower_shadow_pct, max_body_pct, max_body_position
    are kept for backward compatibility but NOT used in detect() (TA-Lib handles this).
    They are still used in quality_metrics calculation.
    """

    def __init__(
        self,
        config: Dict[str, Any] = None,
        min_upper_shadow_pct: float = None,
        max_lower_shadow_pct: float = None,
        max_body_pct: float = None,
        max_body_position: float = None
    ):
        """
        Initialize Shooting Star detector.

        Args:
            config: Configuration dictionary
            min_upper_shadow_pct: حداقل درصد upper shadow از range (default: 0.5 = 50%)
            max_lower_shadow_pct: حداکثر درصد lower shadow از range (default: 0.2 = 20%)
            max_body_pct: حداکثر درصد body از range (default: 0.3 = 30%)
            max_body_position: حداکثر موقعیت body (0.4 = bottom 40%)
        """
        super().__init__(config)

        # تعیین thresholds از مصادر مختلف - همه نسبت به full range
        self.min_upper_shadow_pct = (
            min_upper_shadow_pct
            if min_upper_shadow_pct is not None
            else config.get('shooting_star_min_upper_shadow_pct', 0.5) if config else 0.5
        )

        self.max_lower_shadow_pct = (
            max_lower_shadow_pct
            if max_lower_shadow_pct is not None
            else config.get('shooting_star_max_lower_shadow_pct', 0.2) if config else 0.2
        )

        self.max_body_pct = (
            max_body_pct
            if max_body_pct is not None
            else config.get('shooting_star_max_body_pct', 0.3) if config else 0.3
        )

        self.max_body_position = (
            max_body_position
            if max_body_position is not None
            else config.get('shooting_star_max_body_position', 0.4) if config else 0.4
        )

        self.version = SHOOTING_STAR_PATTERN_VERSION

    def _get_pattern_name(self) -> str:
        return "Shooting Star"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bearish"

    def _get_base_strength(self) -> int:
        return 2  # Medium-Strong pattern

    def detect(
        self,
        df: pd.DataFrame,
        open_col: str = 'open',
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> bool:
        """
        Detect Shooting Star pattern in last N candles using TA-Lib CDLSHOOTINGSTAR.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 11)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        TA-Lib Requirements (based on research in talib-test/):
        1. Minimum 12 candles (11 previous + 1 current) - CRITICAL!
        2. Detects BULLISH candles only (close > open)
        3. Does NOT check for uptrend context (we also don't - handled separately)

        Architecture:
        - This method ONLY detects Shooting Star patterns
        - Trend analysis is done separately by Trend Analyzer
        - Orchestrator combines both for final decision

        شرایط Shooting Star:
        - کندل BULLISH (close > open)
        - Upper shadow بلند (TA-Lib: میانگین 62.8%)
        - Body کوچک (TA-Lib: میانگین 31.3%)
        - Lower shadow کوچک (TA-Lib: میانگین 5.9%)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # TA-Lib needs minimum 12 candles
        if len(df) < 12:
            return False

        try:
            # Prepare data for TA-Lib
            # Use last 100 candles for performance (minimum 12, but more is fine)
            df_tail = df.tail(100)

            # Call TA-Lib CDLSHOOTINGSTAR
            # TA-Lib uses previous candles for context in its algorithm
            pattern = talib.CDLSHOOTINGSTAR(
                df_tail[open_col].values,
                df_tail[high_col].values,
                df_tail[low_col].values,
                df_tail[close_col].values
            )

            # NEW v3.0.0: Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(pattern))

            for i in range(lookback):
                # Check from newest to oldest
                # i=0: last candle (pattern[-1])
                # i=1: second to last (pattern[-2])
                # etc.
                idx = -(i + 1)

                if pattern[idx] != 0:
                    # Pattern found! Store position and return
                    self._last_detection_candles_ago = i
                    return True

            # Not found in last N candles
            return False

        except Exception as e:
            return False

    def _calculate_quality_metrics(self, candle: pd.Series, df: pd.DataFrame) -> Dict[str, Any]:
        """
        محاسبه معیارهای کیفیت Shooting Star.

        Quality Score (0-100):
        - بر اساس قدرت upper shadow
        - کوچکی lower shadow
        - موقعیت body
        - اندازه body

        Shooting Star Types:
        - Perfect: همه شرایط ایده‌آل (upper_shadow >= 70%, lower_shadow <= 5%)
        - Strong: شرایط خوب (upper_shadow >= 60%, lower_shadow <= 10%)
        - Standard: شرایط استاندارد (upper_shadow >= 50%, lower_shadow <= 20%)
        """
        open_price = candle['open']
        high = candle['high']
        low = candle['low']
        close = candle['close']

        # محاسبه اندازه‌ها
        body_size = abs(close - open_price)
        upper_shadow = high - max(open_price, close)
        lower_shadow = min(open_price, close) - low
        full_range = high - low

        if full_range == 0:
            return self._default_quality_metrics()

        # محاسبه درصدها نسبت به full range
        upper_shadow_pct = upper_shadow / full_range
        lower_shadow_pct = lower_shadow / full_range
        body_size_pct = body_size / full_range

        # 1. Upper Shadow Quality (0-100)
        # هرچه بلندتر، بهتر (0.5 → 50 points, 1.0 → 100 points)
        upper_shadow_score = min(100, upper_shadow_pct * 100 * 2)

        # 2. Lower Shadow Quality (0-100)
        # هرچه کوچکتر، بهتر (0.0 → 100 points, 0.2 → 0 points)
        lower_shadow_score = max(0, 100 - (lower_shadow_pct * 500))

        # 3. Body Position Quality (0-100)
        # body باید در پایین باشد
        body_bottom = min(open_price, close)
        body_position = (body_bottom - low) / full_range
        # برای Shooting Star: موقعیت پایین‌تر = بهتر
        body_position_score = (1.0 - body_position) * 100

        # 4. Body Size Quality (0-100)
        # body نباید خیلی بزرگ باشد (0.0 → 100 points, 0.3 → 0 points)
        body_size_score = max(0, 100 - (body_size_pct * 333))

        # 5. Overall Quality (weighted average)
        overall_quality = (
            0.40 * upper_shadow_score +      # مهم‌ترین معیار
            0.25 * lower_shadow_score +
            0.20 * body_position_score +
            0.15 * body_size_score
        )

        # 6. Shooting Star Type Detection
        shooting_star_type = self._detect_shooting_star_type(
            upper_shadow_pct,
            lower_shadow_pct,
            body_position
        )

        return {
            'quality_score': round(overall_quality, 2),
            'overall_quality': round(overall_quality, 2),
            'upper_shadow_score': round(upper_shadow_score, 2),
            'lower_shadow_score': round(lower_shadow_score, 2),
            'body_position_score': round(body_position_score, 2),
            'body_size_score': round(body_size_score, 2),
            'body_size': float(body_size),
            'upper_shadow': float(upper_shadow),
            'lower_shadow': float(lower_shadow),
            'full_range': float(full_range),
            'upper_shadow_pct': float(upper_shadow_pct),
            'lower_shadow_pct': float(lower_shadow_pct),
            'body_position': float(body_position),
            'body_size_pct': float(body_size_pct),
            'shooting_star_type': shooting_star_type
        }

    def _detect_shooting_star_type(
        self,
        upper_shadow_pct: float,
        lower_shadow_pct: float,
        body_position: float
    ) -> str:
        """تشخیص نوع Shooting Star بر اساس معیارها (percentage-based)."""

        # Perfect Shooting Star: شرایط ایده‌آل
        if (upper_shadow_pct >= 0.70 and
            lower_shadow_pct <= 0.05 and
            body_position <= 0.20):
            return "Perfect"

        # Strong Shooting Star: شرایط خوب
        if (upper_shadow_pct >= 0.60 and
            lower_shadow_pct <= 0.10 and
            body_position <= 0.30):
            return "Strong"

        # Standard Shooting Star: شرایط استاندارد
        return "Standard"

    def _default_quality_metrics(self) -> Dict[str, Any]:
        """مقادیر پیش‌فرض برای زمانی که محاسبه ممکن نیست."""
        return {
            'quality_score': 0.0,
            'overall_quality': 0.0,
            'upper_shadow_score': 0.0,
            'lower_shadow_score': 0.0,
            'body_position_score': 0.0,
            'body_size_score': 0.0,
            'body_size': 0.0,
            'upper_shadow': 0.0,
            'lower_shadow': 0.0,
            'full_range': 0.0,
            'upper_shadow_pct': 0.0,
            'lower_shadow_pct': 0.0,
            'body_position': 0.0,
            'body_size_pct': 0.0,
            'shooting_star_type': 'Unknown'
        }

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Shooting Star detection with quality metrics.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-11)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-11
            - recency_multiplier: based on config
            - confidence: Trading confidence (0-1), adjusted by recency
            - metadata: Detailed quality metrics + recency info
        """
        if len(df) == 0:
            return super()._get_detection_details(df)

        try:
            # Get detection position (set by detect())
            candles_ago = getattr(self, '_last_detection_candles_ago', 0)
            if candles_ago is None:
                candles_ago = 0

            # Get recency multiplier
            if candles_ago < len(self.recency_multipliers):
                recency_multiplier = self.recency_multipliers[candles_ago]
            else:
                recency_multiplier = 0.0  # Too old

            # Get the candle where pattern was detected
            candle_idx = -(candles_ago + 1)
            detected_candle = df.iloc[candle_idx]

            # محاسبه معیارهای کیفیت
            quality_metrics = self._calculate_quality_metrics(detected_candle, df)

            # محاسبه base confidence بر اساس overall_quality
            # overall_quality: 0-100 → base_confidence: 0.4-0.95
            base_confidence = 0.4 + (quality_metrics['overall_quality'] / 100) * 0.55
            base_confidence = max(0.4, min(0.95, base_confidence))

            # NEW v3.0.0: Adjust confidence with recency multiplier
            # Recent patterns → higher confidence
            # Older patterns → lower confidence
            adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

            return {
                'location': 'current' if candles_ago == 0 else 'recent',
                'candles_ago': candles_ago,
                'recency_multiplier': recency_multiplier,
                'confidence': adjusted_confidence,
                'metadata': {
                    **quality_metrics,
                    'thresholds': {
                        'min_upper_shadow_pct': float(self.min_upper_shadow_pct),
                        'max_lower_shadow_pct': float(self.max_lower_shadow_pct),
                        'max_body_pct': float(self.max_body_pct),
                        'max_body_position': float(self.max_body_position)
                    },
                    'detector_version': SHOOTING_STAR_PATTERN_VERSION,
                    'price_info': {
                        'open': float(detected_candle['open']),
                        'high': float(detected_candle['high']),
                        'low': float(detected_candle['low']),
                        'close': float(detected_candle['close'])
                    },
                    'recency_info': {
                        'candles_ago': candles_ago,
                        'multiplier': recency_multiplier,
                        'lookback_window': self.lookback_window,
                        'base_confidence': base_confidence,
                        'adjusted_confidence': adjusted_confidence
                    }
                }
            }
        except Exception:
            return super()._get_detection_details(df)
