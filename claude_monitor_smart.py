#!/usr/bin/env python3

"""
Smart wrapper for Claude Monitor that automatically chooses between:
- New client (reads from daemon) if daemon is running
- Original monitor (direct ccusage calls) if daemon is not running

This provides seamless backward compatibility for existing users.
"""

import sys
import os
import argparse
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.client.data_reader import DataReader
from src.client.claude_client import ClaudeClient


class SmartClaudeMonitor:
    """
    Smart wrapper that routes to appropriate monitoring implementation.
    """

    def __init__(self):
        """Initialize the smart monitor."""
        # Default data file path
        config_dir = os.path.expanduser("~/.config/claude-monitor")
        self.data_file_path = os.path.join(config_dir, "monitor_data.json")
        
    def is_daemon_running(self) -> bool:
        """
        Check if daemon is running by examining data file freshness.
        
        Returns:
            True if daemon appears to be running, False otherwise
        """
        data_reader = DataReader(self.data_file_path)
        return data_reader.is_daemon_running()
    
    def show_daemon_info(self):
        """Show information about daemon status."""
        if self.is_daemon_running():
            print("✅ Daemon is running - using new client (reads from daemon)")
            print(f"📁 Data file: {self.data_file_path}")
            data_reader = DataReader(self.data_file_path)
            file_age = data_reader.get_file_age()
            print(f"⏰ Last update: {file_age:.1f} seconds ago")
        else:
            print("❌ Daemon not running - using original monitor (direct ccusage)")
            print("💡 To use daemon mode:")
            print("   1. Run: python run_daemon.py")
            print("   2. Then run this script again")

    def run_new_client(self, args: argparse.Namespace):
        """
        Run the new client that reads from daemon files.
        
        Args:
            args: Command line arguments
        """
        print("🔄 Using new client (daemon mode)")
        
        # Convert original args to new client format
        client_args = argparse.Namespace(
            check_daemon=False,
            data_file=self.data_file_path,
            refresh_interval=1.0  # Always 1 second like original
        )
        
        client = ClaudeClient(
            data_file_path=self.data_file_path,
            total_monthly_sessions=50,  # Default from original
            refresh_interval=1.0
        )
        
        client.main(client_args)

    def run_original_monitor(self, original_args: List[str]):
        """
        Run the original claude_monitor.py with ccusage calls.
        
        Args:
            original_args: Original command line arguments
        """
        print("🔄 Using original monitor (direct ccusage)")
        
        # Import and run original main function
        # We need to modify sys.argv to pass the args correctly
        old_argv = sys.argv[:]
        try:
            sys.argv = ['claude_monitor.py'] + original_args
            
            # Import original module and run it
            import claude_monitor
            # The original script will run automatically when imported
            # since it has if __name__ == "__main__" at the end
            
        finally:
            sys.argv = old_argv

    def parse_arguments(self) -> tuple:
        """
        Parse command line arguments compatible with original claude_monitor.py.
        
        Returns:
            Tuple of (parsed_args, remaining_args_for_original)
        """
        parser = argparse.ArgumentParser(
            description="Smart Claude Monitor - automatically chooses daemon or direct mode",
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False  # We'll handle help manually
        )
        
        # Add smart wrapper specific options
        parser.add_argument(
            "--daemon-info",
            action="store_true",
            help="Show daemon status information and exit"
        )
        
        parser.add_argument(
            "--force-direct",
            action="store_true", 
            help="Force direct ccusage mode even if daemon is running"
        )
        
        parser.add_argument(
            "--force-daemon",
            action="store_true",
            help="Force daemon mode even if daemon is not running"
        )
        
        # Parse known args, let original handle the rest
        args, remaining = parser.parse_known_args()
        
        return args, remaining

    def main(self):
        """Main entry point for smart wrapper."""
        wrapper_args, original_args = self.parse_arguments()
        
        # Handle help - show both wrapper and original help
        if '--help' in sys.argv or '-h' in sys.argv:
            print("Smart Claude Monitor - Wrapper Usage:")
            print("=====================================")
            print("--daemon-info     Show daemon status and exit")
            print("--force-direct    Force direct ccusage mode") 
            print("--force-daemon    Force daemon mode")
            print()
            print("Original Claude Monitor Options:")
            print("===============================")
            # Run original with --help
            self.run_original_monitor(['--help'])
            return
        
        # Handle daemon info request
        if wrapper_args.daemon_info:
            self.show_daemon_info()
            return
        
        # Determine mode
        daemon_running = self.is_daemon_running()
        use_daemon_mode = False
        
        if wrapper_args.force_daemon:
            use_daemon_mode = True
            if not daemon_running:
                print("⚠️  Warning: Forcing daemon mode but daemon not detected as running")
        elif wrapper_args.force_direct:
            use_daemon_mode = False
            if daemon_running:
                print("ℹ️  Note: Daemon is running but using direct mode as requested")
        else:
            # Auto-detect mode
            use_daemon_mode = daemon_running
        
        # Route to appropriate implementation
        if use_daemon_mode:
            # Convert original args back to Namespace for new client
            original_namespace = argparse.Namespace()
            
            # Parse original args to extract any we need
            if '--test-alert' in original_args:
                print("🔔 Test alert mode - delegating to original monitor")
                self.run_original_monitor(original_args)
                return
                
            self.run_new_client(original_namespace)
        else:
            self.run_original_monitor(original_args)


def main():
    """Entry point for smart wrapper script."""
    smart_monitor = SmartClaudeMonitor()
    smart_monitor.main()


if __name__ == "__main__":
    main()