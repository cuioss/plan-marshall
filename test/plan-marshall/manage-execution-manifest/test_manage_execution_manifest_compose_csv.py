# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_csv_fallback_when_marshal_json_missing(plan_context):
    """Without marshal.json, the composer falls back to the CSV input verbatim.

    Backward-compat: existing tests that don't stage a marshal.json continue
    to drive composition via the ``--phase-{5,6}-steps`` flag.
    """
    # No marshal.json is written.
    result = cmd_compose(
        _compose_ns(
            plan_id='csv-fallback',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('csv-fallback')
    assert manifest is not None
    # All DEFAULT_PHASE_6_STEPS survive (no marshal.json to override).
    steps = manifest['phase_6']['steps']
    for expected in ('push', 'create-pr', 'lessons-capture', 'archive-plan'):
        assert expected in steps
