# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import (
    EXECUTION_LOG_KEY,
    UNMEASURED_COLUMN_TOKEN,
    _compose,
    _record_ns,
    cmd_record_step,
    read_manifest,
)


def test_omitted_flags_record_the_unmeasured_token(plan_context):
    """OMITTING the flags records the token — never a fabricated ``0``."""
    _compose('rec-unmeasured')

    result = cmd_record_step(_record_ns(plan_id='rec-unmeasured', step_id='verify:quality-gate', outcome='executed'))

    assert result is not None
    assert result['total_tokens'] == UNMEASURED_COLUMN_TOKEN
    assert result['tool_uses'] == UNMEASURED_COLUMN_TOKEN
    assert result['duration_ms'] == UNMEASURED_COLUMN_TOKEN
    entry = read_manifest('rec-unmeasured')[EXECUTION_LOG_KEY][0]
    assert entry['total_tokens'] == UNMEASURED_COLUMN_TOKEN
    assert entry['tool_uses'] == UNMEASURED_COLUMN_TOKEN
    assert entry['duration_ms'] == UNMEASURED_COLUMN_TOKEN
