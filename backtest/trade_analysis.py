"""
Trade Analysis Tool - تحلیل جزئیات معاملات backtest

این اسکریپت فایل trades.csv را می‌خواند و metadata_json را parse می‌کند
تا جزئیات کامل تحلیل (اندیکاتورها، پترن‌ها، امتیازات) را نمایش دهد.

استفاده:
    python backtest/trade_analysis.py backtest_results/v2_YYYYMMDD_HHMMSS/trades.csv
"""

import pandas as pd
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import argparse


class TradeAnalyzer:
    """
    تحلیلگر معاملات backtest با جزئیات کامل
    """

    def __init__(self, trades_csv_path: str):
        """
        Args:
            trades_csv_path: مسیر فایل trades.csv
        """
        self.trades_csv_path = Path(trades_csv_path)
        self.df = None
        self.trades_with_metadata = []

    def load_trades(self):
        """بارگذاری فایل CSV"""
        if not self.trades_csv_path.exists():
            raise FileNotFoundError(f"File not found: {self.trades_csv_path}")

        print(f"📁 Loading trades from: {self.trades_csv_path}")
        self.df = pd.read_csv(self.trades_csv_path)
        print(f"✅ Loaded {len(self.df)} trades")

        # Parse metadata_json
        if 'metadata_json' in self.df.columns:
            self._parse_metadata()
        else:
            print("⚠️  Warning: metadata_json column not found!")

    def _parse_metadata(self):
        """Parse کردن metadata_json برای هر معامله"""
        print("\n🔍 Parsing metadata...")

        for idx, row in self.df.iterrows():
            try:
                metadata = json.loads(row['metadata_json']) if pd.notna(row['metadata_json']) else {}

                trade_info = {
                    'trade_id': row['trade_id'],
                    'symbol': row['symbol'],
                    'direction': row['direction'],
                    'entry_time': row['entry_time'],
                    'exit_time': row['exit_time'],
                    'entry_price': row['entry_price'],
                    'exit_price': row['exit_price'],
                    'realized_pnl': row['realized_pnl'],
                    'exit_reason': row['exit_reason'],
                    'signal_score': row.get('signal_score', 0),
                    'timeframe': row.get('timeframe', ''),
                    'metadata': metadata
                }

                self.trades_with_metadata.append(trade_info)

            except json.JSONDecodeError as e:
                print(f"❌ Error parsing metadata for trade {idx}: {e}")

        print(f"✅ Parsed metadata for {len(self.trades_with_metadata)} trades")

    def analyze_winning_trades(self):
        """تحلیل معاملات سودده"""
        winning_trades = [t for t in self.trades_with_metadata if t['realized_pnl'] > 0]

        print(f"\n{'='*70}")
        print(f"📈 WINNING TRADES ANALYSIS ({len(winning_trades)} trades)")
        print(f"{'='*70}")

        self._analyze_trade_group(winning_trades, "WINNING")

    def analyze_losing_trades(self):
        """تحلیل معاملات ضررده"""
        losing_trades = [t for t in self.trades_with_metadata if t['realized_pnl'] < 0]

        print(f"\n{'='*70}")
        print(f"📉 LOSING TRADES ANALYSIS ({len(losing_trades)} trades)")
        print(f"{'='*70}")

        self._analyze_trade_group(losing_trades, "LOSING")

    def _analyze_trade_group(self, trades: List[Dict], group_name: str):
        """تحلیل یک گروه از معاملات"""
        if not trades:
            print(f"No {group_name} trades found.")
            return

        # آمار کلی
        total_pnl = sum(t['realized_pnl'] for t in trades)
        avg_pnl = total_pnl / len(trades)
        avg_score = sum(t['signal_score'] for t in trades) / len(trades)

        print(f"\n📊 Summary:")
        print(f"  Total Trades: {len(trades)}")
        print(f"  Total PnL: {total_pnl:.2f} USDT")
        print(f"  Average PnL: {avg_pnl:.2f} USDT")
        print(f"  Average Signal Score: {avg_score:.2f}")

        # تحلیل analyzer scores
        print(f"\n🔬 Analyzer Scores:")
        analyzer_scores = {
            'trend': [],
            'momentum': [],
            'volume': [],
            'pattern': [],
            'sr': [],
            'volatility': []
        }

        for trade in trades:
            metadata = trade['metadata']
            if 'score_breakdown' in metadata and 'analyzer_scores' in metadata['score_breakdown']:
                scores = metadata['score_breakdown']['analyzer_scores']
                for analyzer, score in scores.items():
                    if analyzer in analyzer_scores:
                        analyzer_scores[analyzer].append(score)

        for analyzer, scores in analyzer_scores.items():
            if scores:
                avg = sum(scores) / len(scores)
                print(f"  {analyzer.capitalize():15} → Avg: {avg:6.2f}")

        # تحلیل اندیکاتورها
        print(f"\n📊 Indicator Values:")
        indicators = {}

        for trade in trades:
            metadata = trade['metadata']
            if 'indicators' in metadata:
                for ind_name, ind_value in metadata['indicators'].items():
                    if ind_value is not None:
                        if ind_name not in indicators:
                            indicators[ind_name] = []
                        indicators[ind_name].append(ind_value)

        # نمایش میانگین برخی اندیکاتورهای مهم
        important_indicators = ['rsi', 'ema_20', 'ema_50', 'ema_100', 'macd', 'atr']
        for ind in important_indicators:
            if ind in indicators and indicators[ind]:
                avg = sum(indicators[ind]) / len(indicators[ind])
                print(f"  {ind.upper():15} → Avg: {avg:.2f}")

        # تحلیل پترن‌ها
        print(f"\n🎯 Detected Patterns:")
        pattern_counts = {}

        for trade in trades:
            metadata = trade['metadata']
            if 'detected_patterns' in metadata:
                for pattern in metadata['detected_patterns']:
                    pattern_name = pattern.get('name', 'Unknown')
                    if pattern_name not in pattern_counts:
                        pattern_counts[pattern_name] = 0
                    pattern_counts[pattern_name] += 1

        if pattern_counts:
            sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
            for pattern, count in sorted_patterns[:10]:  # Top 10
                percentage = (count / len(trades)) * 100
                print(f"  {pattern:30} → {count:3} trades ({percentage:.1f}%)")
        else:
            print("  No patterns detected")

        # تحلیل market regime
        print(f"\n🌍 Market Regime:")
        regime_counts = {}

        for trade in trades:
            metadata = trade['metadata']
            regime = metadata.get('market_regime', 'unknown')
            if regime not in regime_counts:
                regime_counts[regime] = 0
            regime_counts[regime] += 1

        for regime, count in sorted(regime_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(trades)) * 100
            print(f"  {regime:15} → {count:3} trades ({percentage:.1f}%)")

    def show_trade_details(self, trade_id: str = None, index: int = None):
        """نمایش جزئیات کامل یک معامله"""
        if trade_id:
            trade = next((t for t in self.trades_with_metadata if t['trade_id'] == trade_id), None)
        elif index is not None:
            if 0 <= index < len(self.trades_with_metadata):
                trade = self.trades_with_metadata[index]
            else:
                print(f"❌ Invalid index: {index}")
                return
        else:
            print("❌ Provide either trade_id or index")
            return

        if not trade:
            print(f"❌ Trade not found")
            return

        print(f"\n{'='*70}")
        print(f"📝 TRADE DETAILS: {trade['trade_id']}")
        print(f"{'='*70}")

        # Basic info
        print(f"\n📊 Basic Information:")
        print(f"  Symbol: {trade['symbol']}")
        print(f"  Direction: {trade['direction']}")
        print(f"  Timeframe: {trade['timeframe']}")
        print(f"  Entry Time: {trade['entry_time']}")
        print(f"  Exit Time: {trade['exit_time']}")
        print(f"  Entry Price: {trade['entry_price']:.2f}")
        print(f"  Exit Price: {trade['exit_price']:.2f}")
        print(f"  PnL: {trade['realized_pnl']:.2f} USDT")
        print(f"  Exit Reason: {trade['exit_reason']}")
        print(f"  Signal Score: {trade['signal_score']:.2f}")

        metadata = trade['metadata']

        # Indicators
        if 'indicators' in metadata:
            print(f"\n📈 Indicator Values at Entry:")
            indicators = metadata['indicators']
            for ind_name, ind_value in sorted(indicators.items()):
                if ind_value is not None:
                    print(f"  {ind_name:20} = {ind_value:.4f}")

        # Analyzer scores
        if 'score_breakdown' in metadata and 'analyzer_scores' in metadata['score_breakdown']:
            print(f"\n🔬 Analyzer Scores:")
            scores = metadata['score_breakdown']['analyzer_scores']
            for analyzer, score in sorted(scores.items()):
                print(f"  {analyzer:15} → {score:.2f}")

        # Weighted scores
        if 'score_breakdown' in metadata and 'weighted_scores' in metadata['score_breakdown']:
            print(f"\n⚖️  Weighted Scores:")
            weighted = metadata['score_breakdown']['weighted_scores']
            for analyzer, score in sorted(weighted.items()):
                print(f"  {analyzer:15} → {score:.2f}")

        # Multipliers
        if 'score_breakdown' in metadata and 'multipliers' in metadata['score_breakdown']:
            print(f"\n✖️  Multipliers:")
            multipliers = metadata['score_breakdown']['multipliers']
            for mult_name, mult_value in sorted(multipliers.items()):
                print(f"  {mult_name:25} → {mult_value:.4f}")

        # Detected patterns
        if 'detected_patterns' in metadata and metadata['detected_patterns']:
            print(f"\n🎯 Detected Patterns:")
            for pattern in metadata['detected_patterns']:
                print(f"  - {pattern.get('name', 'Unknown')}")
                if 'confidence' in pattern:
                    print(f"    Confidence: {pattern['confidence']:.2%}")
                if 'score' in pattern:
                    print(f"    Score: {pattern['score']:.2f}")

        # Analyzer results
        if 'analyzers' in metadata:
            print(f"\n🔍 Analyzer Results:")
            for analyzer_name, result in metadata['analyzers'].items():
                print(f"\n  {analyzer_name.upper()}:")
                self._print_dict(result, indent=4)

    def _print_dict(self, d: Dict, indent: int = 0):
        """Print dictionary به صورت خوانا"""
        prefix = " " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._print_dict(value, indent + 2)
            elif isinstance(value, list):
                print(f"{prefix}{key}: {value[:3]}..." if len(value) > 3 else f"{prefix}{key}: {value}")
            else:
                print(f"{prefix}{key}: {value}")

    def compare_winning_vs_losing(self):
        """مقایسه معاملات سودده و ضررده"""
        winning = [t for t in self.trades_with_metadata if t['realized_pnl'] > 0]
        losing = [t for t in self.trades_with_metadata if t['realized_pnl'] < 0]

        print(f"\n{'='*70}")
        print(f"⚖️  WINNING vs LOSING COMPARISON")
        print(f"{'='*70}")

        if not winning or not losing:
            print("Not enough data for comparison")
            return

        # مقایسه signal scores
        win_avg_score = sum(t['signal_score'] for t in winning) / len(winning)
        lose_avg_score = sum(t['signal_score'] for t in losing) / len(losing)

        print(f"\n📊 Signal Scores:")
        print(f"  Winning trades: {win_avg_score:.2f}")
        print(f"  Losing trades:  {lose_avg_score:.2f}")
        print(f"  Difference:     {win_avg_score - lose_avg_score:.2f}")

        # مقایسه analyzer scores
        print(f"\n🔬 Analyzer Scores Comparison:")
        analyzers = ['trend', 'momentum', 'volume', 'pattern', 'sr']

        for analyzer in analyzers:
            win_scores = []
            lose_scores = []

            for trade in winning:
                if 'score_breakdown' in trade['metadata']:
                    scores = trade['metadata']['score_breakdown'].get('analyzer_scores', {})
                    if analyzer in scores:
                        win_scores.append(scores[analyzer])

            for trade in losing:
                if 'score_breakdown' in trade['metadata']:
                    scores = trade['metadata']['score_breakdown'].get('analyzer_scores', {})
                    if analyzer in scores:
                        lose_scores.append(scores[analyzer])

            if win_scores and lose_scores:
                win_avg = sum(win_scores) / len(win_scores)
                lose_avg = sum(lose_scores) / len(lose_scores)
                diff = win_avg - lose_avg
                print(f"  {analyzer.capitalize():15} → Win: {win_avg:6.2f} | Lose: {lose_avg:6.2f} | Diff: {diff:+6.2f}")


def main():
    parser = argparse.ArgumentParser(description='Analyze backtest trades with detailed metadata')
    parser.add_argument('csv_path', help='Path to trades.csv file')
    parser.add_argument('--trade-id', help='Show details for specific trade ID')
    parser.add_argument('--index', type=int, help='Show details for trade at index')
    parser.add_argument('--winners', action='store_true', help='Analyze winning trades')
    parser.add_argument('--losers', action='store_true', help='Analyze losing trades')
    parser.add_argument('--compare', action='store_true', help='Compare winners vs losers')

    args = parser.parse_args()

    analyzer = TradeAnalyzer(args.csv_path)
    analyzer.load_trades()

    if args.trade_id:
        analyzer.show_trade_details(trade_id=args.trade_id)
    elif args.index is not None:
        analyzer.show_trade_details(index=args.index)
    elif args.winners:
        analyzer.analyze_winning_trades()
    elif args.losers:
        analyzer.analyze_losing_trades()
    elif args.compare:
        analyzer.compare_winning_vs_losing()
    else:
        # Default: show all analyses
        analyzer.analyze_winning_trades()
        analyzer.analyze_losing_trades()
        analyzer.compare_winning_vs_losing()


if __name__ == "__main__":
    main()
