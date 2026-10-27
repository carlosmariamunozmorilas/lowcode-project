# The influence models — where this application's ideas come from

> ✍️ **Draft, 27 October 2026 — to be rewritten in my own voice.** Assembled
> from two of my ChatGPT conversations (15 October and 27 October) that
> reconstructed the history, checked against my own files. The sections marked
> ✍️ are the ones that must sound like me, because they are my story. Delete
> this note when done.

## In one sentence

Before this application existed, I spent five months building a series of
**influence models**: layered maps of what drives the performance of a digital
business. This application is where a small part of that work stops being a
document and becomes something software checks.

## How it started

✍️ *In my words: the question, the moment, why a list of techniques was not
enough.*

In May 2026 I was preparing for an SEO and analytics interview at a Dublin
digital consultancy. Rather than memorise tools and responsibilities, I wanted
to understand the whole system: **what influences SEO performance, how those
factors interact, which of them a business can control, and how to turn that
into measurable results.** On 12 May that became a seven-layer SEO model; by
16 May it had grown into analytics, reporting and conversion.

The idea that stayed with me was that a discipline is not a list of techniques
but a set of connected levers — and that the useful question is always which
lever moves which outcome.

## Three generations

The work grew in two directions: in **scope**, from SEO to whole digital
businesses, and in **purpose**, from understanding a system to deciding where
to invest in it.

| Generation | When | The question it answers | What it is |
|---|---|---|---|
| **1 · Influence Models** | May 2026 | *What influences performance?* | A layered map of the factors behind one outcome — first SEO, then analytics and conversion |
| **2 · AI-Era Influence Models** | June – October 2026 | *How does AI change those influences?* | 18 models of digital businesses — ecommerce, digital marketing, marketing operations, analytics, CRM, SaaS and more — about 479 layers in all, with AI treated as part of each system rather than as a tool beside it |
| **3 · ROI AI Influence Models** | October 2026 | *Which changes are worth investing in?* | 18 editions, one per business model, that turn the layers into investment decisions: incremental benefit against full cost, cash timing, evidence, and a decision to scale, hold, redesign or retire |

Put shortly: the influence models explain *what drives performance*; the
AI-era models explain *how AI transforms those drivers*; the ROI models
evaluate *which transformations are worth paying for*.

## Why they are in this project

✍️ *In my words: why the course was the moment to build something from them.*

I did not start by deciding to build an application. I started by trying to
understand how digital businesses work. By the time this course began, I had a
large body of structured research and no working software — and the course
asks for exactly the step I had not taken: build something real, with AI
assistance, and show that it works.

The models' own advice decided the scope. A team does not need 479 layers; it
needs the few that answer its problem, made usable. So this application takes
**a small, deliberate subset**, and turns each piece into a rule the code
enforces or a number it computes.

## What the application takes from each generation

| Generation | Taken into the application | Where |
|---|---|---|
| 1 · Influence Models | The habit of thought: every action pulls **one lever**, which moves **one KPI**, inside a fixed tree — revenue = sessions × conversion rate × average order value | [`specification.md` §3](specification.md), [`roi.py`](../roi.py) |
| 2 · AI-Era Influence Models | The **review checklist** — claims evidenced, brand and disclosure, permitted data use, audience eligibility — from the governance layer of the digital marketing model; and the rule that **automations reach the application only through its API and never decide**, from the layer on automation | [`specification.md` §3](specification.md), [`portfolio/portfolio-plan.md`](portfolio/portfolio-plan.md) |
| 3 · ROI AI Influence Models | The rules around the return: the prediction is **fixed before review**; every action is **closed with a decision**; each one shows its **break-even** point; and the application **never counts** saved hours as money, ROAS as a result, or ROI percentages added together | [`specification.md`](specification.md), [`roi.py`](../roi.py), [`lifecycle.py`](../lifecycle.py) |

Three models matter most, each for a different part of the application:
**marketing operations** describes how the team works — the application's
shape; **ecommerce** describes how the money works — the KPI tree and ROI on
gross profit; **digital marketing** describes what the team works on — the
levers.

## What it deliberately does not take

- **The layer cards themselves.** Each model has 25 to 40 of them. They explain
  *why* a lever might work; the application records *whether* it did.
- **Influence weights or maturity scores.** They are diagnostic structures, not
  measured relationships, and turning them into numbers in software would
  present a hypothesis as a fact.
- **Forecasting, cash timing, scenarios, NPV.** The ROI models have them; a
  ten-week course application that records what actually happened does not
  need them, and they would multiply its size.
- **A "choose your business model" tool.** An application where a business
  picks its model, its layers and its assumptions and compares returns is a
  different, much larger product. This one solves one team's problem.
- **The models' published figures.** Every number in this repository comes
  from its own worked example, not from the research.

## How to read the models honestly

✍️ *In my words: what I would say if a lecturer or employer asked "is this
validated?"*

The influence models are **my own research, built iteratively with AI
assistance**. They organise established marketing and business practice, and
they state relationships between factors — but those relationships are
hypotheses. They have not been validated statistically, and I do not present
them as a predictive model.

That is also why the application is built the way it is. It does not predict
what an action will achieve. It asks the team to state an expectation before
the work, measures what actually happened afterwards, and labels how sure
anyone can be. In that sense the application is the first place where my own
framework meets evidence.

## The numbers, as of 27 October 2026

| Collection | Count |
|---|---|
| AI-Era Influence Models | 18 models, about 479 layers (fifteen of 25 layers, one of 24, two of 40) |
| ROI AI Influence Models | 18 editions, one per business model, each with a calculator |

Recount from the source files before quoting these elsewhere; the collections
are still growing.
