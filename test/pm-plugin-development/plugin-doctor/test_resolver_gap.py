#!/usr/bin/env python3
"""Tests for the resolver-gap rule family in plugin-doctor.

Two rules guard against the resolver-gap anti-pattern from driving lesson
2026-04-27-18-005:

- ``skill-resolver-gap`` (warning): flags skill ``SKILL.md`` and
  ``standards/*.md`` prose containing LLM-Glob discovery patterns
  (``Use Glob:``, ``Glob pattern:``, ``Discover ... using Glob``,
  ``find ... using Glob patterns``) without an adjacent
  ``python3 .plan/execute-script.py`` invocation within the next 5 lines.
  Honors ``<!-- doctor-ignore: resolver-gap -->`` exemption marker.

- ``agent-glob-resolver-workaround`` (error): flags ``agents/*.md`` whose
  YAML frontmatter ``tools:`` field includes ``Glob`` unless the agent body
  contains a ``# resolver-glob-exempt: <justification>`` marker.

Tests exercise both scanners via direct import (Tier 2 — fast, isolated).
"""

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_analyze_markdown = _load_module('_analyze_markdown', '_analyze_markdown.py')
_analyze_shared = _load_module('_analyze_shared', '_analyze_shared.py')

check_resolver_gap = _analyze_markdown.check_resolver_gap
check_agent_glob_resolver_workaround = _analyze_shared.check_agent_glob_resolver_workaround
_frontmatter_declares_glob_tool = _analyze_shared._frontmatter_declares_glob_tool


# =============================================================================
# skill-resolver-gap
# =============================================================================


def test_resolver_gap_use_glob_without_resolver_flagged():
    """`Use Glob:` prose without resolver call within 5 lines triggers a finding."""
    content = (
        "## Discovery\n"
        "Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n"
        "Then read each file.\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1
    assert findings[0]['line'] == 2


def test_resolver_gap_use_glob_with_resolver_not_flagged():
    """`Use Glob:` followed by `execute-script.py` within 5 lines is exempt."""
    content = (
        "## Discovery\n"
        "Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n"
        "Then resolve via:\n"
        "```bash\n"
        "python3 .plan/execute-script.py plan-marshall:foo:bar list\n"
        "```\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_glob_pattern_phrase_flagged():
    """`Glob pattern:` trigger phrase is detected."""
    content = (
        "Glob pattern: **/*.py\n"
        "Iterate the matches.\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1
    assert findings[0]['line'] == 1


def test_resolver_gap_discover_using_glob_flagged():
    """`Discover ... using Glob` trigger phrase is detected."""
    content = (
        "Discover all components using Glob to find candidates.\n"
        "Then proceed.\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_find_using_glob_patterns_flagged():
    """`find ... using Glob patterns` trigger phrase is detected."""
    content = (
        "find candidate files using Glob patterns: **/*.md\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_exemption_marker_suppresses_finding():
    """`<!-- doctor-ignore: resolver-gap -->` on prior line suppresses the finding."""
    content = (
        "<!-- doctor-ignore: resolver-gap -->\n"
        "Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n"
        "Manual diagnostic only.\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_exemption_must_be_immediately_preceding():
    """Exemption two lines above does NOT suppress the finding."""
    content = (
        "<!-- doctor-ignore: resolver-gap -->\n"
        "\n"
        "Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_resolver_call_at_5th_line_still_within_window():
    """Resolver call exactly 5 lines after match is still within the window."""
    content = (
        "Use Glob: **/*.py\n"
        "filler 1\n"
        "filler 2\n"
        "filler 3\n"
        "filler 4\n"
        "python3 .plan/execute-script.py plan-marshall:foo:bar\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_resolver_call_after_window_flagged():
    """Resolver call beyond 5 lines after match is too far — finding emitted."""
    content = (
        "Use Glob: **/*.py\n"
        "filler 1\n"
        "filler 2\n"
        "filler 3\n"
        "filler 4\n"
        "filler 5\n"
        "python3 .plan/execute-script.py plan-marshall:foo:bar\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_unrelated_prose_not_flagged():
    """Prose without LLM-Glob trigger phrases produces no findings."""
    content = (
        "## Workflow\n"
        "Use the manage-files script to enumerate files.\n"
        "```bash\n"
        "python3 .plan/execute-script.py plan-marshall:manage-files:manage-files list\n"
        "```\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_case_insensitive_match():
    """Trigger phrase matching is case-insensitive."""
    content = (
        "USE GLOB: **/*.py\n"
        "follow up\n"
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


# =============================================================================
# agent-glob-resolver-workaround
# =============================================================================


def test_glob_in_inline_tools_without_exemption_flagged():
    """Agent with inline `tools: Read, Glob` and no exemption marker is flagged."""
    content = (
        "---\n"
        "name: my-agent\n"
        "description: Test agent\n"
        "tools: Read, Write, Glob\n"
        "---\n"
        "\n"
        "# My Agent\n"
        "\n"
        "Body content here.\n"
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_glob_in_inline_tools_with_exemption_not_flagged():
    """Inline `tools: ..., Glob` with `# resolver-glob-exempt: <justification>` is exempt."""
    content = (
        "---\n"
        "name: my-agent\n"
        "description: Test agent\n"
        "tools: Read, Write, Glob\n"
        "---\n"
        "\n"
        "# My Agent\n"
        "\n"
        "# resolver-glob-exempt: diagnostic-only agent — no resolver applies\n"
        "\n"
        "Body content.\n"
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_glob_in_block_list_tools_without_exemption_flagged():
    """Block-list YAML form `tools:\\n  - Glob` is also detected."""
    content = (
        "---\n"
        "name: my-agent\n"
        "description: Test agent\n"
        "tools:\n"
        "  - Read\n"
        "  - Write\n"
        "  - Glob\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_no_glob_in_tools_not_flagged():
    """Agent without Glob in tools produces no finding regardless of body."""
    content = (
        "---\n"
        "name: my-agent\n"
        "description: Test agent\n"
        "tools: Read, Write\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_empty_exemption_marker_does_not_suppress():
    """`# resolver-glob-exempt:` with no justification does NOT suppress the finding."""
    content = (
        "---\n"
        "name: my-agent\n"
        "description: Test\n"
        "tools: Read, Glob\n"
        "---\n"
        "\n"
        "# resolver-glob-exempt:\n"
        "\n"
        "Body.\n"
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_agent_without_frontmatter_not_flagged():
    """Agent without YAML frontmatter produces no finding (cannot determine tools)."""
    content = "# Agent\n\nNo frontmatter here.\n"
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_glob_substring_not_matched():
    """Word like ``GlobalState`` should not satisfy the Glob token check."""
    content = (
        "---\n"
        "name: my-agent\n"
        "description: Test\n"
        "tools: Read, GlobalState\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_frontmatter_declares_glob_inline():
    """Helper detects Glob in inline tools."""
    fm = "name: x\ntools: Read, Glob, Write"
    assert _frontmatter_declares_glob_tool(fm) is True


def test_frontmatter_declares_glob_block():
    """Helper detects Glob in block-list tools."""
    fm = "name: x\ntools:\n  - Read\n  - Glob\n"
    assert _frontmatter_declares_glob_tool(fm) is True


def test_frontmatter_no_glob():
    """Helper returns False when Glob absent."""
    fm = "name: x\ntools: Read, Write"
    assert _frontmatter_declares_glob_tool(fm) is False
