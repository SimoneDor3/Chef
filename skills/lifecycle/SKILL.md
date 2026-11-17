---
name: lifecycle
description: Reference for the product lifecycle kit - phases, gates, ledger files, rules and commands. Load it before running any other skill of this kit, or when someone asks how a product is planned, what phase it is in, where a decision is recorded, or how a change request enters the process.
---

# Product lifecycle

A product moves through four phases. Each ends at a gate that only the owner can sign.

| Phase | Purpose | Leaves when |
|---|---|---|
| 1. Frame | Agree what the product is: problem, people, promise, non-goals | every section of `vision.md` is filled in and signed |
| 2. Discover | Turn every open point into a decision, through discussion rounds | all topics covered, no blocking question open, no decision waiting, features have acceptance criteria, journeys and data sources written |
| 3. Design | Mockups for every journey, design system, copy | every screen approved |
| 4. Build & maintain | Build from the approved design, release, then maintain | per release, owner sign-off |

Nothing in a later phase starts early. In particular **no product code is written before the
Design gate is signed**. Throwaway spikes to answer a question are allowed; they live in
`spikes/`, are named after the question they answer, and never ship.

## The ledger

All state lives in plain files in the product folder (default `product/`):

- `vision.md`: the framing.
- `topics.md`: the areas Discover must cover. Status is `open`, `in progress` or `covered`.
- `questions/Q-NNN-*.md`: one open point each. Status `open`, `discussing` (a proposal exists),
  `decided` or `dropped`. `Blocking: yes` means the Discover gate cannot pass while it is open.
- `decisions/D-NNN-*.md`: one answer each. Status `proposed`, `accepted`, `superseded` or `rejected`.
- `features/F-NNN-*.md`, `journeys/`, `data-sources/`, `design/`: the specifications.
- `sessions/`: notes from each discussion round.
- `gates.md`: the owner's sign-off per phase. `product.json`: name and current phase.
- `dashboard.html`: generated. Never edit it.

Templates for every file type are in this kit's `templates/` folder.

## Rules

1. **Only the owner decides.** You may propose (`add-decision` without `--accepted`). Accepting
   a decision, covering a topic, signing a gate and changing the phase need the owner's explicit
   word in the conversation. "Sounds good" about an option counts; silence does not.
2. **A question is decided only by an accepted decision** that lists it under Answers.
3. **Decisions are never edited after acceptance.** To change one, record a new decision that
   supersedes it, and mark the old one `superseded`.
4. **Facts carry their source.** Anything about an external system (an API, a licence, a price)
   states where it was verified. Unverified claims are labelled as such and usually become a
   question or a spike.
5. **Keep the kit and the product apart.** The kit folder never mentions a product. `check`
   fails if it does, so the kit can be extracted and reused.
6. **After every change**, run `check`, regenerate the dashboard, and commit.

## Maintenance loop

After launch, every new idea, bug that changes behaviour, or change of mind enters at Discover:
record it as questions, run a short round, accept decisions, update features and design, then
build. Small fixes that change no decided behaviour skip straight to Build.

## Commands

The script is `scripts/ledger.py` in this kit (two folders up from this file). It needs only Python 3.9+.

```
python <kit>/scripts/ledger.py status
python <kit>/scripts/ledger.py add-question --topic data --title "..." --context "..." [--blocking]
python <kit>/scripts/ledger.py add-decision --title "..." --decision "..." --why "..." --answers "Q-004" [--accepted]
python <kit>/scripts/ledger.py accept D-007
python <kit>/scripts/ledger.py gate discover
python <kit>/scripts/ledger.py check
python <kit>/scripts/ledger.py dashboard
```

Add `--dir path` before the command if the product folder is not `./product`.

## Skills in this kit

- `frame`: run phase 1.
- `discover`: run one discussion round on one topic.
- `gate`: check a phase's exit criteria and record the owner's sign-off.
- `dashboard`: build and show the overview page.

Design and Build skills are not part of the kit yet. Until they are, Design uses the
`design:*` skills and an approve-in-browser review (ECC `plan-canvas`), and Build uses a
development factory or ECC `orch-*`, fed from the accepted features.

## Other skills worth using

| Phase | Skills |
|---|---|
| Frame, Discover | ECC `product-lens`, `product-capability`, `council` and `dev-team` (several viewpoints), `deep-research`, `market-research`, `intent-driven-development` (acceptance criteria), `architecture-decision-records` |
| Design | `design:design-system`, `design:ux-copy`, `design:user-research`, `design:design-critique`, `design:accessibility-review`, ECC `frontend-design-direction`, `plan-canvas` |
| Build | ECC language reviewers, `tdd-workflow`, `security-review`, `orch-*` |
