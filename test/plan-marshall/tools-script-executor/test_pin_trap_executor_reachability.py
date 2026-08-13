# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the executor reachability defects in the plugin-pin-trap plan (D5).

Three coupled defects in ``generate_executor.py``:

* the generation fallback wrapped discovery in ``except Exception`` but discovery
  signals "inventory not found" via ``sys.exit(2)`` (a ``SystemExit``, which is a
  ``BaseException``, NOT an ``Exception``), so the glob fallback never ran for the
  failure it exists to cover;
* the glob fallback dropped any script whose name merely CONTAINS ``test`` as a
  bare substring, which also strips legitimate entrypoints like ``latest.py``;
* the two land TOGETHER — the discovery gap is invisible until the SystemExit is
  caught, and catching it alone activates a path that silently drops scripts;
* executor validation interpolated a filesystem path into ``python3 -c`` source,
  which a path containing a quote or backslash breaks.

Each test is written to FAIL against the pre-fix code and pass against the fix.
"""

import types
from pathlib import Path

from conftest import load_script_module

_gen = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_pin_trap')


# ---------------------------------------------------------------------------
# Defect 2 + D7(f): the glob fallback keeps a ``latest.py`` and drops real tests.
# ---------------------------------------------------------------------------
def _make_scripts(tmp_path: Path, names: list[str]) -> Path:
    base = tmp_path / 'bundles'
    scripts = base / 'demo-bundle' / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    for name in names:
        (scripts / name).write_text('# script\n', encoding='utf-8')
    return base


def test_glob_fallback_keeps_latest_and_other_test_substring_names(tmp_path):
    base = _make_scripts(tmp_path, ['latest.py', 'attestation.py', 'contest.py', 'real.py'])
    mappings = _gen.discover_scripts_fallback(base)
    stems = {notation.split(':')[2] for notation in mappings}
    assert 'latest' in stems, 'latest.py must not be dropped by a bare `test` substring match'
    assert {'attestation', 'contest', 'real'} <= stems


def test_glob_fallback_still_drops_real_test_files_and_private_modules(tmp_path):
    base = _make_scripts(tmp_path, ['test_foo.py', 'foo_test.py', '_private.py', 'keep.py'])
    mappings = _gen.discover_scripts_fallback(base)
    stems = {notation.split(':')[2] for notation in mappings}
    assert 'keep' in stems
    assert 'test_foo' not in stems
    assert 'foo_test' not in stems
    assert '_private' not in stems


# ---------------------------------------------------------------------------
# Defect 1 (coupled with 2): SystemExit from discovery reaches the glob fallback.
# ---------------------------------------------------------------------------
def test_cmd_generate_catches_systemexit_and_falls_back_to_glob(tmp_path, monkeypatch):
    calls: dict[str, object] = {}

    def _raise_systemexit(_base_path):
        # This is exactly how discover_scripts signals "inventory not found".
        raise SystemExit(2)

    def _fallback(_base_path):
        calls['fallback_used'] = True
        return {'sentinel:demo:x': '/p/x.py'}

    def _fake_generate(mappings, _base_path, dry_run=False, target=None):
        calls['mappings'] = mappings
        return {'status': 'success', 'surface_stats': {}}

    monkeypatch.setattr(_gen, 'get_base_path', lambda use_marketplace=False, marketplace_root=None: tmp_path)
    monkeypatch.setattr(_gen, 'discover_scripts', _raise_systemexit)
    monkeypatch.setattr(_gen, 'discover_scripts_fallback', _fallback)
    monkeypatch.setattr(_gen, 'discover_local_scripts', lambda: {})
    monkeypatch.setattr(_gen, 'generate_executor', _fake_generate)

    args = types.SimpleNamespace(marketplace=False, marketplace_root=None, target='claude', dry_run=True)
    result = _gen.cmd_generate(args)

    assert result.get('status') == 'success'
    assert calls.get('fallback_used') is True, 'SystemExit from discovery must reach the glob fallback'
    assert 'sentinel:demo:x' in calls.get('mappings', {})


# ---------------------------------------------------------------------------
# Defect 3: a filesystem path is passed via argv, not interpolated into -c source.
# ---------------------------------------------------------------------------
def test_get_executor_mappings_survives_quote_in_executor_path(tmp_path, monkeypatch):
    # A checkout path containing a single quote would break a `python3 -c`
    # program that interpolated the path into its source string.
    weird_dir = tmp_path / "we'ird\\dir"
    weird_dir.mkdir(parents=True)
    executor = weird_dir / 'execute-script.py'
    executor.write_text('SCRIPTS = {"a:b:c": "/some/path.py"}\n', encoding='utf-8')

    monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
    mappings = _gen.get_executor_mappings()
    assert mappings == {'a:b:c': '/some/path.py'}


def test_verify_executor_survives_quote_in_executor_path(tmp_path, monkeypatch):
    weird_dir = tmp_path / "od'd\\path"
    weird_dir.mkdir(parents=True)
    executor = weird_dir / 'execute-script.py'
    executor.write_text('SCRIPTS = {"a:b:c": "/x.py", "d:e:f": "/y.py"}\n', encoding='utf-8')

    # Point the logging-module verification at a real plan_logging.py so the
    # second probe subprocess succeeds; the executor path is the quote-carrying one.
    logging_scripts = (
        Path(__file__).parent.parent.parent.parent
        / 'marketplace/bundles/plan-marshall/skills/manage-logging/scripts'
    )
    shared_dirs = [
        Path(__file__).parent.parent.parent.parent / 'marketplace/bundles/plan-marshall/skills' / rel
        for rel in (
            'tools-file-ops/scripts',
            'tools-input-validation/scripts',
            'ref-toon-format/scripts',
            'script-shared/scripts',
            'manage-change-ledger/scripts',
        )
    ]

    monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
    monkeypatch.setattr(_gen, 'get_logging_scripts_dir', lambda base_path: logging_scripts)
    monkeypatch.setattr(_gen, 'get_shared_module_dirs', lambda base_path: shared_dirs)

    is_valid, count = _gen.verify_executor(base_path=tmp_path)
    assert is_valid is True
    assert count == 2
