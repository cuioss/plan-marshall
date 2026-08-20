#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage adr`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for manage-adr.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""


import re

from conftest import get_script_path, load_script_module

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-adr', 'manage-adr.py')


# Tier 2 direct imports - load hyphenated module via the conftest helper
_mod = load_script_module('plan-marshall', 'manage-adr', 'manage-adr.py', 'manage_adr')


cmd_list = _mod.cmd_list


cmd_create = _mod.cmd_create


cmd_read = _mod.cmd_read


cmd_update = _mod.cmd_update


cmd_delete = _mod.cmd_delete


cmd_next_number = _mod.cmd_next_number


cmd_scan = _mod.cmd_scan


parse_metadata_block = _mod.parse_metadata_block


parse_adr_file = _mod.parse_adr_file


generate_filename = _mod.generate_filename


get_next_number = _mod.get_next_number


_detect_corpus_width = _mod._detect_corpus_width


find_adr_by_number = _mod.find_adr_by_number


METADATA_BLOCK_START = _mod.METADATA_BLOCK_START


METADATA_BLOCK_END = _mod.METADATA_BLOCK_END


def _build_metadata_block(*, summary='', tags='', affects='', supersedes=''):
    """Build a well-formed ADR metadata comment block for tests."""
    return (
        f'{METADATA_BLOCK_START}\n'
        f'// summary: {summary}\n'
        f'// tags: {tags}\n'
        f'// affects: {affects}\n'
        f'// supersedes: {supersedes}\n'
        f'{METADATA_BLOCK_END}\n'
    )


def _write_adr(adr_dir, filename, *, title, status='Proposed', **metadata):
    """Write an ADR file with a metadata block into the test ADR dir."""
    (adr_dir / filename).write_text(
        f'= ADR-{filename[:3]}: {title}\n\n'
        + _build_metadata_block(**metadata)
        + f'\n== Status\n\n{status}\n'
    )


# =========================================================================
# Tier 2: Width-agnostic numeric-prefix parsing and numbering
# =========================================================================


def _touch_adr(adr_dir, filename, *, title='Decision', status='Proposed'):
    """Write a minimal valid ADR file whose heading number matches its prefix.

    The status block is terminated with a blank line so cmd_update's
    status-substitution regex (which anchors on a trailing ``\\n\\n``) matches.
    """
    number = re.match(r'^(\d+)-', filename).group(1)
    (adr_dir / filename).write_text(f'= ADR-{number}: {title}\n\n== Status\n\n{status}\n\n')
