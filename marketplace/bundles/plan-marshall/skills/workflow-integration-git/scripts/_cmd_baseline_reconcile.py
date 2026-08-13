#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Mechanical baseline-reconciliation predicate for phase-2-refine Step 3d.

Fetches the upstream tip, walks the commits landed on
``origin/{base_branch}`` since the **merge-base of HEAD and
``origin/{base_branch}``**, and runs ``git merge-tree`` to detect
potential merge conflicts. This is a **non-mutating classifier on every
path**: it never moves the branch ref, never performs a real merge, and
never modifies the working tree. Each upstream commit and each conflicted
file is surfaced in the return TOON; with ``--emit`` an equivalent Q-Gate
finding is appended under ``--source qgate`` so the phase-2-refine
iterate-to-confidence loop consumes the result via the existing
finding-resolution path.

The anchor is the merge-base, **recomputed on every call from live refs** —
never a SHA captured at plan initialisation. A stored initialisation SHA
stops describing "commits I am behind by" the moment the branch's own
history advances past it, so ``{stored SHA}..origin/{base}`` over-reports
commits the branch already contains. The merge-base is the true divergence
point, so ``{merge-base}..origin/{base}`` is exactly the behind-set and
``{merge-base}..HEAD`` is exactly the plan's own in-flight changes.

The LLM-judgement step (decide which upstream commits warrant scope
adjustment) stays bundled in the existing phase-2-refine dispatch — this
script is the mechanical predicate only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from _findings_core import QGATE_PERSIST_OK, add_qgate_finding
from git_provider import run_git

_PHASE = '2-refine'
_QGATE_SOURCE = 'qgate'
_DEFAULT_BASE_BRANCH = 'main'


def _worktree_target(plan_id: str, override: str | None) -> tuple[str | None, str | None]:
    """Select the working tree this reconciliation runs against.

    An argument adapter over the single plan-context resolver, NOT a worktree
    re-deriver: it applies the ``--worktree-path`` override, delegates the
    actual resolution, and maps the outcome onto Step 3d's skip-reason
    vocabulary.

    Returns ``(path, skip_reason_or_None)``. The skip reason is
    populated when the plan declares ``use_worktree==false`` or when
    status.json is missing/unparseable — both are documented skip
    conditions in Step 3d's activation guard.

    Resolution routes through the single plan-context resolver rather than
    hand-reading ``status.metadata``. The skip-reason vocabulary is unchanged
    and is derived structurally, not by matching the resolver's error text:
    a failure to resolve the worktree PRESENCE is ``status_not_found``, while a
    plan that declares a worktree but resolves no path is
    ``worktree_path_missing``.
    """
    if override:
        return override, None

    try:
        from file_ops import WorktreeResolutionError, resolve_plan_context
    except ImportError:
        return None, 'status_module_unavailable'

    try:
        context = resolve_plan_context(plan_id, ensure=False)
        if not context.has_worktree:
            return None, 'main_checkout_flow'
    except WorktreeResolutionError:
        return None, 'status_not_found'

    try:
        worktree_path = context.worktree_path
    except WorktreeResolutionError:
        return None, 'worktree_path_missing'

    # An EMPTY persisted worktree_path never reaches this guard: the resolver
    # raises WorktreeResolutionError for use_worktree=true with an empty path,
    # and the except above already maps that case to 'worktree_path_missing'.
    # What stays reachable here is a NON-EMPTY path that is not a directory —
    # a worktree that was removed or relocated after the path was persisted —
    # which would otherwise be handed to ``git -C <stale-path>`` as a bogus
    # target.
    if not Path(worktree_path).is_dir():
        return None, 'worktree_path_not_a_directory'

    return worktree_path, None


def _resolve_base_branch(plan_id: str, override: str | None) -> tuple[str, str | None]:
    """Resolve the upstream base branch for the plan.

    Returns ``(branch, source)`` where source is ``'cli'`` /
    ``'plan_config'`` / ``'default'`` so the caller can record how the
    value was chosen. Falls back to ``main`` when neither override nor
    plan config provides a value.
    """
    if override:
        return override, 'cli'

    try:
        from _config_core import load_config
    except ImportError:
        return _DEFAULT_BASE_BRANCH, 'default'

    try:
        config = load_config()
    except (FileNotFoundError, ValueError):
        return _DEFAULT_BASE_BRANCH, 'default'

    plan_config = config.get('plan', {}) if isinstance(config, dict) else {}
    refine_section = plan_config.get('phase-2-refine', {}) if isinstance(plan_config, dict) else {}
    branch = refine_section.get('base_branch') if isinstance(refine_section, dict) else None
    # Acknowledge that `plan_id` is part of the public contract even when
    # the implementation reads the marshal.json default rather than a
    # per-plan override; downstream callers may extend this read path.
    _ = plan_id
    if isinstance(branch, str) and branch.strip():
        return branch.strip(), 'plan_config'
    return _DEFAULT_BASE_BRANCH, 'default'


def _resolve_head(worktree_path: str) -> tuple[str, bool]:
    """Return ``(head_sha, ok)`` for the worktree HEAD.

    Used both to compute the anchor and as the reference point for the
    non-mutation guard: HEAD is captured before the probe and re-read after
    it, and any change is a contract violation (this is a classifier that
    performs no writes).
    """
    rc, stdout, _ = run_git(['-C', worktree_path, 'rev-parse', 'HEAD'])
    if rc != 0 or not stdout.strip():
        return '', False
    return stdout.strip(), True


def _resolve_merge_base(worktree_path: str, base_branch: str) -> tuple[str, str]:
    """Return ``(sha, source)`` for the anchor: ``merge-base(HEAD, origin/{base})``.

    The anchor is **recomputed on every call from live refs**, never read from
    a stored status SHA. The merge-base is the true point at which this branch
    diverged from the base, so it is the only anchor for which
    ``{anchor}..origin/{base}`` is the set of commits the branch is *behind by*
    and ``{anchor}..HEAD`` is the set of the branch's *own* commits.

    A stored initialisation SHA cannot describe divergence: once the branch's
    history advances past it (including any merge of upstream into HEAD), that
    SHA is no longer an ancestor of the merged-in upstream commits, so the
    range re-reports them as "upstream" even though the branch already contains
    them. Caching the merge-base re-creates the same staleness with a shorter
    window, so it is computed fresh here on every call.

    Returns ``('', 'unresolved')`` when no merge-base exists (no common
    ancestor, or ``origin/{base}`` does not resolve) — the caller fails closed
    rather than classifying against a bogus anchor.
    """
    rc, stdout, _ = run_git(
        ['-C', worktree_path, 'merge-base', 'HEAD', f'origin/{base_branch}']
    )
    if rc != 0 or not stdout.strip():
        return '', 'unresolved'
    return stdout.strip(), 'merge_base'


def _has_remote(worktree_path: str) -> bool:
    rc, stdout, _ = run_git(['-C', worktree_path, 'remote'])
    return rc == 0 and bool(stdout.strip())


def _remote_branch_exists(worktree_path: str, branch: str) -> bool:
    """Return True when ``origin/{branch}`` resolves on the remote."""
    rc, stdout, _ = run_git(['-C', worktree_path, 'ls-remote', '--heads', 'origin', branch])
    return rc == 0 and bool(stdout.strip())


def _detect_remote_default_branch(worktree_path: str) -> str | None:
    """Detect the remote default branch.

    Preference order: ``git ls-remote --symref origin HEAD`` (parses
    ``ref: refs/heads/{name}``) → ``main`` if it exists on the remote → ``master``
    if it exists → None when nothing resolves.
    """
    rc, stdout, _ = run_git(['-C', worktree_path, 'ls-remote', '--symref', 'origin', 'HEAD'])
    if rc == 0:
        for line in stdout.splitlines():
            if line.startswith('ref:'):
                # Format: ``ref: refs/heads/{name}\tHEAD``
                rest = line[len('ref:'):].strip()
                ref = rest.split('\t', 1)[0].strip() if '\t' in rest else rest.split()[0]
                if ref.startswith('refs/heads/'):
                    return ref[len('refs/heads/'):]

    for fallback in ('main', 'master'):
        if _remote_branch_exists(worktree_path, fallback):
            return fallback
    return None


def _update_references_base_branch(plan_id: str, new_branch: str) -> bool:
    """Persist the new ``base_branch`` in ``references.json``.

    Returns True on a successful write, False when the references module is
    unavailable or the file cannot be loaded — caller decides whether to
    fail-loud or continue against the updated in-memory value.
    """
    try:
        from _references_core import read_references, write_references
    except ImportError:
        return False

    try:
        refs = read_references(plan_id)
    except FileNotFoundError:
        refs = {}

    if not isinstance(refs, dict):
        refs = {}
    refs['base_branch'] = new_branch
    try:
        write_references(plan_id, refs)
    except (FileNotFoundError, OSError):
        return False
    return True


def _maybe_auto_update_stale_base_branch(
    plan_id: str,
    worktree_path: str,
    base_branch: str,
) -> tuple[str, bool, str | None]:
    """Detect a stale ``base_branch`` and auto-update it to the remote default.

    Returns ``(resolved_branch, updated, original_branch_or_None)``:

    * ``resolved_branch`` — the branch the caller should proceed with. Equals
      ``base_branch`` when no update was needed.
    * ``updated`` — True when references.json was updated AND a new default was
      detected.
    * ``original_branch_or_None`` — the prior ``base_branch`` value when
      ``updated`` is True, ``None`` otherwise.
    """
    if _remote_branch_exists(worktree_path, base_branch):
        return base_branch, False, None

    detected = _detect_remote_default_branch(worktree_path)
    if detected is None or detected == base_branch:
        # Nothing to switch to — leave the value alone; downstream callers
        # produce the canonical fetch_failed / unresolvable error.
        return base_branch, False, None

    persisted = _update_references_base_branch(plan_id, detected)
    if persisted:
        try:
            from plan_logging import log_entry
        except ImportError:
            log_entry = None  # type: ignore[assignment]
        if log_entry is not None:
            log_entry(
                'decision',
                plan_id,
                'INFO',
                f'(plan-marshall:workflow-integration-git:baseline-reconcile) '
                f'Stale base_branch {base_branch} (no remote ref) auto-updated to {detected}',
            )

    return detected, persisted, base_branch


def _list_upstream_commits(
    worktree_path: str,
    merge_base_sha: str,
    base_branch: str,
) -> list[dict[str, Any]]:
    """Return ``[{sha, subject, files}]`` for upstream commits since ``merge_base_sha``.

    The range ``{merge_base_sha}..origin/{base_branch}`` is exactly the set of
    commits the branch is *behind by*, because ``merge_base_sha`` is the point
    at which the branch diverged from the base. Uses a single ``git log
    --name-only`` call so the subprocess cost is O(1) in the number of commits —
    long upstream divergence does not require N + 1 subprocesses. The output
    groups each commit's metadata line with its touched-file list separated by
    a blank line.
    """
    rc, stdout, _ = run_git(
        [
            '-C',
            worktree_path,
            'log',
            f'{merge_base_sha}..origin/{base_branch}',
            '--name-only',
            '--pretty=format:%H%x09%s',
        ]
    )
    if rc != 0 or not stdout:
        return []

    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in stdout.splitlines():
        if '\t' in line and not line.startswith(' '):
            # ``{sha}\t{subject}`` header for a new commit.
            sha, subject = line.split('\t', 1)
            if len(sha) >= 7 and all(ch in '0123456789abcdefABCDEF' for ch in sha):
                current = {'sha': sha, 'subject': subject, 'files': []}
                commits.append(current)
                continue
        if current is None:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        current['files'].append(stripped)
    return commits


def _detect_merge_conflicts(
    worktree_path: str,
    base_branch: str,
) -> tuple[list[str], str | None]:
    """Run ``git merge-tree`` and return ``(conflicted_files, error_or_None)``.

    Uses modern ``--write-tree --name-only`` syntax. Returns an empty
    list when the merge is clean (exit 0). Returns an error message
    (without a list of files) when the git invocation itself fails.
    """
    rc, stdout, stderr = run_git(
        [
            '-C',
            worktree_path,
            'merge-tree',
            '--write-tree',
            '--name-only',
            'HEAD',
            f'origin/{base_branch}',
        ]
    )
    if rc == 0:
        return [], None
    if rc == 1:
        # Conflicts: line 1 is the tree SHA, subsequent lines are paths.
        lines = stdout.splitlines()
        return [p.strip() for p in lines[1:] if p.strip()], None
    return [], stderr or f'git merge-tree exited {rc}'


def cmd_baseline_reconcile(args) -> dict:
    """Mechanical baseline reconciliation for phase-2-refine Step 3d.

    A **non-mutating classifier**: it computes the merge-base anchor, lists the
    upstream and in-flight sets against it, and runs a tree-level merge-tree —
    it never moves the branch ref on any classification. The orchestrator
    parses the return TOON: ``upstream_commits`` is the set of commits the
    branch is behind by (anchored on ``merge-base(HEAD, origin/{base_branch})``,
    each entry carrying its touched files); ``conflicts`` is the list of files
    whose three-way merge against ``origin/{base_branch}`` conflicts;
    ``auto_reconcilable`` reports whether an overlap can be reconciled without a
    content conflict (a capability, not a performed action). With ``--emit``,
    the script appends one Q-Gate finding per conflicted file so the existing
    iterate-to-confidence loop addresses the drift via the standard Q-Gate
    finding-resolution path.
    """
    plan_id: str = args.plan_id
    emit: bool = not getattr(args, 'no_emit', False)
    override_branch: str | None = getattr(args, 'base_branch', None)
    override_worktree: str | None = getattr(args, 'worktree_path', None)
    skip_fetch: bool = bool(getattr(args, 'skip_fetch', False))

    worktree_path, skip_reason = _worktree_target(plan_id, override_worktree)
    if worktree_path is None:
        return {
            'status': 'skipped',
            'plan_id': plan_id,
            'reason': skip_reason or 'worktree_unresolved',
        }

    if not _has_remote(worktree_path):
        return {
            'status': 'skipped',
            'plan_id': plan_id,
            'reason': 'no_remote',
        }

    base_branch, branch_source = _resolve_base_branch(plan_id, override_branch)

    # Stale-base-branch auto-update: if the configured base_branch no longer
    # resolves on origin (e.g., a feature branch was merged-and-deleted), swap
    # in the remote default before fetching so the fetch does not fail with a
    # misleading ``could not find remote ref`` error.
    base_branch, base_branch_updated, original_base_branch = _maybe_auto_update_stale_base_branch(
        plan_id, worktree_path, base_branch
    )

    if not skip_fetch and not os.environ.get('PLAN_MARSHALL_SKIP_FETCH'):
        rc, _, stderr = run_git(['-C', worktree_path, 'fetch', 'origin', base_branch])
        if rc != 0:
            return {
                'status': 'skipped',
                'plan_id': plan_id,
                'reason': 'fetch_failed',
                'detail': stderr or f'git fetch origin {base_branch} exited {rc}',
                'base_branch': base_branch,
            }

    # D3 non-mutation guard: capture HEAD before the probe. This is a
    # classifier that performs no writes, so HEAD must be byte-for-byte
    # identical when the probe returns — checked below, before the payload is
    # built. A regression that reintroduces a ref move is then caught HERE, at
    # the probe, rather than discovered later at the landing.
    head_before, head_ok = _resolve_head(worktree_path)
    if not head_ok:
        return {
            'status': 'skipped',
            'plan_id': plan_id,
            'reason': 'head_unresolved',
            'base_branch': base_branch,
        }

    merge_base_sha, merge_base_source = _resolve_merge_base(worktree_path, base_branch)
    if not merge_base_sha:
        return {
            'status': 'skipped',
            'plan_id': plan_id,
            'reason': 'merge_base_unresolved',
            'base_branch': base_branch,
        }

    upstream_commits = _list_upstream_commits(worktree_path, merge_base_sha, base_branch)
    conflicts, merge_error = _detect_merge_conflicts(worktree_path, base_branch)

    # ------------------------------------------------------------------
    # Three-way classification:
    #   no_overlap                     — upstream commits exist but touch
    #                                    disjoint files OR no commits
    #   overlap_no_content_conflict    — upstream + in-flight touch overlapping
    #                                    files BUT merge-tree predicts no
    #                                    content conflict (auto-reconcilable)
    #   overlap_with_content_conflict  — merge-tree predicts conflicts
    #
    # Every input is derived WITHOUT mutating the branch: the upstream and
    # in-flight ranges both anchor on the merge-base, and conflict detection is
    # a tree-level ``git merge-tree`` (write-tree) that never moves HEAD.
    # ------------------------------------------------------------------
    upstream_files: set[str] = set()
    for commit in upstream_commits:
        upstream_files.update(commit.get('files') or [])

    in_flight_files = _list_in_flight_files(worktree_path, merge_base_sha)
    overlap = bool(upstream_files & in_flight_files)

    if conflicts:
        classification = 'overlap_with_content_conflict'
    elif overlap:
        classification = 'overlap_no_content_conflict'
    else:
        classification = 'no_overlap'

    # ``auto_reconcilable`` is a truthful CAPABILITY signal, not a claim that a
    # merge happened: it is true exactly when the overlap can be reconciled
    # without a content conflict, as established by the non-mutating merge-tree
    # probe above. The probe deliberately performs NO merge — the actual
    # reconcile is owned by the caller's rebase step (phase-5 sync-with-main,
    # phase-6 sync-baseline / branch-cleanup). Auto-merging here made the probe
    # a classifier that writes, and moved the ref out from under the very
    # merge-base this range depends on, so the next call re-reported the
    # merged-in commits as upstream — a self-inflicted, self-amplifying
    # over-report. See the module docstring.
    auto_reconcilable = classification == 'overlap_no_content_conflict'

    # ------------------------------------------------------------------
    # Finding emission
    # ------------------------------------------------------------------
    findings_emitted = 0
    # Rejected persists — the conflict finding IS this path's primary output, so
    # a rejection is never absorbed into the ``findings_emitted`` zero bucket
    # (which is indistinguishable from "no conflicts").
    persist_failures: list[dict[str, str]] = []
    if emit and classification == 'overlap_with_content_conflict':
        finding_paths = conflicts
        finding_type = 'triage'
        for path in finding_paths:
            title = f'baseline-reconcile: merge conflict in {path}'
            detail = (
                f'Three-way merge of HEAD against origin/{base_branch} '
                f'reports a conflict in {path}. The plan was authored '
                f'against a baseline that has since drifted upstream; '
                f're-author the affected scope OR justify in '
                f'clarifications why the upstream change is irrelevant '
                f'before phase-5-execute attempts the rebase.'
            )
            result = add_qgate_finding(
                plan_id=plan_id,
                phase=_PHASE,
                source=_QGATE_SOURCE,
                finding_type=finding_type,
                title=title,
                detail=detail,
                file_path=path,
                component='plan-marshall:workflow-integration-git:baseline-reconcile',
                severity='warning',
                iteration=None,
            )
            status = result.get('status')
            if status not in QGATE_PERSIST_OK:
                persist_failures.append(
                    {
                        'title': title,
                        'detail': detail,
                        'file_path': path,
                        'finding_type': finding_type,
                        'message': str(result.get('message', '')),
                    }
                )
            elif status == 'success':
                findings_emitted += 1

    # D3 non-mutation guard: HEAD must be unchanged by a classifier that
    # performs no writes. If it moved, the probe cannot be trusted to have
    # classified the state it reported, so it fails LOUD here rather than
    # returning a verdict derived from a tree it silently mutated. This takes
    # precedence over every other outcome, including a persist failure — a
    # moved ref invalidates the whole classification.
    head_after, head_after_ok = _resolve_head(worktree_path)
    if not head_after_ok or head_after != head_before:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'base_branch': base_branch,
            'error': 'probe_mutated_head',
            'head_before': head_before,
            'head_after': head_after,
            'message': (
                'baseline-reconcile is a non-mutating classifier but HEAD '
                f'changed during the probe (before={head_before}, '
                f'after={head_after}); refusing to return a classification '
                'derived from a mutated tree.'
            ),
        }

    payload: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'worktree_path': worktree_path,
        'base_branch': base_branch,
        'base_branch_source': branch_source,
        'base_branch_updated': base_branch_updated,
        'merge_base_sha': merge_base_sha,
        'merge_base_source': merge_base_source,
        'upstream_commit_count': len(upstream_commits),
        'upstream_commits': upstream_commits,
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
        'in_flight_files': sorted(in_flight_files),
        'merge_tree_error': merge_error,
        'findings_emitted': findings_emitted,
        'emit': emit,
        'classification': classification,
        'auto_reconcilable': auto_reconcilable,
    }
    if base_branch_updated and original_base_branch is not None:
        payload['original_base_branch'] = original_base_branch
    if persist_failures:
        # The conflict finding is this path's primary output — if it never
        # reached the store the command has not done its job, so the caller
        # sees an error carrying the rejected finding content inline rather
        # than a clean result with findings_emitted: 0.
        payload['status'] = 'error'
        payload['error'] = 'finding_persist_failed'
        payload['qgate_persist_failed'] = True
        payload['qgate_persist_failures'] = persist_failures
    return payload


def _list_in_flight_files(worktree_path: str, merge_base_sha: str) -> set[str]:
    """Return the set of files the branch itself changed since ``merge_base_sha``.

    Anchoring on the merge-base makes ``{merge_base_sha}..HEAD`` exactly the
    branch's *own* commits, so the returned set contains only files the plan
    touched. Anchoring on a stale initialisation SHA instead would fold in any
    upstream commits the branch has since merged in, inflating the set with
    files the plan never touched and turning the upstream/in-flight overlap
    spuriously non-empty.
    """
    rc, stdout, _ = run_git(
        ['-C', worktree_path, 'diff', '--name-only', f'{merge_base_sha}..HEAD']
    )
    if rc != 0 or not stdout:
        return set()
    return {line.strip() for line in stdout.splitlines() if line.strip()}
