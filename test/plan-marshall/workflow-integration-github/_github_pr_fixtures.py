# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``workflow-integration-github`` subtree's fixtures helper.

Home of the **currency-subject bot population** — the bots whose participation
credit is currency-tested because they re-review by editing one persistent
comment in place (``bot_registry.participation_requires_update``). Every module
in this subtree that parametrizes over that population imports it from here by
bare name, so exactly ONE definition of it exists in the test tree.

Re-deriving the population in a consuming module — or hand-listing its members —
is the hand-maintained-roster defect this module exists to close: a bot that
newly opts into ``participation_requires_update`` must inherit every case
parametrized over the population rather than silently escaping it.

Its COMPLEMENT — :data:`CURRENCY_BLIND_BOTS`, the append-per-review bots — is derived
here too, from the same registry read, so the partition cannot drift apart or overlap.

Both populations are guarded NON-EMPTY at import (:func:`guard_non_empty`) and their
sizes are published as :data:`CURRENCY_SUBJECT_BOT_COUNT` and
:data:`CURRENCY_BLIND_BOT_COUNT`. A parametrize over an empty tuple produces a skip
rather than a failure, so an unguarded empty population would let a whole sweep report
clean while covering nothing.

A second partition lives here for the same reason — the **evidence content gate**
(``bot_registry.participation_evidence_marker``). Every declared ``(bot_kind, shape)``
evidence pairing is either GATED on a content marker (:data:`MARKER_GATED_EVIDENCE`)
or credited on the shape alone (:data:`UNGATED_EVIDENCE`). Both halves are derived from
one registry read, guarded non-empty, and sized, so a marker newly declared by a bot
moves its pairing from one half to the other with no test edit.
"""

from __future__ import annotations

import bot_registry


class VacuousPopulationError(AssertionError):
    """A derived population is empty, so every verdict over it is vacuous."""


def guard_non_empty[T](population: tuple[T, ...], name: str, derivation: str) -> tuple[T, ...]:
    """Return ``population``, or raise when it is empty.

    Generic over the member type, so a population of ``(bot_kind, shape)`` pairs is
    guarded exactly as a population of bot kinds is.

    Args:
        population: The derived population.
        name: The population's published name, for the failure message.
        derivation: How the population was derived, so a failure names the
            source to investigate rather than only the empty result.

    Returns:
        The population unchanged, when it carries at least one member.

    Raises:
        VacuousPopulationError: when ``population`` is empty.
    """
    if not population:
        raise VacuousPopulationError(
            f'{name} is empty — derived from {derivation}. Every test parametrized '
            f'over it would skip rather than fail, reporting clean while covering nothing.'
        )
    return population


#: Bots whose participation credit is currency-tested, derived from the registry.
CURRENCY_SUBJECT_BOTS: tuple[str, ...] = guard_non_empty(
    tuple(bot for bot in bot_registry.bot_kinds() if bot_registry.participation_requires_update(bot)),
    'CURRENCY_SUBJECT_BOTS',
    'bot_registry.bot_kinds() filtered by bot_registry.participation_requires_update',
)

#: The published size of the currency-subject bot population.
CURRENCY_SUBJECT_BOT_COUNT: int = len(CURRENCY_SUBJECT_BOTS)

#: Bots whose participation credit is NOT currency-tested — the complement, derived from
#: the same registry read so the two populations cannot drift apart or overlap. These are
#: the append-per-review bots: they publish a NEW comment per review, so the producer
#: credits them on the presence of a declared ``participation_evidence`` publish shape and
#: compares no commit.
#:
#: The complement lives here rather than in a consuming module for the same reason the
#: subject population does: derived in two places is hand-maintained in two places. It is
#: guarded non-empty because the behaviour it parametrizes — the accepted, bounded
#: currency-blind gap recorded in ``automatic-review/standards/bot-participation-contract.md``
#: — would otherwise be asserted over nothing.
CURRENCY_BLIND_BOTS: tuple[str, ...] = guard_non_empty(
    tuple(bot for bot in bot_registry.bot_kinds() if not bot_registry.participation_requires_update(bot)),
    'CURRENCY_BLIND_BOTS',
    'bot_registry.bot_kinds() filtered by NOT bot_registry.participation_requires_update',
)

#: The published size of the currency-blind bot population.
CURRENCY_BLIND_BOT_COUNT: int = len(CURRENCY_BLIND_BOTS)

#: Every declared ``(bot_kind, shape)`` evidence pairing, in registry order — the
#: population the content-gate partition below splits.
_DECLARED_EVIDENCE: tuple[tuple[str, str], ...] = tuple(
    (bot, shape) for bot in bot_registry.bot_kinds() for shape in bot_registry.participation_evidence(bot)
)

#: ``(bot_kind, shape, marker)`` for every declared evidence shape the bot GATES on a
#: content marker: a comment in that shape credits only when its body carries ``marker``.
MARKER_GATED_EVIDENCE: tuple[tuple[str, str, str], ...] = guard_non_empty(
    tuple(
        (bot, shape, marker)
        for bot, shape in _DECLARED_EVIDENCE
        if (marker := bot_registry.participation_evidence_marker(bot, shape))
    ),
    'MARKER_GATED_EVIDENCE',
    'declared (bot_kind, shape) evidence pairings with a bot_registry.participation_evidence_marker',
)

#: The published size of the marker-gated evidence population.
MARKER_GATED_EVIDENCE_COUNT: int = len(MARKER_GATED_EVIDENCE)

#: ``(bot_kind, shape)`` for every declared evidence shape with NO content marker — the
#: FAIL-OPEN half, credited on the shape alone exactly as before the gate existed. The
#: complement of :data:`MARKER_GATED_EVIDENCE` over the same registry read.
UNGATED_EVIDENCE: tuple[tuple[str, str], ...] = guard_non_empty(
    tuple(
        (bot, shape) for bot, shape in _DECLARED_EVIDENCE if not bot_registry.participation_evidence_marker(bot, shape)
    ),
    'UNGATED_EVIDENCE',
    'declared (bot_kind, shape) evidence pairings with no bot_registry.participation_evidence_marker',
)

#: The published size of the ungated evidence population.
UNGATED_EVIDENCE_COUNT: int = len(UNGATED_EVIDENCE)
