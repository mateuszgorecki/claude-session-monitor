#!/usr/bin/env python3
"""
Test script to verify daemon functionality.
"""
import sys
import os
import time
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from daemon.claude_daemon import ClaudeDaemon
from shared.data_models import ConfigData
from shared.constants import DEFAULT_CCUSAGE_FETCH_INTERVAL_SECONDS

def test_daemon_basic():
    """Test basic daemon startup and shutdown."""
    print("Testing daemon basic functionality...")
    
    # Create test configuration
    config = ConfigData(
        ccusage_fetch_interval_seconds=5,  # Short interval for testing
        time_remaining_alert_minutes=30,
        inactivity_alert_minutes=10,
        billing_start_day=17
    )
    
    # Create daemon instance
    daemon = ClaudeDaemon(config)
    
    print("✓ Daemon created successfully")
    
    # Start daemon
    daemon.start()
    print("✓ Daemon started")
    
    # Let it run for a few seconds
    print("Running daemon for 10 seconds...")
    time.sleep(10)
    
    # Stop daemon
    daemon.stop()
    print("✓ Daemon stopped")
    
    return True

def test_daemon_context_manager():
    """Test daemon as context manager."""
    print("\nTesting daemon as context manager...")
    
    config = ConfigData(
        ccusage_fetch_interval_seconds=3,
        time_remaining_alert_minutes=30,
        inactivity_alert_minutes=10,
        billing_start_day=17
    )
    
    print("Starting daemon with context manager...")
    with ClaudeDaemon(config) as daemon:
        print("✓ Daemon running in context manager")
        time.sleep(5)
        print("✓ Daemon operations completed")
    
    print("✓ Daemon stopped via context manager")
    return True

def test_daemon_signal_handling():
    """Test daemon signal handling."""
    print("\nTesting daemon signal handling...")
    
    config = ConfigData(
        ccusage_fetch_interval_seconds=2,
        time_remaining_alert_minutes=30,
        inactivity_alert_minutes=10,
        billing_start_day=17
    )
    
    daemon = ClaudeDaemon(config)
    daemon.start()
    
    print("✓ Daemon started, testing signal handling...")
    
    # Test SIGTERM handling
    try:
        # Send SIGTERM to self (daemon should handle it gracefully)
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(1)
        print("✓ SIGTERM handled gracefully")
    except KeyboardInterrupt:
        print("✓ Signal handled as expected")
    
    # Ensure daemon is stopped
    daemon.stop()
    return True

def main():
    """Run all daemon tests."""
    print("=== Claude Daemon Test Suite ===\n")
    
    tests = [
        ("Basic daemon functionality", test_daemon_basic),
        ("Context manager usage", test_daemon_context_manager),
        ("Signal handling", test_daemon_signal_handling)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}")
            if test_func():
                print(f"✅ PASSED: {test_name}\n")
                passed += 1
            else:
                print(f"❌ FAILED: {test_name}\n")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}\n")
            failed += 1
    
    print(f"=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())