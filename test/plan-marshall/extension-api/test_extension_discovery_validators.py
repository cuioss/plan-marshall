#!/usr/bin/env python3
"""Sanity tests asserting extension_discovery.py exposes no in-scope identifier flags.

TASK-3 of the canonical-identifier-validator migration audited
``extension_discovery.py`` and concluded it is AUDIT-ONLY: it does not declare
any identifier flag that is in the canonical migration scope (no
``--plan-id``, ``--lesson-id``, ``--session-id``, ``--task-number``,
``--task-id``, ``--component``, ``--hash-id``, ``--phase``,
``--field``, ``--module``, ``--package``, ``--domain``, ``--name``).

The script's only argument is ``--project-dir``, which is a Bucket B
infrastructure flag that intentionally bypasses canonical validation
(it must accept arbitrary absolute paths).

These tests are a regression net: if a future change accidentally
re-introduces an in-scope identifier flag without wiring up the
canonical validator + ``parse_args_with_toon_errors`` plumbing, the
audit-only assumption silently breaks. Failing the assertion forces
the next migration pass to either wire the validator or document the
exemption explicitly.
"""

from __future__ import annotations

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'extension-api', 'extension_discovery.py')


# Canonical identifier flags governed by ``input_validation.add_*_arg`` helpers.
_IN_SCOPE_FLAGS = (
    '--plan-id',
    '--lesson-id',
    '--session-id',
    '--task-number',
    '--task-id',
    '--component',
    '--hash-id',
    '--phase',
    '--field',
    '--module',
    '--package',
    '--domain',
    '--name',
)


def test_extension_discovery_declares_no_in_scope_identifier_flags() -> None:
    """``extension_discovery.py`` MUST NOT declare any canonical identifier flag.

    If a future change introduces one of the canonical flags without
    wiring ``parse_args_with_toon_errors``, the audit-only classification
    is no longer accurate and the migration pass must be revisited.
    """
    source = SCRIPT_PATH.read_text(encoding='utf-8')

    for flag in _IN_SCOPE_FLAGS:
        # Match the flag as a string literal in the source — looking for
        # ``add_argument('--plan-id', ...)``-style calls. We do NOT match
        # docstring/help mentions; those use bare flag names not wrapped in
        # quotes adjacent to ``add_argument``. The check is intentionally
        # conservative: false positives here would correctly flag a real
        # in-scope flag, false negatives would only happen if someone
        # adds the flag via ``setattr``-style metaprogramming, which no
        # marketplace script does today.
        needle = f"'{flag}'"
        if needle in source:
            # Find the surrounding context to confirm it's an
            # ``add_argument`` call rather than a docstring example.
            idx = source.find(needle)
            window_start = max(0, idx - 80)
            window = source[window_start:idx]
            assert 'add_argument' not in window, (
                f'extension_discovery.py declares in-scope flag {flag!r} but the audit-only '
                f'classification (TASK-3) assumes it does not. Either wire '
                f'parse_args_with_toon_errors via input_validation helpers, or update the '
                f'audit notes to reflect the new flag.'
            )


def test_extension_discovery_does_not_use_input_validation_helpers() -> None:
    """``extension_discovery.py`` MUST NOT import any ``add_*_arg`` helper.

    These helpers exist exclusively to wire canonical identifier flags
    into argparse. Their presence in this script would imply an in-scope
    flag is being declared — contradicting the audit-only classification.
    """
    source = SCRIPT_PATH.read_text(encoding='utf-8')

    forbidden_imports = (
        'add_plan_id_arg',
        'add_lesson_id_arg',
        'add_session_id_arg',
        'add_task_number_arg',
        'add_task_id_arg',
        'add_component_arg',
        'add_hash_id_arg',
        'add_phase_arg',
        'add_field_arg',
        'add_module_arg',
        'add_package_arg',
        'add_domain_arg',
        'add_name_arg',
    )
    for symbol in forbidden_imports:
        assert symbol not in source, (
            f'extension_discovery.py imports {symbol!r}, which implies a canonical '
            f'identifier flag was added. The audit-only classification (TASK-3) is '
            f'no longer accurate; either wire parse_args_with_toon_errors or update '
            f'the audit notes.'
        )
