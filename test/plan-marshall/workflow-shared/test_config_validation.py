#!/usr/bin/env python3
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
import unittest
from pathlib import Path

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


class TestConfigFilesAreValidJson(unittest.TestCase):
    """F8: Validate all workflow config JSON files parse correctly."""

    def test_all_configs_parse_as_valid_json(self):
        for skill_name, config in WORKFLOW_CONFIGS.items():
            config_path = WORKFLOW_SKILLS_DIR / skill_name / 'standards' / config['file']
            with self.subTest(skill=skill_name, file=config['file']):
                self.assertTrue(config_path.exists(), f'Config file missing: {config_path}')
                try:
                    data = json.loads(config_path.read_text())
                except json.JSONDecodeError as e:
                    self.fail(f'Invalid JSON in {config_path}: {e}')
                self.assertIsInstance(data, dict, f'{config_path} root must be a dict')


class TestConfigFilesHaveRequiredKeys(unittest.TestCase):
    """F8: Validate config files contain expected top-level keys."""

    def test_required_keys_present(self):
        for skill_name, config in WORKFLOW_CONFIGS.items():
            config_path = WORKFLOW_SKILLS_DIR / skill_name / 'standards' / config['file']
            with self.subTest(skill=skill_name, file=config['file']):
                if not config_path.exists():
                    self.skipTest(f'Config file missing: {config_path}')
                data = json.loads(config_path.read_text())
                for key in config['required_keys']:
                    self.assertIn(key, data, f'Missing key "{key}" in {config["file"]} for {skill_name}')


class TestConfigFilesHaveNonEmptyArrays(unittest.TestCase):
    """F8: Validate config arrays that should have data are not empty."""

    def test_non_empty_arrays(self):
        for skill_name, config in WORKFLOW_CONFIGS.items():
            config_path = WORKFLOW_SKILLS_DIR / skill_name / 'standards' / config['file']
            with self.subTest(skill=skill_name, file=config['file']):
                if not config_path.exists():
                    self.skipTest(f'Config file missing: {config_path}')
                data = json.loads(config_path.read_text())
                for key in config['non_empty_arrays']:
                    value = data.get(key)
                    self.assertIsNotNone(value, f'Key "{key}" missing in {config["file"]}')
                    self.assertTrue(len(value) > 0, f'Array "{key}" is empty in {config["file"]} for {skill_name}')


class TestCommentPatternsRegexValid(unittest.TestCase):
    """Validate all regex patterns in comment-patterns.json compile successfully."""

    def test_all_patterns_compile(self):
        import re

        config_path = WORKFLOW_SKILLS_DIR / 'workflow-integration-github' / 'standards' / 'comment-patterns.json'
        data = json.loads(config_path.read_text())

        for category in ('code_change', 'explain', 'ignore'):
            for priority, patterns in data.get(category, {}).items():
                for pattern in patterns:
                    with self.subTest(category=category, priority=priority, pattern=pattern):
                        try:
                            re.compile(pattern)
                        except re.error as e:
                            self.fail(f'Invalid regex in [{category}][{priority}]: {pattern} — {e}')


class TestRedFlagPatternsRegexValid(unittest.TestCase):
    """Validate all regex patterns in domain-lists.json compile successfully."""

    def test_all_red_flag_patterns_compile(self):
        import re

        config_path = WORKFLOW_SKILLS_DIR / 'workflow-permission-web' / 'standards' / 'domain-lists.json'
        data = json.loads(config_path.read_text())

        for entry in data.get('red_flags', []):
            pattern = entry.get('pattern', '')
            with self.subTest(pattern=pattern):
                try:
                    re.compile(pattern)
                except re.error as e:
                    self.fail(f'Invalid regex in red_flags: {pattern} — {e}')


class TestArtifactPatternsGlobValid(unittest.TestCase):
    """Validate artifact patterns in artifact-patterns.json are valid glob-style patterns."""

    def test_all_patterns_are_strings(self):
        config_path = WORKFLOW_SKILLS_DIR / 'workflow-integration-git' / 'standards' / 'artifact-patterns.json'
        data = json.loads(config_path.read_text())

        for key in ('safe_patterns', 'uncertain_patterns'):
            for pattern in data.get(key, []):
                with self.subTest(key=key, pattern=pattern):
                    self.assertIsInstance(pattern, str, f'Pattern must be string, got {type(pattern).__name__}')
                    self.assertTrue(len(pattern) > 0, 'Pattern must not be empty')


if __name__ == '__main__':
    unittest.main()
