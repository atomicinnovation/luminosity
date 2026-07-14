---
name: configure
description: >-
  Read or write luminosity configuration values through the CLI. Use to get or
  set a dotted section.key — resolving personal-over-team by default, or scoped
  to a --level (team is the shared, committed file; personal is the local,
  git-ignored file that overrides it).
argument-hint: "[get <section.key> | set <section.key> <value>] [--level team|personal]"
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity config *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)
---

# Configure

!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --skill=configure --fail-safe`

You manage the CLI-owned configuration **values** **only** through the
`luminosity config` command. You never read, parse, or write those values in the
configuration files yourself, and you never construct the files' paths — the CLI
owns the files, their frontmatter format, and level precedence.

## The model

Configuration is a tree of dotted `section.key` values resolved across two
levels:

- **team** — the shared, committed file. Everyone on the project sees it.
- **personal** — the local, git-ignored file. It overrides team for the same
  key.

A read with no level resolves personal-over-team; a write with no level goes to
the personal level, so an accidental change never lands in shared state.

## Managing project context

Separate from the CLI-owned values above, each config file carries a free-form
Markdown **body** below its frontmatter. Anything written there is injected as a
`## Project Context` block near the top of **every** skill's prompt, so it steers
skills without the user repeating it each invocation. The two bodies combine
team-first:

- `.luminosity/config.md` — the shared, committed **team** body.
- `.luminosity/config.local.md` — the local, git-ignored **personal** body.

Editing a body is a **user** action — unlike a `get`/`set`, which you perform
through the CLI, you do not edit these bodies yourself. When the user wants to
add or change injected project context, point them at the relevant body
(`.luminosity/config.md` for shared context, `.luminosity/config.local.md` for
personal) and let them edit it directly. To confirm a body-edit took effect, run:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/luminosity context
```

It prints the assembled block (or nothing when both bodies are empty). Add
`--skill=<skill-name>` to render that skill's own block after it, and `--explain`
to see, per level, whether each file was discovered and whether its body was
non-empty — the way to diagnose an empty or unexpected block.

## Managing skill-specific context

Context can also be scoped to a **single skill**, so it steers only that skill's
prompt rather than every skill's. It is injected as a `## Skill-Specific Context`
block immediately after the project one. As with project context, the two levels
combine team-first:

- `.luminosity/skills/configure/context.md` — the shared, committed **team**
  body.
- `.luminosity/skills/configure/context.local.md` — the local, git-ignored
  **personal** body.

The `<skill-name>` in that path is the name the skill is **invoked by** (its
frontmatter `name:`, e.g. `configure`), *not* the category directory the skill's
source happens to sit in. The user creates the nested directory and the file by
hand; a wrong or mistyped name is silent — it emits **nothing** rather than an
error, because the CLI has no registry of skills to check the name against.

As with project context, editing these bodies is a **user** action. Point the
user at the relevant file and let them edit it directly.

One hazard worth naming: a context file must not open with an **unterminated**
`---` line. A leading `---` with no closing `---` reads as an open frontmatter
block and degrades the whole block. A *terminated* `---…---` block is fine — its
content is stripped when it is YAML frontmatter, and preserved whole when it is
prose (a thematic break).

To see the root and the exact paths the CLI read, run:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --skill=configure --explain
```

## Reading a value

Run the CLI and report what it prints:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/luminosity config get <section.key>
```

Add `--level team` or `--level personal` to read exactly one level instead of
resolving across both. The command prints the value and exits 0; if the key is
not set it exits non-zero and names the key on stderr — relay that outcome
rather than guessing a value.

## Writing a value

```bash
${CLAUDE_PLUGIN_ROOT}/bin/luminosity config set <section.key> <value>
```

This writes the personal level by default. Pass `--level team` to write the
shared, committed file — only do so when the user asks to change shared state.
The command creates the configuration files on first write and reports any
conflict (for example, a key whose parent is already a value) on stderr; surface
that message rather than working around it.

## Guidance

- Take the user's `get`/`set`, the dotted key, any value, and any `--level` from
  their request and pass them straight to the command.
- If the user's intent is ambiguous (which level, or get vs set), ask before
  running a `set`.
- Report the command's stdout for a successful `get`, and its stderr message
  verbatim for any non-zero exit — do not reinterpret or infer around it.
