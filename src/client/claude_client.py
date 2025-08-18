#!/usr/bin/env python3

import os
import sys
import time
import argparse
import subprocess
import threading
from typing import Optional

try:
    from .data_reader import DataReader
    from .display_manager import DisplayManager
    from ..shared.data_models import MonitoringData
    from ..shared.constants import APP_VERSION
    from ..shared.utils import detect_subscription_limits, run_ccusage_command, detect_subscription_plan_from_ccusage
except ImportError:
    # Direct imports when run from main directory
    try:
        from client.data_reader import DataReader
        from client.display_manager import DisplayManager
        from shared.data_models import MonitoringData
        from shared.constants import APP_VERSION
        from shared.utils import detect_subscription_limits, run_ccusage_command, detect_subscription_plan_from_ccusage
    except ImportError:
        # Fallback for different directory structures
        from data_reader import DataReader
        from display_manager import DisplayManager
        from shared.data_models import MonitoringData
        from shared.constants import APP_VERSION
        from shared.utils import detect_subscription_limits, run_ccusage_command, detect_subscription_plan_from_ccusage


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
    
    def start_daemon_background(self) -> bool:
        """
        Start daemon in background if not running.
        
        Returns:
            True if daemon started successfully or already running, False otherwise
        """
        if self.check_daemon_status():
            return True
        
        try:
            # Find run_daemon.py in the project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
            daemon_script = os.path.join(project_root, 'run_daemon.py')
            
            
            if not os.path.exists(daemon_script):
                print(f"❌ Daemon script not found at {daemon_script}")
                return False
            
            print("🚀 Starting daemon in background...")
            
            # Start daemon in background using subprocess
            # Use uv run to ensure proper environment
            process = subprocess.Popen(
                ['uv', 'run', 'python3', daemon_script],
                cwd=project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent process
            )
            
            # Wait a moment for daemon to start
            time.sleep(2)
            
            # Check if daemon is now running
            for attempt in range(10):  # Wait up to 10 seconds
                if self.check_daemon_status():
                    print("✅ Daemon started successfully!")
                    return True
                time.sleep(1)
            
            print("⚠️ Daemon may be starting, continuing...")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start daemon: {e}")
            return False

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
        
        # Render the display and check if data refresh is needed
        needs_refresh = self.display_manager.render_full_display(monitoring_data)
        
        # If activity sessions changed, force refresh of data for next iteration
        if needs_refresh:
            self.data_reader.clear_cache()
        
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
            "--sessions",
            type=int,
            default=50,
            help="Total monthly sessions limit (default: 50 for Claude Max)"
        )
        
        parser.add_argument(
            "--auto-detect",
            action="store_true",
            default=False,
            help="Automatically detect subscription type (overrides --plan default)"
        )
        
        parser.add_argument(
            "--no-auto-detect",
            action="store_false",
            dest="auto_detect",
            help="Use manual plan selection (default behavior)"
        )
        
        parser.add_argument(
            "--plan",
            type=str,
            choices=["Pro", "Max_5x", "Max_20x"],
            default="Max_5x",
            help="Subscription plan (default: Max_5x). Options: Pro, Max_5x, Max_20x."
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
        # Try to auto-start daemon if not running
        if not self.check_daemon_status():
            print("🔍 Daemon not detected, attempting to start...")
            daemon_started = self.start_daemon_background()
            if not daemon_started:
                print("❌ Failed to auto-start daemon, will show offline display")
        
        # Handle plan selection - now plan is always set (default Max_5x)
        if args.auto_detect:
            print("🔍 Automatyczne wykrywanie subskrypcji...")
            
            # Use new ccusage-based plan detection
            ccusage_data = run_ccusage_command()
            plan_info = detect_subscription_plan_from_ccusage(ccusage_data)
            
            # Convert plan to old format for compatibility
            if plan_info['plan_name'] == 'Max_20x':
                subscription_type = 'claude_max_20x'
                session_limit = 200
            elif plan_info['plan_name'] == 'Max_5x':
                subscription_type = 'claude_max_5x'
                session_limit = 100
            else:  # Pro or fallback
                subscription_type = 'claude_pro'
                session_limit = 50
            
            print(f"✅ Wykryto: {plan_info['plan_name']}")
            print(f"📊 Limity okien: {plan_info['prompts_per_window']} promptów/5h okno")
            print(f"🔬 Metoda: {plan_info['detection_method']}")
            print(f"🎯 Pewność: {plan_info['confidence']}")
            print()
            
            self.total_monthly_sessions = session_limit
            self.display_manager = DisplayManager(self.total_monthly_sessions)
        else:
            # Use manual plan selection (default behavior)
            try:
                from ..shared.constants import SUBSCRIPTION_PLANS
            except ImportError:
                try:
                    from shared.constants import SUBSCRIPTION_PLANS
                except ImportError:
                    from constants import SUBSCRIPTION_PLANS
                    
            plan_name = args.plan
            plan_config = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS['Pro'])
            
            print(f"🎯 Plan wybrany: {plan_name}")
            print(f"📊 Limity okien: {plan_config['default_prompts_per_window']} promptów/5h okno")
            print(f"💰 Koszt miesięczny: ${plan_config['monthly_cost']}")
            print()
            
            # Convert to session limit for compatibility and pass plan info
            session_limit = 50 if plan_name == 'Pro' else 100 if plan_name == 'Max_5x' else 200
            
            self.total_monthly_sessions = session_limit
            self.display_manager = DisplayManager(self.total_monthly_sessions, selected_plan=plan_name)
            # Store plan info for DisplayManager to use
            self.selected_plan = plan_name
        
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