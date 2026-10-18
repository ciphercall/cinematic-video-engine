"""Structured logging utility."""

import logging
import sys


def setup_logger(level: str = "INFO") -> logging.Logger:
    """Create a configured logger for the application."""
    logger = logging.getLogger("cinema")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logger.level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        # Handle unicode on Windows console
        handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)
        logger.addHandler(handler)

    return logger
