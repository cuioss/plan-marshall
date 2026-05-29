#!/usr/bin/env python3
"""Regression tests for the project-local ``audit-archived-plan-retrospectives``.

The audit skill is hybrid: ``scripts/audit.py`` is the deterministic computation
core (the testable unit) and ``SKILL.md`` is the LLM orchestration half. The
script has NO executor notation — it runs via direct ``python3 .../audit.py`` —
so this module imports it via ``importlib.util.spec_from_file_location`` (the
established pattern for path-resolved project scripts).

Coverage:

- D1 — ``detect_name_drift`` role resolution: canonical step IDs, the
  ``default:``-namespaced case (``lesson-2026-05-29-13-001.md`` sub-lesson
  13-002), unresolvable roles, and the empty-phase_5 no-op.
- D1 — precision/severity: genuine signals counted, informational rows excluded
  from the genuine-signal total.
- D4 — ``dormate_plan`` path-traversal hardening: ``../``, absolute, and embedded
  path-separator ``plan_id`` values are refused before any move.
- D8 — retrospective-token exclusion across the three metrics-related checks.
"""

import importlib.util
import sys
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
    def test_canonical_step_ids_not_flagged(self):
        # Arrange
        inputs = _inputs(['quality_check', 'build_verify'])
        cache: dict[str, str | None] = {}

        # Act
        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        # Assert — quality_check → quality-gate, build_verify → module-tests
        assert drift is None
        assert cache['quality_check'] == 'quality-gate'
        assert cache['build_verify'] == 'module-tests'

    def test_namespaced_step_ids_resolve_to_roles_and_not_flagged(self):
        # Arrange — the lesson-2026-05-29-13-001 sub-lesson 13-002 namespaced shape
        inputs = _inputs(['default:quality_check', 'default:build_verify'])
        cache: dict[str, str | None] = {}

        # Act
        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)
        resolved = {
            audit._resolve_step_role(PROJECT_ROOT, s, cache)
            for s in inputs.manifest_phase_5
        }

        # Assert — the default: prefix is stripped and roles resolve correctly
        assert drift is None
        assert resolved == {'quality-gate', 'module-tests'}

    def test_unresolvable_role_flagged_as_genuine_drift(self):
        # Arrange — a step ID with no standards file / no role: frontmatter
        inputs = _inputs(['not_a_real_step'])
        cache: dict[str, str | None] = {}

        # Act
        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        # Assert
        assert drift is not None
        assert 'unresolvable role' in drift

    def test_empty_phase_5_returns_no_drift(self):
        # Arrange
        inputs = _inputs([])
        cache: dict[str, str | None] = {}

        # Act
        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        # Assert
        assert drift is None

    def test_standards_dir_absent_degrades_to_unresolved(self, tmp_path: Path):
        # Arrange — a repo_root with no phase-5-execute/standards directory
        inputs = _inputs(['quality_check'])
        cache: dict[str, str | None] = {}

        # Act — best-effort: unresolved rather than crash
        role = audit._resolve_step_role(tmp_path, 'quality_check', cache)
        drift = audit.detect_name_drift(inputs, tmp_path, cache)

        # Assert
        assert role is None
        assert drift is not None
        assert 'unresolvable role' in drift


# =============================================================================
# D1 — precision / severity in the manifest block summary
# =============================================================================


class TestManifestSeverityPrecision:
    def test_genuine_signal_count_counts_only_genuine_rows(self):
        # Arrange — one drift row, one populated name_drift, two informational
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

        # Act
        block = audit.emit_manifest_block(full_rows)

        # Assert — drift + populated name_drift = 2 genuine; informational excluded
        assert 'genuine_signal_count: 2' in block
        assert 'name_drift_count: 1' in block

    def test_severity_classifier_marks_informational_rows(self):
        # Arrange / Act / Assert
        assert (
            audit._manifest_row_severity({'verdict': 'drift', 'name_drift': None})
            == 'genuine'
        )
        assert (
            audit._manifest_row_severity({'verdict': 'ok', 'name_drift': 'x'})
            == 'genuine'
        )
        assert (
            audit._manifest_row_severity({'verdict': 'incomplete', 'name_drift': None})
            == 'informational'
        )
        assert (
            audit._manifest_row_severity({'verdict': 'ok', 'name_drift': None})
            == 'informational'
        )


# =============================================================================
# D4 — dormate_plan path-traversal hardening
# =============================================================================


class TestDormatePlanIdHardening:
    def test_parent_traversal_plan_id_refused(self, tmp_path: Path):
        # Act
        result = audit.dormate_plan(tmp_path, '../escape', confirmed=True)

        # Assert — refused on grammar before any move
        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']

    def test_absolute_path_plan_id_refused(self, tmp_path: Path):
        # Act
        result = audit.dormate_plan(tmp_path, '/etc/passwd', confirmed=True)

        # Assert
        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']

    def test_embedded_separator_plan_id_refused(self, tmp_path: Path):
        # Act
        result = audit.dormate_plan(tmp_path, 'a/b', confirmed=True)

        # Assert
        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']

    def test_well_formed_plan_id_passes_grammar_then_source_not_found(self, tmp_path: Path):
        # Arrange — a canonical kebab/date plan_id with no archived dir on disk
        plan_id = '2026-05-29-some-valid-plan'

        # Act
        result = audit.dormate_plan(tmp_path, plan_id, confirmed=True)

        # Assert — passes grammar (NOT the grammar refusal); fails source-not-found
        assert result['status'] == 'error'
        assert 'source not found' in result['reason']
        assert 'invalid plan_id' not in result['reason']

    def test_inert_without_confirmed(self, tmp_path: Path):
        # Act
        result = audit.dormate_plan(tmp_path, '../escape', confirmed=False)

        # Assert — the inert path fires before grammar validation
        assert result['status'] == 'refused'
        assert 'requires --confirmed' in result['reason']


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
        # Arrange — finalize raw total dominates (2000 of 2800 = 71%, which would
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

        # Act
        result = audit.check_metrics(inputs)

        # Assert — effective total 1000 (400 + 400 + 200); shares 40%/40%/20%,
        # none >= 45%, so nothing is flagged. Without exclusion, finalize's raw
        # 2000/2800 = 71% would have tripped the threshold.
        assert result['disproportionate_token'] == ''

    def test_negative_control_genuine_disproportionate_still_flagged(self, monkeypatch):
        # Arrange — a genuine >=45% phase even after retrospective exclusion
        phases = [
            _phase('5-execute', total_tokens=300),
            _phase('3-outline', total_tokens=700),
            _phase('6-finalize', total_tokens=200, retrospective_tokens=100),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        # Act
        result = audit.check_metrics(inputs)

        # Assert — effective total 1100, outline 700/1100 = 63% → flagged
        assert '3-outline' in result['disproportionate_token']


class TestRetrospectiveExclusionOptimization:
    def test_retrospective_only_outlier_not_flagged(self, monkeypatch):
        # Arrange — three balanced phases plus a finalize whose only spend is
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

        # Act
        result = audit.check_metrics(inputs)

        # Assert — the finalize phase (raw 900 tok/s outlier) is excluded
        assert '6-finalize' not in result['optimization_signal']
        assert result['optimization_signal'] == ''


class TestRetrospectiveExclusionTrend:
    def test_total_and_divisor_exclude_retrospective(self, monkeypatch):
        # Arrange — one plan whose finalize spend is entirely retrospective
        phases = [
            _phase('5-execute', total_tokens=500),
            _phase('6-finalize', total_tokens=400, retrospective_tokens=400),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        # Act
        result = audit.cross_token_trend([inputs])

        # Assert — effective total 500, only one implementation phase counted
        row = result['rows'][0]
        assert row['total_tokens'] == 500
        assert row['phases'] == 1
        assert row['tokens_per_phase'] == 500


class TestRetrospectiveExclusionDegrade:
    def test_absent_attribution_excludes_nothing(self, monkeypatch):
        # Arrange — archived-plan shape: NO retrospective_tokens field anywhere
        phases = [
            _phase('5-execute', total_tokens=1000, duration_seconds=100.0),
            _phase('6-finalize', total_tokens=2000, duration_seconds=50.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        # Act
        metrics = audit.check_metrics(inputs)
        trend = audit.cross_token_trend([inputs])

        # Assert — behaves exactly as pre-D8 (2000/3000 = 67% finalize flagged)
        assert '6-finalize' in metrics['disproportionate_token']
        assert trend['rows'][0]['total_tokens'] == 3000
        assert trend['rows'][0]['phases'] == 2

    def test_only_retrospective_excluded_other_op_spend_counted(self, monkeypatch):
        # Arrange — a finalize phase carrying q-gate-validation / other-op spend
        # (no retrospective_tokens) stays fully counted.
        phases = [
            _phase('5-execute', total_tokens=400),
            _phase('6-finalize', total_tokens=600),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        # Act
        result = audit.check_metrics(inputs)

        # Assert — effective total 1000, finalize 600/1000 = 60% → flagged
        assert '6-finalize' in result['disproportionate_token']
