# SPDX-License-Identifier: FSL-1.1-ALv2
"""Live content-drift check engine for the Claude target.

Regenerates the entire Claude target tree into a throwaway temporary
directory via the existing emit path (``ClaudeTarget.generate`` in emit
mode) and diffs every regenerated ``*.md`` file byte-for-byte against the
same-relative-path file under the on-disk ``target/claude/`` tree. This
catches per-file markdown content drift that the manifest-only equality
gate (``equality_check.run_equality_check``) cannot see: the equality
engine compares the regenerated ``plugin.json`` / ``marketplace.json``
manifests, but it never inspects the ``*.md`` bodies that the emitter
mirrors verbatim (skills, standards, commands) or transforms (agent
canonicals and per-level variants). A skill body edited in
``marketplace/bundles/`` but not re-emitted to ``target/claude/`` — or an
emitted ``.md`` mutated directly under ``target/claude/`` — drifts silently
past the manifest check; this engine surfaces it by name.

The check is **regen-first**: it never trusts the on-disk
``target/claude/`` content. It regenerates a fresh tree from the current
``marketplace/bundles/`` sources into a ``tempfile.TemporaryDirectory()``
and treats that fresh emit as the source of truth, so a source ``.md``
edit that was never re-emitted is caught exactly as an on-disk mutation is.
The real ``target/claude/`` directory is NEVER written by this engine — the
emit always targets the temp dir.

Scope is ``*.md`` files ONLY. Non-``.md`` files are either manifests
(``.claude-plugin/*.json`` — already owned by
``equality_check.run_equality_check``) or the ``.emit-marker.json``
sentinel (build metadata, not a content artifact); both are excluded from
the walk. The fix in every drift case is the documented one: re-run the
Claude target's emit mode so ``target/claude/`` is regenerated from the
current sources::

    python3 marketplace/targets/generate.py --target claude --output target/claude

Source files under ``marketplace/bundles/`` are canonical and MUST NOT be
edited to satisfy the gate — only the build artifact under
``target/claude/`` is regenerated.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field as _dc_field
from pathlib import Path

from marketplace.targets.claude.emitter import iter_bundle_dirs
from marketplace.targets.claude.target import EMIT_MARKER_FILENAME, ClaudeTarget


@dataclass
class ContentDriftResult:
    """Aggregate outcome of a content-drift check.

    Mirrors the shape of ``equality_check.EqualityResult``: a boolean
    verdict, the path lists describing each drift category, and a
    human-readable ``summary`` directing the caller to re-run the emit
    step. All path lists hold ``target_dir``-relative POSIX paths.
    """

    passed: bool
    drifted_files: list[str] = _dc_field(default_factory=list)
    missing_in_target: list[str] = _dc_field(default_factory=list)
    orphan_in_target: list[str] = _dc_field(default_factory=list)
    summary: str = ''


def _is_content_markdown(rel: Path) -> bool:
    """Return True when ``rel`` is an in-scope content ``.md`` file.

    Excludes the ``.emit-marker.json`` sentinel and anything under a
    ``.claude-plugin/`` directory (the regenerated manifests, owned by the
    equality engine). Only ``.md`` files outside ``.claude-plugin/`` are
    in scope.
    """
    if rel.suffix != '.md':
        return False
    if rel.name == EMIT_MARKER_FILENAME:
        return False
    return '.claude-plugin' not in rel.parts


def _collect_markdown(root: Path) -> dict[str, bytes]:
    """Map each in-scope ``*.md`` file under ``root`` to its bytes.

    Keys are ``root``-relative POSIX paths. Symlinks and non-``.md`` files
    are skipped; the ``.emit-marker.json`` sentinel and
    ``.claude-plugin/*.json`` manifests are excluded via
    ``_is_content_markdown``.
    """
    collected: dict[str, bytes] = {}
    try:
        paths = sorted(root.rglob('*'))
    except OSError:
        paths = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        if not _is_content_markdown(rel):
            continue
        try:
            collected[rel.as_posix()] = path.read_bytes()
        except OSError:
            continue
    return collected


def run_content_drift_check(target_dir: Path, marketplace_dir: Path) -> ContentDriftResult:
    """Run the regen-first ``.md`` content-drift check.

    ``target_dir`` is the on-disk emitted Claude target root (e.g.
    ``target/claude``). ``marketplace_dir`` is the bundle root the emitter
    walks (``marketplace/bundles``). The engine regenerates a fresh target
    tree from ``marketplace_dir`` into a temporary directory via
    ``ClaudeTarget.generate`` in emit mode — the real ``target_dir`` is
    never written — then diffs every regenerated ``*.md`` file against the
    same-relative-path file under ``target_dir``.

    Three drift categories are reported, all as ``target_dir``-relative
    POSIX paths:

    * ``drifted_files`` — an ``.md`` file present in both trees whose bytes
      differ.
    * ``missing_in_target`` — an ``.md`` file the fresh emit produced that
      is absent under ``target_dir`` (the on-disk tree is missing emitted
      content).
    * ``orphan_in_target`` — an ``.md`` file present under ``target_dir``
      that a fresh emit does not produce (a stale leftover whose source no
      longer exists).

    When ``target_dir`` does not exist, the result fails with a
    "run emit mode first" diagnostic rather than crashing.
    """
    bundle_dirs = list(iter_bundle_dirs(marketplace_dir, None))
    bundle_names = [b.name for b in bundle_dirs]

    if not target_dir.is_dir():
        summary = (
            f"target/claude not generated at {target_dir} — "
            "run 'python3 marketplace/targets/generate.py --target claude --output target/claude' first"
        )
        return ContentDriftResult(passed=False, summary=summary)

    with tempfile.TemporaryDirectory(prefix='claude-content-drift-') as tmp:
        regen_dir = Path(tmp)
        ClaudeTarget().generate(marketplace_dir, regen_dir, bundle_names or None)
        regenerated = _collect_markdown(regen_dir)
        on_disk = _collect_markdown(target_dir)

    drifted_files: list[str] = []
    missing_in_target: list[str] = []
    for rel, regen_bytes in regenerated.items():
        if rel not in on_disk:
            missing_in_target.append(rel)
        elif on_disk[rel] != regen_bytes:
            drifted_files.append(rel)

    orphan_in_target = [rel for rel in on_disk if rel not in regenerated]

    drifted_files.sort()
    missing_in_target.sort()
    orphan_in_target.sort()

    passed = not drifted_files and not missing_in_target and not orphan_in_target
    if passed:
        summary = f'content-drift check passed: {len(regenerated)} markdown files match'
    else:
        parts: list[str] = []
        if drifted_files:
            parts.append(f'{len(drifted_files)} drifted ({", ".join(drifted_files)})')
        if missing_in_target:
            parts.append(f'{len(missing_in_target)} missing in target ({", ".join(missing_in_target)})')
        if orphan_in_target:
            parts.append(f'{len(orphan_in_target)} orphan in target ({", ".join(orphan_in_target)})')
        summary = (
            f'content-drift check failed: {"; ".join(parts)}. '
            "Re-run 'python3 marketplace/targets/generate.py --target claude --output target/claude' "
            "to regenerate target/claude/ from current sources. "
            "Do NOT edit the source .md files under marketplace/bundles/ — they are canonical."
        )

    return ContentDriftResult(
        passed=passed,
        drifted_files=drifted_files,
        missing_in_target=missing_in_target,
        orphan_in_target=orphan_in_target,
        summary=summary,
    )
