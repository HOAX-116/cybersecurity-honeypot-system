#!/usr/bin/env python3

import socket
import threading
import paramiko
import json
import time
import logging
import sys
import os
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class SSHHoneypot:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.host = '0.0.0.0'
        self.port = config['honeypot']['ssh']['port']
        self.banner = config['honeypot']['ssh']['banner']
        self.fake_users = {user['username']: user['password'] 
                          for user in config['honeypot']['ssh']['fake_users']}
        self.max_connections = config['honeypot']['ssh']['max_connections']
        self.timeout = config['honeypot']['ssh']['timeout']
        self.active_connections = 0
        
        # Generate host key
        self.host_key = self._generate_host_key()
        
    def _generate_host_key(self):
        """Generate RSA host key for SSH server"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return paramiko.RSAKey.from_private_key_file(
            file_obj=type('StringIO', (), {'read': lambda: pem.decode()})()
        )
    
    def _log_event(self, event_type, client_ip, **kwargs):
        """Log honeypot events in JSON format"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'ssh',
            'event_type': event_type,
            'source_ip': client_ip,
            'source_port': kwargs.get('source_port'),
            'destination_port': self.port,
            **kwargs
        }
        
        # Log to file
        log_file = 'logs/ssh_honeypot.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Log to console
        self.logger.info(f"SSH Event: {event_type} from {client_ip}")
    
    def handle_client(self, client_socket, client_address):
        """Handle individual SSH client connections"""
        client_ip = client_address[0]
        client_port = client_address[1]
        
        try:
            self.active_connections += 1
            self._log_event('connection_attempt', client_ip, source_port=client_port)
            
            # Create SSH transport
            transport = paramiko.Transport(client_socket)
            transport.add_server_key(self.host_key)
            
            # Create SSH server interface
            server = SSHServerInterface(self, client_ip)
            
            try:
                transport.start_server(server=server)
                
                # Wait for authentication
                channel = transport.accept(self.timeout)
                if channel is not None:
                    self._handle_shell_session(channel, client_ip)
                    
            except Exception as e:
                self._log_event('transport_error', client_ip, error=str(e))
                
        except Exception as e:
            self._log_event('connection_error', client_ip, error=str(e))
        finally:
            self.active_connections -= 1
            try:
                client_socket.close()
            except:
                pass
    
    def _handle_shell_session(self, channel, client_ip):
        """Handle shell session after successful authentication"""
        try:
            channel.send(b'Welcome to Ubuntu 20.04.5 LTS (GNU/Linux 5.4.0-135-generic x86_64)\r\n\r\n')
            channel.send(b'Last login: ' + datetime.now().strftime('%a %b %d %H:%M:%S %Y').encode() + b' from ' + client_ip.encode() + b'\r\n')
            channel.send(b'$ ')
            
            command_buffer = b''
            
            while True:
                try:
                    data = channel.recv(1024)
                    if not data:
                        break
                    
                    if data == b'\r' or data == b'\n' or data == b'\r\n':
                        command = command_buffer.decode('utf-8', errors='ignore').strip()
                        if command:
                            self._log_event('command_executed', client_ip, command=command)
                            self._handle_command(channel, command, client_ip)
                        command_buffer = b''
                        channel.send(b'$ ')
                    elif data == b'\x03':  # Ctrl+C
                        channel.send(b'^C\r\n$ ')
                        command_buffer = b''
                    elif data == b'\x04':  # Ctrl+D
                        break
                    elif data == b'\x7f':  # Backspace
                        if command_buffer:
                            command_buffer = command_buffer[:-1]
                            channel.send(b'\b \b')
                    else:
                        command_buffer += data
                        channel.send(data)
                        
                except socket.timeout:
                    break
                except Exception as e:
                    self._log_event('shell_error', client_ip, error=str(e))
                    break
                    
        except Exception as e:
            self._log_event('shell_session_error', client_ip, error=str(e))
        finally:
            try:
                channel.close()
            except:
                pass
    
    def _handle_command(self, channel, command, client_ip):
        """Handle commands executed in the shell"""
        command_lower = command.lower().strip()
        
        # Simulate common command responses
        if command_lower == 'whoami':
            channel.send(b'root\r\n')
        elif command_lower == 'pwd':
            channel.send(b'/root\r\n')
        elif command_lower.startswith('ls'):
            channel.send(b'Desktop  Documents  Downloads  Pictures  Videos\r\n')
        elif command_lower == 'id':
            channel.send(b'uid=0(root) gid=0(root) groups=0(root)\r\n')
        elif command_lower == 'uname -a':
            channel.send(b'Linux honeypot 5.4.0-135-generic #152-Ubuntu SMP Wed Nov 23 20:19:22 UTC 2022 x86_64 x86_64 x86_64 GNU/Linux\r\n')
        elif command_lower.startswith('cat /etc/passwd'):
            channel.send(b'root:x:0:0:root:/root:/bin/bash\r\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\r\n')
        elif command_lower.startswith('ps'):
            channel.send(b'  PID TTY          TIME CMD\r\n 1234 pts/0    00:00:00 bash\r\n 5678 pts/0    00:00:00 ps\r\n')
        elif command_lower == 'exit' or command_lower == 'logout':
            channel.send(b'logout\r\n')
            return False
        else:
            # For unknown commands, simulate command not found or hang
            if any(suspicious in command_lower for suspicious in ['wget', 'curl', 'nc', 'nmap']):
                channel.send(f'{command}: command not found\r\n'.encode())
            else:
                channel.send(f'{command}: command not found\r\n'.encode())
        
        return True
    
    def start(self):
        """Start the SSH honeypot server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(self.max_connections)
            
            self.logger.info(f"SSH Honeypot started on {self.host}:{self.port}")
            self._log_event('honeypot_started', '0.0.0.0')
            
            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    
                    if self.active_connections < self.max_connections:
                        client_thread = threading.Thread(
                            target=self.handle_client,
                            args=(client_socket, client_address)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                    else:
                        client_socket.close()
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"SSH server error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to start SSH honeypot: {e}")
        finally:
            server_socket.close()
            self._log_event('honeypot_stopped', '0.0.0.0')


class SSHServerInterface(paramiko.ServerInterface):
    def __init__(self, honeypot, client_ip):
        self.honeypot = honeypot
        self.client_ip = client_ip
    
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_auth_password(self, username, password):
        """Check password authentication"""
        self.honeypot._log_event(
            'login_attempt',
            self.client_ip,
            username=username,
            password=password,
            success=False
        )
        
        # Always fail authentication but log the attempt
        return paramiko.AUTH_FAILED
    
    def check_auth_publickey(self, username, key):
        """Check public key authentication"""
        self.honeypot._log_event(
            'pubkey_attempt',
            self.client_ip,
            username=username,
            key_type=key.get_name(),
            success=False
        )
        return paramiko.AUTH_FAILED
    
    def get_allowed_auths(self, username):
        return 'password,publickey'
    
    def check_channel_shell_request(self, channel):
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True


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
    logger = logging.getLogger('SSH_Honeypot')
    
    # Start SSH honeypot
    honeypot = SSHHoneypot(config, logger)
    honeypot.start()