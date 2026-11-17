# Chef

Chef guides one person, working with Claude Code, from a product idea to a shipped and maintained
product. You prepare the base first (the MVP), then add features one at a time, at your own pace.
Chef proposes every next step; only you approve.

Read [`DESIGN.md`](DESIGN.md) first: it is the reference for how Chef works.

## Status

The design is approved. What exists today is the foundation carried over from the first
prototype:

| Path | What it is |
|---|---|
| `scripts/chef.py` | the product folder tool: records questions and decisions, checks consistency, checks phase exits, builds the offline dashboard (Python 3.9+, no dependencies) |
| `templates/` | the product folder skeleton and one template per file type |
| `skills/` | the prototype's skills (`lifecycle`, `frame`, `discover`, `gate`, `dashboard`), to be replaced by the commands in `DESIGN.md` |
| `tests/` | `python -m unittest discover -s tests` |

Next: build the commands (`/chef:vision`, `/chef:discover`, `/chef:approve`, `/chef:design`,
`/chef:build`, `/chef:idea`, `/chef:bug`, `/chef:status`), the item stages and the new dashboard.

## Installing in a product

Chef is a Claude Code plugin. In the product's repository:

```text
/plugin marketplace add <owner>/Chef
/plugin install chef@chef
```

Chef also expects the ECC and Ponytail plugins and the Graphify CLI. `/chef:vision` will check
for them.

## Rules for working on Chef

- Chef never mentions a specific product. `chef.py check`, run from a product, fails if any file
  here contains that product's name or its listed terms.
- Keep `scripts/chef.py` dependency-free and covered by tests.
- No licence has been chosen yet; decide before publishing.
