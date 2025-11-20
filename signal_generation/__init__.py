"""
Signal Generation Package - Refactored Architecture

Main Components:
- SignalOrchestrator: Main signal generation pipeline
- AnalysisContext: Shared context for analyzers
- IndicatorCalculator: Technical indicator calculation
- SignalScorer: Signal scoring system
- SignalValidator: Signal validation system
- SignalInfo: Signal data model
- TimeframeScoreCache: Intelligent caching system for timeframe scores

Advanced Systems:
- MarketRegimeDetector: Market condition detection
- AdaptiveLearningSystem: Learning from past trades
- CorrelationManager: Symbol correlation management
- EmergencyCircuitBreaker: Risk protection

Analyzers:
- TrendAnalyzer, MomentumAnalyzer, VolumeAnalyzer
- PatternAnalyzer, SRAnalyzer, VolatilityAnalyzer
- HarmonicAnalyzer, ChannelAnalyzer, CyclicalAnalyzer
- HTFAnalyzer
"""

# Core Components
from signal_generation.context import AnalysisContext
from signal_generation.orchestrator import SignalOrchestrator
from signal_generation.signal_info import SignalInfo
from signal_generation.signal_score import SignalScore
from signal_generation.signal_scorer import SignalScorer
from signal_generation.signal_validator import SignalValidator
from signal_generation.timeframe_score_cache import TimeframeScoreCache

# Shared Components
from signal_generation.shared.indicator_calculator import IndicatorCalculator
# Uncomment when data models are added:
# from signal_generation.shared.data_models import (
#     SomeDataModel,
#     AnotherDataModel
# )

# Advanced Systems
from signal_generation.systems import (
    MarketRegimeDetector,
    AdaptiveLearningSystem,
    CorrelationManager,
    EmergencyCircuitBreaker,
    TradeResult
)

# Analyzers
from signal_generation.analyzers import (
    BaseAnalyzer,
    TrendAnalyzer,
    MomentumAnalyzer,
    VolumeAnalyzer,
    PatternAnalyzer,
    SRAnalyzer,
    VolatilityAnalyzer,
    HarmonicAnalyzer,
    ChannelAnalyzer,
    CyclicalAnalyzer,
    HTFAnalyzer
)

__all__ = [
    # Core Components
    'AnalysisContext',
    'SignalOrchestrator',
    'SignalInfo',
    'SignalScore',
    'SignalScorer',
    'SignalValidator',
    'TimeframeScoreCache',

    # Shared Components
    'IndicatorCalculator',

    # Advanced Systems
    'MarketRegimeDetector',
    'AdaptiveLearningSystem',
    'CorrelationManager',
    'EmergencyCircuitBreaker',
    'TradeResult',

    # Analyzers
    'BaseAnalyzer',
    'TrendAnalyzer',
    'MomentumAnalyzer',
    'VolumeAnalyzer',
    'PatternAnalyzer',
    'SRAnalyzer',
    'VolatilityAnalyzer',
    'HarmonicAnalyzer',
    'ChannelAnalyzer',
    'CyclicalAnalyzer',
    'HTFAnalyzer',
]

# Version
__version__ = '2.0.0'
