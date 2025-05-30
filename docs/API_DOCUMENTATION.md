# API Documentation

## Dashboard API Endpoints

The honeypot dashboard provides a RESTful API for accessing attack data and system statistics.

### Base URL
```
http://localhost:12000/api
```

## Endpoints

### GET /api/stats
Get overall system statistics.

**Response:**
```json
{
  "attack_stats": {
    "total_unique_ips": 150,
    "total_attack_attempts": 1250,
    "services_targeted": {
      "ssh": 45,
      "http": 60,
      "ftp": 25,
      "telnet": 20
    },
    "top_attackers": [...]
  },
  "threat_intel_stats": {
    "malicious_ips_count": 50000,
    "feeds_configured": 2,
    "geodb_available": true,
    "last_update": "2025-01-15T10:30:00Z"
  },
  "recent_attacks_count": 100,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### GET /api/recent_attacks
Get recent attack data.

**Parameters:**
- `limit` (optional): Number of attacks to return (default: 50)

**Response:**
```json
{
  "attacks": [
    {
      "source_ip": "192.168.1.100",
      "timestamp": "2025-01-15T10:25:00Z",
      "service": "ssh",
      "event_type": "login_attempt",
      "ip_intelligence": {
        "ip": "192.168.1.100",
        "is_malicious": false,
        "geolocation": {
          "country": "United States",
          "country_code": "US",
          "city": "New York",
          "latitude": 40.7128,
          "longitude": -74.0060
        },
        "risk_score": 25,
        "risk_level": "LOW"
      },
      "attack_pattern": ["brute_force"],
      "severity": "MEDIUM"
    }
  ],
  "total": 100
}
```

### GET /api/top_attackers
Get top attacking IP addresses.

**Response:**
```json
{
  "top_attackers": [
    {
      "ip": "192.168.1.100",
      "attempts": 45,
      "services": ["ssh", "http"],
      "first_seen": "2025-01-15T08:00:00Z",
      "last_seen": "2025-01-15T10:25:00Z"
    }
  ]
}
```

### GET /api/geolocation/{ip}
Get geolocation and threat intelligence for a specific IP.

**Parameters:**
- `ip`: IP address to analyze

**Response:**
```json
{
  "ip": "192.168.1.100",
  "geolocation": {
    "country": "United States",
    "country_code": "US",
    "city": "New York",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timezone": "America/New_York",
    "isp": "Example ISP"
  },
  "analysis": {
    "ip": "192.168.1.100",
    "timestamp": "2025-01-15T10:30:00Z",
    "is_malicious": false,
    "risk_score": 25,
    "risk_level": "LOW"
  }
}
```

### GET /api/attack_map
Get attack data for world map visualization.

**Response:**
```json
{
  "locations": [
    {
      "ip": "192.168.1.100",
      "lat": 40.7128,
      "lng": -74.0060,
      "country": "United States",
      "city": "New York",
      "service": "ssh",
      "severity": "MEDIUM",
      "timestamp": "2025-01-15T10:25:00Z"
    }
  ]
}
```

### GET /api/service_stats
Get statistics broken down by service.

**Response:**
```json
{
  "service_stats": {
    "ssh": {
      "total_attacks": 450,
      "unique_ips": 45,
      "severity_counts": {
        "CRITICAL": 5,
        "HIGH": 15,
        "MEDIUM": 25,
        "LOW": 5,
        "INFO": 0
      }
    },
    "http": {
      "total_attacks": 600,
      "unique_ips": 60,
      "severity_counts": {
        "CRITICAL": 10,
        "HIGH": 20,
        "MEDIUM": 30,
        "LOW": 0,
        "INFO": 0
      }
    }
  }
}
```

### GET /api/timeline
Get attack timeline data for charts.

**Response:**
```json
{
  "timeline": [
    {
      "timestamp": "2025-01-15T08",
      "total_attacks": 25,
      "services": {
        "ssh": 10,
        "http": 15
      },
      "severity_counts": {
        "CRITICAL": 2,
        "HIGH": 8,
        "MEDIUM": 15,
        "LOW": 0,
        "INFO": 0
      }
    }
  ]
}
```

## WebSocket Events

The dashboard uses WebSocket connections for real-time updates.

### Connection
```javascript
const socket = io('http://localhost:12000');
```

### Events

#### connect
Fired when client connects to the server.

```javascript
socket.on('connect', () => {
  console.log('Connected to dashboard');
});
```

#### attack_update
Fired when new attack data is available (every 5 seconds).

```javascript
socket.on('attack_update', (data) => {
  console.log('New attack data:', data);
  // data.recent_attacks - Array of recent attacks
  // data.stats - Updated statistics
});
```

#### disconnect
Fired when client disconnects from the server.

```javascript
socket.on('disconnect', () => {
  console.log('Disconnected from dashboard');
});
```

## Data Models

### Attack Object
```json
{
  "source_ip": "string",
  "timestamp": "ISO8601 string",
  "service": "ssh|http|ftp|telnet",
  "event_type": "string",
  "ip_intelligence": {
    "ip": "string",
    "is_malicious": "boolean",
    "geolocation": "object|null",
    "risk_score": "number",
    "risk_level": "MINIMAL|LOW|MEDIUM|HIGH"
  },
  "attack_pattern": ["string"],
  "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL"
}
```

### Geolocation Object
```json
{
  "country": "string",
  "country_code": "string",
  "city": "string",
  "latitude": "number",
  "longitude": "number",
  "timezone": "string",
  "isp": "string"
}
```

### Service Statistics Object
```json
{
  "total_attacks": "number",
  "unique_ips": "number",
  "severity_counts": {
    "CRITICAL": "number",
    "HIGH": "number",
    "MEDIUM": "number",
    "LOW": "number",
    "INFO": "number"
  }
}
```

## Error Handling

### HTTP Status Codes
- `200 OK` - Request successful
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Endpoint or resource not found
- `500 Internal Server Error` - Server error

### Error Response Format
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "ISO8601 string"
}
```

## Rate Limiting

The API implements basic rate limiting:
- 100 requests per minute per IP
- WebSocket connections limited to 10 per IP

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing:
- API key authentication
- JWT tokens
- IP whitelisting
- HTTPS encryption

## Example Usage

### Python
```python
import requests

# Get recent attacks
response = requests.get('http://localhost:12000/api/recent_attacks?limit=10')
attacks = response.json()['attacks']

for attack in attacks:
    print(f"Attack from {attack['source_ip']} on {attack['service']}")
```

### JavaScript
```javascript
// Fetch attack statistics
fetch('/api/stats')
  .then(response => response.json())
  .then(data => {
    console.log('Total attacks:', data.attack_stats.total_attack_attempts);
  });

// Real-time updates with WebSocket
const socket = io();
socket.on('attack_update', (data) => {
  updateDashboard(data.recent_attacks, data.stats);
});
```

### curl
```bash
# Get system statistics
curl http://localhost:12000/api/stats

# Get recent attacks
curl "http://localhost:12000/api/recent_attacks?limit=5"

# Get geolocation for specific IP
curl http://localhost:12000/api/geolocation/192.168.1.100
```

## Integration Examples

### SIEM Integration
```python
import requests
import time

def forward_to_siem():
    while True:
        response = requests.get('http://localhost:12000/api/recent_attacks?limit=100')
        attacks = response.json()['attacks']
        
        for attack in attacks:
            # Forward to SIEM system
            send_to_siem(attack)
        
        time.sleep(60)  # Check every minute
```

### Alerting Integration
```python
import requests

def check_high_severity_attacks():
    response = requests.get('http://localhost:12000/api/recent_attacks?limit=50')
    attacks = response.json()['attacks']
    
    critical_attacks = [a for a in attacks if a['severity'] == 'CRITICAL']
    
    if critical_attacks:
        send_alert(f"Found {len(critical_attacks)} critical attacks")
```