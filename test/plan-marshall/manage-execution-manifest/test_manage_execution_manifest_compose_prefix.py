# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_prefix_normalization_no_op_for_bare_candidates(plan_context):
    """Sanity: boundary normalization is a no-op for bare candidates.

    The bare-name path (DEFAULT_PHASE_6_STEPS) must continue to work identically
    to the prefixed path. Rule 5 with bare candidates pins the bare-name shape
    end-to-end — boundary stripping at ``cmd_compose`` intake leaves bare names
    unchanged, so the cascade-rule layer sees and emits the same bare strings.

    Review gates are retained under Rule 5; only the legacy 'ci-wait' step ID
    is defensively narrowed out when present in the candidate list.
    """
    bare = (
        'push',
        'create-pr',
        'automatic-review',
        'sonar-roundtrip',
        'ci-wait',  # legacy; should be defensively narrowed out.
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-noop-bare',
            change_type='bug_fix',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_6_steps=','.join(bare),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
    manifest = read_manifest('prefix-noop-bare')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    assert 'push' in steps
    assert 'lessons-capture' in steps
