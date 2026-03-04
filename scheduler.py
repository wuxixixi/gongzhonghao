"""
定时调度器模块

提供两种调度方式：
1. 内置调度器：在程序运行时定时执行
2. Windows 任务计划：通过 schtasks 命令注册

执行时间：每天上午 10:00
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Callable
import threading

from utils.logger import get_logger

_log = get_logger("scheduler")


class DailyScheduler:
    """每日定时调度器

    用于在程序运行时等待到指定时间然后执行任务。
    适用于作为 Windows 任务计划程序的入口脚本。
    """

    def __init__(self, hour: int = 10, minute: int = 0):
        """初始化调度器

        Args:
            hour: 执行小时 (0-23)
            minute: 执行分钟 (0-59)
        """
        self.target_hour = hour
        self.target_minute = minute

    def get_next_run_time(self) -> datetime:
        """计算下次执行时间

        Returns:
            下次执行的 datetime 对象
        """
        now = datetime.now()
        target = now.replace(hour=self.target_hour, minute=self.target_minute, second=0, microsecond=0)

        # 如果今天的时间已过，则返回明天的同一时间
        if target <= now:
            target = target + timedelta(days=1)

        return target

    def wait_until_target_time(self) -> bool:
        """等待到目标时间

        Returns:
            True 如果成功等待，False 如果被中断
        """
        next_run = self.get_next_run_time()
        wait_seconds = (next_run - datetime.now()).total_seconds()

        _log.info("下次执行时间: %s", next_run.strftime("%Y-%m-%d %H:%M:%S"))
        _log.info("等待 %d 秒后开始执行...", int(wait_seconds))

        # 使用短间隔以便能够优雅退出
        check_interval = 60  # 每分钟检查一次
        waited = 0

        while waited < wait_seconds:
            time.sleep(min(check_interval, wait_seconds - waited))
            waited += check_interval

            remaining = wait_seconds - waited
            if remaining > 0 and remaining <= 60:
                _log.info("即将执行，剩余 %d 秒...", int(remaining))

        _log.info("到达目标时间，开始执行任务")
        return True

    def run_at_time(self, task: Callable[[], None], run_immediately: bool = False) -> None:
        """在指定时间执行任务

        Args:
            task: 要执行的任务函数
            run_immediately: 如果为 True，立即执行而不等待（用于调试）
        """
        if run_immediately:
            _log.info("调试模式：立即执行任务")
            task()
            return

        # 等待到目标时间
        if self.wait_until_target_time():
            task()


def register_scheduled_task(task_name: str, script_path: str, time_str: str = "10:00") -> str:
    """注册 Windows 定时任务

    Args:
        task_name: 任务名称，如 "WechatAIDaily"
        script_path: 脚本路径，如 "D:\\公众号\\auto_generator.py"
        time_str: 执行时间，如 "10:00"

    Returns:
        注册结果消息
    """
    import subprocess

    # 构建 schtasks 命令
    cmd = [
        "schtasks",
        "/create",
        "/tn", task_name,
        "/tr", f'python "{script_path}"',
        "/sc", "daily",
        "/st", time_str,
        "/f",  # 如果存在则覆盖
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            _log.info("定时任务注册成功: %s at %s", task_name, time_str)
            return f"定时任务 '{task_name}' 已注册，每天 {time_str} 执行"
        else:
            _log.error("定时任务注册失败: %s", result.stderr)
            return f"注册失败: {result.stderr}"
    except Exception as e:
        _log.error("注册定时任务异常: %s", e)
        return f"注册异常: {e}"


def delete_scheduled_task(task_name: str) -> str:
    """删除 Windows 定时任务

    Args:
        task_name: 任务名称

    Returns:
        删除结果消息
    """
    import subprocess

    cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            _log.info("定时任务已删除: %s", task_name)
            return f"定时任务 '{task_name}' 已删除"
        else:
            _log.warning("删除定时任务失败: %s", result.stderr)
            return f"删除失败: {result.stderr}"
    except Exception as e:
        _log.error("删除定时任务异常: %s", e)
        return f"删除异常: {e}"


def check_scheduled_task(task_name: str) -> Optional[dict]:
    """查询定时任务状态

    Args:
        task_name: 任务名称

    Returns:
        任务信息字典，如果不存在返回 None
    """
    import subprocess

    cmd = ["schtasks", "/query", "/tn", task_name, "/fo", "csv", "/v"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                # 解析 CSV
                headers = [h.strip('"') for h in lines[0].split(",")]
                values = [v.strip('"') for v in lines[1].split(",")]

                info = dict(zip(headers, values))
                return {
                    "name": info.get("TaskName", ""),
                    "next_run": info.get("Next Run Time", ""),
                    "status": info.get("Status", ""),
                    "last_run": info.get("Last Run Time", ""),
                    "last_result": info.get("Last Result", ""),
                }
        return None
    except Exception as e:
        _log.error("查询定时任务异常: %s", e)
        return None
