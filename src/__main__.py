"""Allow running as `python -m src`."""

try:
    from .core.app import main
except ImportError:
    from core.app import main

main()
