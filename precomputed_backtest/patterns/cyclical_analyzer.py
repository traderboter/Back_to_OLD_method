"""
CyclicalAnalyzer - Cyclical Pattern and Cycle Detection

Detects recurring cycles and forecasts potential reversal points.

Uses indicators:
- close price for cycle detection
- Simple cycle detection algorithms

Outputs to context:
- cyclical: {
    'dominant_cycle': int (in periods),
    'cycle_phase': 'top' | 'bottom' | 'rising' | 'falling',
    'next_reversal_in': int (periods),
    'confidence': float (0-1)
  }
"""

from typing import Dict, Any, Optional, List
import logging
import pandas as pd
import numpy as np
from scipy import fft

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.enums import CyclePhase

logger = logging.getLogger(__name__)


class CyclicalAnalyzer(BaseAnalyzer):
    """Analyzes cyclical patterns in price."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        cyclical_config = config.get('cyclical', {})

        # Default parameters (can be overridden per-TF)
        self.default_lookback = 200
        self.default_min_cycle = 10
        self.default_max_cycle = 100
        self.default_min_cycles_for_forecast = 2
        self.default_forecast_length = 20

        # Fallback values
        self.lookback = self.default_lookback
        self.min_cycle = self.default_min_cycle
        self.max_cycle = self.default_max_cycle
        self.min_cycles_for_forecast = self.default_min_cycles_for_forecast
        self.forecast_length = self.default_forecast_length

        # Non-TF specific settings
        self.use_fft = cyclical_config.get('use_fft', True)  # Enable FFT by default

        self.enabled = config.get('analyzers', {}).get('cyclical', {}).get('enabled', True)

        logger.info(f"CyclicalAnalyzer initialized (FFT: {self.use_fft})")
    
    def analyze(self, context: AnalysisContext) -> None:
        """Main analysis method."""
        if not self._check_enabled():
            return

        if not self._validate_context(context):
            return

        try:
            # Get per-TF parameters
            self.lookback = self.get_threshold('lookback', self.default_lookback, context.timeframe)
            self.min_cycle = self.get_threshold('min_cycle', self.default_min_cycle, context.timeframe)
            self.max_cycle = self.get_threshold('max_cycle', self.default_max_cycle, context.timeframe)
            self.min_cycles_for_forecast = self.get_threshold('min_cycles_for_forecast', self.default_min_cycles_for_forecast, context.timeframe)
            self.forecast_length = self.get_threshold('forecast_length', self.default_forecast_length, context.timeframe)

            df = context.df

            if len(df) < 100:
                context.add_result('cyclical', {
                    'status': 'insufficient_data',
                    'dominant_cycle': None
                })
                return

            lookback = min(self.lookback, len(df))
            prices = df['close'].tail(lookback).values

            # Use FFT if enabled, otherwise fallback to autocorrelation
            if self.use_fft:
                result = self._analyze_with_fft(prices)
            else:
                # Detect dominant cycle using autocorrelation
                dominant_cycle = self._detect_dominant_cycle(prices)

                # Determine current phase
                cycle_phase = self._determine_cycle_phase(prices, dominant_cycle)

                # Estimate next reversal
                next_reversal = self._estimate_next_reversal(dominant_cycle, cycle_phase)

                result = {
                    'status': 'ok',
                    'dominant_cycle': dominant_cycle,
                    'cycle_phase': cycle_phase,
                    'next_reversal_in': next_reversal,
                    'confidence': 0.5 if dominant_cycle else 0.2,
                    'method': 'autocorrelation'
                }

            context.add_result('cyclical', result)

            logger.info(
                f"CyclicalAnalyzer ({result.get('method', 'unknown')}): "
                f"{len(result.get('cycles', []))} cycles detected for {context.symbol}"
            )

        except Exception as e:
            logger.error(f"Error in CyclicalAnalyzer: {e}", exc_info=True)
            context.add_result('cyclical', {
                'status': 'error',
                'dominant_cycle': None,
                'error': str(e)
            })
    
    def _detect_dominant_cycle(self, prices: np.ndarray) -> Optional[int]:
        """Detect dominant cycle using autocorrelation."""
        try:
            # Simple autocorrelation
            normalized = (prices - np.mean(prices)) / np.std(prices)
            
            autocorr = np.correlate(normalized, normalized, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find peaks in autocorrelation
            peaks = []
            for i in range(self.min_cycle, min(self.max_cycle, len(autocorr) - 1)):
                if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
                    peaks.append((i, autocorr[i]))
            
            if peaks:
                # Return period with highest correlation
                dominant = max(peaks, key=lambda x: x[1])
                return dominant[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Cycle detection failed: {e}")
            return None
    
    def _determine_cycle_phase(self, prices: np.ndarray, cycle: Optional[int]) -> str:
        """
        REFACTORED: Now uses CyclePhase Enum for type safety.

        Determine current phase of cycle.

        Returns:
            String describing cycle phase (using CyclePhase.value for backward compatibility)
        """
        if not cycle or len(prices) < cycle:
            return CyclePhase.UNKNOWN.value

        recent_prices = prices[-cycle:]
        current = prices[-1]

        max_price = np.max(recent_prices)
        min_price = np.min(recent_prices)

        # Determine phase based on position and recent movement - Using CyclePhase Enum
        if current >= max_price * 0.95:
            phase = CyclePhase.TOP
        elif current <= min_price * 1.05:
            phase = CyclePhase.BOTTOM
        elif current > prices[-2]:
            phase = CyclePhase.RISING
        else:
            phase = CyclePhase.FALLING

        return phase.value  # Return .value for backward compatibility
    
    def _estimate_next_reversal(self, cycle: Optional[int], phase: str) -> Optional[int]:
        """
        Estimate periods until next reversal.

        Args:
            cycle: Dominant cycle period
            phase: Current cycle phase (string value from CyclePhase enum)
        """
        if not cycle:
            return None

        # Simple estimate: half cycle from top/bottom - Using CyclePhase enum values
        if phase in [CyclePhase.TOP.value, CyclePhase.BOTTOM.value]:
            return cycle // 2
        elif phase in [CyclePhase.RISING.value, CyclePhase.FALLING.value]:
            return cycle // 4

        return None
    
    def _analyze_with_fft(self, prices: np.ndarray) -> Dict[str, Any]:
        """
        Analyze cycles using FFT (Fast Fourier Transform).

        This is the scientific approach that was in the old system.
        Detects cyclical patterns through frequency analysis.

        Args:
            prices: Price array

        Returns:
            Analysis result with cycles and forecast
        """
        try:
            # Step 1: Detrend the data (remove linear trend)
            x = np.arange(len(prices))
            trend_coeffs = np.polyfit(x, prices, 1)
            trend = np.polyval(trend_coeffs, x)
            detrended = prices - trend

            # Step 2: Apply FFT
            close_fft = fft.rfft(detrended)
            fft_freqs = fft.rfftfreq(len(detrended))

            # Step 3: Find significant frequencies
            close_fft_mag = np.abs(close_fft)
            threshold = np.mean(close_fft_mag) + np.std(close_fft_mag)
            significant_freq_indices = np.where(close_fft_mag > threshold)[0]

            # Step 4: Filter reasonable cycles (2 to lookback/2 periods)
            filtered_indices = [
                i for i in significant_freq_indices
                if fft_freqs[i] > 0 and 2 <= 1 / fft_freqs[i] <= len(prices) / 2
            ]

            # Step 5: Extract cycle information
            cycles = []
            for idx in filtered_indices:
                if fft_freqs[idx] > 0:
                    period = int(1 / fft_freqs[idx])
                    amplitude = close_fft_mag[idx] / len(detrended)
                    phase = np.angle(close_fft[idx])

                    # Calculate cycle power (amplitude as % of mean price)
                    cycle_power = amplitude / np.mean(prices) * 100

                    cycles.append({
                        'period': period,
                        'amplitude': float(amplitude),
                        'amplitude_percent': float(cycle_power),
                        'phase': float(phase),
                        'frequency': float(fft_freqs[idx])
                    })

            # Step 6: Sort by amplitude and take top cycles
            cycles = sorted(cycles, key=lambda x: x['amplitude'], reverse=True)
            top_cycles = cycles[:min(5, len(cycles))]

            result = {
                'status': 'ok',
                'method': 'fft',
                'cycles': top_cycles,
                'total_cycles_detected': len(cycles),
                'dominant_cycle': top_cycles[0]['period'] if top_cycles else None,
                'detrend_coeffs': [float(c) for c in trend_coeffs]
            }

            # Step 7: Generate forecast if enough cycles detected
            if len(top_cycles) >= self.min_cycles_for_forecast:
                forecast_data = self._generate_fft_forecast(
                    prices, top_cycles, trend, trend_coeffs[0]
                )
                result.update(forecast_data)

            return result

        except Exception as e:
            logger.error(f"FFT analysis failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'method': 'fft',
                'error': str(e),
                'cycles': []
            }

    def _generate_fft_forecast(
        self,
        prices: np.ndarray,
        cycles: List[Dict],
        trend: np.ndarray,
        trend_slope: float
    ) -> Dict[str, Any]:
        """
        Generate price forecast using detected cycles.

        Combines trend continuation with cyclical components.

        Args:
            prices: Historical prices
            cycles: Detected cycles from FFT
            trend: Trend line
            trend_slope: Slope of trend

        Returns:
            Forecast data including direction and strength
        """
        try:
            forecast = np.zeros(self.forecast_length)
            last_trend = trend[-1]

            # Generate forecast by combining trend + cycles
            for i in range(self.forecast_length):
                # Base forecast from trend
                point_forecast = last_trend + trend_slope * (i + 1)

                # Add cyclical components
                for cycle in cycles:
                    period = cycle['period']
                    amplitude = cycle['amplitude']
                    phase = cycle['phase']

                    # Time point in the future
                    t = len(prices) + i

                    # Cyclical component: amplitude * cos(2π * t / period + phase)
                    cycle_component = amplitude * np.cos(2 * np.pi * t / period + phase)
                    point_forecast += cycle_component

                forecast[i] = point_forecast

            # Analyze forecast
            current_price = prices[-1]
            forecast_end = forecast[-1]

            forecast_direction = 'bullish' if forecast_end > current_price else 'bearish'
            forecast_strength = abs(forecast_end - current_price) / current_price

            # Calculate signal scores
            prediction_clarity = min(1.0, forecast_strength * 5)
            cycles_strength = min(1.0, sum(c['amplitude_percent'] for c in cycles) / 10)

            score = 2.5 * prediction_clarity * cycles_strength

            return {
                'forecast': {
                    'values': [float(f) for f in forecast],
                    'direction': forecast_direction,
                    'strength': float(forecast_strength),
                    'end_value': float(forecast_end),
                    'change_percent': float((forecast_end - current_price) / current_price * 100)
                },
                'signal': {
                    'type': f'cycle_{forecast_direction}_forecast',
                    'direction': forecast_direction,
                    'score': float(score),
                    'prediction_clarity': float(prediction_clarity),
                    'cycles_strength': float(cycles_strength)
                },
                'confidence': float(prediction_clarity * cycles_strength)
            }

        except Exception as e:
            logger.error(f"Forecast generation failed: {e}", exc_info=True)
            return {
                'forecast': None,
                'signal': None,
                'confidence': 0.0
            }

    def _validate_context(self, context: AnalysisContext) -> bool:
        return 'close' in context.df.columns
