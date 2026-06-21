#!/usr/bin/env python3
"""Tests for skill-resolution commands in manage-config.

Tests resolve-domain-skills, resolve-workflow-skill-extension, get-skills-by-profile,
list-finalize-steps commands defined in _cmd_skill_resolution.py.

Tier 2 (direct import) tests with 1 subprocess test for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest
from _layout_sim import build_phase_layout
from test_helpers import SCRIPT_PATH, create_marshal_json, create_nested_marshal_json

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')
_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')
_config_defaults = _load_module('_config_defaults', '_config_defaults.py')

cmd_get_skills_by_profile = _cmd_skill_resolution.cmd_get_skills_by_profile
cmd_list_finalize_steps = _cmd_skill_resolution.cmd_list_finalize_steps
cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills
cmd_resolve_workflow_skill_extension = _cmd_skill_resolution.cmd_resolve_workflow_skill_extension

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script  # noqa: E402

# =============================================================================
# resolve-domain-skills Tests (Tier 2)
# =============================================================================


def test_resolve_domain_skills_java_implementation(plan_context, monkeypatch):
    """Test resolve-domain-skills for java + implementation profile."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

    assert result['status'] == 'success'
    defaults_str = str(result['defaults'])
    assert 'pm-dev-java:java-core' in defaults_str
    optionals_str = str(result['optionals'])
    assert 'pm-dev-java:java-cdi' in optionals_str
    # Should NOT include testing defaults
    assert 'pm-dev-java:junit-core' not in defaults_str


def test_resolve_domain_skills_java_testing(plan_context, monkeypatch):
    """Test resolve-domain-skills for java + module_testing profile."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='module_testing'))

    assert result['status'] == 'success'
    defaults_str = str(result['defaults'])
    optionals_str = str(result['optionals'])
    assert 'pm-dev-java:java-core' in defaults_str
    assert 'pm-dev-java:junit-core' in defaults_str
    assert 'pm-dev-java:junit-integration' in optionals_str
    # Should NOT include implementation optionals
    assert 'pm-dev-java:java-cdi' not in optionals_str


def test_resolve_domain_skills_javascript_implementation(plan_context, monkeypatch):
    """Test resolve-domain-skills for javascript + implementation profile."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='javascript', profile='implementation'))

    assert result['status'] == 'success'
    defaults_str = str(result['defaults'])
    optionals_str = str(result['optionals'])
    assert 'pm-dev-frontend:javascript' in defaults_str
    assert 'pm-dev-frontend:lint-config' in optionals_str


def test_resolve_domain_skills_unknown_domain(plan_context, monkeypatch):
    """Test resolve-domain-skills with unknown domain returns error."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='unknown', profile='implementation'))

    assert result['status'] == 'error'
    assert 'unknown' in result['error'].lower()


def test_resolve_domain_skills_unknown_profile(plan_context, monkeypatch):
    """Test resolve-domain-skills with unknown profile returns error."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='invalid-profile'))

    assert result['status'] == 'error'
    assert 'profile' in result['error'].lower()


def test_resolve_domain_skills_java_quality(plan_context, monkeypatch):
    """Test resolve-domain-skills for java + quality profile (finalize phase)."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='quality'))

    assert result['status'] == 'success'
    defaults_str = str(result['defaults'])
    assert 'pm-dev-java:java-core' in defaults_str
    assert 'pm-dev-java:javadoc' in defaults_str


# =============================================================================
# resolve-workflow-skill-extension Tests (Tier 2)
# =============================================================================


def test_resolve_workflow_skill_extension_java_outline(plan_context, monkeypatch):
    """Test resolve-workflow-skill-extension returns outline extension for java."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_workflow_skill_extension(Namespace(domain='java', type='outline'))

    assert result['status'] == 'success'
    assert result['extension'] == 'pm-dev-java:ext-outline-java'
    assert result['domain'] == 'java'
    assert result['type'] == 'outline'


def test_resolve_workflow_skill_extension_java_triage(plan_context, monkeypatch):
    """Test resolve-workflow-skill-extension returns triage extension for java."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_workflow_skill_extension(Namespace(domain='java', type='triage'))

    assert result['status'] == 'success'
    assert result['extension'] == 'pm-dev-java:ext-triage-java'


def test_resolve_workflow_skill_extension_javascript_outline(plan_context, monkeypatch):
    """Test resolve-workflow-skill-extension returns outline extension for javascript."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_workflow_skill_extension(Namespace(domain='javascript', type='outline'))

    assert result['status'] == 'success'
    assert result['extension'] == 'pm-dev-frontend:ext-outline-frontend'


def test_resolve_workflow_skill_extension_missing_type(plan_context, monkeypatch):
    """Test resolve-workflow-skill-extension returns null for missing extension type."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_workflow_skill_extension(Namespace(domain='javascript', type='triage'))

    assert result['status'] == 'success'
    assert result['extension'] is None


def test_resolve_workflow_skill_extension_unknown_domain(plan_context, monkeypatch):
    """Test resolve-workflow-skill-extension returns null for unknown domain (not error)."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_workflow_skill_extension(Namespace(domain='unknown', type='outline'))

    assert result['status'] == 'success'
    assert result['extension'] is None


def test_resolve_workflow_skill_extension_plugin_dev(plan_context, monkeypatch):
    """Test resolve-workflow-skill-extension returns extensions for plugin-dev domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_workflow_skill_extension(
        Namespace(
            domain='plan-marshall-plugin-dev',
            type='outline',
        )
    )

    assert result['status'] == 'success'
    assert result['extension'] == 'pm-plugin-development:ext-outline-workflow'


# =============================================================================
# get-skills-by-profile Tests (Tier 2)
# =============================================================================


def test_get_skills_by_profile_java(plan_context, monkeypatch):
    """Test get-skills-by-profile loads profile-keyed skills from extension.py."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_get_skills_by_profile(Namespace(domain='java'))

    assert result['status'] == 'success'
    assert 'skills_by_profile' in result
    assert 'implementation' in result['skills_by_profile']
    assert 'module_testing' in result['skills_by_profile']
    # integration_testing should NOT appear as standalone profile for java
    assert 'integration_testing' not in result['skills_by_profile']


def test_get_skills_by_profile_includes_core_skills(plan_context, monkeypatch):
    """Test get-skills-by-profile includes core skills in all profiles."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_get_skills_by_profile(Namespace(domain='java'))

    assert result['status'] == 'success'
    # Core skill should appear in every profile
    for profile_skills in result['skills_by_profile'].values():
        assert 'pm-dev-java:java-core' in profile_skills


def test_get_skills_by_profile_includes_profile_skills(plan_context, monkeypatch):
    """Test get-skills-by-profile includes profile-specific skills."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_get_skills_by_profile(Namespace(domain='java'))

    assert result['status'] == 'success'
    assert 'pm-dev-java:junit-core' in result['skills_by_profile']['module_testing']


def test_get_skills_by_profile_javascript(plan_context, monkeypatch):
    """Test get-skills-by-profile works for javascript domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_get_skills_by_profile(Namespace(domain='javascript'))

    assert result['status'] == 'success'
    assert 'skills_by_profile' in result
    all_skills = str(result['skills_by_profile'])
    assert 'pm-dev-frontend:javascript' in all_skills


def test_get_skills_by_profile_unknown_domain(plan_context, monkeypatch):
    """Test get-skills-by-profile returns error for unknown domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_get_skills_by_profile(Namespace(domain='unknown'))

    assert result['status'] == 'error'
    assert 'unknown' in result['error'].lower()


def test_get_skills_by_profile_flat_domain_fallback(plan_context, monkeypatch):
    """Test get-skills-by-profile returns core skills for flat structure domain (no bundle)."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_get_skills_by_profile(Namespace(domain='java'))

    assert result['status'] == 'success'
    assert 'skills_by_profile' in result


# =============================================================================
# configure-execute-task-skills / resolve-execute-task-skill removal (Tier 2)
#
# The configure-execute-task-skills and resolve-execute-task-skill CLI verbs
# were removed: their handler functions no longer exist on
# _cmd_skill_resolution, and neither verb appears in the manage-config or
# query-config argparse choices. These tests pin that absence.
# =============================================================================


def test_execute_task_skill_handlers_removed_from_module():
    """The two execute-task-skill handler functions no longer exist on the module."""
    assert not hasattr(_cmd_skill_resolution, 'cmd_configure_execute_task_skills'), (
        'cmd_configure_execute_task_skills must be removed from _cmd_skill_resolution'
    )
    assert not hasattr(_cmd_skill_resolution, 'cmd_resolve_execute_task_skill'), (
        'cmd_resolve_execute_task_skill must be removed from _cmd_skill_resolution'
    )


@pytest.mark.parametrize(
    'verb',
    ['configure-execute-task-skills', 'resolve-execute-task-skill'],
)
def test_removed_verb_rejected_by_manage_config(verb, plan_context):
    """manage-config rejects each removed verb as an unknown argparse choice."""
    result = run_script(SCRIPT_PATH, verb, cwd=plan_context.fixture_dir)

    assert result.returncode == 2, (
        f'manage-config must reject removed verb {verb!r} with exit code 2 '
        f'(got {result.returncode})'
    )
    assert 'invalid choice' in result.stderr, (
        f'expected an argparse invalid-choice rejection for {verb!r}, got: {result.stderr!r}'
    )


@pytest.mark.parametrize(
    'verb',
    ['configure-execute-task-skills', 'resolve-execute-task-skill'],
)
def test_removed_verb_rejected_by_query_config(verb, plan_context):
    """query-config rejects each removed verb as an unknown argparse choice."""
    query_script = get_script_path('plan-marshall', 'script-shared', 'query/query-config.py')
    result = run_script(query_script, verb, cwd=plan_context.fixture_dir)

    assert result.returncode == 2, (
        f'query-config must reject removed verb {verb!r} with exit code 2 '
        f'(got {result.returncode})'
    )
    assert 'invalid choice' in result.stderr, (
        f'expected an argparse invalid-choice rejection for {verb!r}, got: {result.stderr!r}'
    )


# =============================================================================
# list-finalize-steps Tests (Tier 2)
# =============================================================================


def test_list_finalize_steps_returns_built_in(plan_context, monkeypatch):
    """Test list-finalize-steps returns built-in steps with default: prefix."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_list_finalize_steps(Namespace())

    assert result['status'] == 'success'
    step_names = [s['name'] for s in result['steps']]
    assert 'default:commit-push' in step_names
    assert 'default:create-pr' in step_names
    assert 'default:record-metrics' in step_names
    assert 'default:archive-plan' in step_names
    assert 'default:branch-cleanup' in step_names


def test_list_finalize_steps_count(plan_context, monkeypatch):
    """Test list-finalize-steps returns correct count for built-in steps."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_list_finalize_steps(Namespace())

    assert result['status'] == 'success'
    assert result['count'] >= 7


def test_list_finalize_steps_surfaces_finalize_step_simplify(plan_context, monkeypatch):
    """list-finalize-steps surfaces default:finalize-step-simplify with its description."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_list_finalize_steps(Namespace())

    assert result['status'] == 'success'
    simplify = next(
        (s for s in result['steps'] if s['name'] == 'default:finalize-step-simplify'),
        None,
    )
    assert simplify is not None, (
        'default:finalize-step-simplify must be surfaced by list-finalize-steps'
    )
    assert simplify['description'], (
        'default:finalize-step-simplify must carry a non-empty description'
    )


def test_list_finalize_steps_discovers_project_skills(plan_context):
    """Test list-finalize-steps discovers project-local finalize-step-* skills.

    Scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    create_marshal_json(plan_context.fixture_dir)

    skill_dir = plan_context.fixture_dir / '.claude' / 'skills' / 'finalize-step-hello-world'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-hello-world\ndescription: Hello World\n---\n\n# Hello World\n'
    )

    result = run_script(SCRIPT_PATH, 'list-finalize-steps', cwd=plan_context.fixture_dir)

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'project:finalize-step-hello-world' in result.stdout
    assert 'Hello World' in result.stdout


# =============================================================================
# list-finalize-steps ordering tests (lock in sync-plugin-cache head placement)
# =============================================================================


def _run_discovery_in_cwd(cwd: Path) -> list[dict]:
    """Invoke _discover_all_finalize_steps() with cwd switched to the given path.

    The discovery scans ``.claude/skills/`` relative to the process cwd, so tests
    that exercise project-level skill ordering must chdir into an isolated temp
    directory that contains the desired skill layout. The real
    ``cmd_list_finalize_steps`` wraps the discovery; we call the inner helper
    directly to get the raw list without TOON serialization.

    Uses an isolated ``tmp_path`` (rather than the shared PlanContext fixture
    directory) so per-test ``.claude/skills/`` layouts cannot contaminate
    neighboring tests.
    """
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return _cmd_skill_resolution._discover_all_finalize_steps()
    finally:
        os.chdir(original_cwd)


def test_list_finalize_steps_without_sync_skill_starts_with_built_ins(tmp_path):
    """Without a sync-plugin-cache project skill, output starts with built-in steps."""
    # tmp_path has no .claude/skills directory -> built-ins come first.
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    assert len(steps) > 0
    # First entry must be a built-in default: step (not a project:sync-plugin-cache)
    first = steps[0]
    assert first['source'] == 'built-in'
    assert first['name'].startswith('default:')
    # And no project:finalize-step-sync-plugin-cache anywhere in the list
    names = [s['name'] for s in steps]
    assert 'project:finalize-step-sync-plugin-cache' not in names


def test_list_finalize_steps_special_case_branch_retired(tmp_path):
    """After cluster 02 the resolver no longer special-cases sync-plugin-cache.

    Pre-cluster-02, ``_discover_all_finalize_steps`` had a hard-coded branch
    that placed ``project:finalize-step-sync-plugin-cache`` at index 0 of the
    candidate list whenever ``.claude/skills/finalize-step-sync-plugin-cache/``
    existed. Cluster 02 retired that branch — sync-plugin-cache is now an
    ordinary project-local finalize-step skill (Source 2), discovered the same
    way as ``finalize-step-plugin-doctor`` and ``finalize-step-deploy-target``.
    """
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]

    # Sync-plugin-cache is NOT a built-in default after relocation.
    assert 'default:sync-plugin-cache' not in names
    # Deploy-target is also NOT a built-in default.
    assert 'default:deploy-target' not in names

    # All entries before the first project: step (if any) must be built-ins —
    # the special-case "sync skill first" branch is retired, so any project:
    # skill (sync-plugin-cache included) flows through Source 2 and lands
    # AFTER all built-ins.
    project_indices = [i for i, s in enumerate(steps) if s['source'] == 'project']
    if project_indices:
        first_project_idx = min(project_indices)
        for i in range(first_project_idx):
            assert steps[i]['source'] == 'built-in'


def test_list_finalize_steps_other_project_skills_remain_after_built_ins(tmp_path):
    """All built-ins precede project skills (Source 2 ordering invariant)."""
    other_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-zzz-other'
    other_dir.mkdir(parents=True)
    (other_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-zzz-other\ndescription: Another project finalize step\n---\n\n# Other\n'
    )

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]
    other_idx = names.index('project:finalize-step-zzz-other')

    built_in_indices = [i for i, s in enumerate(steps) if s['source'] == 'built-in']
    assert built_in_indices, 'Expected built-in steps in output'
    assert max(built_in_indices) < other_idx, (
        'Built-ins must precede project skills'
    )


def test_list_finalize_steps_extension_steps_come_last(tmp_path):
    """Extension-contributed steps appear after all built-in and project steps."""

    class _FakeExtModule:
        @staticmethod
        def provides_finalize_steps():
            return [
                {'name': 'ext:finalize-step-from-extension', 'description': 'Provided by extension'},
            ]

    fake_extensions = [{'bundle': 'fake-bundle', 'module': _FakeExtModule()}]

    # Drop in a generic project finalize-step-* skill to cover the full
    # ordering contract (built-ins → project skills → extension skills).
    skills_root = tmp_path / '.claude' / 'skills'
    other_dir = skills_root / 'finalize-step-zzz-other'
    other_dir.mkdir(parents=True)
    (other_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-zzz-other\ndescription: Other project finalize step\n---\n\n# Other\n'
    )

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=fake_extensions):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]
    assert 'ext:finalize-step-from-extension' in names

    ext_idx = names.index('ext:finalize-step-from-extension')
    # Every non-extension entry must precede the extension entry
    for idx, step in enumerate(steps):
        if step['source'] == 'extension':
            continue
        assert idx < ext_idx, (
            f'Non-extension step {step["name"]!r} at {idx} must come before extension step at {ext_idx}'
        )
    # And the extension entry carries source=extension
    assert steps[ext_idx]['source'] == 'extension'


# =============================================================================
# Order field discovery tests (deliverable 5)
# =============================================================================


def test_read_frontmatter_order_parses_int(tmp_path):
    """_read_frontmatter_order returns the int value from frontmatter."""
    md = tmp_path / 'skill.md'
    md.write_text('---\nname: foo\ndescription: bar\norder: 42\n---\n\n# Foo\n')

    assert _cmd_skill_domains._read_frontmatter_order(md) == 42


def test_read_frontmatter_order_missing_returns_none(tmp_path):
    """_read_frontmatter_order returns None when the frontmatter has no order key."""
    md = tmp_path / 'skill.md'
    md.write_text('---\nname: foo\ndescription: bar\n---\n\n# Foo\n')

    assert _cmd_skill_domains._read_frontmatter_order(md) is None


def test_read_frontmatter_order_no_frontmatter_returns_none(tmp_path):
    """_read_frontmatter_order returns None when the file has no frontmatter."""
    md = tmp_path / 'skill.md'
    md.write_text('# Foo\n\nJust body content.\n')

    assert _cmd_skill_domains._read_frontmatter_order(md) is None


def test_read_frontmatter_order_missing_file_returns_none(tmp_path):
    """_read_frontmatter_order returns None when the path does not exist."""
    missing = tmp_path / 'nope.md'

    assert _cmd_skill_domains._read_frontmatter_order(missing) is None


def test_read_frontmatter_order_tolerates_trailing_comment(tmp_path):
    """Trailing YAML comments after the order value are ignored."""
    md = tmp_path / 'skill.md'
    md.write_text('---\nname: foo\norder: 10 # pinned early\n---\n\n# Foo\n')

    assert _cmd_skill_domains._read_frontmatter_order(md) == 10


def test_read_frontmatter_order_tolerates_crlf(tmp_path):
    """CRLF line endings do not prevent the regex from matching."""
    md = tmp_path / 'skill.md'
    md.write_bytes(b'---\r\nname: foo\r\norder: 7\r\n---\r\n\r\n# Foo\r\n')

    assert _cmd_skill_domains._read_frontmatter_order(md) == 7


def test_list_finalize_steps_builtins_have_order(tmp_path):
    """Built-in finalize steps carry order values parsed from standards/*.md frontmatter."""
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    by_name = {s['name']: s for s in steps if s['source'] == 'built-in'}
    assert by_name['default:commit-push']['order'] == 10
    assert by_name['default:create-pr']['order'] == 20
    assert by_name['default:automated-review']['order'] == 30
    assert by_name['default:archive-plan']['order'] == 1000
    assert by_name['default:record-metrics']['order'] == 998


def test_list_finalize_steps_project_skill_order_from_frontmatter(tmp_path):
    """Project finalize-step-* skills expose the `order` declared in their SKILL.md."""
    skill_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-custom'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-custom\ndescription: Custom\norder: 150\n---\n\n# Custom\n'
    )

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    custom = next(s for s in steps if s['name'] == 'project:finalize-step-custom')
    assert custom['order'] == 150


def test_list_finalize_steps_project_skill_without_order_returns_none(tmp_path):
    """Project finalize-step-* skill without `order` frontmatter exposes order: None."""
    skill_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-bare'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('---\nname: finalize-step-bare\ndescription: Bare\n---\n\n# Bare\n')

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    bare = next(s for s in steps if s['name'] == 'project:finalize-step-bare')
    assert bare['order'] is None


def test_list_finalize_steps_extension_order_from_return_dict(tmp_path):
    """Extension-contributed finalize steps propagate the `order` field from the return dict."""

    class _FakeExtModule:
        @staticmethod
        def provides_finalize_steps():
            return [
                {'name': 'ext:with-order', 'description': 'With order', 'order': 500},
                {'name': 'ext:without-order', 'description': 'No order'},
            ]

    fake_extensions = [{'bundle': 'fake-bundle', 'module': _FakeExtModule()}]

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=fake_extensions):
        steps = _run_discovery_in_cwd(tmp_path)

    with_order = next(s for s in steps if s['name'] == 'ext:with-order')
    without_order = next(s for s in steps if s['name'] == 'ext:without-order')
    assert with_order['order'] == 500
    assert without_order['order'] is None


# =============================================================================
# OPTIONAL_BUNDLE_FINALIZE_STEPS discovery tests (deliverable 2)
# =============================================================================


def test_list_finalize_steps_includes_optional_bundle_step(tmp_path):
    """`plan-marshall:plan-retrospective` is surfaced by list-finalize-steps.

    The step is declared in OPTIONAL_BUNDLE_FINALIZE_STEPS and must appear in
    the discovered list with `source: bundle-optional` so it is visible to
    marshall-steward's step picker even when the project has not yet added
    it to marshal.json.
    """
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]
    assert 'plan-marshall:plan-retrospective' in names, (
        f'Expected plan-marshall:plan-retrospective among discovered steps, got {names}'
    )
    retro = next(s for s in steps if s['name'] == 'plan-marshall:plan-retrospective')
    assert retro['source'] == 'bundle-optional'
    assert retro['type'] == 'skill'


def test_default_config_excludes_optional_bundle_finalize_steps():
    """Opt-in bundle finalize steps are absent from the default phase-6-finalize steps list.

    The whole point of OPTIONAL_BUNDLE_FINALIZE_STEPS is that they are
    discoverable (list-finalize-steps) but not activated by default —
    projects must add them to marshal.json explicitly.
    """
    config = _config_defaults.get_default_config()
    finalize_steps = config['plan']['phase-6-finalize']['steps']

    for optional_ref in _config_defaults.OPTIONAL_BUNDLE_FINALIZE_STEPS:
        assert optional_ref not in finalize_steps, (
            f'Optional bundle step {optional_ref!r} must not be in default finalize steps (found in {finalize_steps})'
        )
    # Sanity check: retrospective must be one of the opt-in entries
    assert 'plan-marshall:plan-retrospective' in _config_defaults.OPTIONAL_BUNDLE_FINALIZE_STEPS


def test_list_finalize_steps_optional_bundle_order_from_frontmatter(tmp_path):
    """`order` for plan-retrospective is resolved from its SKILL.md frontmatter.

    The skill declares `order: 995` in frontmatter (placing it after
    `default:record-metrics` and before `default:finalize-step-print-phase-breakdown`);
    discovery must surface that exact value (not None) so marshall-steward can
    slot it into the sorted execution order.
    """
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    retro = next(s for s in steps if s['name'] == 'plan-marshall:plan-retrospective')
    assert retro['order'] == 995, f'Expected order=995 from SKILL.md frontmatter, got {retro["order"]!r}'


def test_list_finalize_steps_optional_bundle_description_populated(tmp_path):
    """Description is populated for the opt-in step (from SKILL.md or fallback map).

    When SKILL.md is present, `get_skill_description` returns the frontmatter
    description. When it cannot parse one, discovery falls back to
    OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS. Either way the final value
    must never equal the bare notation (which is the sentinel the resolver
    uses when nothing was found).
    """
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    retro = next(s for s in steps if s['name'] == 'plan-marshall:plan-retrospective')
    description = retro['description']
    assert description, 'description must not be empty'
    assert description != 'plan-marshall:plan-retrospective', (
        'description must not fall through to the bare notation — the fallback map '
        'should have supplied a human-readable string'
    )
    # Fallback map supplies a curated human-readable description for the
    # retrospective step; the Source 4 path also accepts the frontmatter
    # description parsed from SKILL.md. Both are acceptable outcomes — the
    # only regression we guard against is the bare-notation sentinel.
    fallback = _config_defaults.OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS['plan-marshall:plan-retrospective']
    assert description != 'plan-marshall:plan-retrospective'
    # Sanity check: description is meaningfully longer than the bare notation.
    assert len(description) > len('plan-marshall:plan-retrospective'), (
        f'Description {description!r} is suspiciously short — expected either '
        f'the frontmatter description or fallback {fallback!r}'
    )


def test_list_finalize_steps_optional_bundle_precedes_extensions(tmp_path):
    """Optional bundle steps emit before extension-provided steps.

    The source ordering contract: built-in + project + bundle-optional all
    precede every extension entry. A regression that reversed Source 3/4 in
    _discover_all_finalize_steps() would break marshall-steward's assumption
    that extensions come last.
    """

    class _FakeExtModule:
        @staticmethod
        def provides_finalize_steps():
            return [
                {'name': 'ext:finalize-step-from-extension', 'description': 'Provided by extension'},
            ]

    fake_extensions = [{'bundle': 'fake-bundle', 'module': _FakeExtModule()}]

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=fake_extensions):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]
    assert 'plan-marshall:plan-retrospective' in names
    assert 'ext:finalize-step-from-extension' in names

    retro_idx = names.index('plan-marshall:plan-retrospective')
    ext_idx = names.index('ext:finalize-step-from-extension')
    assert retro_idx < ext_idx, f'Opt-in bundle step (idx {retro_idx}) must precede extension step (idx {ext_idx})'
    # Every extension entry must appear after the retrospective entry
    for idx, step in enumerate(steps):
        if step['source'] == 'extension':
            assert idx > retro_idx, (
                f'Extension step {step["name"]!r} at {idx} must come after bundle-optional retrospective at {retro_idx}'
            )


# =============================================================================
# Layout-aware built-in finalize step order resolution (source + cache layouts)
# =============================================================================


def _build_source_layout_finalize(base: Path) -> Path:
    """Build a source/marketplace layout: <base>/plan-marshall/skills/phase-6-finalize/..."""
    return build_phase_layout(base, 'phase-6-finalize', _config_defaults.BUILT_IN_FINALIZE_STEPS, cache_layout=False)


def _build_cache_layout_finalize(base: Path, version: str = '0.1-BETA') -> Path:
    """Build a versioned plugin-cache layout: <base>/plan-marshall/<version>/skills/phase-6-finalize/..."""
    return build_phase_layout(
        base, 'phase-6-finalize', _config_defaults.BUILT_IN_FINALIZE_STEPS, cache_layout=True, version=version
    )


def test_discover_finalize_steps_source_layout_resolves_order(tmp_path):
    """Built-in finalize steps resolve non-None order in the source/marketplace layout."""
    base = _build_source_layout_finalize(tmp_path / 'bundles')

    with (
        patch.object(_cmd_skill_resolution, 'BUNDLES_DIR', base),
        patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]),
    ):
        steps = _run_discovery_in_cwd(tmp_path)

    built_ins = {s['name']: s for s in steps if s['source'] == 'built-in'}
    for step_name in _config_defaults.BUILT_IN_FINALIZE_STEPS:
        assert built_ins[step_name]['order'] is not None, (
            f'{step_name} must resolve a non-None order in source layout, got None'
        )


def test_discover_finalize_steps_cache_layout_resolves_order(tmp_path):
    """Built-in finalize steps resolve non-None order in the versioned plugin-cache layout."""
    base = _build_cache_layout_finalize(tmp_path / 'bundles')

    with (
        patch.object(_cmd_skill_resolution, 'BUNDLES_DIR', base),
        patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]),
    ):
        steps = _run_discovery_in_cwd(tmp_path)

    built_ins = {s['name']: s for s in steps if s['source'] == 'built-in'}
    for step_name in _config_defaults.BUILT_IN_FINALIZE_STEPS:
        assert built_ins[step_name]['order'] is not None, (
            f'{step_name} must resolve a non-None order in cache layout, got None'
        )


def test_discover_finalize_steps_order_matches_across_layouts(tmp_path):
    """The same built-in finalize order values are resolved in both layouts (no missing_order)."""
    source_base = _build_source_layout_finalize(tmp_path / 'source')
    cache_base = _build_cache_layout_finalize(tmp_path / 'cache')

    with (
        patch.object(_cmd_skill_resolution, 'BUNDLES_DIR', source_base),
        patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]),
    ):
        source_steps = {
            s['name']: s['order'] for s in _run_discovery_in_cwd(tmp_path) if s['source'] == 'built-in'
        }

    with (
        patch.object(_cmd_skill_resolution, 'BUNDLES_DIR', cache_base),
        patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]),
    ):
        cache_steps = {
            s['name']: s['order'] for s in _run_discovery_in_cwd(tmp_path) if s['source'] == 'built-in'
        }

    assert source_steps == cache_steps, (
        f'Built-in finalize step orders must match across layouts: {source_steps} != {cache_steps}'
    )
    assert all(order is not None for order in cache_steps.values()), 'No built-in finalize step may have missing_order'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_resolve_domain_skills(plan_context):
    """Test CLI plumbing: resolve-domain-skills outputs TOON."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'resolve-domain-skills', '--domain', 'java', '--profile', 'implementation')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'pm-dev-java:java-core' in result.stdout


# =============================================================================
# _discover_all_recipes frontmatter-scoping Tests
# =============================================================================


def _make_recipe_skill(parent: Path, name: str, content: str) -> Path:
    """Create a recipe-* skill dir with a SKILL.md carrying *content*."""
    skill_dir = parent / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(content, encoding='utf-8')
    return skill_dir


def test_discover_recipes_ignores_recipe_domain_in_markdown_body(tmp_path):
    """A recipe_domain:-shaped line in the markdown BODY (not frontmatter) is ignored."""
    skill_dir = _make_recipe_skill(
        tmp_path,
        'recipe-frontmatter-scoped',
        '---\n'
        'description: A frontmatter-scoped recipe\n'
        'recipe_domain: java\n'
        '---\n'
        '\n'
        '# Body\n'
        '\n'
        'recipe_domain: hijacked\n'
        'recipe_profile: bogus\n',
    )

    with (
        patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]),
        patch.object(_cmd_skill_resolution, 'iter_project_skill_dirs', return_value=[skill_dir]),
    ):
        recipes = _cmd_skill_resolution._discover_all_recipes()

    assert len(recipes) == 1
    recipe = recipes[0]
    # The frontmatter value wins; the body's hijacked/bogus lines are ignored.
    assert recipe['domain'] == 'java'
    assert recipe['profile'] == ''


def test_discover_recipes_skips_recipe_with_domain_only_in_body(tmp_path):
    """A recipe whose recipe_domain appears ONLY in the body is silently skipped."""
    skill_dir = _make_recipe_skill(
        tmp_path,
        'recipe-body-only',
        '---\n'
        'description: No recipe_domain in frontmatter\n'
        '---\n'
        '\n'
        '# Body\n'
        '\n'
        'recipe_domain: java\n',
    )

    with (
        patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]),
        patch.object(_cmd_skill_resolution, 'iter_project_skill_dirs', return_value=[skill_dir]),
    ):
        recipes = _cmd_skill_resolution._discover_all_recipes()

    # recipe_domain is required and only present in the body → the recipe is skipped.
    assert recipes == []
