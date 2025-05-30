#!/usr/bin/env python3

import socket
import threading
import json
import time
import logging
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote

class HTTPHoneypot:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.host = '0.0.0.0'
        self.port = config['honeypot']['http']['port']
        self.server_name = config['honeypot']['http']['server_name']
        self.fake_pages = {page['path']: page['template'] 
                          for page in config['honeypot']['http']['fake_pages']}
        
    def _log_event(self, event_type, client_ip, **kwargs):
        """Log honeypot events in JSON format"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'http',
            'event_type': event_type,
            'source_ip': client_ip,
            'source_port': kwargs.get('source_port'),
            'destination_port': self.port,
            **kwargs
        }
        
        # Log to file
        log_file = 'logs/http_honeypot.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Log to console
        self.logger.info(f"HTTP Event: {event_type} from {client_ip}")
    
    def _parse_http_request(self, request_data):
        """Parse HTTP request"""
        try:
            lines = request_data.decode('utf-8', errors='ignore').split('\r\n')
            if not lines:
                return None
            
            # Parse request line
            request_line = lines[0].split(' ')
            if len(request_line) < 3:
                return None
            
            method = request_line[0]
            path = request_line[1]
            version = request_line[2]
            
            # Parse headers
            headers = {}
            body = ''
            body_start = False
            
            for line in lines[1:]:
                if not body_start:
                    if line == '':
                        body_start = True
                        continue
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip().lower()] = value.strip()
                else:
                    body += line + '\n'
            
            return {
                'method': method,
                'path': path,
                'version': version,
                'headers': headers,
                'body': body.strip()
            }
        except Exception:
            return None
    
    def _generate_response(self, request, client_ip):
        """Generate HTTP response based on request"""
        if not request:
            return self._generate_error_response(400, "Bad Request")
        
        method = request['method']
        path = request['path']
        headers = request['headers']
        body = request['body']
        
        # Log the request
        self._log_event(
            'http_request',
            client_ip,
            method=method,
            path=path,
            user_agent=headers.get('user-agent', ''),
            referer=headers.get('referer', ''),
            body=body[:1000] if body else ''  # Limit body size in logs
        )
        
        # Check for suspicious patterns
        self._analyze_request(request, client_ip)
        
        # Handle different paths
        if path in self.fake_pages:
            return self._generate_fake_page_response(path)
        elif path == '/':
            return self._generate_index_response()
        elif path.startswith('/admin') or path.startswith('/wp-admin'):
            return self._generate_admin_response()
        elif path.startswith('/api/'):
            return self._generate_api_response(path)
        elif path.endswith('.php'):
            return self._generate_php_response(path)
        elif any(ext in path for ext in ['.jpg', '.png', '.gif', '.css', '.js']):
            return self._generate_static_response(path)
        else:
            return self._generate_404_response()
    
    def _analyze_request(self, request, client_ip):
        """Analyze request for suspicious patterns"""
        path = request['path']
        user_agent = request['headers'].get('user-agent', '').lower()
        
        # Check for directory traversal
        if '../' in path or '..\\' in path:
            self._log_event('directory_traversal_attempt', client_ip, path=path)
        
        # Check for SQL injection patterns
        sql_patterns = ['union select', 'or 1=1', 'drop table', 'insert into', 'delete from']
        if any(pattern in path.lower() for pattern in sql_patterns):
            self._log_event('sql_injection_attempt', client_ip, path=path)
        
        # Check for XSS patterns
        xss_patterns = ['<script', 'javascript:', 'onerror=', 'onload=']
        if any(pattern in path.lower() for pattern in xss_patterns):
            self._log_event('xss_attempt', client_ip, path=path)
        
        # Check for scanning tools
        scanner_agents = ['nikto', 'nmap', 'masscan', 'sqlmap', 'dirb', 'gobuster']
        if any(scanner in user_agent for scanner in scanner_agents):
            self._log_event('automated_scan', client_ip, user_agent=user_agent)
        
        # Check for common attack paths
        attack_paths = ['/etc/passwd', '/proc/', '/sys/', '/.env', '/config.php']
        if any(attack_path in path for attack_path in attack_paths):
            self._log_event('file_access_attempt', client_ip, path=path)
    
    def _generate_fake_page_response(self, path):
        """Generate response for fake pages"""
        if path == '/admin':
            content = '''<!DOCTYPE html>
<html>
<head><title>Admin Login</title></head>
<body>
<h2>Administrator Login</h2>
<form method="post">
<p>Username: <input type="text" name="username"></p>
<p>Password: <input type="password" name="password"></p>
<p><input type="submit" value="Login"></p>
</form>
</body>
</html>'''
        elif path == '/wp-admin':
            content = '''<!DOCTYPE html>
<html>
<head><title>WordPress Admin</title></head>
<body>
<h1>WordPress</h1>
<form method="post">
<p>Username: <input type="text" name="log"></p>
<p>Password: <input type="password" name="pwd"></p>
<p><input type="submit" value="Log In"></p>
</form>
</body>
</html>'''
        elif path == '/phpmyadmin':
            content = '''<!DOCTYPE html>
<html>
<head><title>phpMyAdmin</title></head>
<body>
<h1>Welcome to phpMyAdmin</h1>
<form method="post">
<p>Username: <input type="text" name="pma_username"></p>
<p>Password: <input type="password" name="pma_password"></p>
<p><input type="submit" value="Go"></p>
</form>
</body>
</html>'''
        else:
            content = '<html><body><h1>Page Found</h1></body></html>'
        
        return self._build_http_response(200, "OK", content)
    
    def _generate_index_response(self):
        """Generate index page response"""
        content = '''<!DOCTYPE html>
<html>
<head>
    <title>Welcome to Apache2 Ubuntu Default Page</title>
</head>
<body>
    <h1>Apache2 Ubuntu Default Page</h1>
    <p>It works!</p>
    <p>This is the default welcome page used to test the correct operation of the Apache2 server after installation on Ubuntu systems.</p>
</body>
</html>'''
        return self._build_http_response(200, "OK", content)
    
    def _generate_admin_response(self):
        """Generate admin area response"""
        content = '''<!DOCTYPE html>
<html>
<head><title>Restricted Area</title></head>
<body>
<h1>401 Unauthorized</h1>
<p>This server could not verify that you are authorized to access the document requested.</p>
</body>
</html>'''
        return self._build_http_response(401, "Unauthorized", content)
    
    def _generate_api_response(self, path):
        """Generate API response"""
        api_data = {
            "error": "API endpoint not found",
            "status": 404,
            "path": path
        }
        content = json.dumps(api_data)
        return self._build_http_response(404, "Not Found", content, content_type="application/json")
    
    def _generate_php_response(self, path):
        """Generate PHP file response"""
        content = '''<!DOCTYPE html>
<html>
<head><title>PHP Error</title></head>
<body>
<h1>Parse error</h1>
<p>Parse error: syntax error, unexpected end of file in ''' + path + ''' on line 1</p>
</body>
</html>'''
        return self._build_http_response(500, "Internal Server Error", content)
    
    def _generate_static_response(self, path):
        """Generate static file response"""
        return self._generate_404_response()
    
    def _generate_404_response(self):
        """Generate 404 response"""
        content = '''<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
<h1>Not Found</h1>
<p>The requested URL was not found on this server.</p>
<hr>
<address>''' + self.server_name + ''' Server</address>
</body>
</html>'''
        return self._build_http_response(404, "Not Found", content)
    
    def _generate_error_response(self, code, message):
        """Generate error response"""
        content = f'''<!DOCTYPE html>
<html>
<head><title>{code} {message}</title></head>
<body>
<h1>{code} {message}</h1>
</body>
</html>'''
        return self._build_http_response(code, message, content)
    
    def _build_http_response(self, status_code, status_message, content, content_type="text/html"):
        """Build HTTP response"""
        response = f"HTTP/1.1 {status_code} {status_message}\r\n"
        response += f"Server: {self.server_name}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(content.encode('utf-8'))}\r\n"
        response += f"Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += content
        
        return response.encode('utf-8')
    
    def handle_client(self, client_socket, client_address):
        """Handle individual HTTP client connections"""
        client_ip = client_address[0]
        client_port = client_address[1]
        
        try:
            self._log_event('connection_attempt', client_ip, source_port=client_port)
            
            # Receive request
            request_data = b''
            client_socket.settimeout(10)
            
            while True:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    request_data += chunk
                    
                    # Check if we have complete request
                    if b'\r\n\r\n' in request_data:
                        break
                        
                except socket.timeout:
                    break
                except Exception:
                    break
            
            if request_data:
                # Parse and handle request
                request = self._parse_http_request(request_data)
                response = self._generate_response(request, client_ip)
                
                # Send response
                try:
                    client_socket.sendall(response)
                except Exception:
                    pass
            
        except Exception as e:
            self._log_event('connection_error', client_ip, error=str(e))
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def start(self):
        """Start the HTTP honeypot server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(100)
            
            self.logger.info(f"HTTP Honeypot started on {self.host}:{self.port}")
            self._log_event('honeypot_started', '0.0.0.0')
            
            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"HTTP server error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to start HTTP honeypot: {e}")
        finally:
            server_socket.close()
            self._log_event('honeypot_stopped', '0.0.0.0')


if __name__ == '__main__':
    import yaml
    
    # Load configuration
    with open('config/honeypot_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config['logging']['level']),
        format=config['logging']['format']
    )
    logger = logging.getLogger('HTTP_Honeypot')
    
    # Start HTTP honeypot
    honeypot = HTTPHoneypot(config, logger)
    honeypot.start()