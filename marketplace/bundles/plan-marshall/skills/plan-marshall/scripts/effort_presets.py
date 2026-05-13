"""Named effort-level presets for the ``manage-config effort apply-preset`` write API.

Defines :class:`EffortPresets` — a constant-class that bundles a per-phase
effort payload (``{"default": <level>, "roles": {<phase>: <level | dict>, ...}}``)
under three named profiles:

- ``ECONOMIC`` — minimum-cost configuration; reserves ``medium`` for the
  outline + plan phases and leaves everything else at ``low``.
- ``BALANCED`` — middle-of-the-road profile; defaults to ``medium`` and
  bumps the analytical phases plus the verification-feedback workflow
  on phase-5-execute and phase-6-finalize to ``high``.
- ``HIGH_END`` — maximum-quality profile; defaults to ``high`` and pushes
  the analytical phases to ``xhigh``.

The presets sit alongside the role registry inside the
``plan-marshall:plan-marshall`` skill so that policy decisions about
per-role effort levels stay co-located with the registry rather than
leaking into the storage layer (``manage-config``). The constant-class
shape is plain Python dicts — not :class:`enum.Enum`, not
:func:`dataclasses.dataclass` — so the values round-trip through JSON
unchanged when the ``manage-config effort apply-preset`` writer drops
them into ``marshal.json``.

Effort levels use only the values listed in ``ALLOWED_LEVELS``
(``low|medium|high|xhigh|xxhigh|max|inherit``). The ``RESERVED_LEVELS``
tuple is currently empty; a self-check (:func:`_validate_preset`) runs
at import time and raises :class:`ValueError` if any preset references
an unknown effort level.

Hierarchical shape: a preset's ``roles`` block carries a top-level entry
per phase group (``phase-1-init`` … ``phase-6-finalize``). The value is
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
ALLOWED_LEVELS: tuple[str, ...] = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'max', 'inherit')

# No effort levels are currently reserved. ``max`` was promoted from
# reserved-future to live (resolves to opus, xhigh — Opus-4.7-only) so
# presets may reference it. Future palette expansion may repopulate this
# tuple.
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
        'default': 'low',
        'roles': {
            'phase-3-outline': 'medium',
            'phase-4-plan': 'medium',
        },
    }
    """Minimum-cost preset. Default ``low``; bumps phase-3-outline and
    phase-4-plan to ``medium``. Use when running large batches of routine
    plans where output quality is acceptable at the cheapest tier."""

    BALANCED: dict = {
        'default': 'medium',
        'roles': {
            'phase-2-refine': 'high',
            'phase-3-outline': 'high',
            'phase-4-plan': 'high',
            'phase-5-execute': {'verification-feedback': 'high'},
            'phase-6-finalize': {'verification-feedback': 'high'},
        },
    }
    """Middle-of-the-road preset. Default ``medium``; bumps the three
    analytical phases (phase-2-refine, phase-3-outline, phase-4-plan) to
    ``high``, plus the verification-feedback workflow on phase-5-execute
    (build-runner triage) and phase-6-finalize (sonar / pr-comment /
    plugin-doctor / pr-state triage). The recommended default for
    non-trivial work."""

    HIGH_END: dict = {
        'default': 'high',
        'roles': {
            'phase-2-refine': 'xhigh',
            'phase-3-outline': 'xhigh',
            'phase-4-plan': 'xhigh',
            'phase-5-execute': {'verification-feedback': 'xhigh'},
            'phase-6-finalize': {
                'verification-feedback': 'xhigh',
                'post-run-review': 'xhigh',
            },
        },
    }
    """Maximum-quality preset. Default ``high``; pushes the analytical
    phases to ``xhigh``. Phase-5-execute / phase-6-finalize
    verification-feedback and phase-6-finalize post-run-review
    (retrospective + lessons-capture) ride at ``xhigh``. Use for
    high-stakes plans where the extra reasoning cost is justified by
    output quality."""

    # ---- canonical name table -------------------------------------------

    # Display order matches the wizard prompt order (cheapest ➜ most
    # expensive). Keep ``_NAME_TO_PRESET`` keyed by the canonical
    # lowercase / hyphenated name; aliases are resolved by ``get``.
    _NAME_TO_PRESET: dict[str, dict] = {
        'economic': ECONOMIC,
        'balanced': BALANCED,
        'high-end': HIGH_END,
    }

    _DESCRIPTIONS: dict[str, str] = {
        'economic': (
            'Minimum-cost preset — default low, with phase-3-outline and '
            'phase-4-plan bumped to medium.'
        ),
        'balanced': (
            'Middle-of-the-road preset — default medium, with '
            'phase-2-refine / phase-3-outline / phase-4-plan and '
            'phase-5-execute / phase-6-finalize verification-feedback '
            'bumped to high.'
        ),
        'high-end': (
            'Maximum-quality preset — default high, analytical phases at '
            'xhigh, phase-5-execute / phase-6-finalize verification-feedback '
            'and phase-6-finalize post-run-review at xhigh.'
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


# --- import-time self-check ----------------------------------------------


def _validate_level_keyword(level: str, where: str) -> None:
    """Raise ValueError when ``level`` is not in the allowed-levels enum."""
    if level in RESERVED_LEVELS:
        raise ValueError(
            f"{where} effort '{level}' is reserved (future-additive); "
            f"use 'max' for the current top tier"
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
for _preset_name, _preset in EffortPresets._NAME_TO_PRESET.items():
    _validate_preset(_preset_name, _preset)
del _preset_name, _preset
