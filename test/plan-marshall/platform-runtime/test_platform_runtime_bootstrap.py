#!/usr/bin/env python3
"""Tests for platform_runtime.py — target-aware bootstrap glob discovery.

Covers:
  - _find_skills_root: ancestor walk to locate marketplace skills/ root
  - _bootstrap_glob_discover: sys.path extension routing by target

The two functions collaborate: _bootstrap_glob_discover calls _find_skills_root
to obtain the root, then appends skill script directories based on the target.
"""
import sys  # noqa: I001
from pathlib import Path
from unittest.mock import patch

import pytest

from platform_runtime import (  # type: ignore[import-not-found]
    _COMMON_BOOTSTRAP_LIBS,
    _TARGET_BOOTSTRAP_LIBS,
    _bootstrap_glob_discover,
    _find_skills_root,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_skills_root(base: Path) -> Path:
    """Create a minimal marketplace bundle under base and return the skills/ path.

    Creates:
        base/
          bundle-a/
            .claude-plugin/
              plugin.json
            skills/
              ref-toon-format/
                scripts/          (the common lib expected by bootstrap)
              platform-runtime/
                scripts/
              tools-file-ops/
                scripts/
              tools-permission-doctor/
                scripts/
              tools-permission-fix/
                scripts/
              workflow-permission-web/
                scripts/
              script-shared/
                scripts/

    Returns:
        The ``skills/`` path (``base / "bundle-a" / "skills"``).
    """
    bundle = base / "bundle-a"
    plugin_dir = bundle / ".claude-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text("{}", encoding="utf-8")

    skills = bundle / "skills"
    skills.mkdir()

    # Create script dirs for every library in _COMMON_BOOTSTRAP_LIBS and the
    # claude-specific _TARGET_BOOTSTRAP_LIBS so existence checks pass.
    all_libs = list(_COMMON_BOOTSTRAP_LIBS) + list(_TARGET_BOOTSTRAP_LIBS.get("claude", ()))
    for lib_name in all_libs:
        (skills / lib_name / "scripts").mkdir(parents=True, exist_ok=True)

    return skills


# =============================================================================
# Test: _find_skills_root
# =============================================================================


class TestFindSkillsRoot:
    """Tests for the ancestor-walk marketplace root locator."""

    def test_finds_root_from_script_inside_skills_tree(self, tmp_path):
        """Returns the skills/ Path when the walking file is inside the bundle."""
        skills = _make_skills_root(tmp_path)
        # Simulate __file__ being inside the platform-runtime/scripts/ directory.
        fake_file = skills / "platform-runtime" / "scripts" / "platform_runtime.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.touch()

        with patch("platform_runtime.__file__", str(fake_file)):
            result = _find_skills_root()

        assert result == skills

    def test_returns_none_when_no_marketplace_root_in_ancestry(self, tmp_path):
        """Returns None when no ancestor contains a .claude-plugin/plugin.json bundle."""
        # tmp_path has no bundle directory structure.
        fake_file = tmp_path / "some" / "random" / "script.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.touch()

        with patch("platform_runtime.__file__", str(fake_file)):
            result = _find_skills_root()

        assert result is None

    def test_returns_none_when_skills_dir_has_no_plugin_json(self, tmp_path):
        """Returns None when an ancestor is named 'skills' but lacks the plugin manifest."""
        # Create a 'skills' directory WITHOUT the .claude-plugin/plugin.json sibling.
        skills_dir = tmp_path / "no-manifest" / "skills"
        skills_dir.mkdir(parents=True)
        fake_file = skills_dir / "some-skill" / "scripts" / "script.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.touch()

        with patch("platform_runtime.__file__", str(fake_file)):
            result = _find_skills_root()

        assert result is None

    def test_finds_correct_root_with_deep_nesting(self, tmp_path):
        """Returns the right skills/ when the file is several directories below the bundle."""
        skills = _make_skills_root(tmp_path)
        deep = skills / "a" / "b" / "c" / "d.py"
        deep.parent.mkdir(parents=True)
        deep.touch()

        with patch("platform_runtime.__file__", str(deep)):
            result = _find_skills_root()

        assert result == skills


# =============================================================================
# Test: _bootstrap_glob_discover
# =============================================================================


class TestBootstrapGlobDiscover:
    """Tests for the target-aware sys.path bootstrap."""

    @pytest.fixture(autouse=True)
    def _restore_sys_path(self):
        """Restore sys.path after each test to avoid cross-test pollution."""
        original = list(sys.path)
        yield
        sys.path[:] = original

    def _discover_with_fake_root(self, tmp_path: Path, target: str | None):
        """Call _bootstrap_glob_discover with a patched skills root."""
        skills = _make_skills_root(tmp_path)
        fake_file = skills / "platform-runtime" / "scripts" / "platform_runtime.py"
        fake_file.touch()

        with patch("platform_runtime.__file__", str(fake_file)):
            result = _bootstrap_glob_discover(target)

        return result, skills

    # -- Return value -----------------------------------------------------------

    def test_returns_skills_root_when_root_found(self, tmp_path):
        """Returns the resolved skills/ Path when the marketplace root is found."""
        result, skills = self._discover_with_fake_root(tmp_path, None)
        assert result == skills

    def test_returns_none_when_root_not_found(self, tmp_path):
        """Returns None when no marketplace root is found in the file's ancestry."""
        fake_file = tmp_path / "nowhere" / "script.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.touch()

        with patch("platform_runtime.__file__", str(fake_file)):
            result = _bootstrap_glob_discover(None)

        assert result is None

    # -- Common libs always added -----------------------------------------------

    def test_common_libs_added_when_target_is_none(self, tmp_path):
        """All _COMMON_BOOTSTRAP_LIBS are added to sys.path when target is None."""
        result, skills = self._discover_with_fake_root(tmp_path, None)
        assert result is not None

        for lib_name in _COMMON_BOOTSTRAP_LIBS:
            expected = str(skills / lib_name / "scripts")
            assert expected in sys.path, f"Expected {expected} in sys.path"

    def test_common_libs_added_for_known_target(self, tmp_path):
        """All _COMMON_BOOTSTRAP_LIBS are added when target is a known string ('claude')."""
        result, skills = self._discover_with_fake_root(tmp_path, "claude")
        assert result is not None

        for lib_name in _COMMON_BOOTSTRAP_LIBS:
            expected = str(skills / lib_name / "scripts")
            assert expected in sys.path, f"Expected {expected} in sys.path for target 'claude'"

    def test_common_libs_added_for_unknown_target(self, tmp_path):
        """All _COMMON_BOOTSTRAP_LIBS are added even for an unrecognised target."""
        result, skills = self._discover_with_fake_root(tmp_path, "unknown-target")
        assert result is not None

        for lib_name in _COMMON_BOOTSTRAP_LIBS:
            expected = str(skills / lib_name / "scripts")
            assert expected in sys.path, f"Expected {expected} in sys.path for unknown target"

    # -- Target-specific libs ---------------------------------------------------

    def test_claude_target_adds_target_specific_libs(self, tmp_path):
        """Target-specific libs for 'claude' are added alongside the common libs."""
        result, skills = self._discover_with_fake_root(tmp_path, "claude")
        assert result is not None

        for lib_name in _TARGET_BOOTSTRAP_LIBS["claude"]:
            expected = str(skills / lib_name / "scripts")
            assert expected in sys.path, f"Expected claude-specific lib {expected} in sys.path"

    def test_unknown_target_adds_no_extra_libs(self, tmp_path):
        """An unknown target adds only the common libs — no target-specific extras."""
        skills = _make_skills_root(tmp_path)
        fake_file = skills / "platform-runtime" / "scripts" / "platform_runtime.py"
        fake_file.touch()

        sys_path_before_common = list(sys.path)

        with patch("platform_runtime.__file__", str(fake_file)):
            _bootstrap_glob_discover("unknown-target")

        # Only common libs may have been added — no lib outside _COMMON_BOOTSTRAP_LIBS.
        added = [p for p in sys.path if p not in sys_path_before_common]
        allowed = {str(skills / lib / "scripts") for lib in _COMMON_BOOTSTRAP_LIBS}
        unexpected = [p for p in added if p not in allowed]
        assert unexpected == [], f"Unexpected paths added for unknown target: {unexpected}"

    def test_none_target_adds_no_target_specific_libs(self, tmp_path):
        """Passing target=None adds only the common libs."""
        skills = _make_skills_root(tmp_path)
        fake_file = skills / "platform-runtime" / "scripts" / "platform_runtime.py"
        fake_file.touch()

        sys_path_before = list(sys.path)

        with patch("platform_runtime.__file__", str(fake_file)):
            _bootstrap_glob_discover(None)

        added = [p for p in sys.path if p not in sys_path_before]
        allowed = {str(skills / lib / "scripts") for lib in _COMMON_BOOTSTRAP_LIBS}
        unexpected = [p for p in added if p not in allowed]
        assert unexpected == [], f"Unexpected paths added when target=None: {unexpected}"

    # -- Idempotency ------------------------------------------------------------

    def test_repeated_calls_do_not_duplicate_sys_path_entries(self, tmp_path):
        """Calling _bootstrap_glob_discover twice does not duplicate sys.path entries."""
        skills = _make_skills_root(tmp_path)
        fake_file = skills / "platform-runtime" / "scripts" / "platform_runtime.py"
        fake_file.touch()

        with patch("platform_runtime.__file__", str(fake_file)):
            _bootstrap_glob_discover("claude")
            path_after_first = list(sys.path)
            _bootstrap_glob_discover("claude")

        # sys.path must not have grown between the two calls.
        assert sys.path == path_after_first

    # -- Only existing dirs added -----------------------------------------------

    def test_nonexistent_lib_dir_is_not_added_to_sys_path(self, tmp_path):
        """Directories that do not exist on disk are silently skipped."""
        # Create the bundle structure but omit the scripts/ dir for one lib.
        bundle = tmp_path / "bundle-partial"
        plugin_dir = bundle / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text("{}", encoding="utf-8")

        skills = bundle / "skills"
        skills.mkdir()

        # Create scripts/ for only the first common lib; leave the rest absent.
        first_common = _COMMON_BOOTSTRAP_LIBS[0]
        (skills / first_common / "scripts").mkdir(parents=True)

        fake_file = skills / first_common / "scripts" / "platform_runtime.py"
        fake_file.touch()

        sys_path_before = list(sys.path)

        with patch("platform_runtime.__file__", str(fake_file)):
            _bootstrap_glob_discover(None)

        added = [p for p in sys.path if p not in sys_path_before]

        # Only the lib whose scripts/ directory was created should appear.
        expected_added = str(skills / first_common / "scripts")
        assert expected_added in added

        # The remaining common libs (whose scripts/ dirs are absent) must NOT appear.
        for lib_name in _COMMON_BOOTSTRAP_LIBS[1:]:
            absent_path = str(skills / lib_name / "scripts")
            assert absent_path not in added, f"Non-existent path {absent_path} must not be in sys.path"

    # -- opencode target --------------------------------------------------------

    def test_opencode_target_adds_only_common_libs(self, tmp_path):
        """'opencode' target has an empty _TARGET_BOOTSTRAP_LIBS entry, so only common libs are added."""
        # Verify the assumption: opencode has an entry but it is empty.
        assert "opencode" in _TARGET_BOOTSTRAP_LIBS
        assert _TARGET_BOOTSTRAP_LIBS["opencode"] == ()

        result, skills = self._discover_with_fake_root(tmp_path, "opencode")
        assert result is not None

        # Common libs must be present.
        for lib_name in _COMMON_BOOTSTRAP_LIBS:
            expected = str(skills / lib_name / "scripts")
            assert expected in sys.path, f"Expected {expected} in sys.path for opencode target"
