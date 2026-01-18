#!/bin/bash
# TABLE WARS - PostgreSQL Database Backup Script
# Automatically backs up the database and manages retention

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Users/austinscipione/table-wars-puck/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m)
BACKUP_FILE="tablewars_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=30  # Keep backups for 30 days

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "╔═══════════════════════════════════════════╗"
echo "║   TABLE WARS - Database Backup Script    ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR/$DATE_DIR"

# Check if Docker container is running
if ! docker ps | grep -q tablewars-db; then
    echo -e "${RED}❌ Error: PostgreSQL container 'tablewars-db' is not running${NC}"
    echo "   Start it with: docker-compose up -d postgres"
    exit 1
fi

# Create backup
echo -e "${YELLOW}📦 Creating database backup...${NC}"
if docker exec tablewars-db pg_dump -U tablewars_user tablewars_prod > "$BACKUP_DIR/$DATE_DIR/$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$DATE_DIR/$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup created successfully${NC}"
    echo "   File: $BACKUP_DIR/$DATE_DIR/$BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Compress backup
echo -e "${YELLOW}🗜️  Compressing backup...${NC}"
gzip "$BACKUP_DIR/$DATE_DIR/$BACKUP_FILE"
COMPRESSED_SIZE=$(du -h "$BACKUP_DIR/$DATE_DIR/$BACKUP_FILE.gz" | cut -f1)
echo -e "${GREEN}✅ Backup compressed${NC}"
echo "   Compressed size: $COMPRESSED_SIZE"

# Clean up old backups
echo -e "${YELLOW}🧹 Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"
DELETED_COUNT=$(find "$BACKUP_DIR" -name "tablewars_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Deleted $DELETED_COUNT old backup(s)${NC}"
else
    echo "   No old backups to delete"
fi

# Show backup summary
echo ""
echo "═══════════════════════════════════════════"
echo "Backup Summary:"
echo "═══════════════════════════════════════════"
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "tablewars_backup_*.sql.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "Total backups: $TOTAL_BACKUPS"
echo "Total size: $TOTAL_SIZE"
echo ""
echo "Recent backups:"
ls -lht "$BACKUP_DIR"/*/*.sql.gz 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo -e "${GREEN}✅ Backup complete!${NC}"
