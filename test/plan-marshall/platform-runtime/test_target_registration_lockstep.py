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

import marketplace_paths  # noqa: I001
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
