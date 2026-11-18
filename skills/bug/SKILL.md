---
name: bug
description: Chef's short path from a bug to a fix - reproduce it as a failing test, fix, review, commit. If the fix would change decided behaviour, it becomes an idea instead. Use when the owner reports something broken in a built item.
argument-hint: "<text>"
---

# /chef:bug

Load the `chef` skill first. The bug: $ARGUMENTS

1. Branch: `chef.py branch bug "<short title>"`. Find what it touches: the feature, its acceptance criteria, the accepted decisions.
2. **Decided behaviour?** If the fix would change what an acceptance criterion or an accepted
   decision says, it is not a bug: hand it to `/chef:idea` and stop.
3. Otherwise, with Ponytail on (`/ponytail full`):
   - reproduce it as a failing test (ECC `tdd-guide`);
   - fix it with the smallest change; the build-fix agent from `toolset.json` if the build breaks;
   - run all tests; ECC `security-reviewer` and the language reviewer check the diff;
   - `/ponytail off`.
4. Show the owner the test and the fix. On their yes: commit, with a message naming the bug, then
   `chef.py merge`.
5. Session note, `dashboard`, next move.
