#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The phase-6-finalize step-ID consistency contract.

The failure it guards: ``marshal.json``'s phase-6-finalize manifest lists steps
under fully-qualified IDs (``default:functional-review``,
``project:finalize-step-plugin-doctor``), but the recording side was
inconsistent — a workflow doc recorded under the bare name, and the
``plugin-doctor`` wrapper did not call ``mark-step-done`` at all. The ``phase_steps_complete`` handshake invariant
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
   entry is keyed by the bare suffix. Dropping the canonical
   ``mark-step-done`` call on any wrapper re-introduces this failure mode.
4. The renderer's exact-then-strip-prefix lookup helper (specified in
   ``output-template.md`` § Emission step 5) returns the bare entry when
   the manifest carries a ``project:`` prefixed key and the recorded
   ``phase_steps`` dict is keyed bare — the legacy-tolerant fallback. The
   renderer is currently a specification (no Python module to import), so
   the test colocates a small helper implementation that mirrors the spec
   and asserts the contract behaviour.
5. The plugin-doctor wrapper and both review workflows carry at least one
   ``mark-step-done --step {canonical-id}`` invocation. Removing the calls is
   the failure mode that the recording side originally had.
"""

from __future__ import annotations

from pathlib import Path

# ``_invariants`` is a private module under the plan-marshall scripts directory,
# which the root conftest puts on ``sys.path`` before any test module is imported
# — so it resolves plainly, and this suite holds the same instance the production
# path does.
import _invariants as inv
import pytest

from conftest import PROJECT_ROOT, get_skill_dir

# ---------------------------------------------------------------------------
# Source anchors used by tests 4 and 5
# ---------------------------------------------------------------------------

_PROJECT_SKILLS = PROJECT_ROOT / '.claude' / 'skills'
_PHASE_6_WORKFLOWS = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'workflow'


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
        '# Required steps\n\n- default:functional-review\n- push\n- create-pr\n- default:archive-plan\n',
        encoding='utf-8',
    )

    parsed = inv._parse_required_steps(required)

    assert parsed == [
        'default:functional-review',
        'push',
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
        '- default:functional-review\n- push\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: required)

    metadata = {
        'phase_steps': {
            '6-finalize': {
                'default:functional-review': {
                    'outcome': 'done',
                    'display_detail': 'functional review clean',
                },
                'push': {
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
    """A prefixed requirement recorded under its bare suffix fails the check.

    ``required-steps.md`` lists ``default:functional-review`` (prefixed), but
    the recorded entry on ``metadata.phase_steps['6-finalize']`` is keyed by
    the bare suffix ``functional-review``. The handshake invariant MUST raise
    ``PhaseStepsIncomplete`` with the prefixed step in
    ``excinfo.value.missing`` — the bare key is invisible to the
    required-step lookup, so the step counts as missing.

    A required-steps bullet and a recorded key that disagree on the prefix
    re-introduce this exact failure: the handshake refuses to advance. This
    test is the regression that would catch that drift.
    """
    required = tmp_path / 'required-steps.md'
    required.write_text(
        '- default:functional-review\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: required)

    metadata = {
        'phase_steps': {
            '6-finalize': {
                'functional-review': {
                    'outcome': 'done',
                    'display_detail': 'functional review clean',
                },
            }
        }
    }

    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '6-finalize')

    assert excinfo.value.missing == ['default:functional-review']
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
            bare = manifest_step_id[len(prefix) :]
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
        'push': {'outcome': 'done', 'display_detail': 'committed abc123'},
    }
    record = _renderer_lookup(phase_steps_default_bare, 'default:push')
    assert record is not None
    assert record['display_detail'] == 'committed abc123'

    # Both-miss branch: neither key resolves.
    record = _renderer_lookup(phase_steps_bare, 'project:finalize-step-other')
    assert record is None


# ---------------------------------------------------------------------------
# Test 5: wrappers / workflow contain mark-step-done --step project: refs
# ---------------------------------------------------------------------------


def test_finalize_step_wrappers_mark_step_done_calls_present() -> None:
    """Every source carries its canonical ``mark-step-done --step {id}`` invocation.

    Removing one makes the renderer emit ``<missing display_detail>`` or the
    handshake raise ``PhaseStepsIncomplete``.

    Three sources MUST each carry at least one ``mark-step-done --step {id}``
    invocation under the step's canonical id:

    - ``.claude/skills/finalize-step-plugin-doctor/SKILL.md`` — recording
      lives directly in the project-local wrapper.
    - ``marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/
      functional-review.md`` and ``workflow/code-review.md`` — recording lives
      in the review workflow body, written by the inline dispatcher context.

    Each source is checked for both the ``mark-step-done`` script call and
    the canonical ``--step {id}`` argument; missing either signals that the
    step-id normalization has been reverted.
    """
    sources: list[tuple[Path, str]] = [
        (
            _PROJECT_SKILLS / 'finalize-step-plugin-doctor' / 'SKILL.md',
            'project:finalize-step-plugin-doctor',
        ),
        (
            _PHASE_6_WORKFLOWS / 'functional-review.md',
            'default:functional-review',
        ),
        (
            _PHASE_6_WORKFLOWS / 'code-review.md',
            'default:code-review',
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


# ---------------------------------------------------------------------------
# Test 6: the two review steps are pinned across every roster surface
# ---------------------------------------------------------------------------

_PHASE_6_DIR = get_skill_dir('plan-marshall', 'phase-6-finalize')

#: The two finalize reviews, by their bare step id. Each lives in
#: ``workflow/{bare}.md`` and records under ``default:{bare}``.
_REVIEW_STEPS = ('functional-review', 'code-review')


@pytest.mark.parametrize('bare', _REVIEW_STEPS)
def test_review_step_records_under_its_canonical_step_id(bare: str) -> None:
    """Every terminal record the step body writes names ``default:{bare}``.

    A mark-step-done call under any other spelling would record a key the
    manifest does not carry, and the handshake would count the step missing.
    """
    content = (_PHASE_6_DIR / 'workflow' / f'{bare}.md').read_text(encoding='utf-8')
    calls = [line for line in content.splitlines() if '--step ' in line and '--outcome' in line]
    assert calls, 'control: the workflow must carry terminal mark-step-done calls'
    named = {line.split('--step ', 1)[1].split()[0] for line in calls}
    assert named == {f'default:{bare}'}, f'terminal records name other step ids: {sorted(named)}'


@pytest.mark.parametrize('bare', _REVIEW_STEPS)
def test_review_step_is_on_every_roster_surface(bare: str) -> None:
    """The step is declared on each surface that enumerates finalize steps.

    Each surface is a different reader's view of the roster: the handshake reads
    ``required-steps.md``, the dispatcher reads the SKILL.md dispatch table and the
    dispatched/inline split, and the renderer's reader the output template. A step
    present on some and absent from others is routed by one reader and invisible to
    another.
    """
    required = inv._parse_required_steps(_PHASE_6_DIR / 'standards' / 'required-steps.md')
    assert bare in required
    assert 'push' in required, 'control: the parser must read the real required-steps list'

    skill = (_PHASE_6_DIR / 'SKILL.md').read_text(encoding='utf-8')
    assert f'| `default:{bare}` | `workflow/{bare}.md` |' in skill

    split = (_PHASE_6_DIR / 'standards' / 'dispatch-inline-split.md').read_text(encoding='utf-8')
    assert f'- `default:{bare}` — ' in split

    template = (_PHASE_6_DIR / 'standards' / 'output-template.md').read_text(encoding='utf-8')
    assert f'| `{bare}` |' in template


@pytest.mark.parametrize('bare', _REVIEW_STEPS)
def test_phase_steps_complete_accepts_the_canonical_review_record(
    bare: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A bare required bullet matches the bare key ``mark-step-done`` records.

    ``mark-step-done`` strips the ``default:`` prefix before recording, so the
    required-steps bullet and the recorded key are both the bare id.
    The negative half — the step required but unrecorded — proves the check reads
    the key rather than passing every metadata.
    """
    required = tmp_path / 'required-steps.md'
    required.write_text(f'- {bare}\n', encoding='utf-8')
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: required)

    recorded = {
        'phase_steps': {
            '6-finalize': {
                bare: {'outcome': 'done', 'display_detail': f'{bare} clean'},
            }
        }
    }
    assert len(inv._capture_phase_steps_complete('pid', recorded, '6-finalize')) == 16

    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', {'phase_steps': {'6-finalize': {}}}, '6-finalize')
    assert excinfo.value.missing == [bare]
