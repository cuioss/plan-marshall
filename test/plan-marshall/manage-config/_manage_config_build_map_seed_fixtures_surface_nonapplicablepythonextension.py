#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import ROLE_PRODUCTION, BuildExtensionBase


class _RaisingApplicabilityExtension(BuildExtensionBase):
    """A python-domain build extension whose applies_to_module() raises.

    The aggregator defends each applies_to_module() call so one misbehaving
    extension cannot crash the seed — the raising extension is simply treated as
    not-applicable and dropped.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('marketplace/targets/*.py', ROLE_PRODUCTION)]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        raise RuntimeError('boom — applies_to_module misbehaved')
