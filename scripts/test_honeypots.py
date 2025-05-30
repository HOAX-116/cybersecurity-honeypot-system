#!/usr/bin/env python3

import socket
import time
import threading
import requests
from ftplib import FTP
import telnetlib
import paramiko

class HoneypotTester:
    def __init__(self):
        self.results = {}
    
    def test_ssh_honeypot(self, host='localhost', port=2222):
        """Test SSH honeypot"""
        print(f"Testing SSH honeypot on {host}:{port}")
        try:
            # Test connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                # Test SSH banner
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                try:
                    client.connect(host, port, username='test', password='test', timeout=5)
                    self.results['ssh'] = {'status': 'FAIL', 'reason': 'Login should have failed'}
                except paramiko.AuthenticationException:
                    self.results['ssh'] = {'status': 'PASS', 'reason': 'Authentication properly rejected'}
                except Exception as e:
                    self.results['ssh'] = {'status': 'PASS', 'reason': f'SSH service responding: {str(e)}'}
                finally:
                    client.close()
            else:
                self.results['ssh'] = {'status': 'FAIL', 'reason': 'Connection refused'}
                
        except Exception as e:
            self.results['ssh'] = {'status': 'ERROR', 'reason': str(e)}
    
    def test_http_honeypot(self, host='localhost', port=8080):
        """Test HTTP honeypot"""
        print(f"Testing HTTP honeypot on {host}:{port}")
        try:
            # Test basic connection
            response = requests.get(f'http://{host}:{port}/', timeout=5)
            
            if response.status_code == 200:
                self.results['http'] = {'status': 'PASS', 'reason': 'HTTP service responding'}
                
                # Test admin page
                admin_response = requests.get(f'http://{host}:{port}/admin', timeout=5)
                if admin_response.status_code in [200, 401]:
                    self.results['http']['admin_page'] = 'PASS'
                else:
                    self.results['http']['admin_page'] = 'FAIL'
            else:
                self.results['http'] = {'status': 'FAIL', 'reason': f'Unexpected status code: {response.status_code}'}
                
        except Exception as e:
            self.results['http'] = {'status': 'ERROR', 'reason': str(e)}
    
    def test_ftp_honeypot(self, host='localhost', port=2121):
        """Test FTP honeypot"""
        print(f"Testing FTP honeypot on {host}:{port}")
        try:
            ftp = FTP()
            ftp.connect(host, port, timeout=5)
            
            # Test anonymous login
            try:
                ftp.login('anonymous', 'test@example.com')
                self.results['ftp'] = {'status': 'PASS', 'reason': 'Anonymous login successful'}
                
                # Test directory listing
                try:
                    files = ftp.nlst()
                    self.results['ftp']['listing'] = 'PASS'
                except:
                    self.results['ftp']['listing'] = 'FAIL'
                    
                ftp.quit()
            except Exception as e:
                self.results['ftp'] = {'status': 'PASS', 'reason': f'FTP service responding: {str(e)}'}
                
        except Exception as e:
            self.results['ftp'] = {'status': 'ERROR', 'reason': str(e)}
    
    def test_telnet_honeypot(self, host='localhost', port=2323):
        """Test Telnet honeypot"""
        print(f"Testing Telnet honeypot on {host}:{port}")
        try:
            tn = telnetlib.Telnet(host, port, timeout=5)
            
            # Read initial banner
            banner = tn.read_until(b'login:', timeout=5)
            
            if b'login:' in banner:
                # Try login
                tn.write(b'test\n')
                tn.read_until(b'Password:', timeout=5)
                tn.write(b'test\n')
                
                response = tn.read_some()
                if b'incorrect' in response.lower() or b'failed' in response.lower():
                    self.results['telnet'] = {'status': 'PASS', 'reason': 'Login properly rejected'}
                else:
                    self.results['telnet'] = {'status': 'PASS', 'reason': 'Telnet service responding'}
            else:
                self.results['telnet'] = {'status': 'PASS', 'reason': 'Telnet service responding'}
                
            tn.close()
            
        except Exception as e:
            self.results['telnet'] = {'status': 'ERROR', 'reason': str(e)}
    
    def test_dashboard(self, host='localhost', port=12000):
        """Test dashboard"""
        print(f"Testing dashboard on {host}:{port}")
        try:
            response = requests.get(f'http://{host}:{port}/', timeout=5)
            
            if response.status_code == 200:
                self.results['dashboard'] = {'status': 'PASS', 'reason': 'Dashboard accessible'}
                
                # Test API endpoints
                api_response = requests.get(f'http://{host}:{port}/api/stats', timeout=5)
                if api_response.status_code == 200:
                    self.results['dashboard']['api'] = 'PASS'
                else:
                    self.results['dashboard']['api'] = 'FAIL'
            else:
                self.results['dashboard'] = {'status': 'FAIL', 'reason': f'Status code: {response.status_code}'}
                
        except Exception as e:
            self.results['dashboard'] = {'status': 'ERROR', 'reason': str(e)}
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Running Honeypot System Tests")
        print("=" * 40)
        
        tests = [
            self.test_ssh_honeypot,
            self.test_http_honeypot,
            self.test_ftp_honeypot,
            self.test_telnet_honeypot,
            self.test_dashboard
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"Test error: {e}")
            time.sleep(1)
        
        self.print_results()
    
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 40)
        print("TEST RESULTS")
        print("=" * 40)
        
        for service, result in self.results.items():
            status = result['status']
            reason = result['reason']
            
            if status == 'PASS':
                status_icon = "✅"
            elif status == 'FAIL':
                status_icon = "❌"
            else:
                status_icon = "⚠️"
            
            print(f"{status_icon} {service.upper():10} : {status:5} - {reason}")
            
            # Print sub-tests if any
            for key, value in result.items():
                if key not in ['status', 'reason']:
                    sub_icon = "✅" if value == 'PASS' else "❌"
                    print(f"   {sub_icon} {key}: {value}")
        
        print("=" * 40)


def main():
    tester = HoneypotTester()
    tester.run_all_tests()


if __name__ == '__main__':
    main()