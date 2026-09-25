# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import UNMEASURED_COLUMN_TOKEN, load_script_module


def test_unmeasured_token_matches_the_sibling_ledger():
    """The mirrored literal agrees with ``manage-metrics``' own definition.

    The absence-vs-zero contract is a property of the ledger FAMILY, so the two
    skills define the same literal independently (they run in different processes
    and neither may import the other's private module). Nothing but this check
    stops the two drifting into two different tokens, at which point every
    cross-ledger reader would silently classify one skill's unmeasured column as
    unrecognised.
    """
    metrics = load_script_module('plan-marshall', 'manage-metrics', 'manage-metrics.py', module_name='_mm_token_drift')

    assert UNMEASURED_COLUMN_TOKEN == metrics.UNMEASURED_COLUMN_TOKEN
