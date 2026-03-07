#!/bin/bash
# =============================================================================
# PhytoSynergyDB — Database Restore Script
# =============================================================================
# Usage:
#   ./scripts/restore_db.sh                          # Lists available backups
#   ./scripts/restore_db.sh <backup_file.sql.gz>     # Restores specific backup
#
# WARNING: This will REPLACE all current data with the backup!
# =============================================================================

set -euo pipefail

BACKUP_DIR="$HOME/phytosynergy_backups"
DB_CONTAINER_NAME="phytosynergy-db-project-db-1"

# --- If no argument, list available backups ---
if [ $# -eq 0 ]; then
    echo "============================================"
    echo "  Available PhytoSynergyDB Backups"
    echo "============================================"
    echo ""
    if ls "$BACKUP_DIR"/phytosynergy_*.sql.gz 1>/dev/null 2>&1; then
        echo "  #   Size     Date                  Type         Filename"
        echo "  --- -------- --------------------- ------------ --------------------------------"
        i=1
        ls -1t "$BACKUP_DIR"/phytosynergy_*.sql.gz | while read -r f; do
            SIZE=$(du -h "$f" | cut -f1)
            BASENAME=$(basename "$f")
            # Extract type from filename
            TYPE=$(echo "$BASENAME" | sed 's/phytosynergy_\(.*\)_[0-9]\{8\}.*/\1/')
            DATE=$(stat -c '%y' "$f" 2>/dev/null || stat -f '%Sm' "$f" 2>/dev/null)
            printf "  %-3d %-8s %-21s %-12s %s\n" "$i" "$SIZE" "${DATE:0:19}" "$TYPE" "$BASENAME"
            i=$((i+1))
        done
    else
        echo "  No backups found in $BACKUP_DIR"
    fi
    echo ""
    echo "Usage: $0 <filename.sql.gz>"
    echo "  Example: $0 phytosynergy_daily_20260307_020000.sql.gz"
    exit 0
fi

BACKUP_FILE="$1"

# --- Resolve full path ---
if [ ! -f "$BACKUP_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $1"
    echo "  Checked: $1"
    echo "  Checked: $BACKUP_DIR/$1"
    echo ""
    echo "Run '$0' without arguments to list available backups."
    exit 1
fi

# --- Confirm with user ---
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "============================================"
echo "  PhytoSynergyDB — RESTORE DATABASE"
echo "============================================"
echo ""
echo "  Backup file: $(basename "$BACKUP_FILE")"
echo "  File size:   $BACKUP_SIZE"
echo ""
echo "  WARNING: This will REPLACE ALL current data!"
echo "  The current database will be OVERWRITTEN."
echo ""
read -p "  Are you sure? Type 'YES' to confirm: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo ""
    echo "  Restore cancelled."
    exit 0
fi

# --- Find database container ---
if ! docker ps --format '{{.Names}}' | grep -q "$DB_CONTAINER_NAME"; then
    DB_CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -i "db" | grep -i "phyto" | head -1)
    if [ -z "$DB_CONTAINER_NAME" ]; then
        echo "ERROR: Database container not found."
        exit 1
    fi
fi

# --- Create a safety backup before restoring ---
echo ""
echo "[1/3] Creating safety backup of current database..."
SAFETY_BACKUP="$BACKUP_DIR/phytosynergy_pre-restore_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec "$DB_CONTAINER_NAME" pg_dump \
    -U postgres -d phytosynergy_db \
    --clean --if-exists --no-owner --no-privileges \
    | gzip > "$SAFETY_BACKUP"
echo "  Safety backup: $SAFETY_BACKUP"

# --- Restore the backup ---
echo "[2/3] Restoring database from backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER_NAME" \
    psql -U postgres -d phytosynergy_db --single-transaction -q

# --- Verify ---
echo "[3/3] Verifying restore..."
RECORD_COUNT=$(docker exec "$DB_CONTAINER_NAME" psql -U postgres -d phytosynergy_db -t -c \
    "SELECT COUNT(*) FROM synergy_data_synergyexperiment;" 2>/dev/null || echo "unknown")
echo "  Synergy experiments in restored DB: $RECORD_COUNT"

echo ""
echo "============================================"
echo "  RESTORE COMPLETE"
echo "============================================"
echo "  If something went wrong, you can re-restore"
echo "  from the safety backup:"
echo "  $0 $(basename "$SAFETY_BACKUP")"
echo "============================================"
