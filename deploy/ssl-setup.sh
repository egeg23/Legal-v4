#!/bin/bash

# Legal AI Service - SSL Setup Script
# This script sets up SSL certificates using Let's Encrypt
# Run as root or with sudo

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN=""
EMAIL=""

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

show_help() {
    echo "Usage: $0 --domain <domain> --email <email>"
    echo ""
    echo "Options:"
    echo "  --domain <domain>    Your domain name (e.g., example.com)"
    echo "  --email <email>      Email for Let's Encrypt notifications"
    echo "  --help               Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --domain legal-ai.example.com --email admin@example.com"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --email)
                EMAIL="$2"
                shift 2
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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

validate_args() {
    if [ -z "$DOMAIN" ]; then
        log_error "Domain is required. Use --domain <domain>"
        show_help
        exit 1
    fi
    
    if [ -z "$EMAIL" ]; then
        log_error "Email is required. Use --email <email>"
        show_help
        exit 1
    fi
    
    # Check if domain is local
    if [[ "$DOMAIN" == *".local" ]] || [[ "$DOMAIN" == "localhost" ]]; then
        log_error "Cannot use Let's Encrypt with local domains"
        exit 1
    fi
}

install_certbot() {
    log_info "Installing Certbot..."
    
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
    
    log_success "Certbot installed"
}

obtain_certificate() {
    log_info "Obtaining SSL certificate for ${DOMAIN}..."
    
    # Stop Nginx temporarily if it's using port 80
    if systemctl is-active --quiet nginx; then
        systemctl stop nginx
        NGINX_STOPPED=true
    fi
    
    # Obtain certificate using standalone mode
    certbot certonly --standalone \
        -d ${DOMAIN} \
        --non-interactive \
        --agree-tos \
        --email ${EMAIL}
    
    # Start Nginx again
    if [ "$NGINX_STOPPED" = true ]; then
        systemctl start nginx
    fi
    
    log_success "SSL certificate obtained"
}

update_nginx_config() {
    log_info "Updating Nginx configuration for SSL..."
    
    SERVICE_NAME="legal-ai"
    
    # Backup current config
    if [ -f "/etc/nginx/sites-available/${SERVICE_NAME}" ]; then
        cp /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-available/${SERVICE_NAME}.backup
    fi
    
    # Copy SSL-enabled config
    cp /var/www/legal-ai-service/deploy/nginx.conf /etc/nginx/sites-available/${SERVICE_NAME}
    
    # Update domain
    sed -i "s/legal-ai-service.local/${DOMAIN}/g" /etc/nginx/sites-available/${SERVICE_NAME}
    
    # Test configuration
    nginx -t
    
    # Reload Nginx
    systemctl reload nginx
    
    log_success "Nginx configuration updated"
}

setup_auto_renewal() {
    log_info "Setting up auto-renewal..."
    
    # Enable certbot timer
    systemctl enable certbot.timer
    systemctl start certbot.timer
    
    # Add renewal hook for Nginx reload
    mkdir -p /etc/letsencrypt/renewal-hooks/deploy
    cat > /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh
    
    log_success "Auto-renewal configured"
}

test_ssl() {
    log_info "Testing SSL configuration..."
    
    # Test renewal (dry run)
    certbot renew --dry-run
    
    log_success "SSL test passed"
}

print_info() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}SSL Setup Complete!${NC}"
    echo "========================================"
    echo ""
    echo "Domain: ${DOMAIN}"
    echo "Certificate Path: /etc/letsencrypt/live/${DOMAIN}/"
    echo ""
    echo "Certificate Files:"
    echo "  - Full chain: /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    echo "  - Private key: /etc/letsencrypt/live/${DOMAIN}/privkey.pem"
    echo ""
    echo "Auto-renewal:"
    echo "  - Timer status: $(systemctl is-active certbot.timer)"
    echo "  - Test renewal: certbot renew --dry-run"
    echo ""
    echo "Manual renewal:"
    echo "  certbot renew"
    echo ""
    echo "Access URL:"
    echo "  https://${DOMAIN}"
    echo "========================================"
}

main() {
    echo "========================================"
    echo "Legal AI Service - SSL Setup"
    echo "========================================"
    echo ""
    
    parse_args "$@"
    check_root
    validate_args
    install_certbot
    obtain_certificate
    update_nginx_config
    setup_auto_renewal
    test_ssl
    print_info
}

main "$@"
