# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the upgrade-flow Stage 2 reconcile sub-steps against silent regression.

Stage 2's fine reconcile steps (`sync-defaults`, `steps-sort`, `normalize-keys`)
live in ``references/upgrade-flow.md`` as the doc-level expansion of the coarse
``reconcile-marshal-json`` sub-step the planner emits — they are driven by the LLM
router, not enumerated in ``upgrade.py``. This test is the only detector for the
failure mode D5 closes: Stage 2 losing the **unconditional** top-level canonicalizer
(`normalize-keys`) so a non-canonical key order survives the post-version-bump flow.
It pins that `normalize-keys` is invoked in Stage 2, and LAST — after the two
conditional-write reconcile verbs (D1(c): normalize-keys after any key-adding op).
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_UPGRADE_FLOW = (
    _REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'marshall-steward'
    / 'references'
    / 'upgrade-flow.md'
)


def _stage2_block() -> str:
    """Return the text of the '## Stage 2: reconcile-config' section only."""
    text = _UPGRADE_FLOW.read_text(encoding='utf-8')
    start = text.index('## Stage 2: reconcile-config')
    end = text.index('## Stage 3', start)
    return text[start:end]


def _invocation_index(block: str, verb: str) -> int:
    """Return the position of the manage-config invocation of ``verb`` in ``block``."""
    return block.index(f'plan-marshall:manage-config:manage-config {verb}')


def test_stage2_invokes_normalize_keys_after_sync_defaults_and_steps_sort():
    block = _stage2_block()

    sync_defaults = _invocation_index(block, 'sync-defaults')
    steps_sort = _invocation_index(block, 'steps-sort')
    normalize_keys = _invocation_index(block, 'normalize-keys')

    # All three present, and normalize-keys is LAST — after both conditional-write verbs.
    assert normalize_keys > steps_sort > sync_defaults
