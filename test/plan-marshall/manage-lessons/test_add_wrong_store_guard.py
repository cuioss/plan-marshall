#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``add`` subcommand of manage-lessons.py."""


import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import _lessons_io
from _lessons_helpers import (
    cmd_add,
    cmd_from_error,
)


# =============================================================================
# Tier 2: cross-repo wrong-store refusal guard (deliverable 3)
# =============================================================================

class TestAddWrongStoreGuard:
    """``cmd_add`` / ``cmd_from_error`` refuse to file into a store that does not own the bundle."""

    def test_add_into_unowned_store_refuses_and_writes_nothing(self, tmp_path, monkeypatch):
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        result = cmd_add(
            Namespace(
                component='foreign-bundle:skill',
                category='bug',
                title='Rejected',
                bundle=None,
                allow_foreign_store=False,
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_store'
        assert 'foreign-bundle' in result['message']
        # Nothing was written into the store.
        assert not list(lessons_dir.glob('*.md'))

    def test_allow_foreign_store_bypasses_refusal(self, tmp_path, monkeypatch):
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        result = cmd_add(
            Namespace(
                component='foreign-bundle:skill',
                category='bug',
                title='Allowed Anyway',
                bundle=None,
                allow_foreign_store=True,
            )
        )

        assert result['status'] == 'success'
        assert Path(result['path']).exists()

    def test_owned_bundle_add_passes(self, tmp_path, monkeypatch):
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: True)

        result = cmd_add(
            Namespace(
                component='owned-bundle:skill',
                category='bug',
                title='Owned',
                bundle=None,
                allow_foreign_store=False,
            )
        )

        assert result['status'] == 'success'
        assert Path(result['path']).exists()

    def test_active_override_bypasses_guard(self, tmp_path):
        """Under a PLAN_BASE_DIR override the real guard is skipped (existing add tests unaffected)."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        # No ownership monkeypatch: the real predicate short-circuits True under
        # the override, so cmd_add succeeds even for a bundle the checkout may
        # not own — this is exactly why the PLAN_BASE_DIR-based suites stay green.
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='any-bundle:skill',
                    category='bug',
                    title='Override Bypass',
                    bundle=None,
                    allow_foreign_store=False,
                )
            )

        assert result['status'] == 'success'
        assert Path(result['path']).exists()

    def test_from_error_into_unowned_store_refuses(self, tmp_path, monkeypatch):
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        context = json.dumps({'component': 'foreign-bundle:skill', 'error': 'boom', 'solution': 'x'})
        result = cmd_from_error(Namespace(context=context, allow_foreign_store=False))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_store'
        assert not list(lessons_dir.glob('*.md'))

    def test_prefix_less_component_files_into_local_store_without_a_flag(self, tmp_path, monkeypatch):
        """A project-local lesson files into its own store with no --allow-foreign-store."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        # Ownership is patched False so the test cannot pass merely because the
        # PLAN_BASE_DIR override short-circuits the predicate to True.
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        result = cmd_add(
            Namespace(
                component='integration-tests',
                category='bug',
                title='Project Local',
                bundle=None,
                allow_foreign_store=False,
            )
        )

        assert result['status'] == 'success'
        assert Path(result['path']).exists()

    def test_malformed_component_add_returns_invalid_component(self, tmp_path, monkeypatch):
        """cmd_add reports a malformed component as invalid_component, never wrong_store."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        result = cmd_add(
            Namespace(
                component='bad/component',
                category='bug',
                title='Malformed',
                bundle=None,
                allow_foreign_store=False,
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_component'
        assert not list(lessons_dir.glob('*.md'))

    def test_malformed_component_from_error_returns_invalid_component(self, tmp_path, monkeypatch):
        """cmd_from_error reports a malformed component as invalid_component too.

        This path takes its component from untrusted JSON and bypasses argparse
        validation, so the guard is the only shape check it gets.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        context = json.dumps({'component': 'bad/component', 'error': 'boom', 'solution': 'x'})
        result = cmd_from_error(Namespace(context=context, allow_foreign_store=False))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_component'
        assert not list(lessons_dir.glob('*.md'))

    def test_from_error_explicit_non_string_component_returns_invalid_component(self, tmp_path, monkeypatch):
        """An explicitly-supplied non-string component must NOT be coerced to 'unknown'.

        Only an ABSENT component defaults. Coercing an explicit null/number would
        make the guard's isinstance check unreachable from this path and file a
        lesson under 'unknown' for input the contract calls malformed.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        for value in (None, 42, ['a']):
            context = json.dumps({'component': value, 'error': 'boom', 'solution': 'x'})
            result = cmd_from_error(Namespace(context=context, allow_foreign_store=False))

            assert result['status'] == 'error', f'{value!r} should be rejected'
            assert result['error'] == 'invalid_component', f'{value!r} should be invalid_component'

        assert not list(lessons_dir.glob('*.md'))

    def test_from_error_default_unknown_component_succeeds(self, tmp_path, monkeypatch):
        """The 'unknown' default is prefix-less, so the guard must not refuse it.

        Before the guard was scoped to prefixed components this path was refused
        100% of the time in production (outside a PLAN_BASE_DIR override), because
        no store can ever own a bundle named 'unknown'.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        context = json.dumps({'error': 'boom', 'solution': 'x'})
        result = cmd_from_error(Namespace(context=context, allow_foreign_store=False))

        assert result['status'] == 'success'
        assert list(lessons_dir.glob('*.md'))
