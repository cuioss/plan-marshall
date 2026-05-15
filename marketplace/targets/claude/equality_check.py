"""Equality-check engine for the Claude target.

Regenerates ``plugin.json`` for each bundle in-memory via
``plugin_json_gen.build_plugin_json`` and diffs the result against the
emitted ``target/claude/{bundle}/.claude-plugin/plugin.json``. Also
regenerates the top-level ``marketplace.json`` via
``marketplace_json_gen.build_marketplace_json`` and diffs it against the
emitted ``target/claude/.claude-plugin/marketplace.json``. The build
artifacts under ``target/claude/`` are the source of truth for the
equality gate; the bundle's committed ``.claude-plugin/plugin.json`` is
no longer consulted by this engine. Powers both the standalone validation
mode (``generate.py --target claude`` without ``--output``) and the
post-emit gate that runs immediately after a fresh emit.

Variant-aware drift detection: agents declaring the
dynamic-level-executor extension point expand into multiple
``plugin.json`` entries (canonical + per-emitted-level). The diff
naturally surfaces drift when (a) the canonical's ``levels:`` whitelist
changes without ``plugin.json`` regeneration, (b) the build-time
``xxhigh`` guard suppresses a previously emitted variant, or (c) a new
canonical adds the ``implements:`` declaration but the emitted
``plugin.json`` still lists only the no-suffix entry. Marketplace-json
drift surfaces when (d) a new plugin is added to or removed from the
source marketplace manifest without re-emitting, or (e) a plugin's
``source`` path or description changes. Orphan-file drift surfaces
when (f) an ``agents/`` or ``commands/`` file physically present in
``target/claude/{bundle}/`` is not declared in the emitted
``plugin.json`` — for instance, when a source canonical was deleted but
its previously-emitted variant files lingered in the target tree. The
fix in every case is the documented one: re-run the Claude target's
emit mode so ``target/claude/`` is regenerated from the current
sources (the emitter wipes each bundle's destination directory before
copying, so orphans are eliminated by a fresh emit). Source
``plugin.json`` files under
``marketplace/bundles/{bundle}/.claude-plugin/`` are canonical-only and
MUST NOT be edited to satisfy the gate — only the build artifact under
``target/claude/`` is consulted.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from marketplace.targets.claude.marketplace_json_gen import build_marketplace_json
from marketplace.targets.claude.plugin_json_gen import build_plugin_json


@dataclass
class BundleDiff:
    """Per-bundle drift summary."""

    bundle: str
    field: str
    committed: list[str] | None
    generated: list[str] | None
    only_in_committed: list[str] = field(default_factory=list)
    only_in_generated: list[str] = field(default_factory=list)


@dataclass
class EqualityResult:
    """Aggregate outcome of an equality check."""

    passed: bool
    diffs: list[BundleDiff]
    summary: str
    missing_target_bundles: list[str] = field(default_factory=list)
    marketplace_json_drift: bool = False


def _emitted_plugin_json_path(target_dir: Path, bundle_name: str) -> Path:
    return target_dir / bundle_name / '.claude-plugin' / 'plugin.json'


def _emitted_marketplace_json_path(target_dir: Path) -> Path:
    return target_dir / '.claude-plugin' / 'marketplace.json'


def _check_marketplace_json(target_dir: Path, marketplace_src: Path) -> tuple[bool, str | None]:
    """Diff the emitted ``target_dir/.claude-plugin/marketplace.json`` against a
    fresh regeneration from ``marketplace_src``.

    Returns ``(drifted, diagnostic)``. ``drifted`` is True if the emitted
    file is missing OR its content differs from the regenerated content.
    """
    emitted = _emitted_marketplace_json_path(target_dir)
    if not emitted.exists():
        return True, f'target/claude/.claude-plugin/marketplace.json missing at {emitted}'
    try:
        committed = json.loads(emitted.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        return True, f'target/claude/.claude-plugin/marketplace.json is not valid JSON: {exc}'
    generated = build_marketplace_json(marketplace_src)
    if committed == generated:
        return False, None
    return True, 'target/claude/.claude-plugin/marketplace.json differs from regenerated content'


def _read_emitted_plugin_json(bundle_dir: Path, target_dir: Path) -> dict:
    """Read the emitted ``plugin.json`` for ``bundle_dir`` from ``target_dir``.

    The build artifact under ``target/claude/{bundle}/.claude-plugin/`` is
    the equality-gate source of truth; the bundle's committed
    ``.claude-plugin/plugin.json`` is canonical-only and not consulted
    here.
    """
    plugin_json = _emitted_plugin_json_path(target_dir, bundle_dir.name)
    return json.loads(plugin_json.read_text(encoding='utf-8'))


def _diff_array(bundle: str, field_name: str, committed: list[str], generated: list[str]) -> BundleDiff | None:
    committed_set = set(committed)
    generated_set = set(generated)
    if committed_set == generated_set and committed == generated:
        return None
    return BundleDiff(
        bundle=bundle,
        field=field_name,
        committed=committed,
        generated=generated,
        only_in_committed=sorted(committed_set - generated_set),
        only_in_generated=sorted(generated_set - committed_set),
    )


def _on_disk_entries(target_bundle_dir: Path, subdir: str) -> list[str]:
    """Return ``./{subdir}/{name}`` entries for every .md file present in
    ``target_bundle_dir/{subdir}/``. Used to detect orphan files left over
    from prior emits whose source canonical no longer exists.
    """
    folder = target_bundle_dir / subdir
    if not folder.is_dir():
        return []
    return sorted(
        f'./{subdir}/{p.name}'
        for p in folder.iterdir()
        if p.is_file() and p.suffix == '.md' and not p.name.startswith('.')
    )


def check_bundle(bundle_dir: Path, target_dir: Path) -> list[BundleDiff]:
    """Compare the regenerated ``plugin.json`` against the emitted artifact.

    The emitted file lives at
    ``target_dir/{bundle_dir.name}/.claude-plugin/plugin.json``. Callers
    are responsible for ensuring the emitted file exists; missing files
    are surfaced by ``run_equality_check`` as a structured diagnostic
    rather than being raised here.

    The check has two layers:

    1. Manifest drift: the emitted ``plugin.json`` arrays (``agents``,
       ``commands``, ``skills``) must equal the regenerated arrays.
    2. Orphan files: every ``agents/*.md`` and ``commands/*.md`` file
       physically present under ``target_dir/{bundle}/`` must appear in
       the emitted ``plugin.json``'s declared list for its respective
       field. Files on disk that are not declared (e.g. variants for a
       source canonical that has since been deleted) surface as drift
       entries with ``only_in_committed`` populated. This catches the
       "stale leftover from a previous emit" failure mode that the
       manifest-only check cannot see — the manifest correctly lists
       only what source contains, but the on-disk artifact set has
       drifted past it.
    """
    committed = _read_emitted_plugin_json(bundle_dir, target_dir)
    generated = build_plugin_json(bundle_dir)
    target_bundle_dir = target_dir / bundle_dir.name
    diffs: list[BundleDiff] = []
    for field_name in ('agents', 'commands', 'skills'):
        committed_arr = list(committed.get(field_name, []) or [])
        generated_arr = list(generated.get(field_name, []) or [])
        diff = _diff_array(bundle_dir.name, field_name, committed_arr, generated_arr)
        if diff is not None:
            diffs.append(diff)

    for subdir in ('agents', 'commands'):
        declared = set(committed.get(subdir, []) or [])
        on_disk = set(_on_disk_entries(target_bundle_dir, subdir))
        orphans = sorted(on_disk - declared)
        if not orphans:
            continue
        diffs.append(
            BundleDiff(
                bundle=bundle_dir.name,
                field=f'{subdir}-orphans',
                committed=sorted(on_disk),
                generated=sorted(declared),
                only_in_committed=orphans,
                only_in_generated=[],
            )
        )

    return diffs


def run_equality_check(target_dir: Path, bundle_dirs: Iterable[Path]) -> EqualityResult:
    """Run the equality check across the supplied bundle directories.

    ``target_dir`` is the root of the emitted Claude target output (e.g.
    ``target/claude``). For each bundle, the engine reads
    ``target_dir/{bundle}/.claude-plugin/plugin.json`` and compares it
    against the regenerated content. The engine also diffs
    ``target_dir/.claude-plugin/marketplace.json`` against a fresh
    regeneration from the source marketplace manifest, since the top-level
    marketplace.json must stay in sync with the source for the marketplace
    to remain registerable. When ``target_dir`` itself, a per-bundle
    emitted plugin.json, or the top-level marketplace.json is missing or
    drifts, the engine returns a failing ``EqualityResult`` whose
    ``summary`` directs the caller to re-run the emit step rather than
    crashing.
    """
    bundles_list = list(bundle_dirs)
    bundle_count = len(bundles_list)

    if not target_dir.exists():
        summary = (
            f"target/claude not generated at {target_dir} — "
            "run 'python3 marketplace/targets/generate.py --target claude --output target/claude' first"
        )
        return EqualityResult(
            passed=False,
            diffs=[],
            summary=summary,
            missing_target_bundles=[b.name for b in bundles_list],
        )

    all_diffs: list[BundleDiff] = []
    missing: list[str] = []
    for bundle_dir in bundles_list:
        emitted_path = _emitted_plugin_json_path(target_dir, bundle_dir.name)
        if not emitted_path.exists():
            missing.append(bundle_dir.name)
            continue
        all_diffs.extend(check_bundle(bundle_dir, target_dir))

    if missing:
        joined = ', '.join(sorted(missing))
        summary = (
            f"target/claude/{{bundle}}/.claude-plugin/plugin.json missing for: {joined} — "
            "run 'python3 marketplace/targets/generate.py --target claude --output target/claude' first"
        )
        return EqualityResult(
            passed=False,
            diffs=all_diffs,
            summary=summary,
            missing_target_bundles=sorted(missing),
        )

    # Compare the top-level marketplace.json. Bundles are sourced from
    # ``marketplace/bundles/<name>``; the source marketplace root is the
    # parent of any bundle's parent directory.
    marketplace_drift = False
    marketplace_diagnostic: str | None = None
    if bundles_list:
        marketplace_src = bundles_list[0].parent.parent
        marketplace_drift, marketplace_diagnostic = _check_marketplace_json(target_dir, marketplace_src)

    passed = not all_diffs and not marketplace_drift
    if passed:
        summary = f'equality check passed: {bundle_count} bundles match'
    elif marketplace_drift and not all_diffs:
        summary = (
            f'equality check failed: {marketplace_diagnostic}. '
            "Re-run 'python3 marketplace/targets/generate.py --target claude --output target/claude' "
            "to regenerate target/claude/ from current sources."
        )
    else:
        bundles_with_drift = sorted({d.bundle for d in all_diffs})
        suffix = ''
        if marketplace_drift:
            suffix = f' Also: {marketplace_diagnostic}.'
        summary = (
            f'equality check failed: {len(all_diffs)} drift entries '
            f'across {len(bundles_with_drift)}/{bundle_count} bundles '
            f'({", ".join(bundles_with_drift)}).{suffix} '
            "Re-run 'python3 marketplace/targets/generate.py --target claude --output target/claude' "
            "to regenerate target/claude/ from current sources. "
            "Do NOT edit the source plugin.json files — they are canonical-only."
        )
    return EqualityResult(
        passed=passed,
        diffs=all_diffs,
        summary=summary,
        marketplace_json_drift=marketplace_drift,
    )
