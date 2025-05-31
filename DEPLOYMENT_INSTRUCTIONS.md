# 🚀 AWS Honeypot System Deployment Instructions

## Your Instance Details
- **ELK Stack**: `100.26.191.27` (Private: `172.31.81.26`)
- **Honeypot Services**: `54.165.107.7` (Private: `172.31.84.247`)

## Step 1: Configure Security Groups (CRITICAL - Do This First!)

### 1.1 Get Your Current IP Address
First, find your current public IP address:
```bash
curl ifconfig.me
```
**Write down this IP address - you'll need it for security group rules.**

### 1.2 Configure ELK Stack Security Group

1. Go to **AWS Console** → **EC2** → **Security Groups**
2. Find the security group attached to your ELK instance (`i-07849409590c08a3f`)
3. Click **Edit inbound rules**
4. Add these rules:

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| SSH | TCP | 22 | Your IP/32 | SSH access |
| Custom TCP | TCP | 5601 | Your IP/32 | Kibana |
| Custom TCP | TCP | 9200 | sg-xxxxx | Elasticsearch (honeypot SG) |
| Custom TCP | TCP | 5044 | sg-xxxxx | Logstash (honeypot SG) |

**Note**: For the last two rules, use the security group ID of your honeypot instance instead of `sg-xxxxx`.

### 1.3 Configure Honeypot Services Security Group

1. Find the security group attached to your honeypot instance (`i-0c876f3852ee6cb60`)
2. Click **Edit inbound rules**
3. Add these rules:

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| SSH | TCP | 22 | Your IP/32 | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP honeypot |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS honeypot |
| Custom TCP | TCP | 21 | 0.0.0.0/0 | FTP honeypot |
| Custom TCP | TCP | 23 | 0.0.0.0/0 | Telnet honeypot |
| Custom TCP | TCP | 25 | 0.0.0.0/0 | SMTP honeypot |
| Custom TCP | TCP | 2222 | 0.0.0.0/0 | SSH honeypot |
| Custom TCP | TCP | 3389 | 0.0.0.0/0 | RDP honeypot |
| Custom TCP | TCP | 12000 | Your IP/32 | Dashboard |

## Step 2: Test SSH Connectivity

After configuring security groups, test SSH access:

```bash
# Test ELK instance
ssh -i ~/.ssh/honeypot-key.pem ubuntu@100.26.191.27

# Test Honeypot instance  
ssh -i ~/.ssh/honeypot-key.pem ubuntu@54.165.107.7
```

If you can connect successfully, proceed to Step 3.

## Step 3: Deploy ELK Stack

SSH into your ELK instance and run these commands:

```bash
ssh -i ~/.ssh/honeypot-key.pem ubuntu@100.26.191.27

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
git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
cd cybersecurity-honeypot-system/aws-deployment

# Make scripts executable
chmod +x *.sh

# Run ELK setup
./elk-setup.sh
```

**Wait for the ELK setup to complete (this may take 5-10 minutes).**

## Step 4: Deploy Honeypot Services

SSH into your honeypot instance and run these commands:

```bash
ssh -i ~/.ssh/honeypot-key.pem ubuntu@54.165.107.7

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git curl wget htop fail2ban ufw netcat

# Clone repository
git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
cd cybersecurity-honeypot-system/aws-deployment

# Run honeypot setup script
chmod +x *.sh
./honeypot-setup.sh

# Reboot to apply changes
sudo reboot
```

**Wait for the instance to reboot (about 2-3 minutes).**

## Step 5: Configure and Start Honeypot Services

After reboot, SSH back into the honeypot instance:

```bash
ssh -i ~/.ssh/honeypot-key.pem ubuntu@54.165.107.7
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
wget -O data/GeoLite2-City.mmdb.gz 'https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb.gz'
gunzip data/GeoLite2-City.mmdb.gz

# Update configuration with ELK IP
cp config/honeypot-config-aws.yaml config/honeypot_config.yaml
sed -i 's/host: "localhost"/host: "172.31.81.26"/g' config/honeypot_config.yaml
```

## Step 6: Create Management Scripts

Create startup script:

```bash
cat > start_honeypots.sh <<'EOF'
#!/bin/bash
echo '🍯 Starting Honeypot Services...'
source venv/bin/activate
mkdir -p logs

# Start honeypot services
python3 -u honeypots/ssh_honeypot.py > logs/ssh_honeypot.log 2>&1 &
echo $! > logs/ssh.pid

python3 -u honeypots/http_honeypot.py > logs/http_honeypot.log 2>&1 &
echo $! > logs/http.pid

python3 -u honeypots/ftp_honeypot.py > logs/ftp_honeypot.log 2>&1 &
echo $! > logs/ftp.pid

python3 -u honeypots/telnet_honeypot.py > logs/telnet_honeypot.log 2>&1 &
echo $! > logs/telnet.pid

python3 -u dashboard/app.py > logs/dashboard.log 2>&1 &
echo $! > logs/dashboard.pid

echo '✅ All honeypot services started!'
EOF

chmod +x start_honeypots.sh
```

Create stop script:

```bash
cat > stop_honeypots.sh <<'EOF'
#!/bin/bash
echo '🛑 Stopping Honeypot Services...'
for service in ssh http ftp telnet dashboard; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat logs/${service}.pid)
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo "Stopped $service honeypot"
        fi
        rm -f logs/${service}.pid
    fi
done
pkill -f 'honeypots/'
pkill -f 'dashboard/app.py'
echo '✅ All services stopped'
EOF

chmod +x stop_honeypots.sh
```

Create status check script:

```bash
cat > check_status.sh <<'EOF'
#!/bin/bash
echo '🔍 Honeypot System Status'
echo '========================'
echo "📅 Current Time: $(date)"
echo "🐳 Memory Usage: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "💾 Disk Usage: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
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
echo "🌐 Network Connections:"
netstat -tuln | grep -E ':(22|80|21|23|2222|12000)' | head -5
EOF

chmod +x check_status.sh
```

## Step 7: Start the Honeypot System

```bash
# Start all honeypot services
./start_honeypots.sh

# Check status
./check_status.sh
```

## Step 8: Verify Deployment

### 8.1 Test ELK Stack
Open your browser and visit:
- **Kibana**: http://100.26.191.27:5601
- **Elasticsearch**: http://100.26.191.27:9200

### 8.2 Test Honeypot Services
Open your browser and visit:
- **Dashboard**: http://54.165.107.7:12000
- **HTTP Honeypot**: http://54.165.107.7

### 8.3 Test Individual Honeypots

```bash
# SSH Honeypot
ssh -p 2222 test@54.165.107.7

# HTTP Honeypot
curl http://54.165.107.7/admin

# FTP Honeypot
ftp 54.165.107.7

# Telnet Honeypot
telnet 54.165.107.7 23
```

## 🎉 Success! Your Honeypot System is Running

### Access URLs:
- **📊 Honeypot Dashboard**: http://54.165.107.7:12000
- **📈 Kibana (ELK)**: http://100.26.191.27:5601
- **🔍 Elasticsearch**: http://100.26.191.27:9200

### Management Commands:
```bash
# Check status
./check_status.sh

# Stop services
./stop_honeypots.sh

# Start services
./start_honeypots.sh

# View logs
tail -f logs/honeypot.log
tail -f logs/ssh_honeypot.log
```

### Monitoring:
- Monitor memory usage: `free -h`
- Monitor disk usage: `df -h`
- Monitor Docker containers: `docker ps`
- View attack logs: `tail -f logs/*.log`

## ⚠️ Important Security Notes:

1. **Restrict Access**: Update security groups to allow Kibana and Dashboard access only from your IP
2. **Monitor Resources**: Keep an eye on AWS Free Tier usage limits
3. **Log Rotation**: The system automatically rotates logs to prevent disk space issues
4. **Regular Updates**: Update the system regularly with `sudo apt update && sudo apt upgrade`

## 🔧 Troubleshooting:

If services don't start:
1. Check logs: `tail -f logs/*.log`
2. Check memory: `free -h`
3. Restart services: `./stop_honeypots.sh && ./start_honeypots.sh`
4. Reboot if needed: `sudo reboot`

Your honeypot system is now ready to detect and log cyber attacks! 🛡️🍯