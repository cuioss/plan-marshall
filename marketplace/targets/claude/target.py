# SPDX-License-Identifier: FSL-1.1-ALv2
"""ClaudeTarget — verbatim source mirror + always-generate plugin.json.

The Claude target operates in two modes selected by whether the caller
provides ``--output``:

* **Emit mode (`--output` provided)** — walk every bundle under
  ``marketplace/bundles/`` and copy its content byte-for-byte into
  ``{output}/{bundle}/`` *except* for ``.claude-plugin/plugin.json``,
  which is regenerated deterministically from the bundle's source
  frontmatter. Immediately after emit, the regenerated content is
  diffed against the just-written ``{output}/{bundle}/.claude-plugin/plugin.json``
  so callers see drift as part of the same TOON return. Equality
  failure raises ``RuntimeError`` so the CLI surfaces a non-zero exit.

* **Validate mode (`--output` omitted)** — run the equality check only.
  The engine reads ``target/claude/{bundle}/.claude-plugin/plugin.json``
  (relative to the project root) and diffs it against a fresh in-memory
  regeneration. When ``target/claude/`` is absent, the result includes
  a structured "run emit mode first" diagnostic.

The TOON return contains ``status``, ``emitted_count``,
``plugin_json_diff_count``, and ``equality_check_result``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from marketplace.targets.base import TargetBase
from marketplace.targets.claude.emitter import emit_bundle_verbatim, iter_bundle_dirs
from marketplace.targets.claude.equality_check import run_equality_check
from marketplace.targets.claude.marketplace_json_gen import generate_marketplace_json
from marketplace.targets.claude.plugin_json_gen import generate_plugin_json
from marketplace.targets.claude.source_fingerprint import (
    FingerprintError,
    compute_source_tree_fingerprint,
    hash_objects,
)

# Sentinel file written at the end of every successful emit. The
# project-local ``sync-plugin-cache`` skill reads it to decide whether
# ``target/claude/`` is fresh relative to the worktree source tree.
EMIT_MARKER_FILENAME = '.emit-marker.json'

# Default ``target/claude/`` location used by validate mode when no
# ``--output`` is provided. Resolved against the project root at import
# time so test runners using ``pytest`` from the repository root see the
# same path.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VALIDATE_TARGET_DIR = _PROJECT_ROOT / 'target' / 'claude'


def _compute_emit_file_hashes(output_dir: Path) -> dict[str, str]:
    """Compute a per-file git blob-hash manifest of the emitted tree.

    Walks every regular (non-symlink) file under ``output_dir`` — the
    emitted ``target/claude/`` tree — and returns a mapping of
    ``output_dir``-relative POSIX path to the file's git blob SHA. The
    sentinel file (``.emit-marker.json``) is excluded because the
    manifest is written INTO that file, so it cannot enumerate itself.

    Hashing delegates to the shared ``hash_objects`` primitive
    (``git hash-object --stdin-paths``) so the emit-time manifest and the
    sync-time staleness guard compute byte-identical SHAs. The files are
    passed to ``git hash-object`` by ABSOLUTE path: ``git hash-object``
    resolves a relative pathspec against the enclosing repo's worktree
    root, not against the ``-C`` directory, so a relative path breaks when
    ``output_dir`` happens to live inside a git repo (which the real
    ``target/claude/`` always does). Absolute paths sidestep that
    resolution entirely and work whether or not ``output_dir`` is inside a
    work tree. ``git hash-object`` reads arbitrary worktree bytes
    regardless of whether the paths are tracked, so it works on the
    gitignored ``target/claude/`` tree and on synthetic non-repo fixtures
    alike. The returned mapping is keyed by ``output_dir``-relative POSIX
    path. Returns an empty mapping when ``output_dir`` holds no eligible
    files.
    """
    rel_paths: list[str] = []
    abs_paths: list[str] = []
    for path in sorted(output_dir.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(output_dir).as_posix()
        if rel == EMIT_MARKER_FILENAME:
            continue
        rel_paths.append(rel)
        abs_paths.append(str(path.resolve()))
    if not rel_paths:
        return {}
    shas = hash_objects(output_dir, abs_paths)
    return dict(zip(rel_paths, shas, strict=True))


class ClaudeTarget(TargetBase):
    """Dual-mode Claude build target."""

    @property
    def name(self) -> str:
        return 'claude'

    def supports_agents(self) -> bool:
        return True

    def supports_commands(self) -> bool:
        return True

    @property
    def config_dir(self) -> Path:
        return Path(__file__).resolve().parent

    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path | None,
        bundles: list[str] | None = None,
    ) -> list[Path]:
        bundle_dirs = list(iter_bundle_dirs(marketplace_dir, bundles))
        emitted: list[Path] = []

        # Validate mode: equality check only. Read from the canonical
        # ``target/claude/`` location relative to the project root.
        if output_dir is None:
            equality = run_equality_check(DEFAULT_VALIDATE_TARGET_DIR, bundle_dirs)
            self._last_run = {
                'status': 'success' if equality.passed else 'error',
                'emitted_count': 0,
                'plugin_json_diff_count': len(equality.diffs),
                'equality_check_result': equality,
            }
            if not equality.passed:
                # Surface the drift summary on stderr-style return.
                raise RuntimeError(equality.summary)
            return emitted

        # Emit mode: verbatim mirror + plugin.json regeneration.
        output_dir.mkdir(parents=True, exist_ok=True)

        for bundle_dir in bundle_dirs:
            mirrored = emit_bundle_verbatim(bundle_dir, output_dir)
            emitted.extend(mirrored)

            generated = generate_plugin_json(bundle_dir)
            target_plugin_json = output_dir / bundle_dir.name / '.claude-plugin' / 'plugin.json'
            target_plugin_json.parent.mkdir(parents=True, exist_ok=True)
            target_plugin_json.write_text(generated, encoding='utf-8')
            emitted.append(target_plugin_json)

        # Top-level marketplace.json so target/claude/ is registerable as a
        # Claude Code marketplace. plugins[].source paths are rewritten from
        # the source ./bundles/{name} layout to the flat ./{name} target layout.
        marketplace_src = marketplace_dir.parent
        target_marketplace_json = output_dir / '.claude-plugin' / 'marketplace.json'
        target_marketplace_json.parent.mkdir(parents=True, exist_ok=True)
        target_marketplace_json.write_text(
            generate_marketplace_json(marketplace_src), encoding='utf-8'
        )
        emitted.append(target_marketplace_json)

        # Run equality check after emit so emit_count reflects bytes written
        # AND so the equality engine has fresh artifacts to compare against.
        equality = run_equality_check(output_dir, bundle_dirs)

        self._last_run = {
            'status': 'success' if equality.passed else 'error',
            'emitted_count': len(emitted),
            'plugin_json_diff_count': len(equality.diffs),
            'equality_check_result': equality,
        }

        if not equality.passed:
            # Mirror validate mode: equality failure must propagate so the
            # CLI returns EXIT_ERROR rather than a silent emit-and-pass. The
            # sentinel is NOT written on this path (``finalize`` is never
            # reached), so the sync staleness guard refuses on the next sync.
            raise RuntimeError(equality.summary)

        # Write the emit sentinel over the just-emitted tree so a DIRECT
        # ``generate`` caller (no CLI post-processing) still gets a complete,
        # self-describing marker. In the full CLI path ``finalize`` REWRITES it
        # AFTER the generic post-emit mutations (the deterministic version
        # override of every bundle ``plugin.json`` and the ``dist-manifest.json``
        # emission) so the persisted marker's ``file_hashes`` covers those
        # post-emit artifacts. The equality gate above guards both writes: a
        # failure raises before either runs, leaving no sentinel and so the
        # sync staleness guard correctly refuses on the next sync.
        self._write_emit_marker(output_dir, marketplace_dir)
        return emitted

    def finalize(self, output_dir: Path, marketplace_dir: Path) -> list[Path]:
        """Rewrite the emit sentinel over the FINAL published tree.

        Invoked by the CLI (``generate.py``) after the generic post-emit tree
        mutations — the deterministic ``0.1.N`` version override of every
        bundle ``plugin.json`` and the ``dist-manifest.json`` emission at the
        output root — have been applied. :meth:`generate` already wrote a
        sentinel over the pre-mutation tree (so direct ``generate`` callers get
        one); this rewrite supersedes it so the persisted marker's
        ``file_hashes`` covers the version-overridden ``plugin.json`` files and
        the emitted ``dist-manifest.json``. If the equality gate in
        :meth:`generate` raised, the CLI never reaches this hook (and no
        sentinel was written at all), so the sync staleness guard correctly
        refuses on the next sync.
        """
        return [self._write_emit_marker(output_dir, marketplace_dir)]

    def _write_emit_marker(self, output_dir: Path, marketplace_dir: Path) -> Path:
        """Write the emit sentinel summarizing the emitted tree at ``output_dir``.

        The source-tree fingerprint is computed against the WORKTREE source
        tree under ``marketplace/bundles/`` via git's own ``hash-object``
        primitive so uncommitted edits change the digest. ``repo_root`` is the
        grandparent of ``marketplace_dir`` (``marketplace_dir`` points at
        ``marketplace/bundles/``, so the project root that contains
        ``marketplace/`` is two levels up).

        When ``marketplace_dir`` is not inside a git work tree (ad-hoc
        fixtures, tests with synthetic marketplaces), the fingerprint cannot be
        computed deterministically. The sentinel is written with
        ``source_tree_fingerprint: null`` so its presence is honest about the
        missing fingerprint — the sync guard's missing-fingerprint branch then
        refuses, which is the correct behavior for a non-repo emit.
        """
        repo_root = marketplace_dir.parent.parent
        fingerprint: str | None
        try:
            fingerprint = compute_source_tree_fingerprint(repo_root)
        except FingerprintError:
            fingerprint = None

        # Per-file hash manifest of whatever tree currently lives at
        # ``output_dir``. ``_compute_emit_file_hashes`` excludes the sentinel
        # filename unconditionally. On the full CLI path (the ``finalize``
        # caller) that tree already carries the version-overridden ``plugin.json``
        # files and the emitted ``dist-manifest.json`` — both written by the CLI
        # before ``finalize`` runs — so the sync staleness guard can diagnose a
        # downstream mutation, deletion, or stray extra file by path without
        # re-deriving a source counterpart (``target/claude/`` is transformed
        # generator output, not a raw mirror of ``marketplace/bundles/``). On the
        # direct-``generate`` path those post-emit artifacts do not exist yet and
        # the manifest covers only the mirrored tree. A hashing fault degrades to
        # an empty manifest rather than aborting the emit.
        try:
            file_hashes = _compute_emit_file_hashes(output_dir)
        except FingerprintError:
            file_hashes = {}

        marker_payload: dict[str, object] = {
            'emit_completed_at': datetime.now(timezone.utc).isoformat(),
            'source_tree_fingerprint': fingerprint,
            'file_hashes': file_hashes,
        }
        marker_path = output_dir / EMIT_MARKER_FILENAME
        marker_path.write_text(
            json.dumps(marker_payload, indent=2) + '\n', encoding='utf-8'
        )
        return marker_path
