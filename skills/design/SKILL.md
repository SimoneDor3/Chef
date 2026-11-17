---
name: design
description: Chef's design step - the shared design system first, then screens per journey for the MVP or a feature, reviewed and approved by the owner in the browser. Use when the owner wants to set the look of the product or design an item's screens.
argument-hint: "<system | mvp | feature>"
---

# /chef:design

Load the `chef` skill first. Target: $ARGUMENTS.

## `system`

Before any screen. Write `design/system.md` from Chef's `templates/design-system.md`: colours,
type, components, motion, from the vision's Experience section and the stack. Use
`design:design-system` and ECC `frontend-design-direction`. Build a small mockup page showing it
and review it with the owner in the browser (ECC `plan-canvas`). Set `Status` to `approved` only
on their yes.

## `mvp` or a feature

1. Run `chef.py stage <item> designing`. If refused, say what is missing and stop. If
   `design/system.md` is not approved, do `system` first.
2. List the journeys the item needs (write any missing ones in `journeys/`), then the screens.
3. For each screen: a file from `templates/screen.md` with `Item` set to the item, and a mockup
   next to it. States: default, empty, loading, error. Use `design:ux-copy` for words and
   `design:accessibility-review` before showing.
4. Review in the browser with `plan-canvas`, one journey at a time. Record feedback under Review
   notes; set `Status` to `approved` only on the owner's yes.
5. `check`, `dashboard`, session note, commit. When every screen is approved, next move:
   `/chef:approve <item>`.

No product code here. Mockups are throwaway files in `design/`.
