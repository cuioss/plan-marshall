#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral unit tests for generate_executor.py uncovered branches.

These tests load the script in-process via ``load_script_module`` (so the real
filename is traced and the exercised lines count toward coverage) and call the
target functions directly. They cover the notation→path / marshal-target
resolution helpers, the target-aware resolver selection, project-local script
discovery, the template-substituting writer (dry-run + real-write), the
state/checksum/path helpers, the notation-drift detector, and the command
handlers / main() dispatch — all paths the existing subprocess-and-fixture suite
leaves untouched.
"""

import types
from pathlib import Path

import pytest

from conftest import load_script_module

# Unique module_name so the in-process load is distinct from the existing
# test module's ``load_module()`` exec-based load (which traces as <string>
# and does NOT count for coverage).
_gen = load_script_module(
    'plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_behavior'
)


# =============================================================================
# read_marshal_target — walk-up resolution of runtime.target from marshal.json
# =============================================================================


def test_read_marshal_target_returns_declared_target(tmp_path):
    """A marshal.json declaring runtime.target returns that target verbatim."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{"runtime": {"target": "opencode"}}', encoding='utf-8')

    assert _gen.read_marshal_target(cwd=tmp_path) == 'opencode'


def test_read_marshal_target_defaults_to_claude_when_no_marshal(tmp_path):
    """With no marshal.json anywhere up the tree, the target defaults to claude."""
    # tmp_path has no .plan/marshal.json; the walk reaches the filesystem root
    # without a hit and falls through to the documented default.
    assert _gen.read_marshal_target(cwd=tmp_path) == 'claude'


def test_read_marshal_target_defaults_to_claude_on_malformed_json(tmp_path):
    """A marshal.json that is not valid JSON resolves to the claude default."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{not valid json', encoding='utf-8')

    assert _gen.read_marshal_target(cwd=tmp_path) == 'claude'


def test_read_marshal_target_defaults_when_runtime_key_missing(tmp_path):
    """A marshal.json with no runtime.target key resolves to the claude default."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{"other": {"target": "opencode"}}', encoding='utf-8')

    assert _gen.read_marshal_target(cwd=tmp_path) == 'claude'


def test_read_marshal_target_defaults_when_runtime_not_dict(tmp_path):
    """A marshal.json whose runtime is a scalar (not a mapping) defaults to claude."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{"runtime": "claude"}', encoding='utf-8')

    assert _gen.read_marshal_target(cwd=tmp_path) == 'claude'


# =============================================================================
# generate_target_aware_resolver_code — per-target resolver selection
# =============================================================================


def test_resolver_code_for_opencode_emits_opencode_walk():
    """The opencode target emits the 7-root dash-namespaced resolver body."""
    code = _gen.generate_target_aware_resolver_code('opencode')

    assert 'def _resolve_notation_by_target(' in code
    assert 'OpenCode target' in code
    assert '.opencode/skills' in code


def test_resolver_code_for_claude_emits_plugin_cache_glob():
    """The claude target emits the plugin-cache glob resolver body."""
    code = _gen.generate_target_aware_resolver_code('claude')

    assert 'def _resolve_notation_by_target(' in code
    assert 'Claude target' in code
    assert 'plugins' in code and 'cache' in code


def test_resolver_code_for_unknown_target_falls_back_to_claude():
    """An unrecognized target falls back to the Claude resolver."""
    unknown = _gen.generate_target_aware_resolver_code('borg')
    claude = _gen.generate_target_aware_resolver_code('claude')

    assert unknown == claude


# =============================================================================
# discover_local_scripts — .claude/skills/*/scripts/*.py discovery
# =============================================================================


def test_discover_local_scripts_finds_public_scripts(tmp_path):
    """A .claude/skills/<skill>/scripts/<script>.py maps to default-bundle:skill:script."""
    scripts = tmp_path / '.claude' / 'skills' / 'my-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'do_thing.py').write_text('# script', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert 'default-bundle:my-skill:do_thing' in mappings
    assert mappings['default-bundle:my-skill:do_thing'].endswith('do_thing.py')


def test_discover_local_scripts_skips_private_modules(tmp_path):
    """Underscore-prefixed modules are excluded from local discovery."""
    scripts = tmp_path / '.claude' / 'skills' / 'my-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / '_private.py').write_text('# private', encoding='utf-8')
    (scripts / 'public.py').write_text('# public', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert 'default-bundle:my-skill:public' in mappings
    assert 'default-bundle:my-skill:_private' not in mappings


def test_discover_local_scripts_empty_when_no_local_skills(tmp_path):
    """A project with no .claude/skills/ directory yields an empty mapping."""
    assert _gen.discover_local_scripts(cwd=tmp_path) == {}


def test_discover_local_scripts_skips_hidden_skill_dirs(tmp_path):
    """A dot-prefixed skill directory under .claude/skills is skipped."""
    local = tmp_path / '.claude' / 'skills'
    hidden_scripts = local / '.hidden' / 'scripts'
    hidden_scripts.mkdir(parents=True)
    (hidden_scripts / 'sneaky.py').write_text('# sneaky', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert mappings == {}


# =============================================================================
# generate_executor — template substitution (dry-run, write, missing template)
# =============================================================================

_TEMPLATE_BODY = (
    'SCRIPTS = {\n'
    '{{SCRIPT_MAPPINGS}}\n'
    '}\n'
    'LOGGING_DIR = "{{LOGGING_DIR}}"\n'
    '{{SHARED_MODULE_DIRS}}\n'
    'EXTRA = [{{EXTRA_SCRIPT_DIRS}}]\n'
    'PLAN_DIR_NAME = "{{PLAN_DIR_NAME}}"\n'
    'EXECUTOR_TARGET = "{{EXECUTOR_TARGET}}"\n'
    '{{TARGET_AWARE_RESOLVER}}\n'
)


def _build_synthetic_base(tmp_path: Path) -> Path:
    """Create a minimal marketplace tree carrying the executor template.

    ``generate_executor`` resolves the template via
    ``get_templates_dir(base)`` → ``<base>/plan-marshall/skills/
    tools-script-executor/templates/execute-script.py.template``. Only that file
    is required for the writer to run; the logging/shared dirs resolve to
    non-existent paths and degrade gracefully.
    """
    templates = (
        tmp_path / 'base' / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates'
    )
    templates.mkdir(parents=True)
    (templates / 'execute-script.py.template').write_text(_TEMPLATE_BODY, encoding='utf-8')
    return tmp_path / 'base'


def test_generate_executor_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    """dry_run=True prints the rendered preview and writes no executor file."""
    base = _build_synthetic_base(tmp_path)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    ok = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=True, target='claude')

    assert ok is True
    out = capsys.readouterr().out
    assert '=== execute-script.py ===' in out
    assert not (plan_dir / 'execute-script.py').exists()


def test_generate_executor_writes_substituted_executor(tmp_path, monkeypatch):
    """A real write substitutes every token and lands at executor_path()."""
    base = _build_synthetic_base(tmp_path)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    ok = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')

    assert ok is True
    written = (plan_dir / 'execute-script.py').read_text(encoding='utf-8')
    # Mapping line, target token, and resolver body are all substituted.
    assert '"a:b:c": "/p/c.py"' in written
    assert 'EXECUTOR_TARGET = "claude"' in written
    assert 'def _resolve_notation_by_target(' in written
    # No raw substitution tokens survive.
    assert '{{' not in written


def test_generate_executor_returns_false_when_template_missing(tmp_path, monkeypatch):
    """A base path with no template file makes the writer return False."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    # tmp_path/'empty-base' has no plan-marshall/.../templates/ tree.
    ok = _gen.generate_executor({'a:b:c': '/p/c.py'}, tmp_path / 'empty-base', dry_run=False)

    assert ok is False


# =============================================================================
# update_state — marshall-state.toon generation metadata
# =============================================================================


def test_update_state_writes_generation_metadata(tmp_path, monkeypatch):
    """update_state writes a marshall-state.toon carrying count + checksum."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    _gen.update_state(script_count=7, checksum='deadbeef', logs_cleaned=3)

    content = (tmp_path / 'marshall-state.toon').read_text(encoding='utf-8')
    assert 'deadbeef' in content
    assert '\t7\t' in content
    assert content.rstrip().endswith('3')


# =============================================================================
# check_paths_exist — existing vs missing mapping classification
# =============================================================================


def test_check_paths_exist_partitions_existing_and_missing(tmp_path):
    """check_paths_exist returns existing notations and (notation, path) misses."""
    real = tmp_path / 'real.py'
    real.write_text('# real', encoding='utf-8')
    mappings = {
        'a:b:real': str(real),
        'a:b:ghost': str(tmp_path / 'ghost.py'),
    }

    existing, missing = _gen.check_paths_exist(mappings)

    assert existing == ['a:b:real']
    assert missing == [('a:b:ghost', str(tmp_path / 'ghost.py'))]


# =============================================================================
# verify_executor / get_executor_mappings — missing-executor branches
# =============================================================================


def test_verify_executor_returns_false_when_executor_absent(tmp_path, monkeypatch):
    """verify_executor reports (False, 0) when no executor file exists."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    valid, count = _gen.verify_executor()

    assert valid is False
    assert count == 0


def test_get_executor_mappings_empty_when_executor_absent(tmp_path, monkeypatch):
    """get_executor_mappings swallows the load failure and returns {}."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    assert _gen.get_executor_mappings() == {}


# =============================================================================
# Notation-drift detection helpers
# =============================================================================


def test_flip_notation_separators_swaps_hyphen_and_underscore():
    """Hyphens and underscores swap; other characters are unchanged."""
    assert _gen._flip_notation_separators('manage_status') == 'manage-status'
    assert _gen._flip_notation_separators('manage-status') == 'manage_status'
    assert _gen._flip_notation_separators('plainname') == 'plainname'


def test_collect_referenced_notations_scans_markdown(tmp_path):
    """References after an execute-script.py token are collected from docs."""
    (tmp_path / 'doc.md').write_text(
        'Run `python3 .plan/execute-script.py some-bundle:some-skill:some-script list`.\n',
        encoding='utf-8',
    )

    referenced = _gen._collect_referenced_notations(tmp_path)

    assert 'some-bundle:some-skill:some-script' in referenced


def test_collect_referenced_notations_empty_for_non_directory(tmp_path):
    """A non-directory base path yields an empty reference set."""
    assert _gen._collect_referenced_notations(tmp_path / 'nope') == set()


def test_detect_notation_drift_flags_separator_rename(tmp_path):
    """A caller referencing the underscore form when only the hyphen form is
    registered is flagged as drift (and vice versa)."""
    (tmp_path / 'caller.md').write_text(
        'python3 .plan/execute-script.py b:s:manage_status read\n', encoding='utf-8'
    )
    registered = {'b:s:manage-status': '/path/manage-status.py'}

    drift = _gen._detect_notation_drift(registered, tmp_path)

    assert ('b:s:manage_status', 'b:s:manage-status') in drift


def test_detect_notation_drift_empty_when_reference_registered(tmp_path):
    """A reference that IS registered produces no drift entry."""
    (tmp_path / 'caller.md').write_text(
        'python3 .plan/execute-script.py b:s:manage-status read\n', encoding='utf-8'
    )
    registered = {'b:s:manage-status': '/path/manage-status.py'}

    assert _gen._detect_notation_drift(registered, tmp_path) == []


def test_notation_drift_zero_against_clean_marketplace_source():
    """The clean marketplace SOURCE tree carries zero caller-notation drift.

    Regression pin for the drift-detector self-catalog fix: resolve the
    production ``--marketplace`` base (``get_base_path(use_marketplace=True)``
    forces the marketplace tree, ignoring the plugin-cache / auto-detected
    context), build the filename-derived registered mapping with the pure
    ``discover_scripts_fallback`` glob walk (no subprocess, deterministic), and
    assert ``_detect_notation_drift`` finds nothing over the real source.

    Any future underscore-form third-segment reference whose hyphen-form is
    registered (a half-done entrypoint rename that silently changes a public
    notation) re-fails this test, and the assertion message names the offending
    ``(referenced_notation, registered_notation)`` pairs so the drift is
    identified at failure time.
    """
    try:
        base = _gen.get_base_path(use_marketplace=True)
    except FileNotFoundError:
        pytest.skip(
            'marketplace source tree (marketplace/bundles) is not present in '
            'this checkout — caller-notation drift detection requires the '
            'marketplace source and cannot run against a deployed plugin cache'
        )
    registered = _gen.discover_scripts_fallback(base)

    drift = _gen._detect_notation_drift(registered, base)

    assert drift == [], (
        'caller-notation drift detected in marketplace source — '
        f'offending (referenced, registered) pairs: {drift}'
    )


# =============================================================================
# Command handlers + main() dispatch
# =============================================================================


def test_cmd_paths_error_when_no_mappings(tmp_path, monkeypatch):
    """cmd_paths returns an error result when the executor mappings are empty."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    result = _gen.cmd_paths(types.SimpleNamespace())

    assert result['status'] == 'error'
    assert 'Could not read executor mappings' in result['error']


def test_cmd_drift_error_when_no_mappings(tmp_path, monkeypatch):
    """cmd_drift returns an error result when the executor mappings are empty."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    result = _gen.cmd_drift(types.SimpleNamespace(marketplace=False, marketplace_root=None))

    assert result['status'] == 'error'
    assert 'Could not read executor mappings' in result['error']


def test_cmd_cleanup_reports_deleted_count(tmp_path, monkeypatch):
    """cmd_cleanup returns the number of logs deleted (zero on an empty tree)."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    result = _gen.cmd_cleanup(types.SimpleNamespace(max_age_days=7))

    assert result['status'] == 'success'
    assert result['deleted'] == 0


def test_main_cleanup_dispatch_returns_zero(tmp_path, monkeypatch, capsys):
    """main() routes the cleanup subcommand and emits a TOON success result."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_gen.sys, 'argv', ['generate_executor.py', 'cleanup', '--max-age-days', '30'])

    rc = _gen.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert 'success' in out
