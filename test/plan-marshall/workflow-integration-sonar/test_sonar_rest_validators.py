#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for ``sonar_rest.py``.

Covers the ``--component`` flag declared by the ``metrics`` subcommand
(via ``add_component_arg``). ``metrics`` also requires ``--project``
(unrelated to canonical validation — it's a SonarQube project key, not
a marketplace component notation).

Malformed --component input must surface
``status: error / error: invalid_component`` on stdout TOON (exit 0).

Re-uses ``test/plan-marshall/_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar_rest.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['component'])
def test_metrics_rejects_invalid_component(axis, bad_value):
    """Malformed --component for ``metrics`` surfaces invalid_component.

    ``--project`` is required by argparse on this subcommand; we pass a
    syntactically valid (but functionally arbitrary) value so the
    failure is unambiguously attributed to --component.
    """
    result = run_script(
        SCRIPT_PATH,
        'metrics',
        '--project',
        'sonarqube-project-key',
        '--component',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_component')


def test_metrics_accepts_canonical_component():
    """Happy-path canonical component MUST NOT trigger invalid_component.

    The script will fail with another error (no Sonar credentials,
    network unreachable, etc.) but the failure cause MUST NOT be the
    canonical identifier validator.
    """
    result = run_script(
        SCRIPT_PATH,
        'metrics',
        '--project',
        'sonarqube-project-key',
        '--component',
        HAPPY_VALUES['component'],
    )
    assert_not_invalid_field(result, 'invalid_component')
