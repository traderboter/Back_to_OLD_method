"""
ChannelAnalyzer - Price Channel Detection

Detects price channels (ascending, descending, horizontal).

Uses indicators:
- OHLC data for channel detection
- Linear regression for trendlines

Outputs to context:
- channel: {
    'channel_type': 'ascending' | 'descending' | 'horizontal',
    'upper_bound': float,
    'lower_bound': float,
    'upper_slope': float,
    'lower_slope': float,
    'upper_intercept': float,
    'lower_intercept': float,
    'channel_width': float,
    'price_position': 'upper' | 'middle' | 'lower',
    'breakout': bool,
    'strength': float (0-3)
  }
"""

from typing import Dict, Any, Optional
import logging
import pandas as pd
import numpy as np

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.enums import ChannelType, PricePosition
from signal_generation.constants import (
    CHANNEL_SLOPE_THRESHOLD,
    CHANNEL_FIT_QUALITY_EXCELLENT,
    CHANNEL_FIT_QUALITY_GOOD
)

logger = logging.getLogger(__name__)


class ChannelAnalyzer(BaseAnalyzer):
    """Analyzes price channels."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        channel_config = config.get('channel', {})

        # Default parameters (can be overridden per-TF)
        self.default_lookback = 50

        # Fallback values
        self.lookback = self.default_lookback

        self.enabled = config.get('analyzers', {}).get('channel', {}).get('enabled', True)
        
        logger.info("ChannelAnalyzer initialized")
    
    def analyze(self, context: AnalysisContext) -> None:
        """Main analysis method."""
        if not self._check_enabled():
            return
        
        if not self._validate_context(context):
            return
        
        try:
            # Get per-TF parameters
            self.lookback = self.get_threshold('lookback', self.default_lookback, context.timeframe)

            df = context.df

            if len(df) < 30:
                context.add_result('channel', {
                    'status': 'insufficient_data',
                    'channel_type': ChannelType.IRREGULAR.value  # Using Enum
                })
                return
            
            lookback = min(self.lookback, len(df))
            recent_df = df.tail(lookback)
            
            highs = recent_df['high'].values
            lows = recent_df['low'].values
            current_price = df['close'].iloc[-1]
            
            # Fit linear regression for highs and lows
            x = np.arange(len(highs))
            upper_slope, upper_intercept = np.polyfit(x, highs, 1)
            lower_slope, lower_intercept = np.polyfit(x, lows, 1)
            
            # Determine channel type - Using ChannelType Enum and Constants
            if abs(upper_slope) < CHANNEL_SLOPE_THRESHOLD and abs(lower_slope) < CHANNEL_SLOPE_THRESHOLD:
                channel_type = ChannelType.HORIZONTAL
            elif upper_slope > CHANNEL_SLOPE_THRESHOLD and lower_slope > CHANNEL_SLOPE_THRESHOLD:
                channel_type = ChannelType.ASCENDING
            elif upper_slope < -CHANNEL_SLOPE_THRESHOLD and lower_slope < -CHANNEL_SLOPE_THRESHOLD:
                channel_type = ChannelType.DESCENDING
            else:
                channel_type = ChannelType.IRREGULAR
            
            # Calculate current channel bounds
            upper_bound = upper_slope * (len(x) - 1) + upper_intercept
            lower_bound = lower_slope * (len(x) - 1) + lower_intercept
            channel_width = upper_bound - lower_bound
            
            # Price position - Using PricePosition Enum
            if current_price > upper_bound:
                position = PricePosition.ABOVE
                breakout = True
            elif current_price < lower_bound:
                position = PricePosition.BELOW
                breakout = True
            else:
                mid = (upper_bound + lower_bound) / 2
                position = PricePosition.UPPER if current_price > mid else PricePosition.LOWER
                breakout = False
            
            # Calculate strength (based on how well prices fit channel) - Using Constants
            upper_fit = highs - (upper_slope * x + upper_intercept)
            lower_fit = lows - (lower_slope * x + lower_intercept)
            fit_error = np.mean(np.abs(upper_fit)) + np.mean(np.abs(lower_fit))

            if fit_error < channel_width * CHANNEL_FIT_QUALITY_EXCELLENT:
                strength = 3
            elif fit_error < channel_width * CHANNEL_FIT_QUALITY_GOOD:
                strength = 2
            else:
                strength = 1
            
            result = {
                'status': 'ok',
                'channel_type': channel_type.value,  # Return .value for backward compatibility
                'upper_bound': round(upper_bound, 2),
                'lower_bound': round(lower_bound, 2),
                'upper_slope': round(upper_slope, 6),  # NEW: For RiskRewardCalculator
                'lower_slope': round(lower_slope, 6),  # NEW: For RiskRewardCalculator
                'upper_intercept': round(upper_intercept, 2),  # NEW: For RiskRewardCalculator
                'lower_intercept': round(lower_intercept, 2),  # NEW: For RiskRewardCalculator
                'channel_width': round(channel_width, 2),
                'price_position': position.value,  # Return .value for backward compatibility
                'breakout': breakout,
                'strength': strength
            }
            
            context.add_result('channel', result)
            
            logger.info(f"ChannelAnalyzer: {channel_type} channel for {context.symbol}")
            
        except Exception as e:
            logger.error(f"Error in ChannelAnalyzer: {e}", exc_info=True)
            context.add_result('channel', {
                'status': 'error',
                'channel_type': 'unknown',
                'error': str(e)
            })
    
    def _validate_context(self, context: AnalysisContext) -> bool:
        required = ['high', 'low', 'close']
        return all(col in context.df.columns for col in required)
