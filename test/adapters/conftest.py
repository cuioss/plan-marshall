"""Test configuration for adapter tests.

Adds the project root to sys.path so marketplace.adapters can be imported as a package.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
