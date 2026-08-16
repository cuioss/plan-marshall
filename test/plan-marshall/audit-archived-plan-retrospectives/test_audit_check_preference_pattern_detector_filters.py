#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``preference-pattern-detector`` filters — the authorship filter, the unattributed
bucket that is never promoted, the threshold alias, and aspect registration.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_preference_plan,
    audit,
)


class TestPreferenceAuthorshipFilter:
    """D1 — a finding authored by the pipeline itself cannot seed a preference.

    A ``pr-comment`` finding contributes to preference learning only when it is
    positively attributed to a recognized external reviewer bot (``bot_kind``).
    The ingest verb records the pipeline's OWN posted PR comments with
    ``bot_kind`` absent — indistinguishable from an unattributed human comment —
    so admitting a ``bot_kind``-less ``pr-comment`` would let the pipeline's own
    control traffic become evidence about the pipeline's preferences (the
    self-reinforcing measurement artifact this guard closes). Module attribution
    on these fixtures isolates D1 from the D2 (default-bucket) gate.
    """

    def test_self_authored_pr_comment_excluded_from_preferences(self, tmp_path: Path):
        # A pr-comment with NO bot_kind recurs across 3 plans — the shape of the
        # pipeline's own posted comment. Pre-fix it promotes; the guard drops it.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'self-{i}',
                [{
                    'type': 'pr-comment',
                    'title': 'Pipeline note',
                    'resolution': 'taken_into_account',
                    'module': 'python',
                    'author': 'repo-owner-bot',
                }],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []

    def test_bot_attributed_pr_comment_remains_a_preference(self, tmp_path: Path):
        # NEGATIVE CONTROL — a pr-comment positively attributed to a recognized
        # reviewer bot MUST still promote. A filter that suppresses this too has
        # broken the feature to fix the bug.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'bot-{i}',
                [{
                    'type': 'pr-comment',
                    'title': 'Reviewer claim',
                    'resolution': 'suppressed',
                    'module': 'python',
                    'author': 'coderabbitai',
                    'bot_kind': 'coderabbit',
                }],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 1
        row = result['rows'][0]
        assert row['module'] == 'python'
        assert row['finding_class'] == 'reviewer claim'
        assert row['disposition'] == 'suppressed'

    def test_mixed_corpus_keeps_only_bot_attributed(self, tmp_path: Path):
        # Each plan carries BOTH a self-authored pr-comment (no bot_kind) and a
        # bot-attributed one. Pre-fix: candidate_count == 2. Post-fix: only the
        # bot-attributed tuple survives — the suppression and the negative
        # control proved in one assertion.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'mix-{i}',
                [
                    {
                        'type': 'pr-comment',
                        'title': 'Self note',
                        'resolution': 'taken_into_account',
                        'module': 'python',
                        'author': 'repo-owner-bot',
                    },
                    {
                        'type': 'pr-comment',
                        'title': 'Bot note',
                        'resolution': 'taken_into_account',
                        'module': 'python',
                        'author': 'coderabbitai',
                        'bot_kind': 'coderabbit',
                    },
                ],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 1
        assert result['rows'][0]['finding_class'] == 'bot note'

    def test_non_comment_finding_unaffected_by_authorship_filter(self, tmp_path: Path):
        # The authorship gate is scoped to pr-comment findings. A tool finding
        # (lint-issue) carries no author and no bot_kind, and MUST still promote —
        # it is exactly the tool-disposition signal preference learning exists for.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'lint-{i}',
                [{
                    'type': 'lint-issue',
                    'title': 'Unused import',
                    'resolution': 'suppressed',
                    'module': 'python',
                }],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 1
        assert result['rows'][0]['finding_class'] == 'unused import'

    def test_human_reviewer_pr_comment_without_bot_kind_is_excluded(self, tmp_path: Path):
        # CHARACTERIZATION of a deliberate fail-closed consequence: an external
        # HUMAN reviewer's pr-comment carries an author login but no bot_kind, and
        # is INDISTINGUISHABLE on the finding from the pipeline's own posted
        # comment (both bot_kind-absent, both author-bearing). With no self-login
        # signal available, the gate admits ONLY positively bot-attributed
        # comments, so a human pr-comment is excluded too. This is intended, not a
        # bug — human PR comments carry per-comment-unique title signatures and
        # essentially never recur into a durable preference anyway, while the
        # feature's real value (tool-disposition recurrences) is untouched.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'human-{i}',
                [{
                    'type': 'pr-comment',
                    'title': 'Consider a guard clause',
                    'resolution': 'taken_into_account',
                    'module': 'python',
                    'author': 'some-human-reviewer',
                }],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []

    def test_unrecognized_bot_kind_pr_comment_is_excluded(self, tmp_path: Path):
        # The gate admits a pr-comment ONLY when its bot_kind is a RECOGNIZED
        # reviewer identity. `add_finding` validates bot_kind at write time, but the
        # auditor reads archived JSONL directly, so a legacy / de-registered /
        # hand-edited record carrying an unrecognized bot_kind (here `sonarcloud`,
        # never a registered reviewer bot) must NOT slip through and seed a
        # preference. Validation is against the live registry-derived set.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'bogus-{i}',
                [{
                    'type': 'pr-comment',
                    'title': 'Spurious claim',
                    'resolution': 'taken_into_account',
                    'module': 'python',
                    'author': 'sonarcloud',
                    'bot_kind': 'sonarcloud',
                }],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []


class TestPreferenceUnattributedBucketNotPromoted:
    """D2 — a recurrence collapsing to the ``default`` fallback bucket is the
    UNATTRIBUTED sink (no module, no component), not a genuine cross-cutting
    judgement, and is NOT promotable. Promoting it would route an unverified hint
    to the widest blast radius — the unattributed ``default`` sink. This gate is
    SEPARATE from D1's authorship filter: it fires on ATTRIBUTION, not authorship —
    the fixtures here use non-comment findings so D1 never touches them.
    """

    def test_default_bucket_tuple_not_promoted_but_counted(self, tmp_path: Path):
        # A non-comment finding (untouched by D1) with no module/component recurs
        # across 3 plans → the `default` bucket. Pre-fix it promotes; D2 excludes
        # it from candidates and records it in unattributed_excluded_count.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'u-{i}',
                [{'type': 'lint-issue', 'title': 'Broad rule', 'resolution': 'suppressed'}],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []
        assert result['unattributed_excluded_count'] == 1

    def test_module_attributed_survives_alongside_default(self, tmp_path: Path):
        # NEGATIVE CONTROL, mixed corpus: each plan carries a default-bucket tuple
        # AND a module-attributed tuple. Pre-fix: candidate_count == 2. Post-fix:
        # only the module-attributed tuple survives; the unattributed one is
        # counted-and-dropped. A gate that suppressed both would break the feature.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'm-{i}',
                [
                    {'type': 'lint-issue', 'title': 'Broad rule', 'resolution': 'suppressed'},
                    {'type': 'lint-issue', 'title': 'Scoped rule', 'resolution': 'suppressed', 'module': 'python'},
                ],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 1
        assert result['rows'][0]['module'] == 'python'
        assert result['rows'][0]['finding_class'] == 'scoped rule'
        assert result['unattributed_excluded_count'] == 1


class TestPreferencePatternThresholdAlias:
    """The threshold is the centralized THRESHOLDS constant, not a hard-coded
    literal."""

    def test_threshold_reads_from_table(self, tmp_path: Path):
        result = audit.cross_preference_pattern([])
        assert result['threshold'] == audit.THRESHOLDS['preference_disposition_occurrences']


class TestPreferencePatternRegistry:
    """``preference-pattern-detector`` is wired into both registries as a
    cross-plan check."""

    def test_registered_as_cross_plan(self):
        assert 'preference-pattern-detector' in audit.CHECK_NAMES
        assert 'preference-pattern-detector' in audit.CROSS_PLAN_CHECKS

    def test_synthesis_still_runs_last(self):
        # the new check is inserted BEFORE the synthesis sentinel
        assert audit.CHECK_NAMES[-1] == 'cross-check-synthesis'
        assert audit.CHECK_NAMES.index('preference-pattern-detector') < (
            audit.CHECK_NAMES.index('cross-check-synthesis')
        )

    def test_check_is_a_valid_cli_choice(self):
        # --check choices come from CHECK_NAMES, so membership = selectable
        assert 'preference-pattern-detector' in audit.CHECK_NAMES
