#!/usr/bin/env bash
#
# Hermetic tests for bin/luminosity (the entry-point bootstrap).
#
# No network: the fetcher is stubbed by a fake `curl` on PATH that serves from a
# local release directory, and the launcher is a tiny signed script. Skips
# cleanly if `minisign` is absent or the host verify shim was not built. Run
# directly: `bash scripts/test-luminosity-entrypoint.sh`.
set -uo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "${script_dir}/.." && pwd)
bootstrap="${repo_root}/bin/luminosity"

failures=0
pass() { printf 'ok - %s\n' "$1"; }
note_fail() {
  printf 'not ok - %s\n' "$1" >&2
  failures=$((failures + 1))
}

if ! command -v minisign >/dev/null 2>&1; then
  printf 'skipping: minisign not on PATH\n'
  exit 0
fi

# Host platform alias (mirror the bootstrap's detection).
case "$(uname -m)" in
  arm64 | aarch64) arch_alias=arm64 ;;
  x86_64 | amd64) arch_alias=x64 ;;
  *)
    printf 'skipping: unsupported arch\n'
    exit 0
    ;;
esac
case "$(uname -s)" in
  Darwin) os_alias=darwin ;;
  Linux) os_alias=linux ;;
  *)
    printf 'skipping: unsupported OS\n'
    exit 0
    ;;
esac
platform="${os_alias}-${arch_alias}"
host_shim="${repo_root}/bin/luminosity-verify-${platform}"
if [[ ! -x "${host_shim}" ]]; then
  printf 'skipping: verify shim not built for %s\n' "${platform}"
  exit 0
fi

work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT

# --- fixtures --------------------------------------------------------------

# A plugin root skeleton with a chosen public key.
make_plugin_root() {
  local root="$1" pubkey="$2"
  mkdir -p "${root}/.claude-plugin" "${root}/bin" "${root}/keys"
  printf '{\n  "version": "9.9.9-test"\n}\n' \
    >"${root}/.claude-plugin/plugin.json"
  cp "${host_shim}" "${root}/bin/luminosity-verify-${platform}"
  cp "${pubkey}" "${root}/keys/luminosity-release.pub"
}

# A signed fake launcher: exits with the code named by its first arg after
# "exit-", else prints its args. Placed + signed into a release dir.
make_release() {
  local release="$1" secret="$2"
  mkdir -p "${release}"
  local launcher="${release}/luminosity-${platform}"
  cat >"${launcher}" <<'LAUNCHER'
#!/bin/sh
case "${1:-}" in
	exit-*) exit "${1#exit-}" ;;
	*) printf 'LAUNCHER RAN: %s\n' "$*" ;;
esac
LAUNCHER
  chmod +x "${launcher}"
  minisign -S -s "${secret}" -x "${launcher}.minisig" -m "${launcher}" \
    >/dev/null 2>&1
}

# A fake curl that serves release files by basename and counts hits.
make_fake_curl() {
  local bindir="$1" release="$2" hits="$3"
  mkdir -p "${bindir}"
  cat >"${bindir}/curl" <<CURL
#!/usr/bin/env bash
out=""; url=""
while [[ \$# -gt 0 ]]; do
	case "\$1" in
		-o) out="\$2"; shift 2 ;;
		-*) shift ;;
		*) url="\$1"; shift ;;
	esac
done
printf 'x' >> "${hits}"
src="${release}/\$(basename "\$url")"
[[ -f "\$src" ]] || exit 22
cp "\$src" "\$out"
CURL
  chmod +x "${bindir}/curl"
}

new_key() {
  local dir="$1" name="$2"
  minisign -G -W -f -p "${dir}/${name}.pub" -s "${dir}/${name}.key" \
    >/dev/null 2>&1
}

# Run the bootstrap in a controlled environment. Args after the first 3 are
# forwarded to the bootstrap.
run_bootstrap() {
  local root="$1" release="$2" cachedir="$3"
  shift 3
  local bindir="${work}/fakebin-$$-${RANDOM}"
  local hits="${cachedir}/.hits"
  : >"${hits}"
  make_fake_curl "${bindir}" "${release}" "${hits}"
  CLAUDE_PLUGIN_ROOT="${root}" \
    LUMINOSITY_CACHE_DIR="${cachedir}" \
    LUMINOSITY_RELEASE_BASE_URL="http://mock.invalid/download" \
    PATH="${bindir}:${PATH}" \
    "${bootstrap}" "$@"
}

# --- tests -----------------------------------------------------------------

test_unset_plugin_root() {
  local out
  if out=$(CLAUDE_PLUGIN_ROOT="" "${bootstrap}" version 2>&1); then
    note_fail "unset CLAUDE_PLUGIN_ROOT → named error (exited zero)"
  elif printf '%s' "${out}" | grep -q "CLAUDE_PLUGIN_ROOT"; then
    pass "unset CLAUDE_PLUGIN_ROOT → named error"
  else
    note_fail "unset CLAUDE_PLUGIN_ROOT → named error (${out})"
  fi
}

test_happy_fetch_and_forward() {
  local d="${work}/happy"
  mkdir -p "${d}/cache"
  new_key "${d}" release
  make_plugin_root "${d}/root" "${d}/release.pub"
  make_release "${d}/rel" "${d}/release.key"
  local out
  out=$(run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" hello world)
  if printf '%s' "${out}" | grep -q "LAUNCHER RAN: hello world"; then
    pass "happy path fetches, verifies, execs, forwards args"
  else
    note_fail "happy path fetches, verifies, execs, forwards args (${out})"
  fi
}

test_exit_code_forwarding() {
  local d="${work}/exitcode"
  mkdir -p "${d}/cache"
  new_key "${d}" release
  make_plugin_root "${d}/root" "${d}/release.pub"
  make_release "${d}/rel" "${d}/release.key"
  local rc=0
  run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" exit-7 >/dev/null 2>&1 ||
    rc=$?
  if [[ ${rc} -eq 7 ]]; then
    pass "launcher exit code propagates"
  else
    note_fail "launcher exit code propagates (rc=${rc})"
  fi
}

test_cache_short_circuits() {
  local d="${work}/cache-reuse"
  mkdir -p "${d}/cache"
  new_key "${d}" release
  make_plugin_root "${d}/root" "${d}/release.pub"
  make_release "${d}/rel" "${d}/release.key"
  run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" first >/dev/null 2>&1
  # Delete the release so a second fetch WOULD fail; a cache hit must not fetch.
  rm -rf "${d}/rel"
  local out
  out=$(run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" second 2>&1)
  if printf '%s' "${out}" | grep -q "LAUNCHER RAN: second"; then
    pass "cached launcher is reused without refetching"
  else
    note_fail "cached launcher is reused without refetching (${out})"
  fi
}

test_tampered_cache_fails_closed() {
  local d="${work}/tampered"
  mkdir -p "${d}/cache"
  new_key "${d}" release
  make_plugin_root "${d}/root" "${d}/release.pub"
  make_release "${d}/rel" "${d}/release.key"
  run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" first >/dev/null 2>&1
  # Poison the cached launcher AND remove the release so no clean refetch.
  printf 'poisoned' >"${d}/cache/luminosity-launcher-9.9.9-test-${platform}"
  rm -rf "${d}/rel"
  local out
  if out=$(run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" go 2>&1); then
    note_fail "poisoned cache entry is refused (exited zero)"
  elif printf '%s' "${out}" | grep -q "LAUNCHER RAN"; then
    note_fail "poisoned cache entry is refused (exec'd anyway)"
  else
    pass "poisoned cache entry is refused, not exec'd (fail-closed)"
  fi
}

test_non_release_key_fails_closed() {
  local d="${work}/wrongkey"
  mkdir -p "${d}/cache"
  new_key "${d}" release
  new_key "${d}" attacker
  make_plugin_root "${d}/root" "${d}/release.pub"
  # Sign the launcher with the ATTACKER key; the plugin trusts the release key.
  make_release "${d}/rel" "${d}/attacker.key"
  local out
  if out=$(run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" go 2>&1); then
    note_fail "non-release-key launcher is refused (exited zero)"
  elif printf '%s' "${out}" | grep -q "LAUNCHER RAN"; then
    note_fail "non-release-key launcher is refused (exec'd anyway)"
  else
    pass "non-release-key launcher is refused (fail-closed)"
  fi
}

test_path_decoy_shim_not_used() {
  local d="${work}/decoy"
  mkdir -p "${d}/cache"
  new_key "${d}" release
  new_key "${d}" attacker
  make_plugin_root "${d}/root" "${d}/release.pub"
  # Attacker-signed launcher + a PATH-planted decoy `luminosity-verify` that
  # always succeeds. The bootstrap must invoke the real shim by absolute path.
  make_release "${d}/rel" "${d}/attacker.key"
  local decoybin="${d}/decoybin"
  mkdir -p "${decoybin}"
  printf '#!/bin/sh\nexit 0\n' >"${decoybin}/luminosity-verify"
  chmod +x "${decoybin}/luminosity-verify"
  local out
  if out=$(PATH="${decoybin}:${PATH}" \
    run_bootstrap "${d}/root" "${d}/rel" "${d}/cache" go 2>&1); then
    note_fail "PATH-planted decoy shim is not used (exited zero)"
  elif printf '%s' "${out}" | grep -q "LAUNCHER RAN"; then
    note_fail "PATH-planted decoy shim is not used (exec'd anyway)"
  else
    pass "PATH-planted decoy shim is not used (absolute-path invocation)"
  fi
}

test_readonly_root_falls_back() {
  local d="${work}/readonly"
  mkdir -p "${d}/xdg"
  new_key "${d}" release
  make_plugin_root "${d}/root" "${d}/release.pub"
  make_release "${d}/rel" "${d}/release.key"
  chmod 0555 "${d}/root/bin"
  local bindir="${d}/fakebin"
  local hits="${d}/hits"
  : >"${hits}"
  make_fake_curl "${bindir}" "${d}/rel" "${hits}"
  local out
  out=$(CLAUDE_PLUGIN_ROOT="${d}/root" \
    XDG_CACHE_HOME="${d}/xdg" \
    LUMINOSITY_RELEASE_BASE_URL="http://mock.invalid/download" \
    PATH="${bindir}:${PATH}" \
    "${bootstrap}" ok 2>&1)
  chmod 0755 "${d}/root/bin" # so cleanup can remove it
  if printf '%s' "${out}" | grep -q "LAUNCHER RAN: ok" &&
    [[ -f "${d}/xdg/luminosity/luminosity-launcher-9.9.9-test-${platform}" ]]; then
    pass "read-only plugin root falls back to XDG and still runs"
  else
    note_fail "read-only plugin root falls back to XDG (${out})"
  fi
}

test_unset_plugin_root
test_happy_fetch_and_forward
test_exit_code_forwarding
test_cache_short_circuits
test_tampered_cache_fails_closed
test_non_release_key_fails_closed
test_path_decoy_shim_not_used
test_readonly_root_falls_back

if [[ ${failures} -eq 0 ]]; then
  printf 'all entry-point tests passed\n'
else
  printf '%d entry-point test(s) failed\n' "${failures}" >&2
  exit 1
fi
