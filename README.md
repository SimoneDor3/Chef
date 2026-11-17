# Product lifecycle kit

A reusable process for taking a product from first idea to maintenance, for one owner working
with Claude Code. It gives the thinking phase the same structure a build pipeline gives code.

## The idea

Four phases, each closed by a gate only the owner can sign:

1. **Frame**: what the product is (problem, people, promise, non-goals).
2. **Discover**: every open point becomes a numbered question and is settled in discussion
   rounds, one topic at a time, until nothing blocking is left.
3. **Design**: mockups for every journey, approved screen by screen.
4. **Build & maintain**: development from the approved design. After launch, new ideas and
   changes re-enter at Discover.

Everything lives as plain markdown in the product's own repository, so it is reviewable,
versioned and readable by any agent. A generated dashboard shows where the product stands.

## Contents

| Path | What it is |
|---|---|
| `.claude-plugin/` | Claude Code plugin manifest and a local marketplace entry |
| `skills/lifecycle` | the reference: phases, rules, file formats, commands |
| `skills/frame`, `discover`, `gate`, `dashboard` | one skill per activity |
| `scripts/ledger.py` | the ledger tool: create records, check consistency, check gates, build the dashboard (Python 3.9+, no dependencies) |
| `templates/` | the product folder skeleton and one template per record type |
| `tests/` | `python -m unittest discover -s kit/tests` |

## Using it

Start a product:

```bash
python kit/scripts/ledger.py init --name "My Product"
```

Then ask Claude Code to run the `frame` skill, then `discover` rounds, checking progress with
`gate` and `dashboard`.

To load the skills as a plugin, add the kit as a local marketplace and install it from there:

```text
/plugin marketplace add ./kit
/plugin install product-lifecycle@product-lifecycle
```

The plugin route has not been tested yet; the script works on its own either way.

## Staying reusable

The kit must never mention a specific product. `ledger.py check` enforces it: it fails if any
file in the kit contains the product's name or one of the `separation_terms` listed in that
product's `product.json`. To extract the kit into its own repository with its history:

```bash
git subtree split --prefix=kit -b product-lifecycle-kit
```

## Not built yet

- Design-phase and Build-phase skills (until then: the `design:*` skills, ECC `plan-canvas`
  for browser review, and a development factory or ECC `orch-*` for Build).
- A licence, to be chosen before extraction.
