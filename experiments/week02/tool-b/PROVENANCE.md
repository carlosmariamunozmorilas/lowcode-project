# tool-b — Gemini, provenance

Two runs of the same prompt, same model (Gemini **Pro**), same conversation,
2026-10-21, signed in as the project owner:
https://gemini.google.com/app/88a66199f687a4b5

| | How | Saved |
|---|---|---|
| `run-1/` | prompt sent from the browser, evening | immediately, as the two code blocks of the reply |
| `run-2/` | the same message re-run with Gemini's **Redo**, later that evening | from the reply that replaced run 1 |

The prompt is the one in `../prompt.txt`, sent verbatim. Gemini's input box turns
a line starting with `- ` into a bulleted list and swallows the first dash, so
the text was inserted as plain paragraphs instead of typed; the sent message
keeps all five `- ` bullets intact.

**Redo replaces the visible answer.** The conversation link now shows run 2 only,
with no way back to run 1 in the interface. Run 1 survives in this folder and
nowhere else. That is the clearest argument this repository has for saving
output the moment it appears.

## What each reply said besides the code

Run 1 put this above `requirements.txt`:

> This file pins Flask exactly to 3.1.0 along with its core dependencies to
> ensure fully deterministic installs.

Run 2 made no claim about determinism. Its only prose was the two file names and
a closing offer: *"Want to add basic CSS styling to the HTML string?"*

## Both checked

Each `app.py` was run from the project's venv and returns 200 on `GET /`,
listening on `0.0.0.0:5000`.

## Why this folder exists

An earlier run of the same prompt, at about 15:00 the same day, was recorded in
`docs/week02-tool-comparison.md` from text read off the page rather than from the
files. That text lost the Python indentation and was cut off part-way through
`requirements.txt`, at the word `Werkzeug` — which is how an "unpinned Werkzeug"
entered the first version of the comparison. The conversation is not in the
account's Gemini history. These two runs, saved as files, are what replaced it.
