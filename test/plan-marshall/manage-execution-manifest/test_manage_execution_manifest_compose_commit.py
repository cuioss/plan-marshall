# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _COMMIT_PUSH_DROP_SET,
    _compose_ns,
    _mem,
    _phase_6_with_every_commit_push_gate,
    cmd_compose,
    pytest,
    read_manifest,
)


@pytest.mark.parametrize(
    'commit_and_push,expect_commit_push',
    [
        ('true', True),
        (None, True),  # Absent flag defaults to true.
        ('false', False),
    ],
)
def test_commit_and_push_pre_filter(plan_context, commit_and_push, expect_commit_push):
    """Pre-filter: commit_and_push=false drops push; true retains it.

    The scalar ``commit_push_omitted`` boolean is replaced by the
    ``commit_push_dropped`` record list, so the fired/not-fired state is read as
    "did the pre-filter record any subtraction" rather than from a separate flag
    that could drift out of step with the actual drops.
    """
    slug = commit_and_push or 'absent'
    plan_id = f'matrix-cap-{slug}'
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
            commit_and_push=commit_and_push,
            phase_6_steps=_phase_6_with_every_commit_push_gate(),
        )
    )
    assert result is not None and result['status'] == 'success'
    dropped_steps = {record['step'] for record in result['commit_push_dropped']}
    manifest = read_manifest(plan_id)
    assert manifest is not None
    if expect_commit_push:
        assert dropped_steps == set()
        assert 'push' in manifest['phase_6']['steps']
    else:
        assert dropped_steps == _COMMIT_PUSH_DROP_SET
        assert 'push' not in manifest['phase_6']['steps']



def test_commit_and_push_false_emits_one_decision_log_call_per_dropped_step(plan_context):
    """The emitter fires ONCE PER dropped step, not once per fired pre-filter.

    Per-step rather than per-pre-filter is the whole correction: the gate drops
    three steps, and a single aggregate call could only ever name one of them.
    """
    captured: list[tuple[str, str, str]] = []
    original_helper = _mem._log_commit_push_omitted

    def _capture(plan_id, step, reason):
        captured.append((plan_id, step, reason))

    _mem._log_commit_push_omitted = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-cap-log',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                commit_and_push='false',
                phase_6_steps=_phase_6_with_every_commit_push_gate(),
            )
        )
    finally:
        _mem._log_commit_push_omitted = original_helper

    assert {plan_id for plan_id, _step, _reason in captured} == {'matrix-cap-log'}
    assert {step for _pid, step, _reason in captured} == _COMMIT_PUSH_DROP_SET
    assert all(reason for _pid, _step, reason in captured)



def test_commit_and_push_false_decision_log_message_matches_contract(plan_context):
    """Each dropped step gets its own ``[STATUS]`` line naming the step and reason."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-cap-msg',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                commit_and_push='false',
                phase_6_steps=_phase_6_with_every_commit_push_gate(),
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    prefix = '(plan-marshall:manage-execution-manifest:compose) [STATUS] commit_push_disabled — dropped '
    omission_entries = [(pid, msg) for pid, msg in captured if msg.startswith(prefix)]
    # One line per dropped step — three, not one aggregate.
    assert len(omission_entries) == len(_COMMIT_PUSH_DROP_SET), f'expected one line per dropped step, got {captured!r}'
    assert {pid for pid, _msg in omission_entries} == {'matrix-cap-msg'}
    named_steps = {msg[len(prefix) :].split(' from phase_6.steps: ')[0] for _pid, msg in omission_entries}
    assert named_steps == _COMMIT_PUSH_DROP_SET
    # Each line carries a non-empty reason after the separator.
    for _pid, msg in omission_entries:
        assert msg.split(' from phase_6.steps: ', 1)[1]



def test_commit_and_push_default_does_not_emit_omission_log(plan_context):
    """When commit_and_push is absent (defaults to true), no omission log fires."""
    captured: list[tuple[str, str, str]] = []
    original_helper = _mem._log_commit_push_omitted

    def _capture(plan_id, step, reason):
        captured.append((plan_id, step, reason))

    _mem._log_commit_push_omitted = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-cap-default-nolog',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                commit_and_push=None,
            )
        )
    finally:
        _mem._log_commit_push_omitted = original_helper
    assert captured == []



def test_commit_and_push_invalid_value_rejected(plan_context):
    """Invalid commit_and_push values produce a structured error response."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-cap-bad',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=2,
            commit_and_push='nope',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_commit_and_push'



def test_commit_and_push_false_with_recipe_still_drops_commit_push(plan_context):
    """Pre-filter applies before the row matrix — recipe rule still loses push."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-cap-recipe',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            commit_and_push='false',
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'
    manifest = read_manifest('matrix-cap-recipe')
    assert manifest is not None
    assert 'push' not in manifest['phase_6']['steps']



def test_commit_and_push_false_with_prefixed_input_drops_commit_push_and_pre_push(plan_context):
    """Regression — _apply_commit_push_disabled drops both gates with prefixed input.

    ``_apply_commit_push_disabled`` compares candidate entries against the
    bare-name set ``{push, pre-push-quality-gate, pre-submission-self-review}``.
    Without boundary normalization, a ``marshal.json`` that emits prefixed
    candidates (e.g. ``default:push``) would fail that comparison silently and
    leave the gate steps in the manifest despite ``commit_and_push=false``.

    Boundary normalization in ``cmd_compose`` strips the ``default:`` prefix
    once at intake, so ``_apply_commit_push_disabled`` sees bare strings
    and the membership check works regardless of how the caller spelled the
    candidate IDs. This test feeds a fully prefixed candidate list to
    ``cmd_compose`` with ``commit_and_push=false`` and asserts both gate steps
    are dropped and the manifest output is bare.
    """
    prefixed = [
        'default:pre-push-quality-gate',
        'default:push',
        'default:create-pr',
        'plan-marshall:automatic-review',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:archive-plan',
    ]
    result = cmd_compose(
        _compose_ns(
            plan_id='cap-false-prefixed',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=4,
            phase_6_steps=','.join(prefixed),
            commit_and_push='false',
        )
    )
    assert result is not None and result['status'] == 'success'
    # The pre-filter fired on the prefixed input, and each drop is recorded by
    # its BARE id (the boundary normalization strips the prefix before the gate
    # sees the candidates).
    assert {record['step'] for record in result['commit_push_dropped']} == {
        'push',
        'pre-push-quality-gate',
    }

    manifest = read_manifest('cap-false-prefixed')
    assert manifest is not None
    steps = manifest['phase_6']['steps']

    # Both gate steps are dropped (the latent bug — they would have
    # survived as `default:push` / `default:pre-push-quality-gate`
    # before the boundary normalization landed).
    assert 'push' not in steps
    assert 'pre-push-quality-gate' not in steps

    # Output is bare — no `default:` prefix anywhere.
    assert not any(s.startswith('default:') for s in steps), f'phase_6 leaked `default:`-prefixed entry: {steps!r}'

    # Other steps from the input survive as bare strings.
    for kept in (
        'create-pr',
        'automatic-review',
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    ):
        assert kept in steps, f'expected bare {kept!r} in phase_6 but got: {steps!r}'
