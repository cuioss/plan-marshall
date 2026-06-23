"""
Coverage command handler for manage-config.

Handles the two-dial **coverage** contract — ``thoroughness`` (how completely
in-radius items are covered and how deeply their relations are traced) ×
``scope`` (where the boundary is drawn). The two fields resolve through the
SAME polymorphic per-phase walk that ``_cmd_effort.py`` uses for the single
``effort`` level — applied independently to each field.

Handles:
    coverage read --role <name>           (per-field cell resolver)
    coverage read --role <group>.<sub>    (dotted-key resolver)
    coverage read --phase <g> --role <s>  (two-flag form)
    coverage read --phase <g>             (bare-group lookup)
    coverage read --default               (raw `plan.coverage` lookup)
    coverage resolve --role <name>        (resolved cell + coupling result)

Storage layout — per-phase coverage config lives **inside the matching
plan-phase entry** under the ``coverage`` key, alongside the rest of the
phase's knobs. The plan-wide fallback is a single object at
``plan.coverage``::

    plan.<phase>.coverage.<field>  -> plan.<phase>.coverage  (object)
                                   -> plan.coverage           (plan-wide)
                                   -> inherit

Each of the two fields (``thoroughness`` and ``scope``) walks this order
independently, mirroring ``_resolve_level``'s polymorphic walk.

Coupling constraint — the load-bearing config validation, stated verbatim in
``persona-plan-marshall-agent/standards/thoroughness.md`` § Coupling Constraint::

    reject thoroughness >= T4 AND scope < component

Relation-tracing thoroughness lower-bounds scope: you cannot trace a
relationship whose other end lies outside scope, so ``T4 over change-set`` is
incoherent. The validator rejects an incoherent stored cell at lookup time
(from both ``read`` and ``resolve``) with ``error: coverage_coupling_violation``.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    success_exit,
)

# Allowed thoroughness rungs, kept in lock-step with the T1-T5 ladder in
# persona-plan-marshall-agent/standards/thoroughness.md § Thoroughness Ladder.
ALLOWED_THOROUGHNESS = ('T1', 'T2', 'T3', 'T4', 'T5', 'inherit')

# Allowed scope rungs, kept in lock-step with the nested scope ladder in
# persona-plan-marshall-agent/standards/thoroughness.md § Scope Ladder
# (change-set ⊂ artifact ⊂ component ⊂ module ⊂ overall).
ALLOWED_SCOPE = ('change-set', 'artifact', 'component', 'module', 'overall', 'inherit')

# Ordinal rank over the thoroughness ladder, used by the coupling validator.
# 'inherit' is unranked (it is not a concrete rung) and never participates in
# the comparison.
_THOROUGHNESS_RANK = {'T1': 1, 'T2': 2, 'T3': 3, 'T4': 4, 'T5': 5}

# Ordinal rank over the scope ladder (narrowest to widest). 'component' is the
# coupling-constraint floor for T4+.
_SCOPE_RANK = {'change-set': 1, 'artifact': 2, 'component': 3, 'module': 4, 'overall': 5}

# The two thresholds the coupling constraint compares against.
_COUPLING_THOROUGHNESS_FLOOR = _THOROUGHNESS_RANK['T4']
_COUPLING_SCOPE_FLOOR = _SCOPE_RANK['component']

# Phase groups that may carry a per-phase coverage entry. Kept in lock-step
# with KNOWN_ROLES in _cmd_effort.py.
KNOWN_COVERAGE_GROUPS = (
    'phase-1-init',
    'phase-2-refine',
    'phase-3-outline',
    'phase-4-plan',
    'phase-5-execute',
    'phase-6-finalize',
)


def _validate_thoroughness(value: object, source: str) -> tuple[bool, str | None]:
    """Validate a thoroughness keyword.

    Args:
        value: The candidate thoroughness value. Typed ``object`` because it
            may be a non-string read straight from marshal.json — such a value
            is rejected here rather than silently dropped upstream.
        source: Human-readable description of where the value came from,
            included verbatim in error messages for diagnosability.

    Returns:
        (True, None) when valid; (False, error_message) when invalid.
    """
    if value in ALLOWED_THOROUGHNESS:
        return True, None
    return (
        False,
        f"invalid thoroughness '{value}' at {source}; expected one of {list(ALLOWED_THOROUGHNESS)}",
    )


def _validate_scope(value: object, source: str) -> tuple[bool, str | None]:
    """Validate a scope keyword.

    Args:
        value: The candidate scope value. Typed ``object`` because it may be a
            non-string read straight from marshal.json — such a value is
            rejected here rather than silently dropped upstream.
        source: Human-readable description of where the value came from.

    Returns:
        (True, None) when valid; (False, error_message) when invalid.
    """
    if value in ALLOWED_SCOPE:
        return True, None
    return (
        False,
        f"invalid scope '{value}' at {source}; expected one of {list(ALLOWED_SCOPE)}",
    )


def _validate_coupling(thoroughness: object, scope: object) -> tuple[bool, str | None]:
    """Enforce the scope <-> thoroughness coupling constraint.

    Rejects ``thoroughness >= T4 AND scope < component`` per
    persona-plan-marshall-agent/standards/thoroughness.md § Coupling Constraint.
    A relation-tracing thoroughness (T4/T5) cannot be honoured below
    ``component`` scope because the siblings the relations point at are out of
    radius. ``inherit`` on either field is unconstrained — an unresolved dial
    cannot violate the coupling.

    Returns:
        (True, None) when coherent; (False, error_message) when the constraint
        is violated.
    """
    if thoroughness == 'inherit' or scope == 'inherit':
        return True, None

    t_rank = _THOROUGHNESS_RANK.get(thoroughness) if isinstance(thoroughness, str) else None
    s_rank = _SCOPE_RANK.get(scope) if isinstance(scope, str) else None
    if t_rank is None or s_rank is None:
        # Validity is checked separately by _validate_thoroughness/_validate_scope;
        # an unranked-but-allowed value cannot occur here.
        return True, None

    if t_rank >= _COUPLING_THOROUGHNESS_FLOOR and s_rank < _COUPLING_SCOPE_FLOOR:
        return (
            False,
            f"coverage coupling violation: thoroughness '{thoroughness}' (>= T4) "
            f"requires scope >= 'component', but scope is '{scope}'. "
            f"Relation-tracing thoroughness lower-bounds scope (see "
            f"persona-plan-marshall-agent/standards/thoroughness.md § Coupling Constraint: "
            f"reject thoroughness >= T4 AND scope < component).",
        )
    return True, None


def _split_group(args) -> tuple[str | None, str, str | None]:
    """Resolve the requested group from argparse Namespace.

    Coverage cells are keyed only by phase group (no sub-keys), so unlike
    ``effort`` there is no dotted/two-flag sub-key form. ``--phase`` and
    ``--role`` are accepted as synonyms for the group name to keep the CLI
    shape parallel with ``effort read``; a dotted ``--role group.subkey`` is
    reduced to its group (the sub-key is informational for coverage).

    Returns:
        (group, source_label, error). ``group`` is None when an error is set.
        ``source_label`` is a human-readable rendering of the requested key.
    """
    phase = getattr(args, 'phase', None)
    role = getattr(args, 'role', None)

    if phase is None and role is None:
        return None, '', '--role (or --phase) is required'

    if phase is not None:
        return phase, phase, None

    assert role is not None
    if '.' in role:
        group = role.split('.', 1)[0]
        return group, role, None
    return role, role, None


def _resolve_field(
    plan_block: dict,
    plan_wide: dict | None,
    group: str,
    field: str,
) -> tuple[object, str]:
    """Walk the per-phase ``coverage`` config to a single field keyword.

    Resolution order (mirrors ``_resolve_level``, applied per-field):
        1. plan.<group>.coverage.<field>  (per-phase object slot)
        2. plan.coverage.<field>          (plan-wide object slot)
        3. inherit                         (implicit final fallback)

    A *present* field value is returned verbatim — including a non-string
    (e.g. a number or object accidentally written to marshal.json). Such a
    value propagates to ``_validate_thoroughness`` / ``_validate_scope``, which
    reject it with a clear ``invalid {field}`` error rather than silently
    collapsing to ``inherit`` and masking the misconfiguration. Only an
    *absent* slot (``.get`` returns ``None``) falls through to the next tier.

    Returns:
        (value, source). The caller validates ``value`` against the field's
        allowed enum.
    """
    phase_entry = plan_block.get(group)
    if isinstance(phase_entry, dict):
        phase_coverage = phase_entry.get('coverage')
        if isinstance(phase_coverage, dict):
            value = phase_coverage.get(field)
            if value is not None:
                return value, f'plan.{group}.coverage.{field}'

    if isinstance(plan_wide, dict):
        value = plan_wide.get(field)
        if value is not None:
            return value, f'plan.coverage.{field}'

    return 'inherit', 'implicit_default'


def _resolve_cell(args) -> dict:
    """Resolve the (thoroughness, scope) cell for the requested group.

    Shared by ``coverage read`` and ``coverage resolve``. Validates each
    field's enum and the coupling constraint. Returns an ``error_exit`` dict
    on any failure, otherwise a dict carrying the four resolved values.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    config = load_config()
    plan_block = config.get('plan', {})
    if not isinstance(plan_block, dict):
        plan_block = {}
    plan_wide = plan_block.get('coverage')
    if plan_wide is not None and not isinstance(plan_wide, dict):
        plan_wide = None

    # --default short-circuit: read plan.coverage directly (no group walk).
    if getattr(args, 'default', False):
        if isinstance(plan_wide, dict):
            thoroughness = plan_wide.get('thoroughness')
            scope = plan_wide.get('scope')
            thoroughness = thoroughness if isinstance(thoroughness, str) else 'inherit'
            scope = scope if isinstance(scope, str) else 'inherit'
            t_source = 'plan.coverage.thoroughness' if isinstance(plan_wide.get('thoroughness'), str) else 'implicit_default'
            s_source = 'plan.coverage.scope' if isinstance(plan_wide.get('scope'), str) else 'implicit_default'
        else:
            thoroughness, scope = 'inherit', 'inherit'
            t_source = s_source = 'implicit_default'
        group_label = 'plan.coverage'
    else:
        group, group_label, err = _split_group(args)
        if err is not None:
            return error_exit(err)
        assert group is not None
        if group not in KNOWN_COVERAGE_GROUPS:
            return error_exit(
                f"coverage group '{group}' is not a known phase "
                f"(valid: {list(KNOWN_COVERAGE_GROUPS)})"
            )
        thoroughness, t_source = _resolve_field(plan_block, plan_wide, group, 'thoroughness')
        scope, s_source = _resolve_field(plan_block, plan_wide, group, 'scope')

    ok, err = _validate_thoroughness(thoroughness, t_source)
    if not ok:
        return error_exit(err or 'invalid thoroughness')
    ok, err = _validate_scope(scope, s_source)
    if not ok:
        return error_exit(err or 'invalid scope')

    ok, err = _validate_coupling(thoroughness, scope)
    if not ok:
        return error_exit(err or 'coverage coupling violation', error_type='coverage_coupling_violation')

    return success_exit(
        {
            'role': group_label,
            'thoroughness': thoroughness,
            'scope': scope,
            'thoroughness_source': t_source,
            'scope_source': s_source,
        }
    )


def cmd_coverage_read(args) -> dict:
    """Handle ``coverage read`` subcommand (resolve a cell for a phase/role)."""
    return _resolve_cell(args)


def cmd_coverage_resolve(args) -> dict:
    """Handle ``coverage resolve`` subcommand.

    Returns the resolved ``{thoroughness, scope, thoroughness_source,
    scope_source}`` cell plus a ``coupling`` field for downstream consumers
    (the components that implement the coverage-gathering contract, which fall
    back to this project-default resolver when no per-invocation cell was
    gathered). The coupling constraint is already enforced inside
    :func:`_resolve_cell` — reaching this point means the cell is coherent, so
    ``coupling`` is always ``ok`` on success.
    """
    result = _resolve_cell(args)
    if result.get('status') != 'success':
        return result
    result['coupling'] = 'ok'
    return result


def cmd_coverage_expand(args) -> dict:
    """Handle ``coverage expand`` subcommand.

    Expands the requested ``(thoroughness, scope)`` identifier into the
    canonical operational instruction block defined by the coverage-gathering
    contract (``persona-plan-marshall-agent/standards/coverage-gathering-contract.md``
    § "The Expansion Table"), emitted by :class:`CoveragePresets`. This is the
    static identifier->instruction expander that implementing components consume
    instead of re-interpreting the raw cell — mirroring how ``compatibility``
    expands to ``compatibility_description``.

    Validation reuses the shared ``_validate_thoroughness`` /
    ``_validate_scope`` / ``_validate_coupling`` checks (via
    :meth:`CoveragePresets.expand`); an incoherent cell
    (``thoroughness >= T4 AND scope < component``) returns
    ``error_type: coverage_coupling_violation``.
    """
    from coverage_presets import CoveragePresets

    thoroughness = getattr(args, 'thoroughness', None)
    scope = getattr(args, 'scope', None)

    ok, err = _validate_thoroughness(thoroughness, 'coverage expand --thoroughness')
    if not ok:
        return error_exit(err or 'invalid thoroughness')
    ok, err = _validate_scope(scope, 'coverage expand --scope')
    if not ok:
        return error_exit(err or 'invalid scope')
    ok, err = _validate_coupling(thoroughness, scope)
    if not ok:
        return error_exit(
            err or 'coverage coupling violation',
            error_type='coverage_coupling_violation',
        )

    assert isinstance(thoroughness, str) and isinstance(scope, str)
    return success_exit(
        {
            'thoroughness': thoroughness,
            'scope': scope,
            'instruction': CoveragePresets.expand(thoroughness, scope),
            'summary': CoveragePresets.describe(thoroughness, scope),
        }
    )
