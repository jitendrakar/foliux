#!/bin/bash

# ================================================================= #
# FOLIUX VPS DEPLOYMENT SCRIPT (Ubuntu)                             #
# ================================================================= #

# Configuration
LIVE_DIR="/home/foliux"
GIT_DIR="/home/foliux_git"
VENV_PATH="$LIVE_DIR/venv"
SERVICE_NAME="foliux"
REPO_URL="https://JITENDRAKAR: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@github.com/JITENDRAKAR/foliux.git"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}>>> Starting Two-Step Deployment...${NC}"

check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SUCCESS: $1.${NC}"
    else
        echo -e "${RED}ERROR: $1 failed!${NC}"
        [ ! -z "$2" ] && echo "$2" | tail -n 10
        exit 1
    fi
}

# --- STEP 1: UPDATE GIT STAGING AREA ---
echo -e "\n${BLUE}[1/4] Updating staging area ($GIT_DIR)...${NC}"

# Create staging directory if it doesn't exist
if [ ! -d "$GIT_DIR" ]; then
    echo -e "${YELLOW}Initial setup: Creating staging directory...${NC}"
    sudo mkdir -p "$GIT_DIR"
    sudo chown $USER:$USER "$GIT_DIR"
    git clone $REPO_URL $GIT_DIR
    check_status "Initial clone"
fi

cd $GIT_DIR || exit 1
OLD_VERSION=$(git rev-parse HEAD)

# Ensure the remote URL uses the token for authentication
git remote set-url origin $REPO_URL

# Pull latest changes
echo -e "${YELLOW}Pulling latest changes from GitHub...${NC}"
PULL_OUTPUT=$(git pull origin main 2>&1)

if [[ "$PULL_OUTPUT" == *"Authentication failed"* ]]; then
    echo -e "${RED}AUTH ERROR: Use your Personal Access Token as the password.${NC}"
    exit 1
fi
check_status "Git pull" "$PULL_OUTPUT"
NEW_VERSION=$(git rev-parse HEAD)

# --- SAFETY CHECK ---
if [ ! -f "$GIT_DIR/manage.py" ]; then
    echo -e "${RED}CRITICAL SAFETY ERROR: manage.py not found in $GIT_DIR! Aborting sync to prevent data loss.${NC}"
    exit 1
fi

# --- STEP 2: SYNC TO LIVE DIRECTORY ---
echo -e "\n${BLUE}[2/4] Syncing changes to live directory ($LIVE_DIR)...${NC}"
if [ ! -d "$LIVE_DIR" ]; then 
    echo -e "${YELLOW}Creating live directory...${NC}"
    sudo mkdir -p "$LIVE_DIR"
    sudo chown $USER:$USER "$LIVE_DIR"
fi

# Use rsync to safely copy files while excluding environment-specific data
# This ensures that your .env and database are never overwritten by Git
rsync -av --delete \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '.env' \
    --exclude 'db.sqlite3' \
    --exclude 'media/' \
    --exclude 'static/' \
    --exclude 'staticfiles/' \
    $GIT_DIR/ $LIVE_DIR/
check_status "File sync"

# --- STEP 3: LIVE DEPLOYMENT ---
echo -e "\n${BLUE}[3/4] Finalizing deployment in live folder...${NC}"
cd $LIVE_DIR || exit 1

# Show what changed
if [ "$OLD_VERSION" != "$NEW_VERSION" ]; then
    echo -e "${YELLOW}Changes detected between $OLD_VERSION and $NEW_VERSION:${NC}"
    cd $GIT_DIR && git diff --name-status $OLD_VERSION $NEW_VERSION | sed 's/^/  /' && cd $LIVE_DIR
else
    echo -e "${YELLOW}No code changes detected, refreshing environment...${NC}"
fi

# Venv, Dependencies and Migrations
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt > /dev/null
    
    echo -e "${YELLOW}Running database migrations...${NC}"
    python manage.py migrate --noinput
    
    echo -e "${YELLOW}Collecting static files...${NC}"
    python manage.py collectstatic --noinput
    check_status "Django tasks"
else
    echo -e "${RED}CRITICAL ERROR: Virtual environment not found at $VENV_PATH${NC}"
    echo -e "${YELLOW}Please create it manually once: python3 -m venv $VENV_PATH${NC}"
    exit 1
fi

# Restart Service
echo -e "\n${BLUE}[4/4] Restarting application service ($SERVICE_NAME)...${NC}"
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl daemon-reload
    sudo systemctl restart $SERVICE_NAME
    
    # Verify service is running
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}Service $SERVICE_NAME is now ACTIVE.${NC}"
    else
        echo -e "${RED}Service $SERVICE_NAME FAILED to start!${NC}"
        sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
        exit 1
    fi
else
    echo -e "${YELLOW}systemctl not found, skipping service restart.${NC}"
fi

echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}   DEPLOYMENT COMPLETED SUCCESSFULLY!     ${NC}"
echo -e "${GREEN}==========================================${NC}"

echo -e "${BLUE}Finished at: $(date)${NC}"
