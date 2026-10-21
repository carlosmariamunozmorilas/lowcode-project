# Week 2 — Tool comparison

Claude (Opus) vs Gemini (Pro), on the Week 1 prompt: re-run on Gemini in Block A, written up here for Block B. The Week 2 sheet asks for verbatim prompts, scores with evidence and a reasoned choice. It does not ask for a second feature to be built, so there is one comparison, not two.

> **How the scores were made.** Drafted with Claude from measurements taken on
> 2026-10-21 — `pip-audit`, `pycodestyle`, and a clean install of each
> `requirements.txt` — then reviewed by me before merging. Claude is one of the
> two tools being scored, so every score below cites a measurement rather than
> an impression, and the Claude column deserves the more sceptical reading.

---

## Re-running the Week 1 prompt

**Claude's output:** produced in Week 1, saved in `experiments/week02/tool-a/`.
**Gemini's output:** two runs on 2026-10-21, Gemini **Pro**, saved in
`experiments/week02/tool-b/run-1/` and `run-2/`, with `PROVENANCE.md`.

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

Both pinned every package they listed, transitive ones included. Run 1 said so
above the file —

> *"This file pins Flask exactly to 3.1.0 along with its core dependencies to ensure fully deterministic installs."*

— and every line of the file is indeed pinned. Run 2 produced the same file and
made no claim at all.

Two differences remain. Gemini resolved **older** versions of `click` and
`Jinja2` than Claude, twice — a reminder that a pinned file freezes whatever the
model believed current, which is not the same as current. The measurements below
show what that costs.

And Claude emitted `colorama` with an environment marker, a conditional
dependency that installs only on Windows. Gemini omitted it — which turns out to
matter: on Windows a clean install of Gemini's file pulls `colorama` in anyway,
unpinned. "Every line pinned" and "every dependency pinned" are not the same
claim, and only the second is what the prompt asked for.

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

### Measurements

Taken 2026-10-21 in throwaway virtual environments, so nothing touched the
project's own `.venv`.

**`pip-audit` against each `requirements.txt`** — known advisories, counted once each:

| Package | Claude | Gemini | Fixed in |
|---|---|---|---|
| Flask `3.1.0` | 2 | 2 | 3.1.3 |
| Werkzeug `3.1.3` | 4 | 4 | 3.1.9 |
| Jinja2 | `3.1.6`: 0 | `3.1.4`: **3** | 3.1.6 |
| **Total** | **6** | **9** | |

Six of the nine are shared, and two of those six are the prompt's fault, not
either tool's: *"Flask 3.1.0, pinned to that exact version"* pinned a version
with two known advisories. Pinning did not make the application safe. It made
it auditable — `pip-audit` can only report these because every version is
fixed.

**`pycodestyle` on each `app.py`:**

| | Findings |
|---|---|
| Claude | 1 — `E501`, an 87-character line inside the HTML string. Within Ruff's default limit of 88, which is what Week 7 uses. |
| Gemini run 1 | 2 — `E302` and `E305`, one blank line where PEP 8 wants two around a top-level function |
| Gemini run 2 | 2 — the same two |

**A clean install of each file on this machine (Windows), compared with what it pins:**

| | Pinned | Installed | Installed but not in the file |
|---|---|---|---|
| Claude | 8 | 8 | none |
| Gemini | 7 | 8 | **`colorama==0.4.6`** |

`click` depends on `colorama` on Windows only. Claude listed it with a
`sys_platform == "win32"` marker; Gemini did not list it, so pip resolves it
freely. On the platform this course is taught on, Gemini's file does not meet
the prompt's *"every dependency pinned to an exact version"*.

### Scores

Out of 5.

| Criterion | Claude | Gemini | Evidence |
|---|---|---|---|
| Correctness | 5 | 5 | All three files run and return 200 on `GET /`; every explicit instruction met, Gemini more literally (`methods=['GET']`) |
| Code quality | 5 | 3 | Claude: one long line, clean under Ruff; content separated from the route as a `PAGE` constant. Gemini: two PEP 8 errors in each run, HTML inline, and run 2 indents it inside the string and drops `lang` and `charset`. Scored on the weaker run, since you do not choose which run you get |
| Completeness | 5 | 3 | Claude: clean install matches the file exactly; viewport, `lang`, `charset` present. Gemini: `colorama` installs unpinned on Windows; viewport, `lang` and `charset` in only one of two runs |
| Security | 3 | 2 | Both: debug off; Flask and Werkzeug carry 6 shared advisories. Gemini: 3 more from Jinja2 3.1.4, and `0.0.0.0` puts the development server — with those Werkzeug advisories — on the local network when run as instructed |
| **Total** | **18** | **13** | |

**What these scores cannot show.** Claude was sampled once and Gemini twice, so
Gemini's variability is measured and Claude's is not. A second Claude run could
vary as much. The Week 3 lab is the place to find out.

### Exclusions

All three outputs respected all three: no database, no blueprints, no
`templates/` directory.

---

## Decision

**Chosen for the main build:** Claude.

**Why, in terms of the evidence above:**

- **Its `requirements.txt` is complete on the platform I build on.** A clean
  install matches the file exactly. Gemini's leaves `colorama` floating on
  Windows, which defeats the reason for pinning.
- **Fewer known vulnerabilities from its own choices** — 6 advisories against 9.
  The difference is entirely Jinja2: Claude chose 3.1.6, Gemini 3.1.4.
- **Closer to what Weeks 6 and 7 will mark.** Viewport, `lang` and `charset` are
  present, and the code is clean under the linter Week 7 uses. Gemini dropped
  all three in one of its two runs.

What Gemini did better, and what I keep from it: it read the specification more
literally, and its `0.0.0.0` is the right default for the container in Week 9.
Gemini stays in use as the second opinion and for long-document reading, where
its variability matters less.

**What had to be fixed before integrating:**

1. **The bind address.** Claude's `127.0.0.1` cannot be reached from outside a
   container. It has to come from the environment before Week 9, and the
   Week 3 specification should state it, since neither model could guess it.
2. **Flask and Werkzeug.** The project's own `requirements.txt` is Claude's
   output, so the six shared advisories are in the main repository today.
   Upgrading to Flask 3.1.3 and Werkzeug 3.1.9 clears them. That is due when
   the Week 3 lab regenerates the application and its dependencies, and in any
   case before anything is deployed in Week 10.

---

## One surprising difference

For the forum post.

> I expected the surprising difference to be an unpinned dependency, and it was
> — just not the one I first wrote down. My first comparison said Gemini left
> Werkzeug without a version. That turned out to be my own mistake: I had read
> the reply off the page as text, and the text was cut off mid-line. Re-running
> it and saving the files showed Werkzeug pinned. The real gap was a package
> that was not in Gemini's file at all. `click` needs `colorama` on Windows, so
> a clean install of Gemini's "fully pinned" file quietly pulls it in at
> whatever version pip finds. Claude listed it with a Windows-only marker. Same
> prompt, and the difference only shows up when you install it on the machine
> you actually use.

---

## Evidence still to attach

- [x] Gemini's raw output, two runs, in `experiments/week02/tool-b/run-1/` and `run-2/`, with `PROVENANCE.md` (2026-10-21)
- [x] Claude's Week 1 output in `experiments/week02/tool-a/`
