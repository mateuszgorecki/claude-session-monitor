#!/usr/bin/env python3
"""
Tests for CcusageExecutor unified execution strategies.
"""
import unittest
import json
import subprocess
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add src to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from daemon.ccusage_executor import CcusageExecutor, WrapperScriptStrategy, DirectSubprocessStrategy, OSSystemStrategy


class TestCcusageExecutor(unittest.TestCase):
    """Test CcusageExecutor unified execution strategies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.executor = CcusageExecutor()
    
    def test_default_strategy_is_wrapper_script(self):
        """Test that CcusageExecutor uses WrapperScriptStrategy by default."""
        self.assertIsInstance(self.executor.strategy, WrapperScriptStrategy)
    
    def test_execute_returns_structured_data(self):
        """Test that execute() returns structured data with blocks."""
        # Mock the wrapper script to return valid JSON
        mock_data = {
            "blocks": [
                {
                    "id": "test-session-1",
                    "startTime": "2024-01-01T10:00:00Z",
                    "endTime": "2024-01-01T11:00:00Z",
                    "totalTokens": 1000,
                    "tokenCounts": {
                        "inputTokens": 500,
                        "outputTokens": 500
                    },
                    "costUSD": 0.05,
                    "isActive": False
                }
            ]
        }
        
        with patch.object(self.executor.strategy, 'execute', return_value=mock_data):
            result = self.executor.execute()
            
            self.assertIn("blocks", result)
            self.assertIsInstance(result["blocks"], list)
            self.assertEqual(len(result["blocks"]), 1)
            
            block = result["blocks"][0]
            self.assertEqual(block["id"], "test-session-1")
            self.assertEqual(block["totalTokens"], 1000)
    
    def test_execute_with_since_date(self):
        """Test that execute() properly passes since_date parameter."""
        mock_data = {"blocks": []}
        
        with patch.object(self.executor.strategy, 'execute', return_value=mock_data) as mock_execute:
            self.executor.execute(since_date="2024-01-01")
            
            # Verify strategy was called with since_date
            mock_execute.assert_called_once_with(since_date="2024-01-01")
    
    def test_execute_handles_strategy_failure(self):
        """Test that execute() handles strategy failures gracefully."""
        # Disable fallback for this test
        self.executor.enable_fallback = False
        
        with patch.object(self.executor.strategy, 'execute', side_effect=Exception("Strategy failed")):
            result = self.executor.execute()
            
            # Should return empty blocks on failure
            self.assertEqual(result, {"blocks": []})
    
    def test_fallback_mechanism(self):
        """Test that fallback mechanism tries alternative strategies.""" 
        # Test that _execute_with_fallback is called when primary strategy fails
        with patch.object(self.executor.strategy, 'execute', return_value={"blocks": []}):
            with patch.object(self.executor, '_execute_with_fallback') as mock_fallback:
                mock_fallback.return_value = {"blocks": [{"id": "fallback-test"}]}
                
                result = self.executor.execute()
                
                # Should call fallback mechanism
                mock_fallback.assert_called_once()
                
                # Should get result from fallback
                self.assertIn("blocks", result)
                self.assertEqual(result["blocks"][0]["id"], "fallback-test")
    
    def test_fallback_disabled(self):
        """Test that fallback can be disabled."""
        executor = CcusageExecutor(enable_fallback=False)
        
        with patch.object(executor.strategy, 'execute', return_value={"blocks": []}):
            result = executor.execute()
            
            # Should return empty blocks without fallback
            self.assertEqual(result, {"blocks": []})
    
    def test_strategy_timeout_handling(self):
        """Test that strategies handle timeout properly."""
        with patch.object(self.executor.strategy, 'execute', side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = self.executor.execute()
            
            # Should handle timeout gracefully (may use fallback)
            self.assertIn("blocks", result)
    
    def test_get_available_strategies(self):
        """Test that get_available_strategies returns correct strategy names."""
        strategies = self.executor.get_available_strategies()
        
        expected_strategies = ['WrapperScriptStrategy', 'DirectSubprocessStrategy', 'OSSystemStrategy']
        self.assertEqual(strategies, expected_strategies)


class TestWrapperScriptStrategy(unittest.TestCase):
    """Test WrapperScriptStrategy implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategy = WrapperScriptStrategy()
    
    def test_wrapper_script_strategy_execute(self):
        """Test that WrapperScriptStrategy executes wrapper script correctly."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"blocks": [{"id": "test", "totalTokens": 500}]}'
        
        with patch('subprocess.run', return_value=mock_result):
            result = self.strategy.execute()
            
            self.assertIn("blocks", result)
            self.assertEqual(len(result["blocks"]), 1)
            self.assertEqual(result["blocks"][0]["id"], "test")
    
    def test_wrapper_script_strategy_with_since_date(self):
        """Test that WrapperScriptStrategy handles since_date parameter."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"blocks": []}'
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            self.strategy.execute(since_date="2024-01-01")
            
            # Verify subprocess.run was called with since_date argument
            args, kwargs = mock_run.call_args
            command = args[0]
            self.assertIn("-s", command)
            self.assertIn("2024-01-01", command)
    
    def test_wrapper_script_strategy_handles_failure(self):
        """Test that WrapperScriptStrategy handles execution failures."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"
        
        with patch('subprocess.run', return_value=mock_result):
            result = self.strategy.execute()
            
            # Should return empty blocks on failure
            self.assertEqual(result, {"blocks": []})


class TestDirectSubprocessStrategy(unittest.TestCase):
    """Test DirectSubprocessStrategy implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategy = DirectSubprocessStrategy()
    
    def test_direct_subprocess_strategy_execute(self):
        """Test that DirectSubprocessStrategy executes subprocess correctly."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"blocks": [{"id": "direct-test", "totalTokens": 750}]}'
        
        with patch('subprocess.run', return_value=mock_result):
            with patch.object(self.strategy, '_find_node_executable', return_value='/usr/bin/node'):
                with patch.object(self.strategy, '_find_ccusage_script', return_value='/path/to/ccusage'):
                    result = self.strategy.execute()
                    
                    self.assertIn("blocks", result)
                    self.assertEqual(len(result["blocks"]), 1)
                    self.assertEqual(result["blocks"][0]["id"], "direct-test")
    
    def test_direct_subprocess_strategy_missing_node(self):
        """Test that DirectSubprocessStrategy handles missing Node.js."""
        with patch.object(self.strategy, '_find_node_executable', return_value=None):
            result = self.strategy.execute()
            
            # Should return empty blocks when Node.js not found
            self.assertEqual(result, {"blocks": []})
    
    def test_direct_subprocess_strategy_missing_ccusage(self):
        """Test that DirectSubprocessStrategy handles missing ccusage script."""
        with patch.object(self.strategy, '_find_node_executable', return_value='/usr/bin/node'):
            with patch.object(self.strategy, '_find_ccusage_script', return_value=None):
                result = self.strategy.execute()
                
                # Should return empty blocks when ccusage script not found
                self.assertEqual(result, {"blocks": []})


class TestOSSystemStrategy(unittest.TestCase):
    """Test OSSystemStrategy implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategy = OSSystemStrategy()
    
    def test_os_system_strategy_execute(self):
        """Test that OSSystemStrategy executes os.system correctly."""
        mock_data = {"blocks": [{"id": "system-test", "totalTokens": 1250}]}
        
        with patch('os.system', return_value=0):  # Success exit code
            with patch.object(self.strategy, '_find_node_executable', return_value='/usr/bin/node'):
                with patch.object(self.strategy, '_find_ccusage_script', return_value='/path/to/ccusage'):
                    with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
                        with patch('tempfile.NamedTemporaryFile') as mock_temp:
                            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.json'
                            
                            result = self.strategy.execute()
                            
                            self.assertIn("blocks", result)
                            self.assertEqual(len(result["blocks"]), 1)
                            self.assertEqual(result["blocks"][0]["id"], "system-test")
    
    def test_os_system_strategy_command_failure(self):
        """Test that OSSystemStrategy handles command failures."""
        with patch('os.system', return_value=1):  # Failure exit code
            with patch.object(self.strategy, '_find_node_executable', return_value='/usr/bin/node'):
                with patch.object(self.strategy, '_find_ccusage_script', return_value='/path/to/ccusage'):
                    result = self.strategy.execute()
                    
                    # Should return empty blocks on command failure
                    self.assertEqual(result, {"blocks": []})
    
    def test_os_system_strategy_missing_dependencies(self):
        """Test that OSSystemStrategy handles missing dependencies."""
        with patch.object(self.strategy, '_find_node_executable', return_value=None):
            result = self.strategy.execute()
            
            # Should return empty blocks when dependencies missing
            self.assertEqual(result, {"blocks": []})


if __name__ == '__main__':
    unittest.main()