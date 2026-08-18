# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-component target scoping — the ``targets:`` frontmatter filter.

A capability that exists only on some assistants has no good home in a
build that ships every component everywhere: it either lands on targets
where it cannot work, or it is forced into a runtime no-op. This module
is the fourth home the placement model names — a component declares the
targets it ships to, and on every other target it is simply ABSENT.

Contract
--------
A component (an ``agents/*.md``, a ``commands/*.md``, or a skill's
``SKILL.md``) MAY declare a top-level ``targets:`` frontmatter field:

.. code-block:: yaml

    ---
    name: tools-fix-intellij-diagnostics
    description: ...
    targets: [claude]
    ---

* **Field absent** — the component ships to every target. This is the
  default and the overwhelmingly common case; no existing component
  changes behaviour.
* **Field present** — the component is emitted only by a target whose
  registry name the list contains.

A skill's declaration governs the whole skill DIRECTORY, since a skill is
a directory whose ``SKILL.md`` is its manifest. An agent's or a command's
governs that one file. Files *inside* a skill are not individually
scopable — that would need a file-level mechanism this one deliberately
is not.

Fail closed
-----------
Silent exclusion is prohibited, so every declaration is validated the
moment it is read and an invalid one aborts the build
(:class:`TargetScopeError`):

* a name absent from ``TARGET_REGISTRY`` — almost always a typo, and one
  that would otherwise silently narrow the component's reach;
* an empty list — a component shipped nowhere is an authoring error, not
  an intent; omitting the field is how you say "everywhere";
* a list naming ONLY targets that emit no component tree (``pr-agent``
  derives a single reviewer configuration from skill rules, so it has no
  component to filter) — such a declaration passes a registry-membership
  check while still shipping the component nowhere.

The valid names are derived from ``TARGET_REGISTRY`` and from each
target's own :attr:`~marketplace.targets.base.TargetBase.emits_bundle_tree`
capability, never enumerated here, so a target registered later needs no
edit to this module to be a legal value or to be exempt.

What derivation does NOT give you
---------------------------------
That derivation governs which names are LEGAL. It does not make a new
target honour the filter: ENFORCEMENT is per-target wiring — each
component-tree target calls :func:`emits_to` (or
:func:`excluded_emission_roots`) from its own emit path, and a target that
simply never called it would emit every scoped-out component with nothing
here to stop it. The obligation is stated on
:meth:`~marketplace.targets.base.TargetBase.generate` and in
``marketplace/targets/README.md`` § "Adding a New Target", and it is pinned
by a test that generates through EVERY registered component-tree target and
asserts a scoped-out component is absent from its output — so an unwired
target fails the suite rather than shipping quietly.

Degradation
-----------
A component file that cannot be read or decoded yields "no declaration",
i.e. the pre-existing emit-everywhere behaviour. Failing OPEN is correct
here specifically because this module only ever REMOVES output: a read
fault must not be able to make a component vanish from a target it
belongs on. The unreadable file itself still fails wherever it is
actually consumed.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

#: Frontmatter field a component uses to declare the targets it ships to.
TARGET_SCOPE_FIELD = 'targets'

#: Bundle sub-directories holding single-file components, keyed to nothing
#: else: the file itself is both the declaration site and the emission unit.
_FILE_COMPONENT_DIRS = ('agents', 'commands')

#: Bundle sub-directory holding directory-shaped components. The manifest
#: is ``{skill_dir}/SKILL.md`` and the emission unit is ``{skill_dir}``.
_SKILLS_DIR = 'skills'

#: Manifest filename of a directory-shaped component.
_SKILL_MANIFEST = 'SKILL.md'


class TargetScopeError(RuntimeError):
    """Raised when a component's ``targets:`` declaration is invalid.

    Carries the offending component path and the offending value, so the
    build failure names the file an author has to edit.
    """


# ---------------------------------------------------------------------------
# Registry-derived target sets
# ---------------------------------------------------------------------------


def registered_target_names() -> frozenset[str]:
    """Return every registered target's registry name.

    The import is deferred to call time. This module is imported from inside
    the target sub-packages that ``marketplace.targets`` imports for their
    registration side-effect, so a module-level ``from marketplace.targets
    import TARGET_REGISTRY`` would bind the registry before any target had
    registered into it. That happens to work — the registry is mutated in
    place rather than rebound — but it makes correctness rest on that detail.
    Reading it at call time does not.
    """
    from marketplace.targets import TARGET_REGISTRY  # noqa: PLC0415

    return frozenset(TARGET_REGISTRY)


def component_tree_target_names() -> frozenset[str]:
    """Return the registry names of targets that emit a component tree.

    Derived from each target's ``emits_bundle_tree`` capability rather than
    enumerated. The capability is an instance property, so each registered
    class is constructed — every target is constructible with no arguments
    (the one target taking a selection defaults it).
    """
    from marketplace.targets import TARGET_REGISTRY  # noqa: PLC0415

    return frozenset(
        name for name, target_cls in TARGET_REGISTRY.items() if target_cls().emits_bundle_tree
    )


# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------


def _frontmatter_block(text: str) -> str | None:
    """Return the leading ``---``-fenced block's inner text, or ``None``.

    A UTF-8 BOM is stripped first: ``read_text`` leaves it in the string, and
    a file carrying one would otherwise look like it had no frontmatter at
    all — which reads as "declares no scope" and silently ships the component
    everywhere.

    The closing fence is matched as a whole ``\\n---\\n`` line rather than as
    a bare ``---`` substring, so a value that itself contains three hyphens
    does not truncate the block and hide the fields after it.
    """
    text = text.lstrip('\ufeff')
    if not text.startswith('---\n'):
        return None
    end = text.find('\n---\n', 4)
    if end != -1:
        return text[4:end]
    if text.endswith('\n---'):
        return text[4: len(text) - len('\n---')]
    return None


def _strip_comment(value: str) -> str:
    """Drop a trailing YAML comment from a scalar or flow-sequence value.

    ``targets: [claude]  # note`` and ``targets: claude  # note`` both carry a
    comment the value parser would otherwise fold into a token, producing a
    diagnostic that names ``[claude] # note`` as the unknown target. A ``#``
    is a comment only when it opens a token, which is what YAML requires and
    what keeps a hypothetical name containing ``#`` intact.
    """
    head, sep, _tail = value.partition('#')
    if not sep:
        return value
    if head and not head[-1].isspace():
        return value
    return head.rstrip()


def _split_inline(value: str) -> list[str]:
    """Split an inline scalar or flow-sequence value into tokens.

    Accepts both ``[a, b]`` and the bare ``a, b`` spelling. ``[]`` yields the
    empty list, which the validator rejects — an empty declaration is an
    authoring error rather than a silent no-op.
    """
    inner = _strip_comment(value)
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1]
    return [token.strip().strip('"').strip("'") for token in inner.split(',') if token.strip()]


def _collect_block_items(lines: list[str]) -> list[str]:
    """Collect a YAML block sequence's items, stopping at the first non-item.

    A blank line and a whole-line ``#`` comment are skipped rather than
    ending the sequence: ending there would read a commented list as an
    EMPTY one and reject a component that declares its targets perfectly
    well, under a message describing a file that does not exist.
    """
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if not stripped.startswith('-'):
            break
        item = _strip_comment(stripped[1:].strip()).strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _declared_tokens(text: str) -> list[str] | None:
    """Return the raw ``targets:`` tokens declared by ``text``, or ``None``.

    ``None`` means the field is absent (ship everywhere). An empty list means
    the field is present but names nothing, which the validator rejects.
    Only a TOP-LEVEL key counts: an indented ``targets:`` belongs to a nested
    mapping and is a different field.
    """
    block = _frontmatter_block(text)
    if block is None:
        return None
    lines = block.split('\n')
    for index, line in enumerate(lines):
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(':')
        if not separator or key.strip() != TARGET_SCOPE_FIELD:
            continue
        value = value.strip()
        if value:
            return _split_inline(value)
        return _collect_block_items(lines[index + 1:])
    return None


# ---------------------------------------------------------------------------
# Validation and the public predicate
# ---------------------------------------------------------------------------


def _named(names: frozenset[str] | list[str]) -> str:
    return ', '.join(sorted(names))


def _validate(tokens: list[str], path: Path) -> frozenset[str]:
    """Validate declared tokens against the registry, or raise.

    Every message names the offending component and the offending value, so
    the build failure is actionable without re-deriving what went wrong.
    """
    tree_targets = component_tree_target_names()
    if not tokens:
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}:` declares an empty list — a component that '
            f'ships to no target is an authoring error. Omit the field to ship to every '
            f'target, or name at least one of: {_named(tree_targets)}.'
        )
    registered = registered_target_names()
    unknown = sorted(token for token in tokens if token not in registered)
    if unknown:
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}:` names unknown target(s): {", ".join(unknown)}. '
            f'Registered targets are: {_named(registered)}.'
        )
    if not tree_targets.intersection(tokens):
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}: [{", ".join(tokens)}]` names only target(s) that '
            f'emit no component tree, so the component would ship nowhere. Name at least one '
            f'of: {_named(tree_targets)}.'
        )
    return frozenset(tokens)


def read_target_scope(path: Path) -> frozenset[str] | None:
    """Return the validated target scope declared by ``path``, or ``None``.

    Args:
        path: The component file — an ``agents/*.md``, a ``commands/*.md``,
            or a skill's ``SKILL.md``.

    Returns:
        The declared registry names, or ``None`` when the component declares
        no scope (ship to every target).

    Raises:
        TargetScopeError: The declaration is invalid — see the module
            docstring's fail-closed rules.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    tokens = _declared_tokens(text)
    if tokens is None:
        return None
    return _validate(tokens, path)


def emits_to(path: Path, target_name: str) -> bool:
    """Whether the component at ``path`` is emitted by ``target_name``.

    Raises:
        TargetScopeError: The component's declaration is invalid. Validation
            runs on every read, so an invalid declaration aborts any run that
            reads that component. What that covers is exactly the runs that
            READ components: every component-tree target's emit, and the
            Claude target's validate-only mode (which re-walks each bundle's
            components for this check alone). A ``pr-agent``-only run reads
            no component at all — it derives a reviewer configuration from
            skill rule text — so it neither can nor does validate a
            declaration; the plugin-doctor ``targets-scope-invalid`` rule is
            the authoring-time net for that case.
    """
    scope = read_target_scope(path)
    return scope is None or target_name in scope


# ---------------------------------------------------------------------------
# Bundle-level helpers
# ---------------------------------------------------------------------------


def iter_component_manifests(bundle_dir: Path) -> Iterator[tuple[Path, Path]]:
    """Yield ``(manifest, emission_root)`` for every component in ``bundle_dir``.

    ``manifest`` is the file carrying the ``targets:`` declaration;
    ``emission_root`` is what the declaration governs — the component file
    itself for an agent or a command, the whole skill directory for a skill.
    Both are absolute paths.
    """
    for subdir_name in _FILE_COMPONENT_DIRS:
        subdir = bundle_dir / subdir_name
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.iterdir()):
            if path.is_file() and path.suffix == '.md' and not path.name.startswith('.'):
                yield path, path

    skills_dir = bundle_dir / _SKILLS_DIR
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            manifest = skill_dir / _SKILL_MANIFEST
            if skill_dir.is_dir() and manifest.is_file():
                yield manifest, skill_dir


def excluded_emission_roots(bundle_dir: Path, target_name: str) -> frozenset[Path]:
    """Return the bundle-relative paths ``target_name`` must NOT emit.

    An entry is either a component file (agent, command) or a skill
    directory; a caller skips a path that equals an entry or lies beneath
    one. Validating every component of the bundle — not only the excluded
    ones — is deliberate: an invalid declaration fails the build even when
    the generating target would have included it anyway.

    Raises:
        TargetScopeError: Some component in the bundle declares an invalid
            scope.
    """
    excluded: set[Path] = set()
    for manifest, emission_root in iter_component_manifests(bundle_dir):
        if not emits_to(manifest, target_name):
            excluded.add(emission_root.relative_to(bundle_dir))
    return frozenset(excluded)


def is_under_any(rel: Path, roots: frozenset[Path]) -> bool:
    """Whether the bundle-relative ``rel`` is one of ``roots`` or inside one."""
    if not roots:
        return False
    return rel in roots or any(parent in roots for parent in rel.parents)


__all__ = [
    'TARGET_SCOPE_FIELD',
    'TargetScopeError',
    'component_tree_target_names',
    'emits_to',
    'excluded_emission_roots',
    'is_under_any',
    'iter_component_manifests',
    'read_target_scope',
    'registered_target_names',
]
