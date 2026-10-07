envelope_version=1
sender_type=plan
sender_id=implement-plan-01-model-provisioning
epic=model-provisioning
kind=candidate-lesson
created=2026-09-14T10:57:42Z

envelope_version=1
sender_type=plan
sender_id=implement-plan-01-model-provisioning
epic=model-provisioning
kind=candidate-lesson
created=2026-09-14T11:00:00Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Owed architecture hint: ci-timeout acceptance recurrence in plan-marshall

## Owed enrich call

- module: plan-marshall
- verb: insight
- hint: the project tolerates slow whole-tree CI waits exceeding the wait budget — timeout findings that verify green on re-poll are accepted in plan-marshall without fix tasks

## Provenance

Generalized from 3 accepted ci-timeout dispositions within plan implement-plan-01-model-provisioning (recurrence 3 >= threshold 2). Raw disposition rows stay behind the manage-findings query per the privacy invariant; only this generalized hint is persisted. Enrich via: architecture enrich insight --module plan-marshall --insight "the project tolerates slow whole-tree CI waits exceeding the wait budget — timeout findings that verify green on re-poll are accepted in plan-marshall without fix tasks"
