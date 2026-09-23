# SPDX-License-Identifier: FSL-1.1-ALv2
"""cuioss-review-bot target sub-package.

Exposes ``CuiossReviewBotTarget`` (defined in ``target.py``) and registers it
in the marketplace target registry on import under the name
``cuioss-review-bot``.
"""

from __future__ import annotations

from marketplace.targets import register_target
from marketplace.targets.cuioss_review_bot.target import CuiossReviewBotTarget

register_target('cuioss-review-bot', CuiossReviewBotTarget)

__all__ = ['CuiossReviewBotTarget']
