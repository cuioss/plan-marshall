#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the same-run review/simplify reconciliation seam (plan 130 D1).

``finalize-step-simplify`` and ``automatic-review`` both run inside one finalize
pass, and simplify is ``head_dependent`` — so a loop-back fix commit answering a
review comment re-fires the simplification sweep over the very lines that fix
produced. Nothing today stops that sweep deleting a line the review process
committed to earlier in the SAME run, and a silent deletion reverses a review
decision with no record anywhere.

The seam is pure and deterministic: derive the run's commitments from the plan's
``pr-comment`` findings, parse the simplify pass's own deletions out of its diff,
and reconcile the two. It never edits and never blocks — it makes a conflicting
removal VISIBLE, which is the property the deliverable asks for.

Fail-closed discipline is the load-bearing half. An untriaged finding's
disposition is UNKNOWN, and an anchor-less finding's line is UNKNOWN; reading
either as "no commitment here" is absence-laundered-into-a-negative, so both
resolve to a conflict rather than to silence.
"""

import pytest
from review_commitments import (
    COMMITTED_RESOLUTIONS,
    RELEASED_RESOLUTIONS,
    Commitment,
    Deletion,
    derive_commitments,
    parse_deletions,
    reconcile,
)

# ---------------------------------------------------------------------------
# derive_commitments — which findings bind a line
# ---------------------------------------------------------------------------


def _finding(**overrides):
    record = {
        'hash_id': 'f1',
        'file_path': 'pkg/mod.py',
        'line': 10,
        'resolution': 'fixed',
    }
    record.update(overrides)
    return record


def test_a_fixed_finding_commits_to_its_line():
    """`fixed` means the review asked and the run changed the code — a commitment."""
    commitments = derive_commitments([_finding(resolution='fixed')])

    assert len(commitments) == 1
    assert commitments[0].path == 'pkg/mod.py'
    assert commitments[0].line == 10
    assert commitments[0].basis == 'committed'


def test_acknowledged_dispositions_commit_too():
    """`accepted` / `taken_into_account` absorbed the reviewer's point — also commitments.

    The run took a position on the line. A later pass deleting it reverses that
    position exactly as deleting a `fixed` line does.
    """
    for resolution in ('accepted', 'taken_into_account'):
        commitments = derive_commitments([_finding(resolution=resolution)])
        assert len(commitments) == 1, resolution
        assert commitments[0].basis == 'committed'


def test_a_rejected_finding_releases_the_line():
    """`rejected` means the reviewer was wrong — nothing is owed to that line."""
    assert derive_commitments([_finding(resolution='rejected')]) == ()


def test_a_suppressed_finding_releases_the_line():
    """`suppressed` is an explicit decision NOT to act — no commitment follows."""
    assert derive_commitments([_finding(resolution='suppressed')]) == ()


def test_a_pending_finding_fails_closed_to_a_commitment():
    """An untriaged finding's disposition is UNKNOWN, so it is treated as binding.

    This is the fail-closed direction and it is the important one. Reading
    `pending` as "not a commitment" is exactly absence-read-as-a-negative: nobody
    has decided the line may go, so a pass that deletes it has pre-empted the
    triage that was going to decide.
    """
    commitments = derive_commitments([_finding(resolution='pending')])

    assert len(commitments) == 1
    assert commitments[0].basis == 'undecided'


def test_an_unrecognised_resolution_fails_closed_to_a_commitment():
    """A resolution outside the closed vocabulary is UNKNOWN, never a release.

    A resolution value this seam does not recognise cannot be read as a release —
    that would let a vocabulary change silently widen what simplify may delete.
    """
    commitments = derive_commitments([_finding(resolution='some_new_state')])

    assert len(commitments) == 1
    assert commitments[0].basis == 'undecided'


def test_the_two_resolution_sets_are_disjoint():
    """Committed and released are disjoint, so no resolution is classified twice."""
    assert not (COMMITTED_RESOLUTIONS & RELEASED_RESOLUTIONS)


def test_a_finding_with_no_file_path_anchors_nothing():
    """A review-body or issue comment is about the PR, not about a line.

    It carries no path, so it can bind no deletion. Excluded from the commitment
    set — but the exclusion is COUNTED by :func:`reconcile`, never invisible.
    """
    assert derive_commitments([_finding(file_path=None)]) == ()


def test_a_finding_with_a_path_but_no_line_binds_the_whole_file():
    """An anchor-less commitment is file-wide, because the line is UNKNOWN.

    `github_pr` files `line: None` for review-body kinds. Narrowing such a
    commitment to "no line, so no conflict" would let the highest-level review
    comments — the ones that carry the consolidated findings — bind nothing.
    """
    commitments = derive_commitments([_finding(line=None)])

    assert len(commitments) == 1
    assert commitments[0].line is None
    assert commitments[0].basis == 'committed'


# ---------------------------------------------------------------------------
# parse_deletions — what the simplify pass actually removed
# ---------------------------------------------------------------------------


_DIFF = """diff --git a/pkg/mod.py b/pkg/mod.py
index 1111111..2222222 100644
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -8,7 +8,5 @@ def widget():
     first
     second
-    removed_ten
-    removed_eleven
     kept
     tail
@@ -30,4 +28,4 @@ def other():
     alpha
-    removed_thirty_one
+    replacement
     omega
"""


def test_parse_deletions_reports_old_side_line_ranges():
    """Deleted lines are numbered on the OLD side, which is what a commitment anchors to."""
    deletions = parse_deletions(_DIFF)

    assert Deletion('pkg/mod.py', 10, 11) in deletions
    assert Deletion('pkg/mod.py', 31, 31) in deletions


def test_parse_deletions_groups_contiguous_runs():
    """A contiguous run is one range, not one entry per line."""
    deletions = parse_deletions(_DIFF)

    assert len(deletions) == 2


def test_parse_deletions_ignores_pure_additions():
    """A hunk that only adds lines removes nothing."""
    additions_only = (
        'diff --git a/pkg/new.py b/pkg/new.py\n'
        '--- a/pkg/new.py\n'
        '+++ b/pkg/new.py\n'
        '@@ -1,2 +1,4 @@\n'
        ' head\n'
        '+added\n'
        '+also_added\n'
        ' tail\n'
    )

    assert parse_deletions(additions_only) == ()


def test_parse_deletions_does_not_mistake_the_file_header_for_a_deletion():
    """`--- a/path` starts with a dash but is a header, not a removed line."""
    deletions = parse_deletions(_DIFF)

    assert all(d.path == 'pkg/mod.py' for d in deletions)
    assert all(d.start_line > 0 for d in deletions)


def test_the_no_newline_marker_does_not_shift_later_coordinates():
    """`\\ No newline at end of file` annotates the preceding line; it is not a line.

    Advancing the old-side counter past it shifts every subsequent coordinate in the
    hunk by one, which silently mis-anchors every conflict after it.
    """
    diff = (
        'diff --git a/pkg/mod.py b/pkg/mod.py\n'
        '--- a/pkg/mod.py\n'
        '+++ b/pkg/mod.py\n'
        '@@ -1,5 +1,5 @@\n'
        '-removed_one\n'
        '\\ No newline at end of file\n'
        '+added_one\n'
        ' context_two\n'
        '-removed_three\n'
    )

    deletions = parse_deletions(diff)

    assert Deletion('pkg/mod.py', 1, 1) in deletions
    # Without the fix the marker consumes line 2 and this lands on 4.
    assert Deletion('pkg/mod.py', 3, 3) in deletions


def test_a_removed_line_beginning_with_two_dashes_is_content_not_a_header():
    """`-` + `-- text` renders as `--- text`, which looks exactly like a file header.

    Prefix alone cannot disambiguate it; position can — a header precedes the first
    `@@` of a file, content follows it. Misreading it as a header silently drops the
    deletion AND repoints every later deletion in the hunk at a bogus path.
    """
    diff = (
        'diff --git a/doc/notes.md b/doc/notes.md\n'
        '--- a/doc/notes.md\n'
        '+++ b/doc/notes.md\n'
        '@@ -10,3 +10,2 @@\n'
        '--- a section rule\n'
        ' kept\n'
        '-trailing\n'
    )

    deletions = parse_deletions(diff)

    assert Deletion('doc/notes.md', 10, 10) in deletions
    assert Deletion('doc/notes.md', 12, 12) in deletions
    assert all(d.path == 'doc/notes.md' for d in deletions)


def test_parse_deletions_handles_a_whole_file_removal():
    """A deleted file's `+++ /dev/null` still attributes its removals to the old path."""
    removal = (
        'diff --git a/pkg/gone.py b/pkg/gone.py\n'
        '--- a/pkg/gone.py\n'
        '+++ /dev/null\n'
        '@@ -1,2 +0,0 @@\n'
        '-line_one\n'
        '-line_two\n'
    )

    assert parse_deletions(removal) == (Deletion('pkg/gone.py', 1, 2),)


# ---------------------------------------------------------------------------
# reconcile — the contract itself
# ---------------------------------------------------------------------------


def test_deleting_a_committed_line_is_surfaced_as_a_conflict():
    """THE deliverable: a line the review committed to cannot be removed silently.

    A `fixed` finding at pkg/mod.py:10, and a later simplify pass that deletes
    lines 10-11 of that file. Before this seam the deletion was applied, committed
    by the dispatcher's instrumentation, and pushed with no record that a review
    decision had been reversed.
    """
    commitments = derive_commitments([_finding(hash_id='abc123', line=10)])
    deletions = (Deletion('pkg/mod.py', 10, 11),)

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'conflict'
    assert len(result['conflicts']) == 1
    conflict = result['conflicts'][0]
    assert conflict['path'] == 'pkg/mod.py'
    assert conflict['finding_id'] == 'abc123'
    assert conflict['committed_line'] == 10


def test_a_deletion_elsewhere_in_the_same_file_is_clear():
    """The contract is not "never touch a reviewed file" — that would stop all simplification.

    Without this direction the seam would report a conflict on every deletion in
    any file a reviewer commented on, and a check that fires on everything is
    turned off within a week.
    """
    commitments = derive_commitments([_finding(line=10)])
    deletions = (Deletion('pkg/mod.py', 40, 42),)

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'clear'
    assert result['conflicts'] == []


def test_a_deletion_in_a_different_file_is_clear():
    """Commitments are path-scoped."""
    commitments = derive_commitments([_finding(file_path='pkg/mod.py', line=10)])
    deletions = (Deletion('pkg/other.py', 10, 10),)

    assert reconcile(deletions, commitments)['verdict'] == 'clear'


def test_a_deletion_spanning_a_committed_line_conflicts():
    """A range that CONTAINS the committed line conflicts, not only one that starts on it."""
    commitments = derive_commitments([_finding(line=12)])
    deletions = (Deletion('pkg/mod.py', 5, 20),)

    assert reconcile(deletions, commitments)['verdict'] == 'conflict'


def test_a_file_wide_commitment_conflicts_with_any_deletion_in_that_file():
    """The anchor-less fail-closed case: unknown line means every line is in question."""
    commitments = derive_commitments([_finding(line=None)])
    deletions = (Deletion('pkg/mod.py', 900, 901),)

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'conflict'
    assert result['conflicts'][0]['committed_line'] is None


def test_a_pending_finding_blocks_the_deletion_of_its_line():
    """The fail-closed disposition reaches the verdict, not just the commitment set."""
    commitments = derive_commitments([_finding(resolution='pending', line=10)])
    deletions = (Deletion('pkg/mod.py', 10, 10),)

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'conflict'
    assert result['conflicts'][0]['basis'] == 'undecided'


def test_the_verdict_publishes_the_populations_it_was_computed_over():
    """A clear verdict over zero commitments is not the same fact as a real clear.

    Without the populations, "no conflicts" from a run that had no commitments to
    check reads identically to one that checked many and found none — the
    empty-looks-like-perfect signal.
    """
    result = reconcile((), ())

    assert result['verdict'] == 'clear'
    assert result['commitments_considered'] == 0
    assert result['deletions_considered'] == 0


def test_unanchored_findings_are_counted_not_dropped_silently():
    """A finding that binds no line is excluded from the check AND reported.

    Its exclusion is legitimate, but an unreported exclusion shrinks the
    denominator invisibly.
    """
    findings = [
        _finding(hash_id='anchored', file_path='pkg/mod.py', line=10),
        _finding(hash_id='bodyless', file_path=None, line=None),
    ]
    commitments = derive_commitments(findings)

    result = reconcile((), commitments, unanchored=1)

    assert result['commitments_considered'] == 1
    assert result['unanchored_commitments'] == 1


def test_every_conflicting_deletion_is_reported_not_only_the_first():
    """Three conflicts are three rows — a bundled verdict loses the per-instance record."""
    commitments = (
        Commitment('pkg/a.py', 5, 'f-a', 'fixed', 'committed'),
        Commitment('pkg/b.py', 7, 'f-b', 'accepted', 'committed'),
    )
    deletions = (
        Deletion('pkg/a.py', 5, 5),
        Deletion('pkg/b.py', 7, 9),
        Deletion('pkg/c.py', 1, 1),
    )

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'conflict'
    assert len(result['conflicts']) == 2
    assert {c['finding_id'] for c in result['conflicts']} == {'f-a', 'f-b'}


def test_the_envelope_states_that_it_reports_rather_than_blocks():
    """The seam surfaces a conflict; it never decides the merge.

    Stated in the payload so a consumer cannot read a conflict as a merge verdict
    without ignoring a field that says otherwise — the same discipline
    `review_completeness deficit` uses for `gates_merge: false`.
    """
    result = reconcile((), ())

    assert result['proves'] == 'removal_conflict_only'
    assert result['gates_merge'] is False


# ---------------------------------------------------------------------------
# CLI surface — the contract finalize-step-simplify Step 3b actually invokes
# ---------------------------------------------------------------------------


class TestCLI:
    """The ``reconcile`` verb's argparse surface and its error branches.

    Step 3b invokes the CLI, not the pure functions, so a flag or emitter defect
    would ship green against the unit tests above.
    """

    @staticmethod
    def _script():
        from conftest import get_script_path

        return get_script_path('plan-marshall', 'phase-6-finalize', 'review_commitments.py')

    def test_an_unreadable_diff_is_an_error_with_no_verdict(self, tmp_path):
        """A crashed reconciliation must read UNKNOWN, never as a clear pass.

        Emitting `verdict: clear` here would be the false-clean signal the whole
        seam exists to prevent: the check did not run, so it found nothing.
        """
        from conftest import run_script

        result = run_script(
            self._script(),
            'reconcile',
            '--plan-id',
            'rc-missing-diff',
            '--diff-file',
            str(tmp_path / 'nope.diff'),
        )

        assert not result.success
        assert 'status: error' in result.stdout
        assert 'diff_unreadable' in result.stdout
        assert 'verdict:' not in result.stdout

    def test_both_flags_are_required(self):
        from review_commitments import build_parser

        with pytest.raises(SystemExit):
            build_parser().parse_args(['reconcile', '--plan-id', 'p'])
        with pytest.raises(SystemExit):
            build_parser().parse_args(['reconcile', '--diff-file', 'd'])

    def test_a_clear_run_emits_a_verdict_and_its_populations(self, tmp_path, plan_context):
        """The happy path through the real CLI, including the population fields."""
        from conftest import run_script

        plan_id = 'rc-cli-clear'
        plan_context.plan_dir_for(plan_id)
        diff = tmp_path / 'pass.diff'
        diff.write_text(
            'diff --git a/pkg/mod.py b/pkg/mod.py\n'
            '--- a/pkg/mod.py\n'
            '+++ b/pkg/mod.py\n'
            '@@ -1,3 +1,2 @@\n'
            ' head\n'
            '-surplus\n'
            ' tail\n'
        )

        result = run_script(
            self._script(), 'reconcile', '--plan-id', plan_id, '--diff-file', str(diff)
        )

        assert result.success, result.stderr
        assert 'verdict: clear' in result.stdout
        assert 'gates_merge: false' in result.stdout
        assert 'proves: removal_conflict_only' in result.stdout
        assert 'deletions_considered: 1' in result.stdout

    def test_an_unreached_store_is_refused_with_the_stores_own_code_and_detail(
        self, tmp_path, plan_context
    ):
        """A plan directory absent under the resolved root refuses, and aliases ``detail``.

        Two properties, and the second is the one a bare status check loses. The
        refusal must carry ``manage-findings``' own ``findings_store_unresolved``
        code rather than this module's ``load_failure`` — the two have different
        remedies. And it must carry ``detail``: every other error branch here
        publishes the store's provenance under that key, so re-emitting the raw
        payload (whose findings-side key is ``message``) would print the remedy
        under a name this emitter's readers do not look at.
        """
        from conftest import run_script

        plan_id = 'rc-cli-store-absent'
        assert not (plan_context.plans_dir / plan_id).exists(), 'fixture must not seed this plan'
        diff = tmp_path / 'pass.diff'
        diff.write_text(
            'diff --git a/pkg/mod.py b/pkg/mod.py\n'
            '--- a/pkg/mod.py\n'
            '+++ b/pkg/mod.py\n'
            '@@ -1,2 +1,1 @@\n'
            ' head\n'
            '-surplus\n'
        )

        result = run_script(
            self._script(), 'reconcile', '--plan-id', plan_id, '--diff-file', str(diff)
        )

        assert not result.success
        assert 'findings_store_unresolved' in result.stdout
        assert 'load_failure' not in result.stdout
        assert 'detail: ' in result.stdout
        assert 'verdict:' not in result.stdout
