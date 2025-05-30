#!/bin/bash

# AWS Free Tier Honeypot Setup Script
# Optimized for t2.micro instances with 1GB RAM

set -e

echo "🛡️  Starting AWS Free Tier Honeypot Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
print_status "Installing essential packages..."
sudo apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    docker-compose \
    curl \
    wget \
    htop \
    unzip \
    jq \
    fail2ban \
    ufw

# Configure Docker for low memory usage
print_status "Configuring Docker for low memory usage..."
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Create Docker daemon configuration for memory optimization
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "default-ulimits": {
        "memlock": {
            "Hard": -1,
            "Name": "memlock",
            "Soft": -1
        }
    }
}
EOF

sudo systemctl restart docker

# Configure system for low memory usage
print_status "Optimizing system for low memory usage..."

# Reduce swappiness
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Configure log rotation
sudo tee /etc/logrotate.d/honeypot > /dev/null <<EOF
/home/ubuntu/cybersecurity-honeypot-system/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
EOF

# Create honeypot directories
print_status "Creating honeypot directories..."
mkdir -p ~/honeypot-logs
mkdir -p ~/honeypot-data
mkdir -p ~/honeypot-config

# Set up basic firewall
print_status "Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (current connection)
sudo ufw allow ssh

# Allow honeypot ports
sudo ufw allow 80/tcp    # HTTP honeypot
sudo ufw allow 443/tcp   # HTTPS honeypot
sudo ufw allow 21/tcp    # FTP honeypot
sudo ufw allow 23/tcp    # Telnet honeypot
sudo ufw allow 25/tcp    # SMTP honeypot
sudo ufw allow 2222/tcp  # SSH honeypot
sudo ufw allow 3389/tcp  # RDP honeypot

# Allow management ports (restrict to your IP later)
sudo ufw allow 5601/tcp  # Kibana
sudo ufw allow 12000/tcp # Dashboard

sudo ufw --force enable

# Configure fail2ban for additional security
print_status "Configuring fail2ban..."
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

# Create memory monitoring script
print_status "Creating memory monitoring script..."
tee ~/monitor_memory.sh > /dev/null <<'EOF'
#!/bin/bash

# Memory monitoring script for AWS free tier
MEMORY_THRESHOLD=85  # Alert when memory usage exceeds 85%

while true; do
    MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
    
    if [ $MEMORY_USAGE -gt $MEMORY_THRESHOLD ]; then
        echo "$(date): WARNING - Memory usage is ${MEMORY_USAGE}%" >> ~/memory_alerts.log
        
        # Optional: restart services if memory is critically high
        if [ $MEMORY_USAGE -gt 95 ]; then
            echo "$(date): CRITICAL - Restarting Docker containers due to high memory usage" >> ~/memory_alerts.log
            cd ~/cybersecurity-honeypot-system/aws-deployment
            docker-compose -f docker-compose-freetier.yml restart
        fi
    fi
    
    sleep 300  # Check every 5 minutes
done
EOF

chmod +x ~/monitor_memory.sh

# Create system info script
print_status "Creating system info script..."
tee ~/system_info.sh > /dev/null <<'EOF'
#!/bin/bash

echo "=== AWS Free Tier Honeypot System Info ==="
echo "Date: $(date)"
echo "Uptime: $(uptime)"
echo ""

echo "=== Memory Usage ==="
free -h

echo ""
echo "=== Disk Usage ==="
df -h

echo ""
echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Network Connections ==="
netstat -tuln | grep LISTEN

echo ""
echo "=== Recent Attacks (last 10) ==="
if [ -f ~/cybersecurity-honeypot-system/logs/honeypot.log ]; then
    tail -10 ~/cybersecurity-honeypot-system/logs/honeypot.log
else
    echo "No attack logs found yet"
fi
EOF

chmod +x ~/system_info.sh

# Create startup script
print_status "Creating startup script..."
tee ~/start_honeypot.sh > /dev/null <<'EOF'
#!/bin/bash

echo "🛡️  Starting Honeypot System..."

# Navigate to project directory
cd ~/cybersecurity-honeypot-system

# Start memory monitor in background
if ! pgrep -f "monitor_memory.sh" > /dev/null; then
    nohup ~/monitor_memory.sh > /dev/null 2>&1 &
    echo "Memory monitor started"
fi

# Start ELK stack with free tier optimizations
echo "Starting ELK stack..."
cd aws-deployment
docker-compose -f docker-compose-freetier.yml up -d

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
while ! curl -s http://localhost:9200/_cluster/health > /dev/null; do
    sleep 5
done

echo "ELK stack is ready!"

# Start honeypot services
echo "Starting honeypot services..."
cd ..
source venv/bin/activate
python3 honeypots/start_all.py &

# Start dashboard
echo "Starting dashboard..."
python3 dashboard/app.py &

echo "✅ Honeypot system started successfully!"
echo "📊 Dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):12000"
echo "📈 Kibana: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5601"
EOF

chmod +x ~/start_honeypot.sh

# Create stop script
print_status "Creating stop script..."
tee ~/stop_honeypot.sh > /dev/null <<'EOF'
#!/bin/bash

echo "🛑 Stopping Honeypot System..."

# Stop Python processes
pkill -f "start_all.py"
pkill -f "dashboard/app.py"

# Stop Docker containers
cd ~/cybersecurity-honeypot-system/aws-deployment
docker-compose -f docker-compose-freetier.yml down

# Stop memory monitor
pkill -f "monitor_memory.sh"

echo "✅ Honeypot system stopped"
EOF

chmod +x ~/stop_honeypot.sh

# Create crontab for automatic startup
print_status "Setting up automatic startup..."
(crontab -l 2>/dev/null; echo "@reboot sleep 60 && /home/ubuntu/start_honeypot.sh >> /home/ubuntu/startup.log 2>&1") | crontab -

print_status "✅ AWS Free Tier Honeypot setup completed!"
print_warning "⚠️  Remember to:"
echo "1. Reboot the system to apply all changes: sudo reboot"
echo "2. After reboot, clone your honeypot repository"
echo "3. Run the ELK setup script"
echo "4. Configure your honeypot settings"
echo "5. Restrict management ports to your IP only"

print_status "📋 Useful commands:"
echo "• Start system: ~/start_honeypot.sh"
echo "• Stop system: ~/stop_honeypot.sh"
echo "• Check status: ~/system_info.sh"
echo "• Monitor memory: tail -f ~/memory_alerts.log"
echo "• View logs: docker-compose -f ~/cybersecurity-honeypot-system/aws-deployment/docker-compose-freetier.yml logs"