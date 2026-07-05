# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCodeTarget — concrete OpenCode build target.

Implements ``TargetBase`` by delegating to ``emitter.emit_bundles``. The
target requires an ``output_dir`` (it has no validation-only mode) — when
the CLI invokes this target without ``--output``, ``generate.py`` is
responsible for surfacing the error before reaching the target.
"""

from __future__ import annotations

from pathlib import Path

from marketplace.targets.base import TargetBase
from marketplace.targets.body_transform_engine import (
    build_user_invocable_lookup,
    load_transform_rules,
    make_body_transformer,
)
from marketplace.targets.opencode.emitter import emit_bundles


class OpenCodeTarget(TargetBase):
    """Build target for OpenCode-format output."""

    @property
    def name(self) -> str:
        return 'opencode'

    @property
    def config_dir(self) -> Path:
        """Directory holding ``mapping.json`` and ``frontmatter-rules.json``."""
        return Path(__file__).resolve().parent

    def supports_agents(self) -> bool:
        return True

    def supports_commands(self) -> bool:
        return True

    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path | None,
        bundles: list[str] | None = None,
    ) -> list[Path]:
        if output_dir is None:
            raise ValueError(
                'OpenCodeTarget requires --output: pass an output directory '
                '(e.g. target/opencode/)'
            )
        rules = load_transform_rules(self.config_dir / 'mapping.json')
        lookup = build_user_invocable_lookup(marketplace_dir)
        transformer = make_body_transformer(lookup, rules)
        return emit_bundles(
            marketplace_dir,
            output_dir,
            self.config_dir,
            bundles=bundles,
            body_transformer=transformer,
        )


__all__ = ['OpenCodeTarget']
