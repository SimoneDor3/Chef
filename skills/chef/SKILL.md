---
name: chef
description: Shared rules for every /chef command - stages, the product folder, who decides, and the chef.py commands. Load it before running any /chef command, or when someone asks how Chef works, what stage an item is in, or where something is recorded.
user-invocable: false
---

# Chef: shared rules

Chef guides one owner from an idea to a shipped product: the MVP first, then features one at a
time. Chef does the work, shows the result and proposes the next move. **Only the owner approves.**

## Stages

Each item (`mvp`, or a feature labelled later such as `F-004`) moves one stage at a time:

`idea → discovering → scoped → designing → designed → building → shipped`

- `/chef:discover`, `/chef:design`, `/chef:build` move an item into `discovering`, `designing`,
  `building` when they start. The owner running the command is the approval.
- `/chef:approve` makes the other moves (`scoped`, `designed`, `shipped`), after the owner's yes.
- Every move goes through `chef.py stage <item> <stage>`, which refuses and lists what is missing.
  Never edit stages in `product.json` by hand.
- Features labelled MVP travel with the MVP and have no stage of their own.
- **Hard stop before code:** no product code until the item is `designed` and moved to `building`.

## The product folder (default `product/`)

`product.json` (name, stages), `vision.md`, `mvp.md`, `topics.md` (labelled MVP or later),
`questions/Q-*`, `decisions/D-*`, `features/F-*`, `toolset.json`, `design/` (`system.md` and one
file per screen with `Item` set), `build/<item>/`, `sessions/`, `dashboard.html` (generated, not
committed). Templates are in Chef's `templates/` folder.

## Branches

Each phase works on its own branch, `<phase>-<scope>`: `vision`, `discover-mvp`,
`discover-<topic>`, `discover-f-004`, `design-system`, `design-mvp`, `build-f-004`, `bug-<title>`.

- At the start of a phase: `chef.py branch <phase> [scope]`. It creates the branch from the main
  branch, or resumes it. It refuses while another phase branch is open: say which, and offer to
  merge it (on the owner's yes) or continue it.
- At the end, ask the owner to approve the result. Only on yes: `chef.py merge`. On no, the branch
  stays open and the phase goes on.
- `/chef:idea` and `/chef:status` need no branch.

## Rules

1. Propose freely (`add-decision` without `--accepted`). Accepting a decision, covering a topic,
   approving a screen or a stage needs the owner's explicit word. Silence is not a yes.
2. A question is decided only by an accepted decision that lists it under Answers.
3. Accepted decisions are never edited; a new decision supersedes them.
4. Facts about the outside world carry their source; unverified ones become questions.
5. Chef never mentions a product; `check` fails if it does.
6. **After every step:** `check`, `dashboard`, a few lines in `sessions/`, commit on the phase
   branch, then name the next move (`chef.py next`).

## Commands

The script is `scripts/chef.py` in the Chef plugin (`${CLAUDE_PLUGIN_ROOT}`). Python 3.9+, no
dependencies. Add `--dir <path>` before the command if the folder is not `./product`.

```
chef.py init --name "..."
chef.py add-topic --id sync --name "Sync" --label MVP|later --scope "..."
chef.py add-question --topic sync --title "..." --context "..." [--blocking]
chef.py add-decision --title "..." --decision "..." --why "..." --answers "Q-004" [--accepted]
chef.py accept D-007
chef.py add-feature --title "..." --label MVP|later --goal "..."
chef.py topic stack covered      # open | "in progress" | covered
chef.py drop F-007 --reason "..."  # an idea the owner turned down; the file stays
chef.py stage mvp                 # where it is, and the checks for the next move
chef.py stage mvp scoped          # move it, or refuse with what is missing
chef.py next | status | check
chef.py dashboard [--open]
chef.py deps | settings           # used by /chef:vision
chef.py branch discover sync      # start or resume discover-sync
chef.py merge                     # merge the open phase branch, on the owner's yes
```

## How to talk to the owner

One question at a time, with two to four concrete options and your recommendation. Plain words.
End every step with the next move.
