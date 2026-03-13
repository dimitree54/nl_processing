"""Module logger setup for extract_word_details package."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the extract_word_details module."""
    return logging.getLogger(f"nl_processing.extract_word_details.{name}")
