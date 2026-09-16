---
name: repo-research
description: Map an unfamiliar repository or upstream specification before implementation, using targeted evidence and a concise handoff.
metadata:
  short-description: Investigate a codebase before coding
---

# Repository research

1. Restate the bounded research question and the decision it supports.
2. Read the nearest `AGENTS.md`, relevant specs, package manifests, entry points, and tests.
3. Use targeted file listing/search rather than whole-repository dumps.
4. Separate facts from hypotheses and retain path/line evidence where practical.
5. Stop when the implementation decision is supported; report unknowns instead of expanding indefinitely.
6. Research is read-only unless the user separately requests implementation.
