# {{PRODUCT}}: product folder

Everything decided about {{PRODUCT}} before and during development lives in this folder. It is
managed with the product kit (`kit/`); the kit's `lifecycle` skill explains the process.

| Path | Holds |
|---|---|
| `product.json` | name and current phase |
| `vision.md` | the framing: problem, people, promise, non-goals |
| `topics.md` | the areas Discover must cover, with their status |
| `questions/` | every open point, one file each (`Q-001-...md`) |
| `decisions/` | every answer, one file each (`D-001-...md`) |
| `features/` | features with acceptance criteria (`F-001-...md`) |
| `journeys/` | user journeys, step by step |
| `data-sources/` | one dossier per integration or data source |
| `design/` | one file per screen, linked to its mockup |
| `sessions/` | notes from each discussion round |
| `gates.md` | the owner's sign-off for each phase |
| `dashboard.html` | generated overview; never edit by hand |

Rules: only the owner accepts decisions and signs gates. A question is decided only when an
accepted decision answers it. Changing a past decision means a new decision that supersedes it.
