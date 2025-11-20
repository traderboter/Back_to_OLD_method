"""
RiskRewardCalculator - Calculate SL/TP with 5-Method Priority System

این ماژول Stop-Loss و Take-Profit را با استفاده از 5 روش به ترتیب اولویت محاسبه می‌کند:
1. Harmonic Pattern-based (D point ±1%)
2. Price Channel-based (channel lines ±1%)
3. Support/Resistance-based (nearest level with max 3×ATR check)
4. ATR-based (fallback)
5. Percentage-based (final fallback)

Usage:
    calculator = RiskRewardCalculator(config)
    result = calculator.calculate_sl_tp(
        direction='LONG',
        entry_price=50000.0,
        context=analysis_context,
        config=adapted_config
    )
"""

from typing import Dict, Any, Optional, Tuple
import logging
from signal_generation.context import AnalysisContext

logger = logging.getLogger(__name__)


class RiskRewardCalculator:
    """
    محاسبه SL/TP با استفاده از 5 روش اولویت‌دار.

    Priority Flow:
    1. Harmonic → 2. Channel → 3. S/R → 4. ATR → 5. Percentage

    Key features:
    - Adaptive SL/TP based on pattern type
    - Safety checks for minimum distance
    - Maximum 3×ATR distance check for S/R
    - Risk-Reward ratio calculation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize RiskRewardCalculator.

        Args:
            config: Global configuration dictionary
        """
        self.config = config

        # Default risk parameters
        self.default_sl_percent = config.get('risk', {}).get('default_stop_loss_percent', 2.0)
        self.default_rr_ratio = config.get('risk', {}).get('preferred_risk_reward_ratio', 2.0)
        self.min_rr_ratio = config.get('risk', {}).get('min_risk_reward_ratio', 1.5)

        # ATR multipliers
        self.atr_sl_multiplier = config.get('risk', {}).get('atr_trailing_multiplier', 2.0)

        # Safety parameters
        self.min_sl_distance_atr_mult = 0.5  # Minimum SL distance = 0.5×ATR
        self.max_sr_distance_atr_mult = 3.0  # Maximum S/R distance = 3.0×ATR

        logger.info("RiskRewardCalculator initialized")

    def calculate_sl_tp(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext,
        adapted_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        محاسبه Stop-Loss و Take-Profit با استفاده از 5 روش اولویت‌دار.

        Args:
            direction: 'LONG' or 'SHORT'
            entry_price: قیمت ورود
            context: AnalysisContext با نتایج تمام analyzers
            adapted_config: تنظیمات adaptive (اختیاری)

        Returns:
            Dictionary حاوی:
            {
                'stop_loss': float,
                'take_profit': float,
                'risk_reward_ratio': float,
                'risk_distance': float,
                'sl_method': str (نام روش استفاده شده)
            }
        """
        # Normalize direction
        direction = direction.upper()
        if direction not in ['LONG', 'SHORT']:
            raise ValueError(f"Invalid direction: {direction}. Must be 'LONG' or 'SHORT'")

        # Get adapted config or use defaults
        if adapted_config is None:
            adapted_config = {}

        default_sl_percent = adapted_config.get('default_stop_loss_percent', self.default_sl_percent)
        preferred_rr = adapted_config.get('preferred_risk_reward_ratio', self.default_rr_ratio)
        min_rr = adapted_config.get('min_risk_reward_ratio', self.min_rr_ratio)

        try:
            # Get ATR for safety checks and fallback
            atr = self._get_atr(context)

            # Try each method in priority order
            stop_loss = None
            take_profit = None
            calculation_method = "None"

            # 1. Try Harmonic Pattern
            sl, tp, method = self._try_harmonic_sl_tp(direction, entry_price, context)
            if sl is not None and tp is not None:
                stop_loss, take_profit, calculation_method = sl, tp, method
                logger.debug(f"Using Harmonic method: {method}")

            # 2. Try Price Channel
            if stop_loss is None:
                sl, tp, method = self._try_channel_sl_tp(direction, entry_price, context)
                if sl is not None and tp is not None:
                    stop_loss, take_profit, calculation_method = sl, tp, method
                    logger.debug(f"Using Channel method: {method}")

            # 3. Try Support/Resistance (با چک فاصله max 3×ATR)
            if stop_loss is None:
                sl, method = self._try_sr_sl(direction, entry_price, context, atr)
                if sl is not None:
                    # Check if S/R is too far (max 3×ATR)
                    sl_dist_atr_ratio = abs(entry_price - sl) / atr if atr > 0 else 0
                    if sl_dist_atr_ratio <= self.max_sr_distance_atr_mult:
                        stop_loss = sl
                        calculation_method = method
                        logger.debug(f"Using S/R method: {method} (distance: {sl_dist_atr_ratio:.2f}×ATR)")
                    else:
                        logger.debug(f"S/R too far ({sl_dist_atr_ratio:.2f}×ATR > {self.max_sr_distance_atr_mult}×ATR), skipping")

            # 4. ATR-based fallback
            if stop_loss is None and atr > 0:
                sl_multiplier = adapted_config.get('atr_trailing_multiplier', self.atr_sl_multiplier)
                if direction == 'LONG':
                    stop_loss = entry_price - (atr * sl_multiplier)
                else:
                    stop_loss = entry_price + (atr * sl_multiplier)
                calculation_method = f"ATR x{sl_multiplier}"
                logger.debug(f"Using ATR fallback: {calculation_method}")

            # 5. Percentage-based fallback (final fallback)
            if stop_loss is None:
                if direction == 'LONG':
                    stop_loss = entry_price * (1 - default_sl_percent / 100)
                else:
                    stop_loss = entry_price * (1 + default_sl_percent / 100)
                calculation_method = f"Percentage {default_sl_percent}%"
                logger.debug(f"Using Percentage fallback: {calculation_method}")

            # Apply safety checks for SL
            stop_loss = self._apply_sl_safety_checks(
                stop_loss, entry_price, direction, atr, calculation_method
            )

            # Calculate risk distance
            risk_distance = abs(entry_price - stop_loss)
            if risk_distance <= 1e-6:
                logger.warning(f"Risk distance too small ({risk_distance}), using default percentage")
                risk_distance = entry_price * (default_sl_percent / 100)
                if direction == 'LONG':
                    stop_loss = entry_price - risk_distance
                else:
                    stop_loss = entry_price + risk_distance

            # Calculate TP if not set yet (from Harmonic or Channel)
            if take_profit is None:
                take_profit = self._calculate_tp(
                    entry_price, stop_loss, direction, preferred_rr, min_rr,
                    risk_distance, context
                )

            # Apply safety checks for TP
            take_profit = self._apply_tp_safety_checks(
                take_profit, entry_price, stop_loss, direction, min_rr, risk_distance
            )

            # Calculate final RR
            final_reward_distance = abs(take_profit - entry_price)
            final_rr = final_reward_distance / risk_distance if risk_distance > 0 else 0

            # Final sanity checks
            if abs(take_profit) < 1e-6:
                logger.error(f"Calculated TP near zero! Using minimum viable TP")
                take_profit = entry_price * (1.05 if direction == 'LONG' else 0.95)

            if abs(stop_loss) < 1e-6:
                logger.error(f"Calculated SL near zero! Using minimum viable SL")
                stop_loss = entry_price * (0.95 if direction == 'LONG' else 1.05)

            precision = 8
            return {
                'stop_loss': round(stop_loss, precision),
                'take_profit': round(take_profit, precision),
                'risk_reward_ratio': round(final_rr, 2),
                'risk_distance': round(risk_distance, precision),
                'sl_method': calculation_method
            }

        except Exception as e:
            logger.error(f"Error calculating SL/TP: {e}", exc_info=True)
            # Emergency fallback
            return self._error_fallback(direction, entry_price, default_sl_percent, min_rr)

    def _get_atr(self, context: AnalysisContext) -> float:
        """
        دریافت ATR از context.

        Args:
            context: AnalysisContext

        Returns:
            ATR value (or default if not available)
        """
        # Try to get ATR from volatility analyzer
        volatility_result = context.get_result('volatility')
        if volatility_result and volatility_result.get('status') == 'ok':
            atr = volatility_result.get('atr')
            if atr and atr > 0:
                return atr

        # Try to get ATR directly from DataFrame
        if 'atr' in context.df.columns:
            atr = context.df['atr'].iloc[-1]
            if atr and atr > 0:
                return atr

        # Default fallback: 0.5% of current price
        current_price = context.df['close'].iloc[-1]
        default_atr = current_price * 0.005
        logger.warning(f"ATR not found, using default: {default_atr}")
        return default_atr

    def _try_harmonic_sl_tp(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext
    ) -> Tuple[Optional[float], Optional[float], str]:
        """
        تلاش برای محاسبه SL/TP با Harmonic Patterns.

        Method 1 (Highest Priority):
        - LONG: SL = D point × 0.99, TP based on pattern type
        - SHORT: SL = D point × 1.01, TP based on pattern type
        - Butterfly/Crab: TP = entry ± (entry - SL) × 1.618
        - Others: TP = X point

        Returns:
            (stop_loss, take_profit, method_name) or (None, None, "")
        """
        harmonic_result = context.get_result('harmonic')
        if not harmonic_result or harmonic_result.get('status') != 'ok':
            return None, None, ""

        patterns = harmonic_result.get('patterns', [])
        if not patterns:
            return None, None, ""

        # Find best matching pattern
        direction_map = {'LONG': 'bullish', 'SHORT': 'bearish'}
        target_direction = direction_map.get(direction)

        matching_patterns = [p for p in patterns if p.get('type') == target_direction]
        if not matching_patterns:
            return None, None, ""

        # Sort by strength/completion
        best_pattern = max(
            matching_patterns,
            key=lambda p: (p.get('strength', 0), p.get('completion', 0))
        )

        pattern_name = best_pattern.get('name', '').lower()
        points = best_pattern.get('points', {})

        if 'D' not in points or 'X' not in points:
            return None, None, ""

        d_point_price = points['D']['price']
        x_point_price = points['X']['price']

        stop_loss = None
        take_profit = None

        if direction == 'LONG':
            stop_loss = d_point_price * 0.99  # 1% below D point

            # Target based on pattern type
            if 'butterfly' in pattern_name or 'crab' in pattern_name:
                # Higher target for Butterfly/Crab
                take_profit = entry_price + (entry_price - stop_loss) * 1.618
            else:
                # Target to X point for other patterns
                take_profit = x_point_price

        elif direction == 'SHORT':
            stop_loss = d_point_price * 1.01  # 1% above D point

            # Target based on pattern type
            if 'butterfly' in pattern_name or 'crab' in pattern_name:
                take_profit = entry_price - (stop_loss - entry_price) * 1.618
            else:
                take_profit = x_point_price

        method = f"Harmonic_{pattern_name}"
        return stop_loss, take_profit, method

    def _try_channel_sl_tp(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext
    ) -> Tuple[Optional[float], Optional[float], str]:
        """
        تلاش برای محاسبه SL/TP با Price Channels.

        Method 2:
        - LONG (ascending/horizontal): SL = lower line × 0.99, TP = upper line × 0.99
        - SHORT (descending/horizontal): SL = upper line × 1.01, TP = lower line × 1.01

        Returns:
            (stop_loss, take_profit, method_name) or (None, None, "")
        """
        channel_result = context.get_result('channel')
        if not channel_result or channel_result.get('status') != 'ok':
            return None, None, ""

        channel_type = channel_result.get('channel_type', 'irregular')

        # Check if channel is suitable for direction
        if direction == 'LONG' and channel_type not in ['ascending', 'horizontal']:
            return None, None, ""
        if direction == 'SHORT' and channel_type not in ['descending', 'horizontal']:
            return None, None, ""

        upper_bound = channel_result.get('upper_bound')
        lower_bound = channel_result.get('lower_bound')

        if upper_bound is None or lower_bound is None:
            return None, None, ""

        stop_loss = None
        take_profit = None

        if direction == 'LONG':
            stop_loss = lower_bound * 0.99  # Slightly below lower channel line
            take_profit = upper_bound * 0.99  # Target to upper channel line

        elif direction == 'SHORT':
            stop_loss = upper_bound * 1.01  # Slightly above upper channel line
            take_profit = lower_bound * 1.01  # Target to lower channel line

        method = f"Price_Channel_{channel_type}"
        return stop_loss, take_profit, method

    def _try_sr_sl(
        self,
        direction: str,
        entry_price: float,
        context: AnalysisContext,
        atr: float
    ) -> Tuple[Optional[float], str]:
        """
        تلاش برای محاسبه SL با Support/Resistance.

        Method 3:
        - LONG: SL = nearest support × 0.999
        - SHORT: SL = nearest resistance × 1.001
        - فاصله بیش از 3×ATR رد می‌شود (در _calculate_sl_tp چک می‌شود)

        Returns:
            (stop_loss, method_name) or (None, "")
        """
        sr_result = context.get_result('support_resistance')
        if not sr_result or sr_result.get('status') != 'ok':
            return None, ""

        nearest_support = sr_result.get('nearest_support')
        nearest_resistance = sr_result.get('nearest_resistance')

        # Handle dict format (old system compatibility)
        if isinstance(nearest_support, dict):
            nearest_support = nearest_support.get('price')
        if isinstance(nearest_resistance, dict):
            nearest_resistance = nearest_resistance.get('price')

        stop_loss = None
        method = ""

        if direction == 'LONG' and nearest_support and nearest_support < entry_price:
            stop_loss = nearest_support * 0.999
            method = "Support Level"

        elif direction == 'SHORT' and nearest_resistance and nearest_resistance > entry_price:
            stop_loss = nearest_resistance * 1.001
            method = "Resistance Level"

        return stop_loss, method

    def _apply_sl_safety_checks(
        self,
        stop_loss: float,
        entry_price: float,
        direction: str,
        atr: float,
        calculation_method: str
    ) -> float:
        """
        اعمال safety checks برای Stop-Loss.

        Ensures:
        - Minimum distance = 0.5×ATR

        Args:
            stop_loss: مقدار اولیه SL
            entry_price: قیمت ورود
            direction: جهت معامله
            atr: ATR value
            calculation_method: روش محاسبه (برای لاگ)

        Returns:
            stop_loss تصحیح شده
        """
        min_sl_distance = atr * self.min_sl_distance_atr_mult if atr > 0 else entry_price * 0.001

        if direction == 'LONG':
            if (entry_price - stop_loss) < min_sl_distance:
                original_sl = stop_loss
                stop_loss = entry_price - min_sl_distance
                logger.debug(
                    f"SL too close for LONG: {original_sl:.6f} → {stop_loss:.6f} "
                    f"(min distance: {min_sl_distance:.6f})"
                )

        elif direction == 'SHORT':
            if (stop_loss - entry_price) < min_sl_distance:
                original_sl = stop_loss
                stop_loss = entry_price + min_sl_distance
                logger.debug(
                    f"SL too close for SHORT: {original_sl:.6f} → {stop_loss:.6f} "
                    f"(min distance: {min_sl_distance:.6f})"
                )

        return stop_loss

    def _calculate_tp(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        preferred_rr: float,
        min_rr: float,
        risk_distance: float,
        context: AnalysisContext
    ) -> float:
        """
        محاسبه Take-Profit بر اساس Risk-Reward ratio.

        با تنظیم بر اساس نزدیکترین S/R.

        Args:
            entry_price: قیمت ورود
            stop_loss: Stop-Loss
            direction: جهت معامله
            preferred_rr: نسبت RR ترجیحی
            min_rr: حداقل نسبت RR
            risk_distance: فاصله ریسک
            context: AnalysisContext

        Returns:
            take_profit قیمت
        """
        # Calculate base TP using preferred RR
        reward_distance = risk_distance * preferred_rr
        reward_distance = max(reward_distance, entry_price * 0.001)  # Ensure non-zero

        if direction == 'LONG':
            take_profit = entry_price + reward_distance
        else:
            take_profit = entry_price - reward_distance

        # Adjust TP based on nearby S/R
        sr_result = context.get_result('support_resistance')
        if sr_result and sr_result.get('status') == 'ok':
            nearest_support = sr_result.get('nearest_support')
            nearest_resistance = sr_result.get('nearest_resistance')

            # Handle dict format
            if isinstance(nearest_support, dict):
                nearest_support = nearest_support.get('price')
            if isinstance(nearest_resistance, dict):
                nearest_resistance = nearest_resistance.get('price')

            # Adjust for LONG
            if direction == 'LONG' and nearest_resistance:
                if nearest_resistance < take_profit:
                    # Resistance is in the way
                    if nearest_resistance > entry_price + (risk_distance * min_rr):
                        # Resistance still gives us min RR, use it
                        take_profit = nearest_resistance * 0.999
                        logger.debug(f"TP adjusted to resistance: {take_profit:.2f}")
                    else:
                        logger.debug(
                            f"Nearest resistance {nearest_resistance:.2f} would make TP too close, "
                            f"keeping calculated TP: {take_profit:.2f}"
                        )

            # Adjust for SHORT
            elif direction == 'SHORT' and nearest_support:
                if nearest_support > take_profit:
                    # Support is in the way
                    if nearest_support < entry_price - (risk_distance * min_rr):
                        # Support still gives us min RR, use it
                        take_profit = nearest_support * 1.001
                        logger.debug(f"TP adjusted to support: {take_profit:.2f}")
                    else:
                        logger.debug(
                            f"Nearest support {nearest_support:.2f} would make TP too close, "
                            f"keeping calculated TP: {take_profit:.2f}"
                        )

        return take_profit

    def _apply_tp_safety_checks(
        self,
        take_profit: float,
        entry_price: float,
        stop_loss: float,
        direction: str,
        min_rr: float,
        risk_distance: float
    ) -> float:
        """
        اعمال safety checks برای Take-Profit.

        Ensures:
        - Minimum RR ratio is met

        Args:
            take_profit: مقدار اولیه TP
            entry_price: قیمت ورود
            stop_loss: Stop-Loss
            direction: جهت معامله
            min_rr: حداقل نسبت RR
            risk_distance: فاصله ریسک

        Returns:
            take_profit تصحیح شده
        """
        min_reward = risk_distance * min_rr

        if direction == 'LONG':
            if take_profit <= entry_price + (min_reward * 0.9):
                original_tp = take_profit
                take_profit = entry_price + min_reward
                logger.debug(
                    f"TP too close for LONG: {original_tp:.6f} → {take_profit:.6f} "
                    f"(min RR: {min_rr})"
                )

        elif direction == 'SHORT':
            if take_profit >= entry_price - (min_reward * 0.9):
                original_tp = take_profit
                take_profit = entry_price - min_reward
                logger.debug(
                    f"TP too close for SHORT: {original_tp:.6f} → {take_profit:.6f} "
                    f"(min RR: {min_rr})"
                )

        return take_profit

    def _error_fallback(
        self,
        direction: str,
        entry_price: float,
        default_sl_percent: float,
        min_rr: float
    ) -> Dict[str, Any]:
        """
        Emergency fallback در صورت خطا.

        Args:
            direction: جهت معامله
            entry_price: قیمت ورود
            default_sl_percent: درصد پیش‌فرض SL
            min_rr: حداقل نسبت RR

        Returns:
            Dictionary حاوی SL/TP emergency
        """
        if direction == 'LONG':
            stop_loss = entry_price * (1 - default_sl_percent / 100)
            take_profit = entry_price * (1 + (default_sl_percent * min_rr) / 100)
        else:
            stop_loss = entry_price * (1 + default_sl_percent / 100)
            take_profit = entry_price * (1 - (default_sl_percent * min_rr) / 100)

        risk_distance = abs(entry_price - stop_loss)

        precision = 8
        return {
            'stop_loss': round(stop_loss, precision),
            'take_profit': round(take_profit, precision),
            'risk_reward_ratio': min_rr,
            'risk_distance': round(risk_distance, precision),
            'sl_method': 'Error Fallback'
        }
