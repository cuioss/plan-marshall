"""Base class for marketplace adapters.

Adapters translate the Claude Code marketplace format (the source of truth)
into target-specific output for other AI assistants.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class AdapterBase(ABC):
    """Abstract base class for marketplace adapters.

    Each adapter reads the existing plugin.json + SKILL.md files from
    marketplace/bundles/ and generates output in the target assistant's
    expected format.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the adapter name (e.g., 'opencode')."""

    @abstractmethod
    def generate(self, marketplace_dir: Path, output_dir: Path, bundles: list[str] | None = None) -> list[Path]:
        """Generate target-specific output from marketplace sources.

        Args:
            marketplace_dir: Path to marketplace/bundles/ directory.
            output_dir: Path to write generated output.
            bundles: Optional list of bundle names to export. None means all.

        Returns:
            List of generated file paths.
        """

    @abstractmethod
    def supports_agents(self) -> bool:
        """Whether this adapter supports exporting agents."""

    @abstractmethod
    def supports_commands(self) -> bool:
        """Whether this adapter supports exporting commands."""
