---
name: self-improvement
description: Optimize an existing agent, prompt, tool, parser, rule set, or workflow by comparing a bounded candidate against an explicit baseline. Do not use for a one-off rewrite.
---

# Self-improvement harness

## Required inputs

Identify:

- current baseline;
- target failure mode or improvement objective;
- exact invariants and no-regression conditions;
- evidence that can distinguish improvement from noise.

If the evaluation cannot distinguish the candidate from noise, record `unresolved`.

## Workflow

1. Bound the edit and avoid unrelated refactoring.
2. Preserve the baseline until the candidate is evaluated.
3. Run exact deterministic checks first.
4. Run higher-level evaluation only where exact checks are insufficient.
5. Reject critical regressions.
6. Accept only when required gates pass.
7. Record the candidate, evidence, decision, and remaining unknowns.

Do not optimize a single aggregate score while hiding a critical failure-class regression.
