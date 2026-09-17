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

def test_acknowledged_dispositions_commit_too():
    """`accepted` / `taken_into_account` absorbed the reviewer's point — also commitments.

    The run took a position on the line. A later pass deleting it reverses that
    position exactly as deleting a `fixed` line does.
    """
    for resolution in ('accepted', 'taken_into_account'):
        commitments = derive_commitments([_finding(resolution=resolution)])
        assert len(commitments) == 1, resolution
        assert commitments[0].basis == 'committed'


def test_a_suppressed_finding_releases_the_line():
    """`suppressed` is an explicit decision NOT to act — no commitment follows."""
    assert derive_commitments([_finding(resolution='suppressed')]) == ()


def test_an_unrecognised_resolution_fails_closed_to_a_commitment():
    """A resolution outside the closed vocabulary is UNKNOWN, never a release.

    A resolution value this seam does not recognise cannot be read as a release —
    that would let a vocabulary change silently widen what simplify may delete.
    """
    commitments = derive_commitments([_finding(resolution='some_new_state')])

    assert len(commitments) == 1
    assert commitments[0].basis == 'undecided'


def test_a_finding_with_no_file_path_anchors_nothing():
    """A review-body or issue comment is about the PR, not about a line.

    It carries no path, so it can bind no deletion. Excluded from the commitment
    set — but the exclusion is COUNTED by :func:`reconcile`, never invisible.
    """
    assert derive_commitments([_finding(file_path=None)]) == ()


def test_parse_deletions_reports_old_side_line_ranges():
    """Deleted lines are numbered on the OLD side, which is what a commitment anchors to."""
    deletions = parse_deletions(_DIFF)

    assert Deletion('pkg/mod.py', 10, 11) in deletions
    assert Deletion('pkg/mod.py', 31, 31) in deletions


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


def test_a_deletion_spanning_a_committed_line_conflicts():
    """A range that CONTAINS the committed line conflicts, not only one that starts on it."""
    commitments = derive_commitments([_finding(line=12)])
    deletions = (Deletion('pkg/mod.py', 5, 20),)

    assert reconcile(deletions, commitments)['verdict'] == 'conflict'


def test_a_pending_finding_blocks_the_deletion_of_its_line():
    """The fail-closed disposition reaches the verdict, not just the commitment set."""
    commitments = derive_commitments([_finding(resolution='pending', line=10)])
    deletions = (Deletion('pkg/mod.py', 10, 10),)

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'conflict'
    assert result['conflicts'][0]['basis'] == 'undecided'


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


def test_the_envelope_states_that_it_reports_rather_than_blocks():
    """The seam surfaces a conflict; it never decides the merge.

    Stated in the payload so a consumer cannot read a conflict as a merge verdict
    without ignoring a field that says otherwise — the same discipline
    `review_completeness deficit` uses for `gates_merge: false`.
    """
    result = reconcile((), ())

    assert result['proves'] == 'removal_conflict_only'
    assert result['gates_merge'] is False
