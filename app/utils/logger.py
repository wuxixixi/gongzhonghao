import logging
import sys
from pathlib import Path
from datetime import datetime
from app.config.settings import PROJECT_ROOT


def get_logger(name: str) -> logging.Logger:
    """获取统一配置的 logger 实例"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    # 控制台 handler — INFO 级别
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
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
