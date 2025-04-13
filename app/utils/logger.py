"""
Copyright (c) 2023-2025 Timothy Jaeryang Baek
All rights reserved.

This file is licensed under the BSD 3-Clause License.
See the LICENSE and NOTICE files for the full license text.
"""

import json
import logging
import sys
from typing import TYPE_CHECKING

from loguru import logger

from app.settings import (
    # AUDIT_LOG_FILE_ROTATION_SIZE,
    # AUDIT_LOG_LEVEL,
    # AUDIT_LOGS_FILE_PATH,
    GLOBAL_LOG_LEVEL,
    LOG_FILE
)


if TYPE_CHECKING:
    from loguru import Record


def stdout_format(record: "Record") -> str:
    """
    Generates a formatted string for log records that are output to the console. This format includes a timestamp, log level, source location (module, function, and line), the log message, and any extra data (serialized as JSON).

    Parameters:
    record (Record): A Loguru record that contains logging details including time, level, name, function, line, message, and any extra context.
    Returns:
    str: A formatted log string intended for stdout.
    """
    record["extra"]["extra_json"] = json.dumps(record["extra"])
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level> - {extra[extra_json]}"
        "\n{exception}"
    )


class InterceptHandler(logging.Handler):
    """
    Intercepts log records from Python's standard logging module
    and redirects them to Loguru's logger.
    """

    def emit(self, record):
        """
        Called by the standard logging module for each log event.
        It transforms the standard `LogRecord` into a format compatible with Loguru
        and passes it to Loguru's logger.
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def start_logger():
    """
    Initializes and configures Loguru's logger with distinct handlers:

    A console (stdout) handler for general log messages (excluding those marked as auditable).
    A file handler for general logs with rotation.
    An optional file handler for audit logs if audit logging is enabled.
    Additionally, this function reconfigures Python's standard logging to route through Loguru and adjusts logging levels for Uvicorn.

    Parameters:
    enable_audit_logging (bool): Determines whether audit-specific log entries should be recorded to file.
    """
    logger.remove()

    # 콘솔 로거 추가
    logger.add(
        sys.stdout,
        level=GLOBAL_LOG_LEVEL,
        format=stdout_format,
        filter=lambda record: "auditable" not in record["extra"],        
    )
    
    # 파일 핸들러 추가 - 일반 로그용 (매일 자정에 로테이션)
    logger.add(
        LOG_FILE,  # 로그 파일 경로
        level=GLOBAL_LOG_LEVEL,
        rotation="00:00",  # 매일 자정에 로테이션
        retention="30 days",  # 30일간 보관
        compression="zip",  # 압축 방식
        format=stdout_format,  # 같은 포맷 사용 또는 다른 포맷 정의 가능
        filter=lambda record: "auditable" not in record["extra"],
        encoding="utf-8"
    )

    logging.basicConfig(
        handlers=[InterceptHandler()], force=True
    )
    for uvicorn_logger_name in ["uvicorn", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.setLevel(GLOBAL_LOG_LEVEL)
        uvicorn_logger.handlers = []
    for uvicorn_logger_name in ["uvicorn.access"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.setLevel(GLOBAL_LOG_LEVEL)
        uvicorn_logger.handlers = [InterceptHandler()]

    logger.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")
    logger.info(f"로그 파일 핸들러 초기화 완료: logs/app.log")