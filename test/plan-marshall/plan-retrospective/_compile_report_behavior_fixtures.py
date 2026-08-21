# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``compile report behavior`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

In-process behavioral tests for ``compile-report.py``.

The sibling ``test_compile_report.py`` exercises the full pipeline through the
``run_script`` subprocess harness plus a few in-process ``cmd_run`` cleanup
cases. The modules this preamble serves unit-test the assembler's pure decision/rendering helpers
IN-PROCESS — ``should_emit`` (every branch), ``_dispatch_boundaries_has_present_phase``,
the two body renderers, ``build_header``/``build_document``, ``resolve_output_path``,
``resolve_plan_dir``, and ``load_fragments`` — plus an in-process archived
``cmd_run`` that the subprocess suite reaches only out-of-process.
"""


from __future__ import annotations

from conftest import load_script_module

_cr = load_script_module('plan-marshall', 'plan-retrospective', 'compile-report.py', 'cr_behavior_mod')
