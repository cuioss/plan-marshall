envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:14Z

component=plan-marshall:tools-script-executor
category=anti-pattern
bundle=plan-marshall

# Quoting an empty placeholder can never fix an argparse crash — the executor strips empty args before argparse runs

The generated executor removes every empty-string argument from the argv it forwards:

```python
script_args = [a for a in script_args if a]   # .plan/execute-script.py:989
```

Consequence: `--flag ""` and a bare `--flag` are **indistinguishable** downstream. A flag that argparse declares as requiring a value therefore raises `exit_code: 2` in both cases, and no amount of quoting at the call site changes the argv argparse actually sees.

This defect class was diagnosed wrongly at spec time on plan `crashed-participation-gate-records-a-pass`. The spec's root-cause story named the unquoted placeholder as the cause and framed quoting and the parser relaxation as **complementary defences**. Both claims are false. The plan's own first-pass self-review callouts repeated the wrong story before it was corrected in commit `5d10ad536`.

## Solution

For any optional list-style flag that a call site may interpolate with an empty value, relax the **parser**:

```python
parser.add_argument("--reviewers", nargs="?", const="")
```

Quoting the call site is cosmetic hygiene, not a fix, and MUST NOT be described as a defence-in-depth layer against this crash. Describing it that way is what makes the defect reintroducible: an author who trusts the old text adds a list flag, quotes it, skips `nargs`, and gets the same exit-2.

## Impact

Applies to every marketplace script reached through `.plan/execute-script.py`. The strip is global and unconditional, so the exposure is a property of the executor, not of any one parser. Any doc, spec, or review comment that attributes an empty-flag exit-2 to missing quotes is wrong and should be corrected at the source rather than worked around at the call site.
