# Working on Chef

This repository is Chef itself, a Claude Code plugin. `DESIGN.md` is the approved reference;
change it first when behaviour changes, and keep the code in line with it.

- Products that use Chef live in other repositories. Never mention a specific product here.
- Run `python -m unittest discover -s tests` before every commit.
- `scripts/chef.py` uses only the Python standard library.
- Keep explanations and docs plain and short.
