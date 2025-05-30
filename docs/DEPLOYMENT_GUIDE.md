# Deployment Guide

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04 LTS or newer
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB free space
- **CPU**: 2 cores minimum, 4 cores recommended
- **Network**: Internet connection for threat intelligence feeds

### Software Dependencies
- Python 3.8+
- Docker & Docker Compose
- Git
- Build tools (gcc, make, etc.)

## Installation Steps

### 1. Clone Repository
```bash
git clone <repository-url>
cd cybersecurity-honeypot-system
```

### 2. Run Installation Script
```bash
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

### 3. Download GeoIP Database
1. Register at [MaxMind](https://www.maxmind.com/en/geolite2/signup)
2. Download GeoLite2-City.mmdb
3. Place in `data/GeoLite2-City.mmdb`

### 4. Configure System
Edit `config/honeypot_config.yaml`:
- Update email settings for alerts
- Customize service ports if needed
- Set appropriate log levels

### 5. Start Services
```bash
./start_honeypot.sh
```

## Service Configuration

### SSH Honeypot (Port 2222)
- Simulates OpenSSH server
- Logs all login attempts
- Captures commands executed
- **Security**: Never allows actual login

### HTTP Honeypot (Port 8080)
- Simulates Apache web server
- Serves fake admin pages
- Detects web attacks (SQLi, XSS, etc.)
- Logs all HTTP requests

### FTP Honeypot (Port 2121)
- Simulates ProFTPD server
- Allows anonymous login only
- Logs file transfer attempts
- Serves fake file listings

### Telnet Honeypot (Port 2323)
- Simulates Telnet service
- Logs all login attempts
- Captures session interactions
- **Security**: Never allows actual login

## Dashboard Access

### Web Interface
- **URL**: http://localhost:12000
- **Features**: Real-time attack monitoring, geolocation mapping, statistics

### Kibana (ELK Stack)
- **URL**: http://localhost:5601
- **Features**: Advanced log analysis, custom dashboards, alerting

## Security Considerations

### Network Security
- Run honeypots on isolated network segment
- Use firewall rules to control access
- Monitor for lateral movement attempts

### Data Protection
- Logs contain sensitive attack data
- Implement proper access controls
- Regular backup of log data
- Consider encryption for stored logs

### Legal Considerations
- Ensure compliance with local laws
- Document legitimate research purposes
- Implement proper data retention policies
- Consider privacy implications

## Monitoring & Maintenance

### Log Management
- Logs rotate automatically (daily)
- Monitor disk space usage
- Archive old logs as needed

### System Health
```bash
# Check service status
./status_honeypot.sh

# View recent logs
tail -f logs/honeypot.log

# Monitor resource usage
htop
docker stats
```

### Updates
```bash
# Update threat intelligence feeds
# (Automatic every hour by default)

# Update system packages
sudo apt update && sudo apt upgrade

# Update Python dependencies
pip install -r requirements.txt --upgrade
```

## Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check port conflicts
netstat -tlnp | grep -E "(2222|8080|2121|2323)"

# Check Docker status
docker-compose ps
sudo systemctl status docker

# Check service logs
journalctl -u honeypot -f
journalctl -u honeypot-dashboard -f
```

#### Dashboard Not Accessible
```bash
# Check if dashboard is running
curl http://localhost:12000

# Check firewall
sudo ufw status

# Check logs
tail -f logs/honeypot.log
```

#### No Attack Data
```bash
# Generate sample data for testing
python3 scripts/generate_sample_data.py

# Test honeypots
python3 scripts/test_honeypots.py
```

### Performance Tuning

#### High CPU Usage
- Reduce log verbosity
- Increase log rotation frequency
- Limit concurrent connections

#### High Memory Usage
- Adjust Elasticsearch heap size
- Reduce log retention period
- Monitor Docker container resources

#### High Disk Usage
- Implement log compression
- Reduce log retention period
- Monitor log file sizes

## Scaling & Advanced Deployment

### Multi-Server Deployment
- Deploy honeypots on separate servers
- Centralize logging with remote Elasticsearch
- Use load balancer for dashboard access

### Cloud Deployment
- Use container orchestration (Kubernetes)
- Implement auto-scaling
- Use managed Elasticsearch service

### Integration with SIEM
- Forward logs to external SIEM
- Configure custom alert rules
- Implement automated response

## Backup & Recovery

### Data Backup
```bash
# Backup configuration
tar -czf config-backup.tar.gz config/

# Backup logs
tar -czf logs-backup.tar.gz logs/

# Backup Elasticsearch data
docker-compose exec elasticsearch elasticsearch-dump
```

### System Recovery
```bash
# Restore configuration
tar -xzf config-backup.tar.gz

# Restart services
./stop_honeypot.sh
./start_honeypot.sh
```

## Support & Resources

### Log Files
- `logs/honeypot.log` - Main log file
- `logs/ssh_honeypot.log` - SSH-specific logs
- `logs/http_honeypot.log` - HTTP-specific logs
- `logs/ftp_honeypot.log` - FTP-specific logs
- `logs/telnet_honeypot.log` - Telnet-specific logs

### Configuration Files
- `config/honeypot_config.yaml` - Main configuration
- `docker-compose.yml` - ELK stack configuration
- `elk-stack/logstash/pipeline/honeypot.conf` - Log processing

### Useful Commands
```bash
# Real-time log monitoring
tail -f logs/honeypot.log | jq .

# Search for specific IP
grep "192.168.1.100" logs/*.log

# Count attacks by service
grep -h "ssh" logs/*.log | wc -l

# View top attacking IPs
grep -h "source_ip" logs/*.log | sort | uniq -c | sort -nr | head -10
```