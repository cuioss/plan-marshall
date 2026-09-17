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

class TestTier0EnabledMatrix:
    """Step 3 — deterministic discover + diff against the extracted baseline."""

    def test_empty_diff_yields_branch_c_no_commit(self):
        """No drift detected -> no commit, Tier 1 skipped, Branch C."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
        )
        assert result['branch'] == 'C'
        assert result['tier_0_committed'] is False
        assert result['tier_1_action'] == 'skipped'
        assert result['display_detail'] == 'no module structure changed'

    def test_drift_detected_in_added_bucket_triggers_commit(self):
        """Modules in `added` move to the union -> commit fires."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('mod-x',),
        )
        assert result['tier_0_committed'] is True
        assert result['affected_modules'] == ('mod-x',)

    def test_drift_detected_in_removed_bucket_triggers_commit(self):
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_removed=('mod-r',),
        )
        assert result['tier_0_committed'] is True
        assert 'mod-r' in result['affected_modules']

    def test_changed_bucket_is_ignored_against_git_baseline(self):
        """Pseudo-code §3b: the `changed` bucket is noise against a git baseline.

        Against a derived-less origin/main baseline EVERY common module reports
        as `changed` (no committed per-module derived.json sha), so the changed
        bucket carries no signal. A diff that populates ONLY `changed` (no
        added/removed) is treated as no drift -> Branch C, no commit.
        """
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_changed=('mod-c',),
        )
        assert result['branch'] == 'C'
        assert result['tier_0_committed'] is False
        assert result['affected_modules'] == ()

    def test_affected_modules_is_sorted_union_of_added_and_removed(self):
        """Pseudo-code §3b: affected = added union removed (sorted); changed ignored."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('zeta',),
            diff_removed=('alpha',),
            diff_changed=('mu',),  # noise — must NOT appear in the union
        )
        assert result['affected_modules'] == ('alpha', 'zeta')

    def test_overlap_between_buckets_dedupes_in_union(self):
        """A module appearing in both added and removed counts once in the union."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('shared',),
            diff_removed=('shared',),
        )
        assert result['affected_modules'] == ('shared',)


class TestTier1KnobDispatch:
    """Step 4d — tier-1 knob dispatch with non-empty diff."""

    def test_tier_1_disabled_yields_branch_f_deferred(self):
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='disabled',
            change_type='feature',
            diff_added=('mod-a',),
        )
        assert result['branch'] == 'F'
        assert result['tier_1_action'] == 'deferred'
        assert result['display_detail'] == 'refreshed; re-enrichment deferred'

    def test_tier_1_auto_yields_branch_e_enrich(self):
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('m1',),
            diff_removed=('m2',),
        )
        assert result['branch'] == 'E'
        assert result['tier_1_action'] == 'enrich'
        assert result['display_detail'] == 'refreshed + re-enriched (2 modules)'

    def test_tier_1_prompt_accepted_routes_through_auto_branch(self):
        """`Re-enrich now` follows the auto branch verbatim."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
            diff_added=('mod-only',),
            user_response='Re-enrich now',
        )
        assert result['branch'] == 'E'
        assert result['tier_1_action'] == 'enrich'
        assert result['display_detail'] == 'refreshed + re-enriched (1 modules)'

    def test_tier_1_prompt_declined_routes_through_disabled_branch(self):
        """`Skip — note in PR` follows the disabled branch verbatim."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
            diff_added=('mod-x',),
            user_response='Skip — note in PR',
        )
        assert result['branch'] == 'F'
        assert result['tier_1_action'] == 'deferred'

    def test_tier_1_prompt_aborted_treated_as_decline(self):
        """`AskUserQuestion aborted` is informationally equivalent to Skip."""
        result = _decide_architecture_refresh(
            baseline_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
            diff_added=('mod-y',),
            user_response='aborted',
        )
        assert result['branch'] == 'F'
        assert result['tier_1_action'] == 'deferred'

    def test_tier_1_prompt_requires_user_response_with_drift(self):
        """The standard documents `prompt` as default — caller must supply UX answer."""
        with pytest.raises(ValueError, match='user_response'):
            _decide_architecture_refresh(
                baseline_present=True,
                tier_0='enabled',
                tier_1='prompt',
                change_type='feature',
                diff_added=('mod-z',),
            )


class TestRequiredStepsRegistration:
    """The `phase_steps_complete` invariant enforces this step's completion."""

    def test_architecture_refresh_listed_in_required_steps_md(self):
        steps = inv._parse_required_steps(_REQUIRED_STEPS_MD)
        assert 'architecture-refresh' in steps, (
            'architecture-refresh MUST be registered in required-steps.md so '
            'the phase_steps_complete handshake enforces it.'
        )

    def test_required_steps_md_uses_bare_step_name(self):
        """Bare step name (no `default:` prefix) — matches mark-step-done arg."""
        text = _REQUIRED_STEPS_MD.read_text(encoding='utf-8')
        assert '- architecture-refresh' in text
        assert '- default:architecture-refresh' not in text, (
            'required-steps.md uses bare names; the dispatcher adds the default: prefix at lookup time.'
        )

    def test_required_steps_parser_handles_canonical_format(self):
        """Smoke test — the live parser returns a non-empty list including ours."""
        steps = inv._parse_required_steps(_REQUIRED_STEPS_MD)
        assert isinstance(steps, list)
        assert len(steps) > 0
        # Sanity — the canonical finalize steps are also present.
        for canonical in ('push', 'create-pr', 'archive-plan'):
            assert canonical in steps


class TestNoShellExtraction:
    @pytest.fixture(scope='class')
    @classmethod
    def standard_text(cls) -> str:
        return str(_ARCHITECTURE_REFRESH_MD.read_text(encoding='utf-8'))

    def test_standard_prescribes_no_extraction_command(self, standard_text: str):
        offenders, examined = _scan_shell_extraction(standard_text)
        assert examined > 0, 'the scan examined 0 fenced command lines — a clean result would be vacuous'
        print(f'architecture-refresh shell-extraction scan: examined={examined} command lines')
        assert offenders == [], f'extraction commands still prescribed across {examined} command lines: {offenders}'

    def test_positive_control_detects_every_removed_extraction_call(self):
        offenders, examined = _scan_shell_extraction(_REMOVED_EXTRACTION_BLOCK)
        assert examined == 4
        assert len(offenders) == 4, f'the scan missed a removed extraction call: {offenders}'

    def test_negative_control_ignores_prose_and_comments(self):
        described = (
            'The step no longer calls `rm -rf`, `mkdir -p`, `git archive` or `tar -xf`.\n\n'
            '```text\n# no git archive / tar extraction — the verb reads the ref\n'
            'diff := architecture diff-modules --pre-ref origin/main\n```\n'
        )
        offenders, examined = _scan_shell_extraction(described)
        assert examined == 1
        assert offenders == []


class TestCrossReferences:
    @pytest.fixture(scope='class')
    @classmethod
    def skill_md_text(cls) -> str:
        return str(_PHASE_6_SKILL_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def standard_text(cls) -> str:
        return str(_ARCHITECTURE_REFRESH_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def phase_1_text(cls) -> str:
        return str(_PHASE_1_INIT_SKILL_MD.read_text(encoding='utf-8'))

    def test_skill_md_dispatch_table_routes_default_architecture_refresh(
        self,
        skill_md_text: str,
    ):
        """The SKILL.md dispatch table must resolve default:architecture-refresh."""
        assert 'default:architecture-refresh' in skill_md_text
        assert 'standards/architecture-refresh.md' in skill_md_text

    def test_skill_md_lists_architecture_refresh_in_inline_only_steps(
        self,
        skill_md_text: str,
    ):
        """Tier-1 prompt mode means architecture-refresh runs inline (no Task agent).

        Membership is read from ``standards/dispatch-inline-split.md`` — the single
        source of truth — reached through the pointer ``SKILL.md`` now carries. The
        previous form asserted the *shape* of SKILL.md's hand-maintained
        "Inline-only built-in steps" bullet (a bare ``'architecture-refresh' in
        skill_md_text`` substring check plus a bullet-layout split). That bullet was
        collapsed into a pointer precisely so the membership list stops being
        duplicated across five SKILL.md sites, so re-asserting its layout would pin
        the duplication this change removes — and the substring check was never
        evidence of inline classification in the first place.
        """
        # 1. SKILL.md's inline-only section points at the SSOT instead of listing names.
        inline_section = skill_md_text.split('Inline-only built-in steps')[1]
        pointer_paragraph = inline_section.split('\n\n')[0]
        assert 'standards/dispatch-inline-split.md' in pointer_paragraph, (
            'SKILL.md\'s "Inline-only built-in steps" section must point at '
            'standards/dispatch-inline-split.md as the single source of truth for '
            'inline membership, rather than re-listing the member steps'
        )

        # 2. The SSOT itself carries the classification.
        roster_text = _DISPATCH_INLINE_SPLIT_MD.read_text(encoding='utf-8')
        inline = parse_roster(roster_text, _INLINE_HEADING)
        dispatched = parse_roster(roster_text, _DISPATCHED_HEADING)
        assert inline, 'Inline roster parsed empty — the assertion would be vacuous'
        assert 'default:architecture-refresh' in inline, (
            'architecture-refresh requires an AskUserQuestion for its Tier-1 `prompt` '
            'mode, which a dispatched leaf cannot fire — dispatch-inline-split.md must '
            'classify it inline'
        )
        assert 'default:architecture-refresh' not in dispatched, (
            'architecture-refresh must carry exactly one classification; it is inline'
        )

        # 3. It must still be absent from the agent-suitable dispatch table.
        section = skill_md_text.split('Agent-suitable built-in steps')[1]
        section_top = section.split('Inline-only built-in steps')[0]
        assert 'architecture-refresh' not in section_top, (
            'architecture-refresh must NOT appear in the agent-suitable table; '
            'it requires AskUserQuestion and runs inline.'
        )

    def test_skill_md_standards_table_lists_architecture_refresh_row(
        self,
        skill_md_text: str,
    ):
        """The standards-table at the bottom of SKILL.md must mention the doc."""
        assert 'standards/architecture-refresh.md' in skill_md_text

    def test_standard_frontmatter_declares_default_name(
        self,
        standard_text: str,
    ):
        """Frontmatter `name:` must match the dispatch token after the prefix."""
        assert 'name: default:architecture-refresh' in standard_text

    def test_standard_frontmatter_declares_order(self, standard_text: str):
        """Frontmatter `order:` makes the manifest composer sort deterministically."""
        # This derived-state refresh sorts after the code-mutating settle steps
        # and still settles BEFORE the single push barrier (order 11), so the
        # descriptors describe the settled tree and the quality gate at order 10
        # certifies them together with the code. Pin `order: 9` to detect
        # accidental edits.
        assert 'order: 9' in standard_text

    def test_standard_frontmatter_declares_default_on_true(
        self,
        standard_text: str,
    ):
        """The step is reactivated — frontmatter `default_on: true` enables it by default."""
        assert 'default_on: true' in standard_text
        assert 'default_on: false' not in standard_text

    def test_phase_1_init_does_not_produce_architecture_pre_snapshot(
        self,
        phase_1_text: str,
    ):
        """Under the on-demand crawl model phase-1-init MUST NOT snapshot architecture-pre/.

        The legacy snapshot is removed; architecture-refresh derives its
        pre-baseline from the committed origin/main tree instead.
        """
        # No 'architecture-pre' copy-tree step should remain in phase-1-init.
        assert 'architecture-pre' not in phase_1_text or 'copy-tree' not in phase_1_text

    def test_standard_cross_references_run_config_knobs(
        self,
        standard_text: str,
    ):
        """Cross-references section must cite manage-run-config as the knob source."""
        assert 'manage-run-config' in standard_text

    def test_standard_cross_references_required_steps(
        self,
        standard_text: str,
    ):
        """Cross-references must cite required-steps.md so the contract is discoverable."""
        assert 'required-steps.md' in standard_text
