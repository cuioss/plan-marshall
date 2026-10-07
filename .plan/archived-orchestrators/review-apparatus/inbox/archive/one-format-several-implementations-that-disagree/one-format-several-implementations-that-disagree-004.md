envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T19:18:34Z

category=bug
component=plan-marshall:automatic-review
title=A documented empty-string default that the executor makes unreachable

## Signal

`script_failure_clusters` — `review_completeness check` rejected with exit 2 at
the pre-merge review barrier:

```text
review_completeness.py check: error: argument --measured-diff-size: expected one argument
```

The call passed `--measured-diff-size ""`, exactly as `branch-cleanup.md`
prescribes.

## The divergence

`branch-cleanup.md` § "Predicate 2" says of this scalar:

> The two lists default to the empty list and the scalar to the empty string when
> the producer emitted none … the empty fallback, never a hard failure.

And the producer legitimately emits `measured_diff_size: ""` when no size-caused
refusal occurred — which is the normal case.

But the two mechanisms that make the empty case safe for the *list* flags do not
apply to this scalar:

1. The generated executor strips every empty-string argument before argparse sees
   it (`script_args = [a for a in script_args if a]`), so `--measured-diff-size ""`
   arrives as a bare `--measured-diff-size`.
2. The list flags survive that because each declares `nargs='?'` with `const=''`.
   **`--measured-diff-size` does not** — it takes a mandatory value.

So the bare flag consumes nothing and argparse rejects. The documented "empty
fallback" is unreachable through the executor: the working form is to **omit the
flag entirely**.

The document is even aware of the hazard — it warns twice, in bold, "never rely on
quoting alone to make an empty list safe" — but the warning is scoped to the list
flags, and the scalar sitting beside them was not given the same treatment.

## The generalisable shape

Where a caller-facing document promises a default for an absent value, the promise
has to hold against the **actual invocation path**, not the parser in isolation.
Here three layers each behaved correctly on their own terms (producer emits empty,
executor strips empty, argparse requires a value) and the composition is a
rejection. Any flag documented as empty-safe needs either `nargs='?'` + `const`, or
a document that says "omit it".

## How to apply

Either give `--measured-diff-size` `nargs='?'` with `const=''` to match its
siblings, or correct `branch-cleanup.md` to say the flag is omitted when the
producer emitted no size. The first is preferable — it makes the call shape uniform
across all the barrier's flags, which is what made the divergence surprising.
