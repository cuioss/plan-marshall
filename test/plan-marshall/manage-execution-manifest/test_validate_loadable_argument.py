# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_validate_loadable_fixtures import _validate_loadable_ns, cmd_validate_loadable

# =============================================================================
# Mutual exclusivity
# =============================================================================


class TestArgumentValidation:
    def test_neither_step_id_nor_all_returns_invalid_arguments(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-neither'))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'

    def test_both_step_id_and_all_returns_invalid_arguments(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-both', step_id='push', use_all=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'
