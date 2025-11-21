"""
Engulfing Pattern Detector

Detects Bullish and Bearish Engulfing candlestick patterns using TALib.
Engulfing patterns are strong reversal patterns.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 2 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-2 candles ago)

Version: 2.0.0 (2025-10-25) - MAJOR CHANGE
- 🔄 BREAKING: Fix TA-Lib integration (3+ candles required)
- 🔬 بر اساس تحقیقات در talib-test/:
  * TA-Lib نیاز به حداقل 3 کندل دارد (2 قبلی + 1 فعلی)
  * با کمتر از 3 کندل: هیچ تشخیصی نمی‌دهد
- 📊 Detection rate در BTC 1-hour data: 1714/10543 = 16.26%
- ✅ بیشترین detection rate در بین همه الگوها!
"""

ENGULFING_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class EngulfingPattern(BasePattern):
    """
    Engulfing candlestick pattern detector using TA-Lib.

    Characteristics:
    - Can be bullish or bearish
    - Second candle completely engulfs first candle's body
    - Strong reversal signal
    - Direction determined by engulfing candle color

    Strength: 3/3 (Strong)

    TA-Lib Requirements (based on research in talib-test/):
    - Minimum 3 candles (2 previous + 1 current) - CRITICAL!
    - Detection rate on BTC 1-hour: 1714/10543 = 16.26%
    - Highest detection rate among all patterns!
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Engulfing detector."""
        super().__init__(config)
        self.version = ENGULFING_PATTERN_VERSION

    def _get_pattern_name(self) -> str:
        return "Engulfing"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish or bearish

    def _get_base_strength(self) -> int:
        return 3  # Strong pattern

    def _get_talib_result(self, df: pd.DataFrame) -> np.ndarray:
        """Get TALib CDLENGULFING result (helper method to avoid duplicate calls)."""
        try:
            result = talib.CDLENGULFING(
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values
            )
            return result
        except Exception:
            return np.array([])

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
        Detect Engulfing pattern in last N candles using TA-Lib CDLENGULFING.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 2)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        TA-Lib Requirements (based on research in talib-test/):
        1. Minimum 3 candles (2 previous + 1 current) - CRITICAL!
        2. Can detect both bullish and bearish engulfing
        3. Detection rate: 16.26% (highest among all patterns!)

        Returns:
            bool: True if Engulfing pattern detected in last N candles
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # TA-Lib needs minimum 3 candles
        if len(df) < 3:
            return False

        try:
            # Use TALib to detect
            # Pass full DataFrame - TA-Lib uses previous candles for context
            result = talib.CDLENGULFING(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values
            )

            # NEW v3.0.0: Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(result))

            for i in range(lookback):
                # Check from newest to oldest
                # i=0: last candle (result[-1])
                # i=1: second to last (result[-2])
                # etc.
                idx = -(i + 1)

                # result values: +100 (bullish), -100 (bearish), 0 (no pattern)
                if result[idx] != 0:
                    # Pattern found! Store position
                    self._last_detection_candles_ago = i
                    return True

            # Not found in last N candles
            return False

        except Exception as e:
            return False

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """Determine actual direction (bullish or bearish)."""
        try:
            # Use helper method to get TALib result
            result = self._get_talib_result(df)

            if len(result) == 0:
                return 'bullish'

            # Positive = bullish, negative = bearish
            return 'bullish' if result[-1] > 0 else 'bearish'

        except Exception:
            return 'bullish'

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Engulfing detection with recency information.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-N)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-N
            - recency_multiplier: based on config
            - confidence: Trading confidence (0-1), adjusted by recency
            - metadata: Detailed metrics + recency info
        """
        # Validate minimum candles
        if len(df) < 2:
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

            # Get the two candles where pattern was detected
            # For Engulfing, we need the engulfing candle and the one before it
            candle_idx = -(candles_ago + 1)
            detected_candle = df.iloc[candle_idx]
            prev_candle = df.iloc[candle_idx - 1]

            # Calculate body sizes
            prev_body = abs(prev_candle['close'] - prev_candle['open'])
            curr_body = abs(detected_candle['close'] - detected_candle['open'])
            prev_full_range = prev_candle['high'] - prev_candle['low']
            curr_full_range = detected_candle['high'] - detected_candle['low']

            # Engulfing ratio (how much bigger is current body)
            # Use safe division: minimum threshold is 30% of candle's full range
            safe_prev_body = max(prev_body, prev_full_range * 0.3) if prev_full_range > 0 else 0.0001
            engulfing_ratio = curr_body / safe_prev_body if safe_prev_body > 0 else 1

            # Determine direction using TALib result
            result = self._get_talib_result(df)
            if len(result) > candles_ago:
                direction = 'bullish' if result[candle_idx] > 0 else 'bearish'
            else:
                direction = 'bullish'

            # Calculate base confidence
            base_confidence = min(0.75 + (engulfing_ratio / 10), 0.95)

            # NEW v3.0.0: Adjust confidence with recency multiplier
            adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

            return {
                'location': 'current' if candles_ago == 0 else 'recent',
                'candles_ago': candles_ago,
                'recency_multiplier': recency_multiplier,
                'confidence': adjusted_confidence,
                'metadata': {
                    'prev_body_size': float(prev_body),
                    'curr_body_size': float(curr_body),
                    'prev_full_range': float(prev_full_range),
                    'curr_full_range': float(curr_full_range),
                    'engulfing_ratio': float(engulfing_ratio),
                    'pattern_direction': direction,
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
