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




def test_participation_evidence_marker_gates_only_coderabbits_issue_comment():
    """CodeRabbit gates its ``issue_comment`` shape on the review-verdict wrapper; nothing else is gated.

    CodeRabbit publishes two artifacts in the ``issue_comment`` shape — the
    walkthrough posted before any review completes, and the review verdict wrapped
    in ``<!-- recent_review_start -->`` — so that one shape carries the marker. Its
    other two shapes declare none and credit on the shape alone.

    Sourcery declares no ``issue_comment`` shape, so it has nothing to gate. PR-Agent
    is DELIBERATELY left undeclared: its Guide ``issue_comment`` is its only
    unconditional evidence shape, and a gate there is a change the contract records as
    not taken.

    The title's claim is a CLOSURE claim — only CodeRabbit, and only that one shape —
    so BOTH axes are population-derived. The bots come from ``bot_kinds()``, because a
    hand-written pair keeps the claim passing while a newly registered bot declares a
    marker outside it. The shapes come from the registry's own declared evidence
    vocabulary, because a fixed ``('issue_comment', 'review_body', 'inline')`` tuple
    lets a marker on any OTHER publish shape pass unseen — the sweep can only ask
    about names it already knows.

    The whole declared MAP is asserted per bot, which is what catches a marker on a
    shape nobody thought to ask about; the per-shape accessor assertions stay
    alongside it, because the map states what is DECLARED and the accessor states the
    fail-open ``''`` an undeclared shape reads as. Those are not interchangeable
    claims.
    """
    shapes = sorted({shape for bot in bot_registry.bot_kinds() for shape in bot_registry.participation_evidence(bot)})
    assert shapes, 'no registered bot declares an evidence shape — the sweep below would be vacuous'

    assert bot_registry.participation_evidence_markers('coderabbit') == {
        'issue_comment': '<!-- recent_review_start -->'
    }
    assert bot_registry.participation_evidence_marker('coderabbit', 'issue_comment') == ('<!-- recent_review_start -->')
    assert bot_registry.participation_evidence_marker('coderabbit', 'review_body') == ''
    assert bot_registry.participation_evidence_marker('coderabbit', 'inline') == ''

    others = [bot for bot in bot_registry.bot_kinds() if bot != 'coderabbit']
    assert others, 'no non-CodeRabbit bot is registered — the sweep below would be vacuous'
    for bot_kind in others:
        assert bot_registry.participation_evidence_markers(bot_kind) == {}, bot_kind
        for shape in shapes:
            assert bot_registry.participation_evidence_marker(bot_kind, shape) == '', (bot_kind, shape)


def test_participation_evidence_marker_is_declared_only_on_a_declared_evidence_shape():
    """A marker can only NARROW a shape the bot already declares — it never admits a new one.

    BOTH axes are population-derived: the bots from ``bot_kinds()``, and the shapes
    from each bot's OWN declared key set via ``participation_evidence_markers`` —
    never from a shape vocabulary written here. That is what closes the gap this
    test's title warns about. A vocabulary-driven sweep can only ask about names it
    already knows, so a marker keyed on a typo'd or invented shape read ``''`` for
    every name it asked about (FAIL-OPEN, the intended gate silently never running)
    and was unreachable by the sweep entirely. Reading the declared keys makes that
    key the first thing the sweep sees.

    The sweep is no longer the only line of defence either:
    ``bot_registry._validate_participation_evidence_markers`` now rejects such a key
    at LOAD time, which is pinned separately below. Both are kept — the loader fails
    a bad edit loudly for any doc, and this states what the shipped records declare.

    Non-vacuity: at least one shipped bot must declare a marker, or the sweep proves
    nothing.
    """
    declared = 0
    for bot_kind in bot_registry.bot_kinds():
        for shape, marker in bot_registry.participation_evidence_markers(bot_kind).items():
            assert shape in bot_registry.participation_evidence(bot_kind), (bot_kind, shape)
            if marker:
                declared += 1
    assert declared > 0, 'no shipped bot declares an evidence marker — the sweep above is vacuous'


def test_participation_evidence_markers_exposes_the_declared_key_set(tmp_path):
    """The plural accessor's whole point: the KEY set, enumerable without naming it first.

    The singular accessor can only be asked about a shape the caller already names, so
    a sweep built on it never sees a key nobody thought to ask for — which is exactly
    the key a typo produces. The KEY set therefore survives verbatim, and the VALUES
    are routed through ``participation_evidence_marker`` so the two accessors cannot
    disagree about what a shape is gated on.

    A DECLARED-but-blank entry is no longer part of that story: the loader refuses one
    (pinned below), so every value the map carries is a literal the producer would
    really compare against. What the map distinguishes is a shape with a key from one
    without — ``review_body`` here is a DECLARED evidence shape that simply carries no
    marker, and the singular accessor reads ``''`` for it exactly as for the undeclared
    ``inline``.
    """
    (tmp_path / 'demo.md').write_text(
        '```yaml\n'
        'bot_kind: demo\n'
        'author_login: demo-bot\n'
        'participation_evidence:\n'
        '  - issue_comment\n'
        '  - review_body\n'
        'participation_evidence_markers:\n'
        '  issue_comment: "  <!-- demo_verdict -->  "\n'
        '```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    markers = reg.participation_evidence_markers('demo')

    assert markers == {'issue_comment': '<!-- demo_verdict -->'}
    # Every value agrees with the singular accessor, shape for shape.
    for shape, marker in markers.items():
        assert marker == reg.participation_evidence_marker('demo', shape)
    # Neither ungated shape has a key — the declared one no more than the absent one.
    assert 'review_body' not in markers
    assert 'inline' not in markers
    assert reg.participation_evidence_marker('demo', 'review_body') == ''
    assert reg.participation_evidence_marker('demo', 'inline') == ''
    # A bot with no map at all, and an unregistered kind, both read as no declaration.
    assert reg.participation_evidence_markers('not-registered') == {}


def test_a_marker_keyed_on_an_undeclared_shape_is_rejected_at_load(tmp_path):
    """⛔ The typo case fails LOUD at load, instead of silently disabling the gate.

    ``issue_comments`` for ``issue_comment`` is one character, and the accessor's
    fail-open default turns it into no gate at all: the shape keeps crediting on
    shape alone while the doc reads as though it were gated. For CodeRabbit that is
    live — its pre-review walkthrough publishes in the very shape the marker gates,
    so an ungated ``issue_comment`` credits participation off a comment posted before
    any review completed.

    Paired with its matched positive control — the SAME record with the key spelled
    correctly — because without it this would also pass on a loader that had simply
    started rejecting every record carrying the field.
    """
    doc = tmp_path / 'typo.md'
    header = '```yaml\nbot_kind: typo\nauthor_login: typo-bot\nparticipation_evidence:\n  - issue_comment\n'
    doc.write_text(
        f'{header}participation_evidence_markers:\n  issue_comments: "<!-- verdict -->"\n```\n',
        encoding='utf-8',
    )

    with pytest.raises(bot_registry.BotRegistryError, match='issue_comments'):
        bot_registry.BotRegistry(standards_dir=tmp_path)

    doc.write_text(
        f'{header}participation_evidence_markers:\n  issue_comment: "<!-- verdict -->"\n```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.participation_evidence_marker('typo', 'issue_comment') == '<!-- verdict -->'


def test_a_marker_on_a_record_declaring_no_evidence_shape_is_rejected_at_load(tmp_path):
    """A marker NARROWS a declared shape; with none declared there is nothing to narrow.

    The empty-``participation_evidence`` boundary of the same rule. It is the one an
    author reaches by adding the gate map and forgetting the shape list, and admitting
    it would leave a record whose every marker is inert.
    """
    (tmp_path / 'noshapes.md').write_text(
        '```yaml\n'
        'bot_kind: noshapes\n'
        'author_login: noshapes-bot\n'
        'participation_evidence_markers:\n'
        '  issue_comment: "<!-- verdict -->"\n'
        '```\n',
        encoding='utf-8',
    )

    with pytest.raises(bot_registry.BotRegistryError, match='participation_evidence'):
        bot_registry.BotRegistry(standards_dir=tmp_path)


def test_a_non_map_participation_evidence_markers_declaration_is_rejected_at_load(tmp_path):
    """⛔ ``participation_evidence_markers: true`` names no shape, so it fails LOUD.

    The reader coerces the scalar through ``_scalar`` to a bool, which is neither a
    map to validate nor the absence of a declaration. Admitting it would leave every
    shape crediting on shape alone while the doc reads as though one were gated — the
    same silent ungating a mis-keyed marker produces, reached by a different typo.

    The two genuinely-absent shapes are the matched negative controls, and both must
    still load: the field missing entirely, and the block key that opened and gathered
    no children (which ``_parse_block`` normalises to ``[]``). Without them this would
    also pass on a loader that had simply started rejecting every record touching the
    field.
    """
    header = '```yaml\nbot_kind: scalar\nauthor_login: scalar-bot\nparticipation_evidence:\n  - issue_comment\n'
    doc = tmp_path / 'scalar.md'
    doc.write_text(f'{header}participation_evidence_markers: true\n```\n', encoding='utf-8')

    with pytest.raises(bot_registry.BotRegistryError, match='must be a map'):
        bot_registry.BotRegistry(standards_dir=tmp_path)

    doc.write_text(f'{header}```\n', encoding='utf-8')
    absent = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert absent.participation_evidence_marker('scalar', 'issue_comment') == ''

    doc.write_text(f'{header}participation_evidence_markers:\n```\n', encoding='utf-8')
    childless = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert childless.participation_evidence_marker('scalar', 'issue_comment') == ''


def test_a_blank_or_non_string_marker_value_is_rejected_at_load(tmp_path):
    """⛔ A declared key with no usable literal fails LOUD instead of silently ungating.

    ``issue_comment: "   "`` and ``review_body: true`` both clear KEY validation — the
    shapes ARE declared — and then normalise to ``''`` at the accessor, which the
    producer reads as UNGATED. The author wrote a gate and the shape credits on shape
    alone. For CodeRabbit that is live: its pre-review walkthrough publishes in the
    very shape the marker gates.

    EVERY offending key is named, so one load reports the whole edit rather than only
    the first mistake in it. Paired with its matched positive control — the same
    record with a real literal — because without it this would also pass on a loader
    that had started rejecting every record carrying the field.
    """
    header = (
        '```yaml\nbot_kind: blankval\nauthor_login: blankval-bot\n'
        'participation_evidence:\n  - issue_comment\n  - review_body\n'
    )
    doc = tmp_path / 'blankval.md'
    doc.write_text(
        f'{header}participation_evidence_markers:\n  issue_comment: "   "\n  review_body: true\n```\n',
        encoding='utf-8',
    )

    with pytest.raises(bot_registry.BotRegistryError, match=r"\['issue_comment', 'review_body'\]"):
        bot_registry.BotRegistry(standards_dir=tmp_path)

    doc.write_text(
        f'{header}participation_evidence_markers:\n  issue_comment: "<!-- verdict -->"\n```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.participation_evidence_markers('blankval') == {'issue_comment': '<!-- verdict -->'}


def test_participation_evidence_marker_is_fail_open_on_every_undeclared_shape(tmp_path):
    """No map, a childless block, a map naming another shape, or an unknown kind all read ``''``.

    ``''`` is the FAIL-OPEN value — the producer reads it as "no gate on this shape",
    so the shape credits exactly as it did before the field existed. Failing closed
    instead would turn every undeclared shape into non-evidence and regress a bot
    whose unconditional evidence shape carries no marker to ``absent``.

    ⛔ Fail-open governs the UNDECLARED shape, never a declared one. A blank or
    non-string VALUE, and a key outside ``participation_evidence``, are refused at
    load and can never reach this accessor — pinned by the rejection tests above. The
    rules are complements, not a contradiction: a shape the doc never mentioned reads
    as ungated, and a shape the doc declares badly stops the load.
    """
    (tmp_path / 'nomap.md').write_text(
        '```yaml\nbot_kind: nomap\nauthor_login: nomap-bot\nparticipation_evidence:\n  - issue_comment\n```\n',
        encoding='utf-8',
    )
    (tmp_path / 'emptymap.md').write_text(
        '```yaml\nbot_kind: emptymap\nauthor_login: emptymap-bot\nparticipation_evidence_markers:\n```\n',
        encoding='utf-8',
    )
    (tmp_path / 'other.md').write_text(
        '```yaml\n'
        'bot_kind: other\n'
        'author_login: other-bot\n'
        'participation_evidence:\n'
        '  - issue_comment\n'
        '  - review_body\n'
        'participation_evidence_markers:\n'
        '  issue_comment: "<!-- verdict -->"\n'
        '```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.participation_evidence_marker('nomap', 'issue_comment') == ''
    assert reg.participation_evidence_marker('emptymap', 'issue_comment') == ''
    # A declared map that names only another shape leaves this DECLARED evidence shape
    # ungated, and the undeclared one with it.
    assert reg.participation_evidence_marker('other', 'review_body') == ''
    assert reg.participation_evidence_marker('other', 'inline') == ''
    # The matched positive control: the shape it DOES name keeps its literal.
    assert reg.participation_evidence_marker('other', 'issue_comment') == '<!-- verdict -->'
    assert reg.participation_evidence_marker('not-registered', 'issue_comment') == ''


def test_participation_evidence_marker_is_whitespace_stripped(tmp_path):
    """A declared literal is normalised, so a stray space cannot gate on a string no body carries."""
    (tmp_path / 'demo.md').write_text(
        '```yaml\n'
        'bot_kind: demo\n'
        'author_login: demo-bot\n'
        'participation_evidence:\n'
        '  - issue_comment\n'
        'participation_evidence_markers:   # the gate map\n'
        '  issue_comment: "  <!-- demo_verdict -->  "   # a quoted HTML comment survives the comment strip\n'
        '```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.participation_evidence_marker('demo', 'issue_comment') == '<!-- demo_verdict -->'
