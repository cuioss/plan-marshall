#!/usr/bin/env python3
"""Regression tests for the project-local ``audit-archived-plan-retrospectives``.

The audit skill is hybrid: ``scripts/audit.py`` is the deterministic computation
core (the testable unit) and ``SKILL.md`` is the LLM orchestration half. The
script has NO executor notation — it runs via direct ``python3 .../audit.py`` —
so this module imports it via ``importlib.util.spec_from_file_location`` (the
established pattern for path-resolved project scripts).

Coverage:

- D1 — ``detect_name_drift`` role resolution (purely in-code, no role-file
  read): the parameterized canonical-verify step IDs
  (``default:verify:{canonical}``), the legacy bare default-step names, the
  ``default:``-namespaced case (``lesson-2026-05-29-13-001.md`` sub-lesson
  13-002), unresolvable roles (unknown canonical / unknown bare name), and the
  empty-phase_5 no-op.
- D1 — precision/severity: genuine signals counted, informational rows excluded
  from the genuine-signal total.
- D2 — ``dormate_plans`` batch dormation: multi-id and ``--dormate-all`` success,
  inert-without-confirmed, all-or-nothing refuse-on-clash, and silent dedup.
- D4 — ``dormate_plans`` path-traversal hardening: ``../``, absolute, and embedded
  path-separator ``plan_id`` values are refused before any move.
- D8 — retrospective-token exclusion across the three metrics-related checks.
"""

import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT

_AUDIT_SCRIPT = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'audit-archived-plan-retrospectives'
    / 'scripts'
    / 'audit.py'
)

def _load_audit():
    spec = importlib.util.spec_from_file_location('audit_under_test', _AUDIT_SCRIPT)
    assert spec is not None, f'Failed to load module spec for {_AUDIT_SCRIPT}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before exec_module so @dataclass can resolve the module via
    # sys.modules[cls.__module__] (required under Python 3.14's dataclasses
    # with `from __future__ import annotations`).
    sys.modules['audit_under_test'] = mod
    spec.loader.exec_module(mod)
    return mod

audit = _load_audit()

def _inputs(phase_5: list[str]) -> Any:
    """Build a minimal PlanInputs carrying only the phase_5 manifest list."""
    return audit.PlanInputs(
        plan_id='test-plan',
        plan_dir=PROJECT_ROOT / '.plan' / 'temp' / 'nonexistent-plan',
        manifest_present=True,
        manifest_phase_5=list(phase_5),
    )

# =============================================================================
# D1 — detect_name_drift role resolution
# =============================================================================

class TestNameDriftRoleResolution:
    def test_parameterized_canonical_verify_steps_not_flagged(self):
        # the post-deletion shape: a well-composed manifest carries the single
        # parameterized canonical-verify step, one row per canonical.
        inputs = _inputs(['default:verify:quality-gate', 'default:verify:module-tests'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)
        resolved = {
            audit._resolve_step_role(PROJECT_ROOT, s, cache)
            for s in inputs.manifest_phase_5
        }

        # quality-gate → quality-gate, module-tests → module-tests; resolution is
        # in-code via the canonical→role table (no role-file read).
        assert drift is None
        assert resolved == {'quality-gate', 'module-tests'}

    def test_canonical_verify_aliases_resolve_to_module_tests(self):
        # the `verify` and `module-tests` canonicals both map to module-tests;
        # a coverage canonical resolves but alone gives zero intersection.
        cache: dict[str, str | None] = {}

        assert (
            audit._resolve_step_role(PROJECT_ROOT, 'default:verify:verify', cache)
            == 'module-tests'
        )
        assert (
            audit._resolve_step_role(PROJECT_ROOT, 'verify:module-tests', cache)
            == 'module-tests'
        )
        assert (
            audit._resolve_step_role(PROJECT_ROOT, 'default:verify:coverage', cache)
            == 'coverage'
        )

    def test_canonical_verify_alongside_coverage_not_flagged(self):
        # a coverage/integration step alongside a core role does NOT mis-flag:
        # the intersection with {quality-gate, module-tests} is non-empty.
        inputs = _inputs(
            ['default:verify:quality-gate', 'default:verify:coverage']
        )
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is None

    def test_legacy_bare_step_ids_not_flagged(self):
        # archived plans whose manifests predate the parameterized form carry the
        # legacy bare names; they resolve in-code via the back-compat table.
        inputs = _inputs(['quality_check', 'build_verify'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        # quality_check → quality-gate, build_verify → module-tests
        assert drift is None
        assert cache['quality_check'] == 'quality-gate'
        assert cache['build_verify'] == 'module-tests'

    def test_namespaced_legacy_step_ids_resolve_to_roles_and_not_flagged(self):
        # the lesson-2026-05-29-13-001 sub-lesson 13-002 namespaced shape
        inputs = _inputs(['default:quality_check', 'default:build_verify'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)
        resolved = {
            audit._resolve_step_role(PROJECT_ROOT, s, cache)
            for s in inputs.manifest_phase_5
        }

        # the default: prefix is stripped and roles resolve correctly
        assert drift is None
        assert resolved == {'quality-gate', 'module-tests'}

    def test_unknown_canonical_flagged_as_genuine_drift(self):
        # a parameterized step whose {canonical} segment is not in the table
        inputs = _inputs(['default:verify:bogus-canonical'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is not None
        assert 'unresolvable role' in drift

    def test_unresolvable_role_flagged_as_genuine_drift(self):
        # a bare step name absent from both the canonical and legacy tables
        inputs = _inputs(['not_a_real_step'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is not None
        assert 'unresolvable role' in drift

    def test_resolution_is_in_code_independent_of_filesystem(self, tmp_path: Path):
        # resolution no longer reads any role-file: a repo_root with no
        # phase-5-execute/standards directory resolves the same as PROJECT_ROOT.
        cache: dict[str, str | None] = {}

        role = audit._resolve_step_role(tmp_path, 'default:verify:quality-gate', cache)

        assert role == 'quality-gate'

    def test_empty_phase_5_returns_no_drift(self):
        inputs = _inputs([])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is None

# =============================================================================
# D1 — precision / severity in the manifest block summary
# =============================================================================

class TestManifestSeverityPrecision:
    def test_genuine_signal_count_counts_only_genuine_rows(self):
        # one drift row, one populated name_drift, two informational
        rows = [
            {'verdict': 'drift', 'name_drift': None},
            {'verdict': 'ok', 'name_drift': 'unresolvable role: foo'},
            {'verdict': 'incomplete', 'name_drift': None},
            {'verdict': 'unloggable', 'name_drift': None},
            {'verdict': 'ok', 'name_drift': None},
        ]
        full_rows = [
            {
                'plan_id': f'p{i}',
                'reason': '',
                'expected_rule': None,
                'actual_rule': None,
                'change_type': None,
                'scope': None,
                'recipe': None,
                'affected': 0,
                'modified': 0,
                **r,
            }
            for i, r in enumerate(rows)
        ]

        block = audit.emit_manifest_block(full_rows)

        # drift + populated name_drift = 2 genuine; informational excluded
        assert 'genuine_signal_count: 2' in block
        assert 'name_drift_count: 1' in block

    def test_severity_classifier_marks_informational_rows(self):
        assert (
            audit._manifest_genuine({'verdict': 'drift', 'name_drift': None})
            is True
        )
        assert (
            audit._manifest_genuine({'verdict': 'ok', 'name_drift': 'x'})
            is True
        )
        assert (
            audit._manifest_genuine({'verdict': 'incomplete', 'name_drift': None})
            is False
        )
        assert (
            audit._manifest_genuine({'verdict': 'ok', 'name_drift': None})
            is False
        )

# =============================================================================
# D2/D4 — dormate_plans batch dormation + path-traversal hardening
# =============================================================================
#
# The single-id ``dormate_plan`` was subsumed by the batch ``dormate_plans``
# (clean break — old single-id-only assertions are replaced, not duplicated).
# The path-traversal guard coverage is preserved by driving the same hostile
# ids through the batch function as one-element lists, and the new
# ``TestDormatePlans`` class covers the batch-specific behaviours: multi-id
# success, ``--dormate-all`` via ``dormate_all_plans``, inert-without-confirmed,
# all-or-nothing refuse-on-clash, and silent dedup.

def _archived_plan_dir(repo_root: Path, plan_id: str) -> Path:
    """Create and return an archived-plan source dir with a marker file."""
    plan_dir = repo_root / '.plan' / 'local' / 'archived-plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    return plan_dir

def _dormated_plan_dir(repo_root: Path, plan_id: str) -> Path:
    """Path to the dormation destination for a single plan id."""
    return repo_root / '.plan' / 'temp' / 'dormated-plans' / plan_id

class TestDormatePlanIdHardening:
    """The path-traversal guard fires identically under the batch function:
    each hostile id is driven through ``dormate_plans`` as a one-element list.
    """

    def test_parent_traversal_plan_id_refused(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['../escape'], confirmed=True)

        # refused on grammar before any move
        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']
        assert result['moved'] == []

    def test_absolute_path_plan_id_refused(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['/etc/passwd'], confirmed=True)

        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']
        assert result['moved'] == []

    def test_embedded_separator_plan_id_refused(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['a/b'], confirmed=True)

        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']
        assert result['moved'] == []

    def test_well_formed_plan_id_passes_grammar_then_source_not_found(self, tmp_path: Path):
        # a canonical kebab/date plan_id with no archived dir on disk
        plan_id = '2026-05-29-some-valid-plan'

        result = audit.dormate_plans(tmp_path, [plan_id], confirmed=True)

        # passes grammar (NOT the grammar refusal); fails source-not-found
        assert result['status'] == 'error'
        assert 'source not found' in result['reason']
        assert 'invalid plan_id' not in result['reason']
        assert result['moved'] == []

    def test_inert_without_confirmed(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['../escape'], confirmed=False)

        # the inert path fires before grammar validation
        assert result['status'] == 'refused'
        assert 'requires --confirmed' in result['reason']
        assert result['moved'] == []

class TestDormatePlans:
    """Batch-specific behaviours of ``dormate_plans`` / ``dormate_all_plans``."""

    def test_multi_id_success_relocates_every_plan(self, tmp_path: Path):
        # two valid archived plans on disk
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')
        _archived_plan_dir(tmp_path, '2026-06-02-plan-b')

        result = audit.dormate_plans(
            tmp_path, ['2026-06-01-plan-a', '2026-06-02-plan-b'], confirmed=True
        )

        # both moved, sources gone, destinations present
        assert result['status'] == 'success'
        assert result['moved'] == ['2026-06-01-plan-a', '2026-06-02-plan-b']
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert not (archived / '2026-06-01-plan-a').exists()
        assert not (archived / '2026-06-02-plan-b').exists()
        assert _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').is_dir()
        assert _dormated_plan_dir(tmp_path, '2026-06-02-plan-b').is_dir()

    def test_dormate_all_relocates_every_archived_plan(self, tmp_path: Path):
        # three archived plans; dormate_all_plans enumerates them all
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')
        _archived_plan_dir(tmp_path, '2026-06-02-plan-b')
        _archived_plan_dir(tmp_path, '2026-06-03-plan-c')

        result = audit.dormate_all_plans(tmp_path, confirmed=True)

        # all three relocated (sorted) via the dormate_plans delegate
        assert result['status'] == 'success'
        assert result['moved'] == [
            '2026-06-01-plan-a',
            '2026-06-02-plan-b',
            '2026-06-03-plan-c',
        ]
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert list(archived.iterdir()) == []
        assert _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').is_dir()
        assert _dormated_plan_dir(tmp_path, '2026-06-02-plan-b').is_dir()
        assert _dormated_plan_dir(tmp_path, '2026-06-03-plan-c').is_dir()

    def test_dormate_all_absent_archive_dir_is_noop_success(self, tmp_path: Path):
        # no archived-plans directory exists at all
        result = audit.dormate_all_plans(tmp_path, confirmed=True)

        # empty no-op success
        assert result['status'] == 'success'
        assert result['moved'] == []

    def test_inert_without_confirmed_leaves_sources_untouched(self, tmp_path: Path):
        # a valid archived plan that must NOT move
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')

        result = audit.dormate_plans(
            tmp_path, ['2026-06-01-plan-a'], confirmed=False
        )

        # refused, nothing moved, source still on disk
        assert result['status'] == 'refused'
        assert result['moved'] == []
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert (archived / '2026-06-01-plan-a').is_dir()
        assert not _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').exists()

    def test_all_or_nothing_refuse_on_clash_moves_nothing(self, tmp_path: Path):
        # two valid sources, but a pre-existing destination for the
        # SECOND plan. The all-or-nothing pre-check must refuse the WHOLE batch
        # before relocating the first (clean) plan.
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')
        _archived_plan_dir(tmp_path, '2026-06-02-plan-b')
        clash = _dormated_plan_dir(tmp_path, '2026-06-02-plan-b')
        clash.mkdir(parents=True, exist_ok=True)

        result = audit.dormate_plans(
            tmp_path, ['2026-06-01-plan-a', '2026-06-02-plan-b'], confirmed=True
        )

        # error, nothing moved, BOTH sources still present
        assert result['status'] == 'error'
        assert result['moved'] == []
        assert 'already exists' in result['reason']
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert (archived / '2026-06-01-plan-a').is_dir()
        assert (archived / '2026-06-02-plan-b').is_dir()
        # The first (clean) plan was NOT relocated despite being clash-free.
        assert not _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').exists()

    def test_silent_dedup_collapses_duplicate_ids(self, tmp_path: Path):
        # one archived plan, supplied id listed three times
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')

        # duplicates must collapse silently (no double-move error)
        result = audit.dormate_plans(
            tmp_path,
            ['2026-06-01-plan-a', '2026-06-01-plan-a', '2026-06-01-plan-a'],
            confirmed=True,
        )

        # moved exactly once, no error
        assert result['status'] == 'success'
        assert result['moved'] == ['2026-06-01-plan-a']
        assert _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').is_dir()

# =============================================================================
# D8 — retrospective-token exclusion in the three metrics-related checks
# =============================================================================

def _phase(
    name: str,
    *,
    total_tokens: int = 0,
    duration_seconds: float = 0.0,
    retrospective_tokens: int = 0,
    agent_duration_seconds: float = 0.0,
    idle_duration_ms: float = 0.0,
) -> Any:
    return audit.PhaseMetrics(
        phase=name,
        total_tokens=total_tokens,
        duration_seconds=duration_seconds,
        retrospective_tokens=retrospective_tokens,
        agent_duration_seconds=agent_duration_seconds,
        idle_duration_ms=idle_duration_ms,
    )

class TestRetrospectiveExclusionDisproportionate:
    def test_retrospective_does_not_trip_share_threshold(self, monkeypatch):
        # finalize raw total dominates (2000 of 2800 = 71%, which would
        # trip the 45% threshold on raw tokens), but the bulk is retrospective.
        # The two implementation phases carry balanced effective shares so that no
        # phase trips the threshold once retrospective spend is excluded.
        phases = [
            _phase('5-execute', total_tokens=400),
            _phase('3-outline', total_tokens=400),
            _phase('6-finalize', total_tokens=2000, retrospective_tokens=1800),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # effective total 1000 (400 + 400 + 200); shares 40%/40%/20%,
        # none >= 45%, so nothing is flagged. Without exclusion, finalize's raw
        # 2000/2800 = 71% would have tripped the threshold.
        assert result['disproportionate_token'] == ''

    def test_negative_control_genuine_disproportionate_still_flagged(self, monkeypatch):
        # a genuine >=45% phase even after retrospective exclusion
        phases = [
            _phase('5-execute', total_tokens=300),
            _phase('3-outline', total_tokens=700),
            _phase('6-finalize', total_tokens=200, retrospective_tokens=100),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # effective total 1100, outline 700/1100 = 63% → flagged
        assert '3-outline' in result['disproportionate_token']

class TestRetrospectiveExclusionOptimization:
    def test_retrospective_only_outlier_not_flagged(self, monkeypatch):
        # three balanced phases plus a finalize whose only spend is
        # retrospective (effective 0 → excluded from the ratio set).
        phases = [
            _phase('2-refine', total_tokens=1000, duration_seconds=100.0),
            _phase('4-plan', total_tokens=1100, duration_seconds=110.0),
            _phase('5-execute', total_tokens=900, duration_seconds=90.0),
            _phase(
                '6-finalize',
                total_tokens=9000,
                retrospective_tokens=9000,
                duration_seconds=10.0,
            ),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # the finalize phase (raw 900 tok/s outlier) is excluded
        assert '6-finalize' not in result['optimization_signal']
        assert result['optimization_signal'] == ''

class TestRetrospectiveExclusionTrend:
    def test_total_and_divisor_exclude_retrospective(self, monkeypatch):
        # one plan whose finalize spend is entirely retrospective
        phases = [
            _phase('5-execute', total_tokens=500),
            _phase('6-finalize', total_tokens=400, retrospective_tokens=400),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.cross_token_trend([inputs])

        # effective total 500, only one implementation phase counted
        row = result['rows'][0]
        assert row['total_tokens'] == 500
        assert row['phases'] == 1
        assert row['tokens_per_phase'] == 500

class TestRetrospectiveExclusionDegrade:
    def test_absent_attribution_excludes_nothing(self, monkeypatch):
        # archived-plan shape: NO retrospective_tokens field anywhere
        phases = [
            _phase('5-execute', total_tokens=1000, duration_seconds=100.0),
            _phase('6-finalize', total_tokens=2000, duration_seconds=50.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        metrics = audit.check_metrics(inputs)
        trend = audit.cross_token_trend([inputs])

        # behaves exactly as pre-D8 (2000/3000 = 67% finalize flagged)
        assert '6-finalize' in metrics['disproportionate_token']
        assert trend['rows'][0]['total_tokens'] == 3000
        assert trend['rows'][0]['phases'] == 2

    def test_only_retrospective_excluded_other_op_spend_counted(self, monkeypatch):
        # a finalize phase carrying q-gate-validation / other-op spend
        # (no retrospective_tokens) stays fully counted.
        phases = [
            _phase('5-execute', total_tokens=400),
            _phase('6-finalize', total_tokens=600),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # effective total 1000, finalize 600/1000 = 60% → flagged
        assert '6-finalize' in result['disproportionate_token']

# =============================================================================
# D1 — THRESHOLDS centralization: single-source table + back-compat aliases
# =============================================================================

class TestThresholdsCentralization:
    """The ``THRESHOLDS`` table is the single source of truth and every
    back-compatible module-level alias resolves to the same value it owns."""

    def test_systemic_threshold_alias_matches_table(self):
        # the request-mandated 3+ occurrences
        assert audit.SYSTEMIC_THRESHOLD == audit.THRESHOLDS['systemic_occurrences']
        assert audit.SYSTEMIC_THRESHOLD == 3

    def test_pr_slow_review_alias_matches_table(self):
        assert audit.PR_SLOW_REVIEW_HOURS == audit.THRESHOLDS['pr_slow_review_hours']

    def test_phase_token_share_alias_matches_table(self):
        assert (
            audit.PHASE_TOKEN_SHARE_THRESHOLD
            == audit.THRESHOLDS['phase_token_share']
        )

    def test_scope_file_bands_alias_matches_table(self):
        # alias is the same mapping object the table owns
        assert audit.SCOPE_FILE_BANDS == audit.THRESHOLDS['scope_file_bands']
        assert audit.SCOPE_FILE_BANDS['surgical'] == (1, 3)
        assert audit.SCOPE_FILE_BANDS['multi_module'] == (5, None)

    def test_tasks_per_deliverable_aliases_match_table(self):
        assert (
            audit.TASKS_PER_DELIVERABLE_LOW
            == audit.THRESHOLDS['tasks_per_deliverable_low']
        )
        assert (
            audit.TASKS_PER_DELIVERABLE_HIGH
            == audit.THRESHOLDS['tasks_per_deliverable_high']
        )

    def test_thresholds_table_carries_every_documented_constant(self):
        # every magic number the checks consume must live in the table
        expected_keys = {
            'systemic_occurrences',
            'pr_slow_review_hours',
            'phase_token_share',
            'token_rate_outlier_multiple',
            'token_trend_regression_fraction',
            'build_minimal_seconds',
            'build_heavy_seconds',
            'build_clustering_minutes',
            'long_session_messages',
            'slow_call_seconds',
            'high_frequency_calls',
            'scope_file_bands',
            'tasks_per_deliverable_low',
            'tasks_per_deliverable_high',
        }

        # table is a superset of the documented constants
        assert expected_keys <= set(audit.THRESHOLDS)

class TestCorpusRelativeHelpers:
    """``median`` / ``percentile`` are the corpus-relative threshold helpers a
    check SHOULD prefer over a hard-coded constant when a live distribution
    exists."""

    def test_median_empty_returns_zero(self):
        assert audit.median([]) == 0.0

    def test_median_odd_length_returns_middle(self):
        # unsorted input is sorted internally
        assert audit.median([3.0, 1.0, 2.0]) == 2.0

    def test_median_even_length_averages_two_middle(self):
        assert audit.median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_percentile_empty_returns_zero(self):
        assert audit.percentile([], 50.0) == 0.0

    def test_percentile_nearest_rank_is_deterministic(self):
        # nearest-rank: rank = round(pct/100 * n), floored at 1
        values = [10.0, 20.0, 30.0, 40.0]

        assert audit.percentile(values, 0.0) == 10.0
        assert audit.percentile(values, 100.0) == 40.0
        assert audit.percentile(values, 50.0) == 20.0

    def test_percentile_clamps_out_of_range_pct(self):
        values = [5.0, 15.0, 25.0]

        # pct outside [0,100] is clamped, never raises
        assert audit.percentile(values, -10.0) == 5.0
        assert audit.percentile(values, 250.0) == 25.0

# =============================================================================
# D1 — uniform severity column + genuine_signal_count across emit_* blocks
# =============================================================================

class TestSeveritySummary:
    """``_severity_summary`` stamps a uniform ``severity`` cell on every row and
    returns the genuine-signal count — the generalization of the manifest-only
    severity pattern to every ``emit_*_block``."""

    def test_stamps_severity_and_counts_genuine(self):
        # predicate fires on rows whose ``flag`` is truthy
        rows = [{'flag': 'x'}, {'flag': ''}, {'flag': 'y'}]

        stamped, count = audit._severity_summary(rows, lambda r: bool(r['flag']))

        assert count == 2
        assert stamped[0]['severity'] == 'genuine'
        assert stamped[1]['severity'] == 'informational'
        assert stamped[2]['severity'] == 'genuine'

    def test_all_informational_when_predicate_never_fires(self):
        rows = [{'v': 1}, {'v': 2}]

        stamped, count = audit._severity_summary(rows, lambda _r: False)

        assert count == 0
        assert all(r['severity'] == 'informational' for r in stamped)

    def test_empty_rows_yields_zero_count(self):
        stamped, count = audit._severity_summary([], lambda _r: True)

        assert stamped == []
        assert count == 0

class TestEmitTableBlockSeverity:
    """Every ``emit_table_block`` carries the uniform ``severity`` final column
    and the ``genuine_signal_count`` summary line."""

    def test_severity_column_appended_and_count_line_present(self):
        # two rows, one genuine (mismatch populated)
        rows = [
            {'plan_id': 'p1', 'mismatch': 'declared=surgical actual=99'},
            {'plan_id': 'p2', 'mismatch': ''},
        ]

        block = audit.emit_table_block(
            'scope-estimate-accuracy',
            ['plan_id', 'mismatch'],
            rows,
            lambda r: bool(r['mismatch']),
        )

        # header carries the appended severity column + count line
        assert 'rows[2]{plan_id,mismatch,severity}:' in block
        assert 'genuine_signal_count: 1' in block
        assert 'check: scope-estimate-accuracy' in block
        assert 'plans_scanned: 2' in block

    def test_genuine_and_informational_rows_emit_correct_severity_cell(self):
        rows = [
            {'plan_id': 'g', 'outlier': 'over_decomposed (ratio=5.00)'},
            {'plan_id': 'i', 'outlier': ''},
        ]

        block = audit.emit_table_block(
            'task-count-efficiency',
            ['plan_id', 'outlier'],
            rows,
            lambda r: bool(r['outlier']),
        )
        lines = [ln.strip() for ln in block.splitlines()]

        # the row cells end in genuine / informational respectively
        genuine_row = next(ln for ln in lines if ln.startswith('g,'))
        info_row = next(ln for ln in lines if ln.startswith('i,'))
        assert genuine_row.endswith(',genuine')
        assert info_row.endswith(',informational')

class TestEmitRecurringBlockSeverity:
    """Every systemic recurring pattern cleared the N-occurrence threshold, so
    every row is by definition a genuine signal."""

    def test_all_systemic_rows_are_genuine(self):
        result = {
            'threshold': 3,
            'systemic_count': 2,
            'rows': [
                {
                    'signature': 'sig-a',
                    'occurrence_count': 4,
                    'plan_ids': ['p1', 'p2'],
                    'candidate': 'novel',
                },
                {
                    'signature': 'sig-b',
                    'occurrence_count': 3,
                    'plan_ids': ['p3'],
                    'candidate': 'covered_by:lesson-x',
                },
            ],
        }

        block = audit.emit_recurring_block(result)

        # both rows genuine; the count + threshold lines present
        assert 'genuine_signal_count: 2' in block
        assert 'threshold: 3' in block
        assert (
            'rows[2]{signature,occurrence_count,plan_ids,candidate,severity}:'
            in block
        )

    def test_empty_systemic_rows_yields_zero_genuine(self):
        result = {'threshold': 3, 'systemic_count': 0, 'rows': []}

        block = audit.emit_recurring_block(result)

        assert 'genuine_signal_count: 0' in block
        assert 'systemic_count: 0' in block

class TestEmitTrendBlockSeverity:
    """A trend row is genuine only when a sustained regression fired for the
    whole series; without regression the per-plan rows are informational."""

    def test_regression_marks_all_rows_genuine(self):
        # a populated regression string flags the whole series
        result = {
            'plans_in_series': 2,
            'regression': 'tokens/phase rose 100 -> 200 (+100%)',
            'rows': [
                {'plan_id': 'p1', 'phases': 1, 'total_tokens': 100, 'tokens_per_phase': 100},
                {'plan_id': 'p2', 'phases': 1, 'total_tokens': 200, 'tokens_per_phase': 200},
            ],
        }

        block = audit.emit_trend_block(result)

        # both supporting rows genuine when regression fired
        assert 'genuine_signal_count: 2' in block

    def test_no_regression_marks_all_rows_informational(self):
        # empty regression string
        result = {
            'plans_in_series': 2,
            'regression': '',
            'rows': [
                {'plan_id': 'p1', 'phases': 1, 'total_tokens': 100, 'tokens_per_phase': 100},
                {'plan_id': 'p2', 'phases': 1, 'total_tokens': 110, 'tokens_per_phase': 110},
            ],
        }

        block = audit.emit_trend_block(result)

        assert 'genuine_signal_count: 0' in block
        assert (
            'rows[2]{plan_id,phases,total_tokens,tokens_per_phase,severity}:'
            in block
        )

# =============================================================================
# D1 — persisted report sink: path-guarding + load / diff round-trip
# =============================================================================

class TestPersistedReportSink:
    """``write_persisted_report`` writes only under ``audit-reports/`` and the
    round-trip ``load_latest_prior_report`` reads back the summary metrics it
    persisted."""

    def test_write_creates_report_under_audit_reports(self, tmp_path: Path):
        blocks = ['check: metrics\nstatus: success\n']
        summary = {'plans_scanned': 2, 'metrics_genuine': 1}

        dest = audit.write_persisted_report(tmp_path, blocks, summary)

        # landed under the guarded directory with the timestamp grammar
        assert dest is not None
        reports_dir = (tmp_path / audit.AUDIT_REPORTS_REL).resolve()
        assert dest.parent == reports_dir
        assert audit._REPORT_STEM_RE.match(dest.stem)
        assert dest.is_file()

    def test_written_report_carries_summary_metrics_header(self, tmp_path: Path):
        summary = {'plans_scanned': 3, 'foo': 'bar'}

        dest = audit.write_persisted_report(tmp_path, ['check: x\n'], summary)
        assert dest is not None
        text = dest.read_text(encoding='utf-8')

        # header block + keys (sorted) + the run's block text
        assert 'report: audit' in text
        assert 'summary_metrics:' in text
        assert 'plans_scanned: 3' in text
        assert 'foo: bar' in text
        assert 'check: x' in text

    def test_load_latest_prior_round_trips_summary_metrics(self, tmp_path: Path):
        # write a report, then read its summary back
        summary = {'plans_scanned': 5, 'metrics_genuine': 2, 'regression': True}
        audit.write_persisted_report(tmp_path, ['check: m\n'], summary)

        loaded = audit.load_latest_prior_report(tmp_path)

        # int + bool coercion round-trips through _coerce_metric
        assert loaded is not None
        assert loaded['plans_scanned'] == 5
        assert loaded['metrics_genuine'] == 2
        assert loaded['regression'] is True

    def test_load_latest_prior_returns_none_when_no_reports(self, tmp_path: Path):
        # no audit-reports directory at all
        loaded = audit.load_latest_prior_report(tmp_path)

        assert loaded is None

    def test_load_latest_prior_ignores_non_timestamp_files(self, tmp_path: Path):
        # a stray non-grammar file must not be picked as "latest"
        reports_dir = (tmp_path / audit.AUDIT_REPORTS_REL).resolve()
        reports_dir.mkdir(parents=True)
        (reports_dir / 'not-a-report.toon').write_text('garbage\n', encoding='utf-8')

        loaded = audit.load_latest_prior_report(tmp_path)

        # no valid timestamp-stem report exists
        assert loaded is None

    def test_latest_is_lexicographically_greatest_stem(self, tmp_path: Path):
        # two valid reports; the greater stem is "latest prior"
        reports_dir = (tmp_path / audit.AUDIT_REPORTS_REL).resolve()
        reports_dir.mkdir(parents=True)
        older = reports_dir / '20260101T000000Z.toon'
        newer = reports_dir / '20260601T120000Z.toon'
        older.write_text(
            'report: audit\nsummary_metrics:\n  plans_scanned: 1\n', encoding='utf-8'
        )
        newer.write_text(
            'report: audit\nsummary_metrics:\n  plans_scanned: 9\n', encoding='utf-8'
        )

        loaded = audit.load_latest_prior_report(tmp_path)

        # the newer (greater stem) summary is returned
        assert loaded is not None
        assert loaded['plans_scanned'] == 9

class TestDiffSummaryMetrics:
    """``diff_summary_metrics`` reports every changed metric, sorted, with empty
    strings filling a side where a key is absent."""

    def test_changed_keys_reported_sorted(self):
        prior = {'a': 1, 'b': 2, 'c': 3}
        current = {'a': 1, 'b': 99, 'c': 3}

        changes = audit.diff_summary_metrics(prior, current)

        # only b changed
        assert changes == [('b', 2, 99)]

    def test_added_key_reports_empty_prior_side(self):
        # key only in current
        changes = audit.diff_summary_metrics({}, {'new_metric': 7})

        assert changes == [('new_metric', '', 7)]

    def test_removed_key_reports_empty_current_side(self):
        # key only in prior
        changes = audit.diff_summary_metrics({'gone': 4}, {})

        assert changes == [('gone', 4, '')]

    def test_no_changes_yields_empty_list(self):
        assert audit.diff_summary_metrics({'a': 1}, {'a': 1}) == []

    def test_full_round_trip_write_load_diff(self, tmp_path: Path):
        # write a prior report, then diff a current summary against it
        prior_summary = {'plans_scanned': 4, 'metrics_genuine': 1}
        audit.write_persisted_report(tmp_path, ['check: p\n'], prior_summary)
        prior = audit.load_latest_prior_report(tmp_path)
        assert prior is not None
        current_summary = {'plans_scanned': 4, 'metrics_genuine': 3}

        changes = audit.diff_summary_metrics(prior, current_summary)

        # only metrics_genuine moved 1 -> 3
        assert changes == [('metrics_genuine', 1, 3)]

class TestCoerceMetric:
    """``_coerce_metric`` reconstructs bool / int / str types when reading a
    persisted report's summary header back from text."""

    def test_bool_strings_coerce_to_bool(self):
        assert audit._coerce_metric('True') is True
        assert audit._coerce_metric('False') is False

    def test_int_string_coerces_to_int(self):
        assert audit._coerce_metric('42') == 42
        assert isinstance(audit._coerce_metric('42'), int)

    def test_non_numeric_string_stays_string(self):
        assert audit._coerce_metric('plan-abc') == 'plan-abc'

# =============================================================================
# D1 — dedup pre-tagger: novel vs covered_by:{lesson_id}
# =============================================================================

class TestDedupPretag:
    """``_dedup_pretag`` is the Gate-1 PRE-filter: ``novel`` when no filed lesson
    covers the signature, ``covered_by:{lesson_id}`` when one does — using the
    same substring containment match as the body's adjudication."""

    def test_empty_signature_is_novel(self):
        assert audit._dedup_pretag('', ['lesson-x\tsome title']) == 'novel'
        assert audit._dedup_pretag('   ', ['lesson-x\tsome title']) == 'novel'

    def test_uncovered_signature_is_novel(self):
        # corpus title shares no containment with the signature
        corpus = ['lesson-2026-06-01-12-001\tflaky network retry']

        assert audit._dedup_pretag('scope estimate drift', corpus) == 'novel'

    def test_covered_signature_names_the_lesson_id(self):
        # corpus entry is `lesson_id\ttitle`; substring containment fires
        corpus = ['lesson-2026-06-01-12-001\tdisproportionate token usage in finalize']

        tag = audit._dedup_pretag('disproportionate token usage', corpus)

        # names the covering lesson id parsed from the corpus filename stem
        assert tag == 'covered_by:lesson-2026-06-01-12-001'

    def test_existing_substring_of_signature_also_covers(self):
        # symmetric containment: corpus title is a substring of the sig
        corpus = ['lesson-99\ttoken drift']

        tag = audit._dedup_pretag('recurring token drift signature', corpus)

        assert tag == 'covered_by:lesson-99'

    def test_tab_prefixed_entry_with_empty_lesson_id_returns_bare_covered(self):
        # a leading-tab entry yields an empty lesson_id, so there is no
        # id to qualify the tag with; the title still drives containment.
        corpus = ['\tdisproportionate token usage']

        tag = audit._dedup_pretag('disproportionate token usage in finalize', corpus)

        # covered, but no id available to qualify it
        assert tag == 'covered'

    def test_bare_title_entry_uses_title_as_lesson_id(self):
        # a corpus entry with no tab → the whole string is the
        # lesson_id (and also the containment title via the `title or lesson_id`
        # fallback), so the tag is qualified with that string.
        corpus = ['disproportionate token usage']

        tag = audit._dedup_pretag('disproportionate token usage in finalize', corpus)

        assert tag == 'covered_by:disproportionate token usage'

    def test_case_insensitive_containment(self):
        # match must be case-insensitive
        corpus = ['lesson-7\tTOKEN Drift Pattern']

        tag = audit._dedup_pretag('token drift pattern', corpus)

        assert tag == 'covered_by:lesson-7'

# =============================================================================
# D2 — global-log-analysis cross-plan check
# =============================================================================

def _write_log(repo_root: Path, name: str, lines: list[str]) -> None:
    """Write a global log file under ``{repo_root}/.plan/local/logs/{name}``.

    ``name`` MUST match one of the three globbed patterns
    (``script-execution-*.log`` / ``work-*.log`` / ``decision-*.log``) for
    ``cross_global_log_analysis`` to pick it up. Each entry in ``lines`` is one
    raw log line written verbatim.
    """
    logs_dir = repo_root / '.plan' / 'local' / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text('\n'.join(lines) + '\n', encoding='utf-8')

def _write_metrics_window(
    repo_root: Path,
    plan_id: str,
    start: str,
    end: str,
    *,
    archived: bool = True,
) -> None:
    """Seed an archived (or active) plan's ``work/metrics.toon`` window.

    Writes a single-phase ``metrics.toon`` carrying ``start_time`` / ``end_time``
    lines so ``plan_execution_windows`` derives a ``(start, end)`` window for the
    plan. ``start`` / ``end`` are ``YYYY-MM-DDTHH:MM:SSZ`` strings (trailing ``Z``
    is stripped by the parser).
    """
    sub = 'archived-plans' if archived else 'plans'
    work = repo_root / '.plan' / 'local' / sub / plan_id / 'work'
    work.mkdir(parents=True, exist_ok=True)
    body = (
        'report: metrics\n'
        'phases:\n'
        '  - phase: 5-execute\n'
        f'    start_time: {start}\n'
        f'    end_time: {end}\n'
    )
    (work / 'metrics.toon').write_text(body, encoding='utf-8')

def _line(ts: str, level: str, rest: str, *, hash_: str = '3befe7') -> str:
    """Build a single log line in the shared ``_LOG_LINE_RE`` grammar."""
    return f'[{ts}] [{level}] [{hash_}] {rest}'

class TestGlobalLogAnalysisLineGrammar:
    """The shared line grammar drives every downstream signal — a line that does
    not match ``_LOG_LINE_RE`` is silently skipped and never counted."""

    def test_well_formed_line_is_counted_by_level(self, tmp_path: Path):
        # two grammar-valid lines at distinct levels
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                _line('2026-06-01T10:00:01Z', 'WARNING', '[STATUS] (x) heads up'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # both lines parsed; level buckets reflect each LEVEL cell
        assert result['total_log_lines'] == 2
        assert result['level_counts'] == {'INFO': 1, 'WARNING': 1}

    def test_malformed_lines_are_skipped(self, tmp_path: Path):
        # only the first line matches the bracketed grammar
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                'this line has no bracketed timestamp/level/hash prefix',
                '[2026-06-01T10:00:02Z] INFO missing-hash-brackets',
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # only the single well-formed line is counted
        assert result['total_log_lines'] == 1
        assert result['level_counts'] == {'INFO': 1}

    def test_missing_logs_dir_yields_empty_all_zero_result(self, tmp_path: Path):
        # no .plan/local/logs directory at all
        # best-effort: empty result rather than raising
        result = audit.cross_global_log_analysis(tmp_path)

        assert result['logs_present'] is False
        assert result['total_log_lines'] == 0
        assert result['error_count'] == 0
        assert result['slow_call_count'] == 0
        assert result['high_frequency_count'] == 0
        assert result['fixture_leak_count'] == 0

class TestGlobalLogAnalysisCallAggregation:
    """Script-execution lines aggregate per ``notation subcommand`` key, summing
    call counts and durations across the corpus."""

    def test_calls_aggregate_per_notation_and_subcommand(self, tmp_path: Path):
        # three calls: two share a key, one is a different subcommand
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:manage-tasks:manage-tasks read --plan-id p (0.10s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:manage-tasks:manage-tasks read --plan-id q (0.20s)'),
                _line('2026-06-01T10:00:02Z', 'INFO', 'pm:manage-tasks:manage-tasks update --status done (0.30s)'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # total wall-clock summed; per-key aggregation distinct by subcommand
        assert result['total_script_seconds'] == 0.6
        # no high-frequency / slow rows at these low counts/durations
        assert result['high_frequency_count'] == 0
        assert result['slow_call_count'] == 0

    def test_high_frequency_caller_flagged_at_ceiling(self, tmp_path: Path):
        # exactly high_frequency_calls (50) identical-key calls
        ceiling = audit.THRESHOLDS['high_frequency_calls']
        lines = [
            _line(
                '2026-06-01T10:00:00Z',
                'INFO',
                'pm:manage-logging:manage-logging work --plan-id p (0.01s)',
            )
            for _ in range(ceiling)
        ]
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        result = audit.cross_global_log_analysis(tmp_path)

        # the >=ceiling key surfaces as a single high-frequency row
        assert result['high_frequency_count'] == 1
        row = result['high_frequency'][0]
        assert row['count'] == ceiling
        assert row['key'] == 'pm:manage-logging:manage-logging work'

    def test_below_high_frequency_ceiling_not_flagged(self, tmp_path: Path):
        # one call below the (50) ceiling
        ceiling = audit.THRESHOLDS['high_frequency_calls']
        lines = [
            _line('2026-06-01T10:00:00Z', 'INFO', 'pm:manage-files:manage-files exists --file f (0.01s)')
            for _ in range(ceiling - 1)
        ]
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        result = audit.cross_global_log_analysis(tmp_path)

        # under threshold, no high-frequency row
        assert result['high_frequency_count'] == 0

class TestGlobalLogAnalysisDurationBands:
    """Durations split into three bands: normal (< slow), slow
    (slow <= d < impossible), and impossible (>= impossible ceiling)."""

    def test_slow_call_flagged_at_slow_ceiling(self, tmp_path: Path):
        # a call exactly at slow_call_seconds (30.0)
        slow = audit.THRESHOLDS['slow_call_seconds']
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line(
                    '2026-06-01T10:00:00Z',
                    'INFO',
                    f'pm:build-pyproject:pyproject_build run --command-args verify ({slow:.1f}s)',
                ),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # lands in the slow band, not impossible
        assert result['slow_call_count'] == 1
        assert result['impossible_count'] == 0
        assert result['slow_calls'][0]['seconds'] == slow

    def test_fast_call_not_flagged_slow(self, tmp_path: Path):
        # just under the slow ceiling
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:s:s run (29.9s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['slow_call_count'] == 0
        assert result['impossible_count'] == 0

    def test_impossible_duration_flagged_separately_from_slow(self, tmp_path: Path):
        # a hang-shaped duration at the impossible ceiling (600s)
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:s:s run (650.0s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # counted as impossible, NOT double-counted as slow
        assert result['impossible_count'] == 1
        assert result['slow_call_count'] == 0
        assert result['impossible_calls'][0]['seconds'] == 650.0

    def test_slow_calls_sorted_descending_by_seconds(self, tmp_path: Path):
        # two slow calls of differing magnitude
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (35.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:b:b run (90.0s)'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # slowest first
        seconds = [r['seconds'] for r in result['slow_calls']]
        assert seconds == [90.0, 35.0]

class TestGlobalLogAnalysisErrorFlagging:
    """Non-INFO levels and INFO lines carrying a failure marker both surface as
    error lines."""

    def test_non_info_level_flagged(self, tmp_path: Path):
        # an ERROR-level line with no failure marker in the body
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'ERROR', '[STATUS] (x) something off')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['error_count'] == 1
        assert result['error_lines'][0]['level'] == 'ERROR'

    def test_info_line_with_failure_marker_flagged(self, tmp_path: Path):
        # INFO level but the body carries a fail marker (status: error)
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:x:x run -> status: error exit_code: 1')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # an INFO line still counts when a fail marker fires
        assert result['error_count'] == 1
        assert result['error_lines'][0]['level'] == 'INFO'

    def test_clean_info_line_not_flagged(self, tmp_path: Path):
        # INFO with no failure markers
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) all good')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['error_count'] == 0

class TestGlobalLogAnalysisPlanAttribution:
    """A flagged line is attributed to every archived/active plan whose execution
    window (from ``metrics.toon`` start/end) contains its timestamp; a line
    outside every window is ad-hoc."""

    def test_in_window_line_attributed_to_plan(self, tmp_path: Path):
        # a plan window enclosing the error line's timestamp
        _write_metrics_window(
            tmp_path, 'plan-alpha', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:30:00Z', 'ERROR', '[STATUS] (x) inside window')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # the error row names the enclosing plan
        assert result['plan_windows_derived'] == 1
        assert result['error_lines'][0]['plans'] == ['plan-alpha']

    def test_outside_window_line_is_ad_hoc(self, tmp_path: Path):
        # the error timestamp falls OUTSIDE the plan window
        _write_metrics_window(
            tmp_path, 'plan-alpha', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T23:00:00Z', 'ERROR', '[STATUS] (x) after window')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # no plan window contains it; attribution is empty (emitted ad-hoc)
        assert result['error_lines'][0]['plans'] == []

    def test_active_plan_window_also_correlated(self, tmp_path: Path):
        # a window seeded under active plans/ (not archived-plans/)
        _write_metrics_window(
            tmp_path,
            'plan-active',
            '2026-06-01T09:00:00Z',
            '2026-06-01T09:30:00Z',
            archived=False,
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T09:15:00Z', 'WARNING', '[STATUS] (x) mid active run')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # active-plan windows are correlated alongside archived ones
        assert result['plan_windows_derived'] == 1
        assert result['error_lines'][0]['plans'] == ['plan-active']

    def test_overlapping_windows_attribute_all_enclosing_plans(self, tmp_path: Path):
        # two plans whose windows both contain the timestamp
        _write_metrics_window(
            tmp_path, 'plan-aaa', '2026-06-01T10:00:00Z', '2026-06-01T12:00:00Z'
        )
        _write_metrics_window(
            tmp_path, 'plan-bbb', '2026-06-01T11:00:00Z', '2026-06-01T13:00:00Z'
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T11:30:00Z', 'ERROR', '[STATUS] (x) overlap zone')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # both enclosing plans named, sorted
        assert result['error_lines'][0]['plans'] == ['plan-aaa', 'plan-bbb']

class TestGlobalLogAnalysisFixtureLeak:
    """Synthetic test-fixture bundle/plan ids must NEVER appear in the shared
    global log; their presence is a leak (a test wrote to the real logs)."""

    def test_fake_bundle_signature_flagged(self, tmp_path: Path):
        # a synthetic fixture bundle id leaked into the corpus
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'fake-test-bundle:skill:script run (0.01s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # leak detector fires and captures the signature
        assert result['fixture_leak_count'] == 1
        assert 'fake-test-bundle' in result['fixture_leaks'][0]['signature']

    def test_idem_and_raising_bundle_signatures_flagged(self, tmp_path: Path):
        # the other two synthetic-bundle signatures from the regex
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] idem-bundle wrote a file'),
                _line('2026-06-01T10:00:01Z', 'INFO', '[STATUS] raising-bundle threw'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # both synthetic-bundle leaks captured
        assert result['fixture_leak_count'] == 2

    def test_orphan_md_signature_flagged(self, tmp_path: Path):
        # an orphan-md-* synthetic plan id
        _write_log(
            tmp_path,
            'decision-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '(x) plan orphan-md-xyz123 resolved')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['fixture_leak_count'] == 1
        assert 'orphan-md-xyz123' in result['fixture_leaks'][0]['signature']

    def test_clean_corpus_has_no_fixture_leaks(self, tmp_path: Path):
        # only real-looking notations, no synthetic signatures
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:manage-tasks:manage-tasks read (0.01s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['fixture_leak_count'] == 0

class TestEmitGlobalLogBlock:
    """``emit_global_log_block`` renders the result dict to a TOON block: every
    flagged line is a genuine signal, ad-hoc attribution fills empty windows, and
    the summary lines carry the level buckets and per-band counts."""

    def test_block_carries_summary_lines_and_genuine_count(self, tmp_path: Path):
        # one genuine ERROR failure (carries failure markers) + one slow call
        _write_metrics_window(
            tmp_path, 'plan-x', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                # A real failure: carries markers (status: error / exit_code=1) and is
                # NOT a bare script-call probe, so the corrected flagger flags it.
                _line('2026-06-01T10:10:00Z', 'ERROR', 'pm:x:x run -> status: error exit_code=1'),
                _line('2026-06-01T10:20:00Z', 'INFO', 'pm:y:y run (40.0s)'),
            ],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # header, counts, and a genuine-only signal total
        assert 'check: global-log-analysis' in block
        assert 'status: success' in block
        # one error line + one slow call = 2 genuine signals
        assert 'genuine_signal_count: 2' in block
        assert 'error_count: 1' in block
        assert 'slow_call_count: 1' in block
        assert 'rows[2]{kind,detail,attributed_plans,severity}:' in block

    def test_debug_and_benign_probes_excluded_from_error_count(self, tmp_path: Path):
        # The corrected flagger flags only elevated levels (>=WARNING) + real failure
        # markers, and excludes (a) DEBUG diagnostics (below INFO) and (b) bare
        # script-call probes at an elevated level with no failure marker (a benign
        # non-zero-exit query such as `exists`/`read` answering "not found").
        _write_metrics_window(
            tmp_path, 'plan-x', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                # DEBUG diagnostic — NOT an error.
                _line('2026-06-01T10:05:00Z', 'DEBUG', 'pm:a:a resolve cache hit'),
                # benign ERROR-level probe: a completed script call (has a duration)
                # with no failure marker — a "not found" boolean query, NOT a failure.
                _line('2026-06-01T10:10:00Z', 'ERROR', 'pm:f:f exists (0.21s)'),
                # a genuine marker-bearing failure IS still flagged at any level.
                _line('2026-06-01T10:20:00Z', 'INFO', 'pm:g:g check Traceback (most recent call last)'),
            ],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # Only the Traceback line is a genuine error; DEBUG + benign probe excluded.
        assert 'error_count: 1' in block
        assert 'genuine_signal_count: 1' in block

    def test_non_query_command_at_error_is_not_a_benign_probe(self, tmp_path: Path):
        # The benign-probe exclusion is restricted to read-only QUERY subcommands.
        # A non-query command (e.g. `run`) at ERROR with no failure marker must STILL
        # be flagged — it is a genuine failure, not a "not found" probe.
        _write_metrics_window(
            tmp_path, 'plan-x', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                # ERROR-level `run` call, has a duration, NO failure marker — not a query.
                _line('2026-06-01T10:10:00Z', 'ERROR', 'pm:b:b run (0.50s)'),
                # ERROR-level `exists` query with a duration — benign, excluded.
                _line('2026-06-01T10:20:00Z', 'ERROR', 'pm:f:f exists (0.21s)'),
            ],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # the `run` failure is flagged; the `exists` probe is not
        assert 'error_count: 1' in block

    def test_empty_result_renders_zero_signal_block(self, tmp_path: Path):
        # no logs at all
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # well-formed block with zero rows and zero genuine signals
        assert 'genuine_signal_count: 0' in block
        assert 'logs_present: false' in block
        assert 'rows[0]{kind,detail,attributed_plans,severity}:' in block

    def test_ad_hoc_attribution_when_no_enclosing_window(self, tmp_path: Path):
        # an error line with no plan window covering it
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'ERROR', 'orphaned error with no window')],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # the empty attribution renders as the literal ad-hoc sentinel
        assert 'ad-hoc' in block

    def test_global_log_analysis_in_check_registry(self):
        # the check is registered and cross-plan scoped
        assert 'global-log-analysis' in audit.CHECK_NAMES
        assert 'global-log-analysis' in audit.CROSS_PLAN_CHECKS

# =============================================================================
# D3 — dormate_global_logs confirmed-gated past-date move
# =============================================================================

def _logs_dir(repo_root: Path) -> Path:
    """Path to ``{repo_root}/.plan/local/logs`` (the dormation source dir)."""
    return repo_root / '.plan' / 'local' / 'logs'

def _dormated_global_logs_dir(repo_root: Path) -> Path:
    """Path to the dormation destination ``dormated-plans/global-logs``."""
    return repo_root / '.plan' / 'temp' / 'dormated-plans' / 'global-logs'

def _seed_log_file(repo_root: Path, name: str, body: str = 'line\n') -> Path:
    """Create a single global-log file under the dormation source dir."""
    logs_dir = _logs_dir(repo_root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / name
    path.write_text(body, encoding='utf-8')
    return path

def _past_date_stamp(days_back: int = 1) -> str:
    """A ``YYYY-MM-DD`` stamp strictly before today (default: yesterday)."""
    return (datetime.now().date() - timedelta(days=days_back)).strftime('%Y-%m-%d')

def _today_stamp() -> str:
    """Today's ``YYYY-MM-DD`` stamp — the still-active log that must never move."""
    return datetime.now().date().strftime('%Y-%m-%d')

class TestDormateGlobalLogs:
    """``dormate_global_logs`` mirrors ``dormate_plan``: inert without
    ``--confirmed``, moves only COMPLETE past-date ``{prefix}-YYYY-MM-DD.log``
    files, never touches today's still-active log, and refuses (never
    overwrites) on a destination-name clash."""

    def test_inert_without_confirmed(self, tmp_path: Path):
        # a past-date log that WOULD be eligible if confirmed
        _seed_log_file(tmp_path, f'work-{_past_date_stamp()}.log')

        # inert path fires before any scan/move
        result = audit.dormate_global_logs(tmp_path, confirmed=False)

        # refused, nothing moved, source file untouched
        assert result['status'] == 'refused'
        assert result['moved'] == []
        assert 'requires --confirmed' in result['reason']
        assert (_logs_dir(tmp_path) / f'work-{_past_date_stamp()}.log').exists()

    def test_missing_logs_dir_is_noop_success(self, tmp_path: Path):
        # no .plan/local/logs dir at all

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # clean no-op, not an error
        assert result['status'] == 'success'
        assert result['moved'] == []

    def test_past_date_logs_moved(self, tmp_path: Path):
        # three distinct-prefix past-date logs
        yesterday = _past_date_stamp(1)
        older = _past_date_stamp(5)
        _seed_log_file(tmp_path, f'work-{yesterday}.log')
        _seed_log_file(tmp_path, f'decision-{older}.log')
        _seed_log_file(tmp_path, f'script-execution-{older}.log')

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # all three relocated, sorted, source emptied of them
        assert result['status'] == 'success'
        assert result['moved'] == sorted(
            [
                f'work-{yesterday}.log',
                f'decision-{older}.log',
                f'script-execution-{older}.log',
            ]
        )
        dest = _dormated_global_logs_dir(tmp_path)
        for name in result['moved']:
            assert (dest / name).exists()
            assert not (_logs_dir(tmp_path) / name).exists()

    def test_today_active_log_not_moved(self, tmp_path: Path):
        # today's log (still active) plus one past-date log
        today_name = f'work-{_today_stamp()}.log'
        past_name = f'work-{_past_date_stamp()}.log'
        _seed_log_file(tmp_path, today_name)
        _seed_log_file(tmp_path, past_name)

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # only the past-date log moved; today's stays put
        assert result['status'] == 'success'
        assert result['moved'] == [past_name]
        assert (_logs_dir(tmp_path) / today_name).exists()
        assert not (_dormated_global_logs_dir(tmp_path) / today_name).exists()

    def test_non_dated_files_ignored(self, tmp_path: Path):
        # files that do NOT match the dated-log grammar
        _seed_log_file(tmp_path, 'work.log')  # no date segment
        _seed_log_file(tmp_path, 'notes.txt')  # wrong extension
        _seed_log_file(tmp_path, 'work-2026-13-99.log')  # date-shaped but invalid

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # nothing eligible; all source files remain
        assert result['status'] == 'success'
        assert result['moved'] == []
        assert (_logs_dir(tmp_path) / 'work.log').exists()
        assert (_logs_dir(tmp_path) / 'notes.txt').exists()
        assert (_logs_dir(tmp_path) / 'work-2026-13-99.log').exists()

    def test_refuse_on_existing_destination_never_overwrites(self, tmp_path: Path):
        # a past-date source AND a colliding file already at the dest
        past_name = f'work-{_past_date_stamp()}.log'
        _seed_log_file(tmp_path, past_name, body='SOURCE CONTENT\n')
        dest_dir = _dormated_global_logs_dir(tmp_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        clash = dest_dir / past_name
        clash.write_text('PRE-EXISTING\n', encoding='utf-8')

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # all-or-nothing refusal; neither side mutated
        assert result['status'] == 'error'
        assert result['moved'] == []
        assert 'already exists' in result['reason']
        assert clash.read_text(encoding='utf-8') == 'PRE-EXISTING\n'
        assert (_logs_dir(tmp_path) / past_name).read_text(encoding='utf-8') == 'SOURCE CONTENT\n'

    def test_refuse_on_exists_is_all_or_nothing(self, tmp_path: Path):
        # two eligible past-date logs; one collides at the dest.
        # The refuse-on-exists pre-check must abort BEFORE moving the clean one.
        collide_name = f'work-{_past_date_stamp(1)}.log'
        clean_name = f'decision-{_past_date_stamp(2)}.log'
        _seed_log_file(tmp_path, collide_name)
        _seed_log_file(tmp_path, clean_name)
        dest_dir = _dormated_global_logs_dir(tmp_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / collide_name).write_text('PRE-EXISTING\n', encoding='utf-8')

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # refused, and the non-colliding source was NOT partially moved
        assert result['status'] == 'error'
        assert result['moved'] == []
        assert (_logs_dir(tmp_path) / clean_name).exists()
        assert not (dest_dir / clean_name).exists()

    def test_filename_grammar_excludes_path_separators(self):
        # the dated-log regex never matches a name
        # carrying a path separator, complementing the is_relative_to guards so
        # a crafted entry cannot escape the source dir via the capture group.
        assert audit._GLOBAL_LOG_RE.match('work-2026-05-31.log') is not None
        assert audit._GLOBAL_LOG_RE.match('../escape-2026-05-31.log') is None
        assert audit._GLOBAL_LOG_RE.match('a/b-2026-05-31.log') is None
        assert audit._GLOBAL_LOG_RE.match('/abs-2026-05-31.log') is None

# =============================================================================
# D4 — token-economics cross-plan check
# =============================================================================

def _write_token_plan(
    repo_root: Path,
    plan_id: str,
    *,
    change_type: str = 'feature',
    scope_estimate: str = 'surgical',
    files: int = 5,
    task_count: int = 3,
    phase_tokens: dict[str, int] | None = None,
    session_message_count: int | None = None,
) -> Any:
    """Materialise one synthetic plan and return its parsed ``PlanInputs``.

    Builds a self-contained plan directory under ``{repo_root}/.plan/temp`` —
    never the live ``.plan/local`` tree — carrying the four artefacts the
    token-economics collector reads:

    - ``references.json`` — supplies ``scope_estimate`` and the
      ``modified_files`` list whose length becomes the per-plan file count.
    - ``status.json`` — supplies ``metadata.change_type``.
    - ``work/metrics.toon`` — INI-shaped ``[phase]`` blocks with ``total_tokens``
      lines plus the top-level ``session_message_count`` scalar.
    - ``tasks/TASK-*.json`` — ``task_count`` empty files counted by glob.

    The plan is then parsed through the real ``collect_inputs`` so the
    change_type / scope / file-count wiring is exercised end-to-end rather than
    hand-stuffed onto a ``PlanInputs`` instance.
    """
    if phase_tokens is None:
        phase_tokens = {'5-execute': 10_000}
    plan_dir = repo_root / '.plan' / 'temp' / 'token-corpus' / plan_id
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)

    import json as _json

    (plan_dir / 'references.json').write_text(
        _json.dumps(
            {
                'scope_estimate': scope_estimate,
                'modified_files': [f'src/file_{i}.py' for i in range(files)],
            }
        ),
        encoding='utf-8',
    )
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': {'change_type': change_type}}),
        encoding='utf-8',
    )

    metrics_lines: list[str] = []
    if session_message_count is not None:
        metrics_lines.append(f'session_message_count: {session_message_count}')
    for phase, tokens in phase_tokens.items():
        metrics_lines.append(f'[{phase}]')
        metrics_lines.append(f'  total_tokens: {tokens}')
    (plan_dir / 'work' / 'metrics.toon').write_text(
        '\n'.join(metrics_lines) + '\n', encoding='utf-8'
    )

    for n in range(1, task_count + 1):
        (plan_dir / 'tasks' / f'TASK-{n:03d}.json').write_text('{}', encoding='utf-8')

    return audit.collect_inputs(plan_dir)

class TestTokenEconomicsCollect:
    """``_collect_token_economics_rows`` joins per-plan metrics, the TASK count,
    and the references/status fields into one efficiency row per plan."""

    def test_per_plan_join_yields_tokens_per_file_and_task(self, tmp_path: Path):
        # 12,000 tokens, 4 files, 3 tasks → floor-divided ratios
        inputs = _write_token_plan(
            tmp_path,
            'plan-join',
            files=4,
            task_count=3,
            phase_tokens={'5-execute': 12_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        # single row, ratios floor-divided, fields joined from artefacts
        assert len(rows) == 1
        row = rows[0]
        assert row.plan_id == 'plan-join'
        assert row.change_type == 'feature'
        assert row.scope_estimate == 'surgical'
        assert row.files == 4
        assert row.tasks == 3
        assert row.total_tokens == 12_000
        assert row.tokens_per_file == 3_000  # 12000 // 4
        assert row.tokens_per_task == 4_000  # 12000 // 3

    def test_zero_files_and_tasks_yield_zero_ratios(self, tmp_path: Path):
        # empty footprint must not raise ZeroDivisionError
        inputs = _write_token_plan(
            tmp_path, 'plan-empty', files=0, task_count=0,
            phase_tokens={'5-execute': 5_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        # guarded division returns 0, not an exception
        assert rows[0].tokens_per_file == 0
        assert rows[0].tokens_per_task == 0

    def test_plan_without_metrics_is_excluded_from_corpus(self, tmp_path: Path):
        # a plan whose metrics.toon has no parseable phase block
        good = _write_token_plan(tmp_path, 'plan-good', phase_tokens={'5-execute': 9_000})
        empty_dir = tmp_path / '.plan' / 'temp' / 'token-corpus' / 'plan-nometrics'
        (empty_dir / 'work').mkdir(parents=True, exist_ok=True)
        bad = audit.collect_inputs(empty_dir)

        rows = audit._collect_token_economics_rows([good, bad])

        # only the plan carrying phase metrics survives
        assert {r.plan_id for r in rows} == {'plan-good'}

    def test_exec_metrics_blind_set_when_execute_phase_absent(self, tmp_path: Path):
        # planning-only metrics, no 5-execute token block
        inputs = _write_token_plan(
            tmp_path, 'plan-blind',
            phase_tokens={'2-refine': 4_000, '4-plan': 6_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        # execute total == 0 → structural blindness flag
        assert rows[0].exec_metrics_blind is True

    def test_session_message_count_read_from_top_level_scalar(self, tmp_path: Path):
        # the scalar lives above the first [phase] section
        inputs = _write_token_plan(
            tmp_path, 'plan-msgs', session_message_count=412,
            phase_tokens={'5-execute': 8_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        assert rows[0].session_message_count == 412

class TestTokenEconomicsThresholds:
    """``_derive_token_economics_thresholds`` measures every cut-point from the
    LIVE corpus distribution — none are hard-coded magic numbers."""

    def test_empty_corpus_yields_all_zero_thresholds(self):
        thr = audit._derive_token_economics_thresholds([])

        # an empty corpus can flag nothing
        assert all(v == 0.0 for v in thr.values())
        assert thr['floor_band'] == 0.0
        assert thr['median_total'] == 0.0

    def test_floor_band_is_corpus_tenth_percentile(self, tmp_path: Path):
        # ten plans with distinct totals so p10 is determinate
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'p-{i}', phase_tokens={'5-execute': (i + 1) * 1_000}
                )
                for i in range(10)
            ]
        )

        thr = audit._derive_token_economics_thresholds(rows)

        # nearest-rank p10 of [1000..10000] equals the manual computation
        totals = sorted(float(r.total_tokens) for r in rows)
        assert thr['floor_band'] == audit.percentile(totals, 10)
        assert thr['median_total'] == audit.median(totals)

    def test_median_total_matches_manual_median(self, tmp_path: Path):
        # three plans, odd count → middle value is the median
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(tmp_path, 'lo', phase_tokens={'5-execute': 1_000}),
                _write_token_plan(tmp_path, 'mid', phase_tokens={'5-execute': 5_000}),
                _write_token_plan(tmp_path, 'hi', phase_tokens={'5-execute': 9_000}),
            ]
        )

        thr = audit._derive_token_economics_thresholds(rows)

        assert thr['median_total'] == 5_000.0

    def test_planning_exec_ratio_excludes_blind_plans(self, tmp_path: Path):
        # one measured plan (ratio 2.0) and one execute-blind plan that
        # must NOT contribute to the median ratio distribution.
        measured = _write_token_plan(
            tmp_path, 'measured',
            phase_tokens={'2-refine': 2_000, '4-plan': 2_000, '5-execute': 2_000},
        )
        blind = _write_token_plan(
            tmp_path, 'blind',
            phase_tokens={'2-refine': 9_000, '4-plan': 9_000},
        )

        # collect the per-plan rows first (the threshold deriver consumes
        # _TokenEconomicsRow, not raw PlanInputs)
        rows = audit._collect_token_economics_rows([measured, blind])
        thr = audit._derive_token_economics_thresholds(rows)

        # planning 4000 / execute 2000 = 2.0, blind plan excluded
        assert thr['median_planning_exec_ratio'] == 2.0

    def test_corpus_phase_shares_sum_over_grand_total(self, tmp_path: Path):
        # two plans, all spend in one phase each
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(tmp_path, 'a', phase_tokens={'3-outline': 4_000}),
                _write_token_plan(tmp_path, 'b', phase_tokens={'5-execute': 6_000}),
            ]
        )

        # grand total 10,000: outline 4000/10000, execute 6000/10000
        thr = audit._derive_token_economics_thresholds(rows)

        assert thr['corpus_outline_share'] == 0.4
        assert thr['corpus_execute_share'] == 0.6

class TestTokenEconomicsFlags:
    """``_token_economics_flags`` derives each anti-pattern flag from the
    corpus-relative cut-points — no flag string carries a hard-coded comparand."""

    def test_fixed_overhead_floor_fires_on_cheapest_tiny_plan(self, tmp_path: Path):
        # a corpus where one plan sits in the bottom decile AND the
        # bottom file-count quartile (the non-amortizing 6-phase tax).
        corpus = [
            _write_token_plan(
                tmp_path, f'big-{i}', files=20, phase_tokens={'5-execute': 50_000}
            )
            for i in range(9)
        ]
        floor = _write_token_plan(
            tmp_path, 'floor', files=1, phase_tokens={'5-execute': 500}
        )
        rows = audit._collect_token_economics_rows([*corpus, floor])
        thr = audit._derive_token_economics_thresholds(rows)
        floor_row = next(r for r in rows if r.plan_id == 'floor')

        flags = audit._token_economics_flags(floor_row, thr)

        # flag present and annotates the floating p10 / p25 cut-points
        assert any(f.startswith('fixed_overhead_floor(') for f in flags)
        assert any('p10=' in f and 'p25=' in f for f in flags)

    def test_planning_gt_exec_fires_above_median_ratio(self, tmp_path: Path):
        # corpus median planning/exec ratio is low; one plan blows past it
        baseline = [
            _write_token_plan(
                tmp_path, f'bal-{i}',
                phase_tokens={'2-refine': 1_000, '5-execute': 10_000},
            )
            for i in range(3)
        ]
        heavy = _write_token_plan(
            tmp_path, 'planheavy',
            phase_tokens={'2-refine': 8_000, '4-plan': 8_000, '5-execute': 2_000},
        )
        rows = audit._collect_token_economics_rows([*baseline, heavy])
        thr = audit._derive_token_economics_thresholds(rows)
        heavy_row = next(r for r in rows if r.plan_id == 'planheavy')

        flags = audit._token_economics_flags(heavy_row, thr)

        # ratio 8.0x exceeds the corpus median, annotated against it
        assert any(f.startswith('planning_gt_exec(') and '>median=' in f for f in flags)

    def test_planning_gt_exec_suppressed_for_blind_plan(self, tmp_path: Path):
        # an execute-blind plan must never get planning_gt_exec even
        # though its planning spend is enormous (execute is unmeasured, not zero).
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, 'm',
                    phase_tokens={'2-refine': 1_000, '5-execute': 5_000},
                ),
                _write_token_plan(
                    tmp_path, 'blind',
                    phase_tokens={'2-refine': 9_000, '4-plan': 9_000},
                ),
            ]
        )
        thr = audit._derive_token_economics_thresholds(rows)
        blind_row = next(r for r in rows if r.plan_id == 'blind')

        flags = audit._token_economics_flags(blind_row, thr)

        # no planning_gt_exec, but the exec_metrics_blind floor IS present
        assert not any(f.startswith('planning_gt_exec(') for f in flags)
        assert any(f.startswith('exec_metrics_blind(') for f in flags)

    def test_outline_refine_finalize_heavy_fire_at_phase_p75(self, tmp_path: Path):
        # the baseline plans carry a MODEST outline/refine/finalize share
        # (1,000 of 10,000 each = 10%) so each phase-share distribution has genuine
        # spread and its p75 is a positive cut-point set by the corpus, not zero.
        # One plan is dominated by outline+refine+finalize (30% each) so its share
        # lands strictly above each phase's p75. (A corpus where only ONE plan ever
        # touches a phase has no distribution — p75 collapses to zero and the
        # `cut > 0` guard correctly declines to call that lone plan "heavy".)
        light = [
            _write_token_plan(
                tmp_path, f'exec-{i}',
                phase_tokens={
                    '2-refine': 1_000,
                    '3-outline': 1_000,
                    '6-finalize': 1_000,
                    '5-execute': 7_000,
                },
            )
            for i in range(3)
        ]
        heavy = _write_token_plan(
            tmp_path, 'phaseheavy',
            phase_tokens={
                '2-refine': 3_000,
                '3-outline': 3_000,
                '6-finalize': 3_000,
                '5-execute': 1_000,
            },
        )
        rows = audit._collect_token_economics_rows([*light, heavy])
        thr = audit._derive_token_economics_thresholds(rows)
        heavy_row = next(r for r in rows if r.plan_id == 'phaseheavy')

        flags = audit._token_economics_flags(heavy_row, thr)

        # all three phase-heavy flags fire, each annotated against >=p75
        labels = {f.split('(')[0] for f in flags}
        assert {'outline_heavy', 'refine_heavy', 'finalize_heavy'} <= labels
        assert all('>=p75=' in f for f in flags if f.split('(')[0].endswith('_heavy'))

    def test_big_spend_tiny_footprint_fires_on_inversion(self, tmp_path: Path):
        # a plan at/above the corpus median total but with a footprint
        # in the bottom file-count quartile (the tokens/file inversion).
        small_cheap = [
            _write_token_plan(
                tmp_path, f'sm-{i}', files=2, phase_tokens={'5-execute': 1_000}
            )
            for i in range(3)
        ]
        big_tiny = _write_token_plan(
            tmp_path, 'inversion', files=2, phase_tokens={'5-execute': 80_000}
        )
        wide = [
            _write_token_plan(
                tmp_path, f'wide-{i}', files=40, phase_tokens={'5-execute': 5_000}
            )
            for i in range(3)
        ]
        rows = audit._collect_token_economics_rows([*small_cheap, big_tiny, *wide])
        thr = audit._derive_token_economics_thresholds(rows)
        inv_row = next(r for r in rows if r.plan_id == 'inversion')

        flags = audit._token_economics_flags(inv_row, thr)

        assert any(
            f.startswith('big_spend_tiny_footprint(')
            and '>=median=' in f
            and 'p25=' in f
            for f in flags
        )

    def test_long_session_fires_at_message_p75(self, tmp_path: Path):
        # three short sessions, one long one at/above the corpus p75
        short = [
            _write_token_plan(
                tmp_path, f'short-{i}', session_message_count=50,
                phase_tokens={'5-execute': 5_000},
            )
            for i in range(3)
        ]
        long_plan = _write_token_plan(
            tmp_path, 'marathon', session_message_count=900,
            phase_tokens={'5-execute': 5_000},
        )
        rows = audit._collect_token_economics_rows([*short, long_plan])
        thr = audit._derive_token_economics_thresholds(rows)
        long_row = next(r for r in rows if r.plan_id == 'marathon')

        flags = audit._token_economics_flags(long_row, thr)

        # annotated against the floating message-count p75
        assert any(f.startswith('long_session(') and '>=p75=' in f for f in flags)

    def test_exec_metrics_blind_floor_annotation_listed_first(self, tmp_path: Path):
        # an execute-blind plan; the blindness flag must lead the list
        # so the reader knows every downstream number is a floor.
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, 'blind', phase_tokens={'2-refine': 4_000, '4-plan': 6_000}
                ),
            ]
        )
        thr = audit._derive_token_economics_thresholds(rows)

        flags = audit._token_economics_flags(rows[0], thr)

        # the blindness annotation is the first flag and names the floors
        assert flags[0].startswith('exec_metrics_blind(5-execute=0;floors:')

    def test_clean_plan_has_no_flags(self, tmp_path: Path):
        # a corpus of identical, unremarkable plans: nothing crosses any
        # corpus-relative cut-point (every plan IS the corpus). Because the
        # distribution is uniform on every dimension, the corpus-relative outlier
        # flags must all suppress: the floor band collapses onto the median (no cheap
        # tail), no plan outspends the median (no big-spend outlier), and no session
        # outlier exists (no plan records a `session_message_count`, so the long-
        # session distribution is empty). A representative member is therefore clean.
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'clean-{i}', files=10,
                    phase_tokens={'5-execute': 10_000},
                )
                for i in range(5)
            ]
        )
        thr = audit._derive_token_economics_thresholds(rows)

        flags = audit._token_economics_flags(rows[0], thr)

        # a representative corpus member trips none of the anti-patterns
        assert flags == []

class TestTokenEconomicsCrossCheck:
    """``cross_token_economics`` assembles per-plan rows, by-dimension aggregates,
    and the derived thresholds; ``emit_token_economics_block`` renders them."""

    def test_rows_sorted_descending_by_total_tokens(self, tmp_path: Path):
        inputs = [
            _write_token_plan(tmp_path, 'small', phase_tokens={'5-execute': 1_000}),
            _write_token_plan(tmp_path, 'large', phase_tokens={'5-execute': 9_000}),
            _write_token_plan(tmp_path, 'medium', phase_tokens={'5-execute': 5_000}),
        ]

        result = audit.cross_token_economics(inputs)

        # descending order, corpus count echoed
        assert result['plans_in_corpus'] == 3
        assert [r['plan_id'] for r in result['rows']] == ['large', 'medium', 'small']

    def test_by_change_type_aggregate_amortizes_tokens_per_file(self, tmp_path: Path):
        # two feature plans, one chore plan
        inputs = [
            _write_token_plan(
                tmp_path, 'feat-a', change_type='feature', files=2,
                phase_tokens={'5-execute': 4_000},
            ),
            _write_token_plan(
                tmp_path, 'feat-b', change_type='feature', files=2,
                phase_tokens={'5-execute': 6_000},
            ),
            _write_token_plan(
                tmp_path, 'chore-a', change_type='chore', files=5,
                phase_tokens={'5-execute': 5_000},
            ),
        ]

        result = audit.cross_token_economics(inputs)
        by_ct = {row['value']: row for row in result['by_change_type']}

        # feature: 2 plans, (4000+6000)//(2+2) tokens/file
        assert by_ct['feature']['n'] == 2
        assert by_ct['feature']['avg_tokens'] == 5_000  # (4000+6000)//2
        assert by_ct['feature']['tokens_per_file'] == 2_500  # 10000 // 4
        assert by_ct['chore']['n'] == 1
        assert by_ct['chore']['tokens_per_file'] == 1_000  # 5000 // 5

    def test_by_scope_aggregate_groups_on_scope_estimate(self, tmp_path: Path):
        # two scopes
        inputs = [
            _write_token_plan(
                tmp_path, 'surg-a', scope_estimate='surgical',
                phase_tokens={'5-execute': 3_000},
            ),
            _write_token_plan(
                tmp_path, 'surg-b', scope_estimate='surgical',
                phase_tokens={'5-execute': 5_000},
            ),
            _write_token_plan(
                tmp_path, 'mm-a', scope_estimate='multi_module',
                phase_tokens={'5-execute': 9_000},
            ),
        ]

        result = audit.cross_token_economics(inputs)
        by_scope = {row['value']: row for row in result['by_scope']}

        assert by_scope['surgical']['n'] == 2
        assert by_scope['multi_module']['n'] == 1

    def test_empty_corpus_yields_zero_aggregates_no_rows(self):
        # no plans carrying metrics
        result = audit.cross_token_economics([])

        # best-effort empty result, never raises
        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert result['by_change_type'] == []
        assert result['by_scope'] == []

    def test_emit_block_carries_derived_thresholds_and_genuine_count(
        self, tmp_path: Path
    ):
        # a corpus with exactly one clearly-flagged plan (long session).
        # The token/file footprint is deliberately UNIFORM across all four plans so
        # the corpus-relative floor/big-spend outlier flags correctly suppress (no
        # cheap tail, no plan outspending the median) — only the genuine session
        # outlier should be flagged. The three baseline plans record no
        # `session_message_count`, so they are excluded from the message-count p75
        # distribution and cannot trip `long_session`; the marathon plan alone sets
        # the p75 and exceeds it.
        short = [
            _write_token_plan(
                tmp_path, f'short-{i}',
                phase_tokens={'5-execute': 5_000},
            )
            for i in range(3)
        ]
        flagged = _write_token_plan(
            tmp_path, 'flagged', session_message_count=999,
            phase_tokens={'5-execute': 5_000},
        )
        result = audit.cross_token_economics([*short, flagged])

        block = audit.emit_token_economics_block(result)

        # header, derived (floating) thresholds, and the genuine count
        assert 'check: token-economics' in block
        assert 'status: success' in block
        assert 'floor_band_p10_tokens:' in block
        assert 'median_total_tokens:' in block
        assert 'long_session_p75_msgs:' in block
        assert 'genuine_signal_count: 1' in block
        # the flagged plan's row carries the genuine severity stamp
        assert 'genuine' in block

    def test_emit_block_includes_by_change_type_and_by_scope_tables(
        self, tmp_path: Path
    ):
        inputs = [
            _write_token_plan(
                tmp_path, 'a', change_type='feature', scope_estimate='surgical',
                phase_tokens={'5-execute': 5_000},
            ),
            _write_token_plan(
                tmp_path, 'b', change_type='fix', scope_estimate='multi_module',
                phase_tokens={'5-execute': 7_000},
            ),
        ]
        result = audit.cross_token_economics(inputs)

        block = audit.emit_token_economics_block(result)

        # both aggregate tables are rendered with their column headers
        assert 'by_change_type[' in block
        assert 'by_scope[' in block
        assert 'tokens_per_file' in block

    def test_thresholds_are_corpus_derived_not_hard_coded(self, tmp_path: Path):
        # two corpora with disjoint scales must yield different floors,
        # proving the cut-points float with the live distribution (no magic number).
        small_rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'sm-{i}', phase_tokens={'5-execute': (i + 1) * 100}
                )
                for i in range(10)
            ]
        )
        big_rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'bg-{i}', phase_tokens={'5-execute': (i + 1) * 100_000}
                )
                for i in range(10)
            ]
        )

        small_thr = audit._derive_token_economics_thresholds(small_rows)
        big_thr = audit._derive_token_economics_thresholds(big_rows)

        # the floor band scales with the corpus, it is not a constant
        assert small_thr['floor_band'] != big_thr['floor_band']
        assert big_thr['floor_band'] == small_thr['floor_band'] * 1_000

# =============================================================================
# D5 — quality-chain cross-plan check
# =============================================================================

def _write_findings_plan(
    repo_root: Path,
    plan_id: str,
    findings_by_file: dict[str, list[dict[str, Any]]],
) -> Any:
    """Materialise a plan carrying ``artifacts/findings/{file}`` JSONL findings.

    ``findings_by_file`` maps a findings filename (e.g. ``test-failure.jsonl``,
    ``pr-comment.jsonl``, ``qgate-phase-6.jsonl``) to a list of finding dicts;
    each dict is written as one JSONL line. The plan is parsed through the real
    ``collect_inputs`` so the quality-chain check reads it end-to-end.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'qc-corpus' / plan_id
    findings_dir = plan_dir / 'artifacts' / 'findings'
    findings_dir.mkdir(parents=True, exist_ok=True)
    for fname, records in findings_by_file.items():
        lines = '\n'.join(_json.dumps(r) for r in records) + '\n'
        (findings_dir / fname).write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)

class TestQualityChainMechanism:
    """``_qc_mechanism`` classifies which quality gate surfaced a finding."""

    def test_build_files_classify_as_build(self):
        assert audit._qc_mechanism('test-failure.jsonl', {}) == 'build'
        assert audit._qc_mechanism('build-error.jsonl', {}) == 'build'

    def test_bot_pr_comment_is_auto_review(self):
        assert (
            audit._qc_mechanism('pr-comment.jsonl', {'detail': 'gemini-code-assist says'})
            == 'auto-review'
        )

    def test_human_pr_comment_is_human_review(self):
        assert (
            audit._qc_mechanism('pr-comment.jsonl', {'detail': 'reviewer asks to rename'})
            == 'human-review'
        )

    def test_qgate_and_assessments_are_self_review(self):
        assert audit._qc_mechanism('qgate-phase-6.jsonl', {}) == 'self-review'
        assert audit._qc_mechanism('assessments.jsonl', {}) == 'self-review'
        assert audit._qc_mechanism('other.jsonl', {'source': 'qgate'}) == 'self-review'

    def test_user_review_source_is_human_review(self):
        assert audit._qc_mechanism('other.jsonl', {'source': 'user_review'}) == 'human-review'

    def test_unclassified_is_other(self):
        assert audit._qc_mechanism('mystery.jsonl', {}) == 'other'

class TestQualityChainResolution:
    """``_qc_resolution`` buckets a finding's disposition via resolution +
    resolution_detail regex."""

    def test_promoted_short_circuits_to_lesson(self):
        assert audit._qc_resolution({'promoted': True, 'resolution': 'fixed'}) == 'lesson'

    def test_fixed_without_rerun_is_direct_fix(self):
        assert audit._qc_resolution({'resolution': 'fixed', 'resolution_detail': 'patched'}) == 'direct_fix'

    def test_fixed_with_flake_detail_is_rerun_flake(self):
        assert (
            audit._qc_resolution({'resolution': 'fixed', 'resolution_detail': 'transient flake, re-run'})
            == 'rerun_flake'
        )

    def test_taken_into_account_with_task_detail_is_loop_back(self):
        assert (
            audit._qc_resolution(
                {'resolution': 'taken_into_account', 'resolution_detail': 'addressed by TASK-012'}
            )
            == 'loop_back'
        )

    def test_taken_into_account_without_marker_is_direct_fix(self):
        assert (
            audit._qc_resolution({'resolution': 'taken_into_account', 'resolution_detail': 'done inline'})
            == 'direct_fix'
        )

    def test_accepted_suppressed_pass_through(self):
        assert audit._qc_resolution({'resolution': 'accepted'}) == 'accepted'
        assert audit._qc_resolution({'resolution': 'suppressed'}) == 'suppressed'

    def test_pending_none_empty_bucket_to_pending(self):
        assert audit._qc_resolution({'resolution': 'pending'}) == 'pending'
        assert audit._qc_resolution({'resolution': 'none'}) == 'pending'
        assert audit._qc_resolution({}) == 'pending'

class TestQualityChainShiftLeftTier:
    """``_qc_shift_left_tier`` grades how deterministically the surfacer could
    have caught a finding."""

    def test_regex_keyword_is_tier1(self):
        assert audit._qc_shift_left_tier({'title': 'regex pattern over-fits the input'}) == 1

    def test_duplication_keyword_is_tier1(self):
        assert audit._qc_shift_left_tier({'detail': 'duplicated wording across two sections'}) == 1

    def test_naming_keyword_is_tier2(self):
        assert audit._qc_shift_left_tier({'title': 'rename this helper for clarity'}) == 2

    def test_logic_keyword_is_tier3(self):
        assert audit._qc_shift_left_tier({'detail': 'off-by-one bug in the boundary check'}) == 3

    def test_sparse_body_is_tier4(self):
        assert audit._qc_shift_left_tier({'title': 'see comment'}) == 4

class TestQualityChainFlags:
    """``_quality_chain_flags`` computes the per-plan chain anti-pattern flags."""

    def test_auto_review_only_when_no_build_or_self_review(self, tmp_path: Path):
        # only a bot PR comment, no build/self-review surface
        inputs = _write_findings_plan(
            tmp_path,
            'plan-auto-only',
            {'pr-comment.jsonl': [{'detail': 'gemini flagged a regex', 'resolution': 'fixed'}]},
        )
        plan = audit._collect_quality_chain([inputs])[0]

        flags = audit._quality_chain_flags(plan)

        assert any(f.startswith('auto_review_only') for f in flags)
        # no self-review surface → no_qgate6 also fires
        assert 'no_qgate6' in flags

    def test_build_pending_pile_fires_at_two_pending(self, tmp_path: Path):
        # two unresolved build failures
        inputs = _write_findings_plan(
            tmp_path,
            'plan-build-pile',
            {
                'test-failure.jsonl': [
                    {'resolution': 'pending', 'title': 'test a fails'},
                    {'resolution': 'pending', 'title': 'test b fails'},
                ]
            },
        )
        plan = audit._collect_quality_chain([inputs])[0]

        flags = audit._quality_chain_flags(plan)

        assert any(f.startswith('build_pending_pile') for f in flags)

    def test_review_body_duplicate_when_title_spans_self_and_auto(self, tmp_path: Path):
        # same title in both self-review and auto-review
        inputs = _write_findings_plan(
            tmp_path,
            'plan-dupe',
            {
                'qgate-phase-6.jsonl': [{'title': 'Missing null guard', 'resolution': 'fixed'}],
                'pr-comment.jsonl': [
                    {'detail': 'gemini: Missing null guard', 'title': 'Missing null guard', 'resolution': 'fixed'}
                ],
            },
        )
        plan = audit._collect_quality_chain([inputs])[0]

        flags = audit._quality_chain_flags(plan)

        assert any(f.startswith('review_body_duplicate') for f in flags)

class TestQualityChainCrossCheck:
    """``cross_quality_chain`` assembles the matrix, per-plan rows, per-finding
    rows, and shift-left histogram; ``emit_quality_chain_block`` renders them
    with the D1 severity column."""

    def test_plans_without_findings_dir_excluded(self, tmp_path: Path):
        # one plan with findings, one bare plan dir
        good = _write_findings_plan(
            tmp_path, 'has-findings',
            {'test-failure.jsonl': [{'resolution': 'fixed', 'title': 't'}]},
        )
        bare_dir = tmp_path / '.plan' / 'temp' / 'qc-corpus' / 'no-findings'
        bare_dir.mkdir(parents=True, exist_ok=True)
        bare = audit.collect_inputs(bare_dir)

        result = audit.cross_quality_chain([good, bare])

        # only the plan with a findings dir is in the corpus
        assert result['plans_in_corpus'] == 1
        assert result['rows'][0]['plan_id'] == 'has-findings'

    def test_corpus_matrix_sums_per_plan_matrices(self, tmp_path: Path):
        # two plans, each one direct-fix build finding
        inputs = [
            _write_findings_plan(
                tmp_path, 'p1',
                {'test-failure.jsonl': [{'resolution': 'fixed', 'title': 'a'}]},
            ),
            _write_findings_plan(
                tmp_path, 'p2',
                {'build-error.jsonl': [{'resolution': 'fixed', 'title': 'b'}]},
            ),
        ]

        result = audit.cross_quality_chain(inputs)

        # corpus build/direct_fix cell == 2
        assert result['corpus_matrix']['build']['direct_fix'] == 2

    def test_empty_corpus_yields_zero_aggregates(self):
        result = audit.cross_quality_chain([])

        # best-effort empty, never raises
        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert result['findings'] == []

    def test_emit_block_carries_severity_and_shift_left_summary(self, tmp_path: Path):
        # an auto-review-only plan with a Tier-1 regex finding
        inputs = _write_findings_plan(
            tmp_path, 'plan-shift',
            {'pr-comment.jsonl': [
                {'detail': 'gemini: regex over-fits', 'title': 'regex over-fits', 'resolution': 'fixed'}
            ]},
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)

        # header, the matrix/plan/finding tables, severity + shift-left
        assert 'check: quality-chain' in block
        assert 'status: success' in block
        assert 'corpus_matrix[' in block
        assert 'plans[' in block
        assert 'findings[' in block
        assert 'shift_left_tiers:' in block
        assert 'tier1=1' in block
        # the auto-review finding row is a genuine signal (D1 severity column)
        assert 'genuine' in block

    def test_per_finding_rows_emitted_for_every_finding(self, tmp_path: Path):
        # three findings across two files
        inputs = _write_findings_plan(
            tmp_path, 'plan-rows',
            {
                'test-failure.jsonl': [
                    {'resolution': 'fixed', 'title': 'one'},
                    {'resolution': 'pending', 'title': 'two'},
                ],
                'qgate-phase-6.jsonl': [{'resolution': 'fixed', 'title': 'three'}],
            },
        )
        result = audit.cross_quality_chain([inputs])

        # every finding produced a per-finding record (walk-every-finding)
        assert len(result['findings']) == 3
        titles = {f['title'] for f in result['findings']}
        assert titles == {'one', 'two', 'three'}

    def test_check_registered_in_registries(self):
        # the check is dispatchable and marked cross-plan
        assert 'quality-chain' in audit.CHECK_NAMES
        assert 'quality-chain' in audit.CROSS_PLAN_CHECKS

class TestQualityChainFindingSeverity:
    """``_qc_finding_genuine`` is the D1 severity predicate stamped onto every
    per-finding row by ``emit_quality_chain_block``. A finding is genuine
    (actionable) when it is an auto-review row (caught only at the most expensive
    stage) OR is still ``pending`` at archive time (unresolved chain debt); a
    finding cleanly resolved by an earlier mechanism is informational. The
    existing emit test only proves an auto-review row stamps ``genuine`` — these
    pin the ``pending`` branch and the informational disposition directly."""

    def test_pending_build_finding_is_genuine(self):
        # unresolved chain debt, even though build is the
        # cheapest mechanism, is a genuine signal.
        assert audit._qc_finding_genuine(
            {'mechanism': 'build', 'resolution': 'pending'}
        )

    def test_pending_self_review_finding_is_genuine(self):
        # a self-review finding left pending is debt too
        assert audit._qc_finding_genuine(
            {'mechanism': 'self-review', 'resolution': 'pending'}
        )

    def test_auto_review_finding_is_genuine_regardless_of_resolution(self):
        # auto-review is the shift-left subject; a cleanly
        # direct-fixed auto-review row is STILL genuine (it shifted right).
        assert audit._qc_finding_genuine(
            {'mechanism': 'auto-review', 'resolution': 'direct_fix'}
        )

    def test_direct_fix_build_finding_is_informational(self):
        # the expected disposition, not a signal
        assert not audit._qc_finding_genuine(
            {'mechanism': 'build', 'resolution': 'direct_fix'}
        )

    def test_lesson_self_review_finding_is_informational(self):
        # promoted-to-lesson self-review is informational
        assert not audit._qc_finding_genuine(
            {'mechanism': 'self-review', 'resolution': 'lesson'}
        )

    def test_human_review_direct_fix_is_informational(self):
        # a resolved human-review row is expected, not a signal
        assert not audit._qc_finding_genuine(
            {'mechanism': 'human-review', 'resolution': 'direct_fix'}
        )

    def test_emit_block_renders_pending_finding_row_as_genuine(self, tmp_path: Path):
        # a single self-review finding left pending (no auto-review row,
        # so the only `genuine` cell must come from the pending-branch predicate).
        inputs = _write_findings_plan(
            tmp_path,
            'plan-pending',
            {'qgate-phase-6.jsonl': [{'title': 'unguarded null', 'resolution': 'pending'}]},
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)
        finding_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('plan-pending,self-review,pending,')
        )

        # the pending self-review finding row ends on the genuine cell,
        # and the finding-genuine summary count reflects it.
        assert finding_line.endswith(',genuine')
        assert 'finding_genuine_signal_count: 1' in block

    def test_emit_block_renders_direct_fixed_build_finding_as_informational(
        self, tmp_path: Path
    ):
        # a single cleanly direct-fixed build finding: the expected
        # disposition, so its per-finding row must stamp informational and the
        # finding-genuine count must be zero.
        inputs = _write_findings_plan(
            tmp_path,
            'plan-clean',
            {'test-failure.jsonl': [{'title': 'flaky boundary', 'resolution': 'fixed'}]},
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)
        finding_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('plan-clean,build,direct_fix,')
        )

        assert finding_line.endswith(',informational')
        assert 'finding_genuine_signal_count: 0' in block

# =============================================================================
# D6 — sequence-and-build-minimality cross-plan check
# =============================================================================

def _sbm_call(ts: str, notation: str, sub: str, dur: float | None = None) -> str:
    """Build one ``script-execution.log`` call line in the ``_SBM_CALL_RE`` grammar.

    Format: ``[<ts>Z] [INFO] [<hash>] <notation> <sub>[ (<dur>s)]``. ``ts`` is a
    bare ``YYYY-MM-DDTHH:MM:SS`` stamp (no trailing ``Z`` — this helper adds it).
    A ``dur`` of ``None`` omits the trailing duration clause, which the parser
    reads as a 0.0-second (``unknown``-band) call.
    """
    head = f'[{ts}Z] [INFO] [3befe7] {notation} {sub}'
    return head if dur is None else f'{head} ({dur:.1f}s)'

def _sbm_dispatch(ts: str, role: str) -> str:
    """Build one ``work.log`` ``[DISPATCH] ... role=phase-N...`` marker line.

    The phase-bucketing timeline in ``_sequence_build_minimality_plan`` only reads
    work.log lines that start with a ``[<ts>Z]`` stamp AND match ``_SBM_DISPATCH_RE``;
    ``role`` is a ``phase-N-name`` token (e.g. ``phase-5-execute``).
    """
    return f'[{ts}Z] [INFO] [3befe7] [DISPATCH] (orchestrator) role={role} dispatched'

def _write_sbm_plan(
    repo_root: Path,
    plan_id: str,
    *,
    sel_lines: list[str] | None = None,
    work_lines: list[str] | None = None,
    modified_files: list[str] | None = None,
    change_type: str | None = None,
    ci_runs: int = 0,
) -> Any:
    """Materialise a synthetic plan dir for the sequence-and-build-minimality check.

    Writes ``logs/script-execution.log`` (the ordered call timeline),
    ``logs/work.log`` (dispatch markers + build-verb mentions),
    ``references.json`` (the ``modified_files`` footprint), ``status.json``
    (``metadata.change_type``), and ``ci_runs`` empty ``artifacts/ci-runs/run-N/``
    directories. The plan is then parsed through the real ``collect_inputs`` so the
    check reads ``change_type`` end-to-end. Lives under ``.plan/temp/`` — never the
    real ``.plan/local/``.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'sbm-corpus' / plan_id
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'script-execution.log').write_text(
        '\n'.join(sel_lines or []) + '\n', encoding='utf-8'
    )
    (logs_dir / 'work.log').write_text(
        '\n'.join(work_lines or []) + '\n', encoding='utf-8'
    )
    (plan_dir / 'references.json').write_text(
        _json.dumps({'modified_files': modified_files or []}), encoding='utf-8'
    )
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': {'change_type': change_type} if change_type else {}}),
        encoding='utf-8',
    )
    for i in range(ci_runs):
        (plan_dir / 'artifacts' / 'ci-runs' / f'run-{i}').mkdir(
            parents=True, exist_ok=True
        )
    return audit.collect_inputs(plan_dir)

_BUILD = 'pm:build-pyproject:pyproject_build'
_ARCH = 'pm:manage-architecture:architecture'

class TestSequenceBuildMinimalityClassify:
    """``_sbm_classify_build`` buckets a build's wall-clock duration against the
    centralized minimal/heavy bands (120s / 400s)."""

    def test_zero_duration_is_unknown(self):
        # an unrecorded (0.0s) build is ``unknown``
        assert audit._sbm_classify_build(0.0) == 'unknown'

    def test_negative_duration_is_unknown(self):
        # defensive: <= 0 collapses to ``unknown``
        assert audit._sbm_classify_build(-5.0) == 'unknown'

    def test_below_minimal_band_is_minimal(self):
        # strictly under build_minimal_seconds
        assert audit._sbm_classify_build(119.9) == 'minimal'

    def test_at_minimal_ceiling_is_scoped(self):
        # exactly build_minimal_seconds tips into scoped
        minimal = float(audit.THRESHOLDS['build_minimal_seconds'])
        assert audit._sbm_classify_build(minimal) == 'scoped'

    def test_between_bands_is_scoped(self):
        # 120..400 is a scoped run
        assert audit._sbm_classify_build(250.0) == 'scoped'

    def test_at_heavy_ceiling_is_heavy(self):
        # exactly build_heavy_seconds is heavy (NOT scoped)
        heavy = float(audit.THRESHOLDS['build_heavy_seconds'])
        assert audit._sbm_classify_build(heavy) == 'heavy'

    def test_above_heavy_band_is_heavy(self):
        # well over the heavy ceiling
        assert audit._sbm_classify_build(900.0) == 'heavy'

class TestSequenceBuildMinimalityPhaseBucketing:
    """``_sequence_build_minimality_plan`` attributes each ``script-execution.log``
    call to the phase whose ``[DISPATCH] role=phase-N`` marker most recently
    preceded it on the ``work.log`` timeline."""

    def test_calls_before_first_dispatch_bucket_to_one_init(self, tmp_path: Path):
        # a single call before any dispatch marker
        inputs = _write_sbm_plan(
            tmp_path, 'phase-default',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            work_lines=[_sbm_dispatch('2026-06-01T11:00:00', 'phase-5-execute')],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the call predates the dispatch, so it falls in the default
        # ``1-init`` bucket (role normalized: ``phase-`` stripped).
        assert '1-init:1' in row['phase_graph']

    def test_call_after_dispatch_buckets_to_normalized_role(self, tmp_path: Path):
        # a build call after a phase-5-execute dispatch marker
        inputs = _write_sbm_plan(
            tmp_path, 'phase-exec',
            sel_lines=[_sbm_call('2026-06-01T12:00:00', _BUILD, 'run', 30.0)],
            work_lines=[_sbm_dispatch('2026-06-01T11:00:00', 'phase-5-execute')],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the call is attributed to ``5-execute`` and tagged with one build
        assert '5-execute:1(b=1)' in row['phase_graph']

    def test_arch_call_annotates_phase_with_arch_count(self, tmp_path: Path):
        # an architecture call after a dispatch contributes the ``a=`` tag
        inputs = _write_sbm_plan(
            tmp_path, 'phase-arch',
            sel_lines=[_sbm_call('2026-06-01T12:00:00', _ARCH, 'resolve', 0.5)],
            work_lines=[_sbm_dispatch('2026-06-01T11:00:00', 'phase-4-plan')],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the architecture call lands in 4-plan with an ``a=1`` annotation
        assert '4-plan:1(a=1)' in row['phase_graph']
        assert row['arch_calls'] == 1

class TestSequenceBuildMinimalityBuildClass:
    """The per-plan row counts builds by duration band and reports the corpus
    build-second aggregates."""

    def test_three_bands_counted_independently(self, tmp_path: Path):
        # one minimal (<120), one scoped (120..400), one heavy (>400) build
        inputs = _write_sbm_plan(
            tmp_path, 'three-bands',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0),
                _sbm_call('2026-06-01T11:00:00', _BUILD, 'run', 250.0),
                _sbm_call('2026-06-01T12:00:00', _BUILD, 'run', 500.0),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # each band counted once; aggregates reflect the heaviest + total
        assert row['builds'] == 3
        assert row['build_minimal'] == 1
        assert row['build_scoped'] == 1
        assert row['build_heavy'] == 1
        assert row['max_build_seconds'] == 500
        assert row['total_build_seconds'] == 780

    def test_non_build_calls_are_not_classified_as_builds(self, tmp_path: Path):
        # an architecture call and a manage-* call, neither a build
        inputs = _write_sbm_plan(
            tmp_path, 'no-builds',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve', 0.5),
                _sbm_call('2026-06-01T10:01:00', 'pm:manage-tasks:manage-tasks', 'read'),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # two calls recorded, zero builds
        assert row['calls'] == 2
        assert row['builds'] == 0
        assert row['build_minimal'] == 0

class TestSequenceBuildMinimalityVerbMining:
    """Build-verb mining over ``work.log`` distinguishes scoped vs all-modules
    ``module-tests`` runs and counts the other build verbs."""

    def test_scoped_vs_all_module_tests(self, tmp_path: Path):
        # one scoped (known module) and one all-modules (no arg) run
        inputs = _write_sbm_plan(
            tmp_path, 'verb-mt',
            work_lines=[
                'ran module-tests plan-marshall and it passed',
                'then ran module-tests across the whole tree',
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # scoped counted once (smt), all-modules counted once (amt)
        assert 'smt=1' in row['verbs']
        assert 'amt=1' in row['verbs']

    def test_unknown_module_arg_counts_as_all(self, tmp_path: Path):
        # a module-tests arg that is NOT a known buildable module
        inputs = _write_sbm_plan(
            tmp_path, 'verb-unknown',
            work_lines=['ran module-tests not-a-real-module here'],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # an unrecognised arg falls into the all-modules bucket
        assert 'smt=0' in row['verbs']
        assert 'amt=1' in row['verbs']

    def test_other_build_verbs_counted(self, tmp_path: Path):
        # one each of quality-gate, verify, coverage, compile
        inputs = _write_sbm_plan(
            tmp_path, 'verb-others',
            work_lines=[
                'invoked quality-gate plan-marshall',
                'invoked verify plan-marshall',
                'invoked coverage plan-marshall',
                'invoked compile plan-marshall',
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # each verb tallied in its own slot
        assert 'qg=1' in row['verbs']
        assert 'vf=1' in row['verbs']
        assert 'cov=1' in row['verbs']
        assert 'cmp=1' in row['verbs']

class TestSequenceBuildMinimalityFlags:
    """Each redundancy / anti-pattern flag fires on its own primitive and is
    absent on a clean plan."""

    def test_build_churn_flag_on_clustered_builds(self, tmp_path: Path):
        # two builds 5 minutes apart (< 10-minute clustering window)
        inputs = _write_sbm_plan(
            tmp_path, 'flag-churn',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0),
                _sbm_call('2026-06-01T10:05:00', _BUILD, 'run', 30.0),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the second build clusters with the first
        assert row['build_churn'] == 1
        assert any(f.startswith('build_churn(') for f in row['flags'])

    def test_no_churn_when_builds_spaced_beyond_window(self, tmp_path: Path):
        # two builds 20 minutes apart (> 10-minute window)
        inputs = _write_sbm_plan(
            tmp_path, 'flag-nochurn',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0),
                _sbm_call('2026-06-01T10:20:00', _BUILD, 'run', 30.0),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # spaced builds do not cluster
        assert row['build_churn'] == 0
        assert not any(f.startswith('build_churn(') for f in row['flags'])

    def test_non_minimal_build_flag_on_heavy_build(self, tmp_path: Path):
        # a single heavy (> 400s) build
        inputs = _write_sbm_plan(
            tmp_path, 'flag-heavy',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 600.0)],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the heavy build raises non_minimal_build
        assert row['build_heavy'] == 1
        assert any(f.startswith('non_minimal_build(') for f in row['flags'])

    def test_docs_only_build_flag_when_no_py_touched(self, tmp_path: Path):
        # a build ran but only a markdown file was modified
        inputs = _write_sbm_plan(
            tmp_path, 'flag-docs',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            modified_files=['doc/guide.md'],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # docs_only footprint + a build => the docs_only_build flag
        assert row['docs_only'] is True
        assert any(f.startswith('docs_only_build(') for f in row['flags'])

    def test_no_docs_only_flag_when_py_touched(self, tmp_path: Path):
        # a build ran and a .py file was modified
        inputs = _write_sbm_plan(
            tmp_path, 'flag-py',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            modified_files=['scripts/audit.py'],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # a .py touch clears docs_only
        assert row['docs_only'] is False
        assert not any(f.startswith('docs_only_build(') for f in row['flags'])

    def test_ci_rerun_flag_on_multiple_ci_run_dirs(self, tmp_path: Path):
        # two CI run directories under artifacts/ci-runs/
        inputs = _write_sbm_plan(tmp_path, 'flag-ci', ci_runs=2)

        row = audit._sequence_build_minimality_plan(inputs)

        # >1 CI run directory raises ci_rerun
        assert row['ci_runs'] == 2
        assert any(f.startswith('ci_rerun(') for f in row['flags'])

    def test_no_ci_rerun_flag_for_single_run(self, tmp_path: Path):
        # exactly one CI run directory (not a rerun)
        inputs = _write_sbm_plan(tmp_path, 'flag-ci-single', ci_runs=1)

        row = audit._sequence_build_minimality_plan(inputs)

        # a single CI run is not a rerun signal
        assert row['ci_runs'] == 1
        assert not any(f.startswith('ci_rerun(') for f in row['flags'])

    def test_phase_reentry_flag_when_role_dispatched_twice(self, tmp_path: Path):
        # phase-5-execute dispatched twice on the work.log timeline
        inputs = _write_sbm_plan(
            tmp_path, 'flag-reentry',
            work_lines=[
                _sbm_dispatch('2026-06-01T10:00:00', 'phase-5-execute'),
                _sbm_dispatch('2026-06-01T11:00:00', 'phase-5-execute'),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the re-dispatched role surfaces in phase_reentry + the flag fires
        assert row['phase_reentry'] == '5-execute'
        assert any(f.startswith('phase_reentry(') for f in row['flags'])

    def test_arch_over_resolution_flag_when_arch_dwarfs_builds(self, tmp_path: Path):
        # 5 architecture calls against a single build (>= 5x ratio)
        sel = [
            _sbm_call(f'2026-06-01T10:0{i}:00', _ARCH, 'resolve', 0.5) for i in range(5)
        ]
        sel.append(_sbm_call('2026-06-01T10:06:00', _BUILD, 'run', 30.0))
        inputs = _write_sbm_plan(tmp_path, 'flag-arch', sel_lines=sel)

        row = audit._sequence_build_minimality_plan(inputs)

        # arch (5) >= 5 * builds (1) raises arch_over_resolution
        assert row['arch_calls'] == 5
        assert row['builds'] == 1
        assert any(f.startswith('arch_over_resolution(') for f in row['flags'])

    def test_consecutive_dup_flag_on_back_to_back_identical_calls(self, tmp_path: Path):
        # two identical (notation, sub) calls back-to-back
        inputs = _write_sbm_plan(
            tmp_path, 'flag-dup',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', 'pm:manage-tasks:manage-tasks', 'read'),
                _sbm_call('2026-06-01T10:01:00', 'pm:manage-tasks:manage-tasks', 'read'),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the second identical call is a consecutive duplicate
        assert row['consecutive_dup'] == 1
        assert any(f.startswith('consecutive_dup(') for f in row['flags'])

    def test_clean_minimal_plan_has_no_flags(self, tmp_path: Path):
        # one minimal build touching a .py file, single CI run, distinct calls
        inputs = _write_sbm_plan(
            tmp_path, 'flag-clean',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve', 0.5),
                _sbm_call('2026-06-01T10:05:00', _BUILD, 'run', 30.0),
            ],
            modified_files=['scripts/audit.py'],
            ci_runs=1,
        )

        row = audit._sequence_build_minimality_plan(inputs)

        # the expected minimal shape carries no redundancy flag
        assert row['flags'] == []

class TestSequenceBuildMinimalityEmitBlock:
    """``emit_sequence_build_minimality_block`` renders the cross-plan block with
    the D1 severity column, the genuine-signal count, and is wired into the check
    registries."""

    def test_check_registered_in_registries(self):
        # dispatchable and cross-plan scoped
        assert 'sequence-and-build-minimality' in audit.CHECK_NAMES
        assert 'sequence-and-build-minimality' in audit.CROSS_PLAN_CHECKS

    def test_genuine_predicate_fires_only_with_flags(self):
        # a row with >=1 flag is genuine, an empty-flag
        # row is informational (the D1 severity predicate).
        assert audit._sbm_genuine({'flags': ['build_churn(1<10m)']}) is True
        assert audit._sbm_genuine({'flags': []}) is False

    def test_block_carries_thresholds_and_corpus_totals(self, tmp_path: Path):
        # one plan with a single minimal build
        inputs = _write_sbm_plan(
            tmp_path, 'emit-thresholds',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([inputs])

        block = audit.emit_sequence_build_minimality_block(result)

        # header, the duration-band thresholds, and corpus aggregates
        assert 'check: sequence-and-build-minimality' in block
        assert 'status: success' in block
        assert 'build_minimal_seconds: 120' in block
        assert 'build_heavy_seconds: 400' in block
        assert 'build_clustering_minutes: 10' in block
        assert 'corpus_builds: 1' in block
        assert 'corpus_build_minimal: 1' in block

    def test_flagged_row_renders_genuine_severity_cell(self, tmp_path: Path):
        # a heavy build raises non_minimal_build, the only flag, so the
        # per-plan row must stamp the genuine severity cell.
        inputs = _write_sbm_plan(
            tmp_path, 'emit-genuine',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 600.0)],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([inputs])

        block = audit.emit_sequence_build_minimality_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('emit-genuine,')
        )

        # the flagged row ends on the genuine cell, and the count reflects it
        assert row_line.endswith(',genuine')
        assert 'genuine_signal_count: 1' in block

    def test_clean_row_renders_informational_severity_cell(self, tmp_path: Path):
        # a minimal-only plan with no redundancy primitive: informational
        inputs = _write_sbm_plan(
            tmp_path, 'emit-clean',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([inputs])

        block = audit.emit_sequence_build_minimality_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('emit-clean,')
        )

        # the clean row stamps informational and the genuine count is zero
        assert row_line.endswith(',informational')
        assert 'genuine_signal_count: 0' in block

    def test_rows_sorted_descending_by_total_build_seconds(self, tmp_path: Path):
        # two plans; the heavier total must sort first
        light = _write_sbm_plan(
            tmp_path, 'sort-light',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            modified_files=['scripts/audit.py'],
        )
        heavy = _write_sbm_plan(
            tmp_path, 'sort-heavy',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 600.0)],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([light, heavy])

        # rows ordered by descending total_build_seconds
        assert [r['plan_id'] for r in result['rows']] == ['sort-heavy', 'sort-light']

    def test_empty_corpus_yields_zero_aggregates_no_rows(self):
        # no plans in the corpus
        result = audit.cross_sequence_build_minimality([])
        block = audit.emit_sequence_build_minimality_block(result)

        # all-zero aggregates, no rows, zero genuine signals
        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert 'plans_in_corpus: 0' in block
        assert 'genuine_signal_count: 0' in block

# =============================================================================
# D7 — input-integrity meta-check (per-plan presence/health + corpus
# data_confidence summary + D1 severity emission)
# =============================================================================

def _write_ii_plan(
    repo_root: Path,
    plan_id: str,
    *,
    has_execution: bool = True,
    has_metrics: bool = True,
    has_references: bool = True,
    has_tasks: bool = True,
    has_findings: bool = True,
    has_script_log: bool = True,
    phase_tokens: dict[str, int] | None = None,
    dispatch_marker: bool = True,
) -> Any:
    """Materialise a synthetic plan dir for the input-integrity meta-check.

    Builds, under ``{repo_root}/.plan/temp/ii-corpus/{plan_id}`` (never the live
    ``.plan/local`` tree), exactly the canonical input set
    ``check_input_integrity`` probes — each artefact toggled by its
    ``has_*`` flag so a test can omit any single input:

    - ``execution.toon`` — the composed manifest presence sentinel.
    - ``work/metrics.toon`` — INI-shaped ``[phase]`` blocks with ``total_tokens``
      lines; ``phase_tokens`` controls which phases are recorded and with how
      many tokens (a zero-token ``5-execute`` is the load-bearing ``blind`` case).
    - ``references.json`` — scope/footprint sentinel.
    - ``tasks/TASK-*.json`` — one non-empty task file (glob-counted).
    - ``artifacts/findings/*.jsonl`` — one non-empty findings file.
    - ``logs/script-execution.log`` — non-empty plan-scoped script log.
    - ``logs/work.log`` — carries a ``[DISPATCH] role=phase-N`` marker iff
      ``dispatch_marker`` is True.

    Returns a ``PlanInputs`` bound to the materialised ``plan_dir``;
    ``check_input_integrity`` reads only ``plan_dir`` / ``plan_id`` from disk, so
    the instance is constructed directly rather than parsed.
    """
    import json as _json

    if phase_tokens is None:
        phase_tokens = {'5-execute': 10_000, '6-finalize': 5_000}
    plan_dir = repo_root / '.plan' / 'temp' / 'ii-corpus' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    if has_execution:
        (plan_dir / 'execution.toon').write_text('phase_5:\n', encoding='utf-8')
    if has_metrics:
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        metrics_lines: list[str] = []
        for phase, tokens in phase_tokens.items():
            metrics_lines.append(f'[{phase}]')
            metrics_lines.append(f'  total_tokens: {tokens}')
        (plan_dir / 'work' / 'metrics.toon').write_text(
            '\n'.join(metrics_lines) + '\n', encoding='utf-8'
        )
    if has_references:
        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': []}), encoding='utf-8'
        )
    if has_tasks:
        (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text('{}', encoding='utf-8')
    if has_findings:
        (plan_dir / 'artifacts' / 'findings').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'artifacts' / 'findings' / 'f.jsonl').write_text(
            '{"id": 1}\n', encoding='utf-8'
        )
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    if has_script_log:
        (logs_dir / 'script-execution.log').write_text(
            '[2026-06-01T10:00:00Z] [INFO] call\n', encoding='utf-8'
        )
    work_lines = ['[2026-06-01T10:00:00Z] [INFO] [3befe7] work line']
    if dispatch_marker:
        work_lines.append(
            '[2026-06-01T10:00:01Z] [INFO] [3befe7] '
            '[DISPATCH] (orchestrator) role=phase-5-execute dispatched'
        )
    (logs_dir / 'work.log').write_text(
        '\n'.join(work_lines) + '\n', encoding='utf-8'
    )

    return audit.PlanInputs(plan_id=plan_id, plan_dir=plan_dir)

class TestInputIntegrityPresenceDetection:
    """``check_input_integrity`` reports a presence/health boolean (as a
    lowercase string) for every canonical input the plan dir carries."""

    def test_all_inputs_present_reports_true(self, tmp_path: Path):
        # a fully-populated plan dir
        inputs = _write_ii_plan(tmp_path, 'all-present')

        row = audit.check_input_integrity(inputs)

        # each presence flag is the string 'true'
        assert row['has_execution'] == 'true'
        assert row['has_metrics'] == 'true'
        assert row['has_references'] == 'true'
        assert row['has_tasks'] == 'true'
        assert row['has_findings'] == 'true'
        assert row['has_script_log'] == 'true'

    def test_missing_execution_manifest_reports_false(self, tmp_path: Path):
        # execution.toon omitted
        inputs = _write_ii_plan(tmp_path, 'no-exec', has_execution=False)

        row = audit.check_input_integrity(inputs)

        # only has_execution flips, the rest stay present
        assert row['has_execution'] == 'false'
        assert row['has_metrics'] == 'true'
        assert row['has_references'] == 'true'

    def test_missing_metrics_reports_false(self, tmp_path: Path):
        # work/metrics.toon omitted
        inputs = _write_ii_plan(tmp_path, 'no-metrics', has_metrics=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_metrics'] == 'false'

    def test_missing_references_reports_false(self, tmp_path: Path):
        # references.json omitted
        inputs = _write_ii_plan(tmp_path, 'no-refs', has_references=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_references'] == 'false'

    def test_empty_tasks_dir_reports_false(self, tmp_path: Path):
        # no TASK-*.json files
        inputs = _write_ii_plan(tmp_path, 'no-tasks', has_tasks=False)

        row = audit.check_input_integrity(inputs)

        # an absent (or empty) tasks dir reads as has_tasks=false
        assert row['has_tasks'] == 'false'

    def test_empty_findings_dir_reports_false(self, tmp_path: Path):
        # no *.jsonl findings files
        inputs = _write_ii_plan(tmp_path, 'no-findings', has_findings=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_findings'] == 'false'

    def test_missing_script_log_reports_false(self, tmp_path: Path):
        # no plan-scoped script-execution.log
        inputs = _write_ii_plan(tmp_path, 'no-log', has_script_log=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_script_log'] == 'false'

class TestInputIntegrityFlags:
    """The three input-health flags — ``metrics_blind``, ``incomplete_lifecycle``,
    ``missing_dispatch_markers`` — each fire on their own primitive and clear on a
    fully-recorded plan."""

    def test_clean_plan_fires_no_flags(self, tmp_path: Path):
        # every input present, non-zero data-bearing phases, dispatch
        inputs = _write_ii_plan(tmp_path, 'clean')

        row = audit.check_input_integrity(inputs)

        # all three flag cells are empty
        assert row['metrics_blind'] == ''
        assert row['incomplete_lifecycle'] == ''
        assert row['missing_dispatch_markers'] == ''

    def test_zero_token_execute_sets_metrics_blind(self, tmp_path: Path):
        # a recorded 5-execute with zero tokens (the load-bearing case)
        inputs = _write_ii_plan(
            tmp_path, 'exec-blind',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        # 5-execute is named in metrics_blind
        assert '5-execute' in row['metrics_blind']

    def test_zero_token_nonexecute_phase_sets_metrics_blind(self, tmp_path: Path):
        # a zero-token 6-finalize (data-bearing, but not the escalator)
        inputs = _write_ii_plan(
            tmp_path, 'finalize-blind',
            phase_tokens={'5-execute': 10_000, '6-finalize': 0},
        )

        row = audit.check_input_integrity(inputs)

        # 6-finalize is flagged blind; 5-execute (non-zero) is not
        assert '6-finalize' in row['metrics_blind']
        assert '5-execute' not in row['metrics_blind']

    def test_recorded_nonzero_phase_not_metrics_blind(self, tmp_path: Path):
        # both data-bearing phases carry tokens
        inputs = _write_ii_plan(
            tmp_path, 'no-blind',
            phase_tokens={'5-execute': 1, '6-finalize': 1},
        )

        row = audit.check_input_integrity(inputs)

        # no phase is blind
        assert row['metrics_blind'] == ''

    def test_missing_execute_phase_sets_incomplete_lifecycle(self, tmp_path: Path):
        # 5-execute section never recorded (only 6-finalize)
        inputs = _write_ii_plan(
            tmp_path, 'no-execute-phase',
            phase_tokens={'6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        # incomplete_lifecycle names the missing 5-execute
        assert '5-execute' in row['incomplete_lifecycle']

    def test_missing_finalize_phase_sets_incomplete_lifecycle(self, tmp_path: Path):
        # 6-finalize section never recorded (only 5-execute)
        inputs = _write_ii_plan(
            tmp_path, 'no-finalize-phase',
            phase_tokens={'5-execute': 10_000},
        )

        row = audit.check_input_integrity(inputs)

        # incomplete_lifecycle names the missing 6-finalize
        assert '6-finalize' in row['incomplete_lifecycle']

    def test_missing_dispatch_markers_flag_when_absent(self, tmp_path: Path):
        # work.log carries no [DISPATCH] role=phase-N line
        inputs = _write_ii_plan(tmp_path, 'no-dispatch', dispatch_marker=False)

        row = audit.check_input_integrity(inputs)

        # the marker-absence flag is the string 'true'
        assert row['missing_dispatch_markers'] == 'true'

    def test_dispatch_markers_present_clears_flag(self, tmp_path: Path):
        # work.log carries a [DISPATCH] role=phase-N marker
        inputs = _write_ii_plan(tmp_path, 'has-dispatch', dispatch_marker=True)

        row = audit.check_input_integrity(inputs)

        # the flag is empty
        assert row['missing_dispatch_markers'] == ''

class TestInputIntegrityDataConfidence:
    """The per-plan ``data_confidence`` bucket: ``blind`` iff the 5-execute phase
    recorded zero tokens, else ``partial`` on any other gap/defect, else
    ``fully-recorded``."""

    def test_fully_recorded_when_no_gap_or_defect(self, tmp_path: Path):
        # every input present, every flag clear
        inputs = _write_ii_plan(tmp_path, 'fr')

        row = audit.check_input_integrity(inputs)

        assert row['data_confidence'] == 'fully-recorded'

    def test_zero_token_execute_is_blind(self, tmp_path: Path):
        # the load-bearing zero-token 5-execute
        inputs = _write_ii_plan(
            tmp_path, 'blind',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        # a blind 5-execute floors every downstream number
        assert row['data_confidence'] == 'blind'

    def test_missing_input_is_partial_not_blind(self, tmp_path: Path):
        # a missing input with a healthy (non-zero) 5-execute
        inputs = _write_ii_plan(tmp_path, 'partial-input', has_references=False)

        row = audit.check_input_integrity(inputs)

        # partial: a gap, but the load-bearing phase is not blind
        assert row['data_confidence'] == 'partial'

    def test_defect_without_blind_execute_is_partial(self, tmp_path: Path):
        # incomplete lifecycle (no 6-finalize) but 5-execute recorded
        inputs = _write_ii_plan(
            tmp_path, 'partial-defect',
            phase_tokens={'5-execute': 10_000},
        )

        row = audit.check_input_integrity(inputs)

        # partial, not blind: 5-execute carries tokens
        assert row['data_confidence'] == 'partial'

    def test_missing_optional_findings_alone_stays_fully_recorded(
        self, tmp_path: Path
    ):
        # only the OPTIONAL findings artefact absent, no flag fired
        inputs = _write_ii_plan(tmp_path, 'opt-findings', has_findings=False)

        row = audit.check_input_integrity(inputs)

        # findings is not part of the any_input_missing set, so the plan
        # remains fully-recorded
        assert row['data_confidence'] == 'fully-recorded'

class TestInputIntegrityGenuinePredicate:
    """``_input_integrity_genuine`` is the D1 severity predicate: genuine iff a
    real input-health defect fired (any of the three flags)."""

    def test_any_flag_is_genuine(self):
        # each flag alone makes the row genuine
        assert audit._input_integrity_genuine(
            {'metrics_blind': '5-execute',
             'incomplete_lifecycle': '',
             'missing_dispatch_markers': ''}
        ) is True
        assert audit._input_integrity_genuine(
            {'metrics_blind': '',
             'incomplete_lifecycle': '6-finalize',
             'missing_dispatch_markers': ''}
        ) is True
        assert audit._input_integrity_genuine(
            {'metrics_blind': '',
             'incomplete_lifecycle': '',
             'missing_dispatch_markers': 'true'}
        ) is True

    def test_no_flag_is_informational(self):
        # all flags empty => not genuine
        assert audit._input_integrity_genuine(
            {'metrics_blind': '',
             'incomplete_lifecycle': '',
             'missing_dispatch_markers': ''}
        ) is False

class TestInputIntegrityEmitBlock:
    """``emit_input_integrity_block`` renders the corpus ``data_confidence``
    summary, the per-plan rows with the uniform D1 ``severity`` column, and the
    check is wired into the registries (in ``CHECK_NAMES``, NOT ``CROSS_PLAN``)."""

    def test_check_registered_in_check_names_only(self):
        # dispatchable but deliberately per-plan
        assert 'input-integrity' in audit.CHECK_NAMES
        assert 'input-integrity' not in audit.CROSS_PLAN_CHECKS

    def test_block_header_and_corpus_confidence_summary(self, tmp_path: Path):
        # three plans: fully-recorded, partial, blind
        rows = [
            audit.check_input_integrity(_write_ii_plan(tmp_path, 'p-fr')),
            audit.check_input_integrity(
                _write_ii_plan(tmp_path, 'p-partial', has_references=False)
            ),
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'p-blind',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            ),
        ]

        block = audit.emit_input_integrity_block(rows)

        # header + the three-bucket data_confidence tally
        assert 'check: input-integrity' in block
        assert 'status: success' in block
        assert 'plans_scanned: 3' in block
        assert 'data_confidence_fully_recorded: 1' in block
        assert 'data_confidence_partial: 1' in block
        assert 'data_confidence_blind: 1' in block

    def test_block_lists_blind_plan_ids(self, tmp_path: Path):
        # two blind plans (zero-token 5-execute) + one healthy
        rows = [
            audit.check_input_integrity(_write_ii_plan(tmp_path, 'healthy')),
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'blind-b',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            ),
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'blind-a',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            ),
        ]

        block = audit.emit_input_integrity_block(rows)

        # blind plan ids are sorted, semicolon-joined, healthy excluded
        assert 'blind_plan_ids: blind-a;blind-b' in block

    def test_block_header_declares_severity_column(self, tmp_path: Path):
        # one plan
        rows = [audit.check_input_integrity(_write_ii_plan(tmp_path, 'one'))]

        block = audit.emit_input_integrity_block(rows)

        # the rows[] header carries the full column set ending in severity
        assert (
            'rows[1]{plan_id,has_execution,has_metrics,has_references,'
            'has_tasks,has_findings,has_script_log,metrics_blind,'
            'incomplete_lifecycle,missing_dispatch_markers,data_confidence,'
            'severity}:'
        ) in block

    def test_genuine_row_renders_genuine_severity_cell(self, tmp_path: Path):
        # a blind plan (zero-token 5-execute) is a genuine defect
        rows = [
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'g',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            )
        ]

        block = audit.emit_input_integrity_block(rows)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('g,')
        )

        # the flagged row ends on the genuine cell + count reflects it
        assert row_line.endswith(',genuine')
        assert 'genuine_signal_count: 1' in block

    def test_clean_row_renders_informational_severity_cell(self, tmp_path: Path):
        # a fully-recorded plan has no flag => informational
        rows = [audit.check_input_integrity(_write_ii_plan(tmp_path, 'i'))]

        block = audit.emit_input_integrity_block(rows)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('i,')
        )

        # clean row stamps informational, genuine count is zero
        assert row_line.endswith(',informational')
        assert 'genuine_signal_count: 0' in block

    def test_empty_corpus_yields_zero_counts(self):
        # no plans scanned
        block = audit.emit_input_integrity_block([])

        # all-zero buckets, empty blind list, zero genuine
        assert 'plans_scanned: 0' in block
        assert 'data_confidence_fully_recorded: 0' in block
        assert 'data_confidence_partial: 0' in block
        assert 'data_confidence_blind: 0' in block
        assert 'genuine_signal_count: 0' in block

# =============================================================================
# D8 — cross-check-synthesis facet-completeness critic
# =============================================================================
#
# ``cross_check_synthesis`` reads the OTHER checks' RETAINED structured results
# (never their emitted strings) and computes five cross-facet couplings. The
# helpers below build the structured per-check result shapes the critic consumes:
#
#   token-efficiency-trend        -> {regression: str}
#   input-integrity               -> [{plan_id, data_confidence}]
#   sequence-and-build-minimality -> {rows: [{plan_id, flags:[...]}]}
#   token-economics               -> {rows: [{plan_id, flags:[...], tokens_per_file}]}
#   metrics                       -> [{plan_id, disproportionate_token}]
#   quality-chain                 -> {rows: [{plan_id, flags:[...]}]}
#   recurring-pattern-detector    -> {rows: [{signature}]}
#   global-log-analysis           -> {error_count}
#   quality-verification-report   -> [{unfiled_lessons}]
#   scope-estimate-accuracy       -> [{plan_id, mismatch}]
#   task-count-efficiency         -> [{plan_id, outlier}]

def _flag_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap per-plan ``{plan_id, flags}`` rows in the cross-plan result shape."""
    return {'rows': rows}

def _coupling_row(result: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the single coupling row matching ``name`` from a synthesis result."""
    return next(r for r in result['rows'] if r['coupling'] == name)

class TestCrossCheckSynthesisFlaggedPlansHelper:
    """``_syn_flagged_plans`` collects plan ids whose flags match a predicate;
    ``_syn_build_walltime_outlier_plans`` collects the build-wall-clock upper half."""

    def test_matching_flag_collected(self):
        # two plans, only one carries a build_churn flag
        result = _flag_result(
            [
                {'plan_id': 'p-churn', 'flags': ['build_churn:3']},
                {'plan_id': 'p-clean', 'flags': []},
            ]
        )

        matched = audit._syn_flagged_plans(
            result, lambda f: f.startswith('build_churn')
        )

        # only the churning plan is collected
        assert matched == {'p-churn'}

    def test_malformed_result_yields_empty_set(self):
        # a non-dict result is best-effort tolerated
        matched = audit._syn_flagged_plans(None, lambda f: True)

        # empty set, no raise
        assert matched == set()

    def test_build_walltime_outlier_plans_collected(self):
        # three build-running plans; the upper half (>= median total_build_seconds)
        result = _flag_result(
            [
                {'plan_id': 'p-hi', 'flags': [], 'total_build_seconds': 900},
                {'plan_id': 'p-mid', 'flags': [], 'total_build_seconds': 450},
                {'plan_id': 'p-lo', 'flags': [], 'total_build_seconds': 50},
            ]
        )

        plans = audit._syn_build_walltime_outlier_plans(result)

        # median of [50,450,900] = 450; plans >= 450 are the outliers
        assert plans == {'p-hi', 'p-mid'}

    def test_build_walltime_excludes_zero_build_plans(self):
        # a plan that ran no builds (0 seconds) cannot be a wall-clock outlier
        result = _flag_result(
            [
                {'plan_id': 'p-build', 'flags': [], 'total_build_seconds': 300},
                {'plan_id': 'p-nobuild', 'flags': [], 'total_build_seconds': 0},
            ]
        )

        plans = audit._syn_build_walltime_outlier_plans(result)

        # only the build-running plan; the zero-build plan is excluded entirely
        assert plans == {'p-build'}

    def test_build_walltime_non_dict_yields_empty_set(self):
        # best-effort on a non-dict input
        assert audit._syn_build_walltime_outlier_plans(None) == set()

class TestCrossCheckSynthesisCouplingA:
    """Coupling (a) trend_empty_untrustworthy: empty token-trend regression
    co-occurring with at least one blind-execute plan (input-integrity)."""

    def test_fires_on_empty_trend_with_blind_plan(self):
        # regression empty AND a blind input-integrity plan
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'trend_empty_untrustworthy')

        # fired, detail names the blind plan
        assert row['fired'] is True
        assert 'p-blind' in row['detail']

    def test_does_not_fire_when_regression_present(self):
        # a non-empty regression means the trend IS trustworthy
        all_results = {
            'token-efficiency-trend': {'regression': '12% rise'},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'trend_empty_untrustworthy')

        # not fired
        assert row['fired'] is False

    def test_does_not_fire_without_blind_plan(self):
        # empty regression but no blind-execute plan
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-ok', 'data_confidence': 'fully_recorded'},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'trend_empty_untrustworthy')

        # not fired
        assert row['fired'] is False

class TestCrossCheckSynthesisCouplingB:
    """Coupling (b) churn_explains_walltime: a plan flagged non_minimal_build /
    build_churn whose build WALL-CLOCK (total_build_seconds) is in the corpus upper
    half. It correlates churn against wall-clock — NOT against token metrics, which
    cannot see build cost (cache_read/cache_creation are excluded from total_tokens)."""

    def test_fires_on_churn_with_high_walltime(self):
        # a churning plan whose build wall-clock is at/above the corpus median
        all_results = {
            'sequence-and-build-minimality': _flag_result(
                [
                    {'plan_id': 'p-hi', 'flags': ['non_minimal_build:2'], 'total_build_seconds': 800},
                    {'plan_id': 'p-lo', 'flags': ['build_churn:3'], 'total_build_seconds': 100},
                ]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'churn_explains_walltime')

        # median of [100,800]=450; only p-hi (800>=450) is both churning AND upper-half
        assert row['fired'] is True
        assert 'p-hi' in row['detail']
        assert 'p-lo' not in row['detail']

    def test_fires_on_build_churn_flag_specifically(self):
        # the build_churn flag (not just non_minimal_build) also qualifies
        all_results = {
            'sequence-and-build-minimality': _flag_result(
                [
                    {'plan_id': 'p-churn', 'flags': ['build_churn:6'], 'total_build_seconds': 600},
                    {'plan_id': 'p-clean', 'flags': [], 'total_build_seconds': 200},
                ]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'churn_explains_walltime')

        # median [200,600]=400; p-churn (600>=400) churns AND is upper-half
        assert row['fired'] is True
        assert 'p-churn' in row['detail']

    def test_does_not_fire_when_churn_has_low_walltime(self):
        # churn on a plan whose build wall-clock is BELOW the corpus median
        all_results = {
            'sequence-and-build-minimality': _flag_result(
                [
                    {'plan_id': 'p-churn-lo', 'flags': ['build_churn:5'], 'total_build_seconds': 50},
                    {'plan_id': 'p-clean-hi', 'flags': [], 'total_build_seconds': 900},
                ]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'churn_explains_walltime')

        # median [50,900]=475; the only upper-half plan (p-clean-hi) does not churn
        assert row['fired'] is False

class TestCrossCheckSynthesisCouplingC:
    """Coupling (c) qgate_gap_chain: a plan flagged no_qgate6 / auto_review_only
    (quality-chain) AND (ci_rerun (sequence) OR finalize_heavy (economics))."""

    def test_fires_on_qgate_gap_plus_ci_rerun(self):
        # qgate gap intersects with a ci_rerun flag
        all_results = {
            'quality-chain': _flag_result(
                [{'plan_id': 'p-z', 'flags': ['no_qgate6']}]
            ),
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-z', 'flags': ['ci_rerun:2']}]
            ),
            'token-economics': _flag_result([]),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'qgate_gap_chain')

        # fired via the ci_rerun arm
        assert row['fired'] is True
        assert 'p-z' in row['detail']

    def test_fires_on_qgate_gap_plus_finalize_heavy(self):
        # auto_review_only intersects with finalize_heavy
        all_results = {
            'quality-chain': _flag_result(
                [{'plan_id': 'p-w', 'flags': ['auto_review_only']}]
            ),
            'sequence-and-build-minimality': _flag_result([]),
            'token-economics': _flag_result(
                [{'plan_id': 'p-w', 'flags': ['finalize_heavy']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'qgate_gap_chain')

        # fired via the finalize_heavy arm
        assert row['fired'] is True
        assert 'p-w' in row['detail']

    def test_does_not_fire_without_downstream_signal(self):
        # qgate gap present but no ci_rerun / finalize_heavy anywhere
        all_results = {
            'quality-chain': _flag_result(
                [{'plan_id': 'p-q', 'flags': ['no_qgate6']}]
            ),
            'sequence-and-build-minimality': _flag_result([]),
            'token-economics': _flag_result([]),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'qgate_gap_chain')

        # no downstream cost signal => not fired
        assert row['fired'] is False

class TestCrossCheckSynthesisCouplingD:
    """Coupling (d) argparse_signature_cluster: argparse-shaped recurring
    signatures AND global-log errors AND unfiled quality-verification
    signatures — collapse-to-ONE source-keyed candidate."""

    def test_fires_when_all_three_facets_present(self):
        # an argparse signature, a global-log error, an unfiled lesson
        all_results = {
            'recurring-pattern-detector': {
                'rows': [{'signature': 'argparse: invalid choice foo'}]
            },
            'global-log-analysis': {'error_count': 3},
            'quality-verification-report': [{'unfiled_lessons': 1}],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'argparse_signature_cluster')

        # fired, caveat names the single-source collapse
        assert row['fired'] is True
        assert 'collapse to ONE' in row['detail']

    def test_does_not_fire_without_global_errors(self):
        # argparse signature + unfiled lesson but ZERO global errors
        all_results = {
            'recurring-pattern-detector': {
                'rows': [{'signature': 'argparse: unrecognized argument'}]
            },
            'global-log-analysis': {'error_count': 0},
            'quality-verification-report': [{'unfiled_lessons': 2}],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'argparse_signature_cluster')

        # missing one of the three facets => not fired
        assert row['fired'] is False

    def test_does_not_fire_when_signature_not_argparse_shaped(self):
        # a non-argparse signature does not match _SYN_ARGPARSE_SIG_RE
        all_results = {
            'recurring-pattern-detector': {
                'rows': [{'signature': 'flaky network timeout'}]
            },
            'global-log-analysis': {'error_count': 5},
            'quality-verification-report': [{'unfiled_lessons': 1}],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'argparse_signature_cluster')

        # no argparse-shaped signature => not fired
        assert row['fired'] is False

class TestCrossCheckSynthesisCouplingE:
    """Coupling (e) scope_underestimate_cost: a scope-estimate mismatch AND
    (high tokens/file >= corpus median OR a task-count outlier)."""

    def test_fires_on_scope_mismatch_plus_high_tpf(self):
        # p-hi mismatches scope AND sits at/above the tpf median
        all_results = {
            'scope-estimate-accuracy': [
                {'plan_id': 'p-hi', 'mismatch': True},
            ],
            'token-economics': _flag_result(
                [
                    {'plan_id': 'p-hi', 'flags': [], 'tokens_per_file': 9000},
                    {'plan_id': 'p-lo', 'flags': [], 'tokens_per_file': 1000},
                ]
            ),
            'task-count-efficiency': [],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'scope_underestimate_cost')

        # fired via the high-tokens/file arm
        assert row['fired'] is True
        assert 'p-hi' in row['detail']

    def test_fires_on_scope_mismatch_plus_task_outlier(self):
        # mismatch intersects with a task-count outlier
        all_results = {
            'scope-estimate-accuracy': [
                {'plan_id': 'p-out', 'mismatch': True},
            ],
            'token-economics': _flag_result([]),
            'task-count-efficiency': [
                {'plan_id': 'p-out', 'outlier': True},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'scope_underestimate_cost')

        # fired via the task-outlier arm
        assert row['fired'] is True
        assert 'p-out' in row['detail']

    def test_does_not_fire_without_cost_signal(self):
        # scope mismatch but median guard suppresses tpf, no outlier
        all_results = {
            'scope-estimate-accuracy': [
                {'plan_id': 'p-m', 'mismatch': True},
            ],
            'token-economics': _flag_result([]),
            'task-count-efficiency': [],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'scope_underestimate_cost')

        # no cost signal => not fired
        assert row['fired'] is False

class TestCrossCheckSynthesisGenuinePredicate:
    """``_syn_genuine`` maps a fired coupling to a genuine (actionable) signal."""

    def test_fired_row_is_genuine(self):
        # fired => genuine
        assert audit._syn_genuine({'fired': True}) is True

    def test_unfired_row_is_informational(self):
        # not fired => informational
        assert audit._syn_genuine({'fired': False}) is False

class TestCrossCheckSynthesisEmitBlock:
    """``emit_cross_check_synthesis_block`` renders the header counts, the D1
    severity column, and is wired into both the CHECK_NAMES and CROSS_PLAN
    registries (runs LAST)."""

    def test_check_registered_as_cross_plan(self):
        # dispatchable AND cross-plan
        assert 'cross-check-synthesis' in audit.CHECK_NAMES
        assert 'cross-check-synthesis' in audit.CROSS_PLAN_CHECKS

    def test_synthesis_runs_last_in_check_names(self):
        # synthesis must be the final dispatch entry so
        # every upstream result is retained before it reads them
        assert audit.CHECK_NAMES[-1] == 'cross-check-synthesis'

    def test_block_header_and_severity_column(self):
        # one fired coupling (a) over an otherwise-empty corpus
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }
        result = audit.cross_check_synthesis(all_results)

        block = audit.emit_cross_check_synthesis_block(result)

        # header counts + the rows[] column set ends in severity
        assert 'check: cross-check-synthesis' in block
        assert 'status: success' in block
        assert 'couplings_evaluated: 6' in block
        assert 'couplings_fired: 1' in block
        assert 'genuine_signal_count: 1' in block
        assert 'rows[6]{coupling,fired,caveat,detail,severity}:' in block

    def test_fired_coupling_renders_genuine_cell(self):
        # coupling (a) fires
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }
        result = audit.cross_check_synthesis(all_results)

        block = audit.emit_cross_check_synthesis_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('trend_empty_untrustworthy,')
        )

        # fired row carries true + a trailing genuine severity cell
        assert row_line.startswith('trend_empty_untrustworthy,true,')
        assert row_line.endswith(',genuine')

    def test_unfired_coupling_renders_informational_cell(self):
        # empty corpus: no coupling fires
        result = audit.cross_check_synthesis({})

        block = audit.emit_cross_check_synthesis_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('trend_empty_untrustworthy,')
        )

        # unfired row carries false + a trailing informational cell
        assert row_line.startswith('trend_empty_untrustworthy,false,')
        assert row_line.endswith(',informational')
        assert 'couplings_fired: 0' in block
        assert 'genuine_signal_count: 0' in block

    def test_empty_results_evaluate_all_couplings(self):
        # no upstream results at all (best-effort degradation)
        result = audit.cross_check_synthesis({})
        block = audit.emit_cross_check_synthesis_block(result)

        # every coupling still evaluated, none fired
        assert result['couplings_evaluated'] == 6
        assert result['couplings_fired'] == 0
        assert 'couplings_evaluated: 6' in block

# =============================================================================
# D9 — existing-check backfill (current-baseline coverage gap)
#
# The classes below close the dedicated-coverage gap for the seven pre-existing
# checks that, before this backfill, were either entirely untested
# (check_quality_verification, check_scope_estimate, check_pr_merge_velocity,
# check_task_count, cross_recurring_pattern) or exercised only on the
# retrospective-exclusion negative-control path (check_metrics, cross_token_trend).
# Each class asserts against the check's genuine flagging logic and edge cases
# read straight from scripts/audit.py — never the emit-time severity column,
# which the TestEmit*Severity classes above already own.
# =============================================================================

def _scope_inputs(
    *,
    scope_estimate: str | None,
    modified: int = 0,
    affected: int = 0,
) -> Any:
    """Build a PlanInputs carrying only the scope-estimate-relevant counts.

    ``check_scope_estimate`` reads ``scope_estimate`` plus the modified/affected
    file counts already collected onto ``PlanInputs`` (it does NOT re-read disk),
    so the instance is constructed directly rather than materialised.
    """
    return audit.PlanInputs(
        plan_id='scope-plan',
        plan_dir=PROJECT_ROOT / '.plan' / 'temp' / 'nonexistent-scope-plan',
        scope_estimate=scope_estimate,
        modified_files_count=modified,
        affected_files_count=affected,
    )

class TestCheckScopeEstimate:
    """``check_scope_estimate`` flags a declared scope band the actual touched
    file count falls outside, prefers modified over affected counts, and tolerates
    an unbanded / absent declaration."""

    def test_in_band_surgical_not_flagged(self):
        # surgical band is [1, 3]; actual 2 sits inside.
        inputs = _scope_inputs(scope_estimate='surgical', modified=2)

        result = audit.check_scope_estimate(inputs)

        assert result['mismatch'] == ''
        assert result['declared_scope'] == 'surgical'
        assert result['actual_file_count'] == 2

    def test_surgical_overshoot_flagged(self):
        # actual 9 exceeds the surgical [1, 3] upper bound.
        inputs = _scope_inputs(scope_estimate='surgical', modified=9)

        result = audit.check_scope_estimate(inputs)

        # the mismatch names the band and the actual count
        assert 'declared=surgical' in result['mismatch']
        assert 'actual=9' in result['mismatch']

    def test_below_band_low_bound_flagged(self):
        # single_module band is [1, 15]; actual 0 sits below the low bound.
        inputs = _scope_inputs(scope_estimate='single_module', modified=0, affected=0)

        result = audit.check_scope_estimate(inputs)

        # actual 0 < low 1 → flagged
        assert 'declared=single_module' in result['mismatch']
        assert 'actual=0' in result['mismatch']

    def test_unbounded_upper_band_never_overshoots(self):
        # multi_module band is [5, None]; a large actual cannot overshoot.
        inputs = _scope_inputs(scope_estimate='multi_module', modified=500)

        result = audit.check_scope_estimate(inputs)

        # no upper bound, actual >= low → not flagged
        assert result['mismatch'] == ''

    def test_modified_count_preferred_over_affected(self):
        # modified (post-execution truth) 2 wins over affected 99.
        inputs = _scope_inputs(scope_estimate='surgical', modified=2, affected=99)

        result = audit.check_scope_estimate(inputs)

        # the in-band modified count is used, not the out-of-band affected
        assert result['actual_file_count'] == 2
        assert result['mismatch'] == ''

    def test_affected_used_when_modified_zero(self):
        # modified 0 falls back to affected 7 (overshoots surgical [1, 3]).
        inputs = _scope_inputs(scope_estimate='surgical', modified=0, affected=7)

        result = audit.check_scope_estimate(inputs)

        # fallback count is used and flags the overshoot
        assert result['actual_file_count'] == 7
        assert 'actual=7' in result['mismatch']

    def test_unmapped_scope_string_flagged(self):
        # a declared scope with no band mapping in SCOPE_FILE_BANDS.
        inputs = _scope_inputs(scope_estimate='gigantic', modified=4)

        result = audit.check_scope_estimate(inputs)

        # the no-band-mapping branch fires
        assert 'no band mapping' in result['mismatch']
        assert result['declared_scope'] == 'gigantic'

    def test_absent_scope_never_flagged(self):
        # no declared scope at all.
        inputs = _scope_inputs(scope_estimate=None, modified=42)

        result = audit.check_scope_estimate(inputs)

        # empty declared scope short-circuits both branches
        assert result['declared_scope'] == ''
        assert result['mismatch'] == ''

def _write_task_count_plan(
    repo_root: Path,
    plan_id: str,
    *,
    task_count: int,
    deliverables: list[Any] | None = None,
    task_deliverable_ids: list[Any] | None = None,
) -> Any:
    """Materialise a plan dir carrying ``tasks/TASK-*.json`` + ``references.json``.

    ``check_task_count`` globs ``tasks/TASK-*.json`` and resolves the deliverable
    count via ``_deliverable_count`` (``references.json::deliverables`` first, then
    the distinct ``deliverable`` ids referenced by tasks). ``deliverables`` seeds
    the explicit list; ``task_deliverable_ids`` seeds the per-task fallback ids.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'tc-corpus' / plan_id
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for n in range(1, task_count + 1):
        body: dict[str, Any] = {}
        if task_deliverable_ids is not None and n - 1 < len(task_deliverable_ids):
            body['deliverable'] = task_deliverable_ids[n - 1]
        (tasks_dir / f'TASK-{n:03d}.json').write_text(
            _json.dumps(body), encoding='utf-8'
        )
    refs: dict[str, Any] = {}
    if deliverables is not None:
        refs['deliverables'] = deliverables
    (plan_dir / 'references.json').write_text(_json.dumps(refs), encoding='utf-8')
    return audit.collect_inputs(plan_dir)

class TestCheckTaskCount:
    """``check_task_count`` flags under- and over-decomposition relative to the
    deliverable count, derives deliverables from references or the task fallback,
    and stays silent when no deliverables exist."""

    def test_balanced_ratio_not_flagged(self, tmp_path: Path):
        # 4 tasks over 2 deliverables → ratio 2.0, inside [0.5, 4.0].
        inputs = _write_task_count_plan(
            tmp_path, 'balanced', task_count=4, deliverables=['d1', 'd2']
        )

        result = audit.check_task_count(inputs)

        assert result['task_count'] == 4
        assert result['deliverable_count'] == 2
        assert result['outlier'] == ''

    def test_under_decomposition_flagged(self, tmp_path: Path):
        # 2 tasks over 8 deliverables → ratio 0.25 < 0.5.
        inputs = _write_task_count_plan(
            tmp_path,
            'under',
            task_count=2,
            deliverables=[f'd{i}' for i in range(8)],
        )

        result = audit.check_task_count(inputs)

        assert 'under_decomposed' in result['outlier']
        assert 'ratio=0.25' in result['outlier']

    def test_over_decomposition_flagged(self, tmp_path: Path):
        # 10 tasks over 2 deliverables → ratio 5.0 > 4.0.
        inputs = _write_task_count_plan(
            tmp_path, 'over', task_count=10, deliverables=['d1', 'd2']
        )

        result = audit.check_task_count(inputs)

        assert 'over_decomposed' in result['outlier']
        assert 'ratio=5.00' in result['outlier']

    def test_deliverables_derived_from_tasks_when_absent_in_references(
        self, tmp_path: Path
    ):
        # references.json has no deliverables list; the per-task
        # ``deliverable`` ids supply the distinct-count fallback (2 distinct ids).
        inputs = _write_task_count_plan(
            tmp_path,
            'task-fallback',
            task_count=2,
            deliverables=None,
            task_deliverable_ids=[7, 9],
        )

        result = audit.check_task_count(inputs)

        # distinct ids {7, 9} → 2 deliverables, ratio 1.0, not flagged
        assert result['deliverable_count'] == 2
        assert result['outlier'] == ''

    def test_zero_deliverables_short_circuits_no_flag(self, tmp_path: Path):
        # tasks present but no deliverables list and no task ids.
        inputs = _write_task_count_plan(
            tmp_path,
            'no-deliverables',
            task_count=3,
            deliverables=None,
            task_deliverable_ids=None,
        )

        result = audit.check_task_count(inputs)

        # deliverable_count 0 → ratio guard skipped, never flagged
        assert result['deliverable_count'] == 0
        assert result['outlier'] == ''

    def test_no_tasks_dir_reports_zero(self, tmp_path: Path):
        # a plan dir with references.json but no tasks/ directory.
        import json as _json

        plan_dir = tmp_path / '.plan' / 'temp' / 'tc-corpus' / 'no-tasks'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'references.json').write_text(
            _json.dumps({'deliverables': ['d1']}), encoding='utf-8'
        )
        inputs = audit.collect_inputs(plan_dir)

        result = audit.check_task_count(inputs)

        # missing tasks/ → 0 tasks; ratio 0.0 < 0.5 → under_decomposed
        assert result['task_count'] == 0
        assert 'under_decomposed' in result['outlier']

def _write_velocity_plan(
    repo_root: Path,
    plan_id: str,
    runs: list[tuple[str, str | None, str | None]],
) -> Any:
    """Materialise a plan dir with ``artifacts/ci-runs/{run}/manifest.toon`` files.

    ``runs`` is a list of ``(run_subdir, pr_number, fetched_at)`` tuples; each
    tuple writes one manifest. A ``None`` pr_number / fetched_at omits that scalar
    line. ``check_pr_merge_velocity`` takes the min fetched_at as PR-open and the
    max as merge, computing the open-to-merge elapsed hours.
    """
    plan_dir = repo_root / '.plan' / 'temp' / 'velocity-corpus' / plan_id
    ci_runs = plan_dir / 'artifacts' / 'ci-runs'
    for run_subdir, pr_number, fetched_at in runs:
        run_dir = ci_runs / run_subdir
        run_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        if pr_number is not None:
            lines.append(f'pr_number: {pr_number}')
        if fetched_at is not None:
            lines.append(f'fetched_at: {fetched_at}')
        (run_dir / 'manifest.toon').write_text(
            '\n'.join(lines) + '\n', encoding='utf-8'
        )
    return audit.collect_inputs(plan_dir)

class TestCheckPrMergeVelocity:
    """``check_pr_merge_velocity`` computes open-to-merge elapsed hours from the
    ci-runs manifests and flags review cycles over the 24h threshold."""

    def test_no_ci_runs_marks_inapplicable(self, tmp_path: Path):
        # a plan dir with no artifacts/ci-runs at all.
        plan_dir = tmp_path / '.plan' / 'temp' / 'velocity-corpus' / 'no-runs'
        plan_dir.mkdir(parents=True, exist_ok=True)
        inputs = audit.collect_inputs(plan_dir)

        result = audit.check_pr_merge_velocity(inputs)

        # no manifests → inapplicable, never flagged
        assert result['applicable'] == 'false'
        assert result['flagged'] == ''
        assert result['elapsed_hours'] == ''

    def test_fast_review_cycle_not_flagged(self, tmp_path: Path):
        # open 10:00, merge 12:00 same day → 2.0h, under the 24h ceiling.
        inputs = _write_velocity_plan(
            tmp_path,
            'fast',
            [
                ('run-1', '101', '2026-05-30T10:00:00Z'),
                ('run-2', '101', '2026-05-30T12:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        assert result['applicable'] == 'true'
        assert result['pr_number'] == '101'
        assert result['elapsed_hours'] == '2.0'
        assert result['flagged'] == ''

    def test_slow_review_cycle_flagged(self, tmp_path: Path):
        # open 09:00 on the 28th, merge 09:00 on the 30th → 48.0h > 24h.
        inputs = _write_velocity_plan(
            tmp_path,
            'slow',
            [
                ('run-1', '202', '2026-05-28T09:00:00Z'),
                ('run-2', '202', '2026-05-30T09:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # 48h exceeds the 24h ceiling
        assert result['elapsed_hours'] == '48.0'
        assert result['flagged'] == 'true'

    def test_boundary_exactly_at_threshold_not_flagged(self, tmp_path: Path):
        # exactly 24.0h elapsed; the flag is a strict ``>`` comparison.
        inputs = _write_velocity_plan(
            tmp_path,
            'boundary',
            [
                ('run-1', '303', '2026-05-29T00:00:00Z'),
                ('run-2', '303', '2026-05-30T00:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # 24.0h is NOT > 24.0 → not flagged
        assert result['elapsed_hours'] == '24.0'
        assert result['flagged'] == ''

    def test_missing_pr_number_marks_inapplicable(self, tmp_path: Path):
        # manifests carry timestamps but no pr_number scalar.
        inputs = _write_velocity_plan(
            tmp_path,
            'no-pr',
            [
                ('run-1', None, '2026-05-28T09:00:00Z'),
                ('run-2', None, '2026-05-30T09:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # without a pr_number the check is inapplicable
        assert result['applicable'] == 'false'
        assert result['pr_number'] == ''

    def test_min_and_max_span_across_three_manifests(self, tmp_path: Path):
        # three runs; open is the earliest, merge the latest fetched_at.
        inputs = _write_velocity_plan(
            tmp_path,
            'span',
            [
                ('run-1', '404', '2026-05-30T08:00:00Z'),
                ('run-2', '404', '2026-05-30T20:00:00Z'),
                ('run-3', '404', '2026-05-30T14:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # 08:00 → 20:00 = 12.0h, under the ceiling
        assert result['elapsed_hours'] == '12.0'
        assert result['flagged'] == ''

def _write_qv_plan(
    repo_root: Path,
    plan_id: str,
    *,
    report_md: str | None = None,
    findings_by_file: dict[str, list[dict[str, Any]]] | None = None,
) -> Any:
    """Materialise a plan carrying ``quality-verification-report.md`` and/or
    ``artifacts/findings/*.jsonl``.

    ``report_md`` is written verbatim as the report body (the check mines its
    ```json fenced blocks for ``findings`` / ``proposed_lessons``).
    ``findings_by_file`` adds JSONL findings (each list entry one line), whose
    count rolls into ``findings_present``.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'qv-corpus' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    if report_md is not None:
        (plan_dir / 'quality-verification-report.md').write_text(
            report_md, encoding='utf-8'
        )
    if findings_by_file is not None:
        findings_dir = plan_dir / 'artifacts' / 'findings'
        findings_dir.mkdir(parents=True, exist_ok=True)
        for fname, records in findings_by_file.items():
            lines = '\n'.join(_json.dumps(r) for r in records) + '\n'
            (findings_dir / fname).write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)

class TestCheckQualityVerification:
    """``check_quality_verification`` mines the report's JSON blocks for findings
    and proposed lessons, sums JSONL findings, and cross-checks proposed lessons
    against the supplied lessons-corpus signatures to surface the unfiled set."""

    def test_unfiled_lesson_surfaced(self, tmp_path: Path):
        # one proposed lesson whose title is absent from the corpus.
        report = (
            '# Quality Verification\n\n'
            '```json\n'
            '{"findings": [{"id": 1}], '
            '"proposed_lessons": [{"title": "Brand New Signature"}]}\n'
            '```\n'
        )
        inputs = _write_qv_plan(tmp_path, 'unfiled', report_md=report)

        # empty corpus → the proposed lesson is unfiled
        result = audit.check_quality_verification(inputs, [])

        assert result['findings_present'] == 1
        assert result['proposed_lessons'] == 1
        assert result['unfiled_lessons'] == 1
        assert result['unfiled_signatures'] == ['Brand New Signature']

    def test_filed_lesson_excluded_from_unfiled(self, tmp_path: Path):
        # the proposed lesson title matches a corpus signature
        # (substring match is enough per ``_signature_filed``).
        report = (
            '```json\n'
            '{"proposed_lessons": [{"title": "Argparse Rejection Drift"}]}\n'
            '```\n'
        )
        inputs = _write_qv_plan(tmp_path, 'filed', report_md=report)

        # corpus already carries a covering signature
        result = audit.check_quality_verification(
            inputs, ['argparse rejection drift across phase skills']
        )

        # proposed but filed → zero unfiled
        assert result['proposed_lessons'] == 1
        assert result['unfiled_lessons'] == 0
        assert result['unfiled_signatures'] == []

    def test_jsonl_findings_rolled_into_count(self, tmp_path: Path):
        # no report; two JSONL findings files contribute to the count.
        inputs = _write_qv_plan(
            tmp_path,
            'jsonl',
            findings_by_file={
                'test-failure.jsonl': [{'id': 1}, {'id': 2}],
                'pr-comment.jsonl': [{'id': 3}],
            },
        )

        result = audit.check_quality_verification(inputs, [])

        # 2 + 1 JSONL findings, no proposed lessons
        assert result['findings_present'] == 3
        assert result['proposed_lessons'] == 0
        assert result['unfiled_lessons'] == 0

    def test_report_and_jsonl_findings_combine(self, tmp_path: Path):
        # report findings AND a JSONL findings file both count.
        report = '```json\n{"findings": [{"id": 1}, {"id": 2}]}\n```\n'
        inputs = _write_qv_plan(
            tmp_path,
            'combined',
            report_md=report,
            findings_by_file={'build-error.jsonl': [{'id': 9}]},
        )

        result = audit.check_quality_verification(inputs, [])

        # 2 report + 1 JSONL = 3
        assert result['findings_present'] == 3

    def test_lessons_key_alias_and_bare_string_lessons(self, tmp_path: Path):
        # the alternate ``lessons`` key plus a bare-string lesson entry
        # (both supported by the proposed-lesson extraction).
        report = (
            '```json\n'
            '{"lessons": ["Bare String Lesson", {"signature": "Dict Lesson"}]}\n'
            '```\n'
        )
        inputs = _write_qv_plan(tmp_path, 'alias', report_md=report)

        result = audit.check_quality_verification(inputs, [])

        # both forms captured as proposed lessons
        assert result['proposed_lessons'] == 2
        assert set(result['unfiled_signatures']) == {'Bare String Lesson', 'Dict Lesson'}

    def test_missing_report_yields_empty_counts(self, tmp_path: Path):
        # a plan dir with neither report nor findings.
        plan_dir = tmp_path / '.plan' / 'temp' / 'qv-corpus' / 'empty'
        plan_dir.mkdir(parents=True, exist_ok=True)
        inputs = audit.collect_inputs(plan_dir)

        result = audit.check_quality_verification(inputs, [])

        # no inputs → all-zero, nothing unfiled
        assert result['findings_present'] == 0
        assert result['proposed_lessons'] == 0
        assert result['unfiled_lessons'] == 0
        assert result['unfiled_signatures'] == []

    def test_malformed_json_block_ignored(self, tmp_path: Path):
        # a non-JSON fenced block must not raise; it is skipped.
        report = '```json\nthis is not valid json\n```\n'
        inputs = _write_qv_plan(tmp_path, 'malformed', report_md=report)

        result = audit.check_quality_verification(inputs, [])

        # best-effort skip leaves all counts at zero
        assert result['findings_present'] == 0
        assert result['proposed_lessons'] == 0

def _write_recurring_plan(
    repo_root: Path,
    plan_id: str,
    finding_titles: list[str],
) -> Any:
    """Materialise a plan whose ``artifacts/findings/findings.jsonl`` carries
    one finding per supplied title.

    ``cross_recurring_pattern`` derives each finding's signature from its
    ``title`` (or ``type``) up to the first colon, lowercased, dedupes per plan,
    and counts the distinct plans each signature appears in.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'rp-corpus' / plan_id
    findings_dir = plan_dir / 'artifacts' / 'findings'
    findings_dir.mkdir(parents=True, exist_ok=True)
    lines = '\n'.join(_json.dumps({'title': t}) for t in finding_titles) + '\n'
    (findings_dir / 'findings.jsonl').write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)

class TestCrossRecurringPattern:
    """``cross_recurring_pattern`` aggregates finding signatures across plans and
    surfaces any appearing in N>=3 distinct plans as a systemic signal."""

    def test_signature_in_three_plans_is_systemic(self, tmp_path: Path):
        # the same signature appears in exactly 3 plans (threshold).
        all_inputs = [
            _write_recurring_plan(tmp_path, f'plan-{i}', ['Argparse rejection: phase-5'])
            for i in range(3)
        ]

        result = audit.cross_recurring_pattern(all_inputs)

        # colon suffix stripped, signature lowercased, count 3
        assert result['threshold'] == 3
        assert result['systemic_count'] == 1
        row = result['rows'][0]
        assert row['signature'] == 'argparse rejection'
        assert row['occurrence_count'] == 3
        assert row['plan_ids'] == ['plan-0', 'plan-1', 'plan-2']

    def test_signature_below_threshold_not_systemic(self, tmp_path: Path):
        # a signature in only 2 plans stays below the N>=3 threshold.
        all_inputs = [
            _write_recurring_plan(tmp_path, 'plan-a', ['Worktree leak']),
            _write_recurring_plan(tmp_path, 'plan-b', ['Worktree leak']),
        ]

        result = audit.cross_recurring_pattern(all_inputs)

        # 2 < 3 → nothing systemic
        assert result['systemic_count'] == 0
        assert result['rows'] == []

    def test_duplicate_signature_within_plan_counts_once(self, tmp_path: Path):
        # one plan repeats a signature; two other plans carry it once.
        all_inputs = [
            _write_recurring_plan(
                tmp_path, 'dup', ['Flaky test: foo', 'Flaky test: bar']
            ),
            _write_recurring_plan(tmp_path, 'p2', ['Flaky test: baz']),
            _write_recurring_plan(tmp_path, 'p3', ['Flaky test: qux']),
        ]

        result = audit.cross_recurring_pattern(all_inputs)

        # per-plan dedup → 3 distinct plans, not 4 raw occurrences
        row = result['rows'][0]
        assert row['signature'] == 'flaky test'
        assert row['occurrence_count'] == 3
        assert sorted(row['plan_ids']) == ['dup', 'p2', 'p3']

    def test_rows_sorted_by_descending_occurrence(self, tmp_path: Path):
        # signature A in 4 plans, signature B in 3 plans.
        all_inputs = []
        for i in range(4):
            all_inputs.append(
                _write_recurring_plan(tmp_path, f'a-{i}', ['Alpha sig'])
            )
        for i in range(3):
            all_inputs.append(
                _write_recurring_plan(tmp_path, f'b-{i}', ['Beta sig'])
            )

        result = audit.cross_recurring_pattern(all_inputs)

        # both systemic; higher occurrence first
        assert result['systemic_count'] == 2
        assert result['rows'][0]['signature'] == 'alpha sig'
        assert result['rows'][0]['occurrence_count'] == 4
        assert result['rows'][1]['signature'] == 'beta sig'

    def test_type_field_used_when_title_absent(self, tmp_path: Path):
        # findings carry ``type`` instead of ``title``.
        import json as _json

        all_inputs = []
        for i in range(3):
            plan_dir = tmp_path / '.plan' / 'temp' / 'rp-corpus' / f't-{i}'
            findings_dir = plan_dir / 'artifacts' / 'findings'
            findings_dir.mkdir(parents=True, exist_ok=True)
            (findings_dir / 'f.jsonl').write_text(
                _json.dumps({'type': 'lint-issue'}) + '\n', encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_recurring_pattern(all_inputs)

        # ``type`` supplies the signature when ``title`` is missing
        assert result['systemic_count'] == 1
        assert result['rows'][0]['signature'] == 'lint-issue'

    def test_no_findings_dir_yields_no_systemic(self, tmp_path: Path):
        # plans with no artifacts/findings directory at all.
        all_inputs = []
        for i in range(3):
            plan_dir = tmp_path / '.plan' / 'temp' / 'rp-corpus' / f'bare-{i}'
            plan_dir.mkdir(parents=True, exist_ok=True)
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_recurring_pattern(all_inputs)

        # nothing to aggregate
        assert result['systemic_count'] == 0
        assert result['rows'] == []

# =============================================================================
# D9 — check_metrics / cross_token_trend POSITIVE-PATH backfill
#
# The TestRetrospectiveExclusion* classes above exercise these two checks ONLY on
# the retrospective-exclusion negative-control path. The two classes below add the
# genuine flagging logic each check is built to surface, independent of the
# retrospective_tokens field.
# =============================================================================

class TestMetricsCoreFlags:
    """``check_metrics`` flags disproportionate token share, incomplete (zero-token)
    phase recordings, impossible durations, and token-rate optimization outliers."""

    def test_no_metrics_reports_incomplete(self, monkeypatch):
        # no phases parsed at all.
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: [])
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # the empty-metrics sentinel row
        assert result['phases_recorded'] == 0
        assert result['incomplete_recording'] == 'true'
        assert result['anomalies'] == ['no metrics.toon recorded']

    def test_disproportionate_share_flagged(self, monkeypatch):
        # outline consumes 600/1000 = 60% (>= 45% threshold).
        phases = [
            _phase('3-outline', total_tokens=600),
            _phase('5-execute', total_tokens=400),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        assert result['disproportionate_token'] == '3-outline=60%'
        assert any('3-outline' in a for a in result['anomalies'])

    def test_zero_token_phase_flagged_incomplete(self, monkeypatch):
        # a recorded phase carrying zero tokens.
        phases = [
            _phase('5-execute', total_tokens=500),
            _phase('6-finalize', total_tokens=0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # the zero-token phase name lands in incomplete_recording
        assert result['incomplete_recording'] == '6-finalize'

    def test_worked_exceeding_wall_is_impossible(self, monkeypatch):
        # agent worked 200s but wall-clock is only 100s.
        phases = [
            _phase(
                '5-execute',
                total_tokens=500,
                duration_seconds=100.0,
                agent_duration_seconds=200.0,
            ),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # worked > wall flagged as impossible
        assert result['impossible_value'] == '5-execute:worked>100s'

    def test_negative_idle_is_impossible(self, monkeypatch):
        # a phase with a negative idle duration.
        phases = [
            _phase('5-execute', total_tokens=500, idle_duration_ms=-5.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        assert result['impossible_value'] == '5-execute:negative_idle'

    def test_token_rate_outlier_flagged(self, monkeypatch):
        # three baseline phases at ~10 tok/s plus one outlier at 100
        # tok/s (>= 3x the median non-zero ratio).
        phases = [
            _phase('2-refine', total_tokens=1000, duration_seconds=100.0),
            _phase('3-outline', total_tokens=1000, duration_seconds=100.0),
            _phase('4-plan', total_tokens=1000, duration_seconds=100.0),
            _phase('5-execute', total_tokens=1000, duration_seconds=10.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # 5-execute (100 tok/s) is the >= 3x median outlier
        assert result['optimization_signal'].startswith('5-execute:')

    def test_balanced_phases_flag_nothing(self, monkeypatch):
        # three balanced phases, all non-zero, similar rates.
        phases = [
            _phase('3-outline', total_tokens=300, duration_seconds=30.0),
            _phase('4-plan', total_tokens=350, duration_seconds=35.0),
            _phase('5-execute', total_tokens=350, duration_seconds=35.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # no anomaly fields populated
        assert result['disproportionate_token'] == ''
        assert result['incomplete_recording'] == ''
        assert result['impossible_value'] == ''
        assert result['optimization_signal'] == ''
        assert result['anomalies'] == []

class TestTokenTrendCore:
    """``cross_token_trend`` orders plans chronologically and flags a sustained
    upward trend in tokens-per-phase across the corpus."""

    def test_upward_trend_flags_regression(self, tmp_path: Path):
        # six plans (date-prefixed for chronological ordering) whose
        # tokens-per-phase climb steeply from first third to last third.
        import json as _json

        all_inputs = []
        token_totals = [1000, 1100, 1200, 4000, 4500, 5000]
        for idx, total in enumerate(token_totals):
            plan_id = f'2026-05-{idx + 10:02d}-trend'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                f'[5-execute]\n  total_tokens: {total}\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_token_trend(all_inputs)

        # first-third mean ~1000, last-third mean ~5000 → regression flagged
        assert result['plans_in_series'] == 6
        assert result['regression'] != ''
        assert 'rose' in result['regression']

    def test_flat_trend_no_regression(self, tmp_path: Path):
        # six plans all at the same tokens-per-phase.
        import json as _json

        all_inputs = []
        for idx in range(6):
            plan_id = f'2026-05-{idx + 10:02d}-flat'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                '[5-execute]\n  total_tokens: 1000\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_token_trend(all_inputs)

        # no rise → empty regression
        assert result['plans_in_series'] == 6
        assert result['regression'] == ''

    def test_fewer_than_three_plans_no_regression(self, tmp_path: Path):
        # only two plans; the regression rule needs >= 3.
        import json as _json

        all_inputs = []
        for idx, total in enumerate([1000, 9000]):
            plan_id = f'2026-05-{idx + 10:02d}-short'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                f'[5-execute]\n  total_tokens: {total}\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_token_trend(all_inputs)

        # under the 3-plan floor, regression stays empty
        assert result['plans_in_series'] == 2
        assert result['regression'] == ''

    def test_plan_without_metrics_excluded_from_series(self, tmp_path: Path):
        # one plan has no metrics.toon and must be skipped.
        import json as _json

        all_inputs = []
        # two plans WITH metrics
        for idx in range(2):
            plan_id = f'2026-05-{idx + 10:02d}-has'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                '[5-execute]\n  total_tokens: 1000\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))
        # one plan WITHOUT metrics
        bare_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / '2026-05-20-bare'
        bare_dir.mkdir(parents=True, exist_ok=True)
        (bare_dir / 'references.json').write_text(_json.dumps({}), encoding='utf-8')
        all_inputs.append(audit.collect_inputs(bare_dir))

        result = audit.cross_token_trend(all_inputs)

        # only the two metric-bearing plans land in the series
        assert result['plans_in_series'] == 2
        assert all(r['plan_id'].endswith('-has') for r in result['rows'])

# =============================================================================
# D3/D5 — task-graph-redundancy check
# =============================================================================
#
# ``check_task_graph_redundancy`` reconstructs a plan's task graph from
# ``tasks/TASK-*.json`` as adjacency over step targets + verification verbs and
# flags five redundancy signals. ``_finalize_deliverable_fanout`` stamps the
# per-run ``deliverable_fanout`` cell from the corpus median (max(3, median*2)).

_HEAVY_BUILD_CMD = (
    'python3 .plan/execute-script.py '
    'plan-marshall:build-pyproject:pyproject_build run '
    '--command-args "module-tests plan-marshall"'
)
_LIGHT_CMD = (
    'python3 .plan/execute-script.py '
    'plan-marshall:manage-tasks:manage-tasks list --plan-id p'
)

def _write_task_graph_plan(
    repo_root: Path,
    plan_id: str,
    tasks: list[dict[str, Any]],
) -> Any:
    """Materialise a plan dir with ``tasks/TASK-NNN.json`` and return PlanInputs.

    Each entry in ``tasks`` is a task dict (``number`` / ``profile`` /
    ``deliverable`` / ``steps`` / ``verification`` keys as the test needs). The
    files are written under ``{repo_root}/.plan/temp/tgr-corpus/{plan_id}/tasks``
    (never the live ``.plan/local`` tree). ``check_task_graph_redundancy`` reads
    only ``plan_dir`` from disk, so the returned instance is constructed directly.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'tgr-corpus' / plan_id
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for t in tasks:
        number = int(t['number'])
        (tasks_dir / f'TASK-{number:03d}.json').write_text(
            _json.dumps(t), encoding='utf-8'
        )
    return audit.PlanInputs(plan_id=plan_id, plan_dir=plan_dir)

def _step(target: str, intent: str = 'write-replace') -> dict[str, Any]:
    return {'target': target, 'intent': intent}

def _task(
    number: int,
    *,
    profile: str = 'implementation',
    deliverable: int = 1,
    targets: list[str] | None = None,
    steps: list[dict[str, Any]] | None = None,
    commands: list[str] | None = None,
) -> dict[str, Any]:
    """Build a minimal TASK dict for the task-graph fixture."""
    if steps is None:
        steps = [_step(tgt) for tgt in (targets or [])]
    return {
        'number': number,
        'profile': profile,
        'deliverable': deliverable,
        'steps': steps,
        'verification': {'commands': commands or []},
    }

class TestTaskGraphRedundancy:
    """The five redundancy signals over a reconstructed task graph."""

    def test_duplicate_task_and_in_task_build_both_genuine(self, tmp_path: Path):
        # two tasks edit the SAME file (multi_task_file) and one bakes a
        # HEAVY build into its verification (in_task_build).
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-dup-build',
            [
                _task(1, targets=['src/foo.py']),
                _task(
                    2,
                    targets=['src/foo.py'],
                    commands=[_HEAVY_BUILD_CMD],
                ),
            ],
        )

        row = audit.check_task_graph_redundancy(inputs)

        # both signals populated, and the row is genuine
        assert row['multi_task_file'] == 'src/foo.py'
        assert 'T2:module-tests plan-marshall' in row['in_task_build']
        assert audit._task_graph_redundancy_genuine(row) is True

    def test_clean_plan_flags_none_and_is_informational(self, tmp_path: Path):
        # distinct targets, a single light verification, balanced fanout
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-clean',
            [
                _task(1, deliverable=1, targets=['src/a.py'], commands=[_LIGHT_CMD]),
                _task(2, deliverable=2, targets=['src/b.py']),
            ],
        )

        rows = [audit.check_task_graph_redundancy(inputs)]
        # deliverable_fanout needs the corpus median stamped
        audit._finalize_deliverable_fanout(rows)
        row = rows[0]

        # every signal empty; informational
        assert row['multi_task_file'] == ''
        assert row['dup_substep'] == ''
        assert row['in_task_build'] == ''
        assert row['verif_task_fanout'] == ''
        assert row['deliverable_fanout'] == ''
        assert audit._task_graph_redundancy_genuine(row) is False

    def test_dup_substep_same_target_intent_in_two_tasks(self, tmp_path: Path):
        # the SAME (target, intent) baked into two tasks
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-dupstep',
            [
                _task(1, steps=[_step('src/x.py', 'refactor')]),
                _task(2, steps=[_step('src/x.py', 'refactor')]),
            ],
        )

        row = audit.check_task_graph_redundancy(inputs)

        # the (target, intent) pair is surfaced
        assert 'src/x.py [refactor]' in row['dup_substep']
        assert audit._task_graph_redundancy_genuine(row) is True

    def test_verif_task_fanout_more_than_one_test_task(self, tmp_path: Path):
        # two test/verification tasks (a collapse candidate)
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-fanout',
            [
                _task(1, profile='implementation', targets=['src/a.py']),
                _task(2, profile='module_testing', targets=['test/a.py']),
                _task(3, profile='verification', targets=['test/b.py']),
            ],
        )

        row = audit.check_task_graph_redundancy(inputs)

        # both test/verification task numbers listed
        assert row['verif_task_fanout'] == '2;3'
        assert audit._task_graph_redundancy_genuine(row) is True

    def test_deliverable_fanout_against_per_run_median(self, tmp_path: Path):
        # a corpus where one plan's per-deliverable task count is a high
        # outlier relative to the per-run median. The lean plans set a low median
        # (1 task/deliverable) so the threshold is max(3, 1*2)=3; the busy plan's
        # single deliverable carries 4 tasks (>=3 → flagged).
        lean_a = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path, 'lean-a', [_task(1, deliverable=1, targets=['a.py'])]
            )
        )
        lean_b = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path, 'lean-b', [_task(1, deliverable=1, targets=['b.py'])]
            )
        )
        busy = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path,
                'busy',
                [
                    _task(1, deliverable=1, targets=['c1.py']),
                    _task(2, deliverable=1, targets=['c2.py']),
                    _task(3, deliverable=1, targets=['c3.py']),
                    _task(4, deliverable=1, targets=['c4.py']),
                ],
            )
        )
        rows = [lean_a, lean_b, busy]

        threshold = audit._finalize_deliverable_fanout(rows)

        # threshold is the corpus floor; only the busy plan is flagged
        assert threshold == 3
        assert lean_a['deliverable_fanout'] == ''
        assert lean_b['deliverable_fanout'] == ''
        assert busy['deliverable_fanout'] != ''
        assert audit._task_graph_redundancy_genuine(busy) is True

    def test_is_heavy_build_cmd_distinguishes_heavy_from_light(self):
        # Heavy: a build runner + a HEAVY token
        assert audit.is_heavy_build_cmd(_HEAVY_BUILD_CMD) is True
        # Heavy: full-suite verify verb
        assert audit.is_heavy_build_cmd(
            'pyproject_build run --command-args "verify plan-marshall"'
        ) is True
        # Light: a manage-* call is never a heavy build
        assert audit.is_heavy_build_cmd(_LIGHT_CMD) is False

    def test_check_registered_in_check_names_only(self):
        # Per-plan check: in CHECK_NAMES, NOT in CROSS_PLAN_CHECKS
        assert 'task-graph-redundancy' in audit.CHECK_NAMES
        assert 'task-graph-redundancy' not in audit.CROSS_PLAN_CHECKS

    def test_emit_block_shape_and_severity_column(self, tmp_path: Path):
        # one genuine plan (multi_task_file) + one clean plan
        genuine = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path,
                'g',
                [
                    _task(1, targets=['src/dup.py']),
                    _task(2, targets=['src/dup.py']),
                ],
            )
        )
        clean = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path, 'c', [_task(1, deliverable=1, targets=['src/solo.py'])]
            )
        )
        rows = [genuine, clean]
        threshold = audit._finalize_deliverable_fanout(rows)

        block = audit.emit_task_graph_redundancy_block(rows, threshold)

        # header, corpus totals, column header, and severity cells
        assert 'check: task-graph-redundancy' in block
        assert 'status: success' in block
        assert 'plans_scanned: 2' in block
        assert 'multi_task_file_plans: 1' in block
        assert f'deliverable_fanout_threshold: {threshold}' in block
        assert 'genuine_signal_count: 1' in block
        assert (
            'rows[2]{plan_id,tasks,multi_task_file,dup_substep,in_task_build,'
            'verif_task_fanout,deliverable_fanout,severity}' in block
        )
        # the genuine plan's row ends in ,genuine; the clean one in ,informational
        assert ',genuine' in block
        assert ',informational' in block

class TestCrossCheckSynthesisCouplingF:
    """Coupling (f) redundant_build_churn: a plan whose task graph carries an
    in_task_build AND whose sequence was flagged build_churn / phase_reentry."""

    def test_fires_on_in_task_build_plus_build_churn(self):
        # same plan flagged in_task_build AND build_churn
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-x', 'in_task_build': 'T2:module-tests'},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-x', 'flags': ['build_churn:3']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # fired, naming the plan
        assert row['fired'] is True
        assert 'p-x' in row['detail']

    def test_fires_on_in_task_build_plus_phase_reentry(self):
        # in_task_build AND phase_reentry on the same plan
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-y', 'in_task_build': 'T1:quality-gate'},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-y', 'flags': ['phase_reentry:5-execute']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # fired
        assert row['fired'] is True

    def test_does_not_fire_when_signals_disjoint(self):
        # in_task_build on one plan, churn on a DIFFERENT plan
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-a', 'in_task_build': 'T2:module-tests'},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-b', 'flags': ['build_churn:3']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # not fired (no plan carries both)
        assert row['fired'] is False

    def test_does_not_fire_without_in_task_build(self):
        # churn present but no in_task_build anywhere
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-c', 'in_task_build': ''},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-c', 'flags': ['build_churn:3']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # not fired
        assert row['fired'] is False
