# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_boundary_normalization_strips_prefix_for_all_downstream_consumers(plan_context):
    """Boundary contract — every entry the cascade-rule layer + downstream output sees is bare.

    Pins the boundary-normalization invariant: ``cmd_compose`` strips a single
    leading ``default:``
    from each ``phase_5_candidates`` and ``phase_6_candidates`` entry once at
    intake (via ``canonicalize_step_key``), and every downstream site — the
    six-row matrix, ``_apply_commit_push_disabled``,
    ``_apply_pre_push_quality_gate_inactive``, ``_apply_security_class_inactive``
    and ``_apply_scope_gated_finalize`` — consumes those already-bare strings
    without any per-site ``canonicalize_step_key`` call.

    The test feeds a deliberately MIXED candidate list (some entries
    prefixed, some bare, plus a project-prefixed entry to demonstrate the
    ``project:`` prefix is preserved verbatim) to ``cmd_compose``, then
    asserts that every default-domain entry in the resulting
    ``phase_6.steps`` is bare. The only entry that retains its leading
    prefix is the ``project:`` step — its prefix is the canonical
    typed-step notation and is NOT stripped by ``canonicalize_step_key``
    (which only normalizes the ``default:`` namespace).

    This invariant guards against regressions where a future contributor
    re-introduces a per-site ``canonicalize_step_key`` call that masks a
    boundary leak: with the prefix stripped at intake, a per-site strip
    becomes dead code, and a missing intake strip becomes a visible test
    failure here rather than a silent functional drift.
    """
    mixed = [
        # Prefixed default entries.
        'default:push',
        'default:create-pr',
        'plan-marshall:automatic-review',
        # Bare default entries (no prefix to strip).
        'lessons-capture',
        # Typed-step entry (project: prefix is preserved verbatim).
        'project:finalize-step-plugin-doctor',
        # More prefixed defaults.
        'default:branch-cleanup',
        'default:archive-plan',
    ]
    mixed_phase_5 = [
        'default:quality-gate',  # prefixed
        'module-tests',  # bare
    ]
    # Use a Row 7 (default) shape so the cascade-rule output preserves
    # candidates verbatim (modulo boundary normalization). No CI configured.
    result = cmd_compose(
        _compose_ns(
            plan_id='boundary-mixed',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=10,
            phase_5_steps=','.join(mixed_phase_5),
            phase_6_steps=','.join(mixed),
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'default'

    manifest = read_manifest('boundary-mixed')
    assert manifest is not None
    phase_5_steps = manifest['phase_5']['verification_steps']
    phase_6_steps = manifest['phase_6']['steps']

    # Every default-domain entry is bare — no `default:` prefix anywhere
    # in either phase's output.
    assert not any(s.startswith('default:') for s in phase_5_steps), (
        f'phase_5 leaked `default:`-prefixed entry: {phase_5_steps!r}'
    )
    assert not any(s.startswith('default:') for s in phase_6_steps), (
        f'phase_6 leaked `default:`-prefixed entry: {phase_6_steps!r}'
    )

    # Phase 5 carries the bare normalization of both inputs.
    assert phase_5_steps == ['quality-gate', 'module-tests']

    # Every Phase-6 default-domain entry from the input survives as a bare
    # string after Row 7 (no cascade-rule subtractions on the default rule).
    for bare_default in (
        'push',
        'create-pr',
        'automatic-review',
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    ):
        assert bare_default in phase_6_steps, f'expected bare {bare_default!r} in phase_6 but got: {phase_6_steps!r}'

    # The non-default-namespace `project:` prefix is preserved verbatim —
    # boundary normalization strips ONLY the `default:` namespace.
    assert 'project:finalize-step-plugin-doctor' in phase_6_steps
