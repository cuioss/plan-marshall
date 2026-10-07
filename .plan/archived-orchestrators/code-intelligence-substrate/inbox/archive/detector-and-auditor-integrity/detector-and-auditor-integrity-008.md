envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:30:00Z

# Neither token ledger sees the whole plan; the union exceeds either by 12 rows and 4.46M tokens

component: plan-marshall:manage-metrics
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

`reconcile-ledgers` on this plan:

```
execution_log_rows: 32
boundary_rows:      33
union_rows:         45
findings_count:     25
```

Neither ledger alone sees more than 73% of the plan's dispatches.

Twelve dispatches recorded usage at termination that **no `record-step` row
names**:

- phase 5-execute, 9 rows: 620,767 + 354,293 + 210,485 + 443,105 + 306,524 +
  359,502 + 431,445 + 304,223 + 548,756 = **3,579,100 tokens**
- phase 6-finalize, 3 rows: 194,923 + 347,913 + 341,059 = **883,895 tokens**
- total invisible to any `execution_log` sum: **4,462,995 tokens**

## Why this is not academic

The `routing-decisions` aspect publishes `cost_preview.execution_log_tokens:
2,655,237` over population `5-execute,6-finalize` — derived from the execution
log. Against a union that includes the 4.46M above, that figure captures roughly
**37%** of the spend it appears to summarize, and it is published with a
population label that names the phases but not the ledger's coverage of them.

Separately, 6-finalize carries 18 boundary rows and no `end_time`;
`reconcile-ledgers` reports `boundary_never_closed` over 3,539,132 tokens.

## The generalizable rule

Two append-only ledgers written by independent call sites with no shared key will
diverge in BOTH directions, and only their union is the population. A figure
derived from one of them must publish which ledger it came from and that
ledger's coverage — `execution_log_tokens` names its phases but not its
completeness, so a reader cannot tell a 2.66M total from a 7.12M one. Publish
`union_rows` beside any single-ledger sum, or run the reconciliation before
quoting either.
