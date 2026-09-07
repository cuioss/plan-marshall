#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The CI-provider population a per-provider suite must cover, DERIVED not declared.

CI providers are discovered, not enumerated: ``_list_providers`` scans every
marketplace bundle's script directory for ``*_provider.py`` and reads each
module's ``get_provider_declarations()``. A suite that hard-codes its provider
arms therefore states a population it does not own — and a provider added to the
tree joins production silently while that suite keeps reporting green over the
providers it happened to know about.

This module is the single seam both body-fidelity suites (``pr view`` and ``issue
view``) resolve their arms through, so hardening one cannot leave the other
behind. Each suite still owns its own STUB DRIVERS — those are provider-specific
by nature — but neither owns the population they must cover.

Resolution note: the discovery walks up from the current working directory to
find ``marketplace/bundles``. It does NOT read ``PLAN_BASE_DIR``, so the autouse
per-test sandbox in the root conftest neither helps nor hinders it, and calling
it at module import (where a parametrize source needs it) reaches the same real
tree a test-body call would.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: The category a CI provider declares. The same string ``ci_health`` and the
#: provider-selection validator use.
CI_CATEGORY = 'ci'


def discover_ci_provider_skills() -> tuple[tuple[str, ...], str]:
    """Return the discovered CI providers' ``skill_name`` values, plus any failure.

    Returns:
        ``(skill_names, failure)``. ``failure`` is empty on a successful scan and
        carries the exception text otherwise — reported rather than raised so a
        discovery problem surfaces as ONE named test failure instead of a
        collection error that takes the whole suite, including the coverage
        assertion that would have explained it, out with it.
    """
    try:
        from _list_providers import find_full_providers_by_category

        declared = find_full_providers_by_category(CI_CATEGORY)
    # Broad by intent: the failure is REPORTED to the caller, never swallowed and
    # never raised out of a parametrize source, where it would take collection down.
    except Exception as exc:
        return (), f'{type(exc).__name__}: {exc}'
    return tuple(sorted({p['skill_name'] for p in declared if p.get('skill_name')})), ''


def build_provider_arms(
    drivers_by_skill: dict[str, Callable[..., Any]],
) -> tuple[tuple[tuple[str, Callable[..., Any]], ...], tuple[str, ...], str]:
    """Pair each DISCOVERED CI provider with the caller's stub driver for it.

    Args:
        drivers_by_skill: The caller's stub drivers, keyed by provider
            ``skill_name``. The caller owns the mapping; it does not own which
            keys are required.

    Returns:
        ``(arms, undriven, failure)`` — the parametrizable ``(skill_name, driver)``
        pairs, the discovered providers with no driver, and the discovery failure
        text. ``undriven`` providers are deliberately NOT parametrized as
        half-cases: a case with no driver cannot assert anything, so the gap is
        reported by :func:`population_defect` instead of pretending to run.
    """
    discovered, failure = discover_ci_provider_skills()
    arms = tuple((skill, drivers_by_skill[skill]) for skill in discovered if skill in drivers_by_skill)
    undriven = tuple(skill for skill in discovered if skill not in drivers_by_skill)
    return arms, undriven, failure


def population_defect(
    arms: tuple[tuple[str, Callable[..., Any]], ...],
    undriven: tuple[str, ...],
    failure: str,
    *,
    suite: str,
    parity_floor: int = 2,
) -> str:
    """Return why ``arms`` is not a trustworthy population, or ``''`` when it is.

    Three ways the population can be untrustworthy, checked in the order that
    explains the others:

    1. Discovery failed, so the population is unknown rather than small — every
       parametrized case below it is vacuous and the emptiness means nothing.
    2. A discovered provider has no driver — the explicit failure a new provider
       must produce, instead of joining production with no coverage here.
    3. Fewer arms than the parity floor — a suite whose whole claim is "both
       providers behave the same way" cannot make it over one provider.
    """
    if failure:
        return f'{suite}: CI-provider discovery failed, so every provider case below is vacuous — {failure}'
    if undriven:
        return (
            f'{suite}: discovered CI provider(s) {list(undriven)} have no stub driver here, '
            f'so they run through no body-fidelity case at all. Add a driver for each to the '
            f"suite's own mapping — this suite must cover every provider the tree declares, "
            f'not the ones it was written against.'
        )
    if len(arms) < parity_floor:
        return (
            f'{suite}: parity is unassertable over {len(arms)} provider(s) '
            f'{[name for name, _ in arms]} — the floor is {parity_floor}'
        )
    return ''
