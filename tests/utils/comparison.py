"""
Comparison utilities for validating new system against old system.

این ماژول ابزارهایی برای مقایسه خروجی سیستم جدید با سیستم قدیم فراهم می‌کند.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """نتیجه مقایسه دو سیگنال."""

    matches: bool
    differences: List[Dict[str, Any]] = field(default_factory=list)

    # Percentage differences
    score_diff_percentage: float = 0.0
    sl_diff_percentage: float = 0.0
    tp_diff_percentage: float = 0.0
    rr_diff_percentage: float = 0.0

    # Summary
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'matches': self.matches,
            'differences': self.differences,
            'score_diff_percentage': self.score_diff_percentage,
            'sl_diff_percentage': self.sl_diff_percentage,
            'tp_diff_percentage': self.tp_diff_percentage,
            'rr_diff_percentage': self.rr_diff_percentage,
            'total_checks': self.total_checks,
            'passed_checks': self.passed_checks,
            'failed_checks': self.failed_checks,
            'pass_rate': f"{(self.passed_checks / self.total_checks * 100):.1f}%" if self.total_checks > 0 else "0%"
        }

    def __str__(self) -> str:
        """String representation."""
        status = "✅ MATCH" if self.matches else "❌ MISMATCH"
        return (
            f"{status}\n"
            f"Passed: {self.passed_checks}/{self.total_checks} "
            f"({self.passed_checks / self.total_checks * 100:.1f}%)\n"
            f"Score diff: {self.score_diff_percentage:.2f}%\n"
            f"SL diff: {self.sl_diff_percentage:.2f}%\n"
            f"TP diff: {self.tp_diff_percentage:.2f}%\n"
            f"Differences: {len(self.differences)}"
        )


def compare_signals(
    old_signal: Dict[str, Any],
    new_signal: Dict[str, Any],
    tolerance: float = 0.05,  # 5% tolerance
    strict_mode: bool = False
) -> ComparisonResult:
    """
    مقایسه دو سیگنال و یافتن تفاوت‌ها.

    Args:
        old_signal: خروجی سیستم قدیم
        new_signal: خروجی سیستم جدید
        tolerance: حد تلرانس برای تفاوت‌ها (5% پیش‌فرض)
        strict_mode: اگر True، هیچ تفاوتی قابل قبول نیست

    Returns:
        ComparisonResult با جزئیات تفاوت‌ها
    """
    result = ComparisonResult(matches=True)
    differences = []

    # مقایسه direction
    result.total_checks += 1
    if old_signal.get('direction') != new_signal.get('direction'):
        differences.append({
            'field': 'direction',
            'old': old_signal.get('direction'),
            'new': new_signal.get('direction'),
            'severity': 'critical'
        })
        result.failed_checks += 1
    else:
        result.passed_checks += 1

    # مقایسه SL
    result.total_checks += 1
    if 'stop_loss' in old_signal and 'stop_loss' in new_signal:
        sl_diff_pct = abs(old_signal['stop_loss'] - new_signal['stop_loss']) / old_signal['stop_loss'] * 100
        result.sl_diff_percentage = sl_diff_pct

        if strict_mode or sl_diff_pct > (tolerance * 100):
            differences.append({
                'field': 'stop_loss',
                'old': old_signal['stop_loss'],
                'new': new_signal['stop_loss'],
                'diff_pct': sl_diff_pct,
                'severity': 'high' if sl_diff_pct > 10 else 'medium'
            })
            result.failed_checks += 1
        else:
            result.passed_checks += 1

    # مقایسه TP
    result.total_checks += 1
    if 'take_profit' in old_signal and 'take_profit' in new_signal:
        tp_diff_pct = abs(old_signal['take_profit'] - new_signal['take_profit']) / old_signal['take_profit'] * 100
        result.tp_diff_percentage = tp_diff_pct

        if strict_mode or tp_diff_pct > (tolerance * 100):
            differences.append({
                'field': 'take_profit',
                'old': old_signal['take_profit'],
                'new': new_signal['take_profit'],
                'diff_pct': tp_diff_pct,
                'severity': 'high' if tp_diff_pct > 10 else 'medium'
            })
            result.failed_checks += 1
        else:
            result.passed_checks += 1

    # مقایسه RR
    result.total_checks += 1
    if 'risk_reward_ratio' in old_signal and 'risk_reward_ratio' in new_signal:
        rr_diff_pct = abs(old_signal['risk_reward_ratio'] - new_signal['risk_reward_ratio']) / old_signal['risk_reward_ratio'] * 100
        result.rr_diff_percentage = rr_diff_pct

        if strict_mode or rr_diff_pct > (tolerance * 100):
            differences.append({
                'field': 'risk_reward_ratio',
                'old': old_signal['risk_reward_ratio'],
                'new': new_signal['risk_reward_ratio'],
                'diff_pct': rr_diff_pct,
                'severity': 'medium'
            })
            result.failed_checks += 1
        else:
            result.passed_checks += 1

    # مقایسه Score
    result.total_checks += 1
    old_score = old_signal.get('score', {})
    new_score = new_signal.get('score', {})

    if isinstance(old_score, dict) and isinstance(new_score, dict):
        old_final = old_score.get('final_score', 0)
        new_final = new_score.get('final_score', 0)

        if old_final > 0:
            score_diff_pct = abs(old_final - new_final) / old_final * 100
            result.score_diff_percentage = score_diff_pct

            if strict_mode or score_diff_pct > (tolerance * 100):
                differences.append({
                    'field': 'score.final_score',
                    'old': old_final,
                    'new': new_final,
                    'diff_pct': score_diff_pct,
                    'severity': 'high' if score_diff_pct > 15 else 'medium'
                })
                result.failed_checks += 1
            else:
                result.passed_checks += 1

    # مقایسه SL method
    result.total_checks += 1
    if 'sl_method' in old_signal and 'sl_method' in new_signal:
        if old_signal['sl_method'] != new_signal['sl_method']:
            differences.append({
                'field': 'sl_method',
                'old': old_signal['sl_method'],
                'new': new_signal['sl_method'],
                'severity': 'low'  # اطلاعاتی است، نه خطا
            })
            result.failed_checks += 1
        else:
            result.passed_checks += 1

    # مقایسه patterns
    result.total_checks += 1
    old_patterns = set(old_signal.get('pattern_names', []))
    new_patterns = set(new_signal.get('pattern_names', []))

    if old_patterns != new_patterns:
        missing = old_patterns - new_patterns
        extra = new_patterns - old_patterns

        if missing or extra:
            differences.append({
                'field': 'pattern_names',
                'old': list(old_patterns),
                'new': list(new_patterns),
                'missing_in_new': list(missing),
                'extra_in_new': list(extra),
                'severity': 'low' if len(missing) + len(extra) < 3 else 'medium'
            })
            result.failed_checks += 1
    else:
        result.passed_checks += 1

    # نتیجه نهایی
    result.differences = differences
    result.matches = (len(differences) == 0)

    return result


def load_expected_signal(
    symbol: str,
    test_case: str = "default",
    base_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    بارگذاری سیگنال مورد انتظار از سیستم قدیم.

    Args:
        symbol: نماد (مثلاً 'BTCUSDT')
        test_case: نام test case (پیش‌فرض 'default')
        base_path: مسیر پایه (اگر None، از مسیر پیش‌فرض استفاده می‌شود)

    Returns:
        Dictionary حاوی اطلاعات سیگنال

    Raises:
        FileNotFoundError: اگر فایل وجود نداشته باشد
    """
    if base_path is None:
        base_path = Path(__file__).parent.parent / "expected_outputs" / "old_system"

    filename = f"{symbol}_{test_case}.json"
    filepath = base_path / filename

    if not filepath.exists():
        raise FileNotFoundError(
            f"Expected output file not found: {filepath}\n"
            f"Please generate expected outputs from old system first."
        )

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_expected_signal(
    signal: Dict[str, Any],
    symbol: str,
    test_case: str = "default",
    base_path: Optional[Path] = None
) -> Path:
    """
    ذخیره سیگنال به عنوان expected output.

    Args:
        signal: Dictionary حاوی اطلاعات سیگنال
        symbol: نماد
        test_case: نام test case
        base_path: مسیر پایه

    Returns:
        Path به فایل ذخیره شده
    """
    if base_path is None:
        base_path = Path(__file__).parent.parent / "expected_outputs" / "old_system"

    base_path.mkdir(parents=True, exist_ok=True)

    filename = f"{symbol}_{test_case}.json"
    filepath = base_path / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved expected signal to: {filepath}")
    return filepath


def compare_backtest_results(
    old_results: Dict[str, Any],
    new_results: Dict[str, Any],
    tolerance: float = 0.05
) -> Dict[str, Any]:
    """
    مقایسه نتایج backtest دو سیستم.

    Args:
        old_results: نتایج backtest سیستم قدیم
        new_results: نتایج backtest سیستم جدید
        tolerance: حد تلرانس

    Returns:
        Dictionary حاوی نتایج مقایسه
    """
    comparison = {
        'matches': True,
        'differences': []
    }

    # مقایسه metrics اصلی
    metrics_to_compare = [
        'total_return',
        'sharpe_ratio',
        'max_drawdown',
        'win_rate',
        'profit_factor',
        'total_trades'
    ]

    for metric in metrics_to_compare:
        old_val = old_results.get(metric, 0)
        new_val = new_results.get(metric, 0)

        if old_val != 0:
            diff_pct = abs(old_val - new_val) / abs(old_val) * 100

            if diff_pct > (tolerance * 100):
                comparison['matches'] = False
                comparison['differences'].append({
                    'metric': metric,
                    'old': old_val,
                    'new': new_val,
                    'diff_pct': diff_pct
                })

    return comparison


def generate_comparison_report(
    comparisons: List[ComparisonResult],
    output_path: Optional[Path] = None
) -> str:
    """
    تولید گزارش کامل از مقایسه‌ها.

    Args:
        comparisons: لیست نتایج مقایسه
        output_path: مسیر ذخیره گزارش (اختیاری)

    Returns:
        متن گزارش
    """
    total = len(comparisons)
    matched = sum(1 for c in comparisons if c.matches)

    report_lines = [
        "=" * 60,
        "COMPARISON REPORT",
        "=" * 60,
        f"Total Comparisons: {total}",
        f"Matched: {matched} ({matched/total*100:.1f}%)",
        f"Mismatched: {total - matched} ({(total-matched)/total*100:.1f}%)",
        "",
        "Details:",
        "-" * 60
    ]

    for i, comp in enumerate(comparisons, 1):
        report_lines.append(f"\n{i}. Test Case:")
        report_lines.append(str(comp))

        if comp.differences:
            report_lines.append("\nDifferences:")
            for diff in comp.differences:
                report_lines.append(f"  - {diff['field']}: "
                                  f"old={diff.get('old')}, "
                                  f"new={diff.get('new')}, "
                                  f"severity={diff.get('severity', 'unknown')}")

    report = "\n".join(report_lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report saved to: {output_path}")

    return report
