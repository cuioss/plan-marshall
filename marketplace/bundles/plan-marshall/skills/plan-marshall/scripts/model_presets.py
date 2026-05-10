"""Named model-level presets for the ``manage-config models`` write API.

Defines :class:`ModelPresets` — a constant-class that bundles a ``models``
block payload (``{"default": <level>, "roles": {<role>: <level>, ...}}``)
under three named profiles:

- ``ECONOMIC`` — minimum-cost configuration; reserves ``medium`` for the
  reasoning-heavy roles (``q_gate_validation``, ``research``,
  ``phase_plan``) and leaves everything else at ``low``.
- ``BALANCED`` — middle-of-the-road profile; defaults to ``medium`` and
  bumps the four roles that most consistently benefit from extra
  reasoning (``q_gate_validation``, ``research``, ``phase_plan``,
  ``automated_review``) to ``high``.
- ``HIGH_END`` — maximum-quality profile; defaults to ``high`` and pushes
  the deep-reasoning roles to ``xhigh`` / ``xxhigh``.

The presets sit alongside the role registry inside the
``plan-marshall:plan-marshall`` skill so that policy decisions about
per-role levels stay co-located with the registry rather than leaking
into the storage layer (``manage-config``). The constant-class shape is
plain Python dicts — not :class:`enum.Enum`, not :func:`dataclasses.dataclass`
— so the values round-trip through JSON unchanged when the
``manage-config models apply-preset`` writer drops them into
``marshal.json``.

Levels use only the values listed in ``ALLOWED_LEVELS``
(``low|medium|high|xhigh|xxhigh|inherit``). The ``max`` level is
reserved (future-additive) and is therefore forbidden in presets — a
self-check (:func:`_validate_preset`) runs at import time and raises
:class:`ValueError` if any preset deviates. Renaming or retiring a role
in ``_cmd_models.KNOWN_ROLES`` without also updating the presets is
caught by the cross-check tests; the module itself does not import the
role registry to keep the dependency graph one-way (presets ➜
``manage-config``, never the reverse).
"""

from __future__ import annotations

import copy

# Allowed-levels enum — kept in lock-step with
# ``manage-config/scripts/_cmd_models.py:ALLOWED_LEVELS`` and the
# ``model-levels.md`` standard. Duplicated here (rather than imported)
# so this module remains free of any import-time dependency on the
# ``manage-config`` skill scripts; the test suite cross-checks the two
# tuples for drift.
ALLOWED_LEVELS: tuple[str, ...] = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'inherit')

# ``max`` is reserved as a future-additive level (see ``model-levels.md``).
# Presets must never reference it; ``_validate_preset`` raises if they do.
RESERVED_LEVELS: tuple[str, ...] = ('max',)


class ModelPresets:
    """Named ``models`` block presets for ``manage-config models apply-preset``.

    Each class-level constant is a ready-to-write ``models`` block payload
    shaped like the schema documented in ``model-levels.md``::

        {
            "default": "<level>",
            "roles": {
                "<role>": "<level>",
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
            'q_gate_validation': 'medium',
            'research': 'medium',
            'phase_plan': 'medium',
        },
    }
    """Minimum-cost preset. Default ``low``; bumps the three reasoning-heavy
    roles to ``medium``. Use when running large batches of routine plans
    where output quality is acceptable at the cheapest tier."""

    BALANCED: dict = {
        'default': 'medium',
        'roles': {
            'q_gate_validation': 'high',
            'research': 'high',
            'phase_plan': 'high',
            'automated_review': 'high',
        },
    }
    """Middle-of-the-road preset. Default ``medium``; bumps four roles
    (``q_gate_validation``, ``research``, ``phase_plan``,
    ``automated_review``) to ``high``. The recommended default for
    non-trivial work."""

    HIGH_END: dict = {
        'default': 'high',
        'roles': {
            'q_gate_validation': 'xhigh',
            'research': 'xxhigh',
            'phase_plan': 'xhigh',
            'automated_review': 'xhigh',
            'sonar_roundtrip': 'xhigh',
        },
    }
    """Maximum-quality preset. Default ``high``; pushes the deep-reasoning
    roles to ``xhigh`` / ``xxhigh``. Use for high-stakes plans where the
    extra reasoning cost is justified by output quality."""

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
            'Minimum-cost preset — default low, with q_gate_validation, '
            'research, and phase_plan bumped to medium.'
        ),
        'balanced': (
            'Middle-of-the-road preset — default medium, with '
            'q_gate_validation, research, phase_plan, and automated_review '
            'bumped to high.'
        ),
        'high-end': (
            'Maximum-quality preset — default high, with reasoning-heavy '
            'roles pushed to xhigh / xxhigh.'
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


def _validate_preset(name: str, preset: dict) -> None:
    """Validate a preset against the allowed-levels enum.

    Checks (raises :class:`ValueError` on the first failure):

    1. ``preset`` is a dict.
    2. ``preset['default']`` is present and a member of
       :data:`ALLOWED_LEVELS` (and not in :data:`RESERVED_LEVELS`).
    3. ``preset['roles']`` is a dict (may be empty).
    4. Every value in ``preset['roles']`` is a string in
       :data:`ALLOWED_LEVELS` (and not in :data:`RESERVED_LEVELS`).

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
    if default in RESERVED_LEVELS:
        raise ValueError(
            f"preset '{name}' default level '{default}' is reserved "
            f"(future-additive); use 'xxhigh' for the current top tier"
        )
    if default not in ALLOWED_LEVELS:
        raise ValueError(
            f"preset '{name}' default level '{default}' is not in "
            f"ALLOWED_LEVELS {list(ALLOWED_LEVELS)}"
        )
    roles = preset.get('roles')
    if not isinstance(roles, dict):
        raise ValueError(
            f"preset '{name}' 'roles' must be a dict; "
            f'got {type(roles).__name__}'
        )
    for role_name, level in roles.items():
        if not isinstance(level, str):
            raise ValueError(
                f"preset '{name}' role '{role_name}' level must be a "
                f'string; got {type(level).__name__}'
            )
        if level in RESERVED_LEVELS:
            raise ValueError(
                f"preset '{name}' role '{role_name}' level '{level}' is "
                f"reserved (future-additive); use 'xxhigh' for the current "
                f'top tier'
            )
        if level not in ALLOWED_LEVELS:
            raise ValueError(
                f"preset '{name}' role '{role_name}' level '{level}' is "
                f'not in ALLOWED_LEVELS {list(ALLOWED_LEVELS)}'
            )


# Run the self-check at import time so schema typos surface immediately.
for _preset_name, _preset in ModelPresets._NAME_TO_PRESET.items():
    _validate_preset(_preset_name, _preset)
del _preset_name, _preset
