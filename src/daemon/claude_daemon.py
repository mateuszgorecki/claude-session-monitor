#!/usr/bin/env python3
"""
Core daemon implementation for Claude session monitor.
Provides background monitoring service that continuously tracks Claude API usage.
"""
import threading
import time
import signal
import logging
from typing import Optional, Callable
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.data_models import ConfigData, MonitoringData
from shared.constants import DEFAULT_CCUSAGE_FETCH_INTERVAL_SECONDS
from .data_collector import DataCollector


class ClaudeDaemon:
    """
    Core daemon class for background Claude API monitoring.
    
    Provides:
    - Daemon lifecycle management (start/stop)
    - Signal handling for graceful shutdown
    - Threaded monitoring loop with configurable intervals
    - Integration with shared infrastructure
    """
    
    def __init__(self, config: ConfigData):
        """
        Initialize the daemon with configuration.
        
        Args:
            config: Configuration data containing monitoring settings
        """
        self.config = config
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Set up logging
        self._setup_logging()
        
        # Register signal handlers
        self._setup_signal_handlers()
        
        # Data collection component
        self.data_collector = DataCollector(config)
        
        self.logger.info(f"Daemon initialized with fetch interval: {config.ccusage_fetch_interval_seconds}s")
    
    def _setup_logging(self):
        """Set up logging for the daemon."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def start(self):
        """
        Start the daemon in a background thread.
        
        This method is idempotent - calling it multiple times has no effect
        if the daemon is already running.
        """
        with self._lock:
            if self.is_running:
                self.logger.warning("Daemon is already running")
                return
            
            self.logger.info("Starting daemon...")
            self.is_running = True
            self._stop_event.clear()
            
            # Start the monitoring thread
            self._thread = threading.Thread(target=self._main_loop, daemon=True)
            self._thread.start()
            
            self.logger.info("Daemon started successfully")
    
    def stop(self):
        """
        Stop the daemon and wait for the thread to finish.
        
        This method is idempotent - calling it multiple times is safe.
        """
        with self._lock:
            if not self.is_running:
                return
            
            self.logger.info("Stopping daemon...")
            self.is_running = False
            self._stop_event.set()
        
        # Wait for the thread to finish (outside the lock)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                self.logger.warning("Daemon thread did not stop within timeout")
            else:
                self.logger.info("Daemon stopped successfully")
    
    def _main_loop(self):
        """
        Main monitoring loop that runs in the background thread.
        
        Continuously monitors Claude API usage at configured intervals,
        with proper error handling to ensure daemon stability.
        """
        self.logger.info("Daemon main loop started")
        
        last_collection_time = 0
        collection_interval = self.config.ccusage_fetch_interval_seconds
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check if it's time to collect data
                if current_time - last_collection_time >= collection_interval:
                    self._collect_data()
                    last_collection_time = current_time
                
                # Sleep for a short interval to prevent busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in daemon main loop: {e}")
                # Continue running despite errors
                time.sleep(1)
        
        self.logger.info("Daemon main loop stopped")
    
    def _collect_data(self):
        """
        Collect monitoring data using DataCollector.
        """
        try:
            self.logger.debug("Collecting monitoring data...")
            monitoring_data = self.data_collector.collect_data()
            
            # Log summary of collected data
            sessions_count = len(monitoring_data.current_sessions)
            total_cost = monitoring_data.total_cost_this_month
            self.logger.info(f"Collected {sessions_count} sessions, total cost: ${total_cost:.4f}")
            
            # TODO: In Task 2.3, this data will be saved to file using FileManager
            
        except RuntimeError as e:
            # Log collection failures but don't stop the daemon
            error_status = self.data_collector.get_error_status()
            if error_status and error_status.consecutive_failures > 5:
                self.logger.warning(f"Data collection has failed {error_status.consecutive_failures} consecutive times")
            else:
                self.logger.error(f"Data collection failed: {e}")
            
            # In Task 2.4, notification manager will handle alerts for repeated failures
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()