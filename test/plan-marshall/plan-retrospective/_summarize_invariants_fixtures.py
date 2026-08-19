# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``summarize invariants`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))


SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'summarize-invariants.py'
)


def _load_summarize_module():
    """Import ``summarize-invariants.py`` as a module for function-level tests."""
    spec = importlib.util.spec_from_file_location('summarize_invariants_module', SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_summarize = _load_summarize_module()
