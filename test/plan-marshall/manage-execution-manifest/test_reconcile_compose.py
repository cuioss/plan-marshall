# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_reconcile_fixtures import (
    DEFAULT_PHASE_5_STEPS,
    DEFAULT_PHASE_6_STEPS,
    Namespace,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# compose writes the candidate snapshot reconcile depends on
# =============================================================================


class TestComposeSnapshotsCandidateSteps:
    def test_compose_records_the_candidate_set_it_selected_from(self, plan_context):
        cmd_compose(
            Namespace(
                plan_id='rec-compose',
                change_type='feature',
                track='complex',
                scope_estimate='multi_module',
                recipe_key=None,
                affected_files_count=5,
                phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
                commit_and_push=None,
            )
        )
        manifest = read_manifest('rec-compose')
        candidates = manifest['phase_6'].get('candidate_steps')
        assert candidates, 'compose must snapshot the phase-6 candidate set'
        selected = manifest['phase_6']['steps']
        # Subset holds HERE because this compose leaves every ceremony gate at
        # its `auto` default. It is NOT a general invariant: a gate resolved to
        # `always` force-inserts its canonical step via
        # `_apply_ceremony_finalize_selection` with no candidate-membership
        # check, so a forced-in step legitimately appears in `steps` and not in
        # `candidate_steps`. Do not generalize this assertion — see
        # standards/manifest-schema.md.
        assert set(selected).issubset(set(candidates)), (
            'with every ceremony gate at `auto`, each selected step must come from the recorded candidate set'
        )
