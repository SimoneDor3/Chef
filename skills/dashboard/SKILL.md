---
name: dashboard
description: Build the product dashboard - an HTML page showing the current phase, gate checks, topics, open questions, decisions waiting for the owner, and what has been decided. Use when the owner wants an overview of where the product stands.
---

# Dashboard

1. Run `chef.py check` and fix any problem it reports first.
2. Run `chef.py dashboard`. It writes `dashboard.html` in the product folder.
3. Show it: open it in the owner's browser if you run on their machine, or publish it as a page
   if the environment offers that. Otherwise give its path.
4. Summarise in three lines: phase, what blocks the gate, and the next useful round.
