#!/usr/bin/env python3
"""Consolidated sync engine for the project-local ``sync-plugin-cache`` skill.

Pipeline:

    marketplace/bundles/  →  target/claude/  →  ~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/

The script consumes the multi-target generator output at
``target/claude/`` (or a worktree-local equivalent) and rsyncs each
emitted bundle into the host plugin cache.

Outputs a TOON document on stdout:

    status: success | partial | error
    synced_count: N
    failed_count: M
    summary_message: "<human-readable summary>"
    synced[N]{bundle,version,status}:
      bundle1,0.1.0,success
      bundle2,unknown,skipped
    failed[M]{bundle,error}:
      bundle3,"rsync exited 23"

Exit codes:

    0 on ``status: success`` or ``status: partial`` (partial means at
      least one bundle synced; the caller decides whether to treat that
      as a hard failure based on the failure table).
    1 on ``status: error`` (nothing synced, hard failure).
    2 on bad inputs (no target/, staleness guard tripped, etc.).

Flags:

    --from-worktree PATH   Resolve source from {PATH}/target/claude/.
    --bundle NAME          Restrict sync to a single bundle.
    --source-root PATH     Override the source root (advanced — bypasses
                           the worktree resolver). Default is
                           ``{cwd}/target/claude``.
    --cache-root PATH      Override the cache destination root. Default
                           is ``~/.claude/plugins/cache/plan-marshall``.
    --skip-staleness-guard Bypass the staleness check (dangerous —
                           reserved for tests and recovery flows).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_CACHE_ROOT = Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
TARGET_SUBDIR = Path('target') / 'claude'
MARKETPLACE_SUBDIR = Path('marketplace') / 'bundles'

# Hard-coded denylist applied when the git-based ignore probe is unavailable
# (e.g., shallow checkouts, missing ``git`` binary, or sources sitting
# outside any git repository). The patterns target transient runtime
# artifacts that frequently appear in marketplace/ during pytest /
# mypy / ruff runs and would otherwise trip the time-based staleness
# check despite belonging to ``.gitignore``.
#
# Each entry is a path *segment* compared against ``Path.parts`` (so
# ``__pycache__`` matches any directory named ``__pycache__`` anywhere in
# the tree). Entries that include a ``.`` (suffix) are treated as
# trailing-suffix matches against the filename.
_TRANSIENT_DIR_NAMES: frozenset[str] = frozenset(
    {
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
    }
)
_TRANSIENT_FILE_NAMES: frozenset[str] = frozenset(
    {
        '.coverage',
    }
)
_TRANSIENT_FILE_SUFFIXES: tuple[str, ...] = ('.pyc',)


def _read_version(plugin_json: Path) -> str:
    try:
        data = json.loads(plugin_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return 'unknown'
    version = data.get('version')
    return version if isinstance(version, str) and version else 'unknown'


def _emit_toon(
    *,
    status: str,
    synced: list[dict[str, str]],
    failed: list[dict[str, str]],
    summary_message: str,
) -> str:
    synced_count = sum(1 for row in synced if row['status'] == 'success')
    failed_count = len(failed)
    lines = [
        f'status: {status}',
        f'synced_count: {synced_count}',
        f'failed_count: {failed_count}',
        f'summary_message: "{summary_message}"',
    ]
    lines.append(f'synced[{len(synced)}]{{bundle,version,status}}:')
    for row in synced:
        lines.append(f'  {row["bundle"]},{row["version"]},{row["status"]}')
    if failed:
        lines.append(f'failed[{len(failed)}]{{bundle,error}}:')
        for row in failed:
            err = row['error'].replace('"', '\\"')
            lines.append(f'  {row["bundle"]},"{err}"')
    return '\n'.join(lines) + '\n'


def _resolve_source_root(args: argparse.Namespace) -> Path:
    source_root: Path | None = args.source_root
    from_worktree: Path | None = args.from_worktree
    if source_root is not None:
        return source_root
    if from_worktree is not None:
        return from_worktree / TARGET_SUBDIR
    return Path.cwd() / TARGET_SUBDIR


def _resolve_marketplace_root(args: argparse.Namespace) -> Path:
    from_worktree: Path | None = args.from_worktree
    if from_worktree is not None:
        return from_worktree / MARKETPLACE_SUBDIR
    return Path.cwd() / MARKETPLACE_SUBDIR


def _is_transient_artifact(rel_parts: tuple[str, ...]) -> bool:
    """Return True when the path matches the hard-coded transient-artifact denylist.

    Used as the fallback ignore filter when the git-based probe is unavailable.
    Compares path segments against :data:`_TRANSIENT_DIR_NAMES`, the filename
    against :data:`_TRANSIENT_FILE_NAMES`, and the filename suffix against
    :data:`_TRANSIENT_FILE_SUFFIXES`. The match is conservative — only drops
    paths that look like runtime artifacts of pytest / mypy / ruff /
    coverage. Tracked source files (``.py``, ``.md``, ``.json``, ``.toon``,
    etc.) always pass through.
    """
    if not rel_parts:
        return False
    for part in rel_parts:
        if part in _TRANSIENT_DIR_NAMES:
            return True
    filename = rel_parts[-1]
    if filename in _TRANSIENT_FILE_NAMES:
        return True
    return any(filename.endswith(suffix) for suffix in _TRANSIENT_FILE_SUFFIXES)


def _git_ignored_files(root: Path) -> set[str] | None:
    """Return the set of paths under ``root`` that git considers ignored.

    Invokes ``git -C {root_parent} ls-files --others --ignored
    --exclude-standard`` to enumerate ignored files (``--others`` includes
    untracked, ``--ignored`` filters down to those matched by gitignore /
    excludes / core.excludesfile). Returns paths as strings relative to
    ``root_parent`` so callers can compare against ``Path.relative_to``
    output without further translation.

    Returns ``None`` when git is unavailable, the directory is not inside
    a git work tree, or the invocation fails for any other reason — the
    caller MUST fall back to the hard-coded denylist in that case so the
    guard still trips on tracked source-file changes.
    """
    if not root.is_dir():
        return None
    if not shutil.which('git'):
        return None
    try:
        # Run git from the parent of marketplace/bundles so ignored paths
        # are reported as ``marketplace/bundles/...``. This makes the
        # downstream comparison straightforward.
        repo_root = root.parent.parent if root.name == 'bundles' else root
        result = subprocess.run(
            [
                'git',
                '-C',
                str(repo_root),
                'ls-files',
                '--others',
                '--ignored',
                '--exclude-standard',
                '--',
                str(root.relative_to(repo_root)),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None
    if result.returncode != 0:
        # Outside a git repo / shallow checkout / other failure mode —
        # fall back to the denylist.
        return None
    ignored: set[str] = set()
    for line in result.stdout.splitlines():
        path = line.strip()
        if path:
            # The git output is repo-relative; resolve to absolute so
            # callers can compare against ``Path`` objects consistently.
            ignored.add(str((repo_root / path).resolve()))
    return ignored


def _iter_filtered_files(root: Path, ignored: set[str] | None) -> list[Path]:
    """Yield files under ``root`` excluding git-ignored / transient artifacts.

    When ``ignored`` is non-None (git probe succeeded), drop any file
    whose absolute path is in the set. Always also apply the
    transient-artifact denylist as a belt-and-suspenders safeguard so
    fresh untracked artifacts (not yet seen by git) and pyc files
    matching the .gitignore pattern but not yet enumerated by ls-files
    are still excluded.
    """
    files: list[Path] = []
    if not root.is_dir():
        return files
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        # Use parts relative to root for the denylist match so deeply
        # nested transient dirs (e.g., bundle/.../scripts/__pycache__/x.pyc)
        # are caught regardless of nesting depth.
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            rel_parts = path.parts
        if _is_transient_artifact(rel_parts):
            continue
        if ignored is not None and str(path.resolve()) in ignored:
            continue
        files.append(path)
    return files


def _newest_mtime(root: Path, ignored: set[str] | None = None) -> float:
    """Return the newest mtime under ``root`` (recursively), or 0 if empty/missing.

    When ``ignored`` is non-None it is the set of git-ignored absolute
    paths (from :func:`_git_ignored_files`); those files are skipped.
    The transient-artifact denylist is always applied via
    :func:`_iter_filtered_files`.
    """
    newest = 0.0
    for path in _iter_filtered_files(root, ignored):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime > newest:
            newest = mtime
    return newest


def _oldest_mtime(root: Path, ignored: set[str] | None = None) -> float:
    """Return the oldest mtime under ``root`` (recursively), or 0 if empty/missing.

    Mirrors :func:`_newest_mtime`'s filtering: ignored / transient files
    are skipped so the staleness comparison only considers tracked,
    source-shaped files.
    """
    oldest: float | None = None
    for path in _iter_filtered_files(root, ignored):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if oldest is None or mtime < oldest:
            oldest = mtime
    return oldest if oldest is not None else 0.0


def _regenerate_hint() -> str:
    return (
        'Regenerate with `python3 marketplace/targets/generate.py '
        '--target claude --output target/claude`.'
    )


def _is_bundle_dir(path: Path) -> bool:
    """A directory is a bundle iff it carries its own ``.claude-plugin/plugin.json``.

    Filters out non-bundle directories that may live alongside bundle
    folders in the target tree — notably the top-level ``.claude-plugin/``
    directory that holds the marketplace.json registration manifest.
    """
    return path.is_dir() and (path / '.claude-plugin' / 'plugin.json').is_file()


def _staleness_guard(source_root: Path, marketplace_root: Path) -> str | None:
    """Return a human-readable reason when source is missing/stale, else None."""
    if not source_root.is_dir():
        return f'source root not found: {source_root}. {_regenerate_hint()}'
    bundles_in_source = sorted(p.name for p in source_root.iterdir() if _is_bundle_dir(p))
    if not bundles_in_source:
        return f'source root contains no bundles: {source_root}. {_regenerate_hint()}'

    if marketplace_root.is_dir():
        bundles_in_market = sorted(p.name for p in marketplace_root.iterdir() if _is_bundle_dir(p))
        missing = [b for b in bundles_in_market if b not in bundles_in_source]
        if missing:
            return (
                'target/claude/ appears stale — bundles in marketplace/bundles/ are missing '
                f'from target output: {", ".join(missing)}. {_regenerate_hint()}'
            )

        # Time-based staleness: if the oldest file in target/claude/ is older
        # than the newest file in marketplace/bundles/, the mirror is stale.
        # Refuse so callers regenerate before sync.
        #
        # Filter the marketplace walk via the git-ignored probe so transient
        # artifacts (``__pycache__``, ``.pyc``, ``.pytest_cache``, ...) do
        # NOT trip the guard after a pytest / mypy / ruff run. ``ignored``
        # is None when the git probe is unavailable; the transient-artifact
        # denylist applied inside :func:`_iter_filtered_files` still drops
        # the common cases. The source root (``target/claude/``) is a
        # generator output that does not contain transient artifacts, so
        # filtering there is a no-op in practice but kept symmetrical.
        ignored_source = _git_ignored_files(source_root)
        ignored_marketplace = _git_ignored_files(marketplace_root)
        oldest_target = _oldest_mtime(source_root, ignored_source)
        newest_source = _newest_mtime(marketplace_root, ignored_marketplace)
        if oldest_target and newest_source and oldest_target < newest_source:
            return (
                'target/claude/ is stale — oldest target file predates the newest source file. '
                f'{_regenerate_hint()}'
            )

    return None


def _rsync_bundle(*, bundle: str, source_dir: Path, dest_dir: Path) -> tuple[str, str]:
    """rsync one bundle. Returns (status, error_message)."""
    if not shutil.which('rsync'):
        return 'failed', 'rsync not found on PATH'
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        'rsync',
        '-a',
        '--delete',
        f'{source_dir}/',
        f'{dest_dir}/',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 'failed', f'rsync exec error: {exc}'
    if result.returncode != 0:
        return 'failed', f'rsync exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}'
    return 'success', ''


def _select_bundles(source_root: Path, only: str | None) -> list[Path]:
    if not source_root.is_dir():
        return []
    bundles = sorted(p for p in source_root.iterdir() if _is_bundle_dir(p))
    if only is not None:
        bundles = [b for b in bundles if b.name == only]
    return bundles


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Synchronize the Claude plugin cache from target/claude/.',
        allow_abbrev=False,
    )
    parser.add_argument('--from-worktree', type=Path, default=None, metavar='PATH')
    parser.add_argument('--bundle', type=str, default=None, metavar='NAME')
    parser.add_argument('--source-root', type=Path, default=None, metavar='PATH')
    parser.add_argument('--cache-root', type=Path, default=DEFAULT_CACHE_ROOT, metavar='PATH')
    parser.add_argument('--skip-staleness-guard', action='store_true')
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv if argv is not None else sys.argv[1:])

    source_root = _resolve_source_root(args)
    marketplace_root = _resolve_marketplace_root(args)

    if not args.skip_staleness_guard:
        reason = _staleness_guard(source_root, marketplace_root)
        if reason is not None:
            sys.stdout.write(
                _emit_toon(
                    status='error',
                    synced=[],
                    failed=[],
                    summary_message=reason,
                )
            )
            return 2

    bundles = _select_bundles(source_root, args.bundle)
    if not bundles:
        msg = (
            f'no matching bundles in {source_root}'
            + (f' (filter: --bundle {args.bundle})' if args.bundle else '')
        )
        sys.stdout.write(
            _emit_toon(status='error', synced=[], failed=[], summary_message=msg)
        )
        return 1

    synced: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    def task(bundle_dir: Path) -> tuple[str, str, str, str]:
        version = _read_version(bundle_dir / '.claude-plugin' / 'plugin.json')
        dest = args.cache_root / bundle_dir.name / version
        status, error = _rsync_bundle(bundle=bundle_dir.name, source_dir=bundle_dir, dest_dir=dest)
        return bundle_dir.name, version, status, error

    with ThreadPoolExecutor(max_workers=min(8, len(bundles) or 1)) as pool:
        futures = [pool.submit(task, b) for b in bundles]
        for fut in as_completed(futures):
            name, version, status, error = fut.result()
            synced.append({'bundle': name, 'version': version, 'status': status})
            if status != 'success':
                failed.append({'bundle': name, 'error': error or 'unknown error'})

    synced.sort(key=lambda row: row['bundle'])
    failed.sort(key=lambda row: row['bundle'])

    if not failed:
        status = 'success'
        message = f'synced {len(synced)} bundle(s) to {args.cache_root}'
        exit_code = 0
    elif len(failed) == len(bundles):
        status = 'error'
        message = f'all {len(failed)} bundle(s) failed'
        exit_code = 1
    else:
        status = 'partial'
        message = f'{len(synced) - len(failed)} succeeded, {len(failed)} failed'
        exit_code = 0

    sys.stdout.write(_emit_toon(status=status, synced=synced, failed=failed, summary_message=message))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
