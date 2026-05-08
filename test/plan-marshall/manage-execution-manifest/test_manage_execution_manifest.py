#!/usr/bin/env python3
"""Tests for manage-execution-manifest.py script.

Tier 2 (direct import) tests with a couple of subprocess tests for CLI
plumbing. Mirrors the test layout used by manage-references and other
manage-* skills.
"""

import importlib.util
import json
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import PlanContext, get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_read = _mem.cmd_read
cmd_validate = _mem.cmd_validate
read_manifest = _mem.read_manifest
get_manifest_path = _mem.get_manifest_path
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor. The handler is wrapped in try/except so failures are
# already silent, but we replace it with a no-op for clarity and speed.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_strategy: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_strategy=commit_strategy,
    )


def _read_ns(plan_id: str = 'test-plan') -> Namespace:
    return Namespace(plan_id=plan_id)


def _validate_ns(
    plan_id: str = 'test-plan',
    phase_5_steps: str | None = 'quality-gate,module-tests,coverage',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
) -> Namespace:
    return Namespace(plan_id=plan_id, phase_5_steps=phase_5_steps, phase_6_steps=phase_6_steps)


# =============================================================================
# Decision Matrix Tests — table-driven cases (one per row of the matrix +
# the requested 8th case for early_terminate analysis-with-empty-files)
# =============================================================================


def test_default_code_shaped_feature_runs_full_phases():
    """Row 7 — default: feature plan gets the full Phase 5 and Phase 6 sets."""
    with PlanContext(plan_id='matrix-default'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-default',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=12,
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['rule_fired'] == 'default'
        assert result['phase_5']['early_terminate'] is False
        assert result['phase_5']['verification_steps_count'] == 2  # quality-gate + module-tests
        assert result['phase_6']['steps_count'] == len(DEFAULT_PHASE_6_STEPS)


def test_early_terminate_analysis_with_empty_files():
    """Row 1 — analysis with affected_files_count=0 → early_terminate=true."""
    with PlanContext(plan_id='matrix-analysis'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-analysis',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
        )
        assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
        assert result['phase_5']['early_terminate'] is True
        assert result['phase_5']['verification_steps_count'] == 0
        # Phase 6 keeps the records-and-archive duo (lessons-capture + archive-plan).
        assert result['phase_6']['steps_count'] == 2


def test_recipe_path_drops_heavy_review_steps():
    """Row 2 — recipe_key present → drop automated-review/sonar-roundtrip."""
    with PlanContext(plan_id='matrix-recipe'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-recipe',
                change_type='tech_debt',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=2,
            )
        )
        assert result is not None and result['rule_fired'] == 'recipe'
        manifest = read_manifest('matrix-recipe')
        assert manifest is not None
        assert 'automated-review' not in manifest['phase_6']['steps']
        assert 'sonar-roundtrip' not in manifest['phase_6']['steps']
        assert 'commit-push' in manifest['phase_6']['steps']


def test_docs_only_skips_phase_5_verification():
    """Row 3 — docs-only signal: no module-tests/coverage in candidates → empty Phase 5 list."""
    with PlanContext(plan_id='matrix-docs'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-docs',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                # docs-only candidate set: only quality-gate, no module-tests/coverage.
                phase_5_steps='quality-gate',
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
            )
        )
        assert result is not None and result['rule_fired'] == 'docs_only'
        assert result['phase_5']['verification_steps_count'] == 0
        manifest = read_manifest('matrix-docs')
        assert manifest is not None
        assert 'automated-review' not in manifest['phase_6']['steps']
        assert 'sonar-roundtrip' not in manifest['phase_6']['steps']


def test_tests_only_runs_module_tests_and_full_phase_6():
    """Row 4 — verification change_type with affected files → module-tests + full Phase 6."""
    with PlanContext(plan_id='matrix-tests'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-tests',
                change_type='verification',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_5_steps='quality-gate,module-tests,coverage',
            )
        )
        assert result is not None and result['rule_fired'] == 'tests_only'
        manifest = read_manifest('matrix-tests')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['module-tests']
        assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)


def test_surgical_bug_fix_trims_heavy_review_steps():
    """Row 5 — surgical+bug_fix: trim Phase 6 review steps."""
    with PlanContext(plan_id='matrix-bug'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-bug',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('matrix-bug')
        assert manifest is not None
        for stripped in ('automated-review', 'sonar-roundtrip'):
            assert stripped not in manifest['phase_6']['steps']
        assert 'lessons-capture' in manifest['phase_6']['steps']


def test_surgical_tech_debt_trims_heavy_review_steps():
    """Row 5 — surgical+tech_debt: same trim, distinct rule key."""
    with PlanContext(plan_id='matrix-tech'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-tech',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=2,
                # Need code-shaped candidate set (module-tests present) so we
                # don't fall into the docs_only row first.
                phase_5_steps='quality-gate,module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('matrix-tech')
        assert manifest is not None
        assert 'commit-push' in manifest['phase_6']['steps']
        for stripped in ('automated-review', 'sonar-roundtrip'):
            assert stripped not in manifest['phase_6']['steps']


# =============================================================================
# Boundary-Normalization Regression Tests
#
# `phase_6_candidates` may arrive prefixed (`default:foo` from marshal.json's
# step registry) or bare (`foo` from DEFAULT_PHASE_6_STEPS). Lesson
# ``2026-04-27-23-004`` closed the prefix-handling gap by normalizing both
# ``phase_5_candidates`` and ``phase_6_candidates`` once at the
# ``cmd_compose`` boundary — every leading ``default:`` is stripped a single
# time at intake, so the seven-row matrix, the pre-filter helpers, and the
# bot-enforcement guard all see bare names. Manifest output and result fields
# are bare strings throughout.
#
# These tests feed prefixed candidates and assert the resulting manifest
# carries bare-name entries, with each cascade rule (Rule 1, 2, 3, 5, 6)
# dropping or including the right steps. They previously asserted that the
# prefix survived verbatim into the manifest output — that contract has been
# retired in favor of the boundary-normalization contract pinned by
# ``test_boundary_normalization_strips_prefix_for_all_downstream_consumers``.
# =============================================================================


_PREFIXED_PHASE_6 = (
    'default:pre-push-quality-gate',
    'default:commit-push',
    'default:create-pr',
    'default:automated-review',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:archive-plan',
)


def test_rule_1_early_terminate_analysis_with_prefixed_candidates():
    """Rule 1 (early_terminate_analysis) — prefixed candidates: include only lessons/archive (bare)."""
    with PlanContext(plan_id='prefix-rule-1'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-rule-1',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
                phase_6_steps=','.join(_PREFIXED_PHASE_6),
            )
        )
        assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
        manifest = read_manifest('prefix-rule-1')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Boundary normalization strips `default:` at intake — output is bare.
        assert set(steps) == {'lessons-capture', 'archive-plan'}
        # No `default:`-prefixed entries survive anywhere in the manifest.
        assert not any(s.startswith('default:') for s in steps)
        # Heavy steps that would have leaked through pre-fix are absent.
        for excluded in ('commit-push', 'create-pr', 'automated-review', 'pre-push-quality-gate', 'branch-cleanup'):
            assert excluded not in steps


def test_rule_2_recipe_with_prefixed_candidates():
    """Rule 2 (recipe) — prefixed candidates: drop automated-review/sonar-roundtrip (bare output)."""
    prefixed_with_sonar = _PREFIXED_PHASE_6 + ('default:sonar-roundtrip',)
    with PlanContext(plan_id='prefix-rule-2'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-rule-2',
                change_type='tech_debt',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=2,
                phase_6_steps=','.join(prefixed_with_sonar),
            )
        )
        assert result is not None and result['rule_fired'] == 'recipe'
        manifest = read_manifest('prefix-rule-2')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # No `default:` prefix in output — boundary-normalized at intake.
        assert not any(s.startswith('default:') for s in steps)
        # Heavy review steps are dropped.
        for dropped in ('automated-review', 'sonar-roundtrip'):
            assert dropped not in steps
        # Non-heavy steps survive (bare).
        assert 'commit-push' in steps
        assert 'create-pr' in steps
        assert 'lessons-capture' in steps


def test_rule_3_docs_only_with_prefixed_candidates():
    """Rule 3 (docs_only) — prefixed candidates: drop sonar-roundtrip/automated-review (bare output)."""
    prefixed_with_sonar = _PREFIXED_PHASE_6 + ('default:sonar-roundtrip',)
    with PlanContext(plan_id='prefix-rule-3'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-rule-3',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                # docs-only candidate set: only quality-gate, no module-tests/coverage.
                phase_5_steps='quality-gate',
                phase_6_steps=','.join(prefixed_with_sonar),
            )
        )
        assert result is not None and result['rule_fired'] == 'docs_only'
        manifest = read_manifest('prefix-rule-3')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert not any(s.startswith('default:') for s in steps)
        # Review steps dropped.
        for dropped in ('sonar-roundtrip', 'automated-review'):
            assert dropped not in steps
        # Non-review steps survive (bare).
        assert 'commit-push' in steps
        assert 'lessons-capture' in steps


def test_rule_5_surgical_bug_fix_with_prefixed_candidates():
    """Rule 5 (surgical_bug_fix) — prefixed candidates: drop automated-review/sonar-roundtrip (bare output)."""
    prefixed_with_sonar = _PREFIXED_PHASE_6 + ('default:sonar-roundtrip',)
    with PlanContext(plan_id='prefix-rule-5-bug'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-rule-5-bug',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_6_steps=','.join(prefixed_with_sonar),
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('prefix-rule-5-bug')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert not any(s.startswith('default:') for s in steps)
        for dropped in ('automated-review', 'sonar-roundtrip'):
            assert dropped not in steps
        assert 'lessons-capture' in steps
        assert 'commit-push' in steps


def test_rule_5_surgical_tech_debt_with_prefixed_candidates():
    """Rule 5 (surgical_tech_debt) — prefixed candidates: same drop as bug_fix (bare output)."""
    prefixed_with_sonar = _PREFIXED_PHASE_6 + ('default:sonar-roundtrip',)
    with PlanContext(plan_id='prefix-rule-5-tech'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-rule-5-tech',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=2,
                # Code-shaped candidate set so we don't fall into docs_only first.
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(prefixed_with_sonar),
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('prefix-rule-5-tech')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert not any(s.startswith('default:') for s in steps)
        for dropped in ('automated-review', 'sonar-roundtrip'):
            assert dropped not in steps
        assert 'commit-push' in steps


def test_rule_6_verification_no_files_with_prefixed_candidates():
    """Rule 6 (verification_no_files) — prefixed candidates: include only lessons/archive (bare output)."""
    with PlanContext(plan_id='prefix-rule-6'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-rule-6',
                change_type='verification',
                scope_estimate='none',
                affected_files_count=0,
                phase_6_steps=','.join(_PREFIXED_PHASE_6),
            )
        )
        assert result is not None and result['rule_fired'] == 'verification_no_files'
        manifest = read_manifest('prefix-rule-6')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Boundary normalization strips `default:` at intake — output is bare.
        assert set(steps) == {'lessons-capture', 'archive-plan'}
        assert not any(s.startswith('default:') for s in steps)
        for excluded in ('commit-push', 'create-pr', 'automated-review', 'pre-push-quality-gate', 'branch-cleanup'):
            assert excluded not in steps


def test_prefix_normalization_no_op_for_bare_candidates():
    """Sanity: boundary normalization is a no-op for bare candidates.

    The bare-name path (DEFAULT_PHASE_6_STEPS) must continue to work identically
    to the prefixed path. Rule 5 with bare candidates pins the bare-name shape
    end-to-end — boundary stripping at ``cmd_compose`` intake leaves bare names
    unchanged, so the cascade-rule layer sees and emits the same bare strings.
    """
    bare = (
        'commit-push',
        'create-pr',
        'automated-review',
        'sonar-roundtrip',
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    )
    with PlanContext(plan_id='prefix-noop-bare'):
        result = cmd_compose(
            _compose_ns(
                plan_id='prefix-noop-bare',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_6_steps=','.join(bare),
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('prefix-noop-bare')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Bare names: heavy review steps still dropped; helper is a no-op.
        for dropped in ('automated-review', 'sonar-roundtrip'):
            assert dropped not in steps
        assert 'commit-push' in steps
        assert 'lessons-capture' in steps


def test_boundary_normalization_strips_prefix_for_all_downstream_consumers():
    """Boundary contract — every entry the cascade-rule layer + downstream output sees is bare.

    Pins the boundary-normalization invariant introduced by lesson
    ``2026-04-27-23-004``: ``cmd_compose`` strips a single leading ``default:``
    from each ``phase_5_candidates`` and ``phase_6_candidates`` entry once at
    intake (via ``_strip_default_prefix``), and every downstream site — the
    seven-row matrix, ``_apply_commit_strategy_none``,
    ``_apply_pre_push_quality_gate_inactive``,
    ``_apply_pre_submission_self_review_inactive``, and the bot-enforcement
    guard — consumes those already-bare strings without any per-site
    ``_strip_default_prefix`` call.

    The test feeds a deliberately MIXED candidate list (some entries
    prefixed, some bare, plus a project-prefixed entry to demonstrate the
    ``project:`` prefix is preserved verbatim) to ``cmd_compose``, then
    asserts that every default-domain entry in the resulting
    ``phase_6.steps`` is bare. The only entry that retains its leading
    prefix is the ``project:`` step — its prefix is the canonical
    typed-step notation and is NOT stripped by ``_strip_default_prefix``
    (which only normalizes the ``default:`` namespace).

    This invariant guards against regressions where a future contributor
    re-introduces a per-site ``_strip_default_prefix`` call that masks a
    boundary leak: with the prefix stripped at intake, a per-site strip
    becomes dead code, and a missing intake strip becomes a visible test
    failure here rather than a silent functional drift.
    """
    mixed = [
        # Prefixed default entries.
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        # Bare default entries (no prefix to strip).
        'lessons-capture',
        # Typed-step entry (project: prefix is preserved verbatim).
        'project:finalize-step-plugin-doctor',
        # More prefixed defaults.
        'default:branch-cleanup',
        'default:archive-plan',
    ]
    mixed_phase_5 = [
        'default:quality-gate',  # prefixed
        'module-tests',  # bare
    ]
    with PlanContext(plan_id='boundary-mixed') as ctx:
        # Use a Row 7 (default) shape so the cascade-rule output preserves
        # candidates verbatim (modulo boundary normalization).
        # Force the bot-enforcement guard's no-op path by NOT configuring CI.
        assert ctx.plan_dir is not None  # silence unused-var warning
        result = cmd_compose(
            _compose_ns(
                plan_id='boundary-mixed',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_5_steps=','.join(mixed_phase_5),
                phase_6_steps=','.join(mixed),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['rule_fired'] == 'default'

        manifest = read_manifest('boundary-mixed')
        assert manifest is not None
        phase_5_steps = manifest['phase_5']['verification_steps']
        phase_6_steps = manifest['phase_6']['steps']

        # Every default-domain entry is bare — no `default:` prefix anywhere
        # in either phase's output.
        assert not any(s.startswith('default:') for s in phase_5_steps), (
            f'phase_5 leaked `default:`-prefixed entry: {phase_5_steps!r}'
        )
        assert not any(s.startswith('default:') for s in phase_6_steps), (
            f'phase_6 leaked `default:`-prefixed entry: {phase_6_steps!r}'
        )

        # Phase 5 carries the bare normalization of both inputs.
        assert phase_5_steps == ['quality-gate', 'module-tests']

        # Every Phase-6 default-domain entry from the input survives as a bare
        # string after Row 7 (no cascade-rule subtractions on the default rule).
        for bare_default in (
            'commit-push',
            'create-pr',
            'automated-review',
            'lessons-capture',
            'branch-cleanup',
            'archive-plan',
        ):
            assert bare_default in phase_6_steps, (
                f'expected bare {bare_default!r} in phase_6 but got: {phase_6_steps!r}'
            )

        # The non-default-namespace `project:` prefix is preserved verbatim —
        # boundary normalization strips ONLY the `default:` namespace.
        assert 'project:finalize-step-plugin-doctor' in phase_6_steps


# =============================================================================
# Bundle-self-modification tests removed
#
# The ``bundle_self_modification`` stacked rule was retired by cluster 02
# deliverable 9 — the new built-in ``default:sync-plugin-cache`` step
# (order 14) sits unconditionally between ``default:deploy-target`` (order 12)
# and the agent-dispatched steps in the canonical Phase 6 ordering, which
# subsumes the rule's previous job. Tests pinning the removed rule have been
# deleted with the rule itself.
# =============================================================================


def test_verification_no_files_keeps_full_phase_5_trims_phase_6():
    """Row 6 — verification w/o files: full Phase 5, Phase 6 trimmed to records+archive."""
    with PlanContext(plan_id='matrix-vnofiles'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-vnofiles',
                change_type='verification',
                scope_estimate='none',
                affected_files_count=0,
                phase_5_steps='quality-gate,module-tests,coverage',
            )
        )
        assert result is not None and result['rule_fired'] == 'verification_no_files'
        manifest = read_manifest('matrix-vnofiles')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['quality-gate', 'module-tests', 'coverage']
        assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'archive-plan'}


# =============================================================================
# Schema + I/O tests
# =============================================================================


def test_compose_writes_manifest_to_expected_path():
    with PlanContext(plan_id='io-write'):
        cmd_compose(_compose_ns(plan_id='io-write'))
        manifest_path = get_manifest_path('io-write')
        assert manifest_path.exists()
        manifest = read_manifest('io-write')
        assert manifest is not None
        assert manifest['manifest_version'] == 1
        assert manifest['plan_id'] == 'io-write'
        assert isinstance(manifest['phase_5']['verification_steps'], list)
        assert isinstance(manifest['phase_6']['steps'], list)


def test_read_returns_full_manifest():
    with PlanContext(plan_id='io-read'):
        cmd_compose(_compose_ns(plan_id='io-read'))
        result = cmd_read(_read_ns(plan_id='io-read'))
        assert result is not None and result['status'] == 'success'
        assert result['plan_id'] == 'io-read'
        assert 'phase_5' in result
        assert 'phase_6' in result


def test_read_missing_manifest_returns_none_with_toon_error(capsys):
    with PlanContext(plan_id='io-missing'):
        result = cmd_read(_read_ns(plan_id='io-missing'))
        assert result is None
        captured = capsys.readouterr()
        assert 'file_not_found' in captured.out


def test_validate_happy_path():
    with PlanContext(plan_id='val-ok'):
        cmd_compose(_compose_ns(plan_id='val-ok'))
        result = cmd_validate(_validate_ns(plan_id='val-ok'))
        assert result is not None and result['status'] == 'success'
        assert result['valid'] is True
        assert result['phase_5_unknown_steps_count'] == 0
        assert result['phase_6_unknown_steps_count'] == 0


def test_validate_missing_manifest_returns_none(capsys):
    with PlanContext(plan_id='val-missing'):
        result = cmd_validate(_validate_ns(plan_id='val-missing'))
        assert result is None
        captured = capsys.readouterr()
        assert 'file_not_found' in captured.out


def test_validate_unknown_phase_5_step_flagged():
    with PlanContext(plan_id='val-unknown-p5'):
        cmd_compose(
            _compose_ns(
                plan_id='val-unknown-p5',
                phase_5_steps='quality-gate,module-tests',
            )
        )
        # Now validate with a candidate set that DOESN'T include module-tests.
        result = cmd_validate(
            _validate_ns(
                plan_id='val-unknown-p5',
                phase_5_steps='quality-gate',
            )
        )
        assert result is not None and result['status'] == 'error'
        assert result['error'] == 'invalid_manifest'
        assert result['phase_5_unknown_steps_count'] == 1
        assert 'module-tests' in result['phase_5_unknown_steps']


# =============================================================================
# Input validation tests
# =============================================================================


@pytest.mark.parametrize(
    'field,value,error_code',
    [
        ('change_type', 'unknown_type', 'invalid_change_type'),
        ('scope_estimate', 'massive', 'invalid_scope_estimate'),
        ('track', 'twisty', 'invalid_track'),
    ],
)
def test_compose_rejects_invalid_enum_values(field, value, error_code):
    with PlanContext(plan_id='val-enum'):
        kwargs = {field: value}
        result = cmd_compose(_compose_ns(plan_id='val-enum', **kwargs))
        assert result is not None and result['status'] == 'error'
        assert result['error'] == error_code


def test_compose_clamps_negative_affected_files_count():
    """Negative affected_files_count should be clamped to 0 (no crash)."""
    with PlanContext(plan_id='val-negfiles'):
        result = cmd_compose(
            _compose_ns(
                plan_id='val-negfiles',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=-5,
            )
        )
        # With clamp to 0, analysis+0 → early_terminate.
        assert result is not None and result['status'] == 'success'
        assert result['rule_fired'] == 'early_terminate_analysis'


# =============================================================================
# Rule precedence + edge-case coverage
# =============================================================================


def test_early_terminate_wins_over_recipe_when_both_match():
    """Rule 1 evaluates before Rule 2 — analysis + recipe_key + 0 files → early_terminate."""
    with PlanContext(plan_id='matrix-precedence-er'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-precedence-er',
                change_type='analysis',
                scope_estimate='none',
                recipe_key='lesson_cleanup',
                affected_files_count=0,
            )
        )
        assert result is not None and result['rule_fired'] == 'early_terminate_analysis'


def test_recipe_wins_over_docs_only_when_both_match():
    """Rule 2 evaluates before Rule 3 — recipe_key short-circuits the docs-only branch."""
    with PlanContext(plan_id='matrix-precedence-rd'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-precedence-rd',
                change_type='tech_debt',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=2,
                # Docs-only candidate set; recipe rule should still win.
                phase_5_steps='quality-gate',
            )
        )
        assert result is not None and result['rule_fired'] == 'recipe'


def test_surgical_enhancement_with_code_candidates_falls_to_default():
    """Row 5 only matches bug_fix/tech_debt; surgical+enhancement+code → default."""
    with PlanContext(plan_id='matrix-surgical-enh'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-surgical-enh',
                change_type='enhancement',
                scope_estimate='surgical',
                affected_files_count=2,
                # Candidate set has module-tests so docs_only does NOT match.
                phase_5_steps='quality-gate,module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'default'
        manifest = read_manifest('matrix-surgical-enh')
        assert manifest is not None
        # Default keeps the full phase_6 candidate list.
        assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)


def test_surgical_enhancement_with_docs_candidates_hits_docs_only():
    """surgical+enhancement falls into docs_only when candidates lack module-tests/coverage."""
    with PlanContext(plan_id='matrix-surgical-enh-docs'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-surgical-enh-docs',
                change_type='enhancement',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='quality-gate',
            )
        )
        assert result is not None and result['rule_fired'] == 'docs_only'


def test_single_module_tech_debt_with_docs_candidates_hits_docs_only():
    """Row 3 also fires for single_module scope (not just surgical)."""
    with PlanContext(plan_id='matrix-single-mod-docs'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-single-mod-docs',
                change_type='tech_debt',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_5_steps='quality-gate',
            )
        )
        assert result is not None and result['rule_fired'] == 'docs_only'


def test_recipe_with_partial_phase_5_candidates_filters_to_known_steps():
    """Recipe rule intersects phase_5 candidates with {quality-gate, module-tests}."""
    with PlanContext(plan_id='matrix-recipe-filter'):
        cmd_compose(
            _compose_ns(
                plan_id='matrix-recipe-filter',
                change_type='tech_debt',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=2,
                # Pass an unknown candidate alongside the known ones.
                phase_5_steps='quality-gate,module-tests,coverage,exotic-step',
            )
        )
        manifest = read_manifest('matrix-recipe-filter')
        assert manifest is not None
        # Recipe keeps only quality-gate + module-tests; coverage/exotic dropped.
        assert manifest['phase_5']['verification_steps'] == ['quality-gate', 'module-tests']


def test_compose_is_idempotent_and_deterministic():
    """Re-composing with identical inputs overwrites and yields identical manifest."""
    with PlanContext(plan_id='matrix-idempotent'):
        first = cmd_compose(_compose_ns(plan_id='matrix-idempotent'))
        manifest_first = read_manifest('matrix-idempotent')
        second = cmd_compose(_compose_ns(plan_id='matrix-idempotent'))
        manifest_second = read_manifest('matrix-idempotent')
        assert first is not None and second is not None
        assert first['rule_fired'] == second['rule_fired']
        assert manifest_first == manifest_second


def test_compose_default_phase_6_steps_when_csv_omitted():
    """When --phase-6-steps is None, DEFAULT_PHASE_6_STEPS is used."""
    with PlanContext(plan_id='matrix-default-csv'):
        cmd_compose(
            Namespace(
                plan_id='matrix-default-csv',
                change_type='feature',
                track='complex',
                scope_estimate='multi_module',
                recipe_key=None,
                affected_files_count=12,
                phase_5_steps=None,  # Falls back to DEFAULT_PHASE_5_STEPS.
                phase_6_steps=None,  # Falls back to DEFAULT_PHASE_6_STEPS.
                commit_strategy=None,
            )
        )
        manifest = read_manifest('matrix-default-csv')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == list(DEFAULT_PHASE_5_STEPS)
        assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)


# =============================================================================
# Additional read / validate coverage
# =============================================================================


def test_read_returns_all_manifest_keys():
    """read echoes every manifest field the composer wrote."""
    with PlanContext(plan_id='io-read-fields'):
        cmd_compose(_compose_ns(plan_id='io-read-fields'))
        result = cmd_read(_read_ns(plan_id='io-read-fields'))
        assert result is not None
        # Mandatory schema keys.
        assert result['manifest_version'] == 1
        assert 'phase_5' in result and 'phase_6' in result
        # phase_5 sub-keys.
        assert 'early_terminate' in result['phase_5']
        assert 'verification_steps' in result['phase_5']
        # phase_6 sub-keys.
        assert 'steps' in result['phase_6']


def test_validate_without_candidate_sets_skips_step_id_check():
    """validate succeeds (status=success) when candidate sets aren't supplied."""
    with PlanContext(plan_id='val-no-candidates'):
        cmd_compose(_compose_ns(plan_id='val-no-candidates'))
        result = cmd_validate(
            Namespace(
                plan_id='val-no-candidates',
                phase_5_steps=None,
                phase_6_steps=None,
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['valid'] is True


def test_validate_unknown_phase_6_step_flagged():
    """validate flags phase_6 steps not present in the candidate set."""
    with PlanContext(plan_id='val-unknown-p6'):
        cmd_compose(
            _compose_ns(
                plan_id='val-unknown-p6',
                # Default phase_6 candidate set; manifest will contain
                # the full DEFAULT_PHASE_6_STEPS list.
            )
        )
        result = cmd_validate(
            Namespace(
                plan_id='val-unknown-p6',
                phase_5_steps=None,
                # Restrict allowed phase_6 steps to a tiny subset; everything
                # else in the manifest becomes "unknown".
                phase_6_steps='commit-push',
            )
        )
        assert result is not None and result['status'] == 'error'
        assert result['error'] == 'invalid_manifest'
        assert result['phase_6_unknown_steps_count'] >= 1
        # All non-commit-push DEFAULT_PHASE_6_STEPS entries should be flagged.
        assert 'create-pr' in result['phase_6_unknown_steps']


def test_validate_detects_corrupt_manifest_version():
    """validate flags a manifest_version mismatch from a tampered file."""
    with PlanContext(plan_id='val-bad-version'):
        cmd_compose(_compose_ns(plan_id='val-bad-version'))
        # Tamper with the on-disk manifest to flip the version.
        path = get_manifest_path('val-bad-version')
        text = path.read_text(encoding='utf-8')
        # TOON top-level scalar replacement: serialize_toon emits
        # `manifest_version: 1` — flip the literal.
        path.write_text(text.replace('manifest_version: 1', 'manifest_version: 99'), encoding='utf-8')

        result = cmd_validate(_validate_ns(plan_id='val-bad-version'))
        assert result is not None and result['status'] == 'error'
        assert result['error'] == 'invalid_manifest'
        assert 'manifest_version mismatch' in result['message']


def test_validate_detects_plan_id_mismatch():
    """validate flags a plan_id mismatch from a tampered file."""
    with PlanContext(plan_id='val-bad-pid'):
        cmd_compose(_compose_ns(plan_id='val-bad-pid'))
        path = get_manifest_path('val-bad-pid')
        text = path.read_text(encoding='utf-8')
        path.write_text(text.replace('plan_id: val-bad-pid', 'plan_id: other-plan'), encoding='utf-8')

        result = cmd_validate(_validate_ns(plan_id='val-bad-pid'))
        assert result is not None and result['status'] == 'error'
        assert result['error'] == 'invalid_manifest'
        assert 'plan_id mismatch' in result['message']


# =============================================================================
# commit_strategy pre-filter tests
# =============================================================================


@pytest.mark.parametrize(
    'commit_strategy,expect_commit_push,expect_omitted',
    [
        ('per_plan', True, False),
        ('per_deliverable', True, False),
        (None, True, False),  # Absent flag defaults to per_plan.
        ('none', False, True),
    ],
)
def test_commit_strategy_pre_filter(commit_strategy, expect_commit_push, expect_omitted):
    """Pre-filter: commit_strategy=none drops commit-push; other values retain it."""
    # plan_id may not contain underscores — convert any underscored strategy
    # value to a hyphenated slug.
    slug = (commit_strategy or 'absent').replace('_', '-')
    plan_id = f'matrix-cs-{slug}'
    with PlanContext(plan_id=plan_id):
        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=8,
                commit_strategy=commit_strategy,
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['commit_push_omitted'] is expect_omitted
        manifest = read_manifest(plan_id)
        assert manifest is not None
        if expect_commit_push:
            assert 'commit-push' in manifest['phase_6']['steps']
        else:
            assert 'commit-push' not in manifest['phase_6']['steps']


def test_commit_strategy_none_emits_decision_log_message():
    """commit_strategy=none triggers the dedicated decision-log emission helper."""
    captured: list[str] = []
    original_helper = _mem._log_commit_push_omitted

    def _capture(plan_id):
        captured.append(plan_id)

    _mem._log_commit_push_omitted = _capture
    try:
        with PlanContext(plan_id='matrix-cs-log'):
            cmd_compose(
                _compose_ns(
                    plan_id='matrix-cs-log',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    commit_strategy='none',
                )
            )
    finally:
        _mem._log_commit_push_omitted = original_helper
    assert captured == ['matrix-cs-log']


def test_commit_strategy_none_decision_log_message_matches_contract():
    """commit_strategy=none emits the exact decision-log line from the deliverable contract."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        with PlanContext(plan_id='matrix-cs-msg'):
            cmd_compose(
                _compose_ns(
                    plan_id='matrix-cs-msg',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    commit_strategy='none',
                )
            )
    finally:
        _mem._emit_decision_log = original_emit

    # Expect at least the omission entry; the rule-fired entry is also emitted.
    omission_entries = [(pid, msg) for pid, msg in captured if 'commit-push omitted' in msg]
    assert len(omission_entries) == 1, f'expected one omission entry, got {captured!r}'
    pid, msg = omission_entries[0]
    assert pid == 'matrix-cs-msg'
    assert msg == ('(plan-marshall:manage-execution-manifest:compose) commit-push omitted — commit_strategy=none')


def test_commit_strategy_default_does_not_emit_omission_log():
    """When commit_strategy is absent (defaults to per_plan), no omission log fires."""
    captured: list[str] = []
    original_helper = _mem._log_commit_push_omitted

    def _capture(plan_id):
        captured.append(plan_id)

    _mem._log_commit_push_omitted = _capture
    try:
        with PlanContext(plan_id='matrix-cs-default-nolog'):
            cmd_compose(
                _compose_ns(
                    plan_id='matrix-cs-default-nolog',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    commit_strategy=None,
                )
            )
    finally:
        _mem._log_commit_push_omitted = original_helper
    assert captured == []


def test_commit_strategy_invalid_value_rejected():
    """Invalid commit_strategy values produce a structured error response."""
    with PlanContext(plan_id='matrix-cs-bad'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-cs-bad',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=2,
                commit_strategy='nope',
            )
        )
        assert result is not None and result['status'] == 'error'
        assert result['error'] == 'invalid_commit_strategy'


def test_commit_strategy_none_with_recipe_still_drops_commit_push():
    """Pre-filter applies before the row matrix — recipe rule still loses commit-push."""
    with PlanContext(plan_id='matrix-cs-recipe'):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-cs-recipe',
                change_type='tech_debt',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=2,
                commit_strategy='none',
            )
        )
        assert result is not None and result['rule_fired'] == 'recipe'
        manifest = read_manifest('matrix-cs-recipe')
        assert manifest is not None
        assert 'commit-push' not in manifest['phase_6']['steps']


def test_commit_strategy_none_with_prefixed_input_drops_commit_push_and_pre_push():
    """Regression — _apply_commit_strategy_none drops both gates with prefixed input.

    Pins the latent bug fixed by lesson ``2026-04-27-23-004``: before boundary
    normalization, ``_apply_commit_strategy_none`` compared candidate entries
    against the bare-name set ``{commit-push, pre-push-quality-gate,
    pre-submission-self-review}``. When ``marshal.json`` emitted prefixed
    candidates (e.g., ``default:commit-push``), the comparison silently failed
    and the gate steps survived in the manifest despite ``commit_strategy=none``.

    Boundary normalization in ``cmd_compose`` strips the ``default:`` prefix
    once at intake, so ``_apply_commit_strategy_none`` now sees bare strings
    and the membership check works regardless of how the caller spelled the
    candidate IDs. This test feeds a fully prefixed candidate list to
    ``cmd_compose`` with ``commit_strategy=none`` and asserts both gate steps
    are dropped and the manifest output is bare.
    """
    prefixed = [
        'default:pre-push-quality-gate',
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='cs-none-prefixed'):
        result = cmd_compose(
            _compose_ns(
                plan_id='cs-none-prefixed',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                phase_6_steps=','.join(prefixed),
                commit_strategy='none',
            )
        )
        assert result is not None and result['status'] == 'success'
        # commit_push omitted flag is True — pre-filter fired on the prefixed input.
        assert result['commit_push_omitted'] is True

        manifest = read_manifest('cs-none-prefixed')
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Both gate steps are dropped (the latent bug — they would have
        # survived as `default:commit-push` / `default:pre-push-quality-gate`
        # before the boundary normalization landed).
        assert 'commit-push' not in steps
        assert 'pre-push-quality-gate' not in steps

        # Output is bare — no `default:` prefix anywhere.
        assert not any(s.startswith('default:') for s in steps), f'phase_6 leaked `default:`-prefixed entry: {steps!r}'

        # Other steps from the input survive as bare strings.
        for kept in (
            'create-pr',
            'automated-review',
            'lessons-capture',
            'branch-cleanup',
            'archive-plan',
        ):
            assert kept in steps, f'expected bare {kept!r} in phase_6 but got: {steps!r}'


# =============================================================================
# CLI plumbing (subprocess) tests — keep small, just confirm wiring
# =============================================================================


def test_cli_compose_then_read_roundtrip():
    with PlanContext(plan_id='cli-rt'):
        result = run_script(
            SCRIPT_PATH,
            'compose',
            '--plan-id',
            'cli-rt',
            '--change-type',
            'feature',
            '--track',
            'complex',
            '--scope-estimate',
            'multi_module',
            '--affected-files-count',
            '10',
        )
        assert result.success, f'compose failed: stderr={result.stderr!r}'
        compose_data = result.toon()
        assert compose_data['status'] == 'success'

        read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-rt')
        assert read_result.success
        read_data = read_result.toon()
        assert read_data['plan_id'] == 'cli-rt'
        assert read_data['manifest_version'] == 1


def test_cli_compose_invalid_change_type_emits_toon_error():
    with PlanContext(plan_id='cli-bad'):
        result = run_script(
            SCRIPT_PATH,
            'compose',
            '--plan-id',
            'cli-bad',
            '--change-type',
            'nonsense',
            '--track',
            'simple',
            '--scope-estimate',
            'surgical',
        )
        # Script exits 0 on validation errors (TOON contract); error in stdout.
        assert result.returncode == 0
        data = result.toon()
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_change_type'


def test_cli_compose_with_all_optional_flags_roundtrips():
    """CLI accepts --recipe-key, --affected-files-count, and both step CSVs."""
    with PlanContext(plan_id='cli-allflags'):
        result = run_script(
            SCRIPT_PATH,
            'compose',
            '--plan-id',
            'cli-allflags',
            '--change-type',
            'tech_debt',
            '--track',
            'simple',
            '--scope-estimate',
            'surgical',
            '--recipe-key',
            'lesson_cleanup',
            '--affected-files-count',
            '2',
            '--phase-5-steps',
            'quality-gate,module-tests',
            '--phase-6-steps',
            'commit-push,create-pr,branch-cleanup',
        )
        assert result.success, f'compose failed: stderr={result.stderr!r}'
        data = result.toon()
        assert data['status'] == 'success'
        assert data['rule_fired'] == 'recipe'


def test_cli_validate_happy_path():
    """validate via CLI returns status=success TOON."""
    with PlanContext(plan_id='cli-val-ok'):
        compose = run_script(
            SCRIPT_PATH,
            'compose',
            '--plan-id',
            'cli-val-ok',
            '--change-type',
            'feature',
            '--track',
            'complex',
            '--scope-estimate',
            'multi_module',
        )
        assert compose.success

        result = run_script(
            SCRIPT_PATH,
            'validate',
            '--plan-id',
            'cli-val-ok',
            '--phase-5-steps',
            'quality-gate,module-tests',
            '--phase-6-steps',
            ','.join(DEFAULT_PHASE_6_STEPS),
        )
        assert result.success
        data = result.toon()
        assert data['status'] == 'success'
        # TOON parser may coerce booleans — accept both shapes defensively.
        assert data['valid'] in (True, 'true', 1)


def test_cli_compose_commit_strategy_none_omits_commit_push():
    """CLI accepts --commit-strategy none and emits a manifest without commit-push."""
    with PlanContext(plan_id='cli-cs-none'):
        result = run_script(
            SCRIPT_PATH,
            'compose',
            '--plan-id',
            'cli-cs-none',
            '--change-type',
            'feature',
            '--track',
            'complex',
            '--scope-estimate',
            'multi_module',
            '--commit-strategy',
            'none',
        )
        assert result.success, f'compose failed: stderr={result.stderr!r}'
        compose_data = result.toon()
        assert compose_data['status'] == 'success'
        # TOON parser may coerce the bool — accept both shapes defensively.
        assert compose_data['commit_push_omitted'] in (True, 'true', 1)

        read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-cs-none')
        assert read_result.success
        manifest = read_result.toon()
        assert 'commit-push' not in manifest['phase_6']['steps']


def test_cli_read_missing_manifest_emits_toon_error():
    """read without a prior compose emits file_not_found via TOON."""
    with PlanContext(plan_id='cli-no-manifest'):
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-no-manifest')
        # Script exits 0 on missing-file errors (TOON contract).
        assert result.returncode == 0
        data = result.toon()
        assert data['status'] == 'error'
        assert data['error'] == 'file_not_found'


# =============================================================================
# pre-push-quality-gate pre-filter tests
# =============================================================================


def _write_marshal(
    ctx: PlanContext, *, activation_globs: list[str] | None = None, include_pre_push_key: bool = True
) -> None:
    """Write a marshal.json with the given activation_globs configuration.

    When ``include_pre_push_key`` is False, the ``pre_push_quality_gate`` key is
    omitted entirely (simulating the "absent" branch). When ``activation_globs``
    is None and the key is present, the inner ``activation_globs`` field is
    omitted (also "absent").
    """
    assert ctx.fixture_dir is not None
    marshal_path = ctx.fixture_dir / 'marshal.json'
    data: dict = {'plan': {'phase-6-finalize': {}}}
    if include_pre_push_key:
        pre_push: dict = {}
        if activation_globs is not None:
            pre_push['activation_globs'] = activation_globs
        data['plan']['phase-6-finalize']['pre_push_quality_gate'] = pre_push
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


def _write_references(ctx: PlanContext, modified_files: list[str]) -> None:
    """Write a references.json containing the given ``modified_files`` list."""
    assert ctx.plan_dir is not None
    refs_path = ctx.plan_dir / 'references.json'
    refs_path.write_text(json.dumps({'modified_files': modified_files}), encoding='utf-8')


def _candidate_phase_6_with_pre_push() -> str:
    """Return a Phase 6 candidate CSV that includes pre-push-quality-gate.

    The default candidate set does NOT include pre-push-quality-gate, so tests
    that exercise the pre-filter must opt the step in via the candidate CSV.
    """
    return ','.join(list(DEFAULT_PHASE_6_STEPS) + ['pre-push-quality-gate'])


class TestPrePushQualityGatePreFilter:
    """Activation-driven pre-filter for ``pre-push-quality-gate``.

    Each test asserts BOTH the resulting ``phase_6.steps`` content AND the
    decision-log line presence/absence. The decision-log emitter is patched on
    ``_mem._emit_decision_log`` and entries are captured into a list per test.
    """

    _OMIT_LINE = (
        '(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — '
        'activation_globs empty or no modified_files match'
    )

    @staticmethod
    def _capture_decision_log() -> tuple[list[tuple[str, str]], Callable[[str, str], None]]:
        """Install a capturing replacement for ``_emit_decision_log``.

        Returns the capture list plus the original function so the caller can
        restore it in a ``finally`` block.
        """
        captured: list[tuple[str, str]] = []
        original = _mem._emit_decision_log

        def _capture(plan_id: str, message: str) -> None:
            captured.append((plan_id, message))

        _mem._emit_decision_log = _capture
        return captured, original

    @classmethod
    def _omit_entries(cls, captured: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [entry for entry in captured if entry[1] == cls._OMIT_LINE]

    def test_omit_when_activation_globs_absent(self):
        """Config key missing → step removed and omission line emitted."""
        plan_id = 'pp-globs-absent'
        with PlanContext(plan_id=plan_id) as ctx:
            # marshal.json exists but lacks the pre_push_quality_gate key entirely.
            _write_marshal(ctx, include_pre_push_key=False)
            _write_references(ctx, ['marketplace/bundles/plan-marshall/skills/foo.py'])

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=4,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['status'] == 'success'
            assert result['pre_push_quality_gate_omitted'] is True
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
            # All other DEFAULT_PHASE_6_STEPS preserved.
            for step in DEFAULT_PHASE_6_STEPS:
                assert step in manifest['phase_6']['steps']
            omit_entries = self._omit_entries(captured)
            assert len(omit_entries) == 1
            assert omit_entries[0][0] == plan_id

    def test_omit_when_activation_globs_empty(self):
        """activation_globs: [] → same behavior as missing config."""
        plan_id = 'pp-globs-empty'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=[])
            _write_references(ctx, ['marketplace/bundles/plan-marshall/skills/foo.py'])

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=4,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['pre_push_quality_gate_omitted'] is True
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
            for step in DEFAULT_PHASE_6_STEPS:
                assert step in manifest['phase_6']['steps']
            assert len(self._omit_entries(captured)) == 1

    def test_omit_when_modified_files_empty(self):
        """Globs configured but references.modified_files empty → step removed."""
        plan_id = 'pp-mod-empty'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=['marketplace/bundles/**/*.py'])
            _write_references(ctx, [])  # empty list

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=4,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['pre_push_quality_gate_omitted'] is True
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
            assert len(self._omit_entries(captured)) == 1

    def test_omit_when_no_glob_matches(self):
        """Globs configured, modified_files contains only non-matching paths → step removed."""
        plan_id = 'pp-no-match'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=['marketplace/bundles/**/*.py'])
            # All paths fall outside marketplace/bundles/.
            _write_references(ctx, ['doc/readme.md', 'CHANGELOG.txt'])

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=2,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['pre_push_quality_gate_omitted'] is True
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
            assert len(self._omit_entries(captured)) == 1

    def test_keep_when_glob_matches(self):
        """At least one modified_file matches → step retained, no omission line."""
        plan_id = 'pp-match'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=['marketplace/bundles/**/*.py'])
            _write_references(
                ctx,
                [
                    'doc/readme.md',  # non-match
                    'marketplace/bundles/plan-marshall/skills/foo.py',  # match
                ],
            )

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=2,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['pre_push_quality_gate_omitted'] is False
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' in manifest['phase_6']['steps']
            # No omission entry emitted.
            assert self._omit_entries(captured) == []

    def test_commit_strategy_none_strips_pre_push_too(self):
        """commit_strategy=none strips both commit-push and pre-push-quality-gate.

        The commit-strategy pre-filter runs FIRST and removes both steps, so the
        downstream pre-push-quality-gate filter sees the step already gone and
        is a no-op (no omission line emitted by the pre-push filter, regardless
        of glob match).
        """
        plan_id = 'pp-cs-none'
        with PlanContext(plan_id=plan_id) as ctx:
            # Configure globs and matching modified_files — the gate WOULD be
            # active, but commit_strategy=none must strip it anyway.
            _write_marshal(ctx, activation_globs=['marketplace/bundles/**/*.py'])
            _write_references(ctx, ['marketplace/bundles/plan-marshall/skills/foo.py'])

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=4,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                        commit_strategy='none',
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['status'] == 'success'
            assert result['commit_push_omitted'] is True
            # The pre-push-quality-gate filter is a no-op once commit-push
            # filter has already removed the step.
            assert result['pre_push_quality_gate_omitted'] is False
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'commit-push' not in manifest['phase_6']['steps']
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
            # Pre-push-quality-gate omission line is NOT emitted (commit-push
            # filter handled the removal).
            assert self._omit_entries(captured) == []

    def test_pre_filter_order_independent_of_seven_row_matrix(self):
        """Pre-filter runs before Row 1/Row 2/Row 7 — observable via decision-log ordering.

        The composer calls (in order):
          1. _apply_commit_strategy_none
          2. _apply_pre_push_quality_gate_inactive
          3. _decide() — which selects a row (Row 1: early_terminate, Row 2:
             recipe, Row 7: default, etc.)
          4. _log_commit_push_omitted (if fired)
          5. _log_pre_push_quality_gate_omitted (if fired)
          6. _log_decision (always — rule line)

        Even though log emission happens after _decide, the row matrix already
        sees the filtered candidate list, which means the omission line MUST be
        captured before the rule line, and the rule line MUST reflect the
        absence of pre-push-quality-gate from phase_6.steps.

        This test temporarily replaces ``_log_decision`` (which the module-level
        setup stubs out for speed) with a capturing implementation that mirrors
        the production message contract, so the rule-fired line is observable.
        """
        plan_id = 'pp-order'
        with PlanContext(plan_id=plan_id) as ctx:
            # Activation_globs absent → pre-filter fires.
            _write_marshal(ctx, include_pre_push_key=False)
            _write_references(ctx, ['marketplace/bundles/plan-marshall/skills/foo.py'])

            captured: list[tuple[str, str]] = []
            original_emit = _mem._emit_decision_log
            original_log_decision = _mem._log_decision

            def _capture(plan_id_: str, message: str) -> None:
                captured.append((plan_id_, message))

            # Capturing replacement for _log_decision that mirrors the contract
            # in scripts/manage-execution-manifest.py::_log_decision().
            def _log_decision_capture(plan_id_, rule, body):
                phase_5 = body.get('phase_5', {})
                phase_6 = body.get('phase_6', {})
                p5_steps = phase_5.get('verification_steps', [])
                p6_steps = phase_6.get('steps', [])
                early = phase_5.get('early_terminate', False)
                message = (
                    f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
                    f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
                    f'phase_6.steps={p6_steps}'
                )
                _capture(plan_id_, message)

            _mem._emit_decision_log = _capture
            _mem._log_decision = _log_decision_capture
            try:
                # Use a Row 7 (default) shape — feature + multi_module + files.
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=10,
                        phase_6_steps=_candidate_phase_6_with_pre_push(),
                    )
                )
            finally:
                _mem._emit_decision_log = original_emit
                _mem._log_decision = original_log_decision

            assert result is not None and result['rule_fired'] == 'default'
            assert result['pre_push_quality_gate_omitted'] is True

            # Ordering: omission line precedes rule-fired line.
            messages = [msg for _, msg in captured]
            omit_idx = next(
                (i for i, m in enumerate(messages) if m == self._OMIT_LINE),
                None,
            )
            rule_idx = next(
                (i for i, m in enumerate(messages) if 'Rule default fired' in m),
                None,
            )
            assert omit_idx is not None, f'omission line missing in {messages!r}'
            assert rule_idx is not None, f'rule line missing in {messages!r}'
            assert omit_idx < rule_idx, (
                f'pre-filter omission line must precede rule line; got omit_idx={omit_idx}, rule_idx={rule_idx}'
            )

            # Rule line reflects filtered phase_6.steps (no pre-push-quality-gate).
            rule_msg = messages[rule_idx]
            assert 'pre-push-quality-gate' not in rule_msg

            # Manifest content also reflects the pre-filter outcome.
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']

    # =========================================================================
    # Boundary-normalization regression cases (lesson 2026-04-27-23-004)
    #
    # The activation-failure branches of ``_apply_pre_push_quality_gate_inactive``
    # compare candidate entries against the bare literal
    # ``'pre-push-quality-gate'``. Before boundary normalization landed, a
    # ``default:pre-push-quality-gate`` candidate would silently bypass the
    # filter — the membership check ``'pre-push-quality-gate' in candidates``
    # returned ``False`` even with the prefixed entry in the list, so the gate
    # survived the manifest with the prefix attached.
    #
    # Boundary normalization in ``cmd_compose`` strips the ``default:`` prefix
    # at intake, so the pre-filter sees bare names regardless of how the
    # caller spelled the candidate IDs. These regressions exercise all three
    # activation-failure branches with a fully prefixed input list and assert
    # the gate is dropped + the manifest output is bare.
    # =========================================================================

    def test_omit_when_activation_globs_empty_with_prefixed_input(self):
        """Regression — activation_globs=[] drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-globs-empty'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:commit-push',
            'default:create-pr',
            'default:archive-plan',
        ]
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=[])
            _write_references(ctx, ['marketplace/bundles/plan-marshall/skills/foo.py'])

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=4,
                        phase_6_steps=','.join(prefixed),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['status'] == 'success'
            assert result['pre_push_quality_gate_omitted'] is True

            manifest = read_manifest(plan_id)
            assert manifest is not None
            steps = manifest['phase_6']['steps']

            # Gate dropped despite prefixed input — boundary normalization
            # made the membership check work.
            assert 'pre-push-quality-gate' not in steps
            assert 'default:pre-push-quality-gate' not in steps

            # Output is fully bare.
            assert not any(s.startswith('default:') for s in steps), (
                f'phase_6 leaked `default:`-prefixed entry: {steps!r}'
            )

            # Other steps from the input survive as bare strings.
            for kept in ('commit-push', 'create-pr', 'archive-plan'):
                assert kept in steps

            # Omission line emitted exactly once.
            assert len(self._omit_entries(captured)) == 1

    def test_omit_when_modified_files_empty_with_prefixed_input(self):
        """Regression — empty modified_files drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-mod-empty'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:commit-push',
            'default:create-pr',
            'default:archive-plan',
        ]
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=['marketplace/bundles/**/*.py'])
            _write_references(ctx, [])  # empty list

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=4,
                        phase_6_steps=','.join(prefixed),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['pre_push_quality_gate_omitted'] is True

            manifest = read_manifest(plan_id)
            assert manifest is not None
            steps = manifest['phase_6']['steps']

            assert 'pre-push-quality-gate' not in steps
            assert 'default:pre-push-quality-gate' not in steps
            assert not any(s.startswith('default:') for s in steps)

            assert len(self._omit_entries(captured)) == 1

    def test_omit_when_no_glob_matches_with_prefixed_input(self):
        """Regression — non-matching modified_files drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-no-match'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:commit-push',
            'default:create-pr',
            'default:archive-plan',
        ]
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal(ctx, activation_globs=['marketplace/bundles/**/*.py'])
            # All paths fall outside the configured glob.
            _write_references(ctx, ['doc/readme.md', 'CHANGELOG.txt'])

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=2,
                        phase_6_steps=','.join(prefixed),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None and result['pre_push_quality_gate_omitted'] is True

            manifest = read_manifest(plan_id)
            assert manifest is not None
            steps = manifest['phase_6']['steps']

            assert 'pre-push-quality-gate' not in steps
            assert 'default:pre-push-quality-gate' not in steps
            assert not any(s.startswith('default:') for s in steps)

            assert len(self._omit_entries(captured)) == 1


# =============================================================================
# Bot-Enforcement Guard — Remediation behavior (lesson 2026-04-28-10-001)
#
# When ci.provider is github or gitlab AND `automated-review` is missing from
# the assembled phase_6.steps (e.g., dropped by Row 5 surgical_bug_fix /
# surgical_tech_debt), the guard appends `default:automated-review` back into
# the list and emits a decision-log entry. The composition continues normally;
# no `bot_enforcement_violation` error is raised. Row 5's other subtractions
# (`sonar-roundtrip`) stay dropped — the guard remediates
# only `automated-review`.
#
# Row 5 + no CI provider configured remains the baseline: the guard is a
# no-op and `automated-review` stays dropped. The existing
# test_surgical_bug_fix_trims_heavy_review_steps and
# test_surgical_tech_debt_trims_heavy_review_steps cover that path.
# =============================================================================


def _write_marshal_with_ci(ctx: PlanContext, *, provider: str) -> None:
    """Write a marshal.json that configures ``ci.provider`` for the guard's lookup.

    The bot-enforcement guard reads ``data['ci']['provider']`` from the project's
    ``marshal.json``. Tests for the github/gitlab branch must materialize this
    field; the no-CI baseline simply omits it.
    """
    assert ctx.fixture_dir is not None
    marshal_path = ctx.fixture_dir / 'marshal.json'
    data: dict = {'ci': {'provider': provider}, 'plan': {'phase-6-finalize': {}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


_REMEDIATION_LINE_TEMPLATE = (
    '(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard remediated — '
    'ci_provider={provider}, automated-review re-added to phase_6.steps'
)


class TestBotEnforcementGuardRemediation:
    """Row 5 + ci.provider in {github, gitlab}: guard remediates instead of asserting."""

    @staticmethod
    def _capture_decision_log() -> tuple[list[tuple[str, str]], Callable[[str, str], None]]:
        captured: list[tuple[str, str]] = []
        original = _mem._emit_decision_log

        def _capture(plan_id: str, message: str) -> None:
            captured.append((plan_id, message))

        _mem._emit_decision_log = _capture
        return captured, original

    @classmethod
    def _remediation_messages(cls, captured: list[tuple[str, str]], provider: str) -> list[tuple[str, str]]:
        line = _REMEDIATION_LINE_TEMPLATE.format(provider=provider)
        return [entry for entry in captured if entry[1] == line]

    @staticmethod
    def _compose_row_5(plan_id: str, change_type: str, *, prefixed_candidates: bool) -> dict:
        """Compose a Row 5 manifest with default-prefixed or bare candidates.

        Both shapes are exercised because phase_6_candidates can arrive prefixed
        from marshal.json or bare from DEFAULT_PHASE_6_STEPS, and Row 5 plus the
        guard must work consistently on both.
        """
        if prefixed_candidates:
            phase_6 = ','.join(_PREFIXED_PHASE_6 + ('default:sonar-roundtrip',))
        else:
            phase_6 = None  # use DEFAULT_PHASE_6_STEPS via _compose_ns default
        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type=change_type,
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=phase_6,
            )
        )
        assert result is not None
        return result

    def _assert_remediation(
        self,
        provider: str,
        change_type: str,
        rule_fired: str,
        *,
        prefixed_candidates: bool,
    ) -> None:
        # Plan IDs must be kebab-case — convert change_type's underscore to hyphen.
        change_type_kebab = change_type.replace('_', '-')
        plan_id = f'guard-remediate-{provider}-{change_type_kebab}-{"prefixed" if prefixed_candidates else "bare"}'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal_with_ci(ctx, provider=provider)

            captured, original = self._capture_decision_log()
            try:
                result = self._compose_row_5(plan_id, change_type, prefixed_candidates=prefixed_candidates)
            finally:
                _mem._emit_decision_log = original

            # (a) Composition succeeds — no bot_enforcement_violation.
            assert result['status'] == 'success'
            assert result['rule_fired'] == rule_fired

            manifest = read_manifest(plan_id)
            assert manifest is not None
            steps = manifest['phase_6']['steps']

            # (b) automated-review is back in phase_6.steps after remediation.
            #     Guard appends `default:automated-review`; tests assert via
            #     prefix-aware membership so both candidate shapes pass.
            bare_step_names = {s[len('default:') :] if s.startswith('default:') else s for s in steps}
            assert 'automated-review' in bare_step_names

            # (c) Row 5's other subtractions are still dropped — only
            #     automated-review is remediated.
            assert 'sonar-roundtrip' not in bare_step_names

            # (d) Decision-log records the remediation exactly once.
            remediations = self._remediation_messages(captured, provider)
            assert len(remediations) == 1, (
                f'expected exactly one remediation log entry for {provider}, '
                f'got {len(remediations)}: {[m for _, m in captured]!r}'
            )
            assert remediations[0][0] == plan_id

    # --- Row 5 surgical_bug_fix variants ---

    def test_github_surgical_bug_fix_remediates_with_default_candidates(self):
        """Row 5 surgical_bug_fix + ci.provider=github (bare candidates) → remediation."""
        self._assert_remediation('github', 'bug_fix', 'surgical_bug_fix', prefixed_candidates=False)

    def test_gitlab_surgical_bug_fix_remediates_with_default_candidates(self):
        """Row 5 surgical_bug_fix + ci.provider=gitlab (bare candidates) → remediation."""
        self._assert_remediation('gitlab', 'bug_fix', 'surgical_bug_fix', prefixed_candidates=False)

    def test_github_surgical_bug_fix_remediates_with_prefixed_candidates(self):
        """Row 5 surgical_bug_fix + ci.provider=github (default:-prefixed candidates) → remediation."""
        self._assert_remediation('github', 'bug_fix', 'surgical_bug_fix', prefixed_candidates=True)

    # --- Row 5 surgical_tech_debt variants ---

    def test_github_surgical_tech_debt_remediates_with_default_candidates(self):
        """Row 5 surgical_tech_debt + ci.provider=github (bare candidates) → remediation."""
        self._assert_remediation('github', 'tech_debt', 'surgical_tech_debt', prefixed_candidates=False)

    def test_gitlab_surgical_tech_debt_remediates_with_default_candidates(self):
        """Row 5 surgical_tech_debt + ci.provider=gitlab (bare candidates) → remediation."""
        self._assert_remediation('gitlab', 'tech_debt', 'surgical_tech_debt', prefixed_candidates=False)

    def test_github_surgical_tech_debt_remediates_with_prefixed_candidates(self):
        """Row 5 surgical_tech_debt + ci.provider=github (default:-prefixed candidates) → remediation."""
        self._assert_remediation('github', 'tech_debt', 'surgical_tech_debt', prefixed_candidates=True)

    # --- Guard is a no-op when automated-review already present ---

    def test_github_default_rule_no_remediation_when_automated_review_present(self):
        """Guard is a no-op on the default rule (Row 7) — automated-review survives untouched."""
        plan_id = 'guard-noop-github-default'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal_with_ci(ctx, provider='github')

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=10,
                    )
                )
            finally:
                _mem._emit_decision_log = original

            assert result is not None
            assert result['status'] == 'success'
            assert result['rule_fired'] == 'default'

            # automated-review is in the default candidate set and Row 7 keeps
            # the candidates as-is, so it's already present and the guard is
            # a no-op (no remediation log entry).
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'automated-review' in manifest['phase_6']['steps']
            assert self._remediation_messages(captured, 'github') == []

    def test_github_default_rule_with_prefixed_candidates_keeps_automated_review_bare_without_violation(self):
        """Regression: prefixed phase_6 candidates on GitHub CI must not trip the guard.

        Lesson ``2026-04-28-10-001`` originally reported that prefixed inputs
        (``default:automated-review`` and friends) raised
        ``bot_enforcement_violation`` because the guard's bare-name membership
        check at line 829 of ``manage-execution-manifest.py`` did not see the
        prefixed entry. The defect was fixed by two upstream changes:

        1. PR #303 (``0362bcaf``) converted ``_apply_bot_enforcement_guard``
           from assertion-style to remediation-style, so the
           ``bot_enforcement_violation`` error branch is unreachable on the
           composition-time path.
        2. PR #305 (``a5231b8b``) added boundary normalization at
           ``cmd_compose`` lines 976-977 — every leading ``default:`` is
           stripped from ``phase_6_candidates`` once at intake, so by the time
           the guard's ``'automated-review' in phase_6_steps`` membership
           check runs, every entry is already bare.

        This test pins both fixes by feeding a fully-prefixed candidate list
        (``_PREFIXED_PHASE_6`` — every entry carries ``default:``, including
        ``default:automated-review``) on a GitHub-CI plan with a Row 7
        (default) shape. Row 7 preserves the candidates verbatim modulo
        boundary normalization, so any regression of either fix shows up here:

        - If boundary normalization at lines 976-977 is removed, the guard's
          bare-name membership check fails to find ``automated-review``, the
          guard appends a duplicate, and the `assert exactly-one` below trips.
        - If ``_strip_default_prefix`` at line 118 is neutered, the same
          duplicate-append path fires.
        - If a future contributor reverts the guard from remediation back to
          assertion, ``status`` becomes ``error`` and the
          ``bot_enforcement_violation`` assertion below trips.
        - If ``automated-review`` is mispositioned (e.g., after
          ``archive-plan``), the placement validator emits its own
          ``bot_enforcement_violation`` and the same assertion catches it.
        """
        plan_id = 'guard-noop-github-default-prefixed'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal_with_ci(ctx, provider='github')

            captured, original = self._capture_decision_log()
            try:
                result = cmd_compose(
                    _compose_ns(
                        plan_id=plan_id,
                        change_type='feature',
                        scope_estimate='multi_module',
                        affected_files_count=10,
                        # Fully-prefixed candidate list — boundary normalization
                        # at cmd_compose intake must strip every `default:` once
                        # so the guard sees bare names.
                        phase_6_steps=','.join(_PREFIXED_PHASE_6),
                    )
                )
            finally:
                _mem._emit_decision_log = original

            # (a) Composition succeeds — the lesson's original symptom
            #     (``bot_enforcement_violation`` on prefixed inputs) does not
            #     reproduce.
            assert result is not None
            assert result['status'] == 'success', (
                f'expected success on GitHub CI + prefixed candidates, '
                f'got error: {result!r}'
            )
            assert result['rule_fired'] == 'default'

            manifest = read_manifest(plan_id)
            assert manifest is not None
            steps = manifest['phase_6']['steps']

            # (b) No `default:`-prefixed entry survives anywhere — boundary
            #     normalization is the only sanctioned strip site.
            assert not any(s.startswith('default:') for s in steps), (
                f'phase_6 leaked `default:`-prefixed entry: {steps!r}'
            )

            # (c) Exactly one bare ``automated-review`` entry — the guard's
            #     membership check did not double-add it.
            assert steps.count('automated-review') == 1, (
                f'expected exactly one automated-review entry, '
                f'got {steps.count("automated-review")}: {steps!r}'
            )

            # (d) ``automated-review`` precedes every plan-mutating anchor.
            #     Mirrors ``_validate_automated_review_placement``'s contract.
            review_index = steps.index('automated-review')
            for anchor in ('archive-plan', 'record-metrics', 'branch-cleanup'):
                if anchor in steps:
                    assert steps.index(anchor) > review_index, (
                        f'automated-review (index {review_index}) must precede '
                        f'plan-mutating anchor {anchor!r} (index {steps.index(anchor)}): '
                        f'{steps!r}'
                    )

            # (e) Guard did not need to remediate — automated-review was
            #     present after boundary normalization, so no remediation log.
            assert self._remediation_messages(captured, 'github') == [], (
                f'expected no remediation log entries, got: '
                f'{[m for _, m in captured]!r}'
            )


# =============================================================================
# Compose-time placement validator (lesson 2026-04-28-13-002)
#
# The remediation guard guarantees ``automated-review`` is *present* on
# GitHub/GitLab plans, but a future pre-filter or recipe interaction could
# leave it *misplaced* — sitting at an index later than a plan-mutating step
# (``archive-plan``, ``record-metrics``, ``branch-cleanup``, or
# ``plan-marshall:plan-retrospective``). The new ``_validate_automated_review_placement``
# check rejects such manifests with ``status='error'`` and
# ``error='bot_enforcement_violation'``. The diagnostic carries both step
# names so downstream auditing can pinpoint the ordering breach.
#
# Construction trick: the bot-enforcement remediation guard returns early on
# its membership check (``'automated-review' in phase_6_steps``) and therefore
# does NOT reposition a misplaced occurrence. To exercise the validator we
# pass an explicit ``--phase-6-steps`` candidate list where ``automated-review``
# is already present in the wrong position; Row 7 (default) preserves the
# candidate ordering verbatim, the guard is a no-op, and the misplacement
# survives to the validator.
# =============================================================================


class TestAutomatedReviewPlacement:
    """Compose-time validator rejects ``automated-review`` after plan-mutating anchors."""

    @staticmethod
    def _candidates_with_review_after(anchor: str) -> str:
        """Build a phase_6 candidate CSV where ``automated-review`` follows ``anchor``.

        The candidate list mirrors the canonical ordering for the steps that
        always remain (commit-push, create-pr, lessons-capture) so the manifest
        is otherwise plausible; only the ``automated-review`` / ``anchor`` pair
        is deliberately misordered. The anchor is inserted before
        ``automated-review`` so the validator's earliest-anchor scan returns
        precisely the parametrized name.
        """
        return ','.join(['commit-push', 'create-pr', 'lessons-capture', anchor, 'automated-review'])

    def test_compose_rejects_automated_review_after_archive_plan(self):
        """Misplaced ``automated-review`` after ``archive-plan`` → bot_enforcement_violation."""
        plan_id = 'placement-archive-plan'
        with PlanContext(plan_id=plan_id) as ctx:
            # GitHub provider so the existing remediation guard runs but
            # short-circuits on the membership check (line 845), leaving the
            # misplacement intact for the new validator to catch.
            _write_marshal_with_ci(ctx, provider='github')

            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=5,
                    phase_6_steps=self._candidates_with_review_after('archive-plan'),
                )
            )

            assert result is not None
            assert result['status'] == 'error', f'expected error status, got {result!r}'
            assert result['error'] == 'bot_enforcement_violation'
            # Diagnostic must name BOTH step identifiers so downstream auditing
            # can pinpoint the ordering breach without re-deriving it.
            assert 'automated-review' in result['message']
            assert 'archive-plan' in result['message']
            # No manifest is persisted on rejection — read_manifest returns None.
            assert read_manifest(plan_id) is None

    @pytest.mark.parametrize(
        'anchor',
        ['record-metrics', 'branch-cleanup', 'plan-marshall:plan-retrospective'],
    )
    def test_compose_rejects_automated_review_after_other_plan_mutating_steps(self, anchor: str):
        """Misplaced ``automated-review`` after each remaining anchor → bot_enforcement_violation.

        Parametrized over the three plan-mutating anchors NOT covered by the
        ``archive-plan`` test above. Together these cover the full anchor set
        in ``_validate_automated_review_placement``'s ``plan_mutating`` set:
        ``archive-plan``, ``record-metrics``, ``branch-cleanup``,
        ``plan-marshall:plan-retrospective``.
        """
        # Plan IDs must be kebab-case; the colon-prefixed retrospective anchor
        # would otherwise leak a ``:`` into the directory name.
        anchor_slug = anchor.replace(':', '-').replace('plan-marshall-', 'pm-')
        plan_id = f'placement-{anchor_slug}'
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal_with_ci(ctx, provider='github')

            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=5,
                    phase_6_steps=self._candidates_with_review_after(anchor),
                )
            )

            assert result is not None
            assert result['status'] == 'error', f'expected error status for anchor={anchor!r}, got {result!r}'
            assert result['error'] == 'bot_enforcement_violation'
            assert 'automated-review' in result['message']
            assert anchor in result['message']
            assert read_manifest(plan_id) is None
