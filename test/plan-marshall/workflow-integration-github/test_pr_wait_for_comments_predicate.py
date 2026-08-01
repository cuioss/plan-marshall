#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end tests for ``pr wait-for-comments``'s two-arm completion predicate.

Sibling of ``test_pr_wait_for_comments_rate_limited.py``, scoped to the
COMPLETION PREDICATE rather than to the rate-limit discriminator (which keeps its
own file).

The defect these pin: ``cmd_pr_wait_for_comments`` decided "a re-review arrived"
purely from unresolved-comment COUNT growth. A bot that re-reviews by EDITING its
single persistent comment in place produces no count growth, so the await was
structurally blind to it and burned its full timeout even when the bot reviewed
correctly and on time. The predicate now also fires on ``updated_at`` movement for
any bot whose registry record declares ``participation_requires_update: true``.

**Verification contract — why these differ from D1's local unit assertions.**
These drive ``cmd_pr_wait_for_comments`` END TO END with the REAL ``poll_until``:
only ``check_auth`` and ``fetch_pr_comments_data`` are monkeypatched, so the
genuine ``check_fn`` / ``is_complete_fn`` pair runs against a comment sequence that
CHANGES BETWEEN POLLS. ``interval=0`` on the completing arms and a 1-second budget
on the timing-out arms keep the suite deterministic and near-constant-time.

Population-derived, never literal-listed: every arm selects its bots through
``bot_registry.participation_requires_update`` over ``bot_registry.bot_kinds()``
and resolves each login through ``bot_registry.login_to_bot_kind()``. A bot added
or reclassified in a standards doc is therefore covered automatically instead of
escaping the sweep.

Arms:
    1. in-place edit ends the wait with NO count growth (the reproduced defect)
    2. mixed-bot: the count arm still fires, and the two arms do not mask each
       other in either direction
    3. a refusal never satisfies the movement arm, even when its timestamp moved
    4. unanswerable detector: BOTH registry disjuncts, PLUS the discriminating
       answerable-but-silent case
    5. divergent input (naive / unparseable / non-dict) fails CLOSED
"""

import argparse
from datetime import UTC, datetime, timedelta

import bot_registry
import github_ops

# Comfortably outside any plausible test runtime, so the ordering versus the
# handler's own ``wait_start`` (captured as ``datetime.now(UTC)`` at call time) is
# never a race.
_OFFSET = timedelta(hours=1)


def _before_wait() -> str:
    return (datetime.now(UTC) - _OFFSET).isoformat().replace('+00:00', 'Z')


def _after_wait() -> str:
    return (datetime.now(UTC) + _OFFSET).isoformat().replace('+00:00', 'Z')


# A refusal notice recognised STRUCTURALLY (a limit-exceeded statement AND a
# notice shape), so this fixture stays bot-agnostic rather than depending on any
# one bot's registry ``refusal_patterns``.
_REFUSAL_BODY = (
    '> [!WARNING] The review request could not be served: this account has '
    'exceeded the limit for the number of commits or files that can be '
    'reviewed. Please try again later.'
)


def _movement_bots() -> list[str]:
    """Registered bots that re-review by EDITING one persistent comment."""
    return [k for k in bot_registry.bot_kinds() if bot_registry.participation_requires_update(k)]


def _count_bots() -> list[str]:
    """Registered bots that append a NEW comment per review."""
    return [k for k in bot_registry.bot_kinds() if not bot_registry.participation_requires_update(k)]


def _login_for(bot_kind: str) -> str:
    """Resolve ``bot_kind`` back to its registry login."""
    for login, kind in bot_registry.login_to_bot_kind().items():
        if kind == bot_kind:
            return login
    raise AssertionError(f'{bot_kind} declares no author_login in the registry')


def _the_mover() -> str:
    """The bot the movement arm is exercised against, derived from the registry."""
    movers = _movement_bots()
    # Not a courtesy check: with no `participation_requires_update` bot registered
    # the movement arms below would pass vacuously against ANY implementation.
    assert movers, 'no registered bot declares participation_requires_update — movement arms would be vacuous'
    return movers[0]


def _the_appender() -> str:
    """A bot whose reviews append a new comment, so the count arm applies to it."""
    appenders = _count_bots()
    assert appenders, 'no registered bot declares participation_requires_update: false'
    return appenders[0]


def _comment(bot_kind: str, *, created_at: str, updated_at: str, body: str = 'Guide') -> dict:
    return {
        'kind': 'issue_comment',
        'id': f'IC_{bot_kind}',
        'author': _login_for(bot_kind),
        'body': body,
        'path': '',
        'line': 0,
        'resolved': False,
        'created_at': created_at,
        'updated_at': updated_at,
        'thread_id': '',
    }


def _wait_args(*, pr_number=123, timeout=5, interval=0):
    return argparse.Namespace(pr_number=pr_number, timeout=timeout, interval=interval)


def _wire(monkeypatch, sequence: list[dict]) -> None:
    """Patch auth + fetch only — ``poll_until`` stays REAL.

    ``sequence`` supplies successive answers to the ``unresolved_only=True``
    probes: entry 0 is the baseline snapshot, entry 1 the first poll, and so on.
    The final entry repeats for every later poll, so a timing-out arm settles on a
    stable observation. The post-poll full fetch (``unresolved_only=False``) is
    answered from the most recently served entry, which is what the rate-limit
    discriminator inspects.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    state = {'index': 0, 'last': sequence[0]}

    def fake_fetch(pr_number, unresolved_only=False):
        assert pr_number == 123
        if not unresolved_only:
            return {'status': 'success', 'comments': state['last']['comments']}
        entry = sequence[min(state['index'], len(sequence) - 1)]
        state['index'] += 1
        state['last'] = entry
        return {
            'status': 'success',
            'unresolved': entry['unresolved'],
            'comments': entry['comments'],
        }

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)


def test_in_place_edit_ends_the_wait_without_count_growth(monkeypatch):
    # THE defect, reproduced and fixed. The bot's persistent comment is already
    # present at baseline with a pre-wait created_at, and the unresolved count
    # NEVER changes — only updated_at advances past the wait start on a later
    # poll. Pre-fix this arm runs to the full timeout: that is the burned await.
    mover = _the_mover()
    stale = _comment(mover, created_at=_before_wait(), updated_at=_before_wait())
    edited = _comment(mover, created_at=_before_wait(), updated_at=_after_wait())
    _wire(
        monkeypatch,
        [
            {'unresolved': 1, 'comments': [stale]},  # baseline
            {'unresolved': 1, 'comments': [stale]},  # poll 1 — nothing moved yet
            {'unresolved': 1, 'comments': [edited]},  # poll 2 — the in-place edit
        ],
    )

    result = github_ops.cmd_pr_wait_for_comments(_wait_args())

    assert result['status'] == 'success'
    assert result['timed_out'] is False
    # The count never grew — which is exactly why the count-only predicate could
    # not see this, and why asserting on new_count is the load-bearing assertion.
    assert result['new_count'] == 0
    assert result['baseline_count'] == 1
    assert result['final_count'] == 1
    assert result['movement_matched_bots'] == [{'bot_kind': mover}]


def test_count_arm_still_fires_and_the_arms_do_not_mask_each_other(monkeypatch):
    # The count arm is unchanged for a bot that appends a new comment per review.
    # An appending bot posts a SECOND comment (count grows) while the
    # requires_update bot's comment does NOT move: the count arm must fire and the
    # movement arm must contribute nothing. Together with the arm above — where
    # movement fires with new_count == 0 — this pins that neither arm masks the
    # other in either direction.
    mover = _the_mover()
    appender = _the_appender()
    unmoved = _comment(mover, created_at=_before_wait(), updated_at=_before_wait())
    first = _comment(appender, created_at=_before_wait(), updated_at=_before_wait(), body='review 1')
    second = _comment(appender, created_at=_after_wait(), updated_at=_after_wait(), body='review 2')
    second['id'] = 'IC_appender_2'
    _wire(
        monkeypatch,
        [
            {'unresolved': 1, 'comments': [unmoved, first]},
            {'unresolved': 2, 'comments': [unmoved, first, second]},
        ],
    )

    result = github_ops.cmd_pr_wait_for_comments(_wait_args())

    assert result['timed_out'] is False
    assert result['new_count'] == 1
    # The movement arm contributed nothing: the requires_update bot never moved,
    # and the appending bot is not consulted by the movement arm at all.
    assert result['movement_matched_bots'] == []


def test_a_refusal_never_satisfies_the_movement_arm(monkeypatch):
    # A bot editing its comment to say it could NOT review is the bot talking
    # about itself, not a re-review. The timestamp DID move here, so the only
    # thing that can reject it is the refusal seam.
    mover = _the_mover()
    refusal = _comment(
        mover, created_at=_before_wait(), updated_at=_after_wait(), body=_REFUSAL_BODY
    )
    _wire(
        monkeypatch,
        [
            {'unresolved': 1, 'comments': [refusal]},
            {'unresolved': 1, 'comments': [refusal]},
        ],
    )

    result = github_ops.cmd_pr_wait_for_comments(_wait_args(timeout=1, interval=1))

    assert result['timed_out'] is True
    assert result['movement_matched_bots'] == []
    # The discriminator: the refusal WAS observed and classified, so the non-match
    # is the refusal seam rejecting it — not the comment going unnoticed for some
    # unrelated reason, which would make this arm pass for the wrong cause.
    assert [r['bot_kind'] for r in result['rate_limited_bots']] == [mover]


def test_unanswerable_when_no_bot_kinds_are_registered(monkeypatch):
    # First registry disjunct: no bot kinds at all, so no arm has a subject.
    _wire(monkeypatch, [{'unresolved': 1, 'comments': []}])
    monkeypatch.setattr(bot_registry, 'bot_kinds', lambda: [])

    result = github_ops.cmd_pr_wait_for_comments(_wait_args(timeout=1, interval=1))

    assert result['timed_out'] is True
    assert result['detector_answerable'] is False
    assert result['unanswerable_reason']
    assert 'registered' in result['unanswerable_reason']


def test_unanswerable_when_every_bot_declares_no_participation_evidence(monkeypatch):
    # Second registry disjunct: bots exist but none declares an evidence shape —
    # the fail-closed never-provable state. Covering BOTH disjuncts is deliberate:
    # asserting only one would pass against an implementation that happens to
    # check only the other.
    _wire(monkeypatch, [{'unresolved': 1, 'comments': []}])
    monkeypatch.setattr(bot_registry, 'participation_evidence', lambda _bot_kind: [])

    result = github_ops.cmd_pr_wait_for_comments(_wait_args(timeout=1, interval=1))

    assert result['timed_out'] is True
    assert result['detector_answerable'] is False
    assert 'participation_evidence' in result['unanswerable_reason']


def test_a_silent_await_against_the_real_registry_stays_answerable(monkeypatch):
    # THE discriminating case. Asserting only the two unanswerable arms above
    # would pass against a constant False, so this pins the other side: with the
    # registry UNPATCHED and simply no comment movement, the await is a genuine
    # timeout — answerable, and reported as such.
    #
    # It also pins the explicit non-widening the operator settled: an await that
    # merely STARTS WITH NO COMMENTS is answerable, never unanswerable. The signal
    # is derived from the registry alone and is independent of the observed set.
    _wire(monkeypatch, [{'unresolved': 0, 'comments': []}])

    result = github_ops.cmd_pr_wait_for_comments(_wait_args(timeout=1, interval=1))

    assert result['timed_out'] is True
    assert result['detector_answerable'] is True
    assert result['unanswerable_reason'] == ''
    assert result['movement_matched_bots'] == []


def _divergent_case(monkeypatch, comment):
    _wire(
        monkeypatch,
        [
            {'unresolved': 1, 'comments': [comment]},
            {'unresolved': 1, 'comments': [comment]},
        ],
    )
    return github_ops.cmd_pr_wait_for_comments(_wait_args(timeout=1, interval=1))


def test_naive_past_timestamp_is_normalized_and_does_not_match(monkeypatch):
    # Fail-closed obligation 1. A timezone-NAIVE stamp (no Z, no offset) must be
    # normalized to UTC rather than compared against an aware wait_start — the
    # latter raises TypeError. Normalized, this stamp is in the PAST, so the
    # correct outcome is a clean non-match: no crash, no match.
    mover = _the_mover()
    naive_past = (datetime.now(UTC) - _OFFSET).replace(tzinfo=None).isoformat()
    comment = _comment(mover, created_at=naive_past, updated_at=naive_past)

    result = _divergent_case(monkeypatch, comment)

    assert result['status'] == 'success'
    assert result['timed_out'] is True
    assert result['movement_matched_bots'] == []


def test_unparseable_timestamp_is_a_non_match_not_a_wildcard(monkeypatch):
    # Fail-closed obligation 2, and the inverse of the happy-path arms: a stamp
    # that fails to parse yields None, and None must never act as a
    # match-anything wildcard that reads a stale comment as fresh.
    mover = _the_mover()
    comment = _comment(mover, created_at='not-a-timestamp', updated_at='also-not-a-timestamp')

    result = _divergent_case(monkeypatch, comment)

    assert result['status'] == 'success'
    assert result['timed_out'] is True
    assert result['movement_matched_bots'] == []


def test_non_dict_element_in_the_comment_list_is_filtered_not_matched(monkeypatch):
    # Fail-closed obligation 3. ``comments`` is an externally-fetched list, so its
    # elements are untrusted: a non-dict element must be filtered rather than
    # crashing the poll or being echoed into a match.
    _wire(
        monkeypatch,
        [
            {'unresolved': 1, 'comments': ['not-a-dict', None, 42]},
            {'unresolved': 1, 'comments': ['not-a-dict', None, 42]},
        ],
    )

    result = github_ops.cmd_pr_wait_for_comments(_wait_args(timeout=1, interval=1))

    assert result['status'] == 'success'
    assert result['timed_out'] is True
    assert result['movement_matched_bots'] == []
