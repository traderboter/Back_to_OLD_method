"""
Basic Usage Example - NEW SYSTEM

This example demonstrates how to use the NEW SYSTEM for signal generation.
"""

import asyncio
import pandas as pd
import yaml
from datetime import datetime, timezone


# Step 1: Setup (Mock implementations for demo)
# In production, you would import actual implementations
class MockMarketDataFetcher:
    """Mock market data fetcher for demo"""
    async def fetch_ohlcv(self, symbol, timeframe, limit=200):
        """Return mock OHLCV data"""
        print(f"  Fetching {symbol} {timeframe} data...")
        # In production, this would fetch real data
        dates = pd.date_range(start='2024-01-01', periods=limit, freq='1h')
        data = {
            'timestamp': dates,
            'open': [50000 + i * 10 for i in range(limit)],
            'high': [50100 + i * 10 for i in range(limit)],
            'low': [49900 + i * 10 for i in range(limit)],
            'close': [50000 + i * 10 for i in range(limit)],
            'volume': [1000 + i for i in range(limit)]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


async def example_single_timeframe():
    """Example 1: Generate signal for single timeframe"""
    print("\n" + "="*60)
    print("Example 1: Single Timeframe Signal Generation")
    print("="*60)

    # Import required modules
    from signal_generation.orchestrator import SignalOrchestrator
    from signal_generation.shared.indicator_calculator import IndicatorCalculator

    # Load configuration
    config = {
        'indicators': {
            'ema_periods': [20, 50, 100, 200],
            'sma_periods': [20, 50, 200],
            'rsi_period': 14,
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'atr_period': 14
        },
        'risk_management': {
            'min_risk_reward_ratio': 1.5,
            'preferred_risk_reward_ratio': 2.0,
            'atr_trailing_multiplier': 2.0
        },
        'signal_scoring': {
            'minimum_signal_score': 50.0
        },
        'orchestrator': {
            'enabled_analyzers': [
                'trend', 'momentum', 'volume', 'support_resistance',
                'volatility', 'harmonic', 'channel', 'cyclical', 'htf'
            ]
        }
    }

    # Initialize components
    print("\n1. Initializing components...")
    indicator_calc = IndicatorCalculator(config)
    market_fetcher = MockMarketDataFetcher()

    orchestrator = SignalOrchestrator(
        config=config,
        market_data_fetcher=market_fetcher,
        indicator_calculator=indicator_calc
    )
    print("   ✓ Orchestrator initialized")

    # Generate signal
    print("\n2. Generating signal...")
    signal = await orchestrator.generate_signal_for_symbol(
        symbol='BTCUSDT',
        timeframe='1h'
    )

    # Display result
    print("\n3. Result:")
    if signal:
        print(f"   ✅ Signal Generated!")
        print(f"   Direction: {signal.direction}")
        print(f"   Entry: {signal.entry_price:.2f}")
        print(f"   Stop Loss: {signal.stop_loss:.2f}")
        print(f"   Take Profit: {signal.take_profit:.2f}")
        print(f"   Risk/Reward: {signal.risk_reward_ratio:.2f}")
        print(f"   Score: {signal.score.final_score:.2f}")
        print(f"   SL Method: {signal.metadata.get('sl_method', 'N/A')}")
    else:
        print("   ❌ No signal generated")


async def example_multi_timeframe():
    """Example 2: Generate signal for multiple timeframes"""
    print("\n" + "="*60)
    print("Example 2: Multi-Timeframe Signal Generation")
    print("="*60)

    from signal_generation.orchestrator import SignalOrchestrator
    from signal_generation.shared.indicator_calculator import IndicatorCalculator

    # Configuration with multi-TF settings
    config = {
        'indicators': {
            'ema_periods': [20, 50, 100, 200],
            'sma_periods': [20, 50, 200],
            'rsi_period': 14,
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'atr_period': 14
        },
        'signal_processing': {
            'multi_timeframe': {
                'weights': {
                    '5m': 0.7,   # 15% importance
                    '15m': 0.85, # 20% importance
                    '1h': 1.0,   # 30% importance
                    '4h': 1.1    # 35% importance
                },
                'direction_margin': 1.3,
                'min_timeframes': 2
            }
        },
        'risk_management': {
            'min_risk_reward_ratio': 1.5,
            'preferred_risk_reward_ratio': 2.0,
            'atr_trailing_multiplier': 2.0
        },
        'orchestrator': {
            'use_multi_tf_aggregation': True
        }
    }

    # Initialize
    print("\n1. Initializing components...")
    indicator_calc = IndicatorCalculator(config)
    market_fetcher = MockMarketDataFetcher()

    orchestrator = SignalOrchestrator(
        config=config,
        market_data_fetcher=market_fetcher,
        indicator_calculator=indicator_calc
    )
    print("   ✓ Orchestrator initialized")

    # Fetch data for multiple timeframes
    print("\n2. Fetching multi-timeframe data...")
    timeframes_data = {}
    for tf in ['5m', '15m', '1h', '4h']:
        df = await market_fetcher.fetch_ohlcv('BTCUSDT', tf, 200)
        timeframes_data[tf] = df
    print(f"   ✓ Fetched {len(timeframes_data)} timeframes")

    # Generate multi-TF signal
    print("\n3. Generating multi-timeframe signal...")
    signal = await orchestrator.analyze_symbol(
        symbol='BTCUSDT',
        timeframes_data=timeframes_data
    )

    # Display result
    print("\n4. Result:")
    if signal:
        print(f"   ✅ Multi-TF Signal Generated!")
        print(f"   Direction: {signal.direction}")
        print(f"   Entry: {signal.entry_price:.2f}")
        print(f"   Stop Loss: {signal.stop_loss:.2f}")
        print(f"   Take Profit: {signal.take_profit:.2f}")
        print(f"   Risk/Reward: {signal.risk_reward_ratio:.2f}")
        print(f"   Score: {signal.score.final_score:.2f}")

        # Multi-TF specific metadata
        metadata = signal.metadata
        print(f"\n   Multi-TF Details:")
        print(f"   - Timeframes used: {metadata.get('timeframes_used', [])}")
        print(f"   - Aggregation method: {metadata.get('aggregation_method', 'N/A')}")
        print(f"   - SL Method: {metadata.get('sl_method', 'N/A')}")
        print(f"   - Confidence: {metadata.get('confidence_level', 'N/A')}")

        # Key factors
        print(f"\n   Key Factors:")
        for factor in signal.key_factors[:5]:  # Show first 5
            print(f"   - {factor}")
    else:
        print("   ❌ No signal generated")


async def example_score_breakdown():
    """Example 3: Detailed score breakdown"""
    print("\n" + "="*60)
    print("Example 3: Score Breakdown (13 Multipliers)")
    print("="*60)

    from signal_generation.signal_scorer import SignalScorer
    from signal_generation.context import AnalysisContext

    # Create mock context with analysis results
    print("\n1. Creating analysis context...")
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [50000] * 200,
        'high': [50100] * 200,
        'low': [49900] * 200,
        'close': [50000] * 200,
        'volume': [1000] * 200,
        'ema_20': [50000] * 200,
        'ema_50': [49900] * 200,
        'rsi': [55] * 200,
        'macd': [10] * 200,
        'atr': [500] * 200
    })
    df.set_index('timestamp', inplace=True)

    context = AnalysisContext('BTCUSDT', '1h', df)

    # Add analyzer results
    context.add_result('trend', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 0.8,
        'phase': 'early'
    })
    context.add_result('momentum', {
        'status': 'ok',
        'direction': 'bullish',
        'strength': 0.7,
        'momentum_strength': 1.2,
        'macd_market_type': 'A_bullish_strong'
    })
    context.add_result('volume', {
        'status': 'ok',
        'is_confirmed': True
    })
    print("   ✓ Context created with mock results")

    # Calculate score
    print("\n2. Calculating score with 13 multipliers...")
    config = {'signal_scoring': {'minimum_signal_score': 50.0}}
    scorer = SignalScorer(config)
    score = scorer.calculate_score(context, 'LONG')

    # Display breakdown
    print("\n3. Score Breakdown:")
    print(f"   Base Score: {score.base_score:.2f} (50-100)")
    print(f"   ────────────────────────────────")
    print(f"   Multipliers:")
    print(f"   1. Timeframe Weight:        {score.timeframe_weight:.2f}")
    print(f"   2. Trend Alignment:         {score.trend_alignment:.2f}")
    print(f"   3. Volume Confirmation:     {score.volume_confirmation:.2f}")
    print(f"   4. Pattern Quality:         {score.pattern_quality:.2f}")
    print(f"   5. Confluence Score:        +{score.confluence_score:.2f}")
    print(f"   6. Symbol Performance:      {score.symbol_performance_factor:.2f}")
    print(f"   7. Correlation Safety:      {score.correlation_safety_factor:.2f}")
    print(f"   8. MACD Analysis:           {score.macd_analysis_score:.2f}")
    print(f"   9. Structure Score:         {score.structure_score:.2f}")
    print(f"   10. Volatility Score:       {score.volatility_score:.2f}")
    print(f"   11. Harmonic Pattern:       {score.harmonic_pattern_score:.2f}")
    print(f"   12. Price Channel:          {score.price_channel_score:.2f}")
    print(f"   13. Cyclical Pattern:       {score.cyclical_pattern_score:.2f}")
    print(f"   ────────────────────────────────")
    print(f"   FINAL SCORE: {score.final_score:.2f}")


async def example_risk_calculation():
    """Example 4: Risk/Reward calculation with 5 methods"""
    print("\n" + "="*60)
    print("Example 4: SL/TP Calculation (5-Method Priority)")
    print("="*60)

    from signal_generation.risk_calculator import RiskRewardCalculator
    from signal_generation.context import AnalysisContext

    # Create context
    print("\n1. Creating context with indicators...")
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'close': [50000 + i*10 for i in range(200)],
        'atr': [500] * 200
    })
    df.set_index('timestamp', inplace=True)
    context = AnalysisContext('BTCUSDT', '1h', df)

    # Add analyzer results for different methods
    context.add_result('volatility', {
        'status': 'ok',
        'atr_value': 500.0,
        'recommended_stop_atr': 2.0
    })
    context.add_result('support_resistance', {
        'status': 'ok',
        'nearest_support': 49000.0,
        'nearest_resistance': 51000.0
    })
    print("   ✓ Context ready")

    # Calculate SL/TP
    print("\n2. Calculating SL/TP with priority system...")
    config = {
        'min_risk_reward_ratio': 1.5,
        'preferred_risk_reward_ratio': 2.0,
        'atr_trailing_multiplier': 2.0,
        'max_sr_distance_atr_ratio': 3.0
    }

    calculator = RiskRewardCalculator({'risk_management': config})
    entry_price = 50000.0

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=entry_price,
        context=context,
        adapted_config=config
    )

    # Display result
    print("\n3. Result:")
    print(f"   Entry Price: {entry_price:.2f}")
    print(f"   Stop Loss: {result['stop_loss']:.2f}")
    print(f"   Take Profit: {result['take_profit']:.2f}")
    print(f"   Risk/Reward: {result['risk_reward_ratio']:.2f}")
    print(f"   Method Used: {result['sl_method']}")
    print(f"\n   Priority Methods Tried:")
    print(f"   1. Harmonic Pattern → (not available)")
    print(f"   2. Price Channel → (not available)")
    print(f"   3. Support/Resistance → (available but > 3×ATR)")
    print(f"   4. ATR-based → ✓ USED")


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "NEW SYSTEM - USAGE EXAMPLES" + " "*15 + "║")
    print("╚" + "="*58 + "╝")

    # Run examples
    await example_single_timeframe()
    await example_multi_timeframe()
    await example_score_breakdown()
    await example_risk_calculation()

    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("✓ Example 1: Single timeframe signal generation")
    print("✓ Example 2: Multi-timeframe signal generation")
    print("✓ Example 3: Score breakdown (13 multipliers)")
    print("✓ Example 4: SL/TP calculation (5 methods)")
    print("\nFor more details, see:")
    print("- README_NEW_SYSTEM.md")
    print("- docs/MIGRATION_GUIDE.md")
    print("- docs/IMPLEMENTATION_SUMMARY.md")
    print("="*60 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
