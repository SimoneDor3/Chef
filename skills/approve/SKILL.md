---
name: approve
description: Ask the owner to approve the MVP or a feature into its next stage (scoped, designed or shipped) - show a recap, ask yes or no, and move it only if Chef's checks pass. Use when the owner wants to lock scope, lock design, or sign off a build.
argument-hint: "<mvp | feature>"
---

# /chef:approve

Load the `chef` skill first. Item: $ARGUMENTS (default: the item `chef.py next` names).

1. Run `chef.py stage <item>`. If the next stage is one a command starts (discovering,
   designing, building), say which command to run instead and stop.
2. If any check is OPEN, show each with what would close it and which command does that. Stop:
   never approve past a failing check, even if asked.
3. Show a short recap of what is being locked:
   - **scoped:** goal, features in and out with their acceptance criteria, the stack, what is later;
   - **designed:** the design system and every screen, with links to the mockups;
   - **shipped:** the build summary: what was built, tests and reviews, cost, shortcuts taken.
4. Ask one plain yes or no. Only on yes: `chef.py stage <item> <next>`.
5. `check`, `dashboard`, session note, commit (the message names the item and stage), and if a phase
   branch is open, `chef.py merge`. Next move.
