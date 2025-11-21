"""
Mat Hold Pattern Detector

Detects Mat Hold candlestick pattern using TALib.
Mat Hold is a bullish continuation pattern.

Version: 1.1.1 (2025-10-27) - Fix BasePattern Compatibility
- Fixed __init__ signature to match BasePattern interface
- Now properly accepts config dictionary as first parameter
- Backward compatible: penetration can be passed directly or via config

Version: 1.1.0 (2025-10-27) - Add Penetration Parameter
- Added configurable penetration parameter (default: 0.3)
- Previous version was too strict with TALib's default 0.5
- Lower penetration makes pattern detection more practical

Version: 1.0.0 (2025-10-26) - Initial Implementation
- 5-candle bullish continuation pattern
- Shows brief pullback before uptrend continues
- Confirms bullish trend strength
"""

MAT_HOLD_PATTERN_VERSION = "1.1.1"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class MatHoldPattern(BasePattern):
    """
    Mat Hold candlestick pattern detector.

    Characteristics:
    - 5-candle bullish continuation pattern
    - Pattern structure:
      1. Long bullish candle (strong uptrend)
      2. Small gap up, can be bullish or bearish
      3-4. Small candles pulling back (but staying above candle 1 close)
      5. Strong bullish candle closing above all previous candles
    - Confirms bullish trend continuation
    - Similar to Rising Three Methods but with gap

    Strength: 3/3 (Strong) - trend continuation
    Direction: Bullish only

    Parameters:
    - penetration: Percentage of penetration required (0.0-1.0)
                   Lower values = more detections (less strict)
                   Higher values = fewer detections (more strict)
                   Default: 0.3 (30% penetration)
    """

    def __init__(self, config: Dict[str, Any] = None, penetration: float = None):
        """
        Initialize Mat Hold pattern detector.

        Args:
            config: Configuration dictionary (inherited from BasePattern)
            penetration: Penetration percentage for TALib (0.0-1.0, default: 0.3)
                        Lower = more lenient detection (more patterns found)
                        Higher = stricter detection (fewer patterns found)
                        Can also be set via config['mat_hold_penetration']
        """
        super().__init__(config)

        # Determine penetration from multiple sources (explicit arg > config > default)
        if penetration is not None:
            self.penetration = penetration
        elif config and 'mat_hold_penetration' in config:
            self.penetration = config['mat_hold_penetration']
        else:
            self.penetration = 0.3  # Default value

        # Clamp between 0 and 1
        self.penetration = max(0.0, min(1.0, self.penetration))

    def _get_pattern_name(self) -> str:
        return "Mat Hold"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bullish"

    def _get_base_strength(self) -> int:
        return 3  # Strong pattern - confirms uptrend

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
        Detect Mat Hold pattern in last N candles using TALib.

        Multi-candle lookback detection:
        - Checks last N candles (lookback_window, default: 15)
        - Stores which candle has the pattern
        - Enables recency-based scoring

        Based on research:
        - Minimum 17 candles required (12 lookback + 5 pattern)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # Need minimum 17 candles
        if len(df) < 17:
            return False

        try:
            result = talib.CDLMATHOLD(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values,
                penetration=self.penetration
            )

            # Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(result))

            for i in range(lookback):
                idx = -(i + 1)
                if result[idx] != 0:
                    self._last_detection_candles_ago = i
                    return True

            return False

        except Exception as e:
            return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Mat Hold detection with recency information.
        """
        if len(df) < 5:
            return super()._get_detection_details(df)

        # Get detection position
        candles_ago = getattr(self, '_last_detection_candles_ago', 0)
        if candles_ago is None:
            candles_ago = 0

        # Get recency multiplier
        if candles_ago < len(self.recency_multipliers):
            recency_multiplier = self.recency_multipliers[candles_ago]
        else:
            recency_multiplier = 0.0

        # Get the five candles where pattern was detected
        pattern_end_idx = len(df) - candles_ago
        pattern_start_idx = pattern_end_idx - 5

        # Ensure we have valid indices
        if pattern_start_idx < 0 or pattern_end_idx > len(df):
            return super()._get_detection_details(df)

        candles = df.iloc[pattern_start_idx:pattern_end_idx].copy()

        # Double check we have exactly 5 candles
        if len(candles) != 5:
            return super()._get_detection_details(df)

        # Calculate body sizes
        bodies = [abs(candles.iloc[i]['close'] - candles.iloc[i]['open']) for i in range(5)]
        full_ranges = [candles.iloc[i]['high'] - candles.iloc[i]['low'] for i in range(5)]
        avg_body = sum(bodies) / 5
        avg_full_range = sum(full_ranges) / 5

        # Check for gap between candle 1 and 2
        gap_size = candles.iloc[1]['open'] - candles.iloc[0]['close']
        has_gap = gap_size > 0

        # Strong candles (1st and 5th) should be larger
        strong_candle_size = (bodies[0] + bodies[4]) / 2
        pullback_size = (bodies[1] + bodies[2] + bodies[3]) / 3

        # Continuation strength
        continuation_strength = strong_candle_size / pullback_size if pullback_size > 0 else 1.0

        # Base confidence
        # Higher when:
        # 1. Strong candles are much larger
        # 2. Gap is present
        gap_bonus = 0.05 if has_gap else 0.0
        base_confidence = min(0.75 + (min(continuation_strength, 3.0) / 30.0) + gap_bonus, 0.95)

        # Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': adjusted_confidence,
            'metadata': {
                'body_sizes': [float(b) for b in bodies],
                'full_ranges': [float(r) for r in full_ranges],
                'avg_body': float(avg_body),
                'avg_full_range': float(avg_full_range),
                'gap_size': float(gap_size),
                'has_gap': bool(has_gap),
                'strong_candle_size': float(strong_candle_size),
                'pullback_size': float(pullback_size),
                'continuation_strength': float(continuation_strength),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
