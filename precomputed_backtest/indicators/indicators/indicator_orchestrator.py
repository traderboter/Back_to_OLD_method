"""
Indicator Orchestrator - Coordinates all indicator calculations

This orchestrator manages the calculation of all technical indicators.
It loads indicator calculators dynamically and coordinates their execution.
"""

from typing import Dict, Any, List, Optional, Type
import pandas as pd
import logging

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator

logger = logging.getLogger(__name__)


class IndicatorOrchestrator:
    """
    Orchestrator for indicator calculation.

    Responsibilities:
    1. Load all available indicator calculators
    2. Execute indicator calculations in proper order
    3. Manage dependencies between indicators
    4. Provide unified interface for indicator calculation

    Key features:
    - Dynamic indicator loading
    - Dependency management
    - Caching support
    - Batch calculation
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize IndicatorOrchestrator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Indicator calculators
        self.trend_indicators: Dict[str, BaseIndicator] = {}
        self.momentum_indicators: Dict[str, BaseIndicator] = {}
        self.volatility_indicators: Dict[str, BaseIndicator] = {}
        self.volume_indicators: Dict[str, BaseIndicator] = {}
        self.other_indicators: Dict[str, BaseIndicator] = {}

        # All indicators (for easy access)
        self.all_indicators: Dict[str, BaseIndicator] = {}

        # Settings
        self.cache_enabled = self.config.get('indicators', {}).get('cache_enabled', True)

        # Statistics
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'errors': 0
        }

        # Load indicators
        self._load_indicators()

        logger.info(
            f"IndicatorOrchestrator initialized: "
            f"{len(self.all_indicators)} indicators loaded"
        )

    def _load_indicators(self):
        """Load all available indicator calculators automatically."""
        try:
            # Import all indicator classes
            from signal_generation.analyzers.indicators.ema import EMAIndicator
            from signal_generation.analyzers.indicators.sma import SMAIndicator
            from signal_generation.analyzers.indicators.rsi import RSIIndicator
            from signal_generation.analyzers.indicators.macd import MACDIndicator
            from signal_generation.analyzers.indicators.stochastic import StochasticIndicator
            from signal_generation.analyzers.indicators.atr import ATRIndicator
            from signal_generation.analyzers.indicators.bollinger_bands import BollingerBandsIndicator
            from signal_generation.analyzers.indicators.obv import OBVIndicator
            from signal_generation.analyzers.indicators.adx import ADXIndicator

            # Register all indicators
            indicators = [
                # Trend indicators
                EMAIndicator,
                SMAIndicator,
                ADXIndicator,
                # Momentum indicators
                RSIIndicator,
                MACDIndicator,
                StochasticIndicator,
                # Volatility indicators
                ATRIndicator,
                BollingerBandsIndicator,
                # Volume indicators
                OBVIndicator
            ]

            for indicator_class in indicators:
                self.register_indicator(indicator_class)

            logger.info(f"Loaded {len(self.all_indicators)} indicators successfully")

        except Exception as e:
            logger.error(f"Error loading indicators: {e}", exc_info=True)

    def register_indicator(self, indicator_class: Type[BaseIndicator]):
        """
        Register an indicator calculator.

        Args:
            indicator_class: Indicator class to register
        """
        try:
            # Instantiate indicator
            indicator = indicator_class(self.config)

            # Add to appropriate registry
            indicator_type = indicator.indicator_type

            if indicator_type == 'trend':
                self.trend_indicators[indicator.name] = indicator
            elif indicator_type == 'momentum':
                self.momentum_indicators[indicator.name] = indicator
            elif indicator_type == 'volatility':
                self.volatility_indicators[indicator.name] = indicator
            elif indicator_type == 'volume':
                self.volume_indicators[indicator.name] = indicator
            else:
                self.other_indicators[indicator.name] = indicator

            # Add to all_indicators
            self.all_indicators[indicator.name] = indicator

            logger.debug(f"Registered {indicator_type} indicator: {indicator.name}")

        except Exception as e:
            logger.error(f"Error registering indicator {indicator_class}: {e}")

    def calculate_all(
        self,
        df: pd.DataFrame,
        indicator_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Calculate all (or specified) indicators.

        Args:
            df: DataFrame with OHLCV data
            indicator_names: Optional list of specific indicators to calculate
                           (if None, calculates all)

        Returns:
            DataFrame with all indicator columns added
        """
        result_df = df.copy()

        # Determine which indicators to calculate
        if indicator_names:
            indicators_to_calc = [
                self.all_indicators[name]
                for name in indicator_names
                if name in self.all_indicators
            ]
        else:
            indicators_to_calc = list(self.all_indicators.values())

        # Calculate in order: trend -> momentum -> volatility -> volume -> other
        # This ensures any dependencies are satisfied
        calculation_order = [
            ('trend', self.trend_indicators),
            ('momentum', self.momentum_indicators),
            ('volatility', self.volatility_indicators),
            ('volume', self.volume_indicators),
            ('other', self.other_indicators)
        ]

        for indicator_type, indicator_dict in calculation_order:
            for indicator_name, indicator in indicator_dict.items():
                # Skip if not in requested list
                if indicator_names and indicator_name not in indicator_names:
                    continue

                try:
                    # Calculate indicator
                    result_df = indicator.calculate_safe(result_df)
                    self.stats['total_calculations'] += 1

                    logger.debug(f"Calculated {indicator_type} indicator: {indicator_name}")

                except Exception as e:
                    logger.error(
                        f"Error calculating indicator {indicator_name}: {e}",
                        exc_info=True
                    )
                    self.stats['errors'] += 1

        return result_df

    def calculate_by_type(
        self,
        df: pd.DataFrame,
        indicator_type: str
    ) -> pd.DataFrame:
        """
        Calculate all indicators of a specific type.

        Args:
            df: DataFrame with OHLCV data
            indicator_type: Type of indicators ('trend', 'momentum', 'volatility', 'volume', 'other')

        Returns:
            DataFrame with indicator columns added
        """
        result_df = df.copy()

        # Get indicators of specified type
        if indicator_type == 'trend':
            indicators = self.trend_indicators
        elif indicator_type == 'momentum':
            indicators = self.momentum_indicators
        elif indicator_type == 'volatility':
            indicators = self.volatility_indicators
        elif indicator_type == 'volume':
            indicators = self.volume_indicators
        elif indicator_type == 'other':
            indicators = self.other_indicators
        else:
            logger.warning(f"Unknown indicator type: {indicator_type}")
            return result_df

        # Calculate each indicator
        for indicator_name, indicator in indicators.items():
            try:
                result_df = indicator.calculate_safe(result_df)
                self.stats['total_calculations'] += 1

            except Exception as e:
                logger.error(
                    f"Error calculating {indicator_type} indicator {indicator_name}: {e}",
                    exc_info=True
                )
                self.stats['errors'] += 1

        return result_df

    def get_indicator(self, name: str) -> Optional[BaseIndicator]:
        """
        Get a specific indicator by name.

        Args:
            name: Indicator name

        Returns:
            Indicator calculator if found, None otherwise
        """
        return self.all_indicators.get(name)

    def get_indicator_value(
        self,
        df: pd.DataFrame,
        indicator_name: str,
        column: Optional[str] = None
    ) -> Any:
        """
        Get calculated indicator value(s).

        Args:
            df: DataFrame with calculated indicators
            indicator_name: Name of indicator
            column: Optional specific column

        Returns:
            Indicator value(s)
        """
        indicator = self.get_indicator(indicator_name)
        if indicator:
            return indicator.get_values(df, column)
        else:
            logger.warning(f"Indicator not found: {indicator_name}")
            return None

    def get_available_indicators(self) -> Dict[str, List[str]]:
        """
        Get list of all available indicators grouped by type.

        Returns:
            Dictionary with indicator types as keys
        """
        return {
            'trend': list(self.trend_indicators.keys()),
            'momentum': list(self.momentum_indicators.keys()),
            'volatility': list(self.volatility_indicators.keys()),
            'volume': list(self.volume_indicators.keys()),
            'other': list(self.other_indicators.keys())
        }

    def clear_all_caches(self):
        """Clear caches for all indicators."""
        for indicator in self.all_indicators.values():
            indicator.clear_cache()
        logger.debug("All indicator caches cleared")

    def set_timeframe(self, timeframe: str) -> None:
        """
        Set timeframe for all registered indicators.

        This allows indicators to use per-timeframe parameters.

        Args:
            timeframe: Current timeframe (e.g., '5m', '15m', '1h', '4h')
        """
        for indicator in self.all_indicators.values():
            indicator.timeframe = timeframe
        logger.debug(f"Set timeframe={timeframe} for {len(self.all_indicators)} indicators")

    def get_stats(self) -> Dict[str, int]:
        """
        Get calculation statistics.

        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset calculation statistics."""
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'errors': 0
        }
        logger.debug("Indicator calculation stats reset")

    def __str__(self) -> str:
        """String representation."""
        return (
            f"IndicatorOrchestrator("
            f"total={len(self.all_indicators)}, "
            f"trend={len(self.trend_indicators)}, "
            f"momentum={len(self.momentum_indicators)}, "
            f"volatility={len(self.volatility_indicators)}, "
            f"volume={len(self.volume_indicators)})"
        )
