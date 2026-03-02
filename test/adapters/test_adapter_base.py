"""Tests for the adapter base class ABC contract."""

from pathlib import Path

import pytest
from marketplace.adapters.adapter_base import AdapterBase


class IncompleteAdapter(AdapterBase):
    """Adapter that does not implement abstract methods."""


class MinimalAdapter(AdapterBase):
    """Minimal concrete adapter implementation."""

    def name(self) -> str:
        return 'test'

    def generate(self, marketplace_dir: Path, output_dir: Path, bundles: list[str] | None = None) -> list[Path]:
        return []

    def supports_agents(self) -> bool:
        return True

    def supports_commands(self) -> bool:
        return False


class TestAdapterBase:
    """Verify the ABC contract of AdapterBase."""

    def test_cannot_instantiate_abstract(self):
        """AdapterBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AdapterBase()  # type: ignore[abstract]

    def test_cannot_instantiate_incomplete(self):
        """Subclass without all abstract methods cannot be instantiated."""
        with pytest.raises(TypeError):
            IncompleteAdapter()  # type: ignore[abstract]

    def test_concrete_adapter_instantiates(self):
        """Complete implementation can be instantiated."""
        adapter = MinimalAdapter()
        assert adapter.name() == 'test'
        assert adapter.supports_agents() is True
        assert adapter.supports_commands() is False

    def test_generate_returns_list(self):
        """generate() returns a list of paths."""
        adapter = MinimalAdapter()
        result = adapter.generate(Path('/fake'), Path('/fake-out'))
        assert result == []
