"""Tests for _build_shared utilities."""

import importlib
import sys
from pathlib import Path

# Add script path for imports
_SCRIPT_DIR = Path(__file__).resolve().parents[3] / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'extension-api' / 'scripts'
sys.path.insert(0, str(_SCRIPT_DIR))

_build_shared = importlib.import_module('_build_shared')


class TestGetBashTimeout:
    """Tests for get_bash_timeout()."""

    def test_adds_buffer_to_inner_timeout(self):
        result = _build_shared.get_bash_timeout(300)
        assert result == 330  # 300 + 30 buffer

    def test_small_timeout(self):
        result = _build_shared.get_bash_timeout(10)
        assert result == 40  # 10 + 30 buffer

    def test_zero_timeout(self):
        result = _build_shared.get_bash_timeout(0)
        assert result == 30  # 0 + 30 buffer

    def test_buffer_constant_is_30(self):
        assert _build_shared.OUTER_TIMEOUT_BUFFER == 30
