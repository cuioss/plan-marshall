#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the deterministic spec-ingestion seam.

Scope note (deliberate, operator-confirmed)
--------------------------------------------
``phase-1-init`` is an LLM-driven markdown skill with **no script entry point**,
so a pytest cannot literally "run init". These tests instead pin the deterministic
seam the phase-1-init file-pointer branch delegates to —
``manage-plan-documents request create --body-file`` — which is the only
executable surface on the ingestion path. The doc-contract half (that phase-1-init
routes the pointer branch through this seam, and aborts fail-closed on a missing
target) is verified by the phase-1-init plugin-doctor gate, not here. No
phase-level harness is in scope; the operator confirmed the script-seam scope.

There is a residual gap this scope leaves open: a future edit could reroute
phase-1-init away from ``--body-file`` without any test in this module failing.
That gap is intentional and recorded here at the test site so it stays visible —
the plugin-doctor gate over the skill body is the compensating control.

Assertion mechanism (normative for every case)
----------------------------------------------
Each test branches on the parsed TOON ``status`` field, **never on the process
exit code**. ``manage-plan-documents`` follows the canonical output contract: the
``body_file_not_found`` refusal is an *operation* failure that exits ``0`` and
carries its verdict only in the stdout TOON. A test that asserted on
``returncode`` would pass vacuously against both the refusal and the happy path,
reproducing the exact "confident signal hides a caveat" defect this seam closes.
All assertions run against the constructed-argv subprocess boundary
(``run_script`` + ``parse_toon``), not against internal helpers.

The orchestrator-store half pins that ``--body-file`` resolves a logical
``.plan/orchestrator/…`` pointer through the store seam: with
``orchestrator.use_worktree`` on, a spec staged only in the shared ledger
worktree is ingested from there even when the main checkout holds a divergent
copy, and with the knob off the pointer reads the current checkout's copy.
"""

from pathlib import Path

from _orchestrator_worktree_fixtures import build_ledger_repo, use_real_resolver, write_marshal
from file_ops import get_orchestrator_store_root
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-plan-documents', 'manage-plan-documents.py')

# The template placeholder that a metadata-only create leaves in place and that
# --body-file ingestion must replace. Kept in sync with _cmd_request._BODY_STUB
# and templates/request.md.
_BODY_STUB = '_Body not yet provided — write content here._'


def test_body_file_ingestion_carries_the_brief(plan_context):
    """Happy path: --body-file splices the spec content in, not the pointer string."""
    # Arrange: a distinctive multi-line spec body (headings + a fenced block, so
    # the marshalling path — which the inline --body shell argument used to trip —
    # is exercised end to end).
    spec_path = plan_context.fixture_dir / 'PLAN-99-example-spec.md'
    spec_text = (
        '# Example Spec Brief\n'
        '\n'
        'A distinctive first paragraph that only exists in the spec file.\n'
        '\n'
        '## Approach\n'
        '\n'
        '```python\n'
        "print('sentinel-fenced-line')\n"
        '```\n'
        '\n'
        'Closing paragraph after the fenced block.\n'
    )
    spec_path.write_text(spec_text, encoding='utf-8')

    # Act: invoke the seam exactly as the phase-1-init pointer branch does.
    result = run_script(
        SCRIPT_PATH,
        'request',
        'create',
        '--plan-id',
        'ingest-happy',
        '--title',
        'Ingest Happy Path',
        '--source',
        'description',
        '--source-id',
        str(spec_path),
        '--body-file',
        str(spec_path),
    )

    # Assert: branch on the TOON status, never the exit code.
    data = parse_toon(result.stdout)
    assert data['status'] == 'success', f'stdout={result.stdout!r} stderr={result.stderr!r}'

    rendered = Path(data['path']).read_text(encoding='utf-8')
    # The spec's own content is carried through verbatim.
    assert 'A distinctive first paragraph that only exists in the spec file.' in rendered
    assert '## Approach' in rendered
    assert "print('sentinel-fenced-line')" in rendered
    assert 'Closing paragraph after the fenced block.' in rendered
    # The bare pointer string is NOT the body, and the stub is gone.
    assert _BODY_STUB not in rendered
    # source_id carries the pointer so provenance survives ingestion.
    assert f'source_id: {spec_path}' in rendered


def test_body_file_missing_target_refuses_loud(plan_context):
    """Loud failure: a nonexistent --body-file target yields body_file_not_found."""
    # Arrange: a path that does not exist.
    missing = plan_context.fixture_dir / 'definitely-absent-spec.md'
    assert not missing.exists()

    # Act.
    result = run_script(
        SCRIPT_PATH,
        'request',
        'create',
        '--plan-id',
        'ingest-missing',
        '--title',
        'Ingest Missing Target',
        '--source',
        'description',
        '--body-file',
        str(missing),
    )

    # Assert: the refusal is on the TOON, not the exit code.
    data = parse_toon(result.stdout)
    assert data['status'] == 'error', f'stdout={result.stdout!r} stderr={result.stderr!r}'
    assert data['error'] == 'body_file_not_found'
    assert 'body_file' in data
    assert 'message' in data
    # The abort leaves no empty-brief artifact behind.
    assert not (plan_context.plan_dir_for('ingest-missing') / 'request.md').exists()


def test_body_file_directory_target_refuses_loud(plan_context):
    """Loud failure: a directory --body-file target hits the is_file() guard."""
    # Arrange: an existing path that is a directory, not a regular file.
    a_directory = plan_context.fixture_dir / 'spec-is-a-directory'
    a_directory.mkdir(parents=True, exist_ok=True)

    # Act.
    result = run_script(
        SCRIPT_PATH,
        'request',
        'create',
        '--plan-id',
        'ingest-directory',
        '--title',
        'Ingest Directory Target',
        '--source',
        'description',
        '--body-file',
        str(a_directory),
    )

    # Assert: exists() alone would pass — the is_file() guard is what refuses.
    data = parse_toon(result.stdout)
    assert data['status'] == 'error', f'stdout={result.stdout!r} stderr={result.stderr!r}'
    assert data['error'] == 'body_file_not_found'
    assert not (plan_context.plan_dir_for('ingest-directory') / 'request.md').exists()


def test_body_file_undecodable_refuses_loud(plan_context):
    """Loud failure: an existing regular file with invalid UTF-8 yields body_file_unreadable."""
    # Arrange: an existing regular file whose bytes are not valid UTF-8, so the
    # exists() and is_file() guards both pass and only the decode guard can refuse.
    undecodable = plan_context.fixture_dir / 'undecodable-spec.md'
    undecodable.write_bytes(b'\xff\xfe\x00 invalid utf-8 bytes \xff')
    assert undecodable.is_file()

    # Act.
    result = run_script(
        SCRIPT_PATH,
        'request',
        'create',
        '--plan-id',
        'ingest-undecodable',
        '--title',
        'Ingest Undecodable Target',
        '--source',
        'description',
        '--body-file',
        str(undecodable),
    )

    # Assert: the read no longer raises an uncaught UnicodeDecodeError — the
    # structured refusal is on the TOON, not the exit code.
    data = parse_toon(result.stdout)
    assert data['status'] == 'error', f'stdout={result.stdout!r} stderr={result.stderr!r}'
    assert data['error'] == 'body_file_unreadable'
    assert 'body_file' in data
    assert 'message' in data
    # The abort leaves no empty-brief artifact behind.
    assert not (plan_context.plan_dir_for('ingest-undecodable') / 'request.md').exists()


def test_no_body_file_preserves_metadata_stub(plan_context):
    """Non-pointer branch: create without --body-file keeps the stub placeholder."""
    # Act: the plain-description branch — no --body-file, caller writes the body
    # later via Write(path).
    result = run_script(
        SCRIPT_PATH,
        'request',
        'create',
        '--plan-id',
        'ingest-stub',
        '--title',
        'Ingest No Body File',
        '--source',
        'description',
    )

    # Assert: success, and the metadata-only stub still carries the placeholder.
    data = parse_toon(result.stdout)
    assert data['status'] == 'success', f'stdout={result.stdout!r} stderr={result.stderr!r}'
    rendered = Path(data['path']).read_text(encoding='utf-8')
    assert _BODY_STUB in rendered


# The logical spec pointer phase-1-init records as ``source_id`` and passes as
# ``--body-file`` on its file-pointer branch.
_SPEC_POINTER = '.plan/orchestrator/epic-alpha/plans/PLAN-01-alpha.md'
_WORKTREE_BODY = 'Spec body staged in the shared ledger worktree and not yet landed.'
_MAIN_BODY = 'Divergent stale copy on the main checkout.'


def _stage_divergent_specs(tmp_path, monkeypatch, *, knob: bool):
    """A real sandbox whose shared worktree and main checkout hold different specs.

    The shared worktree is created in-process first (knob on for that call), so
    the worktree copy exists before ingestion runs; the knob is then set to
    ``knob`` in the main checkout's ``marshal.json``, which is the only file the
    seam reads it from.
    """
    use_real_resolver(monkeypatch)
    monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
    repo = build_ledger_repo(tmp_path)
    monkeypatch.chdir(repo.main)
    write_marshal(repo.main, {'orchestrator': {'use_worktree': True}})
    get_orchestrator_store_root()
    for checkout, body in ((repo.expected_worktree, _WORKTREE_BODY), (repo.main, _MAIN_BODY)):
        spec = checkout / _SPEC_POINTER
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(f'# Spec\n\n{body}\n', encoding='utf-8')
    write_marshal(repo.main, {'orchestrator': {'use_worktree': knob}})
    return repo


def _ingest_pointer(repo, plan_id: str) -> str:
    """Run the pointer-branch ingestion from the main checkout; return the rendered body."""
    result = run_script(
        SCRIPT_PATH,
        'request',
        'create',
        '--plan-id',
        plan_id,
        '--title',
        'Ingest Store Pointer',
        '--source',
        'description',
        '--source-id',
        _SPEC_POINTER,
        '--body-file',
        _SPEC_POINTER,
        cwd=repo.main,
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'success', f'stdout={result.stdout!r} stderr={result.stderr!r}'
    return Path(data['path']).read_text(encoding='utf-8')


def test_knob_on_ingests_the_spec_staged_in_the_shared_worktree(tmp_path, monkeypatch):
    """Knob on: the worktree copy is read and the divergent main copy is not."""
    repo = _stage_divergent_specs(tmp_path, monkeypatch, knob=True)

    rendered = _ingest_pointer(repo, 'ingest-knob-on')

    assert _WORKTREE_BODY in rendered
    assert _MAIN_BODY not in rendered
    # The logical pointer — not a physical worktree path — is what provenance records.
    assert f'source_id: {_SPEC_POINTER}' in rendered


def test_knob_off_ingests_the_current_checkout_copy(tmp_path, monkeypatch):
    """Knob off (matched control): the pointer resolves on the current checkout."""
    repo = _stage_divergent_specs(tmp_path, monkeypatch, knob=False)

    rendered = _ingest_pointer(repo, 'ingest-knob-off')

    assert _MAIN_BODY in rendered
    assert _WORKTREE_BODY not in rendered
