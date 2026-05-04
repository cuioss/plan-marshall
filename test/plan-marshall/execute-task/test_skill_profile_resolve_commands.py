"""Lock the resolve-command contract for execute-task profiles.

Lesson 2026-05-03-21-003 (and three consolidated antecedents) documented that
per-task verification was too lenient: the implementation profile resolved
``compile`` (mypy on production sources only, no ruff) and the module_testing
profile resolved ``module-tests`` (pytest only, no static analysis on tests).
Static-analysis regressions accumulated silently across tasks and only
surfaced at the holistic verification step.

These tests assert that ``execute-task/SKILL.md`` documents the tightened
contract:

- implementation profile resolves ``quality-gate`` (mypy + ruff on production)
- module_testing profile resolves ``verify`` (= quality-gate + module-tests)
- the Common Workflow safety-net branch maps both profiles to the same
  stricter commands
- the Enforcement Constraints block requires ``quality-gate`` / ``verify`` to
  exit cleanly before a task may be marked ``done``

The SKILL.md document is the authoritative source consumed by the LLM agent
that runs the per-task workflow; pinning these strings prevents silent drift
back to the lax pre-lesson behaviour.
"""

from pathlib import Path

import pytest

SKILL_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
    / 'execute-task' / 'SKILL.md'
)


@pytest.fixture(scope='module')
def skill_text() -> str:
    """Read execute-task SKILL.md once per module."""
    return SKILL_PATH.read_text(encoding='utf-8')


def _section_body(text: str, heading: str, next_heading_prefix: str = '## ') -> str:
    """Return the body between ``heading`` and the next heading at the same level."""
    start = text.index(heading)
    after_start = start + len(heading)
    next_idx = text.find('\n' + next_heading_prefix, after_start)
    return text[start:next_idx] if next_idx != -1 else text[start:]


def test_implementation_profile_resolves_quality_gate(skill_text: str) -> None:
    section = _section_body(skill_text, '## Profile: implementation')

    assert 'resolve command: `quality-gate`' in section, (
        'implementation profile must resolve `quality-gate`, not `compile`. '
        'Lesson 2026-05-03-21-003 requires ruff to run alongside mypy on '
        'production sources at task time.'
    )
    assert 'resolve command: `compile`' not in section, (
        'implementation profile must not resolve the looser `compile` target.'
    )


def test_module_testing_profile_resolves_verify(skill_text: str) -> None:
    section = _section_body(skill_text, '## Profile: module_testing')

    assert 'resolve command: `verify`' in section, (
        'module_testing profile must resolve `verify` (quality-gate + '
        'module-tests), not `module-tests` alone. Lesson 2026-05-03-21-003 '
        'requires mypy + ruff to run on test files at task time.'
    )
    assert 'resolve command: `module-tests`' not in section, (
        'module_testing profile must not resolve the looser `module-tests` '
        'target on its Step 5 line.'
    )


def test_safety_net_branch_maps_to_strict_commands(skill_text: str) -> None:
    expected = (
        'Where `{resolve_command}` depends on profile: '
        '`implementation` → `quality-gate`, `module_testing` → `verify`.'
    )
    assert expected in skill_text, (
        'The Common Workflow safety-net branch must map both profiles to the '
        'same stricter resolve commands as the per-profile Step 5 lines.'
    )


def test_constraints_block_requires_strict_gate(skill_text: str) -> None:
    constraints_section = _section_body(
        skill_text, '**Constraints:**', next_heading_prefix='## '
    )

    assert 'MUST NOT be marked `done`' in constraints_section, (
        'Constraints block must forbid marking a task done before the strict '
        'gate exits cleanly.'
    )
    assert '`quality-gate`' in constraints_section
    assert '`verify`' in constraints_section
    assert 'necessary but not sufficient' in constraints_section, (
        'Constraints block must explicitly state that module-tests passing '
        'alone is necessary but not sufficient.'
    )
