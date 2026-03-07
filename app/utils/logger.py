"""
日志模块

提供：
- 统一配置的日志实例
- 结构化日志支持
- JSON 格式日志输出
- 性能计时功能
"""

import logging
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict
from functools import wraps
from contextlib import contextmanager

from app.config.settings import PROJECT_ROOT


def _fix_windows_encoding():
    """修复 Windows 控制台编码问题"""
    import platform
    if platform.system() == "Windows":
        # 设置 stdout/stderr 为 UTF-8
        import io
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding='utf-8', errors='replace'
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding='utf-8', errors='replace'
        )


# 模块导入时修复编码
_fix_windows_encoding()


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 基础信息
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    结构化日志器
    
    使用方法：
        from app.utils.logger import StructuredLogger
        
        log = StructuredLogger("my_module")
        
        # 普通日志
        log.info("操作完成")
        
        # 结构化日志
        log.info("用户登录", user_id=123, ip="192.168.1.1")
        
        # 计时
        with log.timer("数据处理"):
            # 处理数据
            pass
    """
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._configure()
    
    def _configure(self):
        """配置日志器"""
        if self._logger.handlers:
            return
        
        self._logger.setLevel(logging.DEBUG)
        
        # 控制台 handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))
        self._logger.addHandler(console)
        
        # 文件 handler
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{datetime.now():%Y%m%d}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        self._logger.addHandler(fh)
        
        # JSON 文件 handler（可选）
        json_log_file = log_dir / f"{datetime.now():%Y%m%d}_structured.jsonl"
        json_fh = logging.FileHandler(json_log_file, encoding="utf-8")
        json_fh.setLevel(logging.DEBUG)
        json_fh.setFormatter(StructuredFormatter())
        self._logger.addHandler(json_fh)
    
    def _log(self, level: int, message: str, **kwargs):
        """记录日志"""
        extra = {'extra_data': kwargs} if kwargs else {}
        self._logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        kwargs['exception'] = True
        self._logger.exception(message, extra={'extra_data': kwargs})
    
    @contextmanager
    def timer(self, operation: str, **kwargs):
        """
        计时上下文管理器
        
        Args:
            operation: 操作名称
            **kwargs: 额外数据
        """
        start_time = time.time()
        self.debug(f"开始: {operation}", **kwargs)
        
        try:
            yield
            duration = time.time() - start_time
            self.info(f"完成: {operation}", duration_ms=round(duration * 1000, 2), **kwargs)
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"失败: {operation}",
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                **kwargs
            )
            raise
    
    def log_operation(self, operation: str, success: bool, **kwargs):
        """
        记录操作结果
        
        Args:
            operation: 操作名称
            success: 是否成功
            **kwargs: 额外数据
        """
        level = logging.INFO if success else logging.WARNING
        self._log(level, f"{operation}: {'成功' if success else '失败'}", success=success, **kwargs)


def get_logger(name: str) -> logging.Logger:
    """获取统一配置的 logger 实例（兼容旧接口）"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    # 控制台 handler — INFO 级别 (使用 UTF-8 编码)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    # 确保编码正确
    console.stream = sys.stdout
    logger.addHandler(console)

    # 文件 handler — DEBUG 级别
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{datetime.now():%Y%m%d}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    return logger


def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志器"""
    return StructuredLogger(name)


# 装饰器：记录函数执行
def log_execution(logger_name: str = None):
    """
    函数执行日志装饰器
    
    Args:
        logger_name: 日志器名称（默认使用函数所在模块）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = logger_name or func.__module__
            log = StructuredLogger(name)
            
            with log.timer(func.__name__):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
