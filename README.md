# Multi-Service Cybersecurity Honeypot System

A sophisticated honeypot infrastructure designed to capture and analyze attacker behavior patterns across multiple services including SSH, HTTP, FTP, and Telnet.

## Features

- **Multi-Service Honeypots**: SSH, HTTP, FTP, and Telnet services simulation
- **Real-time Threat Intelligence Dashboard**: ELK Stack integration for attack visualization
- **Automated Threat Categorization**: AI-powered attack pattern analysis
- **Geolocation-based Attack Tracking**: Real-time geographical attack mapping
- **Alerting Mechanisms**: Immediate threat response notifications
- **Comprehensive Logging**: Detailed attack logs and forensic data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Honeypots     │    │   ELK Stack     │    │   Dashboard     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ SSH (2222)  │ │───▶│ │Elasticsearch│ │───▶│ │   Kibana    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ │ (5601)      │ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ └─────────────┘ │
│ │HTTP (8080)  │ │───▶│ │  Logstash   │ │    │ ┌─────────────┐ │
│ └─────────────┘ │    │ └─────────────┘ │    │ │   Flask     │ │
│ ┌─────────────┐ │    │                 │    │ │ Dashboard   │ │
│ │ FTP (2121)  │ │    │                 │    │ │ (12000)     │ │
│ └─────────────┘ │    │                 │    │ └─────────────┘ │
│ ┌─────────────┐ │    │                 │    │                 │
│ │Telnet(2323) │ │    │                 │    │                 │
│ └─────────────┘ │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

1. **Install Dependencies**:
   ```bash
   ./scripts/install_dependencies.sh
   ```

2. **Start ELK Stack**:
   ```bash
   docker-compose up -d elasticsearch logstash kibana
   ```

3. **Start Honeypots**:
   ```bash
   python3 honeypots/start_all.py
   ```

4. **Access Dashboard**:
   - Kibana: http://localhost:5601
   - Custom Dashboard: http://localhost:12000

## Configuration

Edit `config/honeypot_config.yaml` to customize:
- Service ports
- Logging levels
- Alert thresholds
- Geolocation settings

## Security Considerations

- All honeypots run in isolated containers
- No real credentials are exposed
- All interactions are logged and monitored
- Automated threat response mechanisms

## License

MIT License - See LICENSE file for details