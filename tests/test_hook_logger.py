import unittest
import tempfile
import os
import json
from datetime import datetime
from unittest.mock import patch
import time

# Import the class we're testing (will fail initially - RED phase)
from hooks.hook_utils import HookLogger


class TestHookLogger(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'test_hook.log')
        self.hook_logger = HookLogger(self.log_file)
    
    def tearDown(self):
        # Clean up temp files
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        os.rmdir(self.temp_dir)
    
    def test_log_event_creates_file_and_writes_json(self):
        """Test that log_event creates file and writes valid JSON"""
        event_data = {
            'session_id': 'test-session-123',
            'event_type': 'notification',
            'data': {'message': 'User input received'}
        }
        
        self.hook_logger.log_event(event_data)
        
        # Check file was created
        self.assertTrue(os.path.exists(self.log_file))
        
        # Check JSON content
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            
            logged_event = json.loads(lines[0].strip())
            self.assertEqual(logged_event['session_id'], 'test-session-123')
            self.assertEqual(logged_event['event_type'], 'notification')
            self.assertEqual(logged_event['data']['message'], 'User input received')
            self.assertIn('timestamp', logged_event)
    
    def test_log_event_appends_multiple_events(self):
        """Test that multiple events are properly appended"""
        event1 = {'session_id': 'session-1', 'event_type': 'start', 'data': {}}
        event2 = {'session_id': 'session-2', 'event_type': 'stop', 'data': {}}
        
        self.hook_logger.log_event(event1)
        self.hook_logger.log_event(event2)
        
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            
            logged_event1 = json.loads(lines[0].strip())
            logged_event2 = json.loads(lines[1].strip())
            
            self.assertEqual(logged_event1['session_id'], 'session-1')
            self.assertEqual(logged_event2['session_id'], 'session-2')
    
    def test_log_event_handles_missing_directory(self):
        """Test that log_event creates directory if it doesn't exist"""
        missing_dir = os.path.join(self.temp_dir, 'missing')
        missing_log_file = os.path.join(missing_dir, 'test.log')
        
        logger = HookLogger(missing_log_file)
        event_data = {'session_id': 'test', 'event_type': 'test', 'data': {}}
        
        logger.log_event(event_data)
        
        self.assertTrue(os.path.exists(missing_log_file))
        
        # Cleanup
        os.remove(missing_log_file)
        os.rmdir(missing_dir)
    
    def test_log_event_thread_safety(self):
        """Test that concurrent log_event calls don't corrupt the file"""
        import threading
        
        def log_events():
            for i in range(10):
                event_data = {
                    'session_id': f'session-{threading.current_thread().name}-{i}',
                    'event_type': 'concurrent_test',
                    'data': {'thread': threading.current_thread().name, 'iteration': i}
                }
                self.hook_logger.log_event(event_data)
                time.sleep(0.001)  # Small delay to increase chance of race condition
        
        threads = []
        for i in range(3):
            t = threading.Thread(target=log_events, name=f'Thread-{i}')
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Check that all events were logged properly
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 30)  # 3 threads * 10 events each
            
            # Check that all lines are valid JSON
            for line in lines:
                try:
                    json.loads(line.strip())
                except json.JSONDecodeError:
                    self.fail(f"Invalid JSON line: {line}")


if __name__ == '__main__':
    unittest.main()