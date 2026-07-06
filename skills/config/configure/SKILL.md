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
---

# Configure

You manage luminosity configuration **only** through the `luminosity config`
command. You never read, parse, or write the configuration files yourself, and
you never construct their paths — the CLI owns the files, their format, and
level precedence.

## The model

Configuration is a tree of dotted `section.key` values resolved across two
levels:

- **team** — the shared, committed file. Everyone on the project sees it.
- **personal** — the local, git-ignored file. It overrides team for the same
  key.

A read with no level resolves personal-over-team; a write with no level goes to
the personal level, so an accidental change never lands in shared state.

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
