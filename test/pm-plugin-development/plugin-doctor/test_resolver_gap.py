#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the resolver-gap rule family in plugin-doctor.

Two rules guard against the resolver-gap anti-pattern from driving lesson
2026-04-27-18-005:

- ``skill-resolver-gap`` (warning): flags skill ``SKILL.md`` and
  ``standards/*.md`` prose containing LLM-Glob discovery patterns
  (``Use Glob:``, ``Glob pattern:``, ``Discover ... using Glob``,
  ``find ... using Glob patterns``) without an adjacent
  ``python3 .plan/execute-script.py`` invocation within the next 5 lines.
  Honors a per-file ``plugin-doctor-disable: [skill-resolver-gap]``
  frontmatter key (Granularity-3), which suppresses every finding in the file.
  The retired ``<!-- doctor-ignore: resolver-gap -->`` inline marker is no
  longer honored.

- ``agent-glob-resolver-workaround`` (error): flags ``agents/*.md`` whose
  YAML frontmatter ``tools:`` field includes ``Glob`` unless the same
  frontmatter declares ``forwards_tool_capabilities: true`` as a typed
  boolean flag. The legacy ``# resolver-glob-exempt:`` body-marker
  exemption has been removed in favor of the structured frontmatter flag.

Tests exercise both scanners via direct import (Tier 2 — fast, isolated).
"""

from conftest import get_script_path, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_analyze_markdown = _load_module('_analyze_markdown', '_analyze_markdown.py')
_analyze_shared = _load_module('_analyze_shared', '_analyze_shared.py')

check_resolver_gap = _analyze_markdown.check_resolver_gap
check_agent_glob_resolver_workaround = _analyze_shared.check_agent_glob_resolver_workaround
_frontmatter_declares_glob_tool = _analyze_shared._frontmatter_declares_glob_tool
_frontmatter_declares_forwards_tool_capabilities = (
    _analyze_shared._frontmatter_declares_forwards_tool_capabilities
)


# =============================================================================
# skill-resolver-gap
# =============================================================================


def test_resolver_gap_use_glob_without_resolver_flagged():
    """`Use Glob:` prose without resolver call within 5 lines triggers a finding."""
    content = '## Discovery\nUse Glob: marketplace/bundles/*/skills/*/SKILL.md\nThen read each file.\n'
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1
    assert findings[0]['line'] == 2


def test_resolver_gap_use_glob_with_resolver_not_flagged():
    """`Use Glob:` followed by `execute-script.py` within 5 lines is exempt."""
    content = (
        '## Discovery\n'
        'Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n'
        'Then resolve via:\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:foo:bar list\n'
        '```\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_glob_pattern_phrase_flagged():
    """`Glob pattern:` trigger phrase is detected."""
    content = 'Glob pattern: **/*.py\nIterate the matches.\n'
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1
    assert findings[0]['line'] == 1


def test_resolver_gap_discover_using_glob_flagged():
    """`Discover ... using Glob` trigger phrase is detected."""
    content = 'Discover all components using Glob to find candidates.\nThen proceed.\n'
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_find_using_glob_patterns_flagged():
    """`find ... using Glob patterns` trigger phrase is detected."""
    content = 'find candidate files using Glob patterns: **/*.md\n'
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_frontmatter_disable_suppresses_whole_file():
    """A ``plugin-doctor-disable: [skill-resolver-gap]`` frontmatter key suppresses findings."""
    content = (
        '---\n'
        'plugin-doctor-disable: [skill-resolver-gap]\n'
        '---\n'
        'Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n'
        'Manual diagnostic only.\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_frontmatter_disable_block_list_form():
    """The YAML block-list ``plugin-doctor-disable`` form is honored."""
    content = (
        '---\n'
        'plugin-doctor-disable:\n'
        '  - skill-resolver-gap\n'
        '---\n'
        'Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_frontmatter_disable_for_other_rule_does_not_suppress():
    """A disable list naming a DIFFERENT rule leaves the finding flagged."""
    content = (
        '---\n'
        'plugin-doctor-disable: [some-other-rule]\n'
        '---\n'
        'Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_retired_inline_marker_no_longer_suppresses():
    """The retired ``<!-- doctor-ignore: resolver-gap -->`` marker is ignored."""
    content = (
        '<!-- doctor-ignore: resolver-gap -->\n'
        'Use Glob: marketplace/bundles/*/skills/*/SKILL.md\n'
        'Manual diagnostic only.\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_resolver_call_at_5th_line_still_within_window():
    """Resolver call exactly 5 lines after match is still within the window."""
    content = (
        'Use Glob: **/*.py\n'
        'filler 1\n'
        'filler 2\n'
        'filler 3\n'
        'filler 4\n'
        'python3 .plan/execute-script.py plan-marshall:foo:bar\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_resolver_call_after_window_flagged():
    """Resolver call beyond 5 lines after match is too far — finding emitted."""
    content = (
        'Use Glob: **/*.py\n'
        'filler 1\n'
        'filler 2\n'
        'filler 3\n'
        'filler 4\n'
        'filler 5\n'
        'python3 .plan/execute-script.py plan-marshall:foo:bar\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


def test_resolver_gap_unrelated_prose_not_flagged():
    """Prose without LLM-Glob trigger phrases produces no findings."""
    content = (
        '## Workflow\n'
        'Use the manage-files script to enumerate files.\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-files:manage-files list\n'
        '```\n'
    )
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert findings == []


def test_resolver_gap_case_insensitive_match():
    """Trigger phrase matching is case-insensitive."""
    content = 'USE GLOB: **/*.py\nfollow up\n'
    findings = check_resolver_gap(content, '/path/SKILL.md')
    assert len(findings) == 1


# =============================================================================
# agent-glob-resolver-workaround
# =============================================================================


def test_glob_in_inline_tools_without_exemption_flagged():
    """Agent with inline `tools: Read, Glob` and no exemption marker is flagged."""
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test agent\n'
        'tools: Read, Write, Glob\n'
        '---\n'
        '\n'
        '# My Agent\n'
        '\n'
        'Body content here.\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_glob_in_inline_tools_with_frontmatter_flag_not_flagged():
    """Inline `tools: ..., Glob` with `forwards_tool_capabilities: true` in frontmatter is exempt."""
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test agent\n'
        'tools: Read, Write, Glob\n'
        'forwards_tool_capabilities: true\n'
        '---\n'
        '\n'
        '# My Agent\n'
        '\n'
        'Body content.\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_glob_in_inline_tools_with_legacy_body_marker_still_flagged():
    """Legacy body marker `# resolver-glob-exempt: ...` is no longer authoritative.

    The body-comment marker exemption was removed in favor of the structured
    frontmatter flag `forwards_tool_capabilities: true`. An agent that still
    carries the legacy marker but lacks the frontmatter flag MUST be flagged.
    """
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test agent\n'
        'tools: Read, Write, Glob\n'
        '---\n'
        '\n'
        '# My Agent\n'
        '\n'
        '# resolver-glob-exempt: diagnostic-only agent — no resolver applies\n'
        '\n'
        'Body content.\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_frontmatter_flag_false_value_does_not_exempt():
    """`forwards_tool_capabilities: false` does NOT suppress the finding."""
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test agent\n'
        'tools: Read, Write, Glob\n'
        'forwards_tool_capabilities: false\n'
        '---\n'
        '\n'
        'Body.\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_frontmatter_flag_quoted_true_does_not_exempt():
    """Quoted `"true"` is NOT the canonical YAML boolean and does NOT exempt."""
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test agent\n'
        'tools: Read, Write, Glob\n'
        'forwards_tool_capabilities: "true"\n'
        '---\n'
        '\n'
        'Body.\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_glob_in_block_list_tools_with_frontmatter_flag_not_flagged():
    """Block-list `tools` form combined with `forwards_tool_capabilities: true` is exempt."""
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test agent\n'
        'tools:\n'
        '  - Read\n'
        '  - Write\n'
        '  - Glob\n'
        'forwards_tool_capabilities: true\n'
        '---\n'
        '\n'
        'Body.\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_glob_in_block_list_tools_without_exemption_flagged():
    """Block-list YAML form `tools:\\n  - Glob` is also detected."""
    content = '---\nname: my-agent\ndescription: Test agent\ntools:\n  - Read\n  - Write\n  - Glob\n---\n\nBody.\n'
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_no_glob_in_tools_not_flagged():
    """Agent without Glob in tools produces no finding regardless of body."""
    content = '---\nname: my-agent\ndescription: Test agent\ntools: Read, Write\n---\n\nBody.\n'
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_frontmatter_flag_missing_does_not_suppress():
    """Frontmatter without `forwards_tool_capabilities` key emits the finding."""
    content = '---\nname: my-agent\ndescription: Test\ntools: Read, Glob\n---\n\nBody.\n'
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_body_marker_outside_frontmatter_does_not_exempt():
    """Standalone `# resolver-glob-exempt:` body marker is no longer scoped as an exemption.

    Regression guard for the breaking refactor: even when the body contains
    the legacy marker on its own line (no surrounding context), the analyzer
    MUST NOT treat it as an exemption — the frontmatter flag is the sole
    authoritative signal.
    """
    content = (
        '---\n'
        'name: my-agent\n'
        'description: Test\n'
        'tools: Read, Glob\n'
        '---\n'
        '\n'
        '# resolver-glob-exempt: standalone marker\n'
    )
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert len(findings) == 1


def test_agent_without_frontmatter_not_flagged():
    """Agent without YAML frontmatter produces no finding (cannot determine tools)."""
    content = '# Agent\n\nNo frontmatter here.\n'
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_glob_substring_not_matched():
    """Word like ``GlobalState`` should not satisfy the Glob token check."""
    content = '---\nname: my-agent\ndescription: Test\ntools: Read, GlobalState\n---\n\nBody.\n'
    findings = check_agent_glob_resolver_workaround('/path/agents/my.md', content)
    assert findings == []


def test_frontmatter_declares_glob_inline():
    """Helper detects Glob in inline tools."""
    fm = 'name: x\ntools: Read, Glob, Write'
    assert _frontmatter_declares_glob_tool(fm) is True


def test_frontmatter_declares_glob_block():
    """Helper detects Glob in block-list tools."""
    fm = 'name: x\ntools:\n  - Read\n  - Glob\n'
    assert _frontmatter_declares_glob_tool(fm) is True


def test_frontmatter_no_glob():
    """Helper returns False when Glob absent."""
    fm = 'name: x\ntools: Read, Write'
    assert _frontmatter_declares_glob_tool(fm) is False


def test_frontmatter_declares_forwards_tool_capabilities_true():
    """Helper detects `forwards_tool_capabilities: true` as a top-level YAML flag."""
    fm = 'name: x\ntools: Read, Glob\nforwards_tool_capabilities: true'
    assert _frontmatter_declares_forwards_tool_capabilities(fm) is True


def test_frontmatter_declares_forwards_tool_capabilities_false():
    """Helper returns False when the flag is `false`."""
    fm = 'name: x\ntools: Read, Glob\nforwards_tool_capabilities: false'
    assert _frontmatter_declares_forwards_tool_capabilities(fm) is False


def test_frontmatter_declares_forwards_tool_capabilities_missing():
    """Helper returns False when the flag is absent."""
    fm = 'name: x\ntools: Read, Glob'
    assert _frontmatter_declares_forwards_tool_capabilities(fm) is False


def test_frontmatter_declares_forwards_tool_capabilities_quoted_rejected():
    """Helper rejects quoted `"true"` — only the lowercase YAML boolean is canonical."""
    fm = 'name: x\ntools: Read, Glob\nforwards_tool_capabilities: "true"'
    assert _frontmatter_declares_forwards_tool_capabilities(fm) is False


# =============================================================================
# Inline-marker removal guard
# =============================================================================


def test_resolver_gap_analyzer_source_has_no_inline_marker_references():
    """The resolver-gap analyzer source references none of the retired markers.

    The inline-marker suppression mechanism (``_SUPPRESS_MARKER`` /
    ``_IGNORE_MARKER`` / ``doctor-ignore``) was removed in favor of the
    config-based declarative-suppression substrate. ``check_resolver_gap`` lives
    in ``_analyze_markdown.py``; this guard reads the live source and asserts
    none of the retired tokens survive.
    """
    source = get_script_path(
        'pm-plugin-development',
        'plugin-doctor',
        '_analyze_markdown.py',
    ).read_text(encoding='utf-8')
    for marker in ('_SUPPRESS_MARKER', '_IGNORE_MARKER', 'doctor-ignore'):
        assert marker not in source, (
            f'Retired inline marker {marker!r} still present in _analyze_markdown.py'
        )
