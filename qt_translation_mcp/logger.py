"""日志配置模块"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "qt_translation_mcp", log_dir: str = None) -> logging.Logger:
    """配置日志系统
    
    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录，如果为 None 则只输出到 stderr
    
    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台输出 (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 主日志文件
        log_file = log_path / f"qt_translation_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 错误日志文件
        error_log_file = log_path / f"qt_translation_error_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 模块名称，如果为 None 则返回根 logger
    
    Returns:
        logger 实例
    """
    if name:
        return logging.getLogger(f"qt_translation_mcp.{name}")
    return logging.getLogger("qt_translation_mcp")
