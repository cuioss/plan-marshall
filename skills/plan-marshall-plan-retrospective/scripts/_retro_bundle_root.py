# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-source resolution of the retrospective's fragment-bundle root.

The retrospective writes every aspect fragment to ``{fragment_dir}`` — the
``work`` directory under the bundle root ``collect-fragments init`` resolves —
and a script that READS a sibling aspect's fragment must look under that same
root. Two private copies of the rule drift apart silently: the archived-mode
root moved to a synthetic tmp directory and a reader that still derived it from
the archived plan directory never saw the current run's fragment. The rule
therefore lives here once, and both the bundle's producer
(``collect-fragments.py``) and its readers (``check-manifest-consistency.py``)
call it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from file_ops import base_path

_ARCHIVED_TMP_SUBDIR = 'plan-retrospective'
_FRAGMENT_DIR_NAME = 'work'


def resolve_bundle_root(mode: str, plan_id: str) -> Path:
    """Return the directory the bundle and its fragments live under for ``mode``.

    Live mode roots at the plan directory. Archived mode roots at a synthetic
    per-plan directory under the OS tmpdir — never at the archived plan
    directory, which is the audit's read-only input.

    Args:
        mode: Either ``'live'`` or ``'archived'``.
        plan_id: Plan identifier. Required for both modes.

    Returns:
        Absolute path to the bundle root.

    Raises:
        ValueError: On unknown ``mode`` or missing ``plan_id``.
    """
    if not plan_id:
        raise ValueError('--plan-id is required')
    if mode == 'live':
        return base_path('plans', plan_id).resolve()
    if mode == 'archived':
        return (Path(tempfile.gettempdir()) / _ARCHIVED_TMP_SUBDIR / f'plan-{plan_id}').resolve()
    raise ValueError(f'Unknown mode: {mode!r}')


def resolve_fragment_dir(mode: str, plan_id: str) -> Path:
    """Return ``{fragment_dir}`` — the directory every aspect fragment is written to.

    It is the ``work`` directory under :func:`resolve_bundle_root`: the plan
    directory's ``work`` in live mode, the synthetic tmp root's ``work`` in
    archived mode. The bundle file itself lives in the same directory.
    """
    return resolve_bundle_root(mode, plan_id) / _FRAGMENT_DIR_NAME
