#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests binding repository exclusions and module qualification to a task's skills.

The resolver and the architecture path are two producers of the same task skill
list. These tests pin the three properties that make them agree: a repository
exclusion removes a skill whichever producer surfaced it, a module that cannot
prove an optional applies never receives it, and a domain extension with no
module-level signal keeps its optionals.

Discovery is exercised for real over a POM fixture in one test so the
CDI-positive path cannot pass by monkeypatching the very signal it claims to
prove.
"""

import os
import sys
import types
from pathlib import Path

from conftest import create_marshal_json, load_script_module, load_skill_module

# In-process module under test — a distinct load from the manage-personas suite
# so the discovery cache here is not shared with those tests.
_mp = load_script_module(
    'plan-marshall',
    'manage-personas',
    'manage_personas.py',
    'manage_personas_binding_under_test',
)

JAVA_CDI = 'pm-dev-java:java-cdi'
JAVA_CORE = 'pm-dev-java:java-core'
JAVA_QUARKUS = 'pm-dev-java:java-quarkus'


# =============================================================================
# Fixtures and helpers
# =============================================================================


def _write_marshal(config: dict) -> Path:
    """Write a real marshal.json where the project config reader resolves it."""
    return Path(create_marshal_json(Path(os.environ['PLAN_BASE_DIR']), config=config, nest_in_plan_dir=False))


def _exclusions(*skills: str) -> dict:
    """Build a marshal.json payload declaring java exclusions."""
    return {'skill_domains': {'java': {'excluded_skills': list(skills)}}}


def _java_extension():
    """Load the real pm-dev-java extension — its qualification is under test."""
    return load_skill_module(
        'pm-dev-java',
        'plan-marshall-plugin',
        'extension.py',
        'extension_pm_dev_java_skill_binding',
        register=False,
    ).Extension()


def _java_module(*dependencies: str) -> dict:
    """Build the minimal module dict the java extension's applicability reads."""
    return {'name': 'sample-module', 'build_systems': ['maven'], 'dependencies': list(dependencies)}


def _install_fake_skill_resolution(monkeypatch, func):
    """Inject a fake ``_cmd_skill_resolution`` module exposing ``func``."""
    fake = types.ModuleType('_cmd_skill_resolution')
    fake.cmd_resolve_domain_skills = func
    monkeypatch.setitem(sys.modules, '_cmd_skill_resolution', fake)


def _install_cell(monkeypatch, *, defaults, optionals):
    """Install a fake java cell plus the real java extension."""

    def fake(ns):
        return {
            'status': 'success',
            'defaults': {skill: {} for skill in defaults},
            'optionals': {skill: {} for skill in optionals},
        }

    _install_fake_skill_resolution(monkeypatch, fake)
    monkeypatch.setattr(_mp, '_find_domain_extension', lambda domain: _java_extension())


def _write_persona(bundles_root: Path, key: str, composes: list[str]) -> Path:
    """Write a synthetic persona whose composition edges are ``composes``."""
    bundle, skill = key.split(':', 1)
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / 'SKILL.md'
    path.write_text(
        '---\nimplements: persona\nprofiles: []\ncomposes: [' + ', '.join(composes) + ']\n---\n',
        encoding='utf-8',
    )
    return path


def _write_pom(root: Path, *, dependencies: list[tuple[str, str]]) -> Path:
    """Write a minimal Maven POM declaring ``(groupId, artifactId)`` dependencies."""
    dep_xml = '\n'.join(
        '    <dependency>\n'
        f'      <groupId>{group_id}</groupId>\n'
        f'      <artifactId>{artifact_id}</artifactId>\n'
        '      <version>1.0</version>\n'
        '    </dependency>'
        for group_id, artifact_id in dependencies
    )
    pom = root / 'pom.xml'
    pom.write_text(
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        '  <modelVersion>4.0.0</modelVersion>\n'
        '  <groupId>de.example</groupId>\n'
        '  <artifactId>cdi-sample</artifactId>\n'
        '  <version>1.0.0</version>\n'
        '  <dependencies>\n'
        f'{dep_xml}\n'
        '  </dependencies>\n'
        '</project>\n',
        encoding='utf-8',
    )
    return pom


# =============================================================================
# One exclusion binds every producer of a task's skills
# =============================================================================


def _architecture_services(module_data: dict, project_dir: Path, excluded: list[str]) -> set[str]:
    """Persist what the architecture path produced and read it back as phase-4 does.

    The union this test builds must not be the only evidence: the architecture
    half has to come back through ``get_module_info``, the seam a later phase
    actually reads, or deleting the read seam would leave the test green.
    """
    core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_arch_core_binding')
    query = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_arch_query_binding')

    produced = _java_extension().applies_to_module(module_data)
    # The extension already applies the execution-context veto, so persist a
    # STALE copy of the excluded skill: only the read seam can remove it, and the
    # test would otherwise stay green with that seam deleted.
    stored = produced['skills_by_profile']
    stored.setdefault('implementation', {'defaults': [], 'optionals': []})['optionals'].append(
        {'skill': JAVA_QUARKUS, 'description': 'stale persisted entry'}
    )
    core.save_project_meta(
        {'name': 'demo', 'description': '', 'description_reasoning': '', 'extensions_used': [], 'modules': {'m': {}}},
        str(project_dir),
    )
    core.save_module_derived('m', {**module_data, 'paths': {'module': 'm'}, 'commands': {}}, str(project_dir))
    core.save_module_enriched('m', {'skills_by_profile': stored}, str(project_dir))
    create_marshal_json(project_dir, config=_exclusions(*excluded), nest_in_plan_dir=True)

    served = query.get_module_info('m', project_dir=str(project_dir))
    return {
        entry['skill']
        for profile in served['skills_by_profile'].values()
        for key in ('defaults', 'optionals')
        for entry in profile[key]
        if isinstance(entry, dict)
    }


def test_final_task_skills_drop_a_repository_excluded_skill(monkeypatch, tmp_path):
    """The union of the architecture and persona paths never carries an excluded skill."""
    _write_marshal(_exclusions(JAVA_QUARKUS))
    module_data = _java_module('jakarta.enterprise:jakarta.enterprise.cdi-api:4.0')
    _install_cell(monkeypatch, defaults=[JAVA_CORE], optionals=[JAVA_QUARKUS])
    monkeypatch.setattr(_mp, '_resolve_module_data', lambda module: (module_data, 'resolved'))

    persona = _mp._resolve_profile_domain_skills('implementation', 'java', module='sample-module')
    final = _architecture_services(module_data, tmp_path, [JAVA_QUARKUS]) | set(persona['skills'])

    assert JAVA_QUARKUS not in final
    assert JAVA_CDI in final


def test_extension_without_the_hook_admits_defaults_only(monkeypatch):
    """A readable module whose extension has no hook signal gets no optional."""

    class _NoHookExtension:
        def applies_to_module(self, module_data):
            return {'applicable': True, 'skills_by_profile': {}}

    _install_cell(monkeypatch, defaults=[JAVA_CORE], optionals=[JAVA_CDI])
    monkeypatch.setattr(_mp, '_find_domain_extension', lambda domain: _NoHookExtension())
    monkeypatch.setattr(_mp, '_resolve_module_data', lambda module: (_java_module(), 'resolved'))

    result = _mp._resolve_profile_domain_skills('implementation', 'java', module='sample-module')

    assert result['skills'] == [JAVA_CORE]


def test_extensionbase_default_hook_keeps_optionals(monkeypatch):
    """A domain with no module-level signal keeps the optionals its base admits."""
    from extension_base import ExtensionBase

    class _DefaultHookExtension(ExtensionBase):
        def get_skill_domains(self):
            return [{'domain': {'key': 'python'}, 'profiles': {}}]

        def applies_to_module(self, module_data, active_profiles=None):
            return {'applicable': True, 'skills_by_profile': {}}

    optionals = ['pm-dev-python:pytest-testing']
    _install_cell(monkeypatch, defaults=[JAVA_CORE], optionals=optionals)
    monkeypatch.setattr(_mp, '_find_domain_extension', lambda domain: _DefaultHookExtension())
    monkeypatch.setattr(_mp, '_resolve_module_data', lambda module: (_java_module(), 'resolved'))

    result = _mp._resolve_profile_domain_skills('module_testing', 'python', module='sample-module')

    assert result['skills'] == [JAVA_CORE, *optionals]


def test_cmd_resolve_drops_an_excluded_composed_skill(tmp_path, monkeypatch):
    """A composed ref the repository excludes never reaches the flattened skills[]."""
    _write_persona(tmp_path, 'plan-marshall:persona-x', composes=['plan-marshall:ref-code-quality'])
    monkeypatch.setattr(_mp, 'resolve_bundles_root', lambda _script: tmp_path)
    _write_marshal(_exclusions('plan-marshall:ref-code-quality'))

    result = _mp.cmd_resolve(types.SimpleNamespace(persona_key='plan-marshall:persona-x', domains='java', module=''))

    assert 'plan-marshall:ref-code-quality' not in result['skills']
    assert _mp.BASE_PERSONA in result['skills']


def test_cmd_resolve_drops_an_excluded_base_persona(tmp_path, monkeypatch):
    """The base skill is subject to the repository veto like every other skill."""
    _write_persona(tmp_path, 'plan-marshall:persona-x', composes=[])
    monkeypatch.setattr(_mp, 'resolve_bundles_root', lambda _script: tmp_path)
    _write_marshal(_exclusions(_mp.BASE_PERSONA))

    result = _mp.cmd_resolve(types.SimpleNamespace(persona_key='plan-marshall:persona-x', domains='java', module=''))

    assert _mp.BASE_PERSONA not in result['skills']


def test_cmd_resolve_keeps_a_composed_skill_without_an_exclusion(tmp_path, monkeypatch):
    """Matched negative control: the same composition keeps its ref unexcluded."""
    _write_persona(tmp_path, 'plan-marshall:persona-x', composes=['plan-marshall:ref-code-quality'])
    monkeypatch.setattr(_mp, 'resolve_bundles_root', lambda _script: tmp_path)
    _write_marshal(_exclusions())

    result = _mp.cmd_resolve(types.SimpleNamespace(persona_key='plan-marshall:persona-x', domains='java', module=''))

    assert 'plan-marshall:ref-code-quality' in result['skills']


# =============================================================================
# The production path's tests can fail for the reason they name
# =============================================================================


def test_joined_discovery_admits_cdi_optional_for_a_real_pom(tmp_path, monkeypatch):
    """Real discovery over a CDI POM supplies the signal that admits java-cdi."""
    _write_pom(tmp_path, dependencies=[('jakarta.enterprise', 'jakarta.enterprise.cdi-api')])
    _install_cell(monkeypatch, defaults=[JAVA_CORE], optionals=[JAVA_CDI])
    _install_real_discovery(tmp_path, monkeypatch)

    result = _mp._resolve_profile_domain_skills('implementation', 'java', module='cdi-sample')

    assert JAVA_CDI in result['skills']
    assert result['module_status'] == 'resolved'


def _install_real_discovery(tmp_path: Path, monkeypatch) -> None:
    """Point the resolver's real discovery at ``tmp_path`` and clear its cache."""
    import resolve_project_dir

    monkeypatch.setattr(resolve_project_dir, 'resolve_project_dir', lambda *_args, **_kwargs: str(tmp_path))
    _mp._discovered_modules.cache_clear()


def test_resolve_module_data_unreadable_when_discovery_raises(monkeypatch):
    """A discovery failure is reported as unreadable, never as a readable module."""

    def boom():
        raise RuntimeError('discovery failed')

    monkeypatch.setattr(_mp, '_discovered_modules', boom)

    assert _mp._resolve_module_data('sample-module') == (None, 'unreadable')


def test_resolve_module_data_unreadable_when_the_module_is_absent(monkeypatch):
    """A module discovery does not know is unreadable, not an applicable module."""
    monkeypatch.setattr(_mp, '_discovered_modules', lambda: {'other-module': {'name': 'other-module'}})

    assert _mp._resolve_module_data('sample-module') == (None, 'unreadable')


# =============================================================================
# The exclusion match is symmetric
# =============================================================================


def test_full_notation_exclusion_removes_a_bare_skill():
    """A full-notation exclusion removes the skill a cell carries bare."""
    assert _mp._is_excluded('java-cdi', {'pm-dev-java:java-cdi'}) is True


def test_bare_name_exclusion_removes_a_full_notation_skill():
    """A bare-name exclusion removes the full-notation skill."""
    assert _mp._is_excluded('pm-dev-java:java-cdi', {'java-cdi'}) is True


def test_unrelated_exclusion_leaves_a_skill_alone():
    """The matched negative control: a different bare name removes nothing."""
    assert _mp._is_excluded('pm-dev-java:java-cdi', {'pm-dev-java:java-quarkus'}) is False


def test_bundle_qualified_exclusion_does_not_remove_another_bundle_skill():
    """A qualified exclusion narrows to its bundle; it is not a bare-name match."""
    assert _mp._is_excluded('other-bundle:java-quarkus', {'pm-dev-java:java-quarkus'}) is False


def test_bundle_qualified_exclusion_removes_its_own_bundle_skill():
    """The matched positive control for the narrowing case."""
    assert _mp._is_excluded('pm-dev-java:java-quarkus', {'pm-dev-java:java-quarkus'}) is True
