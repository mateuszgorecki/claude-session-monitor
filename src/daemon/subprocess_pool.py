"""
Subprocess pool manager to avoid fork exhaustion in launchd daemons.
"""
import json
import logging
import os
import subprocess
import threading
import time
from queue import Queue, Empty
from typing import Optional, Dict, Any, List


class SubprocessPool:
    """
    Manages a pool of subprocess workers to avoid fork exhaustion.
    This is specifically designed for launchd daemons with process limits.
    """
    
    def __init__(self, max_workers: int = 2):
        """
        Initialize the subprocess pool.
        
        Args:
            max_workers: Maximum number of concurrent subprocess workers
        """
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._command_queue = Queue()
        self._result_cache = {}
        self._cache_ttl = 10  # seconds
        self._workers = []
        self._shutdown = False
        
    def start(self):
        """Start the worker threads."""
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"SubprocessWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
            
    def stop(self):
        """Stop all worker threads."""
        self._shutdown = True
        # Put sentinel values to wake up workers
        for _ in range(self.max_workers):
            self._command_queue.put(None)
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=2)
            
    def _worker_loop(self):
        """Worker loop that processes commands from the queue."""
        while not self._shutdown:
            try:
                task = self._command_queue.get(timeout=1)
                if task is None or self._shutdown:
                    break
                    
                command, result_future = task
                try:
                    result = self._execute_command(command)
                    result_future['result'] = result
                    result_future['error'] = None
                except Exception as e:
                    result_future['result'] = None
                    result_future['error'] = e
                finally:
                    result_future['done'] = True
                    
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                
    def _execute_command(self, command: List[str]) -> Dict[str, Any]:
        """Execute a command and return the result."""
        env = self._prepare_environment()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                env=env,
                timeout=30
            )
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timed out',
                'stdout': '',
                'stderr': ''
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': e.stdout or '',
                'stderr': e.stderr or '',
                'returncode': e.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': ''
            }
            
    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare environment for subprocess execution."""
        env = os.environ.copy()
        
        # Get current PATH and ensure it includes common locations
        current_path = env.get('PATH', '')
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
        all_paths = path_additions + [current_path] if current_path else path_additions
        final_path = ':'.join(all_paths)
        
        env.update({
            'PATH': final_path,
            'HOME': home_dir,
            'LANG': 'en_US.UTF-8',
            'DISPLAY': ':0',
            'USER': os.getenv('USER', 'unknown'),
            'TMPDIR': '/tmp'
        })
        
        return env
        
    def run_command(self, command: List[str], use_cache: bool = True) -> Dict[str, Any]:
        """
        Run a command through the subprocess pool.
        
        Args:
            command: Command and arguments as a list
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary with command results
        """
        # Check cache first
        cache_key = ' '.join(command)
        if use_cache:
            with self._lock:
                if cache_key in self._result_cache:
                    cached_result, timestamp = self._result_cache[cache_key]
                    if time.time() - timestamp < self._cache_ttl:
                        self.logger.debug(f"Returning cached result for: {cache_key}")
                        return cached_result
                        
        # Create a future for the result
        result_future = {
            'done': False,
            'result': None,
            'error': None
        }
        
        # Queue the command
        self._command_queue.put((command, result_future))
        
        # Wait for completion
        start_time = time.time()
        while not result_future['done']:
            if time.time() - start_time > 35:  # 35 second timeout
                self.logger.error(f"Command timed out in queue: {command}")
                return {
                    'success': False,
                    'error': 'Command timed out in queue',
                    'stdout': '',
                    'stderr': ''
                }
            time.sleep(0.1)
            
        # Handle result
        if result_future['error']:
            return {
                'success': False,
                'error': str(result_future['error']),
                'stdout': '',
                'stderr': ''
            }
            
        result = result_future['result']
        
        # Cache successful results
        if use_cache and result.get('success'):
            with self._lock:
                self._result_cache[cache_key] = (result, time.time())
                # Clean old cache entries
                self._clean_cache()
                
        return result
        
    def _clean_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._result_cache.items()
            if current_time - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._result_cache[key]


# Global subprocess pool instance
_subprocess_pool = None
_pool_lock = threading.Lock()


def get_subprocess_pool() -> SubprocessPool:
    """Get or create the global subprocess pool."""
    global _subprocess_pool
    with _pool_lock:
        if _subprocess_pool is None:
            _subprocess_pool = SubprocessPool(max_workers=2)
            _subprocess_pool.start()
        return _subprocess_pool


def run_ccusage_pooled(since_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Run ccusage command using the subprocess pool.
    
    Args:
        since_date: Optional date to fetch data since
        
    Returns:
        Dictionary with parsed JSON data or error information
    """
    pool = get_subprocess_pool()
    
    command = ["ccusage", "blocks", "-j"]
    if since_date:
        command.extend(["-s", since_date])
        
    result = pool.run_command(command)
    
    if not result.get('success'):
        logging.error(f"ccusage command failed: {result.get('error')}")
        return {"blocks": []}
        
    try:
        return json.loads(result.get('stdout', '{}'))
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse ccusage output: {e}")
        return {"blocks": []}