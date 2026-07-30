#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived detector: no compose-time subtraction may drop a step silently.

**What this module is.** The other two new modules in this deliverable pin two
specific defects. This one pins the CLASS: every predicate in the composer that
narrows a step list must report what it removed. It exists because the
outline-time derivation found the real population to be **thirteen** subtraction
sites, not the three the request named — five matrix rows subtracted in complete
silence and two more reported only an aggregate — so a per-site test written
against the known members would have covered a quarter of the surface and read
as complete.

**How the population is derived (never hand-listed).** Two halves, both read off
the module rather than typed into this file:

*Half A — the ``_apply_*`` narrowing callables.* Every public name on the
composer matching ``_apply_*``. The composer re-exports the pre-filters defined
in ``_manifest_rules.py`` alongside the ones it defines itself, so one scan spans
both files. ``test_apply_sites_are_fully_re_exported`` additionally asserts that
``_manifest_rules``' own ``_apply_*`` set is a SUBSET of the scanned set — without
it, a new pre-filter added to ``_manifest_rules`` but never re-exported would be
invisible to the derivation, and the detector would report full coverage of a
population it could not see.

*Half B — the ``_decide`` matrix rows.* Derived BEHAVIOURALLY by driving
``_decide`` across the cross-product of its own declared input enums
(``VALID_CHANGE_TYPES`` x ``VALID_SCOPE_ESTIMATES`` x recipe-present x
affected-files x task-queue-active) and collecting the distinct rule names it
returns. A row added to the matrix therefore enters the population the moment it
becomes reachable, with nothing to update here.

**What happens when someone adds a fourteenth subtraction site.** Half A picks
the new ``_apply_*`` callable up automatically. ``_SITE_INVOCATIONS`` — the table
that drives each site into a firing drop — then has no entry for it, and
``test_every_derived_site_is_covered`` fails naming the uncovered site. The
author cannot add the entry without stating how the new site reports its
subtraction, and ``test_every_site_reports_every_step_it_removed`` then holds
that report to naming exactly the steps that vanished. The failure is loud at
the point of addition; there is no path by which a new site joins the composer
and quietly drops steps. The same holds for a new matrix row through Half B,
where the record assertion is applied to every reachable row with no table at
all.

**Why the reports are not all the same shape.** They genuinely are not, and
flattening that into one assertion would be false. A multi-step site must name
each dropped step individually (the ``{step, reason}`` convention the
security-class gate established); a single-step gate's identity is structurally
fixed by its own parameter, so its report is a flag or a verdict and the step
needs no naming. ``_SITE_INVOCATIONS`` therefore declares each site's report
KIND, and the shared invariant is asserted per kind: *the report accounts for
exactly the steps the site removed*.
"""

import json
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import _manifest_rules
import _manifest_validation
import pytest

from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_subtraction_visibility_population',
)

_decide = _mem._decide
cmd_compose = _mem.cmd_compose
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
VALID_CHANGE_TYPES = _mem.VALID_CHANGE_TYPES
VALID_SCOPE_ESTIMATES = _mem.VALID_SCOPE_ESTIMATES

_mem._emit_decision_log = lambda *a, **kw: None

#: The cardinality the outline-time derivation recorded (§ "D1 gate result — the
#: derived subtraction population"). It is asserted as a FLOOR, not an equality:
#: the derivation below also sees the three already-loud confirming sites the
#: outline listed outside its table, so the live count legitimately exceeds
#: thirteen. A count that falls BELOW it means the derivation stopped seeing
#: sites it used to see — the failure mode a hand-listed population hides.
_OUTLINE_DERIVED_SITE_COUNT = 13

#: The three sites the original request named. Asserted as members of the derived
#: population, never as its definition — the whole finding of the derivation is
#: that these three are a small minority of it.
_REQUEST_KNOWN_SITES = frozenset(
    {
        '_apply_scope_gated_finalize',
        '_apply_pre_push_quality_gate_inactive',
        '_apply_security_class_inactive',
    }
)

#: The vacuous pre-filter removed by this plan, together with its unreachable
#: emitter and its always-False result key. Asserted ABSENT: ``setattr`` on a
#: module succeeds for a name that was never defined, so a stale neutralization
#: in some other test module would silently re-create a removed attribute rather
#: than failing — absence has to be asserted explicitly to be known.
_REMOVED_VACUOUS_SITE = '_apply_pre_submission_self_review_inactive'
_REMOVED_VACUOUS_EMITTER = '_log_pre_submission_self_review_omitted'
_REMOVED_VACUOUS_RESULT_KEY = 'pre_submission_self_review_omitted'


# =============================================================================
# Derivation
# =============================================================================


def _derive_apply_sites(module: Any) -> set[str]:
    """Return every ``_apply_*`` narrowing callable exposed by ``module``."""
    return {
        name
        for name in dir(module)
        if name.startswith('_apply_') and callable(getattr(module, name))
    }


#: Disjoint candidate lists for the matrix drive. Phase-5 and phase-6 share no
#: step id, so a removed step is unambiguously attributable to one list — which
#: is what lets the record assertion compare a single flat set.
_MATRIX_PHASE_5_CANDIDATES = ('verify:quality-gate', 'verify:module-tests', 'verify:coverage')
_MATRIX_PHASE_6_CANDIDATES = (*DEFAULT_PHASE_6_STEPS, 'ci-wait')


def _drive_decision_matrix() -> list[tuple[str, list[str], list[dict[str, str]]]]:
    """Drive ``_decide`` over its own declared input enums; return one row per call.

    Each entry is ``(rule, removed_steps, records)``. The inputs are the module's
    OWN vocabularies (``VALID_CHANGE_TYPES`` / ``VALID_SCOPE_ESTIMATES``) plus the
    two-valued axes the matrix branches on, so a newly-reachable row appears here
    without this function changing.
    """
    rows: list[tuple[str, list[str], list[dict[str, str]]]] = []
    for change_type in VALID_CHANGE_TYPES:
        for scope_estimate in VALID_SCOPE_ESTIMATES:
            for recipe_key in (None, 'lesson_cleanup'):
                for affected_files_count in (0, 3):
                    for task_queue_active in (False, True):
                        body, rule, records = _decide(
                            change_type=change_type,
                            track='simple',
                            scope_estimate=scope_estimate,
                            recipe_key=recipe_key,
                            affected_files_count=affected_files_count,
                            phase_5_candidates=list(_MATRIX_PHASE_5_CANDIDATES),
                            phase_6_candidates=list(_MATRIX_PHASE_6_CANDIDATES),
                            task_queue_active=task_queue_active,
                        )
                        kept_5 = body['phase_5']['verification_steps']
                        kept_6 = body['phase_6']['steps']
                        removed = [s for s in _MATRIX_PHASE_5_CANDIDATES if s not in kept_5]
                        removed += [s for s in _MATRIX_PHASE_6_CANDIDATES if s not in kept_6]
                        rows.append((rule, removed, records))
    return rows


def _derive_matrix_rule_keys() -> set[str]:
    """Return every ``_decide`` rule name reachable from the declared input enums."""
    return {rule for rule, _removed, _records in _drive_decision_matrix()}


def _derive_population() -> set[str]:
    """The full derived subtraction-site population: Half A + Half B."""
    return _derive_apply_sites(_mem) | _derive_matrix_rule_keys()


# =============================================================================
# Per-site invocation table
# =============================================================================


@dataclass
class SiteRun:
    """One ``_apply_*`` site driven into a firing drop.

    ``kind`` names how the site reports its subtraction:

    - ``records`` — a ``list[{'step', 'reason'}]``, one per dropped step.
    - ``ids`` — a ``list[str]`` of dropped step ids.
    - ``gate_records`` — a ``list[{'gate', 'step'}]``, one per gate that changed
      the list.
    - ``flag`` — a boolean; the site is parameterized by exactly one step
      (``single_step``), so its identity needs no naming.
    - ``verdict`` — a ``(decision, reason)`` pair for a single-step gate
      (``single_step``), where the decision names the authority's answer and the
      reason is threaded from that authority rather than composed locally.
    """

    before: list[str]
    after: list[str]
    kind: str
    report: Any
    single_step: str | None = None
    removed: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.removed = [s for s in self.before if s not in self.after]


def _run_commit_push_disabled(monkeypatch) -> SiteRun:
    before = ['push', 'pre-push-quality-gate', 'pre-submission-self-review', 'archive-plan']
    kept, records = _mem._apply_commit_push_disabled(list(before), False)
    return SiteRun(before, kept, 'records', records)


def _run_code_step_inactive(monkeypatch) -> SiteRun:
    before = ['finalize-step-simplify', 'archive-plan']
    kept, fired = _mem._apply_code_step_inactive(
        list(before), 'finalize-step-simplify', 'analysis', 0
    )
    return SiteRun(before, kept, 'flag', fired, single_step='finalize-step-simplify')


def _run_simplify_inactive(monkeypatch) -> SiteRun:
    before = ['finalize-step-simplify', 'archive-plan']
    kept, fired = _mem._apply_simplify_inactive(list(before), 'analysis', 0)
    return SiteRun(before, kept, 'flag', fired, single_step='finalize-step-simplify')


def _run_security_class_inactive(monkeypatch) -> SiteRun:
    before = ['finalize-step-security-audit', 'archive-plan']
    kept, records = _mem._apply_security_class_inactive(
        list(before), frozenset({'finalize-step-security-audit'}), 0, 0
    )
    return SiteRun(before, kept, 'records', records)


def _run_scope_gated_finalize(monkeypatch) -> SiteRun:
    before = ['plan-marshall:plan-retrospective', 'archive-plan']
    kept, dropped, _immune = _mem._apply_scope_gated_finalize(list(before), 'surgical', None)
    return SiteRun(before, kept, 'ids', dropped)


def _run_unresolved_ask_provider_drop(monkeypatch) -> SiteRun:
    before = ['automatic-review', 'archive-plan']
    kept, dropped = _mem._apply_unresolved_ask_provider_drop(
        list(before), {'automatic-review': {'lane': 'ask'}}, None, None
    )
    return SiteRun(before, kept, 'ids', dropped)


def _run_ceremony_finalize_selection(monkeypatch) -> SiteRun:
    before = ['pre-submission-self-review', 'archive-plan']
    steps = list(before)
    _forced_in, forced_out = _mem._apply_ceremony_finalize_selection(
        steps,
        {'self_review': 'never', 'qgate': 'auto', 'simplify': 'auto', 'security_audit': 'auto'},
    )
    return SiteRun(before, steps, 'gate_records', forced_out)


def _run_pre_push_quality_gate_inactive(monkeypatch) -> SiteRun:
    import extension_base

    monkeypatch.setattr(
        extension_base,
        'should_execute_build',
        lambda _cmd, _plan_id, *a, **kw: {
            'decision': 'not_necessary',
            'reason': 'plan footprint touches no build_map glob',
        },
    )
    before = ['pre-push-quality-gate', 'archive-plan']
    kept, decision, reason = _mem._apply_pre_push_quality_gate_inactive(list(before), 'a-plan')
    return SiteRun(
        before, kept, 'verdict', (decision, reason), single_step='pre-push-quality-gate'
    )


def _run_canonical_verify_inactive(monkeypatch) -> SiteRun:
    monkeypatch.setattr(_mem, '_resolve_footprint', lambda _plan_id: ['src/plain_module.py'])
    before = ['verify:integration-tests', 'verify:quality-gate']
    kept, dropped = _mem._apply_canonical_verify_inactive(list(before), 'a-plan', {})
    return SiteRun(before, kept, 'ids', dropped)


def _run_domain_seeded_step_resolvability(monkeypatch) -> SiteRun:
    monkeypatch.setattr(
        _manifest_validation, '_domain_appended_canonicals', lambda: frozenset({'arch-gate'})
    )
    monkeypatch.setattr(_mem, '_invoke_architecture_resolve', lambda *a, **kw: None)
    before = ['verify:arch-gate', 'verify:quality-gate']
    kept, dropped = _mem._apply_domain_seeded_step_resolvability(list(before), 'a-plan')
    return SiteRun(before, kept, 'ids', dropped)


def _run_lane_resolution(monkeypatch) -> SiteRun:
    lanes = {'sonar-roundtrip': {'class': 'prunable', 'tier': 'full', 'cost_size': 'L'}}
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step: lanes.get(step))
    before = ['sonar-roundtrip', 'archive-plan']
    kept, records, _warnings = _mem._apply_lane_resolution(list(before), 'minimal', None, 'a-plan')
    return SiteRun(before, kept, 'records', records)


#: Every derived ``_apply_*`` site, mapped to a callable that drives it into a
#: FIRING drop. This table is the one hand-maintained artifact in the module —
#: and its incompleteness is loud, not silent: ``test_every_derived_site_is_covered``
#: fails the moment the derived population contains a key this table does not.
_SITE_INVOCATIONS = {
    '_apply_commit_push_disabled': _run_commit_push_disabled,
    '_apply_code_step_inactive': _run_code_step_inactive,
    '_apply_simplify_inactive': _run_simplify_inactive,
    '_apply_security_class_inactive': _run_security_class_inactive,
    '_apply_scope_gated_finalize': _run_scope_gated_finalize,
    '_apply_unresolved_ask_provider_drop': _run_unresolved_ask_provider_drop,
    '_apply_ceremony_finalize_selection': _run_ceremony_finalize_selection,
    '_apply_pre_push_quality_gate_inactive': _run_pre_push_quality_gate_inactive,
    '_apply_canonical_verify_inactive': _run_canonical_verify_inactive,
    '_apply_domain_seeded_step_resolvability': _run_domain_seeded_step_resolvability,
    '_apply_lane_resolution': _run_lane_resolution,
}


# =============================================================================
# The derived population itself
# =============================================================================


class TestDerivedPopulation:
    """The population is read off the module and is bigger than the known members."""

    def test_population_is_non_empty(self):
        assert _derive_population()

    def test_population_contains_the_three_request_known_sites(self):
        population = _derive_population()

        missing = sorted(_REQUEST_KNOWN_SITES - population)
        assert not missing, f'derivation stopped seeing known subtraction sites: {missing}'

    def test_population_meets_the_outline_derived_floor(self):
        """A count BELOW the outline's thirteen means the derivation shrank.

        Asserted as a floor rather than an equality: the derivation also sees the
        three already-loud confirming sites the outline listed outside its table,
        so the live count legitimately exceeds thirteen. What must never happen is
        the count dropping — that is the derivation losing sight of a site, which
        is precisely the failure a hand-listed population cannot detect.
        """
        population = _derive_population()

        assert len(population) >= _OUTLINE_DERIVED_SITE_COUNT, (
            f'derived population has {len(population)} sites '
            f'({sorted(population)}) — below the {_OUTLINE_DERIVED_SITE_COUNT} the '
            'outline-time derivation recorded. A site the scan used to see has '
            'become invisible to it; fix the derivation, do not lower the floor.'
        )

    def test_apply_sites_are_fully_re_exported(self):
        """A pre-filter defined in ``_manifest_rules`` must be visible to Half A.

        Half A scans the composer entry module. That is complete only while every
        ``_manifest_rules`` pre-filter is re-exported there. A new site added to
        ``_manifest_rules`` without the re-export would be silently outside the
        derived population — full coverage of a population with a hole in it.
        """
        rules_sites = _derive_apply_sites(_manifest_rules)
        composer_sites = _derive_apply_sites(_mem)

        invisible = sorted(rules_sites - composer_sites)
        assert not invisible, (
            f'_manifest_rules defines {invisible} but the composer does not re-export '
            'them, so the derived population cannot see them'
        )

    def test_the_vacuous_pre_filter_and_its_emitter_are_gone(self):
        """Absence is asserted, never assumed.

        ``setattr`` on a module succeeds for a name that was never defined, so a
        stale neutralization elsewhere in the suite would RE-CREATE the removed
        emitter rather than failing. Only an explicit absence assertion makes the
        removal knowable.
        """
        assert not hasattr(_mem, _REMOVED_VACUOUS_SITE)
        assert not hasattr(_mem, _REMOVED_VACUOUS_EMITTER)
        assert not hasattr(_manifest_rules, _REMOVED_VACUOUS_SITE)


# =============================================================================
# Coverage completeness — the fourteenth-site tripwire
# =============================================================================


class TestSiteCoverageCompleteness:
    """The invocation table must account for the derived population exactly."""

    def test_every_derived_site_is_covered(self):
        """A newly-added subtraction site fails HERE, at the point of addition.

        This is the assertion that makes the module a detector rather than a
        sample. A fourteenth ``_apply_*`` site enters the derived population
        automatically and has no invocation entry, so the test names it and
        fails; the author cannot satisfy it without declaring how the new site
        reports its subtraction, which the report-invariant test then checks.
        """
        uncovered = sorted(_derive_apply_sites(_mem) - set(_SITE_INVOCATIONS))

        assert not uncovered, (
            f'uncovered compose-time subtraction site(s): {uncovered}. Add an entry to '
            '_SITE_INVOCATIONS that drives each into a firing drop and declares how it '
            'reports the subtraction. A site with no entry can drop steps silently.'
        )

    def test_no_stale_invocation_entries(self):
        """The mirror direction — a table entry for a site that no longer exists.

        Without it the table would keep passing after a site was deleted, and its
        entry would sit there as a false claim of live coverage.
        """
        stale = sorted(set(_SITE_INVOCATIONS) - _derive_apply_sites(_mem))

        assert not stale, f'_SITE_INVOCATIONS names sites that no longer exist: {stale}'


# =============================================================================
# The invariant — every site reports exactly what it removed
# =============================================================================


class TestEverySiteReportsItsSubtraction:
    """No compose-time subtraction may leave the candidate list unaccounted for."""

    @pytest.mark.parametrize('site_name', sorted(_SITE_INVOCATIONS))
    def test_site_actually_drops_something(self, site_name, monkeypatch):
        """Each invocation must FIRE, or its report assertion proves nothing.

        A site driven with inputs that happen not to trigger the drop reports an
        empty record list, which trivially "accounts for" the empty removed set.
        Pinning that the drop fired first is what keeps the invariant below from
        passing vacuously.
        """
        run = _SITE_INVOCATIONS[site_name](monkeypatch)

        assert run.removed, f'{site_name} was not driven into a firing drop'

    @pytest.mark.parametrize('site_name', sorted(_SITE_INVOCATIONS))
    def test_every_site_reports_every_step_it_removed(self, site_name, monkeypatch):
        run = _SITE_INVOCATIONS[site_name](monkeypatch)

        if run.kind == 'records':
            assert all(set(r) == {'step', 'reason'} for r in run.report), (
                f'{site_name} emitted a malformed subtraction record: {run.report}'
            )
            assert all(r['reason'] for r in run.report), (
                f'{site_name} emitted a record with no reason: {run.report}'
            )
            assert {r['step'] for r in run.report} == set(run.removed)
        elif run.kind == 'ids':
            assert set(run.report) == set(run.removed)
        elif run.kind == 'gate_records':
            assert all('step' in r and 'gate' in r for r in run.report)
            assert {r['step'] for r in run.report} == set(run.removed)
        elif run.kind == 'flag':
            # A single-step gate: identity is fixed by the site's own parameter,
            # so the report is the fired flag rather than a named record.
            assert run.report is True
            assert run.removed == [run.single_step]
        elif run.kind == 'verdict':
            decision, reason = run.report
            assert decision == 'not_necessary'
            assert reason, f'{site_name} dropped a step without the authority reason'
            assert run.removed == [run.single_step]
        else:  # pragma: no cover — a new kind must be given an assertion arm
            pytest.fail(f'{site_name} declares an unknown report kind {run.kind!r}')

    @pytest.mark.parametrize('site_name', sorted(_SITE_INVOCATIONS))
    def test_site_reports_nothing_it_did_not_remove(self, site_name, monkeypatch):
        """The other direction: a report may not name a step that survived.

        A site that reported its whole candidate list would satisfy a
        "names every removed step" check while telling the operator that steps
        which are still in the manifest were dropped.
        """
        run = _SITE_INVOCATIONS[site_name](monkeypatch)

        if run.kind in ('records', 'gate_records'):
            reported = {r['step'] for r in run.report}
        elif run.kind == 'ids':
            reported = set(run.report)
        else:
            reported = {run.single_step}
        survivors = reported & set(run.after)
        assert not survivors, f'{site_name} reported surviving step(s) as dropped: {survivors}'


# =============================================================================
# The decision matrix — every reachable row reports its own narrowing
# =============================================================================


class TestDecisionMatrixRowsReportTheirNarrowing:
    """Half B, asserted over every reachable row with no per-row table at all.

    Five of these rows narrowed in complete silence before this plan. The
    assertions are applied to the WHOLE drive rather than to named rows, so a new
    matrix row is held to the same contract the moment it becomes reachable.
    """

    def test_the_drive_reaches_more_than_one_rule(self):
        """Guards the drive itself: a matrix that only ever returned the default
        row would make every assertion below vacuous."""
        assert len(_derive_matrix_rule_keys()) > 1

    def test_every_narrowing_row_emits_well_formed_records(self):
        for rule, removed, records in _drive_decision_matrix():
            if not removed:
                continue
            assert records, f"decide rule '{rule}' narrowed {removed} but reported nothing"
            assert all(set(r) == {'step', 'reason'} for r in records), (
                f"decide rule '{rule}' emitted a malformed record: {records}"
            )
            assert all(r['reason'] for r in records), (
                f"decide rule '{rule}' emitted a record with no reason: {records}"
            )

    def test_every_narrowing_row_names_exactly_the_steps_it_removed(self):
        for rule, removed, records in _drive_decision_matrix():
            assert {r['step'] for r in records} == set(removed), (
                f"decide rule '{rule}' reported {sorted({r['step'] for r in records})} "
                f'but removed {sorted(set(removed))}'
            )

    def test_a_row_that_narrows_nothing_reports_nothing(self):
        """The paired direction — no row may invent a subtraction it did not make."""
        for rule, removed, records in _drive_decision_matrix():
            if removed:
                continue
            assert records == [], f"decide rule '{rule}' reported {records} without narrowing"

    def test_at_least_one_row_narrows_and_one_does_not(self):
        """Both branches of the two tests above must actually be exercised."""
        rows = _drive_decision_matrix()

        assert any(removed for _rule, removed, _records in rows)
        assert any(not removed for _rule, removed, _records in rows)


# =============================================================================
# The removed result key does not survive into a composed result
# =============================================================================


class TestRemovedResultKeyIsAbsentFromCompose:
    """The always-False result key is gone from the compose contract itself.

    Asserting only that the pre-filter and its emitter are absent from the module
    would leave a hand-written ``'pre_submission_self_review_omitted': False``
    entry in the result dict undetected — a dead key a consumer could still read
    and believe.
    """

    def test_compose_result_carries_no_pre_submission_self_review_omitted(self, plan_context):
        plan_id = 'population-compose-contract'
        status_path = Path(plan_context.plan_dir_for(plan_id)) / 'status.json'
        status_path.write_text(json.dumps({'metadata': {}}))

        result = cmd_compose(
            Namespace(
                plan_id=plan_id,
                change_type='feature',
                track='complex',
                scope_estimate='multi_module',
                recipe_key=None,
                affected_files_count=3,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
                commit_and_push=None,
            )
        )

        assert result is not None and result['status'] == 'success'
        assert _REMOVED_VACUOUS_RESULT_KEY not in result
