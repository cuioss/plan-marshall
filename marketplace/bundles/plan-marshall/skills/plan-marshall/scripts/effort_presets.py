# SPDX-License-Identifier: FSL-1.1-ALv2
"""Named effort-level presets for the ``manage-config effort apply-preset`` write API.

Defines :class:`EffortPresets` — a constant-class that bundles a per-phase
effort payload (``{"default": <level>, "roles": {<phase>: <level | dict>, ...}}``)
under three named profiles:

The three profiles form an evenly-spaced ladder along the crude
summed-level metric (sum of the ordinal ``N`` in ``level-N`` across the
nine effort slots): ``economic`` 30, ``balanced`` 36, ``high-end`` 41 —
so each rung is genuinely distinct from its neighbours (every adjacent
step is at least +5).

- ``ECONOMIC`` — minimum-cost configuration; stored in literal-expanded
  form (every ``KNOWN_ROLES`` phase carries an explicit entry mirroring
  the on-disk shape that ``apply-preset economic`` writes after
  ``_expand_phase_effort``). Defaults to ``level-3`` (sonnet, high) and
  lifts ``phase-3-outline``, ``phase-5-execute.default``, and
  ``phase-6-finalize.post-run-review`` to ``level-4`` (opus, medium).
- ``BALANCED`` — middle-of-the-road profile; stored in literal-expanded
  form (every ``KNOWN_ROLES`` phase carries an explicit entry mirroring
  the on-disk shape that ``apply-preset balanced`` writes after
  ``_expand_phase_effort``). Defaults to ``level-4`` (opus, medium),
  lifts the analytical phases (phase-2-refine, phase-4-plan) to
  ``level-4`` and the highest-value reasoning slots (``phase-3-outline``,
  ``phase-5-execute.default``, ``phase-6-finalize.post-run-review``) to
  ``level-5`` (opus, high), keeping the triage (verification-feedback)
  slots AND ``phase-6-finalize.default`` at ``level-3``.
- ``HIGH_END`` — upper-tier profile; stored in literal-expanded form
  (every ``KNOWN_ROLES`` phase carries an explicit entry mirroring the
  on-disk shape that ``apply-preset high-end`` writes after
  ``_expand_phase_effort``). Defaults to ``level-4`` (opus, medium) and
  pushes every analytical (phase-2/3/4) and primary-execution
  (``phase-5-execute.default``) slot plus ``post-run-review`` to
  ``level-5`` (opus, high), keeping only the triage
  (verification-feedback) and finalize-default slots at ``level-4``.
  ``level-5`` is a deliberate preset default here — the top rung is meant
  to be genuinely high-end. ``level-6``/``level-7`` are NOT used as preset
  defaults: they resolve to alias-capability-gated efforts (opus xhigh /
  fable max) that the build target refuses to emit when the resolved alias
  lacks the capability (silently falling back to the canonical variant),
  so those two tiers stay reserved for explicit per-phase opt-in.

The presets sit alongside the role registry inside the
``plan-marshall:plan-marshall`` skill so that policy decisions about
per-role effort levels stay co-located with the registry rather than
leaking into the storage layer (``manage-config``). The constant-class
shape is plain Python dicts — not :class:`enum.Enum`, not
:func:`dataclasses.dataclass` — so the values round-trip through JSON
unchanged when the ``manage-config effort apply-preset`` writer drops
them into ``marshal.json``.

Effort levels use only the values listed in ``ALLOWED_LEVELS``
(``level-1|level-2|level-3|level-4|level-5|level-6|level-7|inherit``).
The ``RESERVED_LEVELS`` tuple is currently empty; a self-check
(:func:`_validate_preset`) runs at import time and raises
:class:`ValueError` if any preset references an unknown effort level.

Hierarchical shape: a preset's ``roles`` block carries a top-level entry
per phase group (``phase-2-refine`` … ``phase-6-finalize``). The value is
either a string (single-level shorthand applied to every workflow under
that phase) or a nested dict with optional sub-keys (``default``,
``verification-feedback``, ``post-run-review`` — see ``KNOWN_ROLES`` in
``manage-config:_cmd_effort`` for the per-phase whitelist). The
:func:`_validate_preset` self-check tolerates both shapes; the writer in
``manage-config:_cmd_effort`` expands a preset's overrides through the
full ``KNOWN_ROLES`` registry at write time and writes the result under
``plan.<phase>.effort`` so the on-disk ``marshal.json`` is co-located
with the rest of the per-phase config.
"""

from __future__ import annotations

import copy

# Allowed effort-level keywords — kept in lock-step with
# ``manage-config/scripts/_cmd_effort.py:ALLOWED_LEVELS`` and the
# ``effort-levels.md`` standard. Duplicated here (rather than imported)
# so this module remains free of any import-time dependency on the
# ``manage-config`` skill scripts; the test suite cross-checks the two
# tuples for drift.
ALLOWED_LEVELS: tuple[str, ...] = (
    'level-1', 'level-2', 'level-3', 'level-4', 'level-5', 'level-6', 'level-7', 'inherit'
)

# RESERVED_LEVELS names keywords that are in the palette but not yet safe to
# select anywhere — a future-additive placeholder. It is currently empty.
#
# Empty does NOT mean a preset may carry any level. No preset carries
# ``level-6`` or ``level-7``, and none may: both resolve to
# alias-capability-gated efforts (opus xhigh / fable max) that the build target
# silently downgrades to the canonical variant when the resolved alias lacks
# the capability. A preset naming them would advertise a tier it cannot
# guarantee to every project that applies it. They remain available for an
# explicit per-phase opt-in, where the operator picks the tier knowingly and
# the possible downgrade is their own trade to make.
#
# The validator below nonetheless accepts ``level-7`` inside a preset, and that
# asymmetry is deliberate rather than a gap: ``_validate_level_keyword``
# enforces the ALLOWED_LEVELS keyword enum, and ``level-7`` is legitimately a
# member of it because per-phase config uses it. "Which levels may appear in a
# PRESET" is a narrower policy the keyword enum cannot express, so it is
# carried by the preset payloads themselves and by this comment — not by a
# validator rejection. Repopulating this tuple would be the wrong fix: it would
# forbid ``level-7`` in the per-phase config too, where it is sanctioned.
RESERVED_LEVELS: tuple[str, ...] = ()


class EffortPresets:
    """Named effort presets for ``manage-config effort apply-preset``.

    Each class-level constant is a ready-to-write per-phase effort payload
    shaped like the schema documented in ``effort-roles.md``::

        {
            "default": "<level>",
            "roles": {
                "<phase>": "<level>",
                "<phase>": {
                    "<subkey>": "<level>",
                    ...
                },
                ...
            },
        }

    The class methods (:meth:`get`, :meth:`all_names`, :meth:`describe`)
    are the only sanctioned access path. :meth:`get` returns a deep copy
    so callers cannot accidentally mutate the class-level constants.
    """

    # ---- preset payloads -------------------------------------------------

    ECONOMIC: dict = {
        'default': 'level-3',
        'roles': {
            'phase-2-refine': 'level-3',
            'phase-3-outline': 'level-4',
            'phase-4-plan': 'level-3',
            'phase-5-execute': {
                'default': 'level-4',
                'verification-feedback': 'level-3',
            },
            'phase-6-finalize': {
                'default': 'level-3',
                'verification-feedback': 'level-3',
                'post-run-review': 'level-4',
            },
        },
    }
    """Minimum-cost preset, stored in literal-expanded form (every
    ``KNOWN_ROLES`` phase carries an explicit entry). Default ``level-3``
    (sonnet, high); lifts ``phase-3-outline``, ``phase-5-execute.default``,
    and ``phase-6-finalize.post-run-review`` to ``level-4`` (opus, medium),
    keeping every other slot at ``level-3``. Summed-level spread 30. The
    redundancy against the bubbling-resolution semantics is intentional — it
    mirrors the on-disk shape produced by ``apply-preset economic`` after
    ``_expand_phase_effort`` so the wizard's deep-equality match in
    ``effort-menu.md`` Step 1 recognises ``Current: economic preset``."""

    BALANCED: dict = {
        'default': 'level-4',
        'roles': {
            'phase-2-refine': 'level-4',
            'phase-3-outline': 'level-5',
            'phase-4-plan': 'level-4',
            'phase-5-execute': {
                'default': 'level-5',
                'verification-feedback': 'level-3',
            },
            'phase-6-finalize': {
                'default': 'level-3',
                'verification-feedback': 'level-3',
                'post-run-review': 'level-5',
            },
        },
    }
    """Middle-of-the-road preset, stored in literal-expanded form (every
    ``KNOWN_ROLES`` phase carries an explicit entry). Default ``level-4``
    (opus, medium); lifts the analytical phases (phase-2-refine,
    phase-4-plan) to ``level-4`` and the highest-value reasoning slots
    (``phase-3-outline``, ``phase-5-execute.default``,
    ``phase-6-finalize.post-run-review``) to ``level-5`` (opus, high),
    keeping the triage (verification-feedback) slots AND
    ``phase-6-finalize.default`` at ``level-3``.
    Summed-level spread 36. The redundancy against the bubbling-resolution
    semantics is intentional — it mirrors the on-disk shape produced by
    ``apply-preset balanced`` after ``_expand_phase_effort`` so the wizard's
    deep-equality match in ``effort-menu.md`` Step 1 recognises ``Current:
    balanced preset``."""

    HIGH_END: dict = {
        'default': 'level-4',
        'roles': {
            'phase-2-refine': 'level-5',
            'phase-3-outline': 'level-5',
            'phase-4-plan': 'level-5',
            'phase-5-execute': {
                'default': 'level-5',
                'verification-feedback': 'level-4',
            },
            'phase-6-finalize': {
                'default': 'level-4',
                'verification-feedback': 'level-4',
                'post-run-review': 'level-5',
            },
        },
    }
    """Upper-tier preset, stored in literal-expanded form (every
    ``KNOWN_ROLES`` phase carries an explicit entry). Default ``level-4``
    (opus, medium); pushes every analytical phase (phase-2/3/4), the
    per-task implementation tier (``phase-5-execute.default``), and
    ``post-run-review`` to ``level-5`` (opus, high), keeping only the triage
    (verification-feedback) and finalize-default slots at ``level-4``.
    Summed-level spread 41. ``level-5`` is a deliberate preset default here —
    the top rung is meant to be genuinely high-end; ``level-6``/``level-7``
    stay out of presets because their alias-capability-gated efforts (opus
    xhigh / fable max) silently fall back to the canonical variant when the
    resolved alias lacks the capability. The redundancy against the
    bubbling-resolution semantics is intentional — it mirrors the on-disk
    shape produced by ``apply-preset high-end`` after ``_expand_phase_effort``
    so the wizard's deep-equality match in ``effort-menu.md`` Step 1
    recognises ``Current: high-end preset``."""

    # ---- canonical name table -------------------------------------------

    # Display order matches the wizard prompt order (cheapest ➜ most
    # expensive). Keep ``_NAME_TO_PRESET`` keyed by the canonical
    # lowercase / hyphenated name; aliases are resolved by ``get``.
    _NAME_TO_PRESET: dict[str, dict] = {
        'economic': ECONOMIC,
        'balanced': BALANCED,
        'high-end': HIGH_END,
    }

    # ---- pre-respread legacy shapes (recognition-only) -------------------

    # Effort-preset payload shapes a PRIOR release wrote and the current
    # release no longer writes, kept so the wizard recognises an existing
    # project's preset instead of silently reclassifying it as ``custom``
    # (the deep-equality-match brittleness — see ``identify``). Only the two
    # shapes that no current preset matches are listed: the previous
    # ``economic`` (summed-level spread 23) and the previous ``high-end``
    # (spread 34). The previous ``balanced`` (spread 30) is deliberately
    # absent — it is byte-identical to the CURRENT ``economic`` payload, so
    # ``identify`` resolves it as ``economic``/``current`` (current match is
    # checked first), and listing it here would only mislead. These shapes are
    # NEVER written — they exist to CLASSIFY an on-disk config and offer a
    # re-apply, never to migrate values silently (re-applying is the user's
    # opt-in, honouring the cost increase the re-spread carries).
    # SHIM(A): pre-respread effort-preset payload shapes (recognised so the wizard offers re-apply instead of silently reclassifying as custom).
    # shim-owner: plan-marshall (effort_presets)
    # shim-floor: the effort-ladder re-spread that changed the economic/balanced/high-end payloads (economic 23->30, balanced 30->36, high-end 34->41)
    # shim-remove-when: no live marshal.json carries a pre-respread economic (spread 23) or high-end (spread 34) preset shape
    _LEGACY_PRESETS: dict[str, dict] = {
        'economic': {
            'default': 'level-2',
            'roles': {
                'phase-2-refine': 'level-3',
                'phase-3-outline': 'level-3',
                'phase-4-plan': 'level-3',
                'phase-5-execute': {
                    'default': 'level-2',
                    'verification-feedback': 'level-3',
                },
                'phase-6-finalize': {
                    'default': 'level-2',
                    'verification-feedback': 'level-3',
                    'post-run-review': 'level-2',
                },
            },
        },
        'high-end': {
            'default': 'level-3',
            'roles': {
                'phase-2-refine': 'level-4',
                'phase-3-outline': 'level-4',
                'phase-4-plan': 'level-4',
                'phase-5-execute': {
                    'default': 'level-4',
                    'verification-feedback': 'level-4',
                },
                'phase-6-finalize': {
                    'default': 'level-3',
                    'verification-feedback': 'level-4',
                    'post-run-review': 'level-4',
                },
            },
        },
    }

    _DESCRIPTIONS: dict[str, str] = {
        'economic': (
            'Minimum-cost preset (literal-expanded) — default level-3 '
            '(sonnet high), with phase-3-outline, phase-5-execute.default, '
            'and phase-6-finalize.post-run-review at level-4 (opus medium); '
            'summed-level spread 30. Mirrors the on-disk shape written by '
            'apply-preset economic.'
        ),
        # ``balanced`` is the only preset with slots BELOW its stated default,
        # so it is the only one whose description must name the remainder:
        # economic's level-3 default is its floor and nothing sits under
        # high-end's level-4, so their unnamed slots correctly reconstruct to
        # the stated default. Leaving balanced's three level-3 slots unnamed
        # reconstructed to a spread of 39 against a payload of 36, overstating
        # the tier to an operator reading this string in the wizard prompt.
        'balanced': (
            'Middle-of-the-road preset (literal-expanded) — default level-4 '
            '(opus medium), with the analytical phases phase-2-refine and '
            'phase-4-plan at level-4, the highest-value slots '
            '(phase-3-outline, phase-5-execute.default, '
            'phase-6-finalize.post-run-review) at level-5 (opus high), and '
            'the triage slots (phase-5-execute.verification-feedback, '
            'phase-6-finalize.verification-feedback) plus '
            'phase-6-finalize.default at level-3 (sonnet high); '
            'summed-level spread 36. Mirrors the on-disk shape written by '
            'apply-preset balanced.'
        ),
        # Like ``balanced`` above, every slot that deviates from the stated
        # default is named by its canonical token. "every analytical phase"
        # and a bare "post-run-review" both read as prose an operator can only
        # resolve by already knowing the registry, which is exactly what a
        # reconstructable description must not require.
        'high-end': (
            'Upper-tier preset (literal-expanded) — default level-4 (opus '
            'medium), with the analytical phases phase-2-refine, '
            'phase-3-outline and phase-4-plan, plus phase-5-execute.default '
            'and phase-6-finalize.post-run-review, at level-5 (opus high); '
            'summed-level spread 41. Mirrors the on-disk shape written by '
            'apply-preset high-end. level-6/level-7 stay opt-in only '
            '(alias-gated).'
        ),
    }

    # ---- public API ------------------------------------------------------

    @classmethod
    def get(cls, name: str) -> dict:
        """Return the preset payload for ``name`` as a deep copy.

        ``name`` is matched case-insensitively. Both hyphen and underscore
        spellings of ``high-end`` are accepted (so ``HIGH_END``,
        ``high_end``, ``High-End`` all resolve). The returned dict is a
        deep copy of the class-level constant so callers can mutate it
        freely without poisoning the registry for subsequent callers.

        Args:
            name: Preset name. Accepts any case-insensitive variant of
                ``economic``, ``balanced``, ``high-end``, or ``high_end``.

        Returns:
            A deep copy of the preset's payload, ready to be expanded
            into per-phase ``effort`` entries by the writer.

        Raises:
            ValueError: When ``name`` does not match any known preset.
                The message lists the canonical names returned by
                :meth:`all_names` so callers can surface a useful error.
        """
        if not isinstance(name, str):
            raise ValueError(
                f'preset name must be a string; got {type(name).__name__}. '
                f'Valid names: {cls.all_names()}'
            )
        # Normalise: lowercase, then convert underscores to hyphens so
        # ``HIGH_END`` and ``high_end`` map to the canonical ``high-end``.
        canonical = name.strip().lower().replace('_', '-')
        preset = cls._NAME_TO_PRESET.get(canonical)
        if preset is None:
            raise ValueError(
                f"unknown preset '{name}'; valid names: {cls.all_names()}"
            )
        return copy.deepcopy(preset)

    @classmethod
    def all_names(cls) -> list[str]:
        """Return the canonical preset names in display order.

        The display order is cheapest ➜ most expensive: ``economic``,
        ``balanced``, ``high-end``. Used as the ``argparse choices=...``
        list for ``manage-config effort apply-preset --preset`` so
        argparse rejects unknown names before the handler runs.
        """
        return list(cls._NAME_TO_PRESET.keys())

    @classmethod
    def describe(cls, name: str) -> str:
        """Return a one-line human description of preset ``name``.

        Used by the ``marshall-steward`` Effort submenu to annotate the
        preset-selection prompt. Accepts the same case-insensitive /
        underscore-aliased input as :meth:`get`.

        Raises:
            ValueError: When ``name`` does not match any known preset.
        """
        if not isinstance(name, str):
            raise ValueError(
                f'preset name must be a string; got {type(name).__name__}. '
                f'Valid names: {cls.all_names()}'
            )
        canonical = name.strip().lower().replace('_', '-')
        description = cls._DESCRIPTIONS.get(canonical)
        if description is None:
            raise ValueError(
                f"unknown preset '{name}'; valid names: {cls.all_names()}"
            )
        return description

    @classmethod
    def identify(cls, payload: dict) -> dict:
        """Classify a reconstructed effort payload against the preset ladder.

        The configuration wizard recognises a project's preset by
        deep-equality of its on-disk effort configuration against the preset
        payloads (see ``marshall-steward:effort-menu.md`` Step 1). A value
        re-spread changes those payloads, so a project holding a PRIOR
        ladder's shape would stop matching every current preset and be
        silently reclassified as ``custom``. This method closes that gap: it
        first tries an exact match against the CURRENT presets, then against
        the pre-respread :data:`_LEGACY_PRESETS` shapes, so a legacy config is
        reported as its old preset name with a ``previous-ladder`` status the
        wizard surfaces as a re-apply offer.

        Current match is checked FIRST, so a payload that is byte-identical to
        both a current preset and a legacy shape (the previous ``balanced``,
        now identical to the current ``economic``) resolves to the current
        preset — never the stale legacy name.

        Args:
            payload: The reconstructed ``{"default": ..., "roles": {...}}``
                effort payload (the same shape the preset constants carry),
                as rebuilt from ``plan.effort`` + every ``plan.<phase>.effort``
                by the caller.

        Returns:
            ``{"name": <preset name | None>, "status": <status>}`` where
            ``status`` is one of:

            - ``current`` — ``payload`` equals a current preset; ``name`` is it.
            - ``previous-ladder`` — ``payload`` equals a pre-respread shape no
              current preset matches; ``name`` is the preset it used to be.
              Re-applying that preset adopts the current (re-spread) values.
            - ``custom`` — ``payload`` matches nothing; ``name`` is ``None``.

        Never mutates ``payload`` and never writes anything — recognition only.
        """
        if not isinstance(payload, dict) or 'default' not in payload or 'roles' not in payload:
            return {'name': None, 'status': 'custom'}
        for name, preset in cls._NAME_TO_PRESET.items():
            if payload == preset:
                return {'name': name, 'status': 'current'}
        for name, legacy in cls._LEGACY_PRESETS.items():
            if payload == legacy:
                return {'name': name, 'status': 'previous-ladder'}
        return {'name': None, 'status': 'custom'}


# --- import-time self-check ----------------------------------------------


def _validate_level_keyword(level: str, where: str) -> None:
    """Raise ValueError when ``level`` is not in the allowed-levels enum."""
    if level in RESERVED_LEVELS:
        # This validator only ever runs over PRESETS, so the advice names the
        # highest tier a preset may carry — not the highest tier the palette
        # has. Pointing a preset author at ``level-7`` (as it used to) sent
        # them straight into the alias-gated tiers the RESERVED_LEVELS comment
        # above rules out of presets.
        raise ValueError(
            f"{where} effort '{level}' is reserved (future-additive); "
            f"use 'level-5', the highest tier a preset carries — 'level-6' "
            f"and 'level-7' are alias-gated and stay per-phase opt-in only"
        )
    if level not in ALLOWED_LEVELS:
        raise ValueError(
            f"{where} effort '{level}' is not in ALLOWED_LEVELS "
            f'{list(ALLOWED_LEVELS)}'
        )


def _validate_preset(name: str, preset: dict) -> None:
    """Validate a preset against the allowed-levels enum.

    Checks (raises :class:`ValueError` on the first failure):

    1. ``preset`` is a dict.
    2. ``preset['default']`` is present and a member of
       :data:`ALLOWED_LEVELS` (and not in :data:`RESERVED_LEVELS`).
    3. ``preset['roles']`` is a dict (may be empty).
    4. Every value in ``preset['roles']`` is either a string in
       :data:`ALLOWED_LEVELS` (single-level shorthand for the whole phase)
       or a dict whose values are strings in :data:`ALLOWED_LEVELS`
       (per-sub-key overrides).

    Run once per preset at import time so a typo fails fast at module
    load rather than silently shipping into ``marshal.json``.
    """
    if not isinstance(preset, dict):
        raise ValueError(
            f"preset '{name}' must be a dict; got {type(preset).__name__}"
        )
    default = preset.get('default')
    if default is None:
        raise ValueError(f"preset '{name}' missing required 'default' key")
    if not isinstance(default, str):
        raise ValueError(
            f"preset '{name}' 'default' must be a string; "
            f'got {type(default).__name__}'
        )
    _validate_level_keyword(default, f"preset '{name}' default")

    roles = preset.get('roles')
    if not isinstance(roles, dict):
        raise ValueError(
            f"preset '{name}' 'roles' must be a dict; "
            f'got {type(roles).__name__}'
        )
    for group, group_value in roles.items():
        if isinstance(group_value, str):
            _validate_level_keyword(
                group_value, f"preset '{name}' role '{group}'"
            )
        elif isinstance(group_value, dict):
            for subkey, sub_value in group_value.items():
                if not isinstance(sub_value, str):
                    raise ValueError(
                        f"preset '{name}' role '{group}.{subkey}' effort "
                        f'must be a string; got {type(sub_value).__name__}'
                    )
                _validate_level_keyword(
                    sub_value, f"preset '{name}' role '{group}.{subkey}'"
                )
        else:
            raise ValueError(
                f"preset '{name}' role '{group}' must be a string or dict; "
                f'got {type(group_value).__name__}'
            )


# Run the self-check at import time so schema typos surface immediately.
# Both the current presets and the pre-respread legacy shapes are validated:
# a legacy shape referencing an unknown level would misclassify a live config.
for _preset_name, _preset in EffortPresets._NAME_TO_PRESET.items():
    _validate_preset(_preset_name, _preset)
for _preset_name, _preset in EffortPresets._LEGACY_PRESETS.items():
    _validate_preset(f'{_preset_name} (legacy)', _preset)
del _preset_name, _preset
