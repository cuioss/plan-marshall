#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fixture builders for the manage-config test modules.

Named ``_{domain}_fixtures.py`` rather than ``test_*.py`` because it declares no
test function: pytest collects any module matching ``test_*.py``, so a helper
under that name is imported, yields nothing, and is invisible in the run.

``create_marshal_json`` and ``create_run_config`` are NOT defined here. They are
the shared builders in ``test/conftest.py``, bound below to the baseline and
layout this subtree's modules expect, so that the one builder serves every
subtree and no module inherits a baseline by accident of which module it
imported.
"""

import functools
import json
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARSHAL_PRESET_JAVA, get_script_path
from conftest import create_marshal_json as _create_marshal_json
from conftest import create_run_config as _create_run_config

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-config', 'manage-config.py')

#: The shared marshal builder bound to this subtree's expectations: the
#: java-flavoured baseline, written flat into the fixture directory (which is
#: where ``plan_context`` points ``MARSHAL_PATH``), with the
#: ``raw-project-data.json`` module-facts companion beside it.
create_marshal_json = functools.partial(
    _create_marshal_json,
    preset=MARSHAL_PRESET_JAVA,
    nest_in_plan_dir=False,
    with_project_data=True,
)

#: The shared run-configuration builder, written flat for the same reason.
create_run_config = functools.partial(_create_run_config, nest_in_plan_dir=False)


def create_nested_marshal_json(fixture_dir: Path) -> Path:
    """Create marshal.json with nested skill_domains structure.

    System domain contains defaults and optionals.
    Domain-specific domains contain bundle reference and workflow_skill_extensions.

    NOTE: Profiles (core, implementation, module_testing, quality) are NOT stored
    in marshal.json - they are loaded from extension.py at runtime.
    """
    config = {
        'skill_domains': {
            'system': {
                'defaults': ['plan-marshall:persona-plan-marshall-agent'],
                'optionals': ['plan-marshall:diagnostic-patterns'],
            },
            'java': {
                'bundle': 'pm-dev-java',
                'workflow_skill_extensions': {
                    'outline': 'pm-dev-java:ext-outline-java',
                    'triage': 'pm-dev-java:ext-triage-java',
                },
            },
            'javascript': {
                'bundle': 'pm-dev-frontend',
                'workflow_skill_extensions': {'outline': 'pm-dev-frontend:ext-outline-frontend'},
            },
            'plan-marshall-plugin-dev': {
                'bundle': 'pm-plugin-development',
                'workflow_skill_extensions': {
                    'outline': 'pm-plugin-development:ext-outline-workflow',
                    'triage': 'pm-plugin-development:ext-triage-plugin',
                },
            },
        },
        'system': {
            'retention': {'logs_days': 1, 'archived_plans_days': 5, 'temp_on_maintenance': True}
        },
        'plan': {
            'phase-1-init': {
                'branch_strategy': 'direct',
            },
            'phase-2-refine': {
                'confidence_threshold': 95,
            },
            'phase-5-execute': {
                'compatibility': 'breaking',
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:archive-plan': {},
                },
            },
        },
        'providers': [
            {
                'skill_name': 'workflow-integration-github',
                'display_name': 'GitHub CLI (gh)',
                'auth_type': 'system',
                'default_url': 'https://github.com',
                'description': 'GitHub CI provider via gh CLI',
                'verify_command': 'gh auth status',
                'provider': 'unknown',
                'repo_url': None,
                'detected_at': None,
            },
        ],
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))
    return marshal_path


def parse_toon_output(output: str) -> dict:
    """Parse TOON output to dict (simplified parser for tests)."""
    result = {}
    lines = output.strip().split('\n')
    for line in lines:
        if ':' in line and not line.endswith(':'):
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Try to parse as JSON for lists/bools/numbers
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                result[key] = value
        elif line.startswith('- '):
            # Array item
            if 'items' not in result:
                result['items'] = []
            result['items'].append(line[2:].strip())
    return result
