# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared-harness collection pointer.

The behaviours formerly pinned here now live in dedicated collection units
that import their shared constants from ``_shared_harness_fixtures``:

- ``test_shared_harness_parse_ns_defaults`` pins parser defaults.
- ``test_shared_harness_parse_ns_no_seam`` pins the named no-seam error.
- ``test_shared_harness_marshal_presets`` pins distinct marshal baselines.
- ``test_shared_harness_zero_guard`` pins the no-zero-test whole-tree guard.

This module keeps the historic import path valid and pins the carve shape
itself, so a missing split unit fails here rather than silently shrinking
the suite.
"""

from pathlib import Path

_SPLIT_UNITS = (
    'test_shared_harness_parse_ns_defaults.py',
    'test_shared_harness_parse_ns_no_seam.py',
    'test_shared_harness_marshal_presets.py',
    'test_shared_harness_zero_guard.py',
)


def test_split_units_are_present():
    """The carve shape holds: every split unit exists beside this pointer."""
    root = Path(__file__).resolve().parent
    missing = [name for name in _SPLIT_UNITS if not (root / name).is_file()]
    assert missing == [], f'split collection units missing beside pointer: {missing}'
