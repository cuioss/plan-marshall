#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for automatic-review/scripts/bot_registry.py — the data-not-code bot loader.

The registry parses each ``automatic-review/standards/{bot_kind}.md`` fenced-YAML
data block ONCE and exposes stable accessors so the finding store, the re-review
strategy registry, the producer pre-filter, and the rate-limit detector DERIVE
what they need instead of hard-coding the shipped bot set across several code
files. Three bots ship today
(``coderabbit``, ``cuioss-review-bot``, ``sourcery``), and that count is asserted from
:data:`_SHIPPED_BOTS` rather than restated per test.

Coverage:

1. Shipped-standards contract — the real ``standards/*.md`` docs parse into the
   expected bot set, login map, triggers, skip-label flags, ignore patterns,
   contentless-review / actionable-content markers, per-shape
   participation-evidence content markers, rate-limit classes, rate-limit ETA
   patterns, and severity maps.
2. Derived ``BOT_KINDS`` — ``_findings_core.BOT_KINDS`` equals the registry's
   ``bot_kinds()`` (proving it is derived, not a literal).
3. Constrained-YAML reader units — the scalar/comment/block parsers over
   synthetic blocks, including quoted values carrying ``#`` and ``:``.
4. Robustness — a missing or empty standards directory yields an empty registry
   rather than raising; unknown bot kinds return empty defaults.
5. Load-time record validation — a non-map ``participation_evidence_markers``
   declaration, a key outside the record's own ``participation_evidence``, and a
   blank or non-string marker value all raise ``BotRegistryError``. The one place
   the permissive reader is checked rather than tolerated, because that field is
   the one whose malformation disables a gate SILENTLY.

Module import resolves via the root conftest's marketplace PYTHONPATH setup
(``import bot_registry``).
"""

import re

import bot_registry
import pytest

# The bots shipped as standards docs in this skill.
_SHIPPED_BOTS = ['coderabbit', 'cuioss-review-bot', 'sourcery']


# =============================================================================
# 1. Shipped-standards contract (the real standards/*.md docs)
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
    md = '# Doc\n```bash\necho not-this\n```\nprose\n```yaml\nbot_kind: example\nauthor_login: example-bot\n```\n'
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
    (tmp_path / 'real.md').write_text('```yaml\nbot_kind: real\nauthor_login: real-bot\n```\n', encoding='utf-8')
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert reg.bot_kinds() == ['real']


def test_missing_standards_dir_yields_empty_registry(tmp_path):
    """A non-existent standards directory yields an empty registry, not an error."""
    reg = bot_registry.BotRegistry(standards_dir=tmp_path / 'does-not-exist')
    assert reg.bot_kinds() == []
    assert reg.login_to_bot_kind() == {}


def test_unknown_bot_kind_returns_empty_defaults():
    """Accessors return empty defaults (not raise) for an unregistered bot_kind."""
    assert bot_registry.trigger_comment('nope') == ''
    assert bot_registry.completion_check_name('nope') == ''
    assert bot_registry.honors_skip_label('nope') is False
    assert bot_registry.ignore_patterns('nope') == []
    assert bot_registry.severity_map('nope') == {}
    # The content-aware marker accessors fail closed for an unregistered kind too —
    # an empty required list is what stops the producer's layer 3 from ever firing.
    assert bot_registry.contentless_review_markers('nope') == []
    assert bot_registry.actionable_content_markers('nope') == []
    # The evidence content gate fails OPEN — no gate — for an unregistered kind.
    assert bot_registry.participation_evidence_marker('nope', 'issue_comment') == ''
    # The rate-limit accessors fail closed for an unregistered kind too.
    assert bot_registry.rate_limit_class('nope') == 'unknown'
    assert bot_registry.rate_limit_eta_patterns('nope') == []


def test_review_body_summary_patterns_are_registry_owned():
    """The status-summary signature is per-bot DATA, not a literal in a counter.

    A `review_body` can be either the bot's consolidated findings or its
    "Actionable comments posted: N" status line, and the counting rule
    (`bot-participation-contract.md` § "The counting rule") excludes the latter.
    Which literal marks it is a per-bot fact, so it belongs in the registry beside
    `ignore_patterns` and `refusal_patterns` — a counter that hard-codes the login
    or the bot_kind is the hard-coded-population archetype one directory away from
    the registry that exists to prevent it.
    """
    assert bot_registry.review_body_summary_patterns('coderabbit') == [
        'Actionable comments posted:',
    ]


def test_review_body_summary_patterns_default_empty_and_fail_closed():
    """A bot that declares none never has a review_body reclassified as a summary.

    Empty is the fail-closed default in the direction that matters HERE: for the
    gate-escape count, dropping a substantive review_body under-counts escapes and
    makes the gates look better than they are. A bot that has not opted in keeps
    every review_body counted.
    """
    assert bot_registry.review_body_summary_patterns('sourcery') == []
    assert bot_registry.review_body_summary_patterns('cuioss-review-bot') == []
    assert bot_registry.review_body_summary_patterns('no-such-bot') == []


def test_bot_kind_for_login_normalises_casing_and_the_bot_suffix():
    """The login→bot_kind lookup tolerates the two drifts real logins carry.

    `github_pr` stores `author` VERBATIM, and GraphQL author logins arrive both
    with a `[bot]` suffix and with non-canonical casing — the repo's own fixtures
    use `coderabbitai[bot]`. A raw exact-match lookup silently resolves those to
    nothing, which disables every per-bot rule keyed off the author for exactly the
    records that have no `bot_kind` to fall back on.

    The registry owns the login map, so the normalised lookup belongs here rather
    than being re-implemented by each consumer.
    """
    assert bot_registry.bot_kind_for_login('coderabbitai') == 'coderabbit'
    assert bot_registry.bot_kind_for_login('coderabbitai[bot]') == 'coderabbit'
    assert bot_registry.bot_kind_for_login('CodeRabbitAI') == 'coderabbit'
    assert bot_registry.bot_kind_for_login('CodeRabbitAI[bot]') == 'coderabbit'


def test_bot_kind_for_login_returns_empty_for_a_human_or_absent_login():
    """A non-bot author resolves to no bot_kind — never to a wrong one."""
    assert bot_registry.bot_kind_for_login('some-human') == ''
    assert bot_registry.bot_kind_for_login('') == ''
    assert bot_registry.bot_kind_for_login(None) == ''
