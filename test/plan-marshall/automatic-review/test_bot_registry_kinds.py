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




def test_bot_kinds_equals_shipped_set_sorted():
    """``bot_kinds()`` returns the shipped bot set in deterministic sorted order."""
    assert bot_registry.bot_kinds() == sorted(_SHIPPED_BOTS)


def test_bot_kinds_is_deterministically_sorted():
    """Repeated calls return the same sorted list (load order is stable)."""
    first = bot_registry.bot_kinds()
    second = bot_registry.bot_kinds()
    assert first == second == sorted(first)


def test_login_to_bot_kind_maps_every_shipped_author():
    """Each shipped bot's ``author_login`` resolves to its ``bot_kind``.

    The ``cuioss-review-bot`` entry maps a key to an IDENTICAL value, and that is
    the deliberate contract rather than a copy-paste slip: this reviewer's config
    token and its GitHub author login are ONE name, so the map sends it to itself.
    Collapsing the two was the point of the rename — a config naming the bot by a
    token its reviews are not authored under reads as a bot that never reviewed.
    The dedicated assertion below states the identity explicitly so a future reader
    cannot "fix" it back into a spurious second name.
    """
    mapping = bot_registry.login_to_bot_kind()
    assert mapping == {
        'coderabbitai': 'coderabbit',
        'cuioss-review-bot': 'cuioss-review-bot',
        'sourcery-ai': 'sourcery',
    }


def test_cuioss_review_bot_login_and_kind_are_the_same_name():
    """The login and the bot_kind are deliberately the same string — pinned here.

    The regression guard for the rename: any future edit that reintroduces a
    distinct ``bot_kind`` for this reviewer (so that its config token and its
    review-author login diverge again) turns this red. Derived from the registry
    on both sides rather than restating the literal twice, so the assertion is
    about the IDENTITY holding, not about one hard-coded spelling.
    """
    mapping = bot_registry.login_to_bot_kind()

    assert 'cuioss-review-bot' in mapping, (
        'the cuioss-review-bot record is absent from the registry — the identity assertion below would be vacuous'
    )
    assert mapping['cuioss-review-bot'] == 'cuioss-review-bot'
    # ...and the round trip holds through the normalising lookup real callers use,
    # including the ``[bot]``-suffixed form the provider reports on some paths.
    assert bot_registry.bot_kind_for_login('cuioss-review-bot') == 'cuioss-review-bot'
    assert bot_registry.bot_kind_for_login('cuioss-review-bot[bot]') == 'cuioss-review-bot'


def test_trigger_comment_per_bot():
    """Each bot's re-review trigger comment is read from its data block."""
    assert bot_registry.trigger_comment('coderabbit') == '@coderabbitai review'
    assert bot_registry.trigger_comment('sourcery') == '@sourcery-ai review'
    assert bot_registry.trigger_comment('cuioss-review-bot') == '/review'


def test_completion_check_name_per_bot():
    """CodeRabbit publishes an in-progress completion check-run; the others do not."""
    assert bot_registry.completion_check_name('coderabbit') == 'CodeRabbit'
    assert bot_registry.completion_check_name('sourcery') == ''
    assert bot_registry.completion_check_name('cuioss-review-bot') == ''


def test_honors_skip_label_per_bot():
    """CodeRabbit and PR-Agent honor the central skip label; Sourcery does not.

    The two ``True`` cases are honored by DIFFERENT mechanisms — CodeRabbit from its own
    central config, PR-Agent from the reusable workflow's ``if:`` guard, because its
    ``ignore_pr_labels`` setting is webhook-server-only and inert in GitHub Action mode.
    The registry records the observable behaviour, not the mechanism.
    """
    assert bot_registry.honors_skip_label('coderabbit') is True
    assert bot_registry.honors_skip_label('cuioss-review-bot') is True
    assert bot_registry.honors_skip_label('sourcery') is False
