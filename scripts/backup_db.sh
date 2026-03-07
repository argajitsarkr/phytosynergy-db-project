#!/bin/bash
# =============================================================================
# PhytoSynergyDB — Automated PostgreSQL Backup Script
# =============================================================================
# Usage:
#   ./scripts/backup_db.sh              # Standard daily backup
#   ./scripts/backup_db.sh pre-deploy   # Pre-deployment snapshot
#   ./scripts/backup_db.sh manual       # Manual backup with custom tag
#
# Backups are stored in: ~/phytosynergy_backups/
# Retention: Keeps last 30 daily backups, all pre-deploy backups kept forever
# =============================================================================

set -euo pipefail

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$HOME/phytosynergy_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_TYPE="${1:-daily}"
DB_CONTAINER_NAME="phytosynergy-db-project-db-1"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# --- Determine backup filename ---
case "$BACKUP_TYPE" in
    pre-deploy)
        FILENAME="phytosynergy_pre-deploy_${TIMESTAMP}.sql.gz"
        ;;
    manual)
        FILENAME="phytosynergy_manual_${TIMESTAMP}.sql.gz"
        ;;
    *)
        FILENAME="phytosynergy_daily_${TIMESTAMP}.sql.gz"
        ;;
esac

BACKUP_PATH="$BACKUP_DIR/$FILENAME"

echo "============================================"
echo "  PhytoSynergyDB Backup"
echo "============================================"
echo "  Type:      $BACKUP_TYPE"
echo "  Timestamp: $TIMESTAMP"
echo "  Output:    $BACKUP_PATH"
echo "============================================"

# --- Check if database container is running ---
if ! docker ps --format '{{.Names}}' | grep -q "$DB_CONTAINER_NAME"; then
    # Try alternate naming convention
    DB_CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -i "db" | grep -i "phyto" | head -1)
    if [ -z "$DB_CONTAINER_NAME" ]; then
        echo "ERROR: Database container not found. Is Docker Compose running?"
        echo "  Run: docker ps   to check running containers"
        exit 1
    fi
fi

echo "  Container: $DB_CONTAINER_NAME"
echo ""

# --- Perform pg_dump ---
echo "[1/3] Dumping PostgreSQL database..."
docker exec "$DB_CONTAINER_NAME" pg_dump \
    -U postgres \
    -d phytosynergy_db \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --format=plain \
    | gzip > "$BACKUP_PATH"

# --- Verify backup ---
echo "[2/3] Verifying backup..."
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
if [ ! -s "$BACKUP_PATH" ]; then
    echo "ERROR: Backup file is empty! Something went wrong."
    rm -f "$BACKUP_PATH"
    exit 1
fi
echo "  Backup size: $BACKUP_SIZE"

# --- Cleanup old daily backups (keep last 30) ---
echo "[3/3] Cleaning up old daily backups (keeping last 30)..."
if [ "$BACKUP_TYPE" = "daily" ]; then
    ls -1t "$BACKUP_DIR"/phytosynergy_daily_*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
    REMAINING=$(ls -1 "$BACKUP_DIR"/phytosynergy_daily_*.sql.gz 2>/dev/null | wc -l)
    echo "  Daily backups retained: $REMAINING"
fi

echo ""
echo "============================================"
echo "  BACKUP COMPLETE"
echo "  File: $BACKUP_PATH"
echo "  Size: $BACKUP_SIZE"
echo "============================================"

# --- List recent backups ---
echo ""
echo "Recent backups:"
ls -lht "$BACKUP_DIR"/phytosynergy_*.sql.gz 2>/dev/null | head -5
