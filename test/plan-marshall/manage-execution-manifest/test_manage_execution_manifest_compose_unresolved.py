# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _seed_marshal_with_finalize_steps,
    cmd_compose,
    read_manifest,
)


class TestUnresolvedAskProviderDropCompose:
    """End-to-end compose round-trip of the D6 unresolved-ask provider-drop pre-filter."""

    def test_unresolved_ask_automatic_review_drops_when_no_ci_provider(self, plan_context):
        """{automatic-review: ask, no CI provider} → dropped from phase_6.steps."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider=None)
        result = cmd_compose(_compose_ns(plan_id='d6-ar-drop', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        # The compose pipeline boundary-normalizes every candidate to its bare
        # form before the pre-filters run (``canonicalize_step_key``), so the
        # promoted ``plan-marshall:automatic-review`` candidate is carried — and
        # dropped/reported — as bare ``automatic-review`` (the same bare form the
        # manifest stores, per the keep-case assertion below).
        assert 'automatic-review' in result['unresolved_ask_provider_dropped']
        manifest = read_manifest('d6-ar-drop')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automatic-review' not in steps and 'plan-marshall:automatic-review' not in steps
        # Non-infra candidates survive.
        assert 'push' in steps and 'archive-plan' in steps

    def test_unresolved_ask_automatic_review_kept_when_ci_provider_present(self, plan_context):
        """{automatic-review: ask, CI provider present} → kept."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider='github')
        result = cmd_compose(_compose_ns(plan_id='d6-ar-keep', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-ar-keep')['phase_6']['steps']
        assert 'automatic-review' in steps

    def test_unresolved_ask_sonar_roundtrip_drops_when_no_sonar_provider(self, plan_context):
        """{sonar-roundtrip: ask, no Sonar provider} → dropped."""
        steps_map = {
            'push': {},
            'default:sonar-roundtrip': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, sonar_provider=False)
        result = cmd_compose(_compose_ns(plan_id='d6-sr-drop', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert 'sonar-roundtrip' in result['unresolved_ask_provider_dropped']
        steps = read_manifest('d6-sr-drop')['phase_6']['steps']
        assert 'sonar-roundtrip' not in steps
        assert 'push' in steps and 'archive-plan' in steps

    def test_unresolved_ask_sonar_roundtrip_kept_when_sonar_provider_present(self, plan_context):
        """{sonar-roundtrip: ask, Sonar provider present} → kept."""
        steps_map = {
            'push': {},
            'default:sonar-roundtrip': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, sonar_provider=True)
        result = cmd_compose(_compose_ns(plan_id='d6-sr-keep', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-sr-keep')['phase_6']['steps']
        assert 'sonar-roundtrip' in steps

    def test_resolved_full_ask_with_provider_survives(self, plan_context):
        """A full-resolved ask (override overwritten to ``full``) with a configured
        provider is never dropped by this pre-filter."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'full'},
            'default:sonar-roundtrip': {'lane': 'full'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider='github', sonar_provider=True)
        result = cmd_compose(_compose_ns(plan_id='d6-resolved-full', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-resolved-full')['phase_6']['steps']
        assert 'automatic-review' in steps and 'sonar-roundtrip' in steps

    def test_resolved_standard_ask_survives_even_without_provider(self, plan_context):
        """A standard-resolved ask survives even when the provider is absent — only an
        UNRESOLVED ``ask`` is provider-gated by this pre-filter."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'standard'},
            'default:sonar-roundtrip': {'lane': 'standard'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider=None, sonar_provider=False)
        result = cmd_compose(_compose_ns(plan_id='d6-resolved-standard', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-resolved-standard')['phase_6']['steps']
        assert 'automatic-review' in steps and 'sonar-roundtrip' in steps
