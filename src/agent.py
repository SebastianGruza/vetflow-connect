"""Compatibility wrapper for the refactored application entry point."""

from __future__ import annotations

from .core.app import VERSION, main, run_discover, setup_logging

__all__ = ["VERSION", "main", "run_discover", "setup_logging"]
