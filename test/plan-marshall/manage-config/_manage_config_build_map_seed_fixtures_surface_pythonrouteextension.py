#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import BuildExtensionBase


class _NoRouteExtension(BuildExtensionBase):
    """A python-domain build extension that declares no routes at all (base default).

    Declares itself applicable so the omission is attributable to the empty route
    set, not to the applicability filter.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}
