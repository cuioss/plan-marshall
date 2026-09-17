#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression tests for the phase-6-finalize architecture-refresh standard.

The standard at ``standards/architecture-refresh.md`` is a markdown executor
playbook, not a Python module. These tests pin its decision flow contract by:

1. **Parsing the standard's pseudo-code summary** and re-implementing it as a
   pure decision function in this test module. The re-implementation is
   exercised across the full matrix:

      * Tier-0 ``enabled`` vs ``disabled``
      * ``origin/main`` baseline present vs absent (no committed baseline)
      * Drift detected vs none (``added union removed`` non-empty vs empty)
      * The ``discover --force --apply plan`` attribution verdict, and whether
        plan-time writers left uncommitted descriptor edits before discover ran
      * Tier-1 dispatch knob (``prompt`` / ``auto`` / ``disabled``)
      * ``change_type`` shortcut for ``bug_fix`` / ``verification``

2. **Asserting the standard's narrative** documents every observable branch
   (absent baseline, tier-0 disabled, empty diff, non-empty diff with each
   tier-1 value, change_type shortcut, each attribution outcome) and emits the
   matching ``--display-detail`` template per branch, reads its baseline by ref
   with no shell extraction, and points at the delta-class table instead of
   restating it.

3. **Asserting registration** of ``architecture-refresh`` in
   ``standards/required-steps.md`` so the ``phase_steps_complete`` handshake
   enforces it whenever it is in ``manifest.phase_6.steps``.

4. **Asserting cross-references** are correct: the SKILL.md dispatch table
   resolves ``default:architecture-refresh`` to this standard, the standard
   declares its inline-dispatch contract, phase-1-init is cited as NOT
   snapshotting the architecture descriptor, and the manage-run-config
   tier-0/tier-1 knobs are referenced.

The functional behaviour of the underlying scripts (``architecture discover
--force --apply plan``, ``diff-modules --pre-ref``,
``descriptor-regression-check --pre-ref``, ``manage-run-config architecture-refresh
get-tier-0/1``, etc.) is covered by their own bundle-scoped test suites; this
file pins ONLY the orchestration contract documented in the standard.
"""

from __future__ import annotations

import re
from typing import Any

# ``_invariants`` is imported PLAINLY so this suite exercises the same module
# instance the ``phase_steps_complete`` invariant uses at runtime; the root
# conftest already puts its marketplace ``scripts/`` directory on ``sys.path``.
import _invariants as inv
import pytest
from _dispatch_roster import parse_roster
from _push_prescription_scan import fenced_command_lines, scan_push_prescriptions

from conftest import MARKETPLACE_ROOT, load_script_module

# The delta-class vocabulary and the verdict set are declared once, in the
# discover attribution module. The decision model and the pointer guard below
# derive from it rather than restating either set.
_descriptor_delta = load_script_module(
    'plan-marshall', 'manage-architecture', '_descriptor_delta.py', '_descriptor_delta'
)
DELTA_CLASSES: dict[str, str] = _descriptor_delta.DELTA_CLASSES
VERDICTS: tuple[str, ...] = _descriptor_delta.VERDICTS

# ---------------------------------------------------------------------------
# Standards-doc paths (authoritative narrative surface).
# ---------------------------------------------------------------------------

_MANAGE_API_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-architecture' / 'standards' / 'manage-api.md'
_PHASE_6_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_PHASE_6_SKILL_MD = _PHASE_6_DIR / 'SKILL.md'
_ARCHITECTURE_REFRESH_MD = _PHASE_6_DIR / 'standards' / 'architecture-refresh.md'
_DISPATCH_INLINE_SPLIT_MD = _PHASE_6_DIR / 'standards' / 'dispatch-inline-split.md'
_DISPATCHED_HEADING = '## Dispatched steps'
_INLINE_HEADING = '## Inline steps'
_REQUIRED_STEPS_MD = _PHASE_6_DIR / 'standards' / 'required-steps.md'
_PHASE_1_INIT_SKILL_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-1-init' / 'SKILL.md'


# ---------------------------------------------------------------------------
# Retired PR-body-write prescription scan (order-9 contract).
# ---------------------------------------------------------------------------
#
# ``default:architecture-refresh`` is order 9 and ``default:create-pr`` is
# order 20, so NO PR exists while this step runs, and the PR-body-write
# sequence this branch used to prescribe (``ci pr view`` -> ``ci pr
# prepare-body`` -> ``ci pr edit``) cannot be prescribed here. The standard
# still NAMES those three calls, inside an owed-follow-up note, so a substring
# search over the whole document cannot tell a live prescription from its own
# retraction.
#
# SCOPE: this scan covers those three retired shapes and nothing else. Other
# ``ci pr`` verbs are deliberately NOT matched — each would need its own
# matched control to be guarded honestly, and this guard's control set
# (``_RETIRED_PR_CALL_SHAPES``) is exactly the three. A green run here therefore
# means "the retired PR-body-write sequence is not prescribed", NOT "no PR
# operation of any kind appears".
#
# The scan reuses ``fenced_command_lines`` — the same fence-tracking primitive
# the push scan uses — rather than filtering prose. Reuse, not a second
# implementation: a private copy is how two guards come to disagree about what
# counts as a command.

#: The three retired PR-body-write calls. Matched as command WORDS with
#: flexible inner whitespace, so the pseudo-code assignment forms
#: (``existing := ci pr view --head …``), the multi-line executor form (whose
#: ``pr view`` sits on a continuation line carrying neither the script name nor
#: a leading ``ci``), and a bare ``ci pr edit …`` are all one pattern. Keying on
#: the leading ``ci`` token or on ``execute-script.py`` is what let two of the
#: three retired shapes through.
_RETIRED_PR_BODY_WRITE = re.compile(r'\bpr\s+(?:view|edit)\b|\bprepare-body\b')


def _scan_pr_operation_prescriptions(text: str) -> tuple[list[str], int]:
    """Return ``(retired PR-body-write lines, fenced command lines examined)``.

    The second element is the published population: a document whose fences
    resolve no command lines yields ``(…, 0)``, which the caller MUST treat as
    an unresolved scan rather than a clean one.
    """
    commands = fenced_command_lines(text)
    offenders = [line.strip() for line in commands if _RETIRED_PR_BODY_WRITE.search(line)]
    return offenders, len(commands)


#: The three call shapes this step retired, verbatim from the removed pseudo-code
#: and command blocks. Two are ``:=`` assignment forms whose line begins with the
#: assigned name, and the third is a bare invocation — the spread is the point:
#: a guard keyed on how a line STARTS catches only the third.
_RETIRED_PR_CALL_SHAPES = (
    'existing := ci pr view --head {worktree_branch}',
    'body_path := ci pr prepare-body --plan-id {plan_id} --for edit',
    'ci pr edit --pr-number {pr_number} --plan-id {plan_id}',
)


# ===========================================================================
# Decision-flow re-implementation (mirrors the standard's pseudo-code).
#
# The architecture-refresh standard ends with a "Pseudo-Code Summary" section
# that is the authoritative procedural form of its decision tree. We mirror
# that summary here and exercise it across the full matrix below. If the
# narrative ever diverges from this re-implementation, the assertions in
# ``TestNarrativeContract`` will catch the drift on the markdown side and the
# parametric tests will catch it on the behavioural side.
# ===========================================================================


# Sentinel for "Tier 0 disabled — affected modules never computed".
_AFFECTED_UNKNOWN = object()


#: Verdicts under which ``discover --force --apply plan`` writes the plan projection.
_PLAN_PROJECTION_VERDICTS = frozenset({'plan_attributable', 'mixed'})
#: Verdicts that leave a tool migration unwritten for the steward upgrade.
_MIGRATION_DEFERRED_VERDICTS = frozenset({'migration_only', 'mixed'})
#: Verdicts under which nothing about the discover delta can be attributed.
_UNATTRIBUTABLE_VERDICTS = frozenset({'undecidable', 'no_baseline'})

_DETAIL_MIGRATION_NOT_COMMITTED = 'tool migration not committed; run marshall-steward upgrade'
_DETAIL_UNATTRIBUTABLE = 'descriptor delta unattributable; not committed'
_DETAIL_MIGRATION_DEFERRED = 'refreshed derived data ({affected_module_count} modules); migration deferred'
#: Branch I at a zero module union. ``migration_deferred`` is derived from the
#: discover attribution and is independent of ``affected``, so a round can commit
#: segment-1 plan-time descriptor edits with ``added`` and ``removed`` both empty.
#: The count is omitted for the same reason Branch J omits it: rendering
#: ``(0 modules)`` would advertise a module delta the round does not have.
_DETAIL_MIGRATION_DEFERRED_NO_STRUCTURE_CHANGE = 'refreshed derived data; migration deferred'

# -- The four Tier-1-skip exit cells (Step 5 Branches C / D / J / K) ---------
#
# The exit detail is selected on BOTH dimensions — whether Step 3d committed,
# and whether `added union removed` is non-empty — because neither implies the
# other. A round can commit segment-1 plan-time descriptor edits while the
# module union is empty (J), and a round can see a non-empty union whose commit
# already landed in an earlier commit on the branch (K). Keying on one dimension
# alone is what let a committed round report "no module structure changed".
_DETAIL_NO_STRUCTURE_CHANGE = 'no module structure changed'
_DETAIL_REFRESHED = 'refreshed derived data ({affected_module_count} modules)'
_DETAIL_REFRESHED_NO_STRUCTURE_CHANGE = 'refreshed derived data; no module structure changed'
_DETAIL_STRUCTURE_CHANGE_NOT_COMMITTED = 'module structure changed ({affected_module_count} modules); nothing to commit'


def _tier1_exit(*, committed: bool, affected: tuple[str, ...]) -> tuple[str, str]:
    """Return ``(branch, display_detail)`` for a Tier-1 skip.

    Mirrors ``tier1_exit_detail()`` in the standard's Pseudo-Code Summary. Branch
    J deliberately interpolates no module count: rendering ``(0 modules)`` would
    advertise a module delta the round does not have.
    """
    if committed and affected:
        return 'D', _DETAIL_REFRESHED.format(affected_module_count=len(affected))
    if committed:
        return 'J', _DETAIL_REFRESHED_NO_STRUCTURE_CHANGE
    if affected:
        return 'K', _DETAIL_STRUCTURE_CHANGE_NOT_COMMITTED.format(affected_module_count=len(affected))
    return 'C', _DETAIL_NO_STRUCTURE_CHANGE


def _decide_architecture_refresh(
    *,
    baseline_present: bool,
    tier_0: str,
    tier_1: str,
    change_type: str,
    diff_added: tuple[str, ...] = (),
    diff_removed: tuple[str, ...] = (),
    diff_changed: tuple[str, ...] = (),
    attribution: str | None = None,
    preexisting_plan_writes: bool = False,
    regressive: bool = False,
    user_response: str | None = None,
) -> dict[str, Any]:
    """Pure re-implementation of the standard's pseudo-code summary.

    Returns a dict with keys:

      * ``branch``: the ``A``-``K`` branch identifier from "Step 5: Mark Step
        Complete" (no baseline / tier-0+tier-1 skipped / nothing committed and no
        structure change / refresh only / refresh + enrich / refresh + deferred
        re-enrichment / migration not committed / unattributable / refresh with
        migration deferred / committed with an empty module union / structure
        change this step did not commit), or ``refused`` when the regression gate
        rejected the delta.
      * ``tier_0_committed``: True if the Tier-0 ``chore(architecture):
        refresh`` commit fires.
      * ``tier_1_action``: ``enrich`` / ``deferred`` / ``skipped``.
      * ``affected_modules``: sorted union ``added union removed``, or
        ``_AFFECTED_UNKNOWN`` when Tier 0 is disabled.
      * ``display_detail``: the ``--display-detail`` payload that the
        ``mark-step-done`` call MUST carry on this branch.

    ``attribution`` is the ``discover --force --apply plan`` verdict. When
    omitted it is derived the way a structural-only run reports it: a drift
    (``added union removed`` non-empty) is ``plan_attributable``, no drift is
    ``clean``.

    The commit gate is the on-disk porcelain status, and the model derives that
    status from its two real sources instead of from the diff buckets: discover's
    plan projection (written only under ``plan_attributable`` / ``mixed``) and
    ``preexisting_plan_writes`` — uncommitted descriptor edits plan-time writers
    left before discover ran. A migration class and an unattributable difference
    are never written under ``--apply plan``, so neither can dirty the tree.

    Note: ``diff_changed`` is accepted but DELIBERATELY ignored. Against a
    derived-less ``origin/main`` git baseline every common module classifies as
    ``changed`` (no committed per-module ``derived.json`` sha), so the changed
    bucket is noise; the reliable drift signal is the index-derived
    ``added union removed`` buckets only.
    """
    migration_deferred = False
    unattributable = False
    # -- Step 2a: Tier-0 disabled — no probe, affected never computed --------
    if tier_0 == 'disabled':
        affected: tuple[Any, ...] = _AFFECTED_UNKNOWN  # type: ignore[assignment]
        tier_0_committed = False
    elif tier_0 == 'enabled':
        # -- Step 2b/2c: diff-modules --pre-ref origin/main probe ----------
        if not baseline_present:
            return {
                'branch': 'A',
                'tier_0_committed': False,
                'tier_1_action': 'skipped',
                'affected_modules': (),
                'display_detail': 'skipped — no committed origin/main architecture baseline',
            }
        # -- Step 3b: affected = added union removed (changed bucket is noise) ---
        affected = tuple(sorted(set(diff_added) | set(diff_removed)))
        # -- Step 3a: discover --force --apply plan verdict -----------------
        if attribution is None:
            attribution = 'plan_attributable' if affected else 'clean'
        if attribution not in VERDICTS:
            raise ValueError(f'attribution must be one of {VERDICTS}, got {attribution!r}')
        migration_deferred = attribution in _MIGRATION_DEFERRED_VERDICTS
        unattributable = attribution in _UNATTRIBUTABLE_VERDICTS
        # -- Step 3c: porcelain gate over segment-1 writes + plan projection -
        dirty = preexisting_plan_writes or attribution in _PLAN_PROJECTION_VERDICTS
        # -- Step 3c.5 / 3d: regression gate, then commit ------------------
        if dirty and regressive:
            return {
                'branch': 'refused',
                'tier_0_committed': False,
                'tier_1_action': 'skipped',
                'affected_modules': affected,
                'display_detail': 'regressive descriptor delta refused — {violation_fields}',
            }
        tier_0_committed = dirty
    else:
        raise ValueError(f'tier_0 must be enabled|disabled, got {tier_0!r}')

    # -- Step 3e: a deferred or unattributable verdict ends after Tier 0 -----
    if unattributable:
        return {
            'branch': 'H',
            'tier_0_committed': tier_0_committed,
            'tier_1_action': 'skipped',
            'affected_modules': affected,
            'display_detail': _DETAIL_UNATTRIBUTABLE,
        }
    if migration_deferred:
        if tier_0_committed:
            detail = (
                _DETAIL_MIGRATION_DEFERRED.format(affected_module_count=len(affected))
                if affected
                else _DETAIL_MIGRATION_DEFERRED_NO_STRUCTURE_CHANGE
            )
            return {
                'branch': 'I',
                'tier_0_committed': tier_0_committed,
                'tier_1_action': 'skipped',
                'affected_modules': affected,
                'display_detail': detail,
            }
        return {
            'branch': 'G',
            'tier_0_committed': False,
            'tier_1_action': 'skipped',
            'affected_modules': affected,
            'display_detail': _DETAIL_MIGRATION_NOT_COMMITTED,
        }

    # -- Step 4: Tier 1 -----------------------------------------------------
    # 4a. change_type shortcut
    if change_type in {'bug_fix', 'verification'}:
        if affected is _AFFECTED_UNKNOWN:
            return {
                'branch': 'B',
                'tier_0_committed': False,
                'tier_1_action': 'skipped',
                'affected_modules': _AFFECTED_UNKNOWN,
                'display_detail': 'tier-0 disabled; tier-1 skipped',
            }
        branch, detail = _tier1_exit(committed=tier_0_committed, affected=affected)
        return {
            'branch': branch,
            'tier_0_committed': tier_0_committed,
            'tier_1_action': 'skipped',
            'affected_modules': affected,
            'display_detail': detail,
        }

    # 4c. affected unknown (Tier-0 disabled)
    if affected is _AFFECTED_UNKNOWN:
        return {
            'branch': 'B',
            'tier_0_committed': False,
            'tier_1_action': 'skipped',
            'affected_modules': _AFFECTED_UNKNOWN,
            'display_detail': 'tier-0 disabled; tier-1 skipped',
        }

    # 4b. affected empty (Tier-0 enabled, no added/removed). An empty module
    # union does NOT mean nothing was committed: segment-1 plan-time descriptor
    # edits dirty the tree with added and removed both empty, so this exit reads
    # `tier_0_committed` rather than assuming it False (Branch J vs Branch C).
    if len(affected) == 0:
        branch, detail = _tier1_exit(committed=tier_0_committed, affected=())
        return {
            'branch': branch,
            'tier_0_committed': tier_0_committed,
            'tier_1_action': 'skipped',
            'affected_modules': (),
            'display_detail': detail,
        }

    # 4d. tier_1 dispatch — affected is non-empty, tier-0 enabled, change_type
    # is not in the shortcut list, and the verdict deferred nothing.
    n = len(affected)
    if tier_1 == 'disabled':
        return {
            'branch': 'F',
            'tier_0_committed': tier_0_committed,
            'tier_1_action': 'deferred',
            'affected_modules': affected,
            'display_detail': ('refreshed; re-enrichment deferred'),
        }
    if tier_1 == 'auto':
        return {
            'branch': 'E',
            'tier_0_committed': tier_0_committed,
            'tier_1_action': 'enrich',
            'affected_modules': affected,
            'display_detail': f'refreshed + re-enriched ({n} modules)',
        }
    if tier_1 == 'prompt':
        if user_response is None:
            raise ValueError('tier_1=prompt requires a user_response (Re-enrich now / Skip — note in PR).')
        if user_response == 'Re-enrich now':
            return {
                'branch': 'E',
                'tier_0_committed': tier_0_committed,
                'tier_1_action': 'enrich',
                'affected_modules': affected,
                'display_detail': f'refreshed + re-enriched ({n} modules)',
            }
        if user_response in ('Skip — note in PR', 'aborted'):
            return {
                'branch': 'F',
                'tier_0_committed': tier_0_committed,
                'tier_1_action': 'deferred',
                'affected_modules': affected,
                'display_detail': ('refreshed; re-enrichment deferred'),
            }
        raise ValueError(f'unknown user_response: {user_response!r}')

    raise ValueError(f'tier_1 must be prompt|auto|disabled, got {tier_1!r}')


# ===========================================================================
# Absent-baseline handling — origin/main carries no committed descriptor.
# ===========================================================================


_TIER_0_BLOCK_WITH_PUSH = """\
After the commit, push immediately so the refresh lands on the same PR as the
plan's substantive commits:

```bash
git -C {worktree_path} push
```
"""

_TIER_0_BLOCK_WITHOUT_PUSH = """\
**This step does NOT push.** It commits and stops. `default:push` (order 11) is
a **pure push barrier** that ships the converged branch — including this commit. Pushing here would be a
second push of the same branch from a step the single-push contract does not
authorise.

```text
        git -C {worktree_path} commit -m "chore(architecture): refresh"
        # no push — the order-11 default:push barrier ships this commit
```
"""

_SHELL_EXTRACTION = re.compile(r'(?:^|\s)(?:rm|mkdir|tar)\s|\bgit\b[^\n]*\barchive\b')

def _scan_shell_extraction(text: str) -> tuple[list[str], int]:
    """Return ``(extraction command lines, fenced command lines examined)``."""
    commands = fenced_command_lines(text)
    offenders = [line.strip() for line in commands if _SHELL_EXTRACTION.search(line)]
    return offenders, len(commands)

_REMOVED_EXTRACTION_BLOCK = """\
```bash
rm -rf {worktree_path}/.plan/temp/architecture-baseline {worktree_path}/.plan/temp/architecture-baseline.tar
```

```bash
mkdir -p {worktree_path}/.plan/temp/architecture-baseline
```

```bash
git -C {worktree_path} archive --format=tar --output=.plan/temp/architecture-baseline.tar origin/main .plan/project-architecture
```

```bash
tar -xf {worktree_path}/.plan/temp/architecture-baseline.tar -C {worktree_path}/.plan/temp/architecture-baseline
```
"""

def _restated_classes(text: str) -> list[str]:
    """Delta-class names written as code spans — the form a restated class table takes."""
    return [name for name in DELTA_CLASSES if f'`{name}`' in text]

_CLASS_TABLE_HEADER = '| Class | Attribution | Detected when |'

_CLASS_TABLE_ROW = re.compile(r'^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|')

def _published_class_attributions(text: str) -> dict[str, str]:
    """Parse ``class -> attribution`` out of the published delta-class table.

    Returns the EMPTY mapping when the table cannot be resolved at all, so a
    caller that publishes the parsed row count fails loudly on a table the
    parser no longer recognises instead of passing vacuously on zero rows.

    Raises ``ValueError`` naming the class when the table carries TWO rows for
    it. Assignment into a dict is last-write-wins, so a silent overwrite lets a
    self-contradictory table compare EQUAL to ``DELTA_CLASSES`` — and keep the
    expected row count — whenever the last of the conflicting rows happens to
    agree, which is the same green-over-a-disagreeing-document shape the guard
    below exists to remove, re-entering through the parser. Raising rather than
    returning the empty mapping is deliberate: the empty mapping is this
    helper's documented signal for "the table could not be resolved at all",
    and a duplicate row is the opposite situation — the table resolved
    perfectly well and states two things at once — so reusing that signal would
    report "parsed 0 rows" about a table the parser read in full.
    """
    _, separator, tail = text.partition(_CLASS_TABLE_HEADER)
    if not separator:
        return {}
    parsed: dict[str, str] = {}
    # ``tail`` opens mid-line, so element 0 is the header's own remainder;
    # element 1 is the delimiter row, which matches no data-row pattern.
    for line in tail.splitlines()[1:]:
        if not line.startswith('|'):
            break
        row = _CLASS_TABLE_ROW.match(line)
        if row is not None:
            class_name, attribution = row.group(1), row.group(2)
            if class_name in parsed:
                raise ValueError(
                    'the published delta-class table carries two rows for '
                    f'`{class_name}` ({parsed[class_name]!r} then {attribution!r}) — '
                    'the second would silently overwrite the first, so the table can '
                    'state two attributions at once while parsing to a mapping that '
                    'agrees with DELTA_CLASSES. Each class must be published exactly '
                    'once; do not delete this check.'
                )
            parsed[class_name] = attribution
    return parsed

_MATRIX_CASES = [
    # baseline absent, tier-0 enabled — Branch A short-circuit.
    (False, 'enabled', 'prompt', 'feature', False, 'A', 'no committed origin/main', None),
    (False, 'enabled', 'auto', 'bug_fix', True, 'A', 'no committed origin/main', None),
    # baseline absent, tier-0 disabled — extraction skipped, Branch B.
    (False, 'disabled', 'auto', 'feature', True, 'B', 'tier-0 disabled', None),
    # tier-0 disabled (baseline present) — Branch B for any tier-1 setting.
    (True, 'disabled', 'prompt', 'feature', True, 'B', 'tier-0 disabled', None),
    (True, 'disabled', 'auto', 'feature', False, 'B', 'tier-0 disabled', None),
    (True, 'disabled', 'disabled', 'refactor', True, 'B', 'tier-0 disabled', None),
    # tier-0 enabled, no drift — Branch C.
    (True, 'enabled', 'prompt', 'feature', False, 'C', 'no module structure changed', None),
    (True, 'enabled', 'auto', 'feature', False, 'C', 'no module structure changed', None),
    # tier-0 enabled, drift, change_type shortcut — Branch D.
    (True, 'enabled', 'auto', 'bug_fix', True, 'D', 'refreshed derived data', None),
    (True, 'enabled', 'prompt', 'verification', True, 'D', 'refreshed derived data', None),
    # tier-0 enabled, drift, tier-1 auto — Branch E.
    (True, 'enabled', 'auto', 'feature', True, 'E', 'refreshed + re-enriched', None),
    # tier-0 enabled, drift, tier-1 prompt accepted — Branch E.
    (True, 'enabled', 'prompt', 'feature', True, 'E', 'refreshed + re-enriched', 'Re-enrich now'),
    # tier-0 enabled, drift, tier-1 disabled — Branch F.
    (True, 'enabled', 'disabled', 'feature', True, 'F', 're-enrichment deferred', None),
    # tier-0 enabled, drift, tier-1 prompt declined — Branch F.
    (True, 'enabled', 'prompt', 'feature', True, 'F', 're-enrichment deferred', 'Skip — note in PR'),
]

class TestAbsentBaselineHandling:
    """Step 2 — absent-baseline short-circuit (Branch A)."""

    def test_no_baseline_yields_branch_a_when_tier_0_enabled(self):
        """A missing origin/main baseline short-circuits Tier 0 to Branch A."""
        for tier_1 in ('prompt', 'auto', 'disabled'):
            result = _decide_architecture_refresh(
                baseline_present=False,
                tier_0='enabled',
                tier_1=tier_1,
                change_type='feature',
            )
            assert result['branch'] == 'A', (
                f'Absent baseline must yield Branch A with tier_0=enabled tier_1={tier_1}, got {result}'
            )
            assert result['tier_0_committed'] is False
            assert result['tier_1_action'] == 'skipped'
            assert 'no committed origin/main architecture baseline' in result['display_detail']

    def test_no_baseline_with_tier_0_disabled_yields_branch_b(self):
        """Tier-0 disabled skips extraction entirely — baseline presence is moot."""
        result = _decide_architecture_refresh(
            baseline_present=False,
            tier_0='disabled',
            tier_1='auto',
            change_type='feature',
        )
        assert result['branch'] == 'B', (
            'Tier-0 disabled never extracts a baseline; absent baseline cannot reach Branch A.'
        )
        assert result['display_detail'] == 'tier-0 disabled; tier-1 skipped'

    def test_no_baseline_short_circuits_change_type_shortcut(self):
        """Absent baseline (tier-0 enabled) wins over the change_type shortcut."""
        result = _decide_architecture_refresh(
            baseline_present=False,
            tier_0='enabled',
            tier_1='auto',
            change_type='bug_fix',
        )
        assert result['branch'] == 'A'
        assert 'no committed origin/main architecture baseline' in result['display_detail']


class TestTier0DisabledMatrix:
    """Step 2a — Tier-0 disabled paths."""

    def test_tier_0_disabled_skips_commit_and_enters_tier_1_with_unknown(self):
        """Tier-0 disabled never commits; affected is sentinel UNKNOWN."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='disabled',
            tier_1='prompt',
            change_type='feature',
        )
        assert result['tier_0_committed'] is False
        assert result['affected_modules'] is _AFFECTED_UNKNOWN

    def test_tier_0_disabled_yields_branch_b_for_normal_change_types(self):
        """Tier 1 cannot proceed without a diff -> Branch B short-circuits."""
        for tier_1 in ('prompt', 'auto', 'disabled'):
            result = _decide_architecture_refresh(
                baseline_present=True,
                tier_0='disabled',
                tier_1=tier_1,
                change_type='feature',
            )
            assert result['branch'] == 'B', f'Tier-0 disabled with tier_1={tier_1} must yield Branch B'
            assert result['display_detail'] == 'tier-0 disabled; tier-1 skipped'


class TestTier1ExitCells:
    """`committed` and `len(affected)` each decide half of the exit detail."""

    def test_exit_cell_population_is_the_full_two_by_two(self):
        """All four cells resolve to distinct branches — no cell is unreachable in the model."""
        cells = {
            _tier1_exit(committed=committed, affected=affected)[0]
            for committed in (True, False)
            for affected in ((), ('mod-x',))
        }
        assert cells == {'C', 'D', 'J', 'K'}, (
            f'the four exit cells must map to four distinct branches, got {sorted(cells)}'
        )

    def test_committed_with_empty_union_is_branch_j_not_c(self):
        """THE regression: a committed round with no added/removed is Branch J.

        Reached the way the standard names it — segment-1 plan-time descriptor
        edits leave the tree dirty (`preexisting_plan_writes`) while the discover
        verdict is `clean`, so `added` and `removed` are both empty. Keying the
        exit on the module union alone reports "no module structure changed" for
        a round that committed.
        """
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            attribution='clean',
            preexisting_plan_writes=True,
        )
        assert result['tier_0_committed'] is True, 'the fixture must actually commit, or the cell is not exercised'
        assert result['affected_modules'] == ()
        assert result['branch'] == 'J', (
            'a committed round with an empty module union must be Branch J; Branch C '
            'would report "no module structure changed" for a round that shipped a commit'
        )
        assert result['display_detail'] == _DETAIL_REFRESHED_NO_STRUCTURE_CHANGE
        assert '0 modules' not in result['display_detail'], (
            "Branch J must not interpolate the zero count — '(0 modules)' advertises "
            'a module delta the round does not have'
        )

    def test_committed_with_empty_union_under_change_type_shortcut_is_also_branch_j(self):
        """The same cell reached through the 4a exit rather than the 4b exit."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='bug_fix',
            attribution='clean',
            preexisting_plan_writes=True,
        )
        assert result['tier_0_committed'] is True
        assert result['branch'] == 'J', 'both Tier-1 exits must select the same cell for the same inputs'
        assert result['display_detail'] == _DETAIL_REFRESHED_NO_STRUCTURE_CHANGE

    def test_uncommitted_with_non_empty_union_is_branch_k(self):
        """The mirror cell: structure changed against origin/main, but not by this step.

        Reachable when the descriptor change already landed in an earlier commit
        on the branch, so the porcelain status is clean while `added` union
        `removed` is non-empty. This is the cell the standard's old
        "mark-step-done with appropriate detail" left unnamed.
        """
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='bug_fix',
            diff_added=('mod-x',),
            attribution='clean',
        )
        assert result['tier_0_committed'] is False
        assert result['affected_modules'] == ('mod-x',)
        assert result['branch'] == 'K'
        assert result['display_detail'] == 'module structure changed (1 modules); nothing to commit'

    def test_neither_dimension_is_branch_c(self):
        """The negative control: Branch C keeps the cell it legitimately owns."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='bug_fix',
            attribution='clean',
        )
        assert result['tier_0_committed'] is False
        assert result['affected_modules'] == ()
        assert result['branch'] == 'C'
        assert result['display_detail'] == _DETAIL_NO_STRUCTURE_CHANGE


class TestPushScannerControls:
    """The scanner distinguishes a prescribed push from a described one."""

    def test_positive_control_detects_the_pre_fix_push(self):
        """The pre-fix Tier-0 block IS reported — the guard would have gone red."""
        offenders, examined = scan_push_prescriptions(_TIER_0_BLOCK_WITH_PUSH)
        assert examined > 0, 'Control fixture resolved no command lines.'
        assert offenders == ['git -C {worktree_path} push'], (
            'The scanner failed to detect the push the pre-fix Tier-0 block '
            f'prescribed, so its clean verdict on the live standard proves nothing: {offenders}'
        )

    def test_negative_control_ignores_a_described_push(self):
        """Prose about pushing, and a comment recording its absence, are NOT prescriptions."""
        offenders, examined = scan_push_prescriptions(_TIER_0_BLOCK_WITHOUT_PUSH)
        assert examined > 0, 'Control fixture resolved no command lines, so the clean result is vacuous.'
        assert offenders == [], (
            'The scanner reported a push prescription in a block that only DESCRIBES '
            f'not pushing — it would fail every correctly-fixed step doc: {offenders}'
        )


class TestPublishedClassAttributions:
    @pytest.fixture(scope='class')
    @classmethod
    def manage_api_text(cls) -> str:
        return str(_MANAGE_API_MD.read_text(encoding='utf-8'))

    def test_published_table_states_the_declared_attributions(self, manage_api_text: str):
        published = _published_class_attributions(manage_api_text)
        print(f'published delta-class table: parsed {len(published)} row(s)')
        assert published, (
            'the delta-class table in manage-api.md parsed to 0 rows — the parser no '
            'longer resolves the published table, so the comparison below would be '
            'vacuous. Repair the parser or the table; do not delete this assertion.'
        )
        assert published == DELTA_CLASSES, (
            'the attribution published in manage-api.md disagrees with DELTA_CLASSES '
            f'(parsed {len(published)} row(s)): {published} != {DELTA_CLASSES}'
        )

    def test_positive_control_a_flipped_attribution_reddens_the_guard(self, manage_api_text: str):
        """A single flipped attribution must make the comparison above fail."""
        flipped = manage_api_text.replace(
            '| `index_entry_added` | plan |',
            '| `index_entry_added` | migration |',
            1,
        )
        assert flipped != manage_api_text, (
            'the control edited nothing — the published row it flips has changed shape, '
            'so it no longer demonstrates that the guard fires'
        )
        published = _published_class_attributions(flipped)
        assert len(published) == len(DELTA_CLASSES), 'the flip must change an attribution, not drop a row'
        assert published['index_entry_added'] == 'migration'
        assert published != DELTA_CLASSES

    def test_positive_control_a_dropped_row_reddens_the_guard(self, manage_api_text: str):
        """A row missing from the published table must make the comparison above fail."""
        dropped = ''.join(
            line
            for line in manage_api_text.splitlines(keepends=True)
            if not line.startswith('| `key_packages_rekey` |')
        )
        assert dropped != manage_api_text, (
            'the control dropped nothing — the published row it removes has changed '
            'shape, so it no longer demonstrates that the guard fires'
        )
        published = _published_class_attributions(dropped)
        assert len(published) == len(DELTA_CLASSES) - 1
        assert 'key_packages_rekey' not in published
        assert published != DELTA_CLASSES

    def test_positive_control_a_duplicate_row_is_rejected(self, manage_api_text: str):
        """Two contradictory rows for one class must raise, not silently merge.

        Injected as a SECOND row for a class the table already publishes, with a
        conflicting attribution. Under last-write-wins the guard above would see
        a mapping equal to ``DELTA_CLASSES`` at the expected row count — green
        over a document stating two things at once — so the rejection branch is
        what stands between the parser and that vacuity, and this control is
        what exercises it.
        """
        duplicated = ''.join(
            line + '| `index_entry_added` | migration | injected conflicting row |\n'
            if line.startswith('| `index_entry_added` |')
            else line
            for line in manage_api_text.splitlines(keepends=True)
        )
        assert duplicated != manage_api_text, (
            'the control injected nothing — the published row it duplicates has '
            'changed shape, so it no longer demonstrates that the parser rejects '
            'a duplicate'
        )
        with pytest.raises(ValueError, match='index_entry_added'):
            _published_class_attributions(duplicated)

    def test_negative_control_an_unresolvable_table_parses_to_zero_rows(self):
        """No table means no rows — which is what the published count turns into a failure."""
        assert _published_class_attributions('# Architecture Manage API\n\nJust prose.\n') == {}
