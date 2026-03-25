#!/bin/bash

# Legal AI Service - Deployment Script
# This script automates the deployment of the Legal AI Service
# Run as root or with sudo

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="legal-ai-service"
APP_DIR="/var/www/${APP_NAME}"
APP_USER="www-data"
APP_GROUP="www-data"
SERVICE_NAME="legal-ai"
DOMAIN="legal-ai-service.local"
USE_SSL=false

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --ssl)
                USE_SSL=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --domain <domain>    Set the domain name (default: legal-ai-service.local)"
    echo "  --ssl                Enable SSL with Let's Encrypt"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Deploy with default settings"
    echo "  $0 --domain example.com             # Deploy with custom domain"
    echo "  $0 --domain example.com --ssl       # Deploy with SSL"
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    log_success "System packages updated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Install Python and pip
    apt-get install -y python3 python3-pip python3-venv python3-dev
    
    # Install Nginx
    apt-get install -y nginx
    
    # Install other dependencies
    apt-get install -y git curl wget build-essential libssl-dev
    
    # Install certbot for SSL (optional)
    if [ "$USE_SSL" = true ]; then
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    log_success "Dependencies installed"
}

# Setup application directory
setup_app_directory() {
    log_info "Setting up application directory..."
    
    # Create directory
    mkdir -p ${APP_DIR}
    
    # Copy application files
    if [ -d "/mnt/okcomputer/output/legal-ai-service" ]; then
        cp -r /mnt/okcomputer/output/legal-ai-service/* ${APP_DIR}/
    else
        log_error "Source directory not found: /mnt/okcomputer/output/legal-ai-service"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p ${APP_DIR}/uploads
    mkdir -p /var/log/${SERVICE_NAME}
    mkdir -p /var/www/certbot
    
    # Set permissions
    chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}
    chown -R ${APP_USER}:${APP_GROUP} /var/log/${SERVICE_NAME}
    chmod 755 ${APP_DIR}
    chmod 755 ${APP_DIR}/uploads
    
    log_success "Application directory set up"
}

# Create Python virtual environment
setup_virtualenv() {
    log_info "Setting up Python virtual environment..."
    
    cd ${APP_DIR}
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate and install requirements
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
    
    # Deactivate
    deactivate
    
    # Set permissions
    chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}/venv
    
    log_success "Virtual environment set up"
}

# Setup environment file
setup_environment() {
    log_info "Setting up environment file..."
    
    if [ ! -f "${APP_DIR}/.env" ]; then
        cp ${APP_DIR}/deploy/.env.example ${APP_DIR}/.env
        log_warning "Environment file created from template. Please edit ${APP_DIR}/.env with your actual values!"
    fi
    
    chown ${APP_USER}:${APP_GROUP} ${APP_DIR}/.env
    chmod 600 ${APP_DIR}/.env
    
    log_success "Environment file set up"
}

# Setup systemd service
setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    # Copy service file
    cp ${APP_DIR}/deploy/legal-ai.service /etc/systemd/system/${SERVICE_NAME}.service
    
    # Update domain in service file if needed
    if [ "$DOMAIN" != "legal-ai-service.local" ]; then
        sed -i "s/legal-ai-service.local/${DOMAIN}/g" /etc/systemd/system/${SERVICE_NAME}.service
    fi
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable ${SERVICE_NAME}.service
    
    log_success "Systemd service set up"
}

# Setup Nginx
setup_nginx() {
    log_info "Setting up Nginx..."
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Copy Nginx configuration
    if [ "$USE_SSL" = true ]; then
        cp ${APP_DIR}/deploy/nginx.conf /etc/nginx/sites-available/${SERVICE_NAME}
    else
        cp ${APP_DIR}/deploy/nginx-http-only.conf /etc/nginx/sites-available/${SERVICE_NAME}
    fi
    
    # Update domain in Nginx config
    sed -i "s/legal-ai-service.local/${DOMAIN}/g" /etc/nginx/sites-available/${SERVICE_NAME}
    
    # Create symlink
    ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    
    # Test Nginx configuration
    nginx -t
    
    # Reload Nginx
    systemctl reload nginx
    
    log_success "Nginx set up"
}

# Setup SSL with Let's Encrypt
setup_ssl() {
    if [ "$USE_SSL" = true ]; then
        log_info "Setting up SSL with Let's Encrypt..."
        
        # Check if domain is valid for Let's Encrypt
        if [ "$DOMAIN" = "legal-ai-service.local" ] || [ "$DOMAIN" = "localhost" ]; then
            log_warning "Cannot use Let's Encrypt with local domain. Skipping SSL setup."
            USE_SSL=false
            return
        fi
        
        # Obtain certificate
        certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN}
        
        # Setup auto-renewal
        systemctl enable certbot.timer
        systemctl start certbot.timer
        
        log_success "SSL certificate installed"
    fi
}

# Setup firewall
setup_firewall() {
    log_info "Setting up firewall (UFW)..."
    
    # Install UFW if not present
    apt-get install -y ufw
    
    # Reset UFW
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow 22/tcp
    
    # Allow HTTP
    ufw allow 80/tcp
    
    # Allow HTTPS
    ufw allow 443/tcp
    
    # Enable UFW
    ufw --force enable
    
    log_success "Firewall configured"
    ufw status verbose
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Start the Flask application
    systemctl start ${SERVICE_NAME}.service
    
    # Restart Nginx
    systemctl restart nginx
    
    log_success "Services started"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check if service is running
    if systemctl is-active --quiet ${SERVICE_NAME}.service; then
        log_success "Legal AI Service is running"
    else
        log_error "Legal AI Service is not running"
        systemctl status ${SERVICE_NAME}.service
        exit 1
    fi
    
    # Check if Nginx is running
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx is not running"
        exit 1
    fi
    
    # Test HTTP connection
    sleep 2
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        log_success "Application is accessible via HTTP"
    else
        log_warning "Application may not be accessible yet. Please check manually."
    fi
}

# Print final information
print_info() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo "========================================"
    echo ""
    echo "Application Directory: ${APP_DIR}"
    echo "Domain: ${DOMAIN}"
    echo ""
    echo "Services Status:"
    echo "  - Legal AI Service: $(systemctl is-active ${SERVICE_NAME}.service)"
    echo "  - Nginx: $(systemctl is-active nginx)"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:          journalctl -u ${SERVICE_NAME} -f"
    echo "  Restart app:        systemctl restart ${SERVICE_NAME}"
    echo "  Check status:       systemctl status ${SERVICE_NAME}"
    echo "  Edit config:        nano ${APP_DIR}/.env"
    echo ""
    echo "Access URLs:"
    if [ "$USE_SSL" = true ]; then
        echo "  HTTPS: https://${DOMAIN}"
    fi
    echo "  HTTP:  http://${DOMAIN}"
    echo ""
    echo "========================================"
    
    if [ ! -f "${APP_DIR}/.env" ] || grep -q "your_kimi_api_key_here" "${APP_DIR}/.env" 2>/dev/null; then
        log_warning "IMPORTANT: Please edit ${APP_DIR}/.env and set your actual API keys!"
    fi
}

# Main deployment function
main() {
    echo "========================================"
    echo "Legal AI Service - Deployment Script"
    echo "========================================"
    echo ""
    
    # Parse arguments
    parse_args "$@"
    
    # Run deployment steps
    check_root
    update_system
    install_dependencies
    setup_app_directory
    setup_virtualenv
    setup_environment
    setup_systemd_service
    setup_nginx
    setup_ssl
    setup_firewall
    start_services
    verify_deployment
    print_info
}

# Run main function
main "$@"
