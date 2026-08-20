#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Observable invariants for title-token ownership and lifecycle.

The **no-orphan-token invariant**: every path that SETS a title token has a
clear that fires on the matching completion event. A set with no paired clear
leaves the terminal asserting something false for as long as the process lives.

The guard is derived from the ``TITLE_TOKEN_STATES`` constant rather than a
hand-maintained list, so a token added later is covered automatically. A
hand-listed guard is the failure mode this deliberately avoids: it passes
vacuously the moment the vocabulary grows past the list, and the omission is
invisible at the guard's own site.

Owner arbitration and age-based staleness are asserted here at the INVARIANT
level — as properties that hold across the whole vocabulary — rather than as
per-value cases. The per-value behaviour of the ``title-token`` verb lives in
``test_title_token.py``.
"""

import json
from argparse import Namespace
from datetime import UTC, datetime, timedelta

from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_tto_cmd_lifecycle'
)
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_tto_cmd_query')
_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_tto_cmd_core')

cmd_create = _lifecycle.cmd_create
cmd_title_token = _query.cmd_title_token
TITLE_TOKEN_STATES = _core.TITLE_TOKEN_STATES
TITLE_TOKEN_OWNERS = _core.TITLE_TOKEN_OWNERS
TITLE_TOKEN_STALE_AFTER_SECONDS = _core.TITLE_TOKEN_STALE_AFTER_SECONDS
read_title_token = _core.read_title_token
title_token_is_stale = _core.title_token_is_stale


def _read_status(plan_context, plan_id):
    return json.loads(
        (plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8')
    )


def _set(plan_id, state, owner='cli'):
    return cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state=state, owner=owner))


def _clear(plan_id, owner='cli'):
    return cmd_title_token(Namespace(plan_id=plan_id, token_verb='clear', owner=owner))


def _age_token(plan_context, plan_id, seconds):
    """Backdate the stored token's ``set_at`` by ``seconds``, in place."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_file.read_text(encoding='utf-8'))
    aged = datetime.now(UTC) - timedelta(seconds=seconds)
    status['title_token']['set_at'] = aged.strftime('%Y-%m-%dT%H:%M:%SZ')
    status_file.write_text(json.dumps(status), encoding='utf-8')


# =============================================================================
# (b) No-orphan-token invariant — derived from the vocabulary, not a hand list
# =============================================================================


class TestNoOrphanTokenInvariant:
    """Every settable state can be retired by its own owner.

    The class iterates ``TITLE_TOKEN_STATES`` x ``TITLE_TOKEN_OWNERS`` so a
    state or owner added later is covered without editing this file. That
    derivation is the point: a hand-maintained list would silently stop
    covering the vocabulary the moment it grew.
    """

    def test_every_state_can_be_set_and_cleared_by_its_owner(self, plan_context):
        """The invariant, swept across the full vocabulary cross-product.

        For every (state, owner) pair: a set persists the record, and the
        matching owner-scoped clear removes it. A pair that could be set but
        never cleared is an orphan token by construction — the terminal would
        keep painting its glyph with no path back.
        """
        for state in sorted(TITLE_TOKEN_STATES):
            for owner in sorted(TITLE_TOKEN_OWNERS):
                plan_id = f'orphan-{state}-{owner}'
                cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))

                _set(plan_id, state, owner=owner)
                stored = _read_status(plan_context, plan_id)['title_token']
                assert stored['state'] == state, (state, owner)
                assert stored['owner'] == owner, (state, owner)

                result = _clear(plan_id, owner=owner)
                assert result['cleared'] is True, (state, owner)
                assert 'title_token' not in _read_status(plan_context, plan_id), (state, owner)

    def test_every_state_ages_out_even_if_no_clear_ever_fires(self, plan_context):
        """The backstop half: a token whose clear NEVER fires still self-heals.

        The owner-scoped clear covers the healthy path; this covers the
        process-death path, where no clear can fire at all. Without it the
        invariant would hold only while every writer stays alive — exactly the
        assumption the retired phase-boundary sweep made.
        """
        for state in sorted(TITLE_TOKEN_STATES):
            plan_id = f'aged-{state}'
            cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))
            _set(plan_id, state, owner='cli')
            _age_token(plan_context, plan_id, TITLE_TOKEN_STALE_AFTER_SECONDS + 60)

            assert read_title_token(_read_status(plan_context, plan_id)) is None, state

    def test_no_state_is_retired_while_still_live(self, plan_context):
        """Positive control for both mechanisms above.

        Without this, a ``read_title_token`` that unconditionally returned
        ``None`` would satisfy every ageing assertion in this class. Each state
        must still READ while fresh.
        """
        for state in sorted(TITLE_TOKEN_STATES):
            plan_id = f'live-{state}'
            cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))
            _set(plan_id, state, owner='cli')

            live = read_title_token(_read_status(plan_context, plan_id))
            assert live is not None, state
            assert live['state'] == state


# =============================================================================
# Owner arbitration — asserted as a property over the vocabulary
# =============================================================================


class TestOwnerArbitrationInvariant:
    """Arbitration is asymmetric by design: open SET, owner-scoped CLEAR.

    Both halves are swept over the owner vocabulary rather than spot-checked on
    one pair, because the asymmetry is what makes ownership mean anything: an
    open clear would let any writer retire any other writer's glyph, and a
    scoped set would let a stale token block every later writer.
    """

    def test_a_set_from_any_owner_wins_over_any_other_owner(self, plan_context):
        """SET is open: every owner can overwrite every other owner's record."""
        for setter in sorted(TITLE_TOKEN_OWNERS):
            for overwriter in sorted(TITLE_TOKEN_OWNERS):
                plan_id = f'arb-set-{setter}-{overwriter}'
                cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))

                _set(plan_id, 'lock-waiting', owner=setter)
                _set(plan_id, 'build-busy', owner=overwriter)

                stored = _read_status(plan_context, plan_id)['title_token']
                assert stored['owner'] == overwriter, (setter, overwriter)
                assert stored['state'] == 'build-busy', (setter, overwriter)

    def test_a_clear_from_any_foreign_owner_is_refused(self, plan_context):
        """CLEAR is scoped: no owner can retire a live foreign-owned record."""
        for holder in sorted(TITLE_TOKEN_OWNERS):
            for intruder in sorted(TITLE_TOKEN_OWNERS - {holder}):
                plan_id = f'arb-clear-{holder}-{intruder}'
                cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))

                _set(plan_id, 'build-busy', owner=holder)
                result = _clear(plan_id, owner=intruder)

                assert result['cleared'] is False, (holder, intruder)
                assert result['reason'] == 'foreign_owner', (holder, intruder)
                stored = _read_status(plan_context, plan_id)['title_token']
                assert stored['owner'] == holder, (holder, intruder)

    def test_staleness_overrides_ownership_for_every_owner_pair(self, plan_context):
        """The one sanctioned override: an AGED record yields to any owner.

        Ownership must not outlive usefulness — a token stranded by a dead
        process would otherwise be permanently unclearable by anyone.
        """
        for holder in sorted(TITLE_TOKEN_OWNERS):
            for reaper in sorted(TITLE_TOKEN_OWNERS - {holder}):
                plan_id = f'arb-stale-{holder}-{reaper}'
                cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))

                _set(plan_id, 'build-busy', owner=holder)
                _age_token(plan_context, plan_id, TITLE_TOKEN_STALE_AFTER_SECONDS + 60)

                result = _clear(plan_id, owner=reaper)
                assert result['cleared'] is True, (holder, reaper)
                assert result['reason'] == 'stale', (holder, reaper)


# =============================================================================
# Staleness threshold — the boundary, not just "old" vs "new"
# =============================================================================


class TestStalenessBoundary:
    """The threshold is a real boundary with both sides pinned.

    Asserting only "very old is stale" would pass for a predicate that called
    everything stale. Both sides of the documented threshold are checked so the
    boundary itself is the contract.
    """

    def test_just_inside_the_threshold_is_live(self):
        now = datetime.now(UTC)
        set_at = now - timedelta(seconds=TITLE_TOKEN_STALE_AFTER_SECONDS - 1)
        record = {
            'owner': 'cli',
            'state': 'build-busy',
            'set_at': set_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        assert title_token_is_stale(record, now=now) is False

    def test_just_outside_the_threshold_is_stale(self):
        now = datetime.now(UTC)
        set_at = now - timedelta(seconds=TITLE_TOKEN_STALE_AFTER_SECONDS + 1)
        record = {
            'owner': 'cli',
            'state': 'build-busy',
            'set_at': set_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        assert title_token_is_stale(record, now=now) is True

    def test_the_threshold_exceeds_the_longest_build_ceiling(self):
        """The threshold is DERIVED, not arbitrary.

        It must comfortably exceed the longest architecture-resolved build
        ceiling in this project (~1926 s for an unscoped whole-tree verify), or
        a live build bracket could age out mid-call and drop the 🔨 while the
        build was still running.
        """
        longest_observed_build_ceiling_seconds = 1926
        assert TITLE_TOKEN_STALE_AFTER_SECONDS > longest_observed_build_ceiling_seconds
