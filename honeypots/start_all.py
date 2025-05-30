#!/usr/bin/env python3

import sys
import os
import yaml
import logging
import threading
import time
import signal
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from honeypots.ssh_honeypot import SSHHoneypot
from honeypots.http_honeypot import HTTPHoneypot
from honeypots.ftp_honeypot import FTPHoneypot
from honeypots.telnet_honeypot import TelnetHoneypot

class HoneypotOrchestrator:
    def __init__(self, config_path='config/honeypot_config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self.honeypots = {}
        self.threads = {}
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config['logging']
        
        # Create logs directory
        log_file = log_config['file']
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger('HoneypotOrchestrator')
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_all()
        sys.exit(0)
    
    def _start_honeypot(self, name, honeypot_class):
        """Start a specific honeypot in a thread"""
        try:
            honeypot = honeypot_class(self.config, logging.getLogger(f'{name}_Honeypot'))
            self.honeypots[name] = honeypot
            
            thread = threading.Thread(target=honeypot.start, name=f'{name}_Thread')
            thread.daemon = True
            self.threads[name] = thread
            
            thread.start()
            self.logger.info(f"Started {name} honeypot")
            
        except Exception as e:
            self.logger.error(f"Failed to start {name} honeypot: {e}")
    
    def start_all(self):
        """Start all enabled honeypots"""
        self.logger.info("Starting Honeypot System...")
        self.running = True
        
        # Start SSH honeypot
        if self.config['honeypot']['ssh']['enabled']:
            self._start_honeypot('SSH', SSHHoneypot)
        
        # Start HTTP honeypot
        if self.config['honeypot']['http']['enabled']:
            self._start_honeypot('HTTP', HTTPHoneypot)
        
        # Start FTP honeypot
        if self.config['honeypot']['ftp']['enabled']:
            self._start_honeypot('FTP', FTPHoneypot)
        
        # Start Telnet honeypot
        if self.config['honeypot']['telnet']['enabled']:
            self._start_honeypot('Telnet', TelnetHoneypot)
        
        self.logger.info(f"Started {len(self.threads)} honeypot services")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
                
                # Check if any threads have died
                for name, thread in list(self.threads.items()):
                    if not thread.is_alive():
                        self.logger.warning(f"{name} honeypot thread died, restarting...")
                        # Remove dead thread
                        del self.threads[name]
                        del self.honeypots[name]
                        
                        # Restart honeypot
                        if name == 'SSH' and self.config['honeypot']['ssh']['enabled']:
                            self._start_honeypot('SSH', SSHHoneypot)
                        elif name == 'HTTP' and self.config['honeypot']['http']['enabled']:
                            self._start_honeypot('HTTP', HTTPHoneypot)
                        elif name == 'FTP' and self.config['honeypot']['ftp']['enabled']:
                            self._start_honeypot('FTP', FTPHoneypot)
                        elif name == 'Telnet' and self.config['honeypot']['telnet']['enabled']:
                            self._start_honeypot('Telnet', TelnetHoneypot)
                        
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
            self.stop_all()
    
    def stop_all(self):
        """Stop all honeypots"""
        self.logger.info("Stopping all honeypots...")
        self.running = False
        
        # Wait for threads to finish (with timeout)
        for name, thread in self.threads.items():
            self.logger.info(f"Stopping {name} honeypot...")
            thread.join(timeout=5)
        
        self.logger.info("All honeypots stopped")
    
    def status(self):
        """Get status of all honeypots"""
        status_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'running': self.running,
            'honeypots': {}
        }
        
        for name, thread in self.threads.items():
            status_info['honeypots'][name] = {
                'running': thread.is_alive(),
                'thread_name': thread.name
            }
        
        return status_info
    
    def print_status(self):
        """Print current status"""
        status = self.status()
        
        print("\n" + "="*50)
        print("HONEYPOT SYSTEM STATUS")
        print("="*50)
        print(f"System Running: {status['running']}")
        print(f"Timestamp: {status['timestamp']}")
        print("\nHoneypot Services:")
        
        for name, info in status['honeypots'].items():
            status_str = "RUNNING" if info['running'] else "STOPPED"
            print(f"  {name:10} : {status_str}")
        
        print("="*50)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Service Honeypot System')
    parser.add_argument('--config', '-c', default='config/honeypot_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--status', '-s', action='store_true',
                       help='Show status and exit')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = HoneypotOrchestrator(args.config)
    
    if args.status:
        orchestrator.print_status()
        return
    
    # Start all honeypots
    try:
        orchestrator.start_all()
    except Exception as e:
        orchestrator.logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()