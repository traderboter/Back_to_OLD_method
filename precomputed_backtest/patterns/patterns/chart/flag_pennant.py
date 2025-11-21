"""
Flag and Pennant Pattern Detector

Detects Flag and Pennant chart patterns.
These are strong continuation patterns that form after a sharp price move (flagpole).

Flag: Small rectangular consolidation against the trend
Pennant: Small triangular consolidation after a sharp move

Both indicate a brief pause before trend continuation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from scipy.signal import find_peaks

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class FlagPennantPattern(BasePattern):
    """
    Flag and Pennant chart pattern detector.

    Characteristics:
    - Flag: Rectangular consolidation (small channel against the trend)
      * Bullish Flag: Downward sloping channel after uptrend
      * Bearish Flag: Upward sloping channel after downtrend

    - Pennant: Small symmetrical triangle after sharp move
      * Similar to symmetrical triangle but smaller and shorter duration

    Both patterns:
    - Require a strong prior move (flagpole)
    - Brief consolidation period (3-15 candles)
    - High probability of continuation

    Strength: 3/3 (Strong continuation pattern)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Initialize instance variables BEFORE calling super().__init__
        self._detected_type = None  # 'bullish_flag', 'bearish_flag', 'bullish_pennant', 'bearish_pennant'
        self._flagpole_direction = None  # 'up' or 'down'

        # Configuration
        self.min_flagpole_size = config.get('flag_min_flagpole_size', 0.02) if config else 0.02  # 2% minimum move
        self.max_consolidation_candles = config.get('flag_max_consolidation', 15) if config else 15
        self.min_consolidation_candles = config.get('flag_min_consolidation', 3) if config else 3
        self.flag_slope_threshold = config.get('flag_slope_threshold', 0.01) if config else 0.01
        self.pennant_convergence_min = config.get('pennant_convergence_min', 0.3) if config else 0.3

        super().__init__(config)

    def _get_pattern_name(self) -> str:
        if self._detected_type == 'bullish_flag':
            return "Bullish Flag"
        elif self._detected_type == 'bearish_flag':
            return "Bearish Flag"
        elif self._detected_type == 'bullish_pennant':
            return "Bullish Pennant"
        elif self._detected_type == 'bearish_pennant':
            return "Bearish Pennant"
        return "Flag/Pennant"

    def _get_pattern_type(self) -> str:
        return "chart"

    def _get_direction(self) -> str:
        if self._detected_type and 'bullish' in self._detected_type:
            return 'bullish'
        elif self._detected_type and 'bearish' in self._detected_type:
            return 'bearish'
        return 'neutral'

    def _get_base_strength(self) -> int:
        return 3  # Strong continuation pattern

    def detect(
        self,
        df: pd.DataFrame,
        open_col: str = 'open',
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> bool:
        """Detect Flag or Pennant pattern."""
        if not self._validate_dataframe(df):
            return False

        if len(df) < 20:
            return False

        try:
            # Step 1: Find the flagpole (sharp prior move)
            flagpole_info = self._detect_flagpole(df, close_col, high_col, low_col)
            if not flagpole_info:
                return False

            self._flagpole_direction = flagpole_info['direction']
            flagpole_end_idx = flagpole_info['end_idx']

            # Step 2: Analyze consolidation after flagpole
            consolidation_df = df.iloc[flagpole_end_idx:].head(self.max_consolidation_candles)

            if len(consolidation_df) < self.min_consolidation_candles:
                return False

            # Step 3: Try to detect Flag pattern
            if self._detect_flag(consolidation_df, high_col, low_col, self._flagpole_direction):
                if self._flagpole_direction == 'up':
                    self._detected_type = 'bullish_flag'
                else:
                    self._detected_type = 'bearish_flag'
                return True

            # Step 4: Try to detect Pennant pattern
            if self._detect_pennant(consolidation_df, high_col, low_col):
                if self._flagpole_direction == 'up':
                    self._detected_type = 'bullish_pennant'
                else:
                    self._detected_type = 'bearish_pennant'
                return True

            return False

        except Exception as e:
            return False

    def _detect_flagpole(self, df: pd.DataFrame, close_col: str, high_col: str, low_col: str) -> Optional[Dict[str, Any]]:
        """
        Detect the flagpole (strong prior move).

        Returns:
            Dict with 'direction' ('up' or 'down'), 'size', 'end_idx'
            None if no significant move found
        """
        if len(df) < 10:
            return None

        # Look at recent 5-20 candles for the flagpole
        lookback = min(20, len(df) - 5)
        recent_df = df.tail(lookback)

        closes = recent_df[close_col].values
        highs = recent_df[high_col].values
        lows = recent_df[low_col].values

        # Find significant peaks and troughs
        peaks, _ = find_peaks(highs, distance=3)
        troughs, _ = find_peaks(-lows, distance=3)

        if len(peaks) == 0 or len(troughs) == 0:
            return None

        # Check for upward flagpole (sharp rise)
        if len(troughs) > 0 and len(peaks) > 0:
            last_trough_idx = troughs[-1]
            last_peak_idx = peaks[-1]

            # Upward move: trough before peak
            if last_trough_idx < last_peak_idx:
                move_size = (highs[last_peak_idx] - lows[last_trough_idx]) / lows[last_trough_idx]
                if move_size >= self.min_flagpole_size:
                    return {
                        'direction': 'up',
                        'size': move_size,
                        'start_idx': last_trough_idx,
                        'end_idx': last_peak_idx
                    }

        # Check for downward flagpole (sharp fall)
        if len(peaks) > 0 and len(troughs) > 0:
            last_peak_idx = peaks[-1] if len(peaks) > 0 else 0
            last_trough_idx = troughs[-1] if len(troughs) > 0 else 0

            # Downward move: peak before trough
            if last_peak_idx < last_trough_idx:
                move_size = (highs[last_peak_idx] - lows[last_trough_idx]) / highs[last_peak_idx]
                if abs(move_size) >= self.min_flagpole_size:
                    return {
                        'direction': 'down',
                        'size': abs(move_size),
                        'start_idx': last_peak_idx,
                        'end_idx': last_trough_idx
                    }

        return None

    def _detect_flag(self, consolidation_df: pd.DataFrame, high_col: str, low_col: str, flagpole_direction: str) -> bool:
        """
        Detect Flag pattern in consolidation.

        Flag characteristics:
        - Rectangular channel (parallel lines)
        - Slopes AGAINST the prior trend
          * After uptrend (bullish): flag slopes down
          * After downtrend (bearish): flag slopes up
        """
        if len(consolidation_df) < 3:
            return False

        highs = consolidation_df[high_col].values
        lows = consolidation_df[low_col].values
        x = np.arange(len(highs))

        # Calculate slopes
        upper_slope = np.polyfit(x, highs, 1)[0]
        lower_slope = np.polyfit(x, lows, 1)[0]

        # Check if lines are roughly parallel (similar slopes)
        slope_diff = abs(upper_slope - lower_slope)
        avg_slope = (abs(upper_slope) + abs(lower_slope)) / 2

        # Lines should be roughly parallel
        if avg_slope > 0 and slope_diff / avg_slope > 0.5:
            return False

        # For bullish flag: consolidation should slope down (against uptrend)
        if flagpole_direction == 'up':
            if upper_slope < -self.flag_slope_threshold and lower_slope < -self.flag_slope_threshold:
                return True

        # For bearish flag: consolidation should slope up (against downtrend)
        elif flagpole_direction == 'down':
            if upper_slope > self.flag_slope_threshold and lower_slope > self.flag_slope_threshold:
                return True

        return False

    def _detect_pennant(self, consolidation_df: pd.DataFrame, high_col: str, low_col: str) -> bool:
        """
        Detect Pennant pattern in consolidation.

        Pennant characteristics:
        - Small symmetrical triangle
        - Converging trendlines
        - Short duration (typically 3-10 candles)
        """
        if len(consolidation_df) < 3:
            return False

        highs = consolidation_df[high_col].values
        lows = consolidation_df[low_col].values
        x = np.arange(len(highs))

        # Calculate trendlines
        upper_coeffs = np.polyfit(x, highs, 1)
        lower_coeffs = np.polyfit(x, lows, 1)

        upper_slope = upper_coeffs[0]
        lower_slope = lower_coeffs[0]

        # Pennant: upper line declining, lower line rising (convergence)
        if upper_slope < -self.flag_slope_threshold and lower_slope > self.flag_slope_threshold:
            # Check convergence
            upper_line = np.polyval(upper_coeffs, x)
            lower_line = np.polyval(lower_coeffs, x)

            start_gap = upper_line[0] - lower_line[0]
            end_gap = upper_line[-1] - lower_line[-1]

            if start_gap > 0:
                convergence_ratio = (start_gap - end_gap) / start_gap

                # Lines should converge significantly
                if convergence_ratio >= self.pennant_convergence_min:
                    return True

        return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get additional details about Flag/Pennant detection."""
        try:
            return {
                'location': 'forming',
                'candles_ago': 0,
                'confidence': 0.75,  # Flag/Pennant are high-probability patterns
                'metadata': {
                    'pattern_type': self._detected_type,
                    'flagpole_direction': self._flagpole_direction,
                    'continuation_expected': True
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
        """Determine actual direction (continuation of flagpole)."""
        if self._detected_type and 'bullish' in self._detected_type:
            return 'bullish'
        elif self._detected_type and 'bearish' in self._detected_type:
            return 'bearish'
        return 'neutral'
