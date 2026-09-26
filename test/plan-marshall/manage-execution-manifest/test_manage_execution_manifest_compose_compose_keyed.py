# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    _write_full_marshal,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# Keyed-map marshal.json read-through
#
# ``_read_marshal_phase_step_map`` / ``_read_marshal_phase_steps`` read the
# canonical keyed-map on-disk form, normalizing each value to the internal
# id-keyed map. These tests feed the keyed map through the composer end-to-end
# and assert the manifest snapshots the resolved params and the composed step
# sets. (The manifest's own ``step_params`` snapshot is an id-keyed dict; the
# manifest's ``steps`` / ``verification_steps`` are bare-name id lists.)
# =============================================================================


def test_compose_reads_keyed_map_marshal_preserves_prefixes(plan_context):
    """A keyed-map marshal.json composes the declared step set, preserving project: prefixes.

    The keyed map is the sole on-disk form; the composer reads it and preserves
    the ``project:`` prefix (only ``default:`` is stripped at intake).
    """
    phase_6 = [
        'default:push',
        'project:finalize-step-deploy-target',
        'default:create-pr',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:record-metrics',
        'default:archive-plan',
    ]
    phase_5 = ['verify:quality-gate', 'verify:module-tests']

    _write_full_marshal(plan_context.fixture_dir, phase_6_steps=phase_6, phase_5_steps=phase_5)
    cmd_compose(
        _compose_ns(
            plan_id='keyed-map-marshal',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
        )
    )
    keyed_manifest = read_manifest('keyed-map-marshal')
    assert keyed_manifest is not None

    # the project: prefix survives the keyed-map read (only default: is stripped)
    assert 'project:finalize-step-deploy-target' in keyed_manifest['phase_6']['steps']
    # the phase-5 verification step set is composed from the keyed map
    assert keyed_manifest['phase_5']['verification_steps'] == phase_5


def test_compose_reads_keyed_map_phase_5_verification_steps(plan_context):
    """The keyed-map read-through applies to phase-5 verification_steps as well.

    Mirrors the phase-6 read-through for the phase-5 verification_steps key —
    marshal.json is the source of truth over the agent CSV.
    """
    phase_5 = ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_6_steps=list(DEFAULT_PHASE_6_STEPS),
        phase_5_steps=phase_5,
    )
    cmd_compose(
        _compose_ns(
            plan_id='keyed-map-phase-5',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
            phase_5_steps='WRONG,STUFF',  # noise — marshal.json keyed map should win
        )
    )
    manifest = read_manifest('keyed-map-phase-5')
    assert manifest is not None
    # marshal.json keyed map wins over the agent CSV
    assert manifest['phase_5']['verification_steps'] == phase_5
