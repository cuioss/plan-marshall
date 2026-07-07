#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI entry point for marketplace target generation.

Usage:
    python3 marketplace/targets/generate.py --target claude
    python3 marketplace/targets/generate.py --target claude --output target/claude
    python3 marketplace/targets/generate.py --target opencode --output target/opencode
    python3 marketplace/targets/generate.py --target all --output target

Exits 0 on success, 2 on any failure (unknown target, missing required
flag, generator-reported error).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import marketplace.targets` resolves.
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from marketplace.targets import TARGET_REGISTRY  # noqa: E402

DEFAULT_MARKETPLACE_DIR = Path(__file__).resolve().parent.parent / 'bundles'

EXIT_OK = 0
EXIT_ERROR = 2

# Fallback base version when marketplace.json is absent or carries no metadata.version.
_BASE_VERSION_FALLBACK = '0.1'
# Per-target dist-manifest filename emitted at each target output root.
_DIST_MANIFEST_FILENAME = 'dist-manifest.json'


def _build_parser() -> argparse.ArgumentParser:
    target_choices = sorted(TARGET_REGISTRY.keys()) + ['all']
    parser = argparse.ArgumentParser(
        prog='marketplace-targets-generate',
        description='Generate marketplace target output (claude verbatim mirror, opencode emitter).',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--target',
        required=True,
        choices=target_choices,
        help='Target to generate. Use "all" to run every registered target sequentially.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help=(
            'Output directory. Required for opencode (and for claude when emitting); '
            'optional for claude when running equality-check only.'
        ),
    )
    parser.add_argument(
        '--bundles',
        type=str,
        default=None,
        help='Comma-separated list of bundles to process. Default: all bundles.',
    )
    parser.add_argument(
        '--marketplace-dir',
        type=Path,
        default=DEFAULT_MARKETPLACE_DIR,
        help='Path to the marketplace/bundles/ directory. Default: marketplace/bundles/.',
    )
    parser.add_argument(
        '--version',
        type=str,
        default=None,
        help=(
            'Explicit deterministic version to stamp into the dist-manifest and the '
            'target-tree bundle plugin.json files. When omitted, the version is computed '
            'as {base}.{N} where base is read from marketplace/.claude-plugin/marketplace.json '
            'and N is the first-parent commit count (git rev-list --count --first-parent HEAD).'
        ),
    )
    parser.add_argument(
        '--previous-manifest',
        type=Path,
        default=None,
        help=(
            'Path to the previous dist-branch-tip dist-manifest.json. Its content '
            'fingerprints are diffed against the freshly-computed ones to derive each '
            'changed_at version (unchanged carries the previous value forward; changed '
            'advances to the current version). Absent (first publish) bootstraps every '
            'changed_at to the current version.'
        ),
    )
    return parser


def _parse_bundles(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    items = [b.strip() for b in raw.split(',') if b.strip()]
    if not items:
        return None
    return items


def _resolve_targets(name: str) -> list[str]:
    if name == 'all':
        return sorted(TARGET_REGISTRY.keys())
    return [name]


# ---------------------------------------------------------------------------
# Deterministic version + dist-manifest emission
# ---------------------------------------------------------------------------


def _git_output(args: list[str], cwd: Path) -> str | None:
    """Run ``git -C {cwd} {args}`` and return stripped stdout, or ``None`` on failure."""
    try:
        result = subprocess.run(
            ['git', '-C', str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _read_base_version(marketplace_root: Path) -> str:
    """Read the single base version from ``<marketplace_root>/.claude-plugin/marketplace.json``.

    ``marketplace.json`` is the sole source of record for the base version (e.g.
    ``0.1``); the deterministic ``0.1.N`` version is derived from it. Falls back to
    :data:`_BASE_VERSION_FALLBACK` when the manifest is absent or carries no
    ``metadata.version``.
    """
    manifest = marketplace_root / '.claude-plugin' / 'marketplace.json'
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return _BASE_VERSION_FALLBACK
    if not isinstance(data, dict):
        return _BASE_VERSION_FALLBACK
    metadata = data.get('metadata')
    version = metadata.get('version') if isinstance(metadata, dict) else None
    return version if isinstance(version, str) and version else _BASE_VERSION_FALLBACK


def _compute_commit_count(repo: Path) -> int:
    """Return the first-parent commit count (``git rev-list --count --first-parent HEAD``).

    Returns 0 when git is unavailable or the count cannot be parsed (e.g. a
    shallow checkout without ``fetch-depth: 0``).
    """
    out = _git_output(['rev-list', '--count', '--first-parent', 'HEAD'], repo)
    if out is None:
        return 0
    try:
        return int(out)
    except ValueError:
        return 0


def _compute_source_sha(repo: Path) -> str:
    """Return the source commit sha (``git rev-parse HEAD``), or ``unknown`` on failure."""
    return _git_output(['rev-parse', 'HEAD'], repo) or 'unknown'


def _resolve_version(explicit: str | None, base: str, repo: Path) -> str:
    """Resolve the deterministic version.

    An explicit ``--version`` value wins verbatim; otherwise the version is
    ``{base}.{N}`` where ``N`` is the first-parent commit count. Deterministic:
    the same commit yields the same version in CI and locally.
    """
    if explicit:
        return explicit
    return f'{base}.{_compute_commit_count(repo)}'


def _bootstrap_marketplace_imports(bundles_dir: Path) -> None:
    """Place every marketplace per-skill scripts directory on ``sys.path``.

    The fingerprint helpers — ``compute_executor_scripts_fingerprint`` (D1's
    ``generate_executor``) and ``compute_config_seed_fingerprint`` (D2's
    ``_config_defaults``) — plus their transitive cross-skill imports
    (``extension_discovery``, ``configurable_contract``, ``marketplace_bundles``,
    ``file_ops``, ...) resolve against the per-skill ``scripts`` directories the
    executor normally puts on ``PYTHONPATH``. This replicates that layout for a
    standalone ``generate.py`` run.
    """
    for scripts_dir in sorted(bundles_dir.glob('*/skills/*/scripts')):
        if not scripts_dir.is_dir():
            continue
        candidates = [scripts_dir]
        candidates.extend(
            child for child in scripts_dir.iterdir() if child.is_dir() and not child.name.startswith(('.', '__'))
        )
        for directory in candidates:
            entry = str(directory)
            if entry not in sys.path:
                sys.path.insert(0, entry)


def _compute_executor_scripts_fingerprint(bundles_dir: Path) -> str:
    """Compute the machine-portable executor script-set fingerprint (D1)."""
    _bootstrap_marketplace_imports(bundles_dir)
    from generate_executor import (  # noqa: PLC0415
        compute_executor_scripts_fingerprint,
        discover_scripts,
    )

    try:
        mappings = discover_scripts(bundles_dir)
    except SystemExit as exc:
        # ``discover_scripts`` signals a missing marketplace-inventory script
        # via ``sys.exit()`` (its CLI error protocol), which happens for a
        # partial/fixture marketplace that omits the pm-plugin-development
        # bundle. ``SystemExit`` is a ``BaseException``, so it would escape the
        # caller's best-effort ``except Exception`` degradation guard in
        # ``main()`` and abort the entire generation. Translate it into a
        # regular exception so the fingerprint degrades gracefully to empty.
        raise RuntimeError(f'executor script discovery unavailable: {exc}') from exc
    return compute_executor_scripts_fingerprint(mappings, bundles_dir)


def _compute_config_seed_fingerprint(bundles_dir: Path) -> str:
    """Compute the config-seed fingerprint over the default config (D2)."""
    _bootstrap_marketplace_imports(bundles_dir)
    from _config_defaults import compute_config_seed_fingerprint  # noqa: PLC0415

    return compute_config_seed_fingerprint()


def _load_previous_manifest(path: Path | None) -> dict | None:
    """Load the previous dist-manifest, or ``None`` when absent/unreadable (first publish)."""
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _derive_changed_at(
    current_version: str,
    current_fingerprint: str,
    previous: dict | None,
    fingerprint_key: str,
    changed_at_key: str,
) -> str:
    """Derive a ``changed_at`` version by diffing fingerprints against the previous manifest.

    - **First publish** (no previous manifest) bootstraps to the current version.
    - **Unchanged fingerprint** carries the previous ``changed_at`` forward
      (bootstrapping to the current version when the previous manifest lacked it).
    - **Changed fingerprint** advances to the current version.
    """
    if not previous:
        return current_version
    if previous.get(fingerprint_key) == current_fingerprint:
        carried = previous.get(changed_at_key)
        return carried if isinstance(carried, str) and carried else current_version
    return current_version


def _build_dist_manifest(
    version: str,
    source_sha: str,
    executor_fingerprint: str,
    config_fingerprint: str,
    previous: dict | None,
) -> dict:
    """Assemble the six-field dist-manifest with CI-carry-forward ``changed_at`` semantics."""
    return {
        'version': version,
        'source_sha': source_sha,
        'executor_scripts_fingerprint': executor_fingerprint,
        'executor_changed_at_version': _derive_changed_at(
            version,
            executor_fingerprint,
            previous,
            'executor_scripts_fingerprint',
            'executor_changed_at_version',
        ),
        'config_seed_fingerprint': config_fingerprint,
        'config_changed_at_version': _derive_changed_at(
            version,
            config_fingerprint,
            previous,
            'config_seed_fingerprint',
            'config_changed_at_version',
        ),
    }


def _override_bundle_plugin_versions(output_dir: Path, version: str) -> int:
    """Stamp ``version`` into every target-tree bundle ``plugin.json``.

    The source bundle ``plugin.json`` files carry the static base version; the
    published/generated tree carries the live per-landing ``0.1.N`` version. Only
    the ``version`` field is rewritten — every other key is preserved verbatim.

    Returns:
        The number of bundle ``plugin.json`` files rewritten.
    """
    count = 0
    for plugin_json in sorted(output_dir.glob('*/.claude-plugin/plugin.json')):
        try:
            data = json.loads(plugin_json.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        data['version'] = version
        plugin_json.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        count += 1
    return count


def _emit_dist_manifest(output_dir: Path, manifest: dict) -> None:
    """Write the dist-manifest JSON at the target output root."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / _DIST_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8'
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    marketplace_dir = args.marketplace_dir.resolve()
    if not marketplace_dir.exists():
        print(f'error: marketplace directory not found: {marketplace_dir}', file=sys.stderr)
        return EXIT_ERROR

    bundles = _parse_bundles(args.bundles)
    target_names = _resolve_targets(args.target)
    output_dir = args.output.resolve() if args.output is not None else None

    # Deterministic version + dist-manifest are derived from source once and are
    # identical across every emitted target tree. Fingerprints (and therefore the
    # manifest) are only needed when emitting output; a pure equality-check run
    # (no --output) skips the heavier fingerprint computation entirely.
    marketplace_root = marketplace_dir.parent
    base_version = _read_base_version(marketplace_root)
    version = _resolve_version(args.version, base_version, marketplace_root)
    source_sha = _compute_source_sha(marketplace_root)
    previous_manifest = _load_previous_manifest(args.previous_manifest)

    manifest: dict | None = None
    if output_dir is not None:
        try:
            executor_fingerprint = _compute_executor_scripts_fingerprint(marketplace_dir)
        except Exception as exc:  # noqa: BLE001
            print(f'warning: could not compute executor scripts fingerprint: {exc}', file=sys.stderr)
            executor_fingerprint = ''
        try:
            config_fingerprint = _compute_config_seed_fingerprint(marketplace_dir)
        except Exception as exc:  # noqa: BLE001
            print(f'warning: could not compute config seed fingerprint: {exc}', file=sys.stderr)
            config_fingerprint = ''
        manifest = _build_dist_manifest(
            version, source_sha, executor_fingerprint, config_fingerprint, previous_manifest
        )

    overall_ok = True
    for target_name in target_names:
        target_cls = TARGET_REGISTRY.get(target_name)
        if target_cls is None:
            print(f'error: unknown target {target_name!r}', file=sys.stderr)
            return EXIT_ERROR

        target = target_cls()
        per_target_output = output_dir / target_name if (output_dir is not None and args.target == 'all') else output_dir

        try:
            generated = target.generate(marketplace_dir, per_target_output, bundles=bundles)
        except NotImplementedError as exc:
            print(f'error: target {target_name!r} not yet implemented: {exc}', file=sys.stderr)
            overall_ok = False
            continue
        except Exception as exc:  # noqa: BLE001
            print(f'error: target {target_name!r} failed: {exc}', file=sys.stderr)
            overall_ok = False
            continue

        print(f'{target_name}: produced {len(generated)} entries')

        # Stamp the deterministic version into every target-tree bundle plugin.json
        # and emit the per-target dist-manifest.json at the output root, THEN run
        # the target's finalize hook so any sentinel it writes summarizes the
        # final published tree (including the version-overridden plugin.json
        # files and the just-emitted dist-manifest.json) rather than a stale
        # pre-mutation snapshot.
        if per_target_output is not None and manifest is not None:
            overridden = _override_bundle_plugin_versions(per_target_output, version)
            _emit_dist_manifest(per_target_output, manifest)
            target.finalize(per_target_output, marketplace_dir)
            print(
                f'{target_name}: stamped version {version} into {overridden} bundle plugin.json; '
                f'emitted {_DIST_MANIFEST_FILENAME}'
            )

    return EXIT_OK if overall_ok else EXIT_ERROR


if __name__ == '__main__':
    sys.exit(main())
