#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
import file_ops  # noqa: E402

from conftest import PROJECT_ROOT, get_script_path, run_script  # noqa: E402

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
    assert 'default:push' in step_names
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

    Project-local discovery is PROJECT-ROOT-anchored: ``_scan_project_for_implementors``
    resolves the project-local ``.claude/skills/`` via ``file_ops._resolve_plan_root``
    (the uniform cwd rule with a git-toplevel fallback — ADR-002), NOT from the
    scanning script's ``__file__``. Running the subprocess with cwd at the repo
    root makes that resolver land on the real tree, so ``project:finalize-step-plugin-doctor``
    — declared under the repo's ``.claude/skills/finalize-step-plugin-doctor/`` — is
    surfaced. (Runtime writes still resolve via the inherited ``PLAN_BASE_DIR``
    sandbox, so the read-only project scan does not pollute the real tree.)
    """
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'list-finalize-steps', cwd=PROJECT_ROOT)

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'project:finalize-step-plugin-doctor' in result.stdout


# =============================================================================
# list-finalize-steps ordering tests (lock in sync-plugin-cache head placement)
# =============================================================================


def _run_discovery_in_cwd(cwd: Path) -> list[dict]:
    """Invoke _discover_all_finalize_steps() with the project root pinned to the repo.

    Project-local finalize-step discovery routes through
    ``extension_discovery._scan_project_for_implementors``, which anchors on the
    PROJECT root resolved cwd-relatively via ``file_ops._resolve_plan_root`` (the
    uniform cwd rule with a git-toplevel fallback — ADR-002), NOT on the scanning
    script's ``__file__``. Under a pytest ``tmp_path`` cwd that resolver finds no
    ``.plan/local`` ancestor and no enclosing git repo, so the project steps would
    be missed. This helper pins ``_resolve_plan_root`` to the real repo root
    (``PROJECT_ROOT``) for the duration of discovery — mirroring the monkeypatch
    used by ``test_extension_discovery_behavior.py`` — so tests assert against the
    repo's real shipped project finalize steps. The ``cwd`` argument is retained
    for call-site compatibility; the chdir is harmless because discovery no longer
    reads the cwd to locate project steps.
    """
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        with patch.object(file_ops, '_resolve_plan_root', lambda: PROJECT_ROOT):
            return _cmd_skill_resolution._discover_all_finalize_steps()
    finally:
        os.chdir(original_cwd)


def test_list_finalize_steps_starts_with_built_ins(tmp_path):
    """The discovered list is sorted by order; the lowest-order step is a built-in.

    find_implementors sorts all implementors by ``(order, name)``. The repo's
    lowest-order finalize steps are built-in ``default:`` steps (pre-push-quality-gate
    at order 5 is the head), so the first entry is a built-in.
    """
    steps = _run_discovery_in_cwd(tmp_path)

    assert len(steps) > 0
    first = steps[0]
    assert first['source'] == 'built-in'
    assert first['name'].startswith('default:')


def test_list_finalize_steps_sync_and_deploy_are_project_steps(tmp_path):
    """sync-plugin-cache and deploy-target are project-local steps, not built-in defaults.

    They are meta-project-only project-local finalize-step skills (Source: project),
    discovered the same way as ``finalize-step-plugin-doctor`` — never built-in
    ``default:`` steps.
    """
    steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]

    # Neither is a built-in default.
    assert 'default:sync-plugin-cache' not in names
    assert 'default:deploy-target' not in names

    # Both are discovered as project steps in the real repo.
    by_name = {s['name']: s for s in steps}
    assert by_name['project:finalize-step-sync-plugin-cache']['source'] == 'project'
    assert by_name['project:finalize-step-deploy-target']['source'] == 'project'


def test_list_finalize_steps_ordered_ascending_by_order(tmp_path):
    """The discovered list is globally sorted ascending by resolved order.

    find_implementors returns all implementors (built-in, bundle-optional, and
    project) merged and sorted by ``(order, name)``. The ordering invariant is the
    global ascending order, NOT a "built-ins before project steps" partition —
    project steps interleave by their declared order (e.g. plugin-doctor at order
    6 precedes default:push at order 10).
    """
    steps = _run_discovery_in_cwd(tmp_path)

    orders = [s['order'] for s in steps if s['order'] is not None]
    assert orders == sorted(orders), (
        f'discovered finalize steps must be ascending by order: {orders}'
    )


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
    steps = _run_discovery_in_cwd(tmp_path)

    by_name = {s['name']: s for s in steps if s['source'] == 'built-in'}
    assert by_name['default:push']['order'] == 10
    assert by_name['default:create-pr']['order'] == 20
    assert by_name['default:automated-review']['order'] == 30
    assert by_name['default:archive-plan']['order'] == 1000
    assert by_name['default:record-metrics']['order'] == 998


def test_list_finalize_steps_project_skill_order_from_frontmatter(tmp_path):
    """Project finalize-step-* skills expose the `order` declared in their SKILL.md.

    Discovery is repo-anchored, so this asserts against a real shipped project
    step: ``project:finalize-step-plugin-doctor`` declares ``order: 6``.
    """
    steps = _run_discovery_in_cwd(tmp_path)

    doctor = next(s for s in steps if s['name'] == 'project:finalize-step-plugin-doctor')
    assert doctor['order'] == 6


def test_list_finalize_steps_project_skill_order_defaults_to_zero_when_absent():
    """A discovered implementor record defaults `order` to 0 when frontmatter omits it.

    The discovery query's record builder defaults a missing ``order`` to ``0`` (no
    longer ``None``). Verified directly against the implementor-record builder so
    the contract is pinned without scaffolding a synthetic project skill (which is
    not discovered under the repo-anchored scan).
    """
    import tempfile

    from extension_discovery import _build_implementor_record  # type: ignore[import-not-found]

    handle = tempfile.NamedTemporaryFile(
        mode='w', suffix='.md', delete=False, encoding='utf-8'
    )
    handle.write('---\nname: finalize-step-bare\ndescription: Bare\n---\n\n# Bare\n')
    handle.close()
    bare_doc = Path(handle.name)
    record = _build_implementor_record(bare_doc, 'project', name_override='project:finalize-step-bare')

    assert record['order'] == 0


# =============================================================================
# Bundle-optional finalize-step discovery tests
# =============================================================================
#
# Opt-in bundle finalize steps are no longer a hand-maintained
# OPTIONAL_BUNDLE_FINALIZE_STEPS constant: they are bundle-optional implementors
# (source == 'bundle-optional') surfaced by extension_discovery.find_implementors.
# Discovery is anchored on the marketplace tree (not the process cwd), so these
# tests assert against the real repo's discovered universe.


def _discovered_steps() -> list[dict]:
    """Return the discovered finalize-step list via _discover_all_finalize_steps()."""
    return _cmd_skill_resolution._discover_all_finalize_steps()


def test_list_finalize_steps_includes_optional_bundle_step():
    """`plan-marshall:plan-retrospective` is surfaced by list-finalize-steps.

    The step declares the finalize-step interface in its SKILL.md frontmatter and
    must appear in the discovered list with `source: bundle-optional` so it is
    visible to marshall-steward's step picker even when the project has not yet
    added it to marshal.json.
    """
    steps = _discovered_steps()

    names = [s['name'] for s in steps]
    assert 'plan-marshall:plan-retrospective' in names, (
        f'Expected plan-marshall:plan-retrospective among discovered steps, got {names}'
    )
    retro = next(s for s in steps if s['name'] == 'plan-marshall:plan-retrospective')
    assert retro['source'] == 'bundle-optional'
    assert retro['type'] == 'skill'


def test_default_config_excludes_optional_bundle_finalize_steps():
    """Opt-in bundle finalize steps are absent from the default phase-6-finalize steps list.

    Bundle-optional steps (default_on: false) are discoverable
    (list-finalize-steps) but not activated by default — projects must add them
    to marshal.json explicitly. Discovered via find_implementors filtered to the
    bundle-optional source.
    """
    config = _config_defaults.get_default_config()
    finalize_steps = config['plan']['phase-6-finalize']['steps']

    optional_refs = [s['name'] for s in _discovered_steps() if s['source'] == 'bundle-optional']
    for optional_ref in optional_refs:
        assert optional_ref not in finalize_steps, (
            f'Optional bundle step {optional_ref!r} must not be in default finalize steps (found in {finalize_steps})'
        )
    # Sanity check: retrospective must be one of the opt-in (bundle-optional) entries
    assert 'plan-marshall:plan-retrospective' in optional_refs


def test_list_finalize_steps_optional_bundle_order_from_frontmatter():
    """`order` for plan-retrospective is resolved from its SKILL.md frontmatter.

    The skill declares `order: 995` in frontmatter (placing it after
    `default:record-metrics`); discovery must surface that exact value (not None)
    so marshall-steward can slot it into the sorted execution order.
    """
    steps = _discovered_steps()

    retro = next(s for s in steps if s['name'] == 'plan-marshall:plan-retrospective')
    assert retro['order'] == 995, f'Expected order=995 from SKILL.md frontmatter, got {retro["order"]!r}'


def test_list_finalize_steps_optional_bundle_description_populated():
    """Description is populated for the opt-in step from its SKILL.md frontmatter.

    The per-step description is now a discovery-query frontmatter field (the
    OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS fallback map was removed). The
    discovered value must be a non-empty human-readable string, never the bare
    notation sentinel.
    """
    steps = _discovered_steps()

    retro = next(s for s in steps if s['name'] == 'plan-marshall:plan-retrospective')
    description = retro['description']
    assert description, 'description must not be empty'
    assert description != 'plan-marshall:plan-retrospective', (
        'description must not fall through to the bare notation — the SKILL.md '
        'frontmatter should have supplied a human-readable string'
    )
    # Sanity check: description is meaningfully longer than the bare notation.
    assert len(description) > len('plan-marshall:plan-retrospective'), (
        f'Description {description!r} is suspiciously short — expected the '
        f'frontmatter description'
    )


# =============================================================================
# Built-in finalize step order resolution
# =============================================================================
#
# The synthetic source/cache layout tests (which patched ``BUNDLES_DIR`` and
# scaffolded a fake ``phase-6-finalize`` tree) are retired: discovery now routes
# through ``extension_discovery.find_implementors``, which resolves the
# marketplace bundles root and the plugin-cache roots internally — patching
# ``_cmd_skill_resolution.BUNDLES_DIR`` no longer redirects discovery. The
# cache-aware doc-root resolution is exercised against the real tree by the
# extension-api discovery suite. Here we pin the consumer-facing invariant: every
# discovered built-in step carries a concrete integer order.


def test_discover_finalize_steps_builtins_resolve_concrete_order(tmp_path):
    """Every discovered built-in finalize step carries a concrete integer order.

    find_implementors reads each built-in step doc's ``order`` frontmatter; the
    record builder defaults a missing order to 0 (never None). This asserts the
    real tree resolves a concrete non-negative integer order for every built-in.
    """
    steps = _run_discovery_in_cwd(tmp_path)

    built_ins = {s['name']: s for s in steps if s['source'] == 'built-in'}
    assert built_ins, 'Expected discovered built-in finalize steps'
    for step_name, rec in built_ins.items():
        assert isinstance(rec['order'], int), (
            f'{step_name} must resolve a concrete integer order, got {rec["order"]!r}'
        )


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
