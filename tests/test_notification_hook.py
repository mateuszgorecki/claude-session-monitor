import unittest
import tempfile
import os
import json
from unittest.mock import patch, Mock
from io import StringIO

# Import the module we're testing (will fail initially - RED phase)
from hooks.notification_hook import main, parse_notification_data, create_activity_event


class TestNotificationHook(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'test_notification.log')
        
    def tearDown(self):
        # Clean up temp files
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_parse_notification_data_valid_json(self):
        """Test parsing valid notification JSON from stdin"""
        notification_json = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "message": "Task completed successfully",
            "title": "Claude Code"
        }
        
        result = parse_notification_data(json.dumps(notification_json))
        
        self.assertEqual(result['session_id'], 'abc123')
        self.assertEqual(result['transcript_path'], '/path/to/conversation.jsonl')
        self.assertEqual(result['message'], 'Task completed successfully')
        self.assertEqual(result['title'], 'Claude Code')
    
    def test_parse_notification_data_invalid_json(self):
        """Test handling of invalid JSON input"""
        invalid_json = "{ invalid json"
        
        result = parse_notification_data(invalid_json)
        
        self.assertIsNone(result)
    
    def test_create_activity_event_from_notification(self):
        """Test creating activity event from notification data"""
        notification_data = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "message": "Waiting for user input",
            "title": "Claude Code"
        }
        
        event = create_activity_event(notification_data)
        
        self.assertEqual(event['session_id'], 'abc123')
        self.assertEqual(event['event_type'], 'notification')
        self.assertEqual(event['data']['message'], 'Waiting for user input')
        self.assertEqual(event['data']['transcript_path'], '/path/to/conversation.jsonl')
        self.assertEqual(event['data']['title'], 'Claude Code')
    
    def test_create_activity_event_handles_missing_session_id(self):
        """Test creating activity event when session_id is missing"""
        notification_data = {
            "transcript_path": "/path/to/conversation.jsonl",
            "message": "Some message",
            "title": "Claude Code"
        }
        
        event = create_activity_event(notification_data)
        
        self.assertEqual(event['session_id'], 'unknown')
        self.assertEqual(event['event_type'], 'notification')
    
    @patch('hooks.notification_hook.HookLogger')
    @patch('sys.stdin')
    def test_main_function_processes_stdin(self, mock_stdin, mock_hook_logger):
        """Test main function reads from stdin and logs event"""
        # Setup mock stdin
        notification_json = {
            "session_id": "test123",
            "transcript_path": "/path/to/test.jsonl",
            "message": "Test notification",
            "title": "Claude Code"
        }
        mock_stdin.read.return_value = json.dumps(notification_json)
        
        # Setup mock logger
        mock_logger_instance = Mock()
        mock_hook_logger.return_value = mock_logger_instance
        
        # Set environment variable for log file
        with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file}):
            main()
        
        # Verify logger was called with correct event
        mock_logger_instance.log_event.assert_called_once()
        logged_event = mock_logger_instance.log_event.call_args[0][0]
        
        self.assertEqual(logged_event['session_id'], 'test123')
        self.assertEqual(logged_event['event_type'], 'notification')
        self.assertEqual(logged_event['data']['message'], 'Test notification')
    
    @patch('hooks.notification_hook.HookLogger')
    @patch('sys.stdin')
    def test_main_function_handles_invalid_input(self, mock_stdin, mock_hook_logger):
        """Test main function handles invalid JSON input gracefully"""
        # Setup mock stdin with invalid JSON
        mock_stdin.read.return_value = "invalid json"
        
        # Setup mock logger
        mock_logger_instance = Mock()
        mock_hook_logger.return_value = mock_logger_instance
        
        # Set environment variable for log file
        with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file}):
            main()
        
        # Verify logger was not called due to invalid input
        mock_logger_instance.log_event.assert_not_called()
    
    @patch('hooks.notification_hook.HookLogger')
    @patch('sys.stdin')
    def test_main_function_uses_default_log_file(self, mock_stdin, mock_hook_logger):
        """Test main function uses default log file when env var not set"""
        # Setup mock stdin
        notification_json = {
            "session_id": "test123",
            "message": "Test notification",
            "title": "Claude Code"
        }
        mock_stdin.read.return_value = json.dumps(notification_json)
        
        # Setup mock logger
        mock_logger_instance = Mock()
        mock_hook_logger.return_value = mock_logger_instance
        
        # Clear environment variable
        with patch.dict(os.environ, {}, clear=True):
            main()
        
        # Verify HookLogger was initialized with default path
        mock_hook_logger.assert_called_once()
        args = mock_hook_logger.call_args[0]
        self.assertIn('claude_activity_', args[0])
        self.assertTrue(args[0].endswith('.log'))


if __name__ == '__main__':
    unittest.main()