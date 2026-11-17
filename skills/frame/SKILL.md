---
name: frame
description: Run phase 1 of the product lifecycle - interview the owner to fill in vision.md (problem, people, promise, experience, non-goals, constraints, success) and seed the first open questions. Use when starting a new product, or when the vision needs rewriting.
---

# Frame

Load the `lifecycle` skill first for the rules and commands.

1. If there is no product folder, ask the owner for the product name, then run
   `ledger.py init --name "<name>"`.
2. Read whatever already exists: `vision.md`, notes the owner points to, earlier documents.
   Summarise what you already know before asking anything.
3. Go through `vision.md` one section at a time. For each, propose a draft from what you know and
   ask the owner to correct it. Ask at most three questions at once, and prefer offering concrete
   options to open-ended questions.
4. Anything the owner cannot answer yet becomes a question (`add-question`), not a guess in the
   vision. Mark it blocking if later phases depend on it.
5. When every section is filled, run `ledger.py gate frame` and show the result. If the owner
   signs, use the `gate` skill to record it.
6. Run `check` and `dashboard`, and commit.
