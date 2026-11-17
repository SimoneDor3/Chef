# {{PRODUCT}}: product folder

Everything decided about {{PRODUCT}} lives here, managed by the Chef plugin. Run `/chef:status`
to see where things stand and the next move.

| Path | Holds |
|---|---|
| `product.json` | name, and the stage of the MVP and of each later feature |
| `vision.md` | problem, people, promise, experience, non-goals, constraints, success |
| `mvp.md` | the MVP: goal, what is in, what is out, how we know it works |
| `topics.md` | areas to discuss, labelled MVP or later, with status |
| `questions/` | one open point each (`Q-001-...md`) |
| `decisions/` | one answer each (`D-001-...md`) |
| `features/` | goal, scope, acceptance criteria, label (`F-001-...md`) |
| `toolset.json` | the stack and the ECC agents and skills that fit it |
| `journeys/`, `data-sources/` | user journeys and integration dossiers |
| `design/` | `system.md` and one file per screen |
| `build/` | plan and reports per item (`build/mvp/`, `build/F-004/`) |
| `sessions/` | a few lines per working session |
| `dashboard.html` | generated; never edit; not committed |

Only the owner accepts decisions and approves stages. Accepted decisions are never edited, only
superseded.
