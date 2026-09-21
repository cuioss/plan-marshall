envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:33Z

# An AST collector that records only definition nodes misses the import that publishes the same seam

**Signal**: automated review — CodeRabbit inline finding `ad7796`, severity Major, triaged FIX and fixed in-run
**Component**: `plan-marshall:persona-module-tester` (test-guard authoring) — surfaced in `test/test_parser_seam_coverage.py:349`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## What the reviewer said

> `parse_ns` resolves a callable `build_parser` through `getattr(module, name)`. A structural hook can add `from helper import build_parser`; that creates seam 1, but this collector does not record `ast.ImportFrom` bindings. The exemption can then remain pinned and this guard passes.

## What was confirmed

The seam the structural pin stands in for is `conftest._parser_from_builder`, which resolves via `getattr(module, name, None)` + `callable()`. A module-level `from helper import build_parser` therefore **does** publish seam 1 — while the collector recorded only `FunctionDef` / `AsyncFunctionDef` / `ClassDef` / `Assign` / `AnnAssign`, so a `SEAM_EXEMPT` row would stay pinned and green.

This was the seam-1 mirror of a gap the module docstring already named for seam 2 — i.e. the shape was known on one seam and not transferred to the other. Fixed on-branch by recording `ImportFrom` and `Import` alias bindings (`asname or name`), extending the failure message to say whether the builder is *defined* or *imported*, and adding a regression test with a matched negative control.

## Why it is candidate-lesson material

A guard whose subject is "does this module publish name N" must model **every binding form the resolver can see**, not the subset that is syntactically a definition. An AST collector enumerating definition node types is the recurring under-derivation: it reads as complete because the node list is explicit.

Second-order: the docstring had already named the identical gap for the sibling seam. A known gap on one member of a symmetric pair is a standing obligation to check the other.

## Proposed rule (for orchestrator judgement)

When a guard asserts a name is *not* published, derive the binding-form set from the resolver the guard stands in for (here: `getattr` + `callable`), not from the node types that first came to mind. Where the guard covers a symmetric pair of seams, a gap named for one is a defect on the other until disproved.
