#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``manage-solution-outline get-module-context`` (per-module layout).

Pins the D3 reader contract: ``cmd_get_module_context`` reads the per-module
project-architecture layout (top-level ``_project.json`` plus per-module
``derived.json`` / ``enriched.json``) and returns a structured context for
solution-outline placement decisions.

Covers three branches:

* **happy path** — at least two modules with mixed enrichment fields, asserting
  the returned ``modules`` list pins the documented shape (``name``, ``path``,
  ``purpose``, ``responsibility``, plus the optional ``key_packages``,
  ``tips``, ``insights``, ``best_practices``, ``skills_by_profile`` fields).
* **not_found** — ``_project.json`` is absent, so the command returns the
  documented ``not_found`` status with a remediation suggestion.
* **worktree-resolution fallback** — a matched pair (worktree absent vs
  worktree materialized) plus a scope control, driven end-to-end through
  ``main()``, pinning that the reader degrades to the checkout root only when
  the plan's worktree cannot be resolved and always names the checkout it read
  from.
"""

import sys
from argparse import Namespace
from pathlib import Path

import file_ops
import pytest
from toon_parser import parse_toon

from conftest import load_script_module

# =============================================================================
# Module Loading
# =============================================================================

_mod = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    'manage-solution-outline.py',
    module_name='manage_solution_outline',
)

cmd_get_module_context = _mod.cmd_get_module_context

# _architecture_core helpers — used to seed the per-module layout under the
# fixture's project_dir without round-tripping through the discover/init
# commands.
_arch_core = load_script_module(
    'plan-marshall',
    'manage-architecture',
    '_architecture_core.py',
    module_name='_architecture_core_test_module',
)

save_project_meta = _arch_core.save_project_meta
save_module_derived = _arch_core.save_module_derived
save_module_enriched = _arch_core.save_module_enriched


# =============================================================================
# Fixtures
# =============================================================================


def _ns(project_dir: str) -> Namespace:
    """Build the Namespace shape that ``cmd_get_module_context`` expects."""
    return Namespace(project_dir=project_dir)


def _seed_two_module_project(project_dir: Path) -> None:
    """Seed a per-module layout with two modules at ``project_dir``.

    ``core`` carries the full optional-field set (``key_packages``, ``tips``,
    ``insights``, ``best_practices``, ``skills_by_profile``); ``web`` carries
    only the required fields, exercising the optional-field omission path.
    """
    save_project_meta(
        {
            'name': 'multi-module-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'core': {}, 'web': {}},
        },
        str(project_dir),
    )

    save_module_derived(
        'core',
        {
            'name': 'core',
            'paths': {'module': 'core'},
            'packages': [],
        },
        str(project_dir),
    )
    save_module_enriched(
        'core',
        {
            'purpose': 'Domain layer',
            'responsibility': 'Encapsulates business rules and entities',
            'key_packages': {
                'de.cuioss.core.domain': 'Aggregate roots',
                'de.cuioss.core.value': 'Value objects',
            },
            'tips': ['Keep entities free of framework annotations'],
            'insights': ['Repository abstractions live in service layer'],
            'best_practices': ['Prefer immutable value objects over mutable DTOs'],
            'skills_by_profile': {
                'implementation': ['pm-dev-java:java-core'],
                'unit-testing': ['pm-dev-java:junit-core'],
            },
        },
        str(project_dir),
    )

    save_module_derived(
        'web',
        {
            'name': 'web',
            'paths': {'module': 'web'},
            'packages': [],
        },
        str(project_dir),
    )
    save_module_enriched(
        'web',
        {
            'purpose': 'HTTP entry points',
            'responsibility': 'Expose REST endpoints and translate DTOs',
        },
        str(project_dir),
    )


# =============================================================================
# Happy Path
# =============================================================================


def test_get_module_context_returns_per_module_entries(tmp_path):
    """Reader returns a structured context with one entry per module.

    Pins the contract: ``status`` is ``success``, ``module_count`` reflects the
    ``_project.json`` index, and ``modules`` carries one entry per module with
    the documented shape.
    """
    _seed_two_module_project(tmp_path)

    result = cmd_get_module_context(_ns(str(tmp_path)))

    assert result['status'] == 'success'
    assert result['module_count'] == 2
    modules = result['modules']
    assert len(modules) == 2
    # Modules come back in the order ``iter_modules`` yields (sorted by name).
    names = [m['name'] for m in modules]
    assert names == ['core', 'web']


def test_get_module_context_pins_optional_field_shape(tmp_path):
    """The optional fields surface verbatim from the per-module ``enriched.json``.

    ``core`` carries every optional field; the test pins the shape the script
    documents — ``key_packages`` is a list of package names (the dict keys),
    while ``tips``, ``insights``, ``best_practices`` and ``skills_by_profile``
    flow through untouched.
    """
    _seed_two_module_project(tmp_path)

    result = cmd_get_module_context(_ns(str(tmp_path)))

    # required fields
    core = next(m for m in result['modules'] if m['name'] == 'core')
    assert core['path'] == 'core'
    assert core['purpose'] == 'Domain layer'
    assert core['responsibility'] == 'Encapsulates business rules and entities'

    # optional fields are present and carry the documented shape
    assert core['key_packages'] == ['de.cuioss.core.domain', 'de.cuioss.core.value']
    assert core['tips'] == ['Keep entities free of framework annotations']
    assert core['insights'] == ['Repository abstractions live in service layer']
    assert core['best_practices'] == ['Prefer immutable value objects over mutable DTOs']
    assert core['skills_by_profile'] == {
        'implementation': ['pm-dev-java:java-core'],
        'unit-testing': ['pm-dev-java:junit-core'],
    }


def test_get_module_context_omits_optionals_when_enrichment_lacks_them(tmp_path):
    """Modules without optional enrichment fields omit them from the entry.

    ``web`` only declares ``purpose`` and ``responsibility``; the contract
    requires the optional keys to be absent (rather than defaulted to empty
    values) so callers can branch on presence.
    """
    _seed_two_module_project(tmp_path)

    result = cmd_get_module_context(_ns(str(tmp_path)))

    web = next(m for m in result['modules'] if m['name'] == 'web')
    assert web['name'] == 'web'
    assert web['path'] == 'web'
    assert web['purpose'] == 'HTTP entry points'
    assert web['responsibility'] == 'Expose REST endpoints and translate DTOs'
    for optional_key in ('key_packages', 'tips', 'insights', 'best_practices', 'skills_by_profile'):
        assert optional_key not in web, f"web entry should omit '{optional_key}' when absent"


def test_get_module_context_surfaces_best_practices_when_populated(tmp_path):
    """``best_practices`` flows into the entry when the enriched store carries it.

    Pins the D1 contract directly: a module whose ``enriched.json`` declares a
    non-empty ``best_practices`` list surfaces that list verbatim alongside
    ``tips`` and ``insights`` (architecture-enriched hints reach the outline).
    """
    save_project_meta(
        {
            'name': 'hints-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'default': {}},
        },
        str(tmp_path),
    )
    save_module_derived('default', {'name': 'default', 'paths': {'module': '.'}}, str(tmp_path))
    save_module_enriched(
        'default',
        {
            'purpose': 'Root project module',
            'responsibility': 'Cross-cutting project facts',
            'best_practices': [
                'Resolve build commands via architecture, never hard-code ./pw',
                'Route .plan/ access through manage-* scripts',
            ],
        },
        str(tmp_path),
    )

    result = cmd_get_module_context(_ns(str(tmp_path)))

    assert result['status'] == 'success'
    entry = result['modules'][0]
    assert entry['best_practices'] == [
        'Resolve build commands via architecture, never hard-code ./pw',
        'Route .plan/ access through manage-* scripts',
    ]


def test_get_module_context_omits_best_practices_when_empty(tmp_path):
    """An empty ``best_practices`` list is omitted from the entry.

    Parity with the ``tips``/``insights`` truthiness guard: the key is absent
    (not defaulted to ``[]``) so callers branch on presence, leaving the
    required-section contract of consumers unaffected.
    """
    save_project_meta(
        {
            'name': 'empty-hints-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'default': {}},
        },
        str(tmp_path),
    )
    save_module_derived('default', {'name': 'default', 'paths': {'module': '.'}}, str(tmp_path))
    save_module_enriched(
        'default',
        {
            'purpose': 'Root project module',
            'responsibility': 'Cross-cutting project facts',
            'best_practices': [],
        },
        str(tmp_path),
    )

    result = cmd_get_module_context(_ns(str(tmp_path)))

    assert result['status'] == 'success'
    entry = result['modules'][0]
    assert 'best_practices' not in entry


def test_get_module_context_uses_default_path_when_module_lacks_paths(tmp_path):
    """Modules whose derived data lacks ``paths.module`` fall back to ``'.'``.

    The reader documents this fallback explicitly so callers always see a
    non-empty ``path`` field even when discovery wrote a sparse derived shape.
    """
    save_project_meta(
        {
            'name': 'sparse-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'root': {}},
        },
        str(tmp_path),
    )
    # Note: derived.json without ``paths`` key — the reader must still resolve.
    save_module_derived('root', {'name': 'root'}, str(tmp_path))
    save_module_enriched(
        'root',
        {'purpose': 'Project root', 'responsibility': 'Top-level aggregator'},
        str(tmp_path),
    )

    result = cmd_get_module_context(_ns(str(tmp_path)))

    assert result['status'] == 'success'
    root = result['modules'][0]
    assert root['path'] == '.'


def test_get_module_context_omits_modules_absent_from_live_crawl(tmp_path):
    """A module listed in _project.json but absent from the live crawl is omitted.

    Under the on-demand crawl model the reader iterates the live crawl
    result, not _project.json's index. A module that has neither a real
    filesystem presence nor an on-disk derived.json fallback simply does
    not appear in the response — there is no half-written shape to surface.
    """
    # index lists 'orphan' but no derived.json is written for it,
    # and no real module exists at that path.
    save_project_meta(
        {
            'name': 'half-written-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'orphan': {}},
        },
        str(tmp_path),
    )
    save_module_enriched(
        'orphan',
        {'purpose': 'Late arrival', 'responsibility': 'Pending discovery'},
        str(tmp_path),
    )

    result = cmd_get_module_context(_ns(str(tmp_path)))

    # 'orphan' is absent because the live crawl doesn't see it.
    assert result['status'] == 'success'
    assert result['module_count'] == 0


# =============================================================================
# not_found Branch
# =============================================================================


def test_get_module_context_returns_not_found_when_project_meta_absent(tmp_path):
    """Reader returns ``status='not_found'`` when ``_project.json`` is missing.

    The contract: ``not_found`` keys off the existence of ``_project.json``,
    which is the canonical source-of-truth file for "which modules exist".
    The response includes a discover suggestion so callers know how to
    remediate.
    """
    # tmp_path has no .plan/project-architecture/ at all.

    result = cmd_get_module_context(_ns(str(tmp_path)))

    assert result['status'] == 'not_found'
    assert 'message' in result
    assert 'suggestion' in result
    assert 'architecture discover' in result['suggestion']


@pytest.mark.parametrize(
    'project_dir_arg',
    [
        # Default invocation falls back to '.' — but in tests we pass an
        # explicit absent tmp_path subdirectory to keep cwd clean.
        'definitely-missing-subdir',
    ],
)
def test_get_module_context_not_found_message_references_data_dir(tmp_path, project_dir_arg):
    """The ``not_found`` branch surfaces the absent data-directory path.

    Pins the user-facing remediation contract: the ``file`` field reports the
    project-architecture directory the reader looked in, so callers can
    surface the exact path that needs ``architecture discover``.
    """
    # point at a subdirectory that does not exist on disk.
    missing = tmp_path / project_dir_arg

    result = cmd_get_module_context(_ns(str(missing)))

    assert result['status'] == 'not_found'
    # The reader returns the parent of _project.json (i.e., the data dir).
    assert 'project-architecture' in result['file']


# =============================================================================
# Worktree-resolution fallback — matched pair plus scope control
# =============================================================================
#
# ``get-module-context`` is a read-only reader consumed by phase-3-outline,
# which runs BEFORE phase-5-execute materializes a plan's worktree (ADR-002).
# A plan declaring ``use_worktree=true`` therefore has an empty
# ``worktree_path`` at outline time, and the shared two-state resolver raises
# ``WorktreeResolutionError`` for exactly that state. The reader degrades to
# the cwd-relative checkout root and REPORTS the degradation on its payload.
#
# The three arms below are deliberately matched:
#
# * positive — worktree absent  → fallback fires, reads the checkout root
# * negative — worktree present → fallback does NOT fire, reads the worktree
# * scope    — a non-``WorktreeResolutionError`` failure is still fatal
#
# Without the negative arm the fallback could pass by ALWAYS reading the
# checkout root — a different defect wearing the same green. Without the scope
# arm the catch could widen into a blanket suppression of every routing error.


def _run_main(monkeypatch, capsys, argv):
    """Drive ``main()`` with a patched argv and return ``(exit_code, stdout)``."""
    monkeypatch.setattr(sys, 'argv', ['manage-solution-outline', *argv])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    code = exc.value.code if exc.value.code is not None else 0
    return code, capsys.readouterr().out


def _seed_named_modules(project_dir: Path, module_names: list[str]) -> list[str]:
    """Seed a minimal per-module layout and return the seeded population.

    Each module carries only the four required fields so the emitted
    ``modules[]`` table stays uniform. The return value is the population every
    count-bearing assertion below publishes alongside its expected count.
    """
    save_project_meta(
        {
            'name': project_dir.name,
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': dict.fromkeys(module_names, {}),
        },
        str(project_dir),
    )
    for name in module_names:
        save_module_derived(name, {'name': name, 'paths': {'module': name}}, str(project_dir))
        save_module_enriched(
            name,
            {'purpose': f'{name} purpose', 'responsibility': f'{name} responsibility'},
            str(project_dir),
        )
    return module_names


def _stub_get_worktree_path(monkeypatch, *, use_worktree: bool, worktree_path: str) -> None:
    """Stub the single ``get-worktree-path`` shell-out with a TOON payload.

    Stubbing at the subprocess boundary keeps the real resolution logic in
    play: ``_parse_get_worktree_path_output`` and ``PlanContext`` both execute
    for real, so the ``use_worktree=true`` + empty-path state raises the
    genuine ``WorktreeResolutionError`` rather than a hand-made stand-in.
    """
    payload = (
        'status: success\n'
        f'use_worktree: {"true" if use_worktree else "false"}\n'
        f'worktree_path: "{worktree_path}"\n'
    )
    monkeypatch.setattr(file_ops, '_run_get_worktree_path', lambda plan_id: payload)


def test_get_module_context_falls_back_to_checkout_when_worktree_unmaterialized(
    plan_context, monkeypatch, capsys, tmp_path
):
    """Positive arm: an unmaterialized worktree degrades to the checkout root.

    This is the phase-3-outline state — ``use_worktree`` is true but the
    worktree does not exist yet. The command must succeed, return the REAL
    seeded context (an empty payload would make the fallback pass vacuously),
    and name the checkout it read from.
    """
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    population = _seed_named_modules(checkout, ['core', 'web'])
    _stub_get_worktree_path(monkeypatch, use_worktree=True, worktree_path='')
    # pytest's basetemp lives INSIDE this repository, so the real
    # cwd-relative resolver would walk up past the fixture and land on the
    # repository root. Pin the checkout root the reader degrades to, so the
    # arm asserts the degradation target rather than the harness layout.
    monkeypatch.setattr(_mod, 'cwd_checkout_root', lambda: str(checkout))
    monkeypatch.chdir(checkout)

    code, out = _run_main(monkeypatch, capsys, ['get-module-context', '--plan-id', 'so-wt-absent'])

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['worktree_fallback'] is True
    assert 'worktree_path is empty' in data['worktree_fallback_reason']
    assert Path(data['project_dir']).resolve() == checkout.resolve()
    # Count-bearing assertions publish their population: a zero module_count
    # against an empty seed would otherwise read as a pass.
    assert len(population) == 2, f'seeded population must be non-empty: {population}'
    assert data['module_count'] == len(population), (
        f'expected {len(population)} modules from population {population}, got {data["module_count"]}'
    )
    assert sorted(m['name'] for m in data['modules']) == sorted(population)


def test_get_module_context_reads_the_worktree_when_it_is_materialized(
    plan_context, monkeypatch, capsys, tmp_path
):
    """Negative arm: a materialized worktree is read, and no fallback is reported.

    The worktree and the checkout are seeded with DISJOINT module sets, so the
    returned population identifies which tree was actually read — the fallback
    cannot pass here by reading the checkout root.
    """
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    checkout_population = _seed_named_modules(checkout, ['core', 'web'])
    worktree = tmp_path / 'worktree'
    worktree.mkdir()
    population = _seed_named_modules(worktree, ['isolated'])
    _stub_get_worktree_path(monkeypatch, use_worktree=True, worktree_path=str(worktree))
    monkeypatch.chdir(checkout)

    code, out = _run_main(monkeypatch, capsys, ['get-module-context', '--plan-id', 'so-wt-present'])

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['worktree_fallback'] is False
    assert 'worktree_fallback_reason' not in data
    assert Path(data['project_dir']).resolve() == worktree.resolve()
    # Both populations are published so the disjointness that makes this arm
    # discriminating is visible in the failure message.
    assert set(population).isdisjoint(checkout_population), (
        f'arms must be disjoint: worktree={population}, checkout={checkout_population}'
    )
    assert data['module_count'] == len(population), (
        f'expected {len(population)} modules from worktree population {population} '
        f'(checkout population {checkout_population}), got {data["module_count"]}'
    )
    assert sorted(m['name'] for m in data['modules']) == sorted(population)


def test_get_module_context_non_resolution_failure_stays_fatal(
    plan_context, monkeypatch, capsys, tmp_path
):
    """Scope arm: the fallback catches ONLY worktree-resolution failures.

    With the fallback armed (the stubbed plan has no materialized worktree),
    supplying both routing flags must still exit 2 — the degradation must not
    widen into a blanket suppression of every routing error.
    """
    _stub_get_worktree_path(monkeypatch, use_worktree=True, worktree_path='')

    code, out = _run_main(
        monkeypatch,
        capsys,
        ['get-module-context', '--plan-id', 'so-wt-scope', '--project-dir', str(tmp_path)],
    )

    assert code == 2
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert data['error'] == 'mutually_exclusive_args'
