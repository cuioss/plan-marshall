# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    _apply_unresolved_ask_provider_drop,
    _override_map,
    _restore_footprint_resolver,
    pytest,
)


class TestUnresolvedAskProviderDropPreFilter:
    """Direct unit coverage of the D6 unresolved-ask provider-drop pre-filter."""

    @pytest.mark.parametrize(
        'ar_lane,ci_provider,expect_present',
        [
            ('ask', None, False),  # unresolved ask + no CI provider → DROP
            ('ask', 'github', True),  # unresolved ask + CI provider → keep
            ('ask', 'gitlab', True),  # provider identity is irrelevant — any non-None keeps
            ('auto', None, True),  # resolved auto (steward answered) → keep even w/o provider
            ('full', None, True),  # resolved full → keep even w/o provider
            ('off', None, True),  # off is resolved; the later lane pass drops it, not this one
        ],
    )
    def test_automatic_review_truth_table(self, ar_lane, ci_provider, expect_present):
        candidates = ['plan-marshall:automatic-review', 'push', 'archive-plan']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane=ar_lane), ci_provider, None
        )
        assert ('plan-marshall:automatic-review' in kept) is expect_present
        assert ('plan-marshall:automatic-review' in dropped) is (not expect_present)
        # Non-infra candidates are never disturbed.
        assert 'push' in kept and 'archive-plan' in kept

    @pytest.mark.parametrize(
        'sr_lane,sonar_provider,expect_present',
        [
            ('ask', None, False),  # unresolved ask + no Sonar provider → DROP
            ('ask', 'sonar', True),  # unresolved ask + Sonar provider → keep
            ('auto', None, True),  # resolved auto → keep even w/o provider
            ('full', None, True),  # resolved full → keep even w/o provider
            ('off', None, True),  # off is resolved; dropped later by the lane pass, not here
        ],
    )
    def test_sonar_roundtrip_truth_table(self, sr_lane, sonar_provider, expect_present):
        # The candidate list is boundary-normalized in compose (``default:`` is
        # stripped), so the helper is given the bare ``sonar-roundtrip`` form.
        candidates = ['sonar-roundtrip', 'push']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(sr_lane=sr_lane), None, sonar_provider
        )
        assert ('sonar-roundtrip' in kept) is expect_present
        assert ('sonar-roundtrip' in dropped) is (not expect_present)
        assert 'push' in kept

    def test_both_unresolved_no_providers_drop_both(self):
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip', 'push']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask', sr_lane='ask'), None, None
        )
        assert kept == ['push']
        assert set(dropped) == {'plan-marshall:automatic-review', 'sonar-roundtrip'}

    def test_provider_isolation_ci_present_sonar_absent(self):
        # A configured CI provider keeps automatic-review; an absent Sonar
        # provider still drops an unresolved sonar-roundtrip. The two elements
        # are keyed to distinct providers.
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask', sr_lane='ask'), 'github', None
        )
        assert kept == ['plan-marshall:automatic-review']
        assert dropped == ['sonar-roundtrip']

    def test_no_override_keeps_infra_elements(self):
        # No marshal override at all (e.g. CSV-fallback, marshal_map None/empty):
        # the effective tier is undeterminable, not ``ask``, so nothing is dropped
        # (conservative keep).
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip']
        for override_map in ({}, None):
            kept, dropped = _apply_unresolved_ask_provider_drop(candidates, override_map, None, None)
            assert dropped == []
            assert kept == candidates

    def test_non_infra_elements_pass_through_untouched(self):
        candidates = ['push', 'archive-plan', 'finalize-step-simplify']
        kept, dropped = _apply_unresolved_ask_provider_drop(candidates, _override_map(ar_lane='ask'), None, None)
        assert kept == candidates
        assert dropped == []

    def test_does_not_mutate_input_list(self):
        candidates = ['plan-marshall:automatic-review', 'push']
        _apply_unresolved_ask_provider_drop(candidates, _override_map(ar_lane='ask'), None, None)
        assert candidates == ['plan-marshall:automatic-review', 'push']
