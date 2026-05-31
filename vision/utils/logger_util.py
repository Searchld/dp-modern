import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from queue import Queue
from pathlib import Path


class LoggerUtil:
    """
    生产级日志系统：
    - QueueHandler 防止多线程/多进程冲突
    - QueueListener 单线程写文件（避免锁竞争）
    - 自动防重复初始化
    """

    _loggers = {}
    _listener = None
    _queue = None
    _lock = threading.Lock()
    _initialized = False

    DEFAULT_LOG_DIR = "./logs"
    DEFAULT_LOG_LEVEL = logging.INFO

    @classmethod
    def _init_global_listener(cls, log_dir):
        """全局只初始化一次 listener"""

        if cls._initialized:
            return

        with cls._lock:
            if cls._initialized:
                return

            cls._queue = Queue(-1)

            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / "app.log"

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(process)d | %(threadName)s | "
                "%(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # 文件 handler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=2 * 1024 * 1024,
                backupCount=500,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)

            # 控制台 handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)

            cls._listener = QueueListener(
                cls._queue,
                file_handler,
                console_handler,
                respect_handler_level=True,
            )
            cls._listener.start()

            cls._initialized = True

    @classmethod
    def get_logger(cls, name="app", log_dir=DEFAULT_LOG_DIR):
        """
        获取 logger（线程/进程安全）
        """

        cls._init_global_listener(log_dir)

        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(cls.DEFAULT_LOG_LEVEL)
        logger.propagate = False
        logger.handlers.clear()

        # 关键：所有日志进入队列
        queue_handler = QueueHandler(cls._queue)
        logger.addHandler(queue_handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def shutdown(cls):
        """优雅关闭（可选）"""
        if cls._listener:
            cls._listener.stop()
