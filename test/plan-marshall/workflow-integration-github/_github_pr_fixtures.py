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

The population is guarded NON-EMPTY at import (:func:`guard_non_empty`) and its
size is published as :data:`CURRENCY_SUBJECT_BOT_COUNT`. A parametrize over an
empty tuple produces a skip rather than a failure, so an unguarded empty
population would let a whole sweep report clean while covering nothing.
"""

from __future__ import annotations

import bot_registry


class VacuousPopulationError(AssertionError):
    """A derived population is empty, so every verdict over it is vacuous."""


def guard_non_empty(population: tuple[str, ...], name: str, derivation: str) -> tuple[str, ...]:
    """Return ``population``, or raise when it is empty.

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
