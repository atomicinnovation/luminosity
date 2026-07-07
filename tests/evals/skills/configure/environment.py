"""Sandbox-side constants shared by the solver and scorer.

Kept in a leaf module so the solver (which seeds the fixture) and the scorer
(which re-reads it) can both import them without a cycle.
"""

# The agent's working directory inside the sandbox: claude_code() is rooted
# here, seed_fixtures writes the .git boundary + .luminosity tree here, and the
# scorer runs its level-scoped re-reads here.
WORKDIR = "/work"

# The launcher binary, on PATH in the sandbox image. The agent invokes it via
# ${CLAUDE_PLUGIN_ROOT}/bin/luminosity; the scorer's own re-reads call the same
# binary by name.
LUMINOSITY_BIN = "luminosity"
