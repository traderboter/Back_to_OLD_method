"""
Triangle Pattern Detector

Detects Ascending, Descending, and Symmetrical Triangle chart patterns.
These are continuation/breakout patterns.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class TrianglePattern(BasePattern):
    """
    Triangle chart pattern detector.

    Characteristics:
    - Ascending Triangle: Flat top, rising bottom (bullish)
    - Descending Triangle: Declining top, flat bottom (bearish)
    - Symmetrical Triangle: Converging lines (neutral until breakout)

    Strength: 2/3 (Medium)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Initialize instance variables BEFORE calling super().__init__
        # because _get_pattern_name() and _get_direction() will be called during parent init
        self._detected_type = None  # 'ascending', 'descending', or 'symmetrical'
        # افزایش threshold از 0.0001 به 0.005 برای تشخیص راحت‌تر (50x بیشتر)
        self.slope_threshold = config.get('triangle_slope_threshold', 0.005) if config else 0.005
        self.min_lookback = config.get('triangle_min_lookback', 20) if config else 20

        super().__init__(config)

    def _get_pattern_name(self) -> str:
        if self._detected_type == 'ascending':
            return "Ascending Triangle"
        elif self._detected_type == 'descending':
            return "Descending Triangle"
        elif self._detected_type == 'symmetrical':
            return "Symmetrical Triangle"
        return "Triangle"

    def _get_pattern_type(self) -> str:
        return "chart"

    def _get_direction(self) -> str:
        if self._detected_type == 'ascending':
            return 'bullish'
        elif self._detected_type == 'descending':
            return 'bearish'
        return 'neutral'  # Symmetrical

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
        """Detect Triangle pattern."""
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

            # Upper trendline (resistance)
            upper_slope = np.polyfit(x, highs, 1)[0]

            # Lower trendline (support)
            lower_slope = np.polyfit(x, lows, 1)[0]

            # Ascending triangle: flat top, rising bottom
            if abs(upper_slope) < self.slope_threshold and lower_slope > self.slope_threshold:
                self._detected_type = 'ascending'
                return True

            # Descending triangle: declining top, flat bottom
            elif upper_slope < -self.slope_threshold and abs(lower_slope) < self.slope_threshold:
                self._detected_type = 'descending'
                return True

            # Symmetrical triangle: converging lines
            elif upper_slope < -self.slope_threshold and lower_slope > self.slope_threshold:
                self._detected_type = 'symmetrical'
                return True

            return False

        except Exception as e:
            return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get additional details about triangle detection."""
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

            # Calculate convergence (distance between lines)
            upper_line = np.polyval(upper_coeffs, x)
            lower_line = np.polyval(lower_coeffs, x)

            # Convergence at start and end
            start_gap = upper_line[0] - lower_line[0]
            end_gap = upper_line[-1] - lower_line[-1]

            convergence_ratio = (start_gap - end_gap) / start_gap if start_gap > 0 else 0

            # Calculate completion percentage
            completion = min(convergence_ratio, 0.9)

            return {
                'location': 'forming',
                'candles_ago': 0,
                'confidence': min(0.60 + (completion * 0.20), 0.85),
                'metadata': {
                    'upper_slope': float(upper_slope),
                    'lower_slope': float(lower_slope),
                    'convergence_ratio': float(convergence_ratio),
                    'completion': float(completion),
                    'pattern_type': self._detected_type
                }
            }

        except Exception:
            pass

        return super()._get_detection_details(df)

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """Determine actual direction."""
        if self._detected_type == 'ascending':
            return 'bullish'
        elif self._detected_type == 'descending':
            return 'bearish'
        return 'neutral'
