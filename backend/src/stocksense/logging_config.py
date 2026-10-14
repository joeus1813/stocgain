"""Standard-library UTC logging configuration."""

import logging
import time


def configure_logging(level: str) -> None:
    """Configure UTC timestamps and key-value application messages."""
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        level=level,
        format="%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
