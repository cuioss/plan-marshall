#!/usr/bin/env python3
"""End-to-end tests for the docs-only post-matrix rule in ``cmd_compose``.

The rule inspects the plan-wide union of every deliverable's
``affected_files`` and, when the union resolves to the ``doc-only`` bucket,
suppresses holistic Python verification steps (``quality-gate``,
``module-tests``, ``coverage``) from ``phase_5.verification_steps``. The
rule layers ON TOP of the seven-row matrix: Row 3 (``docs_only``) keys on
the role heuristic and catches plans where the candidate set itself
signals docs-only; this rule catches plans where the candidate set looks
code-shaped but the actual affected files are all docs.

See sibling lessons ``2026-05-28-10-001`` and ``2026-05-27-19-002``.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

# =============================================================================
# Module loading (script has hyphens in filename → load via importlib)
# =============================================================================

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


_mem = _load_module('_mem_script_compose_docs_only', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess in tests.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_commit_push_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_pre_submission_self_review_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_bot_enforcement_guard_remediated = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_docs_only_classifier_fired = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Helpers
# =============================================================================


def _compose_ns(
    plan_id: str,
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = None,
    phase_6_steps: str | None = None,
    commit_strategy: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        # Default phase-5 steps: use the canonical names whose standards files
        # carry the role: quality-gate / role: module-tests frontmatter. These
        # are what marshal.json declares in real plans and what _role_of can
        # resolve. The CSV-style ``quality-gate,module-tests`` names work for
        # role-intersection tests but bypass the post-matrix classifier's
        # suppression check because _role_of returns None for them.
        phase_5_steps=phase_5_steps if phase_5_steps is not None else ','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_strategy=commit_strategy,
    )


def _seed_references(plan_dir: Path, affected_files: list[str]) -> None:
    """Write ``references.json`` carrying the supplied ``affected_files`` list."""
    refs = {'affected_files': affected_files}
    (plan_dir / 'references.json').write_text(json.dumps(refs, indent=2))


# =============================================================================
# Tests
# =============================================================================


def test_docs_only_plan_suppresses_holistic_python_verification_steps(plan_context):
    """End-to-end: docs-only affected_files → quality-gate + module-tests suppressed.

    A ``feature`` plan with multi_module scope normally hits Row 7 (default)
    and emits both quality-gate and module-tests under
    ``phase_5.verification_steps``. When the plan-wide affected_files
    resolve to ``doc-only`` (all .md files under marketplace/bundles), the
    post-matrix rule strips both steps so the manifest carries an empty
    ``verification_steps`` list.
    """
    # Arrange — seed references.json with doc-only paths
    plan_id = 'docs-only-feature-plan'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        [
            'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md',
            'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md',
        ],
    )

    # Act — compose a feature plan that would normally retain quality-gate + module-tests
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
        )
    )

    # Assert — the docs-only classifier fired and stripped holistic steps
    assert result is not None and result['status'] == 'success'
    assert result['docs_only_classifier_fired'] is True
    assert result['plan_wide_bucket'] == 'doc-only'
    assert result['phase_5']['verification_steps_count'] == 0
    # Manifest on disk also reflects the suppression
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == []


def test_mixed_plan_retains_holistic_python_verification_steps(plan_context):
    """End-to-end: mixed affected_files → quality-gate + module-tests retained.

    When the plan-wide affected_files include at least one .py file, the
    post-matrix rule does NOT fire. The matrix's normal output (Row 7
    default for a feature plan) carries quality-gate + module-tests
    through to ``phase_5.verification_steps`` unchanged.
    """
    # Arrange — seed references.json with mixed paths (.py + .md)
    plan_id = 'mixed-plan'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        [
            'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py',
            'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md',
        ],
    )

    # Act
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=2,
        )
    )

    # Assert — classifier did not fire; quality-gate + module-tests retained
    assert result is not None and result['status'] == 'success'
    assert result['docs_only_classifier_fired'] is False
    assert result['plan_wide_bucket'] == 'mixed'
    assert result['phase_5']['verification_steps_count'] == 2


def test_python_prod_plan_retains_holistic_python_verification_steps(plan_context):
    """End-to-end: python-prod affected_files → holistic steps retained.

    A plan whose affected files are all production Python sources resolves
    to the ``python-prod`` bucket — the post-matrix rule does not fire.
    """
    # Arrange — seed references.json with python-prod paths only
    plan_id = 'python-prod-plan'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        [
            'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py',
        ],
    )

    # Act
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=1,
        )
    )

    # Assert — classifier did not fire; quality-gate + module-tests retained
    assert result is not None and result['status'] == 'success'
    assert result['docs_only_classifier_fired'] is False
    assert result['plan_wide_bucket'] == 'python-prod'
    assert result['phase_5']['verification_steps_count'] == 2


def test_docs_only_classifier_is_noop_when_matrix_already_emptied_phase_5(plan_context):
    """Row 3 (matrix docs_only) empties phase_5 first; post-matrix rule is a no-op.

    When the matrix's Row 3 fires (candidate set has no module-tests/coverage
    roles AND change_type/scope match), ``phase_5.verification_steps`` is
    already empty. The post-matrix rule runs but suppresses nothing —
    ``docs_only_classifier_fired`` remains False because no steps were
    removed.
    """
    # Arrange — seed doc-only paths AND craft a candidate set that hits Row 3
    plan_id = 'matrix-row-3-then-post-matrix-noop'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        ['marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md'],
    )

    # Act — change_type=tech_debt + scope_estimate=surgical + docs-only candidates
    # triggers Row 3 (matrix docs_only): phase_5.verification_steps starts empty.
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_5_steps='quality-gate',  # role: quality-gate; no module-tests/coverage
        )
    )

    # Assert — Row 3 fired; post-matrix rule had nothing left to strip
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'docs_only'
    assert result['phase_5']['verification_steps_count'] == 0
    # Plan-wide bucket is still doc-only — the classifier ran, but the
    # `fired` flag tracks whether it actually removed anything.
    assert result['plan_wide_bucket'] == 'doc-only'
    assert result['docs_only_classifier_fired'] is False


def test_docs_only_plan_with_no_references_is_unknown_and_no_op(plan_context):
    """When references.json is absent and no outline either, the rule is a no-op.

    The evidence-required gate treats an empty bundle change paths list
    as ``"unknown"`` (not ``"doc-only"``) so existing test fixtures and
    ad-hoc compose calls without a plan workspace continue to behave
    normally. The matrix's normal output (Row 7 default for a feature
    plan with affected_files_count > 0) is preserved unchanged.
    """
    # Arrange — no references.json, no solution_outline.md
    plan_id = 'no-references-no-outline'
    plan_context.plan_dir_for(plan_id)  # ensure dir exists, but write nothing

    # Act
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,  # claims files exist but no references on disk
        )
    )

    # Assert — bucket is "unknown"; rule does not fire; matrix output retained
    assert result is not None and result['status'] == 'success'
    assert result['plan_wide_bucket'] == 'unknown'
    assert result['docs_only_classifier_fired'] is False
    # Row 7 default: quality-gate + module-tests both present
    assert result['phase_5']['verification_steps_count'] == 2
