#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-adr.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""


from argparse import Namespace
from pathlib import Path

import pytest
from _manage_adr_fixtures import (
    METADATA_BLOCK_END,
    METADATA_BLOCK_START,
    SCRIPT_PATH,
    _build_metadata_block,
    _detect_corpus_width,
    _touch_adr,
    _write_adr,
    cmd_create,
    cmd_delete,
    cmd_read,
    cmd_scan,
    cmd_update,
    find_adr_by_number,
    generate_filename,
    get_next_number,
    parse_adr_file,
    parse_metadata_block,
)

from conftest import run_script


@pytest.fixture
def adr_dir(tmp_path, monkeypatch):
    """Provide a clean doc/adr directory and chdir into the temp project root."""
    directory = tmp_path / 'doc' / 'adr'
    directory.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return directory


def test_parse_metadata_block_missing_block(adr_dir):
    """Content without any metadata block returns all-empty defaults."""
    content = '= ADR-003: No Block\n\n== Status\n\nProposed\n'

    metadata = parse_metadata_block(content)

    assert metadata['summary'] == ''
    assert metadata['tags'] == []
    assert metadata['affects'] == []
    assert metadata['supersedes'] == []


def test_parse_metadata_block_malformed_lines_ignored(adr_dir):
    """Lines that are not `// field: value` comments are skipped."""
    content = (
        '= ADR-004: Malformed\n\n'
        f'{METADATA_BLOCK_START}\n'
        '// summary: Has a summary\n'
        'this is not a comment line\n'
        '// not a known field but well formed: ignored\n'
        '// tags: alpha,beta\n'
        f'{METADATA_BLOCK_END}\n'
        '\n== Status\n\nProposed\n'
    )

    metadata = parse_metadata_block(content)

    assert metadata['summary'] == 'Has a summary'
    assert metadata['tags'] == ['alpha', 'beta']
    assert 'not a known field but well formed' not in metadata


def test_parse_metadata_block_extra_whitespace_in_list(adr_dir):
    """Comma-split list fields strip surrounding whitespace and empties."""
    content = (
        '= ADR-005: Whitespace\n\n'
        + _build_metadata_block(tags=' a ,  b ,, c ')
        + '\n== Status\n\nProposed\n'
    )

    metadata = parse_metadata_block(content)

    assert metadata['tags'] == ['a', 'b', 'c']


def test_parse_adr_file_surfaces_metadata(adr_dir):
    """parse_adr_file folds metadata fields into its returned dict."""
    adr_path = adr_dir / '007-With_Metadata.adoc'
    adr_path.write_text(
        '= ADR-007: With Metadata\n\n'
        + _build_metadata_block(
            summary='Carry metadata through parse_adr_file',
            tags='lifecycle',
            affects='plan-marshall',
            supersedes='',
        )
        + '\n== Status\n\nAccepted\n'
    )

    adr = parse_adr_file(adr_path)

    assert adr['number'] == 7
    assert adr['title'] == 'With Metadata'
    assert adr['status'] == 'Accepted'
    assert adr['summary'] == 'Carry metadata through parse_adr_file'
    assert adr['tags'] == ['lifecycle']
    assert adr['affects'] == ['plan-marshall']
    assert adr['supersedes'] == []


# =========================================================================
# Tier 2: scan subcommand
# =========================================================================


def test_scan_empty_dir(adr_dir):
    """scan over an empty ADR dir returns zero ADRs."""
    result = cmd_scan(Namespace(command='scan', tag=None, affects=None))

    assert result['status'] == 'success'
    assert result['operation'] == 'scan'
    assert result['count'] == 0
    assert result['adrs'] == []


def test_scan_no_filter_returns_all_with_metadata(adr_dir):
    """scan with no filter returns every ADR plus its metadata fields."""
    _write_adr(adr_dir, '001-First.adoc', title='First', summary='first summary', tags='alpha')
    _write_adr(adr_dir, '002-Second.adoc', title='Second', summary='second summary', affects='plan-marshall')

    result = cmd_scan(Namespace(command='scan', tag=None, affects=None))

    assert result['status'] == 'success'
    assert result['count'] == 2

    by_number = {adr['number']: adr for adr in result['adrs']}
    assert by_number[1]['summary'] == 'first summary'
    assert by_number[1]['tags'] == ['alpha']
    assert by_number[2]['summary'] == 'second summary'
    assert by_number[2]['affects'] == ['plan-marshall']
    for adr in result['adrs']:
        for field in ('number', 'title', 'status', 'summary', 'tags', 'affects', 'supersedes'):
            assert field in adr


def test_scan_tag_filter(adr_dir):
    """scan --tag returns only ADRs whose tags include the value."""
    _write_adr(adr_dir, '001-Persist.adoc', title='Persist', tags='persistence,db')
    _write_adr(adr_dir, '002-Other.adoc', title='Other', tags='ui')

    result = cmd_scan(Namespace(command='scan', tag='persistence', affects=None))

    assert result['count'] == 1
    assert result['adrs'][0]['number'] == 1


def test_scan_affects_filter(adr_dir):
    """scan --affects returns only ADRs whose affects include the value."""
    _write_adr(adr_dir, '001-Core.adoc', title='Core', affects='plan-marshall,pm-documents')
    _write_adr(adr_dir, '002-Docs.adoc', title='Docs', affects='pm-documents')

    result = cmd_scan(Namespace(command='scan', tag=None, affects='plan-marshall'))

    assert result['count'] == 1
    assert result['adrs'][0]['number'] == 1


def test_scan_filter_no_match(adr_dir):
    """scan with a filter matching nothing returns zero ADRs."""
    _write_adr(adr_dir, '001-Solo.adoc', title='Solo', tags='alpha')

    result = cmd_scan(Namespace(command='scan', tag='nonexistent', affects=None))

    assert result['count'] == 0
    assert result['adrs'] == []


def test_create_emits_metadata_block(adr_dir):
    """create produces an ADR carrying the (empty) metadata block."""
    result = cmd_create(Namespace(command='create', title='Has Block', status='Proposed'))

    assert result['status'] == 'success'

    # Empty corpus → default width 4.
    created_file = adr_dir / f'{result["number"]:04d}-Has_Block.adoc'
    content = created_file.read_text()
    assert METADATA_BLOCK_START in content
    assert METADATA_BLOCK_END in content

    metadata = parse_metadata_block(content)
    assert metadata['summary'] == ''
    assert metadata['tags'] == []


def test_detect_corpus_width_empty_defaults_to_four(adr_dir):
    """An empty corpus yields the default prefix width of 4."""
    assert _detect_corpus_width() == 4


def test_detect_corpus_width_three_digit_corpus(adr_dir):
    """A 3-digit corpus (001..007) reports width 3."""
    for n in range(1, 8):
        _touch_adr(adr_dir, f'{n:03d}-Decision_{n}.adoc')

    assert _detect_corpus_width() == 3


def test_detect_corpus_width_four_digit_corpus(adr_dir):
    """A 4-digit corpus reports width 4."""
    _touch_adr(adr_dir, '0001-First.adoc')
    _touch_adr(adr_dir, '0002-Second.adoc')

    assert _detect_corpus_width() == 4


def test_detect_corpus_width_mixed_returns_max(adr_dir):
    """A mixed-width corpus reports the maximum prefix width found."""
    _touch_adr(adr_dir, '007-Narrow.adoc')
    _touch_adr(adr_dir, '0008-Wide.adoc')

    assert _detect_corpus_width() == 4


def test_find_adr_by_number_returns_both_ambiguous_widths(adr_dir):
    """find_adr_by_number surfaces BOTH files when a number is ambiguous.

    A corpus containing a 3-digit (008-) and a 4-digit (0008-) prefix for the
    same decision number returns two matches — the raw signal the cmd_read /
    cmd_update / cmd_delete callers reject as ambiguous_number.
    """
    _touch_adr(adr_dir, '008-Narrow.adoc')
    _touch_adr(adr_dir, '0008-Wide.adoc')

    matches = find_adr_by_number(8)

    assert len(matches) == 2
    assert {p.name for p in matches} == {'008-Narrow.adoc', '0008-Wide.adoc'}


def test_generate_filename_zero_pads_to_width(adr_dir):
    """generate_filename zero-pads the number to the supplied width."""
    assert generate_filename(8, 'Some Title', 3) == '008-Some_Title.adoc'
    assert generate_filename(8, 'Some Title', 4) == '0008-Some_Title.adoc'


def test_get_next_number_on_three_digit_corpus(adr_dir):
    """get_next_number returns max+1 over a 3-digit corpus (001..007 → 8)."""
    for n in range(1, 8):
        _touch_adr(adr_dir, f'{n:03d}-Decision_{n}.adoc')

    assert get_next_number() == 8


def test_get_next_number_on_four_digit_corpus(adr_dir):
    """get_next_number reads width-agnostic prefixes (0008 → 9)."""
    _touch_adr(adr_dir, '0008-Wide.adoc')

    assert get_next_number() == 9


def test_parse_adr_file_three_digit_prefix(adr_dir):
    """parse_adr_file extracts the number from a 3-digit prefixed filename."""
    _touch_adr(adr_dir, '008-Three_Digit.adoc', title='Three Digit')

    adr = parse_adr_file(adr_dir / '008-Three_Digit.adoc')

    assert adr['number'] == 8
    assert adr['title'] == 'Three Digit'


def test_parse_adr_file_four_digit_prefix(adr_dir):
    """parse_adr_file extracts the number from a 4-digit prefixed filename."""
    _touch_adr(adr_dir, '0008-Four_Digit.adoc', title='Four Digit')

    adr = parse_adr_file(adr_dir / '0008-Four_Digit.adoc')

    assert adr['number'] == 8
    assert adr['title'] == 'Four Digit'


def test_create_next_filename_on_seven_adr_three_digit_corpus(adr_dir):
    """Success criterion: a 7-ADR 3-digit corpus emits the next ADR as 008-."""
    for n in range(1, 8):
        _touch_adr(adr_dir, f'{n:03d}-Decision_{n}.adoc')

    result = cmd_create(Namespace(command='create', title='Eighth Decision', status='Proposed'))

    assert result['status'] == 'success'
    assert result['number'] == 8
    assert Path(result['path']).name == '008-Eighth_Decision.adoc'
    assert 'ADR-008' in (adr_dir / '008-Eighth_Decision.adoc').read_text()


def test_create_on_empty_corpus_emits_four_digit_prefix(adr_dir):
    """Success criterion: an empty corpus emits 0001- (default width 4)."""
    result = cmd_create(Namespace(command='create', title='First Decision', status='Proposed'))

    assert result['status'] == 'success'
    assert result['number'] == 1
    assert Path(result['path']).name == '0001-First_Decision.adoc'


def test_find_adr_by_number_is_width_agnostic(adr_dir):
    """find_adr_by_number locates an ADR regardless of its prefix width."""
    _touch_adr(adr_dir, '0008-Wide.adoc')

    matches = find_adr_by_number(8)

    assert len(matches) == 1
    assert matches[0].name == '0008-Wide.adoc'


def test_read_update_delete_on_four_digit_corpus(adr_dir):
    """read/update/delete resolve a 4-digit-prefixed ADR by its number."""
    _touch_adr(adr_dir, '0008-Wide.adoc', title='Wide', status='Proposed')

    read_result = cmd_read(Namespace(command='read', number=8))
    assert read_result['status'] == 'success'
    assert 'Wide' in read_result['content']

    update_result = cmd_update(Namespace(command='update', number=8, status='Accepted'))
    assert update_result['status'] == 'success'
    assert 'Accepted' in (adr_dir / '0008-Wide.adoc').read_text()

    delete_result = cmd_delete(Namespace(command='delete', number=8, force=True))
    assert delete_result['deleted']
    assert not (adr_dir / '0008-Wide.adoc').exists()


# =========================================================================
# Tier 3: Subprocess CLI plumbing tests (retained)
# =========================================================================


def test_cli_invalid_status(adr_dir):
    """Test creating ADR with invalid status via CLI (argparse rejection)."""
    result = run_script(
        SCRIPT_PATH, 'create', '--title', 'Invalid Status', '--status', 'InvalidStatus', cwd=str(Path.cwd())
    )

    assert result.returncode != 0
    assert 'invalid choice' in result.stderr.lower()


def test_cli_create_and_list(adr_dir):
    """Test CLI plumbing: create then list via subprocess."""
    result = run_script(SCRIPT_PATH, 'create', '--title', 'CLI Test', cwd=str(Path.cwd()))

    assert result.returncode == 0
    assert 'success' in result.stdout

    result = run_script(SCRIPT_PATH, 'list', cwd=str(Path.cwd()))

    assert result.returncode == 0
    assert 'success' in result.stdout


def test_cli_scan(adr_dir):
    """Test CLI plumbing: create then scan via subprocess."""
    result = run_script(SCRIPT_PATH, 'create', '--title', 'Scan Me', cwd=str(Path.cwd()))

    assert result.returncode == 0

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(Path.cwd()))

    assert result.returncode == 0
    assert 'success' in result.stdout
    assert 'scan' in result.stdout
