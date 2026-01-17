#!/bin/bash
# Ralph Wiggum - Claude Code Adaptation
# Usage: ./ralph-claude.sh [max_iterations]
#
# This script adapts Ralph Wiggum for use with Claude Code CLI instead of Amp CLI.
# It runs Claude Code in a loop, checking after each iteration if all user stories are complete.

set -e

MAX_ITERATIONS=${1:-10}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD_FILE="$PROJECT_DIR/prd.json"
PROGRESS_FILE="$PROJECT_DIR/progress.txt"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
ARCHIVE_DIR="$PROJECT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         RALPH WIGGUM - Claude Code Edition                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check required files exist
if [ ! -f "$PRD_FILE" ]; then
    echo -e "${RED}Error: prd.json not found at $PRD_FILE${NC}"
    exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
    echo -e "${RED}Error: prompt.md not found at $PROMPT_FILE${NC}"
    exit 1
fi

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
    CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
    LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

    if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
        DATE=$(date +%Y-%m-%d)
        FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^feat/||' | sed 's|^ralph/||')
        ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

        echo -e "${YELLOW}Archiving previous run: $LAST_BRANCH${NC}"
        mkdir -p "$ARCHIVE_FOLDER"
        [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
        [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
        echo "   Archived to: $ARCHIVE_FOLDER"

        # Reset progress file for new run
        echo "## Codebase Patterns" > "$PROGRESS_FILE"
        echo "(Patterns will be added during development)" >> "$PROGRESS_FILE"
        echo "" >> "$PROGRESS_FILE"
        echo "---" >> "$PROGRESS_FILE"
        echo "" >> "$PROGRESS_FILE"
        echo "## Sprint: $(date +%Y-%m-%d)" >> "$PROGRESS_FILE"
        echo "" >> "$PROGRESS_FILE"
    fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
    CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
    if [ -n "$CURRENT_BRANCH" ]; then
        echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
    fi
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
    echo "## Codebase Patterns" > "$PROGRESS_FILE"
    echo "(Patterns will be added during development)" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "## Sprint: $(date +%Y-%m-%d)" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
fi

echo -e "${GREEN}Starting Ralph - Max iterations: $MAX_ITERATIONS${NC}"
echo ""

# Show current PRD status
echo -e "${BLUE}Current PRD Status:${NC}"
jq -r '.userStories[] | "  \(.id): \(.title) - \(if .passes then "✅ DONE" else "❌ TODO" end)"' "$PRD_FILE"
echo ""

for i in $(seq 1 $MAX_ITERATIONS); do
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Ralph Iteration $i of $MAX_ITERATIONS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

    # Check how many stories remain
    REMAINING=$(jq '[.userStories[] | select(.passes == false)] | length' "$PRD_FILE")
    echo -e "${YELLOW}Stories remaining: $REMAINING${NC}"

    if [ "$REMAINING" -eq 0 ]; then
        echo ""
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  All user stories complete! Ralph is done.                ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
        exit 0
    fi

    # Get the next story to work on
    NEXT_STORY=$(jq -r '[.userStories[] | select(.passes == false)] | sort_by(.priority) | .[0] | "\(.id): \(.title)"' "$PRD_FILE")
    echo -e "${YELLOW}Next story: $NEXT_STORY${NC}"
    echo ""

    # Change to project directory
    cd "$PROJECT_DIR"

    # Run Claude Code with the Ralph prompt
    # Using --print to show output, piping through tee for logging
    echo -e "${BLUE}Starting Claude Code...${NC}"
    echo ""

    # Read prompt and pass to Claude Code
    PROMPT=$(cat "$PROMPT_FILE")

    # Run Claude Code (interactive mode)
    # Note: Claude Code doesn't have a --dangerously-allow-all equivalent,
    # so we run it interactively and let it complete
    claude --print "$PROMPT" 2>&1 | tee /tmp/ralph-output-$i.txt || true

    # Check for completion signal in output
    if grep -q "<promise>COMPLETE</promise>" /tmp/ralph-output-$i.txt 2>/dev/null; then
        echo ""
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  Ralph completed all tasks at iteration $i!               ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
        exit 0
    fi

    echo ""
    echo -e "${YELLOW}Iteration $i complete. Sleeping 5 seconds...${NC}"
    sleep 5
done

echo ""
echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  Ralph reached max iterations ($MAX_ITERATIONS) without completing   ║${NC}"
echo -e "${RED}║  Check progress.txt for status.                          ║${NC}"
echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"

# Show final status
echo ""
echo -e "${BLUE}Final PRD Status:${NC}"
jq -r '.userStories[] | "  \(.id): \(.title) - \(if .passes then "✅ DONE" else "❌ TODO" end)"' "$PRD_FILE"

exit 1
