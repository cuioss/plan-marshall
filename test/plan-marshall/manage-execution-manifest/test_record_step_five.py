# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_record_step_fixtures import (
    EXECUTION_LOG_KEY,
    VALID_RECORD_OUTCOMES,
    _compose,
    _record_ns,
    cmd_record_step,
    read_manifest,
)


def test_the_five_outcomes_are_pairwise_distinct_on_disk(plan_context):
    """The partition is a property of the ROWS, not of a reader's convention.

    Recording all five and reading them back is what makes the ledger's own
    bytes answer "which situation was this" — the question a single collapsed
    `error` value could not answer at all.
    """
    _compose('rec-partition')
    for outcome in VALID_RECORD_OUTCOMES:
        cmd_record_step(
            _record_ns(
                plan_id='rec-partition',
                step_id=f'step-{outcome}',
                phase='6-finalize',
                outcome=outcome,
            )
        )

    rows = read_manifest('rec-partition')[EXECUTION_LOG_KEY]

    assert [row['outcome'] for row in rows] == list(VALID_RECORD_OUTCOMES)
    assert len({row['outcome'] for row in rows}) == len(VALID_RECORD_OUTCOMES)
