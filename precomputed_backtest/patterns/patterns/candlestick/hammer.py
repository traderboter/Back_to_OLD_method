"""
Hammer Pattern Detector

Detects Hammer candlestick pattern using TA-Lib CDLHAMMER.
Hammer is a bullish reversal pattern.

Version: 4.0.0 (2025-10-26) - Simplified Architecture
- 🔥 REMOVED: Trend checking (now handled by separate Trend Analyzer)
- ✅ KEPT: TA-Lib CDLHAMMER detection
- ✅ KEPT: Multi-candle lookback (checks last 5 candles)
- ✅ KEPT: Recency-based scoring
- ✅ KEPT: Quality scoring system
- 📐 Architecture: Pattern detection separated from trend analysis

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 5 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-5 candles ago)

Version: 2.0.0 (2025-10-25) - MAJOR CHANGE
- 🔄 BREAKING: بازگشت به استفاده از TA-Lib CDLHAMMER
- 🔬 بر اساس تحقیقات در talib-test/:
  * TA-Lib نیاز به حداقل 12 کندل دارد (11 قبلی + 1 فعلی)
  * TA-Lib هم کندل‌های BEARISH و هم BULLISH را تشخیص می‌دهد
  * TA-Lib ترند را چک نمی‌کند
- 📊 Detection rate در BTC 1-hour data: 277/10543 = 2.63%
- ⭐ 3.7× رایج‌تر از Shooting Star!
- ✅ نگه‌داری quality scoring system
- ⚠️ حذف manual physics detection (جایگزین با TA-Lib)

Why TA-Lib?
- مشکل قبلی: فقط 1 کندل به TA-Lib می‌دادیم → 0 detection
- حل: کل DataFrame (یا حداقل 12 کندل) → 277 detection ✅
- TA-Lib استاندارد صنعت و قابل اعتمادتر است

Quality Score:
- هرچه lower_shadow بلندتر → Quality بیشتر
- upper_shadow کوچکتر → Quality بیشتر
- Body position در بالا → Quality بیشتر
"""

HAMMER_PATTERN_VERSION = "4.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class HammerPattern(BasePattern):
    """
    Hammer candlestick pattern detector using TA-Lib.

    Characteristics (based on TA-Lib and research):
    - Bullish reversal pattern (opposite of Shooting Star)
    - Accepts both BEARISH and BULLISH candles (TA-Lib feature)
    - Small body at top of candle
    - Long lower shadow (TA-Lib average: 63.9% of range)
    - Little to no upper shadow (TA-Lib average: 8.0% of range)

    Strength: 2/3 (Medium-Strong)

    TA-Lib Requirements:
    - Minimum 12 candles (11 previous + 1 current)
    - Lower shadow: ~21-99% of range (mean: 63.9%)
    - Body: ~0.3-50% of range (mean: 28.2%)
    - Upper shadow: ~0-57% of range (mean: 8.0%)
    - Detection rate on BTC 1-hour: 277/10543 = 2.63%

    Architecture Note:
    - This detector ONLY identifies Hammer patterns
    - Trend analysis is handled separately by Trend Analyzer
    - Final decision (LONG/SHORT) is made by orchestrator combining both

    Note: min_lower_shadow_ratio, max_upper_shadow_ratio, min_body_position
    are kept for backward compatibility but NOT used in detect() (TA-Lib handles this).
    They are still used in quality_metrics calculation.
    """

    def __init__(
        self,
        config: Dict[str, Any] = None,
        min_lower_shadow_ratio: float = None,
        max_upper_shadow_ratio: float = None,
        min_body_position: float = None
    ):
        """
        Initialize Hammer detector.

        Args:
            config: Configuration dictionary
            min_lower_shadow_ratio: حداقل نسبت lower shadow/body (default: 2.0) - NOT used in detect()
            max_upper_shadow_ratio: حداکثر نسبت upper shadow/body (default: 0.1) - NOT used in detect()
            min_body_position: حداقل موقعیت body (0.66 = top 1/3) - NOT used in detect()
        """
        super().__init__(config)

        # تعیین thresholds از مصادر مختلف (kept for backward compatibility)
        self.min_lower_shadow_ratio = (
            min_lower_shadow_ratio
            if min_lower_shadow_ratio is not None
            else config.get('hammer_min_lower_shadow_ratio', 2.0) if config else 2.0
        )

        self.max_upper_shadow_ratio = (
            max_upper_shadow_ratio
            if max_upper_shadow_ratio is not None
            else config.get('hammer_max_upper_shadow_ratio', 0.1) if config else 0.1
        )

        self.min_body_position = (
            min_body_position
            if min_body_position is not None
            else config.get('hammer_min_body_position', 0.66) if config else 0.66
        )

        self.version = HAMMER_PATTERN_VERSION

    def _get_pattern_name(self) -> str:
        return "Hammer"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bullish"

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
        Detect Hammer pattern in last N candles using TA-Lib CDLHAMMER.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 5)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        TA-Lib Requirements (based on research in talib-test/):
        1. Minimum 12 candles (11 previous + 1 current) - CRITICAL!
        2. Detects both BEARISH and BULLISH candles
        3. Does NOT check for downtrend context (we also don't - handled separately)

        Architecture:
        - This method ONLY detects Hammer patterns
        - Trend analysis is done separately by Trend Analyzer
        - Orchestrator combines both for final decision

        شرایط Hammer:
        - Lower shadow بلند (TA-Lib: میانگین 63.9%)
        - Body کوچک (TA-Lib: میانگین 28.2%)
        - Upper shadow کوچک (TA-Lib: میانگین 8.0%)
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

            # Call TA-Lib CDLHAMMER
            # TA-Lib uses previous candles for context in its algorithm
            pattern = talib.CDLHAMMER(
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
        محاسبه معیارهای کیفیت Hammer.

        Quality Score (0-100):
        - بر اساس قدرت lower shadow
        - کوچکی upper shadow
        - موقعیت body
        - اندازه body

        Hammer Types:
        - Perfect: همه شرایط ایده‌آل (lower_shadow >= 3x body, no upper shadow)
        - Strong: شرایط خوب (lower_shadow >= 2.5x body)
        - Standard: شرایط استاندارد (lower_shadow >= 2x body)
        """
        open_price = candle['open']
        high = candle['high']
        low = candle['low']
        close = candle['close']

        # محاسبه اندازه‌ها
        body_size = abs(close - open_price)
        lower_shadow = min(open_price, close) - low
        upper_shadow = high - max(open_price, close)
        full_range = high - low

        if full_range == 0:
            return self._default_quality_metrics()

        body_for_ratio = max(body_size, full_range * 0.01)

        # 1. Lower Shadow Quality (0-100)
        # هرچه بلندتر، بهتر
        lower_shadow_ratio = lower_shadow / body_for_ratio
        lower_shadow_score = min(100, (lower_shadow_ratio / 4.0) * 100)

        # 2. Upper Shadow Quality (0-100)
        # هرچه کوچکتر، بهتر
        upper_shadow_ratio = upper_shadow / body_for_ratio
        upper_shadow_score = max(0, 100 - (upper_shadow_ratio * 100))

        # 3. Body Position Quality (0-100)
        # body باید در بالا باشد
        body_bottom = min(open_price, close)
        body_position = (body_bottom - low) / full_range
        body_position_score = body_position * 100

        # 4. Body Size Quality (0-100)
        # body نباید خیلی بزرگ باشد
        body_size_ratio = body_size / full_range
        body_size_score = max(0, 100 - (body_size_ratio * 100))

        # 5. Overall Quality (weighted average)
        overall_quality = (
            0.40 * lower_shadow_score +      # مهم‌ترین معیار
            0.25 * upper_shadow_score +
            0.20 * body_position_score +
            0.15 * body_size_score
        )

        # 6. Hammer Type Detection
        hammer_type = self._detect_hammer_type(
            lower_shadow_ratio,
            upper_shadow_ratio,
            body_position
        )

        return {
            'quality_score': round(overall_quality, 2),
            'overall_quality': round(overall_quality, 2),
            'lower_shadow_score': round(lower_shadow_score, 2),
            'upper_shadow_score': round(upper_shadow_score, 2),
            'body_position_score': round(body_position_score, 2),
            'body_size_score': round(body_size_score, 2),
            'body_size': float(body_size),
            'lower_shadow': float(lower_shadow),
            'upper_shadow': float(upper_shadow),
            'full_range': float(full_range),
            'lower_shadow_ratio': float(lower_shadow_ratio),
            'upper_shadow_ratio': float(upper_shadow_ratio),
            'body_position': float(body_position),
            'body_size_ratio': float(body_size_ratio),
            'hammer_type': hammer_type
        }

    def _detect_hammer_type(
        self,
        lower_shadow_ratio: float,
        upper_shadow_ratio: float,
        body_position: float
    ) -> str:
        """تشخیص نوع Hammer بر اساس معیارها."""

        # Perfect Hammer: شرایط ایده‌آل
        if (lower_shadow_ratio >= 3.0 and
            upper_shadow_ratio <= 0.05 and
            body_position >= 0.80):
            return "Perfect"

        # Strong Hammer: شرایط خوب
        if (lower_shadow_ratio >= 2.5 and
            upper_shadow_ratio <= 0.1 and
            body_position >= 0.70):
            return "Strong"

        # Standard Hammer: شرایط استاندارد
        return "Standard"

    def _default_quality_metrics(self) -> Dict[str, Any]:
        """مقادیر پیش‌فرض برای زمانی که محاسبه ممکن نیست."""
        return {
            'quality_score': 0.0,
            'overall_quality': 0.0,
            'lower_shadow_score': 0.0,
            'upper_shadow_score': 0.0,
            'body_position_score': 0.0,
            'body_size_score': 0.0,
            'body_size': 0.0,
            'lower_shadow': 0.0,
            'upper_shadow': 0.0,
            'full_range': 0.0,
            'lower_shadow_ratio': 0.0,
            'upper_shadow_ratio': 0.0,
            'body_position': 0.0,
            'body_size_ratio': 0.0,
            'hammer_type': 'Unknown'
        }

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Hammer detection with quality metrics.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-5)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-5
            - recency_multiplier: 0.5-1.0
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
                        'min_lower_shadow_ratio': float(self.min_lower_shadow_ratio),
                        'max_upper_shadow_ratio': float(self.max_upper_shadow_ratio),
                        'min_body_position': float(self.min_body_position)
                    },
                    'detector_version': HAMMER_PATTERN_VERSION,
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
