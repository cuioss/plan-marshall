"""Named model-level presets for the ``manage-config models`` write API.

Defines :class:`ModelPresets` — a constant-class that bundles a ``models``
block payload (``{"default": <level>, "roles": {<group>: <level | dict>, ...}}``)
under three named profiles:

- ``ECONOMIC`` — minimum-cost configuration; reserves ``medium`` for the
  reasoning-heavy roles and leaves everything else at ``low``.
- ``BALANCED`` — middle-of-the-road profile; defaults to ``medium`` and
  bumps the four phase-group roles that most consistently benefit from
  extra reasoning to ``high``.
- ``HIGH_END`` — maximum-quality profile; defaults to ``high`` and pushes
  the deep-reasoning cross-phase roles to ``xhigh`` / ``xxhigh`` / ``max``.

The presets sit alongside the role registry inside the
``plan-marshall:plan-marshall`` skill so that policy decisions about
per-role levels stay co-located with the registry rather than leaking
into the storage layer (``manage-config``). The constant-class shape is
plain Python dicts — not :class:`enum.Enum`, not :func:`dataclasses.dataclass`
— so the values round-trip through JSON unchanged when the
``manage-config models apply-preset`` writer drops them into
``marshal.json``.

Levels use only the values listed in ``ALLOWED_LEVELS``
(``low|medium|high|xhigh|xxhigh|max|inherit``). The ``RESERVED_LEVELS``
tuple is currently empty; a self-check (:func:`_validate_preset`) runs
at import time and raises :class:`ValueError` if any preset references
an unknown level.

Hierarchical shape: a preset's ``roles`` block carries a top-level entry
per role group. The value is either a string (for flat single-workflow
phase groups like ``phase-1`` … ``phase-5``) or a nested dict (for
multi-workflow groups ``phase-6`` and ``cross``). The :func:`_validate_preset`
self-check tolerates both shapes; the resolver in
``manage-config:_cmd_models`` expands a preset's overrides through the
full ``KNOWN_ROLES`` registry at write time, so the on-disk
``marshal.json`` is always fully qualified.
"""

from __future__ import annotations

import copy

# Allowed-levels enum — kept in lock-step with
# ``manage-config/scripts/_cmd_models.py:ALLOWED_LEVELS`` and the
# ``model-levels.md`` standard. Duplicated here (rather than imported)
# so this module remains free of any import-time dependency on the
# ``manage-config`` skill scripts; the test suite cross-checks the two
# tuples for drift.
ALLOWED_LEVELS: tuple[str, ...] = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'max', 'inherit')

# No levels are currently reserved. ``max`` was promoted from reserved-future
# to live (resolves to opus, xhigh — Opus-4.7-only) so presets may reference
# it. Future palette expansion may repopulate this tuple.
RESERVED_LEVELS: tuple[str, ...] = ()


class ModelPresets:
    """Named ``models`` block presets for ``manage-config models apply-preset``.

    Each class-level constant is a ready-to-write ``models`` block payload
    shaped like the schema documented in ``model-roles.md``::

        {
            "default": "<level>",
            "roles": {
                "<flat-group>": "<level>",
                "<nested-group>": {
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
            'phase-3': 'medium',
            'phase-4': 'medium',
            'cross': {
                'research': 'medium',
                'q-gate-validation': 'medium',
            },
        },
    }
    """Minimum-cost preset. Default ``low``; bumps phase-3 outline and
    phase-4 plan-time analysis to ``medium`` along with the two cross-phase
    reasoning roles. Use when running large batches of routine plans where
    output quality is acceptable at the cheapest tier."""

    BALANCED: dict = {
        'default': 'medium',
        'roles': {
            'phase-2': 'high',
            'phase-3': 'high',
            'phase-4': 'high',
            'cross': {
                'research': 'high',
                'triage': 'high',
                'q-gate-validation': 'high',
            },
        },
    }
    """Middle-of-the-road preset. Default ``medium``; bumps the three
    analytical phase groups (phase-2 refine, phase-3 outline, phase-4 plan)
    and the cross-phase research/triage/q-gate cores to ``high``. The
    recommended default for non-trivial work."""

    HIGH_END: dict = {
        'default': 'high',
        'roles': {
            'phase-2': 'xhigh',
            'phase-3': 'xhigh',
            'phase-4': 'xhigh',
            'phase-6': {
                'retrospective': 'xhigh',
                'pr-doctor': 'xhigh',
            },
            'cross': {
                'research': 'max',
                'triage': 'xhigh',
                'q-gate-validation': 'xhigh',
                'plugin-doctor': 'xhigh',
            },
        },
    }
    """Maximum-quality preset. Default ``high``; pushes the analytical phase
    groups and the deep-reasoning cross-phase cores to ``xhigh`` / ``xxhigh`` /
    ``max``. ``cross.research`` rides at ``max`` (Opus-4.7-only — falls back
    to canonical when the alias does not accept ``effort: xhigh``).
    Use for high-stakes plans where the extra reasoning cost is justified by
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
            'Minimum-cost preset — default low, with phase-3, phase-4, '
            'and cross.research/cross.q-gate-validation bumped to medium.'
        ),
        'balanced': (
            'Middle-of-the-road preset — default medium, with phase-2, '
            'phase-3, phase-4, and cross.research/triage/q-gate-validation '
            'bumped to high.'
        ),
        'high-end': (
            'Maximum-quality preset — default high, with reasoning-heavy '
            'roles pushed to xhigh / xxhigh / max.'
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
            A deep copy of the preset's ``models`` block payload, ready
            to be written to ``marshal.json``.

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
        list for ``manage-config models apply-preset --preset`` so
        argparse rejects unknown names before the handler runs.
        """
        return list(cls._NAME_TO_PRESET.keys())

    @classmethod
    def describe(cls, name: str) -> str:
        """Return a one-line human description of preset ``name``.

        Used by the ``marshall-steward`` Models submenu to annotate the
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
            f"{where} level '{level}' is reserved (future-additive); "
            f"use 'max' for the current top tier"
        )
    if level not in ALLOWED_LEVELS:
        raise ValueError(
            f"{where} level '{level}' is not in ALLOWED_LEVELS "
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
       :data:`ALLOWED_LEVELS` (flat group) or a dict whose values are
       strings in :data:`ALLOWED_LEVELS` (nested group).

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
                        f"preset '{name}' role '{group}.{subkey}' level "
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
for _preset_name, _preset in ModelPresets._NAME_TO_PRESET.items():
    _validate_preset(_preset_name, _preset)
del _preset_name, _preset
