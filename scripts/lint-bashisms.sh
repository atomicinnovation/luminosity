#!/usr/bin/env bash
# lint-bashisms.sh — fail on a denylist of bash-4-only constructs so the
# migration framework's bash-3.2 floor (ADR-0016) is not silently regressed by
# a CI runner that ships bash 5.x.
#
# KNOWN-INCOMPLETE: this catches only the *enumerated* bash-4 constructs in the
# scanner below. It cannot prove bash-3.2 compatibility — a bash-4 feature
# outside the list (e.g. the ${x@Q} transformation) would pass. The manual
# bash-3.2 replay remains the behavioural backstop; this lint is the regression
# gate for the known set. Heredoc bodies are a known minor false-positive
# surface.
#
# Usage: lint-bashisms.sh [FILE...]   (no args: scans tracked *.sh files)
# Per-line opt-out: append `# lint-bashisms: ignore` to a deliberate exception.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

is_excluded_from_default_scan() {
  case "$1" in
    */test-fixtures/* | workspaces/* | */test-helpers.sh) return 0 ;;
    *) return 1 ;;
  esac
}

scan_for_bash4_constructs() {
  awk '
    /# lint-bashisms: ignore([[:space:]]|$)/ { next }
    {
      code = $0
      sub(/(^|[[:space:]])#.*$/, "", code)
      msg = ""
      if (code ~ /(declare|local|typeset)[[:space:]]+-A/)                      msg = "associative array (declare/local/typeset -A)"                                 # lint-bashisms: ignore
      else if (code ~ /(declare|local|typeset)[[:space:]]+-[[:alpha:]]*n/)     msg = "nameref (declare/local/typeset -n)"                                           # lint-bashisms: ignore
      else if (code ~ /\$\{[^}]*:[-=+?][^}]*\\[{}]/)                           msg = "escaped brace in parameter-expansion default (bash 3.2 keeps the backslash)"  # lint-bashisms: ignore
      else if (code ~ /(^|[^[:alnum:]_])(mapfile|readarray)([^[:alnum:]_]|$)/) msg = "mapfile/readarray"                                                            # lint-bashisms: ignore
      else if (code ~ /\$\{[[:alnum:]_\[\]@*]+(\^|,)/)                         msg = "case-modification expansion (^^ ^ ,, ,)"                                      # lint-bashisms: ignore
      else if (code ~ /&>>/)                                                   msg = "&>> append-both redirect"                                                     # lint-bashisms: ignore
      else if (code ~ /\|&/)                                                   msg = "|& pipe-both"                                                                 # lint-bashisms: ignore
      else if (code ~ /\[-[[:digit:]]/)                                        msg = "negative array subscript"                                                     # lint-bashisms: ignore
      if (msg != "") {
        printf "%s:%d: bash-4 construct: %s\n", FILENAME, FNR, msg
        found = 1
      }
    }
    END { exit (found ? 1 : 0) }
  ' "$1"
}

files=()
if [[ "${#}" -gt 0 ]]; then
  files=("$@")
else
  while IFS= read -r f; do
    is_excluded_from_default_scan "${f}" && continue
    [[ -f "${REPO_ROOT}/${f}" ]] && files+=("${REPO_ROOT}/${f}")
    # git ls-files' exit status is deliberately dropped: a failure yields an
    # empty list and a clean exit, the acceptable fallback for a default scan.
  done < <(git -C "${REPO_ROOT}" ls-files '*.sh' || true)
fi

[[ "${#files[@]}" -eq 0 ]] && exit 0

status=0
for f in "${files[@]}"; do
  scan_for_bash4_constructs "${f}" || status=1
done

exit "${status}"
