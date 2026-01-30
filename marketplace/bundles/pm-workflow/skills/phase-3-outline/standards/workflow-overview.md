# Workflow Overview Diagram

Visual summary of the phase-3-outline two-track workflow for human reference.

```
┌──────────────────────────────────────────────────────────────────┐
│                    TWO-TRACK OUTLINE WORKFLOW                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Step 1: Load Inputs                                              │
│          → Read track from references.json (set by phase-2)      │
│          → Read request (clarified_request or body)              │
│          → Read module_mapping, domains, compatibility           │
│                                                                   │
│  Step 2: Route by Track                                           │
│          ┌──────────────────┬──────────────────┐                 │
│          │  track = simple  │  track = complex │                 │
│          │        ↓         │        ↓         │                 │
│          │   Steps 3-5      │   Steps 6-9      │                 │
│          └──────────────────┴──────────────────┘                 │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Simple Track (Steps 3-5)

For localized changes where targets are already known from module_mapping.

```
┌─────────────────────────────────────────────────────────────────┐
│                      SIMPLE TRACK                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 3: Validate Targets                                        │
│          → Verify target files/modules exist                     │
│          → Match domain                                          │
│                                                                  │
│  Step 4: Create Deliverables                                     │
│          → Direct mapping from module_mapping                    │
│          → Use deliverable template                              │
│          → One deliverable per target                            │
│                                                                  │
│  Step 5: Simple Q-Gate                                           │
│          → Lightweight verification                              │
│          → Verify deliverable aligns with request                │
│                                                                  │
│  → Continue to Step 10                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Complex Track (Steps 6-9)

For codebase-wide changes requiring discovery and analysis via domain skills.

```
┌─────────────────────────────────────────────────────────────────┐
│                      COMPLEX TRACK                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 6: Resolve Domain Skill                                    │
│          → extension-api resolve --domain X --type outline       │
│          → Returns skill notation (e.g., ext-outline-plugin)     │
│                                                                  │
│  Step 7: Load Domain Skill                                       │
│          → Skill: {resolved_skill_notation}                      │
│          → Skill handles: discovery, analysis, deliverables      │
│          → Skill writes: solution_outline.md, assessments.jsonl  │
│                                                                  │
│  Step 8: Skill Completion                                        │
│          → Verify skill returned success                         │
│          → Log completion                                        │
│                                                                  │
│  Step 9: Q-Gate Verification                                     │
│          → Task: pm-workflow:q-gate-validation-agent             │
│          → Verifies deliverables against request                 │
│                                                                  │
│  → Continue to Step 10                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Domain Skill Interaction (Complex Track)

```
phase-3-outline                           ext-outline-{domain}
═══════════════                           ════════════════════

Step 1: Load track, request
              │
              ▼
Step 2: Route → complex
              │
              ▼
Step 6: Resolve skill ───────────────────► {domain}:ext-outline-{domain}
              │
              ▼
Step 7: ┌─────────────────────────────┐
        │ Skill: ext-outline-{domain}  │
        │                              │────► Discovery
        │ Input: plan_id               │      Analysis
        └─────────────────────────────┘      Deliverables
              │                              ↓
              │                         solution_outline.md
              │                         assessments.jsonl
              ▼
Step 8-9: Validate skill output
              │
              ▼
Step 10: Return results
```

## Step 10: Write Solution and Return

Both tracks converge at Step 10:

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 10: FINALIZE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 10.1: Write Solution Document (Simple Track only)         │
│          → Complex Track: skill already wrote it                 │
│                                                                  │
│  Step 10.2: Log Completion                                       │
│          → Log artifact and decision                            │
│                                                                  │
│  Step 10.3: Return Results                                       │
│          → status: success                                       │
│          → track: {simple|complex}                               │
│          → deliverable_count: {N}                                │
│          → qgate_passed: {true|false}                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
