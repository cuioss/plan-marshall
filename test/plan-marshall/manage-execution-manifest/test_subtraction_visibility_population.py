# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_subtraction_visibility_population.py: derived."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_subtraction_visibility_population_fixtures import (
    _OUTLINE_DERIVED_SITE_COUNT,
    _REMOVED_VACUOUS_EMITTER,
    _REMOVED_VACUOUS_SITE,
    _REQUEST_KNOWN_SITES,
    _derive_apply_sites,
    _derive_population,
    _manifest_rules,
    _mem,
)

# =============================================================================
# The derived population itself
# =============================================================================


class TestDerivedPopulation:
    """The population is read off the module and is bigger than the known members."""

    def test_population_is_non_empty(self):
        assert _derive_population()

    def test_population_contains_the_three_request_known_sites(self):
        population = _derive_population()

        missing = sorted(_REQUEST_KNOWN_SITES - population)
        assert not missing, f'derivation stopped seeing known subtraction sites: {missing}'

    def test_population_meets_the_outline_derived_floor(self):
        """A count BELOW the outline's thirteen means the derivation shrank.

        Asserted as a floor rather than an equality: the derivation also sees the
        three already-loud confirming sites the outline listed outside its table,
        so the live count legitimately exceeds thirteen. What must never happen is
        the count dropping — that is the derivation losing sight of a site, which
        is precisely the failure a hand-listed population cannot detect.
        """
        population = _derive_population()

        assert len(population) >= _OUTLINE_DERIVED_SITE_COUNT, (
            f'derived population has {len(population)} sites '
            f'({sorted(population)}) — below the {_OUTLINE_DERIVED_SITE_COUNT} the '
            'outline-time derivation recorded. A site the scan used to see has '
            'become invisible to it; fix the derivation, do not lower the floor.'
        )

    def test_apply_sites_are_fully_re_exported(self):
        """A pre-filter defined in ``_manifest_rules`` must be visible to Half A.

        Half A scans the composer entry module. That is complete only while every
        ``_manifest_rules`` pre-filter is re-exported there. A new site added to
        ``_manifest_rules`` without the re-export would be silently outside the
        derived population — full coverage of a population with a hole in it.
        """
        rules_sites = _derive_apply_sites(_manifest_rules)
        composer_sites = _derive_apply_sites(_mem)

        invisible = sorted(rules_sites - composer_sites)
        assert not invisible, (
            f'_manifest_rules defines {invisible} but the composer does not re-export '
            'them, so the derived population cannot see them'
        )

    def test_the_vacuous_pre_filter_and_its_emitter_are_gone(self):
        """Absence is asserted, never assumed.

        ``setattr`` on a module succeeds for a name that was never defined, so a
        stale neutralization elsewhere in the suite would RE-CREATE the removed
        emitter rather than failing. Only an explicit absence assertion makes the
        removal knowable.
        """
        assert not hasattr(_mem, _REMOVED_VACUOUS_SITE)
        assert not hasattr(_mem, _REMOVED_VACUOUS_EMITTER)
        assert not hasattr(_manifest_rules, _REMOVED_VACUOUS_SITE)
