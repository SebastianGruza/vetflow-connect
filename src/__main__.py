"""Allow running as: python -m scripts.vetflow_connect"""

try:
    from .agent import main
except ImportError:
    from agent import main

main()
