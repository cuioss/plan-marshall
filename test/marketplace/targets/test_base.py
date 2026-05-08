"""Tests for the TargetBase ABC contract."""

from pathlib import Path

import pytest

from marketplace.targets import TARGET_REGISTRY, register_target
from marketplace.targets.base import TargetBase


class IncompleteTarget(TargetBase):
    """Target subclass that omits abstract methods."""


class MinimalTarget(TargetBase):
    """Minimal concrete target implementation."""

    @property
    def name(self) -> str:
        return 'minimal-test-target'

    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path,
        bundles: list[str] | None = None,
    ) -> list[Path]:
        return []

    def supports_agents(self) -> bool:
        return True

    def supports_commands(self) -> bool:
        return False

    @property
    def config_dir(self) -> Path:
        return Path(__file__).resolve().parent


class MissingGenerateTarget(TargetBase):
    """Target subclass missing the generate() method."""

    @property
    def name(self) -> str:
        return 'missing-generate'

    def supports_agents(self) -> bool:
        return False

    def supports_commands(self) -> bool:
        return False

    @property
    def config_dir(self) -> Path:
        return Path(__file__).resolve().parent


class TestTargetBaseContract:
    """Verify TargetBase enforces its abstract contract."""

    def test_cannot_instantiate_target_base(self):
        with pytest.raises(TypeError):
            TargetBase()  # type: ignore[abstract]

    def test_cannot_instantiate_incomplete_subclass(self):
        with pytest.raises(TypeError):
            IncompleteTarget()  # type: ignore[abstract]

    def test_cannot_instantiate_subclass_missing_generate(self):
        with pytest.raises(TypeError):
            MissingGenerateTarget()  # type: ignore[abstract]

    def test_complete_subclass_instantiates(self):
        target = MinimalTarget()
        assert target.name == 'minimal-test-target'
        assert target.supports_agents() is True
        assert target.supports_commands() is False
        assert isinstance(target.config_dir, Path)

    def test_generate_returns_list(self):
        target = MinimalTarget()
        result = target.generate(Path('/fake'), Path('/fake-out'))
        assert result == []


class TestTargetRegistry:
    """Verify the registry pattern populates and rejects collisions."""

    def test_default_targets_registered(self):
        # Sub-package imports populate the registry on first use.
        assert 'claude' in TARGET_REGISTRY
        assert 'opencode' in TARGET_REGISTRY
        assert issubclass(TARGET_REGISTRY['claude'], TargetBase)
        assert issubclass(TARGET_REGISTRY['opencode'], TargetBase)

    def test_register_target_idempotent(self):
        existing = TARGET_REGISTRY['claude']
        register_target('claude', existing)  # same class — no-op
        assert TARGET_REGISTRY['claude'] is existing

    def test_register_target_rejects_collision(self):
        with pytest.raises(RuntimeError):
            register_target('claude', MinimalTarget)

    def test_register_target_adds_new(self):
        before = dict(TARGET_REGISTRY)
        try:
            register_target('minimal-test-target', MinimalTarget)
            assert TARGET_REGISTRY['minimal-test-target'] is MinimalTarget
        finally:
            TARGET_REGISTRY.clear()
            TARGET_REGISTRY.update(before)
