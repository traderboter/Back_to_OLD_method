"""
Pre-compute Patterns - محاسبه و ذخیره الگوها (نسخه مستقل)

این اسکریپت الگوهای کندلی را برای همه کندل‌ها تشخیص و ذخیره می‌کند.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import yaml
import argparse
from tqdm import tqdm
from scipy.signal import find_peaks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleCandlePatternDetector:
    """تشخیص‌دهنده ساده الگوهای کندلی"""

    def __init__(self):
        self.body_threshold = 0.1  # حداقل درصد بدنه نسبت به رنج

    def _body_size(self, open_p: float, close: float, high: float, low: float) -> float:
        """محاسبه اندازه بدنه نسبت به رنج کل"""
        range_size = high - low
        if range_size == 0:
            return 0
        return abs(close - open_p) / range_size

    def _is_bullish(self, open_p: float, close: float) -> bool:
        """آیا کندل صعودی است"""
        return close > open_p

    def _is_bearish(self, open_p: float, close: float) -> bool:
        """آیا کندل نزولی است"""
        return close < open_p

    def _upper_shadow(self, open_p: float, close: float, high: float) -> float:
        """اندازه سایه بالا"""
        return high - max(open_p, close)

    def _lower_shadow(self, open_p: float, close: float, low: float) -> float:
        """اندازه سایه پایین"""
        return min(open_p, close) - low

    def detect_doji(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Doji"""
        body = self._body_size(row['open'], row['close'], row['high'], row['low'])
        if body < 0.1:  # بدنه خیلی کوچک
            return True, 'neutral', 0.6
        return False, 'none', 0

    def detect_hammer(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Hammer (صعودی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        lower_shadow = self._lower_shadow(o, c, l)
        upper_shadow = self._upper_shadow(o, c, h)
        range_size = h - l

        if range_size == 0:
            return False, 'none', 0

        # شرایط hammer: سایه پایین بلند، سایه بالا کوتاه
        if lower_shadow > body * 2 and upper_shadow < body * 0.5:
            return True, 'bullish', 0.7
        return False, 'none', 0

    def detect_shooting_star(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Shooting Star (نزولی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        lower_shadow = self._lower_shadow(o, c, l)
        upper_shadow = self._upper_shadow(o, c, h)

        # شرایط shooting star: سایه بالا بلند، سایه پایین کوتاه
        if upper_shadow > body * 2 and lower_shadow < body * 0.5:
            return True, 'bearish', 0.7
        return False, 'none', 0

    def detect_engulfing(self, curr: pd.Series, prev: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Engulfing"""
        curr_body = abs(curr['close'] - curr['open'])
        prev_body = abs(prev['close'] - prev['open'])

        # Bullish Engulfing
        if (self._is_bearish(prev['open'], prev['close']) and
            self._is_bullish(curr['open'], curr['close']) and
            curr['open'] <= prev['close'] and
            curr['close'] >= prev['open'] and
            curr_body > prev_body):
            return True, 'bullish', 0.8

        # Bearish Engulfing
        if (self._is_bullish(prev['open'], prev['close']) and
            self._is_bearish(curr['open'], curr['close']) and
            curr['open'] >= prev['close'] and
            curr['close'] <= prev['open'] and
            curr_body > prev_body):
            return True, 'bearish', 0.8

        return False, 'none', 0

    def detect_morning_star(self, c1: pd.Series, c2: pd.Series, c3: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Morning Star (صعودی - 3 کندل)"""
        # c1: نزولی بزرگ، c2: کوچک (gap down)، c3: صعودی بزرگ
        if (self._is_bearish(c1['open'], c1['close']) and
            self._body_size(c2['open'], c2['close'], c2['high'], c2['low']) < 0.3 and
            self._is_bullish(c3['open'], c3['close']) and
            c3['close'] > (c1['open'] + c1['close']) / 2):
            return True, 'bullish', 0.85
        return False, 'none', 0

    def detect_evening_star(self, c1: pd.Series, c2: pd.Series, c3: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Evening Star (نزولی - 3 کندل)"""
        # c1: صعودی بزرگ، c2: کوچک (gap up)، c3: نزولی بزرگ
        if (self._is_bullish(c1['open'], c1['close']) and
            self._body_size(c2['open'], c2['close'], c2['high'], c2['low']) < 0.3 and
            self._is_bearish(c3['open'], c3['close']) and
            c3['close'] < (c1['open'] + c1['close']) / 2):
            return True, 'bearish', 0.85
        return False, 'none', 0

    def detect_three_white_soldiers(self, c1: pd.Series, c2: pd.Series, c3: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Three White Soldiers (صعودی)"""
        if (self._is_bullish(c1['open'], c1['close']) and
            self._is_bullish(c2['open'], c2['close']) and
            self._is_bullish(c3['open'], c3['close']) and
            c2['close'] > c1['close'] and
            c3['close'] > c2['close']):
            return True, 'bullish', 0.8
        return False, 'none', 0

    def detect_three_black_crows(self, c1: pd.Series, c2: pd.Series, c3: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Three Black Crows (نزولی)"""
        if (self._is_bearish(c1['open'], c1['close']) and
            self._is_bearish(c2['open'], c2['close']) and
            self._is_bearish(c3['open'], c3['close']) and
            c2['close'] < c1['close'] and
            c3['close'] < c2['close']):
            return True, 'bearish', 0.8
        return False, 'none', 0

    def detect_harami(self, curr: pd.Series, prev: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Harami"""
        # Bullish Harami
        if (self._is_bearish(prev['open'], prev['close']) and
            self._is_bullish(curr['open'], curr['close']) and
            curr['open'] > prev['close'] and
            curr['close'] < prev['open']):
            return True, 'bullish', 0.65

        # Bearish Harami
        if (self._is_bullish(prev['open'], prev['close']) and
            self._is_bearish(curr['open'], curr['close']) and
            curr['open'] < prev['close'] and
            curr['close'] > prev['open']):
            return True, 'bearish', 0.65

        return False, 'none', 0

    def detect_piercing_line(self, curr: pd.Series, prev: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Piercing Line (صعودی)"""
        if (self._is_bearish(prev['open'], prev['close']) and
            self._is_bullish(curr['open'], curr['close']) and
            curr['open'] < prev['low'] and
            curr['close'] > (prev['open'] + prev['close']) / 2):
            return True, 'bullish', 0.75
        return False, 'none', 0

    def detect_dark_cloud_cover(self, curr: pd.Series, prev: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Dark Cloud Cover (نزولی)"""
        if (self._is_bullish(prev['open'], prev['close']) and
            self._is_bearish(curr['open'], curr['close']) and
            curr['open'] > prev['high'] and
            curr['close'] < (prev['open'] + prev['close']) / 2):
            return True, 'bearish', 0.75
        return False, 'none', 0

    def detect_spinning_top(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Spinning Top (بلاتکلیفی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        upper_shadow = self._upper_shadow(o, c, h)
        lower_shadow = self._lower_shadow(o, c, l)
        range_size = h - l

        if range_size == 0:
            return False, 'none', 0

        # بدنه کوچک با سایه‌های تقریباً مساوی
        if (body / range_size < 0.3 and
            abs(upper_shadow - lower_shadow) < range_size * 0.2):
            return True, 'neutral', 0.5
        return False, 'none', 0

    def detect_marubozu(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Marubozu (کندل بدون سایه)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        upper_shadow = self._upper_shadow(o, c, h)
        lower_shadow = self._lower_shadow(o, c, l)
        range_size = h - l

        if range_size == 0:
            return False, 'none', 0

        # بدنه بزرگ با سایه‌های خیلی کوچک
        if body / range_size > 0.9:
            direction = 'bullish' if self._is_bullish(o, c) else 'bearish'
            return True, direction, 0.8
        return False, 'none', 0

    def detect_inverted_hammer(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Inverted Hammer (صعودی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        lower_shadow = self._lower_shadow(o, c, l)
        upper_shadow = self._upper_shadow(o, c, h)

        # شرایط inverted hammer: سایه بالا بلند، سایه پایین کوتاه، در انتهای روند نزولی
        if upper_shadow > body * 2 and lower_shadow < body * 0.3:
            return True, 'bullish', 0.65
        return False, 'none', 0

    def detect_hanging_man(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Hanging Man (نزولی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        lower_shadow = self._lower_shadow(o, c, l)
        upper_shadow = self._upper_shadow(o, c, h)

        # شرایط hanging man: سایه پایین بلند، سایه بالا کوچک (مثل hammer ولی نزولی)
        if lower_shadow > body * 2 and upper_shadow < body * 0.5:
            return True, 'bearish', 0.65
        return False, 'none', 0

    def detect_tweezer_top(self, curr: pd.Series, prev: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Tweezer Top (نزولی)"""
        # دو کندل با high تقریباً یکسان
        tolerance = abs(prev['high'] - curr['high']) / max(prev['high'], curr['high'])
        if (tolerance < 0.001 and
            self._is_bullish(prev['open'], prev['close']) and
            self._is_bearish(curr['open'], curr['close'])):
            return True, 'bearish', 0.7
        return False, 'none', 0

    def detect_tweezer_bottom(self, curr: pd.Series, prev: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Tweezer Bottom (صعودی)"""
        # دو کندل با low تقریباً یکسان
        tolerance = abs(prev['low'] - curr['low']) / max(prev['low'], curr['low'])
        if (tolerance < 0.001 and
            self._is_bearish(prev['open'], prev['close']) and
            self._is_bullish(curr['open'], curr['close'])):
            return True, 'bullish', 0.7
        return False, 'none', 0

    def detect_dragonfly_doji(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Dragonfly Doji (صعودی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        lower_shadow = self._lower_shadow(o, c, l)
        upper_shadow = self._upper_shadow(o, c, h)
        range_size = h - l

        if range_size == 0:
            return False, 'none', 0

        # بدنه خیلی کوچک، سایه پایین بلند، بدون سایه بالا
        if (body / range_size < 0.1 and
            lower_shadow > range_size * 0.7 and
            upper_shadow < range_size * 0.1):
            return True, 'bullish', 0.7
        return False, 'none', 0

    def detect_gravestone_doji(self, row: pd.Series) -> Tuple[bool, str, float]:
        """تشخیص الگوی Gravestone Doji (نزولی)"""
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        body = abs(c - o)
        lower_shadow = self._lower_shadow(o, c, l)
        upper_shadow = self._upper_shadow(o, c, h)
        range_size = h - l

        if range_size == 0:
            return False, 'none', 0

        # بدنه خیلی کوچک، سایه بالا بلند، بدون سایه پایین
        if (body / range_size < 0.1 and
            upper_shadow > range_size * 0.7 and
            lower_shadow < range_size * 0.1):
            return True, 'bearish', 0.7
        return False, 'none', 0


class SimpleChartPatternDetector:
    """تشخیص‌دهنده الگوهای چارت (Chart Patterns)"""

    def __init__(self, min_window: int = 20, tolerance: float = 0.02, shoulder_tolerance: float = 0.05):
        self.min_window = min_window
        self.tolerance = tolerance
        self.shoulder_tolerance = shoulder_tolerance

    def detect_double_top(self, highs: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Double Top (نزولی)"""
        if len(highs) < self.min_window:
            return False, 0

        peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.3)
        if len(peaks) < 2:
            return False, 0

        last_two = peaks[-2:]
        peak_heights = highs[last_two]
        height_diff = abs(peak_heights[0] - peak_heights[1]) / max(peak_heights[0], 0.0001)

        if height_diff < self.tolerance:
            return True, 0.75
        return False, 0

    def detect_double_bottom(self, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Double Bottom (صعودی)"""
        if len(lows) < self.min_window:
            return False, 0

        inverted = -lows
        troughs, _ = find_peaks(inverted, distance=5, prominence=np.std(lows) * 0.3)
        if len(troughs) < 2:
            return False, 0

        last_two = troughs[-2:]
        trough_depths = lows[last_two]
        depth_diff = abs(trough_depths[0] - trough_depths[1]) / max(abs(trough_depths[0]), 0.0001)

        if depth_diff < self.tolerance:
            return True, 0.75
        return False, 0

    def detect_head_shoulders(self, highs: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Head and Shoulders (نزولی)"""
        if len(highs) < 30:
            return False, 0

        peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.3)
        if len(peaks) < 3:
            return False, 0

        last_three = peaks[-3:]
        peak_heights = highs[last_three]

        # سر (وسط) باید بالاتر از شانه‌ها باشد
        if peak_heights[1] <= peak_heights[0] or peak_heights[1] <= peak_heights[2]:
            return False, 0

        # شانه‌ها باید ارتفاع مشابه داشته باشند
        shoulder_diff = abs(peak_heights[0] - peak_heights[2]) / max(peak_heights[0], 0.0001)
        if shoulder_diff < self.shoulder_tolerance:
            return True, 0.85
        return False, 0

    def detect_inverse_head_shoulders(self, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Inverse Head and Shoulders (صعودی)"""
        if len(lows) < 30:
            return False, 0

        inverted = -lows
        troughs, _ = find_peaks(inverted, distance=5, prominence=np.std(lows) * 0.3)
        if len(troughs) < 3:
            return False, 0

        last_three = troughs[-3:]
        trough_depths = lows[last_three]

        # سر (وسط) باید پایین‌تر از شانه‌ها باشد
        if trough_depths[1] >= trough_depths[0] or trough_depths[1] >= trough_depths[2]:
            return False, 0

        # شانه‌ها باید عمق مشابه داشته باشند
        shoulder_diff = abs(trough_depths[0] - trough_depths[2]) / max(abs(trough_depths[0]), 0.0001)
        if shoulder_diff < self.shoulder_tolerance:
            return True, 0.85
        return False, 0

    def detect_ascending_triangle(self, highs: np.ndarray, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Ascending Triangle (صعودی)"""
        if len(highs) < self.min_window:
            return False, 0

        peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.2)
        inverted = -lows
        troughs, _ = find_peaks(inverted, distance=5, prominence=np.std(lows) * 0.2)

        if len(peaks) < 2 or len(troughs) < 2:
            return False, 0

        # سقف‌های تقریباً مسطح
        peak_vals = highs[peaks[-3:]] if len(peaks) >= 3 else highs[peaks]
        high_flat = np.std(peak_vals) / np.mean(peak_vals) < 0.02

        # کف‌های صعودی
        trough_vals = lows[troughs[-3:]] if len(troughs) >= 3 else lows[troughs]
        lows_rising = all(trough_vals[i] < trough_vals[i+1] for i in range(len(trough_vals)-1)) if len(trough_vals) > 1 else False

        if high_flat and lows_rising:
            return True, 0.7
        return False, 0

    def detect_descending_triangle(self, highs: np.ndarray, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Descending Triangle (نزولی)"""
        if len(highs) < self.min_window:
            return False, 0

        peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.2)
        inverted = -lows
        troughs, _ = find_peaks(inverted, distance=5, prominence=np.std(lows) * 0.2)

        if len(peaks) < 2 or len(troughs) < 2:
            return False, 0

        # کف‌های تقریباً مسطح
        trough_vals = lows[troughs[-3:]] if len(troughs) >= 3 else lows[troughs]
        low_flat = np.std(trough_vals) / np.mean(trough_vals) < 0.02

        # سقف‌های نزولی
        peak_vals = highs[peaks[-3:]] if len(peaks) >= 3 else highs[peaks]
        highs_falling = all(peak_vals[i] > peak_vals[i+1] for i in range(len(peak_vals)-1)) if len(peak_vals) > 1 else False

        if low_flat and highs_falling:
            return True, 0.7
        return False, 0

    def detect_symmetric_triangle(self, highs: np.ndarray, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Symmetric Triangle (خنثی)"""
        if len(highs) < self.min_window:
            return False, 0

        peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.2)
        inverted = -lows
        troughs, _ = find_peaks(inverted, distance=5, prominence=np.std(lows) * 0.2)

        if len(peaks) < 2 or len(troughs) < 2:
            return False, 0

        peak_vals = highs[peaks[-3:]] if len(peaks) >= 3 else highs[peaks]
        trough_vals = lows[troughs[-3:]] if len(troughs) >= 3 else lows[troughs]

        # سقف‌های نزولی
        highs_falling = all(peak_vals[i] > peak_vals[i+1] for i in range(len(peak_vals)-1)) if len(peak_vals) > 1 else False
        # کف‌های صعودی
        lows_rising = all(trough_vals[i] < trough_vals[i+1] for i in range(len(trough_vals)-1)) if len(trough_vals) > 1 else False

        if highs_falling and lows_rising:
            return True, 0.65
        return False, 0

    def detect_bull_flag(self, closes: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Bull Flag (صعودی)"""
        if len(closes) < 15:
            return False, 0

        # روند صعودی قوی در 10 کندل اول (pole)
        pole = closes[:10]
        pole_change = (pole[-1] - pole[0]) / pole[0]

        # تثبیت/اصلاح کوچک در کندل‌های بعدی (flag)
        flag = closes[10:]
        flag_change = (flag[-1] - flag[0]) / flag[0] if len(flag) > 0 else 0

        if pole_change > 0.03 and -0.02 < flag_change < 0.01:
            return True, 0.7
        return False, 0

    def detect_bear_flag(self, closes: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Bear Flag (نزولی)"""
        if len(closes) < 15:
            return False, 0

        # روند نزولی قوی در 10 کندل اول (pole)
        pole = closes[:10]
        pole_change = (pole[-1] - pole[0]) / pole[0]

        # تثبیت/اصلاح کوچک در کندل‌های بعدی (flag)
        flag = closes[10:]
        flag_change = (flag[-1] - flag[0]) / flag[0] if len(flag) > 0 else 0

        if pole_change < -0.03 and -0.01 < flag_change < 0.02:
            return True, 0.7
        return False, 0

    def detect_cup_and_handle(self, closes: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Cup and Handle (صعودی)"""
        if len(closes) < 30:
            return False, 0

        # پیدا کردن کف Cup
        min_idx = np.argmin(closes[:25])
        if min_idx < 5 or min_idx > 20:
            return False, 0

        # بررسی شکل U
        left_rim = closes[0]
        right_rim = closes[25]
        cup_bottom = closes[min_idx]

        # دو لبه باید تقریباً هم‌ارتفاع باشند
        rim_diff = abs(left_rim - right_rim) / max(left_rim, 0.0001)
        if rim_diff > 0.05:
            return False, 0

        # کف باید پایین‌تر از لبه‌ها باشد
        if cup_bottom >= min(left_rim, right_rim) * 0.97:
            return False, 0

        # Handle: اصلاح کوچک بعد از Cup
        if len(closes) > 25:
            handle = closes[25:]
            handle_drop = (max(handle) - min(handle)) / max(handle)
            if handle_drop < 0.01 or handle_drop > 0.05:
                return False, 0

        return True, 0.8

    def detect_rising_wedge(self, highs: np.ndarray, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Rising Wedge (نزولی)"""
        if len(highs) < self.min_window:
            return False, 0

        # هر دو خط روند صعودی ولی همگرا
        high_slope = (highs[-1] - highs[0]) / len(highs)
        low_slope = (lows[-1] - lows[0]) / len(lows)

        if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
            return True, 0.7
        return False, 0

    def detect_falling_wedge(self, highs: np.ndarray, lows: np.ndarray) -> Tuple[bool, float]:
        """تشخیص الگوی Falling Wedge (صعودی)"""
        if len(highs) < self.min_window:
            return False, 0

        # هر دو خط روند نزولی ولی همگرا
        high_slope = (highs[-1] - highs[0]) / len(highs)
        low_slope = (lows[-1] - lows[0]) / len(lows)

        if high_slope < 0 and low_slope < 0 and high_slope > low_slope:
            return True, 0.7
        return False, 0


class PatternPrecomputer:
    """محاسبه و ذخیره الگوها"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backtest_config = config.get('backtest', {})

        # مسیر خروجی
        self.output_dir = Path(__file__).parent / 'computed_data' / 'patterns'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # مسیر اندیکاتورها
        self.indicators_dir = Path(__file__).parent / 'computed_data' / 'indicators'

        # تایم‌فریم‌ها و سیمبل‌ها
        self.timeframes = config.get('data_fetching', {}).get('timeframes', ['5m', '15m', '1h', '4h'])
        self.symbols = (
            self.backtest_config.get('symbols') or
            config.get('signal_processing', {}).get('symbols') or
            ['BTC-USDT']
        )

        # تشخیص‌دهنده الگو
        self.detector = SimpleCandlePatternDetector()
        self.chart_detector = SimpleChartPatternDetector()

        logger.info(f"PatternPrecomputer initialized")
        logger.info(f"  Symbols: {self.symbols}")
        logger.info(f"  Timeframes: {self.timeframes}")

    def load_indicators(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """لود اندیکاتورهای از پیش محاسبه شده"""
        filepath = self.indicators_dir / symbol / f"{timeframe}_indicators.parquet"
        if filepath.exists():
            return pd.read_parquet(filepath)
        return None

    def detect_all_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """تشخیص همه الگوها برای هر کندل"""
        n = len(df)
        result = df.copy()

        # ستون‌های الگو (کندلی و چارت)
        pattern_names = [
            # الگوهای کندلی
            'doji', 'hammer', 'shooting_star', 'engulfing',
            'morning_star', 'evening_star', 'three_white_soldiers',
            'three_black_crows', 'harami', 'piercing_line', 'dark_cloud_cover',
            'spinning_top', 'marubozu', 'inverted_hammer', 'hanging_man',
            'tweezer_top', 'tweezer_bottom', 'dragonfly_doji', 'gravestone_doji',
            # الگوهای چارت
            'double_top', 'double_bottom', 'head_shoulders', 'inverse_head_shoulders',
            'ascending_triangle', 'descending_triangle', 'symmetric_triangle',
            'bull_flag', 'bear_flag', 'cup_and_handle', 'rising_wedge', 'falling_wedge'
        ]

        for pname in pattern_names:
            result[f'pattern_{pname}'] = 0
            result[f'pattern_{pname}_direction'] = 'none'
            result[f'pattern_{pname}_score'] = 0.0

        # پیمایش کندل به کندل
        for i in tqdm(range(3, n), desc="    Detecting patterns", unit="candle"):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2]

            # الگوهای تک کندلی
            found, direction, score = self.detector.detect_doji(curr)
            if found:
                result.loc[result.index[i], 'pattern_doji'] = 1
                result.loc[result.index[i], 'pattern_doji_direction'] = direction
                result.loc[result.index[i], 'pattern_doji_score'] = score

            found, direction, score = self.detector.detect_hammer(curr)
            if found:
                result.loc[result.index[i], 'pattern_hammer'] = 1
                result.loc[result.index[i], 'pattern_hammer_direction'] = direction
                result.loc[result.index[i], 'pattern_hammer_score'] = score

            found, direction, score = self.detector.detect_shooting_star(curr)
            if found:
                result.loc[result.index[i], 'pattern_shooting_star'] = 1
                result.loc[result.index[i], 'pattern_shooting_star_direction'] = direction
                result.loc[result.index[i], 'pattern_shooting_star_score'] = score

            # الگوهای دو کندلی
            found, direction, score = self.detector.detect_engulfing(curr, prev)
            if found:
                result.loc[result.index[i], 'pattern_engulfing'] = 1
                result.loc[result.index[i], 'pattern_engulfing_direction'] = direction
                result.loc[result.index[i], 'pattern_engulfing_score'] = score

            found, direction, score = self.detector.detect_harami(curr, prev)
            if found:
                result.loc[result.index[i], 'pattern_harami'] = 1
                result.loc[result.index[i], 'pattern_harami_direction'] = direction
                result.loc[result.index[i], 'pattern_harami_score'] = score

            found, direction, score = self.detector.detect_piercing_line(curr, prev)
            if found:
                result.loc[result.index[i], 'pattern_piercing_line'] = 1
                result.loc[result.index[i], 'pattern_piercing_line_direction'] = direction
                result.loc[result.index[i], 'pattern_piercing_line_score'] = score

            found, direction, score = self.detector.detect_dark_cloud_cover(curr, prev)
            if found:
                result.loc[result.index[i], 'pattern_dark_cloud_cover'] = 1
                result.loc[result.index[i], 'pattern_dark_cloud_cover_direction'] = direction
                result.loc[result.index[i], 'pattern_dark_cloud_cover_score'] = score

            # الگوهای سه کندلی
            found, direction, score = self.detector.detect_morning_star(prev2, prev, curr)
            if found:
                result.loc[result.index[i], 'pattern_morning_star'] = 1
                result.loc[result.index[i], 'pattern_morning_star_direction'] = direction
                result.loc[result.index[i], 'pattern_morning_star_score'] = score

            found, direction, score = self.detector.detect_evening_star(prev2, prev, curr)
            if found:
                result.loc[result.index[i], 'pattern_evening_star'] = 1
                result.loc[result.index[i], 'pattern_evening_star_direction'] = direction
                result.loc[result.index[i], 'pattern_evening_star_score'] = score

            found, direction, score = self.detector.detect_three_white_soldiers(prev2, prev, curr)
            if found:
                result.loc[result.index[i], 'pattern_three_white_soldiers'] = 1
                result.loc[result.index[i], 'pattern_three_white_soldiers_direction'] = direction
                result.loc[result.index[i], 'pattern_three_white_soldiers_score'] = score

            found, direction, score = self.detector.detect_three_black_crows(prev2, prev, curr)
            if found:
                result.loc[result.index[i], 'pattern_three_black_crows'] = 1
                result.loc[result.index[i], 'pattern_three_black_crows_direction'] = direction
                result.loc[result.index[i], 'pattern_three_black_crows_score'] = score

            # الگوهای جدید تک کندلی
            found, direction, score = self.detector.detect_spinning_top(curr)
            if found:
                result.loc[result.index[i], 'pattern_spinning_top'] = 1
                result.loc[result.index[i], 'pattern_spinning_top_direction'] = direction
                result.loc[result.index[i], 'pattern_spinning_top_score'] = score

            found, direction, score = self.detector.detect_marubozu(curr)
            if found:
                result.loc[result.index[i], 'pattern_marubozu'] = 1
                result.loc[result.index[i], 'pattern_marubozu_direction'] = direction
                result.loc[result.index[i], 'pattern_marubozu_score'] = score

            found, direction, score = self.detector.detect_inverted_hammer(curr)
            if found:
                result.loc[result.index[i], 'pattern_inverted_hammer'] = 1
                result.loc[result.index[i], 'pattern_inverted_hammer_direction'] = direction
                result.loc[result.index[i], 'pattern_inverted_hammer_score'] = score

            found, direction, score = self.detector.detect_hanging_man(curr)
            if found:
                result.loc[result.index[i], 'pattern_hanging_man'] = 1
                result.loc[result.index[i], 'pattern_hanging_man_direction'] = direction
                result.loc[result.index[i], 'pattern_hanging_man_score'] = score

            found, direction, score = self.detector.detect_dragonfly_doji(curr)
            if found:
                result.loc[result.index[i], 'pattern_dragonfly_doji'] = 1
                result.loc[result.index[i], 'pattern_dragonfly_doji_direction'] = direction
                result.loc[result.index[i], 'pattern_dragonfly_doji_score'] = score

            found, direction, score = self.detector.detect_gravestone_doji(curr)
            if found:
                result.loc[result.index[i], 'pattern_gravestone_doji'] = 1
                result.loc[result.index[i], 'pattern_gravestone_doji_direction'] = direction
                result.loc[result.index[i], 'pattern_gravestone_doji_score'] = score

            # الگوهای جدید دو کندلی
            found, direction, score = self.detector.detect_tweezer_top(curr, prev)
            if found:
                result.loc[result.index[i], 'pattern_tweezer_top'] = 1
                result.loc[result.index[i], 'pattern_tweezer_top_direction'] = direction
                result.loc[result.index[i], 'pattern_tweezer_top_score'] = score

            found, direction, score = self.detector.detect_tweezer_bottom(curr, prev)
            if found:
                result.loc[result.index[i], 'pattern_tweezer_bottom'] = 1
                result.loc[result.index[i], 'pattern_tweezer_bottom_direction'] = direction
                result.loc[result.index[i], 'pattern_tweezer_bottom_score'] = score

            # الگوهای چارت (نیاز به پنجره داده)
            window_size = 30
            if i >= window_size:
                window_highs = df['high'].iloc[i-window_size:i].values
                window_lows = df['low'].iloc[i-window_size:i].values
                window_closes = df['close'].iloc[i-window_size:i].values

                # Double Top
                found, score = self.chart_detector.detect_double_top(window_highs)
                if found:
                    result.loc[result.index[i], 'pattern_double_top'] = 1
                    result.loc[result.index[i], 'pattern_double_top_direction'] = 'bearish'
                    result.loc[result.index[i], 'pattern_double_top_score'] = score

                # Double Bottom
                found, score = self.chart_detector.detect_double_bottom(window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_double_bottom'] = 1
                    result.loc[result.index[i], 'pattern_double_bottom_direction'] = 'bullish'
                    result.loc[result.index[i], 'pattern_double_bottom_score'] = score

                # Head and Shoulders
                found, score = self.chart_detector.detect_head_shoulders(window_highs)
                if found:
                    result.loc[result.index[i], 'pattern_head_shoulders'] = 1
                    result.loc[result.index[i], 'pattern_head_shoulders_direction'] = 'bearish'
                    result.loc[result.index[i], 'pattern_head_shoulders_score'] = score

                # Inverse Head and Shoulders
                found, score = self.chart_detector.detect_inverse_head_shoulders(window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_inverse_head_shoulders'] = 1
                    result.loc[result.index[i], 'pattern_inverse_head_shoulders_direction'] = 'bullish'
                    result.loc[result.index[i], 'pattern_inverse_head_shoulders_score'] = score

                # Ascending Triangle
                found, score = self.chart_detector.detect_ascending_triangle(window_highs, window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_ascending_triangle'] = 1
                    result.loc[result.index[i], 'pattern_ascending_triangle_direction'] = 'bullish'
                    result.loc[result.index[i], 'pattern_ascending_triangle_score'] = score

                # Descending Triangle
                found, score = self.chart_detector.detect_descending_triangle(window_highs, window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_descending_triangle'] = 1
                    result.loc[result.index[i], 'pattern_descending_triangle_direction'] = 'bearish'
                    result.loc[result.index[i], 'pattern_descending_triangle_score'] = score

                # Symmetric Triangle
                found, score = self.chart_detector.detect_symmetric_triangle(window_highs, window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_symmetric_triangle'] = 1
                    result.loc[result.index[i], 'pattern_symmetric_triangle_direction'] = 'neutral'
                    result.loc[result.index[i], 'pattern_symmetric_triangle_score'] = score

                # Bull Flag
                found, score = self.chart_detector.detect_bull_flag(window_closes)
                if found:
                    result.loc[result.index[i], 'pattern_bull_flag'] = 1
                    result.loc[result.index[i], 'pattern_bull_flag_direction'] = 'bullish'
                    result.loc[result.index[i], 'pattern_bull_flag_score'] = score

                # Bear Flag
                found, score = self.chart_detector.detect_bear_flag(window_closes)
                if found:
                    result.loc[result.index[i], 'pattern_bear_flag'] = 1
                    result.loc[result.index[i], 'pattern_bear_flag_direction'] = 'bearish'
                    result.loc[result.index[i], 'pattern_bear_flag_score'] = score

                # Cup and Handle
                found, score = self.chart_detector.detect_cup_and_handle(window_closes)
                if found:
                    result.loc[result.index[i], 'pattern_cup_and_handle'] = 1
                    result.loc[result.index[i], 'pattern_cup_and_handle_direction'] = 'bullish'
                    result.loc[result.index[i], 'pattern_cup_and_handle_score'] = score

                # Rising Wedge
                found, score = self.chart_detector.detect_rising_wedge(window_highs, window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_rising_wedge'] = 1
                    result.loc[result.index[i], 'pattern_rising_wedge_direction'] = 'bearish'
                    result.loc[result.index[i], 'pattern_rising_wedge_score'] = score

                # Falling Wedge
                found, score = self.chart_detector.detect_falling_wedge(window_highs, window_lows)
                if found:
                    result.loc[result.index[i], 'pattern_falling_wedge'] = 1
                    result.loc[result.index[i], 'pattern_falling_wedge_direction'] = 'bullish'
                    result.loc[result.index[i], 'pattern_falling_wedge_score'] = score

        return result

    def precompute_all(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """محاسبه الگوها برای همه سیمبل‌ها و تایم‌فریم‌ها"""
        results = {}

        for symbol in self.symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {symbol}")
            logger.info(f"{'='*60}")

            results[symbol] = {}

            for tf in self.timeframes:
                logger.info(f"\n  Timeframe: {tf}")

                # لود داده با اندیکاتورها
                df = self.load_indicators(symbol, tf)
                if df is None or df.empty:
                    logger.warning(f"    No indicator data for {symbol}/{tf}")
                    continue

                logger.info(f"    Loaded {len(df)} candles")

                # تشخیص الگوها
                df_with_patterns = self.detect_all_patterns(df)
                results[symbol][tf] = df_with_patterns

                # آمار
                pattern_cols = [c for c in df_with_patterns.columns
                               if c.startswith('pattern_') and not c.endswith('_direction') and not c.endswith('_score')]
                total = sum(df_with_patterns[col].sum() for col in pattern_cols)
                logger.info(f"    Found {int(total)} patterns in {len(pattern_cols)} types")

        return results

    def save_results(self, results: Dict, format: str = 'parquet'):
        """ذخیره نتایج"""
        for symbol, tf_data in results.items():
            symbol_dir = self.output_dir / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)

            for tf, df in tf_data.items():
                if format == 'parquet':
                    filepath = symbol_dir / f"{tf}_patterns.parquet"
                    df.to_parquet(filepath)
                else:
                    filepath = symbol_dir / f"{tf}_patterns.csv"
                    df.to_csv(filepath)

                logger.info(f"  Saved: {filepath}")

        # Metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'symbols': list(results.keys()),
            'timeframes': self.timeframes,
            'candlestick_patterns': [
                'doji', 'hammer', 'shooting_star', 'engulfing',
                'morning_star', 'evening_star', 'three_white_soldiers',
                'three_black_crows', 'harami', 'piercing_line', 'dark_cloud_cover',
                'spinning_top', 'marubozu', 'inverted_hammer', 'hanging_man',
                'tweezer_top', 'tweezer_bottom', 'dragonfly_doji', 'gravestone_doji'
            ],
            'chart_patterns': [
                'double_top', 'double_bottom', 'head_shoulders', 'inverse_head_shoulders',
                'ascending_triangle', 'descending_triangle', 'symmetric_triangle',
                'bull_flag', 'bear_flag', 'cup_and_handle', 'rising_wedge', 'falling_wedge'
            ]
        }

        with open(self.output_dir / 'metadata.yaml', 'w') as f:
            yaml.dump(metadata, f)


def load_config(config_path: str) -> Dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
    """ترکیب دو config"""
    result = base_config.copy()
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description='Pre-compute patterns')
    parser.add_argument('--format', type=str, default='parquet', choices=['parquet', 'csv'])
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  PATTERN PRE-COMPUTATION")
    print("="*70 + "\n")

    # لود config از فولدر محلی
    local_config_path = Path(__file__).parent / 'configs' / 'config.yaml'
    local_backtest_config_path = Path(__file__).parent / 'configs' / 'config_backtest_v2.yaml'

    logger.info(f"Loading local config: {local_config_path}")
    config = load_config(local_config_path)

    if local_backtest_config_path.exists():
        logger.info(f"Loading local backtest config: {local_backtest_config_path}")
        backtest_config = load_config(local_backtest_config_path)
        config = merge_configs(config, backtest_config)

    # اجرا
    precomputer = PatternPrecomputer(config)
    results = precomputer.precompute_all()
    precomputer.save_results(results, format=args.format)

    print("\n" + "="*70)
    print("  PATTERN PRE-COMPUTATION COMPLETED!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
