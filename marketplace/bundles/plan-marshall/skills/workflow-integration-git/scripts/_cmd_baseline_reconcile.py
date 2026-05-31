#!/usr/bin/env python3
"""Mechanical baseline-reconciliation predicate for phase-2-refine Step 3d.

Fetches the upstream tip, walks the commits landed on
``origin/{base_branch}`` since the plan's captured worktree SHA, and
runs ``git merge-tree`` to detect potential merge conflicts — without
modifying the worktree's working tree. Each upstream commit and each
conflicted file is surfaced in the return TOON; with ``--emit`` an
equivalent Q-Gate finding is appended under ``--source qgate`` so the
phase-2-refine iterate-to-confidence loop consumes the result via the
existing finding-resolution path.

The LLM-judgement step (decide which upstream commits warrant scope
adjustment) stays bundled in the existing phase-2-refine dispatch — this
script is the mechanical predicate only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from _findings_core import add_qgate_finding  # type: ignore[import-not-found]
from git_provider import run_git  # type: ignore[import-not-found]

_PHASE = '2-refine'
_QGATE_SOURCE = 'qgate'
_DEFAULT_BASE_BRANCH = 'main'


def _resolve_worktree_path(plan_id: str, override: str | None) -> tuple[str | None, str | None]:
    """Resolve the worktree path for ``plan_id``.

    Returns ``(path, skip_reason_or_None)``. The skip reason is
    populated when the plan declares ``use_worktree==false`` or when
    status.json is missing/unparseable — both are documented skip
    conditions in Step 3d's activation guard.
    """
    if override:
        return override, None

    try:
        from _status_core import read_status  # type: ignore[import-not-found]
    except ImportError:
        return None, 'status_module_unavailable'

    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        return None, 'status_not_found'

    metadata = status.get('metadata', {}) if isinstance(status, dict) else {}
    if metadata.get('use_worktree') is False:
        return None, 'main_checkout_flow'

    worktree_path = metadata.get('worktree_path')
    if not worktree_path or not isinstance(worktree_path, str):
        return None, 'worktree_path_missing'

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
        from _config_core import load_config  # type: ignore[import-not-found]
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


def _resolve_baseline_sha(plan_id: str, worktree_path: str) -> tuple[str, str]:
    """Return ``(sha, source)`` for the baseline SHA used in the diff.

    Preference order: ``status.metadata.worktree_sha`` (captured at
    phase-1-init) → current worktree HEAD.
    """
    try:
        from _status_core import read_status  # type: ignore[import-not-found]

        status = read_status(plan_id)
        metadata = status.get('metadata', {}) if isinstance(status, dict) else {}
        sha = metadata.get('worktree_sha')
        if isinstance(sha, str) and sha.strip():
            return sha.strip(), 'metadata'
    except (ImportError, FileNotFoundError):
        pass

    rc, stdout, _ = run_git(['-C', worktree_path, 'rev-parse', 'HEAD'])
    if rc != 0:
        return '', 'unresolved'
    return stdout.strip(), 'head'


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
        from _references_core import read_references, write_references  # type: ignore[import-not-found]
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
            from plan_logging import log_entry  # type: ignore[import-not-found]
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
    baseline_sha: str,
    base_branch: str,
) -> list[dict[str, Any]]:
    """Return ``[{sha, subject, files}]`` for upstream commits since ``baseline_sha``.

    Uses a single ``git log --name-only`` call so the subprocess cost is
    O(1) in the number of commits — long upstream divergence does not
    require N + 1 subprocesses. The output groups each commit's metadata
    line with its touched-file list separated by a blank line.
    """
    rc, stdout, _ = run_git(
        [
            '-C',
            worktree_path,
            'log',
            f'{baseline_sha}..origin/{base_branch}',
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

    The orchestrator parses the return TOON: ``upstream_commits`` is the
    full diff against the plan baseline (each entry carries its touched
    files); ``conflicts`` is the list of files whose three-way merge
    against ``origin/{base_branch}`` failed. With ``--emit``, the script
    appends one Q-Gate finding per conflicted file so the existing
    iterate-to-confidence loop addresses the drift via the standard
    Q-Gate finding-resolution path.
    """
    plan_id: str = args.plan_id
    emit: bool = not getattr(args, 'no_emit', False)
    override_branch: str | None = getattr(args, 'base_branch', None)
    override_worktree: str | None = getattr(args, 'worktree_path', None)
    skip_fetch: bool = bool(getattr(args, 'skip_fetch', False))

    worktree_path, skip_reason = _resolve_worktree_path(plan_id, override_worktree)
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

    baseline_sha, baseline_source = _resolve_baseline_sha(plan_id, worktree_path)
    if not baseline_sha:
        return {
            'status': 'skipped',
            'plan_id': plan_id,
            'reason': 'baseline_sha_unresolved',
            'base_branch': base_branch,
        }

    upstream_commits = _list_upstream_commits(worktree_path, baseline_sha, base_branch)
    conflicts, merge_error = _detect_merge_conflicts(worktree_path, base_branch)

    # ------------------------------------------------------------------
    # Three-way classification (deliverable 6):
    #   no_overlap                     — upstream commits exist but touch
    #                                    disjoint files OR no commits
    #   overlap_no_content_conflict    — upstream + in-flight touch overlapping
    #                                    files BUT merge-tree predicts no
    #                                    content conflict (auto-resolvable)
    #   overlap_with_content_conflict  — merge-tree predicts conflicts
    # ------------------------------------------------------------------
    upstream_files: set[str] = set()
    for commit in upstream_commits:
        upstream_files.update(commit.get('files') or [])

    in_flight_files = _list_in_flight_files(worktree_path, baseline_sha)
    overlap = bool(upstream_files & in_flight_files)

    if conflicts:
        classification = 'overlap_with_content_conflict'
    elif overlap:
        classification = 'overlap_no_content_conflict'
    else:
        classification = 'no_overlap'

    # ------------------------------------------------------------------
    # Focused reconcile (only on overlap_no_content_conflict)
    # ------------------------------------------------------------------
    auto_reconciled = False
    merge_commit_sha: str | None = None
    merge_failure_paths: list[str] = []
    reconciled_modified_files_count: int | None = None
    if classification == 'overlap_no_content_conflict':
        merge_rc, merge_stdout, merge_stderr = run_git(
            ['-C', worktree_path, 'merge', f'origin/{base_branch}', '--no-edit']
        )
        if merge_rc == 0:
            auto_reconciled = True
            rc_sha, sha_out, _ = run_git(['-C', worktree_path, 'rev-parse', 'HEAD'])
            if rc_sha == 0:
                merge_commit_sha = sha_out.strip() or None
            try:
                from plan_logging import log_entry  # type: ignore[import-not-found]
            except ImportError:
                log_entry = None  # type: ignore[assignment]
            if log_entry is not None:
                commit_subjects = ', '.join(
                    f'{c.get("sha", "")[:8]} {c.get("subject", "")}'
                    for c in upstream_commits
                )
                log_entry(
                    'decision',
                    plan_id,
                    'INFO',
                    f'(plan-marshall:workflow-integration-git:baseline-reconcile) '
                    f'Focused reconcile auto-resolved overlap_no_content_conflict drift '
                    f'(merged origin/{base_branch} into HEAD): {commit_subjects}',
                )

            # Reconcile references.modified_files against the post-merge
            # plan-branch-only diff so the absorbed upstream content does not
            # pollute the ledger. The absorb merge has already succeeded; a
            # reconcile failure (references missing / not a git worktree) is
            # logged but MUST NOT abort the reconcile predicate.
            try:
                from _references_core import reconcile_modified_files  # type: ignore[import-not-found]

                reconcile_result = reconcile_modified_files(
                    plan_id, Path(worktree_path), base_branch
                )
            except (ImportError, OSError) as exc:
                reconcile_result = {'status': 'error', 'error': type(exc).__name__, 'message': str(exc)}

            if reconcile_result.get('status') == 'success':
                reconciled_modified_files_count = reconcile_result.get('after_count')
            else:
                try:
                    from plan_logging import log_entry as _recon_log  # type: ignore[import-not-found]
                except ImportError:
                    _recon_log = None  # type: ignore[assignment]
                if _recon_log is not None:
                    _recon_log(
                        'work',
                        plan_id,
                        'WARNING',
                        f'(plan-marshall:workflow-integration-git:baseline-reconcile) '
                        f'modified_files reconcile after auto-merge did not succeed: '
                        f'{reconcile_result.get("error", "unknown")} — absorb itself succeeded, continuing',
                    )
        else:
            # Rare: merge-tree predicted no conflict but the real merge produced
            # one (e.g., overlapping renames). Capture the conflicting file
            # paths via ``git diff --name-only --diff-filter=U`` BEFORE
            # aborting — parsing ``merge_stdout`` is unreliable because the
            # merge output contains human-readable log messages
            # (``Auto-merging…``, ``CONFLICT…``) rather than a clean list of
            # paths. Then abort the merge and downgrade classification so
            # downstream paths handle it as a real conflict.
            rc_diff, diff_stdout, _ = run_git(
                ['-C', worktree_path, 'diff', '--name-only', '--diff-filter=U']
            )
            if rc_diff == 0:
                merge_failure_paths = [
                    line.strip() for line in (diff_stdout or '').splitlines() if line.strip()
                ]
            else:
                merge_failure_paths = []
            run_git(['-C', worktree_path, 'merge', '--abort'])
            classification = 'overlap_with_content_conflict'
            if not merge_failure_paths:
                merge_failure_paths = ['<unknown>']
            merge_error = (merge_stderr or '').strip() or merge_error
            # ``merge_stdout`` is intentionally unused now; retain the param to
            # preserve the existing call signature for downstream readers.
            _ = merge_stdout

    # ------------------------------------------------------------------
    # Finding emission
    # ------------------------------------------------------------------
    findings_emitted = 0
    if emit and classification == 'overlap_with_content_conflict':
        finding_paths = conflicts or merge_failure_paths
        finding_type = (
            'baseline_drift_reconcile_failed'
            if merge_failure_paths
            else 'triage'
        )
        for path in finding_paths:
            result = add_qgate_finding(
                plan_id=plan_id,
                phase=_PHASE,
                source=_QGATE_SOURCE,
                finding_type=finding_type,
                title=f'baseline-reconcile: merge conflict in {path}',
                detail=(
                    f'Three-way merge of HEAD against origin/{base_branch} '
                    f'reports a conflict in {path}. The plan was authored '
                    f'against a baseline that has since drifted upstream; '
                    f're-author the affected scope OR justify in '
                    f'clarifications why the upstream change is irrelevant '
                    f'before phase-5-execute attempts the rebase.'
                ),
                file_path=path,
                component='plan-marshall:workflow-integration-git:baseline-reconcile',
                severity='warning',
                iteration=None,
            )
            if result.get('status') == 'success':
                findings_emitted += 1

    payload: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'worktree_path': worktree_path,
        'base_branch': base_branch,
        'base_branch_source': branch_source,
        'base_branch_updated': base_branch_updated,
        'baseline_sha': baseline_sha,
        'baseline_sha_source': baseline_source,
        'upstream_commit_count': len(upstream_commits),
        'upstream_commits': upstream_commits,
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
        'merge_tree_error': merge_error,
        'findings_emitted': findings_emitted,
        'emit': emit,
        'classification': classification,
        'auto_reconciled': auto_reconciled,
    }
    if merge_commit_sha is not None:
        payload['merge_commit_sha'] = merge_commit_sha
    if reconciled_modified_files_count is not None:
        payload['reconciled_modified_files_count'] = reconciled_modified_files_count
    if merge_failure_paths:
        payload['merge_failure_paths'] = merge_failure_paths
    if base_branch_updated and original_base_branch is not None:
        payload['original_base_branch'] = original_base_branch
    return payload


def _list_in_flight_files(worktree_path: str, baseline_sha: str) -> set[str]:
    """Return the set of files modified in the worktree since ``baseline_sha``."""
    rc, stdout, _ = run_git(
        ['-C', worktree_path, 'diff', '--name-only', f'{baseline_sha}..HEAD']
    )
    if rc != 0 or not stdout:
        return set()
    return {line.strip() for line in stdout.splitlines() if line.strip()}
