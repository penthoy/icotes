#!/bin/bash
set -e

# iLabors Code Editor - Production Deployment Script
# This script sets up the application for production deployment on Ubuntu/Debian servers
# with nginx reverse proxy, systemd service, and security best practices

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="ilaborcode"
APP_USER="ilaborcode"
APP_DIR="/opt/$APP_NAME"
NGINX_CONFIG="/etc/nginx/sites-available/$APP_NAME"
SYSTEMD_SERVICE="/etc/systemd/system/$APP_NAME.service"
LOG_DIR="/var/log/$APP_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Parse command line arguments
DOMAIN=""
SSL_EMAIL=""
SKIP_NGINX=false
SKIP_SSL=false
SKIP_FIREWALL=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --ssl-email)
            SSL_EMAIL="$2"
            shift 2
            ;;
        --skip-nginx)
            SKIP_NGINX=true
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-firewall)
            SKIP_FIREWALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --domain DOMAIN        Domain name for the application (required for SSL)
  --ssl-email EMAIL      Email for Let's Encrypt SSL certificate
  --skip-nginx           Skip nginx configuration
  --skip-ssl             Skip SSL certificate setup
  --skip-firewall        Skip firewall configuration
  --dry-run              Show what would be done without making changes
  -h, --help             Show this help message

Examples:
  $0 --domain myapp.example.com --ssl-email admin@example.com
  $0 --skip-ssl --domain localhost
  $0 --skip-nginx --skip-firewall
EOF
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Dry run function
execute_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "[DRY RUN] Would execute: $1"
    else
        eval "$1"
    fi
}

# Main deployment function
main() {
    print_status "Starting production deployment of iLabors Code Editor"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "Running in dry-run mode - no changes will be made"
    fi
    
    # Check root privileges
    check_root
    
    # Update system packages
    print_status "Updating system packages..."
    execute_cmd "apt update && apt upgrade -y"
    
    # Install required packages
    print_status "Installing required packages..."
    execute_cmd "apt install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates"
    
    # Install Node.js
    install_nodejs
    
    # Install Python
    install_python
    
    # Install nginx (if not skipped)
    if [[ "$SKIP_NGINX" != "true" ]]; then
        install_nginx
    fi
    
    # Create application user
    create_app_user
    
    # Setup application directory
    setup_app_directory
    
    # Configure systemd service
    setup_systemd_service
    
    # Configure nginx (if not skipped)
    if [[ "$SKIP_NGINX" != "true" ]]; then
        configure_nginx
    fi
    
    # Setup SSL (if domain provided and not skipped)
    if [[ -n "$DOMAIN" && "$SKIP_SSL" != "true" ]]; then
        setup_ssl
    fi
    
    # Configure firewall (if not skipped)
    if [[ "$SKIP_FIREWALL" != "true" ]]; then
        configure_firewall
    fi
    
    # Setup log rotation
    setup_log_rotation
    
    # Final steps
    final_setup
    
    print_success "Production deployment completed!"
    print_final_instructions
}

# Install Node.js
install_nodejs() {
    print_status "Installing Node.js..."
    if ! command -v node &> /dev/null; then
        execute_cmd "curl -fsSL https://deb.nodesource.com/setup_18.x | bash -"
        execute_cmd "apt install -y nodejs"
    else
        print_success "Node.js is already installed"
    fi
}

# Install Python
install_python() {
    print_status "Installing Python..."
    execute_cmd "apt install -y python3 python3-pip python3-venv python3-dev"
}

# Install nginx
install_nginx() {
    print_status "Installing nginx..."
    if ! command -v nginx &> /dev/null; then
        execute_cmd "apt install -y nginx"
        execute_cmd "systemctl enable nginx"
        execute_cmd "systemctl start nginx"
    else
        print_success "nginx is already installed"
    fi
}

# Create application user
create_app_user() {
    print_status "Creating application user..."
    if ! id "$APP_USER" &>/dev/null; then
        execute_cmd "useradd --system --home $APP_DIR --shell /bin/bash --create-home $APP_USER"
        print_success "Created user: $APP_USER"
    else
        print_success "User $APP_USER already exists"
    fi
}

# Setup application directory
setup_app_directory() {
    print_status "Setting up application directory..."
    
    # Create directories
    execute_cmd "mkdir -p $APP_DIR $LOG_DIR"
    
    # Copy application files
    execute_cmd "cp -r $SCRIPT_DIR/* $APP_DIR/"
    
    # Set permissions
    execute_cmd "chown -R $APP_USER:$APP_USER $APP_DIR $LOG_DIR"
    execute_cmd "chmod +x $APP_DIR/start.sh"
    
    # Install dependencies as app user
    execute_cmd "sudo -u $APP_USER bash -c 'cd $APP_DIR && npm ci --omit=dev'"
    execute_cmd "sudo -u $APP_USER bash -c 'cd $APP_DIR && npm run build'"
    
    print_success "Application directory setup complete"
}

# Setup systemd service
setup_systemd_service() {
    print_status "Setting up systemd service..."
    
    cat > /tmp/$APP_NAME.service << EOF
[Unit]
Description=iLabors Code Editor
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/start.sh --skip-root-check
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME
KillMode=mixed
KillSignal=SIGINT
TimeoutSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$APP_DIR $LOG_DIR
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Environment
Environment=NODE_ENV=production
Environment=BACKEND_HOST=127.0.0.1
Environment=BACKEND_PORT=8000
Environment=WORKERS=2

[Install]
WantedBy=multi-user.target
EOF

    execute_cmd "mv /tmp/$APP_NAME.service $SYSTEMD_SERVICE"
    execute_cmd "systemctl daemon-reload"
    execute_cmd "systemctl enable $APP_NAME"
    
    print_success "Systemd service configured"
}

# Configure nginx
configure_nginx() {
    print_status "Configuring nginx..."
    
    SERVER_NAME="${DOMAIN:-localhost}"
    
    cat > /tmp/nginx-config << EOF
server {
    listen 80;
    server_name $SERVER_NAME;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=websocket:10m rate=5r/s;
    
    # Main location
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
    }
    
    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
    }
    
    # WebSocket connections
    location /ws/ {
        limit_req zone=websocket burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

    execute_cmd "mv /tmp/nginx-config $NGINX_CONFIG"
    execute_cmd "ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/"
    execute_cmd "rm -f /etc/nginx/sites-enabled/default"
    execute_cmd "nginx -t"
    execute_cmd "systemctl restart nginx"
    
    print_success "nginx configuration complete"
}

# Setup SSL with Let's Encrypt
setup_ssl() {
    print_status "Setting up SSL certificate..."
    
    if [[ -z "$SSL_EMAIL" ]]; then
        print_warning "No SSL email provided, skipping SSL setup"
        return
    fi
    
    # Install certbot
    execute_cmd "apt install -y certbot python3-certbot-nginx"
    
    # Get certificate
    execute_cmd "certbot --nginx -d $DOMAIN --email $SSL_EMAIL --agree-tos --non-interactive"
    
    # Setup auto-renewal
    execute_cmd "crontab -l | { cat; echo '0 3 * * * certbot renew --quiet'; } | crontab -"
    
    print_success "SSL certificate configured"
}

# Configure firewall
configure_firewall() {
    print_status "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        execute_cmd "ufw --force enable"
        execute_cmd "ufw default deny incoming"
        execute_cmd "ufw default allow outgoing"
        execute_cmd "ufw allow ssh"
        execute_cmd "ufw allow 'Nginx Full'"
        execute_cmd "ufw --force reload"
        print_success "UFW firewall configured"
    else
        print_warning "UFW not found, skipping firewall configuration"
    fi
}

# Setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    cat > /tmp/logrotate-config << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $APP_USER $APP_USER
    postrotate
        systemctl reload $APP_NAME
    endscript
}
EOF

    execute_cmd "mv /tmp/logrotate-config /etc/logrotate.d/$APP_NAME"
    print_success "Log rotation configured"
}

# Final setup
final_setup() {
    print_status "Performing final setup..."
    
    # Create environment file
    cat > $APP_DIR/.env.production << EOF
NODE_ENV=production
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
WORKERS=2
EOF

    execute_cmd "chown $APP_USER:$APP_USER $APP_DIR/.env.production"
    execute_cmd "chmod 640 $APP_DIR/.env.production"
    
    # Start the service
    execute_cmd "systemctl start $APP_NAME"
    
    print_success "Application started"
}

# Print final instructions
print_final_instructions() {
    echo ""
    echo "========================================"
    echo "         DEPLOYMENT COMPLETE"
    echo "========================================"
    echo ""
    echo "Service Management:"
    echo "  Start:    sudo systemctl start $APP_NAME"
    echo "  Stop:     sudo systemctl stop $APP_NAME"
    echo "  Restart:  sudo systemctl restart $APP_NAME"
    echo "  Status:   sudo systemctl status $APP_NAME"
    echo "  Logs:     sudo journalctl -fu $APP_NAME"
    echo ""
    echo "Application Details:"
    echo "  Directory: $APP_DIR"
    echo "  User:      $APP_USER"
    echo "  Logs:      $LOG_DIR"
    echo ""
    if [[ "$SKIP_NGINX" != "true" ]]; then
        echo "Web Access:"
        if [[ -n "$DOMAIN" ]]; then
            echo "  URL:       https://$DOMAIN"
        else
            echo "  URL:       http://localhost"
        fi
        echo "  nginx:     sudo systemctl status nginx"
    else
        echo "Direct Access:"
        echo "  URL:       http://localhost:8000"
    fi
    echo ""
    echo "Health Checks:"
    echo "  General:   curl http://localhost:8000/health"
    echo "  Terminal:  curl http://localhost:8000/api/terminal/health"
    echo ""
    echo "Configuration Files:"
    echo "  nginx:     $NGINX_CONFIG"
    echo "  systemd:   $SYSTEMD_SERVICE"
    echo "  logs:      /etc/logrotate.d/$APP_NAME"
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Note: This was a dry run. No changes were made."
    fi
}

# Run main function
main "$@"
