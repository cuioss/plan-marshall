# SPDX-License-Identifier: FSL-1.1-ALv2
"""PR-Agent target sub-package.

Exposes ``PrAgentTarget`` (defined in ``target.py``) and registers it in
the marketplace target registry on import.
"""

from __future__ import annotations

from marketplace.targets import register_target
from marketplace.targets.pr_agent.target import PrAgentTarget

register_target('pr-agent', PrAgentTarget)

__all__ = ['PrAgentTarget']
