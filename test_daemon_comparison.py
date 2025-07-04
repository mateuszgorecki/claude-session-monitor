#!/usr/bin/env python3
"""
Test script to compare daemon results with original claude_monitor.py
"""
import sys
import os
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from daemon.claude_daemon import ClaudeDaemon
from shared.data_models import ConfigData, MonitoringData
from shared.file_manager import DataFileManager


def load_monitoring_data_from_file() -> dict:
    """Load monitoring data from daemon's output file."""
    data_manager = DataFileManager()
    try:
        return data_manager.read_data()
    except Exception as e:
        print(f"❌ Nie można odczytać danych z pliku demona: {e}")
        return None


def run_original_monitor(billing_start_day: int = 1) -> dict:
    """Run original claude_monitor.py and capture its data calculation logic."""
    import subprocess
    import tempfile
    
    # Run original monitor with --start-day parameter
    try:
        # Since the original doesn't output JSON, we'll need to extract the logic differently
        # For now, let's just capture the key parameters it would use
        return {
            "billing_start_day": billing_start_day,
            "test_type": "original_monitor",
            "note": "Original monitor doesn't export data - need to check console output manually"
        }
    except Exception as e:
        print(f"❌ Błąd uruchamiania oryginalnego monitora: {e}")
        return None


def compare_results(daemon_data: dict, original_data: dict) -> bool:
    """Compare results between daemon and original monitor."""
    print("\n=== PORÓWNANIE WYNIKÓW ===")
    
    if not daemon_data:
        print("❌ Brak danych z demona")
        return False
    
    if not original_data:
        print("❌ Brak danych z oryginalnego monitora")
        return False
    
    # Analyze daemon data
    print("\n📊 DANE Z DEMONA:")
    if 'current_sessions' in daemon_data:
        sessions = daemon_data['current_sessions']
        print(f"   Liczba sesji: {len(sessions)}")
        if sessions:
            total_cost = sum(s.get('cost_usd', 0) for s in sessions)
            total_tokens = sum(s.get('total_tokens', 0) for s in sessions)
            print(f"   Całkowity koszt: ${total_cost:.6f}")
            print(f"   Całkowite tokeny: {total_tokens:,}")
            
            # Show session details
            print("\n   📋 SZCZEGÓŁY SESJI:")
            for i, session in enumerate(sessions[:3]):  # Show first 3
                print(f"     {i+1}. ID: {session.get('session_id', 'N/A')[:20]}...")
                print(f"        Tokeny: {session.get('total_tokens', 0):,}")
                print(f"        Koszt: ${session.get('cost_usd', 0):.6f}")
                print(f"        Aktywna: {session.get('is_active', False)}")
            
            if len(sessions) > 3:
                print(f"     ... i {len(sessions) - 3} więcej sesji")
    
    if 'total_cost_this_month' in daemon_data:
        print(f"   Koszt miesięczny: ${daemon_data['total_cost_this_month']:.6f}")
    
    if 'max_tokens_per_session' in daemon_data:
        print(f"   Max tokeny na sesję: {daemon_data['max_tokens_per_session']:,}")
    
    if 'last_update' in daemon_data:
        print(f"   Ostatnia aktualizacja: {daemon_data['last_update']}")
    
    print("\n📊 DANE Z ORYGINALNEGO MONITORA:")
    print(f"   {original_data}")
    
    return True


def test_daemon_data_collection(billing_start_day: int = 1, duration: int = 30):
    """Test daemon data collection for specified duration."""
    print(f"\n=== TEST DEMONA (billing_start_day={billing_start_day}) ===")
    
    # Create configuration with custom billing start day
    config = ConfigData(
        ccusage_fetch_interval_seconds=10,  # Fetch every 10 seconds
        time_remaining_alert_minutes=30,
        inactivity_alert_minutes=10,
        billing_start_day=billing_start_day,
        total_monthly_sessions=50
    )
    
    print(f"📝 Konfiguracja demona:")
    print(f"   Interwał pobierania: {config.ccusage_fetch_interval_seconds}s")
    print(f"   Dzień startu abonamentu: {config.billing_start_day}")
    print(f"   Alerty czasowe: {config.time_remaining_alert_minutes} min")
    
    # Start daemon
    print(f"\n🚀 Uruchamiam demona na {duration} sekund...")
    
    daemon = ClaudeDaemon(config)
    
    try:
        daemon.start()
        print("✓ Demon uruchomiony")
        
        # Let daemon collect data
        for i in range(duration):
            if i % 5 == 0:  # Progress update every 5 seconds
                print(f"   ⏳ Zbieranie danych... {i}/{duration}s")
            time.sleep(1)
        
        # Stop daemon
        daemon.stop()
        print("✓ Demon zatrzymany")
        
        # Give a moment for final data write
        time.sleep(2)
        
        # Load and return collected data
        data = load_monitoring_data_from_file()
        if data:
            print("✓ Dane pomyślnie pobrane z pliku")
            # Show summary of collected data
            if 'current_sessions' in data:
                sessions = data['current_sessions']
                print(f"📊 Zebrano {len(sessions)} sesji, koszt: ${data.get('total_cost_this_month', 0):.4f}")
        
        return data
        
    except Exception as e:
        print(f"❌ Błąd podczas pracy demona: {e}")
        daemon.stop()
        return None


def main():
    """Main test function with command line options."""
    parser = argparse.ArgumentParser(description='Test daemon and compare with original monitor')
    parser.add_argument('--start-day', type=int, default=1, 
                       help='Billing start day (1-31)')
    parser.add_argument('--duration', type=int, default=30,
                       help='Test duration in seconds (default: 30)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare results with original monitor')
    
    args = parser.parse_args()
    
    print("=== PORÓWNANIE DEMONA Z ORYGINALNYM CLAUDE_MONITOR ===")
    print(f"Dzień startu abonamentu: {args.start_day}")
    print(f"Czas testowania: {args.duration} sekund")
    
    # Test daemon
    daemon_data = test_daemon_data_collection(args.start_day, args.duration)
    
    if args.compare:
        # Test original monitor (placeholder)
        print(f"\n=== TEST ORYGINALNEGO MONITORA ===")
        print("💡 Aby porównać z oryginalnym monitorem:")
        print(f"   1. Uruchom: python3 claude_monitor.py --start-day {args.start_day}")
        print(f"   2. Porównaj wyniki wizualnie z danymi demona powyżej")
        print(f"   3. Sprawdź czy liczba sesji, koszty i tokeny są podobne")
        
        original_data = run_original_monitor(args.start_day)
        
        # Compare results
        compare_results(daemon_data, original_data)
    
    if daemon_data:
        print("\n✅ TEST ZAKOŃCZONY POMYŚLNIE")
        print(f"\n📁 Dane zapisane w: ~/.config/claude-monitor/monitor_data.json")
        print(f"📁 Kopia iCloud: ~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/")
        
        # Show file locations
        data_manager = DataFileManager()
        print(f"\n📍 Lokalizacje plików:")
        print(f"   Główny plik: {data_manager.file_path}")
        if hasattr(data_manager, 'icloud_sync_path') and data_manager.icloud_sync_path:
            print(f"   Kopia iCloud: {data_manager.icloud_sync_path}")
    else:
        print("\n❌ TEST NIEUDANY - brak danych z demona")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())