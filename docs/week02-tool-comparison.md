# Week 2 — Tool comparison

Claude (Opus) vs Gemini (Pro). Two comparisons: the Week 1 prompt re-run for Block A, and the `/contact` feature built in the live session for Block B.

> Scores are mine to fill in. The evidence below is what was actually observed; the judgement is the part that is assessed.

---

## Part 1 — Block A: re-running the Week 1 prompt

**Date:** 2026-10-21

### The prompt

Identical to the one used in Week 1, except for one artefact noted below.

```
Write a minimal Flask web application for Python 3.11.

- A single file called app.py
- Flask 3.1.0, pinned to that exact version
- One route, GET /, returning an HTML page with an <h1> and a short paragraph
- Runs with `python app.py` on port 5000, debug off
- Also produce requirements.txt with every dependency pinned to an exact version

Do not add a database, blueprints, or a templates directory. Keep it to those two files.
```

> **Caveat on verbatim-ness.** The prompt was entered into Gemini through browser automation and the leading `- ` of the first bullet was lost, so Gemini received `A single file called app.py`. Everything else was identical. This is recorded rather than hidden; it is not believed to affect the result, since the instruction itself survived intact.

### `requirements.txt` — the headline difference

| Dependency | Claude | Gemini |
|---|---|---|
| blinker | `1.9.0` | `1.9.0` |
| click | `8.1.8` | `8.1.7` |
| Flask | `3.1.0` | `3.1.0` |
| itsdangerous | `2.2.0` | `2.2.0` |
| Jinja2 | `3.1.6` | `3.1.4` |
| MarkupSafe | `3.0.2` | `3.0.2` |
| **Werkzeug** | `3.1.3` | **`Werkzeug`** — no version |
| colorama | `0.4.6 ; sys_platform == "win32"` | absent |
| **Total pinned** | **8 of 8** | **6 of 7** |

Both tools pinned the transitive dependency tree, which was the explicit instruction. Gemini left one unpinned — and immediately above the file it wrote:

> *"This file pins Flask 3.1.0 along with its exact underlying dependency tree to ensure a fully deterministic environment."*

**The prose claims determinism the artefact does not deliver.** The claim and the output contradict each other, and only reading the file catches it.

This matters beyond tidiness. Werkzeug is the WSGI layer Flask runs on and is where security patches land. In Week 8, `pip-audit` cannot tell you whether an unpinned dependency is vulnerable, because it does not know which version you would resolve to.

Claude additionally emitted `colorama` with an environment marker, a conditional dependency that installs only on Windows.

### `app.py` — three differences

| | Claude | Gemini |
|---|---|---|
| Viewport meta tag | present | **absent** |
| Route decorator | `@app.route("/")` | `@app.route("/", methods=["GET"])` |
| HTML | module-level `PAGE` constant | returned inline from the function |

The missing `<meta name="viewport">` is the one with consequences: Week 6 is responsive design and accessibility, so that is either work already done or work still owed.

Gemini was the more literal reader of the specification — `methods=["GET"]` is redundant, since GET is Flask's default, but it is exactly what was asked for.

### What both got wrong, identically

Both produced `app.run(host="127.0.0.1", port=5000, debug=False)`.

`127.0.0.1` accepts connections only from the machine itself. In Week 9 the application runs inside a container and the port will not be reachable from outside it; Week 10 needs it reachable from the internet.

**Neither tool is at fault.** The prompt never specified the bind address, so both filled the gap with the restrictive default. This is the clearest evidence in the whole exercise that the constraint, not the model, is what determines the output — and it is the answer to the third forum question.

### Scores

| Criterion | Claude | Gemini | Evidence |
|---|---|---|---|
| Correctness | | | Both run; both return 200 on `GET /` |
| Code quality | | | |
| Completeness | | | 8/8 pinned vs 6/7; viewport meta present vs absent |
| Security | | | Unpinned Werkzeug blinds `pip-audit` in Week 8 |

### Exclusions

Both respected all three: no database, no blueprints, no `templates/` directory.

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

- [ ] Gemini's raw `app.py` and `requirements.txt`, copied with Gemini's own copy button, into `experiments/week02/tool-b/`
- [ ] Claude's Week 1 output into `experiments/week02/tool-a/`
- [ ] Both `/contact` outputs from the live session
