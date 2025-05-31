#!/bin/bash

# Honeypot Services Deployment Script for AWS Instance
# Instance: i-0c876f3852ee6cb60 (54.165.107.7)

set -e

echo "🍯 Deploying Honeypot Services on AWS Instance..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# SSH connection details
HONEYPOT_PUBLIC_IP="54.165.107.7"
ELK_PRIVATE_IP="172.31.81.26"
KEY_PATH="$HOME/.ssh/honeypot-key.pem"  # Update this path to your key file

print_status "Connecting to Honeypot Services instance: $HONEYPOT_PUBLIC_IP"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    print_error "SSH key file not found at $KEY_PATH"
    print_warning "Please update the KEY_PATH variable in this script to point to your .pem file"
    exit 1
fi

# Create deployment commands
DEPLOYMENT_COMMANDS="
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git curl wget htop fail2ban ufw

# Clone repository
git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
cd cybersecurity-honeypot-system

# Run honeypot setup script
chmod +x aws-deployment/*.sh
./aws-deployment/honeypot-setup.sh

# Reboot to apply all changes
echo 'System will reboot in 10 seconds...'
sleep 10
sudo reboot
"

# Execute initial setup on honeypot instance
print_status "Executing initial setup commands on honeypot instance..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$HONEYPOT_PUBLIC_IP "$DEPLOYMENT_COMMANDS"

print_status "⏳ Waiting for instance to reboot (60 seconds)..."
sleep 60

# Wait for instance to come back online
print_status "Waiting for instance to come back online..."
while ! ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$HONEYPOT_PUBLIC_IP "echo 'Instance is back online'" 2>/dev/null; do
    echo -n "."
    sleep 5
done
echo ""

# Deploy honeypot services
HONEYPOT_DEPLOYMENT="
cd cybersecurity-honeypot-system

# Run deployment script with ELK IP
echo '$ELK_PRIVATE_IP' | ./aws-deployment/deploy-honeypot.sh

# Start honeypot services
./start_honeypots.sh &

echo '✅ Honeypot services deployment completed!'
echo '📊 Dashboard URL: http://$HONEYPOT_PUBLIC_IP:12000'
"

print_status "Deploying honeypot services..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$HONEYPOT_PUBLIC_IP "$HONEYPOT_DEPLOYMENT"

print_status "✅ Honeypot Services deployment completed!"
print_status "🔗 Access URLs:"
echo "• Dashboard: http://$HONEYPOT_PUBLIC_IP:12000"
echo "• SSH Honeypot: ssh -p 2222 test@$HONEYPOT_PUBLIC_IP"
echo "• HTTP Honeypot: http://$HONEYPOT_PUBLIC_IP"
echo "• FTP Honeypot: ftp $HONEYPOT_PUBLIC_IP"

print_warning "⚠️  Next steps:"
echo "1. Wait 2-3 minutes for all services to start"
echo "2. Test services: ssh -i $KEY_PATH ubuntu@$HONEYPOT_PUBLIC_IP 'cd cybersecurity-honeypot-system && ./test_honeypots.sh'"
echo "3. Check status: ssh -i $KEY_PATH ubuntu@$HONEYPOT_PUBLIC_IP 'cd cybersecurity-honeypot-system && ./check_status.sh'"
echo "4. Access dashboard and Kibana to view attack data"