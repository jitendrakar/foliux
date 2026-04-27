#!/bin/bash

# ================================================================= #
# FOLIUX VPS DEPLOYMENT SCRIPT (Ubuntu)                             #
# ================================================================= #

# Configuration - Update these to match your VPS settings
PROJECT_DIR="/home/foliux"
VENV_PATH="$PROJECT_DIR/venv"
SERVICE_NAME="foliux"  # Name of your systemd service file (e.g., foliux.service)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Deployment to Foliux...${NC}"

# Navigate to project directory
cd $PROJECT_DIR || { echo "❌ Directory $PROJECT_DIR not found"; exit 1; }

# 1. Pull latest changes
echo -e "${BLUE}📥 Pulling latest changes from Git...${NC}"
git pull foliux main

# 2. Activate virtual environment
if [ -d "$VENV_PATH" ]; then
    echo -e "${BLUE}🐍 Activating virtual environment...${NC}"
    source "$VENV_PATH/bin/activate"
else
    echo -e "⚠️ Virtual environment not found at $VENV_PATH"
fi

# 3. Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
pip install -r requirements.txt

# 4. Run database migrations
echo -e "${BLUE}⚙️ Running database migrations...${NC}"
python manage.py migrate --noinput

# 5. Collect static files
echo -e "${BLUE}🎨 Collecting static files...${NC}"
python manage.py collectstatic --noinput

# 6. Restart the application service
echo -e "${BLUE}🔄 Restarting application service ($SERVICE_NAME)...${NC}"
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl restart $SERVICE_NAME
    echo -e "${GREEN}✅ Service $SERVICE_NAME restarted.${NC}"
else
    echo -e "⚠️ systemctl not found. Please restart your web server manually (e.g., Gunicorn/Nginx)."
fi

echo -e "${GREEN}✨ Deployment completed successfully!${NC}"
