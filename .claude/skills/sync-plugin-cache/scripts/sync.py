#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Consolidated sync engine for the project-local ``sync-plugin-cache`` skill.

Pipeline:

    marketplace/bundles/  →  target/claude/  →  ~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/

The script consumes the multi-target generator output at
``target/claude/`` (or a worktree-local equivalent) and rsyncs each
emitted bundle into the host plugin cache. After a successful (non-error)
sync it also mirrors the top-level ``target/claude/dist-manifest.json``
into the plugin-cache ROOT (``{cache_root}/dist-manifest.json``, alongside
the versioned ``{bundle}/{version}/`` dirs) so the dist-branch versioning
feature's ``find_installed_manifest_path`` resolves the installed version
from ``base_path/dist-manifest.json`` in the meta-project's own
preflight/executor-regen context.

Staleness guard
---------------

The guard refuses to sync when ``target/claude/`` is missing, contains no
bundles, or is stale relative to the worktree source tree. Staleness is
determined by a sentinel file ``target/claude/.emit-marker.json`` written
at the end of every successful emit by
``marketplace/targets/claude/target.py``. The sentinel carries a
``source_tree_fingerprint`` computed from git's native ``ls-files`` /
``hash-object`` primitives over ``marketplace/bundles/``; the guard
recomputes the same fingerprint and refuses on mismatch. Both sides
import the helper from
``marketplace.targets.claude.source_fingerprint`` so the fingerprint
algorithm cannot drift between emit and sync.

The sentinel fingerprint is supplemented by a file-level content-hash
check (``_file_level_drift``): the emitter records a per-file hash
manifest of the emitted tree in the sentinel's ``file_hashes`` field, and
the guard re-hashes each live file under ``target/claude/`` and compares
it to the manifest. A manifest entry whose live file is gone (missing) or
hashes differently (diverged), or a live target file absent from the
manifest (extra), is named by path in the refusal message — turning an
opaque single-digest mismatch into a per-file diagnosis. The manifest is
the comparison baseline (not the raw ``marketplace/bundles/`` source)
because ``target/claude/`` is transformed generator output — expanded
agent variants, a variant-aware ``plugin.json``, a top-level
``marketplace.json`` — with no verbatim source counterpart. The check
reuses the shared ``hash_objects`` primitive so the manifest and the
live re-hash compute identically, hashing the gitignored
``target/claude/`` tree directly via ``git hash-object`` (which reads
arbitrary worktree bytes regardless of tracking).

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


def _resolve_repo_root_for_sentinel(source_root: Path) -> Path:
    """Resolve the repo root that the sentinel was written against.

    The emitter computes the fingerprint relative to
    ``marketplace_dir.parent`` (the project root that contains
    ``marketplace/``). When sync runs against
    ``{repo}/target/claude/`` the repo root is the grandparent of
    ``source_root``. The ``--from-worktree`` and ``--source-root``
    flags can move the source root around; the guard pairs the
    sentinel's recompute against the directory tree that produced it,
    which is always two levels up from ``source_root`` for the
    canonical ``{repo}/target/claude/`` layout. Callers using
    ``--source-root`` for ad-hoc paths can still bypass the guard via
    ``--skip-staleness-guard``.
    """
    return source_root.parent.parent


def _import_source_fingerprint():
    """Import the shared fingerprint helper.

    The helper lives under ``marketplace/targets/claude/source_fingerprint.py``
    in the project tree. This script runs as a standalone Python file
    with no marketplace package on ``sys.path``, so we resolve the
    project root from the script's own location (``.claude/skills/
    sync-plugin-cache/scripts/sync.py`` -> repo root is four parents up)
    and prepend it to ``sys.path`` before importing.
    """
    script_path = Path(__file__).resolve()
    # script_path = .../{repo}/.claude/skills/sync-plugin-cache/scripts/sync.py
    # parents[0]=scripts, [1]=sync-plugin-cache, [2]=skills, [3]=.claude, [4]=repo
    repo_root = script_path.parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from marketplace.targets.claude.source_fingerprint import (  # noqa: E402
        FingerprintError,
        compute_source_tree_fingerprint,
    )

    return compute_source_tree_fingerprint, FingerprintError


def _import_hash_objects():
    """Import the shared per-file blob-hash helper.

    Resolves the project root the same way as
    :func:`_import_source_fingerprint` (script location -> four parents
    up) and returns the ``hash_objects`` primitive plus its
    ``FingerprintError`` type. ``hash_objects`` hashes arbitrary worktree
    bytes via ``git hash-object --stdin-paths`` regardless of whether the
    paths are tracked — so it works on the gitignored ``target/claude/``
    tree as well as the tracked ``marketplace/bundles/`` source.
    """
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from marketplace.targets.claude.source_fingerprint import (  # noqa: E402
        FingerprintError,
        hash_objects,
    )

    return hash_objects, FingerprintError


DEFAULT_CACHE_ROOT = Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
TARGET_SUBDIR = Path('target') / 'claude'
MARKETPLACE_SUBDIR = Path('marketplace') / 'bundles'

# Sentinel filename written at the end of every successful emit by the
# Claude target. See ``marketplace/targets/claude/target.py``.
EMIT_MARKER_FILENAME = '.emit-marker.json'

# Top-level manifest filename mirrored into the plugin-cache ROOT after a
# successful sync. The dist-branch versioning feature reads the installed
# version from ``base_path/dist-manifest.json``; for the meta-project's own
# preflight the base_path IS the cache root, so the manifest must ride into
# the cache root alongside the versioned ``{bundle}/{version}/`` dirs.
DIST_MANIFEST_FILENAME = 'dist-manifest.json'


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


def _relative_file_map(root: Path) -> dict[str, Path]:
    """Map every regular file under ``root`` to its ``root``-relative POSIX path.

    The map key is the path relative to ``root`` rendered with forward
    slashes so the source and target trees compare identically across
    platforms. Symlinks and non-regular entries are skipped — only the
    file bytes that ``rsync`` would mirror participate in the drift
    comparison. Returns an empty map when ``root`` is not a directory.
    """
    if not root.is_dir():
        return {}
    file_map: dict[str, Path] = {}
    try:
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                file_map[path.relative_to(root).as_posix()] = path
    except OSError:
        return file_map
    return file_map


def _file_level_drift(source_root: Path, file_hashes: dict[str, str]) -> str | None:
    """Return a human-readable reason naming per-file target drift, else None.

    Supplements the single ``source_tree_fingerprint`` sentinel with
    per-file granularity by comparing the emitted ``target/claude/`` tree
    against the per-file hash manifest the emitter recorded in the
    sentinel (``file_hashes`` — keyed by ``source_root``-relative POSIX
    path). ``target/claude/`` is TRANSFORMED generator output (expanded
    agent variants, a variant-aware ``plugin.json``, a top-level
    ``marketplace.json``), not a raw mirror of ``marketplace/bundles/`` —
    so the manifest, not the raw source tree, is the only correct
    comparison baseline. Three drift classes are detected and the specific
    offending paths are named in the refusal message:

    * **missing** — a manifest entry has no corresponding live file
      (an emitted file was deleted after the emit).
    * **diverged** — a manifest entry's live file hashes differently than
      recorded (the file's bytes were mutated after the emit).
    * **extra** — a live ``target/claude/`` file is absent from the
      manifest (a stray artefact appeared after the emit). The sentinel
      itself (``.emit-marker.json``) is always excluded — it carries the
      manifest and so can never be one of its own entries.

    Hashing delegates to the shared ``hash_objects`` primitive
    (``git hash-object``) so the live hashes are byte-identical to the
    manifest the emitter wrote with the same primitive; the live files are
    passed by ABSOLUTE path because ``git hash-object`` resolves a relative
    pathspec against the enclosing repo's worktree root (not the ``-C``
    directory), which would break when ``target/claude/`` lives inside a
    git repo — as it always does in production. ``git hash-object`` reads
    arbitrary worktree bytes and therefore works on the gitignored
    ``target/claude/`` tree. Returns ``None`` when every manifest entry
    matches its live file and the tree carries no extra file. A clean
    import / hashing failure degrades to ``None`` (the sentinel fingerprint
    check remains the primary guard) rather than blocking sync on an
    environmental fault.
    """
    live_files = _relative_file_map(source_root)
    live_files.pop(EMIT_MARKER_FILENAME, None)

    missing = sorted(rel for rel in file_hashes if rel not in live_files)
    extra = sorted(rel for rel in live_files if rel not in file_hashes)

    try:
        hash_objects, _FingerprintError = _import_hash_objects()
    except ImportError:
        return None

    common = sorted(set(file_hashes) & set(live_files))
    diverged: list[str] = []
    if common:
        abs_paths = [str(live_files[rel].resolve()) for rel in common]
        try:
            live_shas = hash_objects(source_root, abs_paths)
        except _FingerprintError:
            return None
        for rel, live_sha in zip(common, live_shas, strict=True):
            if live_sha != file_hashes[rel]:
                diverged.append(rel)

    if not (missing or extra or diverged):
        return None

    parts: list[str] = []
    if missing:
        parts.append(f'missing from target: {", ".join(missing)}')
    if extra:
        parts.append(f'extra in target: {", ".join(extra)}')
    if diverged:
        parts.append(f'content diverged: {", ".join(diverged)}')
    return (
        'staleness_guard: target/claude/ drifted from its emit manifest at file level — '
        + '; '.join(parts)
        + f'. {_regenerate_hint()}'
    )


def _staleness_guard(source_root: Path, marketplace_root: Path) -> str | None:
    """Return a human-readable reason when source is missing/stale, else None.

    Sentinel-based staleness check:

    1. ``source_root`` must exist and contain at least one bundle (the
       same structural prerequisites as before).
    2. Every bundle present in ``marketplace_root`` must also be present
       in ``source_root`` (catches "added a bundle, forgot to re-emit").
    3. The sentinel file ``{source_root}/.emit-marker.json`` must exist
       and parse as JSON carrying a ``source_tree_fingerprint`` field.
    4. Recomputing the fingerprint against the worktree
       ``marketplace/bundles/`` (via the shared
       ``compute_source_tree_fingerprint`` helper imported from
       ``marketplace.targets.claude.source_fingerprint``) must match the
       sentinel's stored fingerprint. Mismatch -> source drifted since
       the last emit; refuse so callers regenerate before sync.
    5. File-level content-hash check (``_file_level_drift``): every file
       under ``target/claude/`` is compared against the per-file hash
       manifest the emitter recorded in the sentinel's ``file_hashes``
       field. A manifest entry whose live file is gone (missing) or hashes
       differently (diverged), or a live target file absent from the
       manifest (extra), is named in the refusal message. This supplements
       the single-sentinel fingerprint with per-file granularity so a
       localized target drift is reported by path rather than as an opaque
       digest mismatch. The manifest — not the raw ``marketplace/bundles/``
       tree — is the comparison baseline because ``target/claude/`` is
       transformed generator output, not a verbatim source mirror.
    """
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

    sentinel_path = source_root / EMIT_MARKER_FILENAME
    if not sentinel_path.is_file():
        return (
            f'staleness_guard: sentinel missing or unreadable at {sentinel_path} '
            f'— run finalize-step-deploy-target first. {_regenerate_hint()}'
        )
    try:
        sentinel = json.loads(sentinel_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            f'staleness_guard: sentinel missing or unreadable at {sentinel_path} '
            f'({exc}). {_regenerate_hint()}'
        )
    stored_fingerprint = sentinel.get('source_tree_fingerprint')
    if not isinstance(stored_fingerprint, str) or not stored_fingerprint:
        return (
            f'staleness_guard: sentinel at {sentinel_path} is missing '
            f'source_tree_fingerprint. {_regenerate_hint()}'
        )

    try:
        compute_source_tree_fingerprint, FingerprintError = _import_source_fingerprint()
    except ImportError as exc:
        return (
            f'staleness_guard: cannot import source_fingerprint helper ({exc}). '
            f'{_regenerate_hint()}'
        )

    repo_root = _resolve_repo_root_for_sentinel(source_root)
    try:
        live_fingerprint = compute_source_tree_fingerprint(repo_root)
    except FingerprintError as exc:
        return (
            f'staleness_guard: failed to recompute source fingerprint ({exc}). '
            f'{_regenerate_hint()}'
        )

    if live_fingerprint != stored_fingerprint:
        return (
            'staleness_guard: source tree changed since last emit — '
            f're-run finalize-step-deploy-target. {_regenerate_hint()}'
        )

    file_hashes = sentinel.get('file_hashes')
    if isinstance(file_hashes, dict):
        file_drift = _file_level_drift(source_root, file_hashes)
        if file_drift is not None:
            return file_drift

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


def _copy_dist_manifest(source_root: Path, cache_root: Path) -> bool:
    """Mirror the top-level ``dist-manifest.json`` into the plugin-cache root.

    The dist-branch versioning feature reads the installed version from the
    resolved ``base_path`` — which for the meta-project's own preflight and
    executor-regen calls is the plugin-cache root
    (``~/.claude/plugins/cache/plan-marshall``). The per-bundle rsync only
    mirrors ``{cache_root}/{bundle}/{version}/`` and never populates the
    ``base_path/dist-manifest.json`` slot that ``find_installed_manifest_path``
    resolves, so the manifest must be copied into the cache root explicitly.
    This mirrors the documented design — the manifest "rides into the plugin
    cache on install".

    The copy targets the cache ROOT, alongside the versioned
    ``{bundle}/{version}/`` directories; the per-bundle ``rsync --delete``
    never touches the root, so the copied sentinel is not clobbered.

    Best-effort: an absent source manifest is a no-op (matching the
    fresh-install/empty-sentinel discipline elsewhere) and a copy error is
    swallowed, so a missing or unwritable manifest never converts a
    successful sync into a failure. Returns ``True`` only when the manifest
    was copied, ``False`` otherwise.
    """
    source_manifest = source_root / DIST_MANIFEST_FILENAME
    if not source_manifest.is_file():
        return False
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        dest_manifest = cache_root / DIST_MANIFEST_FILENAME
        dest_manifest.unlink(missing_ok=True)
        shutil.copyfile(source_manifest, dest_manifest)
    except OSError:
        return False
    return True


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

    # Mirror the top-level dist-manifest.json into the cache root after a
    # successful (non-error) sync so the meta-project's own preflight can
    # resolve the installed version from base_path/dist-manifest.json.
    if status != 'error':
        _copy_dist_manifest(source_root, args.cache_root)

    sys.stdout.write(_emit_toon(status=status, synced=synced, failed=failed, summary_message=message))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
