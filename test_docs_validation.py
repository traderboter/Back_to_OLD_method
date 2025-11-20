#!/usr/bin/env python3
"""
تست برای تایید صحت مستندات سیستم تولید سیگنال
این تست چک می‌کند که مستندات با کد واقعی مطابقت دارد
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple


class DocsValidator:
    """اعتبارسنجی مستندات با کد واقعی"""

    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(__file__).parent
        self.results: Dict[str, List[str]] = {
            "passed": [],
            "failed": [],
            "warnings": []
        }

    def validate_file_references(self) -> bool:
        """بررسی صحت مسیرهای فایل ذکر شده در مستندات"""
        print("🔍 بررسی مسیرهای فایل...")

        # فایل‌های کلیدی که باید وجود داشته باشند
        critical_files = [
            "signal_processor.py",
            "signal_generation/orchestrator.py",
            "signal_generation/analyzers/indicators/indicator_orchestrator.py",
            "signal_generation/timeframe_score_cache.py",
        ]

        all_exist = True
        for file_path in critical_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                self.results["passed"].append(f"✅ فایل موجود: {file_path}")
            else:
                self.results["failed"].append(f"❌ فایل وجود ندارد: {file_path}")
                all_exist = False

        return all_exist

    def validate_function_signatures(self) -> bool:
        """بررسی امضای توابع کلیدی"""
        print("🔍 بررسی امضای توابع...")

        # توابع کلیدی که باید چک شوند
        functions_to_check = [
            ("signal_processor.py", "async def process_symbol", 392),
            ("signal_generation/orchestrator.py", "async def analyze_symbol", 854),
        ]

        all_valid = True
        for file_path, function_sig, expected_line in functions_to_check:
            full_path = self.base_path / file_path
            if not full_path.exists():
                continue

            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # جستجوی تابع
            found = False
            actual_line = None
            for i, line in enumerate(lines, 1):
                if function_sig in line:
                    found = True
                    actual_line = i
                    break

            if found:
                # چک کردن شماره خط (با تلرانس ±10 خط)
                if abs(actual_line - expected_line) <= 10:
                    self.results["passed"].append(
                        f"✅ {file_path}:{actual_line} - {function_sig}"
                    )
                else:
                    self.results["warnings"].append(
                        f"⚠️  {file_path} - {function_sig} در خط {actual_line} است "
                        f"(مستندات می‌گوید {expected_line})"
                    )
            else:
                self.results["failed"].append(
                    f"❌ {file_path} - {function_sig} پیدا نشد"
                )
                all_valid = False

        return all_valid

    def validate_class_existence(self) -> bool:
        """بررسی وجود کلاس‌های کلیدی"""
        print("🔍 بررسی کلاس‌های کلیدی...")

        classes_to_check = [
            ("signal_generation/analyzers/indicators/indicator_orchestrator.py",
             "IndicatorOrchestrator"),
            ("signal_generation/timeframe_score_cache.py",
             "TimeframeScoreCache"),
        ]

        all_exist = True
        for file_path, class_name in classes_to_check:
            full_path = self.base_path / file_path
            if not full_path.exists():
                self.results["failed"].append(
                    f"❌ فایل {file_path} وجود ندارد"
                )
                all_exist = False
                continue

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if f"class {class_name}" in content:
                self.results["passed"].append(
                    f"✅ کلاس {class_name} در {file_path} یافت شد"
                )
            else:
                self.results["failed"].append(
                    f"❌ کلاس {class_name} در {file_path} پیدا نشد"
                )
                all_exist = False

        return all_exist

    def validate_analyzers(self) -> bool:
        """بررسی وجود Analyzer ها"""
        print("🔍 بررسی Analyzer ها...")

        expected_analyzers = [
            "trend_analyzer.py",
            "momentum_analyzer.py",
            "volume_analyzer.py",
            "volatility_analyzer.py",
            "pattern_analyzer.py",
            "sr_analyzer.py",
            "harmonic_analyzer.py",
            "channel_analyzer.py",
            "cyclical_analyzer.py",
            "htf_analyzer.py",
            "volume_pattern_analyzer.py",
        ]

        analyzers_dir = self.base_path / "signal_generation" / "analyzers"

        if not analyzers_dir.exists():
            self.results["failed"].append(
                f"❌ پوشه analyzers وجود ندارد: {analyzers_dir}"
            )
            return False

        all_exist = True
        for analyzer in expected_analyzers:
            analyzer_path = analyzers_dir / analyzer
            if analyzer_path.exists():
                self.results["passed"].append(f"✅ Analyzer موجود: {analyzer}")
            else:
                self.results["failed"].append(f"❌ Analyzer وجود ندارد: {analyzer}")
                all_exist = False

        return all_exist

    def validate_indicators(self) -> bool:
        """بررسی وجود اندیکاتورها"""
        print("🔍 بررسی اندیکاتورها...")

        expected_indicators = [
            "ema.py",
            "sma.py",
            "rsi.py",
            "macd.py",
            "bollinger_bands.py",
            "stochastic.py",
            "adx.py",
            "atr.py",
        ]

        indicators_dir = self.base_path / "signal_generation" / "analyzers" / "indicators"

        if not indicators_dir.exists():
            self.results["failed"].append(
                f"❌ پوشه indicators وجود ندارد: {indicators_dir}"
            )
            return False

        all_exist = True
        for indicator in expected_indicators:
            indicator_path = indicators_dir / indicator
            if indicator_path.exists():
                self.results["passed"].append(f"✅ Indicator موجود: {indicator}")
            else:
                self.results["failed"].append(f"❌ Indicator وجود ندارد: {indicator}")
                all_exist = False

        return all_exist

    def validate_orchestrator_methods(self) -> bool:
        """بررسی متدهای IndicatorOrchestrator"""
        print("🔍 بررسی متدهای IndicatorOrchestrator...")

        orchestrator_path = (
            self.base_path / "signal_generation" / "analyzers" /
            "indicators" / "indicator_orchestrator.py"
        )

        if not orchestrator_path.exists():
            self.results["failed"].append(
                "❌ فایل indicator_orchestrator.py وجود ندارد"
            )
            return False

        with open(orchestrator_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # متدهای مهم که باید وجود داشته باشند
        expected_methods = [
            "calculate_ema",
            "calculate_sma",
            "calculate_rsi",
            "calculate_macd",
            "calculate_bollinger_bands",
            "calculate_stochastic",
            "calculate_adx",
            "calculate_atr",
        ]

        all_exist = True
        for method in expected_methods:
            if f"def {method}" in content or f"async def {method}" in content:
                self.results["passed"].append(
                    f"✅ متد موجود در IndicatorOrchestrator: {method}"
                )
            else:
                self.results["warnings"].append(
                    f"⚠️  متد در IndicatorOrchestrator پیدا نشد: {method}"
                )

        return all_exist

    def print_results(self):
        """نمایش نتایج"""
        print("\n" + "="*70)
        print("📊 نتایج اعتبارسنجی مستندات")
        print("="*70)

        if self.results["passed"]:
            print(f"\n✅ موفق ({len(self.results['passed'])} مورد):")
            for item in self.results["passed"]:
                print(f"  {item}")

        if self.results["warnings"]:
            print(f"\n⚠️  هشدار ({len(self.results['warnings'])} مورد):")
            for item in self.results["warnings"]:
                print(f"  {item}")

        if self.results["failed"]:
            print(f"\n❌ خطا ({len(self.results['failed'])} مورد):")
            for item in self.results["failed"]:
                print(f"  {item}")

        print("\n" + "="*70)

        total_checks = (
            len(self.results["passed"]) +
            len(self.results["warnings"]) +
            len(self.results["failed"])
        )
        passed_count = len(self.results["passed"])

        print(f"📈 نتیجه کلی: {passed_count}/{total_checks} تست موفق")

        if self.results["failed"]:
            print("❌ برخی تست‌ها با خطا مواجه شدند")
            return False
        elif self.results["warnings"]:
            print("⚠️  همه تست‌ها موفق اما با هشدار")
            return True
        else:
            print("✅ همه تست‌ها موفق")
            return True

    def run_all_validations(self) -> bool:
        """اجرای تمام تست‌ها"""
        print("🚀 شروع اعتبارسنجی مستندات...")
        print()

        validations = [
            self.validate_file_references,
            self.validate_function_signatures,
            self.validate_class_existence,
            self.validate_analyzers,
            self.validate_indicators,
            self.validate_orchestrator_methods,
        ]

        all_passed = True
        for validation in validations:
            try:
                result = validation()
                if not result:
                    all_passed = False
            except Exception as e:
                self.results["failed"].append(f"❌ خطا در اجرای تست: {e}")
                all_passed = False
            print()

        return self.print_results()


def main():
    """تابع اصلی"""
    validator = DocsValidator()
    success = validator.run_all_validations()

    # خروج با کد مناسب
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
