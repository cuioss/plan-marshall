# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_ENVELOPE_COUNT,
    Namespace,
    _compose_ns,
    _compose_ns_with_envelope_count,
    _mem,
    cmd_compose,
    pytest,
    read_manifest,
)


def test_envelope_count_persisted_when_supplied(plan_context):
    """A supplied --envelope-count lands verbatim in the phase_5 block and result."""
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            4,
            plan_id='envelope-supplied',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == 4
    manifest = read_manifest('envelope-supplied')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == 4



def test_envelope_count_defaults_when_absent(plan_context):
    """Omitting --envelope-count defaults to DEFAULT_ENVELOPE_COUNT (backward compat).

    ``_compose_ns`` builds a Namespace with no ``envelope_count`` attribute, so
    this exercises the ``getattr(args, 'envelope_count', None) is None`` branch
    — the path every pre-TASK-16 caller takes. The composed manifest and result
    both carry the single-envelope default.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='envelope-absent',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT
    manifest = read_manifest('envelope-absent')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT



def test_envelope_count_none_value_defaults(plan_context):
    """An explicit envelope_count=None (argparse default) also yields the default.

    Distinct from the absent-attribute path above: here the attribute is
    present but ``None`` (the argparse ``default=None``). Both must resolve to
    DEFAULT_ENVELOPE_COUNT.
    """
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            None,
            plan_id='envelope-none',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT
    manifest = read_manifest('envelope-none')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT



@pytest.mark.parametrize('raw,expected', [(0, 1), (-3, 1)])
def test_envelope_count_non_positive_clamped_to_default(plan_context, raw, expected):
    """Non-positive envelope_count is clamped — the orchestrator always plans at least one envelope."""
    plan_id = f'envelope-clamp-{raw}'
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            raw,
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == expected
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == expected



def test_envelope_count_written_on_early_terminate_rule(plan_context):
    """envelope_count is written across every decision-matrix rule — including early_terminate.

    Rule 1 (early_terminate_analysis) produces a minimal phase_5 block; the
    composer still stamps envelope_count onto it so the phase_5 block always
    carries the key regardless of which rule fired.
    """
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            3,
            plan_id='envelope-early-terminate',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    assert result['phase_5']['early_terminate'] is True
    assert result['phase_5']['envelope_count'] == 3
    manifest = read_manifest('envelope-early-terminate')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == 3



def test_envelope_count_round_trip_read(plan_context):
    """compose → read round-trip: the read subcommand surfaces envelope_count.

    cmd_read returns the full persisted manifest, so phase_5.envelope_count is
    visible to the orchestrator's read-side consumer exactly as composed.
    """
    cmd_compose(
        _compose_ns_with_envelope_count(
            5,
            plan_id='envelope-round-trip',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    read_result = _mem.cmd_read(Namespace(plan_id='envelope-round-trip'))
    assert read_result is not None and read_result['status'] == 'success'
    assert read_result['phase_5']['envelope_count'] == 5



def test_envelope_count_absent_reads_cleanly_round_trip(plan_context):
    """A manifest composed without --envelope-count reads back with the default — no KeyError."""
    cmd_compose(
        _compose_ns(
            plan_id='envelope-absent-round-trip',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    read_result = _mem.cmd_read(Namespace(plan_id='envelope-absent-round-trip'))
    assert read_result is not None and read_result['status'] == 'success'
    assert read_result['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT
