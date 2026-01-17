# Verification Architecture

Visual overview of the hybrid verification engine.

## Engine Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                    HYBRID VERIFICATION ENGINE                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Phase 1: Structural Checks (Script)                               │
│  - File existence via manage-* tools                               │
│  - TOON/MD syntax validation                                       │
│  - Required sections present                                       │
│  - Cross-references valid                                          │
│                        │                                           │
│                        ▼                                           │
│  Phase 2: Semantic Assessment (LLM-as-Judge)                       │
│  - Reads criteria from test case                                   │
│  - Compares actual vs golden reference                             │
│  - Scores: scope (0-100), completeness (0-100), quality (0-100)    │
│  - Explains reasoning for each score                               │
│                        │                                           │
│                        ▼                                           │
│  Phase 3: Assessment Report                                        │
│  - TOON structured results                                         │
│  - Markdown narrative report                                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Component Interaction

```
Test Case                    Scripts                     LLM Assessment
─────────────────────────────────────────────────────────────────────
test-definition.toon    →   (trigger execution)    →   plan created
expected-artifacts.toon →   verify-structure.py    →   structural pass/fail
criteria/semantic.md    →   collect-artifacts.py   →   artifacts collected
golden/verified-result  →   (comparison input)     →   LLM-as-judge scores
```

## Directory Layout

```
workflow-verification/                    # Test cases (version-controlled)
├── test-cases/{test-id}/
│   ├── test-definition.toon
│   ├── expected-artifacts.toon
│   ├── criteria/semantic.md
│   └── golden/verified-result.md

.plan/temp/workflow-verification/         # Results (ephemeral)
└── {test-id}-{timestamp}/
    ├── actual-artifacts/
    ├── assessment-results.toon
    └── assessment-detail.md
```
