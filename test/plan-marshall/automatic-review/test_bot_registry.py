#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for automatic-review/scripts/bot_registry.py — the data-not-code bot loader.

The registry parses each ``automatic-review/standards/{bot_kind}.md`` fenced-YAML
data block ONCE and exposes stable accessors so the finding store, the re-review
strategy registry, and the producer pre-filter DERIVE what they need instead of
hard-coding three bots across three code files.

Coverage:

1. Shipped-standards contract — the real ``standards/*.md`` docs parse into the
   expected bot set, login map, triggers, skip-label flags, ignore patterns, and
   severity maps.
2. Derived ``BOT_KINDS`` — ``_findings_core.BOT_KINDS`` equals the registry's
   ``bot_kinds()`` (proving it is derived, not a literal).
3. Constrained-YAML reader units — the scalar/comment/block parsers over
   synthetic blocks, including quoted values carrying ``#`` and ``:``.
4. Robustness — a missing or empty standards directory yields an empty registry
   rather than raising; unknown bot kinds return empty defaults.

Module import resolves via the root conftest's marketplace PYTHONPATH setup
(``import bot_registry``).
"""

import bot_registry

# The three bots shipped as standards docs in this skill.
_SHIPPED_BOTS = ['coderabbit', 'gemini', 'sourcery']


# =============================================================================
# 1. Shipped-standards contract (the real standards/*.md docs)
# =============================================================================


def test_bot_kinds_equals_shipped_set_sorted():
    """``bot_kinds()`` returns the shipped bot set in deterministic sorted order."""
    assert bot_registry.bot_kinds() == sorted(_SHIPPED_BOTS)


def test_bot_kinds_is_deterministically_sorted():
    """Repeated calls return the same sorted list (load order is stable)."""
    first = bot_registry.bot_kinds()
    second = bot_registry.bot_kinds()
    assert first == second == sorted(first)


def test_login_to_bot_kind_maps_every_shipped_author():
    """Each shipped bot's ``author_login`` resolves to its ``bot_kind``."""
    mapping = bot_registry.login_to_bot_kind()
    assert mapping == {
        'coderabbitai': 'coderabbit',
        'gemini-code-assist': 'gemini',
        'sourcery-ai': 'sourcery',
    }


def test_trigger_comment_per_bot():
    """Each bot's re-review trigger comment is read from its data block."""
    assert bot_registry.trigger_comment('coderabbit') == '@coderabbitai review'
    assert bot_registry.trigger_comment('gemini') == '/gemini review'
    assert bot_registry.trigger_comment('sourcery') == '@sourcery-ai review'


def test_honors_skip_label_per_bot():
    """CodeRabbit honors the central skip label; Sourcery and Gemini do not."""
    assert bot_registry.honors_skip_label('coderabbit') is True
    assert bot_registry.honors_skip_label('sourcery') is False
    assert bot_registry.honors_skip_label('gemini') is False


def test_ignore_patterns_are_nonempty_literal_markers():
    """Each bot exposes at least one literal whole-comment ignore marker."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert '## Walkthrough' in coderabbit
    assert 'No actionable comments were generated' in coderabbit

    sourcery = bot_registry.ignore_patterns('sourcery')
    assert 'found 0 issues' in sourcery

    gemini = bot_registry.ignore_patterns('gemini')
    assert 'being sunset' in gemini


def test_ignore_patterns_preserve_quoted_special_characters():
    """A quoted marker carrying ``:`` and HTML-comment syntax survives verbatim."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert '<!-- This is an auto-generated comment: summarize by coderabbit.ai -->' in coderabbit


def test_severity_map_per_bot():
    """Each bot's marker->severity map is parsed as a nested mapping."""
    coderabbit = bot_registry.severity_map('coderabbit')
    assert coderabbit['nitpick'] == 'low'
    assert coderabbit['potential_issue_critical'] == 'critical'

    sourcery = bot_registry.severity_map('sourcery')
    assert sourcery['security'] == 'critical'

    gemini = bot_registry.severity_map('gemini')
    assert gemini['low'] == 'low'


def test_module_functions_match_registry_singleton():
    """The module-level functions delegate to the ``REGISTRY`` singleton."""
    assert bot_registry.bot_kinds() == bot_registry.REGISTRY.bot_kinds()
    assert bot_registry.login_to_bot_kind() == bot_registry.REGISTRY.login_to_bot_kind()
    for bot_kind in bot_registry.bot_kinds():
        assert bot_registry.trigger_comment(bot_kind) == bot_registry.REGISTRY.trigger_comment(bot_kind)
        assert bot_registry.ignore_patterns(bot_kind) == bot_registry.REGISTRY.ignore_patterns(bot_kind)


# =============================================================================
# 2. Derived BOT_KINDS (proves _findings_core.BOT_KINDS is data-derived)
# =============================================================================


def test_findings_core_bot_kinds_is_derived_from_registry():
    """``_findings_core.BOT_KINDS`` equals ``bot_registry.bot_kinds()`` — not a literal."""
    from _findings_core import BOT_KINDS

    assert list(BOT_KINDS) == bot_registry.bot_kinds()


def test_findings_core_bot_kinds_contains_every_shipped_bot():
    """The derived enum still contains each shipped bot (coderabbit/gemini/sourcery)."""
    from _findings_core import BOT_KINDS

    for bot_kind in _SHIPPED_BOTS:
        assert bot_kind in BOT_KINDS


# =============================================================================
# 3. Constrained-YAML reader units (synthetic blocks)
# =============================================================================


def test_strip_inline_comment_outside_quotes():
    """A ``#`` preceded by whitespace outside quotes starts a comment and is dropped."""
    assert bot_registry._strip_inline_comment('true          # central config').rstrip() == 'true'


def test_strip_inline_comment_preserves_hash_inside_quotes():
    """A ``#`` inside a quoted span is NOT treated as a comment start."""
    text = '"a #hashtag value"  # real comment'
    assert bot_registry._strip_inline_comment(text).rstrip() == '"a #hashtag value"'


def test_scalar_unquotes_and_coerces_bool():
    """``_scalar`` unquotes strings and coerces ``true``/``false`` to bool."""
    assert bot_registry._scalar(' "@coderabbitai review"  # trigger') == '@coderabbitai review'
    assert bot_registry._scalar(' true  # flag') is True
    assert bot_registry._scalar(' false') is False
    assert bot_registry._scalar(' coderabbit') == 'coderabbit'


def test_extract_registry_block_selects_the_bot_kind_block():
    """The extractor returns the first ``yaml`` fence declaring ``bot_kind:``."""
    md = (
        '# Doc\n'
        '```bash\n'
        'echo not-this\n'
        '```\n'
        'prose\n'
        '```yaml\n'
        'bot_kind: example\n'
        'author_login: example-bot\n'
        '```\n'
    )
    block = bot_registry._extract_registry_block(md)
    assert block is not None
    assert 'bot_kind: example' in block
    assert 'echo not-this' not in block


def test_extract_registry_block_ignores_yaml_without_bot_kind():
    """A ``yaml`` fence with no ``bot_kind:`` line is not treated as a registry block."""
    md = '```yaml\nsome_key: value\n```\n'
    assert bot_registry._extract_registry_block(md) is None


def test_parse_block_scalars_list_and_map():
    """``_parse_block`` reads top-level scalars, a list, and a nested map."""
    block = (
        'bot_kind: demo\n'
        'author_login: demo-bot\n'
        'trigger_comment: "@demo review"\n'
        'honors_skip_label: true\n'
        'ignore_patterns:\n'
        '  - "## Heading"\n'
        '  - "no-op line"   # a comment\n'
        'severity_map:\n'
        '  issue: high\n'
        '  nitpick: low\n'
    )
    data = bot_registry._parse_block(block)
    assert data['bot_kind'] == 'demo'
    assert data['author_login'] == 'demo-bot'
    assert data['trigger_comment'] == '@demo review'
    assert data['honors_skip_label'] is True
    assert data['ignore_patterns'] == ['## Heading', 'no-op line']
    assert data['severity_map'] == {'issue': 'high', 'nitpick': 'low'}


def test_registry_loads_from_synthetic_standards_dir(tmp_path):
    """A synthetic standards dir with one data block loads as one bot."""
    (tmp_path / 'demo.md').write_text(
        '# Demo\n'
        '```yaml\n'
        'bot_kind: demo\n'
        'author_login: demo-bot\n'
        'trigger_comment: "@demo review"\n'
        'honors_skip_label: false\n'
        'ignore_patterns:\n'
        '  - "drop me"\n'
        'severity_map:\n'
        '  issue: medium\n'
        '```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert reg.bot_kinds() == ['demo']
    assert reg.login_to_bot_kind() == {'demo-bot': 'demo'}
    assert reg.trigger_comment('demo') == '@demo review'
    assert reg.honors_skip_label('demo') is False
    assert reg.ignore_patterns('demo') == ['drop me']
    assert reg.severity_map('demo') == {'issue': 'medium'}


def test_registry_skips_docs_without_a_registry_block(tmp_path):
    """A standards doc with no bot_kind data block contributes no bot."""
    (tmp_path / 'prose-only.md').write_text('# Just prose\n\nNo data block here.\n', encoding='utf-8')
    (tmp_path / 'real.md').write_text(
        '```yaml\nbot_kind: real\nauthor_login: real-bot\n```\n', encoding='utf-8'
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert reg.bot_kinds() == ['real']


# =============================================================================
# 4. Robustness — missing dir and unknown keys never raise
# =============================================================================


def test_missing_standards_dir_yields_empty_registry(tmp_path):
    """A non-existent standards directory yields an empty registry, not an error."""
    reg = bot_registry.BotRegistry(standards_dir=tmp_path / 'does-not-exist')
    assert reg.bot_kinds() == []
    assert reg.login_to_bot_kind() == {}


def test_unknown_bot_kind_returns_empty_defaults():
    """Accessors return empty defaults (not raise) for an unregistered bot_kind."""
    assert bot_registry.trigger_comment('nope') == ''
    assert bot_registry.honors_skip_label('nope') is False
    assert bot_registry.ignore_patterns('nope') == []
    assert bot_registry.severity_map('nope') == {}
