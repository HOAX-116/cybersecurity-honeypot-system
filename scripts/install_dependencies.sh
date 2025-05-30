#!/bin/bash

# Multi-Service Cybersecurity Honeypot System
# Installation Script

set -e

echo "🛡️  Installing Cybersecurity Honeypot System Dependencies"
echo "========================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  This script should not be run as root for security reasons"
   exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    docker-compose \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Start and enable Docker
echo "🐳 Setting up Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs data elk-stack/logstash/{config,pipeline} dashboard/templates

# Download GeoLite2 database (requires manual download due to MaxMind licensing)
echo "🌍 Setting up GeoIP database..."
if [ ! -f "data/GeoLite2-City.mmdb" ]; then
    echo "⚠️  GeoLite2 database not found."
    echo "Please download GeoLite2-City.mmdb from MaxMind and place it in the data/ directory."
    echo "You can register for free at: https://www.maxmind.com/en/geolite2/signup"
    echo "After registration, download the GeoLite2 City database and extract GeoLite2-City.mmdb to data/"
fi

# Set up log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/honeypot > /dev/null <<EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF

# Create systemd service files
echo "⚙️  Creating systemd service files..."

# Honeypot service
sudo tee /etc/systemd/system/honeypot.service > /dev/null <<EOF
[Unit]
Description=Multi-Service Honeypot System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python honeypots/start_all.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Dashboard service
sudo tee /etc/systemd/system/honeypot-dashboard.service > /dev/null <<EOF
[Unit]
Description=Honeypot Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python dashboard/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Set up firewall rules (optional)
echo "🔥 Setting up firewall rules..."
if command -v ufw &> /dev/null; then
    echo "Setting up UFW firewall rules..."
    sudo ufw allow 2222/tcp comment "SSH Honeypot"
    sudo ufw allow 8080/tcp comment "HTTP Honeypot"
    sudo ufw allow 2121/tcp comment "FTP Honeypot"
    sudo ufw allow 2323/tcp comment "Telnet Honeypot"
    sudo ufw allow 12000/tcp comment "Dashboard"
    sudo ufw allow 5601/tcp comment "Kibana"
    echo "Firewall rules added. Enable with: sudo ufw enable"
fi

# Create startup script
echo "🚀 Creating startup script..."
cat > start_honeypot.sh << 'EOF'
#!/bin/bash

echo "🛡️  Starting Cybersecurity Honeypot System"
echo "=========================================="

# Start ELK stack
echo "📊 Starting ELK Stack..."
docker-compose up -d elasticsearch logstash kibana

# Wait for Elasticsearch to be ready
echo "⏳ Waiting for Elasticsearch to be ready..."
while ! curl -s http://localhost:9200 > /dev/null; do
    sleep 5
done

# Start honeypots
echo "🕸️  Starting honeypots..."
sudo systemctl start honeypot

# Start dashboard
echo "📈 Starting dashboard..."
sudo systemctl start honeypot-dashboard

echo "✅ Honeypot system started successfully!"
echo ""
echo "Access points:"
echo "  Dashboard: http://localhost:12000"
echo "  Kibana: http://localhost:5601"
echo ""
echo "Honeypot services:"
echo "  SSH: port 2222"
echo "  HTTP: port 8080"
echo "  FTP: port 2121"
echo "  Telnet: port 2323"
EOF

chmod +x start_honeypot.sh

# Create stop script
cat > stop_honeypot.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping Cybersecurity Honeypot System"
echo "========================================"

# Stop services
sudo systemctl stop honeypot
sudo systemctl stop honeypot-dashboard

# Stop ELK stack
docker-compose down

echo "✅ Honeypot system stopped successfully!"
EOF

chmod +x stop_honeypot.sh

# Create status script
cat > status_honeypot.sh << 'EOF'
#!/bin/bash

echo "📊 Cybersecurity Honeypot System Status"
echo "======================================"

echo "Honeypot Services:"
sudo systemctl status honeypot --no-pager -l
echo ""

echo "Dashboard Service:"
sudo systemctl status honeypot-dashboard --no-pager -l
echo ""

echo "Docker Containers:"
docker-compose ps
echo ""

echo "Port Status:"
netstat -tlnp | grep -E "(2222|8080|2121|2323|12000|5601|9200)"
EOF

chmod +x status_honeypot.sh

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Download GeoLite2-City.mmdb and place it in data/ directory"
echo "2. Review and customize config/honeypot_config.yaml"
echo "3. Start the system with: ./start_honeypot.sh"
echo "4. Check status with: ./status_honeypot.sh"
echo "5. Access dashboard at: http://localhost:12000"
echo ""
echo "⚠️  Important Security Notes:"
echo "- Change default passwords in config file"
echo "- Review firewall settings"
echo "- Monitor logs regularly"
echo "- Keep system updated"
echo ""
echo "For manual control:"
echo "- Start honeypots: sudo systemctl start honeypot"
echo "- Start dashboard: sudo systemctl start honeypot-dashboard"
echo "- Start ELK stack: docker-compose up -d"