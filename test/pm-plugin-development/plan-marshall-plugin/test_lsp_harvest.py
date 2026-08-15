#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the discovery-time language-server harvest engine.

Two groups carry the weight:

- **The lift (D2)** is verified by its DROP case, not its happy case. A test that
  only exercises attributable references passes just as well against an
  implementation that guesses an owner, and a confidently-labelled wrong edge is
  worse than a missing one.
- **The lifecycle (D3)** gets one negative control per failure mode. Each must
  produce ``ran=False`` with a DISTINCT stated reason; none may yield a zero-edge
  success.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from lsp_harvest import (
    DEP_TYPE_LSP,
    HarvestOutcome,
    build_lsp_component_refs,
    harvest_workspace,
    import_positions,
    lift_to_modules,
    make_prefix_attributor,
)

# A binary that exists and is executable, used where the test needs the server to
# start (or to hang) rather than to be missing.
PYTHON = sys.executable


def _attributor(table):
    """Build an exact-match attributor from a {path: module} dict."""
    return lambda path: table.get(path)


# =============================================================================
# The file-to-module lift (D2)
# =============================================================================


def test_lift_produces_edge_for_attributable_endpoints():
    """Both endpoints owned by known modules yields one module edge."""
    # Arrange
    attribute = _attributor({'a/x.py': 'alpha', 'b/y.py': 'beta'})

    # Act
    edges, notes = lift_to_modules([('a/x.py', 'b/y.py')], attribute, ['alpha', 'beta'])

    # Assert
    assert edges == [('alpha', 'beta')]
    assert notes == []


def test_unattributable_endpoint_produces_note_and_no_edge():
    """The drop case: no module owns the target, so NO edge is invented.

    This is the assertion the deliverable turns on. An implementation that fell
    back to a directory guess, or to the source module, would pass every
    happy-path test and fail exactly here.
    """
    # Arrange — 'vendor/z.py' is owned by nothing.
    attribute = _attributor({'a/x.py': 'alpha'})

    # Act
    edges, notes = lift_to_modules([('a/x.py', 'vendor/z.py')], attribute, ['alpha'])

    # Assert
    assert edges == []
    assert len(notes) == 1
    assert notes[0].startswith('unattributable-endpoint:')
    assert 'vendor/z.py' in notes[0]


def test_unattributable_source_endpoint_produces_note_and_no_edge():
    """The drop rule binds on the SOURCE endpoint too, not only the target."""
    # Arrange
    attribute = _attributor({'b/y.py': 'beta'})

    # Act
    edges, notes = lift_to_modules([('vendor/z.py', 'b/y.py')], attribute, ['beta'])

    # Assert
    assert edges == []
    assert notes[0].startswith('unattributable-endpoint:')
    assert 'vendor/z.py' in notes[0]


def test_attributed_name_outside_known_modules_produces_note_and_no_edge():
    """A resolver cannot invent a node: an unknown module name is dropped."""
    # Arrange — the seam attributes the path, but no such module was discovered.
    attribute = _attributor({'a/x.py': 'alpha', 'b/y.py': 'ghost'})

    # Act
    edges, notes = lift_to_modules([('a/x.py', 'b/y.py')], attribute, ['alpha'])

    # Assert
    assert edges == []
    assert notes[0].startswith('unknown-endpoint:')


def test_self_edge_is_dropped_and_reported():
    """Two files in one module are not a dependency of that module on itself."""
    # Arrange
    attribute = _attributor({'a/x.py': 'alpha', 'a/y.py': 'alpha'})

    # Act
    edges, notes = lift_to_modules([('a/x.py', 'a/y.py')], attribute, ['alpha'])

    # Assert
    assert edges == []
    assert notes[0].startswith('self-edge:')


def test_lift_deduplicates_many_file_references_into_one_module_edge():
    """Module granularity: many file references collapse to a single edge."""
    # Arrange
    attribute = _attributor({'a/x.py': 'alpha', 'a/z.py': 'alpha', 'b/y.py': 'beta'})
    refs = [('a/x.py', 'b/y.py'), ('a/z.py', 'b/y.py')]

    # Act
    edges, _notes = lift_to_modules(refs, attribute, ['alpha', 'beta'])

    # Assert
    assert edges == [('alpha', 'beta')]


def test_suppression_notes_are_aggregated_with_a_count():
    """Aggregation keeps a large workspace's report readable."""
    # Arrange
    attribute = _attributor({'a/x.py': 'alpha'})
    refs = [('a/x.py', f'vendor/{index}.py') for index in range(10)]

    # Act
    _edges, notes = lift_to_modules(refs, attribute, ['alpha'])

    # Assert
    assert len(notes) == 1
    assert '10 suppressed' in notes[0]


# =============================================================================
# Path attribution
# =============================================================================


def test_prefix_attributor_prefers_the_longest_prefix():
    """A nested module owns its own files, not the enclosing module.

    Shortest- or arbitrary-match would attribute the nested module's files to its
    parent and derive a confidently wrong edge.
    """
    # Arrange — {module_name: module_path}: 'a' owns outer/, 'b' owns outer/inner/.
    attribute = make_prefix_attributor({'a': 'outer', 'b': 'outer/inner'})

    # Act / Assert
    assert attribute('outer/inner/file.py') == 'b'
    assert attribute('outer/file.py') == 'a'


def test_prefix_attributor_matches_whole_segments_only():
    """A shared string prefix is not containment: 'doc' must not claim 'docs/x'."""
    # Arrange — module 'a' owns the doc/ directory.
    attribute = make_prefix_attributor({'a': 'doc'})

    # Act / Assert
    assert attribute('docs/x.py') is None
    assert attribute('doc/x.py') == 'a'


def test_prefix_attributor_returns_none_when_nothing_claims_the_path():
    """An unclaimed path resolves to None so the lift can drop and report it."""
    # Arrange
    attribute = make_prefix_attributor({'a': 'alpha'})

    # Act / Assert
    assert attribute('b/x.py') is None


# =============================================================================
# Position enumeration
# =============================================================================


def test_import_positions_anchor_on_the_imported_name():
    """Positions land on the alias, not on the 'from' keyword.

    Anchoring on the statement's col_offset resolves nothing on a real server —
    a silent zero indistinguishable from a workspace with no references.
    """
    # Arrange
    source = 'from alpha.beta import thing\n'

    # Act
    positions = import_positions(source)

    # Assert — the alias 'thing' and the module 'alpha.beta', never column 0.
    assert (0, source.index('thing')) in positions
    assert (0, source.index('alpha.beta')) in positions
    assert all(character > 0 for _line, character in positions)


def test_import_positions_covers_plain_imports():
    """A plain 'import x' contributes its module-name position."""
    # Arrange
    source = 'import os\n'

    # Act / Assert
    assert import_positions(source) == [(0, source.index('os'))]


def test_import_positions_skips_star_imports():
    """A star import names no symbol to resolve."""
    assert import_positions('from alpha import *\n') == [(0, len('from '))]


def test_import_positions_returns_empty_for_unparseable_source():
    """A syntax error is a scanned-but-empty file, not a harvest failure."""
    assert import_positions('def (:\n') == []


# =============================================================================
# Lifecycle failure modes (D3) — one negative control per mode
# =============================================================================


def test_absent_server_reports_ran_false_with_a_stated_reason(tmp_path):
    """Mode 1: the configured binary is not on PATH."""
    # Arrange
    (tmp_path / 'x.py').write_text('import os\n')

    # Act
    outcome = harvest_workspace(tmp_path, server_cmd=['definitely-not-a-real-language-server-xyz'])

    # Assert
    assert outcome.ran is False
    assert outcome.reason.startswith('server-absent:')
    assert outcome.references == []


def test_server_that_exits_immediately_reports_ran_false(tmp_path):
    """Mode 2: the binary exists but the session never completes."""
    # Arrange
    (tmp_path / 'x.py').write_text('import os\n')

    # Act
    outcome = harvest_workspace(
        tmp_path,
        server_cmd=[PYTHON, '-c', 'raise SystemExit(1)'],
        timeout_s=20.0,
        request_timeout_s=5.0,
    )

    # Assert
    assert outcome.ran is False
    assert outcome.reason.startswith('server-failed-to-start:')
    assert outcome.references == []


def test_unresponsive_server_reports_a_timeout(tmp_path):
    """Mode 3: the server starts, accepts input, and never answers."""
    # Arrange
    (tmp_path / 'x.py').write_text('import os\n')

    # Act — reads stdin forever without ever writing a reply.
    outcome = harvest_workspace(
        tmp_path,
        server_cmd=[PYTHON, '-c', 'import sys; sys.stdin.read()'],
        timeout_s=2.0,
        request_timeout_s=0.5,
    )

    # Assert
    assert outcome.ran is False
    assert outcome.reason.startswith('server-timeout:')
    assert outcome.references == []


def test_workspace_without_sources_reports_unsupported(tmp_path):
    """Mode 4: the server is fine, but the workspace holds nothing to harvest."""
    # Arrange — a tree with no *.py at all.
    (tmp_path / 'README.md').write_text('no sources here\n')

    # Act
    outcome = harvest_workspace(tmp_path, server_cmd=[PYTHON, '-c', 'pass'])

    # Assert
    assert outcome.ran is False
    assert outcome.reason.startswith('workspace-unsupported:')
    assert outcome.references == []


def test_workspace_under_a_skip_named_directory_is_still_harvested(tmp_path):
    """A skip-list name in the ROOT's own path must not veto the whole workspace.

    The skip list filters trees INSIDE the workspace. Matching it against the
    absolute path instead lets a project checked out under `target/` or `venv/`
    match on every file and report itself unsupported — a stated-but-WRONG
    reason, which is worse than a silent one because it looks considered.
    """
    # Arrange — a real workspace that happens to live under a skipped name.
    root = tmp_path / 'target' / 'project'
    root.mkdir(parents=True)
    (root / 'x.py').write_text('import os\n')

    # Act
    outcome = harvest_workspace(
        root, server_cmd=[PYTHON, '-c', 'raise SystemExit(1)'], timeout_s=20.0, request_timeout_s=5.0
    )

    # Assert — it may fail for server reasons, but never for an empty workspace.
    assert not outcome.reason.startswith('workspace-unsupported:')


def test_skip_list_still_excludes_vendor_trees_inside_the_workspace(tmp_path):
    """The relative-path fix must not disable the skip list it narrowed."""
    # Arrange — the only sources live in a skipped subtree.
    vendored = tmp_path / 'node_modules'
    vendored.mkdir()
    (vendored / 'dep.py').write_text('VALUE = 1\n')

    # Act
    outcome = harvest_workspace(tmp_path, server_cmd=[PYTHON, '-c', 'pass'])

    # Assert
    assert outcome.reason.startswith('workspace-unsupported:')


def test_every_failure_mode_states_a_distinct_reason(tmp_path):
    """The four modes must be tellable apart, not collapsed into one message."""
    # Arrange
    sourced = tmp_path / 'sourced'
    sourced.mkdir()
    (sourced / 'x.py').write_text('import os\n')
    empty = tmp_path / 'empty'
    empty.mkdir()
    (empty / 'README.md').write_text('none\n')

    # Act
    reasons = {
        harvest_workspace(sourced, server_cmd=['definitely-not-a-real-language-server-xyz']).reason,
        harvest_workspace(
            sourced, server_cmd=[PYTHON, '-c', 'raise SystemExit(1)'], timeout_s=20.0, request_timeout_s=5.0
        ).reason,
        harvest_workspace(
            sourced,
            server_cmd=[PYTHON, '-c', 'import sys; sys.stdin.read()'],
            timeout_s=2.0,
            request_timeout_s=0.5,
        ).reason,
        harvest_workspace(empty, server_cmd=[PYTHON, '-c', 'pass']).reason,
    }

    # Assert
    assert len(reasons) == 4


def test_no_failure_mode_reports_a_zero_edge_success(tmp_path):
    """The archetype this deliverable exists to prevent, asserted directly."""
    # Arrange
    (tmp_path / 'x.py').write_text('import os\n')

    # Act
    outcomes = [
        harvest_workspace(tmp_path, server_cmd=['definitely-not-a-real-language-server-xyz']),
        harvest_workspace(
            tmp_path, server_cmd=[PYTHON, '-c', 'raise SystemExit(1)'], timeout_s=20.0, request_timeout_s=5.0
        ),
        harvest_workspace(
            tmp_path,
            server_cmd=[PYTHON, '-c', 'import sys; sys.stdin.read()'],
            timeout_s=2.0,
            request_timeout_s=0.5,
        ),
    ]

    # Assert
    assert all(outcome.ran is False and outcome.reason for outcome in outcomes)


def test_garbage_emitting_server_does_not_escape_as_an_exception(tmp_path):
    """A server writing non-protocol output degrades to a stated no-harvest.

    An unhandled decode error here would fail the whole crawl rather than
    reporting that the harvest did not run.
    """
    # Arrange
    (tmp_path / 'x.py').write_text('import os\n')

    # Act
    outcome = harvest_workspace(
        tmp_path,
        server_cmd=[PYTHON, '-c', 'import sys; sys.stdout.write("not-lsp\\r\\n\\r\\n"); sys.stdout.flush()'],
        timeout_s=5.0,
        request_timeout_s=1.0,
    )

    # Assert
    assert outcome.ran is False
    assert outcome.reason


# =============================================================================
# component_refs materialization
# =============================================================================


def test_disabled_harvest_reports_disabled_and_runs_nothing(tmp_path):
    """The default-off gate reports itself rather than silently producing zero."""
    # Act
    refs, status = build_lsp_component_refs(tmp_path, {}, server_cmd=[PYTHON], enabled=False)

    # Assert
    assert refs == {}
    assert status['ran'] is False
    assert status['reason'].startswith('disabled:')


def test_failed_harvest_yields_no_refs_but_a_stated_status(tmp_path):
    """A failed harvest still hands the resolver something to report."""
    # Arrange
    (tmp_path / 'x.py').write_text('import os\n')

    # Act
    refs, status = build_lsp_component_refs(
        tmp_path, {'alpha': '.'}, server_cmd=['definitely-not-a-real-language-server-xyz'], enabled=True
    )

    # Assert
    assert refs == {}
    assert status['ran'] is False
    assert status['reason'].startswith('server-absent:')


def test_harvest_outcome_status_distinguishes_ran_from_found_nothing():
    """The two zero-edge states carry different records."""
    # Arrange
    failed = HarvestOutcome(ran=False, reason='server-absent: x')
    empty = HarvestOutcome(ran=True)

    # Act / Assert
    assert failed.as_status()['ran'] is False
    assert failed.as_status()['reason']
    assert empty.as_status()['ran'] is True
    assert empty.as_status()['reason'] == ''


# =============================================================================
# End-to-end against a real server
# =============================================================================


@pytest.mark.skipif(shutil.which('pyright-langserver') is None, reason='pyright-langserver not installed')
def test_end_to_end_harvest_against_a_real_server():
    """The D0 premise, pinned: a real server yields real cross-file references.

    Skipped where no server is installed, so the suite stays runnable — but where
    one IS present this is the only test that proves the client speaks the
    protocol correctly rather than merely handling its own failure modes.
    """
    # Arrange — two files where one genuinely imports the other.
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        (root / 'target_mod.py').write_text('VALUE = 1\n')
        (root / 'source_mod.py').write_text('from target_mod import VALUE\n\nprint(VALUE)\n')

        # Act
        outcome = harvest_workspace(
            root, server_cmd=['pyright-langserver', '--stdio'], timeout_s=120.0, request_timeout_s=30.0
        )

        # Assert
        assert outcome.ran is True, outcome.reason
        assert ('source_mod.py', 'target_mod.py') in outcome.references


@pytest.mark.skipif(shutil.which('pyright-langserver') is None, reason='pyright-langserver not installed')
def test_end_to_end_materialization_produces_lsp_component_refs():
    """A real harvest reaches the resolver's field in the shape it joins over."""
    # Arrange
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        (root / 'alpha').mkdir()
        (root / 'beta').mkdir()
        (root / 'beta' / 'target_mod.py').write_text('VALUE = 1\n')
        (root / 'alpha' / 'source_mod.py').write_text(
            'import sys\n\nsys.path.insert(0, "../beta")\nfrom target_mod import VALUE\n'
        )

        # Act
        refs, status = build_lsp_component_refs(
            root,
            {'alpha': 'alpha', 'beta': 'beta'},
            server_cmd=['pyright-langserver', '--stdio'],
            enabled=True,
            timeout_s=120.0,
            request_timeout_s=30.0,
        )

        # Assert
        assert status['ran'] is True, status['reason']
        for entries in refs.values():
            assert all(entry['dep_type'] == DEP_TYPE_LSP for entry in entries)
