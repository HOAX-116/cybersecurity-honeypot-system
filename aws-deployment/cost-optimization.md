# AWS Free Tier Cost Optimization Guide

This guide helps you maximize your AWS Free Tier usage and minimize costs while running the honeypot system.

## 💰 Free Tier Limits (12 months)

### EC2 Instances
- **750 hours/month** of t2.micro instances
- **30GB EBS storage** per instance
- **2 million I/O operations** per month

### Data Transfer
- **15GB data transfer out** per month
- **1GB data transfer in** per month (free)

### Other Services
- **5GB S3 storage** (if used for backups)
- **25GB DynamoDB storage** (if used)

## 📊 Resource Usage Estimation

### Two t2.micro Instances (24/7)
- **Total hours**: 2 × 24 × 30 = 1,440 hours/month
- **Free tier**: 750 hours/month
- **Overage**: 690 hours/month (~$6.90/month)

### Storage Usage
- **ELK instance**: ~15GB (logs, indices, system)
- **Honeypot instance**: ~10GB (logs, system, code)
- **Total**: 25GB (within 30GB limit per instance)

### Data Transfer
- **Honeypot traffic**: ~2-5GB/month (depends on attacks)
- **ELK communication**: ~1-2GB/month
- **Management**: ~1GB/month
- **Total**: 4-8GB/month (within 15GB limit)

## 🎯 Cost Optimization Strategies

### 1. Instance Management

#### Stop Instances When Not Needed
```bash
# Stop instances (saves compute costs)
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Start instances when needed
aws ec2 start-instances --instance-ids i-1234567890abcdef0
```

#### Use Spot Instances (Advanced)
- **Savings**: Up to 90% off on-demand pricing
- **Risk**: Instances can be terminated
- **Best for**: Non-critical testing environments

#### Schedule Instance Start/Stop
```bash
# Add to crontab for automatic shutdown at night
0 22 * * * aws ec2 stop-instances --instance-ids i-1234567890abcdef0
0 8 * * 1-5 aws ec2 start-instances --instance-ids i-1234567890abcdef0
```

### 2. Storage Optimization

#### EBS Volume Optimization
```bash
# Monitor disk usage
df -h

# Clean up unnecessary files
sudo apt autoremove
sudo apt autoclean
docker system prune -f
```

#### Log Management
```bash
# Aggressive log rotation (daily instead of weekly)
sudo tee /etc/logrotate.d/honeypot-aggressive > /dev/null <<EOF
/home/ubuntu/cybersecurity-honeypot-system/logs/*.log {
    daily
    missingok
    rotate 3
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
}
EOF
```

#### Elasticsearch Index Management
```bash
# Delete indices older than 3 days (instead of 7)
curl -X DELETE "localhost:9200/honeypot-$(date -d '3 days ago' +%Y.%m.%d)"

# Reduce index size by disabling source storage
curl -X PUT "localhost:9200/_template/honeypot-minimal" -H "Content-Type: application/json" -d '{
  "index_patterns": ["honeypot-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.refresh_interval": "60s"
  },
  "mappings": {
    "_source": {
      "enabled": false
    }
  }
}'
```

### 3. Network Optimization

#### Minimize Data Transfer
```bash
# Compress logs before sending to ELK
# Edit logstash configuration
cat >> elk-stack/logstash/pipeline/honeypot.conf <<EOF
filter {
  # Reduce log verbosity
  if [message] =~ /DEBUG/ {
    drop { }
  }
}
EOF
```

#### Use CloudFront (Free Tier)
- **50GB data transfer out** per month (free)
- Cache static dashboard content
- Reduce direct EC2 data transfer

### 4. Monitoring and Alerts

#### Set Up Billing Alerts
```bash
# AWS CLI command to create billing alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "BillingAlarm" \
  --alarm-description "Billing alarm" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 5.0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --evaluation-periods 1
```

#### Monitor Resource Usage
```bash
# Create monitoring script
cat > monitor_costs.sh <<'EOF'
#!/bin/bash

echo "💰 AWS Cost Monitoring Report"
echo "============================="
echo "Date: $(date)"
echo ""

echo "🖥️  Instance Uptime:"
uptime

echo ""
echo "💾 Storage Usage:"
df -h | grep -E "(/$|/var)"

echo ""
echo "🌐 Network Usage (approximate):"
# Monitor network interfaces
cat /proc/net/dev | grep -E "(eth0|ens)"

echo ""
echo "📊 ELK Resource Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "⚠️  Recommendations:"
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "- Disk usage is high ($DISK_USAGE%), consider cleanup"
fi

MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ $MEMORY_USAGE -gt 85 ]; then
    echo "- Memory usage is high ($MEMORY_USAGE%), consider optimization"
fi

UPTIME_HOURS=$(awk '{print int($1/3600)}' /proc/uptime)
if [ $UPTIME_HOURS -gt 720 ]; then  # 30 days
    echo "- Instance has been running for $UPTIME_HOURS hours, consider stopping if not needed"
fi
EOF

chmod +x monitor_costs.sh
```

## 📅 Monthly Cost Management Routine

### Week 1: Setup and Monitoring
- Deploy honeypot system
- Set up billing alerts
- Monitor initial resource usage

### Week 2: Optimization
- Review logs and optimize retention
- Adjust ELK memory settings if needed
- Clean up unnecessary data

### Week 3: Analysis
- Analyze attack patterns
- Determine if all honeypots are needed
- Optimize based on actual usage

### Week 4: Planning
- Review AWS billing dashboard
- Plan for next month
- Consider stopping instances if limits approached

## 🔄 Automated Cost Optimization

### Daily Cleanup Script
```bash
cat > daily_cleanup.sh <<'EOF'
#!/bin/bash

# Clean Docker
docker system prune -f

# Clean logs older than 3 days
find logs/ -name "*.log" -mtime +3 -delete

# Clean old ELK indices
curl -X DELETE "localhost:9200/honeypot-$(date -d '3 days ago' +%Y.%m.%d)" 2>/dev/null

# Clean system logs
sudo journalctl --vacuum-time=3d

echo "$(date): Daily cleanup completed" >> cleanup.log
EOF

chmod +x daily_cleanup.sh

# Add to crontab
(crontab -l; echo "0 3 * * * cd $(pwd) && ./daily_cleanup.sh") | crontab -
```

### Weekly Resource Report
```bash
cat > weekly_report.sh <<'EOF'
#!/bin/bash

echo "📊 Weekly Resource Report - $(date)"
echo "=================================="

echo ""
echo "💰 Estimated Costs This Month:"
echo "Instance hours: $(awk '{print int($1/3600)}' /proc/uptime) hours"
echo "Storage usage: $(df -h / | tail -1 | awk '{print $3}')"

echo ""
echo "📈 Top Resource Consumers:"
echo "Largest log files:"
ls -lhS logs/ | head -5

echo ""
echo "🔍 Attack Summary:"
if [ -f logs/honeypot.log ]; then
    echo "Total attacks this week: $(grep -c "$(date -d '7 days ago' +%Y-%m-%d)" logs/honeypot.log)"
    echo "Unique IPs: $(grep "$(date -d '7 days ago' +%Y-%m-%d)" logs/honeypot.log | jq -r '.source_ip' | sort -u | wc -l)"
fi

echo ""
echo "⚠️  Recommendations:"
# Add specific recommendations based on usage
EOF

chmod +x weekly_report.sh

# Run weekly on Sundays
(crontab -l; echo "0 9 * * 0 cd $(pwd) && ./weekly_report.sh | mail -s 'Honeypot Weekly Report' your-email@example.com") | crontab -
```

## 🎯 Advanced Cost Optimization

### 1. Use Reserved Instances (After Free Tier)
- **Savings**: Up to 75% for 1-3 year commitments
- **Best for**: Continuous operation

### 2. Implement Auto-Scaling
```bash
# Create launch template for auto-scaling
aws ec2 create-launch-template \
  --launch-template-name honeypot-template \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "t2.micro",
    "SecurityGroupIds": ["sg-12345678"],
    "UserData": "base64-encoded-startup-script"
  }'
```

### 3. Use S3 for Long-term Log Storage
```bash
# Archive old logs to S3 (5GB free)
aws s3 cp logs/archive/ s3://your-honeypot-logs/ --recursive

# Set up lifecycle policy for automatic archival
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-honeypot-logs \
  --lifecycle-configuration file://lifecycle.json
```

### 4. Optimize ELK Stack Further
```yaml
# Ultra-minimal ELK configuration
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms128m -Xmx128m"  # Even smaller heap
      - xpack.security.enabled=false
      - xpack.monitoring.enabled=false
      - xpack.ml.enabled=false
    deploy:
      resources:
        limits:
          memory: 200M
```

## 📊 Cost Tracking Dashboard

### Create Simple Cost Tracking
```bash
cat > cost_tracker.py <<'EOF'
#!/usr/bin/env python3

import json
import subprocess
from datetime import datetime

def get_instance_hours():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.read().split()[0])
    return uptime_seconds / 3600

def get_storage_usage():
    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    usage_line = lines[1].split()
    return {
        'total': usage_line[1],
        'used': usage_line[2],
        'available': usage_line[3],
        'percentage': usage_line[4]
    }

def estimate_monthly_cost():
    hours = get_instance_hours()
    # Assuming 2 instances
    total_hours = hours * 2
    free_tier_hours = 750
    
    if total_hours > free_tier_hours:
        overage_hours = total_hours - free_tier_hours
        overage_cost = overage_hours * 0.0116  # t2.micro hourly rate
    else:
        overage_cost = 0
    
    return {
        'total_hours': total_hours,
        'free_tier_hours': free_tier_hours,
        'overage_hours': max(0, total_hours - free_tier_hours),
        'estimated_overage_cost': overage_cost
    }

if __name__ == "__main__":
    report = {
        'timestamp': datetime.now().isoformat(),
        'instance_hours': get_instance_hours(),
        'storage': get_storage_usage(),
        'cost_estimate': estimate_monthly_cost()
    }
    
    print(json.dumps(report, indent=2))
EOF

chmod +x cost_tracker.py
```

## 🚨 Emergency Cost Control

### If Approaching Limits
1. **Stop non-essential services**:
   ```bash
   # Stop ELK stack temporarily
   docker-compose -f docker-compose-freetier.yml stop
   
   # Keep only SSH honeypot running
   ./stop_honeypots.sh
   python3 honeypots/ssh_honeypot.py &
   ```

2. **Aggressive cleanup**:
   ```bash
   # Remove all logs
   rm -rf logs/*
   
   # Clean all Docker data
   docker system prune -af
   
   # Clean system caches
   sudo apt clean
   sudo journalctl --vacuum-size=100M
   ```

3. **Stop instances**:
   ```bash
   # Stop instances via AWS CLI
   aws ec2 stop-instances --instance-ids i-1234567890abcdef0
   ```

## 📈 Beyond Free Tier Planning

### When to Upgrade
- Consistent monthly overage costs
- Need for higher availability
- Requirement for more storage/compute
- Production deployment needs

### Upgrade Path
1. **t3.small instances** (~$15/month each)
2. **Larger EBS volumes** (~$0.10/GB/month)
3. **Load balancer** (~$18/month)
4. **RDS for logs** (~$15/month for db.t3.micro)

### Cost-Effective Alternatives
- **AWS Lightsail**: Fixed pricing, simpler management
- **DigitalOcean**: Competitive pricing for small instances
- **Linode**: Good performance/price ratio
- **Vultr**: Hourly billing, good for testing

---

Remember: The goal is to learn and experiment within the free tier limits. Monitor your usage regularly and optimize based on your actual needs!