"""
Wedge Pattern Detector

Detects Rising Wedge and Falling Wedge chart patterns.
These are reversal patterns.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class WedgePattern(BasePattern):
    """
    Wedge chart pattern detector.

    Characteristics:
    - Rising Wedge: Both lines rising, upper faster (bearish)
    - Falling Wedge: Both lines falling, lower faster (bullish)

    Strength: 2/3 (Medium)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Initialize instance variables BEFORE calling super().__init__
        # because _get_pattern_name() will be called during parent init
        self._detected_type = None  # 'rising' or 'falling'
        self.min_lookback = config.get('wedge_min_lookback', 20) if config else 20

        super().__init__(config)

    def _get_pattern_name(self) -> str:
        if self._detected_type == 'rising':
            return "Rising Wedge"
        elif self._detected_type == 'falling':
            return "Falling Wedge"
        return "Wedge"

    def _get_pattern_type(self) -> str:
        return "chart"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish (falling) or bearish (rising)

    def _get_base_strength(self) -> int:
        return 2  # Medium strength

    def detect(
        self,
        df: pd.DataFrame,
        open_col: str = 'open',
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> bool:
        """Detect Wedge pattern."""
        if not self._validate_dataframe(df):
            return False

        if len(df) < self.min_lookback:
            return False

        try:
            # Use recent data
            recent_df = df.tail(self.min_lookback)
            highs = recent_df[high_col].values
            lows = recent_df[low_col].values

            # Calculate trendlines
            x = np.arange(len(highs))

            upper_slope = np.polyfit(x, highs, 1)[0]
            lower_slope = np.polyfit(x, lows, 1)[0]

            # Rising wedge: both lines rising, upper faster (bearish)
            if upper_slope > 0 and lower_slope > 0 and upper_slope > lower_slope * 1.2:
                self._detected_type = 'rising'
                return True

            # Falling wedge: both lines falling, lower faster (bullish)
            elif upper_slope < 0 and lower_slope < 0 and lower_slope < upper_slope * 1.2:
                self._detected_type = 'falling'
                return True

            return False

        except Exception as e:
            return False

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """Determine actual direction."""
        if self._detected_type == 'falling':
            return 'bullish'
        elif self._detected_type == 'rising':
            return 'bearish'
        return 'bearish'

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get additional details about wedge detection."""
        try:
            recent_df = df.tail(self.min_lookback)
            highs = recent_df['high'].values
            lows = recent_df['low'].values

            x = np.arange(len(highs))

            # Calculate slopes
            upper_coeffs = np.polyfit(x, highs, 1)
            lower_coeffs = np.polyfit(x, lows, 1)

            upper_slope = upper_coeffs[0]
            lower_slope = lower_coeffs[0]

            # Calculate slope ratio (how much faster one line moves)
            if self._detected_type == 'rising':
                slope_ratio = upper_slope / lower_slope if lower_slope != 0 else 1
            else:
                slope_ratio = lower_slope / upper_slope if upper_slope != 0 else 1

            # Calculate lines
            upper_line = np.polyval(upper_coeffs, x)
            lower_line = np.polyval(lower_coeffs, x)

            # Convergence
            start_gap = upper_line[0] - lower_line[0]
            end_gap = upper_line[-1] - lower_line[-1]

            convergence = (start_gap - end_gap) / start_gap if start_gap > 0 else 0

            return {
                'location': 'forming',
                'candles_ago': 0,
                'confidence': min(0.50 + (convergence * 0.30), 0.85),
                'metadata': {
                    'upper_slope': float(upper_slope),
                    'lower_slope': float(lower_slope),
                    'slope_ratio': float(slope_ratio),
                    'convergence': float(convergence),
                    'wedge_type': self._detected_type
                }
            }

        except Exception:
            pass

        return super()._get_detection_details(df)
