---
name: gate
description: Check a phase's exit criteria in the product ledger and, only on the owner's explicit approval, sign the gate and move the product to the next phase. Use when the owner asks whether a phase is done, wants to move on to design or development, or asks what blocks the next phase.
---

# Gate

Load the `lifecycle` skill first for the rules and commands.

1. Run `ledger.py gate <phase>` for the current phase (from `product.json`) and show every line,
   passed and open.
2. For each open line, say what would close it, and which skill or round would do that.
3. Passing every check is necessary, not sufficient: ask the owner whether the result is right.
4. Only when the owner explicitly signs:
   - in `gates.md`, set that phase's Status to `passed`, Date to today, and Note to anything they add;
   - in `product.json`, set `phase` to the next phase;
   - run `check` and `dashboard`, and commit.
5. Never sign a gate whose checks fail, even if asked. Explain what is missing instead; the owner
   can decide to drop or defer those items through Discover first.
