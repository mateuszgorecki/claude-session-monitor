#!/usr/bin/env python3

"""
Claude Client - Terminal interface for Claude session monitoring.

This is a wrapper script that provides the main claude_client.py entry point
as documented in CLAUDE.md. The actual implementation is in src/client/claude_client.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from client.claude_client import main

if __name__ == "__main__":
    main()