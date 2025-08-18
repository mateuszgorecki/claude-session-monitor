#!/usr/bin/env python3

"""
Standalone Claude Client
Reads monitoring data from daemon files and displays it with the same UI as claude_monitor.py
"""

try:
    from .client.claude_client import main as claude_main
except ImportError:
    # Fallback for package installations
    import sys
    import os
    # Add src to path if we're in the package structure
    src_path = os.path.join(os.path.dirname(__file__))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from client.claude_client import main as claude_main

def main():
    """Entry point for the ccmonitor command"""
    claude_main()

if __name__ == "__main__":
    main()
