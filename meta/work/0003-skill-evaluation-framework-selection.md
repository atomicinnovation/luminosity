---
type: work-item
id: "0003"
title: "Skill Evaluation Framework Selection"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: spike
priority: high
parent: "work-item:0001"
blocks: ["work-item:0005", "work-item:0010"]
tags: [spike, evaluation, skills, tooling]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0003: Skill Evaluation Framework Selection

**Kind**: Spike
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Survey the landscape of skill-evaluation approaches and recommend one, so the
`configure` skill can be the first concrete evaluation target and skill quality
becomes measurable. Time-boxed to 2 days.

## Context

The epic (0001) requires skill evaluation but the author is not familiar with
skill-evaluation approaches. The decision is genuinely open: the spike surveys
the available frameworks broadly rather than choosing from a fixed shortlist.
`skill-creator`, promptfoo, and DeepEval are known starting points, not the limit
of what is considered.

## Requirements

Research questions to resolve, time-boxed to **2 days**:

- Survey the landscape of skill / agent-instruction evaluation frameworks and
  weigh them on merit for: fit with the skills-as-product model, dev-time and
  CI usage, task/assertion authoring effort, variance reporting, and
  maintenance/longevity risk. The following are known starting points and useful
  reference shapes, not an exhaustive shortlist — actively look for others during
  the spike:
  - skill-creator — the one purpose-built for evaluating a skill as a skill
    (native with-skill vs baseline, evals.json tasks, assertion grading, pass-
    rate/token/time deltas as mean ± stddev); interactive/subagent-driven, not
    CI-native as-is.
  - promptfoo — declarative matrix (skill-vs-no-skill is one extra prompt row),
    --repeat for variance, g-eval/llm-rubric/select-best grading, Claude Agent
    SDK provider, native exit codes. Longevity flag: OpenAI acquisition
    (Mar 2026); still MIT.
  - DeepEval — pytest-style authoring, GEval/custom LLM-judge metrics, regression
    comparison; with/without is hand-built; no first-class repeat/variance.
- Recommend an approach (a single framework or a hybrid), and define how a
  `configure` pass-rate / benchmark result is produced and surfaced. Note: the
  epic favours running evals during development with version-controlled benchmark
  results rather than on every CI build, to control token cost — the
  recommendation should account for that execution model.

Output: a written recommendation with a decision, recorded in this spike work
item, feeding the eval-framework ADR (theme 1 decision 11). The "Apply the eval
framework to the `configure` skill" story references this spike.

## Acceptance Criteria

- [ ] When the spike concludes, this work item contains a Recommendation section
      naming the chosen framework (or hybrid), the set of frameworks surveyed
      (at least skill-creator, promptfoo, and DeepEval, plus any others found
      during the survey), and the rationale, including any longevity risks.
- [ ] The recommendation defines how a `configure` pass-rate / benchmark result
      is produced and run during development with results committed to the repo
      (not on every CI build), and confirms or raises the epic's provisional
      floor (≥ 3 tasks, ≥ 80% pass-rate) against the 2025–2026 guidance of 20–50
      real-failure-derived tasks with multi-trial variance.
- [ ] The eval-framework ADR (theme 1 decision 11) cites this work item.

## Open Questions

- None — the eval framework is recorded as its own ADR (decision 11), and the
  recommendation home is this work item.

## Dependencies

- Blocks: "Apply the eval framework to the `configure` skill" story (0010); the
  eval-framework ADR (decision 11) in the spike-dependent ADR story (0005).
- Blocked by: none.
- Parent: epic 0001.

## Assumptions

- The recommendation is not only decided but applied within the epic (A4): the
  first eval target is the `configure` skill.

## Technical Notes

- Accepted 2025–2026 methodology (Anthropic, "Demystifying evals for AI agents",
  Jan 2026): tasks + multiple trials per task, track variance not just pass/fail
  (pass@k vs pass^k), combine code/model/human graders, grade outcomes over
  trajectory, baseline comparison to attribute improvement, start with 20–50
  real-failure tasks.
- skill-creator timing/token capture is one-shot from the task notification —
  must be captured at completion.

## Drafting Notes

- Kind set to `spike`: the epic frames this as resolving an unknown with a
  written recommendation.
- Decision bias set to genuine, open-ended evaluation (per the author): the three
  named frameworks are examples/reference shapes, and the spike actively surveys
  the wider landscape rather than picking from a fixed shortlist.
- Eval framework promoted to its own ADR (decision 11) per the author — requires
  updating epic 0001's theme 1 (10 → 11 decisions) and its first acceptance
  criterion.
- Recommendation home kept consistent with the architecture spike — recorded in
  this work item.
- Enriched with web research on skill-creator/promptfoo/DeepEval current as of
  mid-2026.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Research: Anthropic `skill-creator` Eval/Benchmark workflow
  (https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md);
  "Demystifying evals for AI agents"
  (https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents);
  promptfoo (github.com/promptfoo/promptfoo); DeepEval
  (github.com/confident-ai/deepeval).
