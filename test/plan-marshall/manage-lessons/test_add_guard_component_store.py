#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``add`` subcommand of manage-lessons.py."""


import _lessons_io
import file_ops
import marketplace_paths


# =============================================================================
# Tier 2: cross-repo wrong-store refusal guard (deliverable 3)
# =============================================================================


class TestMainAnchoredStoreOwnsBundle:
    """``marketplace_paths.main_anchored_store_owns_bundle`` repo-ownership predicate."""

    def test_override_short_circuits_true(self, tmp_path, monkeypatch):
        """A PLAN_BASE_DIR override reports ownership True without touching git."""
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)

        assert marketplace_paths.main_anchored_store_owns_bundle('any-bundle') is True

    def test_owns_bundle_when_source_dir_exists(self, tmp_path, monkeypatch):
        """Without an override, ownership is the existence of the bundle source dir."""
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        monkeypatch.setattr(marketplace_paths, '_main_checkout_root', lambda: tmp_path)
        (tmp_path / 'marketplace' / 'bundles' / 'owned-bundle').mkdir(parents=True)

        assert marketplace_paths.main_anchored_store_owns_bundle('owned-bundle') is True
        assert marketplace_paths.main_anchored_store_owns_bundle('foreign-bundle') is False


class TestGuardComponentStoreMatch:
    """``_lessons_io.guard_component_store_match`` raise/return contract."""

    def test_raises_when_store_does_not_own_bundle(self, monkeypatch):
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        try:
            _lessons_io.guard_component_store_match('foreign:skill', allow_foreign=False)
        except _lessons_io.WrongStoreError as exc:
            assert 'foreign' in str(exc)
        else:  # pragma: no cover - the guard must raise
            raise AssertionError('expected WrongStoreError')

    def test_returns_when_store_owns_bundle(self, monkeypatch):
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: True)

        # No exception → guard is satisfied.
        _lessons_io.guard_component_store_match('owned:skill', allow_foreign=False)

    def test_allow_foreign_bypasses_ownership_check(self, monkeypatch):
        def _boom(bundle):  # pragma: no cover - must not be consulted
            raise AssertionError('ownership must not be consulted when allow_foreign is True')

        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', _boom)

        _lessons_io.guard_component_store_match('foreign:skill', allow_foreign=True)

    def test_prefix_less_component_is_project_local_and_never_consults_ownership(self, monkeypatch):
        """A prefix-less component names no bundle, so ownership is not a question to ask.

        The predicate is replaced with a callable that fails the test if invoked —
        asserting the branch is skipped outright rather than merely happening to
        return True.
        """

        def _boom(bundle):  # pragma: no cover - must not be consulted
            raise AssertionError('ownership must not be consulted for a prefix-less component')

        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', _boom)

        # No exception, no flag → a project-local lesson files into its own store.
        _lessons_io.guard_component_store_match('integration-tests', allow_foreign=False)

    def test_prefixed_foreign_bundle_is_still_refused_without_the_flag(self, monkeypatch):
        """The regression that matters: scoping the guard must not turn it off."""
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        try:
            _lessons_io.guard_component_store_match('foreign-bundle:skill', allow_foreign=False)
        except _lessons_io.WrongStoreError as exc:
            assert 'foreign-bundle' in str(exc)
        else:  # pragma: no cover - the guard must still raise
            raise AssertionError('expected WrongStoreError for a prefixed foreign bundle')

    def test_refusal_message_names_the_bundle_prefix_not_the_whole_component(self, monkeypatch):
        """The refusal must state a true reason: the named value really is a bundle."""
        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', lambda bundle: False)

        try:
            _lessons_io.guard_component_store_match('foreign-bundle:some-skill', allow_foreign=False)
        except _lessons_io.WrongStoreError as exc:
            message = str(exc)
            assert "does not own bundle 'foreign-bundle'" in message
            # The bundle-hood claim is made about the prefix only — never about
            # the full component notation.
            assert "does not own bundle 'foreign-bundle:some-skill'" not in message
        else:  # pragma: no cover - the guard must raise
            raise AssertionError('expected WrongStoreError')

    def test_malformed_component_is_rejected_as_malformed(self, monkeypatch):
        """A value failing COMPONENT_RE is malformed, not foreign — and says so."""

        def _boom(bundle):  # pragma: no cover - shape check precedes ownership
            raise AssertionError('ownership must not be consulted for a malformed component')

        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', _boom)

        try:
            _lessons_io.guard_component_store_match('bad/component', allow_foreign=False)
        except _lessons_io.MalformedComponentError as exc:
            assert 'bad/component' in str(exc)
        else:  # pragma: no cover - the guard must raise
            raise AssertionError('expected MalformedComponentError')

    def test_trailing_newline_component_is_malformed(self, monkeypatch):
        """`$` matches before a trailing newline, so `match` would accept this.

        Pins the fullmatch semantics: a component ending in a newline is malformed
        even though every character before it is well-formed.
        """

        def _boom(bundle):  # pragma: no cover - shape check precedes ownership
            raise AssertionError('ownership must not be consulted for a malformed component')

        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', _boom)

        try:
            _lessons_io.guard_component_store_match('integration-tests\n', allow_foreign=False)
        except _lessons_io.MalformedComponentError:
            pass
        else:  # pragma: no cover - the guard must raise
            raise AssertionError('expected MalformedComponentError for a trailing newline')

    def test_non_string_component_is_malformed(self, monkeypatch):
        """A non-string component is malformed, not foreign."""

        def _boom(bundle):  # pragma: no cover - shape check precedes ownership
            raise AssertionError('ownership must not be consulted for a non-string component')

        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', _boom)

        for value in (None, 42, ['a']):
            try:
                _lessons_io.guard_component_store_match(value, allow_foreign=False)
            except _lessons_io.MalformedComponentError:
                continue
            raise AssertionError(f'expected MalformedComponentError for {value!r}')

    def test_allow_foreign_does_not_launder_a_malformed_component(self, monkeypatch):
        """The shape check runs BEFORE the allow_foreign bypass."""

        def _boom(bundle):  # pragma: no cover - shape check precedes ownership
            raise AssertionError('ownership must not be consulted for a malformed component')

        monkeypatch.setattr(_lessons_io, 'main_anchored_store_owns_bundle', _boom)

        try:
            _lessons_io.guard_component_store_match('bad/component', allow_foreign=True)
        except _lessons_io.MalformedComponentError:
            pass
        else:  # pragma: no cover - the override must not bypass the shape check
            raise AssertionError('expected MalformedComponentError even with allow_foreign=True')
