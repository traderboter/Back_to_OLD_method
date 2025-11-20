"""
Base Pattern - Base class for all pattern detectors

This is the abstract base class that all pattern detectors must inherit from.
It provides a consistent interface for pattern detection and scoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import logging

from signal_generation.pattern_score_utils import get_pattern_score

logger = logging.getLogger(__name__)


class BasePattern(ABC):
    """
    Abstract base class for all pattern detectors.

    All pattern classes (candlestick and chart) must inherit from this class
    and implement the abstract methods.

    Key features:
    1. Standardized interface for pattern detection
    2. Automatic pattern metadata
    3. Context-aware scoring support
    4. Consistent output format
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the pattern detector.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.name = self._get_pattern_name()
        self.pattern_type = self._get_pattern_type()
        self.direction = self._get_direction()
        self.base_strength = self._get_base_strength()

        # Recency scoring parameters
        pattern_name_lower = self.name.lower().replace(' ', '_')
        pattern_config = self.config.get('patterns', {}).get(pattern_name_lower, {})

        self.lookback_window = pattern_config.get('lookback_window', 5)
        self.recency_multipliers = pattern_config.get(
            'recency_multipliers',
            [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]  # default
        )

        # Cache for last detection position
        self._last_detection_candles_ago = None

        logger.debug(f"Pattern initialized: {self.name}")

    @abstractmethod
    def _get_pattern_name(self) -> str:
        """
        Get the pattern name.

        Returns:
            Pattern name (e.g., 'Hammer', 'Double Top')
        """
        pass

    @abstractmethod
    def _get_pattern_type(self) -> str:
        """
        Get the pattern type.

        Returns:
            'candlestick' or 'chart'
        """
        pass

    @abstractmethod
    def _get_direction(self) -> str:
        """
        Get the pattern direction.

        Returns:
            'bullish', 'bearish', 'both', or 'reversal'
        """
        pass

    @abstractmethod
    def _get_base_strength(self) -> int:
        """
        Get the base strength of the pattern.

        Returns:
            Strength value (1-3)
            1 = weak, 2 = medium, 3 = strong
        """
        pass

    @abstractmethod
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
        Detect if the pattern exists in the data.

        Args:
            df: DataFrame with OHLCV data
            open_col: Name of open price column
            high_col: Name of high price column
            low_col: Name of low price column
            close_col: Name of close price column
            volume_col: Name of volume column

        Returns:
            True if pattern detected, False otherwise
        """
        pass

    def get_pattern_info(
        self,
        df: pd.DataFrame,
        timeframe: str = '1h',
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete pattern information if detected.

        This is the main public method that should be called.

        Args:
            df: DataFrame with OHLCV data
            timeframe: Timeframe string (e.g., '1h', '4h')
            context: Optional context for context-aware scoring

        Returns:
            Dictionary with pattern info if detected, None otherwise
        """
        try:
            # Detect pattern
            is_detected = self.detect(df)

            if not is_detected:
                return None

            # Get detection details
            detection_details = self._get_detection_details(df)

            # Calculate base strength (might be dynamic)
            base_strength = self._calculate_dynamic_strength(df, detection_details)

            # ✨ Calculate timeframe-based score
            pattern_score = self._get_timeframe_based_score(timeframe, base_strength)
            recency_multiplier = detection_details.get('recency_multiplier', 1.0)
            final_score = pattern_score * recency_multiplier

            # Build pattern info
            pattern_info = {
                'name': self.name,
                'type': self.pattern_type,
                'direction': self._get_actual_direction(df, detection_details),
                'base_strength': base_strength,
                'adjusted_strength': base_strength,  # Will be adjusted by analyzer
                'timeframe': timeframe,
                'base_score': pattern_score,  # ✨ امتیاز پایه بر اساس تایم‌فریم
                'recency_multiplier': recency_multiplier,
                'final_score': final_score,  # ✨ امتیاز نهایی با recency
                'location': detection_details.get('location', 'current'),
                'candles_ago': detection_details.get('candles_ago', 0),
                'confidence': detection_details.get('confidence', 0.5),
                'metadata': detection_details.get('metadata', {})
            }

            # Apply context-aware adjustments if context provided
            if context:
                pattern_info = self._apply_context_adjustments(pattern_info, context)

            return pattern_info

        except Exception as e:
            logger.error(f"Error getting pattern info for {self.name}: {e}", exc_info=True)
            return None

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about the detection.

        Subclasses can override this to provide more information.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with detection details including recency information
        """
        # Get candles_ago (set by detect() method in subclasses)
        candles_ago = getattr(self, '_last_detection_candles_ago', 0)
        if candles_ago is None:
            candles_ago = 0

        # Get recency multiplier
        if candles_ago < len(self.recency_multipliers):
            recency_multiplier = self.recency_multipliers[candles_ago]
        else:
            recency_multiplier = 0.0  # Too old

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': 0.7,
            'metadata': {
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window
                }
            }
        }

    def _calculate_dynamic_strength(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> float:
        """
        Calculate dynamic strength based on pattern quality.

        Subclasses can override this for more sophisticated strength calculation.

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            Strength value (can be float for more precision)
        """
        # Default: return base strength
        return float(self.base_strength)

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """
        Get the actual direction of the pattern.

        For patterns with direction='both', this determines the actual direction.

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            'bullish' or 'bearish'
        """
        # Default: return configured direction
        return self.direction

    def _apply_context_adjustments(
        self,
        pattern_info: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply context-aware adjustments to pattern info.

        Subclasses can override for custom context handling.

        Args:
            pattern_info: Pattern information
            context: Context data (trend, momentum, volume, etc.)

        Returns:
            Updated pattern info
        """
        # Default: no adjustments (done by PatternAnalyzer)
        return pattern_info

    def _validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has required data.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        if df is None or len(df) == 0:
            logger.warning(f"{self.name}: DataFrame is empty")
            return False

        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"{self.name}: Missing column {col}")
                return False

        return True

    def _get_timeframe_based_score(
        self,
        timeframe: str,
        base_strength: int
    ) -> float:
        """
        محاسبه امتیاز بر اساس تایم‌فریم و قدرت پایه.

        این متد از pattern_scores در config استفاده می‌کند که می‌تواند:
        1. ساختار قدیم: {'hammer': 10.0}
        2. ساختار جدید: {'hammer': {'5m': 8.0, '15m': 10.0, '1h': 12.0, '4h': 15.0}}

        Args:
            timeframe: تایم‌فریم فعلی (مثل '5m', '1h', '4h')
            base_strength: قدرت پایه الگو (1-3)

        Returns:
            امتیاز نهایی برای این الگو در این تایم‌فریم
        """
        # دریافت pattern_scores از config
        pattern_scores = self.config.get('pattern_scores', {})

        # استفاده از تابع get_pattern_score که از هر دو ساختار پشتیبانی می‌کند
        pattern_name_lower = self.name.lower().replace(' ', '_')

        # امتیاز پیش‌فرض بر اساس قدرت پایه
        default_score = float(base_strength * 5.0)  # strength 1 = 5.0, 2 = 10.0, 3 = 15.0

        # دریافت امتیاز از config (با پشتیبانی timeframe)
        score = get_pattern_score(
            pattern_scores=pattern_scores,
            pattern_name=pattern_name_lower,
            timeframe=timeframe,
            default_score=default_score
        )

        logger.debug(
            f"Pattern score for {self.name} on {timeframe}: {score} "
            f"(base_strength={base_strength}, default={default_score})"
        )

        return score

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.pattern_type}, {self.direction}, strength={self.base_strength})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"type='{self.pattern_type}', direction='{self.direction}', "
            f"strength={self.base_strength})"
        )
