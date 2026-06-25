---
type: adr
id: "ADR-0008"
title: "Filesystem as Message Bus and Knowledge Corpus"
date: "2026-06-24T22:33:48+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0004"
relates_to: ["adr:ADR-0007", "adr:ADR-0001"]
tags: [architecture, filesystem, message-bus, knowledge-corpus, content, foundations]
last_updated: "2026-06-25T13:59:24+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0008: Filesystem as Message Bus and Knowledge Corpus

**Date**: 2026-06-24
**Status**: Accepted
**Author**: Toby Clemson

## Context

Luminosity's behaviour is delivered as skills running on the Claude Code
runtime (ADR-0007), with deterministic work delegated to a CLI (ADR-0001). The
plugin's job is to **produce first-class content** — articles, blog posts,
social posts, ads, imagery, video — and to work with the **inputs** that shape
it — tone-of-voice guides, messaging frameworks, marketing strategy, audience
personas. The plugin both *consumes* those inputs and can *help create* them, so
the same kind of artefact may be an output of one workflow and an input to
another.

A skill represents one phase of work. Phases must hand work to one another, and
the artefacts above must have a home. Two forces constrain how:

- The conversation context is bounded and costly. Large or long-lived artefacts
  cannot live only in the transcript — they are lost across context compaction
  and across separate skill invocations.
- Subagents do exploratory work in isolated context and return only summaries;
  their durable output needs somewhere to land.

The Accelerator plugin proves a model: phases communicate **through the
filesystem**, with a `meta/` directory as persistent shared memory that skills
read and write at predictable paths. This repo already runs on that model —
`meta/work/`, `meta/decisions/`, `meta/reviews/` are populated. Epic 0001 left
the *directory* undecided as its first Open Question, and ADR-0007 deferred this
mechanism to "decision 8 of the baseline set." This ADR records both, and adds
the home for the deliverables Luminosity exists to produce.

## Decision Drivers

- Bounded, costly conversation context — durable artefacts must outlive the
  transcript and survive compaction and separate invocations.
- Phases and subagents need a predictable, durable handoff channel that does not
  rely on conversational memory.
- The plugin both **produces** shippable deliverables and **consumes/curates**
  the knowledge that feeds them; each needs a discoverable, stable home.
- Reuse Accelerator's proven filesystem-state model rather than inventing one.
- Some consumer repos will run Luminosity **alongside** Accelerator — the layout
  must coexist with an already-populated `meta/`.
- Both humans and skills read these files; the layout must be legible and
  reviewable in version control.

## Considered Options

1. **Filesystem as message bus + knowledge corpus, with two roots** — `meta/`
   for the corpus/message bus and `content/` for deliverables.
2. **Conversation as the channel** — pass artefacts inline through the
   transcript and rely on context to carry them between phases.
3. **Single flat corpus** — everything (deliverables, process state, inputs) in
   one tree under `meta/`, with no product/process separation.
4. **External store** — hold state in a database or service rather than the repo
   filesystem.
5. **Three roots, split by durability** — separate process state from durable
   knowledge: deliverables in `content/`, durable inputs and decisions in one
   root, and transient working state (work items, plans, research) in another.

## Decision

We will use the **filesystem as the message bus and knowledge corpus**. Phases
communicate by reading and writing predictable paths, not by passing artefacts
through the conversation; subagents return summaries while their durable output
lands on disk. State is organised under **two top-level roots**:

- **`meta/`** — persistent shared memory: the knowledge corpus and message bus.
  It holds everything the production process reads and writes that is *not itself
  a deliverable*, in categorised subdirectories — durable inputs (brand and
  tone-of-voice, messaging, strategy, audiences), durable decisions (ADRs under
  `meta/decisions/`), and transient working state (work items, plans, research,
  reviews, notes).
- **`content/`** — the **first-class deliverables** the plugin produces, in
  subdirectories categorised by medium (e.g. `content/articles/`,
  `content/social/`, `content/ads/`, `content/imagery/`, `content/video/`).

The discriminator is **role, not artefact type, origin, or durability**: an
artefact lives in `content/` when it *is the shipped end product*; otherwise it
lives in `meta/`. The same kind of artefact can fall either way by its role — a
messaging framework the plugin creates to *guide its own content production* is
a standing input (`meta/`), whereas the same framework produced as the
*deliverable a client asked for* is the product (`content/`). Neither who
created it nor whether it is durable is the test: `meta/` deliberately spans
durable artefacts (ADRs, brand guides) and transient ones (a single run's
research), and includes inputs the plugin itself authored.

We chose option 1 because it gives phases a durable, cheap handoff that survives
compaction, keeps the conversation lean, and draws a clean line between the
product and the process that makes it. Option 2 was rejected: bounded context
loses artefacts across compaction and separate invocations. Option 3 was
rejected: mixing deliverables with process state obscures what is shippable and,
in repos that also run Accelerator, enlarges the shared-`meta/` collision
surface. Option 4 was rejected: it breaks zero-setup, forfeits the
VCS-reviewable history the filesystem gives for free, and duplicates what the
repo already provides. Option 5 was rejected deliberately: durable and transient
state already coexist legibly under `meta/` because the discriminator is role,
not durability — a third root would fragment the shared memory phases read and
write, and diverge from Accelerator's single-`meta/` convention without removing
the collision it was meant to avoid.

## Consequences

### Positive

- Phases and subagents communicate durably and cheaply; handoffs survive context
  compaction and span separate skill invocations.
- All state is VCS-tracked — diffable, reviewable, and revertable.
- A clear product/process boundary: deliverables in `content/` are easy to find,
  publish, and hand off, while the corpus stays out of the shipped output.
- Reuses Accelerator's proven model; this repo already operates this way.
- Routing the high-volume deliverables to `content/` keeps the bulk of
  Luminosity's footprint **out** of `meta/`, shrinking the namespace shared with
  Accelerator.

### Negative

- Predictable paths are an implicit contract across skills; changing a path is a
  breaking change with no compiler to catch a missed reference.
- Filesystem state can drift from the conversation if a skill writes but fails to
  summarise what it wrote.
- In repos that also run Accelerator, `meta/` is shared. Residual semantic and
  ID-numbering overlap remains in genuinely-shared subdirectories (e.g.
  `meta/work/`, `meta/decisions/`); Luminosity coexists by mirroring
  Accelerator's conventions rather than isolating itself in a separate tree.

### Neutral

- The two roots (`meta/`, `content/`) and the discriminator are fixed here; the
  exact subdirectory names within each are conventions, extensible as new
  artefact types and media appear. This ADR does not enumerate an exhaustive
  subdirectory list.
- `content/` is categorised by medium, mirroring how deliverables are published.
- Skills address these paths via `${CLAUDE_PLUGIN_ROOT}` for plugin scripts and
  repo-relative paths for corpus/content, consistent with existing conventions.
- `meta/` already exists and is populated in this repo; `content/` is established
  by this decision rather than an existing convention, and stays empty until
  production workflows begin emitting deliverables into it.

## References

- `meta/work/0004-record-existing-implicit-architecture-decisions-as-adrs.md` —
  Owning story (decision 8 of 1–8); requires this directory be settled concretely.
- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — Epic;
  resolves its first Open Question (the message-bus / knowledge-corpus directory).
- `meta/decisions/ADR-0007-skills-as-the-product.md` — Companion; deferred this
  mechanism to decision 8.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — Related;
  governs what work lives in skills vs. the CLI.
- Accelerator plugin (https://github.com/atomicinnovation/accelerator) — prior
  plugin proving the filesystem-state model and the `meta/` convention.
