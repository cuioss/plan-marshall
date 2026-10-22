#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D3/D4 of PLAN-LB-88 — the statements about the enforcement scope are true.

Three documents make claims a reader acts on:

* ``pretooluse-enforcement.md`` must record the ``git grep`` decision D1 of
  PLAN-LB-79 asked for (the file-search git verbs join the enforced set through
  R2, not the R5 wrapper table) and must state the scope exactly — the three
  signals, the repository marker, the 24-hour lane marker, and which harness each
  applies to;
* the same document must say how an operator verifies that the hook is actually
  installed, because the install is machine-local and a fresh clone has none;
* ``CLAUDE.md`` § Standalone Plan Lane must stop saying the gate fires only inside
  a plan context — since PLAN-LB-79 D3 the hook binds a root session of this
  repository too — while keeping the lane's own reason for the relaxations (a
  fresh clone carries no hook).

These are doc tests: each asserts a sentence, so a doc edit that drops the
statement fails here.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

_ENFORCEMENT_DOC = (
    REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md'
)
_CLAUDE_MD = REPO_ROOT / 'CLAUDE.md'

#: The decision sentence D1 of PLAN-LB-79 asked for and never recorded.
_GIT_GREP_DECISION = "Decision — the file-search git verbs join the hook's enforced set"


def test_the_git_grep_decision_is_recorded() -> None:
    """``git grep`` / ``git -C … grep`` have a recorded decision and a reason."""
    text = _ENFORCEMENT_DOC.read_text(encoding='utf-8')
    assert _GIT_GREP_DECISION in text, 'the enforcement document records no decision for the file-search git verbs'
    assert '`git grep`' in text and '`git -C … grep`' in text, 'the decision must name both spellings'
    decision_at = text.index(_GIT_GREP_DECISION)
    decision_paragraph = text[decision_at : decision_at + 1600]
    assert 'R2' in decision_paragraph, 'the decision must name the rule family each harness uses'
    assert 'outside what the guard enforces' in decision_paragraph.lower(), (
        'the decision must state the OpenCode gap instead of claiming a binding it does not provide'
    )
    assert 'reason' in decision_paragraph.lower(), 'the decision must carry its reason'


def test_claude_md_no_longer_claims_the_gate_is_plan_context_only() -> None:
    """The Standalone Plan Lane row says what is true and keeps the lane's reason."""
    text = _CLAUDE_MD.read_text(encoding='utf-8')
    assert 'fires only inside a plan context' not in text, (
        'CLAUDE.md still says the PreToolUse gate fires only inside a plan context'
    )
    row = next((line for line in text.splitlines() if line.startswith('| Bash: one command per call')), None)
    assert row is not None, 'CLAUDE.md lost the Bash hard-rule row'
    assert 'root session of this repository' in row, 'the row must say a root session of this repository is bound'
    assert 'fresh clone' in row, 'the row must keep the lane reason (a fresh clone carries no hook)'
    assert 'OpenCode guard' in row, (
        'the row must not claim the rule is absent on a harness whose guard ships in the repository'
    )


def test_the_enforcement_document_names_every_scope_signal_and_the_install_check() -> None:
    """The scope statement is exact, and the install is verifiable by the operator."""
    text = _ENFORCEMENT_DOC.read_text(encoding='utf-8')
    for signal in ('Signal 1', 'Signal 2', 'Signal 3'):
        assert signal in text, f'the scope statement does not name {signal!r}'
    assert 'repository marker' in text, 'the scope statement does not name the repository marker'
    assert '24-hour lane marker' in text, 'the scope statement does not name the 24-hour lane marker'
    assert 'Claude PreToolUse hook' in text and 'OpenCode guard' in text, (
        'the scope statement does not say which harness each signal applies to'
    )
    assert 'Verifying the install' in text, 'the document carries no installation-verification procedure'
    assert 'health-check --checks display' in text, 'the verification procedure must name the health check'
    assert '.claude/settings.local.json' in text, 'the verification procedure must name the install surface'
    assert 'not installed in this checkout' in text, (
        'the document must not claim an installation this checkout does not have'
    )
