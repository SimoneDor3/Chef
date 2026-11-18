# Chef: design

Status: **approved by the owner on 2026-11-17.** Being built; see the roadmap at the end.

## What Chef is

Chef guides one person, working with Claude Code, from a product idea to a shipped and
maintained product. Think of a home cook following a recipe book: you prepare the base first
(the MVP), then add the sides one at a time (features), at your own pace. ECC is the drawer of
kitchen tools. Chef is the recipe book and the cook beside you.

## Principles

1. **Guided, never autopilot.** Chef always knows the current stage, does the work, shows the
   result and proposes the next move. Only the owner approves.
2. **One conversation can carry the whole flow**, but nothing lives only in the conversation.
   Every step is written to small files, so any new session resumes with "continue".
3. **Visual from the first minute.** A dashboard exists from `/chef:vision` onwards and is
   rebuilt after every step. It is a local HTML file, opened on demand, never hosted anywhere.
4. **MVP first, then feature by feature.** Incremental work only starts once a base exists.
5. **Hard stop before code.** No product code until the MVP's scope and design are approved.
   Every other step can warn instead of block.
6. **Cost matters.** The strongest model only where judgement matters; everything else is chosen
   per task. Ponytail during Build, Graphify for reading code.

## The flow

```
/chef:vision <brief>
   └─▶ /chef:discover mvp ─▶ topics labelled MVP or later ─▶ /chef:discover <topic> ...
          └─▶ /chef:approve mvp            (scope locked: features with acceptance criteria)
                 └─▶ /chef:design system ─▶ /chef:design mvp
                        └─▶ /chef:approve mvp        (design locked)
                               └─▶ /chef:build mvp   (plan ▶ your yes ▶ build loop, slice by slice)
                                      └─▶ shipped. From here, feature by feature:
/chef:idea <text> ─▶ /chef:discover <feature> ─▶ approve ─▶ design ─▶ approve ─▶ build ─▶ shipped
/chef:bug <text>  ─▶ build (unless the fix changes a decided behaviour: then it becomes an idea)
```

Each item (the MVP or a feature) moves through these stages, one step per approval:

`idea → discovering → scoped → designing → designed → building → shipped`

Starting `/chef:discover`, `/chef:design` or `/chef:build` on an item moves it into the working
stage (`discovering`, `designing`, `building`); the owner running the command is the approval.
`/chef:approve` makes the other moves (`scoped`, `designed`, `shipped`). Every move is checked by
`chef.py` and refused, with the reason, if something required is missing. Features labelled MVP
travel with the MVP and have no stage of their own.

Anything labelled **later** is parked with its notes, never lost, and does not block the MVP.
An idea the owner turns down is dropped: it leaves the stages but its file and id stay.

## Commands

All commands accept a target: `mvp`, a feature, or (for discover) a topic.

| Command | Does |
|---|---|
| `/chef:vision <brief>` | Starts a product: writes the vision, creates the product folder and the first dashboard, checks dependencies |
| `/chef:discover <mvp \| feature \| topic>` | A conversation, one question at a time with options and a recommendation; records decisions and labels everything MVP or later |
| `/chef:approve <mvp \| feature>` | Shows a recap, asks yes or no, and moves the item one stage on. Refuses if something required is missing, and says what |
| `/chef:design <system \| mvp \| feature>` | Design system first, then screens per journey; reviewed in the browser |
| `/chef:build <mvp \| feature>` | Runs the build loop below |
| `/chef:idea <text>` | Inbox: captures an idea or change request and helps decide whether it is worth a discovery |
| `/chef:bug <text>` | Short path from a bug to a fix |
| `/chef:status` | Where things stand, what waits on the owner, the suggested next move; rebuilds and opens the dashboard |

The conversation is the main interface: commands are shortcuts to start or resume. Every step
ends by naming the next one.

## The product folder

Plain markdown, small files, versioned in the product's own repository.

| Path | Holds |
|---|---|
| `product.json` | name, and the stage of the MVP and of each feature |
| `vision.md` | problem, people, promise, experience, non-goals, constraints, success |
| `mvp.md` | the MVP: goal, what is in, what is out, how we know it works |
| `topics.md` | areas to discuss, each labelled MVP or later, with status |
| `questions/Q-001-*.md` | one open point each |
| `decisions/D-001-*.md` | one answer each; accepted decisions are never edited, only superseded |
| `features/F-001-*.md` | goal, scope, acceptance criteria, label, stage |
| `toolset.json` | the stack and the ECC agents and skills that fit it; approved with the MVP |
| `design/` | the design system and one file per screen, linked to its mockup |
| `build/F-001/` | the plan (slices, risks, models), test and review reports, per feature |
| `sessions/` | a few lines per working session, so the next one can resume |
| `dashboard.html` | generated; never edited; not committed |

IDs (`Q-`, `D-`, `F-` plus three digits) never change and are never reused.

## Discovery

`/chef:discover mvp` always comes first after the vision. It settles the MVP's goal, its
must-have features, what is out, and how success is measured. Every topic it surfaces is labelled
MVP or later; MVP topics are then discussed one by one. **The tech stack is a required MVP
topic**: its decision produces `toolset.json`, which the Build loop uses.

`/chef:approve mvp` passes when the vision and `mvp.md` are filled in, every MVP topic is
settled, no blocking question is open, every MVP feature has acceptance criteria, `toolset.json`
exists, and no proposal is waiting for the owner.

The other checks: `designed` needs an approved design system and every screen of the item
approved; `building` needs the item designed, and for a feature the MVP shipped; `shipped` needs
the build summary in `build/<item>/summary.md`.

## Design

`/chef:design system` sets the shared look (colours, type, components, motion) before any feature
is designed, so the first feature does not set the style by accident. Screens follow the
journeys. The owner approves in the browser (ECC `plan-canvas`), using the `design:*` skills.

## The build loop

```
PLAN    planner: slices, order, risks, and the model for every other role  ▶ owner approves
TESTS   tester writes failing tests from the acceptance criteria, before any code
BUILD   builder makes them pass, one slice at a time
VERIFY  tester runs everything and adds edge cases           ─┐ problems go back to BUILD;
REVIEW  reviewers in parallel, independent of the builder     ─┘ after 3 rounds the owner decides
DONE    summary, cost, shortcuts taken  ▶ owner approves  ▶ commit
```

| Role | Default agent | Model |
|---|---|---|
| Planner | ECC `planner` (+ `architect` for structural changes) | always the strongest |
| Tester | ECC `tdd-guide` with the stack's test skills from `toolset.json` | chosen by the planner |
| Builder | a builder agent with the stack's pattern skills; build-fix agents when builds break | chosen by the planner |
| Security reviewer | ECC `security-reviewer`, on every slice | always strong |
| Code reviewer | Ponytail `ponytail-review` | chosen by the planner |
| Language reviewer | the ECC reviewer for the stack | chosen by the planner |
| Extra reviewers | ECC `pr-test-analyzer`, `silent-failure-hunter`, `database-reviewer`, `a11y-architect` when the planner flags a need | chosen by the planner |

- **Ponytail** is loaded by every Build agent and is off in every other phase: products set
  `PONYTAIL_DEFAULT_MODE=off`, `/chef:build` switches it on (`/ponytail full`) and off again at DONE.
- **Graphify** maps the codebase when Build starts and refreshes on each commit; Build agents query
  it instead of reading files. Code only: no document mapping, no strict mode.
- Reviewers flag defects, not missing abstractions; the planner settles disagreements.

## Dependencies and settings

- **Required plugins:** ECC, Ponytail (pinned to a reviewed release by commit, so its updates never
  reach a product unreviewed; needs Claude Code v2.1.324 or later). **Required tools:** Graphify (Python 3.11+, `uv`), Python 3.9+
  for Chef's own script. `/chef:vision` checks them and says what is missing.
- **Project settings** written by `/chef:vision` into the product's `.claude/settings.json`
  (merged, never overwritten): the pinned Ponytail marketplace; Ponytail off by default (`PONYTAIL_DEFAULT_MODE=off`); ECC GateGuard
  skips the product folder (`GATEGUARD_EXEMPT_GLOBS=product/**`; it stays on for code).

## Repository and roadmap

Chef gets its own repository and its own Claude project and environment, so changes to Chef never
touch a product. Products install Chef as a plugin. The first product built with it is the test bed.

1. Owner approves this design. *(done)*
2. Owner creates an empty `chef` repository on GitHub. *(done)*
3. Move the kit there with its git history, rename it, and keep its tests passing. *(done)*
4. Build the commands, the stages and the new dashboard in the Chef repository. *(done)*
5. Install Chef into the first product and convert its existing notes to the new format.
6. Run `/chef:discover mvp` on it.

## Not in the first version

- The issue-driven factory, as an optional appliance for running projects with a backlog of small jobs.
- Build cost per feature on the dashboard (from Ponytail's local board).
- A licence for Chef, to be chosen before publishing.
