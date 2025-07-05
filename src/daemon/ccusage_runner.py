"""Alternative ccusage runner using os.system to avoid fork issues."""

import os
import json
import tempfile
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def run_ccusage_direct(since_date: Optional[str] = None) -> Dict:
    """Run ccusage using os.system to avoid subprocess fork issues in launchd."""
    
    # Find node executable
    node_path = None
    for path in ["/usr/local/bin/node", "/opt/homebrew/bin/node", 
                 os.path.expanduser("~/.nvm/versions/node/v20.5.0/bin/node")]:
        if os.path.exists(path):
            node_path = path
            break
    
    if not node_path:
        logger.error("Node.js not found, cannot run ccusage")
        return {"blocks": []}
    
    # Find ccusage script
    ccusage_path = os.path.expanduser("~/.nvm/versions/node/v20.5.0/lib/node_modules/ccusage/dist/index.js")
    if not os.path.exists(ccusage_path):
        logger.error(f"ccusage script not found at {ccusage_path}")
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
        
        # Execute using os.system (doesn't fork)
        logger.info(f"Running command: {cmd}")
        
        # Try with explicit shell
        shell_cmd = f"/bin/sh -c '{cmd}'"
        logger.info(f"Shell command: {shell_cmd}")
        
        exit_code = os.system(shell_cmd)
        logger.info(f"Command exit code: {exit_code}")
        
        if exit_code != 0:
            logger.error(f"ccusage command failed with exit code: {exit_code}")
            return {"blocks": []}
        
        # Read result
        with open(tmp_path, 'r') as f:
            result = json.load(f)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to run ccusage: {e}")
        return {"blocks": []}
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass