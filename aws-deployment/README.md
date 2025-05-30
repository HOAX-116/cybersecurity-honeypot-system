# AWS Free Tier Deployment Files

This directory contains optimized deployment scripts and configurations for running the cybersecurity honeypot system on AWS Free Tier.

## 📁 Files Overview

### Core Deployment Scripts
- **`honeypot-setup.sh`** - Initial system setup for honeypot instance
- **`elk-setup.sh`** - ELK stack deployment for monitoring instance  
- **`deploy-honeypot.sh`** - Complete honeypot services deployment

### Configuration Files
- **`docker-compose-freetier.yml`** - Memory-optimized ELK stack configuration
- **`honeypot-config-aws.yaml`** - AWS-optimized honeypot configuration

### Documentation
- **`AWS_FREE_TIER_DEPLOYMENT_GUIDE.md`** - Complete step-by-step deployment guide

## 🚀 Quick Start

### 1. ELK Stack Instance
```bash
# SSH to your ELK instance
ssh -i honeypot-key.pem ubuntu@YOUR_ELK_IP

# Clone repository
git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
cd cybersecurity-honeypot-system/aws-deployment

# Run setup
chmod +x *.sh
./elk-setup.sh
```

### 2. Honeypot Services Instance
```bash
# SSH to your honeypot instance  
ssh -i honeypot-key.pem ubuntu@YOUR_HONEYPOT_IP

# Clone repository
git clone https://github.com/HOAX-116/cybersecurity-honeypot-system.git
cd cybersecurity-honeypot-system/aws-deployment

# Run setup
chmod +x *.sh
./honeypot-setup.sh
sudo reboot

# After reboot, deploy honeypots
./deploy-honeypot.sh
./start_honeypots.sh
```

## 🔧 Key Optimizations for Free Tier

### Memory Usage
- **Elasticsearch**: 256MB heap (vs 512MB default)
- **Logstash**: 128MB heap (vs 256MB default)  
- **Kibana**: 256MB max memory
- **Total ELK**: ~650MB (fits in 1GB with room for OS)

### Storage Management
- **Log rotation**: 5MB max per file
- **Automatic cleanup**: 7-day retention
- **Single shard**: No replicas to save space

### Performance Tuning
- **Reduced workers**: Single worker processes
- **Batch processing**: Optimized for low memory
- **Connection limits**: Prevents resource exhaustion

## 📊 Monitoring

### Resource Monitoring
```bash
# Check system status
./check_status.sh

# Monitor ELK stack
./monitor_elk.sh

# View memory usage
free -h
```

### Log Management
```bash
# Rotate logs manually
./rotate_logs.sh

# Cleanup ELK data
./cleanup_elk.sh

# View recent attacks
tail -f logs/honeypot.log
```

## 🔒 Security Features

### Automatic Protection
- **fail2ban**: Blocks brute force attempts
- **UFW firewall**: Configured with minimal required ports
- **Log monitoring**: Automatic restart on service failure

### Manual Security
- **SSH key authentication**: No password login
- **Security groups**: Network-level access control
- **Regular updates**: Automated system updates

## ⚠️ Important Notes

### Free Tier Limits
- **750 hours/month** per instance type
- **30GB storage** per instance
- **15GB data transfer** per month

### Cost Monitoring
- Monitor AWS billing dashboard
- Set up billing alerts
- Stop instances when not needed

### Maintenance
- **Daily**: Check system status
- **Weekly**: Review logs and clean up
- **Monthly**: Update system packages

## 🆘 Troubleshooting

### Common Issues
1. **High memory usage**: Restart services, check for memory leaks
2. **Disk space full**: Run cleanup scripts, rotate logs
3. **Services not starting**: Check logs, verify configuration
4. **Network issues**: Verify security groups, test connectivity

### Getting Help
1. Check the deployment guide for detailed instructions
2. Review log files for error messages
3. Test network connectivity between instances
4. Verify AWS security group configurations

## 📈 Scaling Beyond Free Tier

When ready to scale beyond free tier:
1. **Upgrade to t3.small** for better performance
2. **Add more storage** for longer log retention
3. **Enable replicas** for high availability
4. **Add load balancing** for multiple honeypot instances

---

For complete deployment instructions, see `AWS_FREE_TIER_DEPLOYMENT_GUIDE.md`