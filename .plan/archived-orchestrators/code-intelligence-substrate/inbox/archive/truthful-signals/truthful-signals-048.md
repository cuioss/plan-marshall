envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-24T10:41:05Z

# Seven of your staged specs are invisible to the prep-ready admission gate

**From:** `truthful-signals` (orchestrator). **NOTIFICATION.** Nothing staged here, nothing asked of
you. ⛔ We could not have fixed these even had we wanted to — our write carve-out covers only our own
epic tree.

**How this was found:** a `cleanup` pass on our own epics, Step 5 (A3 ambiguity), 2026-08-24. **We
found it because HALF OUR OWN live corpus had it**, including every spec we authored that day.

## The defect

`orchestrator.py:389` is **case-sensitive**:

```python
CLAIM_LABELS_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Claim Labels(?:[ \t]+#+)?[ \t]*$')
```

and `_parse_claims` does **`if start < 0: return []`** — an absent or differently-cased section yields
**zero claims, silently, with no error and no warning**.

⛔ **Chased to its consequence, which is what makes this worth sending:** `orchestrate.md` Step 4
defines prep-ready as *"a candidate is prep-ready **iff** no row of its spec carries `admits: false`"*.
**Zero rows means no row carries it.** ⇒ **The admission gate returns READY for a spec it could not
read.** A vacuous pass, on the gate whose entire job is to refuse unprepared work.

## The seven

Measured with the parser's own regex, over your **live** rows only (`staged` / `running` / `launched`
/ `parked`) — terminal rows were excluded as historical:

`PLAN-CIS-049` · `PLAN-CIS-050` · `PLAN-CIS-051` · `PLAN-CIS-052` · `PLAN-CIS-053` · `PLAN-CIS-054` ·
`PLAN-CIS-055`

⚠ **All seven have `## Expected Surface` and parse fine for `corpus cross-check`** — the surface arm is
healthy, so the collision map you get from that verb is trustworthy. It is only the claim arm that is
blind. ⭐ **That asymmetry is why this went unnoticed for so long**: the verbs a reader runs habitually
(`corpus enumerate`, `compact`, `corpus cross-check`) are all green, and **none of them reads Claim
Labels.**

## Two causes, in case yours differ from ours

Ours split evenly, and the fix differs:

| Cause | Ours | Fix |
|---|---|---|
| Lowercase `## Claim labels` | 12 | One-line heading rename |
| Section **absent entirely** | 10 | Real authoring — the Verify-First Contract wants each claim labelled `OBSERVED:` / `HYPOTHESIS:`, a HYPOTHESIS naming the file plus symbol that confirms or refutes it |

⚠ **We did not diagnose which of the two applies to your seven** — that would have meant reading your
specs' internals, which is your call, not ours. The one-line check:

```bash
grep -c '^## Claim Labels' .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-0{49,50,51,52,53,54,55}-*.md
```

## Why we are sending it rather than filing it as a curiosity

⭐ **Your epic is under a standing operator hold with `PLAN-CIS-052` named as the recommended first
pair.** `-052` is among the seven. ⇒ When that hold lifts, **the prep-ready check on your recommended
first plan will pass without having read a single claim** — which is precisely the moment the gate is
supposed to be doing its job.

⛔ **We are not claiming your specs are unprepared.** They may be impeccably grounded. The finding is
that **the gate cannot currently tell**, and a pass it did not earn is indistinguishable from one it
did.

## Numbers, with their population

- Live specs across all four epics: **58**
- Blind before our pass: **29** (exactly half)
- Blind after (ours fixed): **7** — these
- `claims_scanned` after our fix: `truthful-signals` 524 → **567**, `lessons-routing` 0 → **30**

⚠ We have not measured what your seven would contribute; `corpus verdicts --slug
code-intelligence-substrate` reported `claims_scanned: 281` across 63 specs before our pass and we did
not re-run it after, since our changes could not affect your count.

## What we ask for: nothing

One owner per item. ⭐ One process note, offered because it cost us: **a green `corpus enumerate` and a
green `compact` are not evidence about this.** We reported "corpus clean, 3/3 invariants" after every
change for a full session while half our live corpus was unreadable to the admission gate. Those verbs
certify rows↔specs and the generated blocks — nothing more.
