#!/bin/bash

# Legal AI Service - Quick Install Script
# One-liner installation for quick deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "========================================"
echo "  Legal AI Service - Quick Installer"
echo "========================================"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run as root or with sudo${NC}"
    exit 1
fi

# Get domain name
read -p "Enter your domain name (or press Enter for localhost): " DOMAIN
DOMAIN=${DOMAIN:-localhost}

echo ""
echo -e "${YELLOW}Starting installation...${NC}"
echo "Domain: $DOMAIN"
echo ""

# Update system
echo -e "${BLUE}[1/7] Updating system packages...${NC}"
apt-get update > /dev/null 2>&1
apt-get upgrade -y > /dev/null 2>&1
echo -e "${GREEN}✓ System updated${NC}"

# Install dependencies
echo -e "${BLUE}[2/7] Installing dependencies...${NC}"
apt-get install -y python3 python3-pip python3-venv nginx git curl > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Setup application
echo -e "${BLUE}[3/7] Setting up application...${NC}"
mkdir -p /var/www/legal-ai-service

# Copy files from source
if [ -d "/mnt/okcomputer/output/legal-ai-service" ]; then
    cp -r /mnt/okcomputer/output/legal-ai-service/* /var/www/legal-ai-service/
else
    echo -e "${RED}✗ Source directory not found${NC}"
    exit 1
fi

mkdir -p /var/www/legal-ai-service/uploads
mkdir -p /var/log/legal-ai
chown -R www-data:www-data /var/www/legal-ai-service
chown -R www-data:www-data /var/log/legal-ai
echo -e "${GREEN}✓ Application files copied${NC}"

# Setup virtual environment
echo -e "${BLUE}[4/7] Setting up Python environment...${NC}"
cd /var/www/legal-ai-service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
pip install gunicorn > /dev/null 2>&1
deactivate
echo -e "${GREEN}✓ Python environment ready${NC}"

# Setup environment file
echo -e "${BLUE}[5/7] Configuring environment...${NC}"
if [ ! -f "/var/www/legal-ai-service/.env" ]; then
    cp /var/www/legal-ai-service/deploy/.env.example /var/www/legal-ai-service/.env
    
    # Generate random secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your-super-secret-key-change-this-in-production/${SECRET_KEY}/g" /var/www/legal-ai-service/.env
    
    chown www-data:www-data /var/www/legal-ai-service/.env
    chmod 600 /var/www/legal-ai-service/.env
fi
echo -e "${GREEN}✓ Environment configured${NC}"

# Setup systemd service
echo -e "${BLUE}[6/7] Setting up services...${NC}"
cp /var/www/legal-ai-service/deploy/legal-ai.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable legal-ai > /dev/null 2>&1
systemctl start legal-ai

# Setup Nginx
rm -f /etc/nginx/sites-enabled/default
cp /var/www/legal-ai-service/deploy/nginx-http-only.conf /etc/nginx/sites-available/legal-ai
sed -i "s/server_name _;/server_name ${DOMAIN};/g" /etc/nginx/sites-available/legal-ai
ln -sf /etc/nginx/sites-available/legal-ai /etc/nginx/sites-enabled/
nginx -t > /dev/null 2>&1
systemctl restart nginx
echo -e "${GREEN}✓ Services configured${NC}"

# Setup firewall
echo -e "${BLUE}[7/7] Configuring firewall...${NC}"
apt-get install -y ufw > /dev/null 2>&1
ufw --force reset > /dev/null 2>&1
ufw default deny incoming > /dev/null 2>&1
ufw default allow outgoing > /dev/null 2>&1
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw --force enable > /dev/null 2>&1
echo -e "${GREEN}✓ Firewall configured${NC}"

# Final status
echo ""
echo -e "${GREEN}========================================"
echo "  Installation Complete!"
echo "========================================${NC}"
echo ""
echo "Access your application at:"
echo "  http://${DOMAIN}"
echo ""
echo "Important next steps:"
echo "  1. Edit environment file:"
echo "     sudo nano /var/www/legal-ai-service/.env"
echo ""
echo "  2. Set your KIMI_API_KEY in the .env file"
echo ""
echo "  3. Restart the service:"
echo "     sudo systemctl restart legal-ai"
echo ""
echo "Useful commands:"
echo "  View logs:    sudo journalctl -u legal-ai -f"
echo "  Status:       sudo systemctl status legal-ai"
echo "  Restart:      sudo systemctl restart legal-ai"
echo ""
echo -e "${YELLOW}NOTE: Please configure your KIMI_API_KEY before using the service!${NC}"
