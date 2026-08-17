#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep invariants over the platform-runtime target registration block.

Target registration is split across two modules that resolve a target
independently: ``platform_runtime`` (the router's registration block) and
``script-shared``'s ``marketplace_paths`` (the layout-lookup consumer). Nothing
in either module forces them to agree, so a divergence would route layout
lookups at one target while the router dispatched another — silently, since both
modules stay internally consistent. These tests are the coupling.
"""

import pathlib  # noqa: I001

import pytest

import marketplace_paths
import platform_runtime


def test_default_target_agrees_across_modules() -> None:
    """Both modules resolve the same fallback target identifier."""
    assert platform_runtime._DEFAULT_TARGET == marketplace_paths._DEFAULT_RUNTIME_TARGET


def test_default_target_is_registered() -> None:
    """The fallback target is a registered runtime, not a dangling identifier."""
    assert platform_runtime._DEFAULT_TARGET in platform_runtime._REGISTRY


def test_bootstrap_libs_cover_exactly_the_registry() -> None:
    """Every registered target declares bootstrap libs, and no extras are declared.

    An entry missing from ``_TARGET_BOOTSTRAP_LIBS`` silently starves that
    target's runtime of its sibling script directories; an entry with no
    ``_REGISTRY`` counterpart is dead configuration.
    """
    assert set(platform_runtime._TARGET_BOOTSTRAP_LIBS) == set(platform_runtime._REGISTRY)


def test_default_skill_roots_match_what_the_default_target_resolves() -> None:
    """The hardcoded skill-root fallback equals what the default target's op returns.

    ``_DEFAULT_SKILL_ROOTS`` is used when the layout op cannot be reached at all,
    so it is a second, independent encoding of "what the default target's roots
    are". Nothing forces it to agree with the op, and a change to the default
    target -- or to that target's roots -- would leave it quietly wrong.

    The expectation is NOT computed from the constant it guards: it comes from
    invoking the real layout op through the real registry.
    """
    resolved = marketplace_paths._invoke_layout_op(marketplace_paths._DEFAULT_RUNTIME_TARGET)

    assert resolved is not None, "the layout op must be reachable from the checkout"
    assert resolved == marketplace_paths._DEFAULT_SKILL_ROOTS


def test_default_bundle_cache_roots_match_what_the_default_target_resolves() -> None:
    """The hardcoded bundle-cache fallback equals what the default target's op returns.

    Both sides derive a home directory, and they derive it DIFFERENTLY: the
    constant uses ``resolve_home()``, which exists to survive ``Path.home()``
    raising in a container with no ``HOME``; the op calls ``Path.home()`` raw.
    Production degrades correctly there -- ``_invoke_layout_op`` swallows the
    failure and the caller falls back to this same constant -- so a red here
    would report an environment, not a defect, and the guard below skips instead.

    The guard is a courtesy, not a defence: ``claude_runtime`` calls
    ``Path.home()`` at MODULE level, so in that environment this file fails to
    IMPORT and every test in it errors during collection before any guard runs.
    Closing that properly means routing the runtimes' home resolution through
    ``resolve_home()``; it is pre-existing, out of this plan's surface, and
    recorded as residue in the run report.
    """
    try:
        pathlib.Path.home()
    except RuntimeError:  # pragma: no cover - depends on the ambient environment
        pytest.skip("no resolvable home directory; the op's raw Path.home() cannot run")

    resolved = marketplace_paths._invoke_layout_op(
        marketplace_paths._DEFAULT_RUNTIME_TARGET, "layout_bundle_cache_root"
    )

    assert resolved is not None, "the layout op must be reachable from the checkout"
    assert resolved == marketplace_paths._DEFAULT_BUNDLE_CACHE_ROOTS


def test_every_registered_target_resolves_a_bundle_cache_root() -> None:
    """Both layout ops resolve for every registered target, not just the default one.

    The sibling constant test covers only the default target, so this one
    quantifies over the live registry -- a later target is covered without anyone
    remembering, and a target whose implementation raised is caught here rather
    than only wherever else it happens to be exercised.
    """
    for target in platform_runtime._REGISTRY:
        roots = marketplace_paths._invoke_layout_op(target, "layout_bundle_cache_root")

        assert roots, f"{target}: layout_bundle_cache_root resolved nothing ({roots!r})"


def test_layout_op_resolves_each_registered_target_distinctly() -> None:
    """Every registered target resolves through the router's registry to its own roots.

    Every test in this file drives ``_invoke_layout_op`` unpatched -- elsewhere
    in the suite it is patched out at every call site -- and this one quantifies
    over the live ``_REGISTRY`` rather than a name list, so a target added later
    is covered without anyone remembering. Asserting the roots are pairwise
    DISTINCT is what makes it non-vacuous: a registry lookup that collapsed every
    target onto one runtime would still return roots, and only the distinctness
    catches it.

    Its one fragility, accepted deliberately: a future target that legitimately
    discovers in the same roots as an existing one turns this red with no defect
    present. It fires visibly at target-add time, which is the right moment to
    replace distinctness with a per-target assertion.
    """
    resolved = {
        target: marketplace_paths._invoke_layout_op(target)
        for target in platform_runtime._REGISTRY
    }

    assert all(roots is not None for roots in resolved.values()), resolved
    assert len(set(resolved.values())) == len(resolved), (
        f"two registered targets resolved to identical roots: {resolved}"
    )


def test_unregistered_target_resolves_to_the_default_targets_roots() -> None:
    """An unregistered target falls back to the default target's runtime, not to None.

    This pins the documented divergence from the router, which rejects an
    unregistered target with ``unknown_target``: a layout lookup has no error
    channel, so it answers with the default rather than failing. The answer is
    the same one the module's own fallback constant carries.
    """
    assert "no-such-target" not in platform_runtime._REGISTRY

    resolved = marketplace_paths._invoke_layout_op("no-such-target")

    assert resolved == marketplace_paths._DEFAULT_SKILL_ROOTS
