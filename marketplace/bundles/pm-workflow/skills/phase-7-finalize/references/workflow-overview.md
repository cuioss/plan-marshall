# Phase 7: Finalize Workflow Overview

Visual overview of the finalization workflow for human readers.

## 7-Phase Model

```
1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-verify → 7-finalize
                                              ↑                       │
                                              └───────────────────────┘
                                              (loop on PR issues)
```

**Iteration limit**: 3 cycles max for PR issue resolution.

## Shipping Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                  FINALIZE PIPELINE                       │
│                                                          │
│  ┌─────────┐   ┌──────┐   ┌──────┐                      │
│  │ commit  │ → │ push │ → │  PR  │                      │
│  └─────────┘   └──────┘   └──┬───┘                      │
│                              │                           │
│                              ↓                           │
│  ┌───────────────────────────────────────────────┐      │
│  │            AUTOMATED REVIEW                    │      │
│  │  CI checks │ review comments │ Sonar gate     │      │
│  └───────────────────┬───────────────────────────┘      │
│                      │                                   │
│          ┌──────────┴──────────┐                        │
│          ↓                     ↓                        │
│      [issues]            [no issues]                    │
│          │                     │                        │
│          ↓                     ↓                        │
│   create fix tasks       COMPLETE                       │
│   loop → 5-execute                                       │
│   (max 3 iterations)                                    │
└─────────────────────────────────────────────────────────┘
```
