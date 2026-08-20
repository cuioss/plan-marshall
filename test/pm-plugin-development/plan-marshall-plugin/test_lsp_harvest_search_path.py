#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The harvest's search path, and the targets it must refuse.

Two defects that pull in opposite directions and therefore have to be fixed
together:

* a server rooted at the project root cannot follow a bare import satisfied at
  runtime by a launcher's ``sys.path``, so **nothing** cross-component resolves
  and the harvest reports a measured zero;
* the skip list was applied only to the files the harvest QUERIES, never to what
  a definition resolves **to**, so a third-party target reached the lift and
  counted against ``unattributable-endpoint`` — a figure that moves with which
  interpreter the server resolved against.

Widening the search path makes the second worse, which is why the exclusion
lands with it rather than after it. The whole group runs against a fake server
subprocess, so it needs no language server on ``PATH`` and its verdicts are
deterministic rather than dependent on what a real server happened to index.
"""

import json
import shutil
import sys

import pytest
from lsp_harvest import (
    VENDORED_TREE_DIRS,
    ambiguous_module_names,
    bare_import_roots,
    harvest_workspace,
    lift_to_modules,
    make_prefix_attributor,
)

from conftest import PROJECT_ROOT

PYTHON = sys.executable

_FAKE_SERVER = r'''
import json, sys

CONFIG = json.loads(open(sys.argv[1]).read())
RECORD = sys.argv[2]


def read_message():
    header = b""
    while b"\r\n\r\n" not in header:
        c = sys.stdin.buffer.read(1)
        if not c:
            return None
        header += c
    length = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    if length <= 0:
        return {}
    return json.loads(sys.stdin.buffer.read(length))


def write_frame(obj):
    body = json.dumps(obj).encode()
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    sys.stdout.buffer.flush()


while True:
    message = read_message()
    if message is None:
        break
    method = message.get("method")
    if method == "initialize":
        with open(RECORD, "w") as handle:
            handle.write(json.dumps(message.get("params") or {}))
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": {"capabilities": {}}})
    elif method == "textDocument/definition":
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": CONFIG.get("definition")})
    elif method == "shutdown":
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": None})
    elif method == "exit":
        break
    elif "id" in message:
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": None})
'''


def _workspace(tmp_path):
    """The harvested root — a SUBDIRECTORY, so the fake server is not inside it.

    The fake server is itself a ``.py`` file containing imports. Written into the
    root under test it becomes a candidate file and contributes references of its
    own, which is a fixture reaching the state by a different route than the one
    the test names.
    """
    root = tmp_path / 'workspace'
    root.mkdir()
    return root


def _fake_server(home, definition=None):
    """Write a fake server answering every definition with ``definition``.

    Returns ``(server_cmd, record_path)``; ``record_path`` receives the
    ``initialize`` params, which is how the settings the harvest SENDS are
    asserted rather than inferred from what a server did with them.
    """
    home.mkdir(parents=True, exist_ok=True)
    script = home / 'fake_definition_server.py'
    script.write_text(_FAKE_SERVER, encoding='utf-8')
    config = home / 'fake_definition_config.json'
    config.write_text(json.dumps({'definition': definition}), encoding='utf-8')
    record = home / 'initialize_params.json'
    return [PYTHON, str(script), str(config), str(record)], record


def _uri(path):
    return 'file://' + str(path)


# =============================================================================
# The search path the harvest derives and sends
# =============================================================================


def test_bare_import_roots_are_the_directories_that_are_not_packages(tmp_path):
    """A directory with no __init__.py can only be imported from by being on the path."""
    package = tmp_path / 'pkg'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'inside.py').write_text('', encoding='utf-8')
    loose = tmp_path / 'scripts'
    loose.mkdir()
    (loose / 'tool.py').write_text('', encoding='utf-8')

    roots = bare_import_roots([package / 'inside.py', loose / 'tool.py'], tmp_path)

    assert str(loose) in roots
    assert str(package) not in roots


def test_the_harvest_sends_its_derived_search_path_to_the_server(tmp_path):
    """Pins the settings SENT, so the plumbing is checked without a real server."""
    root = _workspace(tmp_path)
    scripts = root / 'component_a' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'caller.py').write_text('import sibling\n', encoding='utf-8')
    (scripts / 'sibling.py').write_text('VALUE = 1\n', encoding='utf-8')
    server_cmd, record = _fake_server(tmp_path / 'server')

    outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

    assert outcome.ran is True
    params = json.loads(record.read_text(encoding='utf-8'))
    extra_paths = params['initializationOptions']['python']['analysis']['extraPaths']
    assert str(scripts) in extra_paths


def test_a_package_directory_is_not_offered_as_a_search_path(tmp_path):
    """Adding a package's own directory would make its modules importable twice."""
    root = _workspace(tmp_path)
    package = root / 'pkg'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'inside.py').write_text('import os\n', encoding='utf-8')
    server_cmd, record = _fake_server(tmp_path / 'server')

    harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

    params = json.loads(record.read_text(encoding='utf-8'))
    assert str(package) not in params['initializationOptions']['python']['analysis']['extraPaths']


def test_ambiguous_module_names_are_the_ones_two_search_paths_supply(tmp_path):
    first = tmp_path / 'one'
    second = tmp_path / 'two'
    for directory in (first, second):
        directory.mkdir()
        (directory / 'extension.py').write_text('', encoding='utf-8')
    (first / 'unique.py').write_text('', encoding='utf-8')

    assert ambiguous_module_names([str(first), str(second)]) == {'extension'}


def test_a_reference_to_an_ambiguous_module_name_is_dropped_and_counted(tmp_path):
    """No search-path order makes the attribution right, so it is not guessed."""
    root = _workspace(tmp_path)
    first = root / 'one'
    second = root / 'two'
    for directory in (first, second):
        directory.mkdir()
        (directory / 'extension.py').write_text('VALUE = 1\n', encoding='utf-8')
    (first / 'caller.py').write_text('import extension\n', encoding='utf-8')
    server_cmd, _record = _fake_server(tmp_path / 'server', definition={'uri': _uri(second / 'extension.py'), 'range': {}})

    outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

    assert outcome.ran is True
    assert outcome.references == []
    assert any(note.startswith('ambiguous-module-name:') for note in outcome.notes)


# =============================================================================
# Vendored trees are refused as targets, not only as sources
# =============================================================================


def test_a_definition_resolving_into_a_venv_produces_no_reference(tmp_path):
    """The tree is skipped for the files QUERIED; it must be skipped for targets too."""
    root = _workspace(tmp_path)
    vendored = root / '.venv' / 'lib' / 'python3.12' / 'site-packages' / 'pkg'
    vendored.mkdir(parents=True)
    (vendored / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    source = root / 'component_a'
    source.mkdir()
    (source / 'caller.py').write_text('import pkg\n', encoding='utf-8')
    server_cmd, _record = _fake_server(tmp_path / 'server', definition={'uri': _uri(vendored / '__init__.py'), 'range': {}})

    outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

    assert outcome.ran is True
    assert all('.venv' not in target for _source, target in outcome.references)
    assert outcome.references == []


def test_a_vendored_target_is_counted_apart_from_an_out_of_workspace_one(tmp_path):
    """Both mean "no module owns this", but only one moves with the interpreter."""
    root = _workspace(tmp_path)
    vendored = root / '.venv' / 'lib' / 'python3.12' / 'site-packages' / 'pkg'
    vendored.mkdir(parents=True)
    (vendored / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    source = root / 'component_a'
    source.mkdir()
    (source / 'caller.py').write_text('import pkg\n', encoding='utf-8')
    server_cmd, _record = _fake_server(tmp_path / 'server', definition={'uri': _uri(vendored / '__init__.py'), 'range': {}})

    outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

    vendor_notes = [note for note in outcome.notes if note.startswith('vendor-tree:')]
    assert vendor_notes, f'no vendor-tree note; notes={outcome.notes}'
    assert not any(note.startswith('out-of-workspace:') for note in outcome.notes)


def test_the_skip_set_is_one_constant_used_for_sources_and_targets():
    """Two lists would drift; the source-side list had already missed .pyprojectx."""
    assert {'.venv', 'node_modules', '.pyprojectx', 'site-packages'} <= VENDORED_TREE_DIRS


def test_a_vendored_target_is_never_attributed_to_a_root_scoped_module():
    """make_prefix_attributor's root-scoped fallback would claim it with NO note.

    ``paths.module`` of ``'.'`` is a value the Python discoverer really emits, so
    a root-scoped module in the table owns whatever nothing else claims —
    including a site-packages file — producing a silent wrong edge. The harvest
    drops such a target before the lift can be asked, so no reference carrying one
    ever reaches this function.
    """
    module_paths = {'alpha': 'alpha', 'rootmod': '.'}
    attribute = make_prefix_attributor(module_paths)

    # The attributor WOULD claim it — this is the reachable defect, pinned so a
    # later narrowing of the fallback does not silently retire the harvest-side
    # exclusion that actually prevents it.
    assert attribute('.venv/lib/python3.12/site-packages/pkg/__init__.py') == 'rootmod'

    edges, _notes = lift_to_modules(
        [('alpha/x.py', '.venv/lib/python3.12/site-packages/pkg/__init__.py')],
        attribute,
        list(module_paths),
    )
    assert edges == [('alpha', 'rootmod')]  # ...which is why the harvest never asks


def test_the_harvest_never_hands_the_lift_a_vendored_target(tmp_path):
    """The end-to-end statement of the rule above, through the real harvest."""
    root = _workspace(tmp_path)
    vendored = root / '.venv' / 'lib' / 'python3.12' / 'site-packages' / 'pkg'
    vendored.mkdir(parents=True)
    (vendored / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    source = root / 'alpha'
    source.mkdir()
    (source / 'caller.py').write_text('import pkg\n', encoding='utf-8')
    server_cmd, _record = _fake_server(tmp_path / 'server', definition={'uri': _uri(vendored / '__init__.py'), 'range': {}})

    outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)
    attribute = make_prefix_attributor({'alpha': 'alpha', 'rootmod': '.'})
    edges, _notes = lift_to_modules(outcome.references, attribute, ['alpha', 'rootmod'])

    assert edges == []


def test_a_workspace_reference_still_produces_one(tmp_path):
    """The control: the exclusions must not have made the harvest derive nothing."""
    root = _workspace(tmp_path)
    first = root / 'alpha'
    second = root / 'beta'
    for directory in (first, second):
        directory.mkdir()
    (second / 'helper.py').write_text('VALUE = 1\n', encoding='utf-8')
    (first / 'caller.py').write_text('import helper\n', encoding='utf-8')
    server_cmd, _record = _fake_server(tmp_path / 'server', definition={'uri': _uri(second / 'helper.py'), 'range': {}})

    outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

    assert outcome.references == [('alpha/caller.py', 'beta/helper.py')]
    attribute = make_prefix_attributor({'alpha': 'alpha', 'beta': 'beta'})
    edges, _notes = lift_to_modules(outcome.references, attribute, ['alpha', 'beta'])
    assert edges == [('alpha', 'beta')]


def test_every_vendored_component_is_excluded_as_a_target(tmp_path):
    """Quantified over the live constant, not over a hand-listed few."""
    root = _workspace(tmp_path)
    source = root / 'alpha'
    source.mkdir()
    (source / 'caller.py').write_text('import pkg\n', encoding='utf-8')

    for component in sorted(VENDORED_TREE_DIRS):
        target_dir = root / component / 'pkg'
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / 'mod.py'
        target.write_text('VALUE = 1\n', encoding='utf-8')
        server_cmd, _record = _fake_server(tmp_path / 'server', definition={'uri': _uri(target), 'range': {}})

        outcome = harvest_workspace(root, server_cmd=server_cmd, timeout_s=20.0, request_timeout_s=5.0)

        assert outcome.references == [], f'{component} was admitted as a target'


# =============================================================================
# The named cross-bundle edge, over the repository's OWN source files
# =============================================================================

# The importing file and the module it imports, at their real repo-relative
# paths. `pm-dev-python/…/extension.py` opens with
# `from extension_base import DerivationResolverBase, ExtensionBase` — a bare
# import satisfied at runtime by the generated executor's sys.path, and the exact
# probe that resolved to nothing before the search path was supplied.
_IMPORTER = 'marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py'
_IMPORTED = 'marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py'

_PYRIGHT = shutil.which('pyright-langserver')


@pytest.mark.skipif(_PYRIGHT is None, reason='pyright-langserver not installed')
def test_a_real_cross_bundle_import_becomes_a_named_module_edge(tmp_path):
    """`pm-dev-python -> plan-marshall`, derived from this repository's own files.

    Not a synthetic fixture edge: both files are copied verbatim from the tree at
    their real repo-relative paths, so the import statement, the module names and
    the resulting edge are all the repository's own. The subtree is narrowed only
    so the test costs seconds instead of the whole-tree harvest's minutes — the
    property under test is that a bare cross-bundle import resolves at all, which
    one such pair exhibits exactly as the full tree does.
    """
    for relative in (_IMPORTER, _IMPORTED):
        source = PROJECT_ROOT / relative
        assert source.exists(), f'{relative} moved; re-derive it before trusting this test'
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    outcome = harvest_workspace(
        tmp_path, server_cmd=[_PYRIGHT, '--stdio'], timeout_s=180.0, request_timeout_s=30.0
    )

    assert outcome.ran is True, outcome.reason
    assert (_IMPORTER, _IMPORTED) in outcome.references, (
        f'the bare cross-bundle import did not resolve; references={outcome.references}, notes={outcome.notes}'
    )

    module_paths = {
        'pm-dev-python': 'marketplace/bundles/pm-dev-python',
        'plan-marshall': 'marketplace/bundles/plan-marshall',
    }
    edges, _notes = lift_to_modules(
        outcome.references, make_prefix_attributor(module_paths), list(module_paths)
    )
    assert ('pm-dev-python', 'plan-marshall') in edges
