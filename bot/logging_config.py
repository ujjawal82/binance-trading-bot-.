from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_file: str | Path = "logs/trading_bot.log", level: int = logging.INFO) -> logging.Logger:
    """Configure a project logger that writes useful audit logs to a file.

    The handler is replaced when this function is called with a different file,
    so the CLI can create separate MARKET/LIMIT evidence logs.
    """
    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)
    logger.propagate = False

    # Remove old handlers to avoid duplicate lines when tests/CLI call repeatedly.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
