#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-133 D2 — the functional-review workflow records the D3e decision.

The D4c decision (a relaxed assertion that keeps its count stays the author's
reading) is recorded in the workflow document. The D3e decision beside it —
``criteria-authorize`` wired as the re-freeze/authorization verb, ``verify-first``
removed — was made but never written down, so the document recorded one choice
and not the other. Document-only: the behaviour is in the verbs the doc names.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import get_skill_dir


def _normalized(path: Path) -> str:
    """The document's text with whitespace collapsed, so a wrapped sentence matches."""
    return re.sub(r'\s+', ' ', path.read_text(encoding='utf-8'))


def test_the_functional_review_workflow_records_the_d3e_decision() -> None:
    """The decision, the wired verb and the removed alternative all appear."""
    text = _normalized(get_skill_dir('plan-marshall', 'phase-6-finalize') / 'workflow' / 'functional-review.md')

    assert 'PLAN-LB-70 D3e' in text, 'the D3e decision is recorded nowhere'
    assert 'criteria-authorize' in text, 'the wired authorization verb is not named'
    assert 'verify-first' in text, 'the removed alternative is not named'
    assert 'PLAN-LB-70 D4c' in text, 'the D4c record the D3e record sits beside was dropped'
