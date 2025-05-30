#!/bin/bash

# Complete AWS Free Tier Honeypot Deployment Script
# This script sets up the honeypot services on the honeypot instance

set -e

echo "🍯 Deploying Honeypot Services on AWS Free Tier..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "config/honeypot_config.yaml" ]; then
    print_error "Please run this script from the cybersecurity-honeypot-system directory"
    exit 1
fi

# Get ELK instance private IP
print_status "Please enter the PRIVATE IP address of your ELK stack instance:"
read -p "ELK Private IP: " ELK_PRIVATE_IP

if [ -z "$ELK_PRIVATE_IP" ]; then
    print_error "ELK Private IP is required"
    exit 1
fi

# Validate IP format
if ! [[ $ELK_PRIVATE_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    print_error "Invalid IP address format"
    exit 1
fi

print_status "Using ELK Private IP: $ELK_PRIVATE_IP"

# Create Python virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p dashboard/templates

# Download GeoLite2 database (free version)
print_status "Downloading GeoLite2 database..."
if [ ! -f "data/GeoLite2-City.mmdb" ]; then
    wget -O data/GeoLite2-City.mmdb.gz "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb.gz"
    gunzip data/GeoLite2-City.mmdb.gz
fi

# Update configuration with ELK IP
print_status "Updating configuration with ELK instance IP..."
cp config/honeypot-config-aws.yaml config/honeypot_config.yaml

# Update Elasticsearch and Logstash hosts
sed -i "s/host: \"localhost\"/host: \"$ELK_PRIVATE_IP\"/g" config/honeypot_config.yaml

# Create optimized honeypot startup script
print_status "Creating optimized honeypot startup script..."
cat > start_honeypots.sh <<'EOF'
#!/bin/bash

echo "🍯 Starting Honeypot Services..."

# Activate virtual environment
source venv/bin/activate

# Set memory limits for Python processes
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Create logs directory if it doesn't exist
mkdir -p logs

# Start honeypot services with memory optimization
echo "Starting SSH honeypot..."
python3 -u honeypots/ssh_honeypot.py > logs/ssh_honeypot.log 2>&1 &
SSH_PID=$!

echo "Starting HTTP honeypot..."
python3 -u honeypots/http_honeypot.py > logs/http_honeypot.log 2>&1 &
HTTP_PID=$!

echo "Starting FTP honeypot..."
python3 -u honeypots/ftp_honeypot.py > logs/ftp_honeypot.log 2>&1 &
FTP_PID=$!

echo "Starting Telnet honeypot..."
python3 -u honeypots/telnet_honeypot.py > logs/telnet_honeypot.log 2>&1 &
TELNET_PID=$!

# Start dashboard
echo "Starting dashboard..."
python3 -u dashboard/app.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!

# Save PIDs for later cleanup
echo $SSH_PID > logs/ssh.pid
echo $HTTP_PID > logs/http.pid
echo $FTP_PID > logs/ftp.pid
echo $TELNET_PID > logs/telnet.pid
echo $DASHBOARD_PID > logs/dashboard.pid

echo "✅ All honeypot services started!"
echo "📊 Dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):12000"

# Monitor services
while true; do
    sleep 60
    
    # Check if processes are still running
    for service in ssh http ftp telnet dashboard; do
        if [ -f "logs/${service}.pid" ]; then
            pid=$(cat logs/${service}.pid)
            if ! kill -0 $pid 2>/dev/null; then
                echo "$(date): $service honeypot died, restarting..." >> logs/restart.log
                case $service in
                    ssh)
                        python3 -u honeypots/ssh_honeypot.py > logs/ssh_honeypot.log 2>&1 &
                        echo $! > logs/ssh.pid
                        ;;
                    http)
                        python3 -u honeypots/http_honeypot.py > logs/http_honeypot.log 2>&1 &
                        echo $! > logs/http.pid
                        ;;
                    ftp)
                        python3 -u honeypots/ftp_honeypot.py > logs/ftp_honeypot.log 2>&1 &
                        echo $! > logs/ftp.pid
                        ;;
                    telnet)
                        python3 -u honeypots/telnet_honeypot.py > logs/telnet_honeypot.log 2>&1 &
                        echo $! > logs/telnet.pid
                        ;;
                    dashboard)
                        python3 -u dashboard/app.py > logs/dashboard.log 2>&1 &
                        echo $! > logs/dashboard.pid
                        ;;
                esac
            fi
        fi
    done
done
EOF

chmod +x start_honeypots.sh

# Create stop script
print_status "Creating stop script..."
cat > stop_honeypots.sh <<'EOF'
#!/bin/bash

echo "🛑 Stopping Honeypot Services..."

# Kill all honeypot processes
for service in ssh http ftp telnet dashboard; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat logs/${service}.pid)
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo "Stopped $service honeypot (PID: $pid)"
        fi
        rm -f logs/${service}.pid
    fi
done

# Kill any remaining Python processes
pkill -f "honeypots/"
pkill -f "dashboard/app.py"

echo "✅ All honeypot services stopped"
EOF

chmod +x stop_honeypots.sh

# Create status check script
print_status "Creating status check script..."
cat > check_status.sh <<'EOF'
#!/bin/bash

echo "🔍 Honeypot System Status"
echo "========================"

echo "📅 Current Time: $(date)"
echo ""

echo "🐳 System Resources:"
echo "Memory Usage: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "Disk Usage: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

echo "🍯 Honeypot Services:"
for service in ssh http ftp telnet dashboard; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat logs/${service}.pid)
        if kill -0 $pid 2>/dev/null; then
            echo "✅ $service honeypot (PID: $pid) - RUNNING"
        else
            echo "❌ $service honeypot - STOPPED"
        fi
    else
        echo "❌ $service honeypot - NOT STARTED"
    fi
done

echo ""
echo "📊 Recent Activity (last 10 entries):"
if [ -f "logs/honeypot.log" ]; then
    tail -10 logs/honeypot.log
else
    echo "No activity logs found"
fi

echo ""
echo "🌐 Network Connections:"
netstat -tuln | grep -E ":(22|80|21|23|2222|12000)" | head -10

echo ""
echo "📈 Log File Sizes:"
ls -lh logs/ 2>/dev/null || echo "No log files found"
EOF

chmod +x check_status.sh

# Create log rotation script
print_status "Creating log rotation script..."
cat > rotate_logs.sh <<'EOF'
#!/bin/bash

echo "🔄 Rotating log files..."

LOG_DIR="logs"
MAX_SIZE=5242880  # 5MB in bytes

for log_file in $LOG_DIR/*.log; do
    if [ -f "$log_file" ]; then
        size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
        if [ $size -gt $MAX_SIZE ]; then
            echo "Rotating $log_file (size: $size bytes)"
            mv "$log_file" "${log_file}.old"
            touch "$log_file"
        fi
    fi
done

# Remove old rotated logs to save space
find $LOG_DIR -name "*.old" -mtime +7 -delete

echo "✅ Log rotation completed"
EOF

chmod +x rotate_logs.sh

# Set up cron jobs
print_status "Setting up cron jobs..."
(crontab -l 2>/dev/null; echo "*/30 * * * * cd $(pwd) && ./rotate_logs.sh >> logs/rotation.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "@reboot sleep 120 && cd $(pwd) && ./start_honeypots.sh >> logs/startup.log 2>&1") | crontab -

# Create systemd service for better management
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/honeypot.service > /dev/null <<EOF
[Unit]
Description=Cybersecurity Honeypot System
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/start_honeypots.sh
ExecStop=$(pwd)/stop_honeypots.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable honeypot

# Test configuration
print_status "Testing configuration..."
python3 -c "
import yaml
with open('config/honeypot_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('✅ Configuration file is valid')
print(f'Elasticsearch host: {config[\"elasticsearch\"][\"host\"]}')
print(f'Logstash host: {config[\"logstash\"][\"host\"]}')
"

# Create test script
print_status "Creating test script..."
cat > test_honeypots.sh <<'EOF'
#!/bin/bash

echo "🧪 Testing Honeypot Services..."

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo "Testing SSH honeypot (port 2222)..."
timeout 5 nc -zv $PUBLIC_IP 2222 && echo "✅ SSH honeypot is accessible" || echo "❌ SSH honeypot is not accessible"

echo "Testing HTTP honeypot (port 80)..."
timeout 5 curl -s http://$PUBLIC_IP > /dev/null && echo "✅ HTTP honeypot is accessible" || echo "❌ HTTP honeypot is not accessible"

echo "Testing FTP honeypot (port 21)..."
timeout 5 nc -zv $PUBLIC_IP 21 && echo "✅ FTP honeypot is accessible" || echo "❌ FTP honeypot is not accessible"

echo "Testing Telnet honeypot (port 23)..."
timeout 5 nc -zv $PUBLIC_IP 23 && echo "✅ Telnet honeypot is accessible" || echo "❌ Telnet honeypot is not accessible"

echo "Testing Dashboard (port 12000)..."
timeout 5 curl -s http://$PUBLIC_IP:12000 > /dev/null && echo "✅ Dashboard is accessible" || echo "❌ Dashboard is not accessible"

echo ""
echo "🌐 Your honeypot URLs:"
echo "📊 Dashboard: http://$PUBLIC_IP:12000"
echo "🔍 Test SSH: ssh -p 2222 test@$PUBLIC_IP"
echo "🌐 Test HTTP: http://$PUBLIC_IP"
echo "📁 Test FTP: ftp $PUBLIC_IP"
EOF

chmod +x test_honeypots.sh

print_status "✅ Honeypot deployment completed!"
print_warning "⚠️  Next steps:"
echo "1. Start the honeypot services: ./start_honeypots.sh"
echo "2. Test the services: ./test_honeypots.sh"
echo "3. Check status: ./check_status.sh"
echo "4. View logs: tail -f logs/honeypot.log"
echo "5. Access dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):12000"

print_status "🔧 Management commands:"
echo "• Start: ./start_honeypots.sh"
echo "• Stop: ./stop_honeypots.sh"
echo "• Status: ./check_status.sh"
echo "• Test: ./test_honeypots.sh"
echo "• Rotate logs: ./rotate_logs.sh"
echo "• Systemd: sudo systemctl start/stop/status honeypot"

print_warning "🔒 Security reminders:"
echo "1. Ensure your ELK instance security group allows traffic from this honeypot instance"
echo "2. Monitor resource usage regularly"
echo "3. Set up log rotation to prevent disk space issues"
echo "4. Consider setting up email alerts for critical events"