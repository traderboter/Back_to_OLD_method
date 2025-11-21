"""
Time Simulator - شبیه‌سازی حرکت در زمان برای Backtest
این ماژول مسئول مدیریت جریان زمان در طول Backtest است
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Callable
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TimeSpeed(Enum):
    """
    سرعت شبیه‌سازی زمان
    """
    REAL_TIME = "real_time"  # زمان واقعی (کند)
    FAST = "fast"  # سریع (بدون تاخیر)
    CUSTOM = "custom"  # سرعت سفارشی


class TimeSimulator:
    """
    کلاس شبیه‌سازی‌کننده زمان برای Backtest
    مسئول حرکت در زمان و مدیریت چرخه‌های شبیه‌سازی
    """

    def __init__(self, start_date: datetime, end_date: datetime,
                 step_minutes: int = 5,
                 speed: str = "fast"):
        """
        مقداردهی اولیه TimeSimulator

        Args:
            start_date: تاریخ شروع شبیه‌سازی
            end_date: تاریخ پایان شبیه‌سازی
            step_minutes: گام زمانی (دقیقه)
            speed: سرعت شبیه‌سازی ('fast' یا 'real_time')
        """
        self.start_date = start_date
        self.end_date = end_date
        self.current_time = start_date
        self.step_minutes = step_minutes
        self.step_delta = timedelta(minutes=step_minutes)
        self.speed = TimeSpeed.FAST if speed == "fast" else TimeSpeed.REAL_TIME

        # محاسبه تعداد کل گام‌ها
        self.total_steps = self._calculate_total_steps()
        self.current_step = 0

        # آمار
        self.stats = {
            'total_time_span': self.end_date - self.start_date,
            'total_steps': self.total_steps,
            'steps_completed': 0,
            'time_elapsed': timedelta(0),
            'start_timestamp': datetime.now(),
            'paused': False
        }

        # Callback برای رویدادهای زمانی
        self.on_day_change: Optional[Callable] = None
        self.on_hour_change: Optional[Callable] = None
        self.on_step: Optional[Callable] = None

        # متغیرهای کمکی
        self._last_day = start_date.day
        self._last_hour = start_date.hour
        self._paused = False

        logger.info(
            f"TimeSimulator initialized: {start_date} to {end_date} "
            f"(step: {step_minutes}m, total steps: {self.total_steps})"
        )

    def _calculate_total_steps(self) -> int:
        """
        محاسبه تعداد کل گام‌ها

        Returns:
            تعداد گام‌ها
        """
        time_diff = self.end_date - self.start_date
        total_minutes = int(time_diff.total_seconds() / 60)
        return total_minutes // self.step_minutes

    def step(self, steps: int = 1) -> datetime:
        """
        حرکت به جلو در زمان

        Args:
            steps: تعداد گام‌های حرکت (پیش‌فرض: 1)

        Returns:
            زمان فعلی جدید
        """
        if self._paused:
            logger.warning("Simulator is paused. Call resume() first.")
            return self.current_time

        if self.is_finished():
            logger.warning("Simulation already finished")
            return self.current_time

        # حرکت در زمان
        for _ in range(steps):
            if self.current_time >= self.end_date:
                break

            previous_time = self.current_time
            self.current_time += self.step_delta
            self.current_step += 1
            self.stats['steps_completed'] += 1

            # بررسی تغییر روز
            if self.current_time.day != self._last_day:
                self._last_day = self.current_time.day
                if self.on_day_change:
                    self.on_day_change(self.current_time)

            # بررسی تغییر ساعت
            if self.current_time.hour != self._last_hour:
                self._last_hour = self.current_time.hour
                if self.on_hour_change:
                    self.on_hour_change(self.current_time)

            # فراخوانی callback گام
            if self.on_step:
                self.on_step(previous_time, self.current_time)

        # به‌روزرسانی زمان سپری شده
        self.stats['time_elapsed'] = datetime.now() - self.stats['start_timestamp']

        return self.current_time

    def step_to_time(self, target_time: datetime) -> datetime:
        """
        حرکت به یک زمان مشخص

        Args:
            target_time: زمان هدف

        Returns:
            زمان فعلی جدید
        """
        if target_time < self.current_time:
            logger.warning(f"Cannot step backward to {target_time}")
            return self.current_time

        if target_time > self.end_date:
            logger.warning(f"Target time {target_time} exceeds end date")
            target_time = self.end_date

        # محاسبه تعداد گام‌ها
        time_diff = target_time - self.current_time
        steps_needed = int(time_diff.total_seconds() / 60) // self.step_minutes

        if steps_needed > 0:
            return self.step(steps_needed)

        return self.current_time

    def step_by_duration(self, duration: timedelta) -> datetime:
        """
        حرکت به اندازه یک بازه زمانی

        Args:
            duration: بازه زمانی (timedelta)

        Returns:
            زمان فعلی جدید
        """
        target_time = self.current_time + duration
        return self.step_to_time(target_time)

    def get_current_time(self) -> datetime:
        """
        دریافت زمان فعلی شبیه‌سازی

        Returns:
            datetime زمان فعلی
        """
        return self.current_time

    def is_finished(self) -> bool:
        """
        بررسی پایان شبیه‌سازی

        Returns:
            True اگر به انتها رسیده باشد
        """
        return self.current_time >= self.end_date

    def get_progress(self) -> float:
        """
        محاسبه درصد پیشرفت

        Returns:
            درصد پیشرفت (0.0 تا 1.0)
        """
        if self.total_steps == 0:
            return 1.0

        return min(1.0, self.current_step / self.total_steps)

    def get_progress_percentage(self) -> float:
        """
        محاسبه درصد پیشرفت به صورت عددی

        Returns:
            درصد پیشرفت (0 تا 100)
        """
        return self.get_progress() * 100

    def get_remaining_time_estimate(self) -> Optional[timedelta]:
        """
        تخمین زمان باقیمانده تا پایان (زمان واقعی، نه زمان شبیه‌سازی)

        Returns:
            timedelta زمان باقیمانده یا None
        """
        if self.current_step == 0:
            return None

        elapsed_real_time = self.stats['time_elapsed']
        progress = self.get_progress()

        if progress == 0:
            return None

        total_estimated = elapsed_real_time / progress
        remaining = total_estimated - elapsed_real_time

        return remaining

    def get_remaining_simulation_time(self) -> timedelta:
        """
        زمان باقیمانده در شبیه‌سازی (زمان مجازی)

        Returns:
            timedelta زمان باقیمانده شبیه‌سازی
        """
        return self.end_date - self.current_time

    def pause(self):
        """
        متوقف کردن شبیه‌سازی
        """
        self._paused = True
        self.stats['paused'] = True
        logger.info(f"Simulation paused at {self.current_time}")

    def resume(self):
        """
        ادامه شبیه‌سازی پس از توقف
        """
        self._paused = False
        self.stats['paused'] = False
        logger.info(f"Simulation resumed from {self.current_time}")

    def is_paused(self) -> bool:
        """
        بررسی وضعیت توقف

        Returns:
            True اگر متوقف شده باشد
        """
        return self._paused

    def reset(self):
        """
        بازنشانی شبیه‌سازی به وضعیت اولیه
        """
        self.current_time = self.start_date
        self.current_step = 0
        self.stats['steps_completed'] = 0
        self.stats['time_elapsed'] = timedelta(0)
        self.stats['start_timestamp'] = datetime.now()
        self._paused = False
        self._last_day = self.start_date.day
        self._last_hour = self.start_date.hour

        logger.info("Simulation reset to start")

    def skip_to_date(self, target_date: datetime):
        """
        پرش به یک تاریخ مشخص بدون پردازش گام‌های میانی

        Args:
            target_date: تاریخ هدف
        """
        if target_date < self.start_date or target_date > self.end_date:
            logger.error(f"Target date {target_date} is out of range")
            return

        if target_date < self.current_time:
            logger.warning("Cannot skip backward, use reset() first")
            return

        # محاسبه تعداد گام‌های پرش شده
        time_diff = target_date - self.current_time
        steps_skipped = int(time_diff.total_seconds() / 60) // self.step_minutes

        self.current_time = target_date
        self.current_step += steps_skipped
        self.stats['steps_completed'] += steps_skipped

        logger.info(f"Skipped to {target_date} ({steps_skipped} steps)")

    def get_statistics(self) -> Dict:
        """
        دریافت آمار شبیه‌سازی

        Returns:
            دیکشنری حاوی آمار
        """
        stats = self.stats.copy()
        stats.update({
            'current_time': self.current_time,
            'current_step': self.current_step,
            'progress_percent': self.get_progress_percentage(),
            'remaining_simulation_time': self.get_remaining_simulation_time(),
            'is_finished': self.is_finished(),
            'is_paused': self.is_paused()
        })

        remaining_real_time = self.get_remaining_time_estimate()
        if remaining_real_time:
            stats['estimated_remaining_real_time'] = remaining_real_time

        return stats

    def get_time_range(self, hours_back: int = 24) -> tuple:
        """
        دریافت بازه زمانی گذشته از زمان فعلی

        Args:
            hours_back: تعداد ساعات گذشته

        Returns:
            (start_time, end_time)
        """
        end_time = self.current_time
        start_time = end_time - timedelta(hours=hours_back)

        # محدود کردن به بازه شبیه‌سازی
        if start_time < self.start_date:
            start_time = self.start_date

        return (start_time, end_time)

    def should_process(self, process_interval_seconds: int) -> bool:
        """
        بررسی اینکه آیا زمان پردازش رسیده است یا خیر

        Args:
            process_interval_seconds: فاصله زمانی پردازش (ثانیه)

        Returns:
            True اگر زمان پردازش رسیده باشد
        """
        # محاسبه تعداد گام‌های معادل این فاصله زمانی
        interval_minutes = process_interval_seconds // 60
        interval_steps = max(1, interval_minutes // self.step_minutes)

        # بررسی اینکه آیا به اندازه کافی گام برداشته‌ایم
        return self.current_step % interval_steps == 0

    def format_current_time(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        فرمت کردن زمان فعلی به رشته

        Args:
            format_str: فرمت دلخواه

        Returns:
            رشته فرمت شده
        """
        return self.current_time.strftime(format_str)

    def get_simulation_duration(self) -> timedelta:
        """
        دریافت کل مدت زمان شبیه‌سازی

        Returns:
            timedelta کل بازه زمانی
        """
        return self.end_date - self.start_date

    def is_market_open(self, market_open_hour: int = 0, market_close_hour: int = 24) -> bool:
        """
        بررسی باز بودن بازار (برای بازارهای با ساعت کاری خاص)

        Args:
            market_open_hour: ساعت باز شدن بازار
            market_close_hour: ساعت بسته شدن بازار

        Returns:
            True اگر بازار باز باشد
        """
        current_hour = self.current_time.hour

        if market_close_hour > market_open_hour:
            return market_open_hour <= current_hour < market_close_hour
        else:
            # بازار 24 ساعته یا overnight
            return current_hour >= market_open_hour or current_hour < market_close_hour

    def is_weekend(self) -> bool:
        """
        بررسی آخر هفته بودن (شنبه یا یکشنبه)

        Returns:
            True اگر آخر هفته باشد
        """
        return self.current_time.weekday() >= 5  # 5=Saturday, 6=Sunday

    def get_current_day_name(self) -> str:
        """
        دریافت نام روز هفته

        Returns:
            نام روز
        """
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.current_time.weekday()]

    def __str__(self) -> str:
        """
        نمایش رشته‌ای از وضعیت شبیه‌سازی
        """
        return (
            f"TimeSimulator: {self.format_current_time()} "
            f"({self.get_progress_percentage():.1f}% complete, "
            f"step {self.current_step}/{self.total_steps})"
        )

    def __repr__(self) -> str:
        """
        نمایش تکنیکال
        """
        return (
            f"TimeSimulator(start={self.start_date}, end={self.end_date}, "
            f"current={self.current_time}, step={self.step_minutes}m)"
        )


class TimeSimulatorWithCheckpoints(TimeSimulator):
    """
    نسخه پیشرفته TimeSimulator با قابلیت ذخیره Checkpoint
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkpoints: Dict[str, Dict] = {}

    def create_checkpoint(self, name: str):
        """
        ایجاد یک checkpoint از وضعیت فعلی

        Args:
            name: نام checkpoint
        """
        self.checkpoints[name] = {
            'current_time': self.current_time,
            'current_step': self.current_step,
            'stats': self.stats.copy()
        }
        logger.info(f"Checkpoint '{name}' created at {self.current_time}")

    def restore_checkpoint(self, name: str) -> bool:
        """
        بازگردانی به یک checkpoint

        Args:
            name: نام checkpoint

        Returns:
            True در صورت موفقیت
        """
        if name not in self.checkpoints:
            logger.error(f"Checkpoint '{name}' not found")
            return False

        cp = self.checkpoints[name]
        self.current_time = cp['current_time']
        self.current_step = cp['current_step']
        self.stats = cp['stats'].copy()

        logger.info(f"Restored checkpoint '{name}' from {self.current_time}")
        return True

    def list_checkpoints(self) -> list:
        """
        دریافت لیست checkpoint‌ها

        Returns:
            لیست نام checkpoint‌ها
        """
        return list(self.checkpoints.keys())

    def delete_checkpoint(self, name: str):
        """
        حذف یک checkpoint

        Args:
            name: نام checkpoint
        """
        if name in self.checkpoints:
            del self.checkpoints[name]
            logger.info(f"Checkpoint '{name}' deleted")