#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import ROLE_PRODUCTION, BuildExtensionBase

# =============================================================================
# Seed-boundary dead-glob regression — the user-visible contract of the filter
# =============================================================================
#
# The end-to-end guarantee the per-route tree-presence filter exists to
# provide: after a build.map seeding pass, a declared route whose file type is
# absent from the project tree (a dead glob) does NOT appear in the persisted
# build.map, while a live route (whose pattern matches a tracked file) survives.
# This drives the REAL seed pipeline (cmd_build_map_seed → aggregate_build_map →
# derive_globs_from_tree → persisted build.map) against a deterministic extension
# declaring BOTH a live and a dead route — distinct from the unit-level filter
# coverage in test_extension_base_classify_paths.py / test_extension_base.py.


class _LiveAndDeadRouteExtension(BuildExtensionBase):
    """A python-domain build extension declaring one LIVE and one DEAD route.

    The live route (``marketplace/targets/*.py``) matches a tracked fixture file;
    the dead route (``vendor/*.tsx``) matches nothing in the fixture tree. The
    seed must persist the live glob and prune the dead one. Declares itself
    applicable so the applicability filter keeps the domain.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('marketplace/targets/*.py', ROLE_PRODUCTION),  # live — fixture has a match
            ('vendor/*.tsx', ROLE_PRODUCTION),  # dead — no .tsx anywhere in the fixture
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}
