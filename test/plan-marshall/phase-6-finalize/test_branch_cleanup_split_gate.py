#!/usr/bin/env python3
"""Tests for the split confirmation-gate plumbing in branch-cleanup.

The gate-decision logic itself lives in workflow doc text
(`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`),
so this suite pins:

1. The config-knob plumbing (`auto_rebase_threshold` and `final_merge_without_asking`
   are reachable through `manage-config plan phase-6-finalize get/set --field`
   with the documented default values).
2. The doc-level invariants of the split-gate structure — two distinct
   sections in branch-cleanup.md, each routed by its own knob, including the
   merged-state suppression and the deferred-merge clean-exit paths.
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

_MARKETPLACE_ROOT = (
    Path(__file__).parent.parent.parent.parent / 'marketplace' / 'bundles'
)
_SCRIPTS_DIR = (
    _MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)
_BRANCH_CLEANUP_DOC = (
    _MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'branch-cleanup.md'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_init_mod = _load_module('_cmd_init_for_split_gate', '_cmd_init.py')
_cmd_quality_phases_mod = _load_module(
    '_cmd_quality_phases_for_split_gate', '_cmd_quality_phases.py'
)


def _branch_cleanup_text() -> str:
    return _BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')


# ---- Config-knob plumbing ----------------------------------------------------


def test_auto_rebase_threshold_roundtrips_when_set(plan_context):
    """auto_rebase_threshold is dynamically read (not schema-registered).

    Calling get on a fresh marshal.json returns error (the field is absent
    from DEFAULT_PLAN_FINALIZE on purpose — branch-cleanup.md documents the
    `no_overlap_only` default as the workflow-level fallback). Once the
    operator explicitly sets the field, it round-trips through get/set so
    consumer projects opting into a non-default value are honoured.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_args = Namespace(
        noun='plan',
        sub_noun='phase-6-finalize',
        verb='set',
        field='auto_rebase_threshold',
        value='auto_resolvable',
    )
    set_result = _cmd_quality_phases_mod.cmd_phase(set_args, 'phase-6-finalize')
    assert set_result['status'] == 'success'

    get_args = Namespace(
        noun='plan',
        sub_noun='phase-6-finalize',
        verb='get',
        field='auto_rebase_threshold',
    )
    get_result = _cmd_quality_phases_mod.cmd_phase(get_args, 'phase-6-finalize')

    assert get_result['status'] == 'success'
    assert get_result['value'] == 'auto_resolvable'


def test_final_merge_without_asking_default_is_false(plan_context):
    """Fresh marshal.json must surface final_merge_without_asking default False.

    The knob is a flat field under plan.phase-6-finalize; the runtime read is
    now `plan phase-6-finalize get --field final_merge_without_asking`.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    args = Namespace(verb='get', field='final_merge_without_asking')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-6-finalize')

    assert result['status'] == 'success'
    assert result['value'] is False


def test_final_merge_without_asking_read_from_phase_6_finalize(plan_context):
    """final_merge_without_asking reads through the standard phase get verb.

    A fresh marshal.json (no live override) reads the canonical default from
    the merged plan.phase-6-finalize block.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Read the whole phase-6-finalize block (no --field).
    args = Namespace(verb='get', field=None)
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-6-finalize')

    assert result['status'] == 'success'
    assert result['final_merge_without_asking'] is False


# ---- Doc-level invariants ----------------------------------------------------


def test_doc_contains_pre_rebase_and_pre_merge_sections():
    """branch-cleanup.md MUST document both pre-rebase and pre-merge gates."""
    text = _branch_cleanup_text()

    # Both headings present, distinct, and named after the orthogonal knobs.
    assert '### Pre-Rebase Confirmation Gate' in text
    assert '### Pre-Merge Confirmation Gate' in text


def test_doc_routes_pre_rebase_via_auto_rebase_threshold():
    """The pre-rebase gate must reference the renamed `auto_rebase_threshold` knob."""
    text = _branch_cleanup_text()

    assert 'auto_rebase_threshold' in text
    # The legacy step-prefixed name MUST be fully removed by deliverable 1.
    assert 'branch_cleanup_auto_proceed_threshold' not in text


def test_doc_routes_pre_merge_via_final_merge_without_asking():
    """The pre-merge gate must reference the renamed `final_merge_without_asking` knob."""
    text = _branch_cleanup_text()

    assert 'final_merge_without_asking' in text
    # The legacy name MUST be fully removed by the branch-cleanup.md rename.
    assert 'auto_merge_after_ci' not in text


def test_doc_pre_merge_reruns_classifier_for_freshness():
    """The pre-merge gate MUST re-dispatch baseline-reconcile so the prompt is anchored to the post-rebase head."""
    text = _branch_cleanup_text()

    # Explicit "re-run the classifier" anchor in the pre-merge section.
    pre_merge_idx = text.index('### Pre-Merge Confirmation Gate')
    pre_merge_section = text[pre_merge_idx:]
    assert 'baseline-reconcile' in pre_merge_section, (
        'pre-merge gate must re-dispatch baseline-reconcile to refresh the '
        'classifier observation against the current head sha'
    )


def test_doc_documents_no_skip_merge_deferral_path():
    """The pre-merge gate MUST document a deferral path that exits cleanly without enabling auto-merge."""
    text = _branch_cleanup_text()

    # "No, skip merge" answer and deferred merge_consent state.
    assert 'No, skip merge' in text
    assert 'merge_consent' in text, (
        'pre-merge gate must drive a merge_consent flag so the auto-merge '
        'fallback only fires when explicit consent was given'
    )


def test_doc_preserves_state_merged_reentry_path():
    """`state == merged` re-entry MUST short-circuit the pre-merge gate."""
    text = _branch_cleanup_text()

    # The doc explicitly notes that there is nothing to merge in this case.
    pre_merge_idx = text.index('### Pre-Merge Confirmation Gate')
    pre_merge_section = text[pre_merge_idx:]
    assert 'state == merged' in pre_merge_section, (
        'pre-merge gate must preserve the state==merged re-entry path '
        '(nothing to merge → skip the merge gate)'
    )
