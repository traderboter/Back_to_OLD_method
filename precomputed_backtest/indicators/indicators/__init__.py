"""
Indicators Module - Technical Indicator Calculation System

This module provides technical indicator calculation functionality.

Components:
- BaseIndicator: Abstract base class for all indicators
- IndicatorOrchestrator: Main coordinator for indicator calculation
- Individual indicators: EMA, SMA, RSI, MACD, ATR, Bollinger, Stochastic, OBV
"""

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator
from signal_generation.analyzers.indicators.indicator_orchestrator import IndicatorOrchestrator

# Trend Indicators
from signal_generation.analyzers.indicators.ema import EMAIndicator
from signal_generation.analyzers.indicators.sma import SMAIndicator

# Momentum Indicators
from signal_generation.analyzers.indicators.rsi import RSIIndicator
from signal_generation.analyzers.indicators.macd import MACDIndicator
from signal_generation.analyzers.indicators.stochastic import StochasticIndicator

# Volatility Indicators
from signal_generation.analyzers.indicators.atr import ATRIndicator
from signal_generation.analyzers.indicators.bollinger_bands import BollingerBandsIndicator

# Volume Indicators
from signal_generation.analyzers.indicators.obv import OBVIndicator

__all__ = [
    'BaseIndicator',
    'IndicatorOrchestrator',

    # Trend
    'EMAIndicator',
    'SMAIndicator',

    # Momentum
    'RSIIndicator',
    'MACDIndicator',
    'StochasticIndicator',

    # Volatility
    'ATRIndicator',
    'BollingerBandsIndicator',

    # Volume
    'OBVIndicator',
]
