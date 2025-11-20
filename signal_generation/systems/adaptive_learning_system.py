"""
Adaptive Learning System
Learns from past trade results to improve signal parameters.
"""

import logging
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Trade result class for adaptive learning system."""

    signal_id: str
    symbol: str
    direction: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    exit_time: datetime
    exit_reason: str  # 'tp', 'sl', 'manual', 'trailing'
    profit_pct: float
    profit_r: float  # Profit/loss in R
    market_regime: Optional[str] = None
    pattern_names: List[str] = field(default_factory=list)
    timeframe: str = ""
    signal_score: float = 0.0
    trade_duration: Optional[timedelta] = None
    signal_type: str = ""

    def __post_init__(self):
        """Calculate trade duration after initialization."""
        if self.entry_time and self.exit_time and not self.trade_duration:
            self.trade_duration = self.exit_time - self.entry_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)

        # Convert datetime to ISO string
        if self.entry_time:
            result['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            result['exit_time'] = self.exit_time.isoformat()
        if self.trade_duration:
            result['trade_duration'] = str(self.trade_duration)

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeResult':
        """Create from dictionary."""
        data_copy = data.copy()

        # Convert ISO string to datetime
        if 'entry_time' in data_copy and isinstance(data_copy['entry_time'], str):
            data_copy['entry_time'] = datetime.fromisoformat(data_copy['entry_time'])
        if 'exit_time' in data_copy and isinstance(data_copy['exit_time'], str):
            data_copy['exit_time'] = datetime.fromisoformat(data_copy['exit_time'])

        # Remove trade_duration to recalculate in __post_init__
        if 'trade_duration' in data_copy and isinstance(data_copy['trade_duration'], str):
            del data_copy['trade_duration']

        return cls(**data_copy)


class AdaptiveLearningSystem:
    """Adaptive learning system to improve signal parameters based on past results."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config.get('adaptive_learning', {})
        self.enabled = self.config.get('enabled', True)
        self.data_file = self.config.get('data_file', 'data/adaptive_learning_data.json')
        self.max_history_per_symbol = self.config.get('max_history_per_symbol', 100)
        self.learning_rate = self.config.get('learning_rate', 0.1)
        self.symbol_performance_weight = self.config.get('symbol_performance_weight', 0.3)
        self.pattern_performance_weight = self.config.get('pattern_performance_weight', 0.3)
        self.regime_performance_weight = self.config.get('regime_performance_weight', 0.2)
        self.default_pattern_score = self.config.get('default_pattern_score', 1.0)

        # Learning data
        self.trade_history: List[TradeResult] = []
        self.symbol_performance: Dict[str, Dict[str, float]] = {}
        self.pattern_performance: Dict[str, Dict[str, float]] = {}
        self.regime_performance: Dict[str, Dict[str, float]] = {}
        self.timeframe_performance: Dict[str, Dict[str, float]] = {}

        # Calculation cache
        self._performance_cache: Dict[str, Any] = {}
        self._cache_ttl_seconds = 3600  # 1 hour

        # Load existing data
        self._load_data()

        logger.info(
            f"AdaptiveLearningSystem initialized. "
            f"Enabled: {self.enabled}, Data file: {self.data_file}"
        )

    def _load_data(self) -> None:
        """Load learning data from file."""
        try:
            if not os.path.exists(self.data_file):
                logger.info(
                    f"Adaptive learning data file not found: {self.data_file}, "
                    f"starting with empty data."
                )
                return

            with open(self.data_file, 'r') as f:
                data = json.load(f)

            # Restore trade history
            if 'trade_history' in data:
                self.trade_history = [
                    TradeResult.from_dict(trade)
                    for trade in data['trade_history']
                ]

            # Restore performance data
            self.symbol_performance = data.get('symbol_performance', {})
            self.pattern_performance = data.get('pattern_performance', {})
            self.regime_performance = data.get('regime_performance', {})
            self.timeframe_performance = data.get('timeframe_performance', {})

            logger.info(
                f"Loaded adaptive learning data: {len(self.trade_history)} trades, "
                f"{len(self.symbol_performance)} symbols, "
                f"{len(self.pattern_performance)} patterns."
            )

        except Exception as e:
            logger.error(f"Error loading adaptive learning data: {e}", exc_info=True)

    def save_data(self) -> None:
        """Save learning data to file."""
        if not self.enabled:
            return

        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(os.path.abspath(self.data_file)), exist_ok=True)

            # Prepare data for saving
            data = {
                'trade_history': [trade.to_dict() for trade in self.trade_history],
                'symbol_performance': self.symbol_performance,
                'pattern_performance': self.pattern_performance,
                'regime_performance': self.regime_performance,
                'timeframe_performance': self.timeframe_performance,
                'last_updated': datetime.now().isoformat()
            }

            # Save to file
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved adaptive learning data to {self.data_file}")

        except Exception as e:
            logger.error(f"Error saving adaptive learning data: {e}", exc_info=True)

    def add_trade_result(self, trade_result: TradeResult) -> None:
        """Add a trade result to learning data and update performance metrics."""
        if not self.enabled:
            return

        try:
            # Add to history
            self.trade_history.append(trade_result)

            # Limit history size
            max_total = self.max_history_per_symbol * 10
            if len(self.trade_history) > max_total:
                self.trade_history = self.trade_history[-max_total:]

            # Update performance metrics
            self._update_symbol_performance(trade_result)
            self._update_pattern_performance(trade_result)
            self._update_regime_performance(trade_result)
            self._update_timeframe_performance(trade_result)

            # Clear cache
            self._performance_cache.clear()

            # Auto-save every 10 trades
            if len(self.trade_history) % 10 == 0:
                self.save_data()

            logger.debug(
                f"Added trade result for {trade_result.symbol}: "
                f"Profit R: {trade_result.profit_r:.2f}, "
                f"Exit: {trade_result.exit_reason}"
            )

        except Exception as e:
            logger.error(f"Error adding trade result: {e}", exc_info=True)

    def _update_symbol_performance(self, trade_result: TradeResult) -> None:
        """Update performance metrics for symbols."""
        symbol = trade_result.symbol
        direction = trade_result.direction

        # Create structure if it doesn't exist
        if symbol not in self.symbol_performance:
            self.symbol_performance[symbol] = {
                'long': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0},
                'short': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0},
                'total': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0}
            }

        # Update stats for specific direction
        perf = self.symbol_performance[symbol][direction]
        perf['count'] += 1

        is_win = trade_result.profit_r > 0
        if is_win:
            perf['win_count'] += 1

        # Update moving average profit
        perf['avg_profit_r'] = (
                                       (perf['avg_profit_r'] * (perf['count'] - 1)) + trade_result.profit_r
                               ) / perf['count']
        perf['win_rate'] = perf['win_count'] / perf['count']

        # Update total stats
        total = self.symbol_performance[symbol]['total']
        total['count'] += 1
        if is_win:
            total['win_count'] += 1
        total['avg_profit_r'] = (
                                        (total['avg_profit_r'] * (total['count'] - 1)) + trade_result.profit_r
                                ) / total['count']
        total['win_rate'] = total['win_count'] / total['count']

    def _update_pattern_performance(self, trade_result: TradeResult) -> None:
        """Update performance metrics for patterns."""
        if not trade_result.pattern_names:
            return

        for pattern in trade_result.pattern_names:
            if pattern not in self.pattern_performance:
                self.pattern_performance[pattern] = {
                    'count': 0,
                    'win_count': 0,
                    'avg_profit_r': 0.0,
                    'win_rate': 0.0
                }

            perf = self.pattern_performance[pattern]
            perf['count'] += 1

            is_win = trade_result.profit_r > 0
            if is_win:
                perf['win_count'] += 1

            perf['avg_profit_r'] = (
                                           (perf['avg_profit_r'] * (perf['count'] - 1)) + trade_result.profit_r
                                   ) / perf['count']
            perf['win_rate'] = perf['win_count'] / perf['count']

    def _update_regime_performance(self, trade_result: TradeResult) -> None:
        """Update performance metrics for market regimes."""
        if not trade_result.market_regime:
            return

        regime = trade_result.market_regime
        direction = trade_result.direction

        # Create structure if it doesn't exist
        if regime not in self.regime_performance:
            self.regime_performance[regime] = {
                'long': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0},
                'short': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0},
                'total': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0}
            }

        # Update stats for specific direction
        perf = self.regime_performance[regime][direction]
        perf['count'] += 1

        is_win = trade_result.profit_r > 0
        if is_win:
            perf['win_count'] += 1

        perf['avg_profit_r'] = (
                                       (perf['avg_profit_r'] * (perf['count'] - 1)) + trade_result.profit_r
                               ) / perf['count']
        perf['win_rate'] = perf['win_count'] / perf['count']

        # Update total stats
        total = self.regime_performance[regime]['total']
        total['count'] += 1
        if is_win:
            total['win_count'] += 1
        total['avg_profit_r'] = (
                                        (total['avg_profit_r'] * (total['count'] - 1)) + trade_result.profit_r
                                ) / total['count']
        total['win_rate'] = total['win_count'] / total['count']

    def _update_timeframe_performance(self, trade_result: TradeResult) -> None:
        """Update performance metrics for timeframes."""
        if not trade_result.timeframe:
            return

        timeframe = trade_result.timeframe
        direction = trade_result.direction

        # Create structure if it doesn't exist
        if timeframe not in self.timeframe_performance:
            self.timeframe_performance[timeframe] = {
                'long': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0},
                'short': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0},
                'total': {'count': 0, 'win_count': 0, 'avg_profit_r': 0.0, 'win_rate': 0.0}
            }

        # Update stats
        perf = self.timeframe_performance[timeframe][direction]
        perf['count'] += 1

        is_win = trade_result.profit_r > 0
        if is_win:
            perf['win_count'] += 1

        perf['avg_profit_r'] = (
                                       (perf['avg_profit_r'] * (perf['count'] - 1)) + trade_result.profit_r
                               ) / perf['count']
        perf['win_rate'] = perf['win_count'] / perf['count']

        # Update total
        total = self.timeframe_performance[timeframe]['total']
        total['count'] += 1
        if is_win:
            total['win_count'] += 1
        total['avg_profit_r'] = (
                                        (total['avg_profit_r'] * (total['count'] - 1)) + trade_result.profit_r
                                ) / total['count']
        total['win_rate'] = total['win_count'] / total['count']

    def get_symbol_performance_factor(self, symbol: str, direction: str = 'total') -> float:
        """Get performance factor for a symbol (0.5 to 1.5)."""
        if not self.enabled or symbol not in self.symbol_performance:
            return 1.0

        perf = self.symbol_performance[symbol].get(direction, {})

        if perf.get('count', 0) < 5:  # Not enough data
            return 1.0

        win_rate = perf.get('win_rate', 0.5)
        avg_profit = perf.get('avg_profit_r', 0.0)

        # Calculate factor (0.5 to 1.5)
        factor = 0.5 + (win_rate * 0.5) + (min(avg_profit, 2.0) / 4.0)
        return min(max(factor, 0.5), 1.5)

    def get_pattern_performance_factors(self, pattern_names: List[str]) -> Dict[str, float]:
        """Get performance factors for patterns."""
        factors = {}

        for pattern in pattern_names:
            if pattern in self.pattern_performance:
                perf = self.pattern_performance[pattern]

                if perf.get('count', 0) >= 5:
                    win_rate = perf.get('win_rate', 0.5)
                    avg_profit = perf.get('avg_profit_r', 0.0)

                    factor = 0.5 + (win_rate * 0.5) + (min(avg_profit, 2.0) / 4.0)
                    factors[pattern] = min(max(factor, 0.5), 1.5)
                else:
                    factors[pattern] = 1.0
            else:
                factors[pattern] = 1.0

        return factors

    def get_adaptive_pattern_scores(self, pattern_scores: Dict[str, float]) -> Dict[str, float]:
        """Calculate adapted pattern scores based on performance."""
        cache_key = "adaptive_pattern_scores"

        if cache_key in self._performance_cache:
            cached_result, timestamp = self._performance_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl_seconds:
                return cached_result

        try:
            import copy
            adjusted_scores = copy.deepcopy(pattern_scores)

            # Adjust scores based on performance
            for pattern, score in pattern_scores.items():
                if pattern in self.pattern_performance:
                    perf = self.pattern_performance[pattern]

                    if perf.get('count', 0) >= 5:
                        performance_factor = self.get_pattern_performance_factors([pattern])[pattern]

                        # Apply gradual adjustment with learning rate
                        adjusted_score = score * (
                                1.0 + (performance_factor - 1.0) * self.learning_rate
                        )
                        adjusted_scores[pattern] = adjusted_score

            # Save to cache
            self._performance_cache[cache_key] = (adjusted_scores, time.time())
            return adjusted_scores

        except Exception as e:
            logger.error(f"Error calculating adaptive pattern scores: {e}", exc_info=True)
            return pattern_scores


