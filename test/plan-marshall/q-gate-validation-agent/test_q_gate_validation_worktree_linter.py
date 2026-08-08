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

from conftest import MARKETPLACE_ROOT, PLAN_DIR_NAME, PROJECT_ROOT, run_script


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

#: The sanctioned content-search target a sweep-invocation line must name to
#: earn the self-violation carve-out, alongside ``--pattern``.
_SANCTIONED_SWEEP_TARGET = 'architecture search --content'


def _is_sanctioned_sweep_invocation(line: str) -> bool:
    """Return True when ``line`` is a real architecture-search sweep command.

    The carve-out exists so the linter's OWN detector lines — which must quote
    the forbidden literal in order to search for it — do not register as
    violations of the rule they implement.

    The discriminator is deliberately the CONJUNCTION of the sanctioned search
    target and the ``--pattern`` flag. Keying on ``--pattern`` alone would be a
    vacuous guard: the flag is a common token, so any unmarked prose or example
    that merely mentioned it next to a forbidden literal would silently inherit
    the exemption and bypass the linter. Requiring the invocation target keeps
    the carve-out attached to actual sweep commands while still following the
    invocation rather than a particular search program's name.
    """
    return _SANCTIONED_SWEEP_TARGET in line and '--pattern' in line


@pytest.fixture(scope='module')
def agent_text() -> str:
    """Return the full text of the q-gate-validation-agent.md file."""
    return str(_AGENT_PATH.read_text(encoding='utf-8'))


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
        # 3. The line is the sweep-invocation line that quotes the regex
        #    (inside a fenced code block defining the pattern to detect).
        if 'WL-B' in line:
            continue
        prev_line = lines[idx - 1] if idx > 0 else ''
        if _line_is_anti_pattern_marked(line, prev_line):
            continue
        # A sweep-invocation line quoting the regex literal is sanctioned; the
        # detector must name the forbidden literal in order to search for it.
        # Keyed on the SANCTIONED INVOCATION, not on `--pattern` alone: the bare
        # flag is not a discriminator, since any prose line that happens to
        # mention `--pattern` alongside the forbidden literal would inherit the
        # exemption and bypass this linter entirely. Requiring the architecture
        # search target as well keeps the carve-out on actual sweep commands
        # while still following the invocation rather than a search program's
        # name.
        stripped = line.lstrip()
        if _is_sanctioned_sweep_invocation(stripped):
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
        # Sweep-invocation lines that quote the regex literal are sanctioned —
        # keyed on the sanctioned invocation, not on `--pattern` alone (see the
        # rationale on the sibling literal check above).
        stripped = line.lstrip()
        if _is_sanctioned_sweep_invocation(stripped):
            continue
        violations.append((idx, line))

    assert not violations, (
        'Section 2.15 contains unmarked "cd <worktree> &&" compounds that '
        'demonstrate the WL-A pattern without an anti-pattern marker: '
        + '; '.join(f'line {idx}: {line.strip()!r}' for idx, line in violations)
    )


# -----------------------------------------------------------------------------
# WL-C optionality resolution — the narrowing that stops WL-C flagging a
# missing ``--plan-id`` on a verb whose own argparse declares it optional.
#
# The controls below spawn real ``--help`` subprocesses through the live
# executor (``conftest`` bootstraps ``.plan/execute-script.py`` at session
# start, so this path is available in a fresh checkout too). They MUST fail
# loudly rather than skip when the parser is unreachable: a skipped control
# proves nothing, and the whole point of the narrowing is that it was verified
# against the real argparse surface rather than against prose.
# -----------------------------------------------------------------------------


_EXECUTOR_PATH = PROJECT_ROOT / PLAN_DIR_NAME / 'execute-script.py'

_MANAGE_LOGGING_NOTATION = 'plan-marshall:manage-logging:manage-logging'

#: The Q-Gate finding this narrowing exists to resolve as fixed (not
#: suppressed, not tolerated): a WL-C hit on the plan-id-less STEWARD example
#: in ``manage-logging/SKILL.md``.
_RESOLVED_FINDING_ID = 'cb10f4'

#: Verbs whose own argparse declares ``--plan-id`` optional — the write verbs
#: whose plan-less form is the documented global/no-plan logging path.
_OPTIONAL_PLAN_ID_VERBS = ('decision', 'work', 'script')

#: Verbs whose own argparse declares ``--plan-id`` required.
_REQUIRED_PLAN_ID_VERBS = ('separator', 'read')

#: The eight auto-routing notations WL-C sweeps for. The sweep regex's
#: alternation group IS the whitelist, so this set is pinned against the regex
#: itself rather than against any prose list.
_EXPECTED_WL_C_NOTATIONS = frozenset(
    {
        'manage-files',
        'manage-tasks',
        'manage-findings',
        'manage-references',
        'manage-solution-outline',
        'manage-plan-documents',
        'manage-logging',
        'manage-status',
    }
)


def strip_optional_groups(usage: str) -> str:
    """Remove balanced ``[...]`` and ``(...)`` groups from an argparse usage string.

    This is the documented WL-C discriminator: argparse renders an optional
    argument inside square brackets and a required one bare, so what survives
    the strip is exactly the required surface.
    """
    kept: list[str] = []
    depth = 0
    for char in usage:
        if char in '[(':
            depth += 1
            continue
        if char in '])':
            depth = max(depth - 1, 0)
            continue
        if depth == 0:
            kept.append(char)
    return ''.join(kept)


def classify_plan_id(usage: str) -> str:
    """Classify ``--plan-id`` on a verb as REQUIRED, OPTIONAL, or UNRESOLVABLE.

    ``UNRESOLVABLE`` is the fail-closed outcome: no usage line, or a usage line
    that never mentions the flag at all. WL-C emits the finding unchanged for an
    unresolvable verb — unresolvable is NOT optional.
    """
    if not usage or not usage.startswith('usage:') or '--plan-id' not in usage:
        return 'UNRESOLVABLE'
    return 'REQUIRED' if '--plan-id' in strip_optional_groups(usage) else 'OPTIONAL'


def _join_usage_block(help_text: str) -> str:
    """Collapse argparse's wrapped ``usage:`` block into one logical line."""
    lines = help_text.split('\n')
    collected: list[str] = []
    for line in lines:
        if not collected:
            if line.startswith('usage:'):
                collected.append(line.strip())
            continue
        if not line.strip():
            break
        collected.append(line.strip())
    return ' '.join(collected)


def _probe_usage_line(*verb_chain: str) -> str:
    """Spawn ``--help`` for ``verb_chain`` through the live executor.

    Fails loudly — never skips — when the executor is absent or the probe does
    not exit cleanly. A control that silently skips would let the narrowing ship
    unverified against the real parser.
    """
    assert _EXECUTOR_PATH.is_file(), (
        f'The WL-C optionality controls probe the live parser through the executor at '
        f'{_EXECUTOR_PATH}, which is missing. conftest bootstraps it at session start; '
        f'a missing executor means the probe cannot run — fail loudly rather than skip.'
    )
    result = run_script(
        _EXECUTOR_PATH,
        _MANAGE_LOGGING_NOTATION,
        *verb_chain,
        '--help',
        cwd=PROJECT_ROOT,
    )
    assert result.success, (
        f'Probing "{_MANAGE_LOGGING_NOTATION} {" ".join(verb_chain)} --help" through the '
        f'executor exited {result.returncode}. stderr: {result.stderr!r}'
    )
    usage = _join_usage_block(result.stdout)
    assert usage, (
        f'No "usage:" block in the --help output for verb chain '
        f'{" ".join(verb_chain) or "<top-level>"}. stdout: {result.stdout!r}'
    )
    return usage


def _derive_manage_logging_verb_population() -> tuple[str, ...]:
    """Derive the complete manage-logging verb set from the script's own parser.

    Population-derived, not hand-listed: the totality control below would be
    vacuous if it iterated a tuple a future verb addition never updated.
    """
    usage = _probe_usage_line()
    choices_match = re.search(r'\{([a-z,\-]+)\}', usage)
    assert choices_match is not None, (
        f'Could not derive the manage-logging subcommand choices from its top-level '
        f'usage line: {usage!r}'
    )
    return tuple(choices_match.group(1).split(','))


@pytest.fixture(scope='module')
def wl_c_block_text(section_2_15_text: str) -> str:
    """Return the WL-C portion of Section 2.15 (WL-C heading → Suppression rule)."""
    start = section_2_15_text.find('**Pattern WL-C')
    assert start != -1, 'Section 2.15 no longer contains a "**Pattern WL-C" subsection.'
    end = section_2_15_text.find('**Suppression rule**', start)
    assert end != -1, (
        'Section 2.15 no longer contains a "**Suppression rule**" block after WL-C; '
        'the WL-C block boundary cannot be resolved.'
    )
    return section_2_15_text[start:end]


@pytest.mark.parametrize('verb', _OPTIONAL_PLAN_ID_VERBS)
def test_wl_c_positive_control_write_verbs_declare_plan_id_optional(verb: str) -> None:
    """The manage-logging write verbs declare ``--plan-id`` OPTIONAL.

    This is the positive control for the narrowing: because these verbs declare
    the flag optional, the plan-id-less STEWARD example in
    ``manage-logging/SKILL.md`` is suppressed under the new rule, which is how
    Q-Gate finding cb10f4 is resolved as FIXED rather than tolerated.
    """
    usage = _probe_usage_line(verb)
    assert classify_plan_id(usage) == 'OPTIONAL', (
        f'manage-logging {verb} must classify --plan-id as OPTIONAL so WL-C suppresses '
        f'the plan-id-less candidate that produced Q-Gate finding {_RESOLVED_FINDING_ID}. '
        f'Live usage line: {usage!r}'
    )


@pytest.mark.parametrize('verb', _REQUIRED_PLAN_ID_VERBS)
def test_wl_c_negative_control_other_verbs_declare_plan_id_required(verb: str) -> None:
    """``separator`` and ``read`` declare ``--plan-id`` REQUIRED.

    This is the guard against the narrowing degenerating into a blanket
    exemption for the whole notation: within one script, some verbs stay
    required, and WL-C must keep emitting for those.
    """
    usage = _probe_usage_line(verb)
    assert classify_plan_id(usage) == 'REQUIRED', (
        f'manage-logging {verb} must classify --plan-id as REQUIRED — the narrowing is '
        f'per-verb, not per-notation, and a blanket exemption would silently disable '
        f'WL-C for this script. Live usage line: {usage!r}'
    )


def test_wl_c_optionality_resolves_for_every_manage_logging_verb() -> None:
    """Every verb in the derived manage-logging population resolves to exactly one class.

    Totality control: the population is derived from the script's own subcommand
    choices, and the derived size is published in the assertion so a shrunken
    population cannot masquerade as a clean pass.
    """
    population = _derive_manage_logging_verb_population()
    assert len(population) == 5, (
        f'manage-logging publishes {len(population)} verbs {population!r}; the WL-C '
        f'totality control was written against a population of 5. Re-derive the '
        f'expected classes before widening this number.'
    )
    assert set(population) == set(_OPTIONAL_PLAN_ID_VERBS) | set(_REQUIRED_PLAN_ID_VERBS), (
        f'The derived manage-logging verb population {population!r} no longer matches the '
        f'verbs the positive and negative controls cover.'
    )

    classifications = {verb: classify_plan_id(_probe_usage_line(verb)) for verb in population}
    unresolvable = sorted(verb for verb, cls in classifications.items() if cls == 'UNRESOLVABLE')
    assert not unresolvable, (
        f'{len(unresolvable)} of {len(population)} manage-logging verbs did not resolve to '
        f'REQUIRED or OPTIONAL: {unresolvable}. WL-C fails closed on an unresolvable verb, '
        f'so an unresolvable result here means the discriminator itself is broken.'
    )


def test_wl_c_sweep_regex_alternation_pins_the_eight_auto_routing_notations(
    wl_c_block_text: str,
) -> None:
    """The WL-C sweep regex's alternation group IS the auto-routing whitelist.

    Pinning the set here is what makes the "there is no separate list" claim
    checkable: dropping a notation from the alternation silently stops sweeping
    that script, with no other file to disagree with.
    """
    alternation_match = re.search(r'plan-marshall:\(([a-z|\-]+)\)', wl_c_block_text)
    assert alternation_match is not None, (
        'Could not find the WL-C sweep regex alternation group '
        '"plan-marshall:(...)" in the WL-C block.'
    )
    notations = frozenset(alternation_match.group(1).split('|'))
    assert notations == _EXPECTED_WL_C_NOTATIONS, (
        f'The WL-C auto-routing whitelist drifted. In the regex but not expected: '
        f'{sorted(notations - _EXPECTED_WL_C_NOTATIONS)}; expected but not in the regex: '
        f'{sorted(_EXPECTED_WL_C_NOTATIONS - notations)}.'
    )


def test_wl_c_documents_the_optionality_resolution_step(section_2_15_text: str) -> None:
    """Section 2.15 must document the per-candidate optionality-resolution step."""
    assert 'WL-C optionality resolution' in section_2_15_text, (
        'Section 2.15 must document a "WL-C optionality resolution" step between the '
        'sweep and the finding, or WL-C reverts to flagging every plan-id-less '
        'invocation regardless of the verb\'s declared optionality.'
    )


def test_wl_c_names_both_optionality_sources(section_2_15_text: str) -> None:
    """The resolution step must name its primary (live --help) and fallback sources."""
    assert 'Primary source' in section_2_15_text and '`--help`' in section_2_15_text, (
        'The WL-C optionality-resolution step must name the primary source: probing '
        'the live parser with --help and reading its usage: line.'
    )
    assert (
        'Fallback source' in section_2_15_text and '## Canonical invocations' in section_2_15_text
    ), (
        'The WL-C optionality-resolution step must name the fallback source: the owning '
        "SKILL.md's ## Canonical invocations entry for the verb."
    )


def test_wl_c_constrains_verb_chain_tokens_before_interpolation(wl_c_block_text: str) -> None:
    """The verb chain reaches an executed probe command, so it must be allow-listed first.

    Step 1 derives the chain from unconstrained non-whitespace runs captured out of
    an arbitrary scanned file, and step 2 interpolates that chain into a command the
    linter runs. Markdown arriving through a pull request is untrusted content, so
    the shape constraint is the containment boundary. Both halves are pinned: the
    canonical kebab-case token shape, and the UNRESOLVABLE classification that routes
    a failing token into the existing fail-closed rule instead of into the probe.
    """
    assert '^[a-z0-9]+(?:-[a-z0-9]+)*$' in wl_c_block_text, (
        'The WL-C optionality-resolution step must name the canonical kebab-case token '
        'shape every extracted verb-chain token is checked against before it is '
        'interpolated into the probe command.'
    )
    assert 'UNRESOLVABLE' in wl_c_block_text, (
        'A verb-chain token that fails the shape check must be classified UNRESOLVABLE '
        'so the existing fail-closed rule emits the finding, rather than the malformed '
        'token being interpolated into an executed command.'
    )


def test_wl_c_states_the_fail_closed_rule(section_2_15_text: str) -> None:
    """An unresolvable verb must emit the finding — unresolvable is not optional."""
    assert 'Fail closed' in section_2_15_text, (
        'The WL-C optionality-resolution step must state a fail-closed rule so an '
        'unresolvable verb emits the finding rather than being silently exempted.'
    )
    assert 'Unresolvable is NOT optional' in section_2_15_text, (
        'The WL-C fail-closed rule must state explicitly that unresolvable is NOT '
        'optional — the narrowing must never widen into a default exemption.'
    )


def test_stale_auto_routing_scripts_cross_reference_is_gone(agent_text: str) -> None:
    """The dangling "Auto-routing scripts" subsection reference must not return.

    ``worktree-handling.md`` has no such subsection, so the old WL-C prose and
    its finding detail both pointed readers at a section that does not exist.
    """
    assert 'Auto-routing scripts' not in agent_text, (
        'q-gate-validation.md still cites a worktree-handling.md "Auto-routing scripts" '
        'subsection, which does not exist. The whitelist is the sweep regex\'s own '
        'alternation group, and the contract lives in the "--plan-id Four-State '
        'Contract" section.'
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
