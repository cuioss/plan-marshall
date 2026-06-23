# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCode target sub-package.

Exposes ``OpenCodeTarget`` (defined in ``target.py``) and registers it in
the marketplace target registry on import.
"""

from __future__ import annotations

from marketplace.targets import register_target
from marketplace.targets.opencode.target import OpenCodeTarget

register_target('opencode', OpenCodeTarget)

__all__ = ['OpenCodeTarget']
