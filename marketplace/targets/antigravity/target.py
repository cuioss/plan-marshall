# SPDX-License-Identifier: FSL-1.1-ALv2
"""AntigravityTarget — concrete Google Antigravity build target.

Implements ``TargetBase`` by delegating to ``emitter.emit_bundles``.
"""

from __future__ import annotations

from pathlib import Path

from marketplace.targets.antigravity.emitter import (
    ANTIGRAVITY_TARGET_NAME,
    emit_bundles,
)
from marketplace.targets.base import TargetBase
from marketplace.targets.body_transform_engine import (
    build_user_invocable_lookup,
    load_transform_rules,
    make_body_transformer,
)


class AntigravityTarget(TargetBase):
    """Build target for Google Antigravity output."""

    @property
    def name(self) -> str:
        return ANTIGRAVITY_TARGET_NAME

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
                'AntigravityTarget requires --output: pass an output directory (e.g. target/antigravity/)'
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
            target_name=self.name,
        )


__all__ = ['AntigravityTarget']
