#!/bin/bash
# =============================================================================
# PhytoSynergyDB — Setup Automated Daily Backups via Cron
# =============================================================================
# Run this ONCE on the server to enable automated daily backups at 2:00 AM
#
# Usage: ./scripts/setup_cron.sh
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_db.sh"
CRON_LOG="$HOME/phytosynergy_backups/cron_backup.log"

# Ensure backup script is executable
chmod +x "$BACKUP_SCRIPT"

# Create backup directory
mkdir -p "$HOME/phytosynergy_backups"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_db.sh"; then
    echo "Cron job already exists:"
    crontab -l | grep "backup_db.sh"
    echo ""
    read -p "Replace existing cron job? (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
    # Remove existing
    crontab -l 2>/dev/null | grep -v "backup_db.sh" | crontab -
fi

# Add cron job: Run daily at 2:00 AM
(crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT daily >> $CRON_LOG 2>&1") | crontab -

echo "============================================"
echo "  Automated Backup Cron Job Installed"
echo "============================================"
echo ""
echo "  Schedule: Every day at 2:00 AM"
echo "  Script:   $BACKUP_SCRIPT"
echo "  Log:      $CRON_LOG"
echo "  Backups:  $HOME/phytosynergy_backups/"
echo ""
echo "  Retention: Last 30 daily backups kept"
echo "  Pre-deploy backups: Kept forever"
echo ""
echo "  To verify: crontab -l"
echo "  To remove: crontab -l | grep -v backup_db.sh | crontab -"
echo "============================================"
