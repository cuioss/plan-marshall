# SPDX-License-Identifier: FSL-1.1-ALv2
"""marketplace.targets — build-time target framework.

Reads source bundles in `marketplace/bundles/` (Claude Code format, the
source of truth) and emits platform-specific artifacts. Each target
implements `marketplace.targets.base.TargetBase` and registers itself in
`TARGET_REGISTRY` from its sub-package `__init__.py`.

Adding a new target:
    1. Create a sub-package `marketplace/targets/{name}/`.
    2. Implement a `TargetBase` subclass under `{name}/target.py`.
    3. In `{name}/__init__.py`, import the subclass and call
       `register_target('{name}', YourTarget)`.
    4. Import the new sub-package below so the registration side-effect
       fires when callers `import marketplace.targets`.
    5. If the target emits a component tree, honour each component's
       `targets:` frontmatter scope from the emit path — see
       `TargetBase.generate` and `marketplace/targets/README.md`
       § "Adding a New Target", which carries the full checklist.
"""

from __future__ import annotations

from marketplace.targets.base import TargetBase

TARGET_REGISTRY: dict[str, type[TargetBase]] = {}


def register_target(name: str, target_cls: type[TargetBase]) -> None:
    """Register a target class in the global registry.

    Idempotent: re-registering the same name with the same class is a
    no-op. Re-registering with a different class is rejected so reload
    accidents do not silently replace a target.

    Raises:
        ValueError: ``name`` is empty, or contains a comma or whitespace.
        RuntimeError: ``name`` is already registered to a different class.
    """
    if not name or ',' in name or any(ch.isspace() for ch in name):
        raise ValueError(
            f'Target name {name!r} must be non-empty and contain neither a comma nor '
            'whitespace. The comma is load-bearing: component target scoping accepts '
            '`targets: a, b`, which YAML reads as one string, and splits it on commas — '
            'so a name containing one could never be matched by that spelling while '
            'still matching in a list. Whitespace is a naming convention, since a '
            'registry name is also a `--target` command-line value.'
        )
    existing = TARGET_REGISTRY.get(name)
    if existing is target_cls:
        return
    if existing is not None:
        raise RuntimeError(f'Target {name!r} already registered as {existing!r}; cannot replace with {target_cls!r}')
    TARGET_REGISTRY[name] = target_cls


# Sub-package imports trigger their own register_target() calls.
from marketplace.targets import (  # noqa: E402
    claude,  # noqa: F401
    opencode,  # noqa: F401
    pr_agent,  # noqa: F401
)

__all__ = ['TargetBase', 'TARGET_REGISTRY', 'register_target']
