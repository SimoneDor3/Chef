---
name: build
description: Chef's build loop for the MVP or a feature - plan approved by the owner, then failing tests, code slice by slice, verification and independent reviews, and a summary for sign-off. Use when an item's design is approved and the owner wants it built, or to resume a build.
argument-hint: "<mvp | feature>"
---

# /chef:build

Load the `chef` skill first. Item: $ARGUMENTS.

## Start

1. If the item is `designed`, run `chef.py stage <item> building`. If refused, say what is
   missing and stop. If it is already `building`, resume from `build/<item>/`.
2. Switch Ponytail on: `/ponytail full`. From then on it reaches every Build agent.
3. Map the code with Graphify (code only) and refresh it after each commit. Agents query it
   instead of reading files.
4. Read `toolset.json`: it names the stack's test skills, pattern skills, reviewer and build-fix agent.

## The loop

```
PLAN    planner: slices, order, risks, model per role       ▶ owner approves
TESTS   tester writes failing tests from the acceptance criteria
BUILD   builder makes them pass, one slice at a time
VERIFY  tester runs everything, adds edge cases         ─┐ problems go back to BUILD;
REVIEW  reviewers in parallel, independent of builder   ─┘ after 3 rounds the owner decides
DONE    summary ▶ owner approves ▶ commit
```

| Role | Agent | Model |
|---|---|---|
| Planner | ECC `planner` (+ `architect` for structural changes) | the strongest |
| Tester | ECC `tdd-guide` with the test skills from `toolset.json` | planner's choice |
| Builder | a builder agent with the pattern skills; the build-fix agent when builds break | planner's choice |
| Security | ECC `security-reviewer`, every slice | strong |
| Code | Ponytail `ponytail-review` | planner's choice |
| Language | the reviewer named in `toolset.json` | planner's choice |
| Extra | ECC `pr-test-analyzer`, `silent-failure-hunter`, `database-reviewer`, `a11y-architect` when the planner flags a need | planner's choice |

- Write the plan to `build/<item>/plan.md` and wait for the owner's yes before any test or code.
- Reviewers flag defects, not missing abstractions. The planner settles disagreements.
- Commit after each green, reviewed slice. Keep test and review reports in `build/<item>/`.

## Done

1. Write `build/<item>/summary.md` from `templates/build-summary.md`: what was built, tests and
   reviews, cost, shortcuts taken.
2. Switch Ponytail off: `/ponytail off`.
3. Next move: `/chef:approve <item>` to mark it shipped.
