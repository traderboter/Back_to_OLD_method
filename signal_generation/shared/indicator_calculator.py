"""
نسخه جدید IndicatorCalculator که از IndicatorOrchestrator استفاده می‌کند.

این فایل به عنوان یک wrapper برای IndicatorOrchestrator عمل می‌کند
تا سازگاری با کد موجود را حفظ کند.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

from signal_generation.analyzers.indicators.indicator_orchestrator import IndicatorOrchestrator

# Import all indicator classes
from signal_generation.analyzers.indicators import (
    EMAIndicator,
    SMAIndicator,
    RSIIndicator,
    MACDIndicator,
    ATRIndicator,
    BollingerBandsIndicator,
    StochasticIndicator,
    OBVIndicator,
)

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """
    Centralized calculator for all technical indicators using IndicatorOrchestrator.

    This is a wrapper around IndicatorOrchestrator that maintains
    compatibility with the existing codebase.

    Calculates indicators in categories:
    1. Moving Averages (EMA, SMA)
    2. Momentum Indicators (RSI, MACD, Stochastic)
    3. Volatility Indicators (ATR, Bollinger Bands)
    4. Volume Indicators (OBV)

    Usage:
        calculator = IndicatorCalculator(config)
        calculator.calculate_all(context)
        # Now context.df has all indicator columns
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the IndicatorCalculator.

        Args:
            config: Configuration dictionary with indicator parameters
        """
        self.config = config

        # Initialize IndicatorOrchestrator
        self.orchestrator = IndicatorOrchestrator(config)

        # Register all indicators
        self._register_indicators()

        logger.info(
            f"IndicatorCalculator initialized with {len(self.orchestrator.all_indicators)} indicators"
        )

    def _register_indicators(self):
        """Register all indicator calculators."""
        # Trend indicators
        self.orchestrator.register_indicator(EMAIndicator)
        self.orchestrator.register_indicator(SMAIndicator)

        # Momentum indicators
        self.orchestrator.register_indicator(RSIIndicator)
        self.orchestrator.register_indicator(MACDIndicator)
        self.orchestrator.register_indicator(StochasticIndicator)

        # Volatility indicators
        self.orchestrator.register_indicator(ATRIndicator)
        self.orchestrator.register_indicator(BollingerBandsIndicator)

        # Volume indicators
        self.orchestrator.register_indicator(OBVIndicator)

        logger.debug(f"Registered {len(self.orchestrator.all_indicators)} indicators")

    def calculate_all(self, context) -> None:
        """
        Calculate all indicators and add them to context.df

        This is the main entry point. It uses IndicatorOrchestrator to
        calculate all indicators efficiently.

        Args:
            context: AnalysisContext object containing the dataframe

        Side Effects:
            - Adds new columns to context.df with all indicators
        """
        try:
            df = context.df
            timeframe = context.timeframe  # Get timeframe for per-TF parameters

            # Validate dataframe
            if not self._validate_dataframe(df):
                logger.warning(f"Invalid dataframe for {context.symbol}")
                return

            # Set timeframe for all indicators (for per-TF parameter support)
            self.orchestrator.set_timeframe(timeframe)

            # Calculate all indicators using orchestrator
            enriched_df = self.orchestrator.calculate_all(df)

            # Add backward compatibility aliases for column names
            # Old code expects 'slowk' and 'slowd' but new code uses 'stoch_k' and 'stoch_d'
            if 'stoch_k' in enriched_df.columns:
                enriched_df['slowk'] = enriched_df['stoch_k']
            if 'stoch_d' in enriched_df.columns:
                enriched_df['slowd'] = enriched_df['stoch_d']

            # Add volume_sma for backward compatibility (volume analyzer expects it)
            if 'volume' in enriched_df.columns:
                volume_sma_period = self.config.get('volume_sma_period', 20)
                enriched_df['volume_sma'] = enriched_df['volume'].rolling(window=volume_sma_period).mean()

            # Update context with enriched dataframe
            context.df = enriched_df

            # Get stats
            stats = self.orchestrator.get_stats()

            logger.info(
                f"IndicatorCalculator completed for {context.symbol}: "
                f"{stats['total_calculations']} calculations, "
                f"{stats['errors']} errors"
            )

        except Exception as e:
            logger.error(f"Error in IndicatorCalculator for {context.symbol}: {e}", exc_info=True)

    def _validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate that dataframe has required columns.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        if df is None or len(df) == 0:
            logger.warning("DataFrame is empty")
            return False

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"Missing required column: {col}")
                return False

        return True

    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate moving averages (for backward compatibility).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with MA columns added
        """
        return self.orchestrator.calculate_by_type(df, 'trend')

    def calculate_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum indicators (for backward compatibility).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with momentum columns added
        """
        return self.orchestrator.calculate_by_type(df, 'momentum')

    def calculate_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volatility indicators (for backward compatibility).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with volatility columns added
        """
        return self.orchestrator.calculate_by_type(df, 'volatility')

    def calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume indicators (for backward compatibility).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with volume columns added
        """
        return self.orchestrator.calculate_by_type(df, 'volume')

    def get_indicator_value(self, indicator_name: str, df: pd.DataFrame, column: Optional[str] = None):
        """
        Get value of a specific indicator (for backward compatibility).

        Args:
            indicator_name: Name of indicator (e.g., 'EMA', 'RSI')
            df: DataFrame with calculated indicators
            column: Specific column to get

        Returns:
            Indicator value(s)
        """
        return self.orchestrator.get_indicator_value(df, indicator_name, column)

    def clear_cache(self):
        """Clear caches for all indicators."""
        self.orchestrator.clear_all_caches()
        logger.debug("All indicator caches cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get calculator statistics.

        Returns:
            Dictionary with statistics
        """
        return self.orchestrator.get_stats()

    def get_available_indicators(self) -> Dict[str, List[str]]:
        """
        Get list of available indicators.

        Returns:
            Dictionary grouped by type
        """
        return self.orchestrator.get_available_indicators()
