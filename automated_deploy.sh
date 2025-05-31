#!/bin/bash

# Automated AWS Honeypot System Deployment
# Run this script after configuring security groups

set -e

echo "🚀 AWS Honeypot System Automated Deployment"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[PHASE]${NC} $1"
}

# Your instance details
ELK_PUBLIC_IP="100.26.191.27"
ELK_PRIVATE_IP="172.31.81.26"
HONEYPOT_PUBLIC_IP="54.165.107.7"
HONEYPOT_PRIVATE_IP="172.31.84.247"

# SSH key path
KEY_PATH="$HOME/.ssh/honeypot-key.pem"

print_status "Instance Configuration:"
echo "• ELK Stack: $ELK_PUBLIC_IP (Private: $ELK_PRIVATE_IP)"
echo "• Honeypot: $HONEYPOT_PUBLIC_IP (Private: $HONEYPOT_PRIVATE_IP)"
echo "• SSH Key: $KEY_PATH"
echo ""

# Check prerequisites
print_header "Checking Prerequisites"

if [ ! -f "$KEY_PATH" ]; then
    print_error "SSH key file not found at $KEY_PATH"
    print_warning "Please ensure your SSH key is saved at $KEY_PATH"
    exit 1
fi

# Check key permissions
if [ "$(stat -c %a "$KEY_PATH")" != "400" ]; then
    print_warning "Fixing SSH key permissions..."
    chmod 400 "$KEY_PATH"
fi

# Test connectivity
print_status "Testing SSH connectivity..."
if ! ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$ELK_PUBLIC_IP "echo 'ELK instance accessible'" 2>/dev/null; then
    print_error "Cannot connect to ELK instance ($ELK_PUBLIC_IP)"
    print_warning "Please ensure:"
    echo "1. Instance is running in AWS Console"
    echo "2. Security group allows SSH (port 22) from your IP"
    echo "3. Your IP hasn't changed since configuring security groups"
    echo ""
    echo "Current IP check: curl ifconfig.me"
    exit 1
fi

if ! ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$HONEYPOT_PUBLIC_IP "echo 'Honeypot instance accessible'" 2>/dev/null; then
    print_error "Cannot connect to Honeypot instance ($HONEYPOT_PUBLIC_IP)"
    print_warning "Please ensure:"
    echo "1. Instance is running in AWS Console"
    echo "2. Security group allows SSH (port 22) from your IP"
    echo "3. Your IP hasn't changed since configuring security groups"
    exit 1
fi

print_status "✅ All prerequisites met!"
echo ""

# Phase 1: Deploy ELK Stack
print_header "Phase 1: Deploying ELK Stack on $ELK_PUBLIC_IP"

ELK_SETUP_COMMANDS='
set -e
echo "📊 Setting up ELK Stack..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and dependencies
sudo apt install -y docker.io docker-compose curl wget git htop

# Configure Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

# Create Docker daemon config for memory optimization
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF

sudo systemctl restart docker

# Clone repository
if [ ! -d "cybersecurity-honeypot-system" ]; then
    git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
fi

cd cybersecurity-honeypot-system/aws-deployment

# Make scripts executable
chmod +x *.sh

# Run ELK setup
./elk-setup.sh

echo "✅ ELK Stack setup completed!"
'

print_status "Executing ELK setup on $ELK_PUBLIC_IP..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$ELK_PUBLIC_IP "$ELK_SETUP_COMMANDS"

print_status "⏳ Waiting for ELK services to stabilize (90 seconds)..."
sleep 90

# Test ELK services
print_status "Testing ELK services..."
if ssh -i "$KEY_PATH" ubuntu@$ELK_PUBLIC_IP "curl -s http://localhost:9200/_cluster/health" >/dev/null; then
    print_status "✅ Elasticsearch is running"
else
    print_warning "⚠️ Elasticsearch may still be starting up"
fi

if ssh -i "$KEY_PATH" ubuntu@$ELK_PUBLIC_IP "curl -s http://localhost:5601/api/status" >/dev/null; then
    print_status "✅ Kibana is running"
else
    print_warning "⚠️ Kibana may still be starting up"
fi

echo ""

# Phase 2: Deploy Honeypot Services
print_header "Phase 2: Deploying Honeypot Services on $HONEYPOT_PUBLIC_IP"

HONEYPOT_SETUP_COMMANDS='
set -e
echo "🍯 Setting up Honeypot Services..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git curl wget htop fail2ban ufw netcat

# Clone repository if not exists
if [ ! -d "cybersecurity-honeypot-system" ]; then
    git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
fi

cd cybersecurity-honeypot-system/aws-deployment

# Run honeypot setup script
chmod +x *.sh
./honeypot-setup.sh

echo "✅ Honeypot setup completed!"
'

print_status "Executing honeypot setup on $HONEYPOT_PUBLIC_IP..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$HONEYPOT_PUBLIC_IP "$HONEYPOT_SETUP_COMMANDS"

print_status "⏳ System will reboot to apply changes..."
ssh -i "$KEY_PATH" ubuntu@$HONEYPOT_PUBLIC_IP "sudo reboot" || true

print_status "Waiting for honeypot instance to reboot (120 seconds)..."
sleep 120

# Wait for instance to come back online
print_status "Waiting for instance to come back online..."
counter=0
while ! ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$HONEYPOT_PUBLIC_IP "echo 'Instance online'" 2>/dev/null; do
    echo -n "."
    sleep 5
    counter=$((counter + 1))
    if [ $counter -gt 24 ]; then  # 2 minutes timeout
        print_error "Instance took too long to come back online"
        exit 1
    fi
done
echo ""

# Phase 3: Deploy and Configure Honeypot Services
print_header "Phase 3: Configuring Honeypot Services"

HONEYPOT_DEPLOYMENT="
set -e
cd cybersecurity-honeypot-system

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs data

# Download GeoLite2 database
if [ ! -f 'data/GeoLite2-City.mmdb' ]; then
    wget -O data/GeoLite2-City.mmdb.gz 'https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb.gz'
    gunzip data/GeoLite2-City.mmdb.gz
fi

# Update configuration with ELK IP
cp config/honeypot-config-aws.yaml config/honeypot_config.yaml
sed -i 's/host: \"localhost\"/host: \"$ELK_PRIVATE_IP\"/g' config/honeypot_config.yaml

# Create optimized startup script
cat > start_honeypots.sh <<'EOF'
#!/bin/bash
echo '🍯 Starting Honeypot Services...'
source venv/bin/activate
mkdir -p logs

# Start honeypot services
python3 -u honeypots/ssh_honeypot.py > logs/ssh_honeypot.log 2>&1 &
echo \$! > logs/ssh.pid

python3 -u honeypots/http_honeypot.py > logs/http_honeypot.log 2>&1 &
echo \$! > logs/http.pid

python3 -u honeypots/ftp_honeypot.py > logs/ftp_honeypot.log 2>&1 &
echo \$! > logs/ftp.pid

python3 -u honeypots/telnet_honeypot.py > logs/telnet_honeypot.log 2>&1 &
echo \$! > logs/telnet.pid

python3 -u dashboard/app.py > logs/dashboard.log 2>&1 &
echo \$! > logs/dashboard.pid

echo '✅ All honeypot services started!'
EOF

chmod +x start_honeypots.sh

# Create stop script
cat > stop_honeypots.sh <<'EOF'
#!/bin/bash
echo '🛑 Stopping Honeypot Services...'
for service in ssh http ftp telnet dashboard; do
    if [ -f \"logs/\${service}.pid\" ]; then
        pid=\$(cat logs/\${service}.pid)
        if kill -0 \$pid 2>/dev/null; then
            kill \$pid
            echo \"Stopped \$service honeypot\"
        fi
        rm -f logs/\${service}.pid
    fi
done
pkill -f 'honeypots/'
pkill -f 'dashboard/app.py'
echo '✅ All services stopped'
EOF

chmod +x stop_honeypots.sh

# Create status check script
cat > check_status.sh <<'EOF'
#!/bin/bash
echo '🔍 Honeypot System Status'
echo '========================'
echo \"📅 Current Time: \$(date)\"
echo \"🐳 Memory Usage: \$(free -h | grep Mem | awk '{print \$3\"/\"\$2}')\"
echo \"💾 Disk Usage: \$(df -h / | tail -1 | awk '{print \$3\"/\"\$2\" (\"\$5\" used)\"}')\"
echo \"\"
echo \"🍯 Honeypot Services:\"
for service in ssh http ftp telnet dashboard; do
    if [ -f \"logs/\${service}.pid\" ]; then
        pid=\$(cat logs/\${service}.pid)
        if kill -0 \$pid 2>/dev/null; then
            echo \"✅ \$service honeypot (PID: \$pid) - RUNNING\"
        else
            echo \"❌ \$service honeypot - STOPPED\"
        fi
    else
        echo \"❌ \$service honeypot - NOT STARTED\"
    fi
done
echo \"\"
echo \"🌐 Network Connections:\"
netstat -tuln | grep -E ':(22|80|21|23|2222|12000)' | head -5
EOF

chmod +x check_status.sh

# Start honeypot services
./start_honeypots.sh

echo '✅ Honeypot deployment completed!'
"

print_status "Deploying honeypot services..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$HONEYPOT_PUBLIC_IP "$HONEYPOT_DEPLOYMENT"

print_status "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Phase 4: Final Testing and Verification
print_header "Phase 4: Testing and Verification"

print_status "Testing ELK Stack connectivity..."
if curl -s "http://$ELK_PUBLIC_IP:9200/_cluster/health" >/dev/null 2>&1; then
    print_status "✅ Elasticsearch is accessible externally"
else
    print_warning "⚠️ Elasticsearch is not accessible externally (check security groups)"
fi

if curl -s "http://$ELK_PUBLIC_IP:5601/api/status" >/dev/null 2>&1; then
    print_status "✅ Kibana is accessible externally"
else
    print_warning "⚠️ Kibana is not accessible externally (check security groups)"
fi

print_status "Testing Honeypot Services..."
if curl -s "http://$HONEYPOT_PUBLIC_IP" >/dev/null 2>&1; then
    print_status "✅ HTTP honeypot is accessible"
else
    print_warning "⚠️ HTTP honeypot is not accessible"
fi

if curl -s "http://$HONEYPOT_PUBLIC_IP:12000" >/dev/null 2>&1; then
    print_status "✅ Dashboard is accessible"
else
    print_warning "⚠️ Dashboard is not accessible (check security groups)"
fi

# Final status check
print_status "Getting final system status..."
ssh -i "$KEY_PATH" ubuntu@$HONEYPOT_PUBLIC_IP "cd cybersecurity-honeypot-system && ./check_status.sh"

echo ""
print_header "🎉 Deployment Complete!"
echo ""
print_status "🔗 Access URLs:"
echo "• 📊 Honeypot Dashboard: http://$HONEYPOT_PUBLIC_IP:12000"
echo "• 📈 Kibana (ELK): http://$ELK_PUBLIC_IP:5601"
echo "• 🔍 Elasticsearch: http://$ELK_PUBLIC_IP:9200"
echo ""
print_status "🧪 Test Your Honeypots:"
echo "• SSH: ssh -p 2222 test@$HONEYPOT_PUBLIC_IP"
echo "• HTTP: curl http://$HONEYPOT_PUBLIC_IP/admin"
echo "• FTP: ftp $HONEYPOT_PUBLIC_IP"
echo "• Telnet: telnet $HONEYPOT_PUBLIC_IP 23"
echo ""
print_status "🔧 Management Commands:"
echo "• Check status: ssh -i $KEY_PATH ubuntu@$HONEYPOT_PUBLIC_IP 'cd cybersecurity-honeypot-system && ./check_status.sh'"
echo "• Stop services: ssh -i $KEY_PATH ubuntu@$HONEYPOT_PUBLIC_IP 'cd cybersecurity-honeypot-system && ./stop_honeypots.sh'"
echo "• Start services: ssh -i $KEY_PATH ubuntu@$HONEYPOT_PUBLIC_IP 'cd cybersecurity-honeypot-system && ./start_honeypots.sh'"
echo ""
print_warning "⚠️ Important Security Notes:"
echo "1. Restrict Kibana and Dashboard access to your IP only in security groups"
echo "2. Monitor resource usage regularly (AWS Free Tier limits)"
echo "3. Set up log rotation to prevent disk space issues"
echo "4. Review attack logs regularly for interesting patterns"
echo ""
print_status "🎯 Your honeypot system is now ready to catch attackers!"