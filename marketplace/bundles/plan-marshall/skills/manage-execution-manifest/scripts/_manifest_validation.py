#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Step-params and loadability/validation helpers for the execution manifest.

Extracted verbatim from ``manage-execution-manifest.py``: the plan-local
step-params get/set handlers, the phase-6 standards-path / frontmatter-order
resolvers, the ascending-order and loadability checks, and the schema-level
:func:`cmd_validate`. None of these functions log or call a test-patched name
(the seed-order path that reads marshal.json — ``cmd_validate_loadable`` — stays
in the entry). The entry re-exports every name the test suite references.
"""

import argparse
from pathlib import Path
from typing import Any

from _manifest_core import (
    _CANONICAL_TO_ROLE,
    _CANONICAL_VERIFY_PREFIX,
    MANIFEST_VERSION,
    PROMOTED_BUILTIN_STEP_IDS,
    VALID_RECORD_PHASES,
    _strip_default_prefix,
    read_manifest,
    write_manifest,
)
from _manifest_decide import _split_csv
from file_ops import output_toon_error
from input_validation import require_valid_plan_id
from marketplace_bundles import resolve_bundles_root, resolve_skills_root
from marketplace_paths import resolve_project_skill_path

# =============================================================================
# Plan-local step-params get/set (manifest snapshot reads + per-plan overrides)
# =============================================================================

# Maps the ``--phase`` record vocabulary (``5-execute`` / ``6-finalize``) to the
# manifest body section key. step-params reuses VALID_RECORD_PHASES so the phase
# argument is identical to record-step's.
_PHASE_TO_BODY_SECTION = {'5-execute': 'phase_5', '6-finalize': 'phase_6'}


def _coerce_param_value(raw: str) -> Any:
    """Coerce a CLI string ``--value`` to bool / int / str for a step param.

    Mirrors the lightweight coercion manage-config's ``step set`` applies so a
    per-plan manifest override stores the same typed value the global keyed map
    would. ``true``/``false`` (case-insensitive) → bool; an integer literal →
    int; everything else stays a string.
    """
    lowered = raw.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


def cmd_step_params_get(args: argparse.Namespace) -> dict[str, Any] | None:
    """Return a step's snapshotted param object from the manifest (plan-local read).

    Reads ``body[phase_section].step_params[step_id]`` from the persisted
    manifest — a literal file read of the compose-time snapshot, never a
    marshal.json read. An absent step id (or a manifest with no ``step_params``
    section) is an explicit error.

    The lookup is PREFIX-AGNOSTIC: the snapshot is keyed by the bare step id
    (``_snapshot_step_params`` strips the ``default:`` prefix at compose time),
    so the caller's ``--step-id`` is stripped here too before the dict lookup.
    Both ``default:branch-cleanup`` and ``branch-cleanup`` therefore resolve to
    the same bare-keyed entry, mirroring ``cmd_validate``'s membership test.
    """
    plan_id = require_valid_plan_id(args)

    if args.phase not in VALID_RECORD_PHASES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.phase!r}. Must be one of {list(VALID_RECORD_PHASES)}',
        }

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    bare_step_id = _strip_default_prefix(args.step_id)
    section = manifest.get(_PHASE_TO_BODY_SECTION[args.phase], {})
    step_params = section.get('step_params', {}) if isinstance(section, dict) else {}
    if not isinstance(step_params, dict) or bare_step_id not in step_params:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'step_not_found',
            'message': f"Step '{args.step_id}' has no snapshotted params in phase {args.phase}",
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': args.phase,
        'step_id': args.step_id,
        'params': step_params[bare_step_id],
    }


def cmd_step_params_set(args: argparse.Namespace) -> dict[str, Any] | None:
    """Write a per-plan param override into the manifest's step_params snapshot.

    Writes ``body[phase_section].step_params[step_id][param] = value`` into the
    persisted manifest (value-coerced) — a plan-local override that wins over the
    marshal.json compose-time default for subsequent ``step-params get`` reads.
    Operates on the manifest only, never on marshal.json. An absent step id is an
    explicit error (the override targets a snapshotted step, not a new one).

    The lookup/write is PREFIX-AGNOSTIC: the snapshot is keyed by the bare step
    id (``_snapshot_step_params`` strips the ``default:`` prefix at compose
    time), so the caller's ``--step-id`` is stripped here too before the dict
    lookup/write. Both ``default:branch-cleanup`` and ``branch-cleanup``
    therefore resolve to the same bare-keyed entry, mirroring ``cmd_validate``.
    """
    plan_id = require_valid_plan_id(args)

    if args.phase not in VALID_RECORD_PHASES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.phase!r}. Must be one of {list(VALID_RECORD_PHASES)}',
        }

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    bare_step_id = _strip_default_prefix(args.step_id)
    section = manifest.get(_PHASE_TO_BODY_SECTION[args.phase])
    if not isinstance(section, dict):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': f'Manifest section {_PHASE_TO_BODY_SECTION[args.phase]!r} is missing or malformed',
        }
    step_params = section.get('step_params')
    if not isinstance(step_params, dict) or bare_step_id not in step_params:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'step_not_found',
            'message': f"Step '{args.step_id}' has no snapshotted params in phase {args.phase}",
        }

    params = dict(step_params[bare_step_id])
    params[args.param] = _coerce_param_value(args.value)
    step_params[bare_step_id] = params
    section['step_params'] = step_params
    write_manifest(plan_id, manifest)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': args.phase,
        'step_id': args.step_id,
        'params': params,
    }


# Paths to the phase-6-finalize standards + workflow directories, resolved
# relative to this script's location in the marketplace source tree. Built-in
# step docs may live under either directory: orchestrator-style steps that the
# dispatcher reads inline live under ``standards/``; ext-point implementor
# workflows (LLM-judgement workflows dispatched as a unit via
# ``execution-context``) live under ``workflow/``. The loadability check
# searches both, ``workflow/`` first.
_PHASE_6_SKILL_DIR = resolve_skills_root(Path(__file__)) / 'phase-6-finalize'
_PHASE_6_WORKFLOW_DIR = _PHASE_6_SKILL_DIR / 'workflow'
_PHASE_6_STANDARDS_DIR = _PHASE_6_SKILL_DIR / 'standards'

# The promoted built-in-equivalent ``automatic-review`` step was moved out of
# ``phase-6-finalize/workflow/automatic-review.md`` into its own top-level bundle
# skill. In the composed manifest it is the boundary-normalized bare
# ``automatic-review`` id, so the loadability / order resolvers below must point
# at the bundle SKILL.md rather than the deleted phase-6 body doc.
_AUTOMATIC_REVIEW_SKILL_MD = resolve_skills_root(Path(__file__)) / 'automatic-review' / 'SKILL.md'

# Repository-root anchor used to render the standards path as a project-relative
# string in the script output. ``resolve_bundles_root`` identity-walks to the
# ``marketplace/bundles`` root (no index arithmetic); its grandparent is the
# repo root, so rendered paths start with `marketplace/bundles/…` and match the
# documented contract.
_REPO_ROOT = resolve_bundles_root(Path(__file__)).parent.parent


def _is_external_step(step_id: str) -> bool:
    """Return True when ``step_id`` is a project/skill (external) step.

    External steps carry a colon (``project:foo`` or ``bundle:skill``).
    Bare names and ``default:``-prefixed names are built-in.
    """
    if step_id.startswith('default:'):
        return False
    return ':' in step_id


def _resolve_standards_path(step_id: str) -> Path:
    """Resolve the doc file path for a built-in ``step_id``.

    Strips the optional ``default:`` prefix. Searches ``workflow/`` first,
    then falls back to ``standards/``. Returns the first matching path; if
    neither exists, returns the ``workflow/`` path (so the caller's missing-
    file error message reports the preferred location).
    """
    bare = _strip_default_prefix(step_id)
    # The promoted ``automatic-review`` step lives in its bundle SKILL.md, not a
    # phase-6 body doc (which was deleted at promotion).
    if bare == 'automatic-review':
        return _AUTOMATIC_REVIEW_SKILL_MD
    workflow_path = _PHASE_6_WORKFLOW_DIR / f'{bare}.md'
    if workflow_path.is_file():
        return workflow_path
    standards_path = _PHASE_6_STANDARDS_DIR / f'{bare}.md'
    if standards_path.is_file():
        return standards_path
    return workflow_path


def _render_standards_rel_path(absolute: Path) -> str:
    """Render ``absolute`` as a repo-root-relative POSIX string.

    Falls back to the absolute string when ``absolute`` is outside the repo.
    """
    try:
        return absolute.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(absolute)


def _read_frontmatter_order(path: Path) -> int | None:
    """Read the integer ``order:`` frontmatter key from a markdown file.

    A minimal frontmatter parser — scans the first ``---``-fenced block for an
    ``order:`` key and returns its value coerced to ``int``. Returns ``None``
    when the file is missing, has no
    frontmatter block, lacks an ``order:`` key, or the value is not an
    integer. PyYAML is intentionally avoided to keep the dependency surface
    narrow; the frontmatter shape is constrained by plugin-doctor and the
    test suite.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return None
    if not text.startswith('---'):
        return None
    for line in text.splitlines()[1:]:
        if line.strip() == '---':
            break
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        if key.strip() != 'order':
            continue
        candidate = value.strip().strip('"').strip("'")
        try:
            return int(candidate)
        except ValueError:
            return None
    return None


def _resolve_step_order(step_id: str) -> int | None:
    """Resolve a step's frontmatter ``order`` integer from its source file.

    Resolution is broader than loadability: it covers ``project:`` steps too,
    because real ordering inversions can occur among project-local steps.

    - Built-in steps (bare or ``default:``-prefixed): resolve the standards /
      workflow doc via ``_resolve_standards_path`` and read its ``order:``
      frontmatter.
    - ``project:``-prefixed steps: resolve the project-local-skill
      ``{bare-name}/SKILL.md`` via the target's layout roots (relative to the
      repo root) and read its ``order:`` frontmatter.
    - Other external steps (``bundle:skill``): no resolvable project-local
      source file — return ``None``.

    Returns ``None`` when no source file exists or no ``order:`` key is
    present. Steps that resolve to ``None`` are skipped by the ascending-order
    check (they neither break nor satisfy ascending order).
    """
    if step_id.startswith('project:'):
        bare = step_id[len('project:') :]
        skill_path = resolve_project_skill_path(f'{bare}/SKILL.md', base=_REPO_ROOT)
        return _read_frontmatter_order(skill_path)
    if _is_external_step(step_id):
        # bundle:skill external steps have no project-local source file.
        return None
    return _read_frontmatter_order(_resolve_standards_path(step_id))


def _sort_steps_by_frontmatter_order(steps: list[Any]) -> list[Any]:
    """Reorder ``steps`` into ascending frontmatter ``order`` at compose time.

    Every entry whose ``_resolve_step_order`` is not ``None`` is sorted into
    ascending resolved-order position; Python's stable sort preserves the
    relative order of entries sharing an equal ``order`` value (they were
    gathered in list-position order). Entries whose order resolves to ``None``
    — non-string entries and external ``bundle:skill`` steps with no resolvable
    source file — keep their exact original index, acting as fixed pins that the
    sortable entries flow around.

    This is the compose-time companion to :func:`_check_ascending_order`: the
    composer sorts so the barrier invariant holds, the validator asserts the
    sort held. Returns a new list; the input is not mutated.
    """
    sortable: list[tuple[int, Any]] = []
    pinned_positions: set[int] = set()
    for index, entry in enumerate(steps):
        order = _resolve_step_order(entry) if isinstance(entry, str) else None
        if order is None:
            pinned_positions.add(index)
        else:
            sortable.append((order, entry))
    # Stable sort by resolved order alone — equal orders keep their original
    # relative sequence because ``sortable`` was built in list-position order.
    sortable.sort(key=lambda pair: pair[0])
    sortable_iter = iter(sortable)
    result: list[Any] = []
    for index, entry in enumerate(steps):
        if index in pinned_positions:
            result.append(entry)
        else:
            result.append(next(sortable_iter)[1])
    return result


def _check_ascending_order(steps: list[Any]) -> str | None:
    """Assert ``steps`` resolve to non-decreasing frontmatter ``order`` values.

    Walks the step list in position order, resolving each step's ``order``
    via ``_resolve_step_order``. Steps whose ``order`` resolves to ``None``
    are skipped (they do not participate in the ascending assertion). An
    inversion is a step whose resolved ``order`` is strictly less than the
    maximum resolved ``order`` seen so far at an earlier list position.

    Returns an actionable diagnostic naming the inverted pair on the first
    inversion, or ``None`` when the resolvable subsequence is non-decreasing.
    The message phrasing matches the request: it names the later-positioned
    step (with the smaller order) and the earlier-positioned step (with the
    larger order) that it appears before.
    """
    max_order: int | None = None
    max_step: str | None = None
    for entry in steps:
        if not isinstance(entry, str):
            continue
        order = _resolve_step_order(entry)
        if order is None:
            continue
        if max_order is not None and order < max_order:
            return (
                f'step `{entry}` (order={order}) appears after '
                f'step `{max_step}` (order={max_order}) — phase_6.steps must be '
                f'in ascending frontmatter `order`'
            )
        if max_order is None or order > max_order:
            max_order = order
            max_step = entry
    return None


def _check_step_loadable(step_id: str) -> dict[str, Any]:
    """Single-step loadability check.

    Returns a dict with ``step_id``, ``standards_path``, ``loadable`` and an
    optional ``message`` (canonical actionable phrasing on failure).
    External steps are short-circuited to ``loadable: true`` with an empty
    standards_path because their loadability is owned by the host plugin
    cache, not the marketplace standards tree.
    """
    if _is_external_step(step_id):
        return {
            'step_id': step_id,
            'standards_path': '',
            'loadable': True,
        }
    bare = _strip_default_prefix(step_id)
    absolute_path = _resolve_standards_path(step_id)
    rel_path = _render_standards_rel_path(absolute_path)
    if absolute_path.is_file():
        return {
            'step_id': bare,
            'standards_path': rel_path,
            'loadable': True,
        }
    message = (
        f'step `{bare}` referenced by `marshal.json` is missing standards file '
        f'`{rel_path}` — the plan likely deleted the file without sweeping `marshal.json`'
    )
    return {
        'step_id': bare,
        'standards_path': rel_path,
        'loadable': False,
        'message': message,
    }


# =============================================================================
# Compose-time step-resolution gate
# =============================================================================
#
# ``_check_step_loadable`` short-circuits every external (``project:`` /
# ``bundle:skill``) step to ``loadable: true`` — it only asserts built-in
# standards-file presence. That leaves a hole: a phase-5/6 step id that names a
# never-existed ``bundle:skill`` (or a renamed ``project:`` skill) composes
# silently and only fails much later at dispatch time. ``_check_step_resolvable``
# closes that hole by RESOLVING external steps against the same discovery
# registries the finalize/verify seed and discovery surfaces use, so the composer
# can fail loud at compose time. It is the gate ``cmd_compose`` runs over the
# FINAL emitted phase lists.


def _phase_step_ext_point(phase: str) -> str:
    """Map a manifest phase key to its step ext-point value.

    ``phase_6`` → the finalize-step ext-point; anything else (``phase_5``) → the
    build-verify-step ext-point. Lazy-imported from ``_config_defaults`` to keep
    the module-import surface narrow and avoid an import cycle.
    """
    from _config_defaults import BUILD_VERIFY_STEP_EXT_POINT, FINALIZE_STEP_EXT_POINT

    return FINALIZE_STEP_EXT_POINT if phase == 'phase_6' else BUILD_VERIFY_STEP_EXT_POINT


def _discovered_implementor_names(phase: str) -> set[str]:
    """Return the discovered implementor step-id set for ``phase``'s step ext-point.

    Enumerates every implementor of the phase's step ext-point via the reusable
    ``extension_discovery.find_implementors`` query — the SOLE discovery path the
    finalize/verify seed and discovery surfaces already use — and returns each
    record's ``name`` in BOTH its declared and boundary-normalized
    (``_strip_default_prefix``) forms, so a promoted ``{bundle}:{skill}`` id and
    its bare alias both match. The :data:`PROMOTED_BUILTIN_STEP_IDS` map is folded
    in defensively (both key and value forms) so a promoted-step id resolves
    regardless of which form the emitted list carries.
    """
    from extension_discovery import find_implementors

    names: set[str] = set()
    for rec in find_implementors(_phase_step_ext_point(phase)):
        name = rec.get('name', '')
        if not name:
            continue
        names.add(name)
        names.add(_strip_default_prefix(name))
    for full, bare in PROMOTED_BUILTIN_STEP_IDS.items():
        names.add(full)
        names.add(bare)
    return names


def _verify_canonicals_universe() -> set[str]:
    """Return the canonical command names a ``verify:{canonical}`` step may name.

    The union of the composer's authoritative ``_CANONICAL_TO_ROLE`` keys (the
    canonical→role table the composer already recognizes — ``quality-gate`` /
    ``verify`` / ``module-tests`` / ``coverage`` / ``integration-tests`` /
    ``e2e``) and every ``ext-point-build-verify-step`` implementor's declared
    ``canonicals`` list (the built-in ``canonical_verify.md`` declares
    ``quality-gate`` / ``module-tests`` / ``coverage``). A ``verify:{canonical}``
    step resolves iff its trailing canonical segment is in this union. Seeding the
    universe from ``_CANONICAL_TO_ROLE`` keeps the gate robust even when discovery
    returns nothing (an exotic test/consumer layout without the phase-5 standards
    docs).
    """
    from _config_defaults import BUILD_VERIFY_STEP_EXT_POINT
    from extension_discovery import find_implementors

    universe: set[str] = set(_CANONICAL_TO_ROLE.keys())
    for rec in find_implementors(BUILD_VERIFY_STEP_EXT_POINT):
        for canonical in rec.get('canonicals', []):
            if isinstance(canonical, str) and canonical:
                universe.add(canonical)
    return universe


def _check_step_resolvable(step_id: str, phase: str) -> dict[str, Any]:
    """Single-step resolvability check for a composed phase-5/6 step id.

    Extends :func:`_check_step_loadable` by RESOLVING external steps rather than
    short-circuiting them to ``loadable: true``. Resolution is keyed on the step
    id shape and the ``phase`` (``phase_5`` / ``phase_6``):

    - **project:** step (either phase): resolves iff its project-local
      ``{bare}/SKILL.md`` exists under the repo root.
    - **phase_5 canonical-verify** step (bare ``{canonical}`` or
      ``verify:{canonical}``): resolves iff ``{canonical}`` is in the verify
      canonicals universe (:func:`_verify_canonicals_universe`).
    - **phase_5 external bundle:skill** verify step: resolves iff its (normalized)
      id is a discovered ``ext-point-build-verify-step`` implementor name.
    - **phase_6 external bundle:skill** step: resolves iff its (normalized) id is a
      discovered ``ext-point-finalize-step`` implementor name.
    - **phase_6 built-in** step (bare / ``default:``): keeps the existing
      standards/workflow file check (:func:`_check_step_loadable`).

    Returns a dict with ``step_id``, ``resolvable`` and — on failure — an
    actionable ``message``.
    """
    bare = _strip_default_prefix(step_id)

    # project: external step (either phase) — resolves via its project-local
    # SKILL.md. Checked first so a project verify step never falls into the
    # canonical-verify branch.
    if step_id.startswith('project:'):
        project_bare = step_id[len('project:') :]
        skill_path = resolve_project_skill_path(f'{project_bare}/SKILL.md', base=_REPO_ROOT)
        if skill_path.is_file():
            return {'step_id': step_id, 'resolvable': True}
        message = (
            f'step `{step_id}` referenced by `marshal.json` resolves to no project-local '
            f'skill `{project_bare}/SKILL.md` — the plan likely renamed or removed the '
            f'skill without sweeping `marshal.json`'
        )
        return {'step_id': step_id, 'resolvable': False, 'message': message}

    if phase == 'phase_5':
        # An external bundle:skill verify step (a colon-bearing id that is NOT the
        # canonical-verify ``verify:{canonical}`` shape) resolves via the
        # build-verify-step discovery registry.
        if _is_external_step(step_id) and not bare.startswith(_CANONICAL_VERIFY_PREFIX):
            names = _discovered_implementor_names('phase_5')
            if step_id in names or bare in names:
                return {'step_id': step_id, 'resolvable': True}
            message = (
                f'step `{step_id}` referenced by `marshal.json` is not a discovered '
                f'ext-point-build-verify-step implementor — the id resolves to no '
                f'built-in verify step, project-local skill, or bundle discovery-registry entry'
            )
            return {'step_id': step_id, 'resolvable': False, 'message': message}
        # Canonical-verify built-in step: accept both the bare ``{canonical}`` and
        # the ``verify:{canonical}`` forms.
        canonical = bare[len(_CANONICAL_VERIFY_PREFIX) :] if bare.startswith(_CANONICAL_VERIFY_PREFIX) else bare
        if canonical in _verify_canonicals_universe():
            return {'step_id': bare, 'resolvable': True}
        message = (
            f'step `{step_id}` names an unknown canonical `{canonical}` — no '
            f'ext-point-build-verify-step implementor (nor the composer canonical→role '
            f'table) declares it'
        )
        return {'step_id': bare, 'resolvable': False, 'message': message}

    # phase_6 external bundle:skill step — resolves via the finalize-step registry.
    if _is_external_step(step_id):
        names = _discovered_implementor_names('phase_6')
        if step_id in names or bare in names:
            return {'step_id': step_id, 'resolvable': True}
        message = (
            f'step `{step_id}` referenced by `marshal.json` is not a discovered '
            f'ext-point-finalize-step implementor — the id resolves to no built-in '
            f'finalize step, project-local skill, or bundle discovery-registry entry'
        )
        return {'step_id': step_id, 'resolvable': False, 'message': message}

    # phase_6 built-in (bare / default:) — keep the existing standards/workflow
    # file check.
    loadable = _check_step_loadable(step_id)
    if loadable.get('loadable'):
        return {'step_id': bare, 'resolvable': True}
    return {
        'step_id': bare,
        'resolvable': False,
        'message': loadable.get('message', f'step `{bare}` is not resolvable'),
    }


def _build_step_marshal_key_map(marshal_map: dict[str, Any] | None) -> dict[str, str]:
    """Map each boundary-normalized step id to its ORIGINAL marshal.json key.

    ``marshal_map`` is the keyed step map read from marshal.json — its keys carry
    the author's original prefixes (``default:foo`` / ``project:foo`` /
    ``bundle:skill``). The composed manifest carries boundary-normalized ids, so a
    resolution failure on a normalized id is reported by the marshal.json key the
    author actually wrote. Returns ``{}`` when the map is absent (the CSV-fallback
    compose path), which the caller degrades to reporting the emitted id itself.
    """
    if not isinstance(marshal_map, dict):
        return {}
    result: dict[str, str] = {}
    for key in marshal_map:
        result.setdefault(_strip_default_prefix(key), key)
        result.setdefault(key, key)
    return result


def check_emitted_steps_resolvable(
    phase_5_steps: list[Any],
    phase_6_steps: list[Any],
    marshal_phase_5_map: dict[str, Any] | None,
    marshal_phase_6_map: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Resolve every FINAL emitted phase-5/6 step id; return the first failure or None.

    Iterates the FINAL emitted ``phase_5.verification_steps`` then
    ``phase_6.steps``, resolving each via :func:`_check_step_resolvable`. Returns
    ``None`` when every step resolves. On the first unresolvable step returns a
    dict carrying ``phase`` (``phase_5`` / ``phase_6``), the emitted ``step_id``,
    the original ``marshal_key`` (the marshal.json key the author wrote, falling
    back to the emitted id on the CSV-fallback path), and an actionable
    ``message`` naming both the offending marshal.json key and the phase.
    """
    for phase, steps, marshal_map in (
        ('phase_5', phase_5_steps, marshal_phase_5_map),
        ('phase_6', phase_6_steps, marshal_phase_6_map),
    ):
        key_map = _build_step_marshal_key_map(marshal_map)
        for step in steps:
            if not isinstance(step, str):
                continue
            verdict = _check_step_resolvable(step, phase)
            if not verdict.get('resolvable'):
                marshal_key = key_map.get(step, step)
                return {
                    'phase': phase,
                    'step_id': step,
                    'marshal_key': marshal_key,
                    'message': (
                        f'{phase} step `{marshal_key}` in marshal.json is unresolvable: '
                        f'{verdict.get("message", "no resolvable source")}'
                    ),
                }
    return None


def cmd_validate(args: argparse.Namespace) -> dict[str, Any] | None:
    """Validate manifest schema and (optionally) step IDs against candidate sets."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    errors: list[str] = []

    # Schema checks.
    if manifest.get('manifest_version') != MANIFEST_VERSION:
        errors.append(
            f'manifest_version mismatch: expected {MANIFEST_VERSION}, got {manifest.get("manifest_version")!r}'
        )
    if manifest.get('plan_id') != plan_id:
        errors.append(f'plan_id mismatch: expected {plan_id!r}, got {manifest.get("plan_id")!r}')

    phase_5 = manifest.get('phase_5')
    phase_6 = manifest.get('phase_6')
    if not isinstance(phase_5, dict):
        errors.append('phase_5 section missing or not a mapping')
        phase_5 = {}
    if not isinstance(phase_6, dict):
        errors.append('phase_6 section missing or not a mapping')
        phase_6 = {}

    if 'early_terminate' not in phase_5 or not isinstance(phase_5.get('early_terminate'), bool):
        errors.append('phase_5.early_terminate missing or not a bool')
    p5_steps = phase_5.get('verification_steps', [])
    if not isinstance(p5_steps, list):
        errors.append('phase_5.verification_steps must be a list')
        p5_steps = []
    p6_steps = phase_6.get('steps', [])
    if not isinstance(p6_steps, list):
        errors.append('phase_6.steps must be a list')
        p6_steps = []

    # Step-ID checks (only when caller passes candidate sets).
    #
    # The comparison is PREFIX-AGNOSTIC: the composer normalizes manifest step
    # IDs to bare names at the compose boundary (``_strip_default_prefix``),
    # while the caller's ``--phase-{5,6}-steps`` CSV may still carry the
    # optional ``default:`` prefix (e.g. ``default:verify:module-tests``). Stripping
    # the prefix from BOTH the allowed set and the manifest step IDs before the
    # set-membership test lets a bare manifest ID validate against a
    # ``default:``-prefixed allowed-list (and vice versa). ``project:`` /
    # ``bundle:skill`` prefixes are preserved verbatim by
    # ``_strip_default_prefix`` so external steps still compare exactly.
    p5_unknown: list[str] = []
    p6_unknown: list[str] = []
    if args.phase_5_steps is not None:
        allowed_5 = {_strip_default_prefix(s) for s in _split_csv(args.phase_5_steps, ())}
        p5_unknown = [s for s in p5_steps if _strip_default_prefix(s) not in allowed_5]
        if p5_unknown:
            errors.append(f'phase_5.verification_steps contains unknown IDs: {p5_unknown}')
    if args.phase_6_steps is not None:
        allowed_6 = {_strip_default_prefix(s) for s in _split_csv(args.phase_6_steps, ())}
        p6_unknown = [s for s in p6_steps if _strip_default_prefix(s) not in allowed_6]
        if p6_unknown:
            errors.append(f'phase_6.steps contains unknown IDs: {p6_unknown}')

    if errors:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': '; '.join(errors),
            'phase_5_unknown_steps_count': len(p5_unknown),
            'phase_5_unknown_steps': p5_unknown,
            'phase_6_unknown_steps_count': len(p6_unknown),
            'phase_6_unknown_steps': p6_unknown,
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'valid': True,
        'phase_5_unknown_steps_count': 0,
        'phase_6_unknown_steps_count': 0,
    }
