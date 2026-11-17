---
name: discover
description: Run one structured discussion round of the Discover phase - pick a topic, work through its open questions with the owner one at a time, and record decisions, new questions and features in the product ledger. Use when the owner wants to settle open points, asks "what's still open", or brings a new idea or change request.
---

# Discover: one discussion round

Load the `lifecycle` skill first for the rules and commands.

## Before the round

1. Run `ledger.py status`. Propose a topic: the owner's choice if they gave one, otherwise the one
   with the most blocking questions, or the one later topics depend on.
2. Read the topic's questions, the decisions they mention, `vision.md`, and any data-source or
   feature files involved. Note which questions depend on others and take those first.
3. Set the topic's status to `in progress` in `topics.md`.

## During the round

Take questions one at a time, blocking ones first. For each:

1. Restate it in one plain sentence and say why it matters.
2. Give what is already known, with sources. If a fact is missing and findable (docs, an API,
   a licence), look it up before asking the owner. If it needs a test, propose a spike.
3. Offer two to four concrete options with their trade-offs, and say which you recommend and why.
   Use a multiple-choice prompt when the options are discrete.
4. Record the outcome straight away:
   - Owner chose: `add-decision ... --answers Q-NNN --accepted --source "owner, round YYYY-MM-DD"`.
   - Owner leaning but not sure: `add-decision` without `--accepted` (it waits in the dashboard).
   - New uncertainty surfaced: `add-question`.
   - Not answerable yet (needs research, a spike, someone else): leave it open and add a note
     under Notes saying what would answer it.
   - No longer relevant: set its Status to `dropped` with a one-line reason under Notes.

Keep a round to about six to eight questions. Stop earlier if the owner is tired or the answers
get vague; a vague decision is worse than an open question.

## Features

When decisions add up to a feature, write it from `templates/feature.md` as `features/F-NNN-*.md`
with acceptance criteria in the form `- **AC-001** Given ..., when ..., then ...`. ECC's
`intent-driven-development` skill writes good criteria. Link the decisions it rests on.

## After the round

1. Write `sessions/YYYY-MM-DD-<topic>.md` from `templates/session.md`.
2. Ask the owner whether the topic is covered. Set `covered` only if they agree and no question in
   it is still open.
3. Run `check`, then `dashboard`, and commit with a message naming the topic and decisions.
4. End with: what was decided, what is still open, and the suggested next topic.
