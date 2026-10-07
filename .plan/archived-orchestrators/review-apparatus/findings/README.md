# Per-run review findings

One document per review run, `PR-{n}.md`, produced by this epic's recurring review practice. Written by
the orchestrator, inside its own tree.

**Cross-repo runs are `{Repo}-PR-{n}.md`** — `{n}` alone is a plan-marshall PR number everywhere in this
corpus, so a consumer-repo PR must carry its repo to avoid colliding with the plan-marshall PR of the same
number. A cross-repo document additionally states in its header whether the PR was open or merged at
analysis time, because the standing practice is a *post-merge* revisit and a pre-merge run cannot answer
§ 3 or § 4.

⛔ **Every rule — the per-bot verdicts, the baseline requirement, the back-feed question, the three
answer shapes — lives in [`../review-practice.md`](../review-practice.md), the single source of truth.
This file MUST NOT restate any of them.** It defines only the per-document section contract below.

## Section contract

Each `PR-{n}.md` carries a one-line header (epic, analysis date, evidence command and comment counts)
followed by four sections:

1. **Participation** — one row per bot: did it produce a result, and what kind.
2. **Verdict** — applying `review-practice.md` § 1, including the structural-deficit assessment and
   **whether a baseline existed at all**.
3. **Posted answers** — was every finding answered on the PR? Per `review-practice.md` § 2, a missing
   answer is itself a finding.
4. **Could we have found it ourselves?** — one row per accepted finding, answered per
   `review-practice.md` § 3.

Close with a **Feeds** list naming the plans or open actions the run informs, so a run document is
never a dead end.

## Current corpus

`PR-1055` · `PR-1057` · `PR-1058` · `PR-1059` · `PR-1061` — the five post-merge revisits taken from
`truthful-signals` on 2026-07-30 and analysed the same day.

`PR-1067` — 2026-07-30. ⭐ The richest single run so far: a rate-limit window reopening by luck and
yielding 5 real defects, a second diff-size refusal, a proven rebase invalidating the required bot, and
the merged tree (the remediation commits) reviewed by nobody. Produced the **fourth answer shape**.

`API-Sheriff-PR-133` — first cross-repo and first **pre-merge** document (2026-07-30). Sections 3 and 4
are recorded as OWED rather than answered; it feeds PLAN-PR-008 and PLAN-PR-001. ⛔ **Its central verdict
is REFUTED** (2026-08-01) and its PLAN-PR-007 feed is WITHDRAWN — read the correction banner in that file
before citing it.

`API-Sheriff-PR-138` — 2026-08-01, cross-repo, **post-merge** (`ffa8cef`). ⭐⭐ The most operationally
valuable run so far: it **refutes PLAN-PR-014's remedy while that plan is running** (the executor strips
falsy args, so quoting the placeholder is vacuous), and carries the tightest green-check-means-never-looked
evidence in the corpus (a success status set 1 second after a refusal, with a measured 4-finding
counterfactual). §§ 7 OWED.

`API-Sheriff-PR-140` — 2026-08-01, cross-repo, **pre-merge with the barrier HELD at `loop_back`**. §§ 3–4
OWED. ⭐ Carries a NEW code-verified defect (`refused_hard` is the fall-through for an undeclared
`rate_limit_class`, reported as a positive "hard quota" claim), a live PLAN-PR-008 deadlock instance, and
a refuted suspicion of the orchestrator's own recorded so it is not re-derived.

`2026-08-01-sweep-4day` — ⭐ **first AGGREGATE document: one question across a 52-PR, two-repo, four-day
window** rather than one run. Deviates from the one-document-per-run shape deliberately (see its own
header note). Carries the `API-Sheriff-PR-133` refutation, the measured PR-Agent structural deficit and
its config cause, the charter-tuning before/after measurement, and the first derived detector-widening
batch.
