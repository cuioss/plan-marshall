#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import ROLE_PRODUCTION, BuildExtensionBase

# =============================================================================
# Applicability scoping — applies_to_module() over discovered modules
# =============================================================================
#
# aggregate_build_map() includes a domain's routes only when that domain's owning
# extension's applies_to_module() returns applicable: True for at least one
# discovered project module. These tests redirect both the extension set AND the
# discovered module set so the filter is driven deterministically — a domain that
# declares routes but applies to no discovered module is dropped, and an empty
# discovered-module set yields an empty aggregation (the seed runs only after
# architecture discovery).


class _NonApplicablePythonExtension(BuildExtensionBase):
    """A python-domain build extension declaring routes but never applicable.

    Mirrors the leak the fix closes: an installed bundle whose domain does not
    apply to the project's modules (e.g. java/oci on a python-only project). It
    declares real routes via classify_globs() but its applies_to_module() always
    returns not-applicable, so the aggregator must drop its routes entirely.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('marketplace/targets/*.py', ROLE_PRODUCTION)]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}
