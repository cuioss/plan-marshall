# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import (
    _APPLICABLE_MODULES,
    _NO_MODULES,
    _config_core_mod,
    _NonApplicablePythonExtension,
    _NoRouteExtension,
    _PythonRouteExtension,
    _RaisingApplicabilityExtension,
    _wire_real_aggregator,
)


def test_aggregate_build_map_collects_route_matching_out_of_scripts_production_py(monkeypatch):
    """The aggregator collects a route matching a production .py OUTSIDE scripts/.

    This is the regression the deliverable fixes: a production file at
    ``marketplace/targets/generate.py`` (not under ``scripts/``) is covered by the
    explicit route ``marketplace/targets/*.py`` — the old static-glob seed
    would have silently missed it.
    """
    # an extension declaring an out-of-scripts production route.
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())

    # run the REAL aggregator.
    aggregated = _config_core_mod.aggregate_build_map()

    # a production-role route in the python domain matches the
    # out-of-scripts file.
    assert 'python' in aggregated
    prod_globs = [entry['glob'] for entry in aggregated['python'] if entry['role'] == 'production']
    import fnmatch

    assert any(fnmatch.fnmatchcase('marketplace/targets/generate.py', g) for g in prod_globs), (
        f'no declared route matched the out-of-scripts production file; globs={prod_globs}'
    )



def test_aggregate_build_map_stamps_each_entry_with_a_build_class(monkeypatch):
    """Each collected (glob, role) route is stamped with its domain's build_class.

    The aggregator's second leg: after the route deriver collects (glob, role),
    the aggregator queries the owning extension's classify_build_class(glob, role)
    and records it. A production route therefore carries the compile build_class,
    not a bare (glob, role) tuple. The build_class NAMES the canonical command
    directly (no name-to-name indirection).
    """
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())

    aggregated = _config_core_mod.aggregate_build_map()

    # every entry carries the three keys and a sensible build_class.
    entries = aggregated['python']
    for entry in entries:
        assert set(entry.keys()) == {'glob', 'role', 'build_class'}
    by_role = {entry['role']: entry['build_class'] for entry in entries}
    assert by_role['production'] == 'compile'
    assert by_role['test'] == 'module-tests'



def test_aggregate_build_map_omits_domain_with_no_routes(monkeypatch):
    """A domain whose extension declares no routes is omitted entirely.

    An extension at the base ``classify_globs()`` default (empty list) contributes
    no entries, so the python domain is dropped from the aggregated map (rather
    than appearing with an empty list). The extension declares itself applicable,
    so the omission is attributable to the empty route set — not the filter.
    """
    # an applicable extension declaring no routes at all.
    _wire_real_aggregator(monkeypatch, _NoRouteExtension())

    aggregated = _config_core_mod.aggregate_build_map()

    # the python domain contributed nothing and is omitted.
    assert 'python' not in aggregated



def test_aggregate_includes_applicable_domain(monkeypatch):
    """A domain applicable for a discovered module keeps its routes.

    The positive control for the applicability filter: with at least one discovered
    module for which applies_to_module() is applicable, the python domain's routes
    survive aggregation unchanged.
    """
    # an applicable extension with one discovered module.
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension(), modules=_APPLICABLE_MODULES)

    aggregated = _config_core_mod.aggregate_build_map()

    # applicable domain's routes are present.
    assert 'python' in aggregated
    by_role = {entry['role']: entry['build_class'] for entry in aggregated['python']}
    assert by_role['production'] == 'compile'
    assert by_role['test'] == 'module-tests'



def test_aggregate_excludes_non_applicable_domain_with_routes(monkeypatch):
    """An installed domain that applies to no discovered module is excluded.

    The core fix: even though the extension declares real routes via
    classify_globs(), its applies_to_module() is not-applicable for every
    discovered module, so its routes are dropped — a python-only project never
    receives routes from a domain that does not apply to its modules.
    """
    # a route-declaring extension that is never applicable.
    _wire_real_aggregator(monkeypatch, _NonApplicablePythonExtension(), modules=_APPLICABLE_MODULES)

    aggregated = _config_core_mod.aggregate_build_map()

    # the non-applicable domain contributed nothing.
    assert 'python' not in aggregated
    assert aggregated == {}



def test_aggregate_empty_when_no_modules_discovered(monkeypatch):
    """An empty discovered-module set yields an empty aggregation.

    With no discovered modules the applicability filter has nothing to match
    against, so the aggregation is empty rather than the unscoped full set — the
    seed runs only after architecture discovery (wizard Step 8b / sync-defaults).
    """
    # an applicable, route-declaring extension but NO discovered modules.
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension(), modules=_NO_MODULES)

    aggregated = _config_core_mod.aggregate_build_map()

    # no modules → empty aggregation regardless of declared routes.
    assert aggregated == {}



def test_aggregate_tolerates_raising_applies_to_module(monkeypatch):
    """A misbehaving applies_to_module() does not crash the seed; its domain drops.

    The defensive try/except around the applies_to_module() call treats a raising
    extension as not-applicable rather than propagating the exception — the seed
    completes and the raising domain is simply omitted.
    """
    # an extension whose applies_to_module() raises, with a discovered module.
    _wire_real_aggregator(monkeypatch, _RaisingApplicabilityExtension(), modules=_APPLICABLE_MODULES)

    # must not raise.
    aggregated = _config_core_mod.aggregate_build_map()

    # the raising domain is dropped; aggregation is empty.
    assert aggregated == {}
