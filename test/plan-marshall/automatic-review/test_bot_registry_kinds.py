#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for automatic-review/scripts/bot_registry.py — the data-not-code bot loader.

The registry parses each ``automatic-review/standards/{bot_kind}.md`` fenced-YAML
data block ONCE and exposes stable accessors so the finding store, the re-review
strategy registry, the producer pre-filter, and the rate-limit detector DERIVE
what they need instead of hard-coding the shipped bot set across several code
files. Two bots ship today
(``coderabbit``, ``sourcery``), and that count is asserted from
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
_SHIPPED_BOTS = ['coderabbit', 'sourcery']


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
        'sourcery-ai': 'sourcery',
    }


def test_trigger_comment_per_bot():
    """Each bot's re-review trigger comment is read from its data block."""
    assert bot_registry.trigger_comment('coderabbit') == '@coderabbitai review'
    assert bot_registry.trigger_comment('sourcery') == '@sourcery-ai review'


def test_completion_check_name_per_bot():
    """CodeRabbit publishes an in-progress completion check-run; Sourcery does not."""
    assert bot_registry.completion_check_name('coderabbit') == 'CodeRabbit'
    assert bot_registry.completion_check_name('sourcery') == ''


def test_honors_skip_label_per_bot():
    """CodeRabbit honors the central skip label; Sourcery does not."""
    assert bot_registry.honors_skip_label('coderabbit') is True
    assert bot_registry.honors_skip_label('sourcery') is False
