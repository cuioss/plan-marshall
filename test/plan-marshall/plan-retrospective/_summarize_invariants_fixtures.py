# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``summarize invariants`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for ``summarize-invariants.py``.

The script reads phase-handshake captures from ``<plan_dir>/handshakes.toon``
(canonical storage owned by ``plan-marshall:plan-marshall:phase_handshake``)
rather than ``status.metadata.phase_handshake``. Fixtures in
``_plan_retrospective_fixtures.py`` materialize the file in the same TOON
shape ``_handshake_store.save_rows``
emits in production.
"""


from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


from conftest import MARKETPLACE_ROOT  # noqa: E402

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
