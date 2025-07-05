#!/usr/bin/env python3
"""Test subprocess execution in different contexts."""

import subprocess
import os
import sys

print(f"Running as user: {os.getuid()}")
print(f"Environment USER: {os.environ.get('USER', 'NOT SET')}")
print(f"Working directory: {os.getcwd()}")
print(f"Python: {sys.executable}")

# Test 1: Simple echo
try:
    result = subprocess.run(['echo', 'test'], capture_output=True, text=True)
    print(f"✓ Echo test: {result.stdout.strip()}")
except Exception as e:
    print(f"✗ Echo test failed: {e}")

# Test 2: Which node
try:
    result = subprocess.run(['which', 'node'], capture_output=True, text=True)
    print(f"✓ Which node: {result.stdout.strip()}")
except Exception as e:
    print(f"✗ Which node failed: {e}")

# Test 3: Direct node call
node_path = os.path.expanduser("~/.nvm/versions/node/v20.5.0/bin/node")
if os.path.exists(node_path):
    try:
        result = subprocess.run([node_path, '--version'], capture_output=True, text=True)
        print(f"✓ Node version: {result.stdout.strip()}")
    except Exception as e:
        print(f"✗ Node execution failed: {e}")

# Test 4: Full ccusage command
ccusage_path = os.path.expanduser("~/.nvm/versions/node/v20.5.0/lib/node_modules/ccusage/dist/index.js")
if os.path.exists(node_path) and os.path.exists(ccusage_path):
    try:
        result = subprocess.run([node_path, ccusage_path, '--version'], 
                              capture_output=True, text=True, timeout=5)
        print(f"✓ ccusage version: {result.stdout.strip()}")
    except Exception as e:
        print(f"✗ ccusage execution failed: {e}")