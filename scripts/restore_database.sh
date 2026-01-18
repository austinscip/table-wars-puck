#!/bin/bash
# TABLE WARS - PostgreSQL Database Restore Script
# Restores database from a backup file

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "╔═══════════════════════════════════════════╗"
echo "║   TABLE WARS - Database Restore Script   ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Check if backup file was provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    find /Users/austinscipione/table-wars-puck/backups -name "*.sql.gz" -exec ls -lh {} \; | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}'
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Check if Docker container is running
if ! docker ps | grep -q tablewars-db; then
    echo -e "${RED}❌ Error: PostgreSQL container 'tablewars-db' is not running${NC}"
    echo "   Start it with: docker-compose up -d postgres"
    exit 1
fi

# Confirm restore
echo -e "${YELLOW}⚠️  WARNING: This will replace ALL current data!${NC}"
echo "   Backup file: $BACKUP_FILE"
echo "   Database: tablewars_prod"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Create a safety backup before restore
echo -e "${YELLOW}📦 Creating safety backup of current database...${NC}"
SAFETY_BACKUP="/tmp/tablewars_pre_restore_$(date +%Y%m%d_%H%M%S).sql"
docker exec tablewars-db pg_dump -U tablewars_user tablewars_prod > "$SAFETY_BACKUP"
echo -e "${GREEN}✅ Safety backup created: $SAFETY_BACKUP${NC}"

# Decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}🗜️  Decompressing backup...${NC}"
    TEMP_SQL="/tmp/tablewars_restore_temp.sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_SQL"
    SQL_FILE="$TEMP_SQL"
else
    SQL_FILE="$BACKUP_FILE"
fi

# Restore database
echo -e "${YELLOW}📥 Restoring database...${NC}"
if docker exec -i tablewars-db psql -U tablewars_user tablewars_prod < "$SQL_FILE"; then
    echo -e "${GREEN}✅ Database restored successfully${NC}"

    # Clean up temp file
    if [ -f "$TEMP_SQL" ]; then
        rm "$TEMP_SQL"
    fi

    echo ""
    echo "═══════════════════════════════════════════"
    echo "Restore complete!"
    echo "═══════════════════════════════════════════"
    echo "Safety backup preserved at: $SAFETY_BACKUP"
    echo ""
    echo "You may want to restart the app:"
    echo "  docker-compose restart app"
else
    echo -e "${RED}❌ Restore failed${NC}"
    echo "Your original data is preserved."
    echo "Safety backup: $SAFETY_BACKUP"
    exit 1
fi
