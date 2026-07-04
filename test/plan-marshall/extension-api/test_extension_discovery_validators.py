#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
from conftest import get_script_path

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
    """``extension_discovery.py`` MUST NOT import any ``add_*_arg`` helper from ``input_validation``.

    These helpers exist exclusively to wire canonical identifier flags
    into argparse. Their presence in this script would imply an in-scope
    flag is being declared — contradicting the audit-only classification.

    NOTE: ``_routing.add_plan_id_arg`` (from ``resolve_project_dir``) is
    permitted — it adds the Bucket B routing flag, not a canonical
    identifier validator. The two modules export functions with the same
    short name; the test is scoped to the ``input_validation`` import.
    """
    source = SCRIPT_PATH.read_text(encoding='utf-8')

    # Reject ``from input_validation import ... add_*_arg ...`` style and
    # ``import input_validation`` followed by ``input_validation.add_*_arg``
    # access. Both forms would indicate a canonical validator was wired in.
    forbidden_helpers_from_input_validation = (
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

    # Locate the input_validation import block (if any).
    in_input_validation_block = False
    forbidden_in_iv_block: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('from input_validation import') or stripped == 'import input_validation':
            in_input_validation_block = True
            forbidden_in_iv_block.append(line)
            continue
        if in_input_validation_block:
            # Continuation line inside the parenthesized import.
            forbidden_in_iv_block.append(line)
            if stripped.endswith(')') or (stripped and not stripped.endswith((',', '('))):
                in_input_validation_block = False

    iv_block_text = '\n'.join(forbidden_in_iv_block)
    for symbol in forbidden_helpers_from_input_validation:
        assert symbol not in iv_block_text, (
            f'extension_discovery.py imports {symbol!r} from input_validation, which implies '
            f'a canonical identifier flag was added. The audit-only classification (TASK-3) '
            f'is no longer accurate; either wire parse_args_with_toon_errors or update the '
            f'audit notes.'
        )

    # Also reject ``input_validation.add_*_arg`` attribute access.
    for symbol in forbidden_helpers_from_input_validation:
        assert f'input_validation.{symbol}' not in source, (
            f'extension_discovery.py uses input_validation.{symbol!r}, which implies a '
            f'canonical identifier flag was added.'
        )


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing contract
# =============================================================================
#
# extension_discovery.py is a Bucket B script — it accepts ``--project-dir``
# AND ``--plan-id`` via ``_routing.add_plan_id_arg`` (the routing flag, not
# the canonical identifier validator). The TASK-10 implementation wired
# ``resolve_project_dir`` into the ``apply-config-defaults`` subcommand.
# These tests pin that wiring so a future regression that drops one of
# the routing flags fails loudly.

from conftest import run_script  # noqa: E402


def test_extension_discovery_imports_routing_helpers() -> None:
    """The script MUST import ``resolve_project_dir`` to enforce the two-state contract."""
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    # The canonical wiring imports the helper module under a known alias.
    assert 'import resolve_project_dir' in source, (
        'extension_discovery.py must import resolve_project_dir to enforce '
        'the two-state --plan-id / --project-dir routing contract.'
    )


def test_extension_discovery_calls_resolve_project_dir() -> None:
    """The script MUST call ``resolve_project_dir`` before any handler reads project_dir."""
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    # The TASK-10 wiring uses the alias ``_routing.resolve_project_dir(...)``
    # — accept either form to avoid coupling tests to the exact alias.
    assert 'resolve_project_dir(' in source, (
        'extension_discovery.py must invoke resolve_project_dir(...) to '
        'apply the two-state routing contract.'
    )


def test_extension_discovery_emits_mutually_exclusive_error_payload() -> None:
    """The script MUST surface ``mutually_exclusive_args`` via emit_mutually_exclusive_error."""
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    assert 'emit_mutually_exclusive_error' in source, (
        'extension_discovery.py must call emit_mutually_exclusive_error to '
        'surface the canonical TOON error payload when both routing flags are set.'
    )


def test_extension_discovery_emits_worktree_resolution_error_payload() -> None:
    """The script MUST surface ``worktree_resolution_failed`` via emit_worktree_error."""
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    assert 'emit_worktree_error' in source, (
        'extension_discovery.py must call emit_worktree_error to surface '
        'the canonical TOON error payload when --plan-id resolution fails.'
    )


def test_extension_discovery_help_declares_routing_flag_pair() -> None:
    """End-to-end: ``apply-config-defaults --help`` MUST declare both --project-dir and --plan-id."""
    result = run_script(SCRIPT_PATH, 'apply-config-defaults', '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert '--plan-id' in result.stdout, 'apply-config-defaults must declare --plan-id'
    assert '--project-dir' in result.stdout, 'apply-config-defaults must keep --project-dir as escape hatch'


def test_extension_discovery_rejects_both_routing_flags(tmp_path) -> None:
    """End-to-end: passing both --plan-id and --project-dir → mutually_exclusive_args."""
    result = run_script(
        SCRIPT_PATH,
        'apply-config-defaults',
        '--plan-id',
        'task-routing-canonical',
        '--project-dir',
        str(tmp_path),
    )
    # The script emits a TOON error payload on stdout.
    assert 'mutually_exclusive_args' in result.stdout, (
        f'Expected mutually_exclusive_args TOON error, got: {result.stdout!r}'
    )
