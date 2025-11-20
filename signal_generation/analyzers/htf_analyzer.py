"""
HTFAnalyzer - Higher Timeframe Analysis

Analyzes higher timeframe structure for multi-timeframe confirmation.

Note: This analyzer requires HTF data to be passed in context metadata.
If HTF data is not available, it will skip analysis.

Uses indicators:
- HTF OHLC data (from context.metadata)
- HTF trend structure

Outputs to context:
- htf: {
    'htf_trend': 'bullish' | 'bearish' | 'neutral',
    'htf_structure': 'higher_highs' | 'lower_lows' | 'ranging',
    'alignment': bool,
    'htf_support': float | None,
    'htf_resistance': float | None,
    'structure_shift': bool,
    'confidence': float (0-1)
  }
"""

from typing import Dict, Any, Optional
import logging
import pandas as pd
import numpy as np

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.enums import Direction, MarketStructure

logger = logging.getLogger(__name__)


class HTFAnalyzer(BaseAnalyzer):
    """Analyzes higher timeframe structure."""
    
    # Timeframe hierarchy (in minutes) - Aligned with OLD SYSTEM
    TF_HIERARCHY = {
        '5m': 5,       # 5 minutes
        '15m': 15,     # 15 minutes
        '1h': 60,      # 1 hour
        '4h': 240      # 4 hours
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        htf_config = config.get('htf', {})

        # Default parameters (can be overridden per-TF)
        self.default_lookback = 50

        # Fallback values
        self.lookback = self.default_lookback

        self.enabled = config.get('analyzers', {}).get('htf', {}).get('enabled', True)
        
        logger.info("HTFAnalyzer initialized")
    
    def analyze(self, context: AnalysisContext) -> None:
        """Main analysis method."""
        if not self._check_enabled():
            return
        
        try:
            # Get per-TF parameters
            self.lookback = self.get_threshold('lookback', self.default_lookback, context.timeframe)

            # Check if HTF data is available in metadata
            htf_data = context.metadata.get('htf_data')
            current_tf = context.timeframe
            
            if not htf_data:
                logger.debug(f"No HTF data available for {context.symbol}")
                context.add_result('htf', {
                    'status': 'no_htf_data',
                    'htf_trend': 'unknown'
                })
                return
            
            # Get higher timeframe
            htf = self._get_higher_timeframe(current_tf)
            
            if htf not in htf_data:
                logger.debug(f"HTF {htf} not available")
                context.add_result('htf', {
                    'status': 'htf_not_available',
                    'htf_trend': 'unknown'
                })
                return
            
            htf_df = htf_data[htf]
            
            if len(htf_df) < 20:
                context.add_result('htf', {
                    'status': 'insufficient_htf_data',
                    'htf_trend': 'unknown'
                })
                return
            
            # Analyze HTF trend
            htf_trend = self._analyze_htf_trend(htf_df)
            
            # Analyze HTF structure
            htf_structure = self._analyze_structure(htf_df)
            
            # Find HTF support/resistance
            htf_support, htf_resistance = self._find_htf_levels(htf_df)
            
            # Check alignment with current timeframe
            current_trend = context.get_result('trend')
            alignment = self._check_alignment(htf_trend, current_trend)
            
            # Detect structure shift
            structure_shift = self._detect_structure_shift(htf_df)
            
            result = {
                'status': 'ok',
                'htf_timeframe': htf,
                'htf_trend': htf_trend,
                'htf_structure': htf_structure,
                'alignment': alignment,
                'htf_support': htf_support,
                'htf_resistance': htf_resistance,
                'structure_shift': structure_shift,
                'confidence': 0.7 if alignment else 0.5
            }
            
            context.add_result('htf', result)
            
            logger.info(f"HTFAnalyzer: {htf} trend={htf_trend} for {context.symbol}")
            
        except Exception as e:
            logger.error(f"Error in HTFAnalyzer: {e}", exc_info=True)
            context.add_result('htf', {
                'status': 'error',
                'htf_trend': 'unknown',
                'error': str(e)
            })
    
    def _get_higher_timeframe(self, current_tf: str) -> str:
        """Get the next higher timeframe."""
        current_minutes = self.TF_HIERARCHY.get(current_tf, 60)
        
        # Find next higher timeframe
        higher_tfs = [tf for tf, minutes in self.TF_HIERARCHY.items() 
                      if minutes > current_minutes]
        
        if higher_tfs:
            return min(higher_tfs, key=lambda tf: self.TF_HIERARCHY[tf])
        
        return '1d'  # Default to daily
    
    def _analyze_htf_trend(self, htf_df: pd.DataFrame) -> str:
        """
        REFACTORED: Now uses Direction Enum for type safety.

        Analyze trend on higher timeframe.

        Returns:
            String describing trend (using Direction.value for backward compatibility)
        """
        try:
            # Simple EMA-based trend
            close = htf_df['close'].values

            if len(close) < 50:
                return Direction.NEUTRAL.value

            # Use pre-calculated EMAs if available, otherwise calculate
            if 'ema_20' in htf_df.columns and 'ema_50' in htf_df.columns:
                ema_20 = htf_df['ema_20'].iloc[-1]
                ema_50 = htf_df['ema_50'].iloc[-1]
            else:
                # Fallback: Calculate EMAs if not pre-calculated
                logger.debug("EMAs not pre-calculated in HTF data, calculating...")
                ema_20 = pd.Series(close).ewm(span=20, adjust=False).mean().iloc[-1]
                ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().iloc[-1]

            current_price = close[-1]

            # Using Direction Enum for type safety
            if current_price > ema_20 > ema_50:
                trend = Direction.BULLISH
            elif current_price < ema_20 < ema_50:
                trend = Direction.BEARISH
            else:
                trend = Direction.NEUTRAL

            return trend.value  # Return .value for backward compatibility

        except Exception as e:
            logger.debug(f"HTF trend analysis failed: {e}")
            return Direction.NEUTRAL.value
    
    def _analyze_structure(self, htf_df: pd.DataFrame) -> str:
        """
        REFACTORED: Now uses MarketStructure Enum for type safety.

        Analyze market structure.

        Returns:
            String describing structure (using MarketStructure.value for backward compatibility)
        """
        try:
            highs = htf_df['high'].tail(10).values
            lows = htf_df['low'].tail(10).values

            # Check for higher highs and higher lows
            recent_highs = highs[-3:]
            recent_lows = lows[-3:]

            higher_highs = all(recent_highs[i] < recent_highs[i+1] for i in range(len(recent_highs)-1))
            higher_lows = all(recent_lows[i] < recent_lows[i+1] for i in range(len(recent_lows)-1))

            # Using MarketStructure Enum for type safety
            if higher_highs and higher_lows:
                structure = MarketStructure.HIGHER_HIGHS
            else:
                lower_highs = all(recent_highs[i] > recent_highs[i+1] for i in range(len(recent_highs)-1))
                lower_lows = all(recent_lows[i] > recent_lows[i+1] for i in range(len(recent_lows)-1))

                if lower_highs and lower_lows:
                    structure = MarketStructure.LOWER_LOWS
                else:
                    structure = MarketStructure.RANGING

            return structure.value  # Return .value for backward compatibility

        except Exception as e:
            logger.debug(f"Structure analysis failed: {e}")
            return MarketStructure.UNKNOWN.value
    
    def _find_htf_levels(self, htf_df: pd.DataFrame) -> tuple:
        """
        Find HTF support and resistance levels.

        Args:
            htf_df: Higher timeframe DataFrame

        Returns:
            Tuple of (support, resistance)
        """
        try:
            lookback = min(self.lookback, len(htf_df))
            recent = htf_df.tail(lookback)

            current_price = htf_df['close'].iloc[-1]

            # Find recent swing lows (support) - levels below current price
            lows = recent['low'].values
            support_levels = [low for low in lows if low < current_price]

            # Find nearest support (closest level below current price)
            support = None
            if support_levels:
                support = max(support_levels)  # Maximum of values below current price = nearest

            # Find recent swing highs (resistance) - levels above current price
            highs = recent['high'].values
            resistance_levels = [high for high in highs if high > current_price]

            # Find nearest resistance (closest level above current price)
            resistance = None
            if resistance_levels:
                resistance = min(resistance_levels)  # Minimum of values above current price = nearest

            return support, resistance

        except Exception as e:
            logger.debug(f"HTF level finding failed: {e}")
            return None, None
    
    def _check_alignment(self, htf_trend: str, current_trend: Optional[Dict]) -> bool:
        """
        Check if current trend aligns with HTF.

        Args:
            htf_trend: HTF trend (string value from Direction enum)
            current_trend: Current timeframe trend result dict

        Returns:
            True if aligned, False otherwise
        """
        # Using Direction enum value for comparison
        if not current_trend or htf_trend == Direction.NEUTRAL.value:
            return False

        current_direction = current_trend.get('direction', Direction.NEUTRAL.value)

        return htf_trend == current_direction
    
    def _detect_structure_shift(self, htf_df: pd.DataFrame) -> bool:
        """Detect if structure has shifted recently."""
        try:
            if len(htf_df) < 10:
                return False
            
            recent_highs = htf_df['high'].tail(5).values
            recent_lows = htf_df['low'].tail(5).values
            
            # Check if recent price broke previous structure
            prev_high = htf_df['high'].iloc[-6]
            prev_low = htf_df['low'].iloc[-6]
            
            current_high = recent_highs[-1]
            current_low = recent_lows[-1]
            
            # Break of structure
            if current_high > prev_high * 1.02 or current_low < prev_low * 0.98:
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Structure shift detection failed: {e}")
            return False
    
    def _validate_context(self, context: AnalysisContext) -> bool:
        return True  # HTF data is optional
