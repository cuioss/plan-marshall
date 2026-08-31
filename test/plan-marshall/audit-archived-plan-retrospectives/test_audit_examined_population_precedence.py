#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``_examined_population`` key PRECEDENCE — the documented order decides, not the
order the block happens to print its keys in.

The defect this pins: the reader was a single `re.search` over an alternation of
the population keys. `re.search` returns the earliest match in the TEXT, never the
earliest alternative in the PATTERN, so an alternation silently substitutes the
block's print order for the documented precedence. The docstring promised
`plans_in_corpus` outranks the check-local aliases; the implementation delivered
"whichever key is printed first".

That was not a latent risk. Both checks that publish an alias beside the canonical
key print the ALIAS FIRST, so the alternation returned the alias in exactly the
blocks where the precedence was supposed to apply — inoperative for 100% of the
population it governed.

⛔ Every test below stages the SAME block in BOTH key orders and asserts the same
answer. A single-order test cannot detect this defect: it passes against the
alternation whenever the order it happens to stage is the one the alternation gets
right. The both-orders pairing is the whole discriminating power of this file.
"""

import pytest
from _audit_fixtures import audit

#: The canonical key, and the two check-local aliases it outranks. Derived from
#: production rather than restated, so a key added there without a decision here
#: fails the coverage test at the bottom instead of silently going unpinned.
_CANONICAL = 'plans_in_corpus'
_ALIASES = tuple(k for k in audit._EXAMINED_POPULATION_KEYS if k != _CANONICAL)


def _block(*pairs: tuple[str, int]) -> str:
    """Render a check block declaring each ``(key, value)`` in the order given."""
    lines = ['check: staged', 'status: success']
    lines += [f'{key}: {value}' for key, value in pairs]
    return '\n'.join(lines) + '\n'


class TestCanonicalKeyOutranksAliasesInBothOrders:
    """`plans_in_corpus` decides regardless of where it is printed."""

    @pytest.mark.parametrize('alias', _ALIASES)
    def test_canonical_wins_when_printed_first(self, alias: str):
        block = _block((_CANONICAL, 11), (alias, 77))

        assert audit._examined_population(block, corpus_size=99) == 11

    @pytest.mark.parametrize('alias', _ALIASES)
    def test_canonical_wins_when_printed_second(self, alias: str):
        """THE red-against-the-pre-fix-implementation case.

        Under the retired single-alternation `re.search`, the alias is the earliest
        match in the text and its value (77) is returned — so this assertion fails
        with 77 != 11. This is also the real-world shape: the checks that publish
        both keys print the alias first.
        """
        block = _block((alias, 77), (_CANONICAL, 11))

        assert audit._examined_population(block, corpus_size=99) == 11

    @pytest.mark.parametrize('alias', _ALIASES)
    def test_the_two_orders_agree(self, alias: str):
        """Stated as an invariant rather than as two coincidentally-equal numbers.

        Print order is not information: the same declarations must yield the same
        population whichever way round they are rendered.
        """
        first = audit._examined_population(_block((_CANONICAL, 11), (alias, 77)), 99)
        second = audit._examined_population(_block((alias, 77), (_CANONICAL, 11)), 99)

        assert first == second == 11


class TestAliasPrecedenceAmongThemselves:
    """With the canonical key ABSENT, the tuple order still decides."""

    def test_earlier_alias_outranks_later_alias_in_both_orders(self):
        # `_EXAMINED_POPULATION_KEYS` order is the contract; whichever alias comes
        # first in that tuple must win from either print position.
        earlier, later = _ALIASES[0], _ALIASES[1]

        printed_in_order = _block((earlier, 5), (later, 6))
        printed_reversed = _block((later, 6), (earlier, 5))

        assert audit._examined_population(printed_in_order, 99) == 5
        assert audit._examined_population(printed_reversed, 99) == 5

    @pytest.mark.parametrize('alias', _ALIASES)
    def test_a_lone_alias_is_still_read(self, alias: str):
        """The reason the aliases are read at all.

        A check publishing only its own spelling must still be understood — the
        precedence exists to rank co-present keys, not to discard the ones it
        outranks.
        """
        assert audit._examined_population(_block((alias, 8)), corpus_size=99) == 8


class TestPrecedenceOverExclusionArithmetic:
    """A declared population outranks the exclusion arithmetic, in both orders."""

    def test_declaration_beats_a_contradicting_exclusion_line(self):
        # `exploration-share` and `billing-composition` narrow on a SECOND axis the
        # shipping arithmetic cannot see, so deriving from exclusions alone reported
        # both as disciplinary over a population of zero.
        declared_first = _block((_CANONICAL, 4), ('plans_excluded_non_shipping', 9))
        excluded_first = _block(('plans_excluded_non_shipping', 9), (_CANONICAL, 4))

        assert audit._examined_population(declared_first, corpus_size=10) == 4
        assert audit._examined_population(excluded_first, corpus_size=10) == 4

    def test_exclusion_arithmetic_still_applies_with_no_declaration(self):
        """The negative control for the precedence: tier 2 must remain reachable.

        Without this, every assertion above would pass against a reader that
        ignored the exclusion line entirely.
        """
        block = _block(('plans_excluded_non_shipping', 3))

        assert audit._examined_population(block, corpus_size=10) == 7


class TestEveryDeclaredKeyIsPinnedHere:
    """Population-derived coverage: no key may be added without a decision.

    The set this file reasons over is DERIVED from
    `_EXAMINED_POPULATION_KEYS`, so a fourth key appearing in production without a
    precedence decision fails here rather than going silently unpinned. The
    population size is published by the assertion itself.
    """

    def test_the_canonical_key_is_first_in_the_production_tuple(self):
        assert audit._EXAMINED_POPULATION_KEYS[0] == _CANONICAL

    def test_the_alias_set_is_exactly_the_non_canonical_remainder(self):
        assert set(_ALIASES) == set(audit._EXAMINED_POPULATION_KEYS) - {_CANONICAL}
        assert len(audit._EXAMINED_POPULATION_KEYS) == 3, (
            'the key population changed — every parametrized case above is derived '
            'from it, and the alias-vs-alias test indexes _ALIASES[0] and [1], so a '
            'new key needs an explicit precedence decision here'
        )
