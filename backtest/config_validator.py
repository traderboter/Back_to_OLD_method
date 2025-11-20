#!/usr/bin/env python3
"""
Config Validator - Backtest Score Verification
===============================================

تأیید اینکه کد واقعاً از امتیازات تعریف شده در config.yaml استفاده می‌کند.

این ابزار:
1. امتیازات استفاده شده در معاملات را از metadata استخراج می‌کند
2. با امتیازات config.yaml مقایسه می‌کند
3. هرگونه mismatch یا باگ را گزارش می‌دهد

استفاده:
    python config_validator.py <trades.csv> <config.yaml>
"""

import csv
import json
import sys
import yaml
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import argparse


class ConfigValidator:
    """تأیید استفاده صحیح از امتیازات config در بک‌تست."""

    def __init__(self, csv_file: str, config_file: str):
        """
        Initialize validator.

        Args:
            csv_file: Path to trades.csv
            config_file: Path to config.yaml
        """
        self.csv_file = csv_file
        self.config_file = config_file

        # Load config
        self.config = self._load_config()
        self.pattern_scores = self.config.get('pattern_scores', {})

        # Storage for actual scores used
        # pattern_name -> timeframe -> list of actual scores
        self.actual_scores = defaultdict(lambda: defaultdict(list))

        # Mismatches found
        self.mismatches = []

        # Detected backtest method (NEW or OLD)
        self.method_type = None

    def _load_config(self) -> Dict:
        """بارگذاری config.yaml."""
        print(f"📂 Loading config from {self.config_file}...")
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✅ Loaded config with {len(config.get('pattern_scores', {}))} pattern scores")
            return config
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            sys.exit(1)

    def extract_scores_from_trades(self):
        """استخراج امتیازات واقعی از metadata معاملات."""
        print(f"\n📂 Loading trades from {self.csv_file}...")

        trade_count = 0
        pattern_count = 0

        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    trade_count += 1
                    metadata = json.loads(row['metadata_json'])

                    # تشخیص روش: NEW یا OLD
                    if 'detected_patterns' in metadata:
                        # روش جدید (NEW method)
                        if self.method_type is None:
                            self.method_type = 'NEW'
                            self._print_method_header()

                        detected_patterns = metadata.get('detected_patterns', [])
                        for pattern in detected_patterns:
                            pattern_name = pattern.get('name', 'Unknown')
                            pattern_tf = pattern.get('timeframe', 'unknown')
                            base_score = pattern.get('base_score', 0.0)

                            self.actual_scores[pattern_name][pattern_tf].append(base_score)
                            pattern_count += 1

                    elif 'timeframes' in metadata:
                        # روش قدیم (OLD method - Multi-TF Aggregation)
                        if self.method_type is None:
                            self.method_type = 'OLD'
                            self._print_method_header()

                        timeframes_data = metadata.get('timeframes', {})

                        for tf, tf_data in timeframes_data.items():
                            analyzers = tf_data.get('analyzers', {})
                            patterns_data = analyzers.get('patterns', {})

                            # Candlestick patterns
                            candlestick_patterns = patterns_data.get('candlestick_patterns', [])
                            for pattern in candlestick_patterns:
                                pattern_name = pattern.get('name', 'Unknown')
                                pattern_tf = pattern.get('timeframe', tf)
                                base_score = pattern.get('base_score', 0.0)

                                self.actual_scores[pattern_name][pattern_tf].append(base_score)
                                pattern_count += 1

                            # Chart patterns
                            chart_patterns = patterns_data.get('chart_patterns', [])
                            for pattern in chart_patterns:
                                pattern_name = pattern.get('name', 'Unknown')
                                pattern_tf = pattern.get('timeframe', tf)
                                base_score = pattern.get('base_score', 0.0)

                                self.actual_scores[pattern_name][pattern_tf].append(base_score)
                                pattern_count += 1
                    else:
                        if trade_count == 1:
                            print(f"⚠️ Unknown metadata structure - cannot detect method")

                except Exception as e:
                    print(f"⚠️ Error parsing trade: {e}")
                    continue

        print(f"✅ Loaded {trade_count} trades")
        print(f"✅ Extracted {pattern_count} pattern instances from {len(self.actual_scores)} unique patterns")

    def validate_scores(self):
        """مقایسه امتیازات واقعی با config."""
        print("\n🔍 Validating scores against config.yaml...")

        total_checks = 0
        mismatches_found = 0

        for pattern_name, tf_scores in self.actual_scores.items():
            # Get expected scores from config
            expected_scores = self._get_expected_scores(pattern_name)

            if not expected_scores:
                print(f"\n⚠️ Pattern '{pattern_name}' not found in config.yaml!")
                self.mismatches.append({
                    'pattern': pattern_name,
                    'type': 'missing_in_config',
                    'message': f"Pattern '{pattern_name}' used in backtest but not defined in config"
                })
                continue

            # Check each timeframe
            for tf, actual_score_list in tf_scores.items():
                total_checks += 1

                # Get most common actual score
                if actual_score_list:
                    actual_score = round(sum(actual_score_list) / len(actual_score_list), 4)
                    min_score = round(min(actual_score_list), 4)
                    max_score = round(max(actual_score_list), 4)
                else:
                    continue

                # Get expected score
                expected_score = expected_scores.get(tf)

                if expected_score is None:
                    print(f"\n⚠️ {pattern_name} [{tf}]: No expected score in config")
                    self.mismatches.append({
                        'pattern': pattern_name,
                        'timeframe': tf,
                        'type': 'missing_timeframe',
                        'actual': actual_score,
                        'expected': None,
                        'message': f"Timeframe '{tf}' not defined in config for '{pattern_name}'"
                    })
                    mismatches_found += 1
                    continue

                # Compare (allow small floating point differences)
                tolerance = 0.01
                if abs(actual_score - expected_score) > tolerance:
                    print(f"\n❌ MISMATCH: {pattern_name} [{tf}]")
                    print(f"   Expected: {expected_score}")
                    print(f"   Actual (avg): {actual_score}")
                    print(f"   Actual (min-max): {min_score} - {max_score}")
                    print(f"   Occurrences: {len(actual_score_list)}")

                    self.mismatches.append({
                        'pattern': pattern_name,
                        'timeframe': tf,
                        'type': 'score_mismatch',
                        'expected': expected_score,
                        'actual': actual_score,
                        'actual_min': min_score,
                        'actual_max': max_score,
                        'count': len(actual_score_list),
                        'message': f"Score mismatch: expected {expected_score}, got {actual_score}"
                    })
                    mismatches_found += 1

        print(f"\n📊 Validation Summary:")
        print(f"   Total checks: {total_checks}")
        print(f"   Mismatches found: {mismatches_found}")
        if total_checks > 0:
            print(f"   Success rate: {((total_checks - mismatches_found) / total_checks * 100):.1f}%")
        else:
            print(f"   ⚠️ No patterns found to validate!")

    def _get_expected_scores(self, pattern_name: str) -> Dict[str, float]:
        """
        دریافت امتیازات مورد انتظار از config.

        Args:
            pattern_name: نام pattern (مثل "Hammer" یا "Head and Shoulders")

        Returns:
            Dict mapping timeframe -> score
        """
        # Try exact match first
        if pattern_name in self.pattern_scores:
            return self.pattern_scores[pattern_name]

        # Try case-insensitive and normalized match
        pattern_name_lower = pattern_name.lower()
        for config_pattern, scores in self.pattern_scores.items():
            if config_pattern.lower() == pattern_name_lower:
                return scores

        # Try with common variations
        variations = [
            pattern_name.replace(' ', '_').lower(),
            pattern_name.replace('_', ' ').title(),
            pattern_name.replace(' ', '').lower()
        ]

        for config_pattern, scores in self.pattern_scores.items():
            config_lower = config_pattern.lower()
            if any(var == config_lower for var in variations):
                return scores

        return {}

    def _print_method_header(self):
        """نمایش header برای متد تشخیص داده شده."""
        print("\n" + "=" * 80)
        print("⚙️  BACKTEST METHOD DETECTION")
        print("=" * 80)

        if self.method_type == 'NEW':
            print("📊 Detected Method: NEW (Best Signal Selection)")
            print("   • Strategy: Select best timeframe signal")
            print("   • Analyzers: 8 simple analyzers")
            print("   • Score limit: max_final_score = 300")
            print("   • Thresholds: min=60, strong>150")
        elif self.method_type == 'OLD':
            print("📊 Detected Method: OLD (Multi-TF Aggregation)")
            print("   • Strategy: Aggregate all timeframe signals")
            print("   • Multipliers: 13 additional coefficients")
            print("   • Score limit: max_final_score = 0 (unlimited)")
            print("   • Thresholds: min=200, strong>500")
        else:
            print("📊 Detected Method: UNKNOWN")

        print("=" * 80)

    def generate_detailed_report(self):
        """تولید گزارش جزئیات کامل."""
        print("\n" + "="*80)
        print("📋 DETAILED VALIDATION REPORT")
        print("="*80)

        if not self.mismatches:
            print("\n✅ SUCCESS! All pattern scores match config.yaml")
            print("   کد به درستی از امتیازات config استفاده می‌کند.")
            return

        print(f"\n❌ Found {len(self.mismatches)} issues:\n")

        # Group by type
        by_type = defaultdict(list)
        for mismatch in self.mismatches:
            by_type[mismatch['type']].append(mismatch)

        # Missing in config
        if 'missing_in_config' in by_type:
            print("🔴 Patterns used but NOT defined in config.yaml:")
            print("="*80)
            for m in by_type['missing_in_config']:
                print(f"   • {m['pattern']}")
            print()

        # Score mismatches
        if 'score_mismatch' in by_type:
            print("🔴 Score mismatches (کد از امتیاز اشتباه استفاده می‌کند):")
            print("="*80)
            for m in by_type['score_mismatch']:
                print(f"\n   Pattern: {m['pattern']}")
                print(f"   Timeframe: {m['timeframe']}")
                print(f"   Expected (config): {m['expected']}")
                print(f"   Actual (used): {m['actual']}")
                print(f"   Difference: {abs(m['expected'] - m['actual']):.4f}")
                print(f"   Occurrences: {m['count']}")
            print()

        # Missing timeframes
        if 'missing_timeframe' in by_type:
            print("⚠️ Timeframes used but not defined in config:")
            print("="*80)
            for m in by_type['missing_timeframe']:
                print(f"   • {m['pattern']} [{m['timeframe']}]: actual score = {m['actual']}")
            print()

    def generate_summary_table(self):
        """تولید جدول خلاصه برای مقایسه سریع."""
        print("\n" + "="*80)
        print("📊 PATTERN SCORE COMPARISON TABLE")
        print("="*80)
        print()

        # Sort patterns alphabetically
        sorted_patterns = sorted(self.actual_scores.items())

        for pattern_name, tf_scores in sorted_patterns:
            expected_scores = self._get_expected_scores(pattern_name)

            if not expected_scores:
                print(f"⚠️ {pattern_name}: NOT IN CONFIG")
                continue

            print(f"📌 {pattern_name}:")

            # Show all 4 timeframes
            for tf in ['5m', '15m', '1h', '4h']:
                expected = expected_scores.get(tf)
                actual_list = tf_scores.get(tf, [])

                if actual_list:
                    actual = round(sum(actual_list) / len(actual_list), 4)
                    count = len(actual_list)

                    if expected is None:
                        print(f"   {tf}: ⚠️ NOT IN CONFIG (actual: {actual}, n={count})")
                    elif abs(actual - expected) < 0.01:
                        print(f"   {tf}: ✅ {expected} (verified, n={count})")
                    else:
                        print(f"   {tf}: ❌ Expected {expected}, Got {actual} (n={count})")
                else:
                    if expected is not None:
                        print(f"   {tf}: ➖ Config: {expected} (not used in backtest)")

            print()

    def check_pattern_name_consistency(self):
        """بررسی consistency نام‌های patterns."""
        print("\n" + "="*80)
        print("🔍 PATTERN NAME CONSISTENCY CHECK")
        print("="*80)

        print("\nPatterns used in backtest:")
        for i, pattern_name in enumerate(sorted(self.actual_scores.keys()), 1):
            in_config = pattern_name in self.pattern_scores or \
                       self._get_expected_scores(pattern_name) != {}

            status = "✅" if in_config else "❌"
            print(f"   {i:2d}. {status} {pattern_name}")

        print(f"\nPatterns defined in config.yaml:")
        for i, pattern_name in enumerate(sorted(self.pattern_scores.keys()), 1):
            used = pattern_name in self.actual_scores

            status = "✅" if used else "⚠️"
            note = "" if used else " (not used in backtest)"
            print(f"   {i:2d}. {status} {pattern_name}{note}")

    def run(self):
        """اجرای کامل validation."""
        self.extract_scores_from_trades()
        self.validate_scores()
        self.generate_detailed_report()
        self.generate_summary_table()
        self.check_pattern_name_consistency()

        # Return exit code
        if self.mismatches:
            print("\n" + "="*80)
            print("❌ VALIDATION FAILED")
            print(f"Found {len(self.mismatches)} issues that need attention.")
            if self.method_type:
                print(f"Backtest Method: {self.method_type}")
            print("="*80)
            return 1
        else:
            print("\n" + "="*80)
            print("✅ VALIDATION PASSED")
            print("All pattern scores match config.yaml correctly!")
            if self.method_type:
                print(f"Backtest Method: {self.method_type}")
            print("="*80)
            return 0


def main():
    parser = argparse.ArgumentParser(
        description='تأیید استفاده صحیح از امتیازات config در بک‌تست'
    )
    parser.add_argument(
        'csv_file',
        help='مسیر به فایل trades.csv'
    )
    parser.add_argument(
        'config_file',
        nargs='?',
        default='config.yaml',
        help='مسیر به فایل config.yaml (پیش‌فرض: config.yaml)'
    )

    args = parser.parse_args()

    validator = ConfigValidator(args.csv_file, args.config_file)
    exit_code = validator.run()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
