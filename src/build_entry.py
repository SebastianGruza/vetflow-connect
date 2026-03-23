"""PyInstaller entry point — explicit imports so the bundler sees all modules."""
import sys
import os

# Ensure the bundled directory is in path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Explicit imports — PyInstaller traces these
import agent  # noqa: F401
import config  # noqa: F401
import hl7_parser  # noqa: F401
import hl7_listener  # noqa: F401
import vetflow_client  # noqa: F401
import xml_builder  # noqa: F401
import auto_discover  # noqa: F401

from agent import main
main()
