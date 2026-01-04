#!/bin/bash

# version_bump.sh
# Increments version numbers across project files

set -e

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "📈 Version Bump Utility"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "❌ You have uncommitted changes. Commit or stash them first."
    exit 1
fi

# Get current version from git tags
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')

if [ -z "$CURRENT_VERSION" ]; then
    echo "No version tags found. Creating initial version v0.1.0"
    NEW_VERSION="0.1.0"
else
    echo "Current version: v$CURRENT_VERSION"
    echo ""

    # Parse version
    MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
    MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
    PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)

    # Get bump type from argument
    BUMP_TYPE=${1:-patch}

    case $BUMP_TYPE in
        major)
            MAJOR=$((MAJOR + 1))
            MINOR=0
            PATCH=0
            echo "🔴 MAJOR version bump (incompatible hardware changes)"
            ;;
        minor)
            MINOR=$((MINOR + 1))
            PATCH=0
            echo "🟡 MINOR version bump (new features, same hardware)"
            ;;
        patch)
            PATCH=$((PATCH + 1))
            echo "🟢 PATCH version bump (bug fixes)"
            ;;
        *)
            echo "Usage: $0 [major|minor|patch]"
            echo ""
            echo "Examples:"
            echo "  major: 1.0.0 → 2.0.0 (new PCB revision, incompatible changes)"
            echo "  minor: 1.0.0 → 1.1.0 (new firmware feature, same hardware)"
            echo "  patch: 1.0.0 → 1.0.1 (bug fix, same hardware)"
            exit 1
            ;;
    esac

    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
fi

echo ""
echo "New version: v$NEW_VERSION"
echo ""

# Update README.md if it exists
if [ -f "README.md" ]; then
    if grep -q "Version:" README.md; then
        sed -i.bak "s/\*\*Version:\*\* \[.*\]/\*\*Version:\*\* $NEW_VERSION/g" README.md
        sed -i.bak "s/\*\*Version:\*\* v[0-9.]\+/\*\*Version:\*\* $NEW_VERSION/g" README.md
        rm README.md.bak
        echo "✓ Updated README.md"
    fi
fi

# Update .claude.md if it exists
if [ -f ".claude.md" ]; then
    if grep -q "Current Version:" .claude.md; then
        sed -i.bak "s/\*\*Current Version:\*\* v[0-9.]\+/\*\*Current Version:\*\* v$NEW_VERSION/g" .claude.md
        rm .claude.md.bak
        echo "✓ Updated .claude.md"
    fi
fi

# Prompt for changelog entry
echo ""
echo "📝 Enter changelog entry for this version:"
echo "(Describe what changed - press Ctrl+D when done)"
echo ""
CHANGELOG_ENTRY=$(cat)

# Get today's date
TODAY=$(date +%Y-%m-%d)

# Update CHANGELOG.md if it exists
if [ -f "CHANGELOG.md" ]; then
    # Create new entry
    NEW_ENTRY="## [$NEW_VERSION] - $TODAY\n\n$CHANGELOG_ENTRY\n\n"

    # Insert after "## [Unreleased]" section
    if grep -q "## \[Unreleased\]" CHANGELOG.md; then
        awk -v new="$NEW_ENTRY" '/## \[Unreleased\]/{print; print ""; print new; next}1' CHANGELOG.md > CHANGELOG.md.tmp
        mv CHANGELOG.md.tmp CHANGELOG.md
        echo "✓ Updated CHANGELOG.md"
    fi
fi

# Commit changes
echo ""
echo "💾 Committing version bump..."
git add .
git commit -m "Bump version to v$NEW_VERSION

$CHANGELOG_ENTRY

🤖 Generated with Claude Code
Co-Authored-By: Version Script <noreply@version.sh>"

# Create tag
git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION

$CHANGELOG_ENTRY"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Version bumped to v$NEW_VERSION"
echo ""
echo "📋 Changes committed and tagged"
echo ""
echo "🚀 Next steps:"
echo "   1. Review: git log -1"
echo "   2. Push: git push origin main"
echo "   3. Push tag: git push origin v$NEW_VERSION"
echo ""
echo "💡 To undo: git tag -d v$NEW_VERSION && git reset HEAD~1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
