"""
Unified ccusage execution with strategy pattern.
Consolidates multiple execution approaches into a single, configurable interface.
"""
import json
import logging
import os
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class ExecutionStrategy(ABC):
    """Abstract base class for ccusage execution strategies."""
    
    @abstractmethod
    def execute(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute ccusage command with optional since_date parameter.
        
        Args:
            since_date: Optional date to fetch data since (YYYYMMDD format)
            
        Returns:
            Dictionary with ccusage result data
        """
        pass


class WrapperScriptStrategy(ExecutionStrategy):
    """Strategy that uses the ccusage wrapper script."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.wrapper_path = self._find_wrapper_path()
    
    def _find_wrapper_path(self) -> str:
        """Find the ccusage wrapper script path."""
        # Look for wrapper script relative to this module
        current_dir = os.path.dirname(__file__)
        wrapper_path = os.path.join(current_dir, '..', '..', 'scripts', 'ccusage_wrapper.sh')
        wrapper_path = os.path.abspath(wrapper_path)
        
        if os.path.exists(wrapper_path):
            return wrapper_path
        
        # Fallback to default location
        return "/usr/local/bin/ccusage_wrapper.sh"
    
    def execute(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute ccusage using wrapper script.
        
        Args:
            since_date: Optional date to fetch data since
            
        Returns:
            Dictionary with ccusage result data
        """
        try:
            command = [self.wrapper_path, "blocks", "-j"]
            if since_date:
                command.extend(["-s", since_date])
            
            self.logger.debug(f"Executing wrapper script: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            self.logger.error("Wrapper script timed out")
            return {"blocks": []}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Wrapper script failed: {e}")
            return {"blocks": []}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse wrapper script output: {e}")
            return {"blocks": []}
        except Exception as e:
            self.logger.error(f"Unexpected error in wrapper script: {e}")
            return {"blocks": []}


class DirectSubprocessStrategy(ExecutionStrategy):
    """Strategy that uses direct subprocess calls to ccusage."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def execute(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute ccusage using direct subprocess calls.
        
        Args:
            since_date: Optional date to fetch data since
            
        Returns:
            Dictionary with ccusage result data
        """
        try:
            # Find node executable
            node_path = self._find_node_executable()
            if not node_path:
                self.logger.error("Node.js executable not found")
                return {"blocks": []}
            
            # Find ccusage script
            ccusage_path = self._find_ccusage_script()
            if not ccusage_path:
                self.logger.error("ccusage script not found")
                return {"blocks": []}
            
            # Build command
            command = [node_path, ccusage_path, "blocks", "-j"]
            if since_date:
                command.extend(["-s", since_date])
            
            # Set up environment
            env = self._prepare_environment()
            
            self.logger.debug(f"Executing direct subprocess: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                env=env,
                timeout=30
            )
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            self.logger.error("Direct subprocess timed out")
            return {"blocks": []}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Direct subprocess failed: {e}")
            return {"blocks": []}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse direct subprocess output: {e}")
            return {"blocks": []}
        except Exception as e:
            self.logger.error(f"Unexpected error in direct subprocess: {e}")
            return {"blocks": []}
    
    def _find_node_executable(self) -> Optional[str]:
        """Find Node.js executable in common locations."""
        node_paths = [
            "/usr/local/bin/node",
            "/opt/homebrew/bin/node",
            os.path.expanduser("~/.nvm/versions/node/v20.5.0/bin/node")
        ]
        
        for path in node_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _find_ccusage_script(self) -> Optional[str]:
        """Find ccusage script in common locations."""
        ccusage_paths = [
            os.path.expanduser("~/.nvm/versions/node/v20.5.0/lib/node_modules/ccusage/dist/index.js"),
            "/usr/local/lib/node_modules/ccusage/dist/index.js",
            "/opt/homebrew/lib/node_modules/ccusage/dist/index.js"
        ]
        
        for path in ccusage_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare environment for subprocess execution."""
        env = os.environ.copy()
        
        # Build PATH with common locations
        path_additions = ['/usr/local/bin', '/usr/bin', '/bin', '/opt/homebrew/bin']
        
        # Add NVM node path if available
        home_dir = os.path.expanduser('~')
        nvm_path = f"{home_dir}/.nvm/versions/node"
        if os.path.exists(nvm_path):
            try:
                node_versions = [d for d in os.listdir(nvm_path) if d.startswith('v')]
                if node_versions:
                    latest_version = sorted(node_versions, reverse=True)[0]
                    node_bin_path = f"{nvm_path}/{latest_version}/bin"
                    if os.path.exists(node_bin_path):
                        path_additions.append(node_bin_path)
            except OSError:
                pass
        
        # Build final PATH
        current_path = env.get('PATH', '')
        all_paths = path_additions + [current_path] if current_path else path_additions
        final_path = ':'.join(all_paths)
        
        env.update({
            'PATH': final_path,
            'HOME': home_dir,
            'LANG': 'en_US.UTF-8',
            'USER': os.getenv('USER', 'unknown'),
            'TMPDIR': '/tmp'
        })
        
        return env


class OSSystemStrategy(ExecutionStrategy):
    """Strategy that uses os.system calls to avoid fork restrictions."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def execute(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute ccusage using os.system to avoid fork restrictions.
        
        Args:
            since_date: Optional date to fetch data since
            
        Returns:
            Dictionary with ccusage result data
        """
        try:
            # Find node executable
            node_path = self._find_node_executable()
            if not node_path:
                self.logger.error("Node.js executable not found")
                return {"blocks": []}
            
            # Find ccusage script
            ccusage_path = self._find_ccusage_script()
            if not ccusage_path:
                self.logger.error("ccusage script not found")
                return {"blocks": []}
            
            # Create temp file for output
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                # Build command
                cmd_parts = [node_path, ccusage_path, "blocks", "-j"]
                if since_date:
                    cmd_parts.extend(["-s", since_date])
                
                # Redirect output to temp file
                cmd = f"{' '.join(cmd_parts)} > {tmp_path} 2>/dev/null"
                shell_cmd = f"/bin/sh -c '{cmd}'"
                
                self.logger.debug(f"Executing os.system: {shell_cmd}")
                
                exit_code = os.system(shell_cmd)
                
                if exit_code != 0:
                    self.logger.error(f"os.system command failed with exit code: {exit_code}")
                    return {"blocks": []}
                
                # Read result
                with open(tmp_path, 'r') as f:
                    result = json.load(f)
                
                return result
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Unexpected error in os.system: {e}")
            return {"blocks": []}
    
    def _find_node_executable(self) -> Optional[str]:
        """Find Node.js executable in common locations."""
        node_paths = [
            "/usr/local/bin/node",
            "/opt/homebrew/bin/node",
            os.path.expanduser("~/.nvm/versions/node/v20.5.0/bin/node")
        ]
        
        for path in node_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _find_ccusage_script(self) -> Optional[str]:
        """Find ccusage script in common locations."""
        ccusage_paths = [
            os.path.expanduser("~/.nvm/versions/node/v20.5.0/lib/node_modules/ccusage/dist/index.js"),
            "/usr/local/lib/node_modules/ccusage/dist/index.js",
            "/opt/homebrew/lib/node_modules/ccusage/dist/index.js"
        ]
        
        for path in ccusage_paths:
            if os.path.exists(path):
                return path
        
        return None


class CcusageExecutor:
    """
    Unified ccusage executor that uses pluggable execution strategies.
    
    Provides a single interface for executing ccusage commands while allowing
    different execution methods based on environment requirements.
    Includes automatic fallback between strategies when primary strategy fails.
    """
    
    def __init__(self, strategy: Optional[ExecutionStrategy] = None, enable_fallback: bool = True):
        """
        Initialize CcusageExecutor with a strategy.
        
        Args:
            strategy: Execution strategy to use. Defaults to WrapperScriptStrategy.
            enable_fallback: Whether to enable automatic fallback to other strategies
        """
        self.logger = logging.getLogger(__name__)
        self.strategy = strategy or WrapperScriptStrategy()
        self.enable_fallback = enable_fallback
        self.logger.debug(f"CcusageExecutor initialized with {self.strategy.__class__.__name__}")
        
        # Define fallback strategy order
        self.fallback_strategies = [
            WrapperScriptStrategy,
            DirectSubprocessStrategy,
            OSSystemStrategy
        ]
    
    def execute(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute ccusage command using the configured strategy with fallback.
        
        Args:
            since_date: Optional date to fetch data since
            
        Returns:
            Dictionary with ccusage result data
        """
        try:
            self.logger.debug(f"Executing ccusage with since_date: {since_date}")
            result = self.strategy.execute(since_date=since_date)
            
            # Validate result structure
            if not isinstance(result, dict) or "blocks" not in result:
                self.logger.warning("Invalid result structure from strategy")
                if self.enable_fallback:
                    return self._execute_with_fallback(since_date)
                return {"blocks": []}
            
            # Check if result is empty (indicating failure)
            if not result.get("blocks"):
                self.logger.warning(f"Primary strategy {self.strategy.__class__.__name__} returned empty result")
                if self.enable_fallback:
                    return self._execute_with_fallback(since_date)
            
            self.logger.debug(f"Successfully executed ccusage, got {len(result['blocks'])} blocks")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing ccusage with {self.strategy.__class__.__name__}: {e}")
            if self.enable_fallback:
                return self._execute_with_fallback(since_date)
            return {"blocks": []}
    
    def _execute_with_fallback(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute ccusage with fallback strategies.
        
        Args:
            since_date: Optional date to fetch data since
            
        Returns:
            Dictionary with ccusage result data
        """
        current_strategy_class = self.strategy.__class__
        
        # Try each fallback strategy in order
        for strategy_class in self.fallback_strategies:
            if strategy_class == current_strategy_class:
                continue  # Skip current strategy
            
            try:
                self.logger.info(f"Trying fallback strategy: {strategy_class.__name__}")
                fallback_strategy = strategy_class()
                result = fallback_strategy.execute(since_date=since_date)
                
                # Validate result
                if isinstance(result, dict) and "blocks" in result and result.get("blocks"):
                    self.logger.info(f"Fallback strategy {strategy_class.__name__} succeeded")
                    return result
                else:
                    self.logger.warning(f"Fallback strategy {strategy_class.__name__} returned empty result")
                    
            except Exception as e:
                self.logger.error(f"Fallback strategy {strategy_class.__name__} failed: {e}")
                continue
        
        # All strategies failed
        self.logger.error("All execution strategies failed")
        return {"blocks": []}
    
    def set_strategy(self, strategy: ExecutionStrategy):
        """
        Change the execution strategy.
        
        Args:
            strategy: New execution strategy to use
        """
        self.strategy = strategy
        self.logger.debug(f"Strategy changed to {strategy.__class__.__name__}")
    
    def get_available_strategies(self) -> List[str]:
        """
        Get list of available strategy names.
        
        Returns:
            List of strategy class names
        """
        return [strategy.__name__ for strategy in self.fallback_strategies]