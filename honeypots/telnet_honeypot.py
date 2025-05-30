#!/usr/bin/env python3

import socket
import threading
import json
import time
import logging
import os
from datetime import datetime

class TelnetHoneypot:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.host = '0.0.0.0'
        self.port = config['honeypot']['telnet']['port']
        self.banner = config['honeypot']['telnet']['banner']
        self.fake_users = {user['username']: user['password'] 
                          for user in config['honeypot']['telnet']['fake_users']}
        
    def _log_event(self, event_type, client_ip, **kwargs):
        """Log honeypot events in JSON format"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'telnet',
            'event_type': event_type,
            'source_ip': client_ip,
            'source_port': kwargs.get('source_port'),
            'destination_port': self.port,
            **kwargs
        }
        
        # Log to file
        log_file = 'logs/telnet_honeypot.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Log to console
        self.logger.info(f"Telnet Event: {event_type} from {client_ip}")
    
    def _send_data(self, client_socket, data):
        """Send data to client"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            client_socket.send(data)
        except Exception:
            pass
    
    def _negotiate_telnet(self, client_socket):
        """Handle basic Telnet option negotiation"""
        # Send basic telnet options
        # IAC WILL ECHO
        self._send_data(client_socket, b'\xff\xfb\x01')
        # IAC WILL SUPPRESS_GO_AHEAD
        self._send_data(client_socket, b'\xff\xfb\x03')
        # IAC DO TERMINAL_TYPE
        self._send_data(client_socket, b'\xff\xfd\x18')
    
    def _handle_login(self, client_socket, client_ip):
        """Handle login process"""
        username = ''
        password = ''
        
        # Send login prompt
        self._send_data(client_socket, f"\r\n{self.banner}\r\n\r\nlogin: ")
        
        # Get username
        username_buffer = b''
        while True:
            try:
                data = client_socket.recv(1)
                if not data:
                    return False, '', ''
                
                # Handle telnet commands
                if data == b'\xff':
                    # Skip telnet command sequences
                    client_socket.recv(2)
                    continue
                
                if data == b'\r' or data == b'\n':
                    username = username_buffer.decode('utf-8', errors='ignore').strip()
                    break
                elif data == b'\x7f' or data == b'\x08':  # Backspace
                    if username_buffer:
                        username_buffer = username_buffer[:-1]
                        self._send_data(client_socket, b'\b \b')
                else:
                    username_buffer += data
                    self._send_data(client_socket, data)
                    
            except Exception:
                return False, '', ''
        
        if not username:
            return False, '', ''
        
        # Send password prompt
        self._send_data(client_socket, "Password: ")
        
        # Get password (don't echo)
        password_buffer = b''
        while True:
            try:
                data = client_socket.recv(1)
                if not data:
                    return False, username, ''
                
                # Handle telnet commands
                if data == b'\xff':
                    # Skip telnet command sequences
                    client_socket.recv(2)
                    continue
                
                if data == b'\r' or data == b'\n':
                    password = password_buffer.decode('utf-8', errors='ignore').strip()
                    break
                elif data == b'\x7f' or data == b'\x08':  # Backspace
                    if password_buffer:
                        password_buffer = password_buffer[:-1]
                else:
                    password_buffer += data
                    
            except Exception:
                return False, username, ''
        
        # Log login attempt
        self._log_event('login_attempt', client_ip, username=username, password=password)
        
        # Check credentials (always fail for security)
        return False, username, password
    
    def _handle_shell_session(self, client_socket, client_ip, username):
        """Handle shell session after login"""
        try:
            # Send welcome message
            self._send_data(client_socket, f"\r\nWelcome to {self.banner}\r\n")
            self._send_data(client_socket, f"Last login: {datetime.now().strftime('%a %b %d %H:%M:%S %Y')} from {client_ip}\r\n")
            
            current_dir = "/home/" + username
            hostname = "honeypot"
            
            while True:
                # Send prompt
                prompt = f"{username}@{hostname}:{current_dir}$ "
                self._send_data(client_socket, prompt)
                
                # Get command
                command_buffer = b''
                while True:
                    try:
                        data = client_socket.recv(1)
                        if not data:
                            return
                        
                        # Handle telnet commands
                        if data == b'\xff':
                            # Skip telnet command sequences
                            try:
                                client_socket.recv(2)
                            except:
                                pass
                            continue
                        
                        if data == b'\r' or data == b'\n':
                            command = command_buffer.decode('utf-8', errors='ignore').strip()
                            self._send_data(client_socket, "\r\n")
                            break
                        elif data == b'\x03':  # Ctrl+C
                            self._send_data(client_socket, "^C\r\n")
                            command_buffer = b''
                            break
                        elif data == b'\x04':  # Ctrl+D
                            self._send_data(client_socket, "logout\r\n")
                            return
                        elif data == b'\x7f' or data == b'\x08':  # Backspace
                            if command_buffer:
                                command_buffer = command_buffer[:-1]
                                self._send_data(client_socket, b'\b \b')
                        else:
                            command_buffer += data
                            self._send_data(client_socket, data)
                            
                    except Exception:
                        return
                
                if not command:
                    continue
                
                # Log command
                self._log_event('command_executed', client_ip, command=command, username=username)
                
                # Handle commands
                if not self._execute_command(client_socket, command, client_ip, username):
                    break
                    
        except Exception as e:
            self._log_event('shell_session_error', client_ip, error=str(e))
    
    def _execute_command(self, client_socket, command, client_ip, username):
        """Execute shell commands"""
        command_lower = command.lower().strip()
        
        if command_lower in ['exit', 'logout', 'quit']:
            self._send_data(client_socket, "logout\r\n")
            return False
        
        elif command_lower == 'whoami':
            self._send_data(client_socket, f"{username}\r\n")
        
        elif command_lower == 'pwd':
            self._send_data(client_socket, f"/home/{username}\r\n")
        
        elif command_lower.startswith('ls'):
            self._send_data(client_socket, "Desktop  Documents  Downloads  Pictures  Videos\r\n")
        
        elif command_lower == 'id':
            self._send_data(client_socket, f"uid=1000({username}) gid=1000({username}) groups=1000({username})\r\n")
        
        elif command_lower == 'uname -a':
            self._send_data(client_socket, "Linux honeypot 5.4.0-135-generic #152-Ubuntu SMP Wed Nov 23 20:19:22 UTC 2022 x86_64 x86_64 x86_64 GNU/Linux\r\n")
        
        elif command_lower.startswith('cat /etc/passwd'):
            self._send_data(client_socket, f"root:x:0:0:root:/root:/bin/bash\r\n{username}:x:1000:1000::/home/{username}:/bin/bash\r\n")
        
        elif command_lower.startswith('ps'):
            self._send_data(client_socket, "  PID TTY          TIME CMD\r\n 1234 pts/0    00:00:00 bash\r\n 5678 pts/0    00:00:00 ps\r\n")
        
        elif command_lower.startswith('netstat'):
            self._send_data(client_socket, "Active Internet connections (w/o servers)\r\nProto Recv-Q Send-Q Local Address           Foreign Address         State\r\n")
        
        elif command_lower.startswith('ifconfig') or command_lower.startswith('ip addr'):
            self._send_data(client_socket, "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\r\n        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255\r\n")
        
        elif command_lower.startswith('cd'):
            parts = command.split()
            if len(parts) > 1:
                directory = parts[1]
                self._log_event('directory_change', client_ip, directory=directory, username=username)
            # Don't actually change directory, just acknowledge
        
        elif any(suspicious in command_lower for suspicious in ['wget', 'curl', 'nc', 'nmap', 'ncat']):
            # Simulate command not found for suspicious commands
            self._send_data(client_socket, f"{command.split()[0]}: command not found\r\n")
        
        elif command_lower.startswith('rm'):
            self._send_data(client_socket, "rm: cannot remove: Permission denied\r\n")
        
        elif command_lower.startswith('sudo'):
            self._send_data(client_socket, f"{username} is not in the sudoers file. This incident will be reported.\r\n")
        
        elif command_lower.startswith('history'):
            self._send_data(client_socket, "    1  ls\r\n    2  pwd\r\n    3  whoami\r\n")
        
        elif command_lower.startswith('env') or command_lower.startswith('printenv'):
            self._send_data(client_socket, f"HOME=/home/{username}\r\nUSER={username}\r\nPATH=/usr/local/bin:/usr/bin:/bin\r\n")
        
        else:
            # For unknown commands, simulate command not found
            cmd_name = command.split()[0] if command.split() else command
            self._send_data(client_socket, f"{cmd_name}: command not found\r\n")
        
        return True
    
    def handle_client(self, client_socket, client_address):
        """Handle individual Telnet client connections"""
        client_ip = client_address[0]
        client_port = client_address[1]
        
        try:
            self._log_event('connection_attempt', client_ip, source_port=client_port)
            
            client_socket.settimeout(300)  # 5 minute timeout
            
            # Handle telnet negotiation
            self._negotiate_telnet(client_socket)
            
            # Handle login
            login_success, username, password = self._handle_login(client_socket, client_ip)
            
            if login_success:
                # This should never happen as we always fail login for security
                self._handle_shell_session(client_socket, client_ip, username)
            else:
                # Send login failed message
                self._send_data(client_socket, "\r\nLogin incorrect\r\n")
                
                # Allow a few more attempts
                for attempt in range(2):
                    login_success, username, password = self._handle_login(client_socket, client_ip)
                    if not login_success:
                        self._send_data(client_socket, "\r\nLogin incorrect\r\n")
                    else:
                        break
                
                if not login_success:
                    self._send_data(client_socket, "\r\nToo many login failures\r\n")
                    
        except Exception as e:
            self._log_event('connection_error', client_ip, error=str(e))
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def start(self):
        """Start the Telnet honeypot server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(50)
            
            self.logger.info(f"Telnet Honeypot started on {self.host}:{self.port}")
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
                    self.logger.error(f"Telnet server error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to start Telnet honeypot: {e}")
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
    logger = logging.getLogger('Telnet_Honeypot')
    
    # Start Telnet honeypot
    honeypot = TelnetHoneypot(config, logger)
    honeypot.start()