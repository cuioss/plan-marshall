#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""End-to-end mailbox delivery, and the population-derived check-point roster.

Two halves, both of this deliverable:

**(A) The delivery round trip.** Every sibling module in this directory pins one
JOINT of the channel — ``test_inbox_channel_contract.py`` proves the CLI wiring
transports a write, ``test_inbox_envelope.py`` proves the address composes from
one rule, ``test_inbox_message_state.py`` proves the lifecycle vocabulary and the
three delivery states are separately representable. None of them walks the whole
path. This module does: a message is WRITTEN to a plan the epic's status queue
reads as running, READ BACK by that same plan through the plan-side read verb,
CONSUMED by it, and the address is observed at each of the three delivery states
the consumption marker exists to keep apart.

Every assertion here is a **matched pair**, and each pair's two arms differ in
exactly ONE variable, so a green arm is never explained by something other than
the variable under test:

* delivered vs queued — the two addressees differ only in their queue STATUS.
* addressee vs bystander — two plans the epic reads as running alike, differing
  only in whether the message was aimed at them.
* the epic drain vs the addressee — ONE delivered message, read by the two
  readers that must disagree about it.
* never vs waiting vs taken — one address walked through all three, with a
  never-addressed sibling asserted against it at every step, because *consumed*
  and *never delivered* are the pair a two-state reading collapses.

**The anti-vacuity control** is explicit rather than implied. Delivery replaced a
REFUSAL: the write verb used to return ``status: error`` with
``error: undeliverable_to_running_plan`` for exactly the case this module now
walks end to end. The refusal's own payload shape is reproduced here as a
literal and run through the SAME predicate the live round trip is judged by, so
the pre-fix behaviour is asserted to FAIL the round trip rather than merely being
described as absent. A test that could pass against that refusal would be
measuring nothing.

**(B) The check-point roster.** ``phase-lifecycle.md`` § "Mailbox check-point
roster" is the sole enumeration of the moments a running plan consults its
mailbox. The roster is **parsed, never hand-listed**: the population comes from
``_dispatch_roster``'s ``parse_roster_rows`` / ``section_lines`` — the same
heading-bounded walk and row parse the phase-6-finalize roster suites read their
own population through, reused unchanged — and both the import-time guard and
each check's own message publish the size it derived, so an empty or shrunken
roster FAILS rather than passing over nothing.

Reachability and completeness are closed in BOTH directions, each by derivation
and each publishing its own population:

* **Roster to site** — for every parsed row, the document that row names is
  opened and the row's anchor key is asserted present at that site.
* **Site to roster** — the documents the rows name are scanned for anchor keys
  and the scanned set is asserted EQUAL to the roster set.

The site-to-roster scan **skips the roster section itself**, heading-bounded.
That skip is load-bearing twice over. Without it the roster's own rows would
supply the very keys the scan is meant to find at execution sites, making the set
equality circular; and the skip must not be performed by CONCATENATING the
regions that survive it, because joining them creates an adjacency the document
does not have and a marker split across the seam would be read as a key nothing
declares. Both properties are pinned by matched controls over synthetic
documents, and the complement walk is tied back to ``section_lines``' own
boundary so the two walks cannot drift.

⛔ **The site-to-roster population is the documents the ROSTER NAMES**, stated
rather than left to be inferred: a check-point marker written into a document no
row names is outside this scan. What the scan does catch is a key present at a
rostered document that no row declares — which is the drift direction the roster
being the sole enumeration is asserted against.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from _dispatch_roster import parse_roster_rows, section_lines
from _ledger_fixtures import write_ledger, write_legacy_status
from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

# =============================================================================
# Part A — the delivery round trip
# =============================================================================

#: The orchestrator script's address, as module-level string constants so every
#: ``parse_ns`` call below stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

_inbox = load_script_module('plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox')
_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script')

WRITE_DESTINATION_QUEUE = _inbox.WRITE_DESTINATION_QUEUE
WRITE_DESTINATION_MAILBOX = _inbox.WRITE_DESTINATION_MAILBOX
MAILBOX_STATE_PRESENT = _inbox.MAILBOX_STATE_PRESENT
MAILBOX_STATE_NO_MAILBOX = _inbox.MAILBOX_STATE_NO_MAILBOX
DELIVERY_STATE_CONSUMED = _inbox.DELIVERY_STATE_CONSUMED
DELIVERY_STATE_DELIVERED_UNCONSUMED = _inbox.DELIVERY_STATE_DELIVERED_UNCONSUMED
DELIVERY_STATE_NEVER_DELIVERED = _inbox.DELIVERY_STATE_NEVER_DELIVERED
CONSUMPTION_CONSUMED = _inbox.CONSUMPTION_CONSUMED
CONSUMPTION_UNCONSUMED = _inbox.CONSUMPTION_UNCONSUMED
LIFECYCLE_CONSUMED = _inbox.LIFECYCLE_CONSUMED
RUNNING_STATUS = _inbox.RUNNING_STATUS
INBOX_DELIVERY_SUBDIR: str = _inbox.INBOX_DELIVERY_SUBDIR

cmd_inbox_list = _inbox.cmd_inbox_list
cmd_inbox_read = _inbox.cmd_inbox_read
cmd_inbox_write = _inbox.cmd_inbox_write
consume_message = _inbox.consume_message

cmd_scaffold = _orch.cmd_scaffold

EPIC = 'delivery-epic'
SENDER = 'sender-plan'

#: The addressee — the plan the epic's status queue reads as running, so a
#: message aimed at it is DELIVERED to its mailbox.
ADDRESSEE = 'addressee-plan'

#: The matched control for the routing decision: identical in every respect
#: except its queue status, so the delivered/queued pair differs in ONE variable.
SETTLED_PLAN = 'settled-plan'

#: The matched control for the address: a plan the queue reads as running exactly
#: as the addressee is, differing only in that no message was ever aimed at it.
BYSTANDER = 'bystander-plan'

#: A queue status that is NOT ``running``. Only its INEQUALITY with
#: :data:`RUNNING_STATUS` matters to the routing decision — the token itself is
#: an ordinary settled state — so the inequality is asserted rather than assumed.
NOT_RUNNING_STATUS = 'landed'
assert NOT_RUNNING_STATUS != RUNNING_STATUS, (
    f'the queued arm of every matched pair below needs a status the routing decision does NOT read as running, '
    f'and {NOT_RUNNING_STATUS!r} is the running token itself — both arms would deliver and the pair would prove nothing'
)

#: The retired refusal the delivery route replaced, reproduced as the payload
#: shape ``cmd_inbox_write`` used to return for a running addressee. It is a
#: LITERAL rather than a live call, because the branch no longer exists: it is
#: run through :func:`_delivery_happened` beside the live result so the pre-fix
#: behaviour is asserted to FAIL the round trip, not merely described as gone.
_PRE_FIX_REFUSAL: dict[str, Any] = {
    'status': 'error',
    'store': 'orchestrator',
    'error': 'undeliverable_to_running_plan',
    'message': 'message names target plan, which is currently running in epic',
    'slug': EPIC,
    'target_plan': ADDRESSEE,
}


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_SCAFFOLD_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'scaffold', '--slug', EPIC, register=False)

_WRITE_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'inbox',
    'write',
    '--slug',
    EPIC,
    '--sender-type',
    'plan',
    '--sender-id',
    SENDER,
    '--kind',
    'finding',
    '--payload-file',
    '',
    register=False,
)

_LIST_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'inbox', 'list', '--slug', EPIC, register=False)

_READ_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'inbox',
    'read',
    '--slug',
    EPIC,
    '--plan-id',
    ADDRESSEE,
    register=False,
)


def _epic_dir(plan_context, slug: str = EPIC) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _inbox_dir(plan_context, slug: str = EPIC) -> Path:
    return _epic_dir(plan_context, slug) / 'inbox'


def _mailbox_dir(plan_context, plan_id: str = ADDRESSEE, slug: str = EPIC) -> Path:
    return _inbox_dir(plan_context, slug) / INBOX_DELIVERY_SUBDIR / plan_id


def _payload(tmp_path: Path, body: str = 'the advisory body', name: str = 'p.md') -> str:
    path = tmp_path / name
    path.write_text(body, encoding='utf-8')
    return str(path)


def _queue_doc(rows: list[tuple[str, str]]) -> dict[str, Any]:
    """A legacy-shaped ledger dict whose queue holds the supplied ``(plan id, status)`` rows.

    Each row is keyed by a spec id (``PLAN-01``, ``PLAN-02``, … in the order
    given) and carries the addressed plan in ``plan_marshall_plan_id`` — the plan
    id it runs under, which is what ``--target-plan`` names.
    """
    return {
        'kind': 'orchestrator',
        'phase': 'orchestrating',
        'plans': [
            {'id': f'PLAN-{index:02d}', 'status': plan_status, 'plan_marshall_plan_id': plan_id}
            for index, (plan_id, plan_status) in enumerate(rows, start=1)
        ],
        'resume_anchor': '',
    }


def _set_plan_queue(plan_context, rows: list[tuple[str, str]], slug: str = EPIC) -> None:
    """Record the epic's queue as the supplied ``(plan id, status)`` rows.

    The machine authority the routing decision reads, seeded as a per-concern
    ledger through ``_ledger_fixtures.write_ledger``. Writing the WHOLE queue in
    one call — rather than marking plans running one at a time — is what lets a
    matched pair's two arms be stated side by side, differing only in the status
    token each row carries.
    """
    write_ledger(_epic_dir(plan_context, slug), _queue_doc(rows))


def _write(tmp_path: Path, *, target_plan: str | None, body: str, name: str) -> dict[str, Any]:
    """Write one message, optionally aimed at ``target_plan``."""
    result: dict[str, Any] = cmd_inbox_write(
        _variant(_WRITE_ARGS, payload_file=_payload(tmp_path, body, name), target_plan=target_plan)
    )
    return result


def _read_mailbox(plan_id: str = ADDRESSEE, slug: str = EPIC) -> dict[str, Any]:
    payload: dict[str, Any] = cmd_inbox_read(_variant(_READ_ARGS, slug=slug, plan_id=plan_id))
    return payload


def _delivery_happened(write_result: dict[str, Any]) -> bool:
    """Whether ``write_result`` says a message was DELIVERED to a plan mailbox.

    The ONE predicate both the live round trip and the reproduced pre-fix refusal
    are judged by, so the anti-vacuity control compares like with like instead of
    asserting two differently-shaped things about two different payloads. It is a
    MEANING test over the closed ``destination`` vocabulary, never a presence test
    on a field: a refusal carries no ``destination`` at all and a queued write
    carries the other member, so all three shapes are discriminated.
    """
    return write_result.get('status') == 'success' and write_result.get('destination') == WRITE_DESTINATION_MAILBOX


class TestDeliveryRoundTrip:
    def test_a_running_addressee_receives_the_message_and_reads_it_back(self, plan_context, tmp_path):
        """The whole path in one case: write -> delivered -> the plan reads it.

        Not "the write reported success" — the reading plan is asserted to
        enumerate the very message the write allocated, with the body it carried,
        because a delivery nobody can read is the failure mode the mailbox exists
        to remove.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS)])

        written = _write(tmp_path, target_plan=ADDRESSEE, body='the advisory body', name='a.md')
        payload = _read_mailbox()

        assert written['status'] == 'success'
        assert written['destination'] == WRITE_DESTINATION_MAILBOX
        assert written['target_plan'] == ADDRESSEE
        # The plan-side read resolved the address the write delivered to...
        assert payload['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert payload['count'] == 1
        assert payload['live_count'] == 1
        assert payload['unconsumed_count'] == 1
        assert payload['delivery_state'] == DELIVERY_STATE_DELIVERED_UNCONSUMED
        # ...and it is THIS message, carrying the body that was written.
        assert [row['name'] for row in payload['messages']] == [written['message']]
        delivered = _mailbox_dir(plan_context) / written['message']
        assert delivered.read_text(encoding='utf-8').endswith('the advisory body\n')

    def test_delivery_and_queueing_differ_only_in_the_addressees_queue_status(self, plan_context, tmp_path):
        """The routing pair, asserted against itself.

        Two addressees in ONE epic, written by ONE sender with identical argv but
        for the plan name, differing in exactly one variable: whether the queue
        reads that plan as running. Asserting the two arms together is what makes
        the running distinction load-bearing rather than a label on a write that
        would have gone to the same place either way.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS), (SETTLED_PLAN, NOT_RUNNING_STATUS)])

        delivered = _write(tmp_path, target_plan=ADDRESSEE, body='for the running plan', name='a.md')
        queued = _write(tmp_path, target_plan=SETTLED_PLAN, body='for the settled plan', name='b.md')

        assert delivered['destination'] == WRITE_DESTINATION_MAILBOX
        assert queued['destination'] == WRITE_DESTINATION_QUEUE
        # The two arms are compared by the DIRECTORY each message landed in, not
        # by filename: both writes come from one sender and each location
        # allocates its own sequence, so the two messages legitimately share a
        # name and a name-based probe would read one arm's file as the other's.
        assert Path(delivered['path']).parent == _mailbox_dir(plan_context, ADDRESSEE)
        assert Path(delivered['path']).is_file()
        assert Path(queued['path']).parent == _inbox_dir(plan_context)
        assert Path(queued['path']).is_file()
        # The queued arm created no mailbox at all for its addressee.
        assert not _mailbox_dir(plan_context, SETTLED_PLAN).exists()
        # Read from each plan's own side, the two arms report opposite states.
        assert _read_mailbox(ADDRESSEE)['delivery_state'] == DELIVERY_STATE_DELIVERED_UNCONSUMED
        assert _read_mailbox(SETTLED_PLAN)['delivery_state'] == DELIVERY_STATE_NEVER_DELIVERED

    def test_only_the_addressee_sees_the_delivery(self, plan_context, tmp_path):
        """The address pair: two plans the queue reads as running alike.

        They differ in exactly one variable — whether the message was aimed at
        them — so a mailbox that leaked to every running plan, or an address that
        resolved to a shared location, fails here rather than passing on the
        addressee's arm alone.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS), (BYSTANDER, RUNNING_STATUS)])

        _write(tmp_path, target_plan=ADDRESSEE, body='aimed at the addressee', name='a.md')

        addressed = _read_mailbox(ADDRESSEE)
        bystanding = _read_mailbox(BYSTANDER)

        assert addressed['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert addressed['count'] == 1
        assert bystanding['mailbox_state'] == MAILBOX_STATE_NO_MAILBOX
        assert bystanding['count'] == 0
        assert addressed['mailbox_dir'] != bystanding['mailbox_dir']

    def test_the_epic_drain_and_the_addressee_disagree_about_one_delivered_message(self, plan_context, tmp_path):
        """ONE message, the two readers that must not agree about it.

        The mailbox tree is disjoint from the queue and the drain enumeration is
        non-recursive, so the drain reports a looked-and-empty queue while the
        addressee reports the message waiting. Asserted as a pair: a drain that
        started counting deliveries, or an addressee that stopped seeing them,
        each fail on the arm the other cannot cover.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS)])

        _write(tmp_path, target_plan=ADDRESSEE, body='delivered, not queued', name='a.md')

        drained = cmd_inbox_list(_LIST_ARGS)
        addressed = _read_mailbox()

        # ``inbox_state`` is the DRAIN's own discriminator vocabulary, distinct
        # from the mailbox read's, so its looked-and-empty member is named here
        # from that vocabulary rather than borrowed from the mailbox one.
        assert drained['inbox_state'] in _inbox.INBOX_STATES
        assert drained['inbox_state'] == 'present'
        assert drained['count'] == 0
        assert drained['live_count'] == 0
        assert addressed['count'] == 1
        assert addressed['live_count'] == 1


class TestLegacyLayoutQueuesRatherThanDelivers:
    def test_a_legacy_ledger_naming_the_addressee_running_queues_the_message(self, plan_context, tmp_path):
        """The ``_orchestrator_inbox`` rule for an unmigrated ledger, as a matched pair.

        Both arms name the addressee as ``running`` in the SAME queue content and
        differ only in the ledger layout: the per-concern arm delivers, while the
        monolithic arm — whose ``plans[]`` is refused rather than read — queues,
        and names why. A legacy document is never POSITIVELY read as running, so
        delivery is never inferred from it.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        write_legacy_status(_epic_dir(plan_context), _queue_doc([(ADDRESSEE, RUNNING_STATUS)]))

        legacy = _write(tmp_path, target_plan=ADDRESSEE, body='aimed at a legacy ledger', name='a.md')

        assert legacy['status'] == 'success'
        assert legacy['destination'] == WRITE_DESTINATION_QUEUE
        assert legacy['routing_reason'] == _inbox.ROUTING_LEDGER_LEGACY
        assert not _mailbox_dir(plan_context).exists()

        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS)])
        migrated = _write(tmp_path, target_plan=ADDRESSEE, body='aimed at a migrated ledger', name='b.md')

        assert migrated['destination'] == WRITE_DESTINATION_MAILBOX
        assert migrated['routing_reason'] == _inbox.ROUTING_TARGET_RUNNING

    def test_every_routing_reason_is_a_member_of_the_closed_vocabulary(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS), (SETTLED_PLAN, NOT_RUNNING_STATUS)])

        reasons = {
            _write(tmp_path, target_plan=ADDRESSEE, body='a', name='a.md')['routing_reason'],
            _write(tmp_path, target_plan=SETTLED_PLAN, body='b', name='b.md')['routing_reason'],
            _write(tmp_path, target_plan='absent-plan', body='c', name='c.md')['routing_reason'],
            _write(tmp_path, target_plan=None, body='d', name='d.md')['routing_reason'],
        }

        assert reasons == {
            _inbox.ROUTING_TARGET_RUNNING,
            _inbox.ROUTING_TARGET_NOT_RUNNING,
            _inbox.ROUTING_TARGET_NOT_QUEUED,
            _inbox.ROUTING_NO_TARGET,
        }
        assert reasons <= _inbox.ROUTING_REASONS


class TestTheRoundTripWalksAllThreeDeliveryStates:
    def test_never_then_waiting_then_taken_with_a_bystander_held_at_never(self, plan_context, tmp_path):
        """All three states, observed THROUGH the round trip, against a control.

        The vocabulary itself is pinned in ``test_inbox_message_state.py``; what
        this case adds is that the three states are what the WHOLE path produces
        — write, read, consume — and that a never-addressed sibling stays at
        ``never_delivered`` through every step of it. That control is the pair
        which matters: *consumed* and *never delivered* agree on every count a
        two-state reading looks at, so the consumed arm is asserted against a real
        never-delivered arm rather than against its own earlier self alone.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS), (BYSTANDER, RUNNING_STATUS)])

        before = _read_mailbox()
        bystander_before = _read_mailbox(BYSTANDER)
        written = _write(tmp_path, target_plan=ADDRESSEE, body='the advisory body', name='a.md')
        waiting = _read_mailbox()
        bystander_waiting = _read_mailbox(BYSTANDER)
        taken = consume_message(EPIC, ADDRESSEE, written['message'])
        after = _read_mailbox()
        bystander_after = _read_mailbox(BYSTANDER)

        # The addressee walks all three states, and no two share a representation.
        assert before['delivery_state'] == DELIVERY_STATE_NEVER_DELIVERED
        assert waiting['delivery_state'] == DELIVERY_STATE_DELIVERED_UNCONSUMED
        assert after['delivery_state'] == DELIVERY_STATE_CONSUMED
        assert len({before['delivery_state'], waiting['delivery_state'], after['delivery_state']}) == 3
        # The consume itself reported the take, and the marker rides the message
        # AT its delivered path — so the address still knows mail arrived here.
        assert taken['status'] == 'success'
        assert taken['consumption'] == CONSUMPTION_CONSUMED
        assert after['count'] == 1
        assert after['consumed_count'] == 1
        assert after['live_count'] == 0
        assert [row['consumption'] for row in after['messages']] == [CONSUMPTION_CONSUMED]
        delivered = _mailbox_dir(plan_context) / written['message']
        assert f'lifecycle={LIFECYCLE_CONSUMED}' in delivered.read_text(encoding='utf-8')
        # The control never moves: the consumed arm agrees with it on both counts
        # a two-state reading has to go on, and is told apart only by the state.
        assert [
            bystander_before['delivery_state'],
            bystander_waiting['delivery_state'],
            bystander_after['delivery_state'],
        ] == [DELIVERY_STATE_NEVER_DELIVERED] * 3
        assert after['live_count'] == bystander_after['live_count'] == 0
        assert after['unconsumed_count'] == bystander_after['unconsumed_count'] == 0
        assert bystander_after['consumed_count'] == 0

    def test_the_waiting_arm_is_unconsumed_before_it_is_consumed(self, plan_context, tmp_path):
        """The per-message half of the same pair, on one address.

        Two messages delivered to ONE mailbox, one taken and one left, so the
        row-level ``consumption`` is asserted between two rows that differ in
        exactly one variable rather than between two mailboxes.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS)])
        taken = _write(tmp_path, target_plan=ADDRESSEE, body='same body', name='a.md')
        left = _write(tmp_path, target_plan=ADDRESSEE, body='same body', name='b.md')

        consume_message(EPIC, ADDRESSEE, taken['message'])

        payload = _read_mailbox()
        rows = {row['name']: row for row in payload['messages']}
        assert rows[taken['message']]['consumption'] == CONSUMPTION_CONSUMED
        assert rows[left['message']]['consumption'] == CONSUMPTION_UNCONSUMED
        assert payload['delivery_state'] == DELIVERY_STATE_DELIVERED_UNCONSUMED
        assert (payload['consumed_count'], payload['unconsumed_count']) == (1, 1)


class TestAntiVacuityAgainstThePreFixRefusal:
    def test_the_delivery_predicate_discriminates_all_three_write_shapes(self, plan_context, tmp_path):
        """THE anti-vacuity control: the pre-fix refusal must FAIL this round trip.

        One predicate, three shapes. The live delivered write passes it; the live
        QUEUED write fails it (so the predicate is not merely reading
        ``status: success``); and the reproduced ``undeliverable_to_running_plan``
        refusal fails it too. Without the third arm every case in this module
        would be describing a behaviour rather than pinning the change to it — the
        refusal is the shape the corpus actually had, and it is asserted red here.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS), (SETTLED_PLAN, NOT_RUNNING_STATUS)])

        delivered = _write(tmp_path, target_plan=ADDRESSEE, body='delivered', name='a.md')
        queued = _write(tmp_path, target_plan=SETTLED_PLAN, body='queued', name='b.md')

        assert _delivery_happened(delivered) is True
        assert _delivery_happened(queued) is False
        assert _delivery_happened(_PRE_FIX_REFUSAL) is False

    def test_the_live_write_carries_none_of_the_refusals_observable_traces(self, plan_context, tmp_path):
        """The refusal left three traces; the delivery leaves none of them.

        It returned an error status, it carried the retired error code, and it
        allocated no file anywhere. Each is asserted against the live write, so a
        reintroduced refusal fails on all three rather than on a status field
        alone — and the mailbox file plus the addressee's own read are facts the
        refusal never produced at all.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        _set_plan_queue(plan_context, [(ADDRESSEE, RUNNING_STATUS)])

        written = _write(tmp_path, target_plan=ADDRESSEE, body='the advisory body', name='a.md')

        assert written['status'] == 'success'
        assert 'error' not in written
        assert written.get('error') != _PRE_FIX_REFUSAL['error']
        assert (_mailbox_dir(plan_context) / written['message']).is_file()
        assert _read_mailbox()['count'] == 1


# =============================================================================
# Part B — the check-point roster
# =============================================================================

_PLAN_MARSHALL_SKILLS: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

#: The roster's home, and the exact heading that bounds it. Both halves are
#: read verbatim from the deliverable rather than paraphrased: the parse is a
#: heading-equality walk, so a heading spelled differently here finds nothing.
_ROSTER_DOC = _PLAN_MARSHALL_SKILLS / 'ref-workflow-architecture' / 'standards' / 'phase-lifecycle.md'
_ROSTER_HEADING = '## Mailbox check-point roster'

#: A check-point's anchor key AS AN EXECUTING SITE PUBLISHES IT. The key rides
#: parentheses immediately after the marker phrase, which is what separates a
#: site from prose that merely CITES the roster (``§ "Mailbox check-point
#: roster"`` carries no parenthesised key) — and from citing prose ONLY.
#: It does NOT separate a site from a roster ROW: a live row carries the full
#: parenthesised form too (the ``subagent-return`` row in ``phase-lifecycle.md``
#: § "Mailbox check-point roster" spells the whole marker), so this pattern
#: matches one. Rows are kept out by the SECTION-EXCLUSION skip instead —
#: ``_regions_excluding_section`` under ``exclude_heading=_ROSTER_HEADING`` —
#: pinned by the matched control in ``TestTheRosterSectionIsSkippedNotScanned``.
_CHECK_POINT_ANCHOR = re.compile(r'Mailbox check-point \(`([^`]+)`\)')

#: Any backticked token. Used to derive a row's document, never to derive its
#: key — the key is what ``parse_roster_rows`` already returns.
_BACKTICKED = re.compile(r'`([^`]+)`')

_ROSTER_TEXT = _ROSTER_DOC.read_text(encoding='utf-8')
_ROSTER_ROWS: list[tuple[str, str]] = parse_roster_rows(_ROSTER_TEXT, _ROSTER_HEADING)
_ROSTER_KEYS: list[str] = [key for key, _ in _ROSTER_ROWS]

# Non-emptiness asserted at IMPORT, ahead of every check below. An empty roster
# would make each direction's set comparison trivially true, so the population
# that every one of them is computed over is guarded here once rather than being
# re-guarded (or forgotten) per test.
assert _ROSTER_ROWS, (
    f'No roster row was parsed from {_ROSTER_DOC.name} § {_ROSTER_HEADING!r} — '
    f'every reachability and completeness check below would compare two empty sets and pass'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The import-time assertion above fails an EMPTY
#: roster; publishing the size is what makes a SHRUNKEN one visible on the green
#: run, where no failure message is ever rendered.
GUARD_POPULATION_LABEL = 'mailbox check-point roster rows'
GUARD_POPULATION_SIZE = len(_ROSTER_ROWS)


def _row_document(row_line: str) -> Path | None:
    """Resolve the document a roster row NAMES, or ``None`` when it names none.

    A row's first backticked ``.md`` token is the document; the row's other
    backticked tokens are its key and the identifiers its prose cites. Deriving
    the document from the row — rather than from a table kept beside it — is what
    lets a row that moves its site be followed instead of going stale.
    """
    tokens: list[str] = _BACKTICKED.findall(row_line)
    for token in tokens:
        if token.endswith('.md'):
            return _PLAN_MARSHALL_SKILLS / token
    return None


def _regions_excluding_section(text: str, heading: str) -> list[list[str]]:
    """Return ``text``'s line regions with the named section REMOVED.

    Regions — a list of line lists — and deliberately never one joined string.
    Joining the surviving regions would place the line before the section
    immediately beside the line after it, an adjacency the document does not
    have, and a construct split across that seam would then match as though the
    document contained it. Scanning each region on its own is what makes the skip
    a skip rather than a splice.

    The boundary rule is ``section_lines``': the heading line is located by
    stripped equality and the section runs to the next ``## `` heading line.
    A document that does not carry the heading yields its lines unchanged, as one
    region, so a scan over a document with no such section is unaffected.
    """
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return [lines]
    end = start + 1
    while end < len(lines) and not lines[end].startswith('## '):
        end += 1
    return [lines[:start], lines[end:]]


def _scan_anchor_keys(text: str, *, exclude_heading: str | None = None) -> set[str]:
    """Collect the anchor keys published at sites in ``text``.

    Each surviving region is matched independently and the results unioned, so no
    key can be produced by an adjacency the skip created.
    """
    regions = _regions_excluding_section(text, exclude_heading) if exclude_heading is not None else [text.splitlines()]
    keys: set[str] = set()
    for region in regions:
        keys.update(_CHECK_POINT_ANCHOR.findall('\n'.join(region)))
    return keys


def _rostered_documents() -> list[Path]:
    """The distinct documents the roster's rows name, in first-named order."""
    documents: list[Path] = []
    for _, row_line in _ROSTER_ROWS:
        document = _row_document(row_line)
        if document is not None and document not in documents:
            documents.append(document)
    return documents


# ---------------------------------------------------------------------------
# The population the two directions are computed over
# ---------------------------------------------------------------------------


class TestRosterPopulation:
    def test_the_roster_population_is_derived_and_non_empty(self):
        """The checks below are only worth as much as the set they range over."""
        assert GUARD_POPULATION_SIZE == len(_ROSTER_ROWS) == len(_ROSTER_KEYS)
        assert GUARD_POPULATION_SIZE > 0, (
            f'{_ROSTER_DOC.name} § {_ROSTER_HEADING!r} yielded {GUARD_POPULATION_SIZE} row(s) — '
            f'an empty roster passes every set comparison below without checking anything'
        )
        assert len(set(_ROSTER_KEYS)) == GUARD_POPULATION_SIZE, (
            f'the roster names {GUARD_POPULATION_SIZE} row(s) but only {len(set(_ROSTER_KEYS))} distinct key(s): '
            f'{_ROSTER_KEYS} — a duplicated key makes the set equality below weaker than the row count suggests'
        )

    def test_every_row_names_a_document_that_exists(self):
        """A row whose site cannot be opened is a roster entry pointing nowhere."""
        unresolved: list[tuple[str, str]] = []
        for key, row_line in _ROSTER_ROWS:
            document = _row_document(row_line)
            if document is None or not document.is_file():
                unresolved.append((key, str(document)))

        assert not unresolved, (
            f'{len(unresolved)} of {GUARD_POPULATION_SIZE} roster row(s) name no readable document: {unresolved}'
        )


# ---------------------------------------------------------------------------
# Direction 1 — roster to site
# ---------------------------------------------------------------------------


class TestRosterReachesEverySite:
    def test_every_rostered_check_point_is_published_at_the_site_its_row_names(self):
        """For each row: open the document it names, find its key published there.

        The population is the parsed rows, so a row added later is checked without
        editing this file, and the checked count is asserted to equal it — a walk
        that silently covered fewer rows than the roster holds would otherwise
        report clean.
        """
        checked: list[str] = []
        missing: list[tuple[str, str]] = []
        for key, row_line in _ROSTER_ROWS:
            document = _row_document(row_line)
            assert document is not None, f'roster row for {key!r} names no document: {row_line}'
            checked.append(key)
            published = _scan_anchor_keys(document.read_text(encoding='utf-8'), exclude_heading=_ROSTER_HEADING)
            if key not in published:
                missing.append((key, str(document)))

        assert len(checked) == GUARD_POPULATION_SIZE, (
            f'walked {len(checked)} row(s) of the {GUARD_POPULATION_SIZE} the roster holds'
        )
        assert not missing, (
            f'{len(missing)} of {GUARD_POPULATION_SIZE} rostered check-point(s) are not published at the site '
            f'their row names: {missing}'
        )


# ---------------------------------------------------------------------------
# Direction 2 — site to roster, with the roster section skipped
# ---------------------------------------------------------------------------


class TestEverySiteIsRostered:
    def test_the_keys_published_at_the_rostered_documents_equal_the_roster(self):
        """Set equality, both populations published in the message.

        The roster section is skipped in every document, so the keys compared are
        the ones EXECUTION SITES publish. Without that skip the roster's own rows
        would be part of the scanned set and the equality would compare the roster
        with itself.
        """
        documents = _rostered_documents()
        assert documents, f'no document was derived from the {GUARD_POPULATION_SIZE} roster row(s)'

        per_document = {
            str(document): sorted(
                _scan_anchor_keys(document.read_text(encoding='utf-8'), exclude_heading=_ROSTER_HEADING)
            )
            for document in documents
        }
        scanned = {key for keys in per_document.values() for key in keys}

        assert scanned, (
            f'scanned {len(documents)} rostered document(s) and found no published check-point at all, '
            f'while the roster names {GUARD_POPULATION_SIZE}: {per_document}'
        )
        assert scanned == set(_ROSTER_KEYS), (
            f'the {len(scanned)} key(s) published across {len(documents)} rostered document(s) disagree with the '
            f'{GUARD_POPULATION_SIZE} the roster names — unrostered: {sorted(scanned - set(_ROSTER_KEYS))}, '
            f'unpublished: {sorted(set(_ROSTER_KEYS) - scanned)}, per document: {per_document}'
        )


# ---------------------------------------------------------------------------
# The skip is a skip — matched controls over synthetic documents
# ---------------------------------------------------------------------------

#: The key the synthetic controls plant. Deliberately not a real roster key, so a
#: control can never be satisfied by the live corpus.
_SYNTHETIC_KEY = 'synthetic-check-point'
_SYNTHETIC_MARKER = f'Mailbox check-point (`{_SYNTHETIC_KEY}`)'


def _synthetic_document(*, marker_inside_roster: bool) -> str:
    """A two-section document with ONE marker, on one side of the roster or the other.

    The two arms differ in exactly one variable — which side the marker sits on —
    so the skip is pinned by the pair rather than by either arm alone.
    """
    filler = 'ordinary prose with no anchor key'
    outside = filler if marker_inside_roster else f'**{_SYNTHETIC_MARKER}** rides an execution site.'
    inside = (
        f'- `{_SYNTHETIC_KEY}` — **{_SYNTHETIC_MARKER}**' if marker_inside_roster else f'- `{_SYNTHETIC_KEY}` — a row'
    )
    return '\n'.join(
        [
            '## An earlier section',
            '',
            outside,
            '',
            _ROSTER_HEADING,
            '',
            inside,
            '',
            '## A later section',
            '',
            filler,
        ]
    )


#: A document whose pre-roster tail and post-roster head would, if the surviving
#: regions were CONCATENATED, spell one marker across the seam. Neither region
#: contains a marker on its own, so a region-wise scan finds nothing and a
#: splicing one invents a key.
_SEAM_HEAD = 'a line ending mid-marker: **Mailbox check-point (`gho'
_SEAM_TAIL = 'st`)** a line beginning mid-marker'


def _seam_document() -> str:
    return '\n'.join(
        [
            '## An earlier section',
            '',
            _SEAM_HEAD,
            _ROSTER_HEADING,
            '',
            f'- `{_SYNTHETIC_KEY}` — a row',
            '',
            '## A later section',
            _SEAM_TAIL,
        ]
    )


class TestTheRosterSectionIsSkippedNotScanned:
    def test_a_marker_outside_the_roster_is_scanned_and_the_same_marker_inside_is_not(self):
        """The matched control pinning the exclusion.

        One marker, two positions. The outside arm proves the scanner CAN see it
        — without that arm an empty inside result would be equally explained by a
        scanner that sees nothing — and the inside arm proves the skip removes it.
        """
        outside = _synthetic_document(marker_inside_roster=False)
        inside = _synthetic_document(marker_inside_roster=True)

        assert _scan_anchor_keys(outside, exclude_heading=_ROSTER_HEADING) == {_SYNTHETIC_KEY}
        assert _scan_anchor_keys(inside, exclude_heading=_ROSTER_HEADING) == set()
        # Non-vacuity: the marker really is present in the inside arm, and it is
        # the SKIP that removed it rather than the marker never being there.
        assert _scan_anchor_keys(inside) == {_SYNTHETIC_KEY}

    def test_the_skip_does_not_concatenate_the_surviving_regions(self):
        """A marker split across the skipped section must not be reassembled.

        The splicing arm is asserted to invent a key, so the region-wise arm's
        empty result is a property of the walk rather than of a document that
        happened to contain nothing.
        """
        document = _seam_document()
        regions = _regions_excluding_section(document, _ROSTER_HEADING)
        spliced = '\n'.join('\n'.join(region) for region in regions)

        phantom = set(_CHECK_POINT_ANCHOR.findall(spliced))
        assert phantom, 'the seam fixture no longer spells a marker across the skipped section — the control is inert'
        assert any('\n' in key for key in phantom), f'the phantom key does not span the seam: {sorted(phantom)}'
        assert _scan_anchor_keys(document, exclude_heading=_ROSTER_HEADING) == set()

    def test_the_skip_boundary_agrees_with_the_shared_section_walk(self):
        """The complement walk and ``section_lines`` cannot drift apart.

        Two walks over one boundary is exactly the duplication that goes stale, so
        the arithmetic ties them: the regions kept, plus the section body
        ``section_lines`` returns, plus the heading line itself, must account for
        every line of the document.
        """
        lines = _ROSTER_TEXT.splitlines()
        body = section_lines(_ROSTER_TEXT, _ROSTER_HEADING)
        regions = _regions_excluding_section(_ROSTER_TEXT, _ROSTER_HEADING)
        kept = sum(len(region) for region in regions)

        assert len(regions) == 2, f'the roster section was not found as an interior section: {len(regions)} region(s)'
        assert kept + len(body) + 1 == len(lines), (
            f'{kept} kept + {len(body)} section + 1 heading != {len(lines)} document line(s) — '
            f'the complement walk and section_lines disagree about the boundary'
        )
