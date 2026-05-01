"""Shared utilities for civic-proof-il (settings, logging, ...)."""

from .logging import configure_logging
from .settings import Settings, get_settings

__all__ = ["Settings", "configure_logging", "get_settings"]
