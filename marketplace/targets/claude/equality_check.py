"""Equality-check engine for the Claude target.

Regenerates ``plugin.json`` for each bundle in-memory via
``plugin_json_gen.build_plugin_json`` and diffs the result against the
committed ``marketplace/bundles/{bundle}/.claude-plugin/plugin.json``.
Powers both the standalone validation mode (``generate.py --target
claude`` without ``--output``) and the CI/PR equality gate.

Variant-aware drift detection: agents declaring the
dynamic-level-executor extension point expand into multiple
``plugin.json`` entries (canonical + per-emitted-level). The diff
naturally surfaces drift when (a) the canonical's ``levels:`` whitelist
changes without ``plugin.json`` regeneration, (b) the build-time
``xxhigh`` guard suppresses a previously emitted variant, or (c) a new
canonical adds the ``implements:`` declaration but the committed
``plugin.json`` still lists only the no-suffix entry. The fix in every
case is the documented one: regenerate via the Claude target and copy
the updated ``plugin.json`` over the committed file.
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


def _committed_plugin_json(bundle_dir: Path) -> dict:
    plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
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


def check_bundle(bundle_dir: Path) -> list[BundleDiff]:
    """Compare the committed ``plugin.json`` against the regenerated one."""
    committed = _committed_plugin_json(bundle_dir)
    generated = build_plugin_json(bundle_dir)
    diffs: list[BundleDiff] = []
    for field_name in ('agents', 'commands', 'skills'):
        committed_arr = list(committed.get(field_name, []) or [])
        generated_arr = list(generated.get(field_name, []) or [])
        diff = _diff_array(bundle_dir.name, field_name, committed_arr, generated_arr)
        if diff is not None:
            diffs.append(diff)
    return diffs


def run_equality_check(marketplace_dir: Path, bundle_dirs: Iterable[Path]) -> EqualityResult:
    """Run the equality check across the supplied bundle directories."""
    all_diffs: list[BundleDiff] = []
    bundle_count = 0
    for bundle_dir in bundle_dirs:
        bundle_count += 1
        all_diffs.extend(check_bundle(bundle_dir))

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
    _ = marketplace_dir  # parameter retained for symmetry with target.generate signature
    return EqualityResult(passed=passed, diffs=all_diffs, summary=summary)
