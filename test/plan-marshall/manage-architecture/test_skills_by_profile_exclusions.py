#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The repository veto binds a persisted ``skills_by_profile`` map at read time.

The architecture store is a cache: a module enriched before an exclusion was
configured still carries the skill, and the enrichment merge is add-only. These
tests pin the read seam that serves phase-4, so "the repository forbids it" holds
for the task a later phase reads and not only for a fresh enrichment.
"""

import tempfile
from pathlib import Path

from conftest import create_marshal_json, load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query'
)
_cmd_client_render = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_render.py', '_cmd_client_render'
)

get_module_info = _cmd_client_query.get_module_info
render_overview = _cmd_client_render.render_overview
render_module_markdown = _cmd_client_render.render_module_markdown

#: A notation that really resolves in this repository, so the read guard's
#: stale-notation message never stands in for the condition under test.
_LIVE = 'plan-marshall:persona-plan-marshall-agent'

#: The excluded skill, named bare in marshal.json to exercise the symmetric match.
_EXCLUDED = 'pm-dev-java:java-quarkus'


def _write_marshal(project_dir: str, *excluded_skills: str) -> Path:
    """Write the project's marshal.json with java exclusions."""
    return _write_skill_domains(project_dir, {'java': {'excluded_skills': list(excluded_skills)}})


def _write_skill_domains(project_dir: str, skill_domains: dict) -> Path:
    """Write a marshal.json carrying the given ``skill_domains`` block."""
    return Path(
        create_marshal_json(
            Path(project_dir),
            config={'skill_domains': skill_domains},
            nest_in_plan_dir=True,
        )
    )


def _seed_module(project_dir: str, skills_by_profile: dict) -> None:
    """Write the minimum store a ``get_module_info`` call needs."""
    _architecture_core.save_project_meta(
        {
            'name': 'demo',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'mod': {}},
        },
        project_dir,
    )
    _architecture_core.save_module_derived(
        'mod',
        {'name': 'mod', 'paths': {'module': 'mod'}, 'internal_dependencies': [], 'commands': {}},
        project_dir,
    )
    _architecture_core.save_module_enriched(
        'mod',
        {'purpose': 'library', 'responsibility': 'demo', 'skills_by_profile': skills_by_profile},
        project_dir,
    )


def _profile(*, defaults=(), optionals=()) -> dict:
    """Build one profile block from skill notations."""
    return {
        'defaults': [{'skill': skill, 'description': 'd'} for skill in defaults],
        'optionals': [{'skill': skill, 'description': 'd'} for skill in optionals],
    }


def _notations(entries) -> list[str]:
    """Return the skill notations of a profile's entry list."""
    return [entry['skill'] if isinstance(entry, dict) else entry for entry in entries]


def test_read_seam_drops_a_skill_excluded_after_enrichment():
    """A stored optional the repository now excludes never reaches the served map."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(project_dir, {'implementation': _profile(defaults=[_LIVE], optionals=[_EXCLUDED])})
        _write_marshal(project_dir, 'java-quarkus')

        payload = get_module_info('mod', project_dir=project_dir)

    implementation = payload['skills_by_profile']['implementation']
    assert _EXCLUDED not in _notations(implementation['optionals'])
    assert _LIVE in _notations(implementation['defaults'])


def test_read_seam_keeps_the_skill_without_an_exclusion():
    """Matched negative control: the same stored map keeps the skill unexcluded."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(project_dir, {'implementation': _profile(defaults=[_LIVE], optionals=[_EXCLUDED])})
        _write_marshal(project_dir)

        payload = get_module_info('mod', project_dir=project_dir)

    assert _EXCLUDED in _notations(payload['skills_by_profile']['implementation']['optionals'])


def test_read_seam_applies_the_union_of_domain_exclusions():
    """The domain-less stored map is vetoed by every domain's exclusion list."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(
            project_dir,
            {
                'implementation': _profile(
                    defaults=[_LIVE],
                    optionals=[_EXCLUDED, 'pm-dev-python:pytest-testing'],
                )
            },
        )
        _write_skill_domains(
            project_dir,
            {
                'java': {'excluded_skills': ['java-quarkus']},
                'python': {'excluded_skills': ['pytest-testing']},
            },
        )

        payload = get_module_info('mod', project_dir=project_dir)

    optionals = _notations(payload['skills_by_profile']['implementation']['optionals'])
    assert _EXCLUDED not in optionals
    assert 'pm-dev-python:pytest-testing' not in optionals


def test_overview_renders_the_effective_skill_count():
    """The display surface counts what the served map shows, not the raw store."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(project_dir, {'implementation': _profile(defaults=[_LIVE], optionals=[_EXCLUDED])})
        _write_marshal(project_dir, 'java-quarkus')

        rendered = render_overview(project_dir)

    assert '- implementation: 1 skill' in rendered


def test_module_deep_dive_renders_the_effective_skill_count():
    """The deep-dive render agrees with the TOON read of the same module."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(project_dir, {'implementation': _profile(defaults=[_LIVE], optionals=[_EXCLUDED])})
        _write_marshal(project_dir, 'java-quarkus')

        rendered = render_module_markdown('mod', project_dir, 400)

    assert '- implementation: 1 skill' in rendered


def test_overview_counts_the_stored_skill_without_an_exclusion():
    """Matched negative control: the same store renders its second skill."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(project_dir, {'implementation': _profile(defaults=[_LIVE], optionals=[_EXCLUDED])})
        _write_marshal(project_dir)

        rendered = render_overview(project_dir)

    assert '- implementation: 2 skills' in rendered


def test_read_seam_marks_an_exclusion_emptied_profile_minimal():
    """A profile the veto empties is a deliberate empty, not an unresolved one."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed_module(project_dir, {'implementation': _profile(optionals=[_EXCLUDED])})
        _write_marshal(project_dir, 'java-quarkus')

        payload = get_module_info('mod', project_dir=project_dir)

    implementation = payload['skills_by_profile']['implementation']
    assert implementation['optionals'] == []
    assert implementation.get('minimal') is True
    assert not any('implementation' in warning for warning in payload.get('warnings', []))
