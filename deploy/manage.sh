#!/bin/bash

# Legal AI Service - Management Script
# Utility script for managing the Legal AI Service

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="legal-ai"
APP_DIR="/var/www/legal-ai-service"

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
    echo "Legal AI Service - Management Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  start       Start the Legal AI Service and Nginx"
    echo "  stop        Stop the Legal AI Service and Nginx"
    echo "  restart     Restart the Legal AI Service and Nginx"
    echo "  status      Show status of all services"
    echo "  logs        Show application logs (follow mode)"
    echo "  logs-nginx  Show Nginx logs (follow mode)"
    echo "  update      Update the application from source"
    echo "  backup      Create a backup of the application"
    echo "  health      Check application health"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs"
    echo "  $0 status"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

cmd_start() {
    log_info "Starting Legal AI Service..."
    
    systemctl start ${SERVICE_NAME}
    systemctl start nginx
    
    log_success "Services started"
    cmd_status
}

cmd_stop() {
    log_info "Stopping Legal AI Service..."
    
    systemctl stop ${SERVICE_NAME}
    systemctl stop nginx
    
    log_success "Services stopped"
}

cmd_restart() {
    log_info "Restarting Legal AI Service..."
    
    systemctl restart ${SERVICE_NAME}
    systemctl restart nginx
    
    log_success "Services restarted"
    cmd_status
}

cmd_status() {
    echo "========================================"
    echo "Service Status"
    echo "========================================"
    echo ""
    
    echo -n "Legal AI Service: "
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "${GREEN}running${NC}"
    else
        echo -e "${RED}stopped${NC}"
    fi
    
    echo -n "Nginx: "
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}running${NC}"
    else
        echo -e "${RED}stopped${NC}"
    fi
    
    echo ""
    echo "Service Details:"
    systemctl status ${SERVICE_NAME} --no-pager | head -10
    
    echo ""
    echo "Nginx Details:"
    systemctl status nginx --no-pager | head -10
}

cmd_logs() {
    log_info "Showing application logs (Press Ctrl+C to exit)..."
    journalctl -u ${SERVICE_NAME} -f
}

cmd_logs_nginx() {
    log_info "Showing Nginx error logs (Press Ctrl+C to exit)..."
    tail -f /var/log/nginx/legal-ai-error.log
}

cmd_update() {
    log_info "Updating Legal AI Service..."
    
    # Stop services
    cmd_stop
    
    # Backup current version
    cmd_backup
    
    # Update code
    if [ -d "/mnt/okcomputer/output/legal-ai-service" ]; then
        cp -r /mnt/okcomputer/output/legal-ai-service/* ${APP_DIR}/
    fi
    
    # Update dependencies
    cd ${APP_DIR}
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    
    # Set permissions
    chown -R www-data:www-data ${APP_DIR}
    
    # Start services
    cmd_start
    
    log_success "Update complete"
}

cmd_backup() {
    log_info "Creating backup..."
    
    BACKUP_DIR="/var/backups/legal-ai-service"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"
    
    mkdir -p ${BACKUP_DIR}
    
    # Create backup
    tar -czf ${BACKUP_FILE} -C ${APP_DIR} . --exclude=venv --exclude=__pycache__
    
    # Backup database if exists
    if [ -f "${APP_DIR}/legal_ai.db" ]; then
        cp ${APP_DIR}/legal_ai.db ${BACKUP_DIR}/database_${TIMESTAMP}.db
    fi
    
    log_success "Backup created: ${BACKUP_FILE}"
    
    # Clean old backups (keep last 10)
    ls -t ${BACKUP_DIR}/backup_*.tar.gz | tail -n +11 | xargs -r rm
}

cmd_health() {
    log_info "Checking application health..."
    
    # Check services
    echo "Services:"
    echo -n "  Legal AI Service: "
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
    fi
    
    echo -n "  Nginx: "
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
    fi
    
    # Check HTTP response
    echo ""
    echo "HTTP Check:"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
    echo -n "  Localhost: "
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
        echo -e "${GREEN}OK (${HTTP_STATUS})${NC}"
    else
        echo -e "${RED}FAIL (${HTTP_STATUS})${NC}"
    fi
    
    # Check disk space
    echo ""
    echo "Disk Space:"
    df -h / | tail -1 | awk '{print "  Used: " $3 " / " $2 " (" $5 ")"}'
    
    # Check memory
    echo ""
    echo "Memory:"
    free -h | grep "Mem:" | awk '{print "  Used: " $3 " / " $2}'
    
    # Check SSL certificate
    echo ""
    echo "SSL Certificate:"
    if [ -d "/etc/letsencrypt/live" ]; then
        for cert in /etc/letsencrypt/live/*/cert.pem; do
            if [ -f "$cert" ]; then
                domain=$(basename $(dirname "$cert"))
                expiry=$(openssl x509 -enddate -noout -in "$cert" | cut -d= -f2)
                echo "  ${domain}: expires ${expiry}"
            fi
        done
    else
        echo "  No SSL certificates found"
    fi
}

# Main
main() {
    check_root
    
    case "${1:-help}" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        logs)
            cmd_logs
            ;;
        logs-nginx)
            cmd_logs_nginx
            ;;
        update)
            cmd_update
            ;;
        backup)
            cmd_backup
            ;;
        health)
            cmd_health
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
