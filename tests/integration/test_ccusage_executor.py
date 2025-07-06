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

# Import the module we're testing (this should fail initially - RED phase)
try:
    from src.daemon.ccusage_executor import CcusageExecutor, CcusageStrategy
except ImportError:
    # Expected in RED phase
    pass


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
        # This test should initially fail with ModuleNotFoundError
        result = self.executor.execute()
        
        # Verify the result structure
        self.assertIsInstance(result, dict)
        self.assertIn("blocks", result)
        self.assertIsInstance(result["blocks"], list)
        
        # Verify success indicator
        self.assertTrue(result.get("success", False))
        
    def test_executor_fallback_mechanism(self):
        """Test that CcusageExecutor falls back to alternative strategies when primary fails."""
        # Mock the first strategy to fail
        with patch.object(self.executor, '_strategies') as mock_strategies:
            # First strategy fails
            mock_strategies[0].execute.side_effect = Exception("Strategy 1 failed")
            # Second strategy succeeds
            mock_strategies[1].execute.return_value = self.sample_ccusage_data
            
            result = self.executor.execute()
            
            # Should have fallen back to second strategy
            self.assertEqual(result, self.sample_ccusage_data)
    
    def test_executor_with_since_date_parameter(self):
        """Test that CcusageExecutor properly passes since_date to strategies."""
        since_date = datetime(2024, 1, 1)
        
        with patch.object(self.executor, '_strategies') as mock_strategies:
            mock_strategies[0].execute.return_value = self.sample_ccusage_data
            
            result = self.executor.execute(since_date=since_date)
            
            # Verify since_date was passed to the strategy
            mock_strategies[0].execute.assert_called_once_with(since_date=since_date)
            self.assertEqual(result, self.sample_ccusage_data)
    
    def test_executor_all_strategies_fail(self):
        """Test that CcusageExecutor raises appropriate error when all strategies fail."""
        with patch.object(self.executor, '_strategies') as mock_strategies:
            # All strategies fail
            for strategy in mock_strategies:
                strategy.execute.side_effect = Exception("Strategy failed")
            
            with self.assertRaises(RuntimeError) as context:
                self.executor.execute()
            
            self.assertIn("All ccusage strategies failed", str(context.exception))


class TestCcusageStrategy(unittest.TestCase):
    """Test the abstract CcusageStrategy interface."""
    
    def test_strategy_interface_requires_execute_method(self):
        """Test that CcusageStrategy requires implementation of execute method."""
        # This test verifies that the abstract base class is properly defined
        with self.assertRaises(TypeError):
            # Should fail because execute() is not implemented
            strategy = CcusageStrategy()


class TestWrapperScriptStrategy(unittest.TestCase):
    """Test the WrapperScriptStrategy implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            from src.daemon.ccusage_executor import WrapperScriptStrategy
            self.strategy = WrapperScriptStrategy()
        except ImportError:
            # Expected in RED phase
            pass
    
    def test_wrapper_script_strategy_executes_ccusage_wrapper(self):
        """Test that WrapperScriptStrategy calls the ccusage wrapper script."""
        # Mock subprocess.run to simulate wrapper script execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(self.sample_ccusage_data),
                stderr=""
            )
            
            result = self.strategy.execute()
            
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn('ccusage_wrapper.sh', ' '.join(args))
            
            # Verify result
            self.assertEqual(result, self.sample_ccusage_data)


if __name__ == '__main__':
    unittest.main()