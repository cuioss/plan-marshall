"""TargetBase — abstract contract for marketplace build targets.

Every target reads source bundles from `marketplace/bundles/` (the canonical
Claude Code format) and emits target-specific artifacts to an output
directory. Targets are configuration-driven — mapping rules live in JSON
files under `{config_dir}/`, not hardcoded in target classes.

See `marketplace/targets/__init__.py` for the registry and
`marketplace/targets/README.md` for the framework overview.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TargetBase(ABC):
    """Abstract base class for all marketplace build targets.

    Subclasses must declare:
      * `name` — short identifier used by the CLI and the registry key
        (e.g. ``"claude"``, ``"opencode"``).
      * `generate` — read source bundles and write target output.
      * `supports_agents` / `supports_commands` — capability flags consumed
        by the emitter so it can skip components a target cannot represent.
      * `config_dir` — directory containing JSON mapping/rule files for
        this target.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the short target identifier (e.g. ``"claude"``)."""

    @abstractmethod
    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path,
        bundles: list[str] | None = None,
    ) -> list[Path]:
        """Generate target-specific artifacts from source bundles.

        Args:
            marketplace_dir: Path to ``marketplace/bundles/`` (the source of
                truth).
            output_dir: Path to write the generated output. Targets that run
                in validation-only mode (e.g. Claude equality check without
                ``--output``) MAY treat this as a no-op directory.
            bundles: Optional list of bundle names to export. ``None`` means
                all bundles under ``marketplace_dir``.

        Returns:
            A list of generated (or would-be-generated) file paths. May be
            empty for validation-only modes.
        """

    @abstractmethod
    def supports_agents(self) -> bool:
        """Whether this target emits agents."""

    @abstractmethod
    def supports_commands(self) -> bool:
        """Whether this target emits commands."""

    @property
    @abstractmethod
    def config_dir(self) -> Path:
        """Return the directory containing this target's JSON config files."""
