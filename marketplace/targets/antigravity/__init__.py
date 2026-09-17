# SPDX-License-Identifier: FSL-1.1-ALv2
"""marketplace.targets.antigravity — Antigravity target sub-package."""

from __future__ import annotations

from marketplace.targets import register_target
from marketplace.targets.antigravity.target import AntigravityTarget

register_target('antigravity', AntigravityTarget)

__all__ = ['AntigravityTarget']
