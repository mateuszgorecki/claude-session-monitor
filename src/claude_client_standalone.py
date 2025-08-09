#!/usr/bin/env python3

"""
Standalone Claude Client
Reads monitoring data from daemon files and displays it with the same UI as claude_monitor.py
"""

from .client.claude_client import main as claude_main

def main():
    """Entry point for the ccmonitor command"""
    claude_main()

if __name__ == "__main__":
    main()
