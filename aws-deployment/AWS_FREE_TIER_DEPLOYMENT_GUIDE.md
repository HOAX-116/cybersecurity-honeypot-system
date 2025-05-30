# AWS Free Tier Honeypot Deployment Guide

This guide provides step-by-step instructions for deploying the cybersecurity honeypot system on AWS Free Tier with optimizations for t2.micro instances.

## 🎯 Overview

The deployment is optimized for AWS Free Tier with the following specifications:
- **Instance Type**: t2.micro (1 vCPU, 1GB RAM)
- **Storage**: 30GB EBS (free tier limit)
- **Memory Usage**: ~650MB for ELK stack, ~200MB for honeypots
- **Network**: Optimized for minimal data transfer

## 📋 Prerequisites

- AWS Account with Free Tier eligibility
- Basic knowledge of AWS EC2 and security groups
- SSH client (PuTTY for Windows, Terminal for Mac/Linux)

## 🚀 Step-by-Step Deployment

### STEP 1: Create Key Pair

1. **AWS Console** → Search "EC2" → Click "EC2"
2. **Left sidebar** → "Key Pairs" (under Network & Security)
3. **Create key pair**:
   - Name: `honeypot-key`
   - Type: RSA
   - Format: .pem
4. **Download and secure the key**:
   ```bash
   chmod 400 ~/Downloads/honeypot-key.pem
   ```

### STEP 2: Create Security Groups

#### Security Group 1: Honeypot Services
- **Name**: `honeypot-services-sg`
- **Description**: Security group for honeypot services
- **Inbound Rules**:
  ```
  SSH     | TCP | 22   | My IP        | SSH access
  HTTP    | TCP | 80   | 0.0.0.0/0    | HTTP honeypot
  HTTPS   | TCP | 443  | 0.0.0.0/0    | HTTPS honeypot
  Custom  | TCP | 21   | 0.0.0.0/0    | FTP honeypot
  Custom  | TCP | 23   | 0.0.0.0/0    | Telnet honeypot
  Custom  | TCP | 25   | 0.0.0.0/0    | SMTP honeypot
  Custom  | TCP | 2222 | 0.0.0.0/0    | SSH honeypot
  Custom  | TCP | 3389 | 0.0.0.0/0    | RDP honeypot
  Custom  | TCP | 12000| My IP        | Dashboard
  ```

#### Security Group 2: ELK Stack
- **Name**: `elk-stack-sg`
- **Description**: Security group for ELK stack
- **Inbound Rules**:
  ```
  SSH     | TCP | 22   | My IP                | SSH access
  Custom  | TCP | 5601 | My IP                | Kibana
  Custom  | TCP | 9200 | honeypot-services-sg | Elasticsearch
  Custom  | TCP | 5044 | honeypot-services-sg | Logstash
  ```

### STEP 3: Launch ELK Stack Instance

1. **Launch Instance**:
   - Name: `elk-stack`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t2.micro
   - Key pair: honeypot-key
   - Security group: elk-stack-sg
   - Storage: 30 GiB

2. **Connect and Setup**:
   ```bash
   ssh -i ~/Downloads/honeypot-key.pem ubuntu@YOUR_ELK_PUBLIC_IP
   ```

3. **Run Initial Setup**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Docker
   sudo apt install -y docker.io docker-compose curl wget
   sudo systemctl enable docker
   sudo systemctl start docker
   sudo usermod -aG docker ubuntu
   
   # Reboot to apply changes
   sudo reboot
   ```

4. **Deploy ELK Stack**:
   ```bash
   # Reconnect after reboot
   ssh -i ~/Downloads/honeypot-key.pem ubuntu@YOUR_ELK_PUBLIC_IP
   
   # Clone repository
   git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
   cd cybersecurity-honeypot-system/aws-deployment
   
   # Make scripts executable
   chmod +x *.sh
   
   # Run ELK setup
   ./elk-setup.sh
   ```

### STEP 4: Launch Honeypot Services Instance

1. **Launch Instance**:
   - Name: `honeypot-services`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t2.micro
   - Key pair: honeypot-key
   - Security group: honeypot-services-sg
   - Storage: 30 GiB

2. **Connect and Setup**:
   ```bash
   ssh -i ~/Downloads/honeypot-key.pem ubuntu@YOUR_HONEYPOT_PUBLIC_IP
   ```

3. **Run Initial Setup**:
   ```bash
   # Clone repository
   git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
   cd cybersecurity-honeypot-system/aws-deployment
   
   # Run honeypot setup
   chmod +x *.sh
   ./honeypot-setup.sh
   
   # Reboot to apply changes
   sudo reboot
   ```

4. **Deploy Honeypot Services**:
   ```bash
   # Reconnect after reboot
   ssh -i ~/Downloads/honeypot-key.pem ubuntu@YOUR_HONEYPOT_PUBLIC_IP
   cd cybersecurity-honeypot-system
   
   # Deploy honeypots (you'll need the ELK private IP)
   ./aws-deployment/deploy-honeypot.sh
   ```

### STEP 5: Start and Test Services

1. **Start Honeypot Services**:
   ```bash
   ./start_honeypots.sh
   ```

2. **Test Services**:
   ```bash
   ./test_honeypots.sh
   ```

3. **Check Status**:
   ```bash
   ./check_status.sh
   ```

## 🔧 Management Commands

### Honeypot Instance
```bash
# Start services
./start_honeypots.sh

# Stop services
./stop_honeypots.sh

# Check status
./check_status.sh

# Test connectivity
./test_honeypots.sh

# Rotate logs
./rotate_logs.sh

# Systemd management
sudo systemctl start honeypot
sudo systemctl stop honeypot
sudo systemctl status honeypot
```

### ELK Instance
```bash
# Monitor ELK stack
./monitor_elk.sh

# Cleanup old data
./cleanup_elk.sh

# Docker management
docker-compose -f docker-compose-freetier.yml ps
docker-compose -f docker-compose-freetier.yml logs
docker-compose -f docker-compose-freetier.yml restart
```

## 📊 Access URLs

Replace `YOUR_PUBLIC_IP` with your actual instance public IP addresses:

- **Dashboard**: `http://YOUR_HONEYPOT_PUBLIC_IP:12000`
- **Kibana**: `http://YOUR_ELK_PUBLIC_IP:5601`
- **Elasticsearch**: `http://YOUR_ELK_PUBLIC_IP:9200`

## 🔍 Testing Your Honeypots

### SSH Honeypot
```bash
ssh -p 2222 admin@YOUR_HONEYPOT_PUBLIC_IP
# Try password: admin
```

### HTTP Honeypot
```bash
curl http://YOUR_HONEYPOT_PUBLIC_IP/admin
curl http://YOUR_HONEYPOT_PUBLIC_IP/wp-admin
```

### FTP Honeypot
```bash
ftp YOUR_HONEYPOT_PUBLIC_IP
# Try anonymous login
```

### Telnet Honeypot
```bash
telnet YOUR_HONEYPOT_PUBLIC_IP 23
# Try username: admin, password: admin
```

## 📈 Monitoring and Maintenance

### Resource Monitoring
```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check running processes
htop

# Monitor Docker containers
docker stats
```

### Log Management
```bash
# View honeypot logs
tail -f logs/honeypot.log

# View specific service logs
tail -f logs/ssh_honeypot.log
tail -f logs/http_honeypot.log

# Check log sizes
ls -lh logs/
```

### Automatic Maintenance
The system includes automatic:
- **Log rotation** (every 30 minutes)
- **ELK cleanup** (daily at 2 AM)
- **Service restart** on failure
- **Memory monitoring** (every 5 minutes)

## ⚠️ Free Tier Limitations & Optimizations

### Memory Optimizations
- **Elasticsearch**: 256MB heap (down from 512MB)
- **Logstash**: 128MB heap (down from 256MB)
- **Kibana**: 256MB max memory
- **Redis**: 50MB max memory
- **Total ELK usage**: ~650MB

### Storage Optimizations
- **Log rotation**: 5MB max per log file
- **Index cleanup**: Removes indices older than 7 days
- **Single shard**: No replicas to save space
- **Compressed logs**: Automatic compression

### Network Optimizations
- **Reduced update intervals**: Less frequent data transfers
- **Batch processing**: Efficient log shipping
- **Local caching**: Reduced external API calls

## 🔒 Security Best Practices

### Instance Security
1. **Keep systems updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Monitor failed login attempts**:
   ```bash
   sudo tail -f /var/log/auth.log
   ```

3. **Use fail2ban** (automatically configured):
   ```bash
   sudo fail2ban-client status
   ```

### Network Security
1. **Restrict management access** to your IP only
2. **Use VPN** for accessing Kibana and dashboard
3. **Monitor unusual traffic patterns**
4. **Regular security group reviews**

### Data Security
1. **Regular backups** of important logs
2. **Encrypt sensitive data** in transit
3. **Monitor for data exfiltration**
4. **Regular security audits**

## 🚨 Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
free -h

# Restart services if needed
sudo systemctl restart honeypot
cd ~/cybersecurity-honeypot-system/aws-deployment
docker-compose -f docker-compose-freetier.yml restart
```

#### Services Not Starting
```bash
# Check service status
./check_status.sh

# Check logs for errors
tail -f logs/startup.log
tail -f logs/honeypot.log

# Manual restart
./stop_honeypots.sh
./start_honeypots.sh
```

#### ELK Stack Issues
```bash
# Check ELK status
./monitor_elk.sh

# Check Docker logs
docker-compose -f docker-compose-freetier.yml logs

# Restart ELK stack
docker-compose -f docker-compose-freetier.yml restart
```

#### Network Connectivity
```bash
# Test ports
nmap -p 80,2222,21,23,12000 YOUR_HONEYPOT_PUBLIC_IP

# Check security groups in AWS Console
# Verify firewall rules
sudo ufw status
```

### Performance Optimization

#### If Memory Usage is High
1. **Reduce log retention**:
   ```bash
   # Edit cleanup script to remove logs more frequently
   nano cleanup_elk.sh
   ```

2. **Disable unnecessary services**:
   ```bash
   # Edit config to disable some honeypots
   nano config/honeypot_config.yaml
   ```

3. **Increase swap space**:
   ```bash
   sudo fallocate -l 1G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

#### If Disk Usage is High
1. **Manual log cleanup**:
   ```bash
   ./rotate_logs.sh
   ./cleanup_elk.sh
   ```

2. **Remove old Docker images**:
   ```bash
   docker system prune -f
   ```

## 📞 Support and Updates

### Getting Help
- **Check logs** first for error messages
- **Review this guide** for common solutions
- **Monitor system resources** for bottlenecks
- **Test network connectivity** between instances

### Updating the System
```bash
# Update honeypot code
cd ~/cybersecurity-honeypot-system
git pull origin main

# Restart services
./stop_honeypots.sh
./start_honeypots.sh

# Update system packages
sudo apt update && sudo apt upgrade -y
```

### Backup Important Data
```bash
# Backup configuration
cp -r config/ ~/backup/

# Backup logs (if needed)
tar -czf ~/backup/logs-$(date +%Y%m%d).tar.gz logs/

# Backup Elasticsearch data
docker run --rm -v honeypot_elasticsearch_data:/data -v ~/backup:/backup alpine tar czf /backup/elasticsearch-$(date +%Y%m%d).tar.gz /data
```

## 🎉 Conclusion

Your AWS Free Tier honeypot system is now deployed and optimized for minimal resource usage while maintaining full functionality. The system will automatically:

- ✅ Monitor and log all attack attempts
- ✅ Provide real-time dashboards and analytics
- ✅ Rotate logs to prevent disk space issues
- ✅ Restart services automatically on failure
- ✅ Alert on high resource usage

Remember to monitor your AWS usage to stay within free tier limits and regularly review security logs for interesting attack patterns!

---

**Happy Honeypotting! 🍯🛡️**