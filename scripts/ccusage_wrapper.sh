#!/bin/bash
# Wrapper script for ccusage that sets up proper environment

# Set up full environment
export PATH="/Users/daniel/.nvm/versions/node/v20.5.0/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export NODE_PATH="/Users/daniel/.nvm/versions/node/v20.5.0/lib/node_modules"
export HOME="/Users/daniel"

# Execute ccusage with all arguments
exec /Users/daniel/.nvm/versions/node/v20.5.0/bin/node /Users/daniel/.nvm/versions/node/v20.5.0/lib/node_modules/ccusage/dist/index.js "$@"