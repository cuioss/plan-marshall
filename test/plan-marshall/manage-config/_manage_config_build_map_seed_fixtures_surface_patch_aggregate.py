#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import ROLE_PRODUCTION, ROLE_TEST, BuildExtensionBase


class _PythonRouteExtension(BuildExtensionBase):
    """A real build extension declaring explicit .py routes under domain key 'python'.

    Mirrors the python domain's explicit (pattern, role) routes: an out-of-scripts
    production route (``marketplace/targets/*.py``, an fnmatch glob) plus a test
    route. The deriver collects the declared routes verbatim, so a production .py
    outside scripts/ is covered by declaring a route whose pattern matches it.
    Declares itself applicable so the applicability filter keeps its routes.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('marketplace/targets/*.py', ROLE_PRODUCTION),
            ('test/*.py', ROLE_TEST),
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}
