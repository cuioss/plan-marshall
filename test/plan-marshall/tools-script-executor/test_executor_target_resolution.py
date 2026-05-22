#!/usr/bin/env python3
"""Tests for target-aware executor resolution in generate_executor.py.

Covers:
  - read_marshal_target: marshal.json upward walk and target extraction
  - generate_target_aware_resolver_code: emits correct resolver per target
  - Claude resolver (_resolve_notation_by_target): plugin-cache glob walk
  - OpenCode resolver (_resolve_notation_by_target): 7-root walk
  - Absolute-path conversion for both targets
  - Integration: resolver round-trip for a real notation on each target
"""

import json  # noqa: I001
import os
import re
import sys
import types
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, _MARKETPLACE_SCRIPT_DIRS

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------

SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts'
)
GENERATE_SCRIPT = SCRIPTS_DIR / 'generate_executor.py'


def _load_generate_executor() -> types.ModuleType:
    """Load generate_executor.py as an in-process module."""
    source = GENERATE_SCRIPT.read_text(encoding='utf-8')
    module = types.ModuleType('generate_executor')
    module.__dict__['__file__'] = str(GENERATE_SCRIPT)
    exec(compile(source, str(GENERATE_SCRIPT), 'exec'), module.__dict__)
    return module


# ---------------------------------------------------------------------------
# Helpers: inline-execute the resolver code in an isolated namespace
# ---------------------------------------------------------------------------


def _exec_resolver(resolver_code: str) -> types.ModuleType:
    """Execute resolver_code inside a minimal module namespace.

    The resolver bodies reference ``Path`` and ``os``; we inject those.
    Returns the module-like namespace so tests can call
    ``ns._resolve_notation_by_target(notation)``.
    """
    ns = types.ModuleType('resolver_under_test')
    ns.__dict__['Path'] = Path
    ns.__dict__['os'] = os
    exec(compile(resolver_code, '<resolver>', 'exec'), ns.__dict__)
    return ns


# =============================================================================
# Tests: read_marshal_target
# =============================================================================


class TestReadMarshalTarget:
    """Tests for the marshal.json target extractor."""

    def test_reads_target_from_plan_marshal_json(self, tmp_path):
        """Returns runtime.target when marshal.json is present and well-formed."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal = {'runtime': {'target': 'opencode'}}
        (plan_dir / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')

        result = module.read_marshal_target(cwd=tmp_path)
        assert result == 'opencode'

    def test_defaults_to_claude_when_marshal_absent(self, tmp_path):
        """Returns 'claude' when no marshal.json is found."""
        module = _load_generate_executor()

        result = module.read_marshal_target(cwd=tmp_path)
        assert result == 'claude'

    def test_defaults_to_claude_when_runtime_key_missing(self, tmp_path):
        """Returns 'claude' when marshal.json lacks the runtime.target key."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text('{}', encoding='utf-8')

        result = module.read_marshal_target(cwd=tmp_path)
        assert result == 'claude'

    def test_defaults_to_claude_when_runtime_target_empty_string(self, tmp_path):
        """Returns 'claude' when runtime.target is an empty string."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal = {'runtime': {'target': ''}}
        (plan_dir / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')

        result = module.read_marshal_target(cwd=tmp_path)
        assert result == 'claude'

    def test_walks_up_from_subdir(self, tmp_path):
        """Finds marshal.json when cwd is a subdirectory of the project root."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal = {'runtime': {'target': 'opencode'}}
        (plan_dir / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')

        subdir = tmp_path / 'a' / 'b' / 'c'
        subdir.mkdir(parents=True)

        result = module.read_marshal_target(cwd=subdir)
        assert result == 'opencode'

    def test_defaults_to_claude_on_malformed_json(self, tmp_path):
        """Returns 'claude' when marshal.json is not valid JSON."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text('not json {{{', encoding='utf-8')

        result = module.read_marshal_target(cwd=tmp_path)
        assert result == 'claude'

    def test_reads_target_claude(self, tmp_path):
        """Returns 'claude' when runtime.target is explicitly 'claude'."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal = {'runtime': {'target': 'claude'}}
        (plan_dir / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')

        result = module.read_marshal_target(cwd=tmp_path)
        assert result == 'claude'


# =============================================================================
# Tests: generate_target_aware_resolver_code
# =============================================================================


class TestGenerateTargetAwareResolverCode:
    """Tests for the resolver code generator."""

    def test_returns_string_for_claude_target(self):
        """Returns a non-empty Python source string for target='claude'."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        assert isinstance(code, str)
        assert len(code) > 0

    def test_returns_string_for_opencode_target(self):
        """Returns a non-empty Python source string for target='opencode'."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        assert isinstance(code, str)
        assert len(code) > 0

    def test_claude_and_opencode_resolvers_differ(self):
        """The Claude and OpenCode resolver bodies are different."""
        module = _load_generate_executor()
        claude_code = module.generate_target_aware_resolver_code('claude')
        opencode_code = module.generate_target_aware_resolver_code('opencode')
        assert claude_code != opencode_code

    def test_unknown_target_returns_claude_resolver(self):
        """An unknown target string falls back to the Claude resolver."""
        module = _load_generate_executor()
        claude_code = module.generate_target_aware_resolver_code('claude')
        unknown_code = module.generate_target_aware_resolver_code('unknown-platform')
        assert claude_code == unknown_code

    def test_resolver_code_defines_function(self):
        """Both resolvers define the ``_resolve_notation_by_target`` function."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            code = module.generate_target_aware_resolver_code(target)
            assert 'def _resolve_notation_by_target(' in code, (
                f'Target {target!r} resolver missing function definition'
            )

    def test_resolver_code_is_valid_python(self):
        """Both resolver code strings compile without syntax errors."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            code = module.generate_target_aware_resolver_code(target)
            try:
                compile(code, f'<resolver-{target}>', 'exec')
            except SyntaxError as exc:
                pytest.fail(f'Resolver for {target!r} has syntax error: {exc}')

    def test_claude_resolver_references_plugin_cache(self):
        """Claude resolver body mentions the plugin-cache path."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        assert 'plugins' in code and 'cache' in code, (
            'Claude resolver must reference the plugin cache path'
        )

    def test_opencode_resolver_references_seven_roots(self):
        """OpenCode resolver body references the 7 skill discovery roots."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        # Check for a representative subset of the 7 roots
        assert '.opencode/skills' in code, 'OpenCode resolver must include .opencode/skills root'
        assert '.claude/skills' in code, 'OpenCode resolver must include .claude/skills root'
        assert '.config/opencode/skills' in code, 'OpenCode resolver must include ~/.config/opencode/skills root'
        assert 'OPENCODE_CONFIG_DIR' in code, 'OpenCode resolver must honour OPENCODE_CONFIG_DIR env var'

    def test_opencode_resolver_uses_dash_namespaced_layout(self):
        """OpenCode resolver uses ``{bundle}-{skill}`` directory naming."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        # The dash-namespaced pattern must be present
        assert "f'{bundle}-{skill}'" in code or "bundle-skill" in code or "dir_name" in code, (
            'OpenCode resolver must construct dash-namespaced directory name'
        )


# =============================================================================
# Tests: Claude resolver (_resolve_notation_by_target)
# =============================================================================


class TestClaudeResolver:
    """Tests for the inline Claude resolver function."""

    def test_returns_none_when_cache_dir_absent(self, tmp_path, monkeypatch):
        """Returns None when the plugin cache root does not exist."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Point HOME at tmp_path so ~/.claude/plugins/cache is absent
        monkeypatch.setenv('HOME', str(tmp_path))

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is None

    def test_returns_none_for_unknown_notation(self, tmp_path, monkeypatch):
        """Returns None when the skill/script combination is not in the cache."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Create minimal plugin cache structure without the target script
        cache_dir = tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '1.0.0' / 'skills'
        cache_dir.mkdir(parents=True)

        monkeypatch.setenv('HOME', str(tmp_path))

        result = ns._resolve_notation_by_target('no-bundle:no-skill:no-script')
        assert result is None

    def test_finds_script_in_cache_and_returns_absolute_path(self, tmp_path, monkeypatch):
        """Discovers a script in the plugin cache and returns its absolute path."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Set up a minimal cache tree with a real script file
        version_dir = (
            tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '1.2.3'
        )
        scripts_dir = version_dir / 'skills' / 'manage-status' / 'scripts'
        scripts_dir.mkdir(parents=True)
        script_file = scripts_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')

        monkeypatch.setenv('HOME', str(tmp_path))

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None, 'Expected to find the script in the fake cache'
        assert os.path.isabs(result), f'Returned path must be absolute, got {result!r}'
        assert result.endswith('manage-status.py'), f'Expected manage-status.py, got {result!r}'

    def test_skips_hidden_version_directories(self, tmp_path, monkeypatch):
        """Hidden directories (starting with '.') inside the cache are skipped."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Create only a hidden version dir — should not be discovered
        hidden_version = (
            tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '.hidden-version'
        )
        scripts_dir = hidden_version / 'skills' / 'some-skill' / 'scripts'
        scripts_dir.mkdir(parents=True)
        (scripts_dir / 'some_script.py').write_text('# hidden', encoding='utf-8')

        monkeypatch.setenv('HOME', str(tmp_path))

        result = ns._resolve_notation_by_target('plan-marshall:some-skill:some_script')
        assert result is None, 'Hidden version directories must be skipped'

    def test_invalid_notation_returns_none(self, tmp_path, monkeypatch):
        """A notation with fewer or more than 3 parts returns None."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))

        assert ns._resolve_notation_by_target('two:parts') is None
        assert ns._resolve_notation_by_target('too:many:parts:here') is None
        assert ns._resolve_notation_by_target('') is None


# =============================================================================
# Tests: OpenCode resolver (_resolve_notation_by_target)
# =============================================================================


class TestOpenCodeResolver:
    """Tests for the inline OpenCode resolver function."""

    def test_returns_none_when_no_roots_exist(self, tmp_path, monkeypatch):
        """Returns None when none of the 7 roots contain the script."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is None

    def test_finds_script_in_opencode_skills_dir(self, tmp_path, monkeypatch):
        """Discovers a script in the .opencode/skills root (project-local)."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

        # Create the .opencode/skills/{bundle}-{skill}/scripts/{script}.py structure
        skill_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        skill_dir.mkdir(parents=True)
        script_file = skill_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')

        # Change cwd to tmp_path so relative .opencode/skills resolves correctly
        monkeypatch.chdir(tmp_path)

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None, 'Expected to find the script in .opencode/skills'
        assert os.path.isabs(result), f'Returned path must be absolute, got {result!r}'
        assert result.endswith('manage-status.py'), f'Expected manage-status.py, got {result!r}'

    def test_finds_script_via_env_var_override(self, tmp_path, monkeypatch):
        """$OPENCODE_CONFIG_DIR/skills root has highest priority."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))

        # Set up OPENCODE_CONFIG_DIR root with the target script
        config_dir = tmp_path / 'opencode-config'
        skill_dir = config_dir / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        skill_dir.mkdir(parents=True)
        script_file = skill_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')

        # Also create a lower-priority root with a different file to verify priority
        fallback_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        fallback_dir.mkdir(parents=True)
        (fallback_dir / 'manage-status.py').write_text('# fallback', encoding='utf-8')

        monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(config_dir))
        monkeypatch.chdir(tmp_path)

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None
        assert os.path.isabs(result)
        # Must have resolved through the env-var root (first match)
        assert str(config_dir.resolve()) in result, (
            f'Expected resolution through OPENCODE_CONFIG_DIR={config_dir}, got {result}'
        )

    def test_finds_script_in_user_global_config_root(self, tmp_path, monkeypatch):
        """Discovers a script in ~/.config/opencode/skills (user-global root)."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

        # Create the user-global root
        skill_dir = (
            tmp_path / '.config' / 'opencode' / 'skills'
            / 'plan-marshall-manage-status' / 'scripts'
        )
        skill_dir.mkdir(parents=True)
        (skill_dir / 'manage-status.py').write_text('# user-global', encoding='utf-8')

        # cwd has no local .opencode/skills root
        monkeypatch.chdir(tmp_path)

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None
        assert os.path.isabs(result)

    def test_uses_dash_namespaced_directory(self, tmp_path, monkeypatch):
        """Resolver constructs ``{bundle}-{skill}`` directory name, not ``{bundle}/{skill}``."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)
        monkeypatch.chdir(tmp_path)

        # Create the WRONG (slash-namespaced) layout — must NOT be found
        wrong_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall' / 'manage-status' / 'scripts'
        wrong_dir.mkdir(parents=True)
        (wrong_dir / 'manage-status.py').write_text('# wrong layout', encoding='utf-8')

        result_wrong = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result_wrong is None, (
            'Slash-namespaced layout must not be found; resolver uses dash-namespaced dirs'
        )

        # Create the CORRECT (dash-namespaced) layout — must be found
        correct_dir = (
            tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        )
        correct_dir.mkdir(parents=True)
        (correct_dir / 'manage-status.py').write_text('# correct layout', encoding='utf-8')

        result_correct = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result_correct is not None, 'Dash-namespaced layout must be found'
        assert os.path.isabs(result_correct)

    def test_returns_absolute_path(self, tmp_path, monkeypatch):
        """Matched path is always converted to absolute before return."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

        # Create the dash-namespaced layout
        skill_dir = (
            tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        )
        skill_dir.mkdir(parents=True)
        (skill_dir / 'manage-status.py').write_text('# stub', encoding='utf-8')

        monkeypatch.chdir(tmp_path)

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None
        assert os.path.isabs(result), f'Path must be absolute, got {result!r}'

    def test_invalid_notation_returns_none(self, tmp_path, monkeypatch):
        """A notation with fewer or more than 3 parts returns None."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        monkeypatch.setenv('HOME', str(tmp_path))

        assert ns._resolve_notation_by_target('two:parts') is None
        assert ns._resolve_notation_by_target('too:many:parts:here') is None
        assert ns._resolve_notation_by_target('') is None


# =============================================================================
# Tests: generate_executor injects resolver placeholders
# =============================================================================


class TestGenerateExecutorInjectsResolver:
    """Verify that the generator correctly replaces {{TARGET_AWARE_RESOLVER}} and {{EXECUTOR_TARGET}}."""

    def _generate_to_tmp(
        self,
        tmp_path: Path,
        module,
        target: str,
        monkeypatch,
    ) -> Path:
        """Run generate_executor → target file and return its path."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        # Use the real marketplace for base_path
        base_path = module.get_base_path(use_marketplace=True)

        # Run with empty mappings (we only care about the resolver injection)
        ok = module.generate_executor({}, base_path, dry_run=False, target=target)
        assert ok, 'generate_executor returned False'

        generated = plan_dir / 'execute-script.py'
        assert generated.exists(), f'Expected executor at {generated}'
        return generated

    def test_claude_executor_contains_plugin_cache_reference(self, tmp_path, monkeypatch):
        """Generated Claude executor references the plugin-cache path."""
        module = _load_generate_executor()
        generated = self._generate_to_tmp(tmp_path, module, 'claude', monkeypatch)
        content = generated.read_text(encoding='utf-8')
        assert 'plugins' in content and 'cache' in content, (
            'Claude executor must contain plugin-cache reference in resolver'
        )

    def test_opencode_executor_contains_opencode_roots(self, tmp_path, monkeypatch):
        """Generated OpenCode executor contains the 7-root walk references."""
        module = _load_generate_executor()
        generated = self._generate_to_tmp(tmp_path, module, 'opencode', monkeypatch)
        content = generated.read_text(encoding='utf-8')
        assert '.opencode/skills' in content, 'OpenCode executor must reference .opencode/skills'
        assert 'OPENCODE_CONFIG_DIR' in content, 'OpenCode executor must honour OPENCODE_CONFIG_DIR'

    def test_executor_target_comment_injected(self, tmp_path, monkeypatch):
        """The {{EXECUTOR_TARGET}} placeholder is replaced with the actual target."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            generated = self._generate_to_tmp(tmp_path, module, target, monkeypatch)
            content = generated.read_text(encoding='utf-8')
            assert f'target: {target}' in content, (
                f'Expected "target: {target}" in executor header comment for {target!r}'
            )

    def test_no_unresolved_placeholders(self, tmp_path, monkeypatch):
        """The generated executor must not contain any {{...}} template tokens."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            generated = self._generate_to_tmp(tmp_path, module, target, monkeypatch)
            content = generated.read_text(encoding='utf-8')
            unresolved = re.findall(r'\{\{[A-Z_]+\}\}', content)
            assert unresolved == [], (
                f'Target {target!r}: unresolved template tokens in executor: {unresolved}'
            )

    def test_resolve_notation_calls_target_resolver(self, tmp_path, monkeypatch):
        """The generated executor's resolve_notation calls _resolve_notation_by_target."""
        module = _load_generate_executor()
        generated = self._generate_to_tmp(tmp_path, module, 'claude', monkeypatch)
        content = generated.read_text(encoding='utf-8')
        assert '_resolve_notation_by_target(' in content, (
            'resolve_notation must delegate to _resolve_notation_by_target'
        )


# =============================================================================
# Tests: cmd_generate --target flag
# =============================================================================


class TestCmdGenerateTargetFlag:
    """Tests for the --target flag on the generate subcommand."""

    def test_help_mentions_target_flag(self):
        """generate --help lists the --target flag."""
        import subprocess

        env = os.environ.copy()
        pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
        env['PYTHONPATH'] = (
            f'{pythonpath}{os.pathsep}{env["PYTHONPATH"]}' if 'PYTHONPATH' in env else pythonpath
        )
        result = subprocess.run(
            [sys.executable, str(GENERATE_SCRIPT), 'generate', '--help'],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0
        assert '--target' in result.stdout, '--target flag must appear in generate --help'

    def test_executor_target_in_toon_output(self, tmp_path, monkeypatch):
        """cmd_generate result dict contains executor_target key."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        # Build a minimal args namespace
        class FakeArgs:
            marketplace = True
            marketplace_root = MARKETPLACE_ROOT.parent.parent  # project root
            dry_run = False
            force = False
            target = 'opencode'

        result = module.cmd_generate(FakeArgs())

        assert result.get('status') == 'success', f'Expected success, got {result}'
        assert result.get('executor_target') == 'opencode', (
            f'Expected executor_target=opencode, got {result}'
        )
