#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared plan-footprint resolution for the retrospective / audit consumers.

One resolution chain, so the recall check (``check-artifact-consistency``) and the
mis-prune check (``check-routing-decisions``) grade against the **same** footprint —
the D4 "one footprint resolution, two consumers" contract. Both call the whole-chain
:func:`resolve_footprint`. ``analyze-logs`` reuses the per-tier helpers here for its
own scope-deviation resolver, which keeps a **different** diff-failure policy (fall
through to the legacy key rather than reporting unresolvable) and therefore composes
the helpers itself rather than calling the whole-chain function.

Resolution tiers, in order:

1. **Live diff** — a live plan whose worktree the ONE resolver
   (:func:`_references_core.resolve_live_worktree`) resolves to a directory on disk.
   A ``CalledProcessError`` here reports UNRESOLVABLE rather than falling through: the
   worktree resolved but the diff failed, so a lower tier would answer a different
   question while presenting as the same measurement.
2. **Realized-footprint capture** — ``references.realized_footprint``, persisted by
   ``default:branch-cleanup`` (via ``manage-references capture-footprint``) while the
   worktree still existed and the diff was still accurate. This is the primary tier
   for an ARCHIVED plan and the set the resolver **prefers** over any re-derivation:
   it is captured-while-true, not re-derived from a substrate that has since changed.
3. **Merge-commit** — ``references.merge_commit_sha`` resolved as
   ``git -C {plan_dir} diff --name-only {sha}^1 {sha}``. The first-parent range names
   the changes the landing commit introduced, which is exact for BOTH a squash landing
   (its single parent is the base) and a true merge commit (its first parent is the
   base branch). It is **not** a ``base..HEAD`` range and carries no sibling
   contamination — a landing commit names its own first parent. It resolves only
   *post*-merge, so it sits BELOW the deterministic capture as a fallback: it cannot
   serve a consumer running before the merge.
4. **PR-landing** — ``references.pr_number`` resolved through the CI abstraction
   (``ci pr view --pr-number N``) to that PR's own ``merge_commit_sha``, then diffed
   by the SAME first-parent range tier 3 uses. It sits strictly BELOW the merge-commit
   tier, so a recorded SHA always keeps precedence and this tier can only ever turn an
   unresolvable answer into a resolved one. It exists because ``default:branch-cleanup``
   records ``merge_commit_sha`` only on the synchronous merge path: on the async
   merge-queue / squash path that key — and ``realized_footprint`` with it — is never
   written, so tiers 2 and 3 fail together and the landing is resolvable only from the
   PR number, which survives the head-branch deletion the queue performs.
5. **Legacy key** — ``references.modified_files`` (a SHIM for archived plans created
   before the change-ledger was removed).
6. **Unresolvable** — :data:`FOOTPRINT_UNRESOLVED`. Key absent and key present-but-empty
   are different answers and are reported differently: an empty list is a resolved,
   genuinely-empty footprint, never the unresolvable sentinel.

Tiers 1-5 are the RESOLVING tiers, named in order by :data:`RESOLVING_TIERS`; entry 6 is
the sentinel, not a tier. The enumeration above and the tiers :func:`resolve_footprint`
actually consults are asserted equal by test — a docstring promising a tier the body does
not wire is the doc-vs-body divergence that hides a missing guard.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, TypeGuard

from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
    resolve_live_worktree,
)
from file_ops import get_executor_path
from toon_parser import parse_toon

#: Stated sentinel for a footprint that could NOT be resolved at all. Deliberately
#: distinct from ``set()`` (the footprint resolved and the plan touched no files).
#: Collapsing the two is what let an exact footprint score a confident "Recall 0%"
#: after branch-cleanup deleted the worktree the resolver measures.
FOOTPRINT_UNRESOLVED = None

#: The RESOLVING tiers :func:`resolve_footprint` consults, in precedence order. The
#: module docstring enumerates these same five and then the unresolvable sentinel,
#: which is NOT a member here because it resolves nothing.
#:
#: Exposed as data — the same discipline :data:`ci_base.LANDING_STATES` follows — so a
#: consumer or a test asserts the chain's population against the chain's OWN declaration
#: rather than a hand-copied list that drifts the moment a tier is inserted.
RESOLVING_TIERS: tuple[str, ...] = (
    'live_diff',
    'realized_capture',
    'merge_commit',
    'pr_landing',
    'legacy_key',
)

#: Executor notation for the CI abstraction the PR-landing tier reads through. ADR-018:
#: the provider is reached via the abstraction, never by invoking ``gh`` directly.
_CI_NOTATION = 'plan-marshall:tools-integration-ci:ci'

#: Seconds allowed for the one ``ci pr view`` round-trip the PR-landing tier makes.
_PR_VIEW_TIMEOUT_SECONDS = 120

# ---------------------------------------------------------------------------
# The PR-landing SHA read — THREE inputs, THREE outcomes
# ---------------------------------------------------------------------------
#
# The landing SHA comes from a fallible provider call, so "did this PR report a
# landing commit?" has three answers, not two. Collapsing the third onto the second
# is the recurring shape where a fallible read is squeezed into a boolean — here it
# would make a provider outage indistinguishable from an open PR, and the caller
# would attribute a transport failure to the PR's own state.

#: The provider reported this PR merged AND carried a usable landing SHA.
PR_SHA_PRESENT = 'present'

#: The provider ANSWERED, and the answer is that there is no landing SHA — the PR is
#: not merged, or it is merged and the provider reported no merge commit. A read
#: result, not a failure.
PR_SHA_REPORTED_ABSENT = 'reported_absent'

#: The provider could NOT be read, or its answer could not be attributed to THIS PR.
#: Nothing is known about the landing; explicitly distinct from ``reported_absent``.
PR_SHA_UNREADABLE = 'unreadable'

#: The read's declared outcome population, in the order the reader tries to establish
#: them. Consumers and tests derive from this rather than restating the members.
PR_SHA_READ_OUTCOMES: tuple[str, ...] = (
    PR_SHA_PRESENT,
    PR_SHA_REPORTED_ABSENT,
    PR_SHA_UNREADABLE,
)


def resolve_diff_file_path(diff_file: str, plan_dir: Path) -> Path:
    """Resolve an explicit ``--diff-file`` argument to an existing file, or raise.

    An absolute path is used verbatim. A RELATIVE path is resolved against the
    plan directory first and the process cwd second, and the first candidate that
    exists wins. Plan-relative comes first because that is the form the capture
    pattern documents (``--diff-file work/footprint.txt``, where ``work/`` is a
    plan-directory subdirectory) and the form the sibling ``collect-fragments add
    --fragment-file`` flag has always accepted in the same workflow.

    **A supplied-but-unresolvable path raises.** It is never reported as an absent
    one. The two were previously indistinguishable: an unresolvable ``--diff-file``
    returned the same empty list as no ``--diff-file`` at all, so the documented
    plan-relative invocation degraded to a ``skip`` reading *"no realized
    footprint"* while the identical file passed as an absolute path found a real
    violation. A could-not-look must not carry the same token as a
    nothing-to-look-at, least of all when that token reads benign in every
    downstream summary.

    Args:
        diff_file: The ``--diff-file`` argument as supplied.
        plan_dir: The resolved plan directory a relative argument is resolved against.

    Returns:
        The existing file the argument names.

    Raises:
        ValueError: When no candidate exists, naming every candidate tried.
    """
    if not diff_file.strip():
        # An empty or whitespace argument is SUPPLIED input that names nothing.
        # Rejected explicitly, because `Path('')` is `.` and every relative
        # candidate would then resolve to an existing DIRECTORY — failing later
        # with a confusing "is a directory" read error instead of naming the
        # actual defect, and only by luck rather than by rule.
        raise ValueError(
            f'Diff file does not exist: {diff_file!r} — the argument is empty and names no path'
        )
    raw = Path(diff_file)
    if raw.is_absolute():
        if raw.exists():
            return raw
        raise ValueError(f'Diff file does not exist: {diff_file}')
    candidates = [plan_dir / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    tried = ', '.join(str(c) for c in candidates)
    raise ValueError(
        f'Diff file does not exist: {diff_file} — a relative --diff-file is resolved '
        f'against the plan directory first and the cwd second; tried: {tried}'
    )


def footprint_resolved(footprint: set[str] | None) -> TypeGuard[set[str]]:
    """The ONE named predicate callers use to read a footprint's resolution state.

    ``not footprint`` is NOT equivalent: it is also true for a resolved-but-empty
    footprint, which is a measured result and must still yield a measured verdict.
    """
    return footprint is not FOOTPRINT_UNRESOLVED


def load_references_dict(plan_dir: Path) -> dict[str, Any]:
    """Read ``references.json`` from ``plan_dir``; return ``{}`` on any error."""
    refs_path = plan_dir / 'references.json'
    if not refs_path.exists():
        return {}
    try:
        data = json.loads(refs_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_path_set(value: Any) -> set[str] | None:
    """Coerce a references path-list value to a set, or None when the key is unusable.

    A missing key (``None``) is ``None``; a bare string is a one-element list; a list
    is the set of its non-empty stringified entries (possibly empty — a resolved,
    genuinely-empty footprint); anything else is ``None`` (unusable → next tier).
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return None
    return {str(p).strip() for p in value if p}


def read_captured_footprint(refs: dict[str, Any]) -> set[str] | None:
    """Tier 2: ``references.realized_footprint`` (the capture-while-true side effect)."""
    return _coerce_path_set(refs.get('realized_footprint'))


def read_legacy_footprint(refs: dict[str, Any]) -> set[str] | None:
    """Tier 4: the legacy ``references.modified_files`` key."""
    # SHIM(B): archived plans' references.modified_files key, written before the change-ledger was removed.
    # shim-owner: plan-retrospective
    # shim-floor: the change-ledger removal that stopped persisting references.modified_files; the current writer no longer emits the key (predates this shallow clone's history root dcd3c00 / #1105, so not PR-pinnable here).
    # shim-remove-when: no archived plan predating the ledger removal is retained (i.e. such archives are purged/aged out).
    return _coerce_path_set(refs.get('modified_files'))


def resolve_merge_commit_footprint(plan_dir: Path, refs: dict[str, Any]) -> set[str] | None:
    """Tier 3: the realized path set of the recorded landing commit, or ``None``.

    Uses ``git -C {plan_dir} diff --name-only {sha}^1 {sha}``. ``plan_dir`` is inside
    the repository (``.plan/archived-plans/…`` sits under the repo root even though
    it is git-ignored), so ``git -C`` resolves the enclosing repo and the landed
    commit in its history.

    ⚠ The ignored thing is that sub-path, not ``.plan/`` as a whole: a number of
    files under ``.plan/`` ARE tracked (``marshal.json``, every
    ``project-architecture/**/enriched.json``), which is why ``script-shared``'s
    ``_plan_state_exemption`` exists. The conclusion here is unaffected — an
    ignored path still resolves its enclosing repo — but the blanket form of the
    claim is false and must not be restated.

    Any git failure — the SHA is absent (a shallow clone that never fetched it),
    ``plan_dir`` is not inside a repository, or a non-zero exit — returns ``None`` so
    the caller falls through to the legacy tier rather than fabricating a set. The SHA
    itself is recorded by ``default:branch-cleanup`` only on the synchronous merge
    path; on the async merge-queue path it is absent and tier 2 is the resolution.
    """
    sha = refs.get('merge_commit_sha')
    if not isinstance(sha, str) or not sha.strip():
        return None
    return diff_landing_commit(plan_dir, sha.strip())


def diff_landing_commit(plan_dir: Path, sha: str) -> set[str] | None:
    """Return the path set a landing commit introduced, or ``None`` when git failed.

    ``git -C {plan_dir} diff --name-only {sha}^1 {sha}`` — the first-parent range, exact
    for BOTH a squash landing (single parent is the base) and a true merge commit (first
    parent is the base branch). Shared by the merge-commit tier
    (:func:`resolve_merge_commit_footprint`) and the PR-landing tier
    (:func:`resolve_pr_landing_footprint`), which differ ONLY in where the SHA came from:
    one reads it from ``references``, the other from the PR. Duplicating the range here
    would let the two tiers drift into answering subtly different questions while
    presenting as the same measurement.

    Any git failure — an unresolvable SHA (a shallow clone that never fetched it),
    ``plan_dir`` outside a repository, or a non-zero exit — returns ``None`` so the
    caller falls through rather than fabricating a set.
    """
    try:
        proc = subprocess.run(
            ['git', '-C', str(plan_dir), 'diff', '--name-only', f'{sha}^1', sha],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def coerce_pr_number(value: Any) -> int | None:
    """Coerce a ``references.pr_number`` value to a positive int, or ``None``.

    Accepts an int or a digit string, because the key is written by a CLI-shaped
    producer whose own ``pr_number`` is parsed out of a URL. Rejects everything else —
    including the literal ``'unknown'`` that ``pr create`` emits when it could not parse
    the number out of the returned URL. That sentinel is precisely the value that must
    NOT reach the provider: querying it would produce a provider error, which is an
    unreadable outcome, when the truth is simply that no usable PR number was recorded.
    """
    if isinstance(value, bool):
        # bool is an int subclass; True would otherwise coerce to PR #1.
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.isdigit():
            number = int(candidate)
            return number if number > 0 else None
    return None


def read_pr_landing_sha(pr_number: int, plan_dir: Path | None = None) -> tuple[str, str | None]:
    """Read THIS PR's landing SHA through the CI abstraction. Returns ``(outcome, sha)``.

    ``outcome`` is one of :data:`PR_SHA_READ_OUTCOMES` and ``sha`` is non-``None`` only
    for :data:`PR_SHA_PRESENT`. The three outcomes are kept distinct because the read is
    fallible: a provider outage must never present as "this PR reported no landing".

    **Corroboration is against THIS PR, never a branch-level fact.** The SHA is accepted
    only from a payload that (a) came back ``status: success``, (b) reports the SAME
    ``pr_number`` that was asked for, and (c) reports that PR's own ``state`` as merged.
    A payload naming a different PR is :data:`PR_SHA_UNREADABLE` rather than
    ``reported_absent`` — the provider answered, but not about the PR in question, so
    nothing is known about this one.

    The provider is reached through the executor's ``ci`` abstraction (ADR-018), never by
    invoking ``gh``/``glab`` directly, so the tier works on every configured provider and
    inherits the abstraction's auth handling.
    """
    try:
        executor = get_executor_path()
    except Exception:
        # The executor could not be located at all — nothing was asked of the provider,
        # so nothing is known. Never 'reported_absent'.
        return PR_SHA_UNREADABLE, None

    cmd = [
        sys.executable,
        str(executor),
        _CI_NOTATION,
        'pr',
        'view',
        '--pr-number',
        str(pr_number),
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PR_VIEW_TIMEOUT_SECONDS,
            cwd=str(plan_dir) if plan_dir is not None else None,
        )
    except (OSError, subprocess.SubprocessError):
        return PR_SHA_UNREADABLE, None

    stdout = completed.stdout or ''
    if not stdout.strip():
        return PR_SHA_UNREADABLE, None
    try:
        payload = parse_toon(stdout)
    except Exception:
        return PR_SHA_UNREADABLE, None
    if not isinstance(payload, dict) or payload.get('status') != 'success':
        return PR_SHA_UNREADABLE, None

    # (b) The payload must be about the PR we asked about.
    if coerce_pr_number(payload.get('pr_number')) != pr_number:
        return PR_SHA_UNREADABLE, None

    # (c) That PR's OWN merged state. A non-merged PR is a READ answer — there is no
    # landing commit yet — so it is reported_absent, not unreadable.
    if str(payload.get('state') or '').strip().lower() != 'merged':
        return PR_SHA_REPORTED_ABSENT, None

    sha = payload.get('merge_commit_sha')
    if not isinstance(sha, str) or not sha.strip():
        # Merged, but the provider reported no merge commit (or reported it absent).
        # The provider ANSWERED — this is an absence it stated, not one we inferred.
        return PR_SHA_REPORTED_ABSENT, None
    return PR_SHA_PRESENT, sha.strip()


def resolve_pr_landing_footprint(plan_dir: Path, refs: dict[str, Any]) -> set[str] | None:
    """Tier 4: the landing path set resolved from ``references.pr_number``, or ``None``.

    The fallback for a capture that never happened. On the async merge-queue / squash
    path ``default:branch-cleanup`` writes neither ``realized_footprint`` (tier 2) nor
    ``merge_commit_sha`` (tier 3), so both fail together and the chain arrives here —
    this tier is not a redundant fourth answer to a question already answered, it is the
    only tier that can resolve that landing at all.

    Ordered strictly BELOW tier 3 by :func:`resolve_footprint`, so a recorded
    ``merge_commit_sha`` always decides the answer and this tier can only ever convert an
    unresolvable result into a resolved one — it never changes an answer an earlier tier
    already gave.

    EVERY unresolvable branch returns ``None`` so the chain falls through: no
    ``pr_number`` recorded, an unusable one, the provider unreadable, the PR not merged,
    no SHA reported, or a git failure diffing the SHA. It never returns an empty set,
    because an empty set is a resolved-and-genuinely-empty footprint.
    """
    pr_number = coerce_pr_number(refs.get('pr_number'))
    if pr_number is None:
        # No usable PR number recorded — the tier has no key to resolve from, and the
        # provider is deliberately NOT called. This is the branch every plan predating
        # the create-pr write takes, and it must cost nothing.
        return None

    outcome, sha = read_pr_landing_sha(pr_number, plan_dir)
    if outcome != PR_SHA_PRESENT or not sha:
        return None
    return diff_landing_commit(plan_dir, sha)


def resolve_footprint(plan_dir: Path, plan_id: str | None = None) -> set[str] | None:
    """The whole-chain resolver shared by the recall and mis-prune consumers.

    Archived mode passes ``plan_id=None`` and therefore skips tier 1 (an archived
    plan's recorded worktree names a directory finalize already removed). Returns a
    set when the footprint resolved (possibly empty), or :data:`FOOTPRINT_UNRESOLVED`
    when no tier answered. Read the distinction through :func:`footprint_resolved`,
    never by testing emptiness.
    """
    refs = load_references_dict(plan_dir)

    worktree = resolve_live_worktree(plan_id)
    if worktree is not None:
        base_ref = resolve_base_ref(None, refs)
        try:
            return compute_plan_branch_diff(worktree, base_ref)
        except subprocess.CalledProcessError:
            return FOOTPRINT_UNRESOLVED

    captured = read_captured_footprint(refs)
    if captured is not None:
        return captured

    merge_set = resolve_merge_commit_footprint(plan_dir, refs)
    if merge_set is not None:
        return merge_set

    # Strictly BELOW the merge-commit tier: a recorded merge_commit_sha keeps
    # precedence, so this tier can only convert an unresolvable answer into a
    # resolved one.
    pr_landing_set = resolve_pr_landing_footprint(plan_dir, refs)
    if pr_landing_set is not None:
        return pr_landing_set

    legacy = read_legacy_footprint(refs)
    if legacy is not None:
        return legacy

    return FOOTPRINT_UNRESOLVED
