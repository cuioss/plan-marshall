"""ClaudeTarget — verbatim source mirror + always-generate plugin.json.

The Claude target operates in two modes selected by whether the caller
provides ``--output``:

* **Emit mode (`--output` provided)** — walk every bundle under
  ``marketplace/bundles/`` and copy its content byte-for-byte into
  ``{output}/{bundle}/`` *except* for ``.claude-plugin/plugin.json``,
  which is regenerated deterministically from the bundle's source
  frontmatter. The regenerated file is also diffed against the committed
  ``plugin.json`` so callers see drift as part of the same TOON return.

* **Validate mode (`--output` omitted)** — run the equality check only.
  Regenerate ``plugin.json`` for every bundle in-memory and report any
  drift versus the committed file. No bytes hit the filesystem.

The TOON return contains ``status``, ``emitted_count``,
``plugin_json_diff_count``, and ``equality_check_result``.
"""

from __future__ import annotations

from pathlib import Path

from marketplace.targets.base import TargetBase
from marketplace.targets.claude.emitter import emit_bundle_verbatim, iter_bundle_dirs
from marketplace.targets.claude.equality_check import EqualityResult, run_equality_check
from marketplace.targets.claude.plugin_json_gen import generate_plugin_json


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

        # Validate mode: equality check only
        if output_dir is None:
            equality = run_equality_check(marketplace_dir, bundle_dirs)
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

        # Emit mode: verbatim mirror + plugin.json regeneration
        output_dir.mkdir(parents=True, exist_ok=True)

        all_diffs: list[EqualityResult] = []
        for bundle_dir in bundle_dirs:
            mirrored = emit_bundle_verbatim(bundle_dir, output_dir)
            emitted.extend(mirrored)

            generated = generate_plugin_json(bundle_dir)
            target_plugin_json = output_dir / bundle_dir.name / '.claude-plugin' / 'plugin.json'
            target_plugin_json.parent.mkdir(parents=True, exist_ok=True)
            target_plugin_json.write_text(generated, encoding='utf-8')
            emitted.append(target_plugin_json)

        # Run equality check after emit so emit_count reflects bytes written.
        equality = run_equality_check(marketplace_dir, bundle_dirs)
        all_diffs.append(equality)

        self._last_run = {
            'status': 'success' if equality.passed else 'error',
            'emitted_count': len(emitted),
            'plugin_json_diff_count': len(equality.diffs),
            'equality_check_result': equality,
        }
        return emitted
