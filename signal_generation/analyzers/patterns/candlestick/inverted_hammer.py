"""
Inverted Hammer Pattern Detector

Detects Inverted Hammer candlestick pattern using TALib.
Inverted Hammer is a bullish reversal pattern.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 11 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-11 candles ago)

Version: 2.0.0 (2025-10-25) - MAJOR CHANGE
- 🔄 BREAKING: Fix TA-Lib integration (12+ candles required)
- 🔬 بر اساس تحقیقات در talib-test/:
  * TA-Lib نیاز به حداقل 12 کندل دارد (11 قبلی + 1 فعلی)
  * با کمتر از 12 کندل: هیچ تشخیصی نمی‌دهد
- 📊 Detection rate در BTC 1-hour data: 59/10543 = 0.56%
"""

INVERTED_HAMMER_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class InvertedHammerPattern(BasePattern):
    """
    Inverted Hammer candlestick pattern detector using TA-Lib.

    Characteristics:
    - Bullish reversal pattern
    - Small body at bottom of candle
    - Long upper shadow (at least 2x body)
    - Little to no lower shadow
    - Best when appears after downtrend

    Strength: 2/3 (Medium)

    TA-Lib Requirements (based on research in talib-test/):
    - Minimum 12 candles (11 previous + 1 current) - CRITICAL!
    - Detection rate on BTC 1-hour: 59/10543 = 0.56%
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Inverted Hammer detector."""
        super().__init__(config)
        self.version = INVERTED_HAMMER_PATTERN_VERSION

    def _get_pattern_name(self) -> str:
        return "Inverted Hammer"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bullish"

    def _get_base_strength(self) -> int:
        return 2

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
        Detect Inverted Hammer pattern in last N candles using TA-Lib CDLINVERTEDHAMMER.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 11)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        TA-Lib Requirements (based on research in talib-test/):
        1. Minimum 12 candles (11 previous + 1 current) - CRITICAL!
        2. Detection rate: 0.56%

        Returns:
            bool: True if Inverted Hammer pattern detected in last N candles
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # TA-Lib needs minimum 12 candles
        if len(df) < 12:
            return False

        try:
            # Use TALib to detect
            # Pass full DataFrame - TA-Lib uses previous candles for context
            result = talib.CDLINVERTEDHAMMER(
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

                if result[idx] != 0:
                    # Pattern found! Store position
                    self._last_detection_candles_ago = i
                    return True

            # Not found in last N candles
            return False

        except Exception as e:
            return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Inverted Hammer detection.

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
            - metadata: Detailed metrics + recency info
        """
        # Validate dataframe
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

            # Calculate shadow ratios
            body_size = abs(detected_candle['close'] - detected_candle['open'])
            lower_shadow = min(detected_candle['open'], detected_candle['close']) - detected_candle['low']
            upper_shadow = detected_candle['high'] - max(detected_candle['open'], detected_candle['close'])
            full_range = detected_candle['high'] - detected_candle['low']

            # Use full_range instead of body_size to avoid zero/very small body issues
            shadow_ratio = upper_shadow / full_range if full_range > 0 else 0

            # Calculate base confidence
            base_confidence = min(0.7 + (shadow_ratio / 10), 0.95)

            # NEW v3.0.0: Adjust confidence with recency multiplier
            adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

            return {
                'location': 'current' if candles_ago == 0 else 'recent',
                'candles_ago': candles_ago,
                'recency_multiplier': recency_multiplier,
                'confidence': adjusted_confidence,
                'metadata': {
                    'body_size': float(body_size),
                    'lower_shadow': float(lower_shadow),
                    'upper_shadow': float(upper_shadow),
                    'full_range': float(full_range),
                    'shadow_ratio': float(shadow_ratio),
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
