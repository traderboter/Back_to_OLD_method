"""
Advanced Systems for Signal Generation

Supporting systems:
- MarketRegimeDetector: Market condition detection
- AdaptiveLearningSystem: Learning from past trades
- CorrelationManager: Symbol correlation management
- EmergencyCircuitBreaker: Risk protection
"""

from signal_generation.systems.market_regime_detector import MarketRegimeDetector
from signal_generation.systems.adaptive_learning_system import (
    AdaptiveLearningSystem,
    TradeResult
)
from signal_generation.systems.correlation_manager import CorrelationManager
from signal_generation.systems.emergency_circuit_breaker import EmergencyCircuitBreaker

__all__ = [
    'MarketRegimeDetector',
    'AdaptiveLearningSystem',
    'TradeResult',
    'CorrelationManager',
    'EmergencyCircuitBreaker',
]
