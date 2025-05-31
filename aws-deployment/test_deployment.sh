#!/bin/bash

# Quick Test Script for AWS Honeypot Deployment
# Tests all services and provides status report

set -e

echo "🧪 Testing AWS Honeypot Deployment"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

# Instance details
ELK_PUBLIC_IP="100.26.191.27"
HONEYPOT_PUBLIC_IP="54.165.107.7"
KEY_PATH="$HOME/.ssh/honeypot-key.pem"

echo "Testing instances:"
echo "• ELK Stack: $ELK_PUBLIC_IP"
echo "• Honeypot: $HONEYPOT_PUBLIC_IP"
echo ""

# Test 1: SSH Connectivity
print_status "Testing SSH connectivity..."
if ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$ELK_PUBLIC_IP "echo 'ELK SSH OK'" 2>/dev/null; then
    print_success "ELK instance SSH connectivity"
else
    print_error "ELK instance SSH connectivity"
fi

if ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$HONEYPOT_PUBLIC_IP "echo 'Honeypot SSH OK'" 2>/dev/null; then
    print_success "Honeypot instance SSH connectivity"
else
    print_error "Honeypot instance SSH connectivity"
fi

# Test 2: ELK Stack Services
print_status "Testing ELK Stack services..."
if curl -s --connect-timeout 10 "http://$ELK_PUBLIC_IP:9200/_cluster/health" | grep -q "yellow\|green"; then
    print_success "Elasticsearch is running and healthy"
else
    print_error "Elasticsearch is not accessible or unhealthy"
fi

if curl -s --connect-timeout 10 "http://$ELK_PUBLIC_IP:5601/api/status" | grep -q "available"; then
    print_success "Kibana is running and available"
else
    print_warning "Kibana may still be starting up or not accessible"
fi

# Test 3: Honeypot Services
print_status "Testing Honeypot services..."

# HTTP Honeypot
if curl -s --connect-timeout 10 "http://$HONEYPOT_PUBLIC_IP" >/dev/null; then
    print_success "HTTP honeypot (port 80) is accessible"
else
    print_error "HTTP honeypot (port 80) is not accessible"
fi

# SSH Honeypot
if timeout 5 nc -z $HONEYPOT_PUBLIC_IP 2222 2>/dev/null; then
    print_success "SSH honeypot (port 2222) is listening"
else
    print_error "SSH honeypot (port 2222) is not listening"
fi

# FTP Honeypot
if timeout 5 nc -z $HONEYPOT_PUBLIC_IP 21 2>/dev/null; then
    print_success "FTP honeypot (port 21) is listening"
else
    print_error "FTP honeypot (port 21) is not listening"
fi

# Telnet Honeypot
if timeout 5 nc -z $HONEYPOT_PUBLIC_IP 23 2>/dev/null; then
    print_success "Telnet honeypot (port 23) is listening"
else
    print_error "Telnet honeypot (port 23) is not listening"
fi

# Dashboard
if curl -s --connect-timeout 10 "http://$HONEYPOT_PUBLIC_IP:12000" >/dev/null; then
    print_success "Dashboard (port 12000) is accessible"
else
    print_error "Dashboard (port 12000) is not accessible"
fi

# Test 4: System Resources
print_status "Checking system resources..."

ELK_MEMORY=$(ssh -i "$KEY_PATH" ubuntu@$ELK_PUBLIC_IP "free | grep Mem | awk '{printf \"%.0f\", \$3/\$2 * 100.0}'" 2>/dev/null || echo "N/A")
HONEYPOT_MEMORY=$(ssh -i "$KEY_PATH" ubuntu@$HONEYPOT_PUBLIC_IP "free | grep Mem | awk '{printf \"%.0f\", \$3/\$2 * 100.0}'" 2>/dev/null || echo "N/A")

echo "• ELK Stack memory usage: ${ELK_MEMORY}%"
echo "• Honeypot memory usage: ${HONEYPOT_MEMORY}%"

if [ "$ELK_MEMORY" != "N/A" ] && [ "$ELK_MEMORY" -lt 90 ]; then
    print_success "ELK Stack memory usage is acceptable"
else
    print_warning "ELK Stack memory usage is high"
fi

if [ "$HONEYPOT_MEMORY" != "N/A" ] && [ "$HONEYPOT_MEMORY" -lt 90 ]; then
    print_success "Honeypot memory usage is acceptable"
else
    print_warning "Honeypot memory usage is high"
fi

# Test 5: Service Status on Honeypot Instance
print_status "Checking honeypot service status..."
HONEYPOT_STATUS=$(ssh -i "$KEY_PATH" ubuntu@$HONEYPOT_PUBLIC_IP "cd cybersecurity-honeypot-system && ./check_status.sh" 2>/dev/null || echo "Status check failed")
echo "$HONEYPOT_STATUS"

# Test 6: Generate Test Attack
print_status "Generating test attack data..."
echo "Attempting to trigger honeypots..."

# Test SSH honeypot
echo "Testing SSH honeypot..."
timeout 10 ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null test@$HONEYPOT_PUBLIC_IP 2>/dev/null || true

# Test HTTP honeypot
echo "Testing HTTP honeypot..."
curl -s "http://$HONEYPOT_PUBLIC_IP/admin" >/dev/null || true
curl -s "http://$HONEYPOT_PUBLIC_IP/wp-admin" >/dev/null || true

print_success "Test attacks generated"

# Summary
echo ""
echo "🎯 Test Summary"
echo "==============="
echo "• ELK Stack IP: $ELK_PUBLIC_IP"
echo "• Honeypot IP: $HONEYPOT_PUBLIC_IP"
echo ""
echo "🔗 Access URLs:"
echo "• Dashboard: http://$HONEYPOT_PUBLIC_IP:12000"
echo "• Kibana: http://$ELK_PUBLIC_IP:5601"
echo "• Elasticsearch: http://$ELK_PUBLIC_IP:9200"
echo ""
echo "🧪 Manual Tests:"
echo "• SSH: ssh -p 2222 admin@$HONEYPOT_PUBLIC_IP"
echo "• HTTP: curl http://$HONEYPOT_PUBLIC_IP/admin"
echo "• FTP: ftp $HONEYPOT_PUBLIC_IP"
echo "• Telnet: telnet $HONEYPOT_PUBLIC_IP 23"
echo ""
print_status "✅ Testing completed! Check the dashboard and Kibana for attack data."