#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the shared canonicalize_step_key resolver.

``canonicalize_step_key`` (`script-shared/scripts/_step_key_canonical.py`) is the
single source of truth every step-record write and read routes through
(``mark-step-done`` / ``assert-step-recorded`` / ``record-step`` / every
manifest-bundle boundary-normalization call site). It supersedes both the former
``_cmd_mark_step._canonicalize_step_key`` and ``_manifest_core._strip_default_prefix``
duplicates, so its semantics are pinned here: default-prefix strip, promoted-alias
map, project/bundle preserve, and idempotence (fixed point on canonical input).
"""

# script-shared/scripts is injected onto PYTHONPATH by the test conftest, so the
# shared resolver imports by bare name — the same pattern the build tests use for
# resolve_project_dir.
from _step_key_canonical import PROMOTED_BUILTIN_STEP_IDS, canonicalize_step_key


def test_strips_leading_default_prefix():
    """A leading ``default:`` prefix strips to the bare manifest key."""
    assert canonicalize_step_key('default:push') == 'push'
    assert canonicalize_step_key('default:branch-cleanup') == 'branch-cleanup'
    assert canonicalize_step_key('default:verify:quality-gate') == 'verify:quality-gate'


def test_preserves_bare_names():
    """A bare name (no prefix) is returned unchanged."""
    assert canonicalize_step_key('push') == 'push'
    assert canonicalize_step_key('branch-cleanup') == 'branch-cleanup'


def test_preserves_project_and_bundle_prefixes():
    """``project:`` and genuinely opt-in ``bundle:skill`` ids pass through verbatim."""
    assert canonicalize_step_key('project:finalize-step-plugin-doctor') == (
        'project:finalize-step-plugin-doctor'
    )
    assert canonicalize_step_key('plan-marshall:plan-retrospective') == (
        'plan-marshall:plan-retrospective'
    )


def test_maps_promoted_builtin_alias_to_bare():
    """A promoted built-in-equivalent bundle id maps to its bare built-in name."""
    assert canonicalize_step_key('plan-marshall:automatic-review') == 'automatic-review'


def test_promoted_alias_map_is_the_documented_pair():
    """The alias map carries exactly the promoted automatic-review pair."""
    assert PROMOTED_BUILTIN_STEP_IDS == {'plan-marshall:automatic-review': 'automatic-review'}


def test_promoted_alias_takes_precedence_over_default_strip():
    """The promoted-alias map is consulted before the ``default:`` strip.

    A promoted id has no ``default:`` prefix, so this pins the ORDER: the alias
    map wins, and the result is the bare built-in name, not a default-stripped
    variant of the bundle id.
    """
    assert canonicalize_step_key('plan-marshall:automatic-review') == 'automatic-review'


def test_is_idempotent_fixed_point_on_canonical_input():
    """Applying the resolver twice equals applying it once (fixed point)."""
    for step in (
        'default:push',
        'push',
        'project:finalize-step-plugin-doctor',
        'plan-marshall:plan-retrospective',
        'plan-marshall:automatic-review',
        'verify:module-tests',
    ):
        once = canonicalize_step_key(step)
        assert canonicalize_step_key(once) == once
