# SPDX-License-Identifier: FSL-1.1-ALv2
"""Claude target sub-package.

Imports the concrete `ClaudeTarget` class from `target.py` and registers
it under the name ``"claude"`` in the global `TARGET_REGISTRY`. The
registration is a side-effect of importing this package — see
`marketplace.targets.__init__` for the framework wiring.
"""

from __future__ import annotations

from marketplace.targets import register_target
from marketplace.targets.claude.target import ClaudeTarget

register_target('claude', ClaudeTarget)

__all__ = ['ClaudeTarget']
