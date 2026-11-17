---
name: vision
description: Start a product with Chef - check dependencies, write project settings, create the product folder, write the vision with the owner, and build the first dashboard. Use when the owner starts a new product or wants to rewrite its vision.
argument-hint: "<brief>"
---

# /chef:vision

Load the `chef` skill first. The owner's brief: $ARGUMENTS

1. **Dependencies.** Run `chef.py deps`. Show what is missing and how to install it. Missing
   pieces are a warning, not a stop: Ponytail and Graphify are only needed at Build.
2. **Settings.** Run `chef.py settings` and say in one line what it changed (Ponytail off by
   default; GateGuard skips the product folder).
3. **Folder.** If there is no `product/product.json`, agree the name and run `chef.py init`.
4. **Vision.** Read the brief and anything the owner points to. Then go through `vision.md` one
   section at a time: propose a draft, let the owner correct it. Anything they cannot answer yet
   becomes a question, not a guess.
5. When every section is filled, run `check` and `dashboard --open`, write a session note, commit.
6. Next move: `/chef:discover mvp`.
