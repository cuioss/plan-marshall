# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Namespace,
    _clear_arch_resolve_cache,
    _core,
    _mem,
)


class TestValidateAcceptsRoutedGeneralizedStep:
    """(iv) ``validate`` passes when the allow-list includes the routed ``verify:{verb}`` ID."""

    def test_validate_passes_with_routed_id_in_allow_list(self, plan_context):
        plan_id = 'route-validate-allow'
        body = {
            'manifest_version': _core.MANIFEST_VERSION,
            'plan_id': plan_id,
            'phase_5': {'early_terminate': False, 'verification_steps': ['verify:perf-suite']},
            'phase_6': {'steps': []},
        }
        _mem.write_manifest(plan_id, body)

        result = _mem.cmd_validate(
            Namespace(
                plan_id=plan_id,
                phase_5_steps='default:verify:perf-suite',
                phase_6_steps=None,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['valid'] is True
        assert result['phase_5_unknown_steps_count'] == 0
