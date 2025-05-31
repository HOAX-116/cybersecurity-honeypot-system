#!/bin/bash

# Connectivity Check Script
echo "🔍 AWS Honeypot System Connectivity Check"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Your instance IPs
ELK_IP="100.26.191.27"
HONEYPOT_IP="54.165.107.7"
KEY_PATH="$HOME/.ssh/honeypot-key.pem"

echo "📍 Your current public IP address:"
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "Unable to determine")
echo "   $CURRENT_IP"
echo ""

echo "🔑 SSH Key check:"
if [ -f "$KEY_PATH" ]; then
    PERMS=$(stat -c %a "$KEY_PATH")
    if [ "$PERMS" = "400" ]; then
        echo -e "   ${GREEN}✅ SSH key found with correct permissions${NC}"
    else
        echo -e "   ${YELLOW}⚠️ SSH key found but permissions are $PERMS (should be 400)${NC}"
        echo "   Run: chmod 400 $KEY_PATH"
    fi
else
    echo -e "   ${RED}❌ SSH key not found at $KEY_PATH${NC}"
    echo "   Please save your SSH key to this location"
fi
echo ""

echo "🌐 Testing connectivity to your instances:"

# Test ELK instance
echo -n "   ELK Stack ($ELK_IP): "
if ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$ELK_IP "echo 'success'" 2>/dev/null | grep -q "success"; then
    echo -e "${GREEN}✅ Connected${NC}"
    ELK_CONNECTED=true
else
    echo -e "${RED}❌ Cannot connect${NC}"
    ELK_CONNECTED=false
fi

# Test Honeypot instance
echo -n "   Honeypot ($HONEYPOT_IP): "
if ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$HONEYPOT_IP "echo 'success'" 2>/dev/null | grep -q "success"; then
    echo -e "${GREEN}✅ Connected${NC}"
    HONEYPOT_CONNECTED=true
else
    echo -e "${RED}❌ Cannot connect${NC}"
    HONEYPOT_CONNECTED=false
fi

echo ""

if [ "$ELK_CONNECTED" = true ] && [ "$HONEYPOT_CONNECTED" = true ]; then
    echo -e "${GREEN}🎉 All systems accessible! You can now run the deployment script:${NC}"
    echo "   ./automated_deploy.sh"
else
    echo -e "${YELLOW}⚠️ Some instances are not accessible. Please check:${NC}"
    echo ""
    echo "1. Security Groups Configuration:"
    echo "   - Go to AWS Console → EC2 → Security Groups"
    echo "   - Add SSH rule (port 22) with source: $CURRENT_IP/32"
    echo ""
    echo "2. Instance Status:"
    echo "   - Ensure both instances are running in AWS Console"
    echo ""
    echo "3. Network Issues:"
    echo "   - Check if your IP has changed"
    echo "   - Try from a different network"
    echo ""
    echo "📖 For detailed instructions, see: SECURITY_GROUP_SETUP.md"
fi

echo ""
echo "📚 Available guides:"
echo "   • SECURITY_GROUP_SETUP.md - Security group configuration"
echo "   • DEPLOYMENT_INSTRUCTIONS.md - Manual deployment steps"
echo "   • automated_deploy.sh - Automated deployment script"