"""tmaudit.__main__ — allow `python -m tmaudit ...`."""
import sys
from .cli import main

sys.exit(main())