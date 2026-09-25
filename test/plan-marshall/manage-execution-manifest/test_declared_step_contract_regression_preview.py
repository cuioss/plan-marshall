# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_declared_step_contract_regression_fixtures import (
    _EMITTER,
    Namespace,
    _compose_ns,
    _mem,
    _persisted_phase_6_steps,
    _seed_marshal,
    _write_execution_profile,
    cmd_compose,
    cmd_lanes_preview,
)

# =============================================================================
# (c) Preview membership agrees with compose membership
# =============================================================================


class TestPreviewAgreesWithCompose:
    """``lanes preview`` and ``compose`` report the same steps for the same seed."""

    #: Every member's fate is decided by marshal configuration alone — none is in
    #: the plan-input-dependent family — so the preview can reach the composer's
    #: verdict exactly and the advisory must come back empty.
    #:
    #: Deliberately SCRAMBLED relative to frontmatter order (the merge/archive tail
    #: is seeded first) so the sequence assertions below are not satisfied by an
    #: already-ordered seed.
    _CONFIG_DECIDED_SEED: dict[str, dict | None] = {
        'default:branch-cleanup': None,  # order 70
        'default:archive-plan': None,  # order 1100
        'default:create-pr': None,  # order 20
        'default:ci-verify': None,  # order 22
        'default:lessons-capture': None,
        _EMITTER: None,  # order 992
    }

    def test_preview_membership_equals_compose_membership(self, plan_context):
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        _write_execution_profile(plan_context, 'dsc-agree', 'full')

        compose_result = cmd_compose(_compose_ns('dsc-agree'))
        assert compose_result is not None and compose_result['status'] == 'success'
        composed = _persisted_phase_6_steps('dsc-agree')

        preview = cmd_lanes_preview(Namespace(plan_id='dsc-agree', phase_6_steps=None))
        assert preview is not None and preview['status'] == 'success'
        previewed = preview['lanes']['full']['phase_6_steps']

        assert set(previewed) == set(composed)

    def test_preview_sequence_equals_compose_sequence(self, plan_context):
        """Agreement covers ORDER too — the divergence this reconciliation closed.

        The preview applies the composer's frontmatter-order sort, so an inverted
        seed renders identically on both surfaces.
        """
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        _write_execution_profile(plan_context, 'dsc-agree-seq', 'full')

        cmd_compose(_compose_ns('dsc-agree-seq'))
        composed = _persisted_phase_6_steps('dsc-agree-seq')
        preview = cmd_lanes_preview(Namespace(plan_id='dsc-agree-seq', phase_6_steps=None))

        assert preview['lanes']['full']['phase_6_steps'] == composed

    def test_discriminator_raw_lane_projection_alone_would_disagree(self, plan_context):
        """Non-vacuity: the unsorted projection the preview USED to return differs.

        Pre-fix the preview returned ``_apply_lane_resolution``'s output verbatim,
        which preserves the seed sequence. Asserting that the raw projection does
        NOT match the composed sequence — while the preview does — shows the
        agreement is produced by the reconciliation, not by the seed happening to
        be ordered already.
        """
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        _write_execution_profile(plan_context, 'dsc-agree-discriminator', 'full')

        cmd_compose(_compose_ns('dsc-agree-discriminator'))
        composed = _persisted_phase_6_steps('dsc-agree-discriminator')

        candidates = [_mem.canonicalize_step_key(k) for k in self._CONFIG_DECIDED_SEED]
        raw_kept, _dropped, _warnings = _mem._apply_lane_resolution(candidates, 'full', None)
        assert raw_kept != composed, 'seed must be inverted for this discriminator to bite'

        preview = cmd_lanes_preview(Namespace(plan_id='dsc-agree-discriminator', phase_6_steps=None))
        assert preview['lanes']['full']['phase_6_steps'] == composed

    def test_config_decided_seed_reports_an_empty_advisory(self, plan_context):
        """No member's fate needs a plan input, so the preview claims full agreement."""
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        preview = cmd_lanes_preview(Namespace(plan_id='dsc-advisory-empty', phase_6_steps=None))

        assert preview is not None
        assert preview['plan_input_dependent_steps'] == []

    def test_plan_input_dependent_member_is_named(self, plan_context):
        """A member the preview cannot decide for is named rather than silently shown."""
        seed = dict(self._CONFIG_DECIDED_SEED)
        seed['default:pre-submission-self-review'] = None
        _seed_marshal(seed)

        preview = cmd_lanes_preview(Namespace(plan_id='dsc-advisory-named', phase_6_steps=None))

        assert preview is not None
        assert 'pre-submission-self-review' in preview['plan_input_dependent_steps']
