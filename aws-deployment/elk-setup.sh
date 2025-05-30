#!/bin/bash

# ELK Stack Setup Script for AWS Free Tier
# Optimized for t2.micro instances

set -e

echo "📊 Setting up ELK Stack for AWS Free Tier..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Create ELK directories
print_status "Creating ELK directories..."
mkdir -p elk-stack/logstash/config
mkdir -p elk-stack/logstash/pipeline
mkdir -p logs

# Create Logstash configuration
print_status "Creating Logstash configuration..."
cat > elk-stack/logstash/config/logstash.yml <<EOF
http.host: "0.0.0.0"
xpack.monitoring.elasticsearch.hosts: [ "http://elasticsearch:9200" ]
pipeline.workers: 1
pipeline.batch.size: 125
pipeline.batch.delay: 50
queue.type: memory
queue.max_bytes: 64mb
EOF

# Create Logstash pipeline configuration
print_status "Creating Logstash pipeline..."
cat > elk-stack/logstash/pipeline/honeypot.conf <<'EOF'
input {
  file {
    path => "/logs/*.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => "json"
  }
  
  beats {
    port => 5044
  }
}

filter {
  if [source_ip] {
    geoip {
      source => "source_ip"
      target => "geoip"
    }
  }
  
  if [timestamp] {
    date {
      match => [ "timestamp", "ISO8601" ]
    }
  }
  
  # Add severity level based on event type
  if [event_type] =~ /(?i)(login_attempt|brute_force|exploit)/ {
    mutate {
      add_field => { "severity" => "HIGH" }
    }
  } else if [event_type] =~ /(?i)(scan|probe)/ {
    mutate {
      add_field => { "severity" => "MEDIUM" }
    }
  } else {
    mutate {
      add_field => { "severity" => "LOW" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "honeypot-%{+YYYY.MM.dd}"
  }
  
  # Debug output (remove in production)
  stdout {
    codec => rubydebug
  }
}
EOF

# Create Elasticsearch index template
print_status "Creating Elasticsearch index template..."
cat > elk-stack/honeypot-template.json <<'EOF'
{
  "index_patterns": ["honeypot-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.refresh_interval": "30s",
      "index.max_result_window": 50000
    },
    "mappings": {
      "properties": {
        "timestamp": {
          "type": "date"
        },
        "source_ip": {
          "type": "ip"
        },
        "source_port": {
          "type": "integer"
        },
        "destination_port": {
          "type": "integer"
        },
        "service": {
          "type": "keyword"
        },
        "event_type": {
          "type": "keyword"
        },
        "severity": {
          "type": "keyword"
        },
        "username": {
          "type": "keyword"
        },
        "password": {
          "type": "keyword"
        },
        "command": {
          "type": "text"
        },
        "user_agent": {
          "type": "text"
        },
        "geoip": {
          "properties": {
            "location": {
              "type": "geo_point"
            },
            "country_name": {
              "type": "keyword"
            },
            "city_name": {
              "type": "keyword"
            },
            "region_name": {
              "type": "keyword"
            }
          }
        }
      }
    }
  }
}
EOF

# Start ELK stack
print_status "Starting ELK stack with free tier optimizations..."
docker-compose -f docker-compose-freetier.yml up -d

# Wait for Elasticsearch to be ready
print_status "Waiting for Elasticsearch to be ready..."
timeout=300
counter=0
while ! curl -s http://localhost:9200/_cluster/health > /dev/null; do
    if [ $counter -ge $timeout ]; then
        print_error "Elasticsearch failed to start within $timeout seconds"
        exit 1
    fi
    sleep 5
    counter=$((counter + 5))
    echo -n "."
done
echo ""

print_status "Elasticsearch is ready!"

# Apply index template
print_status "Applying Elasticsearch index template..."
curl -X PUT "localhost:9200/_index_template/honeypot-template" \
     -H "Content-Type: application/json" \
     -d @elk-stack/honeypot-template.json

# Create initial index
print_status "Creating initial index..."
curl -X PUT "localhost:9200/honeypot-$(date +%Y.%m.%d)" \
     -H "Content-Type: application/json" \
     -d '{
       "settings": {
         "number_of_shards": 1,
         "number_of_replicas": 0
       }
     }'

# Wait for Kibana to be ready
print_status "Waiting for Kibana to be ready..."
timeout=300
counter=0
while ! curl -s http://localhost:5601/api/status > /dev/null; do
    if [ $counter -ge $timeout ]; then
        print_error "Kibana failed to start within $timeout seconds"
        exit 1
    fi
    sleep 5
    counter=$((counter + 5))
    echo -n "."
done
echo ""

print_status "Kibana is ready!"

# Create Kibana index pattern
print_status "Creating Kibana index pattern..."
sleep 10  # Give Kibana more time to fully initialize

curl -X POST "localhost:5601/api/saved_objects/index-pattern/honeypot-*" \
     -H "Content-Type: application/json" \
     -H "kbn-xsrf: true" \
     -d '{
       "attributes": {
         "title": "honeypot-*",
         "timeFieldName": "timestamp"
       }
     }' || print_warning "Index pattern creation failed - you can create it manually in Kibana"

# Create basic Kibana dashboard
print_status "Creating basic Kibana dashboard..."
cat > elk-stack/kibana-dashboard.json <<'EOF'
{
  "version": "8.10.0",
  "objects": [
    {
      "id": "honeypot-dashboard",
      "type": "dashboard",
      "attributes": {
        "title": "Honeypot Security Dashboard",
        "description": "Real-time honeypot attack monitoring",
        "panelsJSON": "[]",
        "timeRestore": false,
        "version": 1
      }
    }
  ]
}
EOF

# Create cleanup script
print_status "Creating cleanup script..."
cat > cleanup_elk.sh <<'EOF'
#!/bin/bash

echo "🧹 Cleaning up ELK data to free space..."

# Remove old indices (keep last 7 days)
curl -X DELETE "localhost:9200/honeypot-$(date -d '7 days ago' +%Y.%m.%d)" 2>/dev/null || true

# Clean Docker logs
docker system prune -f

# Restart containers to free memory
docker-compose -f docker-compose-freetier.yml restart

echo "✅ Cleanup completed"
EOF

chmod +x cleanup_elk.sh

# Add cleanup to crontab
print_status "Setting up automatic cleanup..."
(crontab -l 2>/dev/null; echo "0 2 * * * cd ~/cybersecurity-honeypot-system/aws-deployment && ./cleanup_elk.sh >> ~/cleanup.log 2>&1") | crontab -

# Create monitoring script
print_status "Creating ELK monitoring script..."
cat > monitor_elk.sh <<'EOF'
#!/bin/bash

echo "📊 ELK Stack Status"
echo "=================="

echo "🔍 Elasticsearch Health:"
curl -s http://localhost:9200/_cluster/health?pretty

echo ""
echo "📈 Elasticsearch Indices:"
curl -s http://localhost:9200/_cat/indices?v

echo ""
echo "🐳 Docker Container Status:"
docker-compose -f docker-compose-freetier.yml ps

echo ""
echo "💾 Disk Usage:"
df -h

echo ""
echo "🧠 Memory Usage:"
free -h

echo ""
echo "📊 Recent Logs (last 5 entries):"
docker-compose -f docker-compose-freetier.yml logs --tail=5
EOF

chmod +x monitor_elk.sh

print_status "✅ ELK Stack setup completed!"
print_status "📊 Access URLs:"
echo "• Kibana: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR_PUBLIC_IP'):5601"
echo "• Elasticsearch: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR_PUBLIC_IP'):9200"

print_warning "⚠️  Important notes:"
echo "1. ELK stack is optimized for 1GB RAM (uses ~650MB total)"
echo "2. Automatic cleanup runs daily at 2 AM"
echo "3. Only 1 shard and 0 replicas for minimal resource usage"
echo "4. Monitor memory usage regularly with: ./monitor_elk.sh"
echo "5. Manual cleanup available with: ./cleanup_elk.sh"

print_status "🔧 Next steps:"
echo "1. Configure your honeypot to send logs to Logstash (port 5044)"
echo "2. Access Kibana and create visualizations"
echo "3. Set up index patterns if not created automatically"
echo "4. Monitor system resources regularly"