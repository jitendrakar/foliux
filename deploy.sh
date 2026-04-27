#!/bin/bash

# ================================================================= #
# FOLIUX VPS DEPLOYMENT SCRIPT (Ubuntu)                             #
# ================================================================= #

# Configuration
LIVE_DIR="/home/foliux"
GIT_DIR="/home/foliux_git"
VENV_PATH="$LIVE_DIR/venv"
SERVICE_NAME="foliux"
REPO_URL="https://github.com/JITENDRAKAR/foliux.git"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Two-Step Deployment...${NC}"

check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1 successful.${NC}"
    else
        echo -e "${RED}❌ $1 failed!${NC}"
        [ ! -z "$2" ] && echo "$2" | tail -n 10
        exit 1
    fi
}

# --- STEP 1: UPDATE GIT STAGING AREA ---
echo -e "\n${BLUE}📥 1. Updating staging area ($GIT_DIR)...${NC}"
if [ ! -d "$GIT_DIR" ]; then
    echo -e "${YELLOW}Creating staging directory...${NC}"
    git clone $REPO_URL $GIT_DIR
    check_status "Initial clone"
fi

cd $GIT_DIR || exit 1
OLD_VERSION=$(git rev-parse HEAD)
PULL_OUTPUT=$(git pull origin main 2>&1)

if [[ "$PULL_OUTPUT" == *"Authentication failed"* ]]; then
    echo -e "${RED}❌ Auth Error: Use your Personal Access Token as the password.${NC}"
    exit 1
fi
check_status "Git pull" "$PULL_OUTPUT"
NEW_VERSION=$(git rev-parse HEAD)

# --- STEP 2: SYNC TO LIVE DIRECTORY ---
echo -e "\n${BLUE}🔄 2. Syncing changes to live directory ($LIVE_DIR)...${NC}"
if [ ! -d "$LIVE_DIR" ]; then mkdir -p $LIVE_DIR; fi

# Use rsync to safely copy files while excluding environment-specific data
rsync -av --delete \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '.env' \
    --exclude 'db.sqlite3' \
    --exclude 'media/' \
    --exclude 'static/' \
    $GIT_DIR/ $LIVE_DIR/
check_status "File sync"

# --- STEP 3: LIVE DEPLOYMENT ---
echo -e "\n${BLUE}⚙️ 3. Finalizing deployment in live folder...${NC}"
cd $LIVE_DIR || exit 1

# Updated Files List
if [ "$OLD_VERSION" != "$NEW_VERSION" ]; then
    echo -e "${YELLOW}📂 Changes detected:${NC}"
    cd $GIT_DIR && git diff --name-status $OLD_VERSION $NEW_VERSION | sed 's/^/  /' && cd $LIVE_DIR
fi

# Venv and Migrations
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    pip install -r requirements.txt > /dev/null
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    check_status "Django tasks"
else
    echo -e "${RED}❌ Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi

# Restart Service
echo -e "\n${BLUE}🔄 4. Restarting service ($SERVICE_NAME)...${NC}"
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl daemon-reload && sudo systemctl restart $SERVICE_NAME
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}✅ Service is active.${NC}"
    else
        echo -e "${RED}❌ Service failed!${NC}"
        sudo journalctl -u $SERVICE_NAME -n 10 --no-pager
        exit 1
    fi
fi

echo -e "\n${GREEN}✨ DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}🕒 Time: $(date)${NC}"
