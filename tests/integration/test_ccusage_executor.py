#!/usr/bin/env python3
"""
Integration tests for CcusageExecutor - unified ccusage execution strategies.
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the module we're testing
from src.daemon.ccusage_executor import CcusageExecutor, ExecutionStrategy, WrapperScriptStrategy


class TestCcusageExecutor(unittest.TestCase):
    """Test the unified ccusage execution system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.executor = CcusageExecutor()
        self.sample_ccusage_data = {
            "blocks": [
                {
                    "id": "test-session-1",
                    "startTime": "2024-01-01T10:00:00Z",
                    "endTime": "2024-01-01T11:00:00Z",
                    "tokenCounts": {
                        "inputTokens": 1000,
                        "outputTokens": 500
                    },
                    "costUSD": 0.05
                }
            ]
        }
    
    def test_executor_returns_valid_data_with_wrapper_strategy(self):
        """Test that CcusageExecutor returns valid data using WrapperScriptStrategy."""
        # Mock the strategy to return sample data
        with patch.object(self.executor.strategy, 'execute') as mock_execute:
            mock_execute.return_value = self.sample_ccusage_data
            
            result = self.executor.execute()
            
            # Verify the result structure
            self.assertIsInstance(result, dict)
            self.assertIn("blocks", result)
            self.assertIsInstance(result["blocks"], list)
            
            # Verify the result matches expected data
            self.assertEqual(result, self.sample_ccusage_data)
        
    def test_executor_fallback_mechanism(self):
        """Test that CcusageExecutor falls back to alternative strategies when primary fails."""
        # Mock the primary strategy to fail
        with patch.object(self.executor.strategy, 'execute') as mock_primary:
            mock_primary.side_effect = Exception("Primary strategy failed")
            
            # Mock the fallback strategies
            with patch.object(self.executor, 'fallback_strategies') as mock_fallback_classes:
                # Create a mock strategy class that returns our sample data
                mock_strategy_class = MagicMock()
                mock_strategy_class.__name__ = "MockStrategy"
                mock_strategy_instance = MagicMock()
                mock_strategy_instance.execute.return_value = self.sample_ccusage_data
                mock_strategy_class.return_value = mock_strategy_instance
                
                # Set up fallback strategies (skip the first one which would be the current strategy)
                mock_fallback_classes.__iter__.return_value = [mock_strategy_class]
                
                result = self.executor.execute()
                
                # Should have fallen back to alternative strategy
                self.assertEqual(result, self.sample_ccusage_data)
    
    def test_executor_with_since_date_parameter(self):
        """Test that CcusageExecutor properly passes since_date to strategies."""
        since_date = "20240101"
        
        with patch.object(self.executor.strategy, 'execute') as mock_execute:
            mock_execute.return_value = self.sample_ccusage_data
            
            result = self.executor.execute(since_date=since_date)
            
            # Verify since_date was passed to the strategy
            mock_execute.assert_called_once_with(since_date=since_date)
            self.assertEqual(result, self.sample_ccusage_data)
    
    def test_executor_all_strategies_fail(self):
        """Test that CcusageExecutor returns empty blocks when all strategies fail."""
        # Mock primary strategy to fail
        with patch.object(self.executor.strategy, 'execute') as mock_primary:
            mock_primary.side_effect = Exception("Primary strategy failed")
            
            # Mock all fallback strategies to fail
            with patch.object(self.executor, 'fallback_strategies') as mock_fallback_classes:
                mock_strategy_class = MagicMock()
                mock_strategy_class.__name__ = "MockFailingStrategy"
                mock_strategy_instance = MagicMock()
                mock_strategy_instance.execute.side_effect = Exception("Fallback strategy failed")
                mock_strategy_class.return_value = mock_strategy_instance
                
                mock_fallback_classes.__iter__.return_value = [mock_strategy_class]
                
                result = self.executor.execute()
                
                # Should return empty blocks when all strategies fail
                self.assertEqual(result, {"blocks": []})


class TestExecutionStrategy(unittest.TestCase):
    """Test the abstract ExecutionStrategy interface."""
    
    def test_strategy_interface_requires_execute_method(self):
        """Test that ExecutionStrategy requires implementation of execute method."""
        # This test verifies that the abstract base class is properly defined
        with self.assertRaises(TypeError):
            # Should fail because execute() is not implemented
            strategy = ExecutionStrategy()


class TestWrapperScriptStrategy(unittest.TestCase):
    """Test the WrapperScriptStrategy implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategy = WrapperScriptStrategy()
        self.sample_ccusage_data = {
            "blocks": [
                {
                    "id": "test-session-1",
                    "startTime": "2024-01-01T10:00:00Z",
                    "endTime": "2024-01-01T11:00:00Z",
                    "tokenCounts": {
                        "inputTokens": 1000,
                        "outputTokens": 500
                    },
                    "costUSD": 0.05
                }
            ]
        }
    
    def test_wrapper_script_strategy_executes_ccusage_wrapper(self):
        """Test that WrapperScriptStrategy calls the ccusage wrapper script."""
        # Mock subprocess.run to simulate wrapper script execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(self.sample_ccusage_data),
                stderr=""
            )
            
            with patch.object(self.strategy, '_find_wrapper_path') as mock_find_path:
                mock_find_path.return_value = '/mock/path/ccusage_wrapper.sh'
                
                result = self.strategy.execute()
                
                # Verify subprocess.run was called with correct arguments
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                self.assertIn('ccusage_wrapper.sh', ' '.join(args))
                
                # Verify result
                self.assertEqual(result, self.sample_ccusage_data)


if __name__ == '__main__':
    unittest.main()