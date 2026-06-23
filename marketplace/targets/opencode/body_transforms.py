# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCode body transforms — line-level rewrites applied to emitted bodies.

This module implements the two transforms documented in ``transforms.md``:

* **Transform 1: ``Skill:`` directive rewrite** — Claude Code intercepts
  ``Skill: {bundle}:{skill}`` lines at runtime; OpenCode does not.
  The transform rewrites a full-line ``Skill:`` directive into a call to
  the ``skill`` tool. The regex is anchored to a full line so inline
  backtick references like `` `Skill: foo:bar` `` in prose are
  unaffected.

* **Transform 2: Slash-command rewrite** — Claude Code skills with
  ``user-invocable: true`` are invoked as ``/skill-name``. The OpenCode
  dual-emit places them under ``command/{bundle}-{skill}.md`` invoked as
  ``/{bundle}-{skill}``. Cross-references in skill bodies and usage
  examples must be rewritten to the namespaced form. The lookup table
  is built by ``build_user_invocable_lookup`` from a marketplace scan of
  ``user-invocable: true`` skills.

* **Transform 3: Registered-idiom rewrite (data-driven)** — Claude-native
  tool idioms (``AskUserQuestion``, ``Task:``, ``Skill: <entry>``) are
  registered as per-target rewrite *data* in
  ``mapping.json::body_idiom_rewrites``. The shared engine
  (:func:`rewrite_registered_idioms`) reads the registry and applies each
  idiom's *disposition*:

    - ``rewrite_inline_code`` — rewrite backtick-wrapped tool references
      (e.g. `` `AskUserQuestion` `` → `` `question` ``) to the OpenCode tool
      name. Bare prose mentions of the concept are left alone.
    - ``preserve`` — a deliberate, leaf-aware non-rewrite (e.g. ``Task:`` —
      the dispatcher's leaf-constraint prose must NOT be blanket-rewritten).
    - ``source_fix`` — the divergence is fixed in the source, not at emit time
      (e.g. ``Skill: <entry>`` placeholder prose).

  The engine **fails closed**: any registered idiom carrying an *unknown*
  disposition raises :class:`UnmappedIdiomError` at build time, so a new
  Claude idiom cannot be silently emitted un-dispositioned.

Both transforms are idempotent — running them on already-transformed
text is a no-op.

The factory ``make_body_transformer(lookup)`` returns a callable
matching the ``BodyTransformer`` signature consumed by
``emitter.emit_bundles``::

    transformer = make_body_transformer(build_user_invocable_lookup(marketplace_dir))
    emit_bundles(marketplace_dir, output_dir, config_dir, body_transformer=transformer)
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from marketplace.targets.opencode.frontmatter import parse_frontmatter

# Path to the OpenCode target mapping data (relative to this module).
_MAPPING_JSON = Path(__file__).resolve().parent / 'mapping.json'

# The set of dispositions the engine knows how to honour. A registered idiom
# carrying any other disposition is a build-time error (fail-closed).
_KNOWN_DISPOSITIONS = frozenset({'rewrite_inline_code', 'preserve', 'source_fix'})


class UnmappedIdiomError(ValueError):
    """A registered Claude idiom carries an unknown disposition (fail-closed build)."""

# Match a full-line ``Skill: bundle:skill`` directive. The leading and
# trailing anchors are ``MULTILINE`` so the regex applies per-line in a
# multi-line body. The bundle/skill names are kebab-case identifiers.
_NAME_RE = r'[A-Za-z0-9][A-Za-z0-9_-]*'
SKILL_DIRECTIVE_RE = re.compile(
    rf'^Skill:\s+(?P<bundle>{_NAME_RE}):(?P<skill>{_NAME_RE})\s*$',
    re.MULTILINE,
)

# Already-rewritten line. Used for idempotence detection so the transform
# is a no-op when run a second time.
SKILL_REWRITTEN_RE = re.compile(
    r'^Call the `skill` tool with `\{ name: "[^"]+" \}` before continuing\.$',
    re.MULTILINE,
)


BodyTransformer = Callable[[str, str, str], str]


def rewrite_skill_directives(body: str) -> str:
    """Apply Transform 1: full-line ``Skill:`` directive rewrite.

    Idempotent: lines already matching the OpenCode form are left alone.
    """

    def replace(match: re.Match[str]) -> str:
        bundle = match.group('bundle')
        skill = match.group('skill')
        return f'Call the `skill` tool with `{{ name: "{bundle}-{skill}" }}` before continuing.'

    return SKILL_DIRECTIVE_RE.sub(replace, body)


def build_slash_command_re(known_names: list[str]) -> re.Pattern[str] | None:
    """Build the slash-command regex for the supplied skill names.

    Returns ``None`` when ``known_names`` is empty (the resulting regex
    would match nothing useful and would still raise on compile).
    """
    if not known_names:
        return None
    # Sort by length descending so longer names match before shorter
    # prefixes (avoids partial matches when one skill name is a prefix
    # of another).
    alternatives = sorted({n for n in known_names if n}, key=lambda n: (-len(n), n))
    pattern = (
        r'(?<![\w-])/(?P<name>'
        + '|'.join(re.escape(n) for n in alternatives)
        + r')(?=\s|$|=)'
    )
    return re.compile(pattern, re.MULTILINE)


def rewrite_slash_commands(body: str, lookup: dict[str, str]) -> str:
    """Apply Transform 2: rewrite ``/skill-name`` to ``/{bundle}-{skill}``.

    ``lookup`` maps bare skill names to their namespaced form
    (``{bundle}-{skill}``). Names already in namespaced form pass
    through unchanged because the regex only matches the bare names
    listed in ``lookup``.
    """
    pattern = build_slash_command_re(list(lookup))
    if pattern is None:
        return body

    def replace(match: re.Match[str]) -> str:
        name = match.group('name')
        target = lookup.get(name)
        if target is None or target == name:
            return match.group(0)
        return f'/{target}'

    return pattern.sub(replace, body)


def load_idiom_registry(mapping_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the ``body_idiom_rewrites`` registry from ``mapping.json``.

    Returns the registry dict mapping each registered idiom name to its
    disposition record. Returns an empty dict when the key is absent. The load
    validates every registered disposition up-front (fail-closed) — see
    :func:`assert_dispositions_known`.
    """
    path = mapping_path or _MAPPING_JSON
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    registry = data.get('body_idiom_rewrites', {})
    if not isinstance(registry, dict):
        return {}
    assert_dispositions_known(registry)
    return registry


def assert_dispositions_known(registry: dict[str, dict[str, Any]]) -> None:
    """Fail closed: every registered idiom must carry a known disposition.

    Raises :class:`UnmappedIdiomError` when any registered idiom's
    ``disposition`` is missing or not one of :data:`_KNOWN_DISPOSITIONS`. This is
    the structural guard that a NEW Claude idiom cannot be added to the registry
    (or emitted) without an explicit, engine-handled disposition.
    """
    for idiom, record in registry.items():
        disposition = record.get('disposition') if isinstance(record, dict) else None
        if disposition not in _KNOWN_DISPOSITIONS:
            raise UnmappedIdiomError(
                f'Registered idiom {idiom!r} has unknown disposition {disposition!r}; '
                f'known dispositions: {sorted(_KNOWN_DISPOSITIONS)}'
            )


def rewrite_registered_idioms(body: str, registry: dict[str, dict[str, Any]]) -> str:
    """Apply Transform 3: data-driven registered-idiom rewrites.

    Iterates the registry (fail-closed-validated by :func:`load_idiom_registry`)
    and applies each idiom's disposition:

    - ``rewrite_inline_code`` — rewrite backtick-wrapped `` `{idiom}` `` to the
      OpenCode tool name (`` `{opencode_tool}` ``). Bare prose mentions are left.
    - ``preserve`` / ``source_fix`` — no body change (deliberate non-rewrite /
      source-side fix).

    Idempotent: a ``rewrite_inline_code`` whose replacement is already present
    does not re-match (the source idiom name no longer appears in that backtick
    span).
    """
    for idiom, record in registry.items():
        disposition = record.get('disposition')
        if disposition != 'rewrite_inline_code':
            continue
        opencode_tool = record.get('opencode_tool')
        if not opencode_tool:
            continue
        # Rewrite only the backtick-wrapped tool reference, never bare prose.
        body = body.replace(f'`{idiom}`', f'`{opencode_tool}`')
    return body


def make_body_transformer(
    lookup: dict[str, str],
    idiom_registry: dict[str, dict[str, Any]] | None = None,
) -> BodyTransformer:
    """Compose Transform 1 + Transform 2 + Transform 3 into a ``BodyTransformer``.

    The returned callable matches the ``emitter.BodyTransformer``
    signature: ``(body, bundle, kind) -> rewritten body``. The bundle
    and kind arguments are reserved for future per-context behavior; the
    current transforms apply uniformly to skill, agent, and command
    bodies.

    ``idiom_registry`` defaults to the ``mapping.json`` registry loaded via
    :func:`load_idiom_registry` (which fails closed on an unknown disposition).
    """
    registry = idiom_registry if idiom_registry is not None else load_idiom_registry()

    def transform(body: str, _bundle: str, _kind: str) -> str:
        body = rewrite_skill_directives(body)
        body = rewrite_slash_commands(body, lookup)
        body = rewrite_registered_idioms(body, registry)
        return body

    return transform


def _read_skill_frontmatter(skill_md: Path) -> dict[str, str]:
    if not skill_md.is_file():
        return {}
    try:
        content = skill_md.read_text(encoding='utf-8')
    except OSError:
        return {}
    fm, _ = parse_frontmatter(content)
    return fm


def _is_user_invocable(fm: dict[str, str]) -> bool:
    raw = fm.get('user-invocable', '').strip().lower()
    return raw in {'true', 'yes', '1'}


def build_user_invocable_lookup(marketplace_dir: Path) -> dict[str, str]:
    """Scan ``marketplace_dir`` for ``user-invocable: true`` skills.

    Returns a dict mapping the bare skill name to the namespaced
    ``{bundle}-{skill}`` id. The scan is non-destructive — it only reads
    SKILL.md frontmatter for skills under ``{bundle}/skills/{skill}/``.
    """
    lookup: dict[str, str] = {}
    if not marketplace_dir.is_dir():
        return lookup

    for bundle_dir in sorted(marketplace_dir.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            fm = _read_skill_frontmatter(skill_dir / 'SKILL.md')
            if _is_user_invocable(fm):
                lookup[skill_dir.name] = f'{bundle_dir.name}-{skill_dir.name}'
    return lookup


__all__ = [
    'BodyTransformer',
    'SKILL_DIRECTIVE_RE',
    'SKILL_REWRITTEN_RE',
    'UnmappedIdiomError',
    'assert_dispositions_known',
    'build_slash_command_re',
    'build_user_invocable_lookup',
    'load_idiom_registry',
    'make_body_transformer',
    'rewrite_registered_idioms',
    'rewrite_skill_directives',
    'rewrite_slash_commands',
]
