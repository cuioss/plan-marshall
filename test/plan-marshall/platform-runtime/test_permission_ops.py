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

import ast
import json
from pathlib import Path
from typing import Any

import pytest

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
from runtime_base import PERMISSION_FIX_OPERATIONS
from toon_parser import parse_toon

from conftest import get_script_path, run_script


def _parse(output: str) -> dict[str, Any]:
    return parse_toon(output)


def _code_string_literals(source: str) -> list[str]:
    """Return every string literal in ``source`` EXCEPT docstrings.

    A delegation guard asks whether a module RESOLVES a path, and a raw substring
    scan over the file text cannot answer that: it reads a docstring naming the
    resolver a module delegates to exactly as it reads an inlined path the module
    resolves itself. Narrowing the scan to non-docstring literals restores the
    question the guard means to ask — code is still fully covered, and only prose
    stops being mistaken for it.
    """
    tree = ast.parse(source)
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        first = node.body[0] if node.body else None
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            docstring_nodes.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstring_nodes
    ]


def _inlines_a_claude_settings_path(literals: list[str]) -> bool:
    """Whether ``literals`` spell out a ``.claude`` settings path in either form.

    Two spellings reach the same place and both count: one literal carrying the
    joined ``.claude/settings`` segment, or a bare ``.claude`` literal paired with
    a ``settings*.json`` filename literal for a ``Path('.claude') / 'settings.json'``
    style join. Keeping both arms is what stops the guard degrading into a check
    that only one way of writing the defect can trip.
    """
    if any('.claude/settings' in literal for literal in literals):
        return True
    return '.claude' in literals and any(
        literal.startswith('settings') and literal.endswith('.json') for literal in literals
    )


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

        source = Path(claude_runtime.__file__).read_text(encoding='utf-8')
        tree = ast.parse(source)
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)
        assert 'permission_common' not in imported_modules, (
            'claude_runtime back-imports permission_common — back-import not eliminated'
        )
        assert 'permission_doctor' not in imported_modules, (
            'claude_runtime back-imports permission_doctor — back-import not eliminated'
        )

    def test_runtime_defines_settings_path_resolution(self) -> None:
        """The runtime owns the project + global settings-path resolvers."""
        assert callable(_claude_project_settings_path)
        assert callable(_claude_global_settings_path)

    def test_project_settings_path_prefers_settings_json_when_present(self, tmp_path: Path) -> None:
        """_claude_project_settings_path prefers settings.json when it exists."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True)
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')

        resolved = _claude_project_settings_path(str(tmp_path))
        assert resolved == claude_dir / 'settings.json'

    def test_project_settings_path_falls_back_to_local_when_settings_json_absent(self, tmp_path: Path) -> None:
        """_claude_project_settings_path falls back to settings.local.json."""
        resolved = _claude_project_settings_path(str(tmp_path))
        assert resolved == tmp_path / '.claude' / 'settings.local.json'

    def test_global_settings_path_is_under_home_claude(self) -> None:
        """_claude_global_settings_path resolves under ~/.claude."""
        resolved = _claude_global_settings_path()
        assert resolved.name == 'settings.json'
        assert resolved.parent.name == '.claude'

    def test_load_settings_returns_skeleton_for_missing_file(self, tmp_path: Path) -> None:
        """_load_settings returns the empty-permissions skeleton when the file is absent."""
        data = _load_settings(tmp_path / 'nope.json')
        assert data['permissions']['allow'] == []
        assert data['permissions']['deny'] == []
        assert data['permissions']['ask'] == []

    def test_load_settings_reports_error_on_malformed_json(self, tmp_path: Path) -> None:
        """_load_settings surfaces a parse error rather than raising."""
        bad = tmp_path / 'bad.json'
        bad.write_text('{not json', encoding='utf-8')
        data = _load_settings(bad)
        assert 'error' in data
        assert data['permissions']['allow'] == []

    def test_load_settings_backfills_missing_permission_keys(self, tmp_path: Path) -> None:
        """_load_settings backfills allow/deny/ask when a real file omits them."""
        path = tmp_path / 'settings.json'
        path.write_text(json.dumps({'permissions': {'allow': ['Read(**)']}}), encoding='utf-8')
        data = _load_settings(path)
        assert data['permissions']['allow'] == ['Read(**)']
        assert data['permissions']['deny'] == []
        assert data['permissions']['ask'] == []

    def test_save_then_load_round_trips(self, tmp_path: Path) -> None:
        """_save_settings + _load_settings round-trip a permission list."""
        path = tmp_path / '.claude' / 'settings.json'
        payload = {'permissions': {'allow': ['Skill(foo:*)'], 'deny': [], 'ask': []}}
        assert _save_settings(path, payload) is True
        assert _load_settings(path)['permissions']['allow'] == ['Skill(foo:*)']

    def test_runtime_owns_skill_permission_covered(self) -> None:
        """_skill_permission_covered (relocated from permission_doctor) lives in the runtime."""
        assert _skill_permission_covered('foo', ['Skill(foo)']) == 'Skill(foo)'
        assert _skill_permission_covered('foo', ['Skill(foo:*)']) == 'Skill(foo:*)'
        assert _skill_permission_covered('foo', ['Skill(bar)']) is None

    def test_runtime_owns_marshal_step_extraction(self, tmp_path: Path) -> None:
        """_load_marshal_config + _extract_project_steps live in the runtime."""
        marshal = tmp_path / 'marshal.json'
        marshal.write_text(
            json.dumps({'plan': {'phase-6-finalize': {'steps': ['project:my-step', 'push']}}}),
            encoding='utf-8',
        )
        config, err = _load_marshal_config(str(marshal))
        assert err is None
        steps = _extract_project_steps(config)
        assert steps == [{'skill': 'my-step', 'step': 'project:my-step', 'phase': 'phase-6-finalize'}]

    def test_marshal_config_reports_error_for_missing_file(self, tmp_path: Path) -> None:
        """_load_marshal_config returns an error string for an absent marshal.json."""
        _config, err = _load_marshal_config(str(tmp_path / 'absent.json'))
        assert err is not None


class TestWriteOpsFailClosedOnMalformedSettings:
    """The five write ops fail closed (invalid_settings) rather than clobbering a malformed file."""

    def _malformed_settings(self, tmp_path: Path) -> Path:
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{not valid json', encoding='utf-8')
        return path

    def _pin_scope_path(self, monkeypatch, settings_path: Path) -> None:
        monkeypatch.setattr(claude_runtime, '_settings_path_for_scope', lambda scope: settings_path)

    def test_configure_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_configure(
                'project', [{'kind': 'path', 'tool': 'Read', 'path': '**'}]
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_settings'
        assert settings.read_bytes() == before

    def test_fix_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'project', 'add', [{'kind': 'path', 'tool': 'Read', 'path': '**'}], False
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_settings'
        assert settings.read_bytes() == before

    def test_ensure_wildcards_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_ensure_wildcards('project', str(tmp_path / 'marketplace'), False)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_settings'
        assert settings.read_bytes() == before

    def test_ensure_steps_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        # A VALID marshal so the marshal guard passes and the settings guard is reached.
        marshal = tmp_path / 'marshal.json'
        marshal.write_text(json.dumps({'plan': {}}), encoding='utf-8')
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(claude_runtime.ClaudeRuntime().permission_ensure_steps(str(marshal), 'project', False))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_settings'
        assert settings.read_bytes() == before

    def test_web_apply_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        settings = self._malformed_settings(tmp_path)
        before = settings.read_bytes()
        self._pin_scope_path(monkeypatch, settings)
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_web_apply('project', add=['a.com'], remove=[], dry_run=False)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_settings'
        assert settings.read_bytes() == before


class TestAuditOpsFailClosedOnMalformedMarshal:
    """permission_analyze / permission_ensure_steps reject a malformed marshal.json (invalid_marshal)."""

    def _malformed_marshal(self, tmp_path: Path) -> Path:
        marshal = tmp_path / 'marshal.json'
        marshal.write_text('{not valid json', encoding='utf-8')
        return marshal

    def test_analyze_fails_closed_on_malformed_marshal(self, tmp_path: Path, monkeypatch) -> None:
        marshal = self._malformed_marshal(tmp_path)
        # Settings need not exist — analyze tolerates malformed/absent settings (read-only).
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path / 'home'))
        result = _parse(claude_runtime.ClaudeRuntime().permission_analyze('both', ['missing-steps'], str(marshal)))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_marshal'

    def test_ensure_steps_fails_closed_on_malformed_marshal(self, tmp_path: Path, monkeypatch) -> None:
        marshal = self._malformed_marshal(tmp_path)
        settings = tmp_path / '.claude' / 'settings.json'
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({'permissions': {'allow': []}}), encoding='utf-8')
        before = settings.read_bytes()
        monkeypatch.setattr(claude_runtime, '_settings_path_for_scope', lambda scope: settings)
        result = _parse(claude_runtime.ClaudeRuntime().permission_ensure_steps(str(marshal), 'project', False))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_marshal'
        # The malformed-marshal guard fires before any settings write.
        assert settings.read_bytes() == before


# =============================================================================
# 2. The four permission scripts DELEGATE to the runtime layer
# =============================================================================


class TestScriptsDelegateToRuntime:
    """The tools-permission-* scripts no longer own settings path resolution / I/O."""

    def test_permission_common_imports_runtime_helpers(self) -> None:
        """permission_common delegates path-resolution + load/save to the active runtime."""
        source = Path(permission_common.__file__).read_text(encoding='utf-8')
        # D3: routing through the registry, never a direct claude_runtime import.
        assert 'from claude_runtime import' not in source
        assert '_runtime_for_target' in source

    def test_permission_common_path_for_write_delegates(self, tmp_path: Path) -> None:
        """get_project_settings_path_for_write resolves identically to the runtime."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True)
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        delegated = permission_common.get_project_settings_path_for_write(tmp_path)
        assert delegated == _claude_project_settings_path(str(tmp_path))

    def test_permission_common_global_path_delegates(self) -> None:
        """get_global_settings_path resolves identically to the runtime."""
        assert permission_common.get_global_settings_path() == _claude_global_settings_path()

    def test_permission_common_load_settings_path_delegates(self, tmp_path: Path) -> None:
        """load_settings_path returns the same skeleton the runtime produces."""
        result = permission_common.load_settings_path(tmp_path / 'nope.json')
        assert result == _load_settings(tmp_path / 'nope.json')

    def test_permission_common_load_settings_error_contract(self, tmp_path: Path) -> None:
        """load_settings (str variant) preserves its (None, error) contract via the runtime."""
        bad = tmp_path / 'bad.json'
        bad.write_text('{nope', encoding='utf-8')
        data, err = permission_common.load_settings(str(bad))
        assert data == {}
        assert err is not None

    def test_permission_common_save_settings_delegates(self, tmp_path: Path) -> None:
        """save_settings delegates the write to the runtime."""
        path = tmp_path / '.claude' / 'settings.json'
        ok = permission_common.save_settings(str(path), {'permissions': {'allow': [], 'deny': [], 'ask': []}})
        assert ok is True
        assert path.exists()

    def test_permission_doctor_imports_runtime_helpers(self) -> None:
        """permission_doctor delegates marshal/skill helpers to the active runtime."""
        source = Path(permission_doctor.__file__).read_text(encoding='utf-8')
        # D3: routing through the registry, never a direct claude_runtime import.
        assert 'from claude_runtime import' not in source
        assert '_active_runtime' in source

    def test_permission_doctor_skill_covered_delegates(self) -> None:
        """permission_doctor.skill_permission_covered delegates to the runtime."""
        assert permission_doctor.skill_permission_covered('foo', ['Skill(foo)']) == 'Skill(foo)'
        assert permission_doctor.skill_permission_covered('foo', ['Skill(bar)']) is None

    def test_permission_doctor_extract_steps_delegates(self, tmp_path: Path) -> None:
        """permission_doctor.extract_project_steps delegates to the runtime."""
        config = {'plan': {'phase-5-execute': {'steps': ['project:lint']}}}
        assert permission_doctor.extract_project_steps(config) == [
            {'skill': 'lint', 'step': 'project:lint', 'phase': 'phase-5-execute'}
        ]

    def test_permission_fix_has_no_own_claude_settings_path_resolution(self) -> None:
        """permission_fix resolves settings paths only via permission_common (-> runtime).

        It must not open-code a ``.claude/settings`` path-resolution of its own; the
        only ``.claude`` reference allowed is the plugin-cache permission VALUE it
        installs and the ``.claude-plugin`` manifest filename it scans.

        The constraint is about CODE, so the scan is too. ``resolve_settings_arg``
        documents which file the resolver it delegates to prefers, and naming that
        file is the opposite of resolving it — a module that delegates has every
        reason to say where the delegate lands. Scanning raw file text conflated
        the two and made documenting the seam indistinguishable from breaching it.
        """
        literals = _code_string_literals(Path(permission_fix.__file__).read_text(encoding='utf-8'))
        assert not _inlines_a_claude_settings_path(literals)

    @pytest.mark.parametrize(
        ('body', 'inlines'),
        [
            ("def f():\n    return Path('.claude/settings.json')\n", True),
            ("def f():\n    return Path('.claude') / 'settings.json'\n", True),
            (
                'def f():\n    """Delegates; the resolver prefers .claude/settings.local.json."""\n    return g()\n',
                False,
            ),
        ],
        ids=['joined-literal', 'segment-join', 'docstring-mention-only'],
    )
    def test_the_delegation_scan_separates_resolving_a_path_from_naming_one(self, body: str, inlines: bool) -> None:
        """The guard above still catches both inlined spellings, and only those.

        Without the two positive rows, narrowing the scan to code could silently
        become a guard that passes on everything; without the negative row, the
        prose false-positive it was narrowed to remove is not pinned as removed.
        """
        assert _inlines_a_claude_settings_path(_code_string_literals(body)) is inlines

    def test_permission_web_help_has_no_claude_settings_hardcode(self) -> None:
        """permission_web user-facing help no longer hardcodes ~/.claude/settings.json.

        Behavioural: asserts on the rendered ``--help`` output the CLI actually
        prints — the only channel through which a literal settings path can
        reach a user — instead of byte-matching the module source (a source
        comment that merely mentions the path cannot fail, and a help string
        that genuinely carries it cannot pass).
        """
        script = get_script_path('plan-marshall', 'workflow-permission-web', 'permission_web.py')
        result = run_script(script, '--help')

        assert result.returncode == 0
        # Matched control: the help-rendering channel is live. If the
        # subprocess capture silently yielded no output (broken PYTHONPATH,
        # argparse mis-route, harness failure), the absence assertions below
        # would pass vacuously — this proves the rendered text the absence
        # asserts are read from, so the negative result is meaningful.
        assert 'categorize' in result.stdout
        assert '~/.claude/settings.json' not in result.stdout
        assert '.claude/settings.local.json' not in result.stdout


# =============================================================================
# 3. OpenCode permission ops return an honest no-op (no fake-success)
# =============================================================================


class TestOpenCodePermissionsHonestNoop:
    """OpenCode has no validated permission backend — every op is an honest no-op."""

    runtime = OpenCodeRuntime()

    def _assert_noop(self, result: dict[str, Any]) -> None:
        assert result['status'] == 'no-op'
        assert 'reason' in result
        assert 'alternative' in result
        assert 'OpenCode' in result['reason']
        # Never fabricate a write-happened count.
        assert 'permissions_written' not in result
        assert 'changes_applied' not in result
        assert 'domains_added' not in result
        assert 'domains_removed' not in result
        assert 'wildcards_added' not in result

    def test_configure_is_honest_noop(self) -> None:
        self._assert_noop(
            _parse(self.runtime.permission_configure('project', [{'kind': 'path', 'tool': 'Read', 'path': '**'}]))
        )

    def test_analyze_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_analyze('both', ['all'], None)))

    def test_fix_is_honest_noop(self) -> None:
        self._assert_noop(
            _parse(
                self.runtime.permission_fix('project', 'add', [{'kind': 'path', 'tool': 'Read', 'path': '**'}], False)
            )
        )

    def test_ensure_wildcards_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_ensure_wildcards('project', 'marketplace/', False)))

    def test_ensure_steps_is_honest_noop(self, tmp_path: Path) -> None:
        marshal = tmp_path / 'marshal.json'
        marshal.write_text('{}', encoding='utf-8')
        self._assert_noop(_parse(self.runtime.permission_ensure_steps(str(marshal), 'project', False)))

    def test_web_analyze_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_web_analyze('global')))

    def test_web_apply_is_honest_noop(self) -> None:
        self._assert_noop(_parse(self.runtime.permission_web_apply('project', add=['a.com'], remove=[], dry_run=False)))

    def test_invalid_scope_still_errors_before_noop(self) -> None:
        """Scope validation still runs first — invalid scope is an error, not a no-op."""
        result = _parse(
            self.runtime.permission_configure('workspace', [{'kind': 'path', 'tool': 'Read', 'path': '**'}])
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_scope'


# =============================================================================
# 4. Cross-cutting regression: the fail-closed paths drive end-to-end via the
#    public platform-runtime dispatch router (not the bound runtime methods).
# =============================================================================


#: Placeholder the write-dispatch rows carry where a real marshal path belongs.
#: The path is only known once ``tmp_path`` exists, so the row states the SLOT and
#: the test substitutes it — keeping the table plain data rather than a callable.
_MARSHAL_SLOT = '{marshal}'

#: The argv of every write op, as the router receives it. Only the command line
#: varies: each row drives a different write op through the public dispatch
#: surface against the SAME malformed settings file, so the fail-closed rule is
#: shown to be a property of the write path rather than of one op that happens to
#: check. The ``ensure-steps`` row reads a marshal as well, which is why the slot
#: exists — its marshal is valid, so the settings guard is what refuses.
_WRITE_DISPATCH_ARGV = [
    ['permission', 'configure', '--scope', 'project', '--permissions', '{"kind":"path","tool":"Read","path":"**"}'],
    [
        'permission',
        'fix',
        '--scope',
        'project',
        '--operation',
        'add',
        '--permissions',
        '{"kind":"path","tool":"Read","path":"**"}',
    ],
    ['permission', 'ensure-wildcards', '--scope', 'project', '--marketplace-dir', 'marketplace/'],
    ['permission', 'ensure-steps', '--marshal', _MARSHAL_SLOT, '--scope', 'project'],
    ['permission', 'web-apply', '--scope', 'project', '--add', '["example.com"]'],
]

_WRITE_DISPATCH_IDS = [
    'configure',
    'fix',
    'ensure-wildcards',
    'ensure-steps',
    'web-apply',
]


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
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'claude'}}), encoding='utf-8')
        monkeypatch.chdir(tmp_path)
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True, exist_ok=True)
        return claude_dir

    def _malformed_project_settings(self, claude_dir: Path) -> Path:
        settings = claude_dir / 'settings.json'
        settings.write_text('{not valid json', encoding='utf-8')
        return settings

    def _run(self, capsys, argv: list[str]) -> dict[str, Any]:
        rc = platform_runtime.main(argv)
        assert rc == 0
        return _parse(capsys.readouterr().out)

    @pytest.mark.parametrize('argv', _WRITE_DISPATCH_ARGV, ids=_WRITE_DISPATCH_IDS)
    def test_a_write_op_fails_closed_via_dispatch(self, tmp_path, monkeypatch, capsys, argv: list[str]) -> None:
        """Every write op refuses a malformed settings file and leaves its bytes alone."""
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        settings = self._malformed_project_settings(claude_dir)
        before = settings.read_bytes()
        # A VALID marshal, so the marshal guard passes on the row that reads one
        # and the SETTINGS guard is the thing under test on every row alike.
        marshal = tmp_path / 'valid-marshal.json'
        marshal.write_text(json.dumps({'plan': {}}), encoding='utf-8')

        parsed = self._run(capsys, [str(marshal) if a == _MARSHAL_SLOT else a for a in argv])

        assert parsed['status'] == 'error'
        assert parsed['error'] == 'invalid_settings'
        assert settings.read_bytes() == before

    def test_analyze_audit_fails_closed_on_malformed_marshal_via_dispatch(self, tmp_path, monkeypatch, capsys) -> None:
        self._claude_project(tmp_path, monkeypatch)
        marshal = tmp_path / 'bad-marshal.json'
        marshal.write_text('{not valid json', encoding='utf-8')
        parsed = self._run(
            capsys,
            ['permission', 'analyze', '--scope', 'both', '--checks', 'missing-steps', '--marshal', str(marshal)],
        )
        assert parsed['status'] == 'error'
        assert parsed['error'] == 'invalid_marshal'

    def test_ensure_steps_audit_fails_closed_on_malformed_marshal_via_dispatch(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        claude_dir = self._claude_project(tmp_path, monkeypatch)
        # Valid settings so a false-success would actually write; the malformed
        # marshal must fail BEFORE any settings access.
        settings = claude_dir / 'settings.json'
        settings.write_text(json.dumps({'permissions': {'allow': []}}), encoding='utf-8')
        before = settings.read_bytes()
        marshal = tmp_path / 'bad-marshal.json'
        marshal.write_text('{not valid json', encoding='utf-8')
        parsed = self._run(
            capsys,
            ['permission', 'ensure-steps', '--marshal', str(marshal), '--scope', 'project'],
        )
        assert parsed['status'] == 'error'
        assert parsed['error'] == 'invalid_marshal'
        assert settings.read_bytes() == before


# =============================================================================
# 5. The suspicious audit scores the spelling that actually grants write access
# =============================================================================


#: The write-intent rows of ``permission analyze``'s suspicious audit, each as the
#: spelling that GRANTS the access, the severity that spelling carries, and the
#: spelling that does NOT grant it. Claude consults ``Edit(...)`` rules for file
#: writes, so a ``Write(...)`` rule over the same path grants nothing — scoring it
#: reported a risk no setting conferred while the rule that did confer it matched
#: nothing. Each row therefore carries its own negative: the pair is the contract,
#: and asserting either half alone would pass against the inverted table.
_WRITE_INTENT_AUDIT_PAIRS = [
    ('Edit(/**)', 'high', 'Write(/**)'),
    ('Edit(/tmp/**)', 'medium', 'Write(/tmp/**)'),
]

_WRITE_INTENT_AUDIT_IDS = [
    'entire-filesystem',
    'system-temp-directory',
]


class TestSuspiciousAuditScoresTheGrantingSpelling:
    """``permission analyze --checks suspicious`` over the two write-intent rows."""

    def _analyze(self, tmp_path: Path, monkeypatch, capsys, allow: list[str]) -> dict[str, Any]:
        """Audit a claude-target project whose project allow-list is exactly ``allow``."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'claude'}}), encoding='utf-8')
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / 'settings.json').write_text(
            json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}), encoding='utf-8'
        )
        monkeypatch.chdir(tmp_path)

        rc = platform_runtime.main(['permission', 'analyze', '--scope', 'project', '--checks', 'suspicious'])
        assert rc == 0
        return _parse(capsys.readouterr().out)

    @pytest.mark.parametrize(('granting', 'severity', 'inert'), _WRITE_INTENT_AUDIT_PAIRS, ids=_WRITE_INTENT_AUDIT_IDS)
    def test_the_granting_spelling_is_flagged_and_the_inert_one_is_not(
        self, tmp_path, monkeypatch, capsys, granting: str, severity: str, inert: str
    ) -> None:
        """Positive and negative in one test, so the pair cannot drift apart.

        Split across two tests, deleting the negative would leave a suite that is
        still green against a table scoring BOTH spellings — which is the state
        this asserts the audit is not in.
        """
        flagged = self._analyze(tmp_path, monkeypatch, capsys, [granting])
        assert int(flagged['total_findings']) == 1
        assert [f['severity'] for f in flagged['findings']] == [severity]

        ignored = self._analyze(tmp_path, monkeypatch, capsys, [inert])
        assert int(ignored['total_findings']) == 0

    def test_an_unrelated_row_still_fires_so_the_audit_is_not_simply_silent(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """A non-write-intent row is flagged, discriminating a correct table from a dead one.

        Every negative above is an empty finding list, and an audit that scored
        nothing at all would satisfy them all. ``Bash(sudo:*)`` was untouched by
        the re-key, so its finding proves the audit ran and reached a verdict.
        """
        parsed = self._analyze(tmp_path, monkeypatch, capsys, ['Bash(sudo:*)'])
        assert int(parsed['total_findings']) == 1
        assert [f['severity'] for f in parsed['findings']] == ['high']


# =============================================================================
# 6. Permission-list ownership — the three grounds the bounded property rests on
# =============================================================================
# tools-permission-fix/SKILL.md states that retired-rule pruning reaches `allow`
# only, calls each of its three grounds "separately checkable", and adds a
# Precondition that the property holds only while every retired rule is an
# `allow` rule. Nothing checked any of it. A document asserting its own
# verifiability while the verification does not exist is the vacuous-authority
# shape; the tests below are the checks that claim names.

_DENY_WRITING_OPERATION = 'protect-path'
"""The one `permission fix` operation taking a directory path rather than a permission descriptor."""


class TestPermissionListOwnership:
    """`deny` is written by `protect-path` alone, `ask` by nothing, retirement by `allow` only."""

    def _seeded_settings(self, tmp_path: Path, monkeypatch) -> Path:
        """An empty three-list settings file, pinned as the resolved scope path."""
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: tmp_path)
        settings_path = tmp_path / 'settings.json'
        settings_path.write_text(json.dumps({'permissions': {'allow': [], 'deny': [], 'ask': []}}), encoding='utf-8')
        monkeypatch.setattr(claude_runtime, '_settings_path_for_scope', lambda scope: settings_path)
        return settings_path

    def _argument_for(self, tmp_path: Path, operation: str) -> list[Any]:
        if operation == _DENY_WRITING_OPERATION:
            return [str(tmp_path / 'creds')]
        return [{'kind': 'path', 'tool': 'Read', 'path': '**'}]

    def test_the_operation_population_is_not_empty_and_holds_the_deny_writer(self) -> None:
        """Non-vacuity for the sweep below, plus the membership its POSITIVE row rests on.

        Kept as its own test because a parametrized sweep over an EMPTY tuple
        collects zero cases and reports green — the one failure a derived
        population cannot report about itself.

        The membership half guards the other way a green sweep can prove nothing:
        only the `_DENY_WRITING_OPERATION` row carries the positive assertion, so
        were that operation renamed or retired, every remaining row would silently
        become a negative and an implementation writing no deny rule at all would
        pass. Asserting membership queries the published set rather than mirroring
        it, so it cannot itself fall out of date.
        """
        assert PERMISSION_FIX_OPERATIONS
        assert _DENY_WRITING_OPERATION in PERMISSION_FIX_OPERATIONS, (
            f'{_DENY_WRITING_OPERATION} is absent from the published operation set '
            f'{sorted(PERMISSION_FIX_OPERATIONS)} — the sweep below would carry no positive row'
        )

    @pytest.mark.parametrize('operation', PERMISSION_FIX_OPERATIONS, ids=PERMISSION_FIX_OPERATIONS)
    def test_deny_is_written_by_protect_path_alone_and_ask_by_nothing(
        self, tmp_path: Path, monkeypatch, operation: str
    ) -> None:
        """Grounds two and three, swept over the published operation set.

        Both halves ride one test so the pair cannot drift apart: `protect-path`
        carries the POSITIVE — it must actually populate `deny` — and every other
        row carries the negative. Without the positive, an implementation that
        wrote no deny rule at all would satisfy every negative and pass.
        """
        settings_path = self._seeded_settings(tmp_path, monkeypatch)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', operation, self._argument_for(tmp_path, operation), False
            )
        )

        # The operation must have RUN. An op that refused its argument writes no
        # deny list either, so without this every negative row below would be
        # satisfied by a broken call rather than by an observed ownership rule.
        assert result['status'] == 'success', f'{operation} did not run: {result}'

        written = json.loads(settings_path.read_text(encoding='utf-8'))
        deny = written['permissions']['deny']
        ask = written['permissions']['ask']

        assert ask == [], f'{operation} populated permissions.ask with {ask} — nothing in this project writes ask'
        if operation == _DENY_WRITING_OPERATION:
            assert deny, f'{operation} is the sole deny writer but wrote none — the negative rows below prove nothing'
        else:
            assert deny == [], (
                f'{operation} wrote permissions.deny ({deny}); protect-path is meant to be its sole writer'
            )

    def test_the_retired_rule_population_is_not_empty(self) -> None:
        """Non-vacuity for the retirement sweep, for the same reason as above."""
        assert claude_runtime._RETIRED_DEFAULT_RULES

    @pytest.mark.parametrize(
        ('rule_id', 'rule'),
        claude_runtime._RETIRED_DEFAULT_RULES,
        ids=[rule_id for rule_id, _rule in claude_runtime._RETIRED_DEFAULT_RULES],
    )
    def test_a_retired_rule_is_pruned_from_allow_and_only_from_allow(
        self, tmp_path: Path, rule_id: str, rule: str
    ) -> None:
        """Ground one, and the Precondition the bounded property rests on.

        The same rule is parked in all three lists. Pruning it out of `allow`
        while leaving the `deny` and `ask` copies standing is precisely the
        documented asymmetry — and it is what fails the moment a retirement
        targets a `deny` or an `ask` rule without the pruning side being extended
        to reach it, which is the silent no-op the Precondition warns about.
        """
        settings = {'permissions': {'allow': [rule], 'deny': [rule], 'ask': [rule]}}

        result = claude_runtime.ensure_default_permissions(settings, tmp_path / 'settings.json')

        assert rule_id in result['defaults_removed']
        assert rule not in settings['permissions']['allow']
        assert settings['permissions']['deny'] == [rule], (
            f'retiring {rule_id} reached permissions.deny — the pruning side is documented as allow-only'
        )
        assert settings['permissions']['ask'] == [rule], (
            f'retiring {rule_id} reached permissions.ask — the pruning side is documented as allow-only'
        )
