#!/usr/bin/env python3
"""
اسکریپت تشخیص روش Backtest (OLD vs NEW)

استفاده:
  python backtest/check_backtest_method.py v2_20251120_002427
  python backtest/check_backtest_method.py v2_20251120_002407

یا بدون آرگومان برای بررسی آخرین backtest:
  python backtest/check_backtest_method.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def check_backtest_method(folder_name=None):
    """
    بررسی روش استفاده شده در backtest

    Args:
        folder_name: نام فولدر backtest (مثلاً v2_20251120_002427)
                    اگر None باشد، آخرین فولدر را بررسی می‌کند
    """
    # مسیر فولدر backtest_results
    base_dir = Path(__file__).parent.parent  # یک پوشه بالاتر (root)
    results_dir = base_dir / 'backtest_results'

    if not results_dir.exists():
        print(f"❌ فولدر {results_dir} یافت نشد!")
        return None

    # اگر folder_name داده نشده، آخرین فولدر را پیدا کن
    if folder_name is None:
        # پیدا کردن همه فولدرهای v2_*
        v2_folders = sorted([f for f in results_dir.iterdir() if f.is_dir() and f.name.startswith('v2_')])

        if not v2_folders:
            print(f"❌ هیچ فولدر backtest در {results_dir} یافت نشد!")
            return None

        # آخرین فولدر (بر اساس timestamp در نام)
        backtest_folder = v2_folders[-1]
        print(f"📁 آخرین backtest پیدا شد: {backtest_folder.name}")
    else:
        backtest_folder = results_dir / folder_name

        if not backtest_folder.exists():
            print(f"❌ فولدر {backtest_folder} یافت نشد!")
            print(f"\nفولدرهای موجود:")
            for f in sorted(results_dir.iterdir()):
                if f.is_dir() and f.name.startswith('v2_'):
                    print(f"  - {f.name}")
            return None

    # مسیر فایل config.json
    config_file = backtest_folder / 'config.json'

    if not config_file.exists():
        print(f"❌ فایل {config_file} یافت نشد!")
        return None

    # خواندن config.json
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ خطا در خواندن config.json: {e}")
        return None

    # تشخیص روش
    print("\n" + "=" * 70)
    print(f"📊 BACKTEST METHOD DETECTION")
    print("=" * 70)
    print(f"📁 Folder: {backtest_folder.name}")
    print(f"📄 Config: {config_file}")
    print("=" * 70)

    # 1. بررسی scoring_method
    scoring_method = config.get('signal_processing', {}).get('scoring', {}).get('scoring_method', 'unknown')

    # 2. بررسی use_multi_tf_aggregation
    use_multi_tf = config.get('orchestrator', {}).get('use_multi_tf_aggregation', None)

    # 3. بررسی old_system settings
    old_system = config.get('signal_processing', {}).get('scoring', {}).get('old_system', {})
    symbol_perf = old_system.get('symbol_performance_enabled', None)
    correlation_safety = old_system.get('correlation_safety_enabled', None)
    use_rr_confluence = old_system.get('use_rr_based_confluence', None)
    max_final_score = old_system.get('max_final_score', None)

    # 4. بررسی validation thresholds
    validation = config.get('validation', {})
    min_signal_score = validation.get('min_signal_score', None)
    strong_threshold = validation.get('strong_signal_threshold', None)

    # نمایش اطلاعات
    print(f"\n🔑 KEY INDICATORS:")
    print(f"  scoring_method:              {scoring_method.upper()}")
    print(f"  use_multi_tf_aggregation:    {use_multi_tf}")
    print(f"\n⚙️  OLD SYSTEM FEATURES:")
    print(f"  symbol_performance_enabled:  {symbol_perf}")
    print(f"  correlation_safety_enabled:  {correlation_safety}")
    print(f"  use_rr_based_confluence:     {use_rr_confluence}")
    print(f"  max_final_score:             {max_final_score} {'(unlimited)' if max_final_score == 0 else '(limited)' if max_final_score else ''}")
    print(f"\n📊 VALIDATION THRESHOLDS:")
    print(f"  min_signal_score:            {min_signal_score}")
    print(f"  strong_signal_threshold:     {strong_threshold}")

    # تعیین روش نهایی
    print("\n" + "=" * 70)

    if scoring_method == 'old' and use_multi_tf == True:
        method = 'OLD'
        emoji = '⚙️'
        description = 'Multi-TF Aggregation + 13 Multipliers'
    elif scoring_method == 'new' and use_multi_tf == False:
        method = 'NEW'
        emoji = '✅'
        description = 'Best Signal Selection (8 Analyzers)'
    elif scoring_method == 'hybrid':
        method = 'HYBRID'
        emoji = '🔀'
        description = 'Mixed approach'
    else:
        method = 'UNKNOWN'
        emoji = '❓'
        description = 'Cannot determine method clearly'

    print(f"{emoji} METHOD DETECTED: {method}")
    print(f"📝 Description: {description}")
    print("=" * 70)

    # جدول مقایسه
    print(f"\n📋 COMPARISON WITH STANDARD METHODS:")
    print(f"{'Attribute':<35} {'OLD':<15} {'NEW':<15} {'Current':<15}")
    print("-" * 80)
    print(f"{'scoring_method':<35} {'old':<15} {'new':<15} {scoring_method:<15}")
    print(f"{'use_multi_tf_aggregation':<35} {'True':<15} {'False':<15} {str(use_multi_tf):<15}")
    print(f"{'min_signal_score':<35} {'200':<15} {'60':<15} {str(min_signal_score):<15}")
    print(f"{'strong_signal_threshold':<35} {'500':<15} {'150':<15} {str(strong_threshold):<15}")
    print(f"{'max_final_score':<35} {'0 (unlimited)':<15} {'300':<15} {str(max_final_score):<15}")
    print(f"{'OLD system features enabled':<35} {'Yes':<15} {'No':<15} {'Yes' if symbol_perf else 'No':<15}")

    print("\n" + "=" * 70 + "\n")

    return {
        'method': method,
        'scoring_method': scoring_method,
        'use_multi_tf_aggregation': use_multi_tf,
        'min_signal_score': min_signal_score,
        'strong_threshold': strong_threshold,
        'max_final_score': max_final_score,
        'old_system_enabled': symbol_perf
    }


def list_all_backtests():
    """لیست تمام backtestها با روش استفاده شده"""
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / 'backtest_results'

    if not results_dir.exists():
        print(f"❌ فولدر {results_dir} یافت نشد!")
        return

    # پیدا کردن همه فولدرهای v2_*
    v2_folders = sorted([f for f in results_dir.iterdir() if f.is_dir() and f.name.startswith('v2_')])

    if not v2_folders:
        print(f"❌ هیچ فولدر backtest یافت نشد!")
        return

    print("\n" + "=" * 100)
    print(f"📊 ALL BACKTESTS SUMMARY")
    print("=" * 100)
    print(f"{'Folder Name':<30} {'Method':<10} {'Multi-TF':<10} {'Min Score':<12} {'Date/Time':<20}")
    print("-" * 100)

    for folder in v2_folders:
        config_file = folder / 'config.json'

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                scoring_method = config.get('signal_processing', {}).get('scoring', {}).get('scoring_method', '?')
                use_multi_tf = config.get('orchestrator', {}).get('use_multi_tf_aggregation', '?')
                min_score = config.get('validation', {}).get('min_signal_score', '?')

                # استخراج تاریخ از نام فولدر (v2_20251120_002427)
                parts = folder.name.split('_')
                if len(parts) >= 3:
                    date_str = parts[1]  # 20251120
                    time_str = parts[2]  # 002427
                    try:
                        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                        datetime_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        datetime_str = folder.name
                else:
                    datetime_str = folder.name

                method = 'OLD' if scoring_method == 'old' else 'NEW' if scoring_method == 'new' else 'HYBRID'

                print(f"{folder.name:<30} {method:<10} {str(use_multi_tf):<10} {str(min_score):<12} {datetime_str:<20}")

            except:
                print(f"{folder.name:<30} {'ERROR':<10} {'?':<10} {'?':<12} {'?':<20}")
        else:
            print(f"{folder.name:<30} {'NO CONFIG':<10} {'?':<10} {'?':<12} {'?':<20}")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='بررسی روش استفاده شده در Backtest (OLD vs NEW)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال‌های استفاده:
  python backtest/check_backtest_method.py v2_20251120_002427
  python backtest/check_backtest_method.py v2_20251120_002407
  python backtest/check_backtest_method.py --list
  python backtest/check_backtest_method.py
        """
    )

    parser.add_argument(
        'folder',
        nargs='?',
        default=None,
        help='نام فولدر backtest (مثلاً v2_20251120_002427). اگر نداده شود، آخرین فولدر بررسی می‌شود'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='نمایش لیست تمام backtestها'
    )

    args = parser.parse_args()

    if args.list:
        list_all_backtests()
    else:
        result = check_backtest_method(args.folder)

        if result:
            sys.exit(0)
        else:
            sys.exit(1)
