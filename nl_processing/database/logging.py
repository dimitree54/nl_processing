import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"nl_processing.database.{name}")
