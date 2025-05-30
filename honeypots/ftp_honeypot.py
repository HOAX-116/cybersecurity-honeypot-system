#!/usr/bin/env python3

import socket
import threading
import json
import time
import logging
import os
from datetime import datetime

class FTPHoneypot:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.host = '0.0.0.0'
        self.port = config['honeypot']['ftp']['port']
        self.banner = config['honeypot']['ftp']['banner']
        self.anonymous_allowed = config['honeypot']['ftp']['anonymous_allowed']
        self.fake_files = config['honeypot']['ftp']['fake_files']
        
    def _log_event(self, event_type, client_ip, **kwargs):
        """Log honeypot events in JSON format"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'ftp',
            'event_type': event_type,
            'source_ip': client_ip,
            'source_port': kwargs.get('source_port'),
            'destination_port': self.port,
            **kwargs
        }
        
        # Log to file
        log_file = 'logs/ftp_honeypot.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Log to console
        self.logger.info(f"FTP Event: {event_type} from {client_ip}")
    
    def _send_response(self, client_socket, code, message):
        """Send FTP response to client"""
        response = f"{code} {message}\r\n"
        try:
            client_socket.send(response.encode('utf-8'))
        except Exception:
            pass
    
    def _parse_command(self, data):
        """Parse FTP command"""
        try:
            command_line = data.decode('utf-8', errors='ignore').strip()
            if ' ' in command_line:
                command, args = command_line.split(' ', 1)
            else:
                command, args = command_line, ''
            return command.upper(), args
        except Exception:
            return '', ''
    
    def _handle_user_command(self, client_socket, client_ip, username):
        """Handle USER command"""
        self._log_event('login_attempt', client_ip, username=username, step='user')
        
        if username.lower() == 'anonymous' and self.anonymous_allowed:
            self._send_response(client_socket, 331, "Anonymous login ok, send your complete email address as your password")
            return 'NEED_PASS_ANON'
        else:
            self._send_response(client_socket, 331, "Password required for " + username)
            return 'NEED_PASS'
    
    def _handle_pass_command(self, client_socket, client_ip, password, state, username=''):
        """Handle PASS command"""
        self._log_event('login_attempt', client_ip, username=username, password=password, step='password')
        
        if state == 'NEED_PASS_ANON':
            self._send_response(client_socket, 230, "Anonymous access granted, restrictions apply")
            return 'LOGGED_IN'
        else:
            # Always fail non-anonymous login
            self._send_response(client_socket, 530, "Login incorrect")
            return 'NOT_LOGGED_IN'
    
    def _handle_list_command(self, client_socket, client_ip):
        """Handle LIST command"""
        self._log_event('command_executed', client_ip, command='LIST')
        
        # Simulate file listing
        file_list = ""
        for i, filename in enumerate(self.fake_files):
            file_list += f"-rw-r--r--   1 ftp      ftp          {1000 + i*100} Nov 23 10:30 {filename}\r\n"
        
        self._send_response(client_socket, 150, "Here comes the directory listing")
        # In a real FTP server, this would be sent over data connection
        self._send_response(client_socket, 226, "Directory send OK")
    
    def _handle_retr_command(self, client_socket, client_ip, filename):
        """Handle RETR command"""
        self._log_event('file_download_attempt', client_ip, filename=filename)
        
        if filename in self.fake_files:
            self._send_response(client_socket, 150, f"Opening BINARY mode data connection for {filename}")
            # Simulate file transfer
            time.sleep(1)
            self._send_response(client_socket, 226, "Transfer complete")
        else:
            self._send_response(client_socket, 550, f"{filename}: No such file or directory")
    
    def _handle_stor_command(self, client_socket, client_ip, filename):
        """Handle STOR command"""
        self._log_event('file_upload_attempt', client_ip, filename=filename)
        self._send_response(client_socket, 550, "Permission denied")
    
    def _handle_pwd_command(self, client_socket, client_ip):
        """Handle PWD command"""
        self._log_event('command_executed', client_ip, command='PWD')
        self._send_response(client_socket, 257, '"/home/ftp" is current directory')
    
    def _handle_cwd_command(self, client_socket, client_ip, directory):
        """Handle CWD command"""
        self._log_event('command_executed', client_ip, command='CWD', directory=directory)
        
        # Allow some common directories
        if directory in ['/', '/home', '/home/ftp', '..', '.']:
            self._send_response(client_socket, 250, f"CWD command successful")
        else:
            self._send_response(client_socket, 550, f"{directory}: No such file or directory")
    
    def _handle_type_command(self, client_socket, client_ip, type_arg):
        """Handle TYPE command"""
        self._log_event('command_executed', client_ip, command='TYPE', type=type_arg)
        
        if type_arg.upper() in ['A', 'I']:
            self._send_response(client_socket, 200, f"Type set to {type_arg.upper()}")
        else:
            self._send_response(client_socket, 504, "Command not implemented for that parameter")
    
    def _handle_pasv_command(self, client_socket, client_ip):
        """Handle PASV command"""
        self._log_event('command_executed', client_ip, command='PASV')
        # Simulate passive mode response
        self._send_response(client_socket, 227, "Entering Passive Mode (127,0,0,1,20,21)")
    
    def _handle_port_command(self, client_socket, client_ip, port_args):
        """Handle PORT command"""
        self._log_event('command_executed', client_ip, command='PORT', args=port_args)
        self._send_response(client_socket, 200, "PORT command successful")
    
    def handle_client(self, client_socket, client_address):
        """Handle individual FTP client connections"""
        client_ip = client_address[0]
        client_port = client_address[1]
        
        try:
            self._log_event('connection_attempt', client_ip, source_port=client_port)
            
            # Send welcome banner
            self._send_response(client_socket, 220, self.banner)
            
            state = 'NOT_LOGGED_IN'
            username = ''
            
            client_socket.settimeout(300)  # 5 minute timeout
            
            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    command, args = self._parse_command(data)
                    
                    if not command:
                        continue
                    
                    self._log_event('command_received', client_ip, command=command, args=args)
                    
                    if command == 'USER':
                        username = args
                        state = self._handle_user_command(client_socket, client_ip, username)
                    
                    elif command == 'PASS':
                        state = self._handle_pass_command(client_socket, client_ip, args, state, username)
                    
                    elif command == 'QUIT':
                        self._send_response(client_socket, 221, "Goodbye")
                        break
                    
                    elif command == 'SYST':
                        self._send_response(client_socket, 215, "UNIX Type: L8")
                    
                    elif command == 'FEAT':
                        self._send_response(client_socket, 211, "Features supported")
                    
                    elif state == 'LOGGED_IN':
                        if command == 'LIST' or command == 'NLST':
                            self._handle_list_command(client_socket, client_ip)
                        
                        elif command == 'RETR':
                            self._handle_retr_command(client_socket, client_ip, args)
                        
                        elif command == 'STOR':
                            self._handle_stor_command(client_socket, client_ip, args)
                        
                        elif command == 'PWD':
                            self._handle_pwd_command(client_socket, client_ip)
                        
                        elif command == 'CWD':
                            self._handle_cwd_command(client_socket, client_ip, args)
                        
                        elif command == 'TYPE':
                            self._handle_type_command(client_socket, client_ip, args)
                        
                        elif command == 'PASV':
                            self._handle_pasv_command(client_socket, client_ip)
                        
                        elif command == 'PORT':
                            self._handle_port_command(client_socket, client_ip, args)
                        
                        elif command == 'NOOP':
                            self._send_response(client_socket, 200, "NOOP command successful")
                        
                        else:
                            self._send_response(client_socket, 502, f"Command {command} not implemented")
                    
                    else:
                        self._send_response(client_socket, 530, "Please login with USER and PASS")
                
                except socket.timeout:
                    self._send_response(client_socket, 421, "Timeout")
                    break
                except Exception as e:
                    self._log_event('session_error', client_ip, error=str(e))
                    break
                    
        except Exception as e:
            self._log_event('connection_error', client_ip, error=str(e))
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def start(self):
        """Start the FTP honeypot server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(50)
            
            self.logger.info(f"FTP Honeypot started on {self.host}:{self.port}")
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
                    self.logger.error(f"FTP server error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to start FTP honeypot: {e}")
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
    logger = logging.getLogger('FTP_Honeypot')
    
    # Start FTP honeypot
    honeypot = FTPHoneypot(config, logger)
    honeypot.start()