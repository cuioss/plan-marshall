#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for core's ``.plan/**`` path claim, registered through the Axis-D seam.

Before this claim existed, every ``.plan/`` path answered ``module: null`` — the
tree that holds the executor, ``marshal.json`` and every plan-scoped script was
owned by nothing. ``plan-marshall-plugin`` now declares ``('.plan',
'plan-marshall')`` from ``claim_paths()``, alongside the re-homed
``.claude/skills`` entry, so both claims arrive through ONE mechanism — there is
no second declaration surface and no core-side hardcoded fallback.

Covered:

- ``.plan/execute-script.py`` resolves to ``plan-marshall`` rather than ``null``.
- A deeply nested ``.plan/`` path resolves the same way (the claim is the bare
  root segment, so containment covers the whole subtree).
- The claim does not leak past its prefix: ``.plans/x`` shares the leading
  characters but does not nest inside ``.plan``, so it resolves through no claim.
- A project with no ``plan-marshall`` module still answers ``null`` — the
  module-existence guard.
- The behaviour change at the single ``module: null`` consumer is pinned here
  rather than asserted in prose: a finding whose ``file_path`` is under
  ``.plan/**`` used to fall through ``triage.md``'s null branch to the project's
  primary domain and now resolves to ``plan-marshall``.

See ``extension-api/standards/ext-point-path-attribution.md`` for the contract.
"""

import sys
import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import seed_project  # noqa: E402

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

cmd_which_module = _cmd_client.cmd_which_module
resolve_module_for_path = _architecture_core.resolve_module_for_path
project_local_module_for_path = _architecture_core.project_local_module_for_path

_PLAN_ROOT_SCRIPT = '.plan/execute-script.py'
_PLAN_NESTED_SCRIPT = '.plan/local/plans/some-plan/work/scope-creep.toon'
_PLAN_SIBLING_PATH = '.plans/execute-script.py'


def _seed_plan_marshall_project(tmpdir: str) -> None:
    """Seed a ``plan-marshall`` module with NO root module.

    Omitting the root ``default`` module is deliberate: it removes the length-0
    fallback so an unclaimed path resolves to ``None`` rather than to the root
    module. That is what lets the leak assertions below distinguish "the claim
    did not match" from "the claim matched something else".
    """
    modules = {
        'plan-marshall': {
            'name': 'plan-marshall',
            'paths': {
                'module': 'marketplace/bundles/plan-marshall',
                'sources': ['marketplace/bundles/plan-marshall/skills'],
                'tests': ['test/plan-marshall'],
            },
            'files': {
                'skill': ['marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md'],
            },
        },
    }
    seed_project(tmpdir, modules)


def _seed_project_without_plan_marshall(tmpdir: str) -> None:
    """Seed a consumer-shaped project that has no ``plan-marshall`` module."""
    modules = {
        'app': {
            'name': 'app',
            'paths': {'module': 'app', 'sources': ['app/src'], 'tests': ['app/test']},
            'files': {'source': ['app/src/main.py']},
        },
    }
    seed_project(tmpdir, modules)


# =============================================================================
# The claim resolves — closing the module: null answer
# =============================================================================


def test_which_module_resolves_plan_executor_path_to_plan_marshall():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(Namespace(project_dir=tmpdir, path=_PLAN_ROOT_SCRIPT))

        assert result['status'] == 'success'
        assert result['module'] == 'plan-marshall'


def test_which_module_resolves_a_nested_plan_path_to_plan_marshall():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(Namespace(project_dir=tmpdir, path=_PLAN_NESTED_SCRIPT))

        assert result['status'] == 'success'
        assert result['module'] == 'plan-marshall'


def test_resolve_module_for_path_agrees_on_the_plan_claim():
    """Both path→module surfaces reach rung 3 through the same helper."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        assert resolve_module_for_path(_PLAN_ROOT_SCRIPT, tmpdir) == 'plan-marshall'
        assert resolve_module_for_path(_PLAN_NESTED_SCRIPT, tmpdir) == 'plan-marshall'


def test_triage_consumer_receives_plan_marshall_for_a_plan_scoped_finding():
    """The one consumer that branches on ``module: null`` changes behaviour here.

    ``plan-marshall/workflow/triage.md`` falls back to the project's primary
    domain when ``which-module`` answers null. A finding under ``.plan/**`` now
    resolves to ``plan-marshall`` and routes to that module's domain instead.
    That is the intended correction, and it is pinned by this assertion rather
    than asserted in prose.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(Namespace(project_dir=tmpdir, path='.plan/marshal.json'))

        assert result['module'] is not None
        assert result['module'] == 'plan-marshall'


# =============================================================================
# The claim does not leak past its prefix
# =============================================================================


def test_plan_claim_does_not_match_a_sibling_sharing_the_string_prefix():
    """``.plans/`` shares the leading characters but does not nest inside ``.plan``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(Namespace(project_dir=tmpdir, path=_PLAN_SIBLING_PATH))

        assert result['module'] is None


def test_seam_lookup_rejects_the_sibling_prefix_directly():
    """The nest-inside guard, asserted at the seam rather than through the ladder."""
    assert project_local_module_for_path(_PLAN_SIBLING_PATH, ['plan-marshall']) is None
    assert project_local_module_for_path(_PLAN_ROOT_SCRIPT, ['plan-marshall']) == 'plan-marshall'


# =============================================================================
# Module-existence guard — a consumer project without the module
# =============================================================================


def test_project_without_plan_marshall_module_still_answers_null():
    """A claim naming an absent module is dropped by the merge's known-module filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project_without_plan_marshall(tmpdir)

        result = cmd_which_module(Namespace(project_dir=tmpdir, path=_PLAN_ROOT_SCRIPT))

        assert result['module'] is None


def test_both_shipped_claims_arrive_through_the_same_seam():
    """One mechanism, two claims — no second declaration surface.

    Asserting both entries resolve through ``claim_paths()`` is what would catch a
    regression that re-introduced a core-side hardcoded fallback for either one.
    """
    claims, _reports = _load_shipped_claims()

    prefixes = sorted(claim['prefix'] for claim in claims)
    assert prefixes == ['.claude/skills', '.plan']
    assert {claim['module'] for claim in claims} == {'plan-marshall'}
    assert all(claim['producers'] == ['plan-marshall'] for claim in claims)


def _load_shipped_claims():
    """Merge the live attributor population against a known-module set."""
    discover, merge, _lookup = _architecture_core._load_path_attribution_seam()
    return merge(discover(), ['plan-marshall'])
