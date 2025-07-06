# Troubleshooting Guide for Claude Session Monitor Daemon

## Common Issues and Solutions

### "Resource temporarily unavailable" (errno 35) Errors

This error typically occurs when the daemon cannot access GUI resources or when system resource limits are exceeded.

#### Root Causes:
1. **Improper launchd configuration** - Daemon runs without GUI access
2. **Session context issues** - Process lacks user session context
3. **Resource exhaustion** - System running out of processes or memory
4. **Missing dependencies** - Required tools not available in PATH

#### Solutions:

**1. Check launchd Configuration**
```bash
# Verify daemon is loaded as LaunchAgent (not LaunchDaemon)
launchctl list | grep com.claude.monitor.daemon

# Check if plist is in correct location
ls -la ~/Library/LaunchAgents/com.claude.monitor.daemon.plist
```

**2. Verify GUI Access**
```bash
# Test GUI access manually
osascript -e 'display notification "Test" with title "Test"'
terminal-notifier -title "Test" -message "Test"
```

**3. Check System Resources**
```bash
# Check current process limits
launchctl limit

# Monitor process spawning
ps -e | awk '{print $4" "$5" "$6}' | sort | uniq -c | sort -n
```

**4. Verify Dependencies**
```bash
# Check if ccusage is available
which ccusage
ccusage --help

# Check terminal-notifier installation
which terminal-notifier
ls -la /Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier
```

### LaunchD Configuration Issues

#### ProcessType Configuration
- **Background**: No GUI access - causes errno 35 with notifications
- **Interactive**: Full GUI access - recommended for this daemon

#### Session Type Configuration
- **LimitLoadToSessionType**: Must be set to "Aqua" for GUI access
- **SessionCreate**: Should be true for user session context

#### Environment Variables
Essential environment variables for GUI access:
- `DISPLAY`: Set to ":0" for main display
- `USER`: Current user name
- `HOME`: User home directory
- `PATH`: Include all tool locations

### Notification Issues

#### Terminal-notifier Problems
```bash
# Check if terminal-notifier is installed
brew install terminal-notifier

# Verify application bundle exists
ls -la /Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier
```

#### AppleScript (osascript) Issues
```bash
# Test basic AppleScript execution
osascript -e 'return "test"'

# Check if System Events is accessible
osascript -e 'tell application "System Events" to return name of processes'
```

### ccusage Command Issues

#### Installation Problems
```bash
# Install ccusage if missing
npm install -g ccusage
# or
npx ccusage --help
```

#### Permission Issues
```bash
# Check if ccusage can access Claude data
ccusage blocks -j

# Verify PATH includes ccusage location
echo $PATH | grep -E "(npm|node)"
```

### Debugging Steps

#### Enable Detailed Logging
1. Check daemon logs:
```bash
tail -f ~/.config/claude-monitor/daemon.log
tail -f ~/.config/claude-monitor/daemon.error.log
```

2. Test daemon manually:
```bash
cd /path/to/claude-session-monitor
python3 run_daemon.py --interval 30 --start-day 1
```

#### System Resource Monitoring
```bash
# Monitor system resources
top -l 1 | grep "Processes:"
vm_stat | grep "Pages free"

# Check for runaway processes
ps aux | grep -v grep | sort -k3 -nr | head -10
```

### Recovery Procedures

#### Restart Daemon
```bash
# Unload daemon
launchctl unload ~/Library/LaunchAgents/com.claude.monitor.daemon.plist

# Reload daemon
launchctl load ~/Library/LaunchAgents/com.claude.monitor.daemon.plist

# Check status
launchctl list | grep claude.monitor
```

#### Reset Configuration
```bash
# Backup current config
cp ~/.config/claude-monitor/config.json ~/.config/claude-monitor/config.json.backup

# Clear daemon state
rm -f ~/.config/claude-monitor/monitor_data.json

# Restart daemon
launchctl kickstart -k gui/$(id -u)/com.claude.monitor.daemon
```

## Prevention Tips

1. **Regular Monitoring**: Check daemon logs weekly
2. **Resource Limits**: Monitor system resource usage
3. **Dependency Updates**: Keep ccusage and terminal-notifier updated
4. **Configuration Validation**: Verify plist configuration after system updates

## Getting Help

If issues persist:
1. Check daemon logs for specific error messages
2. Test components individually (ccusage, terminal-notifier)
3. Verify system permissions and resource limits
4. Consider running daemon in interactive mode for debugging

## Environment-Specific Notes

### macOS Ventura/Sonoma
- Additional privacy permissions may be required
- Check System Preferences > Privacy & Security > Automation

### Homebrew vs System Python
- Ensure consistent Python environment
- Use virtual environments if needed

### Node.js/npm Dependencies
- Keep Node.js updated for ccusage compatibility
- Consider using npx for ccusage execution