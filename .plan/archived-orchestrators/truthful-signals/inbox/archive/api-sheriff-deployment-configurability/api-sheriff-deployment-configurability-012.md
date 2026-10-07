envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=finding
created=2026-09-15T08:26:54Z

component=plan-marshall:phase-5-execute
category=bug

# Sighting only — the scope-creep fence has still never measured anything in a consuming repo: two more plans shipped with `plan_creation_sha` absent

⛔ **ROUTED FROM API-SHERIFF'S EPIC LEDGER — and this one is ALREADY TRACKED. Do NOT stage a second
plan for it.** One Open Defects entry from the `deployment-configurability` epic (`cuioss/API-Sheriff`),
recorded 2026-09-04 (PLAN-10) and 2026-09-08 (PLAN-07). Filed here by operator direction on 2026-09-15
and retired from that ledger in the same act. It is a **priority data point for work that already
exists**, nothing more.

## Verification at plan-marshall `origin/main` 7a028157e (read-only, 2026-09-15)

**PARTIALLY FIXED — the reader is honest, the producer still does not exist.**

- ✅ The consumer no longer renders an unmeasured state as a measured one:
  `phase-5-execute/scripts/scope_creep_check.py:78-87` returns `status: could_not_look`,
  `reason: no_baseline_sha`, and **omits** `residual_count` — "the unmeasured state is structurally
  unable to render as a measured one" (`:25-39`).
- ⛔ **No writer exists.** `git grep plan_creation_sha origin/main` hits only
  `phase-5-execute/SKILL.md:600`, `scope_creep_check.py` (`:17`, `:27`, `:212`, `:218`) and three test
  files. Nothing writes the field to `references.json`, so the fence is never computed.

## Already tracked

`PLAN-TRUTH-138-the-scope-creep-guard-has-no-producer-and-has-never-measured-anything.md` is
**superseded by** `PLAN-TRUTH-145-declarations-that-cannot-learn-and-cannot-go-stale.md` (**staged**),
whose **D4** declares the field and **D5** builds the producer. That is the right owner and it is
correctly scoped.

**What this adds:** an independent confirmation from outside the meta-project — two API-Sheriff plans
(PLAN-07, PLAN-10) shipped with the fence unobservable, so the guard's "has never measured anything"
claim is now witnessed in a consuming repo as well. Useful as evidence for PLAN-TRUTH-145's priority;
useless as a new work item.

---

## The retired API-Sheriff ledger entry, verbatim

- ⚠ **No scope-creep verdict exists for PLAN-07 — the check was ABSENT, not passed.**
  `references.json` never carried a `plan_creation_sha`. ⚠ **Second occurrence** — PLAN-10 had the
  same gap on 2026-09-04, hand-verified then. Two of this epic's plans have now shipped with that
  fence unobservable, which makes it a pattern rather than an incident. — source: PLAN-07 landing paste.
