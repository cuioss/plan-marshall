#!/usr/bin/env python3
"""Shared test helpers for plan-marshall-config tests.

Provides common fixtures and utilities used across all test modules.
"""

import json
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-plan-marshall-config', 'plan-marshall-config.py')


def create_run_config(fixture_dir: Path, config: dict | None = None) -> Path:
    """Create run-configuration.json in fixture directory.

    Args:
        fixture_dir: Directory to create file in
        config: Optional config dict (uses default if not provided)

    Returns:
        Path to created file
    """
    if config is None:
        config = {
            'version': 1,
            'commands': {},
            'ci': {'git_present': True, 'authenticated_tools': ['git', 'gh'], 'verified_at': '2025-01-15T10:30:00Z'},
        }
    run_config_path = fixture_dir / 'run-configuration.json'
    run_config_path.write_text(json.dumps(config, indent=2))
    return run_config_path


def create_marshal_json(fixture_dir: Path, config: dict | None = None) -> Path:
    """Create marshal.json in fixture directory.

    Also creates raw-project-data.json with module facts (source of truth for modules).
    """
    if config is None:
        config = {
            'skill_domains': {
                'java': {'defaults': ['pm-dev-java:java-create'], 'optionals': ['pm-dev-java:java-cdi']},
                'java-testing': {'defaults': ['pm-dev-java:junit-core'], 'optionals': []},
            },
            'system': {
                'retention': {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}
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
                    'commit_strategy': 'per_deliverable',
                },
                'phase-6-verify': {
                    'max_iterations': 5,
                    '1_quality_check': True,
                    '2_build_verify': True,
                    'domain_steps': {},
                },
                'phase-7-finalize': {
                    'max_iterations': 3,
                    '1_commit_push': True,
                    '2_create_pr': True,
                    '3_automated_review': True,
                    '4_sonar_roundtrip': True,
                    '5_knowledge_capture': True,
                    '6_lessons_capture': True,
                },
            },
            'ci': {
                'repo_url': 'https://github.com/test/repo',
                'provider': 'github',
                'detected_at': '2025-01-15T10:30:00Z',
            },
        }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    # Also create raw-project-data.json with module facts (source of truth)
    raw_data = {
        'project': {'name': 'test-project'},
        'modules': [
            {'name': 'my-core', 'path': 'my-core', 'parent': None, 'build_systems': ['maven'], 'packaging': 'jar'},
            {'name': 'my-ui', 'path': 'my-ui', 'parent': None, 'build_systems': ['maven', 'npm'], 'packaging': 'war'},
        ],
    }
    raw_data_path = fixture_dir / 'raw-project-data.json'
    raw_data_path.write_text(json.dumps(raw_data, indent=2))

    return marshal_path


def create_nested_marshal_json(fixture_dir: Path) -> Path:
    """Create marshal.json with nested skill_domains structure.

    System domain contains task_executors.
    Domain-specific domains contain bundle reference and workflow_skill_extensions.

    NOTE: Profiles (core, implementation, module_testing, quality) are NOT stored
    in marshal.json - they are loaded from extension.py at runtime.
    """
    config = {
        'skill_domains': {
            'system': {
                'defaults': ['plan-marshall:general-development-rules'],
                'optionals': ['plan-marshall:diagnostic-patterns'],
                'task_executors': {
                    'implementation': 'pm-workflow:task-implementation',
                    'module_testing': 'pm-workflow:task-module_testing',
                    'integration_testing': 'pm-workflow:task-integration_testing',
                },
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
                    'outline': 'pm-plugin-development:ext-outline-plugin',
                    'triage': 'pm-plugin-development:ext-triage-plugin',
                },
            },
        },
        'system': {
            'retention': {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}
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
                'commit_strategy': 'per_deliverable',
            },
            'phase-6-verify': {
                'max_iterations': 5,
                '1_quality_check': True,
                '2_build_verify': True,
                'domain_steps': {},
            },
            'phase-7-finalize': {
                'max_iterations': 3,
                '1_commit_push': True,
                '2_create_pr': True,
                '3_automated_review': True,
                '4_sonar_roundtrip': True,
                '5_knowledge_capture': True,
                '6_lessons_capture': True,
            },
        },
        'ci': {'repo_url': None, 'provider': 'unknown', 'detected_at': None},
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
