#!/usr/bin/env bash
# Block destructive git commands in long Claude sessions.
# Wired into .claude/settings.local.json as a PreToolUse hook on Bash.
# Reads the proposed Bash command from stdin (JSON), exits non-zero to block.

set -euo pipefail

input="$(cat)"
cmd="$(printf '%s' "$input" | /usr/bin/python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null || true)"

block() {
  printf 'BLOCKED by block-dangerous-git.sh: %s\n' "$1" 1>&2
  printf 'If you genuinely need this, run it yourself with the ! prefix, or remove the hook for this session.\n' 1>&2
  exit 2
}

# Normalize whitespace for matching
norm="$(printf '%s' "$cmd" | tr -s '[:space:]' ' ')"

case "$norm" in
  *"git push"*)                          block "git push" ;;
  *"git reset --hard"*)                  block "git reset --hard" ;;
  *"git clean -f"*|*"git clean -fd"*|*"git clean -df"*|*"git clean -xf"*) block "git clean -f" ;;
  *"git branch -D"*|*"git branch --delete --force"*) block "git branch -D" ;;
  *"git checkout ."*|*"git checkout -- ."*) block "git checkout ." ;;
  *"git restore ."*|*"git restore --staged ."*) block "git restore ." ;;
  *"git stash drop"*|*"git stash clear"*) block "git stash drop/clear" ;;
  *"git rebase --abort"*) : ;;            # allowed (recovery)
  *"git rebase -i"*)                     block "interactive git rebase" ;;
  *"--no-verify"*)                       block "skipping git hooks (--no-verify)" ;;
  *"git filter-branch"*)                 block "git filter-branch" ;;
  *"git update-ref -d"*)                 block "git update-ref -d" ;;
esac

exit 0
