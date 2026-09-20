# Harness architecture

Gemma-Jev uses the same separation of responsibilities as the source `codex-dev-harness`.

## Layers

1. **Operating rules — `AGENTS.md`**
   - small always-on invariants and routing.
2. **Task skills — `skills/*/SKILL.md`**
   - detailed procedures loaded only when their trigger applies.
3. **Project baseline — `docs/project-baseline.md`**
   - reproducibility, CI, Python quality gates, and specification conventions.
4. **Canonical specifications — `docs/specs/`**
   - current durable requirements and externally meaningful behavior.
5. **Mechanical enforcement — tests and CI**
   - stable invariants enforced without relying on model judgment.

## Task contract

Before implementation, identify the requested outcome, required acceptance criteria, and the evidence that can establish each criterion.

Verification evidence is not equivalent to completion. Green tests do not establish an objective they do not measure.

For reviewable work, preserve a concise mapping:

`criterion -> implementation/change -> evidence`

The PR description is the preferred location for this mapping.

## Evaluation result

Evaluation is separate from execution. Record raw evidence before deciding whether a change is acceptable.

An evaluation should capture, as applicable:

- exact checks and test results;
- primary and secondary metrics;
- failure categories;
- critical no-regression conditions;
- sample count and uncertainty for empirical evaluation;
- evaluator/tool version when material;
- `accept`, `reject`, or `unresolved`.

If evidence is insufficient, use `unresolved` rather than converting uncertainty into success.

## Change gate

Before adopting an agent-generated improvement:

1. record the baseline;
2. define target failure mode, scope, objective, and acceptance conditions;
3. implement a bounded candidate;
4. run deterministic checks first;
5. run the relevant higher-level evaluation;
6. reject critical regressions;
7. merge only after required gates pass.

Iteration count is not evidence of improvement.
