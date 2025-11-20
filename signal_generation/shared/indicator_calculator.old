"""
IndicatorCalculator - Centralized Technical Indicator Calculation System
=========================================================================

This module provides a unified system for calculating all technical indicators
needed by the signal generation analyzers. It calculates each indicator ONCE
and stores results in the AnalysisContext for efficient access.

Performance Benefits:
- Eliminates redundant calculations across analyzers
- Calculates indicators in optimal order (dependencies first)
- Uses vectorized operations for speed
- Caches results in context for instant access

Author: Refactored from signal_generator.py
Date: 2025-10-15
Phase: 2 - Core Infrastructure
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """
    Centralized calculator for all technical indicators.
    
    This class calculates indicators in categories:
    1. Moving Averages (EMA, SMA)
    2. Momentum Indicators (RSI, Stochastic, MFI)
    3. Trend Indicators (MACD, ADX)
    4. Volatility Indicators (ATR, Bollinger Bands)
    5. Volume Indicators (OBV, Volume SMA)
    
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
                   Default parameters will be used if not specified
        """
        self.config = config
        
        # Extract indicator configs with defaults
        self.ma_config = config.get('moving_averages', {
            'ema_periods': [20, 50, 200],
            'sma_periods': [20, 50, 200]
        })
        
        self.momentum_config = config.get('momentum', {
            'rsi_period': 14,
            'stoch_fastk_period': 14,
            'stoch_slowk_period': 3,
            'stoch_slowd_period': 3,
            'mfi_period': 14
        })
        
        self.trend_config = config.get('trend', {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'adx_period': 14
        })
        
        self.volatility_config = config.get('volatility', {
            'atr_period': 14,
            'bb_period': 20,
            'bb_std': 2
        })
        
        self.volume_config = config.get('volume', {
            'volume_sma_period': 20
        })
        
        logger.info("IndicatorCalculator initialized with config")
    
    def calculate_all(self, context) -> None:
        """
        Calculate all indicators and add them to context.df
        
        This is the main entry point. It calls all category-specific
        calculation methods in the correct order.
        
        Args:
            context: AnalysisContext object containing the dataframe
            
        Side Effects:
            - Adds new columns to context.df
            - Updates context.metadata['indicators_calculated'] = True
            
        Raises:
            ValueError: If required OHLCV columns are missing
            Exception: If indicator calculation fails
        """
        try:
            df = context.df
            
            # Validate required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            logger.info(f"Starting indicator calculation for {context.symbol} {context.timeframe}")
            
            # Calculate in dependency order
            # 1. Moving Averages (no dependencies)
            self._calculate_moving_averages(df)
            
            # 2. Momentum Indicators (use close prices)
            self._calculate_momentum_indicators(df)
            
            # 3. Trend Indicators (use OHLC)
            self._calculate_trend_indicators(df)
            
            # 4. Volatility Indicators (use OHLC)
            self._calculate_volatility_indicators(df)
            
            # 5. Volume Indicators (use volume + close)
            self._calculate_volume_indicators(df)
            
            # Mark as calculated in context
            context.metadata['indicators_calculated'] = True
            context.metadata['indicator_count'] = self._count_new_columns(df, required_cols)
            
            logger.info(
                f"✅ Calculated {context.metadata['indicator_count']} indicators "
                f"for {context.symbol} {context.timeframe}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate indicators: {e}", exc_info=True)
            raise
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> None:
        """
        Calculate EMA and SMA indicators.
        
        Adds columns:
        - ema_20, ema_50, ema_200
        - sma_20, sma_50, sma_200
        
        Args:
            df: DataFrame with 'close' column
        """
        try:
            close = df['close'].values.astype(np.float64)
            
            # Calculate EMAs
            for period in self.ma_config['ema_periods']:
                col_name = f'ema_{period}'
                df[col_name] = talib.EMA(close, timeperiod=period)
                logger.debug(f"Calculated {col_name}")
            
            # Calculate SMAs
            for period in self.ma_config['sma_periods']:
                col_name = f'sma_{period}'
                df[col_name] = talib.SMA(close, timeperiod=period)
                logger.debug(f"Calculated {col_name}")
            
            logger.info("✓ Moving averages calculated")
            
        except Exception as e:
            logger.error(f"Failed to calculate moving averages: {e}")
            raise
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> None:
        """
        Calculate momentum oscillators: RSI, Stochastic, MFI
        
        Adds columns:
        - rsi: Relative Strength Index
        - slowk, slowd: Stochastic oscillator
        - mfi: Money Flow Index
        
        Args:
            df: DataFrame with OHLCV columns
        """
        try:
            close = df['close'].values.astype(np.float64)
            high = df['high'].values.astype(np.float64)
            low = df['low'].values.astype(np.float64)
            volume = df['volume'].values.astype(np.float64)
            
            # RSI
            rsi_period = self.momentum_config['rsi_period']
            df['rsi'] = talib.RSI(close, timeperiod=rsi_period)
            logger.debug(f"Calculated RSI({rsi_period})")
            
            # Stochastic
            fastk_period = self.momentum_config['stoch_fastk_period']
            slowk_period = self.momentum_config['stoch_slowk_period']
            slowd_period = self.momentum_config['stoch_slowd_period']
            
            slowk, slowd = talib.STOCH(
                high, low, close,
                fastk_period=fastk_period,
                slowk_period=slowk_period,
                slowk_matype=0,
                slowd_period=slowd_period,
                slowd_matype=0
            )
            df['slowk'] = slowk
            df['slowd'] = slowd
            logger.debug(f"Calculated Stochastic({fastk_period}, {slowk_period}, {slowd_period})")
            
            # MFI (Money Flow Index)
            mfi_period = self.momentum_config['mfi_period']
            df['mfi'] = talib.MFI(high, low, close, volume, timeperiod=mfi_period)
            logger.debug(f"Calculated MFI({mfi_period})")
            
            logger.info("✓ Momentum indicators calculated")
            
        except Exception as e:
            logger.error(f"Failed to calculate momentum indicators: {e}")
            raise
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> None:
        """
        Calculate trend indicators: MACD and ADX
        
        Adds columns:
        - macd, macd_signal, macd_hist: MACD components
        - adx, plus_di, minus_di: ADX and directional indicators
        
        Args:
            df: DataFrame with OHLC columns
        """
        try:
            close = df['close'].values.astype(np.float64)
            high = df['high'].values.astype(np.float64)
            low = df['low'].values.astype(np.float64)
            
            # MACD
            fast = self.trend_config['macd_fast']
            slow = self.trend_config['macd_slow']
            signal = self.trend_config['macd_signal']
            
            macd, macd_signal, macd_hist = talib.MACD(
                close,
                fastperiod=fast,
                slowperiod=slow,
                signalperiod=signal
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist
            logger.debug(f"Calculated MACD({fast}, {slow}, {signal})")
            
            # ADX and Directional Indicators
            adx_period = self.trend_config['adx_period']
            df['adx'] = talib.ADX(high, low, close, timeperiod=adx_period)
            df['plus_di'] = talib.PLUS_DI(high, low, close, timeperiod=adx_period)
            df['minus_di'] = talib.MINUS_DI(high, low, close, timeperiod=adx_period)
            logger.debug(f"Calculated ADX({adx_period}) with +DI and -DI")
            
            logger.info("✓ Trend indicators calculated")
            
        except Exception as e:
            logger.error(f"Failed to calculate trend indicators: {e}")
            raise
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> None:
        """
        Calculate volatility indicators: ATR and Bollinger Bands
        
        Adds columns:
        - atr: Average True Range
        - bb_upper, bb_middle, bb_lower: Bollinger Bands
        
        Args:
            df: DataFrame with OHLC columns
        """
        try:
            close = df['close'].values.astype(np.float64)
            high = df['high'].values.astype(np.float64)
            low = df['low'].values.astype(np.float64)
            
            # ATR
            atr_period = self.volatility_config['atr_period']
            df['atr'] = talib.ATR(high, low, close, timeperiod=atr_period)
            logger.debug(f"Calculated ATR({atr_period})")
            
            # Bollinger Bands
            bb_period = self.volatility_config['bb_period']
            bb_std = self.volatility_config['bb_std']
            
            upper, middle, lower = talib.BBANDS(
                close,
                timeperiod=bb_period,
                nbdevup=bb_std,
                nbdevdn=bb_std,
                matype=0
            )
            df['bb_upper'] = upper
            df['bb_middle'] = middle
            df['bb_lower'] = lower
            logger.debug(f"Calculated Bollinger Bands({bb_period}, {bb_std}σ)")
            
            logger.info("✓ Volatility indicators calculated")
            
        except Exception as e:
            logger.error(f"Failed to calculate volatility indicators: {e}")
            raise
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> None:
        """
        Calculate volume-based indicators: OBV and Volume SMA
        
        Adds columns:
        - obv: On-Balance Volume
        - volume_sma: Volume Simple Moving Average
        
        Args:
            df: DataFrame with 'close' and 'volume' columns
        """
        try:
            close = df['close'].values.astype(np.float64)
            volume = df['volume'].values.astype(np.float64)
            
            # OBV (On-Balance Volume)
            df['obv'] = talib.OBV(close, volume)
            logger.debug("Calculated OBV")
            
            # Volume SMA
            vol_sma_period = self.volume_config['volume_sma_period']
            df['volume_sma'] = talib.SMA(volume, timeperiod=vol_sma_period)
            logger.debug(f"Calculated Volume SMA({vol_sma_period})")
            
            logger.info("✓ Volume indicators calculated")
            
        except Exception as e:
            logger.error(f"Failed to calculate volume indicators: {e}")
            raise
    
    def _count_new_columns(self, df: pd.DataFrame, original_cols: List[str]) -> int:
        """
        Count how many new indicator columns were added.
        
        Args:
            df: DataFrame after indicator calculation
            original_cols: List of original column names
            
        Returns:
            Number of new columns added
        """
        current_cols = set(df.columns)
        original_set = set(original_cols)
        new_cols = current_cols - original_set
        return len(new_cols)
    
    def get_indicator_info(self) -> Dict[str, Any]:
        """
        Get information about configured indicators.
        
        Returns:
            Dictionary with indicator configuration details
        """
        return {
            'moving_averages': {
                'ema_periods': self.ma_config['ema_periods'],
                'sma_periods': self.ma_config['sma_periods'],
                'total': len(self.ma_config['ema_periods']) + len(self.ma_config['sma_periods'])
            },
            'momentum': {
                'indicators': ['RSI', 'Stochastic (K, D)', 'MFI'],
                'total': 4  # rsi, slowk, slowd, mfi
            },
            'trend': {
                'indicators': ['MACD (3 components)', 'ADX (with +DI, -DI)'],
                'total': 6  # macd, macd_signal, macd_hist, adx, plus_di, minus_di
            },
            'volatility': {
                'indicators': ['ATR', 'Bollinger Bands (3 components)'],
                'total': 4  # atr, bb_upper, bb_middle, bb_lower
            },
            'volume': {
                'indicators': ['OBV', 'Volume SMA'],
                'total': 2  # obv, volume_sma
            },
            'grand_total': 22
        }
    
    def validate_indicators(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate that all expected indicators were calculated.
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary mapping indicator names to presence (True/False)
        """
        expected_indicators = [
            # Moving Averages
            'ema_20', 'ema_50', 'ema_200',
            'sma_20', 'sma_50', 'sma_200',
            # Momentum
            'rsi', 'slowk', 'slowd', 'mfi',
            # Trend
            'macd', 'macd_signal', 'macd_hist',
            'adx', 'plus_di', 'minus_di',
            # Volatility
            'atr', 'bb_upper', 'bb_middle', 'bb_lower',
            # Volume
            'obv', 'volume_sma'
        ]
        
        validation = {}
        for indicator in expected_indicators:
            validation[indicator] = indicator in df.columns
        
        return validation


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def example_usage():
    """
    Example showing how to use IndicatorCalculator
    """
    # Assuming you have context from somewhere
    # context = AnalysisContext(symbol='BTCUSDT', timeframe='1h', df=your_dataframe)
    
    # Create calculator with config
    config = {
        'moving_averages': {
            'ema_periods': [20, 50, 200],
            'sma_periods': [20, 50, 200]
        },
        'momentum': {
            'rsi_period': 14,
            'stoch_fastk_period': 14,
            'stoch_slowk_period': 3,
            'stoch_slowd_period': 3,
            'mfi_period': 14
        },
        'trend': {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'adx_period': 14
        },
        'volatility': {
            'atr_period': 14,
            'bb_period': 20,
            'bb_std': 2
        },
        'volume': {
            'volume_sma_period': 20
        }
    }
    
    calculator = IndicatorCalculator(config)
    
    # Calculate all indicators
    # calculator.calculate_all(context)
    
    # Now context.df has all 22 indicator columns!
    # Analyzers can just read them:
    # ema_20 = context.df['ema_20'].iloc[-1]
    # rsi = context.df['rsi'].iloc[-1]
    
    # Get info about indicators
    info = calculator.get_indicator_info()
    print(f"Total indicators configured: {info['grand_total']}")


if __name__ == '__main__':
    example_usage()
