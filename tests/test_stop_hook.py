import unittest
import tempfile
import os
import json
from unittest.mock import patch, Mock
from io import StringIO

# Import the module we're testing (will fail initially - RED phase)
from hooks.stop_hook import main, parse_stop_data, create_stop_event, determine_stop_type


class TestStopHook(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'test_stop.log')
        
    def tearDown(self):
        # Clean up temp files
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_parse_stop_data_valid_json(self):
        """Test parsing valid stop JSON from stdin"""
        stop_json = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "stop_hook_active": False
        }
        
        result = parse_stop_data(json.dumps(stop_json))
        
        self.assertEqual(result['session_id'], 'abc123')
        self.assertEqual(result['transcript_path'], '/path/to/conversation.jsonl')
        self.assertEqual(result['stop_hook_active'], False)
    
    def test_parse_stop_data_invalid_json(self):
        """Test handling of invalid JSON input"""
        invalid_json = "{ invalid json"
        
        result = parse_stop_data(invalid_json)
        
        self.assertIsNone(result)
    
    def test_determine_stop_type_normal_stop(self):
        """Test determining stop type for normal stop"""
        stop_data = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "stop_hook_active": False
        }
        
        stop_type = determine_stop_type(stop_data)
        
        self.assertEqual(stop_type, 'stop')
    
    def test_determine_stop_type_subagent_stop(self):
        """Test determining stop type for subagent stop"""
        stop_data = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "stop_hook_active": True
        }
        
        stop_type = determine_stop_type(stop_data)
        
        self.assertEqual(stop_type, 'subagent_stop')
    
    def test_create_stop_event_normal_stop(self):
        """Test creating stop event for normal stop"""
        stop_data = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "stop_hook_active": False
        }
        
        event = create_stop_event(stop_data)
        
        self.assertEqual(event['session_id'], 'abc123')
        self.assertEqual(event['event_type'], 'stop')
        self.assertEqual(event['data']['stop_type'], 'stop')
        self.assertEqual(event['data']['transcript_path'], '/path/to/conversation.jsonl')
        self.assertEqual(event['data']['stop_hook_active'], False)
    
    def test_create_stop_event_subagent_stop(self):
        """Test creating stop event for subagent stop"""
        stop_data = {
            "session_id": "abc123",
            "transcript_path": "/path/to/conversation.jsonl",
            "stop_hook_active": True
        }
        
        event = create_stop_event(stop_data)
        
        self.assertEqual(event['session_id'], 'abc123')
        self.assertEqual(event['event_type'], 'stop')
        self.assertEqual(event['data']['stop_type'], 'subagent_stop')
        self.assertEqual(event['data']['stop_hook_active'], True)
    
    def test_create_stop_event_handles_missing_session_id(self):
        """Test creating stop event when session_id is missing"""
        stop_data = {
            "transcript_path": "/path/to/conversation.jsonl",
            "stop_hook_active": False
        }
        
        event = create_stop_event(stop_data)
        
        self.assertEqual(event['session_id'], 'unknown')
        self.assertEqual(event['event_type'], 'stop')
    
    @patch('hooks.stop_hook.HookLogger')
    @patch('sys.stdin')
    def test_main_function_processes_stdin(self, mock_stdin, mock_hook_logger):
        """Test main function reads from stdin and logs event"""
        # Setup mock stdin
        stop_json = {
            "session_id": "test123",
            "transcript_path": "/path/to/test.jsonl",
            "stop_hook_active": False
        }
        mock_stdin.read.return_value = json.dumps(stop_json)
        
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
        self.assertEqual(logged_event['event_type'], 'stop')
        self.assertEqual(logged_event['data']['stop_type'], 'stop')
    
    @patch('hooks.stop_hook.HookLogger')
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
    
    @patch('hooks.stop_hook.HookLogger')
    @patch('sys.stdin')
    def test_main_function_uses_default_log_file(self, mock_stdin, mock_hook_logger):
        """Test main function uses default log file when env var not set"""
        # Setup mock stdin
        stop_json = {
            "session_id": "test123",
            "stop_hook_active": False
        }
        mock_stdin.read.return_value = json.dumps(stop_json)
        
        # Setup mock logger
        mock_logger_instance = Mock()
        mock_hook_logger.return_value = mock_logger_instance
        
        # Clear environment variable
        with patch.dict(os.environ, {}, clear=True):
            main()
        
        # Verify HookLogger was initialized with default path
        mock_hook_logger.assert_called_once()
        args = mock_hook_logger.call_args[0]
        self.assertIn('claude_activity.log', args[0])


if __name__ == '__main__':
    unittest.main()