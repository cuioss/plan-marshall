#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The foreign gate's branch rule, as its two documents state it.

The rule lives in exactly two readable places: the pre-archive gate standard
(``archive-plan.md``, the surface the finalize step follows) and the gate
module's own docstring. Each states the CURRENT rule — the default branch is
never a change's branch, an undeclared repository checked out on it is an
unresolvable ``branch_is_default`` row, and a declaration wins over a checkout on
the default branch — and each carries no narrative of what the rule used to be,
so a reader cannot take an obsolete statement for the behaviour.
"""

import re
from pathlib import Path

from conftest import PROJECT_ROOT

_STANDARD = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'archive-plan.md'
)
_MODULE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
    / 'foreign_pr_gate.py'
)

_RULE = "The default branch is never a change's branch"
_DECLARATION_WINS = 'a declaration wins over a checkout on the default branch'


def _normalized(path: Path) -> str:
    """The file's text with whitespace collapsed, so a wrapped sentence matches."""
    return re.sub(r'\s+', ' ', path.read_text(encoding='utf-8'))


def _module_docstring(text: str) -> str:
    """The module docstring, taken from the already-normalized source text."""
    start = text.index('"""') + 3
    end = text.index('"""', start)
    return text[start:end]


def test_the_standard_states_the_default_branch_rule_exactly_once():
    # "Once" is the criterion: a second copy is a second statement that can
    # drift from this one, so the count is asserted rather than mere presence.
    text = _normalized(_STANDARD)
    occurrences = text.count(_RULE)
    assert occurrences == 1, (
        f'{_STANDARD.name} states the default-branch rule {occurrences} time(s); '
        f'the rule belongs in exactly one place in the document'
    )
    assert _DECLARATION_WINS in text
    assert 'branch_is_default' in text


def test_the_standard_carries_no_obsolete_rule_wording():
    text = _normalized(_STANDARD)
    assert 'still holds' not in text, (
        f'{_STANDARD.name} still carries the "still holds" narrative, which states a past '
        f'rationale rather than the current rule'
    )
    assert 'is not the answer' not in text


def test_the_module_docstring_states_the_same_rule():
    docstring = _module_docstring(_normalized(_MODULE))
    assert _RULE in docstring
    assert _DECLARATION_WINS in docstring
    assert 'branch_is_default' in docstring


def test_the_module_docstring_names_no_plain_main_as_a_change_branch():
    # The removed wording named a plain ``main`` as one of the branches a change
    # may live on, which the default-branch rule contradicts.
    docstring = _module_docstring(_normalized(_MODULE))
    assert 'plain ``main``' not in docstring
    assert 'plain `main`' not in docstring
