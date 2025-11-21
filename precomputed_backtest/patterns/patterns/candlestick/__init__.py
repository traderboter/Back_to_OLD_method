"""
Candlestick Patterns Module

Individual candlestick pattern detectors.
Each pattern has its own file for better maintainability.
"""

from signal_generation.analyzers.patterns.candlestick.hammer import HammerPattern
from signal_generation.analyzers.patterns.candlestick.inverted_hammer import InvertedHammerPattern
from signal_generation.analyzers.patterns.candlestick.engulfing import EngulfingPattern
from signal_generation.analyzers.patterns.candlestick.morning_star import MorningStarPattern
from signal_generation.analyzers.patterns.candlestick.piercing_line import PiercingLinePattern
from signal_generation.analyzers.patterns.candlestick.three_white_soldiers import ThreeWhiteSoldiersPattern
from signal_generation.analyzers.patterns.candlestick.morning_doji_star import MorningDojiStarPattern
from signal_generation.analyzers.patterns.candlestick.shooting_star import ShootingStarPattern
from signal_generation.analyzers.patterns.candlestick.hanging_man import HangingManPattern
from signal_generation.analyzers.patterns.candlestick.evening_star import EveningStarPattern
from signal_generation.analyzers.patterns.candlestick.dark_cloud_cover import DarkCloudCoverPattern
from signal_generation.analyzers.patterns.candlestick.three_black_crows import ThreeBlackCrowsPattern
from signal_generation.analyzers.patterns.candlestick.evening_doji_star import EveningDojiStarPattern
from signal_generation.analyzers.patterns.candlestick.doji import DojiPattern
from signal_generation.analyzers.patterns.candlestick.harami import HaramiPattern
from signal_generation.analyzers.patterns.candlestick.harami_cross import HaramiCrossPattern

# Phase 1 - New powerful patterns
from signal_generation.analyzers.patterns.candlestick.marubozu import MarubozuPattern
from signal_generation.analyzers.patterns.candlestick.dragonfly_doji import DragonflyDojiPattern
from signal_generation.analyzers.patterns.candlestick.gravestone_doji import GravestoneDojiPattern
from signal_generation.analyzers.patterns.candlestick.spinning_top import SpinningTopPattern
from signal_generation.analyzers.patterns.candlestick.long_legged_doji import LongLeggedDojiPattern

# Phase 2 - Continuation and confirmation patterns
from signal_generation.analyzers.patterns.candlestick.three_inside import ThreeInsidePattern
from signal_generation.analyzers.patterns.candlestick.three_outside import ThreeOutsidePattern
from signal_generation.analyzers.patterns.candlestick.belt_hold import BeltHoldPattern
from signal_generation.analyzers.patterns.candlestick.three_methods import ThreeMethodsPattern
from signal_generation.analyzers.patterns.candlestick.mat_hold import MatHoldPattern

# Phase 3 - High priority missing patterns (2025-11-18)
from signal_generation.analyzers.patterns.candlestick.tweezer import TweezerPattern
from signal_generation.analyzers.patterns.candlestick.abandoned_baby import AbandonedBabyPattern
from signal_generation.analyzers.patterns.candlestick.kicking import KickingPattern

__all__ = [
    # Bullish patterns
    'HammerPattern',
    'InvertedHammerPattern',
    'MorningStarPattern',
    'PiercingLinePattern',
    'ThreeWhiteSoldiersPattern',
    'MorningDojiStarPattern',

    # Bearish patterns
    'ShootingStarPattern',
    'HangingManPattern',
    'EveningStarPattern',
    'DarkCloudCoverPattern',
    'ThreeBlackCrowsPattern',
    'EveningDojiStarPattern',

    # Reversal/Both
    'EngulfingPattern',
    'DojiPattern',
    'HaramiPattern',
    'HaramiCrossPattern',

    # Phase 1 - New powerful patterns
    'MarubozuPattern',
    'DragonflyDojiPattern',
    'GravestoneDojiPattern',
    'SpinningTopPattern',
    'LongLeggedDojiPattern',

    # Phase 2 - Continuation and confirmation patterns
    'ThreeInsidePattern',
    'ThreeOutsidePattern',
    'BeltHoldPattern',
    'ThreeMethodsPattern',
    'MatHoldPattern',

    # Phase 3 - High priority missing patterns (2025-11-18)
    'TweezerPattern',
    'AbandonedBabyPattern',
    'KickingPattern',
]
