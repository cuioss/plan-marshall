#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract test: the machine-local/secret scanner itself.

ADR-008 (Machine-global home-root anchor tier) and ADR-021 (Machine-local
effort-to-model map) establish that machine-specific configuration (such as
build server sockets/pids, machine-local effort pins, runtime credentials, or
host paths) must live in ~/.plan-marshall/machine-config.json, target-local
infrastructure, or git-ignored run-configuration.json — never in the tracked
.plan/marshal.json repository file.

This suite pins the scanner's classification over fixture configs. It reads no
committed config: a test that inspects this repository's own
``.plan/marshal.json`` makes its verdict depend on the live file, so the
scanner is exercised here against payloads built in the test.

The scanner classifies:
1. Prohibited machine-local top-level keys (e.g., build_server,
   machine_config, run_config).
2. Machine-specific path strings (/Users/, /home/, /tmp/, C:/, *.sock, *.pid)
   anywhere in the configuration.
3. Secret credential keys (auth_token, access_token, bearer_token, password,
   secret, api_key) anywhere in the configuration.
4. Effort declarations that are not abstract ordinal levels
   (level-1..level-7, inherit) — i.e. machine-local model pins.
5. Negative controls assert that violations are correctly flagged.
"""

from __future__ import annotations

import re
from typing import Any

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
        ({'project': {'home_path': '/home/alice/git/repo'}}, 'Machine-local path'),
        ({'project': {'tmp_path': '/tmp/build/agent'}}, 'Machine-local path'),
        ({'project': {'socket_path': '/run/pm.sock'}}, 'Machine-local path'),
        ({'project': {'pid_path': '/run/pm.pid'}}, 'Machine-local path'),
    ]

    for bad_config, expected_substr in test_cases:
        violations = find_machine_local_violations(bad_config)
        assert violations, f'Expected violations for {bad_config}, got none'
        assert any(expected_substr in v for v in violations), (
            f'Expected "{expected_substr}" in violations for {bad_config}, got: {violations}'
        )
