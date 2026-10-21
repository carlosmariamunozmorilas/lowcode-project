# Week 2 — Tool comparison

Claude (Opus) vs Gemini (Pro). Two comparisons: the Week 1 prompt re-run for Block A, and the `/contact` feature built in the live session for Block B.

> Scores are mine to fill in. The evidence below is what was actually observed; the judgement is the part that is assessed.

---

## Part 1 — Block A: re-running the Week 1 prompt

**Claude's output:** produced in Week 1, saved in `experiments/week02/tool-a/`.
**Gemini's output:** two runs on 2026-10-21, Gemini **Pro**, saved in
`experiments/week02/tool-b/run-1/` and `run-2/`, with `PROVENANCE.md`.

> Scores are mine to fill in. The evidence below is what was actually observed; the judgement is the part that is assessed.

> **Correction, 2026-10-21.** An earlier version of this section reported a
> different Gemini result — Werkzeug left unpinned, no viewport meta tag, and the
> same `127.0.0.1` bind as Claude. That run was real: the prompt went to Gemini
> Pro through the browser extension at about 15:00. But its output was never
> saved. It was read off the page as text instead, which lost the Python
> indentation and — as noted at the time — cut off the end of
> `requirements.txt`. The captured text stops at the word `Werkzeug` and runs
> straight into Gemini's interface: the model selector `Pro`, then the footer
> disclaimer. That is what a truncated line looks like, not an unpinned one. The
> conversation is not in the account's Gemini history, so it cannot be reopened
> and checked. This section has therefore been rebuilt from two runs whose files
> are saved in this repository, and what the three disagree about is laid out at
> the end, because the disagreement is the most useful thing here.

### The prompt

Identical for both tools, and reproduced verbatim in `experiments/week02/prompt.txt`.

```
Write a minimal Flask web application for Python 3.11.

- A single file called app.py
- Flask 3.1.0, pinned to that exact version
- One route, GET /, returning an HTML page with an <h1> and a short paragraph
- Runs with `python app.py` on port 5000, debug off
- Also produce requirements.txt with every dependency pinned to an exact version

Do not add a database, blueprints, or a templates directory. Keep it to those two files.
```

> **How it was entered.** Gemini's input box converts a line beginning with `- `
> into a bulleted list and swallows the first dash. Typing the prompt therefore
> changes it. It was inserted as plain paragraphs instead, and the sent message
> keeps all five bullets intact. Worth knowing before Week 3: the tool's own
> editor can silently edit a specification on its way in.

### `requirements.txt`

Gemini's two runs produced byte-identical files.

| Dependency | Claude | Gemini (both runs) |
|---|---|---|
| blinker | `1.9.0` | `1.9.0` |
| click | `8.1.8` | `8.1.7` |
| Flask | `3.1.0` | `3.1.0` |
| itsdangerous | `2.2.0` | `2.2.0` |
| Jinja2 | `3.1.6` | `3.1.4` |
| MarkupSafe | `3.0.2` | `3.0.2` |
| Werkzeug | `3.1.3` | `3.1.3` |
| colorama | `0.4.6 ; sys_platform == "win32"` | absent |
| **Total pinned** | **8 of 8** | **7 of 7** |

Both honoured the instruction: every dependency pinned to an exact version,
transitive ones included. Run 1 said so above the file —

> *"This file pins Flask exactly to 3.1.0 along with its core dependencies to ensure fully deterministic installs."*

— and on this occasion the claim and the artefact agree. Run 2 produced the same
file and made no claim at all.

Two differences remain. Gemini resolved **older** versions of `click` and
`Jinja2` than Claude, twice — not wrong, but a reminder that a pinned file
freezes whatever the model believed current, which is not the same as current.
Week 8 runs `pip-audit` over both.

Claude additionally emitted `colorama` with an environment marker, a conditional
dependency that installs only on Windows. Gemini omitted it. On this machine
that is the difference between a `pip freeze` that matches the file and one that
does not.

### `app.py`

| | Claude | Gemini run 1 | Gemini run 2 |
|---|---|---|---|
| Route decorator | `@app.route("/")` | `methods=['GET']` | `methods=['GET']` |
| HTML | module-level `PAGE` constant | inline, flush-left | inline, indented inside the string |
| `<html lang>` and `charset` | present | present | **absent** |
| Viewport meta | present | present | **absent** |
| Bind address | `127.0.0.1` | `0.0.0.0` | `0.0.0.0` |

The viewport row is the one with consequences. Week 6 is responsive design and
accessibility, and whether Gemini's starting point includes the tag depends on
which run you happen to get. The prompt did not ask for it, so neither answer is
a failure to follow it — but it means a Gemini-generated base is a coin toss on
something Week 6 will mark.

Gemini was the more literal reader of the specification in both runs:
`methods=['GET']` is redundant, GET being Flask's default, but it is exactly what
was asked for. Run 1 also added a comment, `# Runs on port 5000 with debug
disabled, as requested`, which reads as the model confirming its instructions
back. Run 2 indents its HTML inside the string, so the page it serves begins
with a blank line and four spaces before `<!DOCTYPE html>` — harmless to a
browser, untidy in a view-source.

### The bind address — where it actually matters

The prompt never said where the application should be reachable from, and the
tools filled that silence differently — Claude one way, Gemini the other way
twice.

`127.0.0.1` accepts connections only from the machine itself. In Week 9 the
application runs inside a container and that port is not reachable from outside
it; Week 10 needs it reachable from the internet. `0.0.0.0` listens on every
interface, which is what a container needs — and which, outside one, exposes the
development server to the local network.

Running the files makes the difference concrete. Claude's app reports only
`http://127.0.0.1:5000`; both Gemini runs start on `0.0.0.0` and additionally
advertise this machine's address on the local network, which anything on the
same Wi-Fi can reach. All three return 200 on `GET /` (checked 2026-10-21).

Neither is wrong without knowing the deployment, and that is the finding: **the
gap was in the specification, not in either tool.** A one-line request cannot
state a bind address, so the model picks one, and the two models picked
opposite defaults. This is the answer to the Week 3 question about what a
specification must state that a one-line request does not.

### Same prompt, three Gemini results

| Observation | Earlier run (read as page text) | Run 1 (saved) | Run 2 (saved) |
|---|---|---|---|
| Werkzeug | text cut off at `Werkzeug` | `3.1.3` | `3.1.3` |
| Pinned total | recorded as 6 of 7 | 7 of 7 | 7 of 7 |
| click / Jinja2 | `8.1.7` / `3.1.4` | `8.1.7` / `3.1.4` | `8.1.7` / `3.1.4` |
| Viewport meta | absent | present | absent |
| Bind address | `127.0.0.1` | `0.0.0.0` | `0.0.0.0` |
| Determinism claim in the prose | yes | yes | none |

Some of it is stable: the version numbers are identical in all three, and both
saved runs pin everything. Some of it is not: the viewport tag came and went
between two runs of the same message, and so did the sentence promising
determinism.

The earlier run's missing viewport is plausible — run 2 reproduced it. Its
unpinned Werkzeug almost certainly was never Gemini's output at all: the line
was cut, not left without a version. Its `127.0.0.1` cannot be checked either
way; both saved runs bind `0.0.0.0`.

That makes the lesson sharper, not weaker. The most quotable finding in the
first version of this document — a model promising determinism while leaving a
dependency loose — was produced by the way the output was read, not by the
model. **An AI-generated artefact is evidence only if the artefact itself is
saved**: not scraped as page text, not paraphrased, not remembered. And it has to
be saved at once, because it is not reproducible. Two runs of an identical
prompt, in the same conversation, did not produce the same `app.py` — and
pressing Redo to get the second one erased the first from the interface
entirely. Run 1 now exists only in `tool-b/run-1/`.

That is why `experiments/` exists, why its README says a corrected file proves
nothing, and why `tool-b/` carries a `PROVENANCE.md`.

### Scores

| Criterion | Claude | Gemini | Evidence |
|---|---|---|---|
| Correctness | | | All three run; all return 200 on `GET /`, checked 2026-10-21 |
| Code quality | | | `PAGE` constant vs inline HTML; run 2 indents its HTML inside the string |
| Completeness | | | 8/8 pinned incl. Windows marker vs 7/7; viewport in Claude, in one of two Gemini runs |
| Security | | | Bind address differs; Gemini's click and Jinja2 are older |

### Exclusions

All three outputs respected all three: no database, no blueprints, no
`templates/` directory.

---

## Part 2 — Block B: the `/contact` feature

**Date:** 2026-10-21, live session

### The prompt

Identical for both tools. Paste verbatim.

```
[paste here]
```

### Tool A — Claude

Raw output: `experiments/week02/tool-a/`

| Criterion | Score /5 | Evidence |
|---|---|---|
| Correctness | | |
| Code quality | | |
| Completeness | | |
| Security | | |

### Tool B — Gemini

Raw output: `experiments/week02/tool-b/`

| Criterion | Score /5 | Evidence |
|---|---|---|
| Correctness | | |
| Code quality | | |
| Completeness | | |
| Security | | |

### The tests

| Input | Expected | Claude | Gemini |
|---|---|---|---|
| Empty submission | Rejected, not a 500 | | |
| Invalid email (`notanemail`) | Rejected | | |
| Message containing `<script>alert(1)</script>` | Escaped, not executed | | |
| `curl` straight to the route, bypassing the browser | **Still rejected** | | |

The last row decides it. Validation that only runs in the browser is not server-side validation, and a tool whose output fails that row did not build the feature that was asked for.

---

## Decision

**Chosen for the main build:**

**Why, in terms of the evidence above:**

**What had to be fixed before integrating:**

---

## One surprising difference

For the forum post.

---

## Evidence still to attach

- [x] Gemini's raw output, two runs, in `experiments/week02/tool-b/run-1/` and `run-2/`, with `PROVENANCE.md` (2026-10-21)
- [x] Claude's Week 1 output in `experiments/week02/tool-a/`
- [ ] Both `/contact` outputs from the live session
