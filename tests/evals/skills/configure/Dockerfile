# syntax=docker/dockerfile:1
#
# Host-independent sandbox for the configure skill eval. macOS is a first-class
# dev host, and build:launcher only ever produces darwin triples that cannot run
# in a Linux container, so the image consumes the cross-built linux-musl launcher
# from build:release at a pinned linux/amd64 platform.
#
# The Claude Code CLI is a Node application, so the runtime needs Node; the
# pinned npm install (not a floating @latest) plus a cache clean keeps the image
# an immutable, reproducible contract. npm-registry access is a build-time
# prerequisite (an air-gapped build would need a mirror).
FROM node:22-bookworm-slim

# Hand-synced mirror of CC_VERSION in configure_eval.py; at or above the
# plugin's v2.1.144 skill-preload floor.
ARG CLAUDE_CODE_VERSION=2.1.203
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force

# The plugin tree the skill resolves via ${CLAUDE_PLUGIN_ROOT}. bin/luminosity
# is the REAL cross-built launcher, not the shipped release-fetching shim (which
# would fetch a nonexistent prerelease from GitHub and minisign-verify it against
# a signature no developer can produce). Dropping the shim lets the eval grade
# config behaviour through the exact path the skill's allowed-tools permits, with
# no network fetch or verification. The baseline arm finds the same binary on
# PATH to self-discover.
ENV CLAUDE_PLUGIN_ROOT=/opt/luminosity
COPY cli/launcher/bin/luminosity-linux-x64 /opt/luminosity/bin/luminosity
RUN chmod +x /opt/luminosity/bin/luminosity \
    && ln -s /opt/luminosity/bin/luminosity /usr/local/bin/luminosity

WORKDIR /work
