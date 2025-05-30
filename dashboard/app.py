#!/usr/bin/env python3

import os
import sys
import json
import yaml
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from honeypots.threat_intelligence import ThreatIntelligence, AttackAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables
config = None
threat_intel = None
attack_analyzer = None
recent_attacks = []
attack_stats = {}

def load_config():
    """Load configuration"""
    global config
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'honeypot_config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

def init_threat_intelligence():
    """Initialize threat intelligence"""
    global threat_intel, attack_analyzer
    threat_intel = ThreatIntelligence(config)
    attack_analyzer = AttackAnalyzer(threat_intel)
    threat_intel.start_auto_update()

def read_log_files():
    """Read and parse log files"""
    global recent_attacks, attack_stats
    
    log_files = [
        'logs/ssh_honeypot.log',
        'logs/http_honeypot.log',
        'logs/ftp_honeypot.log',
        'logs/telnet_honeypot.log'
    ]
    
    all_attacks = []
    
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                log_entry = json.loads(line)
                                analysis = attack_analyzer.analyze_attack(log_entry)
                                if analysis:
                                    all_attacks.append(analysis)
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logging.error(f"Error reading {log_file}: {e}")
    
    # Sort by timestamp and keep recent attacks
    all_attacks.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_attacks = all_attacks[:100]  # Keep last 100 attacks
    
    # Update statistics
    attack_stats = attack_analyzer.get_attack_statistics()

def log_monitor_thread():
    """Background thread to monitor logs"""
    while True:
        try:
            read_log_files()
            # Emit real-time updates to connected clients
            socketio.emit('attack_update', {
                'recent_attacks': recent_attacks[:10],
                'stats': attack_stats
            })
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logging.error(f"Error in log monitor: {e}")
            time.sleep(10)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    """Get attack statistics"""
    return jsonify({
        'attack_stats': attack_stats,
        'threat_intel_stats': threat_intel.get_stats() if threat_intel else {},
        'recent_attacks_count': len(recent_attacks),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/recent_attacks')
def get_recent_attacks():
    """Get recent attacks"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        'attacks': recent_attacks[:limit],
        'total': len(recent_attacks)
    })

@app.route('/api/top_attackers')
def get_top_attackers():
    """Get top attacking IPs"""
    return jsonify({
        'top_attackers': attack_analyzer.get_top_attackers() if attack_analyzer else []
    })

@app.route('/api/geolocation/<ip>')
def get_ip_geolocation(ip):
    """Get geolocation for specific IP"""
    if threat_intel:
        geo_data = threat_intel.get_geolocation(ip)
        analysis = threat_intel.analyze_ip(ip)
        return jsonify({
            'ip': ip,
            'geolocation': geo_data,
            'analysis': analysis
        })
    return jsonify({'error': 'Threat intelligence not available'})

@app.route('/api/attack_map')
def get_attack_map():
    """Get attack data for world map visualization"""
    attack_locations = []
    
    for attack in recent_attacks[:100]:  # Last 100 attacks
        ip_intel = attack.get('ip_intelligence', {})
        geo = ip_intel.get('geolocation')
        
        if geo and geo.get('latitude') and geo.get('longitude'):
            attack_locations.append({
                'ip': attack['source_ip'],
                'lat': geo['latitude'],
                'lng': geo['longitude'],
                'country': geo.get('country', 'Unknown'),
                'city': geo.get('city', 'Unknown'),
                'service': attack['service'],
                'severity': attack['severity'],
                'timestamp': attack['timestamp']
            })
    
    return jsonify({'locations': attack_locations})

@app.route('/api/service_stats')
def get_service_stats():
    """Get statistics by service"""
    service_stats = {}
    
    for attack in recent_attacks:
        service = attack['service']
        if service not in service_stats:
            service_stats[service] = {
                'total_attacks': 0,
                'unique_ips': set(),
                'severity_counts': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
            }
        
        service_stats[service]['total_attacks'] += 1
        service_stats[service]['unique_ips'].add(attack['source_ip'])
        severity = attack.get('severity', 'INFO')
        service_stats[service]['severity_counts'][severity] += 1
    
    # Convert sets to counts
    for service in service_stats:
        service_stats[service]['unique_ips'] = len(service_stats[service]['unique_ips'])
    
    return jsonify({'service_stats': service_stats})

@app.route('/api/timeline')
def get_attack_timeline():
    """Get attack timeline data"""
    timeline_data = {}
    
    for attack in recent_attacks:
        timestamp = attack['timestamp']
        # Group by hour
        hour_key = timestamp[:13]  # YYYY-MM-DDTHH
        
        if hour_key not in timeline_data:
            timeline_data[hour_key] = {
                'timestamp': hour_key,
                'total_attacks': 0,
                'services': {},
                'severity_counts': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
            }
        
        timeline_data[hour_key]['total_attacks'] += 1
        
        service = attack['service']
        if service not in timeline_data[hour_key]['services']:
            timeline_data[hour_key]['services'][service] = 0
        timeline_data[hour_key]['services'][service] += 1
        
        severity = attack.get('severity', 'INFO')
        timeline_data[hour_key]['severity_counts'][severity] += 1
    
    # Convert to list and sort
    timeline_list = list(timeline_data.values())
    timeline_list.sort(key=lambda x: x['timestamp'])
    
    return jsonify({'timeline': timeline_list})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'status': 'Connected to honeypot dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    pass

def create_templates():
    """Create HTML templates"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cybersecurity Honeypot Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0a; color: #fff; }
        .header { background: linear-gradient(135deg, #1e3c72, #2a5298); padding: 20px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: linear-gradient(135deg, #1a1a1a, #2d2d2d); padding: 20px; border-radius: 10px; border: 1px solid #333; }
        .stat-card h3 { color: #4CAF50; margin-bottom: 10px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #fff; }
        .stat-label { color: #ccc; font-size: 0.9em; }
        .charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .chart-container { background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; }
        .map-container { background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 30px; }
        #map { height: 400px; border-radius: 5px; }
        .attacks-table { background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; }
        .table-container { max-height: 400px; overflow-y: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #2d2d2d; color: #4CAF50; }
        .severity-critical { color: #f44336; }
        .severity-high { color: #ff9800; }
        .severity-medium { color: #ffeb3b; }
        .severity-low { color: #4caf50; }
        .severity-info { color: #2196f3; }
        .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
        .status-online { background: #4CAF50; }
        .status-offline { background: #f44336; }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Cybersecurity Honeypot Dashboard</h1>
        <p>Real-time Threat Intelligence & Attack Monitoring</p>
    </div>

    <div class="container">
        <div class="stats-grid" id="statsGrid">
            <!-- Stats will be populated by JavaScript -->
        </div>

        <div class="map-container">
            <h3>🌍 Global Attack Map</h3>
            <div id="map"></div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h3>📊 Attacks by Service</h3>
                <canvas id="serviceChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>📈 Attack Timeline</h3>
                <canvas id="timelineChart"></canvas>
            </div>
        </div>

        <div class="attacks-table">
            <h3>🚨 Recent Attacks</h3>
            <div class="table-container">
                <table id="attacksTable">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Source IP</th>
                            <th>Service</th>
                            <th>Event</th>
                            <th>Severity</th>
                            <th>Country</th>
                        </tr>
                    </thead>
                    <tbody id="attacksTableBody">
                        <!-- Attacks will be populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Initialize Socket.IO
        const socket = io();
        
        // Initialize map
        const map = L.map('map').setView([20, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Chart instances
        let serviceChart, timelineChart;

        // Initialize dashboard
        function initDashboard() {
            loadStats();
            loadRecentAttacks();
            loadAttackMap();
            loadCharts();
        }

        // Load statistics
        function loadStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    const statsGrid = document.getElementById('statsGrid');
                    const stats = data.attack_stats;
                    
                    statsGrid.innerHTML = `
                        <div class="stat-card">
                            <h3>Total Unique IPs</h3>
                            <div class="stat-value">${stats.total_unique_ips || 0}</div>
                            <div class="stat-label">Attacking sources</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Attempts</h3>
                            <div class="stat-value">${stats.total_attack_attempts || 0}</div>
                            <div class="stat-label">Attack attempts</div>
                        </div>
                        <div class="stat-card">
                            <h3>Services Targeted</h3>
                            <div class="stat-value">${Object.keys(stats.services_targeted || {}).length}</div>
                            <div class="stat-label">Different services</div>
                        </div>
                        <div class="stat-card">
                            <h3>Threat Intel IPs</h3>
                            <div class="stat-value">${data.threat_intel_stats.malicious_ips_count || 0}</div>
                            <div class="stat-label">Known malicious IPs</div>
                        </div>
                    `;
                });
        }

        // Load recent attacks
        function loadRecentAttacks() {
            fetch('/api/recent_attacks?limit=20')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('attacksTableBody');
                    tbody.innerHTML = data.attacks.map(attack => {
                        const time = new Date(attack.timestamp).toLocaleString();
                        const geo = attack.ip_intelligence?.geolocation;
                        const country = geo?.country || 'Unknown';
                        
                        return `
                            <tr>
                                <td>${time}</td>
                                <td>${attack.source_ip}</td>
                                <td>${attack.service.toUpperCase()}</td>
                                <td>${attack.event_type}</td>
                                <td><span class="severity-${attack.severity.toLowerCase()}">${attack.severity}</span></td>
                                <td>${country}</td>
                            </tr>
                        `;
                    }).join('');
                });
        }

        // Load attack map
        function loadAttackMap() {
            fetch('/api/attack_map')
                .then(response => response.json())
                .then(data => {
                    // Clear existing markers
                    map.eachLayer(layer => {
                        if (layer instanceof L.Marker) {
                            map.removeLayer(layer);
                        }
                    });

                    // Add markers for attacks
                    data.locations.forEach(location => {
                        const marker = L.marker([location.lat, location.lng]).addTo(map);
                        marker.bindPopup(`
                            <b>${location.ip}</b><br>
                            ${location.city}, ${location.country}<br>
                            Service: ${location.service.toUpperCase()}<br>
                            Severity: ${location.severity}<br>
                            Time: ${new Date(location.timestamp).toLocaleString()}
                        `);
                    });
                });
        }

        // Load charts
        function loadCharts() {
            // Service chart
            fetch('/api/service_stats')
                .then(response => response.json())
                .then(data => {
                    const ctx = document.getElementById('serviceChart').getContext('2d');
                    const services = Object.keys(data.service_stats);
                    const attacks = services.map(s => data.service_stats[s].total_attacks);

                    if (serviceChart) serviceChart.destroy();
                    serviceChart = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: services.map(s => s.toUpperCase()),
                            datasets: [{
                                data: attacks,
                                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { labels: { color: '#fff' } }
                            }
                        }
                    });
                });

            // Timeline chart
            fetch('/api/timeline')
                .then(response => response.json())
                .then(data => {
                    const ctx = document.getElementById('timelineChart').getContext('2d');
                    const timeline = data.timeline.slice(-24); // Last 24 hours
                    
                    if (timelineChart) timelineChart.destroy();
                    timelineChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: timeline.map(t => new Date(t.timestamp + ':00:00').toLocaleTimeString()),
                            datasets: [{
                                label: 'Attacks',
                                data: timeline.map(t => t.total_attacks),
                                borderColor: '#4CAF50',
                                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: { 
                                    beginAtZero: true,
                                    ticks: { color: '#fff' }
                                },
                                x: { 
                                    ticks: { color: '#fff' }
                                }
                            },
                            plugins: {
                                legend: { labels: { color: '#fff' } }
                            }
                        }
                    });
                });
        }

        // Socket.IO event handlers
        socket.on('connect', () => {
            console.log('Connected to dashboard');
        });

        socket.on('attack_update', (data) => {
            // Update dashboard with real-time data
            loadStats();
            loadRecentAttacks();
            loadAttackMap();
        });

        // Initialize dashboard on page load
        document.addEventListener('DOMContentLoaded', initDashboard);

        // Refresh data every 30 seconds
        setInterval(() => {
            loadStats();
            loadRecentAttacks();
            loadAttackMap();
            loadCharts();
        }, 30000);
    </script>
</body>
</html>'''
    
    with open(os.path.join(templates_dir, 'dashboard.html'), 'w') as f:
        f.write(dashboard_html)

def main():
    """Main function"""
    # Load configuration
    load_config()
    
    # Create templates
    create_templates()
    
    # Initialize threat intelligence
    init_threat_intelligence()
    
    # Start log monitoring thread
    monitor_thread = threading.Thread(target=log_monitor_thread)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Get dashboard configuration
    dashboard_config = config.get('dashboard', {})
    host = dashboard_config.get('host', '0.0.0.0')
    port = dashboard_config.get('port', 12000)
    debug = dashboard_config.get('debug', False)
    
    print(f"Starting Honeypot Dashboard on {host}:{port}")
    
    # Start Flask app with SocketIO
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()