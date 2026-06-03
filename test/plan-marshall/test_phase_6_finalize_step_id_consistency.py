#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Regression coverage for the phase-6-finalize step-ID consistency contract
introduced by deliverable 2 of plan
``target-claude-staleness-silently-halts-phase-6-en`` (lesson
``2026-05-20-08-005``).

The bug: ``marshal.json``'s phase-6-finalize manifest lists project steps
under fully-qualified IDs (``project:finalize-step-pre-submission-
self-review``, ``project:finalize-step-plugin-doctor``), but the recording
side was inconsistent — the ``pre-submission-self-review`` workflow doc
recorded under the bare name, and the ``plugin-doctor`` wrapper did not call
``mark-step-done`` at all. The ``phase_steps_complete`` handshake invariant
therefore raised ``PhaseStepsIncomplete`` (or the renderer emitted
``<missing display_detail>``) at the end of every finalize run that
exercised those steps, even when every step actually succeeded.

These tests pin the end-to-end contract:

1. ``_parse_required_steps`` accepts ``project:``-prefixed bullets verbatim
   alongside bare bullets (parser is shape-agnostic).
2. ``_capture_phase_steps_complete`` matches a prefixed required-step list
   against a prefixed recorded entry — no ``PhaseStepsIncomplete``.
3. ``_capture_phase_steps_complete`` correctly raises ``PhaseStepsIncomplete``
   when the manifest declares a prefixed required step but the recorded
   entry is keyed by the bare suffix — the regression that originally bit
   lesson ``2026-05-20-08-005``. Reverting deliverable 2's fix on any of
   the wrappers re-introduces this exact failure mode.
4. The renderer's exact-then-strip-prefix lookup helper (specified in
   ``output-template.md`` § Emission step 5) returns the bare entry when
   the manifest carries a ``project:`` prefixed key and the recorded
   ``phase_steps`` dict is keyed bare — the legacy-tolerant fallback. The
   renderer is currently a specification (no Python module to import), so
   the test colocates a small helper implementation that mirrors the spec
   and asserts the contract behaviour.
5. The three finalize-step wrappers carry at least one ``mark-step-done
   --step project:finalize-step-{name}`` invocation. Removing the calls is
   the failure mode that the recording side originally had.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

# Load _invariants the same way the existing phase-handshake test split
# does — _invariants is a private module under the plan-marshall scripts
# directory and is not on PYTHONPATH at test-collection time.
_PHASE_HANDSHAKE_SCRIPT = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
_SCRIPTS_DIR = _PHASE_HANDSHAKE_SCRIPT.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _invariants as inv  # noqa: E402

# ---------------------------------------------------------------------------
# Source anchors used by tests 4 and 5
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_PROJECT_SKILLS = _REPO_ROOT / '.claude' / 'skills'
_BUNDLE_ROOT = _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall'
_PRE_SUBMISSION_WORKFLOW = (
    _BUNDLE_ROOT
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'pre-submission-self-review.md'
)


# ---------------------------------------------------------------------------
# Test 1: parser accepts prefixed bullets
# ---------------------------------------------------------------------------


def test_required_steps_parser_accepts_prefixed_ids(tmp_path: Path) -> None:
    """``_parse_required_steps`` is shape-agnostic — it reads bullets verbatim.

    Asserts that a ``required-steps.md`` containing both bare and
    ``project:``-prefixed bullets parses into a list that preserves both
    shapes verbatim. The parser MUST NOT normalize the prefix.
    """
    required = tmp_path / 'required-steps.md'
    required.write_text(
        '# Required steps\n'
        '\n'
        '- project:finalize-step-pre-submission-self-review\n'
        '- commit-push\n'
        '- create-pr\n'
        '- default:archive-plan\n',
        encoding='utf-8',
    )

    parsed = inv._parse_required_steps(required)

    assert parsed == [
        'project:finalize-step-pre-submission-self-review',
        'commit-push',
        'create-pr',
        'default:archive-plan',
    ]


# ---------------------------------------------------------------------------
# Test 2: capture passes when prefixed required matches prefixed recorded
# ---------------------------------------------------------------------------


def test_phase_steps_complete_matches_manifest_id_when_recorded_prefixed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """End-to-end happy path: ``required-steps.md`` and ``phase_steps`` share
    the same prefixed key — ``_capture_phase_steps_complete`` returns the
    deterministic hash and does NOT raise.
    """
    required = tmp_path / 'required-steps.md'
    required.write_text(
        '- project:finalize-step-pre-submission-self-review\n'
        '- commit-push\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: required)

    metadata = {
        'phase_steps': {
            '6-finalize': {
                'project:finalize-step-pre-submission-self-review': {
                    'outcome': 'done',
                    'display_detail': 'self-review clean',
                },
                'commit-push': {
                    'outcome': 'done',
                    'display_detail': 'committed abc123',
                },
            }
        }
    }

    result = inv._capture_phase_steps_complete('pid', metadata, '6-finalize')

    # Stable 16-char SHA256 prefix — matches the existing capture-success
    # assertions in test_phase_handshake_phase_steps.py.
    assert isinstance(result, str)
    assert len(result) == 16


# ---------------------------------------------------------------------------
# Test 3: regression — prefixed required, bare recorded → raises
# ---------------------------------------------------------------------------


def test_phase_steps_complete_fails_when_required_prefixed_but_recorded_bare(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The exact failure mode that bit lesson ``2026-05-20-08-005``.

    ``required-steps.md`` lists ``project:finalize-step-pre-submission-self-
    review`` (prefixed), but the recorded entry on
    ``metadata.phase_steps['6-finalize']`` is keyed by the bare suffix
    ``pre-submission-self-review`` (legacy drift). The handshake invariant
    MUST raise ``PhaseStepsIncomplete`` with the prefixed step in
    ``excinfo.value.missing`` — the bare key is invisible to the
    required-step lookup, so the step counts as missing.

    Reverting deliverable 2's normalization (e.g. restoring the bare
    ``--step pre-submission-self-review`` invocation in the workflow doc)
    re-introduces this exact failure: the recorded key drifts to the bare
    form while the manifest keeps the prefixed form, and the handshake
    refuses to advance. This test is the regression that would have caught
    the original defect.
    """
    required = tmp_path / 'required-steps.md'
    required.write_text(
        '- project:finalize-step-pre-submission-self-review\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: required)

    metadata = {
        'phase_steps': {
            '6-finalize': {
                'pre-submission-self-review': {
                    'outcome': 'done',
                    'display_detail': 'self-review clean',
                },
            }
        }
    }

    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '6-finalize')

    assert excinfo.value.missing == ['project:finalize-step-pre-submission-self-review']
    assert excinfo.value.not_done == []
    assert excinfo.value.legacy_format == []


# ---------------------------------------------------------------------------
# Test 4: renderer prefix-strip lookup contract (spec-anchored)
# ---------------------------------------------------------------------------


def _renderer_lookup(phase_steps: dict[str, dict], manifest_step_id: str) -> dict | None:
    """Reference implementation of the renderer lookup contract specified in
    ``output-template.md`` § Emission step 5.

    1. Attempt exact match against ``manifest_step_id``.
    2. If exact miss AND id begins with ``project:`` or ``default:``,
       strip the prefix and retry against the bare suffix.
    3. Return the matched record dict, or ``None`` if both lookups miss.
    """
    record = phase_steps.get(manifest_step_id)
    if record is not None:
        return record
    for prefix in ('project:', 'default:'):
        if manifest_step_id.startswith(prefix):
            bare = manifest_step_id[len(prefix):]
            return phase_steps.get(bare)
    return None


def test_renderer_lookup_strips_project_prefix_on_miss() -> None:
    """The renderer's exact-then-strip-prefix lookup contract.

    Spec: ``output-template.md`` § Emission step 5 says the renderer first
    attempts an exact match, and only on miss strips a leading ``project:``
    or ``default:`` prefix and retries the lookup against the bare suffix.

    Test exercises both branches of the contract:

    - exact-match branch: prefixed key in ``phase_steps`` is returned
      verbatim.
    - prefix-strip branch: ``phase_steps`` is keyed bare while the manifest
      carries the prefixed form — the bare entry is returned.
    - both-miss branch: neither key resolves → ``None`` (caller emits the
      ``<missing display_detail>`` placeholder).
    """
    # Exact-match branch: prefixed manifest key matches prefixed record key.
    phase_steps_prefixed = {
        'project:finalize-step-plugin-doctor': {
            'outcome': 'done',
            'display_detail': 'plugin-doctor clean: 80 skills scanned',
        }
    }
    record = _renderer_lookup(phase_steps_prefixed, 'project:finalize-step-plugin-doctor')
    assert record is not None
    assert record['display_detail'] == 'plugin-doctor clean: 80 skills scanned'

    # Prefix-strip branch: manifest is prefixed, record is bare.
    phase_steps_bare = {
        'finalize-step-plugin-doctor': {
            'outcome': 'done',
            'display_detail': 'plugin-doctor clean: 80 skills scanned',
        }
    }
    record = _renderer_lookup(phase_steps_bare, 'project:finalize-step-plugin-doctor')
    assert record is not None
    assert record['display_detail'] == 'plugin-doctor clean: 80 skills scanned'

    # Default-prefix variant.
    phase_steps_default_bare = {
        'commit-push': {'outcome': 'done', 'display_detail': 'committed abc123'},
    }
    record = _renderer_lookup(phase_steps_default_bare, 'default:commit-push')
    assert record is not None
    assert record['display_detail'] == 'committed abc123'

    # Both-miss branch: neither key resolves.
    record = _renderer_lookup(phase_steps_bare, 'project:finalize-step-other')
    assert record is None


# ---------------------------------------------------------------------------
# Test 5: wrappers / workflow contain mark-step-done --step project: refs
# ---------------------------------------------------------------------------


def test_finalize_step_wrappers_mark_step_done_calls_present() -> None:
    """Structural regression: removing the canonical ``mark-step-done --step
    project:finalize-step-{name}`` calls re-introduces the lesson
    ``2026-05-20-08-005`` defect (renderer emits ``<missing display_detail>``
    or handshake raises ``PhaseStepsIncomplete``).

    Two sources MUST each carry at least one ``mark-step-done --step
    project:finalize-step-{name}`` invocation:

    - ``.claude/skills/finalize-step-plugin-doctor/SKILL.md`` — recording
      lives directly in the wrapper.
    - ``marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/
      pre-submission-self-review.md`` — recording lives in the dispatched
      workflow body, not in the project-local ``.claude/skills/finalize-
      step-pre-submission-self-review/SKILL.md`` wrapper (the wrapper
      delegates to this workflow doc per its Workflow section).

    Each source is checked for both the ``mark-step-done`` script call and
    the canonical ``--step project:finalize-step-{name}`` argument; missing
    either signals that deliverable 2's normalization has been reverted.
    """
    sources: list[tuple[Path, str]] = [
        (
            _PROJECT_SKILLS / 'finalize-step-plugin-doctor' / 'SKILL.md',
            'project:finalize-step-plugin-doctor',
        ),
        (
            _PRE_SUBMISSION_WORKFLOW,
            'project:finalize-step-pre-submission-self-review',
        ),
    ]

    for source_path, canonical_step_id in sources:
        assert source_path.is_file(), f'expected source not found: {source_path}'
        content = source_path.read_text(encoding='utf-8')
        assert 'mark-step-done' in content, (
            f'{source_path} missing mark-step-done invocation — recording side '
            f'cannot satisfy the phase_steps_complete handshake invariant'
        )
        assert f'--step {canonical_step_id}' in content, (
            f'{source_path} missing canonical --step {canonical_step_id} argument — '
            f'recorded key would drift to bare form, re-introducing lesson '
            f'2026-05-20-08-005 (manifest ID vs phase_steps key divergence)'
        )
