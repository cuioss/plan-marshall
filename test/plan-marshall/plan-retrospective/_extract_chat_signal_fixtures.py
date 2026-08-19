# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``extract chat signal`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))


SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'extract-chat-signal.py'
)


# Direct module load so unit tests can poke the pure helpers.
_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)


# The provenance predicate moved to its own module; this file exercises it only
# where the reduction's parsing behaviour depends on it.
_prov = load_script_module('plan-marshall', 'plan-retrospective', '_chat_provenance.py')


# ---------------------------------------------------------------------------
# JSONL turn builders
# ---------------------------------------------------------------------------


def _turn(role: str, content) -> str:
    """Produce one JSONL event line carrying a ``message`` with ``role``/``content``."""
    return json.dumps({'type': 'turn', 'message': {'role': role, 'content': content}})


def _text_blocks(*texts: str) -> list[dict[str, str]]:
    """Build a list of ``text`` content blocks (the common multi-block shape)."""
    return [{'type': 'text', 'text': t} for t in texts]


# The structural signature of a skill body injected as a synthetic ``user``
# turn: the base-directory line followed by a markdown heading and a body.
SKILL_LOAD_TEXT = (
    'Base directory for this skill: /Users/x/.claude/plugins/cache/demo/skills/demo\n\n'
    '# Demo Skill\n\n'
    'Long injected skill body. ' * 40
)


# ---------------------------------------------------------------------------
# Unit tests: cmd_run (pure, via a Namespace-like shim)
# ---------------------------------------------------------------------------


class _Args:
    """Minimal stand-in for ``argparse.Namespace`` carrying the two run args."""

    def __init__(self, transcript_path: str, read_budget_bytes: int):
        self.transcript_path = transcript_path
        self.read_budget_bytes = read_budget_bytes
