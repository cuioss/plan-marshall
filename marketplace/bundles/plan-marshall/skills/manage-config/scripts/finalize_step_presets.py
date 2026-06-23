# SPDX-License-Identifier: FSL-1.1-ALv2
"""Named finalize-step presets for the ``manage-config finalize-steps apply-preset`` write API.

Defines :class:`FinalizeStepPresets` — a constant-class that bundles a
phase-6-finalize step list under three named profiles:

- ``LOCAL`` — local-only flow with no remote / CI / PR / Sonar steps.
  Commits and pushes, captures lessons, cleans the branch, records metrics,
  and archives the plan.
- ``STANDARD`` — the ``LOCAL`` set plus the PR + CI flow (``create-pr``,
  ``ci-verify``, ``automated-review``); still no Sonar roundtrip.
- ``FULL`` — the ``STANDARD`` set plus the Sonar roundtrip, the
  pre-push quality gate, and the opt-in ``plan-marshall:plan-retrospective``
  bundle step.

The presets sit alongside the finalize-step write surface inside the
``plan-marshall:manage-config`` skill so policy decisions about which
finalize steps belong to each named profile stay co-located with the
authoritative step registry (``BUILT_IN_FINALIZE_STEPS`` +
``OPTIONAL_BUNDLE_FINALIZE_STEPS`` in ``_config_defaults``) rather than
leaking into the wizard prose. The constant-class shape is plain Python
lists — not :class:`enum.Enum`, not :func:`dataclasses.dataclass` — so the
values round-trip through JSON unchanged when the
``manage-config finalize-steps apply-preset`` writer drops them into
``marshal.json``.

Each preset references ONLY step notations that are members of the known
finalize-step universe (``BUILT_IN_FINALIZE_STEPS`` +
``OPTIONAL_BUNDLE_FINALIZE_STEPS``). A self-check
(:func:`_validate_preset`) runs at import time and raises
:class:`ValueError` if any preset references an unknown step notation, so a
typo fails fast at module load rather than silently shipping into
``marshal.json``.

Consumer-scoped by design — zero ``project:`` entries
-----------------------------------------------------
The ``LOCAL`` / ``STANDARD`` / ``FULL`` presets carry **only** ``default:``
built-in and opt-in ``bundle:skill`` steps; none reference a ``project:``
step. This is intentional: presets ship to *consumer* projects, which do not
have the meta-project's project-local finalize-step skills (the
``project:finalize-step-*`` skills under the project-local-skill roots). A
preset that seeded a ``project:`` step would reference a skill the consumer
cannot resolve. The meta-project's own ``project:`` finalize steps are therefore
**hand-maintained** in its ``phase-6-finalize.steps`` array, NOT preset-driven;
``marshall-steward``'s ``determine_mode.py check-missing-finalize-steps``
surfaces any shipped ``project:`` step dropped from that array (discovered from
the target's ``finalize-step-*`` project-local skills) so a steward re-run on the
meta-project does not silently lose them.
"""

from __future__ import annotations

import copy

from _config_defaults import (
    BUILT_IN_FINALIZE_STEPS,
    OPTIONAL_BUNDLE_FINALIZE_STEPS,
)

# The full set of step notations any preset is permitted to reference.
# Kept as a tuple so the import-time self-check can cross-check every
# preset entry against the authoritative registry in _config_defaults.
KNOWN_FINALIZE_STEPS: tuple[str, ...] = tuple(
    BUILT_IN_FINALIZE_STEPS
) + tuple(OPTIONAL_BUNDLE_FINALIZE_STEPS)


class FinalizeStepPresets:
    """Named finalize-step presets for ``manage-config finalize-steps apply-preset``.

    Each class-level constant is a ready-to-write list of finalize-step
    notations (a subset of :data:`KNOWN_FINALIZE_STEPS`), ordered to match
    the canonical ``BUILT_IN_FINALIZE_STEPS`` sequence so the on-disk
    ``plan.phase-6-finalize.steps`` value is deterministic.

    The class methods (:meth:`get`, :meth:`all_names`, :meth:`describe`)
    are the only sanctioned access path. :meth:`get` returns a deep copy so
    callers cannot accidentally mutate the class-level constants.
    """

    # ---- preset payloads -------------------------------------------------

    LOCAL: list[str] = [
        'default:push',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:record-metrics',
        'default:archive-plan',
    ]
    """Local-only flow — commit/push, lessons, branch cleanup, metrics, and
    archive. No remote PR creation, CI verification, automated review, or
    Sonar roundtrip; suited to projects that finalize without a hosted CI /
    PR pipeline."""

    STANDARD: list[str] = [
        'default:push',
        'default:create-pr',
        'default:ci-verify',
        'default:automated-review',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:record-metrics',
        'default:archive-plan',
    ]
    """The ``LOCAL`` set plus the PR + CI flow (``create-pr``, ``ci-verify``,
    ``automated-review``). No Sonar roundtrip; the common hosted-CI default
    for projects without SonarQube/SonarCloud integration."""

    FULL: list[str] = [
        'default:pre-push-quality-gate',
        'default:finalize-step-simplify',
        'default:push',
        'default:create-pr',
        'default:ci-verify',
        'default:automated-review',
        'default:sonar-roundtrip',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:record-metrics',
        'default:archive-plan',
        'plan-marshall:plan-retrospective',
    ]
    """The ``STANDARD`` set plus the simplify sweep, the Sonar roundtrip, the
    pre-push quality gate, and the opt-in ``plan-marshall:plan-retrospective``
    bundle step — the maximal pipeline for projects running the full quality
    stack."""

    # ---- canonical name table -------------------------------------------

    # Display order matches the wizard prompt order (least ➜ most coverage).
    _NAME_TO_PRESET: dict[str, list[str]] = {
        'local': LOCAL,
        'standard': STANDARD,
        'full': FULL,
    }

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

        ``name`` is matched case-insensitively. The returned list is a deep
        copy of the class-level constant so callers can mutate it freely
        without poisoning the registry for subsequent callers.

        Args:
            name: Preset name. Accepts any case-insensitive variant of
                ``local``, ``standard``, or ``full``.

        Returns:
            A deep copy of the preset's step list, ready to be written to
            ``plan.phase-6-finalize.steps``.

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
        preset = cls._NAME_TO_PRESET.get(canonical)
        if preset is None:
            raise ValueError(
                f"unknown preset '{name}'; valid names: {cls.all_names()}"
            )
        return copy.deepcopy(preset)

    @classmethod
    def all_names(cls) -> list[str]:
        """Return the canonical preset names in display order.

        The display order is least ➜ most coverage: ``local``, ``standard``,
        ``full``. Used by the wizard / maintenance-menu preset picker and as
        the validation set for the ``finalize-steps apply-preset --preset``
        argparse callable.
        """
        return list(cls._NAME_TO_PRESET.keys())

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


# --- import-time self-check ----------------------------------------------


def _validate_preset(name: str, preset: list[str]) -> None:
    """Validate a preset against the known finalize-step universe.

    Checks (raises :class:`ValueError` on the first failure):

    1. ``preset`` is a list.
    2. ``preset`` is non-empty.
    3. Every entry is a string.
    4. Every entry is a member of :data:`KNOWN_FINALIZE_STEPS`.
    5. No entry is duplicated within the preset.

    Run once per preset at import time so a typo fails fast at module load
    rather than silently shipping into ``marshal.json``.
    """
    if not isinstance(preset, list):
        raise ValueError(
            f"preset '{name}' must be a list; got {type(preset).__name__}"
        )
    if not preset:
        raise ValueError(f"preset '{name}' must not be empty")
    seen: set[str] = set()
    for step in preset:
        if not isinstance(step, str):
            raise ValueError(
                f"preset '{name}' entry must be a string; "
                f'got {type(step).__name__}'
            )
        if step not in KNOWN_FINALIZE_STEPS:
            raise ValueError(
                f"preset '{name}' references unknown finalize step "
                f"'{step}'; valid steps: {list(KNOWN_FINALIZE_STEPS)}"
            )
        if step in seen:
            raise ValueError(
                f"preset '{name}' lists duplicate finalize step '{step}'"
            )
        seen.add(step)


# Run the self-check at import time so schema typos surface immediately.
for _preset_name, _preset in FinalizeStepPresets._NAME_TO_PRESET.items():
    _validate_preset(_preset_name, _preset)
del _preset_name, _preset
