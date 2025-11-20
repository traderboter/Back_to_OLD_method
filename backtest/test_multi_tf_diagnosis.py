#!/usr/bin/env python3
"""
اسکریپت تشخیص: آیا backtest واقعاً Multi-TF است یا فقط Single-TF؟

این اسکریپت کد backtest را تحلیل می‌کند و نشان می‌دهد:
1. کدام API استفاده می‌شود (analyze_symbol vs generate_signal_for_symbol)
2. چند تایم‌فریم fetch می‌شود
3. آیا Multi-TF Aggregation فعال است
"""

import sys
from pathlib import Path
import re

# رنگ‌ها برای terminal
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_colored(text, color):
    """چاپ متن رنگی"""
    print(f"{color}{text}{RESET}")


def analyze_backtest_code():
    """تحلیل کد backtest"""
    print("=" * 80)
    print_colored("🔍 BACKTEST MULTI-TF DIAGNOSIS", BLUE)
    print("=" * 80)

    backtest_file = Path(__file__).parent / "backtest_engine_v2.py"

    if not backtest_file.exists():
        print_colored(f"❌ فایل پیدا نشد: {backtest_file}", RED)
        return

    with open(backtest_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"\n📁 فایل: {backtest_file}")
    print(f"📏 حجم: {len(content)} bytes")
    print(f"📊 تعداد خطوط: {len(content.splitlines())}")

    # بررسی 1: کدام API استفاده می‌شود؟
    print("\n" + "=" * 80)
    print_colored("TEST 1: کدام API استفاده می‌شود؟", YELLOW)
    print("=" * 80)

    # جستجو برای analyze_symbol
    analyze_symbol_matches = re.findall(
        r'await\s+self\.signal_orchestrator\.analyze_symbol\s*\(',
        content
    )

    # جستجو برای generate_signal_for_symbol
    generate_signal_matches = re.findall(
        r'await\s+self\.signal_orchestrator\.generate_signal_for_symbol\s*\(',
        content
    )

    print(f"\n🔍 analyze_symbol() calls: {len(analyze_symbol_matches)}")
    print(f"🔍 generate_signal_for_symbol() calls: {len(generate_signal_matches)}")

    if len(analyze_symbol_matches) > 0:
        print_colored("✅ استفاده از analyze_symbol() - Multi-TF API", GREEN)
    elif len(generate_signal_matches) > 0:
        print_colored("❌ استفاده از generate_signal_for_symbol() - Single-TF API", RED)
    else:
        print_colored("⚠️  هیچ API call پیدا نشد!", YELLOW)

    # بررسی 2: چند تایم‌فریم fetch می‌شود؟
    print("\n" + "=" * 80)
    print_colored("TEST 2: چند تایم‌فریم fetch می‌شود؟", YELLOW)
    print("=" * 80)

    # پیدا کردن _process_symbol method
    process_symbol_match = re.search(
        r'async def _process_symbol\(.*?\):(.*?)(?=\n    async def|\n    def|\Z)',
        content,
        re.DOTALL
    )

    if process_symbol_match:
        process_symbol_code = process_symbol_match.group(1)

        # شمارش fetch calls
        fetch_calls = re.findall(
            r'await\s+self\.(data_fetcher|market_data_fetcher|historical_provider)\.',
            process_symbol_code
        )

        # چک کردن آیا loop روی timeframes وجود دارد
        tf_loop = re.search(r'for\s+\w+\s+in\s+.*timeframes', process_symbol_code, re.IGNORECASE)

        print(f"\n🔍 تعداد fetch calls در _process_symbol: {len(fetch_calls)}")

        if tf_loop:
            print_colored("✅ حلقه روی timeframes پیدا شد - احتمالاً Multi-TF", GREEN)
        else:
            print_colored("❌ حلقه روی timeframes پیدا نشد - احتمالاً Single-TF", RED)

        # نمایش قسمت مهم کد
        print("\n📄 کد _process_symbol (100 خط اول):")
        print("-" * 80)
        lines = process_symbol_code.split('\n')[:100]
        for i, line in enumerate(lines, 1):
            if 'signal_orchestrator' in line or 'timeframe' in line.lower():
                print_colored(f"{i:3}: {line}", YELLOW)
            else:
                print(f"{i:3}: {line}")
    else:
        print_colored("⚠️  متد _process_symbol پیدا نشد!", YELLOW)

    # بررسی 3: آیا timeframes_data ساخته می‌شود؟
    print("\n" + "=" * 80)
    print_colored("TEST 3: آیا timeframes_data dictionary ساخته می‌شود؟", YELLOW)
    print("=" * 80)

    timeframes_data_creation = re.search(
        r'timeframes_data\s*=\s*\{',
        content
    )

    if timeframes_data_creation:
        print_colored("✅ timeframes_data dictionary پیدا شد - احتمالاً Multi-TF", GREEN)

        # پیدا کردن کد ساخت dictionary
        dict_match = re.search(
            r'timeframes_data\s*=\s*\{(.*?)\}',
            content,
            re.DOTALL
        )
        if dict_match:
            print("\n📄 کد ساخت timeframes_data:")
            print("-" * 80)
            print(dict_match.group(0))
    else:
        print_colored("❌ timeframes_data dictionary پیدا نشد - Single-TF", RED)

    # بررسی 4: مقادیر signal_timeframe
    print("\n" + "=" * 80)
    print_colored("TEST 4: تایم‌فریم signal چیست؟", YELLOW)
    print("=" * 80)

    signal_tf_match = re.search(
        r'self\.signal_timeframe\s*=.*?[\'"](\w+)[\'"]',
        content
    )

    if signal_tf_match:
        tf = signal_tf_match.group(1)
        print(f"\n🔍 signal_timeframe = '{tf}'")
        print_colored(f"⚠️  تنها یک تایم‌فریم ({tf}) به عنوان primary تنظیم شده", YELLOW)

    # نتیجه‌گیری نهایی
    print("\n" + "=" * 80)
    print_colored("📊 نتیجه‌گیری نهایی", BLUE)
    print("=" * 80)

    is_multi_tf = False
    reasons = []

    if len(analyze_symbol_matches) > 0:
        is_multi_tf = True
        reasons.append("✅ استفاده از analyze_symbol() API")
    elif len(generate_signal_matches) > 0:
        reasons.append("❌ استفاده از generate_signal_for_symbol() API (Single-TF)")

    if timeframes_data_creation:
        is_multi_tf = True
        reasons.append("✅ ساخت timeframes_data dictionary")
    else:
        reasons.append("❌ عدم ساخت timeframes_data dictionary")

    print("\n🔍 دلایل:")
    for reason in reasons:
        print(f"  {reason}")

    print("\n")
    if is_multi_tf:
        print_colored("✅ نتیجه: Backtest از Multi-TF Analysis استفاده می‌کند", GREEN)
        print_colored("   همه 4 تایم‌فریم (5m, 15m, 1h, 4h) تحلیل می‌شوند", GREEN)
    else:
        print_colored("❌ نتیجه: Backtest فقط از Single-TF Analysis استفاده می‌کند", RED)
        print_colored("   فقط یک تایم‌فریم تحلیل می‌شود - نیاز به تصحیح!", RED)

    print("\n" + "=" * 80)

    return is_multi_tf


def trace_api_flow():
    """ردیابی جریان API call"""
    print("\n" + "=" * 80)
    print_colored("🔍 API CALL FLOW TRACE", BLUE)
    print("=" * 80)

    backtest_file = Path(__file__).parent / "backtest_engine_v2.py"

    with open(backtest_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print("\n📍 ردیابی flow از _process_symbol تا API call:\n")

    in_process_symbol = False
    indent_level = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # شروع _process_symbol
        if 'async def _process_symbol' in line:
            in_process_symbol = True
            print_colored(f"{i:4}: {line.rstrip()}", BLUE)
            indent_level = len(line) - len(line.lstrip())
            continue

        # پایان method (indent کمتر شده)
        if in_process_symbol:
            current_indent = len(line) - len(line.lstrip())

            # اگر indent به سطح method یا کمتر برگشت، متد تمام شده
            if current_indent <= indent_level and stripped and not stripped.startswith('#'):
                if stripped.startswith('async def ') or stripped.startswith('def '):
                    break

            # نمایش خطوط مهم
            if any(keyword in line for keyword in [
                'signal_orchestrator',
                'timeframe',
                'fetch',
                'analyze',
                'generate_signal',
                'await self.'
            ]):
                if 'signal_orchestrator.analyze_symbol' in line:
                    print_colored(f"{i:4}: {line.rstrip()}", GREEN)
                elif 'signal_orchestrator.generate_signal' in line:
                    print_colored(f"{i:4}: {line.rstrip()}", RED)
                else:
                    print_colored(f"{i:4}: {line.rstrip()}", YELLOW)


if __name__ == "__main__":
    try:
        # تحلیل کد
        is_multi_tf = analyze_backtest_code()

        # ردیابی flow
        trace_api_flow()

        # خروج با exit code
        sys.exit(0 if is_multi_tf else 1)

    except Exception as e:
        print_colored(f"\n❌ خطا: {e}", RED)
        import traceback
        traceback.print_exc()
        sys.exit(2)
