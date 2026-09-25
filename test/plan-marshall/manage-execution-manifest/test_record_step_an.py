# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import _compose, _record_ns, cmd_record_step


def test_an_outcome_outside_the_partition_is_still_refused(plan_context):
    """Widening the vocabulary must not widen it to anything.

    Without this the two additions above would be indistinguishable from
    dropping the membership check altogether.
    """
    _compose('rec-partition-closed')

    result = cmd_record_step(_record_ns(plan_id='rec-partition-closed', step_id='x', outcome='returned_with_findings'))

    assert result is not None
    assert result['error'] == 'invalid_outcome'
