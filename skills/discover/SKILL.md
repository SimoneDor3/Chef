---
name: discover
description: Run a Chef discovery conversation on the MVP, a feature, or one topic - one question at a time with options and a recommendation, recording decisions, questions, features and MVP-or-later labels. Use when the owner wants to settle what the MVP or a feature is, or to work through open questions.
argument-hint: "<mvp | feature | topic>"
---

# /chef:discover

Load the `chef` skill first. Target: $ARGUMENTS (default: what `chef.py next` suggests).

## Start

- **An item** (`mvp` or `F-001`) at `idea`: run `chef.py stage <item> discovering`. If refused,
  say what is missing and stop.
- **A topic**: set it to `in progress` in `topics.md`.
- Read `chef.py status`, the vision, `mvp.md` and the files involved. Summarise what is known.
- If a decision is waiting for the owner, settle it first.

## `mvp`

Settle, one at a time: the MVP's goal, its must-have features, what is out, how success is
measured. Write `mvp.md` as you go. Every area that comes up becomes a topic with
`add-topic --label MVP|later`; every feature becomes `add-feature --label MVP|later`.
**The tech stack is a required MVP topic.**

## A topic or a feature

Take its questions one at a time, blocking ones first. For each: say it plainly and why it
matters; give what is known, with sources (look facts up before asking); offer two to four
options and recommend one. Record straight away:

- owner chose: `add-decision ... --answers Q-NNN --accepted --source "owner, YYYY-MM-DD"`;
- owner leaning: `add-decision` without `--accepted`;
- new uncertainty: `add-question`; no longer relevant: Status `dropped` with a reason.

Features get acceptance criteria as `- **AC-001** Given ..., when ..., then ...`.

## The stack decision

When the stack is decided, write `toolset.json`: the stack, its test tools, and the ECC agents and
skills that fit it (pattern skills, test skills, the language reviewer, the build-fix agent).
Check every name against the installed ECC plugin. Example:

```json
{"stack": ["python", "fastapi"], "tests": ["pytest"],
 "ecc": {"reviewer": "python-reviewer", "build_fix": "build-error-resolver",
         "skills": ["python-patterns", "python-testing", "fastapi-patterns"]}}
```

## End

Keep a round to six to eight questions. Mark a topic `covered` only with the owner's yes and
nothing open in it. Then: `check`, `dashboard`, session note, commit, next move (usually the
next MVP topic, or `/chef:approve mvp` when `chef.py stage mvp` shows every check PASS).
