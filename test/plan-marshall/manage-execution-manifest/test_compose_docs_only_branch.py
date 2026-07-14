#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests asserting the compose docs-only post-matrix branch is removed.

The advisory docs-only post-matrix rule in ``cmd_compose`` — which inspected the
plan-wide union of every deliverable's ``affected_files`` and suppressed holistic
Python verification steps when the union resolved to ``documentation_only`` — has
been deleted. The single deterministic build_map consumer (the deriver) now drives
per-deliverable verification and the single execute-exit verify; compose no longer
suppresses or derives docs-only advisorily.

These tests pin the removal: the ``docs_only_classifier_fired`` / ``plan_wide_bucket``
return fields and the ``_log_docs_only_classifier_fired`` helper no longer exist, the
``cmd_classify_affected_files`` handler and ``classify-affected-files`` subcommand are
gone, and a docs-only-pathed plan now retains exactly the matrix-derived verification
steps (no advisory suppression). The seed-source aggregator
``_classify_paths_via_extensions`` is retained and exercised in
``test_classify_paths_via_extensions.py``.
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
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_submission_self_review_omitted = lambda *a, **kw: None
_mem._emit_decision_log = lambda *a, **kw: None

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
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps if phase_5_steps is not None else ','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=commit_and_push,
    )


def _seed_references(plan_dir: Path, affected_files: list[str]) -> None:
    """Write ``references.json`` carrying the supplied ``affected_files`` list."""
    refs = {'affected_files': affected_files}
    (plan_dir / 'references.json').write_text(json.dumps(refs, indent=2))


# =============================================================================
# Removal of the docs-only post-matrix branch
# =============================================================================


def test_log_docs_only_classifier_fired_helper_removed():
    """The ``_log_docs_only_classifier_fired`` helper no longer exists."""
    assert not hasattr(_mem, '_log_docs_only_classifier_fired')


def test_cmd_classify_affected_files_handler_removed():
    """The ``cmd_classify_affected_files`` handler no longer exists."""
    assert not hasattr(_mem, 'cmd_classify_affected_files')


def test_classify_affected_files_subcommand_removed():
    """The ``classify-affected-files`` subcommand is no longer registered."""
    parser = _mem._build_parser()
    subparsers_action = next(
        action for action in parser._actions if hasattr(action, 'choices') and action.choices
    )
    assert 'classify-affected-files' not in subparsers_action.choices


def test_classify_paths_via_extensions_aggregator_retained():
    """The seed-source aggregator ``_classify_paths_via_extensions`` is retained."""
    assert hasattr(_mem, '_classify_paths_via_extensions')


# =============================================================================
# Compose no longer suppresses docs-only advisorily
# =============================================================================


def test_compose_omits_docs_only_classifier_fields_from_result(plan_context):
    """The compose result no longer carries ``docs_only_classifier_fired`` / ``plan_wide_bucket``."""
    plan_id = 'compose-no-docs-only-fields'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        [
            'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md',
        ],
    )

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=2,
        )
    )

    assert result is not None and result['status'] == 'success'
    assert 'docs_only_classifier_fired' not in result
    assert 'plan_wide_bucket' not in result


def test_docs_only_pathed_plan_retains_matrix_verification_steps(plan_context):
    """A docs-only-pathed feature plan retains its matrix-derived verification steps.

    Before the removal, a ``feature`` plan whose affected files were all docs hit
    Row 7 (default), then the advisory post-matrix rule stripped the holistic
    steps down to an empty ``verification_steps`` list. With the branch deleted,
    compose emits exactly the matrix output — Row 7 keeps both candidate steps —
    regardless of whether the affected files happen to be docs. The deriver, not
    compose, decides per-deliverable build scope downstream.
    """
    plan_id = 'docs-pathed-feature-retains-steps'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        [
            'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md',
            'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md',
        ],
    )

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
        )
    )

    assert result is not None and result['status'] == 'success'
    # Row 7 (default) passes both candidates through; no advisory suppression.
    assert result['phase_5']['verification_steps_count'] == 2
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == list(DEFAULT_PHASE_5_STEPS)


def test_matrix_row_3_docs_only_still_empties_phase_5(plan_context):
    """The seven-row matrix's Row 3 (``docs_only``) is unchanged and still empties phase 5.

    Removing the post-matrix advisory branch does NOT touch the matrix itself —
    Row 3 keys on the candidate role heuristic (no module-tests/coverage roles)
    and legitimately empties ``phase_5.verification_steps`` for a docs-shaped
    candidate set. This test pins that the row-level docs-only handling survives
    the post-matrix branch removal.
    """
    plan_id = 'matrix-row-3-docs-only-survives'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_references(
        plan_dir,
        ['marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md'],
    )

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_5_steps='quality-gate',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'docs_only'
    assert result['phase_5']['verification_steps_count'] == 0
