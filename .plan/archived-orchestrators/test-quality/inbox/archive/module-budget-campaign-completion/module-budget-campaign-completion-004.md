envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=candidate-lesson
created=2026-09-23T14:39:48Z

component=plan-marshall:phase-3-outline
category=improvement
title=Declare test carve fixtures under test/_shared/ with conftest companions
plan_id=module-budget-campaign-completion
source_aspects=artifact-consistency,manifest-decisions,request-result-alignment
confidence=high

# Declare test carve fixtures under test/_shared/ with conftest companions

## Context

Single-carve plan split test/test_shared_harness.py (401 lines) into 4 test_* collection units, merged as PR #1593 via merge queue with pytest green and doctor clean. The outline declared the fixtures hoist at test/_shared_harness_fixtures.py, but the landing promoted fixtures to test/_shared/_shared_harness_fixtures.py, updated test/plan-marshall/script-shared/test_conftest_loader_contract.py, and fixed a TEST_ROOT relocation.

## Root cause

The carve outline template assumes a flat _*fixtures.py hoist outside collection, while this repo's test/_shared/ package owns shared fixtures and its conftest loader contract plus TEST_ROOT scoping move with the fixtures.

## Proposed action

Default test-carve outline fixtures to test/_shared/ when that package exists, and list the conftest loader contract reference plus TEST_ROOT relocation as expected companion edits in the deliverable's affected files.

## Evidence

- aspect: artifact-consistency — outline_only test/_shared_harness_fixtures.py vs references_only test/_shared/_shared_harness_fixtures.py and test_conftest_loader_contract.py
- aspect: manifest-decisions — declared_vs_realized_set mismatch with realized tier realized_capture over 7 files
- aspect: request-result-alignment — goal fulfilled at 83% coverage with the 2-file delta explained as promotion plus companions
