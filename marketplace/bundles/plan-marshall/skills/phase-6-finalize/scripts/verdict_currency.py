#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Verdict-currency classifier for the phase-6-finalize re-entry check.

Answers ONE question for ONE head-dependent step: *does this HEAD advance
INVALIDATE the verdict the step already recorded, or merely supersede the SHA
it was anchored to?*

The dispatcher's re-entry check (``phase-6-finalize/SKILL.md`` § "Special case
— HEAD-dependent steps") historically re-fired a head-dependent step on a bare
SHA inequality: ``head_at_completion != live HEAD`` ⇒ RE-FIRE. That is safe and
maximally expensive — a finalize whose settle band and pre-merge rebase both
advance HEAD re-runs the same gates many times, mostly re-confirming identical
verdicts. This seam narrows the re-fire to advances that can actually change
the answer, without ever narrowing it to advances that can.

The rule, and why it is a purity argument rather than a heuristic
=================================================================

A step declares ``verdict_inputs`` — the fnmatch globs naming the tracked paths
whose CONTENT its verdict reads (see
``extension-api/standards/ext-point-finalize-step.md`` § "Implementor
Frontmatter"). When the tree difference between the recorded SHA and the live
HEAD touches **none** of those paths, the step's verdict is a function of
content that did not change, so a re-run would re-compute the same answer by
construction. That advance is ``preserved``. Any other outcome is
``invalidated``.

The comparison is a **tree diff** (``git diff --name-only {recorded} {live}``),
not a walk of the commits in between, which makes it correct under all three
supersession mechanisms the dispatcher must handle — a loop-back commit, a
force-push, and a rebase — because none of them changes what the two trees
actually contain. It is also strictly narrower than a commit walk: a change and
its revert cancel out, and a rebase that folds in upstream commits touching
nothing in the surface reports no difference on that surface.

Fail-closed: every uncertainty is ``invalidated``
=================================================

The plan this seam implements states the safety direction explicitly — *fail
TOWARD re-running when the classification is uncertain; an unnecessary re-run
costs tokens, a skipped necessary one costs correctness.* That direction is
structural here rather than advisory: ``preserved`` is returned on exactly TWO
paths, each of which PROVES the tree the verdict was computed against is still in
force:

1. ``REASON_HEAD_UNCHANGED`` — the two SHAs are equal, so the trees are
   byte-identical and no verdict about a tree can be stale against that same tree.
   This path is decided FIRST, before any resolution: it needs no declaration, no
   head-dependence fact and no discovery call, and consults none of them, so it
   stays correct even when they cannot be resolved at all.
2. ``REASON_DISJOINT`` — reached only past the resolution gate (the step doc
   resolved AND the step is head-dependent): a non-empty declaration whose globs
   match no path in the tree difference.

EVERY other path — an absent declaration on a genuinely-advanced HEAD, an
unresolvable step doc, unavailable discovery machinery, an unreadable SHA, a git
failure — returns ``invalidated`` with a ``reason`` naming the uncertainty. A step
that declares nothing keeps the pre-existing always-re-fire behaviour on every
real advance, so adoption is opt-in per step and silence is never read as
permission to skip.

Return shape (CLI emits this as TOON; programmatic callers consume
:func:`classify_advance` directly)::

    status: success
    step: <canonical step key>
    verdict: preserved | invalidated
    reason: <machine token, see REASON_* below>
    recorded_head: <sha echo>
    live_head: <sha echo>
    verdict_inputs[N]: [<declared globs>]
    changed_paths[M]: [<tree-diff paths>]
    matched_paths[K]: [<changed paths that matched a declared glob>]
    detail: <one-line human phrasing of the reason>

``matched_paths`` is populated only on ``verdict_inputs_matched`` — it names the
evidence for the re-fire, so the decision is substantiated rather than asserted.

Glob convention
===============

``verdict_inputs`` globs are matched with :func:`fnmatch.fnmatch` against the
full repo-relative path, which is the SAME convention ``build.map`` routes and
``derive_gate_bundles`` already use: single-``*`` globs, never recursive ``**``,
because ``fnmatch``'s ``*`` spans ``/``. So ``marketplace/*`` covers every path
under ``marketplace/``, and ``*.py`` covers every Python file at any depth.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py \\
      plan-marshall:phase-6-finalize:verdict_currency classify \\
      --step pre-push-quality-gate --worktree-path PATH \\
      --head-at-completion SHA [--live-head SHA]

The executor injects ``PYTHONPATH`` for ``toon_parser`` and the extension-api /
script-shared helpers, so no in-script ``sys.path`` manipulation is required.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The ext-point whose implementors declare ``head_dependent`` / ``verdict_inputs``.
_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that declares the step's verdict-input surface.
VERDICT_INPUTS_KEY = 'verdict_inputs'

#: The frontmatter key that declares head-dependence.
HEAD_DEPENDENT_KEY = 'head_dependent'

#: The only verdict that lets the dispatcher skip a re-fire. Reachable past the
#: resolution gate on two paths — ``REASON_HEAD_UNCHANGED`` and
#: ``REASON_DISJOINT``; see the module docstring for why both are safe.
VERDICT_PRESERVED = 'preserved'

#: Every uncertain or genuinely-invalidating outcome.
VERDICT_INVALIDATED = 'invalidated'

# Reason tokens. Exactly one of these accompanies every verdict; only
# REASON_DISJOINT and REASON_HEAD_UNCHANGED can carry VERDICT_PRESERVED.
REASON_HEAD_UNCHANGED = 'head_unchanged'
REASON_DISJOINT = 'disjoint_from_verdict_inputs'
REASON_MATCHED = 'verdict_inputs_matched'
REASON_UNDECLARED = 'verdict_inputs_undeclared'
REASON_STEP_UNRESOLVED = 'step_doc_unresolved'
REASON_DISCOVERY_UNAVAILABLE = 'discovery_unavailable'
REASON_NOT_HEAD_DEPENDENT = 'step_not_head_dependent'
REASON_NO_RECORDED_HEAD = 'recorded_head_absent'
REASON_DIFF_UNAVAILABLE = 'tree_diff_unavailable'

#: Human phrasing per reason, used for the ``detail`` field and the dispatcher's
#: INFO decision line. Keyed by reason token so the two never drift.
_REASON_DETAIL: dict[str, str] = {
    REASON_HEAD_UNCHANGED: (
        'the recorded SHA equals the live HEAD, so the verdict is still anchored to this tree'
    ),
    REASON_DISJOINT: (
        'the tree difference between the recorded SHA and the live HEAD touches no declared '
        'verdict input, so a re-run would re-compute the same verdict from unchanged content'
    ),
    REASON_MATCHED: (
        'the tree difference touches at least one declared verdict input, so the recorded '
        'verdict may no longer hold'
    ),
    REASON_UNDECLARED: (
        'the step declares no verdict_inputs surface, so no advance can be proven '
        'non-invalidating — re-firing is the fail-closed answer'
    ),
    REASON_STEP_UNRESOLVED: (
        'the step matched no finalize-step implementor, so its verdict surface is unknown'
    ),
    REASON_DISCOVERY_UNAVAILABLE: (
        'the extension-discovery machinery could not run, so the declaration could not be read'
    ),
    REASON_NOT_HEAD_DEPENDENT: (
        'the step does not declare head_dependent: true, so this classifier is not its '
        're-entry authority'
    ),
    REASON_NO_RECORDED_HEAD: (
        'the record carries no head_at_completion, so there is no anchor to diff against'
    ),
    REASON_DIFF_UNAVAILABLE: (
        'the tree diff between the recorded SHA and the live HEAD could not be computed'
    ),
}


# ---------------------------------------------------------------------------
# Pure classification
# ---------------------------------------------------------------------------


def classify_advance(
    verdict_inputs: list[str],
    changed_paths: list[str],
) -> tuple[str, str, list[str]]:
    """Classify a HEAD advance against a step's declared verdict-input surface.

    Pure: no git, no filesystem, no discovery. The caller supplies the resolved
    declaration and the resolved tree difference; this function owns only the
    invalidating-or-not decision so it is testable without a live worktree.

    Args:
        verdict_inputs: The step's declared fnmatch globs. An empty list means
            the step declared nothing, which is NOT "matches nothing" — it is
            "surface unknown", and resolves to ``invalidated``.
        changed_paths: Repo-relative paths differing between the recorded SHA's
            tree and the live HEAD's tree.

    Returns:
        A ``(verdict, reason, matched_paths)`` tuple. ``matched_paths`` is
        non-empty only when the reason is :data:`REASON_MATCHED`, where it names
        the changed paths that substantiate the re-fire.
    """
    if not verdict_inputs:
        return VERDICT_INVALIDATED, REASON_UNDECLARED, []

    matched = [
        path
        for path in changed_paths
        if any(fnmatch.fnmatch(path, glob) for glob in verdict_inputs)
    ]
    if matched:
        return VERDICT_INVALIDATED, REASON_MATCHED, matched
    return VERDICT_PRESERVED, REASON_DISJOINT, []


def _payload(
    step: str,
    verdict: str,
    reason: str,
    recorded_head: str,
    live_head: str,
    verdict_inputs: list[str],
    changed_paths: list[str],
    matched_paths: list[str],
) -> dict[str, Any]:
    """Assemble the classifier's TOON payload with its reason detail attached."""
    return {
        'status': 'success',
        'step': step,
        'verdict': verdict,
        'reason': reason,
        'recorded_head': recorded_head,
        'live_head': live_head,
        'verdict_inputs': verdict_inputs,
        'changed_paths': changed_paths,
        'matched_paths': matched_paths,
        'detail': _REASON_DETAIL.get(reason, reason),
    }


# ---------------------------------------------------------------------------
# Resolution seams (split out so the orchestration body is testable)
# ---------------------------------------------------------------------------


def resolve_verdict_inputs(step: str) -> tuple[list[str], bool, str | None]:
    """Resolve one step's ``verdict_inputs`` and ``head_dependent`` declaration.

    Reuses the registry's OWN discovery path — ``find_implementors`` for the
    population and ``extension_discovery._read_frontmatter_fields`` for the
    facts — exactly as ``manage-status``'s head-dependence derivation does, so
    no second frontmatter parser exists to drift from it. Both sides of the step
    comparison run through ``canonicalize_step_key`` because discovery names a
    built-in step ``default:{name}`` while the dispatcher holds the bare key.

    Args:
        step: The canonical step key being re-entered.

    Returns:
        A ``(verdict_inputs, is_head_dependent, unresolved_reason)`` tuple.
        ``unresolved_reason`` is ``None`` when the lookup RESOLVED (even to an
        empty declaration) and a reason token otherwise.
    """
    try:
        import extension_discovery
        from extension_discovery import find_implementors

        from _step_key_canonical import canonicalize_step_key
    except ImportError:
        return [], False, REASON_DISCOVERY_UNAVAILABLE

    try:
        records = find_implementors(_FINALIZE_STEP_EXT_POINT)
    except Exception:  # noqa: BLE001 - any discovery failure is fail-closed, not fatal
        return [], False, REASON_DISCOVERY_UNAVAILABLE

    if not records:
        return [], False, REASON_DISCOVERY_UNAVAILABLE

    wanted = canonicalize_step_key(step)
    for record in records:
        if canonicalize_step_key(str(record.get('name', ''))) != wanted:
            continue
        # Guarded like the discovery call above: ``_read_frontmatter_fields``
        # imports its parsing primitives at call time, so an import failure there
        # would otherwise escape as a traceback and break the always-exit-0
        # contract this verb's callers branch on.
        try:
            fields = extension_discovery._read_frontmatter_fields(
                Path(str(record.get('path', ''))),
                (VERDICT_INPUTS_KEY, HEAD_DEPENDENT_KEY),
            )
        except Exception:  # noqa: BLE001 - an unreadable declaration is fail-closed, not fatal
            return [], False, REASON_DISCOVERY_UNAVAILABLE
        declared = fields.get(VERDICT_INPUTS_KEY)
        globs = [str(item).strip() for item in declared if str(item).strip()] if isinstance(declared, list) else []
        return globs, bool(fields.get(HEAD_DEPENDENT_KEY, False)), None

    return [], False, REASON_STEP_UNRESOLVED


def resolve_changed_paths(
    worktree_path: str,
    recorded_head: str,
    live_head: str,
) -> tuple[list[str], bool]:
    """Return the repo-relative tree difference between two commits.

    Uses ``git diff --name-only {recorded} {live}`` — a two-tree comparison, not
    a commit walk — so the answer is identical whether the SHAs are related by a
    fast-forward, a rebase, or a force-push, and so a change plus its revert
    cancels out instead of counting as a difference.

    Args:
        worktree_path: Directory to run git in (``git -C``).
        recorded_head: The SHA the verdict was computed against.
        live_head: The current worktree HEAD.

    Returns:
        A ``(paths, ok)`` tuple. ``ok`` is ``False`` on any git failure —
        including a SHA git can no longer resolve — and the caller MUST treat
        that as invalidating rather than as an empty difference.
    """
    try:
        completed = subprocess.run(
            [
                'git',
                '-C',
                worktree_path or '.',
                'diff',
                '--name-only',
                recorded_head,
                live_head,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return [], False

    if completed.returncode != 0:
        return [], False

    paths = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return paths, True


def resolve_live_head(worktree_path: str) -> str:
    """Return the worktree HEAD SHA, or an empty string on any failure."""
    try:
        completed = subprocess.run(
            ['git', '-C', worktree_path or '.', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ''
    if completed.returncode != 0:
        return ''
    return completed.stdout.strip()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def classify_step(
    step: str,
    worktree_path: str,
    recorded_head: str,
    live_head: str,
) -> dict[str, Any]:
    """Resolve the declaration and the tree diff, then classify the advance.

    Two returns below are ``preserved`` and both prove the recorded tree is still
    in force: the equal-SHA short-circuit — decided before ANY resolution, so it
    holds even when discovery cannot run — and :func:`classify_advance` reached
    with a resolved, non-empty declaration and a successfully-computed tree
    difference. Every other return is ``invalidated``, carrying the reason it
    could not prove currency.
    """
    if not recorded_head:
        return _payload(
            step, VERDICT_INVALIDATED, REASON_NO_RECORDED_HEAD,
            recorded_head, live_head, [], [], [],
        )

    if not live_head:
        live_head = resolve_live_head(worktree_path)
    if not live_head:
        return _payload(
            step, VERDICT_INVALIDATED, REASON_DIFF_UNAVAILABLE,
            recorded_head, live_head, [], [], [],
        )

    # Equal SHAs short-circuit BEFORE anything is resolved. Identical SHAs mean
    # byte-identical trees, and no verdict about a tree can be stale against that
    # same tree — so the answer needs no declaration, no head-dependence fact, and
    # no discovery call, and it stays correct even when those cannot be resolved
    # at all. Placing this after the resolution gate would answer ``invalidated``
    # for an unmoved HEAD whenever discovery hiccuped, contradicting both the
    # dispatcher's steady-state SKIP row and this module's promise that the path
    # "consults none".
    if recorded_head == live_head:
        return _payload(
            step, VERDICT_PRESERVED, REASON_HEAD_UNCHANGED,
            recorded_head, live_head, [], [], [],
        )

    globs, is_head_dependent, unresolved = resolve_verdict_inputs(step)
    if unresolved is not None:
        return _payload(
            step, VERDICT_INVALIDATED, unresolved,
            recorded_head, live_head, globs, [], [],
        )
    if not is_head_dependent:
        return _payload(
            step, VERDICT_INVALIDATED, REASON_NOT_HEAD_DEPENDENT,
            recorded_head, live_head, globs, [], [],
        )

    if not globs:
        return _payload(
            step, VERDICT_INVALIDATED, REASON_UNDECLARED,
            recorded_head, live_head, globs, [], [],
        )

    changed, ok = resolve_changed_paths(worktree_path, recorded_head, live_head)
    if not ok:
        return _payload(
            step, VERDICT_INVALIDATED, REASON_DIFF_UNAVAILABLE,
            recorded_head, live_head, globs, [], [],
        )

    verdict, reason, matched = classify_advance(globs, changed)
    return _payload(
        step, verdict, reason, recorded_head, live_head, globs, changed, matched,
    )


def cmd_classify(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`classify_step` — emits TOON, always returns 0.

    Exit code 0 on every classification path: an ``invalidated`` verdict is a
    normal answer, not an error, and the dispatcher branches on ``verdict``.
    """
    payload = classify_step(
        step=args.step,
        worktree_path=args.worktree_path,
        recorded_head=args.head_at_completion,
        live_head=args.live_head or '',
    )
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``classify`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Classify whether a HEAD advance invalidates a head-dependent '
            "finalize step's recorded verdict, by comparing the tree difference "
            "between the recorded SHA and the live HEAD against the step's "
            'declared verdict_inputs surface. Fails closed: every uncertainty '
            'returns verdict: invalidated.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    classify_parser = sub.add_parser(
        'classify',
        help="Classify one step's HEAD advance as preserved or invalidated",
        allow_abbrev=False,
    )
    classify_parser.add_argument(
        '--step',
        required=True,
        help='Canonical finalize step key being re-entered (e.g. pre-push-quality-gate).',
    )
    classify_parser.add_argument(
        '--head-at-completion',
        required=True,
        dest='head_at_completion',
        help='The SHA persisted on the step record — the tree the verdict was computed against.',
    )
    classify_parser.add_argument(
        '--worktree-path',
        default='.',
        dest='worktree_path',
        help='Worktree root the git calls run in (git -C). Defaults to the current directory.',
    )
    classify_parser.add_argument(
        '--live-head',
        default=None,
        dest='live_head',
        help='Current worktree HEAD. Resolved via git rev-parse HEAD when omitted.',
    )
    classify_parser.set_defaults(func=cmd_classify)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'VERDICT_INVALIDATED',
    'VERDICT_PRESERVED',
    'classify_advance',
    'classify_step',
    'resolve_changed_paths',
    'resolve_verdict_inputs',
]
