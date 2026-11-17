---
name: idea
description: Chef's inbox - capture an idea or change request as a later feature and help the owner decide whether it is worth a discovery. Use when the owner has a new idea, feature request or change of mind.
argument-hint: "<text>"
---

# /chef:idea

Load the `chef` skill first. The idea: $ARGUMENTS

1. Check it is new: search `features/`, `topics.md` and decisions. If it changes an accepted
   decision, say which one; discovery will need a decision that supersedes it.
2. Restate it in one sentence: who gets what, and why it matters.
3. Capture it: `chef.py add-feature --title "..." --label later --goal "..."`. Ideas never enter
   the MVP this way; that takes `/chef:discover mvp`.
4. Help decide: value for the people in the vision, rough size, risk, what it depends on. Offer:
   discover it now, park it (it waits at `idea`), or drop it
   (`chef.py drop F-NNN --reason "..."`; the file stays so its id is never reused).
5. `check`, `dashboard`, commit, next move.
