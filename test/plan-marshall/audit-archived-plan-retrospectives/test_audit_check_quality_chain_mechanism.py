#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``quality-chain`` mechanism and resolution — how a finding's chain is assembled
and how its shift-left tier is resolved.
"""

from _audit_fixtures import audit


class TestQualityChainMechanism:
    """``_qc_mechanism`` classifies which quality gate surfaced a finding."""

    def test_build_files_classify_as_build(self):
        assert audit._qc_mechanism('test-failure.jsonl', {}) == 'build'
        assert audit._qc_mechanism('build-error.jsonl', {}) == 'build'

    def test_bot_pr_comment_is_auto_review(self):
        assert (
            audit._qc_mechanism('pr-comment.jsonl', {'detail': 'gemini-code-assist says'})
            == 'auto-review'
        )

    def test_human_pr_comment_is_human_review(self):
        assert (
            audit._qc_mechanism('pr-comment.jsonl', {'detail': 'reviewer asks to rename'})
            == 'human-review'
        )

    def test_qgate_and_assessments_are_self_review(self):
        assert audit._qc_mechanism('qgate-phase-6.jsonl', {}) == 'self-review'
        assert audit._qc_mechanism('assessments.jsonl', {}) == 'self-review'
        assert audit._qc_mechanism('other.jsonl', {'source': 'qgate'}) == 'self-review'

    def test_user_review_source_is_human_review(self):
        assert audit._qc_mechanism('other.jsonl', {'source': 'user_review'}) == 'human-review'

    def test_unclassified_is_other(self):
        assert audit._qc_mechanism('mystery.jsonl', {}) == 'other'


class TestQualityChainResolution:
    """``_qc_resolution`` buckets a finding's disposition via resolution +
    resolution_detail regex."""

    def test_promoted_short_circuits_to_lesson(self):
        assert audit._qc_resolution({'promoted': True, 'resolution': 'fixed'}) == 'lesson'

    def test_fixed_without_rerun_is_direct_fix(self):
        assert audit._qc_resolution({'resolution': 'fixed', 'resolution_detail': 'patched'}) == 'direct_fix'

    def test_fixed_with_flake_detail_is_rerun_flake(self):
        assert (
            audit._qc_resolution({'resolution': 'fixed', 'resolution_detail': 'transient flake, re-run'})
            == 'rerun_flake'
        )

    def test_taken_into_account_with_task_detail_is_loop_back(self):
        assert (
            audit._qc_resolution(
                {'resolution': 'taken_into_account', 'resolution_detail': 'addressed by TASK-012'}
            )
            == 'loop_back'
        )

    def test_taken_into_account_without_marker_is_direct_fix(self):
        assert (
            audit._qc_resolution({'resolution': 'taken_into_account', 'resolution_detail': 'done inline'})
            == 'direct_fix'
        )

    def test_accepted_suppressed_rejected_pass_through(self):
        assert audit._qc_resolution({'resolution': 'accepted'}) == 'accepted'
        assert audit._qc_resolution({'resolution': 'suppressed'}) == 'suppressed'
        # `rejected` is the ext-point-verify validity-stage disposition (#788); it
        # is a first-class resolution bucket, not a KeyError into the matrix.
        assert audit._qc_resolution({'resolution': 'rejected'}) == 'rejected'
        assert 'rejected' in audit._QC_RESOLUTIONS

    def test_pending_none_empty_bucket_to_pending(self):
        assert audit._qc_resolution({'resolution': 'pending'}) == 'pending'
        assert audit._qc_resolution({'resolution': 'none'}) == 'pending'
        assert audit._qc_resolution({'resolution': ''}) == 'pending'
        assert audit._qc_resolution({}) == 'pending'
        # An unrecognized resolution coerces to `pending` rather than returning
        # an unbucketed value that would KeyError the matrix (the next #788-style
        # disposition addition is crash-safe, surfaced as unresolved).
        assert audit._qc_resolution({'resolution': 'unrecognized_disposition'}) == 'pending'


class TestQualityChainShiftLeftTier:
    """``_qc_shift_left_tier`` grades how deterministically the surfacer could
    have caught a finding."""

    def test_regex_keyword_is_tier1(self):
        assert audit._qc_shift_left_tier({'title': 'regex pattern over-fits the input'}) == 1

    def test_duplication_keyword_is_tier1(self):
        assert audit._qc_shift_left_tier({'detail': 'duplicated wording across two sections'}) == 1

    def test_naming_keyword_is_tier2(self):
        assert audit._qc_shift_left_tier({'title': 'rename this helper for clarity'}) == 2

    def test_logic_keyword_is_tier3(self):
        assert audit._qc_shift_left_tier({'detail': 'off-by-one bug in the boundary check'}) == 3

    def test_sparse_body_is_tier4(self):
        assert audit._qc_shift_left_tier({'title': 'see comment'}) == 4
