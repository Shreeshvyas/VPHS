#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Automatically detect the directory where this script is located
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="vphs-teachers-portal"  # Default systemd service name

echo "======================================================"
echo " Starting VPHS Server Deployment "
echo " Project Directory: $PROJECT_DIR"
echo " Service Name:      $SERVICE_NAME"
echo "======================================================"

# Navigate to project directory
cd "$PROJECT_DIR"

# Pull latest changes from git
echo "--> Pulling latest changes from Git..."
git pull origin master

# Activate virtual environment
echo "--> Activating virtual environment..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Trying to create one..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Upgrade pip and install requirements
echo "--> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Apply database migrations
echo "--> Running database migrations..."
python manage.py migrate --no-input

# Collect static files
echo "--> Collecting static files..."
python manage.py collectstatic --no-input

# Restart systemd application service
echo "--> Restarting systemd service ($SERVICE_NAME)..."
if systemctl list-units --type=service | grep -Fq "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
    echo "--> Service restarted successfully."
else
    echo "Warning: systemd service '$SERVICE_NAME' not found. You might need to restart your application runner manually."
fi

# Reload Nginx
echo "--> Reloading Nginx..."
if systemctl is-active --quiet nginx; then
    sudo systemctl reload nginx
    echo "--> Nginx reloaded successfully."
else
    echo "Warning: Nginx is not running or active."
fi

echo "======================================================"
echo " VPHS Deployment Completed Successfully! "
echo "======================================================"
