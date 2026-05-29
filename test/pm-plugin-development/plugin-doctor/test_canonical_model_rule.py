#!/usr/bin/env python3
"""Tests for the ``hardcoded-model-on-canonical`` plugin-doctor rule.

Two error branches:

1. ``missing_implements``: canonical agent has ``model:`` or ``effort:``
   without ``implements: <ext-point>``.
2. ``shadowing_with_implements``: canonical agent has ``implements:
   <ext-point>`` AND ``model:`` or ``effort:``.

Variants emitted by the build target into ``target/claude/`` are exempt.
"""

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_analyze_markdown = _load_module('_analyze_markdown', '_analyze_markdown.py')

check_hardcoded_model_on_canonical = _analyze_markdown.check_hardcoded_model_on_canonical
DYNAMIC_LEVEL_EXECUTOR_REF = _analyze_markdown.DYNAMIC_LEVEL_EXECUTOR_REF


SOURCE_FILE = '/repo/marketplace/bundles/plan-marshall/agents/foo-agent.md'
TARGET_FILE = '/repo/target/claude/plan-marshall/agents/foo-agent.md'


def _frontmatter(*lines: str) -> str:
    """Return a synthetic frontmatter string (newline-joined)."""
    return '\n'.join(lines) + '\n'


# =============================================================================
# Branch 1: missing_implements
# =============================================================================


def test_canonical_with_model_no_implements_errors():
    fm = _frontmatter('name: foo-agent', 'tools: Read, Bash', 'model: opus')
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert len(findings) == 1
    assert findings[0]['branch'] == 'missing_implements'
    assert findings[0]['code'] == 'HARDCODED_MODEL_ON_CANONICAL'
    assert 'model:' in findings[0]['message']


def test_canonical_with_effort_no_implements_errors():
    fm = _frontmatter('name: foo-agent', 'effort: high')
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert len(findings) == 1
    assert findings[0]['branch'] == 'missing_implements'
    assert 'effort:' in findings[0]['message']


def test_canonical_with_model_and_effort_no_implements_errors_once():
    fm = _frontmatter('name: foo-agent', 'model: opus', 'effort: high')
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    # Single finding mentioning both fields, not two separate findings.
    assert len(findings) == 1
    assert findings[0]['branch'] == 'missing_implements'
    assert 'model:' in findings[0]['message']
    assert 'effort:' in findings[0]['message']


# =============================================================================
# Branch 2: shadowing_with_implements
# =============================================================================


def test_canonical_with_implements_and_model_errors():
    fm = _frontmatter(
        'name: foo-agent',
        'tools: Read',
        f'implements: {DYNAMIC_LEVEL_EXECUTOR_REF}',
        'model: opus',
    )
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert len(findings) == 1
    assert findings[0]['branch'] == 'shadowing_with_implements'


def test_canonical_with_implements_and_effort_errors():
    fm = _frontmatter(
        'name: foo-agent',
        f'implements: {DYNAMIC_LEVEL_EXECUTOR_REF}',
        'effort: medium',
    )
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert len(findings) == 1
    assert findings[0]['branch'] == 'shadowing_with_implements'


# =============================================================================
# Pass branches
# =============================================================================


def test_canonical_with_implements_no_model_passes():
    fm = _frontmatter(
        'name: foo-agent',
        'tools: Read, Bash',
        f'implements: {DYNAMIC_LEVEL_EXECUTOR_REF}',
    )
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert findings == []


def test_canonical_without_either_passes():
    fm = _frontmatter('name: foo-agent', 'tools: Read')
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert findings == []


def test_canonical_with_other_implements_value_still_treated_as_no_role():
    """A different `implements:` value does NOT exempt the agent.

    Only the canonical ext-point reference exempts; any other value
    means the agent is not opted into the variant system.
    """
    fm = _frontmatter(
        'name: foo-agent',
        'implements: some-other:ext-point-foo',
        'model: opus',
    )
    findings = check_hardcoded_model_on_canonical(fm, SOURCE_FILE)
    assert len(findings) == 1
    assert findings[0]['branch'] == 'missing_implements'


# =============================================================================
# Build-target exemption
# =============================================================================


def test_build_target_variant_file_is_exempt():
    """Files under target/claude/ are emitted by the build target — rule does not fire."""
    fm = _frontmatter(
        'name: foo-agent-high',
        'tools: Read',
        'model: sonnet',
        'effort: high',
    )
    findings = check_hardcoded_model_on_canonical(fm, TARGET_FILE)
    assert findings == []


def test_build_target_canonical_file_also_exempt():
    """Even the canonical no-suffix file under target/claude/ is exempt."""
    fm = _frontmatter('name: foo-agent', 'tools: Read', 'model: opus')
    findings = check_hardcoded_model_on_canonical(fm, TARGET_FILE)
    assert findings == []
