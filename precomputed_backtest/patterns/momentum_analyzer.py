"""
MomentumAnalyzer - Momentum Indicator Analysis

Analyzes momentum indicators (RSI, MACD, Stochastic) to detect:
- Overbought/oversold conditions
- Bullish/bearish divergences
- MACD crossovers
- Momentum strength and direction

Uses indicators (pre-calculated by IndicatorCalculator):
- rsi (Relative Strength Index)
- macd, macd_signal, macd_hist
- slowk, slowd (Stochastic)
- mfi (Money Flow Index)

Can read from context (context-aware):
- trend: To align momentum signals with trend direction

Outputs to context:
- momentum: {
    'direction': 'bullish' | 'bearish' | 'neutral',
    'strength': float (0-3, capped),
    'momentum_strength': float (raw strength, uncapped),
    'rsi_signal': 'overbought' | 'oversold' | 'neutral',
    'macd_signal': dict,
    'macd_market_type': str (A/B/C/D/X market types),
    'advanced_macd_signals': list of advanced MACD signals,
    'stoch_signal': dict,
    'divergence': dict | None,
    'confidence': float (0-1),
    'signals': list of all momentum signals
  }
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np
from scipy import signal as scipy_signal

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.enums import Direction, RSISignal, MACDMarketType
from signal_generation.constants import (
    RSI_OVERSOLD_THRESHOLD,
    RSI_OVERBOUGHT_THRESHOLD,
    STOCH_OVERSOLD_THRESHOLD,
    STOCH_OVERBOUGHT_THRESHOLD
)

logger = logging.getLogger(__name__)


class MomentumAnalyzer(BaseAnalyzer):
    """
    Analyzes momentum indicators for trading signals.
    
    Key features:
    1. RSI analysis (overbought/oversold)
    2. MACD analysis (crossovers, histogram)
    3. Stochastic analysis
    4. Divergence detection
    5. Context-aware scoring (considers trend)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MomentumAnalyzer.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Get momentum-specific configuration
        mom_config = config.get('momentum', {})

        # Default parameters (can be overridden per-TF)
        self.default_rsi_overbought = RSI_OVERBOUGHT_THRESHOLD
        self.default_rsi_oversold = RSI_OVERSOLD_THRESHOLD
        self.default_stoch_overbought = STOCH_OVERBOUGHT_THRESHOLD
        self.default_stoch_oversold = STOCH_OVERSOLD_THRESHOLD
        self.default_macd_threshold = 1.0

        # Fallback values
        self.rsi_overbought = mom_config.get('rsi_overbought', self.default_rsi_overbought)
        self.rsi_oversold = mom_config.get('rsi_oversold', self.default_rsi_oversold)
        self.stoch_overbought = mom_config.get('stoch_overbought', self.default_stoch_overbought)
        self.stoch_oversold = mom_config.get('stoch_oversold', self.default_stoch_oversold)
        
        # Divergence detection lookback
        self.divergence_lookback = mom_config.get('divergence_lookback', 14)

        # Advanced MACD analysis parameters
        self.macd_cross_period = mom_config.get('macd_cross_period', 10)
        self.macd_trendline_period = mom_config.get('macd_trendline_period', 30)
        self.macd_hist_period = mom_config.get('macd_hist_period', 20)

        # Peak detection settings for DIF trendline analysis
        self.macd_peak_detection = mom_config.get('macd_peak_detection', {})
        self.macd_peak_smooth_kernel = self.macd_peak_detection.get('smooth_kernel', 3)
        self.macd_peak_distance = self.macd_peak_detection.get('distance', 3)
        self.macd_peak_prominence_factor = self.macd_peak_detection.get('prominence_factor', 0.1)

        # Pattern scores from config
        self.pattern_scores = config.get('pattern_scores', {})

        # Enable/disable
        self.enabled = config.get('analyzers', {}).get('momentum', {}).get('enabled', True)

        logger.info("MomentumAnalyzer initialized successfully")
    
    def analyze(self, context: AnalysisContext) -> None:
        """
        Main analysis method - analyzes momentum indicators.

        Args:
            context: AnalysisContext with pre-calculated indicators
        """
        # 1. Check if enabled
        if not self._check_enabled():
            logger.debug(f"MomentumAnalyzer disabled for {context.symbol}")
            return

        # 2. Validate context
        if not self._validate_context(context):
            logger.warning(f"MomentumAnalyzer: Invalid context for {context.symbol}")
            return

        try:
            # 3. Read pre-calculated indicators
            df = context.df
            timeframe = context.timeframe  # Get timeframe for per-TF settings

            # Ensure we have enough data
            if len(df) < 50:
                logger.warning(f"Insufficient data for MomentumAnalyzer on {context.symbol}")
                context.add_result('momentum', {
                    'status': 'insufficient_data',
                    'direction': Direction.NEUTRAL.value,  # Using Enum
                    'strength': 0
                })
                return

            # Get current indicator values
            current_rsi = df['rsi'].iloc[-1]
            current_macd = df['macd'].iloc[-1]
            current_macd_signal = df['macd_signal'].iloc[-1]
            current_macd_hist = df['macd_hist'].iloc[-1]
            current_slowk = df['slowk'].iloc[-1]
            current_slowd = df['slowd'].iloc[-1]

            # 4. Analyze RSI (with per-TF thresholds)
            rsi_analysis = self._analyze_rsi(df, timeframe)

            # 5. Analyze MACD (with per-TF thresholds)
            macd_analysis = self._analyze_macd(df, timeframe)
            
            # 6. Analyze Stochastic (with per-TF thresholds)
            stoch_analysis = self._analyze_stochastic(df, timeframe)

            # 7. NEW: Check MFI signals
            mfi_signals = self._check_mfi_signals(df)

            # 8. NEW: Check MACD zero cross signals
            macd_zero_signals = self._check_macd_zero_cross(df)

            # 9. Detect divergences
            divergence = self._detect_divergences(df)

            # 10. NEW: Advanced MACD analysis (from old system)
            # Market type detection
            macd_market_type = self._detect_macd_market_type(df)

            # DIF zero crosses (with first/second counting)
            dif_zero_crosses = self._detect_dif_zero_crosses(df)

            # DIF trendline breaks
            dif_trendline_breaks = self._detect_dif_trendline_breaks(df)

            # Advanced histogram analysis
            histogram_signals = self._analyze_macd_histogram_advanced(df)

            # 11. Calculate overall momentum direction and strength (with new signals)
            momentum_result = self._calculate_momentum(
                rsi_analysis,
                macd_analysis,
                stoch_analysis,
                divergence,
                mfi_signals,
                macd_zero_signals,
                dif_zero_crosses,
                dif_trendline_breaks,
                histogram_signals
            )

            # 12. Context-aware scoring (read trend from context if available)
            trend_context = context.get_result('trend')
            if trend_context:
                momentum_result = self._adjust_for_trend_alignment(
                    momentum_result,
                    trend_context
                )

            # 13. Generate momentum signals (including all advanced MACD signals)
            signals = self._generate_signals(
                rsi_analysis,
                macd_analysis,
                stoch_analysis,
                divergence,
                mfi_signals,
                macd_zero_signals,
                dif_zero_crosses,
                dif_trendline_breaks,
                histogram_signals
            )

            # 14. Calculate confidence
            confidence = self._calculate_confidence(
                momentum_result,
                rsi_analysis,
                macd_analysis,
                stoch_analysis,
                divergence
            )

            # 15. Build final result
            # Collect all advanced MACD signals for easy access
            advanced_macd_signals = (
                dif_zero_crosses +
                dif_trendline_breaks +
                histogram_signals
            )

            result = {
                'status': 'ok',
                'direction': momentum_result['direction'],
                'strength': momentum_result['strength'],
                'momentum_strength': abs(momentum_result['bullish_score'] - momentum_result['bearish_score']),  # NEW: Raw momentum strength (uncapped)
                'rsi_signal': rsi_analysis['signal'],
                'macd_signal': macd_analysis,
                'macd_market_type': macd_market_type,  # NEW: Market type detection
                'advanced_macd_signals': advanced_macd_signals,  # NEW: Advanced MACD signals list
                'stoch_signal': stoch_analysis,
                'divergence': divergence,
                'confidence': confidence,
                'signals': signals,
                'details': {
                    'rsi': round(current_rsi, 2),
                    'macd': round(current_macd, 5),
                    'macd_signal': round(current_macd_signal, 5),
                    'macd_hist': round(current_macd_hist, 5),
                    'slowk': round(current_slowk, 2),
                    'slowd': round(current_slowd, 2)
                }
            }
            
            # 16. Store in context
            context.add_result('momentum', result)

            logger.info(
                f"MomentumAnalyzer completed for {context.symbol} {context.timeframe}: "
                f"{result['direction']} (strength: {result['strength']}, "
                f"confidence: {confidence:.2f}, market_type: {macd_market_type})"
            )
            
        except Exception as e:
            logger.error(f"Error in MomentumAnalyzer for {context.symbol}: {e}", exc_info=True)
            context.add_result('momentum', {
                'status': 'error',
                'direction': Direction.NEUTRAL.value,  # Using Enum
                'strength': 0,
                'error': str(e)
            })
    
    def _analyze_rsi(self, df: pd.DataFrame, timeframe: str = None) -> Dict[str, Any]:
        """
        REFACTORED: Now uses RSISignal Enum for type safety and per-TF thresholds.

        Analyze RSI indicator with per-timeframe threshold support.

        Args:
            df: DataFrame with RSI column
            timeframe: Current timeframe for per-TF thresholds

        Returns:
            Dictionary with RSI analysis (using RSISignal.value for backward compatibility)
        """
        current_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2] if len(df) > 1 else current_rsi

        # Get per-TF thresholds (or fall back to global/default)
        rsi_overbought = self.get_threshold('rsi_overbought', RSI_OVERBOUGHT_THRESHOLD, timeframe)
        rsi_oversold = self.get_threshold('rsi_oversold', RSI_OVERSOLD_THRESHOLD, timeframe)

        # Determine signal - Using RSISignal Enum for type safety
        if current_rsi >= rsi_overbought:
            signal = RSISignal.OVERBOUGHT
        elif current_rsi <= rsi_oversold:
            signal = RSISignal.OVERSOLD
        else:
            signal = RSISignal.NEUTRAL

        # Check for RSI crossing levels
        rsi_crossing_up = prev_rsi < rsi_oversold <= current_rsi
        rsi_crossing_down = prev_rsi > rsi_overbought >= current_rsi

        # Check for reversal (old system logic):
        # Bullish: RSI < 30 AND RSI > prev_RSI (reversing up while oversold)
        # Bearish: RSI > 70 AND RSI < prev_RSI (reversing down while overbought)
        oversold_reversal = current_rsi < rsi_oversold and current_rsi > prev_rsi
        overbought_reversal = current_rsi > rsi_overbought and current_rsi < prev_rsi

        return {
            'value': current_rsi,
            'signal': signal.value,  # Return .value for backward compatibility
            'crossing_up': rsi_crossing_up,
            'crossing_down': rsi_crossing_down,
            'bullish': oversold_reversal,  # Changed to check for reversal
            'bearish': overbought_reversal  # Changed to check for reversal
        }
    
    def _analyze_macd(self, df: pd.DataFrame, timeframe: str = None) -> Dict[str, Any]:
        """
        Analyze MACD indicator with per-timeframe threshold support.

        Args:
            df: DataFrame with MACD columns
            timeframe: Current timeframe for per-TF thresholds

        Returns:
            Dictionary with MACD analysis
        """
        current_macd = df['macd'].iloc[-1]
        current_signal = df['macd_signal'].iloc[-1]
        current_hist = df['macd_hist'].iloc[-1]
        
        prev_macd = df['macd'].iloc[-2] if len(df) > 1 else current_macd
        prev_signal = df['macd_signal'].iloc[-2] if len(df) > 1 else current_signal
        prev_hist = df['macd_hist'].iloc[-2] if len(df) > 1 else current_hist
        
        # Detect crossovers
        bullish_crossover = (prev_macd <= prev_signal and 
                            current_macd > current_signal)
        bearish_crossover = (prev_macd >= prev_signal and 
                            current_macd < current_signal)
        
        # Histogram analysis
        hist_increasing = current_hist > prev_hist
        hist_positive = current_hist > 0
        
        # Determine direction - Using Direction Enum for type safety
        if current_macd > current_signal:
            direction = Direction.BULLISH
        elif current_macd < current_signal:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL

        return {
            'value': current_macd,
            'signal_value': current_signal,
            'histogram': current_hist,
            'direction': direction.value,  # Return .value for backward compatibility
            'bullish_crossover': bullish_crossover,
            'bearish_crossover': bearish_crossover,
            'hist_increasing': hist_increasing,
            'hist_positive': hist_positive
        }
    
    def _analyze_stochastic(self, df: pd.DataFrame, timeframe: str = None) -> Dict[str, Any]:
        """
        Analyze Stochastic indicator.

        Args:
            df: DataFrame with Stochastic columns
            timeframe: Current timeframe for per-TF thresholds

        Returns:
            Dictionary with Stochastic analysis
        """
        # Get per-TF thresholds
        stoch_overbought = self.get_threshold('stoch_overbought', self.default_stoch_overbought, timeframe)
        stoch_oversold = self.get_threshold('stoch_oversold', self.default_stoch_oversold, timeframe)

        current_k = df['slowk'].iloc[-1]
        current_d = df['slowd'].iloc[-1]

        prev_k = df['slowk'].iloc[-2] if len(df) > 1 else current_k
        prev_d = df['slowd'].iloc[-2] if len(df) > 1 else current_d

        # Determine signal
        if current_k >= stoch_overbought:
            signal = 'overbought'
        elif current_k <= stoch_oversold:
            signal = 'oversold'
        else:
            signal = 'neutral'
        
        # Detect crossovers
        bullish_crossover = prev_k <= prev_d and current_k > current_d
        bearish_crossover = prev_k >= prev_d and current_k < current_d
        
        return {
            'k_value': current_k,
            'd_value': current_d,
            'signal': signal,
            'bullish_crossover': bullish_crossover,
            'bearish_crossover': bearish_crossover
        }
    
    def _check_mfi_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check MFI (Money Flow Index) signals.

        MFI is a volume-weighted momentum indicator that shows overbought/oversold
        conditions based on both price and volume.

        Args:
            df: DataFrame with MFI column

        Returns:
            Dictionary with MFI signals (bullish/bearish scores)
        """
        if 'mfi' not in df.columns or len(df) < 2:
            return {'bullish_signal': 0.0, 'bearish_signal': 0.0, 'active': False}

        mfi = df['mfi'].iloc[-1]
        mfi_prev = df['mfi'].iloc[-2]

        bullish_signal = 0.0
        bearish_signal = 0.0
        signal_type = None

        # MFI Oversold reversal (old system logic):
        # MFI < 20 AND MFI > prev_MFI (reversing up while still oversold)
        if mfi < 20 and mfi > mfi_prev:
            bullish_signal = 2.4
            signal_type = 'mfi_oversold_reversal'
            logger.debug(f"MFI oversold reversal detected: {mfi_prev:.1f} → {mfi:.1f}")

        # MFI Overbought reversal (old system logic):
        # MFI > 80 AND MFI < prev_MFI (reversing down while still overbought)
        elif mfi > 80 and mfi < mfi_prev:
            bearish_signal = 2.4
            signal_type = 'mfi_overbought_reversal'
            logger.debug(f"MFI overbought reversal detected: {mfi_prev:.1f} → {mfi:.1f}")

        return {
            'bullish_signal': bullish_signal,
            'bearish_signal': bearish_signal,
            'active': bullish_signal > 0 or bearish_signal > 0,
            'signal_type': signal_type,
            'mfi_value': mfi
        }

    def _check_macd_zero_cross(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check MACD zero line crossovers.

        Zero line crosses indicate shift in momentum direction.
        Crossing above zero = bullish, crossing below = bearish.

        Args:
            df: DataFrame with MACD column

        Returns:
            Dictionary with MACD zero cross signals
        """
        if 'macd' not in df.columns or len(df) < 2:
            return {'bullish_signal': 0.0, 'bearish_signal': 0.0, 'active': False}

        macd = df['macd'].iloc[-1]
        macd_prev = df['macd'].iloc[-2]

        bullish_signal = 0.0
        bearish_signal = 0.0
        signal_type = None

        # MACD crosses above zero (signal 3) - old system score: 1.8
        if macd_prev <= 0 and macd > 0:
            bullish_signal = 1.8
            signal_type = 'macd_zero_cross_up'
            logger.debug(f"MACD crosses above zero: {macd_prev:.5f} → {macd:.5f}")

        # MACD crosses below zero (signal 4) - old system score: 1.8
        elif macd_prev >= 0 and macd < 0:
            bearish_signal = 1.8
            signal_type = 'macd_zero_cross_down'
            logger.debug(f"MACD crosses below zero: {macd_prev:.5f} → {macd:.5f}")

        return {
            'bullish_signal': bullish_signal,
            'bearish_signal': bearish_signal,
            'active': bullish_signal > 0 or bearish_signal > 0,
            'signal_type': signal_type,
            'macd_value': macd
        }

    def _detect_divergences(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bullish/bearish divergences between price and RSI.
        
        Args:
            df: DataFrame with price and RSI
            
        Returns:
            Divergence dict if found, None otherwise
        """
        try:
            lookback = min(self.divergence_lookback, len(df))
            if lookback < 5:
                return None
            
            recent_df = df.tail(lookback)
            
            # Find price lows and highs
            price_lows = recent_df['low'].rolling(window=3, center=True).min()
            price_highs = recent_df['high'].rolling(window=3, center=True).max()
            
            # Find RSI lows and highs
            rsi_lows = recent_df['rsi'].rolling(window=3, center=True).min()
            rsi_highs = recent_df['rsi'].rolling(window=3, center=True).max()
            
            # Bullish divergence: price making lower low, RSI making higher low
            # Ensure we have enough data before accessing indices
            price_lower_low = False
            rsi_higher_low = False

            if len(price_lows) >= 6:  # Need at least 6 to safely access iloc[-5]
                price_lower_low = price_lows.iloc[-1] < price_lows.iloc[-5]
                rsi_higher_low = rsi_lows.iloc[-1] > rsi_lows.iloc[-5]

            if price_lower_low and rsi_higher_low:
                return {
                    'type': 'bullish',
                    'strength': 'strong' if rsi_lows.iloc[-1] < 40 else 'moderate'
                }

            # Bearish divergence: price making higher high, RSI making lower high
            price_higher_high = False
            rsi_lower_high = False

            if len(price_highs) >= 6:  # Need at least 6 to safely access iloc[-5]
                price_higher_high = price_highs.iloc[-1] > price_highs.iloc[-5]
                rsi_lower_high = rsi_highs.iloc[-1] < rsi_highs.iloc[-5]

            if price_higher_high and rsi_lower_high:
                return {
                    'type': 'bearish',
                    'strength': 'strong' if rsi_highs.iloc[-1] > 60 else 'moderate'
                }

            return None
            
        except Exception as e:
            logger.debug(f"Divergence detection failed: {e}")
            return None
    
    def _calculate_momentum(
        self,
        rsi: Dict,
        macd: Dict,
        stoch: Dict,
        divergence: Optional[Dict],
        mfi_signals: Dict,
        macd_zero_signals: Dict,
        dif_zero_crosses: List[Dict],
        dif_trendline_breaks: List[Dict],
        histogram_signals: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calculate overall momentum direction and strength.

        Args:
            rsi: RSI analysis
            macd: MACD analysis
            stoch: Stochastic analysis
            divergence: Divergence analysis
            mfi_signals: MFI signal analysis
            macd_zero_signals: MACD zero cross analysis
            dif_zero_crosses: DIF zero cross signals (NEW)
            dif_trendline_breaks: DIF trendline break signals (NEW)
            histogram_signals: Advanced histogram signals (NEW)

        Returns:
            Dictionary with momentum direction and strength
        """
        bullish_score = 0.0
        bearish_score = 0.0

        # RSI contribution (old system: 2.3 for oversold/overbought reversal)
        if rsi['bullish']:
            bullish_score += 2.3
        if rsi['bearish']:
            bearish_score += 2.3

        # MACD crossover contribution (old system: 2.2 for crossover)
        if macd['bullish_crossover']:
            bullish_score += 2.2
        if macd['bearish_crossover']:
            bearish_score += 2.2

        # Stochastic contribution (old system: 2.5 for oversold/overbought crossover)
        if stoch['signal'] == 'oversold' and stoch['bullish_crossover']:
            bullish_score += 2.5
        if stoch['signal'] == 'overbought' and stoch['bearish_crossover']:
            bearish_score += 2.5

        # MFI contribution (old system: 2.4 for reversal)
        if mfi_signals['active']:
            bullish_score += mfi_signals['bullish_signal']  # Already 2.4
            bearish_score += mfi_signals['bearish_signal']  # Already 2.4

        # MACD zero cross contribution (old system: 1.8 for zero cross)
        if macd_zero_signals['active']:
            bullish_score += macd_zero_signals['bullish_signal']
            bearish_score += macd_zero_signals['bearish_signal']

        # Divergence contribution (old system: 3.5)
        if divergence:
            if divergence['type'] == 'bullish':
                bullish_score += 3.5
            else:
                bearish_score += 3.5

        # NEW: DIF zero crosses contribution (score: 2.0)
        for signal in dif_zero_crosses:
            if signal['direction'] == 'bullish':
                bullish_score += signal['score']
            else:
                bearish_score += signal['score']

        # NEW: DIF trendline breaks contribution (score: 3.0)
        for signal in dif_trendline_breaks:
            if signal['direction'] == 'bullish':
                bullish_score += signal['score']
            else:
                bearish_score += signal['score']

        # NEW: Histogram signals contribution (scores: 1.5, 2.0, 3.8)
        for signal in histogram_signals:
            if signal['direction'] == 'bullish':
                bullish_score += signal['score']
            else:
                bearish_score += signal['score']

        # Determine direction and strength
        if bullish_score > bearish_score:
            direction = 'bullish'
            strength = min(bullish_score - bearish_score, 3)
        elif bearish_score > bullish_score:
            direction = 'bearish'
            strength = min(bearish_score - bullish_score, 3)
        else:
            direction = 'neutral'
            strength = 0

        return {
            'direction': direction,
            'strength': strength,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score
        }
    
    def _adjust_for_trend_alignment(
        self,
        momentum: Dict,
        trend: Dict
    ) -> Dict:
        """
        Adjust momentum scores based on trend alignment (context-aware).
        
        Args:
            momentum: Momentum result
            trend: Trend result from context
            
        Returns:
            Adjusted momentum result
        """
        trend_direction = trend.get('direction', 'neutral')
        momentum_direction = momentum['direction']
        
        # Bonus for trend alignment
        if trend_direction == momentum_direction:
            momentum['strength'] = min(momentum['strength'] * 1.2, 3)
            momentum['trend_aligned'] = True
        else:
            momentum['trend_aligned'] = False
        
        return momentum
    
    def _generate_signals(
        self,
        rsi: Dict,
        macd: Dict,
        stoch: Dict,
        divergence: Optional[Dict],
        mfi_signals: Dict,
        macd_zero_signals: Dict,
        dif_zero_crosses: List[Dict],
        dif_trendline_breaks: List[Dict],
        histogram_signals: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate specific momentum signals.

        Args:
            rsi, macd, stoch: Indicator analyses
            divergence: Divergence analysis
            mfi_signals: MFI signal analysis
            macd_zero_signals: MACD zero cross analysis
            dif_zero_crosses: DIF zero cross signals (NEW)
            dif_trendline_breaks: DIF trendline break signals (NEW)
            histogram_signals: Advanced histogram signals (NEW)

        Returns:
            List of signal dictionaries
        """
        signals = []

        # RSI signals (old system score: 2.3)
        if rsi['crossing_up']:
            signals.append({
                'type': 'rsi_oversold_bounce',
                'direction': 'bullish',
                'strength': 2.3,
                'description': 'RSI crossed above oversold level'
            })

        if rsi['crossing_down']:
            signals.append({
                'type': 'rsi_overbought_reversal',
                'direction': 'bearish',
                'strength': 2.3,
                'description': 'RSI crossed below overbought level'
            })

        # MACD signals (signal line crossovers) - old system score: 2.2
        if macd['bullish_crossover']:
            signals.append({
                'type': 'macd_bullish_cross',
                'direction': 'bullish',
                'strength': 2.2,
                'description': 'MACD bullish crossover'
            })

        if macd['bearish_crossover']:
            signals.append({
                'type': 'macd_bearish_cross',
                'direction': 'bearish',
                'strength': 2.2,
                'description': 'MACD bearish crossover'
            })

        # MFI signals (old system score: 2.4)
        if mfi_signals['active']:
            if mfi_signals['bullish_signal'] > 0:
                signals.append({
                    'type': 'mfi_oversold_reversal',
                    'direction': 'bullish',
                    'strength': 2.4,
                    'description': f'MFI oversold reversal (MFI: {mfi_signals["mfi_value"]:.1f})'
                })
            elif mfi_signals['bearish_signal'] > 0:
                signals.append({
                    'type': 'mfi_overbought_reversal',
                    'direction': 'bearish',
                    'strength': 2.4,
                    'description': f'MFI overbought reversal (MFI: {mfi_signals["mfi_value"]:.1f})'
                })

        # MACD zero cross signals (old system score: 1.8)
        if macd_zero_signals['active']:
            if macd_zero_signals['bullish_signal'] > 0:
                signals.append({
                    'type': 'macd_zero_cross_up',
                    'direction': 'bullish',
                    'strength': 1.8,
                    'description': f'MACD crosses above zero line (MACD: {macd_zero_signals["macd_value"]:.5f})'
                })
            elif macd_zero_signals['bearish_signal'] > 0:
                signals.append({
                    'type': 'macd_zero_cross_down',
                    'direction': 'bearish',
                    'strength': 1.8,
                    'description': f'MACD crosses below zero line (MACD: {macd_zero_signals["macd_value"]:.5f})'
                })

        # Stochastic signals (old system score: 2.5)
        if stoch['bullish_crossover'] and stoch['signal'] == 'oversold':
            signals.append({
                'type': 'stoch_bullish_cross',
                'direction': 'bullish',
                'strength': 2.5,
                'description': 'Stochastic bullish crossover in oversold'
            })

        if stoch['bearish_crossover'] and stoch['signal'] == 'overbought':
            signals.append({
                'type': 'stoch_bearish_cross',
                'direction': 'bearish',
                'strength': 2.5,
                'description': 'Stochastic bearish crossover in overbought'
            })

        # Divergence signals (old system score: 3.5 × strength)
        if divergence:
            signals.append({
                'type': f'{divergence["type"]}_divergence',
                'direction': divergence['type'],
                'strength': 3.5,  # Base score from old system
                'description': f'{divergence["type"].capitalize()} divergence detected'
            })

        # NEW: DIF zero cross signals (score: 2.0)
        for signal in dif_zero_crosses:
            signals.append({
                'type': signal['type'],
                'direction': signal['direction'],
                'strength': signal['score'],
                'description': f"DIF {signal['type'].replace('dif_cross_zero_', '').replace('_', ' ')}"
            })

        # NEW: DIF trendline break signals (score: 3.0)
        for signal in dif_trendline_breaks:
            signals.append({
                'type': signal['type'],
                'direction': signal['direction'],
                'strength': signal['score'],
                'description': f"DIF trendline break {signal['direction']}"
            })

        # NEW: Histogram signals (scores: 1.5, 2.0, 3.8)
        for signal in histogram_signals:
            description_map = {
                'macd_hist_shrink_head': 'MACD histogram shrink head (bearish reversal)',
                'macd_hist_pull_feet': 'MACD histogram pull feet (bullish reversal)',
                'macd_hist_top_divergence': 'MACD histogram bearish divergence (very strong)',
                'macd_hist_bottom_divergence': 'MACD histogram bullish divergence (very strong)',
                'macd_hist_kill_long_bin': 'MACD histogram kill long bin (bearish)'
            }
            signals.append({
                'type': signal['type'],
                'direction': signal['direction'],
                'strength': signal['score'],
                'description': description_map.get(signal['type'], signal['type'])
            })

        return signals
    
    def _calculate_confidence(
        self,
        momentum: Dict,
        rsi: Dict,
        macd: Dict,
        stoch: Dict,
        divergence: Optional[Dict]
    ) -> float:
        """
        Calculate confidence score.
        
        Args:
            momentum, rsi, macd, stoch, divergence: Analysis results
            
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5
        
        # Strong momentum increases confidence
        if momentum['strength'] >= 3:
            confidence += 0.3
        elif momentum['strength'] == 2:
            confidence += 0.2
        elif momentum['strength'] == 1:
            confidence += 0.1
        
        # Multiple confirming indicators
        if macd['direction'] == momentum['direction']:
            confidence += 0.1
        
        # Divergence is strong signal
        if divergence:
            confidence += 0.2
        
        # Trend alignment
        if momentum.get('trend_aligned'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _detect_macd_market_type(self, df: pd.DataFrame) -> str:
        """
        REFACTORED: Now uses MACDMarketType Enum for type safety.

        Detect MACD market type based on DIF, HIST, and EMA alignment.

        Market types (from old system):
        - A_bullish_strong: DIF > 0, HIST > 0, EMA20 > EMA50
        - B_bullish_normal: DIF > 0, HIST < 0, EMA20 > EMA50
        - C_bearish_strong: DIF < 0, HIST < 0, EMA20 < EMA50
        - D_bearish_normal: DIF < 0, HIST > 0, EMA20 < EMA50
        - X_transition: Everything else

        Args:
            df: DataFrame with MACD and EMA columns

        Returns:
            Market type string (using MACDMarketType.value for backward compatibility)
        """
        try:
            if len(df) < 1:
                return "unknown_data"

            curr_dif = df['macd'].iloc[-1]  # DIF = MACD line
            curr_hist = df['macd_hist'].iloc[-1]

            # Check if we have EMA20 and EMA50
            has_ema = 'ema20' in df.columns and 'ema50' in df.columns
            if has_ema:
                curr_ema20 = df['ema20'].iloc[-1]
                curr_ema50 = df['ema50'].iloc[-1]
                ema_bullish = curr_ema20 > curr_ema50
            else:
                # Fallback: use close vs sma50 or just assume based on MACD
                ema_bullish = curr_dif > 0

            # Market type detection - Using MACDMarketType Enum for type safety
            if curr_dif > 0 and curr_hist > 0 and ema_bullish:
                market_type = MACDMarketType.A_BULLISH_STRONG
            elif curr_dif > 0 and curr_hist < 0 and ema_bullish:
                market_type = MACDMarketType.B_BULLISH_NORMAL
            elif curr_dif < 0 and curr_hist < 0 and not ema_bullish:
                market_type = MACDMarketType.C_BEARISH_STRONG
            elif curr_dif < 0 and curr_hist > 0 and not ema_bullish:
                market_type = MACDMarketType.D_BEARISH_NORMAL
            else:
                market_type = MACDMarketType.X_TRANSITION

            return market_type.value  # Return .value for backward compatibility

        except Exception as e:
            logger.error(f"MACD market type detection error: {e}")
            return "error"

    def _find_peaks_and_valleys(
        self,
        data: np.ndarray,
        distance: int = 3,
        prominence_factor: float = 0.1
    ) -> Tuple[List[int], List[int]]:
        """
        Find peaks and valleys in data using scipy.

        Args:
            data: 1D array of values
            distance: Minimum distance between peaks
            prominence_factor: Prominence threshold as factor of data range

        Returns:
            Tuple of (peaks_indices, valleys_indices)
        """
        try:
            if len(data) < 5:
                return [], []

            # Calculate prominence threshold
            data_range = np.ptp(data)  # Peak-to-peak (max - min)
            prominence = data_range * prominence_factor

            # Find peaks
            peaks, _ = scipy_signal.find_peaks(
                data,
                distance=distance,
                prominence=prominence
            )

            # Find valleys (peaks of inverted signal)
            valleys, _ = scipy_signal.find_peaks(
                -data,
                distance=distance,
                prominence=prominence
            )

            return peaks.tolist(), valleys.tolist()

        except Exception as e:
            logger.debug(f"Peak/valley detection error: {e}")
            return [], []

    def _detect_dif_zero_crosses(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect DIF (MACD line) zero line crosses with first/second counting.

        Args:
            df: DataFrame with MACD column

        Returns:
            List of zero cross signals
        """
        signals = []

        try:
            if len(df) < 2:
                return signals

            dif_vals = df['macd'].values

            # Track crosses in recent window
            cross_up_count = 0
            cross_down_count = 0

            for i in range(1, len(dif_vals)):
                crossed_up = dif_vals[i - 1] < 0 and dif_vals[i] > 0
                crossed_down = dif_vals[i - 1] > 0 and dif_vals[i] < 0

                if crossed_up:
                    cross_up_count += 1
                    if i == len(dif_vals) - 1:  # Only report if it's the last candle
                        signal_type = f"dif_cross_zero_up_{'first' if cross_up_count == 1 else 'second'}"
                        score = self.pattern_scores.get(signal_type, 2.0)
                        signals.append({
                            'type': signal_type,
                            'direction': 'bullish',
                            'score': score,
                            'strength': 1.0
                        })

                elif crossed_down:
                    cross_down_count += 1
                    if i == len(dif_vals) - 1:  # Only report if it's the last candle
                        signal_type = f"dif_cross_zero_down_{'first' if cross_down_count == 1 else 'second'}"
                        score = self.pattern_scores.get(signal_type, 2.0)
                        signals.append({
                            'type': signal_type,
                            'direction': 'bearish',
                            'score': score,
                            'strength': 1.0
                        })

            return signals

        except Exception as e:
            logger.error(f"DIF zero cross detection error: {e}")
            return []

    def _detect_dif_trendline_breaks(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect DIF trendline breaks (old system logic).

        Analyzes DIF line for trendline breaks using peak/valley detection
        and trendline projection.

        Args:
            df: DataFrame with MACD column

        Returns:
            List of trendline break signals
        """
        signals = []

        try:
            if len(df) < self.macd_trendline_period:
                return signals

            # Get DIF window
            dif_window = df['macd'].iloc[-self.macd_trendline_period:]

            # Smooth DIF for peak detection
            if len(dif_window) > self.macd_peak_smooth_kernel * 2:
                smooth_dif = scipy_signal.medfilt(
                    dif_window.values,
                    kernel_size=self.macd_peak_smooth_kernel
                )

                # Find peaks and valleys
                peaks_rel, valleys_rel = self._find_peaks_and_valleys(
                    smooth_dif,
                    distance=self.macd_peak_distance,
                    prominence_factor=self.macd_peak_prominence_factor
                )

                # Check for trendline break up (resistance break)
                if len(peaks_rel) >= 2:
                    break_signal = self._check_trendline_break(
                        smooth_dif,
                        dif_window.values,
                        peaks_rel,
                        is_resistance=True
                    )
                    if break_signal:
                        signals.append(break_signal)

                # Check for trendline break down (support break)
                if len(valleys_rel) >= 2:
                    break_signal = self._check_trendline_break(
                        smooth_dif,
                        dif_window.values,
                        valleys_rel,
                        is_resistance=False
                    )
                    if break_signal:
                        signals.append(break_signal)

            return signals

        except Exception as e:
            logger.error(f"DIF trendline break detection error: {e}")
            return []

    def _check_trendline_break(
        self,
        smooth_data: np.ndarray,
        raw_data: np.ndarray,
        points: List[int],
        is_resistance: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a trendline formed by points has been broken.

        Args:
            smooth_data: Smoothed data for trendline calculation
            raw_data: Raw data for break detection
            points: List of peak/valley indices
            is_resistance: True for resistance (peaks), False for support (valleys)

        Returns:
            Signal dict if break detected, None otherwise
        """
        try:
            if len(points) < 2:
                return None

            # Use last two points to form trendline
            p1_idx, p2_idx = points[-2], points[-1]
            p1_val, p2_val = smooth_data[p1_idx], smooth_data[p2_idx]

            if p2_idx == p1_idx:
                return None

            # Calculate trendline: y = k*x + b
            k = (p2_val - p1_val) / (p2_idx - p1_idx)
            b = p1_val - k * p1_idx

            # Check recent candles after p2 for break
            for i in range(p2_idx + 1, len(raw_data)):
                trendline_val = k * i + b
                current_val = raw_data[i]
                margin = abs(current_val * 0.01)

                # Check for break
                if is_resistance and current_val > trendline_val + margin:
                    # Upward break (bullish)
                    score = self.pattern_scores.get('dif_trendline_break_up', 3.0)
                    return {
                        'type': 'dif_trendline_break_up',
                        'direction': 'bullish',
                        'score': score,
                        'strength': 1.0
                    }
                elif not is_resistance and current_val < trendline_val - margin:
                    # Downward break (bearish)
                    score = self.pattern_scores.get('dif_trendline_break_down', 3.0)
                    return {
                        'type': 'dif_trendline_break_down',
                        'direction': 'bearish',
                        'score': score,
                        'strength': 1.0
                    }

            return None

        except Exception as e:
            logger.debug(f"Trendline break check error: {e}")
            return None

    def _analyze_macd_histogram_advanced(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Advanced MACD histogram analysis (old system logic).

        Detects:
        1. Shrink head / pull feet patterns (score: 1.5)
        2. Histogram divergence with price (score: 3.8)
        3. Kill long bin pattern (score: 2.0)

        Args:
            df: DataFrame with MACD histogram and price data

        Returns:
            List of histogram signals
        """
        signals = []

        try:
            if len(df) < self.macd_hist_period:
                return signals

            hist = df['macd_hist']
            close = df['close']

            # Find peaks and valleys in histogram
            peaks_idx, valleys_idx = self._find_peaks_and_valleys(
                hist.values,
                distance=self.macd_peak_distance,
                prominence_factor=self.macd_peak_prominence_factor
            )

            # 1. Shrink head pattern (histogram peak > 0 indicates potential reversal)
            for idx in peaks_idx:
                if idx < len(hist) - 10:  # Not too recent, need confirmation
                    continue
                if hist.iloc[idx] > 0:
                    score = self.pattern_scores.get('macd_hist_shrink_head', 1.5)
                    signals.append({
                        'type': 'macd_hist_shrink_head',
                        'direction': 'bearish',
                        'score': score,
                        'strength': 0.8
                    })

            # 2. Pull feet pattern (histogram valley < 0 indicates potential reversal)
            for idx in valleys_idx:
                if idx < len(hist) - 10:  # Not too recent
                    continue
                if hist.iloc[idx] < 0:
                    score = self.pattern_scores.get('macd_hist_pull_feet', 1.5)
                    signals.append({
                        'type': 'macd_hist_pull_feet',
                        'direction': 'bullish',
                        'score': score,
                        'strength': 0.8
                    })

            # 3. Histogram divergence with price (very important, score: 3.8)
            # Bearish divergence: price higher high, histogram lower high
            if len(peaks_idx) >= 2:
                p1_idx, p2_idx = peaks_idx[-2], peaks_idx[-1]
                if p2_idx > len(hist) - 15:  # Recent enough
                    hist_lower_high = hist.iloc[p2_idx] < hist.iloc[p1_idx]
                    price_higher_high = close.iloc[p2_idx] > close.iloc[p1_idx]

                    if hist_lower_high and price_higher_high:
                        score = self.pattern_scores.get('macd_hist_top_divergence', 3.8)
                        signals.append({
                            'type': 'macd_hist_top_divergence',
                            'direction': 'bearish',
                            'score': score,
                            'strength': 1.5
                        })

            # Bullish divergence: price lower low, histogram higher low
            if len(valleys_idx) >= 2:
                v1_idx, v2_idx = valleys_idx[-2], valleys_idx[-1]
                if v2_idx > len(hist) - 15:  # Recent enough
                    hist_higher_low = hist.iloc[v2_idx] > hist.iloc[v1_idx]
                    price_lower_low = close.iloc[v2_idx] < close.iloc[v1_idx]

                    if hist_higher_low and price_lower_low:
                        score = self.pattern_scores.get('macd_hist_bottom_divergence', 3.8)
                        signals.append({
                            'type': 'macd_hist_bottom_divergence',
                            'direction': 'bullish',
                            'score': score,
                            'strength': 1.5
                        })

            # 4. Kill long bin pattern (consecutive valleys below zero)
            if len(valleys_idx) >= 2:
                for i in range(len(valleys_idx) - 1):
                    v1_idx, v2_idx = valleys_idx[i], valleys_idx[i + 1]
                    if v2_idx < len(hist) - 10:  # Not recent enough
                        continue

                    # Both valleys below zero
                    if hist.iloc[v1_idx] < 0 and hist.iloc[v2_idx] < 0:
                        # Check if histogram stayed below zero between them
                        hist_between = hist.iloc[v1_idx:v2_idx + 1]
                        if hist_between.max() < 0:
                            score = self.pattern_scores.get('macd_hist_kill_long_bin', 2.0)
                            signals.append({
                                'type': 'macd_hist_kill_long_bin',
                                'direction': 'bearish',
                                'score': score,
                                'strength': 1.0
                            })
                            break  # Only report once

            return signals

        except Exception as e:
            logger.error(f"Advanced histogram analysis error: {e}")
            return []

    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate required indicators"""
        required = ['rsi', 'macd', 'macd_signal', 'macd_hist', 'slowk', 'slowd']

        df = context.df
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False

        return True
