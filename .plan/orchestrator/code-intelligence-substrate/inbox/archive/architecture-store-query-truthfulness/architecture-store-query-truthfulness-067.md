envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T08:01:17Z

component: plan-marshall
category: insight
# Owed architecture hint: bug findings as a standing consideration in plan-marshall

Target module: `plan-marshall`
Enrich verb: `insight`
Generalized hint: "the project treats bug findings as a standing consideration in plan-marshall"

Derived from a within-plan recurrence (count 2, threshold 2) of `taken_into_account`
dispositions on `bug`-type findings attributed to module `plan-marshall`, in plan
`architecture-store-query-truthfulness`. Owed call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module plan-marshall --insight "the project treats bug findings as a standing consideration in plan-marshall"
```
