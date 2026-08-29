#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Same-run reconciliation between a review commitment and a later removal.

Pure, deterministic seam backing the "Reconcile against the run's review
commitments" section of
``phase-6-finalize/standards/finalize-step-simplify.md``.

**The gap it closes.** ``automatic-review`` (``order: 30``) and
``finalize-step-simplify`` (``order: 8``) both run inside one finalize pass, and
simplify declares ``head_dependent: true`` — so a loop-back fix commit answering a
review comment advances HEAD and **re-fires the simplification sweep over the very
lines that fix produced**. Simplify's brief is to delete surplus structure, and a
guard added because a reviewer asked for it looks exactly like surplus structure to
a pass that never saw the review. Nothing stopped that deletion, and nothing
recorded it: the dispatcher's commit instrumentation committed the edit and the
push barrier shipped it, so a review decision was reversed inside the same run that
made it, silently.

**What this seam does, and does not.** It derives the run's line-level commitments
from the plan's ``pr-comment`` findings, parses the deletions the simplify pass
actually performed out of its own diff, and reports where the two intersect. It
never edits, never reverts, and never gates the merge — the envelope says so in as
many words (``proves: removal_conflict_only``, ``gates_merge: false``). Surfacing
is the whole deliverable: the contract is that a committed line either survives the
pass **or the removal is visible as a conflict**, never that a removal is
impossible.

Fail-closed classification discipline
-------------------------------------
This module applies rule (b) "fail closed on undetermined / empty state" from
``ref-code-quality/standards/error-handling.md``. Two undetermined states arise,
and reading either as a release would be absence laundered into a negative:

1. **An untriaged (``pending``) finding.** Nobody has yet decided whether the line
   may go. A pass that deletes it has pre-empted the triage that was going to
   decide, so ``pending`` binds the line exactly as a decided commitment does — it
   is merely recorded with ``basis: undecided`` so the two are distinguishable.
   Any resolution outside the closed vocabulary resolves the same way, so a future
   vocabulary change cannot silently widen what simplify may delete.
2. **A commitment with no line anchor.** ``github_pr`` files ``line: None`` for
   review-body comments — which is where the review bots put their *consolidated*
   findings. Narrowing such a commitment to "no line, therefore no conflict" would
   make the highest-value review comments bind nothing at all, so an anchor-less
   commitment binds its whole FILE.

A finding with no ``file_path`` binds nothing: it is a comment about the pull
request rather than about a line. That exclusion is legitimate, so it is
**counted** into ``unanchored_commitments`` rather than silently shrinking the
population the verdict was computed over.

Line-number basis, and its known imprecision
--------------------------------------------
Deletions are reported in the diff's **old-side** numbering — the tree as it stood
immediately before the simplify pass. A finding's stored ``line`` is GitHub's line
at the commit the reviewer reviewed (``github_pr`` stores it verbatim at FIND time).

**Those two coordinates are not guaranteed to be the same.** ``fetch_findings``
pre-filter 5 SKIPS an already-stored ``(bot_kind, comment_id)`` rather than
re-stamping it, so an existing finding's ``line`` is never re-anchored to a later
HEAD. D1's own scenario — review comment, then a loop-back fix commit, then simplify
re-fires — is exactly a case where the fix commit shifts the file between the two.
A drift of a few lines can therefore produce a false positive (a conflict reported
against an innocent deletion) or a false negative (a real conflict missed).

That imprecision is **stated rather than hidden**, and it is tolerable here only
because of what the seam does with a hit: it REPORTS. A false positive costs a
reverted simplification and a finding a human can overturn; it never blocks a merge.
Tightening it would mean re-anchoring stored findings on each FIND, which is a
producer-side change to ``github_pr`` and is deliberately not made here. The
file-wide fail-closed rule above absorbs part of the risk in the safe direction.

Usage:
    review_commitments.py reconcile --plan-id <id> --diff-file <path>
    review_commitments.py --help

The ``--diff-file`` argument is a path to a unified diff of the simplify pass's own
edits (``git diff`` over the worktree before the dispatcher commits them). It is
read from a file rather than stdin so the invocation stays a single Bash call with
no shell plumbing.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from toon_parser import serialize_toon

#: Resolutions in which the run took a POSITION on the line: the reviewer's point
#: was acted on (``fixed``) or absorbed without a code change (``accepted`` /
#: ``taken_into_account``). Deleting such a line reverses a decision the run made.
COMMITTED_RESOLUTIONS = frozenset({'fixed', 'accepted', 'taken_into_account'})

#: Resolutions that RELEASE the line: the reviewer was wrong (``rejected``) or the
#: run explicitly decided not to act (``suppressed``). Nothing is owed to the line,
#: so a later pass may delete it freely. Kept disjoint from
#: :data:`COMMITTED_RESOLUTIONS` so no resolution is classified twice.
RELEASED_RESOLUTIONS = frozenset({'rejected', 'suppressed'})

#: The basis on which a commitment binds — reported per conflict so a reader can
#: tell a decided commitment from a fail-closed one and triage them differently.
BASIS_COMMITTED = 'committed'
BASIS_UNDECIDED = 'undecided'

VERDICT_CLEAR = 'clear'
VERDICT_CONFLICT = 'conflict'


@dataclass(frozen=True)
class Commitment:
    """One line (or one whole file) the review process bound during this run.

    Attributes:
        path: Repo-relative path the commitment applies to.
        line: The committed line in old-side numbering, or ``None`` when the
            finding carried no anchor — in which case the commitment is file-wide
            (see the module docstring's fail-closed rule 2).
        finding_id: The finding's ``hash_id``, so a reported conflict names the
            review comment it reverses rather than merely a coordinate.
        resolution: The finding's resolution verbatim, so the reader sees the raw
            disposition alongside the derived basis.
        basis: :data:`BASIS_COMMITTED` (a decided disposition) or
            :data:`BASIS_UNDECIDED` (fail-closed: the disposition is unknown).
    """

    path: str
    line: int | None
    finding_id: str
    resolution: str
    basis: str


@dataclass(frozen=True)
class Deletion:
    """A contiguous run of lines the simplify pass removed, in old-side numbering."""

    path: str
    start_line: int
    end_line: int


def derive_commitments(findings: list[dict]) -> tuple[Commitment, ...]:
    """Derive the run's line-level commitments from its ``pr-comment`` findings.

    Args:
        findings: Finding records as stored by ``manage-findings`` — each may carry
            ``hash_id``, ``file_path``, ``line``, and ``resolution``.

    Returns:
        One :class:`Commitment` per finding that binds a path, in input order. A
        finding whose resolution is in :data:`RELEASED_RESOLUTIONS`, or that carries
        no ``file_path``, yields none; every other finding yields one, with an
        unrecognised or ``pending`` resolution resolving to
        :data:`BASIS_UNDECIDED` rather than to a release.
    """
    commitments: list[Commitment] = []
    for record in findings:
        resolution = str(record.get('resolution') or 'pending')
        if resolution in RELEASED_RESOLUTIONS:
            continue
        path = record.get('file_path')
        if not path:
            # A comment about the pull request, not about a line — it binds no
            # deletion. Counted by the caller via ``unanchored``, never silent.
            continue
        line = record.get('line')
        basis = BASIS_COMMITTED if resolution in COMMITTED_RESOLUTIONS else BASIS_UNDECIDED
        commitments.append(
            Commitment(
                path=str(path),
                line=int(line) if isinstance(line, int) and line > 0 else None,
                finding_id=str(record.get('hash_id') or ''),
                resolution=resolution,
                basis=basis,
            )
        )
    return tuple(commitments)


def count_unanchored(findings: list[dict]) -> int:
    """Count findings excluded from the commitment set for carrying no path.

    Reported alongside the verdict so the population it was computed over is
    visible: an exclusion nobody counts shrinks the denominator invisibly.
    """
    return sum(
        1
        for record in findings
        if str(record.get('resolution') or 'pending') not in RELEASED_RESOLUTIONS
        and not record.get('file_path')
    )


def _hunk_old_start(header: str) -> int | None:
    """Extract the old-side start line from an ``@@ -a,b +c,d @@`` hunk header."""
    parts = header.split(' ')
    for part in parts:
        if not part.startswith('-'):
            continue
        span = part[1:].split(',', 1)[0]
        try:
            return int(span)
        except ValueError:
            return None
    return None


def parse_deletions(diff_text: str) -> tuple[Deletion, ...]:
    """Parse a unified diff into the contiguous line ranges it removes.

    Line numbers are OLD-side — the tree as it stood before the diff — which is the
    coordinate system a finding's stored ``line`` is expressed in (see the module
    docstring). A pure addition removes nothing and yields no entry.

    Args:
        diff_text: A unified diff, as produced by ``git diff``.

    Returns:
        One :class:`Deletion` per contiguous run of removed lines, in file order.
        Contiguous lines collapse into a single range rather than one entry each,
        so a five-line removal is one reportable unit.
    """
    deletions: list[Deletion] = []
    path: str | None = None
    old_line = 0
    run_start: int | None = None
    run_end: int | None = None
    # Inside a hunk every line carries a prefix char, so a removed line whose own
    # content starts with '-- ' renders as '--- …' and is indistinguishable from a
    # file header by prefix alone. Position disambiguates it: headers precede the
    # first '@@' of a file, content follows it.
    in_hunk = False

    def flush() -> None:
        nonlocal run_start, run_end
        if path is not None and run_start is not None and run_end is not None:
            deletions.append(Deletion(path, run_start, run_end))
        run_start = None
        run_end = None

    for raw in diff_text.splitlines():
        if raw.startswith('diff --git '):
            flush()
            path = None
            in_hunk = False
            continue
        if not in_hunk and raw.startswith('--- '):
            flush()
            # The old-side header names the pre-image path, which is the one a
            # whole-file removal (`+++ /dev/null`) must still be attributed to.
            old_path = raw[4:].strip()
            path = None if old_path == '/dev/null' else _strip_diff_prefix(old_path)
            continue
        if not in_hunk and raw.startswith('+++ '):
            # The new-side header never changes the attribution: a rename is
            # reported against its old path, matching the old-side line numbers.
            continue
        if raw.startswith('@@'):
            flush()
            start = _hunk_old_start(raw)
            old_line = start if start is not None else 0
            in_hunk = True
            continue
        if raw.startswith('\\'):
            # The '\ No newline at end of file' marker annotates the PRECEDING
            # line; it is not itself a line of either side, so it must not advance
            # the old-side counter — doing so shifts every later coordinate in the
            # hunk. It also must not flush: a deletion run continues across it.
            continue
        if raw.startswith('-'):
            if run_start is None:
                run_start = old_line
            run_end = old_line
            old_line += 1
            continue
        flush()
        if raw.startswith('+'):
            # An added line consumes no old-side number.
            continue
        # A context line (leading space).
        old_line += 1

    flush()
    return tuple(deletions)


def _strip_diff_prefix(path: str) -> str:
    """Drop git's ``a/`` / ``b/`` diff prefix, leaving a repo-relative path."""
    for prefix in ('a/', 'b/'):
        if path.startswith(prefix):
            return path[len(prefix):]
    return path


def _binds(commitment: Commitment, deletion: Deletion) -> bool:
    """True when ``deletion`` removes what ``commitment`` bound.

    A commitment with no line anchor binds its whole file (fail-closed rule 2);
    an anchored one binds only a deletion whose range CONTAINS its line, so an
    unrelated removal elsewhere in a reviewed file stays clear. That negative
    direction is as load-bearing as the positive one: a check that flagged every
    deletion in every reviewed file would be disabled within a week.
    """
    if commitment.path != deletion.path:
        return False
    if commitment.line is None:
        return True
    return deletion.start_line <= commitment.line <= deletion.end_line


def reconcile(
    deletions: tuple[Deletion, ...] | list[Deletion],
    commitments: tuple[Commitment, ...] | list[Commitment],
    unanchored: int = 0,
) -> dict:
    """Report every deletion that removes a line the review process committed to.

    Args:
        deletions: The simplify pass's own removals, from :func:`parse_deletions`.
        commitments: The run's commitments, from :func:`derive_commitments`.
        unanchored: How many findings were excluded for carrying no path, from
            :func:`count_unanchored`. Published so the population is visible.

    Returns:
        A TOON-serialisable dict carrying ``verdict`` (:data:`VERDICT_CLEAR` or
        :data:`VERDICT_CONFLICT`), one ``conflicts[]`` record per intersecting
        ``(deletion, commitment)`` pair, and the populations the verdict was
        computed over. Every conflicting pair is reported: three occurrences of one
        deletion class are three rows, because a bundled verdict loses the
        per-instance record a reviewer needs to answer each one.

        The envelope also restates the ceiling in machine-readable form —
        ``proves: removal_conflict_only`` and ``gates_merge: false`` — so a consumer
        cannot read a conflict as a merge verdict without ignoring a field that says
        otherwise.
    """
    conflicts = [
        {
            'path': deletion.path,
            'start_line': deletion.start_line,
            'end_line': deletion.end_line,
            'finding_id': commitment.finding_id,
            'committed_line': commitment.line,
            'resolution': commitment.resolution,
            'basis': commitment.basis,
        }
        for deletion in deletions
        for commitment in commitments
        if _binds(commitment, deletion)
    ]
    return {
        'status': 'success',
        'verdict': VERDICT_CONFLICT if conflicts else VERDICT_CLEAR,
        # This seam reports; it does not decide. A conflict is a thing to answer,
        # not a merge block.
        'proves': 'removal_conflict_only',
        'gates_merge': False,
        'commitments_considered': len(commitments),
        'deletions_considered': len(deletions),
        'unanchored_commitments': unanchored,
        'conflicts': conflicts,
    }


def _read_pr_comment_findings(plan_id: str) -> dict:
    """Read the plan's ``pr-comment`` findings via the shared findings read path.

    Imported inside the function purely to keep the import graph honest about who
    needs it — the pure functions above do not. It buys no import-time isolation:
    ``toon_parser`` is already a module-level import needing the same executor
    ``PYTHONPATH``, so the module does not load without it either way.

    ``query_findings`` signals a read failure TWO ways, and this function returns
    the whole payload rather than its ``findings`` key so the caller can tell them
    apart:

    * it RAISES (``OSError`` / ``ValueError``) on an unreadable or malformed
      store, which :func:`cmd_reconcile` catches and renders as ``load_failure``;
    * it RETURNS a refusal (``status: error`` / ``error:
      findings_store_unresolved``) when the store was never reached at all — the
      plan directory is not under the root it resolved, which is the ordinary
      state of a plan whose directory has MOVED into its worktree. That payload
      carries NO ``findings`` key, so subscripting it here produced
      ``KeyError('findings')`` — an error naming a dict key instead of the absent
      plan directory that caused it.

    Returns the query payload verbatim; the caller checks ``status`` before
    reading ``findings``.
    """
    from _findings_core import query_findings

    result: dict = query_findings(plan_id, finding_type='pr-comment')
    return result


def cmd_reconcile(args: argparse.Namespace) -> int:
    """CLI wrapper — emits TOON. Non-zero exit on an unreadable input.

    A read failure is a structured error with NO ``verdict`` field, so the caller
    reads it as UNKNOWN rather than as a clear pass. A crashed reconciliation that
    rendered as ``clear`` would be the exact false-clean signal this seam exists to
    prevent.

    A store that was never REACHED is re-emitted with ``manage-findings``' own
    ``findings_store_unresolved`` code rather than folded into ``load_failure``:
    the two have different remedies (repair a corrupt store versus run the verb
    from the checkout that holds the plan), and only the store's own message names
    which checkout that is.
    """
    try:
        diff_text = Path(args.diff_file).read_text(encoding='utf-8')
    except OSError as exc:
        print(serialize_toon({'status': 'error', 'error': 'diff_unreadable', 'detail': str(exc)}))
        return 1
    try:
        read = _read_pr_comment_findings(args.plan_id)
    except (OSError, ValueError, KeyError) as exc:
        print(serialize_toon({'status': 'error', 'error': 'load_failure', 'detail': str(exc)}))
        return 1
    if read.get('status') != 'success':
        print(serialize_toon(read))
        return 1
    findings = read['findings']

    payload = reconcile(
        parse_deletions(diff_text),
        derive_commitments(findings),
        unanchored=count_unanchored(findings),
    )
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``reconcile`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Reconcile a simplify pass\'s deletions against the review commitments '
            'made earlier in the SAME finalize run. Reports conflicts; gates '
            'nothing.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    reconcile_parser = sub.add_parser(
        'reconcile',
        help='Report deletions that remove a line the review process committed to',
        allow_abbrev=False,
    )
    reconcile_parser.add_argument('--plan-id', required=True, help='Plan identifier.')
    reconcile_parser.add_argument(
        '--diff-file',
        required=True,
        dest='diff_file',
        help=(
            'Path to a unified diff of the simplify pass\'s own edits (git diff over '
            'the worktree, before the dispatcher commits them). Read from a file '
            'rather than stdin so the invocation stays one Bash call.'
        ),
    )
    reconcile_parser.set_defaults(func=cmd_reconcile)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
