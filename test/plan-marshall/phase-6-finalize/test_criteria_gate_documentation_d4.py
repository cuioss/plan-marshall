#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-133 D4 — the documents state what the criteria gate does.

Two documents described a gate they no longer had:

* ``triage.md`` said a criterion is open until the review's sealed verdict
  grades it met — omitting the authorized, superseded, review-closed and
  review-dropped states the gate applies;
* the ``review_support`` row of the phase-6-finalize scripts table listed three
  of the module's six verbs and named none of its three private modules.

Both are judged on the documents only; the behaviour lives in the scripts the
documents describe and is covered by their own modules.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import get_skill_dir

_SCRIPTS_TABLE = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'


def _normalized(path: Path) -> str:
    """The document's text with whitespace collapsed, so a wrapped sentence matches."""
    return re.sub(r'\s+', ' ', path.read_text(encoding='utf-8'))


def _review_support_row(path: Path) -> str:
    """The scripts-table row for ``review_support.py``, whitespace-collapsed."""
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('| `scripts/review_support.py`'):
            return re.sub(r'\s+', ' ', line)
    raise AssertionError('the scripts table carries no review_support.py row')


def test_triage_states_the_closing_states_and_the_exemptions() -> None:
    text = _normalized(get_skill_dir('plan-marshall', 'plan-marshall') / 'workflow' / 'triage.md')

    for state in ('review_dropped', 'review_closed', 'superseded', 'authoriz'):
        assert state in text, f'triage.md never names the {state} closing state'
    assert 'sealed verdict' in text, 'triage.md never names the sealed verdict'


def test_triage_no_longer_states_the_old_rule() -> None:
    text = _normalized(get_skill_dir('plan-marshall', 'plan-marshall') / 'workflow' / 'triage.md')

    assert 'A criterion is open until the review' not in text, 'triage.md still states the retired single-closing rule'


def test_the_review_support_row_lists_every_verb_and_the_private_modules() -> None:
    row = _review_support_row(_SCRIPTS_TABLE)

    for verb in ('attribution', 'domains', 'validate', 'author-verdict', 'open-criteria', 'test-integrity'):
        assert verb in row, f'the review_support row omits the {verb} verb'
    for module in ('_review_support_validate.py', '_review_support_attribution.py', '_review_support_integrity.py'):
        assert module in row, f'the review_support row names no {module}'
