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

from conftest import MARKETPLACE_ROOT, load_script_module

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'summarize-invariants.py'
)


def _load_summarize_module():
    """Load ``summarize-invariants.py`` as a module for function-level tests.

    The hyphenated filename cannot be imported, so it is resolved by
    (bundle, skill, file). Unregistered, so this copy cannot displace one
    another suite holds.
    """
    return load_script_module(
        'plan-marshall', 'plan-retrospective', 'summarize-invariants.py', 'summarize_invariants_module', register=False
    )


_summarize = _load_summarize_module()
