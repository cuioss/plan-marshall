#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``detect_name_drift`` role resolution — canonical-verify step IDs, legacy bare
default-step names, ``default:``-namespaced steps, unresolvable roles, and the
empty-phase_5 no-op. Resolution is in-code via the canonical->role table.
"""

from pathlib import Path

from _audit_fixtures import (
    _inputs,
    audit,
)

from conftest import PROJECT_ROOT


class TestNameDriftRoleResolution:
    def test_parameterized_canonical_verify_steps_not_flagged(self):
        # the post-deletion shape: a well-composed manifest carries the single
        # parameterized canonical-verify step, one row per canonical.
        inputs = _inputs(['default:verify:quality-gate', 'default:verify:module-tests'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)
        resolved = {
            audit._resolve_step_role(PROJECT_ROOT, s, cache)
            for s in inputs.manifest_phase_5
        }

        # quality-gate → quality-gate, module-tests → module-tests; resolution is
        # in-code via the canonical→role table (no role-file read).
        assert drift is None
        assert resolved == {'quality-gate', 'module-tests'}

    def test_canonical_verify_aliases_resolve_to_module_tests(self):
        # the `verify` and `module-tests` canonicals both map to module-tests;
        # a coverage canonical resolves but alone gives zero intersection.
        cache: dict[str, str | None] = {}

        assert (
            audit._resolve_step_role(PROJECT_ROOT, 'default:verify:verify', cache)
            == 'module-tests'
        )
        assert (
            audit._resolve_step_role(PROJECT_ROOT, 'verify:module-tests', cache)
            == 'module-tests'
        )
        assert (
            audit._resolve_step_role(PROJECT_ROOT, 'default:verify:coverage', cache)
            == 'coverage'
        )

    def test_canonical_verify_alongside_coverage_not_flagged(self):
        # a coverage/integration step alongside a core role does NOT mis-flag:
        # the intersection with {quality-gate, module-tests} is non-empty.
        inputs = _inputs(
            ['default:verify:quality-gate', 'default:verify:coverage']
        )
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is None

    def test_legacy_bare_step_ids_not_flagged(self):
        # archived plans whose manifests predate the parameterized form carry the
        # legacy bare names; they resolve in-code via the back-compat table.
        inputs = _inputs(['quality_check', 'build_verify'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        # quality_check → quality-gate, build_verify → module-tests
        assert drift is None
        assert cache['quality_check'] == 'quality-gate'
        assert cache['build_verify'] == 'module-tests'

    def test_namespaced_legacy_step_ids_resolve_to_roles_and_not_flagged(self):
        # the ``default:``-namespaced legacy shape
        inputs = _inputs(['default:quality_check', 'default:build_verify'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)
        resolved = {
            audit._resolve_step_role(PROJECT_ROOT, s, cache)
            for s in inputs.manifest_phase_5
        }

        # the default: prefix is stripped and roles resolve correctly
        assert drift is None
        assert resolved == {'quality-gate', 'module-tests'}

    def test_unknown_canonical_flagged_as_genuine_drift(self):
        # a parameterized step whose {canonical} segment is not in the table
        inputs = _inputs(['default:verify:bogus-canonical'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is not None
        assert 'unresolvable role' in drift

    def test_unresolvable_role_flagged_as_genuine_drift(self):
        # a bare step name absent from both the canonical and legacy tables
        inputs = _inputs(['not_a_real_step'])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is not None
        assert 'unresolvable role' in drift

    def test_resolution_is_in_code_independent_of_filesystem(self, tmp_path: Path):
        # resolution no longer reads any role-file: a repo_root with no
        # phase-5-execute/standards directory resolves the same as PROJECT_ROOT.
        cache: dict[str, str | None] = {}

        role = audit._resolve_step_role(tmp_path, 'default:verify:quality-gate', cache)

        assert role == 'quality-gate'

    def test_empty_phase_5_returns_no_drift(self):
        inputs = _inputs([])
        cache: dict[str, str | None] = {}

        drift = audit.detect_name_drift(inputs, PROJECT_ROOT, cache)

        assert drift is None
