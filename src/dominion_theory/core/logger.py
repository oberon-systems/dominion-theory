"""
Logger Initialization Module
"""

import logging
import os


def get_logger(
    name: str,
    log_level: str = os.getenv('APP_LOG_LEVEL', 'DEBUG'),
) -> logging.Logger:
    """
    Return logger instance
    """
    fmt = '[%(asctime)s] %(name)s[%(process)d][%(levelname)s]: %(message)s'
    logging.basicConfig(
        format=fmt,
        level=log_level.upper(),
    )

    return logging.getLogger(name)
