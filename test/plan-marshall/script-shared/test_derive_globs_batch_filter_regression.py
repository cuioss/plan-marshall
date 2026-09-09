#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Batch-filter-equivalence regression for ``derive_globs_from_tree``.

Locks the ``fnmatch.filter`` batch route-prune refactor to the exact semantics
of the removed per-element ``any(route_matches(p, route[0]) for p in tracked)``
loop, exercised END-TO-END through ``derive_globs_from_tree`` against a real
git-tracked fixture tree that drives BOTH glob regimes simultaneously:

- a **bare-basename** route (no ``/`` — matched on basename anywhere in the
  tree) whose only matching file lives in a subdirectory; and
- a **path-bearing** route (single ``*`` spanning a directory segment) matched
  against the whole repo-relative path.

The per-element oracle ``_loop_matches_any`` re-derives the prune verdict the
old loop produced; the assertions require ``derive_globs_from_tree`` to keep
every route the oracle keeps and prune every route the oracle prunes, so a
future change to either regime cannot silently regress the batch matcher.

This is a dedicated cross-cutting regression module — distinct from the focused
``_pattern_matches_any`` unit equivalence tests in ``test_extension_base.py`` —
asserting the equivalence at the deriver's public surface rather than at the
helper.
"""

import subprocess
from pathlib import Path

import pytest
from extension_base import (
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    BuildExtensionBase,
    derive_globs_from_tree,
    route_matches,
)


def _git_init_and_track(root: Path, rel_paths: list[str]) -> None:
    """Create + git-add each repo-relative path under ``root`` as a tracked file."""
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'T'], check=True)
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)


def _loop_matches_any(pattern: str, tracked: list[str]) -> bool:
    """Reference oracle — the removed per-element loop the batch prune replaced."""
    return any(route_matches(p, pattern) for p in tracked)


class _DualRegimeExtension(BuildExtensionBase):
    """Declares one bare-basename route and one path-bearing route under one domain.

    - ``package.json`` (bare-basename) — survives only because a tracked
      ``package.json`` exists, matched by basename, even though it lives only
      in a subdirectory.
    - ``marketplace/*.py`` (path-bearing, single ``*`` spanning ``/``) — matches
      a file several segments deep on the full repo-relative path.
    - ``vendor/*.py`` (path-bearing) — a deliberately DEAD route: no ``vendor/``
      file is tracked, so it must be pruned, exercising the prune side of the
      equivalence.
    """

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'dual', 'name': 'Dual', 'description': 'Test only'},
                'profiles': {},
            }
        ]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('package.json', ROLE_CONFIG),
            ('marketplace/*.py', ROLE_PRODUCTION),
            ('vendor/*.py', ROLE_PRODUCTION),
        ]


# Fixture tree exercising both regimes at once: a subdir-only config file
# (bare-basename match) and a deeply-nested production file (path-bearing,
# single-star-spans-slash match), plus files that match no route.
_FIXTURE_TREE: list[str] = [
    'nifi-cuioss-ui/package.json',  # bare-basename match (subdir only)
    'marketplace/targets/generate.py',  # path-bearing, * spans /
    'README.md',  # matches nothing
]


def test_derive_globs_keeps_live_routes_across_both_regimes(tmp_path):
    """Both a subdir-only bare-basename route and a deep path-bearing route survive."""
    _git_init_and_track(tmp_path, _FIXTURE_TREE)

    derived = derive_globs_from_tree(str(tmp_path), [_DualRegimeExtension()])

    # The live routes — and ONLY the live routes — are retained, sorted.
    assert derived['dual'] == [
        ('marketplace/*.py', 'production'),
        ('package.json', 'config'),
    ]


#: ``(tracked corpus, route, whether the route survives the prune)`` — one row
#: per glob regime, each driven against the corpus that isolates it:
#:
#: * the dead path-bearing route, pruned because no ``vendor/`` file is tracked;
#: * the bare-basename route, retained on a basename match several segments deep,
#:   which a full-path-only matcher would prune as dead;
#: * the path-bearing route, retained because its single ``*`` spans the
#:   ``targets/`` segment under fnmatch semantics.
_ROUTE_SURVIVAL_CASES = [
    (_FIXTURE_TREE, ('vendor/*.py', 'production'), False),
    (['nifi-cuioss-ui/package.json'], ('package.json', 'config'), True),
    (['marketplace/targets/generate.py'], ('marketplace/*.py', 'production'), True),
]

_ROUTE_SURVIVAL_IDS = [
    'dead-path-bearing-route-is-pruned',
    'bare-basename-route-matches-a-subdir-only-file',
    'path-bearing-single-star-spans-a-slash',
]


@pytest.mark.parametrize('tracked,route,survives', _ROUTE_SURVIVAL_CASES, ids=_ROUTE_SURVIVAL_IDS)
def test_derive_globs_route_survival(tmp_path, tracked, route, survives):
    _git_init_and_track(tmp_path, tracked)

    derived = derive_globs_from_tree(str(tmp_path), [_DualRegimeExtension()])

    assert (route in derived['dual']) is survives, derived['dual']


def test_derive_globs_prune_matches_per_element_oracle(tmp_path):
    """The deriver's per-route prune verdict equals the removed per-element loop.

    The single load-bearing regression: for the exact fixture corpus, every
    route ``derive_globs_from_tree`` keeps is a route the per-element oracle
    keeps, and every route it prunes is one the oracle prunes — bit-for-bit,
    across both glob regimes simultaneously.
    """
    _git_init_and_track(tmp_path, _FIXTURE_TREE)
    declared = _DualRegimeExtension().classify_globs()

    derived = derive_globs_from_tree(str(tmp_path), [_DualRegimeExtension()])
    kept = set(derived.get('dual', []))

    # Independently recompute the oracle verdict against the same tracked corpus.
    expected_kept = {(pattern, role) for pattern, role in declared if _loop_matches_any(pattern, _FIXTURE_TREE)}

    assert kept == expected_kept, (
        f'deriver prune verdict diverged from per-element oracle: kept={sorted(kept)} expected={sorted(expected_kept)}'
    )
