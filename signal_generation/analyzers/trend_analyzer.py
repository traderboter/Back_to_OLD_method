"""
TrendAnalyzer - Market Trend Detection

This analyzer determines the market trend direction, strength, and phase
using Exponential Moving Averages (EMAs) and price position analysis.

Uses indicators (pre-calculated by IndicatorCalculator):
- ema_20, ema_50, ema_100
- sma_20, sma_50, sma_200
- close price

Outputs to context:
- trend: {
    'direction': Direction enum ('bullish' | 'bearish' | 'sideways' | 'neutral'),
    'strength': float (-3 to 3),
    'phase': TrendPhase enum ('early' | 'developing' | 'mature' | 'late' | 'pullback' | 'transition' | 'undefined'),
    'ema_alignment': bool,
    'price_position': str,
    'ema_slopes': dict,
    'confidence': float (0-1)
  }

REFACTORED: Now uses Enums and Constants for type safety and better maintainability.
"""

from typing import Dict, Any
import logging
import pandas as pd

# Assuming BaseAnalyzer and AnalysisContext are in parent directory
try:
    from signal_generation.analyzers.base_analyzer import BaseAnalyzer
    from signal_generation.context import AnalysisContext
    from signal_generation.enums import Direction, TrendPhase, TrendAlignment
    from signal_generation.constants import MIN_CANDLES_FOR_ANALYSIS
except ImportError:
    # Fallback for testing
    import sys
    sys.path.append('..')
    from analyzers.base_analyzer import BaseAnalyzer
    from context import AnalysisContext
    from enums import Direction, TrendPhase
    from constants import MIN_CANDLES_FOR_ANALYSIS

logger = logging.getLogger(__name__)


class TrendAnalyzer(BaseAnalyzer):
    """
    Analyzes market trend using EMAs and price position.
    
    Determines:
    1. Trend Direction (bullish/bearish/sideways)
    2. Trend Strength (0-3 scale)
    3. Trend Phase (early/developing/mature/late)
    4. EMA Alignment
    5. Confidence level
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize TrendAnalyzer.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Get trend-specific configuration
        # Try both 'trend' and 'trend_analyzer' keys (backward compatibility)
        trend_config = config.get('trend_analyzer', config.get('trend', {}))

        # Minimum slope threshold for trend confirmation (global default)
        self.min_slope_threshold = trend_config.get('min_slope_threshold', 0.0002)

        # Lookback period for slope calculation (global default)
        self.slope_lookback = trend_config.get('slope_lookback', 5)
        
        # Enable/disable this analyzer
        self.enabled = config.get('analyzers', {}).get('trend', {}).get('enabled', True)
        
        logger.info("TrendAnalyzer initialized successfully")
    
    def analyze(self, context: AnalysisContext) -> None:
        """
        Main analysis method - determines market trend.
        
        Args:
            context: AnalysisContext with pre-calculated indicators
        """
        # 1. Check if enabled
        if not self._check_enabled():
            logger.debug(f"TrendAnalyzer disabled, skipping analysis for {context.symbol}")
            return
        
        # 2. Validate context has required data
        if not self._validate_context(context):
            logger.warning(f"TrendAnalyzer: Invalid context for {context.symbol}")
            return
        
        try:
            # 3. Read pre-calculated indicators from context.df
            df = context.df
            timeframe = context.timeframe  # Get timeframe for per-TF thresholds

            # Ensure we have enough data (using constant instead of magic number)
            if len(df) < MIN_CANDLES_FOR_ANALYSIS:
                logger.warning(
                    f"Insufficient data for TrendAnalyzer on {context.symbol} "
                    f"({len(df)} rows, need 100+)"
                )
                context.add_result('trend', {
                    'status': 'insufficient_data',
                    'direction': Direction.NEUTRAL.value,  # Using Enum
                    'strength': 0,
                    'phase': TrendPhase.UNDEFINED.value  # Using Enum
                })
                return
            
            # Get current values (last row)
            current_close = df['close'].iloc[-1]
            current_ema20 = df['ema_20'].iloc[-1]
            current_ema50 = df['ema_50'].iloc[-1]
            current_ema100 = df['ema_100'].iloc[-1]
            
            # 4. Calculate EMA slopes (rate of change)
            ema_slopes = self._calculate_ema_slopes(df, timeframe)
            
            # 5. Determine EMA arrangement pattern
            ema_alignment = self._determine_ema_alignment(
                current_close, current_ema20, current_ema50, current_ema100
            )
            
            # 6. Detect trend direction and strength
            trend_result = self._detect_trend(
                current_close,
                current_ema20,
                current_ema50,
                current_ema100,
                ema_slopes,
                ema_alignment,
                timeframe
            )
            
            # 7. Determine trend phase
            trend_phase = self._determine_trend_phase(
                trend_result['direction'],
                trend_result['strength'],
                ema_alignment,
                ema_slopes,
                timeframe
            )
            
            # 8. Calculate confidence score
            confidence = self._calculate_confidence(
                trend_result['strength'],
                ema_alignment,
                ema_slopes
            )
            
            # 9. Build final result
            result = {
                'status': 'ok',
                'direction': trend_result['direction'],
                'strength': trend_result['strength'],
                'phase': trend_phase,
                'ema_alignment': ema_alignment,
                'price_position': self._get_price_position(current_close, current_ema20, current_ema50),
                'ema_slopes': ema_slopes,
                'confidence': confidence,
                'details': {
                    'close': round(current_close, 5),
                    'ema20': round(current_ema20, 5),
                    'ema50': round(current_ema50, 5),
                    'ema100': round(current_ema100, 5),
                }
            }
            
            # 10. Store result in context
            context.add_result('trend', result)
            
            logger.info(
                f"TrendAnalyzer completed for {context.symbol} {context.timeframe}: "
                f"{result['direction']} (strength: {result['strength']}, "
                f"phase: {result['phase']}, confidence: {confidence:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Error in TrendAnalyzer for {context.symbol}: {e}", exc_info=True)
            context.add_result('trend', {
                'status': 'error',
                'direction': Direction.NEUTRAL.value,  # Using Enum
                'strength': 0,
                'phase': TrendPhase.UNDEFINED.value,  # Using Enum
                'error': str(e)
            })
    
    def _calculate_ema_slopes(self, df: pd.DataFrame, timeframe: str = None) -> Dict[str, float]:
        """
        Calculate rate of change (slope) for EMAs.

        Args:
            df: DataFrame with EMA columns
            timeframe: Current timeframe for per-TF lookback

        Returns:
            Dictionary with slopes for each EMA
        """
        # Get per-TF lookback or use global default
        lookback = self.get_threshold('slope_lookback', self.slope_lookback, timeframe)
        lookback = min(lookback, len(df) - 1)
        
        if lookback < 2:
            return {'ema20': 0.0, 'ema50': 0.0, 'ema100': 0.0}
        
        # Calculate slopes (current - past) / past
        ema20_slope = (
            (df['ema_20'].iloc[-1] - df['ema_20'].iloc[-lookback]) 
            / df['ema_20'].iloc[-lookback]
        ) if df['ema_20'].iloc[-lookback] != 0 else 0.0
        
        ema50_slope = (
            (df['ema_50'].iloc[-1] - df['ema_50'].iloc[-lookback]) 
            / df['ema_50'].iloc[-lookback]
        ) if df['ema_50'].iloc[-lookback] != 0 else 0.0
        
        ema100_slope = (
            (df['ema_100'].iloc[-1] - df['ema_100'].iloc[-lookback]) 
            / df['ema_100'].iloc[-lookback]
        ) if df['ema_100'].iloc[-lookback] != 0 else 0.0
        
        return {
            'ema20': ema20_slope,
            'ema50': ema50_slope,
            'ema100': ema100_slope
        }
    
    def _determine_ema_alignment(
        self,
        close: float,
        ema20: float,
        ema50: float,
        ema100: float
    ) -> str:
        """
        REFACTORED: Now uses TrendAlignment Enum internally for type safety.

        Determine the arrangement/alignment pattern of EMAs.

        Args:
            close: Current close price
            ema20, ema50, ema100: Current EMA values

        Returns:
            String describing the alignment pattern (using TrendAlignment.value for backward compatibility)
        """
        # Using TrendAlignment Enum for type safety
        if ema20 > ema50 > ema100:
            alignment = TrendAlignment.BULLISH_ALIGNED
        elif ema20 < ema50 < ema100:
            alignment = TrendAlignment.BEARISH_ALIGNED
        elif ema20 > ema50 and ema50 < ema100:
            alignment = TrendAlignment.POTENTIAL_BULLISH_REVERSAL
        elif ema20 < ema50 and ema50 > ema100:
            alignment = TrendAlignment.POTENTIAL_BEARISH_REVERSAL
        elif ema20 > ema50 > ema100 and close < ema20:
            alignment = TrendAlignment.BULLISH_PULLBACK
        elif ema20 < ema50 < ema100 and close > ema20:
            alignment = TrendAlignment.BEARISH_PULLBACK
        else:
            alignment = TrendAlignment.MIXED

        return alignment.value  # Return .value for backward compatibility
    
    def _detect_trend(
        self,
        close: float,
        ema20: float,
        ema50: float,
        ema100: float,
        slopes: Dict[str, float],
        alignment: str,
        timeframe: str = None
    ) -> Dict[str, Any]:
        """
        Detect trend direction and strength.

        Args:
            close: Current close price
            ema20, ema50, ema100: Current EMA values
            slopes: Dictionary of EMA slopes
            alignment: EMA alignment pattern
            timeframe: Current timeframe for per-TF thresholds

        Returns:
            Dictionary with 'direction' (as string via .value) and 'strength'

        REFACTORED: Now uses Direction Enum internally for type safety
        """
        direction = Direction.NEUTRAL  # Using Enum instead of string
        strength = 0

        ema20_slope = slopes['ema20']
        ema50_slope = slopes['ema50']

        # Get per-TF threshold (or fall back to global/default)
        # Using 'min_slope' to match config.yaml key
        min_slope_threshold = self.get_threshold('min_slope', self.min_slope_threshold, timeframe)

        # Strong Bullish (strength = 3)
        if (close > ema20 > ema50 > ema100 and
            ema20_slope > min_slope_threshold and
            ema50_slope > min_slope_threshold):
            direction = Direction.BULLISH  # Enum
            strength = 3

        # Moderate Bullish (strength = 2)
        elif (close > ema20 > ema50 and
              ema20_slope > min_slope_threshold):
            direction = Direction.BULLISH  # Enum
            strength = 2

        # Weak Bullish (strength = 1)
        elif close > ema20 and ema20_slope > min_slope_threshold:
            direction = Direction.BULLISH  # Enum
            strength = 1

        # Strong Bearish (strength = -3)
        elif (close < ema20 < ema50 < ema100 and
              ema20_slope < -min_slope_threshold and
              ema50_slope < -min_slope_threshold):
            direction = Direction.BEARISH  # Enum
            strength = -3

        # Moderate Bearish (strength = -2)
        elif (close < ema20 < ema50 and
              ema20_slope < -min_slope_threshold):
            direction = Direction.BEARISH  # Enum
            strength = -2

        # Weak Bearish (strength = -1)
        elif close < ema20 and ema20_slope < -min_slope_threshold:
            direction = Direction.BEARISH  # Enum
            strength = -1

        # Bullish Pullback - keeping as BULLISH for now (pullback tracked via phase)
        elif close < ema50 and ema20 > ema50 and ema50_slope > 0:
            direction = Direction.BULLISH  # Enum (pullback in phase)
            strength = 1

        # Bearish Pullback - keeping as BEARISH for now (pullback tracked via phase)
        elif close > ema50 and ema20 < ema50 and ema50_slope < 0:
            direction = Direction.BEARISH  # Enum (pullback in phase)
            strength = -1

        # Sideways / Neutral
        else:
            direction = Direction.NEUTRAL  # Enum
            strength = 0

        return {
            'direction': direction.value,  # Convert Enum to string for backward compatibility
            'strength': strength
        }
    
    def _determine_trend_phase(
        self,
        direction: str,
        strength: int,
        alignment: str,
        slopes: Dict[str, float],
        timeframe: str = None
    ) -> str:
        """
        REFACTORED: Now uses TrendPhase Enum internally for type safety.

        Determine the phase of the trend (OLD SYSTEM alignment with 'late' phase).

        Phases (7 phases matching OLD SYSTEM):
        - early: Trend just starting (strength = 1)
        - developing: Trend gaining momentum (strength = 2, or strength = 3 without full alignment)
        - mature: Trend fully established (strength = 3 with aligned EMAs, strong slopes)
        - late: Trend losing momentum (strength = 3 but slopes weakening) ✨ NEW
        - pullback: Temporary retracement in trend
        - transition: Changing from one trend to another
        - undefined: No clear trend

        Args:
            direction: Trend direction
            strength: Trend strength
            alignment: EMA alignment pattern
            slopes: EMA slopes
            timeframe: Current timeframe for per-TF thresholds

        Returns:
            String describing trend phase (using TrendPhase.value for backward compatibility)
        """
        # Using TrendPhase Enum for type safety
        phase = TrendPhase.UNDEFINED  # Default

        # Get per-TF threshold (or fall back to global/default)
        # Using 'min_slope' to match config.yaml key
        min_slope_threshold = self.get_threshold('min_slope', self.min_slope_threshold, timeframe)

        if direction == 'sideways' or direction == 'neutral':
            phase = TrendPhase.UNDEFINED
            return phase.value

        if 'pullback' in direction:
            phase = TrendPhase.PULLBACK
            return phase.value

        # Check for transition (potential reversal)
        if 'reversal' in alignment:
            phase = TrendPhase.TRANSITION
            return phase.value

        # For strong trends (strength = 3), distinguish between mature and late
        if abs(strength) == 3:
            if 'aligned' in alignment:
                # Check if slopes are weakening (late phase)
                ema20_slope = slopes.get('ema20', 0)
                ema50_slope = slopes.get('ema50', 0)
                ema100_slope = slopes.get('ema100', 0)

                # Late phase: EMAs aligned but slopes weakening
                # For bullish: slopes are positive but decreasing
                # For bearish: slopes are negative but increasing (becoming less negative)
                if direction == 'bullish' or direction == 'bullish_pullback':
                    # Check if ema20_slope is weaker than ema50_slope (slope divergence)
                    # This indicates momentum loss
                    if ema20_slope < ema50_slope * 0.8:  # 20% weaker
                        phase = TrendPhase.LATE
                    # Check if all slopes are very weak (near exhaustion)
                    elif ema20_slope < min_slope_threshold * 2 and ema50_slope < min_slope_threshold * 2:
                        phase = TrendPhase.LATE
                    else:
                        phase = TrendPhase.MATURE

                elif direction == 'bearish' or direction == 'bearish_pullback':
                    # For bearish, slopes are negative, so we check if becoming less negative
                    if ema20_slope > ema50_slope * 0.8:  # Becoming less steep (weakening)
                        phase = TrendPhase.LATE
                    # Check if slopes are very weak (near exhaustion)
                    elif ema20_slope > -min_slope_threshold * 2 and ema50_slope > -min_slope_threshold * 2:
                        phase = TrendPhase.LATE
                    else:
                        phase = TrendPhase.MATURE
                else:
                    phase = TrendPhase.MATURE
            else:
                # Strong but not fully aligned = developing
                phase = TrendPhase.DEVELOPING

        # Check if it's early trend (weak but starting)
        elif abs(strength) == 1:
            phase = TrendPhase.EARLY

        # Medium strength is developing
        elif abs(strength) == 2:
            phase = TrendPhase.DEVELOPING

        else:
            phase = TrendPhase.UNDEFINED

        return phase.value  # Return .value for backward compatibility
    
    def _get_price_position(self, close: float, ema20: float, ema50: float) -> str:
        """
        Describe price position relative to EMAs.
        
        Args:
            close: Current close price
            ema20, ema50: Current EMA values
            
        Returns:
            String describing price position
        """
        if close > ema20 and close > ema50:
            return 'above_both_emas'
        elif close > ema20 and close < ema50:
            return 'between_emas'
        elif close < ema20 and close < ema50:
            return 'below_both_emas'
        else:
            return 'at_ema'
    
    def _calculate_confidence(
        self,
        strength: int,
        alignment: str,
        slopes: Dict[str, float]
    ) -> float:
        """
        Calculate confidence score for the trend detection.
        
        Args:
            strength: Trend strength
            alignment: EMA alignment
            slopes: EMA slopes
            
        Returns:
            Confidence score (0 to 1)
        """
        confidence = 0.5  # Base confidence
        
        # Strong trend increases confidence
        if abs(strength) == 3:
            confidence += 0.3
        elif abs(strength) == 2:
            confidence += 0.2
        elif abs(strength) == 1:
            confidence += 0.1
        
        # Aligned EMAs increase confidence
        if 'aligned' in alignment:
            confidence += 0.2
        elif 'reversal' in alignment:
            confidence += 0.1
        
        # Consistent slopes increase confidence
        all_slopes = list(slopes.values())
        if all(s > 0 for s in all_slopes):  # All positive
            confidence += 0.1
        elif all(s < 0 for s in all_slopes):  # All negative
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _validate_context(self, context: AnalysisContext) -> bool:
        """
        Validate that context has required indicators.
        
        Args:
            context: AnalysisContext to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = ['close', 'ema_20', 'ema_50', 'ema_100']
        
        df = context.df
        
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False
        
        return True
    
    def _check_enabled(self) -> bool:
        """Check if this analyzer is enabled."""
        return self.enabled
