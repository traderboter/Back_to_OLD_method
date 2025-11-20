"""
SignalOrchestrator - Main Signal Generation Orchestrator

Coordinates the complete signal generation pipeline:
1. Data fetching
2. Indicator calculation (Phase 2)
3. Analyzer execution (Phase 3)
4. Signal scoring (Phase 4)
5. Signal validation (Phase 4)
6. Output delivery

This is the main entry point that ties everything together.
"""

from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
import asyncio
import time

from signal_generation.context import AnalysisContext
from signal_generation.signal_scorer import SignalScorer
from signal_generation.signal_validator import SignalValidator
from signal_generation.signal_info import SignalInfo
from signal_generation.timeframe_score_cache import TimeframeScoreCache
from signal_generation.multi_tf_aggregator import MultiTimeframeAggregator, TimeframeSignal


from signal_generation.systems import (
    MarketRegimeDetector,
    AdaptiveLearningSystem,
    CorrelationManager,
    EmergencyCircuitBreaker,
    TradeResult
)

# Import all 11 analyzers (10 original + VolumePatternAnalyzer)
from signal_generation.analyzers import (
    TrendAnalyzer,
    MomentumAnalyzer,
    VolumeAnalyzer,
    PatternAnalyzer,
    SRAnalyzer,
    VolatilityAnalyzer,
    HarmonicAnalyzer,
    ChannelAnalyzer,
    CyclicalAnalyzer,
    HTFAnalyzer,
    VolumePatternAnalyzer
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorStats:
    """Statistics for orchestrator performance."""

    total_runs: int = 0
    total_symbols_processed: int = 0
    total_signals_attempted: int = 0
    valid_signals: int = 0
    rejected_signals: int = 0
    errors: int = 0

    total_time: float = 0.0
    avg_time_per_symbol: float = 0.0

    last_run_time: Optional[datetime] = None

    # Breakdown by reason
    rejection_reasons: Dict[str, int] = field(default_factory=dict)

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_signals_attempted == 0:
            return 0.0
        return self.valid_signals / self.total_signals_attempted

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        if self.last_run_time:
            data['last_run_time'] = self.last_run_time.isoformat()
        return data

    def __str__(self) -> str:
        """String representation."""
        return (
            f"OrchestratorStats(runs={self.total_runs}, "
            f"symbols={self.total_symbols_processed}, "
            f"valid={self.valid_signals}/{self.total_signals_attempted}, "
            f"success_rate={self.get_success_rate():.1%})"
        )


class SignalOrchestrator:
    """
    Main orchestrator for complete signal generation pipeline.

    Responsibilities:
    1. Coordinate data fetching
    2. Calculate indicators
    3. Run all analyzers
    4. Generate signals
    5. Validate signals
    6. Deliver output

    Key features:
    - Complete pipeline integration
    - Parallel processing support
    - Error handling
    - Statistics tracking
    - Configurable
    """

    def __init__(
            self,
            config: Dict[str, Any],
            market_data_fetcher: Any,  # MarketDataFetcher instance
            indicator_calculator: Any,  # IndicatorCalculator instance
            trade_manager_callback: Optional[Callable] = None,
            skip_validation: Optional[bool] = None
    ):
        """
        Initialize SignalOrchestrator.

        Args:
            config: Configuration dictionary
            market_data_fetcher: MarketDataFetcher for data
            indicator_calculator: IndicatorCalculator for indicators
            trade_manager_callback: Optional callback to send signals
            skip_validation: Skip signal validation (for analysis purposes only).
                           If None, reads from config. Default in config is False.
        """
        self.config = config
        self.market_data_fetcher = market_data_fetcher
        self.indicator_calculator = indicator_calculator
        self.trade_manager_callback = trade_manager_callback

        # Get orchestrator config
        orch_config = config.get('orchestrator', {})

        # Determine skip_validation: parameter overrides config
        if skip_validation is not None:
            self.skip_validation = skip_validation
        else:
            self.skip_validation = orch_config.get('skip_validation', False)

        # Settings
        self.max_concurrent = orch_config.get('max_concurrent', 10)
        self.timeout_per_symbol = orch_config.get('timeout_per_symbol', 30)
        self.ohlcv_limit = orch_config.get('ohlcv_limit', 500)
        self.send_to_trade_manager = orch_config.get('send_to_trade_manager', True)

        # Initialize Phase 4 components
        self.signal_scorer = SignalScorer(config)
        self.signal_validator = SignalValidator(config)

        # Initialize Phase 3 components (10 Analyzers)
        # Initialize Phase 3 components (10 Analyzers)
        self.analyzers = self._initialize_analyzers(config)

        # Initialize Advanced Systems
        systems_config = config.get('systems', {})

        # Market Regime Detector
        self.regime_detector = MarketRegimeDetector(
            systems_config.get('regime_detector', {})
        )

        # Adaptive Learning System
        self.adaptive_learning = AdaptiveLearningSystem(
            systems_config.get('adaptive_learning', {})
        )

        # Correlation Manager
        self.correlation_manager = CorrelationManager(
            systems_config.get('correlation_manager', {})
        )

        # Emergency Circuit Breaker
        self.circuit_breaker = EmergencyCircuitBreaker(
            systems_config.get('circuit_breaker', {})
        )

        # ✨ Timeframe Score Cache - برای جلوگیری از محاسبات تکراری
        self.tf_score_cache = TimeframeScoreCache(config)
        logger.info(f"TimeframeScoreCache initialized (enabled={self.tf_score_cache.enabled})")

        # ✨ Multi-Timeframe Aggregator (OLD SYSTEM)
        # Always use multi-TF aggregation (can be disabled via config if needed)
        self.use_multi_tf_aggregation = orch_config.get('use_multi_tf_aggregation', True)

        if self.use_multi_tf_aggregation:
            self.multi_tf_aggregator = MultiTimeframeAggregator(config)
            logger.info("✅ MultiTimeframeAggregator initialized (OLD SYSTEM)")
        else:
            self.multi_tf_aggregator = None
            logger.info("⚠️ Multi-TF aggregation disabled via config")

        # State
        self.is_running = False
        self.stats = OrchestratorStats()

        # Context cache to avoid recalculation in _generate_signal_with_context
        self._context_cache: Dict[str, Tuple[AnalysisContext, float]] = {}
        self._context_cache_ttl = 60  # 60 seconds TTL

        # Semaphore for concurrent processing
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent)

        logger.info(
            f"SignalOrchestrator initialized: "
            f"{len(self.analyzers)} analyzers, "
            f"max_concurrent={self.max_concurrent}"
        )

    def _initialize_analyzers(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize all 11 analyzers (10 original + VolumePatternAnalyzer).

        Args:
            config: Configuration

        Returns:
            Dictionary of analyzer_name -> analyzer_instance
        """
        analyzers = {}

        analyzer_classes = {
            'trend': TrendAnalyzer,
            'momentum': MomentumAnalyzer,
            'volume': VolumeAnalyzer,
            'volume_patterns': VolumePatternAnalyzer,
            'patterns': PatternAnalyzer,
            'support_resistance': SRAnalyzer,
            'volatility': VolatilityAnalyzer,
            'harmonic': HarmonicAnalyzer,
            'channel': ChannelAnalyzer,
            'cyclical': CyclicalAnalyzer,
            'htf': HTFAnalyzer
        }

        # Check which analyzers are enabled
        enabled = config.get('orchestrator', {}).get('enabled_analyzers', list(analyzer_classes.keys()))

        for name, analyzer_class in analyzer_classes.items():
            if name in enabled:
                try:
                    analyzers[name] = analyzer_class(config)
                    logger.debug(f"Initialized {name} analyzer")
                except Exception as e:
                    logger.error(f"Failed to initialize {name} analyzer: {e}")

        logger.info(f"Initialized {len(analyzers)}/11 analyzers")

        return analyzers

    async def generate_signal_for_symbol(
            self,
            symbol: str,
            timeframe: str
    ) -> Optional[SignalInfo]:
        """
        Main method: Generate signal for single symbol/timeframe.

        Complete pipeline from data fetching to validated signal.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h')

        Returns:
            Valid SignalInfo or None
        """
        start_time = time.time()

        try:
            logger.info(f"=== Starting signal generation for {symbol} {timeframe} ===")

            # === STEP 0: Circuit Breaker Check ===
            if self.circuit_breaker.enabled:
                is_active, reason = self.circuit_breaker.check_if_active()
                if is_active:
                    logger.warning(
                        f"🚨 Circuit breaker active: {reason}. "
                        f"Skipping signal generation for {symbol}."
                    )
                    self.stats.errors += 1
                    return None

            # === STEP 1: Fetch Market Data ===
            logger.info(f"[1/7] Fetching data for {symbol} {timeframe}")

            df = await self._fetch_market_data(symbol, timeframe)

            if df is None:
                logger.warning(f"No data available for {symbol}")
                self.stats.errors += 1
                return None

            logger.info(f"  ✓ Fetched {len(df)} candles")

            # === STEP 1.5: Check Cache ===
            # آیا باید دوباره محاسبه کنیم یا از کش استفاده کنیم؟
            should_recalc, reason = self.tf_score_cache.should_recalculate(
                symbol, timeframe, df
            )

            if not should_recalc:
                # کش معتبر است - استفاده از امتیاز کش شده
                logger.info(
                    f"  💾 Using CACHED score for {symbol} {timeframe} "
                    f"(reason: {reason}) - Skipping recalculation"
                )
                cached_signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
                if cached_signal:
                    return cached_signal

            # کندل جدید آمده یا کش invalid است - محاسبه مجدد
            logger.info(
                f"  🔄 RECALCULATING score for {symbol} {timeframe} "
                f"(reason: {reason})"
            )

            # === STEP 2: Create Analysis Context ===
            logger.info(f"[2/7] Creating context for {symbol}")

            context = AnalysisContext(
                symbol=symbol,
                timeframe=timeframe,
                df=df
            )

            # === STEP 3: Calculate Indicators ===
            logger.info(f"[3/7] Calculating indicators for {symbol}")

            success = self._calculate_indicators(context)

            if not success:
                logger.error(f"Failed to calculate indicators for {symbol}")
                self.stats.errors += 1
                return None

            logger.info(f"  ✓ Indicators calculated")


            logger.info(f"[3.5/7] Detecting market regime for {symbol}")

            regime_info = {'regime': 'unknown', 'confidence': 0.0}

            if self.regime_detector.enabled:
                regime_info = self.regime_detector.detect_regime(context.df)
                logger.info(
                    f"  ✓ Regime: {regime_info.get('regime')}, "
                    f"Confidence: {regime_info.get('confidence', 0):.2f}"
                )

                # Store in context for analyzers to use
                context.metadata['regime_info'] = regime_info


            # === STEP 4: Run Analyzers ===
            logger.info(f"[4/7] Running {len(self.analyzers)} analyzers for {symbol}")

            self._run_analyzers(context)

            # Check minimum required analyzers
            required = ['trend', 'momentum', 'volume']
            missing = [r for r in required if not context.get_result(r)]

            if missing:
                logger.warning(f"Missing required analyzers for {symbol}: {missing}")
                self.stats.errors += 1
                return None

            logger.info(f"  ✓ All analyzers completed")

            # === STEP 5: Determine Direction ===
            logger.info(f"[5/7] Determining signal direction for {symbol}")

            direction = self._determine_direction(context)

            if not direction:
                logger.info(f"No clear direction for {symbol}")
                return None

            logger.info(f"  ✓ Direction: {direction}")

            # === STEP 6: Calculate Score ===
            logger.info(f"[6/7] Scoring signal for {symbol} {direction}")

            score = self.signal_scorer.calculate_score(context, direction)

            if not score:
                logger.warning(f"Failed to calculate score for {symbol}")
                self.stats.errors += 1
                return None

            logger.info(
                f"  ✓ Score: {score.final_score:.2f} "
                f"({score.signal_strength}, conf={score.confidence:.2f})"
            )

            # ✨ لاگ جزئیات الگوهای تشخیص داده شده
            if score.detected_patterns:
                logger.info(
                    f"  📊 الگوهای تشخیص داده شده برای {symbol} {direction}:\n"
                    f"{score.get_pattern_summary()}"
                )

            # Build SignalInfo
            signal = self._build_signal_info(context, direction, score)

            if not signal:
                logger.warning(f"Failed to build signal for {symbol}")
                self.stats.errors += 1
                return None

            self.stats.total_signals_attempted += 1

            if self.correlation_manager.enabled:
                correlation_factor = self.correlation_manager.get_correlation_safety_factor(
                    symbol,
                    direction
                )

                if correlation_factor < 0.7:
                    logger.info(
                        f"High correlation exposure for {symbol} "
                        f"(factor: {correlation_factor:.2f}). "
                        f"Reducing signal score."
                    )
                    # Reduce score
                    score.final_score *= correlation_factor
                    score.correlation_safety_factor = correlation_factor

                    # Update in signal
                    signal.score = score
            # === STEP 7: Validate ===
            logger.info(f"[7/7] Validating signal for {symbol}")

            # Skip validation if requested (for analysis purposes)
            if self.skip_validation:
                logger.info(f"⚠️  Skipping validation for {symbol} (analysis mode)")
                is_valid = True
                reason = "validation_skipped"
            else:
                is_valid, reason = self.signal_validator.validate(signal, context)

            if not is_valid:
                logger.info(f"Signal rejected for {symbol}: {reason}")
                self.stats.rejected_signals += 1

                # Track rejection reason
                if reason not in self.stats.rejection_reasons:
                    self.stats.rejection_reasons[reason] = 0
                self.stats.rejection_reasons[reason] += 1

                return None

            # === SUCCESS ===
            self.stats.valid_signals += 1

            logger.info(
                f"✅ Valid signal generated for {symbol} {direction}! "
                f"Score: {score.final_score:.2f}, RR: {signal.risk_reward_ratio:.2f}"
            )

            # Register signal (skip if validation was skipped)
            if not self.skip_validation:
                self.signal_validator.register_signal(signal)

            # ✨ Update Cache - ذخیره امتیاز برای استفاده‌های بعدی
            self.tf_score_cache.update_cache(symbol, timeframe, signal, df)
            logger.debug(f"💾 Cached signal for {symbol} {timeframe}")

            # ✨ Cache context to avoid recalculation in _generate_signal_with_context
            cache_key = f"{symbol}:{timeframe}"
            self._context_cache[cache_key] = (context, time.time())
            logger.debug(f"💾 Cached context for {symbol} {timeframe}")

            # Send to TradeManager
            if self.send_to_trade_manager and self.trade_manager_callback:
                await self._send_to_trade_manager(signal)

            return signal

        except asyncio.TimeoutError:
            logger.error(f"Timeout processing {symbol}")
            self.stats.errors += 1
            return None

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            self.stats.errors += 1
            return None

        finally:
            # Update stats
            elapsed = time.time() - start_time
            self.stats.total_time += elapsed
            self.stats.total_symbols_processed += 1
            self.stats.avg_time_per_symbol = (
                    self.stats.total_time / self.stats.total_symbols_processed
            )

            logger.info(
                f"=== Completed {symbol} in {elapsed:.2f}s "
                f"(avg: {self.stats.avg_time_per_symbol:.2f}s) ==="
            )

    async def _fetch_market_data(self, symbol: str, timeframe: str):
        """Fetch market data using MarketDataFetcher."""
        try:
            # Use get_historical_data method from MarketDataFetcher
            df = await self.market_data_fetcher.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=self.ohlcv_limit
            )

            if df is None or len(df) < 200:
                logger.warning(f"Insufficient data for {symbol}: {len(df) if df is not None else 0} candles")
                return None

            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def _calculate_indicators(self, context: AnalysisContext) -> bool:
        """Calculate indicators using IndicatorCalculator."""
        try:
            # IndicatorCalculator.calculate_all() modifies context.df in-place
            self.indicator_calculator.calculate_all(context)
            return True

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return False

    def _run_analyzers(self, context: AnalysisContext) -> None:
        """Run all enabled analyzers."""
        for analyzer_name, analyzer in self.analyzers.items():
            try:
                analyzer.analyze(context)
                logger.debug(f"  ✓ {analyzer_name} completed")
            except Exception as e:
                logger.error(f"  ✗ {analyzer_name} failed: {e}", exc_info=True)

    def _determine_direction(self, context: AnalysisContext) -> Optional[str]:
        """
        Determine signal direction from analyzer results.

        Args:
            context: AnalysisContext with results

        Returns:
            'LONG', 'SHORT', or None
        """
        bullish_score = 0
        bearish_score = 0

        # Trend (weight 3x)
        trend_result = context.get_result('trend')
        if trend_result:
            direction = trend_result.get('direction', 'neutral')
            strength = abs(trend_result.get('strength', 0))

            if direction in ['bullish', 'bullish_aligned']:
                bullish_score += strength * 3
            elif direction in ['bearish', 'bearish_aligned']:
                bearish_score += strength * 3

        # Momentum (weight 2x)
        momentum_result = context.get_result('momentum')
        if momentum_result:
            direction = momentum_result.get('direction', 'neutral')
            strength = abs(momentum_result.get('strength', 0))

            if direction == 'bullish':
                bullish_score += strength * 2
            elif direction == 'bearish':
                bearish_score += strength * 2

        # Volume confirmation (bonus +1)
        volume_result = context.get_result('volume')
        if volume_result and volume_result.get('is_confirmed'):
            if bullish_score > bearish_score:
                bullish_score += 1
            elif bearish_score > bullish_score:
                bearish_score += 1

        # Patterns
        pattern_result = context.get_result('patterns')
        if pattern_result:
            patterns = (
                    pattern_result.get('candlestick_patterns', []) +
                    pattern_result.get('chart_patterns', [])
            )

            for pattern in patterns:
                p_dir = pattern.get('direction', 'neutral')
                p_str = pattern.get('adjusted_strength', 0)

                if p_dir == 'bullish':
                    bullish_score += p_str * 0.5
                elif p_dir == 'bearish':
                    bearish_score += p_str * 0.5

        # HTF alignment (bonus +2)
        htf_result = context.get_result('htf')
        if htf_result and htf_result.get('alignment'):
            htf_trend = htf_result.get('htf_trend', 'neutral')

            if htf_trend == 'bullish':
                bullish_score += 2
            elif htf_trend == 'bearish':
                bearish_score += 2

        logger.debug(f"Direction scores: Bullish={bullish_score:.1f}, Bearish={bearish_score:.1f}")

        # Require 1.2x dominance
        if bullish_score > bearish_score * 1.2:
            return 'LONG'
        elif bearish_score > bullish_score * 1.2:
            return 'SHORT'
        else:
            return None

    def _build_signal_info(
            self,
            context: AnalysisContext,
            direction: str,
            score
    ) -> Optional[SignalInfo]:
        """Build SignalInfo with entry/SL/TP."""
        try:
            df = context.df
            current_price = df['close'].iloc[-1]

            # Get volatility for stop loss
            volatility_result = context.get_result('volatility')
            if not volatility_result:
                return None

            atr = volatility_result.get('atr_value')
            stop_atr_mult = volatility_result.get('recommended_stop_atr', 2.0)

            if not atr:
                return None

            stop_distance = atr * stop_atr_mult

            # Get SR for take profit
            sr_result = context.get_result('support_resistance')

            # Calculate levels
            if direction == 'LONG':
                entry = current_price
                stop_loss = entry - stop_distance
                default_tp = entry + (stop_distance * 2)  # Default RR = 2.0

                # Use S/R only if it's better than default (and in correct direction)
                if sr_result and sr_result.get('nearest_resistance'):
                    sr_tp = sr_result['nearest_resistance']
                    # Check: SR must be above entry and provide better RR than default
                    if sr_tp > entry and (sr_tp - entry) >= (default_tp - entry) * 0.8:
                        take_profit = sr_tp
                    else:
                        take_profit = default_tp
                else:
                    take_profit = default_tp
            else:
                entry = current_price
                stop_loss = entry + stop_distance
                default_tp = entry - (stop_distance * 2)  # Default RR = 2.0

                # Use S/R only if it's better than default (and in correct direction)
                if sr_result and sr_result.get('nearest_support'):
                    sr_tp = sr_result['nearest_support']
                    # Check: SR must be below entry and provide better RR than default
                    if sr_tp < entry and (entry - sr_tp) >= (entry - default_tp) * 0.8:
                        take_profit = sr_tp
                    else:
                        take_profit = default_tp
                else:
                    take_profit = default_tp

            # ✨ NEW: Collect all analysis results for complete signal information
            analysis_summary = {
                'patterns': context.get_result('patterns'),
                'trend': context.get_result('trend'),
                'momentum': context.get_result('momentum'),
                'volume': context.get_result('volume'),
                'volume_patterns': context.get_result('volume_patterns'),
                'support_resistance': context.get_result('support_resistance'),
                'volatility': context.get_result('volatility'),
                'harmonic': context.get_result('harmonic'),
                'channel': context.get_result('channel'),
                'cyclical': context.get_result('cyclical'),
                'htf': context.get_result('htf')
            }

            # ✨ NEW: Extract market context for better trade tracking
            market_context = {
                'current_price': float(current_price),
                'atr': float(atr) if atr else None,
                'stop_atr_multiplier': float(stop_atr_mult),
                'timestamp': context.df['timestamp'].iloc[-1] if 'timestamp' in context.df.columns else None
            }

            # Build signal
            signal = SignalInfo(
                symbol=context.symbol,
                timeframe=context.timeframe,
                direction=direction,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                score=score,
                confidence=score.confidence,
                contributing_analyzers=score.contributing_analyzers,
                analysis_summary=analysis_summary,  # ✅ Complete analyzer results
                market_context=market_context  # ✅ Market conditions at signal time
            )

            # 🆕 Fill metadata with complete analysis details for backtest
            signal.metadata = self._build_signal_metadata(context, score, direction)

            # Calculate RR
            signal.calculate_risk_reward()

            # Validate prices
            if not signal.validate_prices():
                return None

            # ✨ NEW: Add key factors from patterns for better understanding
            patterns_result = context.get_result('patterns')
            if patterns_result and patterns_result.get('strongest_pattern'):
                strongest = patterns_result['strongest_pattern']

                # Add main pattern info
                signal.add_key_factor(
                    f"{strongest['name']} pattern detected "
                    f"(confidence: {strongest.get('confidence', 0):.1%})"
                )

                # Add pattern metadata if available
                if 'metadata' in strongest:
                    metadata = strongest['metadata']

                    # Doji-specific metadata
                    if 'doji_type' in metadata:
                        signal.add_key_factor(f"Doji type: {metadata['doji_type']}")

                    if 'quality_score' in metadata:
                        signal.add_key_factor(
                            f"Pattern quality: {metadata['quality_score']:.1f}/100"
                        )

                    # Engulfing-specific metadata
                    if 'engulfing_ratio' in metadata:
                        signal.add_key_factor(
                            f"Engulfing ratio: {metadata['engulfing_ratio']:.2f}x"
                        )

                    # Hammer/Shooting Star metadata
                    if 'lower_shadow_ratio' in metadata and metadata['lower_shadow_ratio'] > 0.5:
                        signal.add_key_factor(
                            f"Strong lower shadow: {metadata['lower_shadow_ratio']:.1%}"
                        )

                    if 'upper_shadow_ratio' in metadata and metadata['upper_shadow_ratio'] > 0.5:
                        signal.add_key_factor(
                            f"Strong upper shadow: {metadata['upper_shadow_ratio']:.1%}"
                        )

                # Add recency info
                if strongest.get('location') == 'recent':
                    candles_ago = strongest.get('candles_ago', 0)
                    signal.add_key_factor(f"Pattern formed {candles_ago} candles ago")

            # Add trend alignment info
            trend_result = context.get_result('trend')
            if trend_result:
                trend_direction = trend_result.get('direction', 'neutral')
                trend_strength = trend_result.get('strength', 0)
                if trend_direction == direction.lower():
                    signal.add_key_factor(
                        f"Aligned with {trend_direction} trend (strength: {trend_strength:.1f})"
                    )

            # Add volume confirmation
            volume_result = context.get_result('volume')
            if volume_result and volume_result.get('is_confirmed'):
                signal.add_key_factor("Volume confirmed")

            return signal

        except Exception as e:
            logger.error(f"Error building signal: {e}")
            return None

    async def _generate_signal_with_context(
            self,
            symbol: str,
            timeframe: str
    ) -> Optional[Tuple[SignalInfo, AnalysisContext]]:
        """
        Generate signal and return both signal and context.

        This is used by analyze_symbol for multi-TF aggregation.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Tuple of (SignalInfo, AnalysisContext) or None
        """
        try:
            # Check if context is cached (to avoid duplicate calculation)
            cache_key = f"{symbol}:{timeframe}"
            if cache_key in self._context_cache:
                cached_context, timestamp = self._context_cache[cache_key]
                # Check if cache is still valid (within TTL)
                if time.time() - timestamp < self._context_cache_ttl:
                    logger.debug(f"💾 Using cached context for {symbol} {timeframe}")
                    # Get signal from TimeframeScoreCache
                    signal = self.tf_score_cache.get_cached_score(symbol, timeframe)
                    if signal:
                        return (signal, cached_context)

            # Use the main generate_signal_for_symbol method
            signal = await self.generate_signal_for_symbol(symbol, timeframe)

            if not signal:
                return None

            # Get context from cache (should be there after generate_signal_for_symbol)
            if cache_key in self._context_cache:
                cached_context, _ = self._context_cache[cache_key]
                return (signal, cached_context)

            # Fallback: Recreate context if not in cache (shouldn't happen normally)
            logger.warning(f"Context not found in cache for {symbol} {timeframe}, recreating...")
            df = await self._fetch_market_data(symbol, timeframe)
            if df is None:
                return None

            context = AnalysisContext(
                symbol=symbol,
                timeframe=timeframe,
                df=df
            )

            # Recalculate indicators and analyzers to populate context
            self._calculate_indicators(context)
            self._run_analyzers(context)

            return (signal, context)

        except Exception as e:
            logger.error(f"Error generating signal with context for {symbol} {timeframe}: {e}")
            return None

    async def analyze_symbol(
            self,
            symbol: str,
            timeframes_data: Dict[str, Any]
    ) -> Optional[SignalInfo]:
        """
        Wrapper method for multi-timeframe signal generation.

        This method is called by SignalProcessor with multi-timeframe data.
        It generates signals for each timeframe and aggregates them.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframes_data: Dict of {timeframe: DataFrame}

        Returns:
            Aggregated SignalInfo or best signal (depending on config)
        """
        try:
            logger.debug(f"analyze_symbol called for {symbol} with {len(timeframes_data)} timeframes")

            # Filter valid timeframes
            valid_timeframes = {
                tf: df for tf, df in timeframes_data.items()
                if df is not None and not df.empty
            }

            if not valid_timeframes:
                logger.warning(f"No valid timeframes data for {symbol}")
                return None

            # === Multi-TF Aggregation (OLD SYSTEM) ===
            if not self.use_multi_tf_aggregation or not self.multi_tf_aggregator:
                logger.warning(f"Multi-TF aggregation is disabled - cannot analyze {symbol}")
                return None

            logger.info(f"🔄 Using Multi-TF Aggregation (OLD SYSTEM) for {symbol}")

            # Generate signals with contexts for each timeframe
            timeframe_signals: Dict[str, TimeframeSignal] = {}

            for timeframe in valid_timeframes.keys():
                try:
                    result = await self._generate_signal_with_context(symbol, timeframe)
                    if result:
                        signal, context = result

                        # Build TimeframeSignal
                        tf_signal = TimeframeSignal(
                            timeframe=timeframe,
                            direction=signal.direction,
                            score=signal.score,
                            context=context,
                            volume_confirmed=(context.get_result('volume') or {}).get('is_confirmed', False)
                        )

                        timeframe_signals[timeframe] = tf_signal
                        logger.debug(f"  ✓ Generated {timeframe} signal: {signal.direction}, score={signal.score.final_score:.2f}")

                except Exception as e:
                    logger.error(f"Error generating signal for {symbol} {timeframe}: {e}")
                    continue

            if not timeframe_signals:
                logger.debug(f"No valid timeframe signals for {symbol}")
                return None

            logger.info(f"  📊 Aggregating {len(timeframe_signals)} timeframe signals for {symbol}")

            # Aggregate using OLD SYSTEM approach
            aggregated_signal = self.multi_tf_aggregator.aggregate_timeframe_scores(
                symbol=symbol,
                timeframe_signals=timeframe_signals
            )

            if aggregated_signal:
                logger.info(
                    f"✅ Multi-TF aggregated signal for {symbol}: {aggregated_signal.direction}, "
                    f"score={aggregated_signal.score.final_score:.2f}"
                )
                return aggregated_signal
            else:
                logger.info(f"No clear direction from multi-TF aggregation for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Error in analyze_symbol for {symbol}: {e}", exc_info=True)
            return None

    async def _send_to_trade_manager(self, signal: SignalInfo) -> None:
        """Send signal to TradeManager via callback."""
        try:
            await self.trade_manager_callback(signal)
            logger.info(f"Signal sent to TradeManager: {signal.symbol}")
        except Exception as e:
            logger.error(f"Failed to send signal to TradeManager: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        stats = self.stats.to_dict()

        # اضافه کردن آمار کش
        if self.tf_score_cache.enabled:
            cache_stats = self.tf_score_cache.get_statistics()
            efficiency = self.tf_score_cache.estimate_efficiency_gain()
            stats['cache'] = {
                'statistics': cache_stats,
                'efficiency': efficiency
            }

        return stats

    def reset_statistics(self) -> None:
        """Reset statistics."""
        self.stats = OrchestratorStats()
        logger.info("Statistics reset")

    def log_cache_statistics(self) -> None:
        """نمایش آمار کش در لاگ"""
        if self.tf_score_cache.enabled:
            self.tf_score_cache.log_statistics()

            # نمایش تخمین بهبود کارایی
            efficiency = self.tf_score_cache.estimate_efficiency_gain()
            logger.info("=" * 60)
            logger.info("📈 Efficiency Gains from Caching:")
            logger.info(f"Total requests: {efficiency['total_requests']}")
            logger.info(f"Requests saved: {efficiency['cache_hits']} ({efficiency['requests_saved_percentage']:.1f}%)")
            logger.info(f"Estimated time saved: {efficiency['estimated_time_saved_minutes']:.1f} minutes")
            logger.info("=" * 60)
        else:
            logger.info("Timeframe score cache is disabled")

    def register_trade_result(self, trade_result: TradeResult) -> None:
        """
        Register a trade result for system learning and feedback.

        Args:
            trade_result: TradeResult with trade information
        """
        try:
            # Add to adaptive learning system
            if self.adaptive_learning.enabled:
                self.adaptive_learning.add_trade_result(trade_result)
                logger.debug(
                    f"Trade result registered in adaptive learning: "
                    f"{trade_result.symbol}, Profit: {trade_result.profit_r:.2f}R"
                )

            # Add to emergency circuit breaker
            if self.circuit_breaker.enabled:
                self.circuit_breaker.add_trade_result(trade_result)
                logger.debug(
                    f"Trade result registered in circuit breaker: "
                    f"{trade_result.symbol}, Profit: {trade_result.profit_r:.2f}R"
                )

            logger.info(
                f"✅ Registered trade result for {trade_result.symbol}: "
                f"Signal ID: {trade_result.signal_id}, "
                f"Direction: {trade_result.direction}, "
                f"Profit: {trade_result.profit_r:.2f}R, "
                f"Exit: {trade_result.exit_reason}"
            )

        except Exception as e:
            logger.error(f"Error registering trade result: {e}", exc_info=True)

    def update_active_positions(self, positions: Dict[str, Dict[str, Any]]) -> None:
        """
        Update active positions for correlation management.

        Args:
            positions: Dictionary of {symbol: position_info}
                      position_info must contain 'direction' key
        """
        try:
            if self.correlation_manager.enabled:
                self.correlation_manager.update_active_positions(positions)
                logger.debug(
                    f"Updated active positions: {len(positions)} positions"
                )

        except Exception as e:
            logger.error(f"Error updating active positions: {e}", exc_info=True)

    def shutdown(self) -> None:
        """
        Shutdown orchestrator and save all data.
        """
        logger.info("Shutting down SignalOrchestrator...")

        try:
            # Save adaptive learning data
            if self.adaptive_learning and self.adaptive_learning.enabled:
                self.adaptive_learning.save_data()
                logger.info("  ✓ Adaptive learning data saved")

            # Save correlation data
            if self.correlation_manager and self.correlation_manager.enabled:
                self.correlation_manager.save_data()
                logger.info("  ✓ Correlation data saved")

            # Log final statistics
            logger.info(f"  Final stats: {self.stats}")

            logger.info("SignalOrchestrator shut down successfully.")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def _build_signal_metadata(self, context: 'AnalysisContext', score: 'SignalScore', direction: str) -> Dict[str, Any]:
        """
        🆕 Build comprehensive metadata for signal analysis in backtest.

        This metadata contains ALL information needed to understand why a trade was opened,
        including indicator values, analyzer results, patterns, and scoring details.

        Args:
            context: AnalysisContext with analysis results
            score: SignalScore object
            direction: Trade direction (LONG/SHORT)

        Returns:
            Dictionary with complete analysis metadata
        """
        df = context.df

        # Extract last candle indicator values
        indicator_values = {}
        indicator_columns = [
            'ema_20', 'ema_50', 'ema_100', 'ema_200',
            'sma_20', 'sma_50', 'sma_200',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'stoch_k', 'stoch_d',
            'atr', 'bb_upper', 'bb_middle', 'bb_lower',
            'obv', 'volume', 'volume_sma'
        ]

        for col in indicator_columns:
            if col in df.columns:
                try:
                    indicator_values[col] = float(df[col].iloc[-1])
                except (ValueError, TypeError):
                    indicator_values[col] = None

        # Add price info
        if 'close' in df.columns:
            indicator_values['close'] = float(df['close'].iloc[-1])
        if 'high' in df.columns:
            indicator_values['high'] = float(df['high'].iloc[-1])
        if 'low' in df.columns:
            indicator_values['low'] = float(df['low'].iloc[-1])
        if 'open' in df.columns:
            indicator_values['open'] = float(df['open'].iloc[-1])

        # Extract analyzer results
        analyzer_results = {}
        analyzer_names = [
            'trend', 'momentum', 'volume', 'patterns', 'sr',
            'volatility', 'harmonic', 'channel', 'cyclical', 'htf'
        ]

        for analyzer_name in analyzer_names:
            result = context.get_result(analyzer_name)
            if result:
                # Convert to serializable format (remove non-serializable objects)
                analyzer_results[analyzer_name] = self._make_serializable(result)

        # Extract market regime
        market_regime = None
        regime_result = context.get_result('market_regime')
        if regime_result and isinstance(regime_result, dict):
            market_regime = regime_result.get('regime', 'unknown')

        # Build complete metadata
        metadata = {
            'timeframe': context.timeframe,
            'symbol': context.symbol,
            'direction': direction,

            # Indicator values at signal time
            'indicators': indicator_values,

            # All analyzer results
            'analyzers': analyzer_results,

            # Market regime
            'market_regime': market_regime,

            # Complete scoring breakdown
            'score_breakdown': {
                'final_score': score.final_score,
                'base_score': score.base_score,
                'confidence': score.confidence,
                'signal_strength': score.signal_strength,

                # Individual analyzer scores
                'analyzer_scores': {
                    'trend': score.trend_score,
                    'momentum': score.momentum_score,
                    'volume': score.volume_score,
                    'pattern': score.pattern_score,
                    'sr': score.sr_score,
                    'volatility': score.volatility_score,
                    'harmonic': score.harmonic_score,
                    'channel': score.channel_score,
                    'cyclical': score.cyclical_score,
                    'htf': score.htf_score,
                },

                # Weighted scores
                'weighted_scores': {
                    'trend': score.weighted_trend,
                    'momentum': score.weighted_momentum,
                    'volume': score.weighted_volume,
                    'pattern': score.weighted_pattern,
                    'sr': score.weighted_sr,
                    'volatility': score.weighted_volatility,
                    'harmonic': score.weighted_harmonic,
                    'channel': score.weighted_channel,
                    'cyclical': score.weighted_cyclical,
                    'htf': score.weighted_htf,
                },

                # Multipliers
                'multipliers': {
                    'confluence_bonus': score.confluence_bonus,
                    'timeframe_weight': score.timeframe_weight,
                    'htf_multiplier': score.htf_multiplier,
                    'volatility_multiplier': score.volatility_multiplier,
                    'trend_alignment': score.trend_alignment,
                    'volume_confirmation': score.volume_confirmation,
                    'pattern_quality': score.pattern_quality,
                    'macd_analysis_score': score.macd_analysis_score,
                },

                # Contributing analyzers
                'contributing_analyzers': score.contributing_analyzers,
                'aligned_analyzers': score.aligned_analyzers,
            },

            # Detected patterns
            'detected_patterns': score.detected_patterns if hasattr(score, 'detected_patterns') else [],
            'pattern_contributions': score.pattern_contributions if hasattr(score, 'pattern_contributions') else {},

            # Confluence details
            'confluence_details': score.confluence_details if hasattr(score, 'confluence_details') else {},
        }

        return metadata

    def _make_serializable(self, obj: Any) -> Any:
        """
        Convert object to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            Serializable version
        """
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Convert object to dict
            return self._make_serializable(obj.__dict__)
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            # Convert to string as fallback
            return str(obj)

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get status of all systems.

        Returns:
            Dictionary with system status
        """
        return {
            'orchestrator': {
                'running': self.is_running,
                'stats': self.stats.to_dict()
            },
            'regime_detector': {
                'enabled': self.regime_detector.enabled if self.regime_detector else False
            },
            'adaptive_learning': {
                'enabled': self.adaptive_learning.enabled if self.adaptive_learning else False,
                'trade_count': len(self.adaptive_learning.trade_history) if self.adaptive_learning else 0
            },
            'correlation_manager': {
                'enabled': self.correlation_manager.enabled if self.correlation_manager else False,
                'symbols_tracked': len(self.correlation_manager.correlation_matrix) if self.correlation_manager else 0,
                'groups': len(self.correlation_manager.correlation_groups) if self.correlation_manager else 0
            },
            'circuit_breaker': (
                self.circuit_breaker.get_statistics()
                if self.circuit_breaker and self.circuit_breaker.enabled
                else {'enabled': False}
            )
        }