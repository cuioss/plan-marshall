#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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


def _params_for(steps_map: dict, step_id: str):
    """Return a step's params from the keyed-map form of steps.

    ``plan.phase-6-finalize.steps`` serializes as the canonical keyed map:
    ``{step_id: {params}}`` (``{}`` for a config-less step). Returns the step's
    nested param object. Raises ``KeyError`` when the step id is absent.
    """
    return steps_map[step_id]


def _discovered_seed_step_ids() -> list:
    """Return the default-on built-in finalize-step ids, in seed order.

    The hand-maintained ``BUILT_IN_FINALIZE_STEPS`` constant was removed; the
    default-on built-in seed is derived from the reusable
    ``extension_discovery.find_implementors`` query (filter ``default_on == true``,
    sort by ``(order, name)``), mirroring ``_seed_finalize_steps()``.
    """
    from extension_discovery import find_implementors

    seed_records = sorted(
        (
            rec
            for rec in find_implementors(_config_defaults.FINALIZE_STEP_EXT_POINT)
            if rec.get('default_on')
        ),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [rec['name'] for rec in seed_records if rec.get('name')]


def _discovered_descriptions() -> dict:
    """Return the ``{step_id: description}`` map across all discovered finalize steps.

    Replaces the removed ``BUILT_IN_FINALIZE_STEP_DESCRIPTIONS`` map: each step's
    description is now a frontmatter field surfaced by the discovery query.
    """
    from extension_discovery import find_implementors

    return {
        rec['name']: rec.get('description', '')
        for rec in find_implementors(_config_defaults.FINALIZE_STEP_EXT_POINT)
        if rec.get('name')
    }


class TestLoopBackWithoutAskingDefault:
    """``loop_back_without_asking`` is the reverse-direction symmetric
    counterpart of ``finalize_without_asking``. Both are flat knobs under
    ``plan.phase-6-finalize`` (the ``ceremony_policy`` block was dissolved and
    every gate/automation knob distributed back into its owning phase). The
    defaults are intentionally asymmetric: forward auto-continue is the common
    case and defaults to ``True``; reverse loop-back surfaces a control return
    to the user and defaults to ``False`` so unattended runs cannot silently
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
        ``loop_back_without_asking=False`` (reverse halt). Both are flat
        ``plan.phase-6-finalize`` knobs. If they drift to a symmetric pair,
        the contract documented in ``marshall-steward/references/wizard-flow.md``
        § Step 7c is broken."""
        cfg = _config_defaults.get_default_config()
        finalize = cfg['plan']['phase-6-finalize']
        forward = finalize['finalize_without_asking']
        reverse = finalize['loop_back_without_asking']
        assert forward is True and reverse is False, (
            'finalize_without_asking must default to True and '
            'loop_back_without_asking must default to False '
            '(asymmetric auto-continuation pair)'
        )

    def test_fresh_project_fallback_seeds_key(self) -> None:
        """A fresh project bootstrap (calling ``get_default_config()``
        without any prior marshal.json) MUST seed
        ``loop_back_without_asking`` explicitly under
        ``plan.phase-6-finalize`` — the key being absent would force every
        downstream consumer to apply its own fallback, and the
        silent-default surface area is exactly the bug pattern this test
        guards against."""
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


class TestFinalMergeWithoutAskingDefault:
    """``final_merge_without_asking`` defaults to ``False`` — the operator is
    prompted before the irreversible final merge (interactive-by-default).
    ``True`` is the explicit opt-in to merge without asking, coordinated via
    the cross-plan merge-lock so concurrently-finalizing plans serialize
    safely on the merge-to-main critical section. The flag is a plain boolean
    — NOT a tri-state. It is a step-owned param of ``default:branch-cleanup``
    in the keyed-map ``steps`` structure (no longer a flat sibling of
    ``steps``)."""

    def test_default_is_false(self) -> None:
        """``get_default_config()`` MUST expose
        ``final_merge_without_asking == False`` nested under
        ``plan.phase-6-finalize.steps['default:branch-cleanup']``."""
        cfg = _config_defaults.get_default_config()
        branch_cleanup = _params_for(
            cfg['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
        )
        assert branch_cleanup['final_merge_without_asking'] is False, (
            'get_default_config() steps[default:branch-cleanup]'
            '["final_merge_without_asking"] must default to False'
        )

    def test_finalize_block_default_matches(self) -> None:
        """The parser-resolved default MUST agree with the value exposed by
        ``get_default_config()`` — both derive from the same `configurable:`
        declaration and must never drift."""
        from configurable_contract import resolve_step_defaults

        assert (
            resolve_step_defaults('default:branch-cleanup')[
                'final_merge_without_asking'
            ]
            is False
        )

    def test_fresh_project_seeds_false(self) -> None:
        """A fresh project bootstrap (calling ``get_default_config()``
        without any prior marshal.json) MUST seed
        ``final_merge_without_asking`` with the ``False`` default nested under
        ``default:branch-cleanup`` — the key being absent would force every
        downstream consumer to apply its own fallback, and the
        interactive-by-default behavior would not flow to fresh projects.
        It must NOT survive as a flat sibling of ``steps``."""
        cfg = _config_defaults.get_default_config()
        finalize = cfg['plan']['phase-6-finalize']
        branch_cleanup = _params_for(finalize['steps'], 'default:branch-cleanup')
        assert 'final_merge_without_asking' in branch_cleanup, (
            'Fresh-project bootstrap must seed final_merge_without_asking '
            'explicitly under steps[default:branch-cleanup]'
        )
        from configurable_contract import resolve_step_defaults

        assert (
            branch_cleanup['final_merge_without_asking']
            == resolve_step_defaults('default:branch-cleanup')[
                'final_merge_without_asking'
            ]
        )
        assert branch_cleanup['final_merge_without_asking'] is False
        # the knob is no longer a flat phase-level field
        assert 'final_merge_without_asking' not in finalize


class TestWorkingPrefixesDefault:
    """``project.working_prefixes`` is the transparent, operator-editable source
    of truth for the canonical closed set of allowed working-branch prefixes
    seeded into marshal.json. The flat list must flow to fresh projects via
    ``get_default_config()`` so the branch-prefix validation and the structural
    coverage test read a populated config rather than every consumer applying
    its own fallback. ``docs/`` is explicitly retired and must never appear in
    the default set. The CI push-trigger allowlist is owned by
    ``python-verify.yml`` and is no longer mirrored in config."""

    _EXPECTED = ['feature/', 'fix/', 'chore/']

    def test_default_config_exposes_working_prefixes(self) -> None:
        """``get_default_config()`` MUST expose
        ``project.working_prefixes`` with the canonical set."""
        cfg = _config_defaults.get_default_config()
        assert cfg['project'].get('working_prefixes') == self._EXPECTED, (
            'get_default_config()["project"]["working_prefixes"] must equal '
            'the canonical working-branch prefix set'
        )

    def test_project_block_default_matches(self) -> None:
        """The ``DEFAULT_PROJECT`` module constant MUST agree with the value
        exposed by ``get_default_config()`` — same physical default, no drift."""
        assert _config_defaults.DEFAULT_PROJECT['working_prefixes'] == self._EXPECTED

    def test_docs_prefix_retired_from_defaults(self) -> None:
        """The retired ``docs/`` prefix MUST be absent from the default set —
        an unlisted CI prefix makes a PR structurally unmergeable."""
        prefixes = _config_defaults.DEFAULT_PROJECT['working_prefixes']
        assert 'docs/' not in prefixes, (
            "'docs/' must be absent from the default working_prefixes"
        )

    def test_branch_naming_key_removed_from_defaults(self) -> None:
        """The flattened model removes the nested ``branch_naming`` wrapper —
        only the flat ``working_prefixes`` field survives."""
        assert 'branch_naming' not in _config_defaults.DEFAULT_PROJECT, (
            'The nested branch_naming block must be gone after the flatten'
        )

    def test_fresh_project_seeds_working_prefixes(self) -> None:
        """A fresh project bootstrap MUST seed ``working_prefixes`` explicitly —
        the key being absent would force every downstream consumer to apply
        its own fallback, defeating the single-source-of-truth design."""
        cfg = _config_defaults.get_default_config()
        project = cfg['project']
        assert 'working_prefixes' in project, (
            'Fresh-project bootstrap must seed project.working_prefixes explicitly'
        )
        assert (
            project['working_prefixes']
            == _config_defaults.DEFAULT_PROJECT['working_prefixes']
        )


class TestReviewCompletionAndBarrierKnobDefaults:
    """The two review-completeness-barrier knobs (D4) seed automatically from
    their owning step's ``configurable:`` frontmatter, so a fresh
    ``get_default_config()`` MUST expose both nested under their owning step in
    the ``plan.phase-6-finalize.steps`` keyed map — no hand-added seed in
    ``_config_defaults.py``. ``review_completion_poll_timeout_seconds`` (600)
    bounds the completion-aware poll under ``plan-marshall:automatic-review``;
    ``pre_merge_comment_barrier`` (``fail_into_loopback``) governs the fail-closed
    pre-merge barrier under ``default:branch-cleanup``."""

    def test_review_completion_poll_timeout_seeds_under_automatic_review(self) -> None:
        """``review_completion_poll_timeout_seconds == 600`` nests under
        ``plan-marshall:automatic-review`` in a fresh config."""
        cfg = _config_defaults.get_default_config()
        automatic_review = _params_for(
            cfg['plan']['phase-6-finalize']['steps'], 'plan-marshall:automatic-review'
        )
        assert automatic_review['review_completion_poll_timeout_seconds'] == 600, (
            'get_default_config() steps[plan-marshall:automatic-review]'
            '["review_completion_poll_timeout_seconds"] must default to 600'
        )

    def test_pre_merge_comment_barrier_seeds_under_branch_cleanup(self) -> None:
        """``pre_merge_comment_barrier == 'fail_into_loopback'`` nests under
        ``default:branch-cleanup`` in a fresh config."""
        cfg = _config_defaults.get_default_config()
        branch_cleanup = _params_for(
            cfg['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
        )
        assert branch_cleanup['pre_merge_comment_barrier'] == 'fail_into_loopback', (
            'get_default_config() steps[default:branch-cleanup]'
            '["pre_merge_comment_barrier"] must default to fail_into_loopback'
        )

    def test_both_knobs_match_their_parser_resolved_defaults(self) -> None:
        """Each seeded knob agrees with its ``configurable:``-declared default via
        ``resolve_step_defaults`` — the seed and the parser derive from the same
        frontmatter declaration and must never drift."""
        from configurable_contract import resolve_step_defaults

        cfg = _config_defaults.get_default_config()
        steps = cfg['plan']['phase-6-finalize']['steps']

        assert (
            _params_for(steps, 'plan-marshall:automatic-review')[
                'review_completion_poll_timeout_seconds'
            ]
            == resolve_step_defaults('plan-marshall:automatic-review')[
                'review_completion_poll_timeout_seconds'
            ]
        )
        assert (
            _params_for(steps, 'default:branch-cleanup')['pre_merge_comment_barrier']
            == resolve_step_defaults('default:branch-cleanup')[
                'pre_merge_comment_barrier'
            ]
        )

    def test_knobs_are_not_flat_phase_level_siblings(self) -> None:
        """Neither knob survives as a flat sibling of ``steps`` — both are
        strictly step-owned nested params."""
        cfg = _config_defaults.get_default_config()
        finalize = cfg['plan']['phase-6-finalize']
        assert 'review_completion_poll_timeout_seconds' not in finalize
        assert 'pre_merge_comment_barrier' not in finalize


class TestCiVerifyRegistration:
    """``default:ci-verify`` MUST be registered in the canonical built-in
    finalize-step set so that ``marshall-steward`` seeds it into new
    projects and the phase-6-finalize dispatcher can resolve it. Position
    is load-bearing: ``ci-verify`` consumes the completed-CI signal and
    classifies failures BEFORE ``automatic-review`` consumes PR-comment
    findings, so it must sit immediately after ``default:create-pr``; the
    reactivated order-25 ``architecture-refresh`` step now sits between
    ``default:ci-verify`` and ``plan-marshall:automatic-review``."""

    def test_ci_verify_in_built_in_finalize_steps(self) -> None:
        """The default-on built-in seed MUST contain ``'default:ci-verify'``
        immediately after ``'default:create-pr'`` — the canonical position
        declared by ``standards/ci-verify.md`` § Placement (order 22, between
        create-pr at 20 and automatic-review at 30). The seed is discovered via
        find_implementors, not a constant. ``architecture-refresh`` is now
        ``default_on: true`` (order 25), so it enters the seed BETWEEN
        ``ci-verify`` (22) and ``automatic-review`` (30): the canonical tail is
        ``ci-verify → architecture-refresh → automatic-review``."""
        steps = _discovered_seed_step_ids()
        assert 'default:ci-verify' in steps, (
            "the default-on seed must contain 'default:ci-verify'"
        )
        assert 'default:architecture-refresh' in steps, (
            "architecture-refresh is now default_on:true and must appear in the seed"
        )
        create_pr_idx = steps.index('default:create-pr')
        ci_verify_idx = steps.index('default:ci-verify')
        architecture_refresh_idx = steps.index('default:architecture-refresh')
        automated_review_idx = steps.index('plan-marshall:automatic-review')
        assert ci_verify_idx == create_pr_idx + 1, (
            "'default:ci-verify' must sit immediately after "
            "'default:create-pr' in the default-on seed"
        )
        assert architecture_refresh_idx == ci_verify_idx + 1, (
            "'default:architecture-refresh' (order 25) must sit immediately "
            "after 'default:ci-verify' (order 22) in the default-on seed"
        )
        assert automated_review_idx == ci_verify_idx + 2, (
            "'plan-marshall:automatic-review' must sit two positions after "
            "'default:ci-verify' — 'architecture-refresh' is now between them"
        )

    def test_ci_verify_has_description(self) -> None:
        """The discovered finalize-step descriptions MUST carry a non-empty
        description for ``'default:ci-verify'`` so that ``list-finalize-steps``
        and the wizard can surface a meaningful label. The text is the workflow
        doc's frontmatter ``description`` field — the discovery query reads it
        directly."""
        descriptions = _discovered_descriptions()
        assert 'default:ci-verify' in descriptions, (
            "the discovered descriptions must register 'default:ci-verify'"
        )
        assert descriptions['default:ci-verify'], (
            "the discovered description for 'default:ci-verify' "
            'must be a non-empty string'
        )


class TestFinalizeStepDescriptionDrift:
    """The discovered finalize-step descriptions are the user-facing source of
    truth surfaced by ``list-finalize-steps`` and the wizard. Each step doc's
    frontmatter ``description`` MUST stay in lockstep with its workflow doc body
    (the description IS the frontmatter field). Q-Gate validation in
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
        ``plan-marshall:automatic-review``."""
        descriptions = _discovered_descriptions()
        text = descriptions['default:sonar-roundtrip']
        assert 'requires: [ci-complete]' in text, (
            "the discovered description for 'default:sonar-roundtrip' "
            "must name the 'requires: [ci-complete]' precondition declared "
            'in sonar-roundtrip.md frontmatter — current text: ' + repr(text)
        )

    def test_branch_cleanup_drops_pr_merge_only_phrasing(self) -> None:
        """``default:branch-cleanup`` MUST NOT contain the old
        ``Merge PR (with --delete-branch) and pull latest`` phrasing —
        that text implies PR-merge is mandatory but the step adapts
        based on whether ``create-pr`` is present in the manifest."""
        descriptions = _discovered_descriptions()
        text = descriptions['default:branch-cleanup']
        assert 'Merge PR (with --delete-branch) and pull latest' not in text, (
            "the discovered description for 'default:branch-cleanup' "
            "must not retain the legacy 'Merge PR (with --delete-branch) "
            "and pull latest' phrasing — current text: " + repr(text)
        )

    def test_branch_cleanup_describes_conditional_adaptation(self) -> None:
        """``default:branch-cleanup`` MUST mention either ``create-pr``,
        ``conditionally``, or ``adapts`` so the conditional shape is
        visible in the description surface."""
        descriptions = _discovered_descriptions()
        text = descriptions['default:branch-cleanup']
        markers = ('create-pr', 'conditionally', 'adapts')
        assert any(marker in text for marker in markers), (
            "the discovered description for 'default:branch-cleanup' "
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
        descriptions = _discovered_descriptions()
        expected = (
            'Capture lessons from triage findings and PR-review '
            'escalations (skipped when qgate_findings=0, '
            'pr_comments_promoted=0, and script_failure_clusters=0)'
        )
        assert descriptions['default:lessons-capture'] == expected, (
            "the discovered description for 'default:lessons-capture' "
            'must match the clarified-request string exactly — expected: '
            + repr(expected)
            + ', got: '
            + repr(descriptions['default:lessons-capture'])
        )

    def test_updated_descriptions_within_readability_bound(self) -> None:
        """All three updated descriptions MUST stay ≤200 chars to keep
        ``list-finalize-steps`` output readable."""
        descriptions = _discovered_descriptions()
        for key in (
            'default:sonar-roundtrip',
            'default:branch-cleanup',
            'default:lessons-capture',
        ):
            text = descriptions[key]
            assert len(text) <= self._READABILITY_BOUND, (
                f"the discovered description for {key!r} exceeds "
                f'{self._READABILITY_BOUND}-char readability bound — '
                f'length={len(text)}, text={text!r}'
            )


class TestSonarConfigKnobsDefaults:
    """The three Sonar roundtrip knobs nest under ``default:sonar-roundtrip`` in
    the keyed-map ``steps`` structure, prefix-stripped (``sonar_`` dropped since
    the owning step already scopes them):

    - ``touched_file_cleanup`` — an ENUM (NOT a bool) controlling which
      surface the sonar-roundtrip success criterion covers. Allowed values are
      ``'new_code_only'`` (the lean default — success requires only new-code
      issues == 0) and ``'touched_files_zero'`` (also sweeps pre-existing
      issues on touched files). Validated by
      ``validate_sonar_touched_file_cleanup`` against
      ``VALID_SONAR_TOUCHED_FILE_CLEANUP``.
    - ``do_transition`` — bool gating the server-side SonarCloud
      dismissal path. ``False`` (default) routes dispositions through in-code
      suppression; ``True`` re-enables ``sonar_rest transition``.
    - ``ce_wait_timeout_seconds`` — int budget (seconds) for the
      synchronous CE-readiness wait performed before enumerating new-code
      issues. Defaults to ``600``, mirroring ``checks_wait_timeout_seconds``.

    Each knob is a step-owned param under ``default:sonar-roundtrip``; the tests
    assert the ``get_default_config()`` runtime contract, agreement with the
    parser-resolved default (``configurable_contract.resolve_step_defaults`` — no
    drift), and fresh-project seeding so every downstream consumer reads a
    populated config rather than applying its own silent fallback.
    """

    @staticmethod
    def _sonar_params(cfg: dict) -> dict:
        return _params_for(cfg['plan']['phase-6-finalize']['steps'], 'default:sonar-roundtrip')

    def test_touched_file_cleanup_default_is_new_code_only(self) -> None:
        """``get_default_config()`` MUST expose ``touched_file_cleanup ==
        'new_code_only'`` nested under ``default:sonar-roundtrip`` — the lean
        default that anchors success on new-code issues == 0."""
        cfg = _config_defaults.get_default_config()
        assert self._sonar_params(cfg)['touched_file_cleanup'] == 'new_code_only', (
            'steps[default:sonar-roundtrip]["touched_file_cleanup"] '
            'must default to "new_code_only"'
        )

    def test_touched_file_cleanup_finalize_block_matches(self) -> None:
        """The parser-resolved default MUST agree with the value exposed by
        ``get_default_config()`` — same physical default, no drift."""
        from configurable_contract import resolve_step_defaults

        assert (
            resolve_step_defaults('default:sonar-roundtrip')[
                'touched_file_cleanup'
            ]
            == 'new_code_only'
        )

    def test_touched_file_cleanup_default_is_a_valid_enum_value(self) -> None:
        """The default value MUST be a member of
        ``VALID_SONAR_TOUCHED_FILE_CLEANUP`` and MUST pass
        ``validate_sonar_touched_file_cleanup`` without raising — the default
        can never be an out-of-enum value."""
        from configurable_contract import resolve_step_defaults

        default = resolve_step_defaults('default:sonar-roundtrip')[
            'touched_file_cleanup'
        ]
        assert default in _config_defaults.VALID_SONAR_TOUCHED_FILE_CLEANUP, (
            'touched_file_cleanup default must be a member of '
            'VALID_SONAR_TOUCHED_FILE_CLEANUP'
        )
        # Must not raise.
        _config_defaults.validate_sonar_touched_file_cleanup(default)

    def test_touched_file_cleanup_validator_rejects_unknown(self) -> None:
        """``validate_sonar_touched_file_cleanup`` MUST raise ``ValueError``
        for a value outside the allowed enum — a bool-shaped value (the
        original task-description guess) is exactly the kind of input the
        enum validator must reject."""
        import pytest

        with pytest.raises(ValueError):
            _config_defaults.validate_sonar_touched_file_cleanup('true')

    def test_do_transition_default_is_false(self) -> None:
        """``get_default_config()`` MUST expose ``do_transition == False``
        nested under ``default:sonar-roundtrip`` — in-code suppression is the
        default disposition path."""
        cfg = _config_defaults.get_default_config()
        assert self._sonar_params(cfg)['do_transition'] is False, (
            'steps[default:sonar-roundtrip]["do_transition"] must default to False'
        )

    def test_do_transition_finalize_block_matches(self) -> None:
        """The parser-resolved default MUST agree with the value exposed by
        ``get_default_config()`` — same physical default, no drift."""
        from configurable_contract import resolve_step_defaults

        assert (
            resolve_step_defaults('default:sonar-roundtrip')[
                'do_transition'
            ]
            is False
        )

    def test_ce_wait_timeout_default_is_600(self) -> None:
        """``get_default_config()`` MUST expose ``ce_wait_timeout_seconds ==
        600`` nested under ``default:sonar-roundtrip`` — mirroring the
        ``checks_wait_timeout_seconds`` CI-completion default."""
        cfg = _config_defaults.get_default_config()
        assert self._sonar_params(cfg)['ce_wait_timeout_seconds'] == 600, (
            'steps[default:sonar-roundtrip]["ce_wait_timeout_seconds"] '
            'must default to 600'
        )

    def test_ce_wait_timeout_finalize_block_matches(self) -> None:
        """The parser-resolved default MUST agree with the value exposed by
        ``get_default_config()`` — same physical default, no drift."""
        from configurable_contract import resolve_step_defaults

        assert (
            resolve_step_defaults('default:sonar-roundtrip')[
                'ce_wait_timeout_seconds'
            ]
            == 600
        )

    def test_fresh_project_seeds_all_three_knobs(self) -> None:
        """A fresh project bootstrap (calling ``get_default_config()`` without
        any prior marshal.json) MUST seed all three Sonar params explicitly,
        prefix-stripped, under ``default:sonar-roundtrip`` — the keys being
        absent would force every downstream consumer to apply its own silent
        fallback, the exact bug pattern these tests guard against. Each seeded
        value also matches the parser-resolved default, and no flat
        ``sonar_``-prefixed sibling of ``steps`` survives."""
        from configurable_contract import resolve_step_defaults

        cfg = _config_defaults.get_default_config()
        finalize = cfg['plan']['phase-6-finalize']
        sonar = self._sonar_params(cfg)
        expected = resolve_step_defaults('default:sonar-roundtrip')
        for key in ('touched_file_cleanup', 'do_transition', 'ce_wait_timeout_seconds'):
            assert key in sonar, (
                f'Fresh-project bootstrap must seed {key} explicitly under '
                'steps[default:sonar-roundtrip]'
            )
            assert sonar[key] == expected[key], (
                f'Fresh-project {key} value must match the parser-resolved default'
            )
        # no flat sonar_-prefixed knob survives as a sibling of steps
        for flat in (
            'sonar_touched_file_cleanup',
            'sonar_do_transition',
            'sonar_ce_wait_timeout_seconds',
        ):
            assert flat not in finalize, (
                f'flat step-owned knob {flat!r} must not survive at phase level'
            )
