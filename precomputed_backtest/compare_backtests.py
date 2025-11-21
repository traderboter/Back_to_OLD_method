"""
Compare Fast Backtest vs Original Backtest Results

This script runs both backtest systems and generates a comparison report.
It helps validate that the fast_backtest produces similar results to the original.

Usage:
    python compare_backtests.py
    python compare_backtests.py --method old
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_fast_backtest(scoring_method: str = 'old') -> dict:
    """Run the fast backtest and return results"""
    from precomputed_backtest.fast_backtest import FastBacktestEngine, load_config, merge_configs

    logger.info(f"\n{'='*60}")
    logger.info("Running FAST BACKTEST...")
    logger.info(f"{'='*60}")

    # Load local configs
    local_config_path = Path(__file__).parent / 'configs' / 'config.yaml'
    local_backtest_config_path = Path(__file__).parent / 'configs' / 'config_backtest_v2.yaml'

    config = load_config(local_config_path)

    if local_backtest_config_path.exists():
        backtest_config = load_config(local_backtest_config_path)
        config = merge_configs(config, backtest_config)

    # Set scoring method
    if 'backtest' not in config:
        config['backtest'] = {}
    config['backtest']['scoring_method'] = scoring_method

    # Run backtest
    engine = FastBacktestEngine(config)
    results = engine.run()

    return {
        'name': 'Fast Backtest',
        'scoring_method': scoring_method,
        'statistics': results['statistics'],
        'trades_count': len(results.get('trades', [])),
        'duration': results.get('duration', 'N/A')
    }


async def run_original_backtest(scoring_method: str = 'old') -> dict:
    """Run the original backtest and return results"""
    from backtest.backtest_engine_v2 import run_backtest_v2

    logger.info(f"\n{'='*60}")
    logger.info("Running ORIGINAL BACKTEST...")
    logger.info(f"{'='*60}")

    try:
        engine, results_dir = await run_backtest_v2(
            config_path='config_backtest_minimal.yaml',
            main_config_path='config.yaml',
            scoring_method=scoring_method
        )

        stats = engine.results.get('statistics', {})

        return {
            'name': 'Original Backtest',
            'scoring_method': scoring_method,
            'statistics': stats,
            'trades_count': stats.get('total_trades', 0),
            'duration': str(engine.results.get('duration', 'N/A')),
            'results_dir': str(results_dir)
        }
    except Exception as e:
        logger.error(f"Error running original backtest: {e}")
        import traceback
        traceback.print_exc()
        return {
            'name': 'Original Backtest',
            'scoring_method': scoring_method,
            'error': str(e),
            'statistics': {},
            'trades_count': 0
        }


def generate_comparison_report(fast_results: dict, original_results: dict) -> str:
    """Generate a comparison report"""

    fast_stats = fast_results.get('statistics', {})
    orig_stats = original_results.get('statistics', {})

    # Helper to safely get values
    def get_stat(stats, key, default=0):
        val = stats.get(key, default)
        return val if val is not None else default

    report = f"""
# Backtest Comparison Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Fast Backtest | Original Backtest | Difference |
|--------|---------------|-------------------|------------|
| Scoring Method | {fast_results.get('scoring_method', 'N/A')} | {original_results.get('scoring_method', 'N/A')} | - |
| Total Trades | {get_stat(fast_stats, 'total_trades')} | {get_stat(orig_stats, 'total_trades')} | {get_stat(fast_stats, 'total_trades') - get_stat(orig_stats, 'total_trades')} |
| Win Rate | {get_stat(fast_stats, 'win_rate'):.1f}% | {get_stat(orig_stats, 'win_rate'):.1f}% | {get_stat(fast_stats, 'win_rate') - get_stat(orig_stats, 'win_rate'):.1f}% |
| Total Return | {get_stat(fast_stats, 'total_return'):.2f}% | {get_stat(orig_stats, 'total_return'):.2f}% | {get_stat(fast_stats, 'total_return') - get_stat(orig_stats, 'total_return'):.2f}% |
| Profit Factor | {get_stat(fast_stats, 'profit_factor'):.2f} | {get_stat(orig_stats, 'profit_factor'):.2f} | {get_stat(fast_stats, 'profit_factor') - get_stat(orig_stats, 'profit_factor'):.2f} |
| Max Drawdown | {get_stat(fast_stats, 'max_drawdown'):.2f}% | {get_stat(orig_stats, 'max_drawdown'):.2f}% | {get_stat(fast_stats, 'max_drawdown') - get_stat(orig_stats, 'max_drawdown'):.2f}% |
| Duration | {fast_results.get('duration', 'N/A')} | {original_results.get('duration', 'N/A')} | - |

## Detailed Statistics

### Fast Backtest
```
Total Trades: {get_stat(fast_stats, 'total_trades')}
Winning: {get_stat(fast_stats, 'winning_trades')} | Losing: {get_stat(fast_stats, 'losing_trades')}
Win Rate: {get_stat(fast_stats, 'win_rate'):.1f}%
Total Return: {get_stat(fast_stats, 'total_return'):.2f}%
Profit Factor: {get_stat(fast_stats, 'profit_factor'):.2f}
Max Drawdown: {get_stat(fast_stats, 'max_drawdown'):.2f}%
Avg Win: {get_stat(fast_stats, 'avg_win'):.2f} USDT
Avg Loss: {get_stat(fast_stats, 'avg_loss'):.2f} USDT
```

### Original Backtest
```
Total Trades: {get_stat(orig_stats, 'total_trades')}
Winning: {get_stat(orig_stats, 'winning_trades')} | Losing: {get_stat(orig_stats, 'losing_trades')}
Win Rate: {get_stat(orig_stats, 'win_rate'):.1f}%
Total Return: {get_stat(orig_stats, 'total_return'):.2f}%
Profit Factor: {get_stat(orig_stats, 'profit_factor'):.2f}
Max Drawdown: {get_stat(orig_stats, 'max_drawdown'):.2f}%
Avg Win: {get_stat(orig_stats, 'average_win', 0):.2f} USDT
Avg Loss: {get_stat(orig_stats, 'average_loss', 0):.2f} USDT
```

## Analysis

"""

    # Add analysis
    trades_diff = abs(get_stat(fast_stats, 'total_trades') - get_stat(orig_stats, 'total_trades'))
    winrate_diff = abs(get_stat(fast_stats, 'win_rate') - get_stat(orig_stats, 'win_rate'))
    return_diff = abs(get_stat(fast_stats, 'total_return') - get_stat(orig_stats, 'total_return'))

    if trades_diff < 50 and winrate_diff < 5 and return_diff < 10:
        report += "**Results are reasonably similar.** The fast backtest appears to be producing comparable results to the original.\n"
    else:
        report += "**Significant differences detected.** Further investigation may be needed.\n"
        report += f"\n- Trade count difference: {trades_diff} trades\n"
        report += f"- Win rate difference: {winrate_diff:.1f}%\n"
        report += f"- Return difference: {return_diff:.2f}%\n"

    # Possible reasons for differences
    report += """
## Possible Reasons for Differences

1. **Signal Generation Logic**: Fast backtest uses simplified scoring, original uses full SignalOrchestrator
2. **Multi-Timeframe**: Original analyzes 4 timeframes, fast may use different logic
3. **Data Period**: May be different start/end dates
4. **Indicator Calculation**: Pre-computed vs real-time calculation
5. **Pattern Detection**: Different pattern detection algorithms

## Recommendations

- If differences are small (<10%), fast backtest is validated
- If differences are large, investigate specific signals and trades
- Compare a sample of individual trades for exact matching
"""

    if original_results.get('error'):
        report += f"\n\n## Error in Original Backtest\n```\n{original_results.get('error')}\n```\n"

    return report


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Compare Fast vs Original Backtest')
    parser.add_argument('--method', type=str, default='old',
                        choices=['new', 'old', 'hybrid'],
                        help='Scoring method to use')
    parser.add_argument('--fast-only', action='store_true',
                        help='Run only fast backtest')
    parser.add_argument('--original-only', action='store_true',
                        help='Run only original backtest')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  BACKTEST COMPARISON TOOL")
    print("  Fast Backtest vs Original Backtest")
    print(f"  Scoring Method: {args.method.upper()}")
    print("="*70 + "\n")

    results = {}

    # Run fast backtest
    if not args.original_only:
        try:
            results['fast'] = run_fast_backtest(args.method)
        except Exception as e:
            logger.error(f"Fast backtest failed: {e}")
            results['fast'] = {'error': str(e), 'statistics': {}}

    # Run original backtest
    if not args.fast_only:
        try:
            results['original'] = await run_original_backtest(args.method)
        except Exception as e:
            logger.error(f"Original backtest failed: {e}")
            results['original'] = {'error': str(e), 'statistics': {}}

    # Generate comparison report
    if 'fast' in results and 'original' in results:
        report = generate_comparison_report(results['fast'], results['original'])

        # Save report
        report_path = Path(__file__).parent / 'reports' / f'comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {report_path}")

    # Also save raw results as JSON
    json_path = Path(__file__).parent / 'reports' / f'comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Raw results saved to: {json_path}")


if __name__ == '__main__':
    asyncio.run(main())
