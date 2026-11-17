---
name: status
description: Where a Chef product stands - stages, what waits on the owner, the suggested next move - and rebuild and open the offline dashboard. Use when the owner asks where things are, what is next, or says "continue".
---

# /chef:status

Load the `chef` skill first.

1. Run `chef.py check`. Fix any problem it reports, or show it to the owner if fixing needs them.
2. Run `chef.py dashboard --open`. It is a local file and is never published. If you are not on
   the owner's machine, give its path instead.
3. Run `chef.py status` and read the latest note in `sessions/`.
4. Answer in a few lines: where the MVP and each feature stand, what waits on the owner, and the
   next move. On "continue", start that move.
