"""
Module: data_models.py - Shared Data Models
This module contains dataclasses for signals, scores, and trade results.
These models are used throughout the signal generation system.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
import random
import time
import logging

logger = logging.getLogger(__name__)


# ==================== SignalScore ====================

@dataclass
class SignalScore:
    """
    Detailed signal score components for signal quality evaluation.
    
    This class breaks down the final signal score into individual components,
    making it easier to understand why a signal has a certain score.
    
    Attributes:
        base_score: Raw base score before any multipliers
        timeframe_weight: Higher timeframe confirmation factor
        trend_alignment: Alignment with trend factor
        volume_confirmation: Volume confirmation factor
        pattern_quality: Pattern quality factor
        confluence_score: Confluence score (includes RR)
        final_score: Final calculated score
        symbol_performance_factor: Symbol historical performance
        correlation_safety_factor: Correlation safety factor
        macd_analysis_score: MACD analysis score
        structure_score: Higher timeframe structure score
        volatility_score: Volatility condition score
        harmonic_pattern_score: Harmonic pattern score
        price_channel_score: Price channel score
        cyclical_pattern_score: Cyclical pattern score
    
    Example:
        >>> score = SignalScore(
        ...     base_score=120.0,
        ...     timeframe_weight=1.2,
        ...     trend_alignment=1.5,
        ...     final_score=216.0
        ... )
    """
    
    base_score: float = 0.0
    timeframe_weight: float = 1.0
    trend_alignment: float = 1.0
    volume_confirmation: float = 1.0
    pattern_quality: float = 1.0
    confluence_score: float = 0.0
    final_score: float = 0.0
    symbol_performance_factor: float = 1.0
    correlation_safety_factor: float = 1.0
    macd_analysis_score: float = 1.0
    structure_score: float = 1.0
    volatility_score: float = 1.0
    harmonic_pattern_score: float = 1.0
    price_channel_score: float = 1.0
    cyclical_pattern_score: float = 1.0

    def to_dict(self) -> Dict[str, float]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            dict: All score components as dictionary
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'SignalScore':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with score components
            
        Returns:
            SignalScore instance
        """
        return cls(**data)


# ==================== SignalInfo ====================

@dataclass
class SignalInfo:
    """
    Complete trading signal information class.
    
    This dataclass contains all information about a trading signal,
    including entry/exit prices, risk management, scoring, and metadata.
    
    Attributes:
        symbol: Trading symbol (e.g., BTCUSDT)
        timeframe: Primary timeframe (usually shortest)
        signal_type: Type of signal (multi_timeframe, reversal, breakout, etc.)
        direction: Trade direction (long or short)
        entry_price: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        risk_reward_ratio: Risk/reward ratio
        timestamp: Signal generation time
        pattern_names: Patterns involved in signal
        score: Detailed score breakdown
        confirmation_timeframes: Analyzed timeframes
        rejected_reason: Reason if rejected
        regime: Detected market regime
        is_reversal: Whether signal is a reversal
        adapted_config: Stored adapted config
        macd_details: MACD analysis details
        volatility_details: Volatility details
        htf_details: Higher timeframe details
        harmonic_details: Harmonic pattern details
        channel_details: Channel details
        cyclical_details: Cyclical pattern details
        correlated_symbols: Correlated symbols and correlation values
        signal_id: Unique ID for signal tracking
        market_context: Market context information
        trade_result: Trade result for learning
    
    Example:
        >>> signal = SignalInfo(
        ...     symbol='BTCUSDT',
        ...     timeframe='5m',
        ...     signal_type='multi_timeframe',
        ...     direction='long',
        ...     entry_price=50000.0,
        ...     stop_loss=49500.0,
        ...     take_profit=51000.0,
        ...     risk_reward_ratio=2.0,
        ...     timestamp=datetime.now(timezone.utc)
        ... )
    """
    
    # Required fields
    symbol: str
    timeframe: str
    signal_type: str
    direction: str  # 'long' or 'short'
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    timestamp: datetime
    
    # Optional fields with defaults
    pattern_names: List[str] = field(default_factory=list)
    score: SignalScore = field(default_factory=SignalScore)
    confirmation_timeframes: List[str] = field(default_factory=list)
    rejected_reason: Optional[str] = None
    
    # Additional information
    regime: Optional[str] = None
    is_reversal: bool = False
    adapted_config: Optional[Dict[str, Any]] = None
    
    # Advanced analysis details
    macd_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    volatility_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    htf_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    harmonic_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    channel_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    cyclical_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # New fields
    correlated_symbols: List[Tuple[str, float]] = field(default_factory=list)
    signal_id: str = ""
    market_context: Dict[str, Any] = field(default_factory=dict)
    trade_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            dict: All signal information as dictionary
        """
        result = asdict(self)
        
        # Convert datetime to ISO string
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
        
        # Convert SignalScore to dictionary
        if self.score:
            result['score'] = self.score.to_dict()
        
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalInfo':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with signal information
            
        Returns:
            SignalInfo instance
        """
        data_copy = data.copy()
        
        # Convert ISO string to datetime
        if 'timestamp' in data_copy and isinstance(data_copy['timestamp'], str):
            data_copy['timestamp'] = datetime.fromisoformat(data_copy['timestamp'])
        
        # Convert score dictionary to SignalScore
        if 'score' in data_copy and isinstance(data_copy['score'], dict):
            data_copy['score'] = SignalScore.from_dict(data_copy['score'])
        
        return cls(**data_copy)

    def ensure_aware_timestamp(self) -> None:
        """
        Ensure timestamp is timezone-aware.
        Converts naive datetime to UTC-aware datetime.
        """
        if self.timestamp and self.timestamp.tzinfo is None:
            # Convert naive to aware with UTC
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
            logger.debug(f"Converted timestamp to UTC-aware for signal {self.signal_id}")

    def generate_signal_id(self) -> None:
        """
        Generate unique ID for the signal.
        Format: SYMBOL_DIRECTION_TIMESTAMP_RANDOM
        Example: BTC_L_1734264000_1234
        """
        if not self.signal_id:
            time_part = int(time.time())
            random_part = random.randint(1000, 9999)
            symbol_part = ''.join(c for c in self.symbol if c.isalnum())[:5]
            direction_part = 'L' if self.direction == 'long' else 'S'
            self.signal_id = f"{symbol_part}_{direction_part}_{time_part}_{random_part}"
            logger.debug(f"Generated signal ID: {self.signal_id}")


# ==================== TradeResult ====================

@dataclass
class TradeResult:
    """
    Trade result class for adaptive learning system.

    This class stores the outcome of a trade for learning purposes.
    The system uses this data to improve future signals.

    Attributes:
        signal_id: Related signal ID
        symbol: Traded symbol
        direction: Trade direction (long or short)
        entry_price: Entry price
        exit_price: Exit price
        stop_loss: Initial stop loss
        take_profit: Initial take profit
        entry_time: Entry time
        exit_time: Exit time
        exit_reason: Exit reason (tp, sl, manual, trailing)
        profit_pct: Profit/loss as percentage
        profit_r: Profit/loss in R (risk units)
        market_regime: Market regime during trade
        pattern_names: Patterns involved (simple names list)
        timeframe: Primary timeframe
        signal_score: Initial signal score
        trade_duration: Trade duration
        signal_type: Signal type

        # 🆕 NEW in v3.1.0: Detailed pattern tracking
        detected_patterns_details: Complete details of all patterns that triggered this trade
                                   Including: name, timeframe, candles_ago, recency_multiplier,
                                   base_strength, adjusted_strength, confidence, metadata
        pattern_contributions: Exact contribution of each pattern to final score
                              Format: {'Hammer': 15.2, 'MACD_bullish': 12.8, ...}
        score_breakdown: Complete breakdown of how final score was calculated
                        Including: base_scores, weighted_scores, bonuses, multipliers

    Example:
        >>> result = TradeResult(
        ...     signal_id='BTC_L_1734264000_1234',
        ...     symbol='BTCUSDT',
        ...     direction='long',
        ...     entry_price=50000.0,
        ...     exit_price=51000.0,
        ...     stop_loss=49500.0,
        ...     take_profit=51000.0,
        ...     entry_time=datetime.now(timezone.utc),
        ...     exit_time=datetime.now(timezone.utc),
        ...     exit_reason='tp',
        ...     profit_pct=2.0,
        ...     profit_r=2.0,
        ...     detected_patterns_details=[{
        ...         'name': 'Hammer',
        ...         'timeframe': '1h',
        ...         'candles_ago': 2,
        ...         'recency_multiplier': 0.8,
        ...         'adjusted_strength': 1.6
        ...     }],
        ...     pattern_contributions={'Hammer': 15.2, 'MACD': 12.8}
        ... )
    """

    # Required fields
    signal_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    exit_time: datetime
    exit_reason: str  # 'tp', 'sl', 'manual', 'trailing'
    profit_pct: float
    profit_r: float

    # Optional fields (existing)
    market_regime: Optional[str] = None
    pattern_names: List[str] = field(default_factory=list)  # Kept for backward compatibility
    timeframe: str = ""
    signal_score: float = 0.0
    trade_duration: Optional[timedelta] = None
    signal_type: str = ""

    # 🆕 NEW: Detailed pattern analysis fields (v3.1.0)
    detected_patterns_details: List[Dict[str, Any]] = field(default_factory=list)
    """
    Complete details of all detected patterns.
    Each pattern contains:
    - name: Pattern name (e.g., 'Hammer')
    - type: Pattern type ('candlestick' or 'chart')
    - direction: Pattern direction ('bullish' or 'bearish')
    - timeframe: Timeframe where pattern was detected
    - candles_ago: How many candles ago pattern was formed (recency)
    - recency_multiplier: Score multiplier based on recency (1.0 to 0.5)
    - base_strength: Base strength of pattern (1-3)
    - adjusted_strength: Strength after recency adjustment
    - confidence: Pattern confidence (0-1)
    - metadata: Additional pattern-specific information
    """

    pattern_contributions: Dict[str, float] = field(default_factory=dict)
    """
    Exact contribution of each pattern to the final score.
    Format: {'Hammer': 15.2, 'MACD_bullish': 12.8, 'RSI_oversold': 8.5}
    This shows how much each pattern added to the total score.
    """

    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    """
    Complete breakdown of score calculation.
    Includes:
    - base_scores: Individual scores from each analyzer
    - weighted_scores: After applying weights
    - aggregates: Bonuses and multipliers
    - final: Final score, confidence, strength
    - patterns: Pattern-specific details
    """

    def __post_init__(self):
        """
        Calculate trade duration after initialization.
        Automatically computes duration if not provided.
        """
        if self.entry_time and self.exit_time and not self.trade_duration:
            self.trade_duration = self.exit_time - self.entry_time
            logger.debug(f"Calculated trade duration: {self.trade_duration}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            dict: All trade result information including detailed pattern analysis
        """
        result = asdict(self)

        # Convert datetime to ISO string
        if self.entry_time:
            result['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            result['exit_time'] = self.exit_time.isoformat()

        # Convert timedelta to seconds
        if self.trade_duration:
            result['trade_duration_seconds'] = self.trade_duration.total_seconds()

        # Ensure new fields are included
        result['detected_patterns_details'] = self.detected_patterns_details
        result['pattern_contributions'] = self.pattern_contributions
        result['score_breakdown'] = self.score_breakdown

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeResult':
        """
        Create from dictionary.

        Args:
            data: Dictionary with trade result information

        Returns:
            TradeResult instance
        """
        data_copy = data.copy()

        # Convert ISO strings to datetime
        if 'entry_time' in data_copy and isinstance(data_copy['entry_time'], str):
            data_copy['entry_time'] = datetime.fromisoformat(data_copy['entry_time'])
        if 'exit_time' in data_copy and isinstance(data_copy['exit_time'], str):
            data_copy['exit_time'] = datetime.fromisoformat(data_copy['exit_time'])

        # Convert seconds to timedelta
        if 'trade_duration_seconds' in data_copy:
            seconds = data_copy.pop('trade_duration_seconds')
            data_copy['trade_duration'] = timedelta(seconds=seconds)

        # Ensure new fields have defaults if not present (backward compatibility)
        data_copy.setdefault('detected_patterns_details', [])
        data_copy.setdefault('pattern_contributions', {})
        data_copy.setdefault('score_breakdown', {})

        return cls(**data_copy)


# ==================== Testing ====================

if __name__ == "__main__":
    """Test data models"""
    print("🧪 Testing Data Models\n")
    
    # Test SignalScore
    print("=" * 60)
    print("Testing SignalScore...")
    score = SignalScore(
        base_score=120.0,
        timeframe_weight=1.2,
        trend_alignment=1.5,
        volume_confirmation=1.3,
        final_score=280.8
    )
    print(f"✅ Created: {score}")
    
    # Serialize
    score_dict = score.to_dict()
    print(f"✅ Serialized: final_score = {score_dict['final_score']}")
    
    # Deserialize
    score_restored = SignalScore.from_dict(score_dict)
    print(f"✅ Deserialized: {score_restored.final_score}")
    
    # Test SignalInfo
    print("\n" + "=" * 60)
    print("Testing SignalInfo...")
    signal = SignalInfo(
        symbol='BTCUSDT',
        timeframe='5m',
        signal_type='multi_timeframe',
        direction='long',
        entry_price=50000.0,
        stop_loss=49500.0,
        take_profit=51000.0,
        risk_reward_ratio=2.0,
        timestamp=datetime.now(timezone.utc),
        pattern_names=['bullish_engulfing', 'golden_cross'],
        score=score
    )
    
    # Generate ID
    signal.generate_signal_id()
    print(f"✅ Created signal with ID: {signal.signal_id}")
    print(f"   Symbol: {signal.symbol}")
    print(f"   Direction: {signal.direction}")
    print(f"   Entry: {signal.entry_price}")
    print(f"   R:R: {signal.risk_reward_ratio}")
    
    # Serialize
    signal_dict = signal.to_dict()
    print(f"✅ Serialized to dict (keys: {len(signal_dict)})")
    
    # Deserialize
    signal_restored = SignalInfo.from_dict(signal_dict)
    print(f"✅ Deserialized: {signal_restored.symbol} {signal_restored.direction}")
    
    # Test TradeResult
    print("\n" + "=" * 60)
    print("Testing TradeResult...")
    
    entry_time = datetime.now(timezone.utc)
    exit_time = entry_time + timedelta(hours=2, minutes=30)
    
    trade = TradeResult(
        signal_id=signal.signal_id,
        symbol='BTCUSDT',
        direction='long',
        entry_price=50000.0,
        exit_price=51000.0,
        stop_loss=49500.0,
        take_profit=51000.0,
        entry_time=entry_time,
        exit_time=exit_time,
        exit_reason='tp',
        profit_pct=2.0,
        profit_r=2.0,
        timeframe='5m',
        signal_score=280.8
    )
    
    print(f"✅ Created trade result:")
    print(f"   Signal ID: {trade.signal_id}")
    print(f"   Profit: {trade.profit_pct}% ({trade.profit_r}R)")
    print(f"   Duration: {trade.trade_duration}")
    print(f"   Exit reason: {trade.exit_reason}")
    
    # Serialize
    trade_dict = trade.to_dict()
    print(f"✅ Serialized to dict")
    
    # Deserialize
    trade_restored = TradeResult.from_dict(trade_dict)
    print(f"✅ Deserialized: Duration = {trade_restored.trade_duration}")
    
    print("\n" + "=" * 60)
    print("✅ All data model tests passed!")
