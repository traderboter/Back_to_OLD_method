#!/usr/bin/env python3
"""
Per-Timeframe Backtest Analyzer
================================

تحلیلگر پیشرفته برای بررسی عملکرد patterns و indicators در تایم‌فریم‌های مختلف.

ویژگی‌ها:
1. تحلیل per-timeframe برای هر pattern
2. شناسایی patterns که در یک TF مفید و در TF دیگر مضر هستند
3. تولید توصیه‌های دقیق برای config.yaml
4. محاسبه win rate, avg profit, count برای هر pattern در هر TF

استفاده:
    python per_timeframe_analyzer.py <trades.csv>
"""

import csv
import json
import sys
from collections import defaultdict
from typing import Dict, List, Tuple
import argparse
import yaml
from pathlib import Path
import re
from datetime import datetime


class PerTimeframeAnalyzer:
    """تحلیلگر per-timeframe برای نتایج بک‌تست."""

    def __init__(self, csv_file: str):
        """
        Initialize analyzer.

        Args:
            csv_file: Path to trades.csv
        """
        self.csv_file = csv_file

        # Data storage: pattern_name -> timeframe -> stats
        self.pattern_stats = defaultdict(lambda: defaultdict(lambda: {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'profit_sum': 0.0,
            'trades': []
        }))

        # Analyzer stats: analyzer_name -> timeframe -> stats
        self.analyzer_stats = defaultdict(lambda: defaultdict(lambda: {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'profit_sum': 0.0
        }))

        self.trades = []

        # Load pattern scores from config.yaml
        self.pattern_scores = self._load_pattern_scores_from_config()

    def load_trades(self):
        """بارگذاری معاملات از CSV."""
        print(f"📂 Loading trades from {self.csv_file}...")

        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Calculate result from realized_pnl
                    realized_pnl = float(row['realized_pnl'])
                    result = 'win' if realized_pnl > 0 else 'loss'

                    trade = {
                        'symbol': row['symbol'],
                        'direction': row['direction'],
                        'entry_price': float(row['entry_price']),
                        'exit_price': float(row['exit_price']),
                        'pnl': realized_pnl,
                        'result': result,
                        'exit_reason': row['exit_reason'],
                        'metadata': json.loads(row['metadata_json'])
                    }
                    self.trades.append(trade)
                except Exception as e:
                    print(f"⚠️ Error parsing trade: {e}")
                    continue

        print(f"✅ Loaded {len(self.trades)} trades")

    def analyze_patterns_per_timeframe(self):
        """تحلیل patterns در هر تایم‌فریم."""
        print("\n🔍 Analyzing patterns per timeframe...")

        for trade in self.trades:
            is_win = trade['result'] == 'win'
            pnl = trade['pnl']

            # Extract patterns from each timeframe
            timeframes_data = trade['metadata'].get('timeframes', {})

            for tf, tf_data in timeframes_data.items():
                analyzers = tf_data.get('analyzers', {})
                patterns_data = analyzers.get('patterns', {})

                # Candlestick patterns
                candlestick_patterns = patterns_data.get('candlestick_patterns', [])
                for pattern in candlestick_patterns:
                    pattern_name = pattern.get('name', 'Unknown')
                    pattern_tf = pattern.get('timeframe', tf)  # Use pattern's TF or fallback

                    stats = self.pattern_stats[pattern_name][pattern_tf]
                    stats['total'] += 1
                    stats['profit_sum'] += pnl
                    stats['trades'].append({
                        'pnl': pnl,
                        'is_win': is_win,
                        'direction': pattern.get('direction'),
                        'strength': pattern.get('adjusted_strength')
                    })

                    if is_win:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1

                # Chart patterns
                chart_patterns = patterns_data.get('chart_patterns', [])
                for pattern in chart_patterns:
                    pattern_name = pattern.get('name', 'Unknown')
                    pattern_tf = pattern.get('timeframe', tf)

                    stats = self.pattern_stats[pattern_name][pattern_tf]
                    stats['total'] += 1
                    stats['profit_sum'] += pnl
                    stats['trades'].append({
                        'pnl': pnl,
                        'is_win': is_win,
                        'direction': pattern.get('direction'),
                        'strength': pattern.get('adjusted_strength')
                    })

                    if is_win:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1

        print(f"✅ Analyzed {len(self.pattern_stats)} unique patterns")

    def generate_report(self):
        """تولید گزارش کامل."""
        print("\n" + "="*80)
        print("📊 PER-TIMEFRAME PATTERN ANALYSIS REPORT")
        print("="*80)

        # Sort patterns by total trades
        sorted_patterns = sorted(
            self.pattern_stats.items(),
            key=lambda x: sum(tf_stats['total'] for tf_stats in x[1].values()),
            reverse=True
        )

        for pattern_name, tf_stats in sorted_patterns:
            print(f"\n{'='*80}")
            print(f"🎯 Pattern: {pattern_name}")
            print(f"{'='*80}")

            # Sort timeframes by total trades
            sorted_tfs = sorted(
                tf_stats.items(),
                key=lambda x: x[1]['total'],
                reverse=True
            )

            for tf, stats in sorted_tfs:
                total = stats['total']
                if total == 0:
                    continue

                wins = stats['wins']
                losses = stats['losses']
                win_rate = (wins / total * 100) if total > 0 else 0
                avg_profit = stats['profit_sum'] / total if total > 0 else 0

                # Determine if good or bad
                status = "✅ GOOD" if win_rate > 55 and avg_profit > 0 else \
                         "⚠️ NEUTRAL" if win_rate >= 45 and win_rate <= 55 else \
                         "❌ BAD"

                print(f"\n  📅 Timeframe: {tf} {status}")
                print(f"     Total trades: {total}")
                print(f"     Win rate: {win_rate:.1f}% ({wins}W / {losses}L)")
                print(f"     Avg profit: {avg_profit:+.2f} USDT")
                print(f"     Total profit: {stats['profit_sum']:+.2f} USDT")

    def generate_config_recommendations(self):
        """تولید توصیه‌های تنظیم config.yaml."""
        print("\n" + "="*80)
        print("💡 CONFIG.YAML RECOMMENDATIONS")
        print("="*80)
        print("\n📖 How to read the recommendations:")
        print("   • 'Current: X → New: Y (Z%)' shows the score change")
        print("   • 'New' value is the FINAL recommended score (not additional change)")
        print("   • Copy the 'New' values directly to your config.yaml")
        print("   • WR = Win Rate, Avg = Average Profit, N = Number of trades")

        recommendations = []

        for pattern_name, tf_stats in self.pattern_stats.items():
            pattern_rec = {
                'pattern': pattern_name,
                'timeframes': {}
            }

            for tf, stats in tf_stats.items():
                total = stats['total']
                if total < 3:  # Skip patterns with < 3 occurrences
                    continue

                win_rate = (stats['wins'] / total * 100) if total > 0 else 0
                avg_profit = stats['profit_sum'] / total if total > 0 else 0

                # Current score from config (we'll need to read this)
                current_score = self._get_current_score(pattern_name, tf)

                # Calculate recommended score
                if win_rate > 70 and avg_profit > 1.5:
                    # Excellent: increase by 50%
                    recommended = current_score * 1.5 if current_score else 2.5
                    action = "⬆️ INCREASE +50%"
                elif win_rate > 60 and avg_profit > 0.5:
                    # Good: increase by 25%
                    recommended = current_score * 1.25 if current_score else 1.5
                    action = "⬆️ INCREASE +25%"
                elif win_rate < 40 or avg_profit < -0.5:
                    # Bad: decrease by 50%
                    recommended = current_score * 0.5 if current_score else 0.2
                    action = "⬇️ DECREASE -50%"
                elif win_rate < 45 or avg_profit < 0:
                    # Poor: decrease by 25%
                    recommended = current_score * 0.75 if current_score else 0.5
                    action = "⬇️ DECREASE -25%"
                else:
                    # Neutral: keep same
                    recommended = current_score if current_score else 1.0
                    action = "➡️ KEEP SAME"

                pattern_rec['timeframes'][tf] = {
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'total': total,
                    'current_score': current_score,
                    'recommended': round(recommended, 2),
                    'action': action
                }

            if pattern_rec['timeframes']:
                recommendations.append(pattern_rec)

        # Print recommendations
        print("\n📝 Recommended changes to config.yaml:\n")
        print("```yaml")
        print("pattern_scores:")

        for rec in recommendations:
            pattern_name = rec['pattern']
            tfs = rec['timeframes']

            # Convert pattern name to config format
            config_name = self._to_config_name(pattern_name)

            print(f"  '{pattern_name}':  # Config key: {config_name}")

            for tf in ['5m', '15m', '1h', '4h']:
                if tf in tfs:
                    info = tfs[tf]
                    current = info['current_score']
                    recommended = info['recommended']

                    # Calculate change percentage
                    if current > 0:
                        change_pct = ((recommended - current) / current) * 100
                        change_str = f"{change_pct:+.0f}%"
                    else:
                        change_str = "N/A"

                    print(f"    {tf}: {recommended}  # "
                          f"Current: {current} → New: {recommended} ({change_str}) | "
                          f"{info['action']} | "
                          f"WR: {info['win_rate']:.1f}%, "
                          f"Avg: {info['avg_profit']:+.2f} USDT, "
                          f"N: {info['total']}")
                else:
                    print(f"    {tf}: 1.0  # No data")
            print()

        print("```")

        # Return recommendations for potential auto-apply
        return recommendations

    def _load_pattern_scores_from_config(self) -> Dict:
        """
        Load pattern_scores from config.yaml.

        Returns:
            Dictionary of pattern_name -> timeframe -> score
        """
        # Find config.yaml in project root (parent of backtest folder)
        csv_path = Path(self.csv_file)
        project_root = csv_path.parent.parent if csv_path.parent.name.startswith('backtest') else csv_path.parent
        config_path = project_root / 'config.yaml'

        if not config_path.exists():
            # Try current directory
            config_path = Path('config.yaml')
            if not config_path.exists():
                # Try parent directory
                config_path = Path('../config.yaml')
                if not config_path.exists():
                    print("⚠️ Warning: config.yaml not found. Using default scores.")
                    return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            pattern_scores = config.get('pattern_scores', {})
            print(f"✅ Loaded pattern scores from: {config_path}")
            print(f"   Found {len(pattern_scores)} patterns in config")
            return pattern_scores

        except Exception as e:
            print(f"⚠️ Warning: Failed to load config.yaml: {e}")
            print("   Using default scores.")
            return {}

    def _get_current_score(self, pattern_name: str, timeframe: str) -> float:
        """
        Get current score from config.yaml.

        Args:
            pattern_name: Pattern name (e.g., "Hammer", "Engulfing")
            timeframe: Timeframe (e.g., "5m", "15m", "1h", "4h")

        Returns:
            Current score from config, or default 1.0
        """
        # Convert pattern name to possible config keys
        possible_keys = [
            pattern_name,  # As is: "Hammer"
            pattern_name.lower(),  # Lowercase: "hammer"
            pattern_name.lower().replace(' ', '_'),  # Underscore: "head_and_shoulders"
            pattern_name.replace(' ', '_'),  # Keep case: "Head_and_Shoulders"
        ]

        # Try to find the pattern in config
        for key in possible_keys:
            if key in self.pattern_scores:
                tf_scores = self.pattern_scores[key]
                if isinstance(tf_scores, dict) and timeframe in tf_scores:
                    return float(tf_scores[timeframe])

        # Default scores if not found
        defaults = {
            '5m': 0.7,
            '15m': 0.9,
            '1h': 1.1,
            '4h': 1.4
        }
        return defaults.get(timeframe, 1.0)

    def _to_config_name(self, pattern_name: str) -> str:
        """Convert pattern name to config format."""
        # This is a simple conversion - adjust as needed
        return pattern_name.lower().replace(' ', '_').replace('&', 'and')

    def apply_recommendations_to_config(self, recommendations: List[Dict]) -> bool:
        """
        Apply recommended changes to config.yaml.

        Args:
            recommendations: List of recommendation dictionaries

        Returns:
            True if successful, False otherwise
        """
        # Find config.yaml
        csv_path = Path(self.csv_file)
        project_root = csv_path.parent.parent if csv_path.parent.name.startswith('backtest') else csv_path.parent
        config_path = project_root / 'config.yaml'

        if not config_path.exists():
            config_path = Path('config.yaml')
            if not config_path.exists():
                print("❌ Error: config.yaml not found!")
                return False

        try:
            # Create backup
            backup_path = config_path.parent / f"config.yaml.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            print(f"✅ Backup created: {backup_path}")

            # Update pattern scores in config content
            lines = config_content.split('\n')
            updated_lines = []
            current_pattern = None
            in_pattern_scores = False

            # Build a lookup dict for easy access
            rec_dict = {}
            for rec in recommendations:
                pattern_name = rec['pattern']
                # Try multiple key formats
                possible_keys = [
                    pattern_name,
                    pattern_name.lower(),
                    pattern_name.lower().replace(' ', '_'),
                    pattern_name.replace(' ', '_')
                ]
                for key in possible_keys:
                    rec_dict[key] = rec['timeframes']

            i = 0
            while i < len(lines):
                line = lines[i]

                # Check if we're in pattern_scores section
                if line.strip().startswith('pattern_scores:'):
                    in_pattern_scores = True
                    updated_lines.append(line)
                    i += 1
                    continue

                # Check if we're exiting pattern_scores (reached a top-level key)
                if in_pattern_scores and line and not line.startswith(' ') and not line.startswith('#'):
                    in_pattern_scores = False

                if in_pattern_scores:
                    # Check if this line defines a pattern (e.g., "  hammer:" or "  'Hammer':" or "  'Double Top/Bottom':")
                    pattern_match = re.match(r"^(\s+)(['\"]?)([^'\":]+?)(['\"]?):\s*(#.*)?$", line)
                    if pattern_match and pattern_match.group(1) == '  ':  # Two spaces = top-level pattern
                        indent = pattern_match.group(1)
                        pattern_key = pattern_match.group(3).strip()
                        current_pattern = pattern_key
                        updated_lines.append(line)
                        i += 1
                        continue

                    # Check if this line is a timeframe score (e.g., "    5m: 0.8")
                    tf_match = re.match(r"^(\s+)(5m|15m|1h|4h):\s*([0-9.]+)(.*)$", line)
                    if tf_match and current_pattern:
                        indent = tf_match.group(1)
                        tf = tf_match.group(2)
                        old_value = tf_match.group(3)
                        comment_part = tf_match.group(4)

                        # Check if we have a recommendation for this pattern+tf
                        updated = False
                        for pattern_key, tf_data in rec_dict.items():
                            if pattern_key.lower() == current_pattern.lower():
                                if tf in tf_data:
                                    new_value = tf_data[tf]['recommended']
                                    # Replace the line with new value
                                    updated_lines.append(f"{indent}{tf}: {new_value}{comment_part}")
                                    updated = True
                                    break

                        if not updated:
                            updated_lines.append(line)
                        i += 1
                        continue

                updated_lines.append(line)
                i += 1

            # Write updated config
            updated_content = '\n'.join(updated_lines)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            print(f"✅ Config updated successfully: {config_path}")
            return True

        except Exception as e:
            print(f"❌ Error updating config.yaml: {e}")
            return False

    def find_problematic_patterns(self):
        """پیدا کردن patterns که در یک TF خوب و در TF دیگر بد هستند."""
        print("\n" + "="*80)
        print("⚠️ TIMEFRAME CONFLICTS - Patterns with inconsistent performance")
        print("="*80)

        conflicts = []

        for pattern_name, tf_stats in self.pattern_stats.items():
            if len(tf_stats) < 2:  # Need at least 2 timeframes
                continue

            tf_performances = {}
            for tf, stats in tf_stats.items():
                total = stats['total']
                if total < 3:
                    continue

                win_rate = (stats['wins'] / total * 100) if total > 0 else 0
                avg_profit = stats['profit_sum'] / total if total > 0 else 0

                # Classify as good, neutral, bad
                if win_rate > 60 and avg_profit > 0.5:
                    performance = 'good'
                elif win_rate < 40 or avg_profit < -0.5:
                    performance = 'bad'
                else:
                    performance = 'neutral'

                tf_performances[tf] = {
                    'performance': performance,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'total': total
                }

            # Check for conflicts
            has_good = any(p['performance'] == 'good' for p in tf_performances.values())
            has_bad = any(p['performance'] == 'bad' for p in tf_performances.values())

            if has_good and has_bad:
                conflicts.append({
                    'pattern': pattern_name,
                    'timeframes': tf_performances
                })

        if conflicts:
            print("\n🔍 Found patterns with conflicting performance across timeframes:\n")

            for conflict in conflicts:
                print(f"⚠️ {conflict['pattern']}:")
                for tf, perf in conflict['timeframes'].items():
                    emoji = "✅" if perf['performance'] == 'good' else \
                            "❌" if perf['performance'] == 'bad' else "⚠️"
                    print(f"   {emoji} {tf}: {perf['performance'].upper()} "
                          f"(WR: {perf['win_rate']:.1f}%, "
                          f"Avg: {perf['avg_profit']:+.2f} USDT, "
                          f"N: {perf['total']})")
                print()
        else:
            print("\n✅ No major conflicts found - patterns are consistent across timeframes")

    def run(self, auto_apply: bool = False, prompt_apply: bool = True):
        """
        اجرای کامل تحلیل.

        Args:
            auto_apply: If True, automatically apply recommendations without prompting
            prompt_apply: If False, skip the apply prompt
        """
        self.load_trades()
        self.analyze_patterns_per_timeframe()
        self.generate_report()
        self.find_problematic_patterns()
        recommendations = self.generate_config_recommendations()

        # Skip prompt if requested
        if not prompt_apply:
            print("\n💡 Use the recommended values above to manually update your config.yaml")
            return

        # Ask user if they want to apply changes
        if recommendations:
            print("\n" + "="*80)
            print("🔧 AUTO-APPLY RECOMMENDATIONS")
            print("="*80)
            print("\n⚠️  Warning: This will modify your config.yaml file!")
            print("   A backup will be created automatically.")

            if auto_apply:
                print("\n⚡ Auto-apply mode enabled - applying recommendations automatically...")
                success = self.apply_recommendations_to_config(recommendations)

                if success:
                    print("\n✅ All recommendations applied successfully!")
                    print("💡 You can now run a new backtest with the updated scores.")
                else:
                    print("\n❌ Failed to apply recommendations.")
                return

            while True:
                try:
                    response = input("\n❓ Do you want to apply these recommendations to config.yaml? (y/n): ").strip().lower()

                    if response == 'y':
                        print("\n🔄 Applying recommendations...")
                        success = self.apply_recommendations_to_config(recommendations)

                        if success:
                            print("\n✅ All recommendations applied successfully!")
                            print("💡 You can now run a new backtest with the updated scores.")
                        else:
                            print("\n❌ Failed to apply recommendations.")
                        break

                    elif response == 'n':
                        print("\n❌ No changes applied to config.yaml")
                        print("💡 You can manually copy the recommended values from above.")
                        break

                    else:
                        print("⚠️  Please enter 'y' or 'n'")

                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
                    break
                except EOFError:
                    print("\n\n❌ No input received.")
                    break
        else:
            print("\n⚠️  No recommendations to apply (all patterns have insufficient data).")


def main():
    parser = argparse.ArgumentParser(
        description='تحلیل per-timeframe نتایج بک‌تست'
    )
    parser.add_argument(
        'csv_file',
        help='مسیر به فایل trades.csv'
    )
    parser.add_argument(
        '--auto-apply',
        action='store_true',
        help='Auto-apply recommendations without prompting (use with caution!)'
    )
    parser.add_argument(
        '--no-prompt',
        action='store_true',
        help='Skip the apply prompt (just show recommendations)'
    )

    args = parser.parse_args()

    analyzer = PerTimeframeAnalyzer(args.csv_file)

    # Pass flags to run method
    if args.auto_apply:
        analyzer.run(auto_apply=True)
    elif args.no_prompt:
        analyzer.run(prompt_apply=False)
    else:
        analyzer.run()


if __name__ == '__main__':
    main()
