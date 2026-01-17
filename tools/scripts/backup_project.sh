#!/bin/bash

# backup_project.sh
# Creates a timestamped backup of the entire project

set -e

echo "💾 Creating Project Backup..."
echo ""

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_NAME=$(basename "$PROJECT_ROOT")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR=~/Projects/backups
BACKUP_NAME="${PROJECT_NAME}_backup_${TIMESTAMP}"

# Create backups directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "📦 Backing up: $PROJECT_NAME"
echo "📁 Destination: $BACKUP_DIR/$BACKUP_NAME"
echo ""

# Create backup
cd "$PROJECT_ROOT/.."
tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" \
    --exclude='*.tar.gz' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.pio' \
    --exclude='__pycache__' \
    --exclude='.vscode' \
    "$PROJECT_NAME"

# Get backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Backup created successfully!"
echo ""
echo "📦 File: ${BACKUP_NAME}.tar.gz"
echo "💾 Size: $BACKUP_SIZE"
echo "📁 Location: $BACKUP_DIR/"
echo ""
echo "🔄 To restore:"
echo "   cd ~/Projects"
echo "   tar -xzf $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo ""
echo "💡 Backups older than 30 days:"
find "$BACKUP_DIR" -name "${PROJECT_NAME}_backup_*.tar.gz" -mtime +30 -ls 2>/dev/null || echo "   None found"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
