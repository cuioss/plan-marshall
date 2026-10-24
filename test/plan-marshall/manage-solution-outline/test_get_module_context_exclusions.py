#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``get-module-context`` serves the vetoed ``skills_by_profile`` map.

PLAN-LB-80 D4. The outline phase reads placement context from this verb; the
enriched map it returns is the same map the architecture path serves, so the
repository's ``excluded_skills`` veto must bind here too. Without it a repository
that forbids a skill still sees it while placing a deliverable.
"""

import json
import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import create_marshal_json, load_script_module

_mod = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    'manage-solution-outline.py',
    module_name='manage_solution_outline_exclusions',
)

cmd_get_module_context = _mod.cmd_get_module_context

_arch_core = load_script_module(
    'plan-marshall',
    'manage-architecture',
    '_architecture_core.py',
    module_name='_architecture_core_outline_exclusions',
)

EXCLUDED = 'pm-dev-java:java-quarkus'
KEPT = 'pm-dev-java:java-core'


def _seed(project_dir: str) -> None:
    """Seed one module whose enriched map carries an excluded and a kept skill."""
    _arch_core.save_project_meta(
        {
            'name': 'demo',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'mod': {}},
        },
        project_dir,
    )
    _arch_core.save_module_derived(
        'mod',
        {'name': 'mod', 'paths': {'module': 'mod'}, 'internal_dependencies': [], 'commands': {}},
        project_dir,
    )
    _arch_core.save_module_enriched(
        'mod',
        {
            'responsibility': 'demo',
            'purpose': 'library',
            'skills_by_profile': {
                'implementation': {
                    'defaults': [{'skill': KEPT, 'description': 'd'}],
                    'optionals': [{'skill': EXCLUDED, 'description': 'd'}],
                }
            },
        },
        project_dir,
    )


def _write_marshal(project_dir: str, excluded: list[str]) -> Path:
    """Write the project's marshal.json with a java exclusion list."""
    return Path(
        create_marshal_json(
            Path(project_dir),
            config={'skill_domains': {'java': {'bundle': 'pm-dev-java', 'excluded_skills': excluded}}},
            nest_in_plan_dir=True,
        )
    )


def test_get_module_context_drops_an_excluded_skill():
    """The served context never carries a skill the repository forbids."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)
        _write_marshal(project_dir, ['java-quarkus'])

        result = cmd_get_module_context(Namespace(project_dir=project_dir))

    assert result['status'] == 'success'
    served = json.dumps(result['modules'])
    assert EXCLUDED not in served
    assert KEPT in served


def test_get_module_context_keeps_a_skill_without_an_exclusion():
    """Matched negative control: the same store keeps its skill unexcluded."""
    with tempfile.TemporaryDirectory() as project_dir:
        _seed(project_dir)
        _write_marshal(project_dir, [])

        result = cmd_get_module_context(Namespace(project_dir=project_dir))

    assert EXCLUDED in json.dumps(result['modules'])
