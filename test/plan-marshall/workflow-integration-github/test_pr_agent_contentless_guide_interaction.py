#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end regression tests for PR-Agent's contentless Guide, producer + aggregator.

On a clean PR, PR-Agent posts exactly one persistent ``## PR Reviewer Guide 🔍``
``issue_comment``. Before the fix that comment survived the producer pre-filter and
was filed as a pending hand-triage ``pr-comment`` finding, and the review
retrospective then mapped the ``accepted`` disposition it always closes with into
the ``false_positive`` bucket while dividing ``pct_resolved_as_fixed`` by
``raw_total`` — so a reviewer that behaved correctly scored 100% false-positive /
0.0% resolved-as-fixed.

This module exercises the producer and the aggregator TOGETHER, which is what
makes it distinct from the co-located unit tests: ``test_github_pr.py`` drives
``_is_obvious_noise`` / ``_is_contentless_boilerplate`` in isolation and
``test_review_retrospective.py`` drives ``aggregate()`` in isolation, while the
arms here run ``cmd_fetch_findings``'s genuine ``_findings_core`` round-trip
against a real findings store and feed its outcome into ``aggregate()``.

Seven arms:

1. **Clean-PR arm** — the fully clean Guide is dropped, files no finding, and —
   the load-bearing assertion — PR-Agent is STILL credited as a participant.
2. **Mixed arm** — the same clean assertions plus one ``<details>`` focus-area
   finding is stored IN FULL: there is no partial-body suppression.
3. **Deviating-assertion arm** — a 🔒 row naming a concrete concern is stored; the
   predicate fails open on a CHANGED required marker.
4. **Partial-clean / docs-only arm** — the 🧪 clean assertion absent is stored; the
   predicate fails open on a MISSING required marker. This arm enforces the
   ``all(required)`` conjunction, so weakening the registry list to the 🔒 row
   alone turns it red instead of silently widening the suppression.
5. **Interaction arm** — the clean-PR arm's post-fix outcome fed into
   ``aggregate()``: a suppressed Guide yields no ``reviewers[]`` row at all, and a
   SURVIVING PR-Agent record resolved ``accepted`` scores in neither quality
   bucket with ``pct_resolved_as_fixed is None`` — never ``0.0``.
6. **Update-movement arm** — arm 1's surviving participation must not become
   UNCONDITIONAL. Across two fetches an unchanged Guide is credited on the first
   and NOT on the second, while a Guide edited in place between fetches is
   credited again. Both directions are asserted because the drop removes the
   comment from the findings store, which is where ``_has_update_movement``'s
   first-presence arm used to read its evidence from.
7. **Rendering-invariance arm** — the drop must not depend on which emphasis
   PR-Agent emits. The verbatim observed #1078 body (HTML ``<strong>`` inside a
   ``<table>``) and the same Guide in GitHub's markdown ``**`` rendering are both
   dropped, which is the whole reason the registry markers are BARE INNER TEXT.
   The HTML case is the anti-vacuity pin: it is red against the superseded
   ``**``-wrapped markers, which matched no real body at all.

Every Guide body comes from ``test/_shared/_pr_agent_guide_bodies.py`` rather
than from a literal here — see that module for why a per-suite fixture is what
made this suite vacuous once already.

The findings store is REAL (isolated via the ``plan_context`` ``PLAN_BASE_DIR``
sandbox); only the GitHub provider surface (``check_auth``,
``fetch_pr_comments_data``, ``fetch_pr_head_sha``) is monkeypatched. The
aggregator ships as a project-local script under ``.claude/skills/`` which
``conftest.get_script_path`` cannot reach, so it is imported through the same
``PROJECT_ROOT``-relative ``sys.path`` prologue ``test_review_retrospective.py``
uses.
"""

from __future__ import annotations

import argparse
import sys

import bot_registry
import pytest
from _pr_agent_guide_bodies import (
    CLEAN_FOCUS_ROW,
    CLEAN_SECURITY_ROW,
    CLEAN_TESTS_ROW,
    GUIDE_DEVIATING_ASSERTION,
    GUIDE_DOCS_ONLY,
    GUIDE_WITH_FINDING,
    OBSERVED_CLEAN_GUIDE,
    RENDERED_MARKDOWN_GUIDE,
    guide_body,
)

from conftest import PROJECT_ROOT, load_script_module

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'finalize-step-review-retrospective'
    / 'scripts'
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# A bare ``type: ignore`` is deliberate here, not laziness: mypy resolves this
# project-local import differently depending on which roots are on its search
# path, so it raises ``import-untyped`` in some environments and
# ``import-not-found`` in others (locally vs CI). A code-scoped ignore is
# therefore "unused" in whichever environment raises the OTHER code, and
# ``--warn-unused-ignores`` turns that into a hard error. The bare form is used
# in both.
import review_retrospective as rr  # type: ignore  # noqa: E402

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

query_findings = _findings_core.query_findings

_PR_AGENT_LOGIN = 'cuioss-review-bot'
_PR_AGENT_REQUIRED_MARKERS = bot_registry.contentless_review_markers('pr-agent')


# ---------------------------------------------------------------------------
# Guide bodies
# ---------------------------------------------------------------------------
#
# The four observable shapes (clean / with-finding / deviating-marker /
# missing-marker) and the verbatim observed #1078 body live in
# ``test/_shared/_pr_agent_guide_bodies.py``, shared with the layer-3 predicate
# units in ``test_github_pr.py``. Only the provider-record wrapper is local.


def _guide_comment(body, comment_id='guide-1', *, created_at=None, updated_at=None):
    """A ``cuioss-review-bot`` issue_comment carrying ``body`` — PR-Agent's one shape.

    ``created_at`` / ``updated_at`` are omitted entirely unless supplied, so the
    arms that do not care about edit movement keep the exact provider record they
    had before. The movement arm supplies both: ``updated_at == created_at`` models
    the UNCHANGED Guide, and a later ``updated_at`` models the in-place re-review
    edit that is PR-Agent's only way of publishing a fresh review.
    """
    comment = {
        'id': comment_id,
        'author': _PR_AGENT_LOGIN,
        'thread_id': '',
        'kind': 'issue_comment',
        'body': body,
        'resolved': False,
    }
    if created_at is not None:
        comment['created_at'] = created_at
    if updated_at is not None:
        comment['updated_at'] = updated_at
    return comment


def _patch_provider(monkeypatch, comments):
    """Monkeypatch only the GitHub provider surface — the findings store stays real."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(
        github_pr._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {
            'status': 'success',
            'provider': 'github',
            'comments': list(comments),
            'total': len(comments),
            'unresolved': len(comments),
        },
    )
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: 'deadbeef')


def _run_fetch(pr_number, plan_id):
    args = argparse.Namespace(pr_number=pr_number, plan_id=plan_id)
    return github_pr.cmd_fetch_findings(args)


def _stored(plan_id):
    return query_findings(plan_id, finding_type='pr-comment')['findings']


def _raw_body(finding):
    """Return the quarantined ``raw_input.body`` the producer persisted."""
    raw_input = finding.get('raw_input') or {}
    return raw_input.get('body', '')


def test_guide_renderer_reproduces_the_observed_body_byte_for_byte():
    """The renderer the derived shapes are built from matches the captured evidence.

    Arms 2, 3 and 4 feed RENDERED bodies, so their realism rests entirely on
    ``guide_body``/``guide_row`` emitting PR-Agent's actual markup. Only arm 1
    and arm 7 feed the verbatim capture, and a renderer that drifted from it
    would leave those three arms exercising a shape the bot never emits — which
    is precisely the failure the ``**``-wrapped fixtures already caused once.
    Equality against the byte-exact literal is what forecloses it.
    """
    assert guide_body(CLEAN_TESTS_ROW, CLEAN_SECURITY_ROW, CLEAN_FOCUS_ROW) == OBSERVED_CLEAN_GUIDE


def test_guide_fixtures_track_the_declared_marker_set():
    """The four Guide shapes stay in step with the registry they exercise.

    Each arm below is meaningful only relative to the DECLARED required-marker
    set: arm 1 needs every marker present, arm 4 needs exactly one absent. Were a
    marker added to ``pr-agent.md`` without the fixtures moving, arm 1 would stop
    exercising the drop while still passing for the wrong reason.
    """
    assert _PR_AGENT_REQUIRED_MARKERS
    for marker in _PR_AGENT_REQUIRED_MARKERS:
        assert marker in OBSERVED_CLEAN_GUIDE
        assert marker in GUIDE_WITH_FINDING
    assert '<details>' in GUIDE_WITH_FINDING
    assert '<details>' not in OBSERVED_CLEAN_GUIDE
    # Arms 3 and 4 each break the conjunction in a DIFFERENT way — one marker
    # changed, one marker removed — so exactly one required marker is absent from
    # each and neither carries a disqualifying marker.
    for deviating in (GUIDE_DEVIATING_ASSERTION, GUIDE_DOCS_ONLY):
        absent = [m for m in _PR_AGENT_REQUIRED_MARKERS if m not in deviating]
        assert len(absent) == 1
        assert '<details>' not in deviating


# ---------------------------------------------------------------------------
# Arm 1 — the clean Guide is dropped, participation survives
# ---------------------------------------------------------------------------


def test_clean_guide_is_dropped_but_still_credits_participation(plan_context, monkeypatch):
    """A fully clean Guide files no finding, yet PR-Agent is still a proven participant.

    The drop is the point of the fix; the surviving participation is what keeps it
    safe. ``participated_bots`` is derived from the raw comment list BEFORE the
    pre-filter runs, so suppressing the bot's only comment removes its findings
    without removing its evidence — the bot resolves to the already-defined
    ``participated_but_empty`` taxonomy member rather than to ``absent``. A drop
    that also erased participation would turn a clean review into a completeness
    failure and hold the finalize step open forever.
    """
    plan_id = 'pr-agent-clean-guide-dropped'
    _patch_provider(monkeypatch, [_guide_comment(OBSERVED_CLEAN_GUIDE)])

    result = _run_fetch(1201, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    # Counted as noise, NOT as a refusal and NOT as a self-response: a clean
    # review is routine successful-review boilerplate, the class ignore_patterns
    # already serves.
    assert result['count_skipped_noise'] == 1
    assert result['count_skipped_refusal'] == 0
    assert result['count_skipped_self_response'] == 0
    # A legitimate non-store — expected_stored accounts for it, so no
    # (producer-mismatch) Q-Gate false-positive.
    assert result['producer_mismatch_hash_id'] is None
    # The load-bearing assertion: participation is untouched by the drop.
    assert {'bot_kind': 'pr-agent', 'evidence_kind': 'issue_comment'} in result['participated_bots']
    assert result['refused_bots'] == []

    assert _stored(plan_id) == []


# ---------------------------------------------------------------------------
# Arm 2 — a finding-bearing Guide is stored in full
# ---------------------------------------------------------------------------


def test_guide_with_a_finding_is_stored_byte_identical(plan_context, monkeypatch):
    """One ``<details>`` finding vetoes the drop, and the stored body is unmodified.

    The byte-identical assertion closes the partial-suppression risk the rejected
    ``ignore_patterns`` route would have carried: the layer either drops the whole
    comment or leaves it entirely alone. It never edits a body to strip the
    boilerplate rows out of a Guide that also carries real content — an operator
    triaging the finding sees exactly what the reviewer wrote.
    """
    plan_id = 'pr-agent-guide-with-finding-stored'
    _patch_provider(monkeypatch, [_guide_comment(GUIDE_WITH_FINDING)])

    result = _run_fetch(1202, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    # The contentless layer did not fire — the counter did not move.
    assert result['count_skipped_noise'] == 0
    assert result['producer_mismatch_hash_id'] is None

    stored = _stored(plan_id)
    assert len(stored) == 1
    assert _raw_body(stored[0]) == GUIDE_WITH_FINDING


# ---------------------------------------------------------------------------
# Arms 3 and 4 — the conjunction fails open, both ways
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('arm', 'body'),
    [
        ('deviating-assertion', GUIDE_DEVIATING_ASSERTION),
        ('docs-only-partial-clean', GUIDE_DOCS_ONLY),
    ],
    # Explicit ids: without them pytest derives the id from the `body` operand and
    # inlines the whole escaped Guide into every test id. `arm` doubles as the
    # plan_id suffix below, so it is hyphen-cased to satisfy `validate_plan_id`'s
    # ^[a-z][a-z0-9-]*$ — an underscore there is rejected at the findings-store
    # boundary, not at parametrize time.
    ids=['deviating-assertion', 'docs-only-partial-clean'],
)
def test_guide_missing_or_changing_a_required_marker_is_stored(plan_context, monkeypatch, arm, body):
    """A Guide that deviates from the declared clean shape is filed, not dropped.

    Two DIFFERENT halves of the ``all(required)`` conjunction:

    - ``deviating-assertion`` CHANGES a required marker — the 🔒 row names a
      concrete concern instead of asserting a clean result. That is a real
      security finding and dropping it would destroy the highest-value output of
      the three-bot set.
    - ``docs-only-partial-clean`` REMOVES a required marker — the 🧪 clean
      assertion is absent, the shape a docs-only PR produces. Its retention is the
      accepted residual behind operator decision Q1: the drop requires EVERY
      declared marker, and this arm turns red if the registry list is ever
      weakened to the 🔒 row alone.
    """
    plan_id = f'pr-agent-guide-{arm}'
    _patch_provider(monkeypatch, [_guide_comment(body)])

    result = _run_fetch(1203, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    assert result['count_skipped_noise'] == 0
    assert result['producer_mismatch_hash_id'] is None

    stored = _stored(plan_id)
    assert len(stored) == 1
    assert _raw_body(stored[0]) == body


# ---------------------------------------------------------------------------
# Arm 7 — the drop is invariant across the two emphasis renderings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('rendering', 'body'),
    [
        ('html-strong-observed', OBSERVED_CLEAN_GUIDE),
        ('markdown-bold', RENDERED_MARKDOWN_GUIDE),
    ],
    # Explicit ids for the same reason arms 3/4 need them: without them pytest
    # inlines the whole escaped Guide into the test id, and `rendering` doubles
    # as the plan_id suffix, which must satisfy `validate_plan_id`.
    ids=['html-strong-observed', 'markdown-bold'],
)
def test_clean_guide_is_dropped_in_either_emphasis_rendering(plan_context, monkeypatch, rendering, body):
    """The clean Guide is dropped whether its assertions are ``<strong>`` or ``**``.

    This is the ANTI-VACUITY pin, and the reason the registry markers are bare
    inner text rather than a rendering:

    - ``html-strong-observed`` feeds the VERBATIM body PR-Agent posted on #1078.
      Its assertions sit inside an HTML ``<table>``, where GitHub renders no
      markdown, so the raw API body carries ``<strong>PR contains tests</strong>``.
      Against the superseded ``**PR contains tests**`` markers two of the three
      required entries could never match, the conjunction was dead, and the whole
      layer was inert on every real clean Guide — while every fixture-driven test
      stayed green because the fixtures were written in the rendering too. This
      case is red against those markers.
    - ``markdown-bold`` feeds the same Guide as GitHub RENDERS it. That shape has
      never been observed from this bot, so it is not a behavioural claim about
      it — it pins the PROPERTY the bare form was chosen for: the marker is a
      substring of both renderings, so the drop cannot be re-broken by an
      upstream change of emphasis.
    """
    plan_id = f'pr-agent-guide-rendering-{rendering}'
    _patch_provider(monkeypatch, [_guide_comment(body)])

    result = _run_fetch(1207, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['count_skipped_noise'] == 1
    assert result['producer_mismatch_hash_id'] is None
    assert _stored(plan_id) == []


# ---------------------------------------------------------------------------
# Arm 6 — the drop must not make participation UNCONDITIONAL
# ---------------------------------------------------------------------------
#
# Arm 1 pins that the drop preserves participation evidence. That is only half the
# contract: PR-Agent declares ``participation_requires_update: true``, so its
# evidence must ALSO show first presence or ``updated_at`` movement — a stale
# unchanged Guide proves only that it reviewed some EARLIER HEAD.
#
# The drop is exactly what put those two halves in tension. ``_has_update_movement``
# read first presence from the STORED pr-comment findings, and a dropped Guide files
# none — so its key never entered that set, the first-presence arm was satisfied on
# every fetch, and the movement requirement silently stopped binding. Arm 1 is
# single-fetch and so cannot see it. Both directions are asserted below: without the
# second case, "never credit after the first fetch" would satisfy the first one
# while breaking every genuine re-review.

_CREATED_AT = '2026-07-30T09:00:00Z'
_EDITED_AT = '2026-07-30T11:30:00Z'


def test_second_fetch_of_an_unchanged_guide_does_not_re_credit_participation(plan_context, monkeypatch):
    """An unchanged clean Guide credits PR-Agent once, never again on a later fetch.

    The false-positive direction, and the reason ``participation_requires_update``
    exists: after a force-push the same Guide is still sitting on the PR having only
    ever reviewed an earlier HEAD. Crediting it a second time reports a proven
    participant on a diff nothing has reviewed.

    Both fetches see the IDENTICAL provider record — same ``comment_id``, and
    ``updated_at == created_at`` so no edit movement is available either. The only
    thing that differs between them is what the plan has already observed, which is
    precisely the signal the drop removed from the findings store.
    """
    plan_id = 'pr-agent-guide-unchanged-second-fetch'
    guide = _guide_comment(OBSERVED_CLEAN_GUIDE, created_at=_CREATED_AT, updated_at=_CREATED_AT)
    _patch_provider(monkeypatch, [guide])

    first = _run_fetch(1205, plan_id)
    second = _run_fetch(1205, plan_id)

    # The Guide is dropped on BOTH fetches — the drop behaviour is unchanged.
    assert first['count_stored'] == 0
    assert second['count_stored'] == 0
    assert first['count_skipped_noise'] == 1
    assert second['count_skipped_noise'] == 1
    assert _stored(plan_id) == []
    # Neither fetch trips the producer-mismatch Q-Gate.
    assert first['producer_mismatch_hash_id'] is None
    assert second['producer_mismatch_hash_id'] is None

    # First presence — the plan is observing this comment for the first time.
    assert {'bot_kind': 'pr-agent', 'evidence_kind': 'issue_comment'} in first['participated_bots']
    # Second fetch: already observed and unmoved, so there is no new review to credit.
    assert second['participated_bots'] == []


def test_guide_edited_between_fetches_credits_participation_again(plan_context, monkeypatch):
    """An in-place edit between fetches IS movement, so PR-Agent is credited again.

    The false-negative guard for the case above. PR-Agent re-reviews by editing its
    one persistent comment rather than posting a new one, so ``updated_at`` movement
    on an already-observed comment is its ONLY way of publishing a fresh review.
    Were the observed-keys record to close the first-presence arm without leaving
    the movement arm live, every genuine PR-Agent re-review would resolve to
    ``absent`` and hold the completeness gate open forever.

    The edited Guide is still fully clean, so it is still dropped — this asserts the
    movement arm on the drop path specifically, not on the stored-finding path.
    """
    plan_id = 'pr-agent-guide-edited-between-fetches'
    unchanged = _guide_comment(OBSERVED_CLEAN_GUIDE, created_at=_CREATED_AT, updated_at=_CREATED_AT)
    _patch_provider(monkeypatch, [unchanged])
    first = _run_fetch(1206, plan_id)
    assert {'bot_kind': 'pr-agent', 'evidence_kind': 'issue_comment'} in first['participated_bots']

    # Same comment_id — the bot edited the Guide in place rather than posting anew.
    edited = _guide_comment(OBSERVED_CLEAN_GUIDE, created_at=_CREATED_AT, updated_at=_EDITED_AT)
    _patch_provider(monkeypatch, [edited])
    second = _run_fetch(1206, plan_id)

    assert second['count_stored'] == 0
    assert second['count_skipped_noise'] == 1
    assert second['producer_mismatch_hash_id'] is None
    assert {'bot_kind': 'pr-agent', 'evidence_kind': 'issue_comment'} in second['participated_bots']


# ---------------------------------------------------------------------------
# Arm 5 — the interaction: neither a false score nor a vacuous one
# ---------------------------------------------------------------------------


def test_suppressed_guide_produces_no_reviewer_row_at_all(plan_context, monkeypatch):
    """With its only comment dropped, PR-Agent contributes zero records — so no score.

    The first half of the interaction. ``aggregate()`` emits a ``reviewers[]`` row
    only for an author that produced at least one record, so a reviewer whose
    single clean Guide was suppressed cannot be scored at all — there is no row to
    misread. This is fed the REAL post-fetch store rather than a hand-built record
    list, which is what makes it an interaction test.
    """
    plan_id = 'pr-agent-suppressed-guide-no-row'
    _patch_provider(monkeypatch, [_guide_comment(OBSERVED_CLEAN_GUIDE)])

    fetch_result = _run_fetch(1204, plan_id)
    assert fetch_result['count_stored'] == 0

    report = rr.aggregate(_stored(plan_id))

    assert report['total_findings'] == 0
    assert report['reviewer_count'] == 0
    assert report['reviewers'] == []


def test_surviving_guide_record_scores_neither_false_positive_nor_vacuous_zero():
    """The second half: a surviving Guide resolved ``accepted`` is not a wrong claim.

    A Guide that DOES carry content survives the producer and is triaged; the
    disposition it closes with is ``accepted`` — the reviewer said something valid
    that the triage absorbed without a code change. Both defects are pinned at
    once:

    - ``false_positives_count == 0`` — an acknowledgement is not evidence the
      reviewer was wrong; only ``rejected`` is.
    - ``pct_resolved_as_fixed is None`` — the record is META (``issue_comment``),
      so it contributes to neither the numerator nor the denominator. The old
      ``raw_total`` denominator reported a confident ``0.0`` here, which is the
      second half of the reported symptom.

    ``None`` and ``0.0`` are the assertion that matters: they are both falsy, so a
    test written as ``not row['pct_resolved_as_fixed']`` would pass against the
    defect. The identity check is deliberate.
    """
    report = rr.aggregate([
        {
            'author': _PR_AGENT_LOGIN,
            'kind': 'issue_comment',
            'title': 'PR Reviewer Guide',
            'resolution': 'accepted',
        }
    ])

    rows = [row for row in report['reviewers'] if row['author'] == _PR_AGENT_LOGIN]
    assert len(rows) == 1
    row = rows[0]

    assert row['raw_total'] == 1
    assert row['meta_count'] == 1
    assert row['actionable_count'] == 0
    assert row['accepted'] == 1
    assert row['false_positives_count'] == 0
    assert row['positives_count'] == 0
    assert row['resolved_actionable_count'] == 0
    assert row['pct_resolved_as_fixed'] is None
