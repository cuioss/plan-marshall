# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_subtraction_visibility_population_fixtures import (
    _REMOVED_VACUOUS_RESULT_KEY,
    DEFAULT_PHASE_6_STEPS,
    Namespace,
    Path,
    cmd_compose,
    json,
)

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
