# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
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
6. **Currency arm** — arm 1's surviving participation must not become UNCONDITIONAL,
   and it must be idempotent. The credit is an SHA comparison against the merge
   candidate (``_reviewed_at_merge_candidate``): re-fetching the unchanged Guide at
   the SAME HEAD keeps the credit (the observer-effect regression the retired
   first-presence arm failed), a force-push that advances HEAD past the reviewed
   commit turns it ``participated_stale``, and a Guide EDITED in place after the
   advance is credited again through the edit arm. A dropped Guide files no finding,
   so the SHA the comparison reads comes from the plan-scoped CURRENCY LEDGER — the
   sole source the currency test consults, which records every credited comment
   whether or not that comment produced a finding. Without the ledger the test would
   be blind on the drop path.
7. **Rendering-invariance arm** — the drop must not depend on which emphasis
   PR-Agent emits. The verbatim observed body (HTML ``<strong>`` inside a
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

_SCRIPTS_DIR = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-review-retrospective' / 'scripts'
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
import review_retrospective as rr  # type: ignore

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')
query_findings = _findings_core.query_findings
_PR_AGENT_LOGIN = 'cuioss-review-bot'
_PR_AGENT_REQUIRED_MARKERS = bot_registry.contentless_review_markers('cuioss-review-bot')


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


def _patch_provider(monkeypatch, comments, head_sha='deadbeef', head_committed_at=''):
    """Monkeypatch only the GitHub provider surface — the findings store stays real.

    ``head_sha`` is the PR HEAD the producer stamps and, since the currency fix,
    compares each comment's recorded SHA against. It defaults to ``deadbeef``; a test
    simulates a loop-back / force-push by re-patching with a DIFFERENT value between
    fetches.

    ``head_committed_at`` is the merge-candidate commit's OWN timestamp, the second
    input to the first-observation arm. It defaults to the empty string — the
    unreadable case, under which the arm keeps its SHA-only behaviour — so the cases
    below stay about the SHA anchor. Patching it is not optional: unpatched, the
    producer's read would shell out to a real ``gh``.
    """
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_committed_at', lambda pr_number: head_committed_at)
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
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: head_sha)


def _run_fetch(pr_number, plan_id):
    """Run the producer's FIND verb against ``plan_id``, with its plan directory present.

    The directory is materialized HERE because ``phase-1-init`` materializes it in
    production before any producer runs, and ``cmd_fetch_findings`` REFUSES a plan
    directory absent from the resolved root — a plan that exists in no checkout is not
    a plan that has filed nothing. The arms below derive their ids per bot and per
    shape, so constructing it in the shared helper keeps that one line of production
    context in one place rather than in every arm.

    ⛔ It does NOT neutralize the refusal. A test whose subject IS the unreached store
    drives ``cmd_fetch_findings`` directly — see the unreached-store section in
    ``test_comments_stage.py``.
    """
    from file_ops import get_base_dir  # local import: resolved per call, after the sandbox fixture

    (get_base_dir() / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)
    args = argparse.Namespace(pr_number=pr_number, plan_id=plan_id)
    return github_pr.cmd_fetch_findings(args)


def _stored(plan_id):
    return query_findings(plan_id, finding_type='pr-comment')['findings']


def _raw_body(finding):
    """Return the quarantined ``raw_input.body`` the producer persisted."""
    raw_input = finding.get('raw_input') or {}
    return raw_input.get('body', '')


_CREATED_AT = '2026-07-30T09:00:00Z'
_EDITED_AT = '2026-07-30T11:30:00Z'
_HEAD_A = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
_HEAD_B = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'


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
    marker added to ``cuioss-review-bot.md`` without the fixtures moving, arm 1 would stop
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


def test_guide_with_a_finding_is_stored_byte_identical(plan_context, monkeypatch):
    """One ``<details>`` finding vetoes the drop, and the stored body is unmodified.

    The byte-identical assertion closes the partial-suppression risk the rejected
    ``ignore_patterns`` route would have carried: the layer either drops the whole
    comment or leaves it entirely alone. It never edits a body to strip the
    boilerplate rows out of a Guide that also carries real content — an operator
    triaging the finding sees exactly what the reviewer wrote.
    """
    plan_id = 'cuioss-review-bot-guide-with-finding-stored'
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
    plan_id = f'cuioss-review-bot-guide-{arm}'
    _patch_provider(monkeypatch, [_guide_comment(body)])

    result = _run_fetch(1203, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    assert result['count_skipped_noise'] == 0
    assert result['producer_mismatch_hash_id'] is None

    stored = _stored(plan_id)
    assert len(stored) == 1
    assert _raw_body(stored[0]) == body
