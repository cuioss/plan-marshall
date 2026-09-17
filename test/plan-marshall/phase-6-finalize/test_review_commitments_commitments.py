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


def test_a_fixed_finding_commits_to_its_line():
    """`fixed` means the review asked and the run changed the code — a commitment."""
    commitments = derive_commitments([_finding(resolution='fixed')])

    assert len(commitments) == 1
    assert commitments[0].path == 'pkg/mod.py'
    assert commitments[0].line == 10
    assert commitments[0].basis == 'committed'


def test_a_rejected_finding_releases_the_line():
    """`rejected` means the reviewer was wrong — nothing is owed to that line."""
    assert derive_commitments([_finding(resolution='rejected')]) == ()


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


def test_the_two_resolution_sets_are_disjoint():
    """Committed and released are disjoint, so no resolution is classified twice."""
    assert not (COMMITTED_RESOLUTIONS & RELEASED_RESOLUTIONS)


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


def test_parse_deletions_groups_contiguous_runs():
    """A contiguous run is one range, not one entry per line."""
    deletions = parse_deletions(_DIFF)

    assert len(deletions) == 2


def test_parse_deletions_does_not_mistake_the_file_header_for_a_deletion():
    """`--- a/path` starts with a dash but is a header, not a removed line."""
    deletions = parse_deletions(_DIFF)

    assert all(d.path == 'pkg/mod.py' for d in deletions)
    assert all(d.start_line > 0 for d in deletions)


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


def test_a_deletion_in_a_different_file_is_clear():
    """Commitments are path-scoped."""
    commitments = derive_commitments([_finding(file_path='pkg/mod.py', line=10)])
    deletions = (Deletion('pkg/other.py', 10, 10),)

    assert reconcile(deletions, commitments)['verdict'] == 'clear'


def test_a_file_wide_commitment_conflicts_with_any_deletion_in_that_file():
    """The anchor-less fail-closed case: unknown line means every line is in question."""
    commitments = derive_commitments([_finding(line=None)])
    deletions = (Deletion('pkg/mod.py', 900, 901),)

    result = reconcile(deletions, commitments)

    assert result['verdict'] == 'conflict'
    assert result['conflicts'][0]['committed_line'] is None


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

        result = run_script(self._script(), 'reconcile', '--plan-id', plan_id, '--diff-file', str(diff))

        assert result.success, result.stderr
        assert 'verdict: clear' in result.stdout
        assert 'gates_merge: false' in result.stdout
        assert 'proves: removal_conflict_only' in result.stdout
        assert 'deletions_considered: 1' in result.stdout

    def test_an_unreached_store_is_refused_with_the_stores_own_code_and_detail(self, tmp_path, plan_context):
        """A plan directory absent under the resolved root refuses, and aliases ``detail``.

        Two properties, and the second is the one a bare status check loses. The
        refusal must carry ``manage-findings``' own ``findings_store_unresolved``
        code rather than this module's ``load_failure`` — the two have different
        remedies. And it must carry ``detail``: every other error branch here
        publishes the store's provenance under that key, so re-emitting the raw
        payload (whose findings-side key is ``message``) would print the remedy
        under a name this emitter's readers do not look at.

        The ``detail`` assertion pins the PAYLOAD, not the key. A bare
        ``'detail: ' in stdout`` passes on an empty value, on a value copied from
        some other branch, and on any future refusal that happens to print the
        key — none of which delivers the provenance this case exists to protect.
        What makes the field worth publishing is that it names WHICH store went
        unreached, so that is what is asserted: the absent plan's own id and the
        never-reached phrasing, read off the ``detail`` line itself rather than
        from anywhere in stdout (``plan_id`` is echoed as its own field, so a
        whole-stdout substring test would pass with ``detail`` empty).
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

        result = run_script(self._script(), 'reconcile', '--plan-id', plan_id, '--diff-file', str(diff))

        assert not result.success
        assert 'findings_store_unresolved' in result.stdout
        assert 'load_failure' not in result.stdout
        assert 'verdict:' not in result.stdout

        detail_lines = [
            line.partition('detail:')[2].strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith('detail:')
        ]
        assert len(detail_lines) == 1, result.stdout
        detail = detail_lines[0]
        assert plan_id in detail, detail
        assert 'never reached' in detail, detail
