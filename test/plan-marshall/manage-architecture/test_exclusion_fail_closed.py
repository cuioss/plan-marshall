#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The exclusion read fails closed, and qualification binds the architecture path.

PLAN-LB-80 D1/D3/D4. Three properties are pinned here:

* D1 — a ``marshal.json`` that exists and cannot be parsed is an ERROR the caller
  sees, not an empty exclusion set. An absent file still means "no exclusions".
  ``enrich`` reports the error instead of persisting an unfiltered map.
* D3 — the architecture path consults ``qualifies_optional`` per optional, so a
  non-CDI module's served optionals never offer ``java-quarkus``. The CDI
  positive is joined from real discovery, not from a union the test builds.
* D4 — the remaining write/read verbs apply the repository veto, and the
  exclusion read uses the caller's ``project_dir`` when it has one.
"""

import json
import os
import tempfile
from argparse import Namespace
from pathlib import Path

import extension_discovery
import pytest
from _arch_fixtures import setup_test_project

from conftest import create_marshal_json, load_script_module, load_skill_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core_fail_closed'
)
_cmd_client_handlers = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_handlers.py', '_cmd_client_handlers_fail_closed'
)
_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query_fail_closed'
)
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich_fail_closed')

extension_base = pytest.importorskip('extension_base')

QUARKUS = 'pm-dev-java:java-quarkus'
CDI = 'pm-dev-java:java-cdi'
JUNIT_WELD = 'pm-dev-java:junit-weld-testing'

#: A module that carries no CDI dependency — the qualification-negative module.
NON_CDI_DEPENDENCIES = ['org.apache.commons:commons-lang3:3.14.0']
#: A module that carries one — the qualification-positive module.
CDI_DEPENDENCIES = ['jakarta.enterprise:jakarta.enterprise.cdi-api:4.0']


# =============================================================================
# Helpers
# =============================================================================


def _module(dependencies: list[str]) -> dict:
    """A minimal maven module derived dict carrying ``dependencies``."""
    return {
        'name': 'module-a',
        'build_systems': ['maven'],
        'paths': {'module': 'module-a', 'sources': ['src/main/java'], 'tests': ['src/test/java']},
        'metadata': {},
        'packages': {},
        'dependencies': dependencies,
        'commands': {},
        'stats': {'source_files': 4, 'test_files': 2},
    }


def _seed(project_dir: str, dependencies: list[str] | None = None) -> None:
    """Seed the architecture store with one module carrying a skill map."""
    setup_test_project(
        project_dir,
        {'module-a': _module(dependencies or NON_CDI_DEPENDENCIES)},
        enrichment_stub={
            'responsibility': 'demo',
            'purpose': 'library',
            'skills_by_profile': {
                'implementation': {
                    'defaults': [{'skill': QUARKUS, 'description': 'd'}],
                    'optionals': [],
                }
            },
        },
    )


def _write_marshal(project_dir: str, skill_domains: dict) -> Path:
    """Write a well-formed ``.plan/marshal.json`` under ``project_dir``."""
    return Path(create_marshal_json(Path(project_dir), config={'skill_domains': skill_domains}, nest_in_plan_dir=True))


def _write_malformed_marshal(project_dir: str) -> Path:
    """Write a ``marshal.json`` that exists but cannot be parsed."""
    plan_dir = Path(project_dir) / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    path = plan_dir / 'marshal.json'
    path.write_text('{"skill_domains": {"java": ', encoding='utf-8')
    return path


def _notations(entries: list) -> list[str]:
    """Return the skill notations of a profile's entry list."""
    return [entry['skill'] if isinstance(entry, dict) else entry for entry in entries]


def _java_extension():
    """Load the real pm-dev-java extension — its qualification is under test."""
    return load_skill_module(
        'pm-dev-java',
        'plan-marshall-plugin',
        'extension.py',
        'extension_pm_dev_java_fail_closed',
        register=False,
    ).Extension()


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
        '  <artifactId>sample</artifactId>\n'
        '  <version>1.0.0</version>\n'
        '  <dependencies>\n'
        f'{dep_xml}\n'
        '  </dependencies>\n'
        '</project>\n',
        encoding='utf-8',
    )
    return pom


def _discovered_module(root: Path | str, dependencies: list[tuple[str, str]]) -> dict:
    """Run the real discovery over a POM fixture and return its module data."""
    _write_pom(Path(root), dependencies=dependencies)
    discovered = extension_discovery.discover_project_modules(Path(root))
    modules = discovered.get('modules') if isinstance(discovered, dict) else None
    assert isinstance(modules, dict) and modules, 'discovery returned no module map'
    return modules['sample']


# =============================================================================
# D1 — an unreadable configuration is an error, not an empty exclusion set
# =============================================================================


def test_malformed_marshal_makes_architecture_module_report_the_error():
    """``architecture module`` reports the read failure instead of serving a skill."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)
        _write_malformed_marshal(project_dir)

        result = _cmd_client_handlers.cmd_module(
            Namespace(module='module-a', project_dir=project_dir, full=False, budget=None)
        )

    assert result['status'] == 'error'
    assert 'skill_exclusions_unreadable' in str(result)


def test_malformed_marshal_is_not_reported_as_no_exclusions():
    """The typed read failure reaches the caller; it never degrades to ``set()``."""
    with tempfile.TemporaryDirectory() as project_dir:
        _write_malformed_marshal(project_dir)

        with pytest.raises(extension_base.SkillExclusionReadError):
            extension_base.all_excluded_skills(project_dir)


def test_absent_marshal_still_means_no_exclusions():
    """Regression guard: a repository with no configuration serves its skills."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)

        payload = _cmd_client_query.get_module_info('module-a', project_dir=project_dir)

    assert QUARKUS in json.dumps(payload['skills_by_profile'])


def test_overview_reports_an_unreadable_configuration():
    """The rendered surface fails closed like every other exclusion reader."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)
        _write_malformed_marshal(project_dir)

        result = _cmd_client_handlers.cmd_overview(Namespace(project_dir=project_dir, budget=200))

    assert result['status'] == 'error'


def test_malformed_marshal_is_reported_even_when_no_module_has_a_skill_map():
    """An empty map is not evidence that the prohibition could be read."""
    with tempfile.TemporaryDirectory() as project_dir:
        setup_test_project(project_dir, {'module-a': _module(NON_CDI_DEPENDENCIES)})
        _write_malformed_marshal(project_dir)

        result = _cmd_client_handlers.cmd_module(
            Namespace(module='module-a', project_dir=project_dir, full=False, budget=None)
        )

    assert result['status'] == 'error'


def test_enrich_reports_an_unreadable_configuration_instead_of_persisting():
    """``enrich --project-dir D`` fails instead of writing an unfiltered map."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)
        _write_malformed_marshal(project_dir)
        before = _architecture_core.load_module_enriched('module-a', project_dir)

        with pytest.raises(extension_base.SkillExclusionReadError):
            _cmd_enrich.enrich_add_domain('module-a', 'java', project_dir, include_optionals=True)

        after = _architecture_core.load_module_enriched('module-a', project_dir)

    assert after == before


# =============================================================================
# D3 — module qualification binds the architecture path
# =============================================================================


def test_non_cdi_module_architecture_optionals_exclude_java_quarkus():
    """A non-CDI module's architecture-served optionals never offer java-quarkus."""
    with tempfile.TemporaryDirectory() as project_dir:
        module_data = _discovered_module(project_dir, [('org.apache.commons', 'commons-lang3')])

        result = _java_extension().applies_to_module(module_data)

    optionals = _notations(result['skills_by_profile']['implementation']['optionals'])
    assert QUARKUS not in optionals
    assert CDI not in optionals
    assert JUNIT_WELD not in _notations(result['skills_by_profile']['module_testing']['optionals'])


def test_cdi_module_optionals_include_java_quarkus_through_the_served_map():
    """The CDI positive is joined from real discovery and read back through the store."""
    with tempfile.TemporaryDirectory() as project_dir:
        module_data = _discovered_module(project_dir, [('jakarta.enterprise', 'jakarta.enterprise.cdi-api')])
        result = _java_extension().applies_to_module(module_data)

        architecture_optionals = _notations(result['skills_by_profile']['implementation']['optionals'])
        # Persist what the architecture path produced, then read it back the way
        # phase-4 does — the assertion must not be a union the test builds.
        setup_test_project(project_dir, {'sample': {**module_data, 'name': 'sample'}})
        _cmd_enrich.enrich_add_domain('sample', 'java', project_dir, include_optionals=True)
        served = _cmd_client_query.get_module_info('sample', project_dir=project_dir)

    assert QUARKUS in architecture_optionals
    assert QUARKUS in json.dumps(served['skills_by_profile'])


# =============================================================================
# D4 — the remaining seams apply the veto, and one scope serves them all
# =============================================================================


def test_enrich_skills_by_profile_does_not_persist_an_excluded_skill():
    """A caller-supplied map is filtered before it is persisted."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)
        _write_marshal(project_dir, {'java': {'bundle': 'pm-dev-java', 'excluded_skills': ['java-quarkus']}})

        _cmd_enrich.enrich_skills_by_profile(
            'module-a',
            {'implementation': {'defaults': [{'skill': QUARKUS}], 'optionals': []}},
            project_dir,
        )
        stored = _architecture_core.load_module_enriched('module-a', project_dir)

    assert QUARKUS not in json.dumps(stored['skills_by_profile'])
    assert stored['skills_by_profile']['implementation'] == {'defaults': [], 'optionals': [], 'minimal': True}


def test_enrich_reads_the_callers_configuration_not_the_execution_context():
    """The enrich path reads the caller's project_dir, not the execution context."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir, CDI_DEPENDENCIES)
        # Execution-context configuration (the harness's own checkout) forbids the skill.
        create_marshal_json(
            Path(os.environ['PLAN_BASE_DIR']),
            config={'skill_domains': {'java': {'bundle': 'pm-dev-java', 'excluded_skills': ['java-quarkus']}}},
            nest_in_plan_dir=False,
        )
        # The enriched project forbids nothing.
        _write_marshal(project_dir, {'java': {'bundle': 'pm-dev-java'}})

        _cmd_enrich.enrich_add_domain('module-a', 'java', project_dir, include_optionals=True)
        served = _cmd_client_query.get_module_info('module-a', project_dir=project_dir)

    assert QUARKUS in json.dumps(served['skills_by_profile'])
