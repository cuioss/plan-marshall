#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``findings storage`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Storage-layout tests for the per-type findings JSONL split.

These tests pin the contract for the per-type storage layer:

* findings live under ``findings/{type}.jsonl`` (one file per finding type),
* Q-Gate findings live under ``findings/qgate-{phase}.jsonl``,
* assessments live under ``findings/assessments.jsonl``,
* per-type files are created lazily on first write,
* ``query_findings`` merges across every per-type file with a stable
  ``hash_id`` space,
* type / resolution / promoted / file-pattern filters keep working post-split,
* ``get_finding`` / ``resolve_finding`` / ``promote_finding`` locate the
  owning per-type file by ``hash_id`` (not by type),
* ``add_finding`` / ``add_qgate_finding`` / ``add_assessment`` route writes to
  their respective files within the same ``findings/`` directory.

Implementation tests (CLI plumbing, validation error paths, qgate dedup/reopen
semantics) live in ``test_findings_store.py`` and ``test_manage_findings.py``;
this module is intentionally storage-layout focused.
"""


import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-findings'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_findings_core = _load_module('_findings_core', '_findings_core.py')


add_assessment = _findings_core.add_assessment


add_finding = _findings_core.add_finding


add_qgate_finding = _findings_core.add_qgate_finding


get_assessments_path = _findings_core.get_assessments_path


get_finding = _findings_core.get_finding


get_findings_dir = _findings_core.get_findings_dir


get_findings_path = _findings_core.get_findings_path


get_qgate_path = _findings_core.get_qgate_path


mark_finding_responded = _findings_core.mark_finding_responded


promote_finding = _findings_core.promote_finding


query_findings = _findings_core.query_findings


query_qgate_findings = _findings_core.query_qgate_findings


resolve_finding = _findings_core.resolve_finding
