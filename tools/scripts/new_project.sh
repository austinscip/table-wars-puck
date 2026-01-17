#!/bin/bash

# new_project.sh
# Creates a new hardware project from this template

set -e

echo "🎯 Hardware Project Generator"
echo ""

# Get project name
read -p "Project name (e.g., ESP32_Sensor): " PROJECT_NAME

if [ -z "$PROJECT_NAME" ]; then
    echo "❌ Project name cannot be empty"
    exit 1
fi

# Get destination
read -p "Create in ~/Projects/? (y/n): " USE_DEFAULT
if [ "$USE_DEFAULT" = "y" ] || [ "$USE_DEFAULT" = "Y" ]; then
    DEST_DIR=~/Projects/$PROJECT_NAME
else
    read -p "Enter full path: " DEST_DIR
fi

# Check if exists
if [ -d "$DEST_DIR" ]; then
    echo "❌ Directory already exists: $DEST_DIR"
    exit 1
fi

# Get project details
echo ""
echo "📝 Project Details (optional - press enter to skip):"
read -p "Description (one line): " DESCRIPTION
read -p "Your name: " AUTHOR_NAME
read -p "CAD tool (Altium/KiCad/Eagle): " CAD_TOOL

# Create project
echo ""
echo "🔨 Creating project: $PROJECT_NAME"

# Copy template
TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cp -r "$TEMPLATE_DIR" "$DEST_DIR"

# Remove template scripts
rm -f "$DEST_DIR/tools/scripts/new_project.sh"
rm -f "$DEST_DIR/HOW_TO_USE_TEMPLATE.md"

# Customize files
cd "$DEST_DIR"

# Update README
if [ -n "$DESCRIPTION" ]; then
    sed -i.bak "s/\[One-line description of what this hardware does\]/$DESCRIPTION/g" README.md
    rm README.md.bak
fi
sed -i.bak "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" README.md
sed -i.bak "s/YYYY-MM-DD/$(date +%Y-%m-%d)/g" README.md
rm README.md.bak

# Update .claude.md
sed -i.bak "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" .claude.md
sed -i.bak "s/YYYY-MM-DD/$(date +%Y-%m-%d)/g" .claude.md
if [ -n "$CAD_TOOL" ]; then
    sed -i.bak "s/\[Altium \/ KiCad \/ Eagle \/ Other\]/$CAD_TOOL/g" .claude.md
fi
rm .claude.md.bak

# Initialize git
git init
git add .
git commit -m "Initial commit: $PROJECT_NAME

Project template initialized.
Created: $(date +%Y-%m-%d)
${AUTHOR_NAME:+Author: $AUTHOR_NAME}

🤖 Generated with [Claude Code](https://claude.com/claude-code)
${AUTHOR_NAME:+Co-Authored-By: $AUTHOR_NAME <noreply@example.com>}"

# Success!
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Project created successfully!"
echo ""
echo "📁 Location: $DEST_DIR"
echo ""
echo "🚀 Next steps:"
echo "   1. cd $DEST_DIR"
echo "   2. Update .claude.md with project details"
echo "   3. Start designing in hardware/$CAD_TOOL/"
echo "   4. Read README.md for full guide"
echo ""
echo "💡 Pro tip: Update .claude.md as you work to maintain context"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Open project
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$DEST_DIR"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$DEST_DIR" 2>/dev/null || true
fi
