#!/bin/bash
set -Eeuo pipefail

# ================================================================
# FOLIUX VPS DEPLOYMENT SCRIPT
# Ubuntu / Django / Gunicorn / Nginx
# ================================================================

LIVE_DIR="/home/foliux"
GIT_DIR="/home/foliux_git"
VENV_PATH="$LIVE_DIR/venv"
SERVICE_NAME="gunicorn.service"
SCHEDULER_SERVICE="foliux-scheduler"
REPO_URL="https://github.com/JITENDRAKAR/foliux.git"
BRANCH="main"
DOMAIN="foliux.com"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}>>> $*${NC}"
}

success() {
    echo -e "${GREEN}SUCCESS: $*${NC}"
}

fail() {
    echo -e "${RED}ERROR: $*${NC}" >&2
    exit 1
}

trap 'echo -e "${RED}Deployment failed at line $LINENO. Check the output above.${NC}" >&2' ERR

if [ "$(id -u)" -ne 0 ]; then
    exec sudo -E bash "$0" "$@"
fi

echo
log "Starting Foliux deployment"
echo "Started: $(date)"

# ------------------------------------------------
# STEP 1: UPDATE GIT STAGING DIRECTORY
# ------------------------------------------------

log "[1/5] Updating Git repository"

if [ ! -d "$GIT_DIR/.git" ]; then
    if [ -e "$GIT_DIR" ] && [ -n "$(ls -A "$GIT_DIR" 2>/dev/null)" ]; then
        fail "$GIT_DIR exists but is not a Git repository. No files were deleted."
    fi

    mkdir -p "$(dirname "$GIT_DIR")"
    git clone --branch "$BRANCH" "$REPO_URL" "$GIT_DIR"
else
    git -C "$GIT_DIR" remote set-url origin "$REPO_URL"
    git -C "$GIT_DIR" fetch origin "$BRANCH"
    git -C "$GIT_DIR" checkout -B "$BRANCH" "origin/$BRANCH"
    git -C "$GIT_DIR" reset --hard "origin/$BRANCH"
fi

git -C "$GIT_DIR" rev-parse --verify HEAD >/dev/null
test -f "$GIT_DIR/manage.py" || fail "manage.py not found in Git repository"

NEW_VERSION="$(git -C "$GIT_DIR" rev-parse --short HEAD)"
log "Git version: $NEW_VERSION"

# ------------------------------------------------
# STEP 2: SYNCHRONIZE APPLICATION FILES
# ------------------------------------------------

log "[2/5] Synchronizing application files"

mkdir -p "$LIVE_DIR"

command -v rsync >/dev/null 2>&1 || fail "rsync is not installed"

# Deliberately omit --delete to protect existing application
# files and data. deploy.sh is excluded so this deployment
# script is not overwritten by the staging copy.
rsync -av \
    --exclude='.git/' \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='.env' \
    --exclude='/db.sqlite3' \
    --exclude='media/' \
    --exclude='staticfiles/' \
    --exclude='deploy.sh' \
    "$GIT_DIR/" "$LIVE_DIR/"

test -f "$LIVE_DIR/manage.py" || fail "manage.py missing from live directory"
test -x "$VENV_PATH/bin/python" || fail "Python virtual environment missing: $VENV_PATH"

success "Application files synchronized"

# ------------------------------------------------
# STEP 3: DEPENDENCIES, MIGRATIONS AND STATIC FILES
# ------------------------------------------------

log "[3/5] Installing dependencies"

cd "$LIVE_DIR"

"$VENV_PATH/bin/python" -m pip install -r requirements.txt

log "Running database migrations"
"$VENV_PATH/bin/python" manage.py migrate --noinput

log "Collecting static files"
"$VENV_PATH/bin/python" manage.py collectstatic --noinput

success "Dependencies, migrations and static files completed"

# ------------------------------------------------
# STEP 4: RESTART THE CORRECT APPLICATION SERVICE
# ------------------------------------------------

log "[4/5] Restarting $SERVICE_NAME"

systemctl daemon-reload

if ! systemctl cat "$SERVICE_NAME" >/dev/null 2>&1; then
    fail "$SERVICE_NAME does not exist. Refusing to start a duplicate service."
fi

systemctl restart "$SERVICE_NAME"

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl status "$SERVICE_NAME" --no-pager || true
    journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true
    fail "$SERVICE_NAME did not start successfully"
fi

success "$SERVICE_NAME is active"

# ------------------------------------------------
# STEP 5: VERIFY WEBSITE THROUGH LOCAL NGINX
# ------------------------------------------------

log "[5/5] Checking website through Nginx"

if ! systemctl is-active --quiet nginx; then
    fail "Nginx is not active. No automatic Nginx restart attempted."
fi

if ! curl -kfsSI --max-time 20 \
    --resolve "$DOMAIN:443:127.0.0.1" \
    "https://$DOMAIN/" >/dev/null; then

    echo -e "${YELLOW}Website check failed. Recent service logs:${NC}"
    journalctl -u "$SERVICE_NAME" -n 30 --no-pager || true
    fail "Website did not return a successful HTTP response"
fi

success "https://$DOMAIN/ returned a successful HTTP response"

# ------------------------------------------------
# OPTIONAL: RESTART THE EXISTING SCHEDULER
# ------------------------------------------------

if [ -f "$LIVE_DIR/foliux-scheduler.service" ]; then
    log "Updating scheduler service configuration"

    DEPLOY_USER="${SUDO_USER:-root}"

    sed \
        -e "s|{{USER}}|$DEPLOY_USER|g" \
        -e "s|{{LIVE_DIR}}|$LIVE_DIR|g" \
        "$LIVE_DIR/foliux-scheduler.service" \
        > /etc/systemd/system/foliux-scheduler.service

    systemctl daemon-reload
    systemctl enable "$SCHEDULER_SERVICE"
    systemctl restart "$SCHEDULER_SERVICE"

    if ! systemctl is-active --quiet "$SCHEDULER_SERVICE"; then
        journalctl -u "$SCHEDULER_SERVICE" -n 30 --no-pager || true
        fail "Scheduler service failed"
    fi

    success "Scheduler service is active"
fi

echo
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN} FOLIUX DEPLOYMENT COMPLETED SUCCESSFULLY ${NC}"
echo -e "${GREEN}============================================${NC}"
echo "Git version: $NEW_VERSION"
echo "Application service: $SERVICE_NAME"
echo "Website: https://$DOMAIN/"
echo "Finished: $(date)"
