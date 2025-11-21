"""
Tweezer Top/Bottom Pattern Detector

Detects Tweezer Top and Tweezer Bottom candlestick patterns.
Tweezer patterns are reversal patterns where two candles have nearly identical highs (top) or lows (bottom).

Version: 1.0.0 (2025-11-18) - Initial Implementation
- ✨ NEW: Tweezer Top detection (bearish reversal)
- ✨ NEW: Tweezer Bottom detection (bullish reversal)
- 📊 Configurable tolerance for price equality (default 0.1%)
- 🔄 Multi-candle lookback detection
- ⭐ High priority pattern - very common in crypto
"""

TWEEZER_PATTERN_VERSION = "1.0.0"

import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class TweezerPattern(BasePattern):
    """
    Tweezer Top/Bottom candlestick pattern detector.

    Characteristics:
    - Two candles with nearly equal highs (Tweezer Top) or lows (Tweezer Bottom)
    - Indicates strong support/resistance at that price level
    - Reversal pattern: price tried to move but was rejected

    Tweezer Top (Bearish):
    - Two candles with nearly identical highs
    - Usually first candle bullish, second bearish
    - Forms at top of uptrend
    - Signals bearish reversal

    Tweezer Bottom (Bullish):
    - Two candles with nearly identical lows
    - Usually first candle bearish, second bullish
    - Forms at bottom of downtrend
    - Signals bullish reversal

    Strength: 2/3 (Medium to Strong)
    Direction: Both (Bullish or Bearish depending on variant)
    Common in crypto: ⭐⭐⭐⭐⭐
    Reliability: 65-75%
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Tweezer detector.

        Args:
            config: Configuration dictionary with optional pattern settings
        """
        super().__init__(config)
        self.version = TWEEZER_PATTERN_VERSION

        # Get pattern-specific configuration
        pattern_config = self.config.get('patterns', {}).get('tweezer', {})

        # Price difference tolerance (default 0.1% = 0.001)
        self.tolerance = pattern_config.get('tolerance', 0.001)

        # Cache for detected variant
        self._detected_variant = None  # 'top' or 'bottom'

    def _get_pattern_name(self) -> str:
        return "Tweezer"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish (bottom) or bearish (top)

    def _get_base_strength(self) -> int:
        return 2  # Medium to strong pattern

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
        Detect Tweezer pattern in last N candles.

        Checks for both Tweezer Top and Tweezer Bottom patterns.
        Uses multi-candle lookback for recency scoring.

        Args:
            df: DataFrame with OHLCV data
            open_col: Name of open price column
            high_col: Name of high price column
            low_col: Name of low price column
            close_col: Name of close price column
            volume_col: Name of volume column

        Returns:
            True if Tweezer pattern detected in last N candles
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None
        self._detected_variant = None

        # Need at least 2 candles for Tweezer
        if len(df) < 2:
            return False

        try:
            # Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(df) - 1)  # -1 because we need 2 candles

            for i in range(lookback):
                # Get the two candles
                # i=0: last two candles (df[-2], df[-1])
                # i=1: (df[-3], df[-2])
                # etc.
                idx2 = -(i + 1)  # Second candle index
                idx1 = idx2 - 1   # First candle index

                candle1 = df.iloc[idx1]
                candle2 = df.iloc[idx2]

                # Check for Tweezer Top
                if self._is_tweezer_top(candle1, candle2, high_col, open_col, close_col):
                    self._last_detection_candles_ago = i
                    self._detected_variant = 'top'
                    return True

                # Check for Tweezer Bottom
                if self._is_tweezer_bottom(candle1, candle2, low_col, open_col, close_col):
                    self._last_detection_candles_ago = i
                    self._detected_variant = 'bottom'
                    return True

            return False

        except Exception as e:
            return False

    def _is_tweezer_top(
        self,
        candle1: pd.Series,
        candle2: pd.Series,
        high_col: str,
        open_col: str,
        close_col: str
    ) -> bool:
        """
        Check if two candles form a Tweezer Top pattern.

        Args:
            candle1: First candle
            candle2: Second candle
            high_col: High price column name
            open_col: Open price column name
            close_col: Close price column name

        Returns:
            True if Tweezer Top detected
        """
        # Check if highs are almost equal (within tolerance)
        high1 = candle1[high_col]
        high2 = candle2[high_col]

        if high1 <= 0:  # Avoid division by zero
            return False

        high_diff = abs(high1 - high2) / high1

        if high_diff <= self.tolerance:
            # Additional confirmation: different candle colors
            # First candle should be bullish (trying to go up)
            # Second candle should be bearish (rejection)
            candle1_bullish = candle1[close_col] > candle1[open_col]
            candle2_bearish = candle2[close_col] < candle2[open_col]

            # Pattern is stronger with color confirmation, but not required
            # Return true if highs match, bonus if colors confirm
            return True

        return False

    def _is_tweezer_bottom(
        self,
        candle1: pd.Series,
        candle2: pd.Series,
        low_col: str,
        open_col: str,
        close_col: str
    ) -> bool:
        """
        Check if two candles form a Tweezer Bottom pattern.

        Args:
            candle1: First candle
            candle2: Second candle
            low_col: Low price column name
            open_col: Open price column name
            close_col: Close price column name

        Returns:
            True if Tweezer Bottom detected
        """
        # Check if lows are almost equal (within tolerance)
        low1 = candle1[low_col]
        low2 = candle2[low_col]

        if low1 <= 0:  # Avoid division by zero
            return False

        low_diff = abs(low1 - low2) / low1

        if low_diff <= self.tolerance:
            # Additional confirmation: different candle colors
            # First candle should be bearish (trying to go down)
            # Second candle should be bullish (rejection)
            candle1_bearish = candle1[close_col] < candle1[open_col]
            candle2_bullish = candle2[close_col] > candle2[open_col]

            # Pattern is stronger with color confirmation, but not required
            # Return true if lows match, bonus if colors confirm
            return True

        return False

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """
        Determine actual direction (bullish or bearish).

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            'bullish' for Tweezer Bottom, 'bearish' for Tweezer Top
        """
        variant = getattr(self, '_detected_variant', 'bottom')
        return 'bullish' if variant == 'bottom' else 'bearish'

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Tweezer detection with recency information.

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-N
            - recency_multiplier: Score multiplier based on age
            - confidence: Trading confidence (0-1), adjusted by recency
            - metadata: Detailed metrics including:
              - variant: 'top' or 'bottom'
              - price_match_quality: How close the highs/lows are
              - color_confirmation: Whether candle colors confirm pattern
              - recency_info: Recency scoring details
        """
        if len(df) < 2:
            return super()._get_detection_details(df)

        try:
            # Get detection position
            candles_ago = getattr(self, '_last_detection_candles_ago', 0)
            if candles_ago is None:
                candles_ago = 0

            # Get recency multiplier
            if candles_ago < len(self.recency_multipliers):
                recency_multiplier = self.recency_multipliers[candles_ago]
            else:
                recency_multiplier = 0.0

            # Get variant
            variant = getattr(self, '_detected_variant', 'bottom')

            # Get the two candles where pattern was detected
            idx2 = -(candles_ago + 1)
            idx1 = idx2 - 1

            candle1 = df.iloc[idx1]
            candle2 = df.iloc[idx2]

            # Calculate match quality
            if variant == 'top':
                high1 = candle1['high']
                high2 = candle2['high']
                price_diff = abs(high1 - high2) / high1 if high1 > 0 else 0
                match_quality = max(0, 1.0 - (price_diff / self.tolerance))

                # Check color confirmation
                candle1_bullish = candle1['close'] > candle1['open']
                candle2_bearish = candle2['close'] < candle2['open']
                color_confirmed = candle1_bullish and candle2_bearish

                price_level = (high1 + high2) / 2
            else:  # bottom
                low1 = candle1['low']
                low2 = candle2['low']
                price_diff = abs(low1 - low2) / low1 if low1 > 0 else 0
                match_quality = max(0, 1.0 - (price_diff / self.tolerance))

                # Check color confirmation
                candle1_bearish = candle1['close'] < candle1['open']
                candle2_bullish = candle2['close'] > candle2['open']
                color_confirmed = candle1_bearish and candle2_bullish

                price_level = (low1 + low2) / 2

            # Calculate base confidence
            # Higher match quality = higher confidence
            base_confidence = 0.65 + (match_quality * 0.15)  # 65-80% base

            # Bonus for color confirmation
            if color_confirmed:
                base_confidence += 0.10  # Up to 90%

            base_confidence = min(base_confidence, 0.90)

            # Adjust confidence with recency multiplier
            adjusted_confidence = min(base_confidence * recency_multiplier, 0.90)

            return {
                'location': 'current' if candles_ago == 0 else 'recent',
                'candles_ago': candles_ago,
                'recency_multiplier': recency_multiplier,
                'confidence': adjusted_confidence,
                'metadata': {
                    'variant': variant,
                    'price_level': float(price_level),
                    'price_match_quality': float(match_quality),
                    'price_difference_pct': float(price_diff * 100),
                    'color_confirmed': color_confirmed,
                    'tolerance_used': self.tolerance,
                    'pattern_name': f"Tweezer {'Top' if variant == 'top' else 'Bottom'}",
                    'recency_info': {
                        'candles_ago': candles_ago,
                        'multiplier': recency_multiplier,
                        'lookback_window': self.lookback_window,
                        'base_confidence': base_confidence,
                        'adjusted_confidence': adjusted_confidence
                    }
                }
            }

        except Exception as e:
            return super()._get_detection_details(df)

    def _calculate_dynamic_strength(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> float:
        """
        Calculate dynamic strength based on pattern quality.

        Higher strength for:
        - Better price match quality
        - Color confirmation
        - Recent detection

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            Strength value (1.5 to 3.0)
        """
        base_strength = float(self.base_strength)  # 2.0

        # Get match quality
        metadata = detection_details.get('metadata', {})
        match_quality = metadata.get('price_match_quality', 0.5)
        color_confirmed = metadata.get('color_confirmed', False)

        # Adjust strength based on quality
        # Perfect match (1.0) = +0.5 strength
        # Good match (0.7) = +0.35 strength
        # Poor match (0.3) = +0.15 strength
        quality_bonus = match_quality * 0.5

        # Color confirmation bonus
        color_bonus = 0.5 if color_confirmed else 0.0

        final_strength = base_strength + quality_bonus + color_bonus

        # Cap between 1.5 and 3.0
        return max(1.5, min(final_strength, 3.0))
