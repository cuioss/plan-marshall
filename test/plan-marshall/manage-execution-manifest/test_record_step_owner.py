# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_record_step_fixtures import ORCHESTRATOR_OWNED_STEPS, owner_of


def test_owner_of_sub_dispatching_steps_are_orchestrator_owned():
    """The known sub-dispatching finalize steps resolve to orchestrator-owned."""
    for step in (
        'finalize-step-plugin-doctor',
        'pre-submission-self-review',
        'automatic-review',
        'finalize-step-simplify',
    ):
        assert owner_of(step) == 'orchestrator-owned', step
        assert step in ORCHESTRATOR_OWNED_STEPS


def test_owner_of_strips_default_and_project_prefixes():
    """default:- and project:-prefixed spellings classify identically to the bare name."""
    assert owner_of('project:finalize-step-plugin-doctor') == 'orchestrator-owned'
    assert owner_of('default:pre-submission-self-review') == 'orchestrator-owned'
    assert owner_of('default:finalize-step-simplify') == 'orchestrator-owned'


def test_owner_of_defaults_leaf_dispatchable():
    """Steps not in the registry default to leaf-dispatchable."""
    for step in ('push', 'create-pr', 'ci-verify', 'verify:quality-gate', 'archive-plan'):
        assert owner_of(step) == 'leaf-dispatchable', step
