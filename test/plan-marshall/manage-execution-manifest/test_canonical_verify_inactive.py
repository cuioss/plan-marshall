#!/usr/bin/env python3
"""Tests for the canonical-verify footprint pre-filter (inactive case).

``_apply_canonical_verify_inactive`` is the generic, canonical-agnostic
footprint pre-filter: it drops a composed phase-5 ``default:verify:{canonical}``
step when its derived role is a footprint-gated role (``integration`` / ``e2e``)
AND the live, non-empty footprint carries no path of that role. The gate is
driven entirely by the ``_CANONICAL_TO_ROLE`` derivation and the
``_FOOTPRINT_GATED_CANONICAL_ROLES`` membership table — there is no per-canonical
branch in the code path.

Safety against compose-time emptiness: an empty footprint (the normal case
during early compose at phase-4-plan, before the worktree is materialised)
makes the pre-filter a no-op so every canonical survives. The gate only fires
against a NON-empty footprint that genuinely lacks the gating role's paths.

These tests drive ``_apply_canonical_verify_inactive`` directly with a
monkeypatched ``_resolve_footprint`` so the prefilter logic is exercised
deterministically without a live worktree or git history. ``_footprint_has_role``
is also covered directly.
"""

import importlib.util
from pathlib import Path

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_canonical_inactive', 'manage-execution-manifest.py')
_apply_canonical_verify_inactive = _mem._apply_canonical_verify_inactive
_footprint_has_role = _mem._footprint_has_role
_FOOTPRINT_GATED_CANONICAL_ROLES = _mem._FOOTPRINT_GATED_CANONICAL_ROLES


_PLAN_ID = 'canonical-inactive'


def _patch_footprint(monkeypatch, footprint: list[str]) -> None:
    """Force ``_resolve_footprint`` to return ``footprint`` for any plan id."""
    monkeypatch.setattr(_mem, '_resolve_footprint', lambda plan_id: list(footprint))


class TestFootprintHasRole:
    """``_footprint_has_role`` is a lowercased substring test over the footprint."""

    def test_matches_integration_marker_in_path(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role(['src/test/FooIT.java'], markers) is True

    def test_matches_e2e_marker_in_path(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['e2e']
        assert _footprint_has_role(['tests/e2e/test_flow.py'], markers) is True

    def test_no_match_returns_false(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role(['src/main/Foo.java', 'README.md'], markers) is False

    def test_match_is_case_insensitive(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        # The marker ``it.java`` is lowercased; an uppercase path still matches.
        assert _footprint_has_role(['SRC/TEST/BARIT.JAVA'], markers) is True

    def test_empty_footprint_returns_false(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role([], markers) is False


class TestCanonicalVerifyInactiveDrop:
    """Footprint-gated canonical-verify steps drop when their role is absent."""

    def test_integration_step_dropped_when_footprint_lacks_integration_paths(self, monkeypatch):
        """``default:verify:integration-tests`` drops when the non-empty footprint
        has no integration-role path."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java', 'README.md'])
        kept, dropped = _apply_canonical_verify_inactive(
            ['default:verify:integration-tests'], _PLAN_ID, {}
        )
        assert kept == []
        assert dropped == ['default:verify:integration-tests']

    def test_e2e_step_dropped_when_footprint_lacks_e2e_paths(self, monkeypatch):
        """``default:verify:e2e`` drops when the non-empty footprint has no e2e path."""
        _patch_footprint(monkeypatch, ['src/main/app.py', 'docs/guide.md'])
        kept, dropped = _apply_canonical_verify_inactive(['default:verify:e2e'], _PLAN_ID, {})
        assert kept == []
        assert dropped == ['default:verify:e2e']

    def test_bare_canonical_verify_form_is_also_gated(self, monkeypatch):
        """The bare ``verify:{canonical}`` form is gated identically to the prefixed form."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        kept, dropped = _apply_canonical_verify_inactive(['verify:integration-tests'], _PLAN_ID, {})
        assert kept == []
        assert dropped == ['verify:integration-tests']

    def test_only_gated_step_dropped_others_kept(self, monkeypatch):
        """Among mixed steps, only the footprint-gated canonical with no matching
        path is dropped; core canonical-verify steps survive."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        steps = [
            'default:verify:quality-gate',
            'default:verify:integration-tests',
            'default:verify:module-tests',
        ]
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert dropped == ['default:verify:integration-tests']
        assert kept == ['default:verify:quality-gate', 'default:verify:module-tests']


class TestCanonicalVerifyInactiveKeep:
    """Steps survive the pre-filter when the gate does not fire."""

    def test_integration_step_kept_when_footprint_has_integration_path(self, monkeypatch):
        """A non-empty footprint WITH an integration-role path keeps the step."""
        _patch_footprint(monkeypatch, ['src/test/java/FooIT.java'])
        kept, dropped = _apply_canonical_verify_inactive(
            ['default:verify:integration-tests'], _PLAN_ID, {}
        )
        assert kept == ['default:verify:integration-tests']
        assert dropped == []

    def test_empty_footprint_is_a_noop_every_canonical_survives(self, monkeypatch):
        """An empty footprint (early compose, pre-materialisation) keeps all steps.

        This is the compose-time-emptiness safety contract: the gate must NOT
        fire against an empty footprint, otherwise a still-unmaterialised plan
        would lose its integration/e2e gate before the worktree even exists.
        """
        _patch_footprint(monkeypatch, [])
        steps = ['default:verify:integration-tests', 'default:verify:e2e']
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_core_roles_never_footprint_gated(self, monkeypatch):
        """``quality-gate`` / ``module-tests`` / ``coverage`` canonicals are NEVER
        footprint-gated — they survive even when the footprint lacks their paths."""
        _patch_footprint(monkeypatch, ['unrelated/path.txt'])
        steps = [
            'default:verify:quality-gate',
            'default:verify:module-tests',
            'default:verify:coverage',
        ]
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_non_canonical_and_external_steps_pass_through_untouched(self, monkeypatch):
        """Non-canonical-verify default steps and external (project:/bundle:skill)
        steps are passed through verbatim — only ``verify:{canonical}`` integration
        / e2e steps are footprint-gated."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        steps = [
            'default:some-non-verify-step',
            'another-bare-step',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
        ]
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_unknown_canonical_passes_through(self, monkeypatch):
        """A ``default:verify:{unknown}`` whose canonical is not in the table has
        role None → not footprint-gated → survives untouched."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        kept, dropped = _apply_canonical_verify_inactive(['default:verify:not-a-canonical'], _PLAN_ID, {})
        assert kept == ['default:verify:not-a-canonical']
        assert dropped == []
