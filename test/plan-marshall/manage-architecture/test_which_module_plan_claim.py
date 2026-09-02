#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for core's ``.plan/**`` path claim, registered through the Axis-D seam.

Before this claim existed, every ``.plan/`` path answered ``module: null`` — the
tree that holds the executor, ``marshal.json`` and every plan-scoped script was
owned by nothing. ``plan-marshall-plugin`` declares ``('.plan', 'plan-marshall')``
from ``claim_paths()`` — its SOLE claim — through the ONE Axis-D mechanism, with
no second declaration surface and no core-side hardcoded fallback. The ``.claude``
project-local tree, once carried here as a re-homed ``.claude/skills`` claim, now
belongs to ``pm-plugin-development`` (the domain that understands Claude Code
plugin artifacts); see that bundle's attributor and
``test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py``.

Covered:

- ``.plan/execute-script.py`` resolves to ``plan-marshall`` rather than ``null``.
- A deeply nested ``.plan/`` path resolves the same way (the claim is the bare
  root segment, so containment covers the whole subtree).
- The claim does not leak past its prefix: ``.plans/x`` shares the leading
  characters but does not nest inside ``.plan``, so it resolves through no claim.
- A project with no ``plan-marshall`` module still answers ``null`` — the
  module-existence guard.
- ``plan-marshall`` now ships ONLY the ``.plan`` claim; the ``.claude`` tree moved
  to ``pm-plugin-development``, so ``.claude/skills`` is no longer a
  ``plan-marshall`` claim.
- The behaviour change at the single ``module: null`` consumer is pinned here
  rather than asserted in prose: a finding whose ``file_path`` is under
  ``.plan/**`` used to fall through ``triage.md``'s null branch to the project's
  primary domain and now resolves to ``plan-marshall``.

See ``extension-api/standards/ext-point-path-attribution.md`` for the contract.
"""

import argparse
import copy
import sys
import tempfile
from pathlib import Path
from typing import Any

from conftest import load_script_module, parse_ns

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

#: The architecture script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ARCH_BUNDLE = 'plan-marshall'
_ARCH_SKILL = 'manage-architecture'
_ARCH_SCRIPT = 'architecture.py'


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from the hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: The ``which-module`` namespace, built by ``architecture.py``'s OWN parser so
#: it carries every default the production CLI applies — the ``command``
#: discriminator and the ``plan_id`` half of the ``--plan-id``/``--project-dir``
#: pair among them, neither of which the hand-built namespaces carried. Hoisted
#: to module scope because ``parse_ns`` re-executes the script module on every
#: call, and ``register=False`` because only the namespace is wanted here.
_WHICH_MODULE_ARGS = parse_ns(
    _ARCH_BUNDLE, _ARCH_SKILL, _ARCH_SCRIPT,
    '--project-dir', '.', 'which-module', '--path', '.',
    register=False,
)


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


def _seed_meta_project(tmpdir: str) -> None:
    """Seed a meta-project with BOTH ``plan-marshall`` and ``pm-plugin-development``.

    The root ``default`` module is deliberately omitted (as in
    :func:`_seed_plan_marshall_project`) so an uncovered path resolves to ``None``
    rather than to a length-0 root fallback — that is what lets the ``.github``
    negative-control assertion below distinguish "unclaimed" from "root-owned". Each
    module's paths are ordinary bundle trees, so neither the exact-inventory rung nor
    the sources/tests containment rung can claim a ``.claude/**`` or ``.github/**``
    path; only the Axis-D seam (rung 3) can, which is the whole point for these
    never-inventoried dotfile trees.
    """
    modules = {
        'plan-marshall': {
            'name': 'plan-marshall',
            'paths': {
                'module': 'marketplace/bundles/plan-marshall',
                'sources': ['marketplace/bundles/plan-marshall/skills'],
                'tests': ['test/plan-marshall'],
            },
            'files': {},
        },
        'pm-plugin-development': {
            'name': 'pm-plugin-development',
            'paths': {
                'module': 'marketplace/bundles/pm-plugin-development',
                'sources': ['marketplace/bundles/pm-plugin-development/skills'],
                'tests': ['test/pm-plugin-development'],
            },
            'files': {},
        },
    }
    seed_project(tmpdir, modules)


# =============================================================================
# The claim resolves — closing the module: null answer
# =============================================================================


def test_which_module_resolves_plan_executor_path_to_plan_marshall():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path=_PLAN_ROOT_SCRIPT))

        assert result['status'] == 'success'
        assert result['module'] == 'plan-marshall'


def test_which_module_resolves_a_nested_plan_path_to_plan_marshall():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path=_PLAN_NESTED_SCRIPT))

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

        result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path='.plan/marshal.json'))

        assert result['module'] is not None
        assert result['module'] == 'plan-marshall'


# =============================================================================
# The claim does not leak past its prefix
# =============================================================================


def test_plan_claim_does_not_match_a_sibling_sharing_the_string_prefix():
    """``.plans/`` shares the leading characters but does not nest inside ``.plan``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_plan_marshall_project(tmpdir)

        result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path=_PLAN_SIBLING_PATH))

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

        result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path=_PLAN_ROOT_SCRIPT))

        assert result['module'] is None


# =============================================================================
# The .claude tree resolves to pm-plugin-development through the which-module
# reader — the founding inconsistency, closed end-to-end
# =============================================================================


def test_which_module_resolves_every_claude_subtree_to_pm_plugin_development():
    """skills, commands, AND settings all resolve to the one owner at the reader.

    Before the move, ``.claude/skills`` resolved to a module while its siblings
    ``.claude/commands`` and ``.claude/settings.json`` resolved to ``null`` — one
    tree, two answers. The bare-root ``.claude`` claim now covers all three uniformly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_meta_project(tmpdir)

        for path in (
            '.claude/skills/cloud-plan-lane/SKILL.md',
            '.claude/commands/some-command.md',
            '.claude/settings.json',
        ):
            result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path=path))
            assert result['status'] == 'success'
            assert result['module'] == 'pm-plugin-development', path


def test_which_module_null_on_uncovered_path_carries_attributor_count():
    """D4 at the reader: an unclaimed dotfile path answers ``null`` but names the count.

    ``.github/**`` is never inventoried and no attributor claims it, so the reader
    answers ``module: null`` — but with ``attributor_count > 0``, marking it a real
    "the capability ran and found no owner" answer rather than a coverage gap. That is
    the residue a caller branches on instead of falling back to a whole-tree scan.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_meta_project(tmpdir)

        result = cmd_which_module(_variant(_WHICH_MODULE_ARGS, project_dir=tmpdir, path='.github/workflows/verify.yml'))

        assert result['status'] == 'success'
        assert result['module'] is None
        # Covered, no matches: the attribution capability ran (N attributors), none claimed it.
        assert result['attributor_count'] > 0
        assert 'pm-plugin-development' in result['attributors']


def test_plan_marshall_ships_only_the_plan_claim():
    """``plan-marshall``'s sole claim is ``.plan`` — the ``.claude`` tree has moved.

    Merged against a known-module set of just ``plan-marshall``, the live
    attributor population yields exactly the ``.plan`` claim: ``pm-plugin-development``'s
    ``.claude`` claim is dropped by the module-existence guard (its module is absent
    from the set), and no ``.claude/skills`` entry survives from ``plan-marshall``
    itself. Asserting the claim resolves through ``claim_paths()`` is what would catch
    a regression that re-introduced a core-side hardcoded fallback.
    """
    claims, _reports = _load_shipped_claims(['plan-marshall'])

    prefixes = sorted(claim['prefix'] for claim in claims)
    assert prefixes == ['.plan']
    assert {claim['module'] for claim in claims} == {'plan-marshall'}
    assert all(claim['producers'] == ['plan-marshall'] for claim in claims)
    # The re-homed entry is gone — ``plan-marshall`` no longer owns any ``.claude`` path.
    assert not any(claim['prefix'].startswith('.claude') for claim in claims)


def test_claude_tree_moved_to_pm_plugin_development():
    """The ``.claude`` tree now arrives from ``pm-plugin-development``, not ``plan-marshall``.

    Merged against a set that includes ``pm-plugin-development``, the live population
    yields a single ``.claude`` claim owned by that module and produced by its
    attributor id — the deliberate ownership move, verified through the same one seam.
    """
    claims, _reports = _load_shipped_claims(['plan-marshall', 'pm-plugin-development'])

    claude_claims = [claim for claim in claims if claim['prefix'] == '.claude']
    assert len(claude_claims) == 1
    assert claude_claims[0]['module'] == 'pm-plugin-development'
    assert claude_claims[0]['producers'] == ['pm-plugin-development']
    # ``.plan`` still belongs to ``plan-marshall`` — the move did not disturb it.
    assert {'.plan', '.claude'} <= {claim['prefix'] for claim in claims}


def _load_shipped_claims(module_names):
    """Merge the live attributor population against a known-module set."""
    discover, merge, _lookup = _architecture_core._load_path_attribution_seam()
    return merge(discover(), module_names)
