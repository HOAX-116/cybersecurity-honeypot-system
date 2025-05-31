#!/bin/bash

# ELK Stack Deployment Script for AWS Instance
# Instance: i-07849409590c08a3f (100.26.191.27)

set -e

echo "🚀 Deploying ELK Stack on AWS Instance..."

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
ELK_PUBLIC_IP="100.26.191.27"
KEY_PATH="$HOME/.ssh/honeypot-key.pem"  # Update this path to your key file

print_status "Connecting to ELK Stack instance: $ELK_PUBLIC_IP"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    print_error "SSH key file not found at $KEY_PATH"
    print_warning "Please update the KEY_PATH variable in this script to point to your .pem file"
    exit 1
fi

# Create deployment commands
DEPLOYMENT_COMMANDS='
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and dependencies
sudo apt install -y docker.io docker-compose curl wget git

# Configure Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

# Clone repository
git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
cd cybersecurity-honeypot-system/aws-deployment

# Make scripts executable
chmod +x *.sh

# Run ELK setup
./elk-setup.sh

echo "✅ ELK Stack deployment completed!"
echo "📊 Kibana URL: http://100.26.191.27:5601"
echo "🔍 Elasticsearch URL: http://100.26.191.27:9200"
'

# Execute deployment on ELK instance
print_status "Executing deployment commands on ELK instance..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$ELK_PUBLIC_IP "$DEPLOYMENT_COMMANDS"

print_status "✅ ELK Stack deployment completed!"
print_status "🔗 Access URLs:"
echo "• Kibana: http://$ELK_PUBLIC_IP:5601"
echo "• Elasticsearch: http://$ELK_PUBLIC_IP:9200"

print_warning "⚠️  Next steps:"
echo "1. Wait 2-3 minutes for all services to start"
echo "2. Test Kibana access: curl http://$ELK_PUBLIC_IP:5601"
echo "3. Test Elasticsearch: curl http://$ELK_PUBLIC_IP:9200"
echo "4. Proceed to deploy honeypot services"