# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import (
    EXECUTION_LOG_KEY,
    MANIFEST_FILENAME,
    UNMEASURED_COLUMN_TOKEN,
    _compose,
    _record_ns,
    cmd_record_step,
    get_plan_dir,
    parse_ns,
    pytest,
    read_manifest,
)


def test_a_measured_zero_and_an_omitted_flag_differ_in_the_file_bytes(plan_context):
    """The distinction survives to disk — asserted on the BYTES, not a round trip.

    ⛔ A round-trip assertion (write, then read back through the same reader)
    passes against the defect: if the writer collapsed both states to ``0`` the
    reader would faithfully return ``0`` twice and the assertion would still be
    about self-consistency rather than about the distinction. Reading the raw
    ``execution.toon`` text is what makes this test capable of failing against a
    writer that fabricates the zero.
    """
    _compose('rec-bytes')
    cmd_record_step(
        _record_ns(
            plan_id='rec-bytes',
            step_id='measured',
            outcome='skipped',
            total_tokens=0,
            tool_uses=0,
            duration_ms=0,
        )
    )
    cmd_record_step(_record_ns(plan_id='rec-bytes', step_id='omitted', outcome='executed'))

    raw = (get_plan_dir('rec-bytes') / MANIFEST_FILENAME).read_text(encoding='utf-8')
    measured_line = next(line for line in raw.splitlines() if line.strip().startswith('measured,'))
    omitted_line = next(line for line in raw.splitlines() if line.strip().startswith('omitted,'))

    assert measured_line != omitted_line
    assert UNMEASURED_COLUMN_TOKEN not in measured_line
    assert UNMEASURED_COLUMN_TOKEN in omitted_line


def test_a_productive_loop_back_is_recordable_as_itself(plan_context):
    """⛔ A findings-bearing return is a loop-back, not an error.

    Before the partition it was recorded as `error`, so every archive-wide
    analysis that counts errors mis-graded a multi-round self-review as a
    defect — the more thoroughly a gate worked, the worse its plan looked.
    """
    _compose('rec-loop-back')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-loop-back',
            step_id='pre-submission-self-review',
            phase='6-finalize',
            outcome='loop_back',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'loop_back'
    assert read_manifest('rec-loop-back')[EXECUTION_LOG_KEY][0]['outcome'] == 'loop_back'


def test_a_clean_run_with_a_negative_verdict_is_recordable_as_failed(plan_context):
    """`failed` stays reachable, and separably so, for a red gate.

    A step that RAN CLEANLY and self-assessed not-clean is neither a productive
    hand-back nor a dispatch that raised; collapsing it into either loses the
    one fact the row exists to carry.
    """
    _compose('rec-failed')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-failed',
            step_id='pre-push-quality-gate',
            phase='6-finalize',
            outcome='failed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'failed'


@pytest.mark.parametrize('outcome', ['skipped', 'loop_back', 'failed'])
def test_a_step_outcome_is_representable_in_the_manifest_ledger(plan_context, outcome):
    """Cross-ledger representability, derived from BOTH parsers rather than asserted.

    A step records its situation on `status.metadata.phase_steps` through
    `mark-step-done`, and the dispatcher mirrors it into the manifest's
    `execution_log[]` through `record-step`. If one vocabulary can express a
    situation the other cannot, the mirror has to collapse it — which is exactly
    how a productive loop-back became an `error` row in the first place.

    Acceptance is probed through each script's OWN parser and handler, so this
    cannot pass against a literal list that has drifted from either surface.
    `done` is deliberately excluded: it maps to `executed`, the one value the
    two vocabularies name differently by design.
    """
    parse_ns(
        'plan-marshall',
        'manage-status',
        'manage-status.py',
        'mark-step-done',
        '--plan-id',
        'rec-cross-ledger',
        '--phase',
        '6-finalize',
        '--step',
        'a-step',
        '--outcome',
        outcome,
        register=False,
    )

    # plan_id is kebab-case-validated, so an outcome carrying an underscore
    # (`loop_back`) cannot be interpolated into one verbatim.
    plan_id = 'rec-cross-' + outcome.replace('_', '-')
    _compose(plan_id)
    result = cmd_record_step(_record_ns(plan_id=plan_id, step_id='a-step', phase='6-finalize', outcome=outcome))

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == outcome
