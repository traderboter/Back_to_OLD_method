# 🗺️ Road Map: بازگرداندن منطق سیستم قدیم با ساختار ماژولار

**تاریخ شروع**: 2025-01-20
**زمان تخمینی**: 10-12 روز کاری
**وضعیت**: در انتظار تأیید

---

## ❓ سوالات کلیدی (باید قبل از شروع پاسخ داده شوند)

### 1. استراتژی پیاده‌سازی
- [ ] **سوال 1**: آیا می‌خواهید تغییرات را مستقیماً در `signal_generation/` فعلی اعمال کنیم؟
  - گزینه A: ✅ بله، مستقیماً تغییر دهیم (سریع‌تر)
  - گزینه B: یک branch جدید بسازیم و بعد merge کنیم
  - گزینه C: یک پوشه جدید مثل `signal_generation_v2/` بسازیم

  **پیشنهاد**: گزینه B (branch جدید برای safety)

### 2. استراتژی Testing
- [ ] **سوال 2**: چه زمانی unit test ها را بنویسیم؟
  - گزینه A: ✅ همزمان با هر مرحله (پیشنهادی، اما کندتر)
  - گزینه B: بعد از تمام پیاده‌سازی‌ها (سریع‌تر، اما خطرناک‌تر)
  - گزینه C: فقط integration tests در پایان

  **پیشنهاد**: گزینه A (TDD approach)

### 3. استراتژی Git
- [ ] **سوال 3**: چطور commit کنیم؟
  - گزینه A: ✅ بعد از هر مرحله یک commit (پیشنهادی)
  - گزینه B: هر روز یک commit
  - گزینه C: در پایان یکجا

  **پیشنهاد**: گزینه A

### 4. Configuration Management
- [ ] **سوال 4**: چطور با config کار کنیم؟
  - گزینه A: ✅ Config فعلی را تغییر دهیم
  - گزینه B: `config_old_system.yaml` جدید بسازیم
  - گزینه C: Flag در config: `use_old_system_logic: true`

  **پیشنهاد**: گزینه C (backward compatible)

### 5. Validation Strategy
- [ ] **سوال 5**: چطور صحت را بررسی کنیم؟
  - گزینه A: مقایسه output با سیستم قدیم (با همان input)
  - گزینه B: ✅ Backtest و مقایسه نتایج
  - گزینه C: فقط manual testing

  **پیشنهاد**: گزینه A + B

### 6. Data for Testing
- [ ] **سوال 6**: داده‌های تست از کجا؟
  - گزینه A: داده‌های واقعی از exchange
  - گزینه B: داده‌های ذخیره شده (CSV/Pickle)
  - گزینه C: داده‌های mock

  **توضیح**: برای مقایسه با سیستم قدیم، نیاز به همان داده‌های ورودی هستیم

---

## 📋 Overview: مراحل کلی

```
Phase 0: Preparation        (1 روز)  ← Setup + Questions
Phase 1: Foundation         (2 روز)  ← RiskCalculator + Analyzer fixes
Phase 2: Core Logic         (3 روز)  ← Scoring + Multi-TF
Phase 3: Integration        (2 روز)  ← Orchestrator + Config
Phase 4: Testing            (2 روز)  ← Unit + Integration tests
Phase 5: Validation         (1 روز)  ← Compare with old system
Phase 6: Documentation      (1 روز)  ← Final docs + handover
```

**جمع**: 12 روز کاری

---

## 🚀 Phase 0: Preparation (روز 0 - 1 روز)

### هدف
آماده‌سازی محیط، ابزارها، و برنامه‌ریزی دقیق

### Tasks

#### Task 0.1: پاسخ به سوالات کلیدی ✋
- [ ] پاسخ دادن به 6 سوال بالا
- [ ] تصمیم‌گیری درباره استراتژی
- [ ] مستندسازی تصمیمات در این فایل

#### Task 0.2: ایجاد Branch جدید
```bash
# ایجاد branch برای کار
git checkout -b feature/restore-old-system-logic

# یا اگر می‌خواهید از main/master شروع کنید
git checkout main
git pull origin main
git checkout -b feature/restore-old-system-logic
```

**Output**: Branch جدید `feature/restore-old-system-logic`

#### Task 0.3: آماده‌سازی Test Data
- [ ] تهیه 5-10 نمونه داده واقعی برای تست
- [ ] ذخیره در `tests/data/sample_ohlcv/`
- [ ] فرمت: `{symbol}_{timeframe}.csv`

**مثال**:
```
tests/data/sample_ohlcv/
├── BTCUSDT_5m.csv
├── BTCUSDT_15m.csv
├── BTCUSDT_1h.csv
├── BTCUSDT_4h.csv
├── ETHUSDT_5m.csv
└── ...
```

#### Task 0.4: آماده‌سازی Old System Output (برای مقایسه)
- [ ] اجرای سیستم قدیم با همان داده‌های تست
- [ ] ذخیره خروجی‌ها در `tests/expected_outputs/old_system/`
- [ ] فرمت: JSON با تمام جزئیات (SL, TP, score, patterns, ...)

**فایل نمونه**: `tests/expected_outputs/old_system/BTCUSDT_signal.json`
```json
{
  "symbol": "BTCUSDT",
  "direction": "long",
  "entry_price": 50000.0,
  "stop_loss": 49500.0,
  "take_profit": 51000.0,
  "risk_reward_ratio": 2.0,
  "sl_method": "Harmonic_butterfly",
  "score": {
    "final_score": 75.5,
    "base_score": 25.0,
    "timeframe_weight": 1.3,
    "trend_alignment": 1.2,
    ...
  },
  "pattern_names": ["harmonic_butterfly", "rsi_bullish_divergence"],
  "timeframe_scores": {
    "5m": {"bullish": 15, "bearish": 5},
    "15m": {"bullish": 18, "bearish": 3},
    "1h": {"bullish": 22, "bearish": 2},
    "4h": {"bullish": 25, "bearish": 1}
  }
}
```

#### Task 0.5: Setup Testing Framework
```bash
# نصب pytest اگر نیست
pip install pytest pytest-asyncio pytest-cov

# ایجاد ساختار tests
mkdir -p tests/unit/signal_generation
mkdir -p tests/integration
mkdir -p tests/data/sample_ohlcv
mkdir -p tests/expected_outputs/old_system
mkdir -p tests/expected_outputs/new_system
```

#### Task 0.6: ایجاد Utility Functions برای تست
**فایل**: `tests/utils/comparison.py`

```python
"""Utilities for comparing old and new system outputs."""
import json
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ComparisonResult:
    """نتیجه مقایسه دو سیگنال"""
    matches: bool
    differences: List[Dict[str, Any]]
    score_diff_percentage: float
    sl_diff_percentage: float
    tp_diff_percentage: float

def compare_signals(
    old_signal: Dict[str, Any],
    new_signal: Dict[str, Any],
    tolerance: float = 0.05  # 5% tolerance
) -> ComparisonResult:
    """
    مقایسه دو سیگنال و یافتن تفاوت‌ها.

    Args:
        old_signal: خروجی سیستم قدیم
        new_signal: خروجی سیستم جدید
        tolerance: حد تلرانس برای تفاوت‌ها (5% پیش‌فرض)

    Returns:
        ComparisonResult با جزئیات تفاوت‌ها
    """
    differences = []

    # مقایسه direction
    if old_signal['direction'] != new_signal['direction']:
        differences.append({
            'field': 'direction',
            'old': old_signal['direction'],
            'new': new_signal['direction']
        })

    # مقایسه SL
    sl_diff_pct = abs(old_signal['stop_loss'] - new_signal['stop_loss']) / old_signal['stop_loss']
    if sl_diff_pct > tolerance:
        differences.append({
            'field': 'stop_loss',
            'old': old_signal['stop_loss'],
            'new': new_signal['stop_loss'],
            'diff_pct': sl_diff_pct * 100
        })

    # مقایسه TP
    tp_diff_pct = abs(old_signal['take_profit'] - new_signal['take_profit']) / old_signal['take_profit']
    if tp_diff_pct > tolerance:
        differences.append({
            'field': 'take_profit',
            'old': old_signal['take_profit'],
            'new': new_signal['take_profit'],
            'diff_pct': tp_diff_pct * 100
        })

    # مقایسه Score
    score_diff_pct = abs(old_signal['score']['final_score'] - new_signal['score']['final_score']) / old_signal['score']['final_score']
    if score_diff_pct > tolerance:
        differences.append({
            'field': 'score.final_score',
            'old': old_signal['score']['final_score'],
            'new': new_signal['score']['final_score'],
            'diff_pct': score_diff_pct * 100
        })

    # مقایسه SL method
    if old_signal.get('sl_method') != new_signal.get('sl_method'):
        differences.append({
            'field': 'sl_method',
            'old': old_signal.get('sl_method'),
            'new': new_signal.get('sl_method')
        })

    # مقایسه patterns
    old_patterns = set(old_signal.get('pattern_names', []))
    new_patterns = set(new_signal.get('pattern_names', []))
    if old_patterns != new_patterns:
        differences.append({
            'field': 'pattern_names',
            'old': list(old_patterns),
            'new': list(new_patterns),
            'missing_in_new': list(old_patterns - new_patterns),
            'extra_in_new': list(new_patterns - old_patterns)
        })

    return ComparisonResult(
        matches=(len(differences) == 0),
        differences=differences,
        score_diff_percentage=score_diff_pct * 100,
        sl_diff_percentage=sl_diff_pct * 100,
        tp_diff_percentage=tp_diff_pct * 100
    )

def load_expected_signal(symbol: str, test_case: str = "default") -> Dict[str, Any]:
    """بارگذاری سیگنال مورد انتظار از سیستم قدیم."""
    path = f"tests/expected_outputs/old_system/{symbol}_{test_case}.json"
    with open(path, 'r') as f:
        return json.load(f)
```

**Deliverables Phase 0**:
- [x] Branch جدید ایجاد شده
- [ ] Test data آماده شده (5-10 نمونه)
- [ ] Expected outputs از سیستم قدیم ذخیره شده
- [ ] Testing framework setup شده
- [ ] Comparison utilities نوشته شده
- [ ] تصمیمات کلیدی مستند شده

**Checkpoint 0**:
```bash
# بررسی آمادگی
ls tests/data/sample_ohlcv/  # باید 20+ فایل CSV باشد
ls tests/expected_outputs/old_system/  # باید 5-10 فایل JSON باشد
pytest tests/utils/test_comparison.py  # باید pass شود
git status  # همه چیز commit شده
```

---

## 🔧 Phase 1: Foundation (روز 1-2، 2 روز)

### هدف
ایجاد بلوک‌های اساسی: RiskCalculator + بهبود Analyzers

---

### Day 1: RiskRewardCalculator

#### Task 1.1: ایجاد فایل و ساختار اولیه
**فایل**: `signal_generation/risk_calculator.py`

```bash
touch signal_generation/risk_calculator.py
```

**محتوا**:
```python
"""
Risk/Reward Calculator - Old System Compatible

محاسبه Stop-Loss و Take-Profit با 5 روش اولویت‌دار مانند سیستم قدیم:
1. Harmonic Pattern-based
2. Price Channel-based
3. Support/Resistance-based (با چک فاصله max 3×ATR)
4. ATR-based (fallback)
5. Percentage-based (final fallback)

محل مرجع در سیستم قدیم: Old_bot/signal_generator.py:4016-4264
"""

import logging
from typing import Dict, Any, Optional, Tuple
from signal_generation.context import AnalysisContext

logger = logging.getLogger(__name__)


class RiskRewardCalculator:
    """
    محاسبه‌گر Stop-Loss و Take-Profit مشابه سیستم قدیم.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        مقداردهی اولیه.

        Args:
            config: تنظیمات (risk_management section)
        """
        self.config = config.get('risk_management', {})

        # پارامترهای پیش‌فرض
        self.default_sl_percent = self.config.get('default_stop_loss_percent', 1.5)
        self.preferred_rr = self.config.get('preferred_risk_reward_ratio', 2.0)
        self.min_rr = self.config.get('min_risk_reward_ratio', 1.5)
        self.atr_multiplier = self.config.get('atr_trailing_multiplier', 2.0)
        self.max_sr_distance_atr = self.config.get('max_sr_distance_atr_ratio', 3.0)

        logger.info(
            f"RiskRewardCalculator initialized: "
            f"preferred_rr={self.preferred_rr}, min_rr={self.min_rr}, "
            f"atr_mult={self.atr_multiplier}"
        )

    def calculate_sl_tp(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        محاسبه Stop-Loss و Take-Profit با روش اولویت‌دار.

        Args:
            direction: 'LONG' یا 'SHORT'
            entry_price: قیمت ورود
            context: Context تحلیل (شامل نتایج analyzers)
            config: تنظیمات اضافی (اختیاری)

        Returns:
            Dictionary شامل:
                - stop_loss: قیمت SL
                - take_profit: قیمت TP
                - risk_reward_ratio: نسبت RR
                - risk_amount_per_unit: مقدار ریسک
                - sl_method: روش محاسبه SL
        """
        # Override config if provided
        if config:
            self.config = config

        direction = direction.upper()

        stop_loss = None
        take_profit = None
        calculation_method = "None"

        # روش 1: Harmonic Pattern
        # TODO: implement

        # روش 2: Price Channel
        # TODO: implement

        # روش 3: S/R Level
        # TODO: implement

        # روش 4: ATR-based (fallback)
        # TODO: implement

        # روش 5: Percentage (final fallback)
        # TODO: implement

        # Finalize and return
        return self._finalize_sl_tp(
            stop_loss, take_profit, calculation_method,
            entry_price, direction
        )

    def _try_harmonic_sl_tp(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        روش 1: محاسبه SL/TP بر اساس Harmonic Pattern.

        محل در سیستم قدیم: signal_generator.py:4061-4091
        """
        # TODO: implement
        return None, None, None

    # TODO: سایر متدها...

    def _finalize_sl_tp(
        self,
        sl: float,
        tp: float,
        method: str,
        entry: float,
        direction: str
    ) -> Dict[str, Any]:
        """
        نهایی‌سازی و safety checks.

        محل در سیستم قدیم: signal_generator.py:4166-4243
        """
        # TODO: implement safety checks

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

        return {
            'stop_loss': round(sl, 8),
            'take_profit': round(tp, 8),
            'risk_reward_ratio': round(rr, 2),
            'risk_amount_per_unit': round(risk, 8),
            'sl_method': method
        }
```

**Deliverable**: فایل ساختار اولیه ایجاد شد

#### Task 1.2: پیاده‌سازی Harmonic Pattern SL/TP
```python
def _try_harmonic_sl_tp(
    self,
    direction: str,
    entry_price: float,
    context: AnalysisContext
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    روش 1: محاسبه SL/TP بر اساس Harmonic Pattern.

    محل در سیستم قدیم: signal_generator.py:4061-4091
    """
    harmonic_result = context.get_result('harmonic')
    if not harmonic_result or not harmonic_result.get('patterns'):
        return None, None, None

    patterns = harmonic_result['patterns']

    # انتخاب بهترین pattern (highest confidence)
    best_pattern = max(patterns, key=lambda p: p.get('confidence', 0))

    pattern_direction = best_pattern.get('direction')
    pattern_type = best_pattern.get('type', '')

    # بررسی هم‌جهتی با direction سیگنال
    if (direction == 'LONG' and pattern_direction != 'bullish') or \
       (direction == 'SHORT' and pattern_direction != 'bearish'):
        return None, None, None

    # بررسی وجود points
    points = best_pattern.get('points', {})
    if 'D' not in points or 'X' not in points:
        logger.debug("Harmonic pattern missing D or X point")
        return None, None, None

    d_price = points['D']['price']
    x_price = points['X']['price']

    # محاسبه SL و TP
    if direction == 'LONG':
        # SL: 1% below D point
        sl = d_price * 0.99

        # TP: based on pattern type
        if 'butterfly' in pattern_type.lower() or 'crab' in pattern_type.lower():
            # Higher target for these patterns
            tp = entry_price + (entry_price - sl) * 1.618
        else:
            # Target to X point
            tp = x_price

    else:  # SHORT
        # SL: 1% above D point
        sl = d_price * 1.01

        if 'butterfly' in pattern_type.lower() or 'crab' in pattern_type.lower():
            tp = entry_price - (sl - entry_price) * 1.618
        else:
            tp = x_price

    method = f"Harmonic_{pattern_type}"

    logger.info(
        f"Harmonic pattern SL/TP: {pattern_type}, "
        f"SL={sl:.2f}, TP={tp:.2f}"
    )

    return sl, tp, method
```

**Deliverable**: Harmonic method implemented

#### Task 1.3: پیاده‌سازی Price Channel SL/TP
```python
def _try_channel_sl_tp(
    self,
    direction: str,
    entry_price: float,
    context: AnalysisContext
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    روش 2: محاسبه SL/TP بر اساس Price Channel.

    محل در سیستم قدیم: signal_generator.py:4093-4125
    """
    channel_result = context.get_result('channel')
    if not channel_result or not channel_result.get('channels'):
        return None, None, None

    channel = channel_result['channels'][0]  # اولین کانال
    channel_direction = channel.get('direction')

    # بررسی سازگاری با direction
    if direction == 'LONG':
        if channel_direction not in ['ascending', 'horizontal']:
            return None, None, None

        # SL: below lower channel line
        lower_current = channel.get('lower_current_price')
        if not lower_current:
            return None, None, None

        sl = lower_current * 0.99

        # TP: to upper channel line
        upper_current = channel.get('upper_current_price')
        if not upper_current:
            return None, None, None

        tp = upper_current * 0.99

    elif direction == 'SHORT':
        if channel_direction not in ['descending', 'horizontal']:
            return None, None, None

        # SL: above upper channel line
        upper_current = channel.get('upper_current_price')
        if not upper_current:
            return None, None, None

        sl = upper_current * 1.01

        # TP: to lower channel line
        lower_current = channel.get('lower_current_price')
        if not lower_current:
            return None, None, None

        tp = lower_current * 1.01

    else:
        return None, None, None

    method = f"Price_Channel_{channel_direction}"

    logger.info(
        f"Price channel SL/TP: {channel_direction}, "
        f"SL={sl:.2f}, TP={tp:.2f}"
    )

    return sl, tp, method
```

**Deliverable**: Channel method implemented

#### Task 1.4: پیاده‌سازی S/R SL + ATR fallback + Percentage fallback
- [ ] Implement `_try_sr_sl()`
- [ ] Implement `_calculate_atr_sl()`
- [ ] Implement `_calculate_percentage_sl()`
- [ ] Implement `_calculate_tp_from_sl()`
- [ ] Implement `_adjust_tp_with_sr()`

#### Task 1.5: پیاده‌سازی Safety Checks
- [ ] Minimum SL distance check
- [ ] Maximum SL distance check
- [ ] TP minimum RR check
- [ ] Zero price checks

#### Task 1.6: پیاده‌سازی main method با priority flow
```python
def calculate_sl_tp(self, ...):
    """Main method با 5 روش اولویت‌دار"""

    # 1. Try Harmonic
    sl, tp, method = self._try_harmonic_sl_tp(direction, entry_price, context)
    if sl and tp:
        return self._finalize_sl_tp(sl, tp, method, entry_price, direction)

    # 2. Try Channel
    sl, tp, method = self._try_channel_sl_tp(direction, entry_price, context)
    if sl and tp:
        return self._finalize_sl_tp(sl, tp, method, entry_price, direction)

    # 3. Try S/R
    sl = self._try_sr_sl(direction, entry_price, context)

    # Check distance with ATR
    if sl:
        atr = context.get_indicator_value('atr')
        if atr and atr > 0:
            sl_dist_atr_ratio = abs(entry_price - sl) / atr
            if sl_dist_atr_ratio > self.max_sr_distance_atr:
                logger.debug(f"S/R too far: {sl_dist_atr_ratio:.1f}×ATR > {self.max_sr_distance_atr}")
                sl = None  # Reject, too far

    if sl:
        # Calculate TP from SL
        tp = self._calculate_tp_from_sl(sl, entry_price, direction, context)
        method = "Support/Resistance Level"
        return self._finalize_sl_tp(sl, tp, method, entry_price, direction)

    # 4. ATR-based fallback
    sl, tp = self._calculate_atr_sl_tp(direction, entry_price, context)
    if sl and tp:
        method = f"ATR x{self.atr_multiplier}"
        return self._finalize_sl_tp(sl, tp, method, entry_price, direction)

    # 5. Percentage fallback (final)
    sl, tp = self._calculate_percentage_sl_tp(direction, entry_price)
    method = f"Percentage {self.default_sl_percent}%"
    return self._finalize_sl_tp(sl, tp, method, entry_price, direction)
```

#### Task 1.7: نوشتن Unit Tests
**فایل**: `tests/unit/signal_generation/test_risk_calculator.py`

```python
import pytest
from signal_generation.risk_calculator import RiskRewardCalculator
from signal_generation.context import AnalysisContext
import pandas as pd

@pytest.fixture
def config():
    return {
        'risk_management': {
            'default_stop_loss_percent': 1.5,
            'preferred_risk_reward_ratio': 2.0,
            'min_risk_reward_ratio': 1.5,
            'atr_trailing_multiplier': 2.0,
            'max_sr_distance_atr_ratio': 3.0
        }
    }

@pytest.fixture
def calculator(config):
    return RiskRewardCalculator(config)

@pytest.fixture
def context_with_harmonic():
    """Context با harmonic pattern"""
    df = pd.DataFrame({
        'close': [50000] * 100,
        'atr': [500] * 100
    })

    context = AnalysisContext('BTCUSDT', '1h', df)

    # Add harmonic pattern result
    context.set_result('harmonic', {
        'status': 'ok',
        'patterns': [{
            'type': 'butterfly',
            'direction': 'bullish',
            'confidence': 0.85,
            'points': {
                'X': {'price': 48000},
                'D': {'price': 49500}
            }
        }]
    })

    return context

def test_harmonic_long_sl_tp(calculator, context_with_harmonic):
    """تست محاسبه SL/TP برای long با harmonic pattern"""
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000,
        context=context_with_harmonic
    )

    # بررسی‌ها
    assert result['sl_method'].startswith('Harmonic')
    assert result['stop_loss'] < 50000  # SL باید پایین‌تر از entry باشد
    assert result['take_profit'] > 50000  # TP باید بالاتر از entry باشد
    assert result['risk_reward_ratio'] >= 1.5  # min RR

def test_fallback_to_atr(calculator):
    """تست fallback به ATR وقتی harmonic/channel نیست"""
    df = pd.DataFrame({
        'close': [50000] * 100,
        'atr': [500] * 100
    })

    context = AnalysisContext('BTCUSDT', '1h', df)
    # بدون harmonic/channel results

    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000,
        context=context
    )

    assert result['sl_method'].startswith('ATR')
    assert result['stop_loss'] == pytest.approx(50000 - 500 * 2.0, rel=0.01)

# TODO: تست‌های بیشتر برای:
# - Channel-based SL/TP
# - S/R with ATR distance check
# - Percentage fallback
# - Safety checks
# - SHORT direction
```

**Run tests**:
```bash
pytest tests/unit/signal_generation/test_risk_calculator.py -v
```

#### Task 1.8: Commit
```bash
git add signal_generation/risk_calculator.py
git add tests/unit/signal_generation/test_risk_calculator.py
git commit -m "feat: Add RiskRewardCalculator with 5-method priority system

Implemented Old System compatible SL/TP calculation:
- Method 1: Harmonic Pattern-based
- Method 2: Price Channel-based
- Method 3: S/R-based (with max 3×ATR distance check)
- Method 4: ATR-based (fallback)
- Method 5: Percentage-based (final fallback)

Includes:
- TP adjustment with nearby S/R
- Safety checks for min/max distances
- Unit tests with 85%+ coverage

Ref: Old_bot/signal_generator.py:4016-4264"
```

**Deliverables Day 1**:
- [x] `signal_generation/risk_calculator.py` (400+ lines)
- [x] Unit tests (200+ lines, 85%+ coverage)
- [x] Commit

---

### Day 2: Analyzer Improvements

#### Task 1.9: MomentumAnalyzer - اضافه کردن momentum_strength
**فایل**: `signal_generation/analyzers/momentum_analyzer.py`

```python
# در متد analyze()، اضافه کردن:

def analyze(self, context: AnalysisContext) -> None:
    # ... existing code ...

    # 🆕 محاسبه momentum_strength
    momentum_strength = self._calculate_momentum_strength(context)

    result = {
        'status': 'ok',
        'direction': direction,
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'momentum_strength': momentum_strength,  # 🆕
        'signals': signals,
        'details': details
    }

    context.set_result('momentum', result)

def _calculate_momentum_strength(self, context: AnalysisContext) -> float:
    """
    محاسبه قدرت momentum (0.8 - 1.2).

    محل در سیستم قدیم: signal_generator.py:5248-5250
    """
    rsi = context.get_indicator_value('rsi')

    if rsi is None:
        return 1.0

    # Strong momentum
    if rsi > 70 or rsi < 30:
        return 1.2

    # Moderate momentum
    elif (60 < rsi <= 70) or (30 <= rsi < 40):
        return 1.1

    # Weak momentum
    elif 40 <= rsi <= 60:
        return 0.9

    return 1.0
```

**Test**:
```python
def test_momentum_strength_strong():
    context = create_context_with_rsi(75)  # Strong bullish
    analyzer = MomentumAnalyzer(config)
    analyzer.analyze(context)

    result = context.get_result('momentum')
    assert result['momentum_strength'] == 1.2

def test_momentum_strength_weak():
    context = create_context_with_rsi(50)  # Weak
    analyzer = MomentumAnalyzer(config)
    analyzer.analyze(context)

    result = context.get_result('momentum')
    assert result['momentum_strength'] == 0.9
```

#### Task 1.10: ChannelAnalyzer - اضافه کردن current_prices
**فایل**: `signal_generation/analyzers/channel_analyzer.py`

```python
# در output channel، اضافه کردن:

channel_data = {
    'type': 'channel',
    'direction': direction,  # 'ascending', 'descending', 'horizontal'
    'upper_slope': upper_slope,
    'upper_intercept': upper_intercept,
    'lower_slope': lower_slope,
    'lower_intercept': lower_intercept,
    # 🆕 اضافه کردن قیمت‌های فعلی
    'upper_current_price': self._calculate_current_price(
        upper_slope, upper_intercept, len(df) - 1
    ),
    'lower_current_price': self._calculate_current_price(
        lower_slope, lower_intercept, len(df) - 1
    ),
    'strength': strength,
    'touch_points_upper': len(upper_touches),
    'touch_points_lower': len(lower_touches)
}

def _calculate_current_price(self, slope: float, intercept: float, index: int) -> float:
    """محاسبه قیمت فعلی روی خط کانال."""
    return slope * index + intercept
```

#### Task 1.11: HTFAnalyzer - بهبود structure_score
**فایل**: `signal_generation/analyzers/htf_analyzer.py`

اطمینان از اینکه output شامل:
- `structure_score` (0.5 - 1.5)
- `trends_aligned` (bool)
- `momentum_aligned` (bool)
- `at_support_zone` (bool)
- `at_resistance_zone` (bool)

#### Task 1.12: نوشتن tests برای تغییرات analyzers

#### Task 1.13: Commit
```bash
git add signal_generation/analyzers/momentum_analyzer.py
git add signal_generation/analyzers/channel_analyzer.py
git add signal_generation/analyzers/htf_analyzer.py
git add tests/unit/signal_generation/analyzers/
git commit -m "feat: Improve analyzers for old system compatibility

Changes:
- MomentumAnalyzer: Add momentum_strength (0.8-1.2 based on RSI)
- ChannelAnalyzer: Add upper_current_price and lower_current_price
- HTFAnalyzer: Ensure structure_score and alignment flags

These outputs are required for old system scoring logic.

Ref: Old_bot/signal_generator.py:5248-5250, 4093-4125"
```

**Deliverables Day 2**:
- [x] Analyzers improved
- [x] Tests added
- [x] Commit

**Checkpoint Phase 1**:
```bash
pytest tests/unit/signal_generation/ -v  # همه تست‌ها pass
git log --oneline -5  # 2 commit جدید
```

---

## ⚙️ Phase 2: Core Logic (روز 3-5، 3 روز)

### هدف
پیاده‌سازی منطق اصلی Scoring و Multi-TF

### Day 3: SignalScorer - Part 1 (Base Structure)

#### Task 2.1: Refactor SignalScorer برای 13 multipliers
**فایل**: `signal_generation/signal_scorer.py`

#### Task 2.2: پیاده‌سازی multiplier methods (1-7)
- base_score
- timeframe_weight
- trend_alignment
- volume_confirmation
- pattern_quality
- confluence_score
- symbol_performance_factor

#### Task 2.3: نوشتن tests برای multipliers

#### Task 2.4: Commit

---

### Day 4: SignalScorer - Part 2 (Remaining Multipliers)

#### Task 2.5: پیاده‌سازی multiplier methods (8-14)
- correlation_safety_factor
- macd_analysis_score
- structure_score
- volatility_score
- harmonic_pattern_score
- price_channel_score
- cyclical_pattern_score

#### Task 2.6: Final score formula

#### Task 2.7: Integration tests

#### Task 2.8: Commit

---

### Day 5: Multi-Timeframe Scoring

#### Task 2.9: Refactor Orchestrator.analyze_symbol()

#### Task 2.10: پیاده‌سازی _calculate_multi_timeframe_score()

#### Task 2.11: Integration با RiskCalculator

#### Task 2.12: Tests

#### Task 2.13: Commit

**Checkpoint Phase 2**:
```bash
pytest tests/unit/signal_generation/test_signal_scorer.py -v
pytest tests/integration/ -v
```

---

## 🔗 Phase 3: Integration (روز 6-7، 2 روز)

### Day 6: Orchestrator Integration

#### Task 3.1: اتصال RiskCalculator به Orchestrator

#### Task 3.2: اتصال SignalScorer به Orchestrator

#### Task 3.3: تست end-to-end

#### Task 3.4: Commit

---

### Day 7: Configuration

#### Task 3.5: به‌روزرسانی config.yaml

#### Task 3.6: اضافه کردن flag `use_old_system_logic`

#### Task 3.7: Backward compatibility tests

#### Task 3.8: Commit

---

## ✅ Phase 4: Testing (روز 8-9، 2 روز)

### Day 8: Unit Tests Complete

#### Task 4.1: Coverage 90%+

#### Task 4.2: Edge cases

### Day 9: Integration Tests

#### Task 4.3: End-to-end tests

#### Task 4.4: Comparison با expected outputs

---

## 🎯 Phase 5: Validation (روز 10، 1 روز)

### Day 10: مقایسه با سیستم قدیم

#### Task 5.1: اجرای هر دو سیستم با همان input

#### Task 5.2: مقایسه outputs

#### Task 5.3: تنظیم differences

---

## 📚 Phase 6: Documentation (روز 11، 1 روز)

### Day 11: مستندسازی نهایی

#### Task 6.1: به‌روزرسانی README

#### Task 6.2: نوشتن migration guide

#### Task 6.3: Handover document

---

## ✅ Completion Checklist

در پایان، این موارد باید تکمیل شوند:

### Code
- [ ] RiskRewardCalculator با 5 روش
- [ ] SignalScorer با 13 multipliers
- [ ] Orchestrator multi-TF refactored
- [ ] Analyzers improved
- [ ] Config updated

### Tests
- [ ] Unit tests 90%+ coverage
- [ ] Integration tests pass
- [ ] Comparison tests با old system pass

### Documentation
- [ ] API docs updated
- [ ] Migration guide written
- [ ] Configuration documented

### Validation
- [ ] Output matches old system (±5%)
- [ ] Backtest performance similar
- [ ] No regression in quality

---

**Total Estimated Time**: 11-12 روز کاری

**Current Status**: Phase 0 - در انتظار پاسخ سوالات کلیدی

---

## 🤔 سوالات؟

قبل از شروع، لطفاً به **6 سوال کلیدی بالا** پاسخ دهید تا بتوانیم مطمئن شویم.
