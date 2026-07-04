#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Gap-1 permission-ops back-import elimination (TASK-5 re-scope).

Asserts the re-scoped contract:

1. ``claude_runtime`` OWNS Claude settings path-resolution + load/save (single
   home) and carries NO back-import from ``permission_common`` /
   ``permission_doctor`` — the runtime is at the bottom of the import graph.
2. The four permission scripts (``permission_common``, ``permission_doctor``,
   ``permission_fix``, ``permission_web``) DELEGATE settings path-resolution +
   load/save to the runtime layer rather than owning it.
3. ``opencode_runtime`` permission ops return an honest ``no-op`` (reason +
   alternative), never a fabricated success that claims a write happened.

conftest.py sets up PYTHONPATH so the cross-skill imports resolve without manual
sys.path manipulation.
"""
from __future__ import annotations  # noqa: I001

import inspect
import json
from pathlib import Path
from typing import Any

import claude_runtime
import permission_common
import platform_runtime
import permission_doctor
import permission_fix
import permission_web
from claude_runtime import (
    _claude_global_settings_path,
    _claude_project_settings_path,
    _extract_project_steps,
    _load_marshal_config,
    _load_settings,
    _save_settings,
    _skill_permission_covered,
)
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


def _parse(output: str) -> dict[str, Any]:
    return parse_toon(output)


# =============================================================================
# 1. claude_runtime owns settings I/O with NO back-import from the scripts
# =============================================================================


class TestRuntimeOwnsSettingsIO:
    """The runtime is the single home for Claude settings path-resolution + I/O."""

    def test_runtime_source_has_no_back_import_from_permission_scripts(self) -> None:
        """claude_runtime MUST NOT import from permission_common / permission_doctor.

        The whole point of the re-scope is to break the runtime->script back-import
        cycle: the runtime sits at the bottom of the import graph, and the scripts
        delegate UP to it (never the reverse). This parses the AST and inspects
        actual ``import`` / ``from ... import`` nodes (including the lazy
        function-local imports the runtime uses), so a docstring that merely names
        ``permission_doctor`` as the relocation source is not flagged.
        """
        import ast

        source = Path(claude_runtime.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)
        assert "permission_common" not in imported_modules, (
            "claude_runtime back-imports permission_common — back-import not eliminated"
        )
        assert "permission_doctor" not in imported_modules, (
            "claude_runtime back-imports permission_doctor — back-import not eliminated"
        )

    def test_runtime_defines_settings_path_resolution(self) -> None:
        """The runtime owns the project + global settings-path resolvers."""
        assert callable(_claude_project_settings_path)
        assert callable(_claude_global_settings_path)

    def test_project_settings_path_prefers_settings_json_when_present(self, tmp_path: Path) -> None:
        """_claude_project_settings_path prefers settings.json when it exists."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "settings.json").write_text("{}", encoding="utf-8")

        resolved = _claude_project_settings_path(str(tmp_path))
        assert resolved == claude_dir / "settings.json"

    def test_project_settings_path_falls_back_to_local_when_settings_json_absent(
        self, tmp_path: Path
    ) -> None:
        """_claude_project_settings_path falls back to settings.local.json."""
        resolved = _claude_project_settings_path(str(tmp_path))
        assert resolved == tmp_path / ".claude" / "settings.local.json"

    def test_global_settings_path_is_under_home_claude(self) -> None:
        """_claude_global_settings_path resolves under ~/.claude."""
        resolved = _claude_global_settings_path()
        assert resolved.name == "settings.json"
        assert resolved.parent.name == ".claude"

    def test_load_settings_returns_skeleton_for_missing_file(self, tmp_path: Path) -> None:
        """_load_settings returns the empty-permissions skeleton when the file is absent."""
        data = _load_settings(tmp_path / "nope.json")
        assert data["permissions"]["allow"] == []
        assert data["permissions"]["deny"] == []
        assert data["permissions"]["ask"] == []

    def test_load_settings_reports_error_on_malformed_json(self, tmp_path: Path) -> None:
        """_load_settings surfaces a parse error rather than raising."""
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        data = _load_settings(bad)
        assert "error" in data
        assert data["permissions"]["allow"] == []

    def test_load_settings_backfills_missing_permission_keys(self, tmp_path: Path) -> None:
        """_load_settings backfills allow/deny/ask when a real file omits them."""
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"permissions": {"allow": ["Read(**)"]}}), encoding="utf-8")
        data = _load_settings(path)
        assert data["permissions"]["allow"] == ["Read(**)"]
        assert data["permissions"]["deny"] == []
        assert data["permissions"]["ask"] == []

    def test_save_then_load_round_trips(self, tmp_path: Path) -> None:
        """_save_settings + _load_settings round-trip a permission list."""
        path = tmp_path / ".claude" / "settings.json"
        payload = {"permissions": {"allow": ["Skill(foo:*)"], "deny": [], "ask": []}}
        assert _save_settings(path, payload) is True
        assert _load_settings(path)["permissions"]["allow"] == ["Skill(foo:*)"]

    def test_runtime_owns_skill_permission_covered(self) -> None:
        """_skill_permission_covered (relocated from permission_doctor) lives in the runtime."""
        assert _skill_permission_covered("foo", ["Skill(foo)"]) == "Skill(foo)"
        assert _skill_permission_covered("foo", ["Skill(foo:*)"]) == "Skill(foo:*)"
        assert _skill_permission_covered("foo", ["Skill(bar)"]) is None

    def test_runtime_owns_marshal_step_extraction(self, tmp_path: Path) -> None:
        """_load_marshal_config + _extract_project_steps live in the runtime."""
        marshal = tmp_path / "marshal.json"
        marshal.write_text(
            json.dumps({"plan": {"phase-6-finalize": {"steps": ["project:my-step", "push"]}}}),
            encoding="utf-8",
        )
        config, err = _load_marshal_config(str(marshal))
        assert err is None
        steps = _extract_project_steps(config)
        assert steps == [{"skill": "my-step", "step": "project:my-step", "phase": "phase-6-finalize"}]

    def test_marshal_config_reports_error_for_missing_file(self, tmp_path: Path) -> None:
        """_load_marshal_config returns an error string for an absent marshal.json."""
        _config, err = _load_marshal_config(str(tmp_path / "absent.json"))
        assert err is not None


class TestWriteOpsFailClosedOnMalformedSettings:
    """The five write ops fail closed (invalid_settings) rather than clobbering a malformed file."""

    def _malformed_settings(self, tmp_path: Path) -> Path:
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")
        return path

    def _pin_scope_path(self, monkeypatch, settings_path: Path) -> None:
        monkeypatch.setattr(
            claude_runtime, "_settings_path_for_scope", lambda scope: settings_path
        )

    def test_configure_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(claude_runtime.ClaudeRuntime().permission_configure("project", ["Read(**)"]))
        assert result["status"] == "error"
        assert result["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_fix_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix("project", "add", ["Read(**)"], False)
        )
        assert result["status"] == "error"
        assert result["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_ensure_wildcards_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_ensure_wildcards(
                "project", str(tmp_path / "marketplace"), False
            )
        )
        assert result["status"] == "error"
        assert result["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_ensure_steps_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        # A VALID marshal so the marshal guard passes and the settings guard is reached.
        marshal = tmp_path / "marshal.json"
        marshal.write_text(json.dumps({"plan": {}}), encoding="utf-8")
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_ensure_steps(str(marshal), "project", False)
        )
        assert result["status"] == "error"
        assert result["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_web_apply_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_web_apply(
                "project", add=["a.com"], remove=[], dry_run=False
            )
        )
        assert result["status"] == "error"
        assert result["error"] == "invalid_settings"
        assert settings.read_bytes() == before


class TestAuditOpsFailClosedOnMalformedMarshal:
    """permission_analyze / permission_ensure_steps reject a malformed marshal.json (invalid_marshal)."""

    def _malformed_marshal(self, tmp_path: Path) -> Path:
        marshal = tmp_path / "marshal.json"
        marshal.write_text("{not valid json", encoding="utf-8")
        return marshal

    def test_analyze_fails_closed_on_malformed_marshal(self, tmp_path: Path, monkeypatch) -> None:
        marshal = self._malformed_marshal(tmp_path)
        # Settings need not exist — analyze tolerates malformed/absent settings (read-only).
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_analyze("both", ["missing-steps"], str(marshal))
        )
        assert result["status"] == "error"
        assert result["error"] == "invalid_marshal"

    def test_ensure_steps_fails_closed_on_malformed_marshal(self, tmp_path: Path, monkeypatch) -> None:
        marshal = self._malformed_marshal(tmp_path)
        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"permissions": {"allow": []}}), encoding="utf-8")
        before = settings.read_bytes()
        monkeypatch.setattr(
            claude_runtime, "_settings_path_for_scope", lambda scope: settings
        )
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_ensure_steps(str(marshal), "project", False)
        )
        assert result["status"] == "error"
        assert result["error"] == "invalid_marshal"
        # The malformed-marshal guard fires before any settings write.
        assert settings.read_bytes() == before


# =============================================================================
# 2. The four permission scripts DELEGATE to the runtime layer
# =============================================================================


class TestScriptsDelegateToRuntime:
    """The tools-permission-* scripts no longer own settings path resolution / I/O."""

    def test_permission_common_imports_runtime_helpers(self) -> None:
        """permission_common delegates path-resolution + load/save to claude_runtime."""
        source = Path(permission_common.__file__).read_text(encoding="utf-8")
        assert "from claude_runtime import" in source

    def test_permission_common_path_for_write_delegates(self, tmp_path: Path) -> None:
        """get_project_settings_path_for_write resolves identically to the runtime."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "settings.json").write_text("{}", encoding="utf-8")
        delegated = permission_common.get_project_settings_path_for_write(tmp_path)
        assert delegated == _claude_project_settings_path(str(tmp_path))

    def test_permission_common_global_path_delegates(self) -> None:
        """get_global_settings_path resolves identically to the runtime."""
        assert permission_common.get_global_settings_path() == _claude_global_settings_path()

    def test_permission_common_load_settings_path_delegates(self, tmp_path: Path) -> None:
        """load_settings_path returns the same skeleton the runtime produces."""
        result = permission_common.load_settings_path(tmp_path / "nope.json")
        assert result == _load_settings(tmp_path / "nope.json")

    def test_permission_common_load_settings_error_contract(self, tmp_path: Path) -> None:
        """load_settings (str variant) preserves its (None, error) contract via the runtime."""
        bad = tmp_path / "bad.json"
        bad.write_text("{nope", encoding="utf-8")
        data, err = permission_common.load_settings(str(bad))
        assert data == {}
        assert err is not None

    def test_permission_common_save_settings_delegates(self, tmp_path: Path) -> None:
        """save_settings delegates the write to the runtime."""
        path = tmp_path / ".claude" / "settings.json"
        ok = permission_common.save_settings(
            str(path), {"permissions": {"allow": [], "deny": [], "ask": []}}
        )
        assert ok is True
        assert path.exists()

    def test_permission_doctor_imports_runtime_helpers(self) -> None:
        """permission_doctor delegates marshal/skill helpers to claude_runtime."""
        source = Path(permission_doctor.__file__).read_text(encoding="utf-8")
        assert "from claude_runtime import" in source

    def test_permission_doctor_skill_covered_delegates(self) -> None:
        """permission_doctor.skill_permission_covered delegates to the runtime."""
        assert permission_doctor.skill_permission_covered("foo", ["Skill(foo)"]) == "Skill(foo)"
        assert permission_doctor.skill_permission_covered("foo", ["Skill(bar)"]) is None

    def test_permission_doctor_extract_steps_delegates(self, tmp_path: Path) -> None:
        """permission_doctor.extract_project_steps delegates to the runtime."""
        config = {"plan": {"phase-5-execute": {"steps": ["project:lint"]}}}
        assert permission_doctor.extract_project_steps(config) == [
            {"skill": "lint", "step": "project:lint", "phase": "phase-5-execute"}
        ]

    def test_permission_fix_has_no_own_claude_settings_path_resolution(self) -> None:
        """permission_fix resolves settings paths only via permission_common (-> runtime).

        It must not open-code a ``.claude/settings`` path-resolution of its own; the
        only ``.claude`` reference allowed is the plugin-cache permission VALUE it
        installs and the ``.claude-plugin`` manifest filename it scans.
        """
        source = Path(permission_fix.__file__).read_text(encoding="utf-8")
        # No literal settings-file path resolution rooted at .claude/settings.
        assert ".claude/settings" not in source
        assert ".claude' / 'settings" not in source

    def test_permission_web_help_has_no_claude_settings_hardcode(self) -> None:
        """permission_web user-facing help no longer hardcodes ~/.claude/settings.json."""
        source = inspect.getsource(permission_web)
        assert "~/.claude/settings.json" not in source
        assert ".claude/settings.local.json" not in source


# =============================================================================
# 3. OpenCode permission ops return an honest no-op (no fake-success)
# =============================================================================


class TestOpenCodePermissionsHonestNoop:
    """OpenCode has no validated permission backend — every op is an honest no-op."""

    runtime = OpenCodeRuntime()

    def _assert_noop(self, result: dict[str, Any]) -> None:
        assert result["status"] == "no-op"
        assert "reason" in result
        assert "alternative" in result
        assert "OpenCode" in result["reason"]
        # Never fabricate a write-happened count.
        assert "permissions_written" not in result
        assert "changes_applied" not in result
        assert "domains_added" not in result
        assert "domains_removed" not in result
        assert "wildcards_added" not in result

    def test_configure_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_configure("project", ["Read(**)"])))

    def test_analyze_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_analyze("both", ["all"], None)))

    def test_fix_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_fix("project", "add", ["Read(**)"], False)))

    def test_ensure_wildcards_is_honest_noop(self) -> None:
        self._assert_noop(
            _parse(self.runtime.permission_ensure_wildcards("project", "marketplace/", False))
        )

    def test_ensure_steps_is_honest_noop(self, tmp_path: Path) -> None:
        marshal = tmp_path / "marshal.json"
        marshal.write_text("{}", encoding="utf-8")
        self._assert_noop(
            _parse(self.runtime.permission_ensure_steps(str(marshal), "project", False))
        )

    def test_web_analyze_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_web_analyze("global")))

    def test_web_apply_is_honest_noop(self) -> None:
        self._assert_noop(
            _parse(self.runtime.permission_web_apply("project", add=["a.com"], remove=[], dry_run=False))
        )

    def test_invalid_scope_still_errors_before_noop(self) -> None:
        """Scope validation still runs first — invalid scope is an error, not a no-op."""
        result = _parse(self.runtime.permission_configure("workspace", ["Read(**)"]))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"


# =============================================================================
# 4. Cross-cutting regression: the fail-closed paths drive end-to-end via the
#    public platform-runtime dispatch router (not the bound runtime methods).
# =============================================================================


class TestFailClosedDispatchRegression:
    """Drive the fail-closed write/audit paths end-to-end through ``platform_runtime.main``.

    This is the user-visible regression angle distinct from the helper-level unit
    assertions above: a malformed ``.claude/settings.json`` is never silently
    clobbered, and a malformed ``marshal.json`` never produces a false-success
    audit. The tests exercise the public router (operation string + argv), which
    resolves the Claude runtime from a marshal.json selecting the claude target.
    These tests fail if any write op is reverted to clobber-on-malformed or any
    audit op is reverted to false-success.
    """

    def _claude_project(self, tmp_path: Path, monkeypatch) -> Path:
        """Make tmp_path a claude-target project with cwd pinned to it; return its .claude dir."""
        plan_dir = tmp_path / ".plan"
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "marshal.json").write_text(
            json.dumps({"runtime": {"target": "claude"}}), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        return claude_dir

    def _malformed_project_settings(self, claude_dir: Path) -> Path:
        settings = claude_dir / "settings.json"
        settings.write_text("{not valid json", encoding="utf-8")
        return settings

    def _run(self, capsys, argv: list[str]) -> dict[str, Any]:
        rc = platform_runtime.main(argv)
        assert rc == 0
        return _parse(capsys.readouterr().out)

    def test_configure_write_fails_closed_via_dispatch(self, tmp_path, monkeypatch, capsys) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        settings = self._malformed_project_settings(claude_dir)
        before = settings.read_bytes()
        parsed = self._run(
            capsys, ["permission", "configure", "--scope", "project", "--permissions", "Read(**)"]
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_fix_write_fails_closed_via_dispatch(self, tmp_path, monkeypatch, capsys) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        settings = self._malformed_project_settings(claude_dir)
        before = settings.read_bytes()
        parsed = self._run(
            capsys,
            ["permission", "fix", "--scope", "project", "--operation", "add", "--permissions", "Read(**)"],
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_ensure_wildcards_write_fails_closed_via_dispatch(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        settings = self._malformed_project_settings(claude_dir)
        before = settings.read_bytes()
        parsed = self._run(
            capsys,
            ["permission", "ensure-wildcards", "--scope", "project", "--marketplace-dir", "marketplace/"],
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_ensure_steps_write_fails_closed_via_dispatch(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        settings = self._malformed_project_settings(claude_dir)
        before = settings.read_bytes()
        # A VALID marshal so the marshal guard passes and the settings guard fires.
        marshal = tmp_path / "valid-marshal.json"
        marshal.write_text(json.dumps({"plan": {}}), encoding="utf-8")
        parsed = self._run(
            capsys,
            ["permission", "ensure-steps", "--marshal", str(marshal), "--scope", "project"],
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_web_apply_write_fails_closed_via_dispatch(self, tmp_path, monkeypatch, capsys) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        settings = self._malformed_project_settings(claude_dir)
        before = settings.read_bytes()
        parsed = self._run(
            capsys,
            ["permission", "web-apply", "--scope", "project", "--add", json.dumps(["example.com"])],
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_settings"
        assert settings.read_bytes() == before

    def test_analyze_audit_fails_closed_on_malformed_marshal_via_dispatch(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        self._claude_project(tmp_path, monkeypatch)
        marshal = tmp_path / "bad-marshal.json"
        marshal.write_text("{not valid json", encoding="utf-8")
        parsed = self._run(
            capsys,
            ["permission", "analyze", "--scope", "both", "--checks", "missing-steps", "--marshal", str(marshal)],
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_marshal"

    def test_ensure_steps_audit_fails_closed_on_malformed_marshal_via_dispatch(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        # Valid settings so a false-success would actually write; the malformed
        # marshal must fail BEFORE any settings access.
        settings = claude_dir / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": []}}), encoding="utf-8")
        before = settings.read_bytes()
        marshal = tmp_path / "bad-marshal.json"
        marshal.write_text("{not valid json", encoding="utf-8")
        parsed = self._run(
            capsys,
            ["permission", "ensure-steps", "--marshal", str(marshal), "--scope", "project"],
        )
        assert parsed["status"] == "error"
        assert parsed["error"] == "invalid_marshal"
        assert settings.read_bytes() == before
