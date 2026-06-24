# SPDX-License-Identifier: FSL-1.1-ALv2
"""Named finalize-step presets for the ``manage-config finalize-steps apply-preset`` write API.

Defines :class:`FinalizeStepPresets` — the access surface that bundles a
phase-6-finalize step list under three named profiles:

- ``local`` — local-only flow with no remote / CI / PR / Sonar steps.
  Commits and pushes, captures lessons, cleans the branch, records metrics,
  and archives the plan.
- ``standard`` — the ``local`` set plus the PR + CI flow (``create-pr``,
  ``ci-verify``, ``automated-review``); still no Sonar roundtrip.
- ``full`` — the ``standard`` set plus the Sonar roundtrip, the
  pre-push quality gate, and the opt-in ``plan-marshall:plan-retrospective``
  bundle step.

Preset membership is no longer a hand-maintained class-attribute literal: each
finalize-step doc DECLARES its preset memberships in a ``presets:`` frontmatter
list, and the preset step lists are BUILT lazily from the reusable
``extension_discovery.find_implementors`` query (the SOLE discovery path — the
seed in ``_config_defaults`` and the discovery surface in ``_cmd_skill_resolution``
consume the same query). A step belongs to preset ``P`` iff ``P`` appears in its
``presets`` list; the per-preset step order is the discovered ``order``. The
contract — addressing surface, the per-step frontmatter fields, and the
supporting-doc exclusion list — lives in the central standard:
``marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md``.

Consumer-scoped by design — zero ``project:`` entries
-----------------------------------------------------
The ``local`` / ``standard`` / ``full`` presets carry **only** ``default:``
built-in and opt-in ``bundle:skill`` steps; none reference a ``project:``
step. This is intentional: presets ship to *consumer* projects, which do not
have the meta-project's project-local finalize-step skills (the
``project:finalize-step-*`` skills under the project-local-skill roots). A
preset that seeded a ``project:`` step would reference a skill the consumer
cannot resolve. Project-local steps carry ``presets: []`` in their frontmatter,
so the discovery-driven preset builder naturally excludes them; the meta-project's
own ``project:`` finalize steps are hand-maintained in its
``phase-6-finalize.steps`` array, NOT preset-driven.
"""

from __future__ import annotations

import copy

# Canonical preset names in display order (least ➜ most coverage). The set is a
# fixed taxonomy; only the per-preset step MEMBERSHIP is discovery-driven.
_PRESET_NAMES: tuple[str, ...] = ('local', 'standard', 'full')


def _discover_presets() -> dict[str, list[str]]:
    """Build the ``{preset_name: [step_id, ...]}`` map from the discovery query.

    Lazy-imports ``FINALIZE_STEP_EXT_POINT`` from ``_config_defaults`` and
    ``find_implementors`` from ``extension_discovery`` (the executor sets
    PYTHONPATH for cross-skill imports), then for each canonical preset name
    collects every discovered step whose ``presets`` list contains that name,
    ordered by the discovered ``order``. A step in no preset contributes to no
    list; a preset with no members resolves to an empty list.

    Returns:
        A mapping from each canonical preset name to its ordered step-id list.
    """
    from _config_defaults import FINALIZE_STEP_EXT_POINT  # type: ignore[import-not-found]
    from extension_discovery import find_implementors  # type: ignore[import-not-found]

    implementors = sorted(
        find_implementors(FINALIZE_STEP_EXT_POINT),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    name_to_preset: dict[str, list[str]] = {name: [] for name in _PRESET_NAMES}
    for rec in implementors:
        step_id = rec.get('name', '')
        presets = rec.get('presets', []) or []
        if presets and not step_id:
            raise ValueError(
                'malformed finalize-step frontmatter: a step declares '
                f'presets={presets!r} but has no resolvable step_id'
            )
        for preset_name in presets:
            if preset_name not in name_to_preset:
                raise ValueError(
                    f'malformed finalize-step frontmatter: step {step_id!r} '
                    f'declares unknown preset {preset_name!r} '
                    f'(known presets: {sorted(name_to_preset)})'
                )
            name_to_preset[preset_name].append(step_id)
    return name_to_preset


class FinalizeStepPresets:
    """Named finalize-step presets for ``manage-config finalize-steps apply-preset``.

    The preset step lists are discovery-driven (built from each step doc's
    ``presets:`` frontmatter via :func:`_discover_presets`), not class-attribute
    literals. The class methods (:meth:`get`, :meth:`all_names`, :meth:`describe`)
    are the only sanctioned access path. :meth:`get` returns a deep copy so
    callers cannot accidentally mutate the discovered lists.
    """

    _DESCRIPTIONS: dict[str, str] = {
        'local': (
            'Local-only flow — commit/push, lessons-capture, branch-cleanup, '
            'record-metrics, archive-plan. No remote PR, CI, review, or Sonar '
            'steps.'
        ),
        'standard': (
            'Standard hosted-CI flow — the local set plus create-pr, '
            'ci-verify, and automated-review. No Sonar roundtrip.'
        ),
        'full': (
            'Full quality stack — the standard set plus finalize-step-simplify, '
            'sonar-roundtrip, pre-push-quality-gate, and the opt-in '
            'plan-retrospective step.'
        ),
    }

    # ---- public API ------------------------------------------------------

    @classmethod
    def get(cls, name: str) -> list[str]:
        """Return the step list for preset ``name`` as a deep copy.

        ``name`` is matched case-insensitively. The returned list is freshly
        discovered (and deep-copied) so callers can mutate it freely without
        poisoning subsequent callers.

        Args:
            name: Preset name. Accepts any case-insensitive variant of
                ``local``, ``standard``, or ``full``.

        Returns:
            A deep copy of the preset's discovered step list, ready to be written
            to ``plan.phase-6-finalize.steps``.

        Raises:
            ValueError: When ``name`` does not match any known preset. The
                message lists the canonical names returned by
                :meth:`all_names` so callers can surface a useful error.
        """
        if not isinstance(name, str):
            raise ValueError(
                f'preset name must be a string; got {type(name).__name__}. '
                f'Valid names: {cls.all_names()}'
            )
        canonical = name.strip().lower()
        if canonical not in _PRESET_NAMES:
            raise ValueError(
                f"unknown preset '{name}'; valid names: {cls.all_names()}"
            )
        return copy.deepcopy(_discover_presets()[canonical])

    @classmethod
    def all_names(cls) -> list[str]:
        """Return the canonical preset names in display order.

        The display order is least ➜ most coverage: ``local``, ``standard``,
        ``full``. Used by the wizard / maintenance-menu preset picker and as
        the validation set for the ``finalize-steps apply-preset --preset``
        argparse callable.
        """
        return list(_PRESET_NAMES)

    @classmethod
    def describe(cls, name: str) -> str:
        """Return a one-line human description of preset ``name``.

        Used by the ``marshall-steward`` quality-pipeline preset picker to
        annotate the preset-selection prompt. Accepts the same
        case-insensitive input as :meth:`get`.

        Raises:
            ValueError: When ``name`` does not match any known preset.
        """
        if not isinstance(name, str):
            raise ValueError(
                f'preset name must be a string; got {type(name).__name__}. '
                f'Valid names: {cls.all_names()}'
            )
        canonical = name.strip().lower()
        description = cls._DESCRIPTIONS.get(canonical)
        if description is None:
            raise ValueError(
                f"unknown preset '{name}'; valid names: {cls.all_names()}"
            )
        return description
