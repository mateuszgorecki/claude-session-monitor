#!/usr/bin/env python3

"""
Standalone Claude Client
Reads monitoring data from daemon files and displays it with the same UI as claude_monitor.py
"""

import os
import sys

# Add src and src/client to path for imports
src_path = os.path.join(os.path.dirname(__file__), 'src')
client_path = os.path.join(src_path, 'client')
sys.path.insert(0, src_path)
sys.path.insert(0, client_path)

from claude_client import main

if __name__ == "__main__":
    main()