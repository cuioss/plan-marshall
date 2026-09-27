# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_config_build_map_seed_fixtures import (
    Namespace,
    _cmd_build_map_mod,
    _cmd_init_mod,
    _PythonRouteExtension,
    _wire_real_aggregator,
)


def test_read_cli_returns_route_seed(plan_context, monkeypatch):
    """The read CLI returns the route seed, with the out-of-scripts glob intact.

    Seed against an extension declaring an out-of-scripts route, then read back
    through cmd_build_map_read: the merged build_map the read CLI returns must
    carry the python-domain glob that matches the out-of-scripts production .py.
    """
    # init, wire, seed.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # read back through the CLI.
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # read succeeds and surfaces the matching glob.
    assert result['status'] == 'success'
    assert 'python' in result['build_map']
    prod_globs = [e['glob'] for e in result['build_map']['python'] if e['role'] == 'production']

    import fnmatch

    assert any(fnmatch.fnmatchcase('marketplace/targets/generate.py', g) for g in prod_globs), (
        f'read CLI did not return a glob for the out-of-scripts file; globs={prod_globs}'
    )
