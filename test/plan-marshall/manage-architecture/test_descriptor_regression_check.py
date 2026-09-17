#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``descriptor-regression-check`` commit-gate verb.

The ``architecture-refresh`` finalize step must REFUSE to commit a regenerated
``_project.json`` whose project identity regressed — name overwritten with the
worktree/plan-id basename, or description/description_reasoning blanked from a
previously-curated value. ``cmd_descriptor_regression_check`` is the
deterministic predicate the commit gate consumes. These tests exercise each
regressive predicate, a benign (identity-preserved) refresh, and the
missing-baseline error contract.

The module-enrichment half compares each module's ``enriched.json`` on both
sides. Its fixtures write documents as raw JSON rather than through the store's
writer, so a dotted legacy ``key_packages`` key — which the writer refuses — can
be seeded exactly as an older tool version left it. The ``--pre-ref`` cases
commit the baseline into a throwaway ``git init`` repository and read it back by
ref.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import load_script_module, parse_ns

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
_handlers = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_handlers.py', '_cmd_client_handlers'
)

save_project_meta = _architecture_core.save_project_meta
get_data_dir = _architecture_core.get_data_dir
cmd_descriptor_regression_check = _cmd_client.cmd_descriptor_regression_check
EXAMINED_FIELDS: tuple[str, ...] = _handlers.DESCRIPTOR_REGRESSION_EXAMINED_FIELDS

_ARCH_SUBDIR = Path('.plan') / 'project-architecture'


def _write_baseline(baseline_dir: str, meta: dict) -> None:
    """Write a baseline ``_project.json`` directly under ``baseline_dir``.

    ``_resolve_snapshot_dir`` accepts a snapshot root that contains
    ``_project.json`` directly, so the test writes the baseline at the simple
    shape rather than nesting a full ``.plan/project-architecture/`` subtree.
    """
    (Path(baseline_dir) / '_project.json').write_text(json.dumps(meta, indent=2, sort_keys=True), encoding='utf-8')


def _curated_meta(name: str = 'curated-project') -> dict:
    """A descriptor with a curated name + description + reasoning."""
    return {
        'name': name,
        'description': 'A curated project description',
        'description_reasoning': 'From README.md first paragraph',
        'extensions_used': [],
        'modules': {'module-a': {}},
    }


def _run(baseline_dir: str, project_dir: str) -> dict:
    args = SimpleNamespace(pre=str(baseline_dir), project_dir=str(project_dir))
    result: dict = cmd_descriptor_regression_check(args)
    return result


def _violation_fields(result: dict) -> set[str]:
    return {v['field'] for v in result['violations']}


def test_name_overwritten_with_basename_is_regressive():
    """A regenerated name equal to the project-dir basename is regressive.

    This is the canonical worktree/plan-id corruption: ``discover --force``
    inside a worktree rewrote ``name`` to ``project_path.name``.
    """
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta(name='plan-marshall'))
        # Regenerated descriptor: name flipped to the project-dir basename.
        basename = Path(project_dir).resolve().name
        regenerated = _curated_meta(name=basename)
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'success'
        assert result['regressive'] is True
        assert 'name' in _violation_fields(result)
        # The reason names the basename signature.
        name_violation = next(v for v in result['violations'] if v['field'] == 'name')
        assert basename in name_violation['reason']


def test_name_changed_to_other_value_is_regressive():
    """Any divergence from the curated baseline name is regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta(name='plan-marshall'))
        regenerated = _curated_meta(name='something-else')
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert 'name' in _violation_fields(result)


def test_description_blanked_is_regressive():
    """A description transitioning from non-empty to empty is regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        regenerated = _curated_meta()
        regenerated['description'] = ''
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'description'}


def test_description_reasoning_blanked_is_regressive():
    """A blanked description_reasoning is regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        regenerated = _curated_meta()
        regenerated['description_reasoning'] = ''
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'description_reasoning'}


def test_benign_refresh_with_module_changes_is_not_regressive():
    """Identity preserved + only the module index shifting is benign."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        # Regenerated descriptor: identity intact, an extra module added.
        regenerated = _curated_meta()
        regenerated['modules'] = {'module-a': {}, 'module-b': {}}
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'success'
        assert result['regressive'] is False
        assert result['violations'] == []


def test_empty_baseline_name_never_flags_name():
    """A baseline with no curated name cannot lose one — name is not regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        baseline = _curated_meta(name='')
        _write_baseline(baseline_dir, baseline)
        # Regenerated descriptor seeds a real name (an improvement, not a loss).
        regenerated = _curated_meta(name='now-named')
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is False
        assert 'name' not in _violation_fields(result)


def test_multiple_violations_collected():
    """Name flip AND description blanking both surface as violations."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta(name='plan-marshall'))
        basename = Path(project_dir).resolve().name
        regenerated = _curated_meta(name=basename)
        regenerated['description'] = ''
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'name', 'description'}


def test_missing_baseline_returns_snapshot_not_found():
    """An absent baseline _project.json yields the snapshot_not_found error."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        # No _project.json written under baseline_dir.
        save_project_meta(_curated_meta(), project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['path'] == str(baseline_dir)


# =============================================================================
# Module enrichment — fixture helpers
# =============================================================================


def _document(responsibility: str = 'Handles core', key_packages: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'type': 'module',
        'responsibility': responsibility,
        'key_packages': {} if key_packages is None else key_packages,
    }


def _write_document(data_dir: Path, module: str, document: dict[str, Any] | str) -> None:
    """Write one ``enriched.json`` raw — a ``str`` is written verbatim (for corrupt documents)."""
    path = data_dir / module / 'enriched.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document if isinstance(document, str) else json.dumps(document), encoding='utf-8')


def _seed_pair(
    baseline_dir: str,
    project_dir: str,
    baseline_docs: dict[str, dict[str, Any] | str],
    current_docs: dict[str, dict[str, Any] | str],
) -> None:
    """Seed a baseline snapshot and a current project, each indexing its own documents."""
    baseline_meta = {**_curated_meta(), 'modules': {name: {} for name in baseline_docs}}
    _write_baseline(baseline_dir, baseline_meta)
    for name, document in baseline_docs.items():
        _write_document(Path(baseline_dir), name, document)

    save_project_meta({**_curated_meta(), 'modules': {name: {} for name in current_docs}}, project_dir)
    for name, document in current_docs.items():
        _write_document(get_data_dir(project_dir), name, document)


def _make_package_dir(project_dir: str, relative: str) -> str:
    (Path(project_dir) / relative).mkdir(parents=True, exist_ok=True)
    return relative


# =============================================================================
# Coverage fields
# =============================================================================


def test_examined_fields_are_the_published_constant_and_not_empty():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        save_project_meta(_curated_meta(), project_dir)

        result = _run(baseline_dir, project_dir)

        assert len(EXAMINED_FIELDS) > 0
        assert result['examined_fields'] == list(EXAMINED_FIELDS)


def test_modules_examined_counts_compared_modules_and_zero_stays_distinguishable():
    """A green verdict over no compared module reports 0; over one module it reports 1."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        save_project_meta(_curated_meta(), project_dir)

        identity_only = _run(baseline_dir, project_dir)

    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _seed_pair(baseline_dir, project_dir, {'core': _document()}, {'core': _document()})

        with_module = _run(baseline_dir, project_dir)

    assert identity_only['regressive'] is False
    assert identity_only['modules_examined'] == 0
    assert with_module['regressive'] is False
    assert with_module['modules_examined'] == 1
    assert with_module['modules_unreadable'] == []


def test_every_violation_field_is_an_examined_field():
    """A fixture tripping every predicate reports only fields the response says it examined."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        basename = Path(project_dir).resolve().name
        baseline = _document(key_packages={'core/src/lost': {'description': 'Lost'}})
        _seed_pair(baseline_dir, project_dir, {'core': baseline}, {'core': _document(responsibility='')})
        regenerated = {**_curated_meta(name=basename), 'description': '', 'description_reasoning': ''}
        save_project_meta({**regenerated, 'modules': {'core': {}}}, project_dir)

        result = _run(baseline_dir, project_dir)

        fields = _violation_fields(result)
        assert fields == set(EXAMINED_FIELDS), 'the fixture no longer trips every predicate'
        assert fields <= set(result['examined_fields'])


# =============================================================================
# Module enrichment predicates
# =============================================================================


def test_lost_key_packages_entry_is_regressive():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _make_package_dir(project_dir, 'core/src/kept')
        entries = {'core/src/kept': {'description': 'Kept'}, 'core/src/lost': {'description': 'Lost'}}
        _seed_pair(
            baseline_dir,
            project_dir,
            {'core': _document(key_packages=entries)},
            {'core': _document(key_packages={'core/src/kept': {'description': 'Kept'}})},
        )

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'enriched.key_packages'}
        assert 'core/src/lost' in result['violations'][0]['reason']


def test_blanked_responsibility_is_regressive():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _seed_pair(baseline_dir, project_dir, {'core': _document()}, {'core': _document(responsibility='  ')})

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'enriched.responsibility'}


def test_byte_identical_rekey_is_a_migration_not_a_violation():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        path_key = _make_package_dir(project_dir, 'core/src/pkg')
        entry = {'description': 'Pipeline'}
        _seed_pair(
            baseline_dir,
            project_dir,
            {'core': _document(key_packages={'com.example.pkg': entry})},
            {'core': _document(key_packages={path_key: dict(entry)})},
        )

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is False
        assert result['violations'] == []
        assert result['migrations'] == [{'module': 'core', 'from_key': 'com.example.pkg', 'to_key': path_key}]
        assert result['unresolved_keys'] == []


def test_rekey_with_a_changed_description_is_regressive():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        path_key = _make_package_dir(project_dir, 'core/src/pkg')
        _seed_pair(
            baseline_dir,
            project_dir,
            {'core': _document(key_packages={'com.example.pkg': {'description': 'Pipeline'}})},
            {'core': _document(key_packages={path_key: {'description': 'Rewritten'}})},
        )

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'enriched.key_packages'}
        assert result['migrations'] == []


def test_blanked_description_on_a_surviving_entry_is_regressive():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        path_key = _make_package_dir(project_dir, 'core/src/pkg')
        _seed_pair(
            baseline_dir,
            project_dir,
            {'core': _document(key_packages={path_key: {'description': 'Pipeline'}})},
            {'core': _document(key_packages={path_key: {'description': ''}})},
        )

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert 'description blanked' in result['violations'][0]['reason']


def test_mixed_vocabulary_reports_the_non_resolving_key():
    """A partial re-key: one key bridged to a path, its parent package key did not."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        path_key = _make_package_dir(project_dir, 'core/src/pkg')
        child = {'description': 'Pipeline'}
        parent = {'description': 'Parent package'}
        _seed_pair(
            baseline_dir,
            project_dir,
            {'core': _document(key_packages={'com.example.pkg': child, 'com.example': parent})},
            {'core': _document(key_packages={path_key: dict(child), 'com.example': dict(parent)})},
        )

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is False
        assert result['unresolved_keys'] == [{'module': 'core', 'key': 'com.example'}]
        assert len(result['migrations']) == 1


@pytest.mark.parametrize(
    ('baseline_doc', 'current_doc', 'reason'),
    [
        ('{not json', _document(), 'baseline_invalid_json'),
        (_document(), '[1, 2]', 'current_not_an_object'),
    ],
)
def test_unreadable_module_document_is_reported_not_examined(baseline_doc, current_doc, reason):
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _seed_pair(baseline_dir, project_dir, {'core': baseline_doc}, {'core': current_doc})

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'success'
        assert result['modules_examined'] == 0
        assert result['modules_unreadable'] == [{'module': 'core', 'reason': reason}]


def test_module_missing_its_document_on_both_sides_names_both():
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        save_project_meta(_curated_meta(), project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['modules_unreadable'] == [{'module': 'module-a', 'reason': 'baseline_absent, current_absent'}]


# =============================================================================
# --pre-ref baselines
# =============================================================================


def _git(repo: Path, *argv: str) -> str:
    completed = subprocess.run(
        [
            'git',
            '-c',
            'user.name=test',
            '-c',
            'user.email=test@example.com',
            '-c',
            'commit.gpgsign=false',
            '-C',
            str(repo),
            *argv,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _commit_baseline(project_dir: str, documents: dict[str, dict[str, Any]]) -> None:
    """``git init`` the project and commit a descriptor tree as its baseline."""
    repo = Path(project_dir)
    _git(repo, 'init', '-q')
    save_project_meta({**_curated_meta(), 'modules': {name: {} for name in documents}}, project_dir)
    for name, document in documents.items():
        _write_document(get_data_dir(project_dir), name, document)
    # ``-f``: a machine-level ignore rule for ``.plan/`` must not empty the baseline.
    _git(repo, 'add', '-f', '-A')
    _git(repo, 'commit', '-q', '-m', 'baseline')


def _run_ref(ref: str, project_dir: str) -> dict:
    result: dict = cmd_descriptor_regression_check(SimpleNamespace(pre_ref=ref, project_dir=str(project_dir)))
    return result


def test_pre_ref_reads_the_committed_baseline_and_detects_a_regression():
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_baseline(project_dir, {'core': _document()})
        _write_document(get_data_dir(project_dir), 'core', _document(responsibility=''))

        result = _run_ref('HEAD', project_dir)

        assert result['status'] == 'success'
        assert result['modules_examined'] == 1
        assert _violation_fields(result) == {'enriched.responsibility'}


def test_pre_ref_leaves_nothing_behind_in_the_project():
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_baseline(project_dir, {'core': _document()})
        before = _git(Path(project_dir), 'status', '--porcelain', '--untracked-files=all')

        result = _run_ref('HEAD', project_dir)

        assert result['regressive'] is False
        assert before == ''
        assert _git(Path(project_dir), 'status', '--porcelain', '--untracked-files=all') == ''


def test_pre_ref_lacking_the_tree_is_snapshot_not_found():
    with tempfile.TemporaryDirectory() as project_dir:
        repo = Path(project_dir)
        _git(repo, 'init', '-q')
        (repo / 'README.md').write_text('no descriptor tree here\n', encoding='utf-8')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-q', '-m', 'no tree')
        save_project_meta(_curated_meta(), project_dir)

        result = _run_ref('HEAD', project_dir)

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['ref'] == 'HEAD'


def test_dash_prefixed_ref_is_refused_as_invalid_ref():
    with tempfile.TemporaryDirectory() as project_dir:
        save_project_meta(_curated_meta(), project_dir)

        result = _run_ref('--output=/tmp/evil', project_dir)

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_ref'
        assert result['ref'] == '--output=/tmp/evil'


def test_pre_and_pre_ref_are_mutually_exclusive_and_one_is_required():
    base = ('plan-marshall', 'manage-architecture', 'architecture.py', 'descriptor-regression-check')
    assert parse_ns(*base, '--pre-ref', 'HEAD', register=False).pre_ref == 'HEAD'
    with pytest.raises(SystemExit):
        parse_ns(*base, '--pre', '.', '--pre-ref', 'HEAD', register=False)
    with pytest.raises(SystemExit):
        parse_ns(*base, register=False)
