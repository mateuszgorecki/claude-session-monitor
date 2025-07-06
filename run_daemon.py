#!/usr/bin/env python3
"""
Simple script to run the Claude monitoring daemon with custom configuration.
"""
import sys
import os
import argparse
import signal
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from daemon.claude_daemon import ClaudeDaemon
from shared.data_models import ConfigData


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🛑 Otrzymano sygnał {signum}, zatrzymuję demona...")
    global daemon_instance
    if daemon_instance:
        daemon_instance.stop()
    sys.exit(0)


daemon_instance = None


def main():
    """Run daemon with command line configuration."""
    parser = argparse.ArgumentParser(description='Uruchom demona Claude Monitor')
    parser.add_argument('--start-day', type=int, default=1, 
                       help='Dzień startu abonamentu (1-31, domyślnie: 1)')
    parser.add_argument('--interval', type=int, default=10,
                       help='Interwał pobierania danych w sekundach (domyślnie: 10)')
    parser.add_argument('--time-alert', type=int, default=30,
                       help='Alert czasowy w minutach (domyślnie: 30)')
    parser.add_argument('--inactivity-alert', type=int, default=10,
                       help='Alert bezczynności w minutach (domyślnie: 10)')
    parser.add_argument('--sessions', type=int, default=50,
                       help='Maksymalne sesje miesięczne (domyślnie: 50)')
    parser.add_argument('--timezone', type=str, default="Europe/Warsaw",
                       help='Strefa czasowa (domyślnie: Europe/Warsaw)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not 1 <= args.start_day <= 31:
        print("❌ Dzień startu abonamentu musi być między 1 a 31")
        return 1
    
    if args.interval < 1:
        print("❌ Interwał musi być większy niż 0 sekund")
        return 1
    
    # Create configuration
    config = ConfigData(
        ccusage_fetch_interval_seconds=args.interval,
        time_remaining_alert_minutes=args.time_alert,
        inactivity_alert_minutes=args.inactivity_alert,
        billing_start_day=args.start_day,
        total_monthly_sessions=args.sessions,
        local_timezone=args.timezone
    )
    
    print("=== CLAUDE MONITORING DAEMON ===")
    print(f"📅 Dzień startu abonamentu: {config.billing_start_day}")
    print(f"⏱️  Interwał pobierania: {config.ccusage_fetch_interval_seconds} sekund")
    print(f"⏰ Alert czasowy: {config.time_remaining_alert_minutes} minut")
    print(f"😴 Alert bezczynności: {config.inactivity_alert_minutes} minut")
    print(f"📊 Maksymalne sesje: {config.total_monthly_sessions}")
    print(f"🌍 Strefa czasowa: {config.local_timezone}")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Terminate
    
    # Create and start daemon
    global daemon_instance
    daemon_instance = ClaudeDaemon(config)
    
    try:
        print(f"\n🚀 Uruchamiam demona...")
        daemon_instance.start()
        print("✅ Demon uruchomiony pomyślnie")
        
        print(f"\n📁 Dane zapisywane w:")
        print(f"   ~/.config/claude-monitor/monitor_data.json")
        print(f"   ~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/ (jeśli dostępne)")
        
        print(f"\n💡 Aby zatrzymać demona naciśnij Ctrl+C")
        print(f"📊 Monitorowanie w toku...")
        
        # Keep daemon running
        while daemon_instance.is_running:
            time.sleep(1)
        
    except KeyboardInterrupt:
        print(f"\n🛑 Otrzymano Ctrl+C, zatrzymuję demona...")
    except Exception as e:
        print(f"\n❌ Błąd demona: {e}")
    finally:
        if daemon_instance and daemon_instance.is_running:
            daemon_instance.stop()
        print("✅ Demon zatrzymany")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())