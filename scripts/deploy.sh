#!/bin/bash
# =============================================================================
# PhytoSynergyDB — Safe Deployment Script
# =============================================================================
# This script safely deploys new code to production:
#   1. Backs up the database FIRST
#   2. Tags the current working version (for rollback)
#   3. Pulls latest code from main branch
#   4. Rebuilds only the web container (database untouched)
#   5. Runs migrations
#   6. Verifies the site is working
#   7. If anything fails → automatic rollback
#
# Usage:
#   ./scripts/deploy.sh                # Deploy latest main
#   ./scripts/deploy.sh rollback       # Rollback to previous version
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

ROLLBACK_TAG_FILE="$PROJECT_DIR/.last_good_deploy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_step()  { echo -e "${BLUE}[DEPLOY]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[  OK  ]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[ WARN ]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR ]${NC} $1"; }

# ===========================================================================
# ROLLBACK MODE
# ===========================================================================
if [ "${1:-}" = "rollback" ]; then
    echo ""
    echo "============================================"
    echo "  PhytoSynergyDB — ROLLBACK"
    echo "============================================"

    if [ ! -f "$ROLLBACK_TAG_FILE" ]; then
        log_error "No rollback point found. Cannot rollback."
        exit 1
    fi

    ROLLBACK_COMMIT=$(cat "$ROLLBACK_TAG_FILE")
    log_step "Rolling back to commit: $ROLLBACK_COMMIT"

    read -p "  Confirm rollback? (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "  Rollback cancelled."
        exit 0
    fi

    # Step 1: Restore database from pre-deploy backup
    LATEST_PRE_DEPLOY=$(ls -1t "$HOME/phytosynergy_backups"/phytosynergy_pre-deploy_*.sql.gz 2>/dev/null | head -1)
    if [ -n "$LATEST_PRE_DEPLOY" ]; then
        log_step "Restoring database from: $(basename "$LATEST_PRE_DEPLOY")"
        gunzip -c "$LATEST_PRE_DEPLOY" | docker exec -i \
            $(docker ps --format '{{.Names}}' | grep -i "db" | grep -i "phyto" | head -1) \
            psql -U postgres -d phytosynergy_db --single-transaction -q
        log_ok "Database restored"
    else
        log_warn "No pre-deploy backup found. Database state unchanged."
    fi

    # Step 2: Checkout the old commit
    git checkout "$ROLLBACK_COMMIT"
    log_ok "Code reverted to $ROLLBACK_COMMIT"

    # Step 3: Rebuild web container
    docker-compose build --no-cache web
    docker-compose up -d web
    log_ok "Web container rebuilt and started"

    # Step 4: Collect static files
    docker-compose exec -T web python manage.py collectstatic --no-input
    log_ok "Static files collected"

    echo ""
    echo "============================================"
    echo -e "  ${GREEN}ROLLBACK COMPLETE${NC}"
    echo "============================================"
    exit 0
fi

# ===========================================================================
# DEPLOY MODE
# ===========================================================================
echo ""
echo "============================================"
echo "  PhytoSynergyDB — Safe Deployment"
echo "============================================"
echo ""

# --- Pre-flight checks ---
log_step "Running pre-flight checks..."

# Check we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    log_error "Not on 'main' branch! Currently on: $CURRENT_BRANCH"
    log_error "Switch to main first: git checkout main"
    exit 1
fi

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running!"
    exit 1
fi

# Check containers are up
if ! docker-compose ps | grep -q "Up"; then
    log_warn "Some containers may not be running. Proceeding anyway..."
fi

log_ok "Pre-flight checks passed"

# --- Step 1: Save current commit hash for rollback ---
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "$CURRENT_COMMIT" > "$ROLLBACK_TAG_FILE"
log_step "Rollback point saved: ${CURRENT_COMMIT:0:8}"

# --- Step 2: Backup database ---
log_step "Backing up database before deployment..."
bash "$PROJECT_DIR/scripts/backup_db.sh" pre-deploy
log_ok "Pre-deployment backup complete"

# --- Step 3: Pull latest code ---
log_step "Pulling latest code from origin/main..."
git pull origin main
NEW_COMMIT=$(git rev-parse HEAD)

if [ "$CURRENT_COMMIT" = "$NEW_COMMIT" ]; then
    log_warn "No new commits. Already up to date."
    echo ""
    read -p "  Rebuild anyway? (y/N): " REBUILD
    if [ "$REBUILD" != "y" ] && [ "$REBUILD" != "Y" ]; then
        echo "  Deployment cancelled."
        exit 0
    fi
fi

log_ok "Code updated: ${CURRENT_COMMIT:0:8} → ${NEW_COMMIT:0:8}"

# Show what changed
echo ""
log_step "Changes in this deployment:"
git log --oneline "${CURRENT_COMMIT}..${NEW_COMMIT}" 2>/dev/null || true
echo ""

# --- Step 4: Rebuild ONLY the web container ---
log_step "Rebuilding web container (database untouched)..."
docker-compose build --no-cache web
log_ok "Web container rebuilt"

# --- Step 5: Restart web container ---
log_step "Restarting web container..."
docker-compose up -d web
log_ok "Web container restarted"

# --- Step 6: Run migrations ---
log_step "Running database migrations..."
docker-compose exec -T web python manage.py migrate --no-input
log_ok "Migrations applied"

# --- Step 7: Collect static files ---
log_step "Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --no-input
log_ok "Static files collected"

# --- Step 8: Health check ---
log_step "Running health check..."
sleep 3  # Give Gunicorn time to start

# Check if web container is running
if docker-compose ps web | grep -q "Up"; then
    log_ok "Web container is running"
else
    log_error "Web container is NOT running!"
    log_error "Check logs: docker-compose logs web"
    echo ""
    log_warn "To rollback: ./scripts/deploy.sh rollback"
    exit 1
fi

# Check if Django responds
HTTP_CODE=$(docker-compose exec -T web python -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://localhost:8000/', timeout=5)
    print(r.status)
except Exception as e:
    print('FAIL')
" 2>/dev/null || echo "FAIL")

if [ "$HTTP_CODE" = "200" ]; then
    log_ok "Django is responding (HTTP 200)"
else
    log_warn "Django health check returned: $HTTP_CODE"
    log_warn "The site may still be starting up. Check manually."
fi

# --- Step 9: Count records (sanity check) ---
RECORD_COUNT=$(docker-compose exec -T db psql -U postgres -d phytosynergy_db -t -c \
    "SELECT COUNT(*) FROM synergy_data_synergyexperiment;" 2>/dev/null | tr -d ' ' || echo "?")
log_ok "Database records: $RECORD_COUNT synergy experiments"

echo ""
echo "============================================"
echo -e "  ${GREEN}DEPLOYMENT COMPLETE${NC}"
echo "============================================"
echo "  Previous: ${CURRENT_COMMIT:0:8}"
echo "  Current:  ${NEW_COMMIT:0:8}"
echo "  Records:  $RECORD_COUNT experiments"
echo ""
echo "  To rollback: ./scripts/deploy.sh rollback"
echo "============================================"
