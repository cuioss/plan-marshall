# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-fragments.py``.

Covers the three subcommands (``init``, ``add``, ``finalize``) across live
and archived modes, plus the fault paths documented in the script header:
malformed TOON fragments and duplicate aspect registration without
``--overwrite``. Mode is now a bundle property (persisted under
``_meta.mode`` by ``init``); ``add`` and ``finalize`` read it from the
bundle rather than accepting ``--mode`` as an argument.

``cmd_add`` validates ``--aspect`` against the canonical aspect-key registry
(static :data:`retro_sections.SECTION_SPEC` keys ∪ domain-contributed aspects)
before touching the bundle. Every aspect key used across these tests is a
member of that registry — the registered static keys are hyphenated
(``request-result-alignment``, ``log-analysis``, ``artifact-consistency``,
``plan-efficiency``, ``lessons-proposal``, …) to match the consumer's section
map, never the underscored variants that would silently empty a report
section. The validation guard itself is exercised by
:class:`TestAddAspectKeyValidation`.
"""


from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))




from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-fragments.py'


# =============================================================================
# Helpers
# =============================================================================


def _write_fragment(tmp_path: Path, name: str, body: str) -> Path:
    """Write ``body`` to ``tmp_path/name`` and return the resulting path."""
    fragment = tmp_path / name
    fragment.write_text(body, encoding='utf-8')
    return fragment


def _valid_fragment_body(aspect: str) -> str:
    """Return a minimal valid TOON fragment for ``aspect``."""
    return f'status: success\naspect: {aspect}\n'


# =============================================================================
# Direct-import unit tests — exercise internal functions for coverage
# =============================================================================
#
# The subprocess-based tests validate the CLI contract end-to-end, but
# coverage.py does not instrument subprocesses here — so to meet the 80%
# coverage target we also exercise the script's public + private helpers
# directly via importlib. This complements (does not replace) the integration
# tests: direct calls exercise branch logic without the argparse layer.


def _load_module():
    """Load collect-fragments.py as an importable module via importlib."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('collect_fragments', str(SCRIPT_PATH))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ArgsNS:
    """Simple namespace mimicking argparse.Namespace for cmd_* tests.

    ``mode`` is intentionally not part of the base fixture: ``cmd_add`` and
    ``cmd_finalize`` do not read ``args.mode`` under the new contract (they
    read the mode from the bundle's persisted ``_meta.mode``). Only
    ``cmd_init`` consumes ``mode`` — callers pass it explicitly when
    constructing init-style namespaces.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# =============================================================================
# Internal helpers that invoke the script
# =============================================================================


def _init_bundle(plan_id: str) -> None:
    """Run ``init`` for ``plan_id`` in live mode and assert success."""
    result = run_script(
        SCRIPT_PATH,
        'init',
        '--plan-id',
        plan_id,
        '--mode',
        'live',
    )
    assert result.success, f'init failed: {result.stderr}'


def _add_aspect(plan_id: str, aspect: str, fragment_path: Path) -> None:
    """Run ``add`` for the given aspect and assert success.

    ``--mode`` is no longer passed: the mode is read from the bundle's
    persisted ``_meta.mode``.
    """
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        plan_id,
        '--aspect',
        aspect,
        '--fragment-file',
        str(fragment_path),
    )
    assert result.success, f'add failed: {result.stderr}'
