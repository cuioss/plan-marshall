# Phase 2: Refine Workflow Overview

Visual overview of the refine workflow for human readers.

## Request Refine Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUEST REFINE LOOP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 2: Load Confidence Threshold                              │
│      ↓                                                          │
│  Step 3: Load Compatibility Strategy                            │
│      ↓                                                          │
│  Step 4: Load Architecture Context ──────────────────────┐      │
│      ↓                                   arch_context    │      │
│  Step 5: Load Request                         │          │      │
│      ↓                                        ↓          ↓      │
│  Step 6: Analyze Request Quality ←── technologies, modules      │
│      ↓                                        │          │      │
│  Step 7: Analyze in Architecture Context ←────┘──────────┘      │
│      │   Module Mapping                                         │
│      │   Feasibility Check                                      │
│      │   Scope Size Estimation                                  │
│      │   Track Selection ─────────→ decision.log                │
│      ↓                    (module details on demand)            │
│  Step 8: Evaluate Confidence                                    │
│      │                                                          │
│      ├── confidence >= threshold → Step 11: Persist & Return    │
│      │                              (track, scope → references) │
│      │                                                          │
│      └── confidence < threshold → Step 9: Clarify with User     │
│              ↓                                                  │
│          Step 10: Update Request                                │
│              ↓                                                  │
│          (loop back to Step 6)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

| Step | Input | Output | Stored As |
|------|-------|--------|-----------|
| Step 2 | marshal.json | threshold value | `confidence_threshold` |
| Step 3 | marshal.json | compatibility value + description | `compatibility`, `compatibility_description` |
| Step 4 | architecture info | project + modules + technologies | `arch_context` |
| Step 5 | request.md | title, description, clarifications | `request` |
| Step 6 | `request` + `arch_context` | quality findings | `quality_findings` |
| Step 7 | `request` + `arch_context` + detailed queries | mapping + feasibility + scope + track | `mapping_findings`, `scope_estimate`, `track` |
| Step 8 | all findings | confidence score | decision |
| Step 11 | all results | - | references.json, decision.log |
