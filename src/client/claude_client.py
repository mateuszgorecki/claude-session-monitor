#!/usr/bin/env python3

import os
import sys
import time
import argparse
from typing import Optional

try:
    from .data_reader import DataReader
    from .display_manager import DisplayManager
    from ..shared.data_models import MonitoringData
    from ..shared.constants import APP_VERSION
except ImportError:
    from data_reader import DataReader
    from display_manager import DisplayManager
    from shared.data_models import MonitoringData
    from shared.constants import APP_VERSION


class ClaudeClient:
    """
    Claude monitor client that reads data from daemon-generated files.
    
    Provides the same user experience as claude_monitor.py but without
    directly calling ccusage - instead reads from daemon's JSON files.
    """

    def __init__(self, data_file_path: Optional[str] = None, 
                 total_monthly_sessions: int = 50,
                 refresh_interval: float = 1.0):
        """
        Initialize Claude client.
        
        Args:
            data_file_path: Path to daemon's data file (default: ~/.config/claude-monitor/monitor_data.json)
            total_monthly_sessions: Expected monthly session limit
            refresh_interval: Display refresh interval in seconds
        """
        # Set default data file path if not provided
        if data_file_path is None:
            config_dir = os.path.expanduser("~/.config/claude-monitor")
            data_file_path = os.path.join(config_dir, "monitor_data.json")
        
        self.data_file_path = data_file_path
        self.total_monthly_sessions = total_monthly_sessions
        self.refresh_interval = refresh_interval
        
        # Initialize components
        self.data_reader = DataReader(self.data_file_path)
        self.display_manager = DisplayManager(total_monthly_sessions)

    def check_daemon_status(self) -> bool:
        """
        Check if daemon is running by examining data file freshness.
        
        Returns:
            True if daemon appears to be running, False otherwise
        """
        return self.data_reader.is_daemon_running()

    def get_monitoring_data(self) -> Optional[MonitoringData]:
        """
        Get current monitoring data from daemon file.
        
        Returns:
            MonitoringData if available, None if daemon not running or data unavailable
        """
        return self.data_reader.read_data()

    def run_single_iteration(self) -> bool:
        """
        Run a single display iteration.
        
        Returns:
            True if successful, False if no data available
        """
        monitoring_data = self.get_monitoring_data()
        
        if monitoring_data is None:
            # Show full-screen daemon offline display
            self.display_manager.render_daemon_offline_display()
            return False
        
        # Render the display
        self.display_manager.render_full_display(monitoring_data)
        return True

    def show_daemon_not_running_message(self):
        """Show message when daemon is not running."""
        self.display_manager.show_error_message(
            "Daemon not running. Please start the daemon first or use the original claude_monitor.py"
        )

    def run(self):
        """
        Run the main client loop - identical behavior to claude_monitor.py.
        
        Refreshes display every second and shows monitoring data.
        """
        try:
            while True:
                success = self.run_single_iteration()
                
                # Wait for next refresh (whether successful or not)
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            self.display_manager.show_exit_message()
            sys.exit(0)

    def parse_arguments(self, args=None):
        """
        Parse command line arguments - compatible with claude_monitor.py.
        
        Args:
            args: Arguments to parse (default: sys.argv)
            
        Returns:
            Parsed arguments namespace
        """
        parser = argparse.ArgumentParser(
            description="Claude Monitor Client - reads data from daemon",
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        parser.add_argument(
            "--refresh-interval", 
            type=float, 
            default=1.0,
            help="Display refresh interval in seconds (default: 1.0)"
        )
        
        parser.add_argument(
            "--check-daemon",
            action="store_true",
            help="Check if daemon is running and exit"
        )
        
        parser.add_argument(
            "--data-file",
            type=str,
            help="Path to daemon data file (default: ~/.config/claude-monitor/monitor_data.json)"
        )
        
        parser.add_argument(
            "--version",
            action="version",
            version=f"Claude Monitor Client {APP_VERSION}"
        )
        
        return parser.parse_args(args)

    def main(self, args):
        """
        Main function for client operation.
        
        Args:
            args: Parsed command line arguments
        """
        # Update configuration from arguments
        if args.data_file:
            self.data_file_path = args.data_file
            self.data_reader = DataReader(self.data_file_path)
        
        if args.refresh_interval:
            self.refresh_interval = args.refresh_interval
        
        # Handle check daemon mode
        if args.check_daemon:
            if self.check_daemon_status():
                self.display_manager.show_info_message("Daemon is running")
                sys.exit(0)
            else:
                self.display_manager.show_error_message("Daemon is not running")
                sys.exit(1)
        
        # Normal operation mode
        self.run()


def main():
    """Entry point for claude_client.py script."""
    client = ClaudeClient()
    args = client.parse_arguments()
    client.main(args)


if __name__ == "__main__":
    main()