#!/usr/bin/env python3
"""Tests for the platform-runtime layout-resolution operation (Gap 4).

Asserts the ``layout skill-roots`` op returns the correct project-local-skill
root(s) per target (Claude → ``.claude/skills``; OpenCode → the executor's
multi-root list), that the router dispatches the new operation, and that the
``marketplace_paths`` consumer helpers (``get_project_skill_roots``,
``resolve_project_skill_path``, ``iter_project_skill_dirs``) route through the op
and probe roots first-match-wins.
"""

import importlib  # noqa: I001
import pathlib

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
import marketplace_paths  # type: ignore[import-not-found]
import platform_runtime  # type: ignore[import-not-found]
from claude_runtime import ClaudeRuntime  # type: ignore[import-not-found]
from opencode_runtime import OpenCodeRuntime  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is a non-empty dict."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict), f"parse_toon returned non-dict: {toon_str!r}"
    return result


# =============================================================================
# 1. Runtime op — per-target roots
# =============================================================================


def test_claude_layout_skill_roots_returns_dot_claude() -> None:
    """ClaudeRuntime.layout_skill_roots returns the single .claude/skills root."""
    result = _parse(ClaudeRuntime().layout_skill_roots())
    assert result["status"] == "success"
    assert result["operation"] == "layout skill-roots"
    assert result["target"] == "claude"
    assert result["roots"] == [".claude/skills"]


def test_opencode_layout_skill_roots_returns_multiroot_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenCodeRuntime.layout_skill_roots mirrors the executor's discovery roots."""
    monkeypatch.delenv("OPENCODE_CONFIG_DIR", raising=False)
    result = _parse(OpenCodeRuntime().layout_skill_roots())
    assert result["status"] == "success"
    assert result["target"] == "opencode"
    roots = result["roots"]
    assert isinstance(roots, list)
    # Project-local roots appear in priority order before the user-global ones.
    assert roots[0] == ".opencode/skills"
    assert ".claude/skills" in roots
    assert ".agents/skills" in roots
    # User-global roots are ~-expanded to absolute paths.
    assert any(r.endswith("/.config/opencode/skills") for r in roots)
    assert any(r.endswith("/.claude/skills") for r in roots)


def test_opencode_layout_skill_roots_honours_config_dir_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A set OPENCODE_CONFIG_DIR prepends its skills root at highest priority."""
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", "/custom/opencode")
    result = _parse(OpenCodeRuntime().layout_skill_roots())
    assert result["roots"][0] == "/custom/opencode/skills"


# =============================================================================
# 2. Router dispatch
# =============================================================================


def test_router_dispatches_layout_skill_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The router resolves runtime.target and dispatches `layout skill-roots`."""
    plan_dir = tmp_path / ".plan"
    plan_dir.mkdir()
    (plan_dir / "marshal.json").write_text('{"runtime": {"target": "claude"}}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    rc = platform_runtime.main(["layout", "skill-roots"])
    assert rc == 0
    result = _parse(capsys.readouterr().out)
    assert result["status"] == "success"
    assert result["operation"] == "layout skill-roots"
    assert result["roots"] == [".claude/skills"]


def test_router_dispatches_layout_skill_roots_opencode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The router selects the OpenCode runtime when marshal.json says so."""
    monkeypatch.delenv("OPENCODE_CONFIG_DIR", raising=False)
    plan_dir = tmp_path / ".plan"
    plan_dir.mkdir()
    (plan_dir / "marshal.json").write_text('{"runtime": {"target": "opencode"}}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    rc = platform_runtime.main(["layout", "skill-roots"])
    assert rc == 0
    result = _parse(capsys.readouterr().out)
    assert result["status"] == "success"
    assert result["target"] == "opencode"
    assert ".opencode/skills" in result["roots"]


# =============================================================================
# 3. marketplace_paths consumer helpers
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_skill_roots_cache():
    """Clear the per-process memoisation cache before and after each test."""
    marketplace_paths._SKILL_ROOTS_CACHE = None
    yield
    marketplace_paths._SKILL_ROOTS_CACHE = None


def test_get_project_skill_roots_falls_back_to_claude_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """With no marshal.json the helper falls back to the Claude default root."""
    monkeypatch.chdir(tmp_path)
    # Force the layout op to be unreachable so the fallback path is exercised.
    monkeypatch.setattr(marketplace_paths, "_invoke_layout_op", lambda target: None)
    assert marketplace_paths.get_project_skill_roots() == (".claude/skills",)


def test_get_project_skill_roots_is_memoised(monkeypatch: pytest.MonkeyPatch) -> None:
    """The op is invoked at most once per process (memoised result reused)."""
    calls: list[str] = []

    def _fake_invoke(target: str):
        calls.append(target)
        return (".claude/skills",)

    monkeypatch.setattr(marketplace_paths, "_read_runtime_target", lambda: "claude")
    monkeypatch.setattr(marketplace_paths, "_invoke_layout_op", _fake_invoke)

    first = marketplace_paths.get_project_skill_roots()
    second = marketplace_paths.get_project_skill_roots()
    assert first == second == (".claude/skills",)
    assert calls == ["claude"], "layout op must be invoked exactly once (memoised)"


def test_resolve_project_skill_path_first_match_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """resolve_project_skill_path returns the first existing root's candidate."""
    # Two roots; the skill exists only under the second.
    (tmp_path / ".opencode" / "skills" / "demo").mkdir(parents=True)
    (tmp_path / ".opencode" / "skills" / "demo" / "SKILL.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        marketplace_paths,
        "get_project_skill_roots",
        lambda: (".claude/skills", ".opencode/skills"),
    )
    resolved = marketplace_paths.resolve_project_skill_path("demo/SKILL.md", base=tmp_path)
    assert resolved == tmp_path / ".opencode" / "skills" / "demo" / "SKILL.md"


def test_resolve_project_skill_path_no_match_returns_first_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """When no root matches, the highest-priority candidate is returned."""
    monkeypatch.setattr(
        marketplace_paths,
        "get_project_skill_roots",
        lambda: (".claude/skills", ".opencode/skills"),
    )
    resolved = marketplace_paths.resolve_project_skill_path("missing/SKILL.md", base=tmp_path)
    assert resolved == tmp_path / ".claude" / "skills" / "missing" / "SKILL.md"


def test_iter_project_skill_dirs_collects_across_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """iter_project_skill_dirs yields child dirs from every existing root in order."""
    (tmp_path / ".claude" / "skills" / "alpha").mkdir(parents=True)
    (tmp_path / ".opencode" / "skills" / "beta").mkdir(parents=True)
    monkeypatch.setattr(
        marketplace_paths,
        "get_project_skill_roots",
        lambda: (".claude/skills", ".opencode/skills"),
    )
    dirs = marketplace_paths.iter_project_skill_dirs(base=tmp_path)
    names = [d.name for d in dirs]
    # .claude/skills is the higher-priority root, so alpha precedes beta.
    assert names == ["alpha", "beta"]


def test_resolve_module_reimport_clean() -> None:
    """marketplace_paths re-imports cleanly (no import-time side effects)."""
    importlib.reload(marketplace_paths)
    marketplace_paths._SKILL_ROOTS_CACHE = None
