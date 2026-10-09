#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract test: no machine-local keys or secrets in tracked .plan/marshal.json.

ADR-008 (Machine-global home-root anchor tier) and ADR-021 (Machine-local
effort-to-model map) establish that machine-specific configuration (such as
build server sockets/pids, machine-local effort pins, runtime credentials, or
host paths) must live in ~/.plan-marshall/machine-config.json, target-local
infrastructure, or git-ignored run-configuration.json — never in the tracked
.plan/marshal.json repository file.

This test asserts that:
1. Tracked .plan/marshal.json contains no prohibited machine-local top-level keys
   (e.g., build_server, machine_config, run_config).
2. No machine-specific path strings (/Users/, /home/, /tmp/, C:/, *.sock, *.pid)
   appear anywhere in the configuration.
3. No secret credential keys (auth_token, access_token, bearer_token, password, secret, api_key)
   appear anywhere in the configuration.
4. Effort declarations use only abstract ordinal levels (level-1..level-7, inherit),
   never machine-local model pins.
5. Negative controls assert that violations are correctly flagged.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

#: Machine-local top-level sections that must never be committed.
PROHIBITED_TOP_LEVEL_KEYS = frozenset(
    {
        'runtime',
        'project_dir',
        'build_server',
        'machine_config',
        'run_config',
        'machine_local',
        'effort_pins',
        'model_pins',
    }
)

#: Key substrings that indicate secret credentials.
SECRET_KEY_PATTERNS = re.compile(
    r'(?:^|[_\-.])(secret|password|api[_\-]?key|auth[_\-]?token|access[_\-]?token|bearer[_\-]?token)(?:$|[_\-.])',
    re.IGNORECASE,
)

#: Regex matching machine-local filesystem paths.
MACHINE_LOCAL_PATH_RE = re.compile(
    r'^[a-zA-Z]:[/\\]|(?:^|[/\\])(?:home|Users)[/\\][a-zA-Z0-9_\-]+|\/tmp\/|\.sock$|\.pid$',
)

#: Abstract effort levels allowed in project-shared config.
VALID_EFFORT_LEVELS = frozenset(
    {
        'level-1',
        'level-2',
        'level-3',
        'level-4',
        'level-5',
        'level-6',
        'level-7',
        'inherit',
    }
)


def _repo_root() -> Path:
    """Resolve checkout root via git rev-parse."""
    completed = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=Path(__file__).resolve().parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip())


def find_machine_local_violations(config: dict[str, Any]) -> list[str]:
    """Scan a configuration dictionary and return descriptions of all violations found."""
    violations: list[str] = []

    # 1. Prohibited top-level keys
    for key in config:
        if key in PROHIBITED_TOP_LEVEL_KEYS:
            violations.append(f'Prohibited top-level machine-local key found: {key}')

    # 2. Recursive scan for secrets, machine paths, and invalid effort pins
    def _scan(obj: Any, path: str = '') -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f'{path}.{k}' if path else k

                # Check for secret keys
                if SECRET_KEY_PATTERNS.search(k):
                    violations.append(f'Secret key found in configuration: {current_path}')

                # Check effort values
                if 'effort' in current_path.split('.'):
                    if isinstance(v, str) and v not in VALID_EFFORT_LEVELS:
                        violations.append(f'Invalid effort level (possible model pin): {current_path}={v}')

                _scan(v, current_path)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _scan(item, f'{path}[{idx}]')
        elif isinstance(obj, str):
            if MACHINE_LOCAL_PATH_RE.search(obj):
                violations.append(f'Machine-local path string found: {path}="{obj}"')

    _scan(config)
    return violations


def test_tracked_marshal_json_has_no_machine_local_keys() -> None:
    """Tracked .plan/marshal.json must not carry machine-local keys or secrets."""
    # Read from HEAD in git to verify the tracked version
    root = _repo_root()
    completed = subprocess.run(
        ['git', 'show', 'HEAD:.plan/marshal.json'],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    config = json.loads(completed.stdout)
    assert isinstance(config, dict), '.plan/marshal.json must be a JSON object'

    violations = find_machine_local_violations(config)
    assert not violations, 'Tracked .plan/marshal.json carries machine-local keys:\n' + '\n'.join(
        f'  - {v}' for v in violations
    )


def test_on_disk_marshal_json_has_no_machine_local_keys() -> None:
    """The checkout file .plan/marshal.json must not carry machine-local keys or secrets."""
    root = _repo_root()
    marshal_path = root / '.plan' / 'marshal.json'
    assert marshal_path.exists(), f'{marshal_path} must exist'

    with open(marshal_path, encoding='utf-8') as f:
        config = json.load(f)

    violations = find_machine_local_violations(config)
    assert not violations, 'On-disk .plan/marshal.json carries machine-local keys:\n' + '\n'.join(
        f'  - {v}' for v in violations
    )


def test_negative_control_flags_prohibited_keys() -> None:
    """Negative control: scanner correctly detects each class of machine-local data."""
    test_cases: list[tuple[dict[str, Any], str]] = [
        ({'runtime': {'target': 'claude-code'}}, 'Prohibited top-level machine-local key found: runtime'),
        ({'project_dir': '/Users/alice/git'}, 'Prohibited top-level machine-local key found: project_dir'),
        ({'build_server': {'socket_path': '/tmp/pm.sock'}}, 'Prohibited top-level'),
        ({'machine_config': {'slots': 4}}, 'Prohibited top-level'),
        ({'run_config': {'trailer': 'test'}}, 'Prohibited top-level'),
        ({'credentials_config': {'api': {'auth_token': 'secret123'}}}, 'Secret key'),
        ({'credentials_config': {'service': {'password': 'pass'}}}, 'Secret key'),
        ({'orchestrator': {'effort': {'default': 'claude-3-5-sonnet'}}}, 'Invalid effort level'),
        ({'project': {'windows_slash': 'C:/build/agent'}}, 'Machine-local path'),
        ({'project': {'windows_backslash': 'C:\\build\\agent'}}, 'Machine-local path'),
    ]

    for bad_config, expected_substr in test_cases:
        violations = find_machine_local_violations(bad_config)
        assert violations, f'Expected violations for {bad_config}, got none'
        assert any(expected_substr in v for v in violations), (
            f'Expected "{expected_substr}" in violations for {bad_config}, got: {violations}'
        )
