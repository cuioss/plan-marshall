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
"""

from pathlib import Path

from conftest import get_script_path, run_script
from toon_parser import parse_toon

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
    spec_body = (
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
    spec_path.write_text(spec_body, encoding='utf-8')

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
