envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=truthful-signals
kind=finding
created=2026-08-02T13:48:51Z

# `orchestrator inbox` has no amend verb, so correcting a filed message requires a hard-rule bypass — and leaves no trace that it happened

**Source**: encountered live in this session while filing
`truthful-signals/inbox/barrier-override-not-head-bound-001.md`, which was written without a
usable provenance reference and had to be corrected after filing.

## The gap

`orchestrator inbox` exposes exactly four operational verbs plus a classifier:

```text
{write, validate, list, archive, detect}
```

`write` appends a NEW `{sender_id}-{NNN}.md`. There is no verb that changes the body of a message
already written. So a message discovered to be wrong or incomplete after filing has only two
routes, and **both are defective**:

1. **Write a successor** (`-002`) and leave `-001` queued. The queue now holds two messages, both
   validating green, with no relation between them. `inbox list` reports them as two independent
   items; nothing marks one as superseded by the other.
2. **Edit the file directly** — which violates the standing `.plan/` access hard rule
   ("ALL `.plan/` file access MUST go through `execute-script.py` manage-* scripts"). It worked
   here only because the operator explicitly authorized it for this one edit. That authorization
   is not generally available, and a contract that is only satisfiable by bypassing another
   contract is not a usable contract.

⛔ **`archive` is NOT the missing verb, and using it as one would lie.** `archive` means
*consumed* — it retires a message the orchestrator has acted on. Retiring an erroneous message
through it would record "consumed" about a message nobody ever acted on, corrupting exactly the
signal the archive exists to carry. Retiring-because-wrong and retiring-because-done are
different facts and need different verbs.

## The signal half (why this belongs to this epic)

The envelope carries `created` and no amendment marker:

```text
envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=truthful-signals
kind=finding
created=2026-08-02T13:42:19Z
```

`barrier-override-not-head-bound-001.md` was materially rewritten AFTER that timestamp — a whole
provenance section was inserted and two artifact pointers were re-anchored — and the envelope is
byte-identical to how it would look had none of that happened. `inbox validate` returns
`status: success` on both the original and the amended form.

⭐ So a post-filing mutation is **structurally invisible**: `created` reads as a fact about the
content, but after an edit it describes only the content's first version. A reader diffing two
epics' inboxes, or an audit reconstructing when a claim entered the ledger, has no way to
distinguish a message filed once from one rewritten hours later. That is the epic's archetype —
a field that is not wrong, but that quietly stops meaning what its name says.

## The sibling surface already solved this

`manage-lessons` carries `supersede` + `cleanup-superseded` + `.tombstones/{id}.json`, so a
lesson that is replaced leaves a resolvable tombstone and the id keeps resolving. The inbox
surface has the *consumed* half (`archive`) and not the *replaced* half. The asymmetry looks
accidental rather than designed — the same corpus problem was recognised and solved one skill
over.

## Candidate remedies (the epic decides; both close the gap)

1. **`inbox amend --slug --message --payload-file`** — replaces the body in place, PRESERVES
   `created`, and stamps `amended` plus a monotonic `revision` in the envelope. `validate` then
   asserts revision monotonicity, and `list` can surface `rev>1` so an amended message is visibly
   different from a virgin one.
2. **`inbox supersede --slug --message --by {successor_id}`** — mirrors the lessons tombstone
   model: the original is marked superseded (a state distinct from archived) and names its
   successor, so the queue stops presenting both as live while the original stays resolvable.

⚠ **Whichever is chosen, the envelope MUST gain a field that makes post-filing mutation visible.**
That is the load-bearing half. A verb that edits the body but leaves the envelope unchanged
replaces an authorized bypass with an unauthorized one and fixes nothing about the signal.

⛔ **Prohibited remedy**: do NOT close this by carving inbox messages out of the `.plan/`
scripts-only rule. The rule is what keeps the store machine-readable and schema-valid; the defect
is the missing verb, not the rule.

## Confirm/refute artifacts

- `python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox --help`
  — enumerates the five subcommands, no amend/supersede among them.
- `.plan/local/orchestrator/truthful-signals/inbox/barrier-override-not-head-bound-001.md` —
  carries `created=2026-08-02T13:42:19Z`, contains a `## Provenance — the evidence root` section
  added after that timestamp, and no marker recording the amendment.
- Sibling contrast: `manage-lessons` § `supersede` / `cleanup-superseded` and the
  `.tombstones/{id}.json` records.

## Scope note

This is a **surface gap, not a bug in a predicate** — nothing currently mis-reports. The failure
it enables is prospective: the next filer without an operator standing over them either dirties
the queue with an uncorrected message or silently breaks the access rule. Sizing it as small is
reasonable; leaving it unlogged is not, because the workaround used here (direct edit) will not
be available next time.
