#!/usr/bin/env python3
"""Tests for the manage-config bootstrap defaults surface.

Asserts the runtime contract returned by ``get_default_config()`` (the
authoritative bootstrap shape consumed by ``marshall-steward`` and the
``manage-config init`` wizard). Complementary to the text-level assertions
in ``test_phase_6_manifest_executor.py`` — those scan the source for the
literal ``'loop_back_without_asking': False`` token, this one asserts the
dict returned by the function actually exposes the value.
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults = _load_module('_config_defaults', '_config_defaults.py')


class TestLoopBackWithoutAskingDefault:
    """``loop_back_without_asking`` is the reverse-direction symmetric
    counterpart of ``finalize_without_asking``. The defaults are
    intentionally asymmetric: forward auto-continue is the common case and
    defaults to ``True``; reverse loop-back surfaces a control return to
    the user and defaults to ``False`` so unattended runs cannot silently
    re-enter execute on a finalize-side fix."""

    def test_default_is_false(self) -> None:
        """``get_default_config()`` MUST expose
        ``plan.phase-6-finalize.loop_back_without_asking == False``."""
        cfg = _config_defaults.get_default_config()
        assert (
            cfg['plan']['phase-6-finalize']['loop_back_without_asking']
            is False
        ), (
            'get_default_config()["plan"]["phase-6-finalize"]'
            '["loop_back_without_asking"] must default to False'
        )

    def test_finalize_block_default_matches(self) -> None:
        """The ``DEFAULT_PLAN_FINALIZE`` module constant MUST agree with the
        value exposed by ``get_default_config()`` — they are the same
        physical default and must never drift."""
        assert (
            _config_defaults.DEFAULT_PLAN_FINALIZE['loop_back_without_asking']
            is False
        )

    def test_asymmetric_with_finalize_without_asking(self) -> None:
        """The two auto-continuation knobs default asymmetrically —
        ``finalize_without_asking=True`` (forward auto) and
        ``loop_back_without_asking=False`` (reverse halt). If they drift
        to a symmetric pair, the contract documented in
        ``marshall-steward/references/wizard-flow.md`` § Step 7c is
        broken."""
        cfg = _config_defaults.get_default_config()
        forward = cfg['plan']['phase-5-execute']['finalize_without_asking']
        reverse = cfg['plan']['phase-6-finalize']['loop_back_without_asking']
        assert forward is True and reverse is False, (
            'finalize_without_asking must default to True and '
            'loop_back_without_asking must default to False '
            '(asymmetric auto-continuation pair)'
        )

    def test_fresh_project_fallback_seeds_key(self) -> None:
        """A fresh project bootstrap (calling ``get_default_config()``
        without any prior marshal.json) MUST seed
        ``loop_back_without_asking`` explicitly — the key being absent
        would force every downstream consumer to apply its own fallback,
        and the silent-default surface area is exactly the bug pattern
        this test guards against."""
        cfg = _config_defaults.get_default_config()
        finalize = cfg['plan']['phase-6-finalize']
        assert 'loop_back_without_asking' in finalize, (
            'Fresh-project bootstrap must seed loop_back_without_asking '
            'explicitly in plan.phase-6-finalize'
        )
        # Sanity: the fresh-project value matches the module-level constant
        assert (
            finalize['loop_back_without_asking']
            == _config_defaults.DEFAULT_PLAN_FINALIZE['loop_back_without_asking']
        )


class TestCiVerifyRegistration:
    """``default:ci-verify`` MUST be registered in the canonical built-in
    finalize-step set so that ``marshall-steward`` seeds it into new
    projects and the phase-6-finalize dispatcher can resolve it. Position
    is load-bearing: ``ci-verify`` consumes the completed-CI signal and
    classifies failures BEFORE ``automated-review`` consumes PR-comment
    findings, so it must sit immediately after ``default:create-pr`` and
    immediately before ``default:automated-review``."""

    def test_ci_verify_in_built_in_finalize_steps(self) -> None:
        """``BUILT_IN_FINALIZE_STEPS`` MUST contain ``'default:ci-verify'``
        at the index immediately after ``'default:create-pr'`` and
        immediately before ``'default:automated-review'`` — the canonical
        position declared by ``standards/ci-verify.md`` § Placement and
        the originating plan's deliverable 6."""
        steps = _config_defaults.BUILT_IN_FINALIZE_STEPS
        assert 'default:ci-verify' in steps, (
            "BUILT_IN_FINALIZE_STEPS must contain 'default:ci-verify'"
        )
        create_pr_idx = steps.index('default:create-pr')
        ci_verify_idx = steps.index('default:ci-verify')
        automated_review_idx = steps.index('default:automated-review')
        assert ci_verify_idx == create_pr_idx + 1, (
            "'default:ci-verify' must sit immediately after "
            "'default:create-pr' in BUILT_IN_FINALIZE_STEPS"
        )
        assert automated_review_idx == ci_verify_idx + 1, (
            "'default:automated-review' must sit immediately after "
            "'default:ci-verify' in BUILT_IN_FINALIZE_STEPS"
        )

    def test_ci_verify_has_description(self) -> None:
        """``BUILT_IN_FINALIZE_STEP_DESCRIPTIONS`` MUST carry a
        non-empty description for ``'default:ci-verify'`` so that
        ``list-finalize-steps`` and the wizard can surface a meaningful
        label. The text is copied verbatim from the workflow doc's
        frontmatter ``description`` field — the two stay in lockstep."""
        descriptions = _config_defaults.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
        assert 'default:ci-verify' in descriptions, (
            "BUILT_IN_FINALIZE_STEP_DESCRIPTIONS must register "
            "'default:ci-verify'"
        )
        assert descriptions['default:ci-verify'], (
            "BUILT_IN_FINALIZE_STEP_DESCRIPTIONS['default:ci-verify'] "
            'must be a non-empty string'
        )


class TestFinalizeStepDescriptionDrift:
    """``BUILT_IN_FINALIZE_STEP_DESCRIPTIONS`` is the user-facing source of
    truth surfaced by ``list-finalize-steps`` and the wizard. Each entry
    MUST stay in lockstep with its workflow doc. Q-Gate validation in
    phase-2-refine of plan ``built-in-finalize-step-descriptions-must-stay-in``
    surfaced three drift defects this class regresses against:

    - ``default:sonar-roundtrip`` — must name the
      ``requires: [ci-complete]`` precondition declared in
      ``sonar-roundtrip.md`` frontmatter.
    - ``default:branch-cleanup`` — must describe the create-pr-presence
      adaptation, NOT imply PR-merge is mandatory.
    - ``default:lessons-capture`` — must match the clarified-request string
      exactly, advertising the Signal Gate skip-conditional behavior.
    """

    _READABILITY_BOUND = 200
    """Per the deliverable Success Criteria: descriptions must stay ≤200
    chars so ``list-finalize-steps`` output remains readable."""

    def test_sonar_roundtrip_names_ci_complete_precondition(self) -> None:
        """``default:sonar-roundtrip`` description MUST contain
        ``requires: [ci-complete]`` so the precondition is visible in the
        wizard / ``list-finalize-steps`` surface, mirroring the shape
        already used by ``default:ci-verify`` and
        ``default:automated-review``."""
        descriptions = _config_defaults.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
        text = descriptions['default:sonar-roundtrip']
        assert 'requires: [ci-complete]' in text, (
            "BUILT_IN_FINALIZE_STEP_DESCRIPTIONS['default:sonar-roundtrip'] "
            "must name the 'requires: [ci-complete]' precondition declared "
            'in sonar-roundtrip.md frontmatter — current text: ' + repr(text)
        )

    def test_branch_cleanup_drops_pr_merge_only_phrasing(self) -> None:
        """``default:branch-cleanup`` MUST NOT contain the old
        ``Merge PR (with --delete-branch) and pull latest`` phrasing —
        that text implies PR-merge is mandatory but the step adapts
        based on whether ``create-pr`` is present in the manifest."""
        descriptions = _config_defaults.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
        text = descriptions['default:branch-cleanup']
        assert 'Merge PR (with --delete-branch) and pull latest' not in text, (
            "BUILT_IN_FINALIZE_STEP_DESCRIPTIONS['default:branch-cleanup'] "
            "must not retain the legacy 'Merge PR (with --delete-branch) "
            "and pull latest' phrasing — current text: " + repr(text)
        )

    def test_branch_cleanup_describes_conditional_adaptation(self) -> None:
        """``default:branch-cleanup`` MUST mention either ``create-pr``,
        ``conditionally``, or ``adapts`` so the conditional shape is
        visible in the description surface."""
        descriptions = _config_defaults.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
        text = descriptions['default:branch-cleanup']
        markers = ('create-pr', 'conditionally', 'adapts')
        assert any(marker in text for marker in markers), (
            "BUILT_IN_FINALIZE_STEP_DESCRIPTIONS['default:branch-cleanup'] "
            'must mention one of ' + repr(markers) + ' to capture the '
            'conditional adaptation based on create-pr presence — current '
            'text: ' + repr(text)
        )

    def test_lessons_capture_matches_clarified_request_string(self) -> None:
        """``default:lessons-capture`` MUST equal the clarified-request
        string verbatim — the exact wording is part of the request
        contract and downstream consumers may grep for the substring
        ``skipped when qgate_findings=0`` to detect the Signal Gate
        behavior advertised here."""
        descriptions = _config_defaults.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
        expected = (
            'Capture lessons from triage findings and PR-review '
            'escalations (skipped when qgate_findings=0, '
            'pr_comments_promoted=0, and script_failure_clusters=0)'
        )
        assert descriptions['default:lessons-capture'] == expected, (
            "BUILT_IN_FINALIZE_STEP_DESCRIPTIONS['default:lessons-capture'] "
            'must match the clarified-request string exactly — expected: '
            + repr(expected)
            + ', got: '
            + repr(descriptions['default:lessons-capture'])
        )

    def test_updated_descriptions_within_readability_bound(self) -> None:
        """All three updated descriptions MUST stay ≤200 chars to keep
        ``list-finalize-steps`` output readable."""
        descriptions = _config_defaults.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
        for key in (
            'default:sonar-roundtrip',
            'default:branch-cleanup',
            'default:lessons-capture',
        ):
            text = descriptions[key]
            assert len(text) <= self._READABILITY_BOUND, (
                f"BUILT_IN_FINALIZE_STEP_DESCRIPTIONS[{key!r}] exceeds "
                f'{self._READABILITY_BOUND}-char readability bound — '
                f'length={len(text)}, text={text!r}'
            )
