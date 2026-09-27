#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import ROLE_CONFIG, BuildExtensionBase

# =============================================================================
# End-to-end pipeline regression — multi-module subdir-only config through
# seed → build.map → build-decision
# =============================================================================
#
# The complete user-visible guarantee the bare-basename subdir-matching fix
# exists to provide: a project whose build config files (``package.json``) live
# ONLY in subdirectories — never at repo root — must still (1) carry the
# bare-basename config route in the seeded ``build.map`` (it survives the
# tree-presence prune because ``route_matches`` matches a bare-basename route by
# basename anywhere in the tree) and (2) resolve to a ``build`` verdict when the
# plan footprint touches one of those subdirectory-only config files.
#
# This is a genuine END-TO-END test: the seed leg drives the REAL aggregator
# (``cmd_build_map_seed`` → ``aggregate_build_map`` → ``derive_globs_from_tree``)
# against a multi-module git fixture, persisting the route into the SAME
# marshal.json the ``plan_context`` fixture redirects ``get_marshal_path()`` to.
# The build-decision leg then drives ``should_execute_build`` (the engine behind
# ``cmd_build_decision``), which reads the seeded globs back from that persisted
# marshal.json via the REAL ``_read_build_map_globs`` — only the footprint helper
# is redirected, so the seed → build.map → glob-read → matcher chain runs against
# the fixed ``extension_base.py`` behaviour end to end. Before the fix the
# bare-basename route would never match a subdir-only ``package.json``, so the
# route would be pruned dead at seed time AND the build-decision would resolve to
# ``not_necessary`` — both halves regress without the fix.


class _MultiModuleSubdirConfigExtension(BuildExtensionBase):
    """A node-domain build extension declaring a bare-basename ``package.json`` route.

    Models a multi-module JS project whose build config lives only in
    per-module subdirectories (``module-a/package.json``, ``module-b/package.json``)
    — never at repo root. The bare-basename ``package.json`` route (no ``/``) must
    match those subdir-only files via the basename regime of ``route_matches``, so
    it survives the seed's tree-presence prune. Declares itself applicable so the
    applicability filter keeps the domain.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'node', 'name': 'Node', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('package.json', ROLE_CONFIG)]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}
