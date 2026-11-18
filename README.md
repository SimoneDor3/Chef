# Chef

Chef guides one person, working with Claude Code, from a product idea to a shipped and maintained
product. You prepare the base first (the MVP), then add features one at a time, at your own pace.
Chef proposes every next step; only you approve.

Read [`DESIGN.md`](DESIGN.md) first: it is the reference for how Chef works.

## Status

Step 4 of the roadmap is built: the commands, the item stages and the offline dashboard.

| Path | What it is |
|---|---|
| `skills/` | the eight commands (`/chef:vision`, `/chef:discover`, `/chef:approve`, `/chef:design`, `/chef:build`, `/chef:idea`, `/chef:bug`, `/chef:status`) and `chef`, the shared rules they load |
| `scripts/chef.py` | the product folder tool: records questions, decisions and features, moves items between stages with checks, suggests the next move, checks dependencies, writes project settings, builds the dashboard (Python 3.9+, no dependencies) |
| `templates/` | the product folder skeleton and one template per file type |
| `tests/` | `python -m unittest discover -s tests` |

Next: install Chef into the first product and convert its notes (roadmap step 5).

## Installing in a product

Chef is a Claude Code plugin. In the product's repository:

```text
/plugin marketplace add <owner>/Chef
/plugin install chef@chef
```

Chef also expects the ECC and Ponytail plugins and the Graphify CLI. Ponytail is pinned to a reviewed
release (see `PONYTAIL_RELEASE` in `scripts/chef.py`), which needs Claude Code v2.1.324 or later. `/chef:vision` will check
for them.

## Rules for working on Chef

- Chef never mentions a specific product. `chef.py check`, run from a product, fails if any file
  here contains that product's name or its listed terms.
- Keep `scripts/chef.py` dependency-free and covered by tests.
- No licence has been chosen yet; decide before publishing.
