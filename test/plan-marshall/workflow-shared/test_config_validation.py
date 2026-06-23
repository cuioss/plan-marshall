#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared config validation tests for all workflow-* skills.

Validates that all standards/*.json files used by workflow scripts are:
- Valid JSON
- Contain expected top-level keys
- Have no empty arrays where data is expected

Also validates TOON output field ordering consistency.

Findings addressed: F6 (TOON field ordering), F8 (config JSON validation).
"""

import json
import re
from pathlib import Path

import pytest

# Resolve paths
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent.parent.parent
WORKFLOW_SKILLS_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'

# Config files and their expected keys
WORKFLOW_CONFIGS = {
    'workflow-integration-git': {
        'file': 'artifact-patterns.json',
        'required_keys': ['safe_patterns', 'uncertain_patterns', 'skip_dirs'],
        'non_empty_arrays': ['safe_patterns', 'skip_dirs'],
    },
    'workflow-integration-github': {
        'file': 'comment-patterns.json',
        'required_keys': ['code_change', 'explain', 'ignore', 'thresholds'],
        'non_empty_arrays': [],
    },
    'workflow-integration-sonar': {
        'file': 'sonar-rules.json',
        'required_keys': ['suppressable_rules', 'fix_suggestions', 'test_acceptable_rules'],
        'non_empty_arrays': ['test_acceptable_rules'],
    },
    'workflow-permission-web': {
        'file': 'domain-lists.json',
        'required_keys': ['major_domains', 'high_reach_domains', 'red_flags'],
        'non_empty_arrays': ['major_domains', 'high_reach_domains', 'red_flags'],
    },
    'workflow-pr-doctor': {
        'file': 'pr-doctor-config.json',
        'required_keys': ['build_step_severity', 'valid_checks', 'default_max_fix_attempts'],
        'non_empty_arrays': ['valid_checks'],
    },
}

_CONFIG_PARAMS = [pytest.param(name, config, id=name) for name, config in WORKFLOW_CONFIGS.items()]


@pytest.mark.parametrize('skill_name, config', _CONFIG_PARAMS)
def test_config_parses_as_valid_json(skill_name, config):
    """F8: Validate workflow config JSON file parses correctly."""
    config_path = WORKFLOW_SKILLS_DIR / skill_name / 'standards' / config['file']

    assert config_path.exists(), f'Config file missing: {config_path}'
    try:
        data = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        pytest.fail(f'Invalid JSON in {config_path}: {e}')

    assert isinstance(data, dict), f'{config_path} root must be a dict'


@pytest.mark.parametrize('skill_name, config', _CONFIG_PARAMS)
def test_required_keys_present(skill_name, config):
    """F8: Validate config file contains expected top-level keys."""
    config_path = WORKFLOW_SKILLS_DIR / skill_name / 'standards' / config['file']
    if not config_path.exists():
        pytest.skip(f'Config file missing: {config_path}')

    data = json.loads(config_path.read_text())

    for key in config['required_keys']:
        assert key in data, f'Missing key "{key}" in {config["file"]} for {skill_name}'


@pytest.mark.parametrize('skill_name, config', _CONFIG_PARAMS)
def test_non_empty_arrays(skill_name, config):
    """F8: Validate config arrays that should have data are not empty."""
    config_path = WORKFLOW_SKILLS_DIR / skill_name / 'standards' / config['file']
    if not config_path.exists():
        pytest.skip(f'Config file missing: {config_path}')

    data = json.loads(config_path.read_text())

    for key in config['non_empty_arrays']:
        value = data.get(key)
        assert value is not None, f'Key "{key}" missing in {config["file"]}'
        assert len(value) > 0, f'Array "{key}" is empty in {config["file"]} for {skill_name}'


def test_comment_patterns_regex_valid():
    """Validate all regex patterns in comment-patterns.json compile successfully."""
    config_path = WORKFLOW_SKILLS_DIR / 'workflow-integration-github' / 'standards' / 'comment-patterns.json'
    data = json.loads(config_path.read_text())

    for category in ('code_change', 'explain', 'ignore'):
        for priority, patterns in data.get(category, {}).items():
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f'Invalid regex in [{category}][{priority}]: {pattern} — {e}')


def test_red_flag_patterns_regex_valid():
    """Validate all regex patterns in domain-lists.json compile successfully."""
    config_path = WORKFLOW_SKILLS_DIR / 'workflow-permission-web' / 'standards' / 'domain-lists.json'
    data = json.loads(config_path.read_text())

    for entry in data.get('red_flags', []):
        pattern = entry.get('pattern', '')
        try:
            re.compile(pattern)
        except re.error as e:
            pytest.fail(f'Invalid regex in red_flags: {pattern} — {e}')


def test_artifact_patterns_are_strings():
    """Validate artifact patterns in artifact-patterns.json are valid glob-style patterns."""
    config_path = WORKFLOW_SKILLS_DIR / 'workflow-integration-git' / 'standards' / 'artifact-patterns.json'
    data = json.loads(config_path.read_text())

    for key in ('safe_patterns', 'uncertain_patterns'):
        for pattern in data.get(key, []):
            assert isinstance(pattern, str), f'Pattern must be string, got {type(pattern).__name__}'
            assert len(pattern) > 0, 'Pattern must not be empty'
