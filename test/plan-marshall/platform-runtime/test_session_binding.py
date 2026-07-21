#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for session_binding.py — the pure session->plan binding policy.

Covers:
  - shape validators (_valid_session_id, _valid_plan_id)
  - resolve_plan: read side (bound / unbound / malformed / empty)
  - bind: last-driven-wins unconditional write (never protects a differing
    live binding) and validation rejection
  - unbind: caller-scoped slot removal + empty-session-dir prune, idempotence,
    validation rejection, and the no-raise contract on I/O failure
  - doctor: reverse-index conflict scan, stale-slot detection, --fix GC, and
    the no-index.json invariant
"""
from __future__ import annotations

import pytest

# conftest.py sets up PYTHONPATH so the sibling module import resolves.
import session_binding

# Canonical session-UUID-shaped ids (all-hex, correct segment lengths).
SID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SID_C = "cccccccc-cccc-cccc-cccc-cccccccccccc"


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    """Redirect the per-session cache to a tmp dir; return the sessions root."""
    root = tmp_path / "sessions"
    monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", root)
    return root


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """chdir to a tmp project root so _plan_is_live resolves plan dirs there."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".plan" / "local" / "plans").mkdir(parents=True)
    return tmp_path


def _make_live_plan(project_root, plan_id: str) -> None:
    """Create a live (non-archived) plan directory under the project root."""
    (project_root / ".plan" / "local" / "plans" / plan_id).mkdir(parents=True, exist_ok=True)


# =============================================================================
# unbind — caller-scoped slot removal (the teardown counterpart of bind)
# =============================================================================


class TestUnbind:
    """Tests for :func:`session_binding.unbind`.

    ``unbind`` removes the caller's OWN ``active-plan`` slot and prunes the
    now-empty session directory. Same validation, same per-session scope, and
    the same best-effort / no-raise contract as ``bind``.
    """

    def test_unbind_removes_existing_slot_and_prunes_session_dir(self, cache):
        """An existing slot is removed and its now-empty session dir is pruned."""
        assert session_binding.bind(SID_A, "plan-a") is True
        assert (cache / SID_A / "active-plan").is_file()

        assert session_binding.unbind(SID_A) is True

        assert not (cache / SID_A / "active-plan").exists()
        assert not (cache / SID_A).exists()
        assert session_binding.resolve_plan(SID_A) is None

    def test_unbind_touches_only_the_callers_own_slot(self, cache):
        """A sibling session's binding survives the caller's unbind untouched."""
        session_binding.bind(SID_A, "plan-a")
        session_binding.bind(SID_B, "plan-b")

        session_binding.unbind(SID_A)

        assert session_binding.resolve_plan(SID_A) is None
        assert session_binding.resolve_plan(SID_B) == "plan-b"

    def test_unbind_is_idempotent_on_absent_slot(self, cache):
        """Unbinding an already-absent slot reports success and does not raise."""
        assert session_binding.unbind(SID_C) is True
        assert session_binding.unbind(SID_C) is True
        assert session_binding.resolve_plan(SID_C) is None

    @pytest.mark.parametrize(
        "bad",
        ["", "../../etc/passwd", "a/b", "a\\b", "..", ".", "x" * 121, "a\x00b"],
    )
    def test_unbind_rejects_malformed_session_id(self, cache, bad):
        """A malformed session id is rejected before any filesystem touch."""
        assert session_binding.unbind(bad) is False

    def test_unbind_returns_false_on_io_error(self, cache, monkeypatch):
        """An I/O error yields False rather than propagating — never raises."""
        session_binding.bind(SID_A, "plan-a")

        def _raise(*_args, **_kwargs):
            raise OSError(13, "Permission denied")

        monkeypatch.setattr(session_binding.Path, "unlink", _raise)

        assert session_binding.unbind(SID_A) is False

    def test_unbind_keeps_a_non_empty_session_dir(self, cache):
        """The dir prune is best-effort: a session dir holding other files stays."""
        session_binding.bind(SID_A, "plan-a")
        (cache / SID_A / "other-file").write_text("keep me", encoding="utf-8")

        assert session_binding.unbind(SID_A) is True

        assert not (cache / SID_A / "active-plan").exists()
        assert (cache / SID_A / "other-file").is_file()


# =============================================================================
# Shape validators
# =============================================================================


class TestValidators:
    """Tests for the single-segment session-id and plan-id shape validators.

    Both ids are single path segments under the cache root, so validation is
    single-segment safety (traversal rejection + length cap) — NOT a canonical
    UUID match.
    """

    def test_valid_session_id_accepts_canonical_uuid(self):
        """A canonical UUID (a safe single segment) passes validation."""
        assert session_binding._valid_session_id(SID_A) is True

    def test_valid_session_id_accepts_non_uuid_single_segment(self):
        """A non-UUID single segment (e.g. a test session id) is accepted — lax by design."""
        assert session_binding._valid_session_id("sess-tab-A") is True

    @pytest.mark.parametrize(
        "bad",
        ["", "../../etc/passwd", "a/b", "a\\b", "..", ".", "x" * 121, "a\x00b"],
    )
    def test_valid_session_id_rejects_unsafe(self, bad):
        """Empty, traversal, separator, null-byte, and over-length session ids are rejected."""
        assert session_binding._valid_session_id(bad) is False

    def test_valid_plan_id_accepts_simple(self):
        """A simple single-segment plan id passes validation."""
        assert session_binding._valid_plan_id("my-plan-123") is True

    @pytest.mark.parametrize(
        "bad",
        ["", "a/b", "a\\b", "..", ".", "x" * 121, "a\x00b"],
    )
    def test_valid_plan_id_rejects_unsafe(self, bad):
        """Empty, traversal, separator, null-byte, and over-length plan ids are rejected."""
        assert session_binding._valid_plan_id(bad) is False


# =============================================================================
# resolve_plan — read side
# =============================================================================


class TestResolvePlan:
    """Tests for the read side."""

    def test_unbound_returns_none(self, cache):
        """An unbound session (no cache file) resolves to None."""
        assert session_binding.resolve_plan(SID_A) is None

    def test_returns_bound_plan(self, cache):
        """After a bind, resolve returns the bound plan id."""
        session_binding.bind(SID_A, "plan-1")
        assert session_binding.resolve_plan(SID_A) == "plan-1"

    def test_malformed_session_id_returns_none(self, cache):
        """A malformed session id resolves to None without touching disk."""
        assert session_binding.resolve_plan("../evil") is None

    def test_empty_slot_file_returns_none(self, cache):
        """An empty active-plan file resolves to None (treated as unbound)."""
        slot = cache / SID_A / "active-plan"
        slot.parent.mkdir(parents=True)
        slot.write_text("   ", encoding="utf-8")
        assert session_binding.resolve_plan(SID_A) is None


# =============================================================================
# bind — last-driven-wins write side
# =============================================================================


class TestBind:
    """Tests for the last-driven-wins write policy."""

    def test_writes_slot(self, cache):
        """bind writes the caller's slot and returns True."""
        assert session_binding.bind(SID_A, "plan-1") is True
        assert (cache / SID_A / "active-plan").read_text(encoding="utf-8") == "plan-1"

    def test_last_driven_wins_overwrites_differing_binding(self, cache):
        """A second bind to a DIFFERENT plan overwrites — never protects the prior binding."""
        assert session_binding.bind(SID_A, "plan-1") is True
        assert session_binding.bind(SID_A, "plan-2") is True
        assert session_binding.resolve_plan(SID_A) == "plan-2"

    def test_idempotent_rebind_same_plan(self, cache):
        """Re-binding the same plan is idempotent and succeeds."""
        assert session_binding.bind(SID_A, "plan-1") is True
        assert session_binding.bind(SID_A, "plan-1") is True
        assert session_binding.resolve_plan(SID_A) == "plan-1"

    def test_rejects_invalid_session_id(self, cache):
        """bind rejects a malformed session id (returns False, writes nothing)."""
        assert session_binding.bind("../evil", "plan-1") is False
        assert not (cache).exists() or not any(cache.iterdir())

    def test_rejects_invalid_plan_id(self, cache):
        """bind rejects a traversal plan id (returns False, writes nothing)."""
        assert session_binding.bind(SID_A, "../evil") is False
        assert session_binding.resolve_plan(SID_A) is None


# =============================================================================
# doctor — reverse-index conflict scan + stale-slot GC
# =============================================================================


class TestDoctor:
    """Tests for the conflict/stale scan and the --fix GC path."""

    def test_single_binding_no_conflict(self, cache, project):
        """One session bound to one live plan reports no conflicts and no stale."""
        _make_live_plan(project, "plan-1")
        session_binding.bind(SID_A, "plan-1")
        report = session_binding.doctor()
        assert report["scanned"] == 1
        assert report["conflicts"] == []
        assert report["stale"] == []
        assert report["gc_removed"] == 0

    def test_detects_two_sessions_one_plan_conflict(self, cache, project):
        """Two live sessions bound to the same plan are flagged as a conflict."""
        _make_live_plan(project, "plan-1")
        session_binding.bind(SID_A, "plan-1")
        session_binding.bind(SID_B, "plan-1")
        report = session_binding.doctor()
        assert len(report["conflicts"]) == 1
        conflict = report["conflicts"][0]
        assert conflict["plan_id"] == "plan-1"
        assert sorted(conflict["sessions"]) == sorted([SID_A, SID_B])

    def test_distinct_plans_no_conflict(self, cache, project):
        """Two sessions bound to distinct plans report no conflict."""
        _make_live_plan(project, "plan-1")
        _make_live_plan(project, "plan-2")
        session_binding.bind(SID_A, "plan-1")
        session_binding.bind(SID_B, "plan-2")
        report = session_binding.doctor()
        assert report["conflicts"] == []

    def test_flags_stale_slot(self, cache, project):
        """A slot bound to an archived/deleted plan (no live dir) is flagged stale."""
        _make_live_plan(project, "live-plan")
        session_binding.bind(SID_A, "live-plan")
        session_binding.bind(SID_B, "gone-plan")  # no live dir → stale
        report = session_binding.doctor()
        stale_plans = {s["plan_id"] for s in report["stale"]}
        assert stale_plans == {"gone-plan"}

    def test_fix_gcs_stale_slot_preserves_live(self, cache, project):
        """--fix removes the stale slot but preserves the live-plan slot."""
        _make_live_plan(project, "live-plan")
        session_binding.bind(SID_A, "live-plan")
        session_binding.bind(SID_B, "gone-plan")
        report = session_binding.doctor(fix=True)
        assert report["gc_removed"] == 1
        assert session_binding.resolve_plan(SID_B) is None  # stale slot GC'd
        assert session_binding.resolve_plan(SID_A) == "live-plan"  # live preserved

    def test_fix_prunes_empty_session_dir(self, cache, project):
        """--fix removes the now-empty session directory, not just the active-plan file."""
        session_binding.bind(SID_B, "gone-plan")
        assert (cache / SID_B).is_dir()
        session_binding.doctor(fix=True)
        assert not (cache / SID_B / "active-plan").exists()  # slot file gone
        assert not (cache / SID_B).exists()  # empty parent dir pruned

    def test_no_index_json_written(self, cache, project):
        """doctor keeps no shared mutable index — no index.json is ever created."""
        _make_live_plan(project, "plan-1")
        session_binding.bind(SID_A, "plan-1")
        session_binding.doctor(fix=True)
        assert not (cache / "index.json").exists()
        assert not (cache.parent / "index.json").exists()

    def test_empty_cache_reports_zero(self, cache, project):
        """A doctor run over an empty cache reports nothing scanned."""
        report = session_binding.doctor()
        assert report["scanned"] == 0
        assert report["conflicts"] == []
        assert report["stale"] == []
