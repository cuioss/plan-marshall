"""Equality-check engine for the Claude target.

Regenerates ``plugin.json`` for each bundle in-memory via
``plugin_json_gen.build_plugin_json`` and diffs the result against the
emitted ``target/claude/{bundle}/.claude-plugin/plugin.json``. The build
artifact under ``target/claude/`` is the source of truth for the equality
gate; the bundle's committed ``.claude-plugin/plugin.json`` is no longer
consulted by this engine. Powers both the standalone validation mode
(``generate.py --target claude`` without ``--output``) and the post-emit
gate that runs immediately after a fresh emit.

Variant-aware drift detection: agents declaring the
dynamic-level-executor extension point expand into multiple
``plugin.json`` entries (canonical + per-emitted-level). The diff
naturally surfaces drift when (a) the canonical's ``levels:`` whitelist
changes without ``plugin.json`` regeneration, (b) the build-time
``xxhigh`` guard suppresses a previously emitted variant, or (c) a new
canonical adds the ``implements:`` declaration but the emitted
``plugin.json`` still lists only the no-suffix entry. The fix in every
case is the documented one: regenerate via the Claude target into
``target/claude/`` and copy the regenerated ``plugin.json`` over the
committed file.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

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


def _emitted_plugin_json_path(target_dir: Path, bundle_name: str) -> Path:
    return target_dir / bundle_name / '.claude-plugin' / 'plugin.json'


def _committed_plugin_json(bundle_dir: Path, target_dir: Path) -> dict:
    """Read the emitted ``plugin.json`` for ``bundle_dir`` from ``target_dir``.

    The function name is preserved for symmetry with the API consumed by
    ``check_bundle``; the source of truth changed (it now reads the
    artifact emitted into ``target/claude/{bundle}/.claude-plugin/``).
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


def check_bundle(bundle_dir: Path, target_dir: Path) -> list[BundleDiff]:
    """Compare the regenerated ``plugin.json`` against the emitted artifact.

    The emitted file lives at
    ``target_dir/{bundle_dir.name}/.claude-plugin/plugin.json``. Callers
    are responsible for ensuring the emitted file exists; missing files
    are surfaced by ``run_equality_check`` as a structured diagnostic
    rather than being raised here.
    """
    committed = _committed_plugin_json(bundle_dir, target_dir)
    generated = build_plugin_json(bundle_dir)
    diffs: list[BundleDiff] = []
    for field_name in ('agents', 'commands', 'skills'):
        committed_arr = list(committed.get(field_name, []) or [])
        generated_arr = list(generated.get(field_name, []) or [])
        diff = _diff_array(bundle_dir.name, field_name, committed_arr, generated_arr)
        if diff is not None:
            diffs.append(diff)
    return diffs


def run_equality_check(target_dir: Path, bundle_dirs: Iterable[Path]) -> EqualityResult:
    """Run the equality check across the supplied bundle directories.

    ``target_dir`` is the root of the emitted Claude target output (e.g.
    ``target/claude``). For each bundle, the engine reads
    ``target_dir/{bundle}/.claude-plugin/plugin.json`` and compares it
    against the regenerated content. When ``target_dir`` itself or a
    per-bundle emitted plugin.json is missing, the engine returns a
    failing ``EqualityResult`` whose ``summary`` directs the caller to
    re-run the emit step rather than crashing.
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

    passed = not all_diffs
    if passed:
        summary = f'equality check passed: {bundle_count} bundles match'
    else:
        bundles_with_drift = sorted({d.bundle for d in all_diffs})
        summary = (
            f'equality check failed: {len(all_diffs)} drift entries '
            f'across {len(bundles_with_drift)}/{bundle_count} bundles '
            f'({", ".join(bundles_with_drift)}). '
            "Re-run 'python3 marketplace/targets/generate.py --target claude --output target/claude' "
            "and copy each generated plugin.json over the committed one."
        )
    return EqualityResult(passed=passed, diffs=all_diffs, summary=summary)
