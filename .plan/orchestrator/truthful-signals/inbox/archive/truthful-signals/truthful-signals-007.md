envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-29T17:37:11Z

## `absent` means two things with opposite remedies, and reports the alarming one

### Relation to the other messages in this cluster

Third defect under the generalisation opened in `-006`. That message covered two detectors watching
the wrong observable. This one is a **classifier**: the observable is read correctly, the gate decision
is correct, and the *label* on the outcome is false in a way that sends the reader to the wrong repair.

It is NOT fixed by either remedy in `-006`. Both of those aim to produce a fresh review; this defect
survives a fresh review being produced, because it concerns how a *stale* one is named.

### Observed — plan-marshall#1059, 2026-07-29

The finalize report stated `pr-agent: absent` and the operator's summary led with "especially the
absent pr-agent". Both are false. Evidence:

| Fact | Value |
|---|---|
| Workflow run | `30466587421`, event `pull_request`, conclusion **success** |
| Step `Verify the reviewer actually produced a review` | **success** — the org fail-closed guard passed |
| Comment | `cuioss-review-bot[bot]`, "PR Reviewer Guide 🔍", created **15:36:44Z**, never updated |
| Reviewed HEAD | `acbdcecf3` |
| Final HEAD at merge | `cf634762`, committed **16:51:40Z** |

pr-agent ran, reviewed, and published — 75 minutes before the rebase that produced the merge candidate.
Its registry sets `participation_requires_update: true` (it re-reviews by editing one persistent Guide
comment in place), the `updated_at` never moved, so participation was correctly **not** credited.

**The gate was right. The word was wrong.**

### The contract contradicts itself in one table

`automatic-review/standards/bot-participation-contract.md`:

- Line 56 defines the member: *"`absent` | No comment posted and no completion check-run observed; the
  review window closed with nothing. | **The bot never engaged at all.**"*
- Line 98 routes a different case to the same member: a bot that cannot be *proven* a participant
  *"is reported as `absent` rather than silently credited"*.
- Line 81 names the case explicitly as one of the things presence does not prove: *"a **stale comment
  tied to a prior HEAD**"*.

So one member carries two states whose conditions are mutually exclusive — one requires no comment,
the other is reached only when a comment exists. The taxonomy declares itself closed ("every
non-participation resolves to one of these"), and it is not: `stale` is a real, common state with no
member of its own, so it lands on the member whose remedy is maximally wrong.

### Why the conflation is expensive, not cosmetic

The two states demand opposite operator responses:

- **never ran** → investigate the App install, the credentials, the caller workflow, the org config.
  This is an infrastructure incident.
- **ran, published, then the diff moved underneath it** → the reviewer is healthy. The defect is
  step *ordering*, and the fix is a re-trigger, not an investigation.

Reporting the second as the first re-opens a question that is settled, against a bot whose reliability
was the explicit subject of the preceding two days of work. On #1059 it did exactly that: the report
led with it, and disproving it took four tool calls against the GitHub API.

Note also that `absent` currently defends itself as *"the fail-closed default"*. It is not being
fail-closed here — the closed outcome (do not credit participation) is right either way. Only the
*name* differs, and naming is precisely where the fail-closed argument does not apply: there is no
safety gained by describing a healthy reviewer as one that never engaged.

### Why it will recur on the common path, not an edge case

Nothing is misconfigured. After #1053, pr-agent is subscribed to `opened` / `reopened` /
`ready_for_review` only — a rebase is invisible to it. And `finalize-step-sync-baseline` rebases and
force-pushes as part of every finalize, *after* the PR-open review. So the plan flow's own step
ordering guarantees that any PR needing a rebase ends with a stale pr-agent Guide and a false `absent`.
#1059 rebased onto 4 upstream commits. This is the normal path.

### Remedy

Add a sixth member — `stale` (or `participated_stale`) — for the case where an admissible publish
shape exists but fails the `participation_requires_update` / HEAD-currency test. It must gate exactly
as `absent` does today (it is not participation, and it must not be creditable), so this is a
reporting-fidelity change with no change to any merge verdict.

The distinguishing evidence is already in hand at classification time: the comment was observed, its
`kind` matched a declared `participation_evidence` shape, and only the currency test failed. Today
that information is discarded on the way to `absent`.

⛔ Do not fix this by crediting stale participation, and do not soften the gate. The failure here is
that a correct refusal was *described* as an infrastructure absence. Widening what counts as
participation would trade a misleading label for an unsound gate, which is the failure mode this epic
is named after.

### Acceptance

- A bot with an admissible publish shape whose comment predates `head_at_completion` classifies to the
  new stale member, not `absent`; a bot with no comment at all still classifies `absent`.
- Both members gate identically for a required bot — no merge verdict changes; a test pins that
  equivalence so a later reader cannot mistake the new member for a softened gate.
- `bot-participation-contract.md` line 56's *"never engaged at all"* becomes true of `absent` again,
  and the taxonomy's closure claim becomes accurate.
- Coverage uses the #1059 shape: review published at PR-open, HEAD advanced by a later rebase.
