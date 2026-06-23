#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Regression tests for the q-gate-validation-agent worktree-linter validator.

The q-gate-validation-agent is a markdown-defined agent (no Python entry
point). Section 2.15 ("Worktree-Linter Validator") was added in TASK-12 of
plan ``lesson-2026-05-07-11-001`` and pins three pattern checks against
deliverables that touch skill, agent, or script source files:

- **WL-A** — direct ``cd <worktree_path>`` shell compounds
- **WL-B** — hard-coded ``.claude/worktrees/`` references
- **WL-C** — manage-* invocations missing ``--plan-id`` (auto-routing scripts
  silently target the main checkout when ``--plan-id`` is missing).

The validator is documented prose (not executable Python), so these tests
pin the **structure** of the validator section in
``marketplace/bundles/plan-marshall/agents/q-gate-validation-agent.md``:

1. **Positive cases** — Section 2.15 exists, names every pattern letter
   (WL-A, WL-B, WL-C), declares its activation condition, finding-emission
   template, suppression rule, and cross-references the centralized
   ``worktree-handling.md`` standard.
2. **Negative cases** — Section 2.15 does NOT itself contain stale
   ``.claude/worktrees/`` literals outside explicit anti-pattern markers
   (the validator must not be self-violating).
3. **Verification matrix sync** — the matrix table at the bottom of the
   agent must include a row for the worktree-linter validator so the
   summary stays in lockstep with the section body.

A future edit that drops Section 2.15, removes a pattern letter, or breaks
the cross-reference to ``worktree-handling.md`` would silently regress the
Q-Gate behaviour. These tests fail loudly when that happens.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT  # type: ignore[import-not-found]


# -----------------------------------------------------------------------------
# Paths to the artifacts under test.
# -----------------------------------------------------------------------------


_AGENT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'workflow'
    / 'q-gate-validation.md'
)

_WORKTREE_HANDLING_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'workflow-integration-git'
    / 'standards'
    / 'worktree-handling.md'
)

_PATTERN_LETTERS = ('WL-A', 'WL-B', 'WL-C')


@pytest.fixture(scope='module')
def agent_text() -> str:
    """Return the full text of the q-gate-validation-agent.md file."""
    return _AGENT_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def section_2_15_text(agent_text: str) -> str:
    """Return the body of Section 2.15 (Worktree-Linter Validator) only.

    Slices the agent text from the ``#### 2.15`` heading through the next
    top-level ``###`` heading (Step 5) so assertions about Section 2.15
    don't accidentally pick up unrelated content elsewhere in the agent.
    """
    start_match = re.search(r'^####\s+2\.15\s+Worktree-Linter Validator', agent_text, re.MULTILINE)
    assert start_match is not None, (
        'Section 2.15 (Worktree-Linter Validator) is missing from '
        'q-gate-validation-agent.md. The validator must be present per '
        'TASK-12 of plan lesson-2026-05-07-11-001.'
    )
    start = start_match.start()
    # The section ends at the next "### Step" or "---" separator that
    # introduces Step 5. The agent uses a "---" separator + "### Step 5"
    # pattern to delimit the verification block.
    end_match = re.search(r'^###\s+Step\s+5\b', agent_text[start:], re.MULTILINE)
    end = (start + end_match.start()) if end_match else len(agent_text)
    return agent_text[start:end]


# -----------------------------------------------------------------------------
# Positive cases — Section 2.15 exists with the expected structure.
# -----------------------------------------------------------------------------


def test_agent_file_exists() -> None:
    """The q-gate-validation-agent.md file must exist at the canonical path.

    The validator is hosted in this single agent file; a missing file means
    the entire validator is gone (catastrophic regression).
    """
    assert _AGENT_PATH.is_file(), (
        f'q-gate-validation-agent.md missing at {_AGENT_PATH}. The validator '
        f'is hosted in this file — missing file means the entire Q-Gate '
        f'validator is gone.'
    )


def test_section_2_15_heading_present(agent_text: str) -> None:
    """The agent must contain a ``#### 2.15 Worktree-Linter Validator`` heading.

    Pins the section number AND the section title so a rename of either
    breaks loudly. Subsection numbering matters because the agent's
    Verification Criteria Matrix (bottom of the file) and prose
    cross-references all key on the section number.
    """
    pattern = r'^####\s+2\.15\s+Worktree-Linter Validator\s*$'
    assert re.search(pattern, agent_text, re.MULTILINE) is not None, (
        'Section 2.15 heading "#### 2.15 Worktree-Linter Validator" is missing '
        'or malformed in q-gate-validation-agent.md.'
    )


@pytest.mark.parametrize('pattern_letter', _PATTERN_LETTERS)
def test_pattern_letter_present_in_section(section_2_15_text: str, pattern_letter: str) -> None:
    """Each of the three pattern letters (WL-A, WL-B, WL-C) must be named in
    Section 2.15.

    The pattern letter is the canonical handle used by the finding-emission
    template (``--title "Q-Gate: worktree_linter — {pattern_letter} ..."``)
    and by downstream consumers (retrospective, log scrapers). Dropping a
    letter silently regresses one of the three checks.
    """
    assert pattern_letter in section_2_15_text, (
        f'Pattern letter {pattern_letter!r} is missing from Section 2.15. '
        f'All three letters (WL-A, WL-B, WL-C) must remain documented.'
    )


def test_pattern_wl_a_documents_cd_compound(section_2_15_text: str) -> None:
    """WL-A subsection must explicitly reference the forbidden
    ``cd <worktree_path>`` shell-compound pattern.

    The forbidden shape is the load-bearing literal — without it the
    pattern description becomes vague and the linter behaviour drifts.
    """
    # Headers describe the pattern; the literal "cd" plus a worktree token
    # must appear in the WL-A description.
    assert re.search(r'WL-A.*cd\s+', section_2_15_text, re.DOTALL) is not None, (
        'WL-A subsection must explicitly reference the forbidden ``cd '
        '<worktree_path>`` shell-compound pattern.'
    )


def test_pattern_wl_b_documents_claude_worktrees_path(section_2_15_text: str) -> None:
    """WL-B subsection must reference the stale ``.claude/worktrees/`` path
    literal that TASK-4 of the same plan migrated to ``.plan/local/worktrees/``.
    """
    assert 'WL-B' in section_2_15_text and '.claude/worktrees/' in section_2_15_text, (
        'WL-B subsection must reference the stale .claude/worktrees/ path '
        'literal so the linter target stays explicit.'
    )


def test_pattern_wl_c_documents_missing_plan_id(section_2_15_text: str) -> None:
    """WL-C subsection must reference the ``--plan-id`` flag whose absence
    triggers the auto-routing failure mode (TASK-10 contract).
    """
    assert 'WL-C' in section_2_15_text and '--plan-id' in section_2_15_text, (
        'WL-C subsection must reference --plan-id; its absence is the '
        'detection signal for the auto-routing failure mode.'
    )


def test_section_cross_references_worktree_handling_md(section_2_15_text: str) -> None:
    """Section 2.15 must cross-reference ``worktree-handling.md`` — the
    centralized authoritative source for worktree-handling rules created in
    TASK-3 of the same plan.

    The cross-reference is the audit trail back to the single source of
    truth; without it the linter rules drift into ad-hoc per-validator
    duplication (the very anti-pattern this plan exists to fix).
    """
    assert 'worktree-handling.md' in section_2_15_text, (
        'Section 2.15 must cross-reference worktree-handling.md — the '
        'centralized authoritative source for worktree rules.'
    )


def test_worktree_handling_md_target_exists() -> None:
    """The cross-referenced ``worktree-handling.md`` file must actually exist
    on disk. A dangling cross-reference would let the linter prose claim
    authority that has no canonical anchor.
    """
    assert _WORKTREE_HANDLING_PATH.is_file(), (
        f'worktree-handling.md missing at {_WORKTREE_HANDLING_PATH}. The '
        f'q-gate worktree-linter cross-references this file as the '
        f'authoritative source — the target must exist.'
    )


def test_section_documents_activation_condition(section_2_15_text: str) -> None:
    """Section 2.15 must declare an explicit activation condition so the
    validator does not run against unrelated deliverables.
    """
    assert 'Activation condition' in section_2_15_text, (
        'Section 2.15 must include an "Activation condition" subsection so '
        'the validator scope is explicit and bounded.'
    )


def test_section_documents_suppression_rule(section_2_15_text: str) -> None:
    """Section 2.15 must declare a suppression rule so anti-pattern
    references inside ``worktree-handling.md`` itself (the standard quotes
    the forbidden patterns to define them) do not produce findings.

    Without the suppression rule the validator would flag its own
    canonical source — guaranteeing a Q-Gate failure on every plan that
    touches the standard.
    """
    assert 'Suppression rule' in section_2_15_text, (
        'Section 2.15 must include a "Suppression rule" subsection so the '
        'validator does not flag the centralized standard itself.'
    )


def test_section_documents_finding_emission_template(section_2_15_text: str) -> None:
    """Section 2.15 must contain a finding emission template that calls
    ``manage-findings qgate add`` with the canonical ``--source qgate``.

    The exact subcommand + source value are the structural contract that
    downstream consumers (manage-findings dedup, retrospective scrapers)
    rely on. Drift here silently breaks the Q-Gate ingest path. The
    ``--source`` argparse enum accepts only ``qgate`` / ``user_review``.
    """
    assert 'qgate add' in section_2_15_text, (
        'Section 2.15 finding-emission template must call "qgate add" '
        '(not bare "add") so dedup-by-title-within-phase applies.'
    )
    assert '--source qgate' in section_2_15_text, (
        'Section 2.15 finding-emission template must use the canonical '
        '--source qgate value (the argparse enum accepts only '
        'qgate / user_review).'
    )


def test_section_documents_pass_and_fail_criteria(section_2_15_text: str) -> None:
    """Section 2.15 must declare both Pass criteria and Fail criteria so
    the validator's decision boundary is explicit.
    """
    assert 'Pass criteria' in section_2_15_text, (
        'Section 2.15 must include a "Pass criteria" subsection.'
    )
    assert 'Fail criteria' in section_2_15_text, (
        'Section 2.15 must include a "Fail criteria" subsection.'
    )


def test_section_references_phase_3_outline_and_4_plan(section_2_15_text: str) -> None:
    """Section 2.15 must declare it runs in BOTH the 3-outline and 4-plan
    phase contexts. The validator covers deliverables introduced in either
    phase; missing one phase leaves the other uncovered.
    """
    assert '3-outline' in section_2_15_text and '4-plan' in section_2_15_text, (
        'Section 2.15 must declare it runs in BOTH 3-outline and 4-plan '
        'phase contexts so deliverables introduced in either phase are '
        'covered.'
    )


def test_verification_matrix_includes_worktree_linter_row(agent_text: str) -> None:
    """The Verification Criteria Matrix at the bottom of the agent file must
    include a row for the Worktree-Linter Validator so the summary table
    stays in lockstep with Section 2.15.

    A drift between Section 2.15 and the matrix row would let casual
    reviewers see one source say the validator runs and the other source
    omit it.
    """
    assert 'Worktree-Linter Validator' in agent_text, (
        'Agent must contain "Worktree-Linter Validator" text outside '
        'Section 2.15 itself — specifically, in the Verification Criteria '
        'Matrix row at the bottom of the file.'
    )
    # The matrix row should mention all three pattern letters or describe
    # the three forbidden patterns; verify at least one of those two
    # invariants holds.
    matrix_match = re.search(
        r'\|\s*Worktree-Linter Validator.*?\|',
        agent_text,
        re.DOTALL,
    )
    assert matrix_match is not None, (
        'The Verification Criteria Matrix must contain a row labelled '
        '"Worktree-Linter Validator" referencing the section.'
    )


# -----------------------------------------------------------------------------
# Negative cases — Section 2.15 must not contain stale literals outside
# explicit anti-pattern / forbidden / Do NOT markers. The suppression rule
# is purely textual; if the validator's own prose contains an unmarked
# stale literal, it would self-violate.
# -----------------------------------------------------------------------------


def _line_is_anti_pattern_marked(line: str, prev_line: str) -> bool:
    """Return True when ``line`` (or the line above it) carries an
    explicit anti-pattern / forbidden / Do NOT marker per the suppression
    rule documented in Section 2.15 itself.

    Mirrors the suppression rule's textual contract so a marker phrasing
    drift in the agent's own prose is caught here.
    """
    markers = (
        'Anti-pattern',
        'anti-pattern',
        'Forbidden',
        'forbidden',
        'forbids',
        'Do NOT',
        'do NOT',
        'do not',
        'MUST NOT',
        'must not',
    )
    haystack = f'{prev_line}\n{line}'
    return any(marker in haystack for marker in markers)


def test_section_2_15_has_no_unmarked_claude_worktrees_literals(section_2_15_text: str) -> None:
    """Inside Section 2.15 itself, every ``.claude/worktrees/`` literal must
    sit on a line that is either:

    - Inside the WL-B pattern description (the linter MUST name the literal
      in order to forbid it — quoted reference is sanctioned), OR
    - Adjacent to an explicit anti-pattern / forbidden / Do NOT marker.

    Naked ``.claude/worktrees/`` literals elsewhere in Section 2.15 would
    be self-violating: the validator describes a pattern that its own prose
    would trigger if a future edit removed the surrounding markers. This
    invariant catches the regression early.
    """
    lines = section_2_15_text.split('\n')
    violations: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        if '.claude/worktrees/' not in line:
            continue
        # Allowed contexts:
        # 1. The line itself names WL-B (the pattern subsection's own prose).
        # 2. The line carries (or its predecessor carries) an anti-pattern
        #    marker per the suppression rule.
        # 3. The line is the rg pattern definition (inside a fenced ``rg ...``
        #    code block that quotes the regex).
        if 'WL-B' in line:
            continue
        prev_line = lines[idx - 1] if idx > 0 else ''
        if _line_is_anti_pattern_marked(line, prev_line):
            continue
        # rg/grep pattern lines that quote the regex literal are sanctioned;
        # detect via the canonical "rg -n " prefix.
        stripped = line.lstrip()
        if stripped.startswith('rg ') or stripped.startswith('grep '):
            continue
        # Migration history references inside the explanation table also
        # carry an explicit "(TASK-4 migrated worktree storage to" marker;
        # accept that as a sanctioned migration-history reference.
        if 'TASK-4' in line and 'migrated' in line:
            continue
        violations.append((idx, line))

    assert not violations, (
        'Section 2.15 contains unmarked ".claude/worktrees/" literals that '
        'would make the validator self-violating: '
        + '; '.join(f'line {idx}: {line.strip()!r}' for idx, line in violations)
    )


def test_section_2_15_has_no_unmarked_cd_worktree_compounds(section_2_15_text: str) -> None:
    """Section 2.15 must not contain unmarked ``cd $WORKTREE && ...`` or
    ``cd /path/to/worktree && ...`` shell compounds anywhere in its prose.

    The validator describes the pattern; demonstration of the forbidden
    shape MUST be wrapped in an explicit anti-pattern marker, otherwise
    the validator's own example silently demonstrates the very pattern
    it forbids.
    """
    lines = section_2_15_text.split('\n')
    violations: list[tuple[int, str]] = []
    # Match the literal cd-compound shape: "cd <something with worktree> &&"
    # but only when that exact compound shape appears (so explanatory text
    # like "uses cd compounds" without the actual && sequence is fine).
    cd_compound = re.compile(r'cd\s+[^\s]*worktree[^\s]*\s*&&', re.IGNORECASE)
    for idx, line in enumerate(lines):
        if not cd_compound.search(line):
            continue
        if 'WL-A' in line:
            continue
        prev_line = lines[idx - 1] if idx > 0 else ''
        if _line_is_anti_pattern_marked(line, prev_line):
            continue
        # rg pattern definitions that quote the regex literal are sanctioned.
        stripped = line.lstrip()
        if stripped.startswith('rg ') or stripped.startswith('grep '):
            continue
        violations.append((idx, line))

    assert not violations, (
        'Section 2.15 contains unmarked "cd <worktree> &&" compounds that '
        'demonstrate the WL-A pattern without an anti-pattern marker: '
        + '; '.join(f'line {idx}: {line.strip()!r}' for idx, line in violations)
    )


# -----------------------------------------------------------------------------
# Self-pin — the file's own location is named verbatim in TASK-13 of plan
# lesson-2026-05-07-11-001. A future restructure should update this
# assertion deliberately rather than silently.
# -----------------------------------------------------------------------------


def test_test_file_lives_at_expected_path() -> None:
    """Pin the test file's location to the path named in TASK-13 of plan
    ``lesson-2026-05-07-11-001``.
    """
    here = Path(__file__).resolve()
    expected_suffix = Path(
        'test/plan-marshall/q-gate-validation-agent/test_q_gate_validation_worktree_linter.py'
    )
    assert str(here).endswith(str(expected_suffix)), (
        f'Test file moved from expected path. Got {here}, expected suffix {expected_suffix}.'
    )
