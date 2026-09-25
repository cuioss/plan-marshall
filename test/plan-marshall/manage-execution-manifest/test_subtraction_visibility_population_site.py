# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_subtraction_visibility_population_fixtures import (
    _SITE_INVOCATIONS,
    _derive_apply_sites,
    _mem,
)

# =============================================================================
# Coverage completeness — the fourteenth-site tripwire
# =============================================================================


class TestSiteCoverageCompleteness:
    """The invocation table must account for the derived population exactly."""

    def test_every_derived_site_is_covered(self):
        """A newly-added subtraction site fails HERE, at the point of addition.

        This is the assertion that makes the module a detector rather than a
        sample. A fourteenth ``_apply_*`` site enters the derived population
        automatically and has no invocation entry, so the test names it and
        fails; the author cannot satisfy it without declaring how the new site
        reports its subtraction, which the report-invariant test then checks.
        """
        uncovered = sorted(_derive_apply_sites(_mem) - set(_SITE_INVOCATIONS))

        assert not uncovered, (
            f'uncovered compose-time subtraction site(s): {uncovered}. Add an entry to '
            '_SITE_INVOCATIONS that drives each into a firing drop and declares how it '
            'reports the subtraction. A site with no entry can drop steps silently.'
        )

    def test_no_stale_invocation_entries(self):
        """The mirror direction — a table entry for a site that no longer exists.

        Without it the table would keep passing after a site was deleted, and its
        entry would sit there as a false claim of live coverage.
        """
        stale = sorted(set(_SITE_INVOCATIONS) - _derive_apply_sites(_mem))

        assert not stale, f'_SITE_INVOCATIONS names sites that no longer exist: {stale}'
