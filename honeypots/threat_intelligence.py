#!/usr/bin/env python3

import requests
import json
import time
import logging
import threading
import os
from datetime import datetime, timedelta
import geoip2.database
import geoip2.errors

class ThreatIntelligence:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('ThreatIntelligence')
        self.threat_feeds = config.get('threat_intelligence', {}).get('sources', [])
        self.update_interval = config.get('threat_intelligence', {}).get('update_interval', 3600)
        self.malicious_ips = set()
        self.geodb_path = config.get('geolocation', {}).get('database_path', 'data/GeoLite2-City.mmdb')
        self.geodb = None
        self.running = False
        
        # Initialize GeoIP database
        self._init_geodb()
        
        # Load initial threat data
        self._load_threat_feeds()
        
    def _init_geodb(self):
        """Initialize GeoIP database"""
        try:
            if os.path.exists(self.geodb_path):
                self.geodb = geoip2.database.Reader(self.geodb_path)
                self.logger.info("GeoIP database loaded successfully")
            else:
                self.logger.warning(f"GeoIP database not found at {self.geodb_path}")
                self._download_geodb()
        except Exception as e:
            self.logger.error(f"Failed to initialize GeoIP database: {e}")
    
    def _download_geodb(self):
        """Download GeoLite2 database (requires MaxMind account)"""
        self.logger.info("GeoIP database not available. Please download GeoLite2-City.mmdb from MaxMind")
        # Note: MaxMind now requires registration to download GeoLite2 databases
        # Users need to download manually and place in data/ directory
    
    def _load_threat_feeds(self):
        """Load threat intelligence feeds"""
        self.logger.info("Loading threat intelligence feeds...")
        
        for feed_url in self.threat_feeds:
            try:
                self._load_feed(feed_url)
            except Exception as e:
                self.logger.error(f"Failed to load threat feed {feed_url}: {e}")
        
        self.logger.info(f"Loaded {len(self.malicious_ips)} malicious IPs")
    
    def _load_feed(self, feed_url):
        """Load individual threat feed"""
        try:
            response = requests.get(feed_url, timeout=30)
            response.raise_for_status()
            
            # Parse different feed formats
            if 'reputation.data' in feed_url:
                self._parse_alienvault_feed(response.text)
            elif 'emerging-Block-IPs.txt' in feed_url:
                self._parse_emerging_threats_feed(response.text)
            else:
                self._parse_generic_feed(response.text)
                
        except Exception as e:
            self.logger.error(f"Error loading feed {feed_url}: {e}")
    
    def _parse_alienvault_feed(self, data):
        """Parse AlienVault OTX reputation feed"""
        for line in data.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('#')
                if parts:
                    ip = parts[0].strip()
                    if self._is_valid_ip(ip):
                        self.malicious_ips.add(ip)
    
    def _parse_emerging_threats_feed(self, data):
        """Parse Emerging Threats feed"""
        for line in data.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if self._is_valid_ip(line):
                    self.malicious_ips.add(line)
    
    def _parse_generic_feed(self, data):
        """Parse generic IP list feed"""
        for line in data.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract IP from line (handle various formats)
                parts = line.split()
                for part in parts:
                    if self._is_valid_ip(part):
                        self.malicious_ips.add(part)
                        break
    
    def _is_valid_ip(self, ip):
        """Check if string is a valid IP address"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except:
            return False
    
    def is_malicious_ip(self, ip):
        """Check if IP is in threat intelligence feeds"""
        return ip in self.malicious_ips
    
    def get_geolocation(self, ip):
        """Get geolocation information for IP"""
        if not self.geodb:
            return None
        
        try:
            response = self.geodb.city(ip)
            return {
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'latitude': float(response.location.latitude) if response.location.latitude else None,
                'longitude': float(response.location.longitude) if response.location.longitude else None,
                'timezone': response.location.time_zone,
                'isp': response.traits.isp if hasattr(response.traits, 'isp') else None
            }
        except geoip2.errors.AddressNotFoundError:
            return None
        except Exception as e:
            self.logger.error(f"Geolocation lookup error for {ip}: {e}")
            return None
    
    def analyze_ip(self, ip):
        """Comprehensive IP analysis"""
        analysis = {
            'ip': ip,
            'timestamp': datetime.utcnow().isoformat(),
            'is_malicious': self.is_malicious_ip(ip),
            'geolocation': self.get_geolocation(ip),
            'risk_score': 0
        }
        
        # Calculate risk score
        if analysis['is_malicious']:
            analysis['risk_score'] += 50
        
        # Add risk based on geolocation
        geo = analysis['geolocation']
        if geo:
            # Higher risk for certain countries (example)
            high_risk_countries = ['CN', 'RU', 'KP', 'IR']
            if geo.get('country_code') in high_risk_countries:
                analysis['risk_score'] += 20
        
        # Categorize risk level
        if analysis['risk_score'] >= 70:
            analysis['risk_level'] = 'HIGH'
        elif analysis['risk_score'] >= 40:
            analysis['risk_level'] = 'MEDIUM'
        elif analysis['risk_score'] >= 20:
            analysis['risk_level'] = 'LOW'
        else:
            analysis['risk_level'] = 'MINIMAL'
        
        return analysis
    
    def start_auto_update(self):
        """Start automatic threat feed updates"""
        self.running = True
        update_thread = threading.Thread(target=self._auto_update_loop)
        update_thread.daemon = True
        update_thread.start()
        self.logger.info("Started automatic threat intelligence updates")
    
    def _auto_update_loop(self):
        """Automatic update loop"""
        while self.running:
            try:
                time.sleep(self.update_interval)
                if self.running:
                    self.logger.info("Updating threat intelligence feeds...")
                    self._load_threat_feeds()
            except Exception as e:
                self.logger.error(f"Error in auto-update loop: {e}")
    
    def stop_auto_update(self):
        """Stop automatic updates"""
        self.running = False
    
    def get_stats(self):
        """Get threat intelligence statistics"""
        return {
            'malicious_ips_count': len(self.malicious_ips),
            'feeds_configured': len(self.threat_feeds),
            'geodb_available': self.geodb is not None,
            'last_update': datetime.utcnow().isoformat()
        }


class AttackAnalyzer:
    def __init__(self, threat_intel):
        self.threat_intel = threat_intel
        self.logger = logging.getLogger('AttackAnalyzer')
        self.attack_patterns = {}
        self.ip_activity = {}
    
    def analyze_attack(self, log_entry):
        """Analyze attack patterns from log entry"""
        source_ip = log_entry.get('source_ip')
        service = log_entry.get('service')
        event_type = log_entry.get('event_type')
        
        if not source_ip:
            return None
        
        # Get IP intelligence
        ip_analysis = self.threat_intel.analyze_ip(source_ip)
        
        # Track IP activity
        if source_ip not in self.ip_activity:
            self.ip_activity[source_ip] = {
                'first_seen': log_entry.get('timestamp'),
                'last_seen': log_entry.get('timestamp'),
                'services_targeted': set(),
                'attack_types': set(),
                'total_attempts': 0
            }
        
        activity = self.ip_activity[source_ip]
        activity['last_seen'] = log_entry.get('timestamp')
        activity['services_targeted'].add(service)
        activity['attack_types'].add(event_type)
        activity['total_attempts'] += 1
        
        # Analyze attack pattern
        attack_analysis = {
            'source_ip': source_ip,
            'timestamp': log_entry.get('timestamp'),
            'service': service,
            'event_type': event_type,
            'ip_intelligence': ip_analysis,
            'attack_pattern': self._classify_attack_pattern(log_entry, activity),
            'severity': self._calculate_severity(log_entry, activity, ip_analysis)
        }
        
        return attack_analysis
    
    def _classify_attack_pattern(self, log_entry, activity):
        """Classify attack pattern"""
        service = log_entry.get('service')
        event_type = log_entry.get('event_type')
        
        patterns = []
        
        # Brute force detection
        if event_type == 'login_attempt' and activity['total_attempts'] > 5:
            patterns.append('brute_force')
        
        # Multi-service scanning
        if len(activity['services_targeted']) > 2:
            patterns.append('multi_service_scan')
        
        # Reconnaissance
        if any(attack_type in ['command_executed', 'file_access_attempt'] 
               for attack_type in activity['attack_types']):
            patterns.append('reconnaissance')
        
        # Automated scanning
        user_agent = log_entry.get('user_agent', '').lower()
        if any(tool in user_agent for tool in ['nmap', 'masscan', 'nikto']):
            patterns.append('automated_scan')
        
        return patterns if patterns else ['unknown']
    
    def _calculate_severity(self, log_entry, activity, ip_analysis):
        """Calculate attack severity"""
        severity_score = 0
        
        # Base score from IP intelligence
        severity_score += ip_analysis.get('risk_score', 0)
        
        # Activity-based scoring
        if activity['total_attempts'] > 10:
            severity_score += 20
        elif activity['total_attempts'] > 5:
            severity_score += 10
        
        if len(activity['services_targeted']) > 2:
            severity_score += 15
        
        # Event-specific scoring
        event_type = log_entry.get('event_type')
        if event_type in ['command_executed', 'file_upload_attempt']:
            severity_score += 25
        elif event_type in ['sql_injection_attempt', 'xss_attempt']:
            severity_score += 30
        
        # Convert to severity level
        if severity_score >= 80:
            return 'CRITICAL'
        elif severity_score >= 60:
            return 'HIGH'
        elif severity_score >= 40:
            return 'MEDIUM'
        elif severity_score >= 20:
            return 'LOW'
        else:
            return 'INFO'
    
    def get_top_attackers(self, limit=10):
        """Get top attacking IPs"""
        sorted_ips = sorted(
            self.ip_activity.items(),
            key=lambda x: x[1]['total_attempts'],
            reverse=True
        )
        
        return [
            {
                'ip': ip,
                'attempts': data['total_attempts'],
                'services': list(data['services_targeted']),
                'first_seen': data['first_seen'],
                'last_seen': data['last_seen']
            }
            for ip, data in sorted_ips[:limit]
        ]
    
    def get_attack_statistics(self):
        """Get attack statistics"""
        total_ips = len(self.ip_activity)
        total_attempts = sum(data['total_attempts'] for data in self.ip_activity.values())
        
        services_targeted = {}
        for data in self.ip_activity.values():
            for service in data['services_targeted']:
                services_targeted[service] = services_targeted.get(service, 0) + 1
        
        return {
            'total_unique_ips': total_ips,
            'total_attack_attempts': total_attempts,
            'services_targeted': services_targeted,
            'top_attackers': self.get_top_attackers(5)
        }