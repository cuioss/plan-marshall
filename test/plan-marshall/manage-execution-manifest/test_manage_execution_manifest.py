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
        # Phase 6 keeps the records-and-archive triad.
        assert result['phase_6']['steps_count'] == 3


def test_recipe_path_drops_heavy_review_steps():
    """Row 2 — recipe_key present → drop automated-review/sonar-roundtrip/knowledge-capture."""
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
        assert 'knowledge-capture' not in manifest['phase_6']['steps']
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
        for stripped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
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
        for stripped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
            assert stripped not in manifest['phase_6']['steps']


# =============================================================================
# Prefix-Normalization Regression Tests
#
# `phase_6_candidates` may arrive prefixed (`default:foo` from marshal.json's
# step registry) or bare (`foo` from DEFAULT_PHASE_6_STEPS). The cascade-rule
# filters in `_decide` previously compared candidates against bare-name literal
# sets, so prefixed candidates silently bypassed the filters and heavy steps
# survived in surgical/recipe manifests. The fix wraps the comparison side in
# `_strip_default_prefix` so both shapes match.
#
# These tests pass prefixed candidates and assert that each affected rule
# (Rule 1, 2, 3, 5, 6) drops or includes the right bare-named steps. They
# would have failed before the fix because the filters were no-ops on the
# prefixed input.
# =============================================================================


_PREFIXED_PHASE_6 = (
    'default:pre-push-quality-gate',
    'default:commit-push',
    'default:create-pr',
    'default:automated-review',
    'default:knowledge-capture',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:archive-plan',
)


def _all_default_prefixed(steps):
    """Return the bare-name suffixes of any `default:`-prefixed steps in `steps`."""
    return {s[len('default:'):] for s in steps if s.startswith('default:')}


def test_rule_1_early_terminate_analysis_with_prefixed_candidates():
    """Rule 1 (early_terminate_analysis) — prefixed candidates: include only knowledge/lessons/archive."""
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
        # Only the include-set survives, prefix preserved verbatim.
        bare_names = _all_default_prefixed(steps)
        assert bare_names == {'knowledge-capture', 'lessons-capture', 'archive-plan'}
        # Heavy steps that would have leaked through pre-fix are absent.
        for excluded in ('commit-push', 'create-pr', 'automated-review',
                         'pre-push-quality-gate', 'branch-cleanup'):
            assert f'default:{excluded}' not in steps


def test_rule_2_recipe_with_prefixed_candidates():
    """Rule 2 (recipe) — prefixed candidates: drop automated-review/sonar-roundtrip/knowledge-capture."""
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
        # Heavy review steps are dropped (prefix and bare both filtered correctly).
        for dropped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
            assert f'default:{dropped}' not in steps
        # Non-heavy steps survive.
        assert 'default:commit-push' in steps
        assert 'default:create-pr' in steps
        assert 'default:lessons-capture' in steps


def test_rule_3_docs_only_with_prefixed_candidates():
    """Rule 3 (docs_only) — prefixed candidates: drop sonar-roundtrip/automated-review."""
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
        # Review steps dropped.
        for dropped in ('sonar-roundtrip', 'automated-review'):
            assert f'default:{dropped}' not in steps
        # Non-review steps survive.
        assert 'default:commit-push' in steps
        assert 'default:knowledge-capture' in steps
        assert 'default:lessons-capture' in steps


def test_rule_5_surgical_bug_fix_with_prefixed_candidates():
    """Rule 5 (surgical_bug_fix) — prefixed candidates: drop automated-review/sonar-roundtrip/knowledge-capture."""
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
        for dropped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
            assert f'default:{dropped}' not in steps
        assert 'default:lessons-capture' in steps
        assert 'default:commit-push' in steps


def test_rule_5_surgical_tech_debt_with_prefixed_candidates():
    """Rule 5 (surgical_tech_debt) — prefixed candidates: same drop as bug_fix."""
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
        for dropped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
            assert f'default:{dropped}' not in steps
        assert 'default:commit-push' in steps


def test_rule_6_verification_no_files_with_prefixed_candidates():
    """Rule 6 (verification_no_files) — prefixed candidates: include only knowledge/lessons/archive."""
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
        bare_names = _all_default_prefixed(steps)
        assert bare_names == {'knowledge-capture', 'lessons-capture', 'archive-plan'}
        for excluded in ('commit-push', 'create-pr', 'automated-review',
                         'pre-push-quality-gate', 'branch-cleanup'):
            assert f'default:{excluded}' not in steps


def test_prefix_normalization_no_op_for_bare_candidates():
    """Sanity: applying _strip_default_prefix to bare candidates is a no-op.

    The bare-name path (DEFAULT_PHASE_6_STEPS) must continue to work identically.
    Rule 5 with bare candidates exercises the same filter that is now wrapped in
    `_strip_default_prefix(s) not in {...}` — confirms the helper's no-op
    behavior on bare names.
    """
    bare = (
        'commit-push', 'create-pr', 'automated-review', 'sonar-roundtrip',
        'knowledge-capture', 'lessons-capture', 'branch-cleanup', 'archive-plan',
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
        for dropped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
            assert dropped not in steps
        assert 'commit-push' in steps
        assert 'lessons-capture' in steps


def test_bundle_self_modification_inserts_early_sync_before_first_agent_step():
    """bundle_self_modification — agent path triggers extra sync before create-pr.

    The default Phase 6 candidate list (prefixed) places sync-plugin-cache late
    in the order. When `references.modified_files` references a bundled agent,
    the composer must insert a SECOND `project:finalize-step-sync-plugin-cache`
    immediately before the earliest agent-dispatched step (`default:create-pr`).
    The existing late-stage occurrence is preserved verbatim.
    """
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'default:knowledge-capture',
        'default:lessons-capture',
        'default:branch-cleanup',
        'project:finalize-step-sync-plugin-cache',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-agent') as ctx:
        # Write references.json with a bundled agent path before composing.
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            '{"modified_files": ["marketplace/bundles/plan-marshall/agents/automated-review-agent.md"]}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-agent',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == 'default:create-pr'

        manifest = read_manifest('bundle-self-mod-agent')
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Two occurrences of the sync step: one early, one late (preserved).
        assert steps.count('project:finalize-step-sync-plugin-cache') == 2

        # Early occurrence sits immediately before the first agent-dispatched step.
        first_agent_idx = next(
            i for i, s in enumerate(steps)
            if s in ('default:create-pr', 'default:automated-review',
                     'default:knowledge-capture', 'default:lessons-capture')
        )
        assert first_agent_idx >= 1
        assert steps[first_agent_idx - 1] == 'project:finalize-step-sync-plugin-cache'

        # Late occurrence preserved (after branch-cleanup, before archive-plan).
        late_idx = steps.index('project:finalize-step-sync-plugin-cache', first_agent_idx + 1)
        assert steps[late_idx - 1] == 'default:branch-cleanup'


@pytest.mark.parametrize(
    'modified_path,expected_glob_surface',
    [
        ('marketplace/bundles/plan-marshall/commands/marshal.md', 'commands'),
        ('marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py', 'skills'),
        ('marketplace/bundles/pm-dev-java/agents/some-agent.md', 'agents-other-bundle'),
    ],
)
def test_bundle_self_modification_fires_for_command_and_skill_paths(modified_path, expected_glob_surface):
    """bundle_self_modification — commands/ and skills/ paths fire the rule too.

    The rule covers all three bundled surfaces (agents, commands, skills) and
    matches across any bundle name (`marketplace/bundles/*/...`).
    """
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'default:lessons-capture',
        'default:archive-plan',
    ]
    plan_id = f'bundle-self-mod-{expected_glob_surface}'
    with PlanContext(plan_id=plan_id) as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            f'{{"modified_files": ["{modified_path}"]}}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=1,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == 'default:create-pr'

        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Sync step inserted before first agent step.
        create_pr_idx = steps.index('default:create-pr')
        assert steps[create_pr_idx - 1] == 'project:finalize-step-sync-plugin-cache'


def test_bundle_self_modification_skipped_for_non_bundle_paths():
    """bundle_self_modification — non-bundle paths leave the manifest untouched."""
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'project:finalize-step-sync-plugin-cache',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-non-bundle') as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            '{"modified_files": ['
            '"test/plan-marshall/manage-references/test_x.py", '
            '"doc/build-structure.adoc"]}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-non-bundle',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=2,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == ''

        manifest = read_manifest('bundle-self-mod-non-bundle')
        assert manifest is not None
        # Single occurrence only — the original late one, untouched.
        assert manifest['phase_6']['steps'].count('project:finalize-step-sync-plugin-cache') == 1


def test_bundle_self_modification_skipped_when_modified_files_absent():
    """bundle_self_modification — no references.json → no insertion."""
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'project:finalize-step-sync-plugin-cache',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-no-refs'):
        # Intentionally do NOT write references.json.
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-no-refs',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=0,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == ''

        manifest = read_manifest('bundle-self-mod-no-refs')
        assert manifest is not None
        assert manifest['phase_6']['steps'].count('project:finalize-step-sync-plugin-cache') == 1


def test_bundle_self_modification_fires_on_affected_files_alone():
    """bundle_self_modification — affected_files is the canonical pre-execute source.

    `phase-4-plan` Step 8b composes the manifest BEFORE Phase 5 has populated
    `modified_files`. The rule MUST fire from `affected_files` alone so the
    manifest is correct on the first compose for normal plans (regression
    guard for the issue gemini flagged on PR #278).
    """
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-affected-only') as ctx:
        assert ctx.plan_dir is not None
        # Only affected_files populated — modified_files absent (mirrors
        # production phase-4-plan compose-call timing).
        (ctx.plan_dir / 'references.json').write_text(
            '{"affected_files": ["marketplace/bundles/plan-marshall/skills/foo/SKILL.md"]}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-affected-only',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=1,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == 'default:create-pr'


def test_bundle_self_modification_unions_affected_and_modified_files():
    """bundle_self_modification — affected_files and modified_files entries union.

    Both fields are read; the rule fires if EITHER contains a bundle path.
    Distinct entries are de-duplicated by the read helper.
    """
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-union') as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            '{"affected_files": ["doc/notes.md"], '
            '"modified_files": ["marketplace/bundles/plan-marshall/agents/foo.md"]}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-union',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=2,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None
        assert result['bundle_self_modification_inserted_before'] == 'default:create-pr'


def test_bundle_self_modification_fires_on_bare_name_candidates():
    """bundle_self_modification — works for bare-name (no `default:` prefix) candidates.

    The script's `DEFAULT_PHASE_6_STEPS` fallback emits bare names. Production
    `marshal.json` emits prefixed names. The matcher normalizes the prefix so
    the rule fires consistently on both call paths (regression guard for the
    prefix-mismatch defect gemini flagged on PR #278).
    """
    bare = [
        'commit-push',
        'create-pr',
        'automated-review',
        'archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-bare') as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            '{"affected_files": ["marketplace/bundles/plan-marshall/skills/foo/SKILL.md"]}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-bare',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=1,
                phase_6_steps=','.join(bare),
            )
        )
        assert result is not None
        # The inserting-before name is reported with whatever prefix the
        # candidate list used — bare here.
        assert result['bundle_self_modification_inserted_before'] == 'create-pr'

        manifest = read_manifest('bundle-self-mod-bare')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert steps.index('project:finalize-step-sync-plugin-cache') == steps.index('create-pr') - 1


def test_bundle_self_modification_detects_sonar_roundtrip_as_agent_step():
    """bundle_self_modification — sonar-roundtrip is recognized as agent-dispatched.

    The Phase 6 dispatch table in `phase-6-finalize/SKILL.md` routes
    `default:sonar-roundtrip` to `plan-marshall:sonar-roundtrip-agent`, so it
    must appear in the agent-dispatched set alongside create-pr / automated-review
    / knowledge-capture / lessons-capture (regression guard for the missing-step
    defect gemini flagged on PR #278). When sonar-roundtrip is the EARLIEST
    agent-dispatched entry in the resolved list, the early sync inserts before
    it, not before any later step.
    """
    prefixed = [
        'default:commit-push',
        'default:sonar-roundtrip',     # earliest agent-dispatched
        'default:create-pr',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-sonar') as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            '{"affected_files": ["marketplace/bundles/plan-marshall/agents/foo.md"]}',
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bundle-self-mod-sonar',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=1,
                phase_6_steps=','.join(prefixed),
            )
        )
        assert result is not None
        assert result['bundle_self_modification_inserted_before'] == 'default:sonar-roundtrip'

        manifest = read_manifest('bundle-self-mod-sonar')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        sonar_idx = steps.index('default:sonar-roundtrip')
        assert steps[sonar_idx - 1] == 'project:finalize-step-sync-plugin-cache'


def test_bundle_self_modification_idempotent_on_recompose():
    """bundle_self_modification — re-running compose doesn't double-insert."""
    prefixed = [
        'default:commit-push',
        'default:create-pr',
        'default:automated-review',
        'project:finalize-step-sync-plugin-cache',
        'default:archive-plan',
    ]
    with PlanContext(plan_id='bundle-self-mod-idem') as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            '{"modified_files": ["marketplace/bundles/plan-marshall/skills/foo/SKILL.md"]}',
            encoding='utf-8',
        )
        ns = _compose_ns(
            plan_id='bundle-self-mod-idem',
            change_type='bug_fix',
            scope_estimate='single_module',
            affected_files_count=1,
            phase_6_steps=','.join(prefixed),
        )
        # Compose twice — second invocation must remain idempotent.
        cmd_compose(ns)
        cmd_compose(ns)
        manifest = read_manifest('bundle-self-mod-idem')
        assert manifest is not None
        # Still exactly two occurrences (one early-inserted, one late-original).
        assert manifest['phase_6']['steps'].count('project:finalize-step-sync-plugin-cache') == 2


# =============================================================================
# Regression: bundle_self_modification three-path coverage (lesson 2026-04-28-06-001)
#
# The lesson identified that the rule never fired at Phase-4 compose time for
# normal plans because:
#   - `references.json::affected_files` was not populated by upstream phases;
#   - `references.json::modified_files` is empty pre-execute;
# leaving the predicate's input union empty even when the deliverable's
# `Affected files:` block clearly listed bundle source paths.
#
# TASK-1 extended `_read_bundle_change_paths` to fall back to deliverable-level
# `Affected files:` blocks in `solution_outline.md` when both reference fields
# are empty. These tests pin all three input paths (positive/positive/negative)
# so the rule's wiring is regression-protected end-to-end.
# =============================================================================


# Canonical late-stage Phase 6 candidate list with sync-plugin-cache placed
# AFTER branch-cleanup. The bundle_self_modification rule MUST insert a SECOND
# occurrence early (before the first agent-dispatched step).
_BSM_REGRESSION_PHASE_6 = [
    'default:commit-push',
    'default:create-pr',
    'default:automated-review',
    'default:sonar-roundtrip',
    'default:knowledge-capture',
    'default:lessons-capture',
    'default:branch-cleanup',
    'project:finalize-step-sync-plugin-cache',
    'default:archive-plan',
]


def _solution_outline_with_affected_files(affected_files: list[str]) -> str:
    r"""Build a minimal `solution_outline.md` body whose single deliverable's
    `Affected files:` block lists the given paths.

    The format matches `marketplace/bundles/plan-marshall/skills/manage-solution-outline/`
    parsing rules — `## Deliverables` H2, `### N. Title` H3, `**Affected files:**`
    bold tag with `- \`path\`` bullet entries.
    """
    bullets = '\n'.join(f'- `{p}`' for p in affected_files)
    return (
        '# Solution Outline\n'
        '\n'
        'plan_id: regression-test\n'
        'source: lesson-2026-04-28-06-001\n'
        '\n'
        '## Summary\n'
        '\n'
        'Regression fixture for the bundle_self_modification outline-fallback path.\n'
        '\n'
        '## Deliverables\n'
        '\n'
        '### 1. Touch a bundle script\n'
        '\n'
        '**Metadata:**\n'
        '- change_type: bug_fix\n'
        '- domain: plan-marshall-plugin-dev\n'
        '\n'
        '**Profiles:**\n'
        '- implementation\n'
        '\n'
        '**Affected files:**\n'
        f'{bullets}\n'
        '\n'
        '**Verification:**\n'
        '- Command: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests plan-marshall"`\n'
        '- Criteria: All tests pass\n'
    )


def _capture_decision_messages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace ``_emit_decision_log`` with an in-memory recorder.

    Returns a list reference whose contents grow as the composer emits decision
    log entries during the test body. The default test setup at module scope
    silences only ``_log_decision``; the bundle_self_modification rule routes
    through ``_log_bundle_self_modification`` -> ``_emit_decision_log`` so we
    install a separate spy here.
    """
    captured: list[str] = []

    def _recorder(plan_id: str, message: str) -> None:  # noqa: ARG001 - signature parity
        captured.append(message)

    monkeypatch.setattr(_mem, '_emit_decision_log', _recorder)
    return captured


def test_bundle_self_modification_regression_references_driven_path(monkeypatch):
    """Regression (lesson 2026-04-28-06-001) — references.affected_files path.

    Positive case: ``references.json::affected_files`` lists a bundle script
    path. The composer MUST emit exactly TWO ``project:finalize-step-sync-plugin-cache``
    entries — one early (before ``default:create-pr``, the earliest of the
    agent-dispatched set ``create-pr | automated-review | sonar-roundtrip |
    knowledge-capture | lessons-capture``) and one in the canonical late-stage
    position (immediately after ``default:branch-cleanup``). The decision log
    MUST contain the canonical bundle_self_modification message.
    """
    captured = _capture_decision_messages(monkeypatch)
    bundle_script = (
        'marketplace/bundles/plan-marshall/skills/foo/scripts/bar.py'
    )
    with PlanContext(plan_id='bsm-regression-references') as ctx:
        assert ctx.plan_dir is not None
        (ctx.plan_dir / 'references.json').write_text(
            json.dumps({'affected_files': [bundle_script]}),
            encoding='utf-8',
        )
        result = cmd_compose(
            _compose_ns(
                plan_id='bsm-regression-references',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=1,
                phase_6_steps=','.join(_BSM_REGRESSION_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == 'default:create-pr'

        manifest = read_manifest('bsm-regression-references')
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Exactly two sync-plugin-cache occurrences (one early, one canonical late).
        assert steps.count('project:finalize-step-sync-plugin-cache') == 2

        # Early occurrence sits immediately before default:create-pr.
        create_pr_idx = steps.index('default:create-pr')
        assert steps[create_pr_idx - 1] == 'project:finalize-step-sync-plugin-cache'

        # Canonical late occurrence preserved (after default:branch-cleanup).
        late_idx = steps.index('project:finalize-step-sync-plugin-cache', create_pr_idx + 1)
        assert steps[late_idx - 1] == 'default:branch-cleanup'

        # Canonical decision-log message emitted.
        assert any(
            'Rule bundle_self_modification fired' in m
            and 'inserted project:finalize-step-sync-plugin-cache before default:create-pr' in m
            for m in captured
        ), f'Expected canonical bundle_self_modification decision log entry; got: {captured}'


def test_bundle_self_modification_regression_outline_fallback_path(monkeypatch):
    """Regression (lesson 2026-04-28-06-001) — solution_outline fallback path.

    Positive case: BOTH ``references.json::affected_files`` and ``modified_files``
    are empty, but ``solution_outline.md`` carries a deliverable whose
    ``Affected files:`` block lists a bundle script path. This is the path the
    parent lesson missed and that TASK-1 newly enables — without the outline
    fallback, the rule would not fire at Phase-4 compose time for the typical
    pre-execute plan shape.

    The composer MUST still emit exactly TWO ``project:finalize-step-sync-plugin-cache``
    entries (early before ``default:create-pr`` + canonical late) and the
    canonical decision log message.
    """
    captured = _capture_decision_messages(monkeypatch)
    bundle_script = (
        'marketplace/bundles/plan-marshall/skills/foo/scripts/bar.py'
    )
    with PlanContext(plan_id='bsm-regression-outline') as ctx:
        assert ctx.plan_dir is not None
        # references.json present but with BOTH fields empty — mirrors the
        # exact pre-execute shape the parent lesson reproduced.
        (ctx.plan_dir / 'references.json').write_text(
            json.dumps({'affected_files': [], 'modified_files': []}),
            encoding='utf-8',
        )
        # Outline carries the deliverable-level Affected files block.
        (ctx.plan_dir / 'solution_outline.md').write_text(
            _solution_outline_with_affected_files([bundle_script]),
            encoding='utf-8',
        )

        result = cmd_compose(
            _compose_ns(
                plan_id='bsm-regression-outline',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=1,
                phase_6_steps=','.join(_BSM_REGRESSION_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == 'default:create-pr'

        manifest = read_manifest('bsm-regression-outline')
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Same TWO-entry shape as the references-driven path.
        assert steps.count('project:finalize-step-sync-plugin-cache') == 2

        create_pr_idx = steps.index('default:create-pr')
        assert steps[create_pr_idx - 1] == 'project:finalize-step-sync-plugin-cache'

        late_idx = steps.index('project:finalize-step-sync-plugin-cache', create_pr_idx + 1)
        assert steps[late_idx - 1] == 'default:branch-cleanup'

        # Same canonical decision-log message — fallback path is wired through
        # the same `_log_bundle_self_modification` emitter.
        assert any(
            'Rule bundle_self_modification fired' in m
            and 'inserted project:finalize-step-sync-plugin-cache before default:create-pr' in m
            for m in captured
        ), f'Expected canonical bundle_self_modification decision log entry; got: {captured}'


def test_bundle_self_modification_regression_negative_control(monkeypatch):
    """Regression (lesson 2026-04-28-06-001) — negative control.

    Negative case: ``references.affected_files`` carries only paths OUTSIDE
    ``marketplace/bundles/*/{skills,agents,commands}/**`` AND no matching
    outline entries exist. The rule MUST NOT fire — the manifest's
    ``phase_6.steps`` contains exactly ONE ``project:finalize-step-sync-plugin-cache``
    occurrence (the canonical late-stage one). No bundle_self_modification
    decision log entry is emitted.
    """
    captured = _capture_decision_messages(monkeypatch)
    with PlanContext(plan_id='bsm-regression-negative') as ctx:
        assert ctx.plan_dir is not None
        # Only non-bundle paths.
        (ctx.plan_dir / 'references.json').write_text(
            json.dumps({
                'affected_files': [
                    'doc/build-structure.adoc',
                    'test/plan-marshall/manage-references/test_x.py',
                ],
            }),
            encoding='utf-8',
        )
        # Outline also lists only non-bundle paths so the fallback cannot
        # rescue the negative case.
        (ctx.plan_dir / 'solution_outline.md').write_text(
            _solution_outline_with_affected_files(['doc/build-structure.adoc']),
            encoding='utf-8',
        )

        result = cmd_compose(
            _compose_ns(
                plan_id='bsm-regression-negative',
                change_type='bug_fix',
                scope_estimate='single_module',
                affected_files_count=2,
                phase_6_steps=','.join(_BSM_REGRESSION_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['bundle_self_modification_inserted_before'] == ''

        manifest = read_manifest('bsm-regression-negative')
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Exactly ONE occurrence — the canonical late-stage one untouched.
        assert steps.count('project:finalize-step-sync-plugin-cache') == 1

        # No bundle_self_modification message in the decision log.
        assert not any(
            'Rule bundle_self_modification fired' in m for m in captured
        ), f'Did not expect bundle_self_modification decision log entry; got: {captured}'


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
        assert set(manifest['phase_6']['steps']) == {'knowledge-capture', 'lessons-capture', 'archive-plan'}


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


@pytest.mark.parametrize('field,value,error_code', [
    ('change_type', 'unknown_type', 'invalid_change_type'),
    ('scope_estimate', 'massive', 'invalid_scope_estimate'),
    ('track', 'twisty', 'invalid_track'),
])
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
    omission_entries = [
        (pid, msg) for pid, msg in captured
        if 'commit-push omitted' in msg
    ]
    assert len(omission_entries) == 1, f'expected one omission entry, got {captured!r}'
    pid, msg = omission_entries[0]
    assert pid == 'matrix-cs-msg'
    assert msg == (
        '(plan-marshall:manage-execution-manifest:compose) '
        'commit-push omitted — commit_strategy=none'
    )


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


# =============================================================================
# CLI plumbing (subprocess) tests — keep small, just confirm wiring
# =============================================================================


def test_cli_compose_then_read_roundtrip():
    with PlanContext(plan_id='cli-rt'):
        result = run_script(
            SCRIPT_PATH,
            'compose',
            '--plan-id', 'cli-rt',
            '--change-type', 'feature',
            '--track', 'complex',
            '--scope-estimate', 'multi_module',
            '--affected-files-count', '10',
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
            '--plan-id', 'cli-bad',
            '--change-type', 'nonsense',
            '--track', 'simple',
            '--scope-estimate', 'surgical',
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
            '--plan-id', 'cli-allflags',
            '--change-type', 'tech_debt',
            '--track', 'simple',
            '--scope-estimate', 'surgical',
            '--recipe-key', 'lesson_cleanup',
            '--affected-files-count', '2',
            '--phase-5-steps', 'quality-gate,module-tests',
            '--phase-6-steps', 'commit-push,create-pr,branch-cleanup',
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
            '--plan-id', 'cli-val-ok',
            '--change-type', 'feature',
            '--track', 'complex',
            '--scope-estimate', 'multi_module',
        )
        assert compose.success

        result = run_script(
            SCRIPT_PATH,
            'validate',
            '--plan-id', 'cli-val-ok',
            '--phase-5-steps', 'quality-gate,module-tests',
            '--phase-6-steps', ','.join(DEFAULT_PHASE_6_STEPS),
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
            '--plan-id', 'cli-cs-none',
            '--change-type', 'feature',
            '--track', 'complex',
            '--scope-estimate', 'multi_module',
            '--commit-strategy', 'none',
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


def _write_marshal(ctx: PlanContext, *, activation_globs: list[str] | None = None,
                   include_pre_push_key: bool = True) -> None:
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
                f'pre-filter omission line must precede rule line; '
                f'got omit_idx={omit_idx}, rule_idx={rule_idx}'
            )

            # Rule line reflects filtered phase_6.steps (no pre-push-quality-gate).
            rule_msg = messages[rule_idx]
            assert 'pre-push-quality-gate' not in rule_msg

            # Manifest content also reflects the pre-filter outcome.
            manifest = read_manifest(plan_id)
            assert manifest is not None
            assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']


# =============================================================================
# Bot-Enforcement Guard — Remediation behavior (lesson 2026-04-28-10-001)
#
# When ci.provider is github or gitlab AND `automated-review` is missing from
# the assembled phase_6.steps (e.g., dropped by Row 5 surgical_bug_fix /
# surgical_tech_debt), the guard appends `default:automated-review` back into
# the list and emits a decision-log entry. The composition continues normally;
# no `bot_enforcement_violation` error is raised. Row 5's other subtractions
# (`sonar-roundtrip`, `knowledge-capture`) stay dropped — the guard remediates
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
    def _remediation_messages(
        cls, captured: list[tuple[str, str]], provider: str
    ) -> list[tuple[str, str]]:
        line = _REMEDIATION_LINE_TEMPLATE.format(provider=provider)
        return [entry for entry in captured if entry[1] == line]

    @staticmethod
    def _compose_row_5(
        plan_id: str, change_type: str, *, prefixed_candidates: bool
    ) -> dict:
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
        plan_id = (
            f'guard-remediate-{provider}-{change_type_kebab}-'
            f'{"prefixed" if prefixed_candidates else "bare"}'
        )
        with PlanContext(plan_id=plan_id) as ctx:
            _write_marshal_with_ci(ctx, provider=provider)

            captured, original = self._capture_decision_log()
            try:
                result = self._compose_row_5(
                    plan_id, change_type, prefixed_candidates=prefixed_candidates
                )
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
            bare_step_names = {
                s[len('default:'):] if s.startswith('default:') else s
                for s in steps
            }
            assert 'automated-review' in bare_step_names

            # (c) Row 5's other subtractions are still dropped — only
            #     automated-review is remediated.
            assert 'sonar-roundtrip' not in bare_step_names
            assert 'knowledge-capture' not in bare_step_names

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
        self._assert_remediation(
            'github', 'bug_fix', 'surgical_bug_fix', prefixed_candidates=False
        )

    def test_gitlab_surgical_bug_fix_remediates_with_default_candidates(self):
        """Row 5 surgical_bug_fix + ci.provider=gitlab (bare candidates) → remediation."""
        self._assert_remediation(
            'gitlab', 'bug_fix', 'surgical_bug_fix', prefixed_candidates=False
        )

    def test_github_surgical_bug_fix_remediates_with_prefixed_candidates(self):
        """Row 5 surgical_bug_fix + ci.provider=github (default:-prefixed candidates) → remediation."""
        self._assert_remediation(
            'github', 'bug_fix', 'surgical_bug_fix', prefixed_candidates=True
        )

    # --- Row 5 surgical_tech_debt variants ---

    def test_github_surgical_tech_debt_remediates_with_default_candidates(self):
        """Row 5 surgical_tech_debt + ci.provider=github (bare candidates) → remediation."""
        self._assert_remediation(
            'github', 'tech_debt', 'surgical_tech_debt', prefixed_candidates=False
        )

    def test_gitlab_surgical_tech_debt_remediates_with_default_candidates(self):
        """Row 5 surgical_tech_debt + ci.provider=gitlab (bare candidates) → remediation."""
        self._assert_remediation(
            'gitlab', 'tech_debt', 'surgical_tech_debt', prefixed_candidates=False
        )

    def test_github_surgical_tech_debt_remediates_with_prefixed_candidates(self):
        """Row 5 surgical_tech_debt + ci.provider=github (default:-prefixed candidates) → remediation."""
        self._assert_remediation(
            'github', 'tech_debt', 'surgical_tech_debt', prefixed_candidates=True
        )

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
