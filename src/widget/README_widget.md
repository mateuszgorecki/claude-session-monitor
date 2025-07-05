# Claude Session Monitor Widget for Scriptable

A beautiful iOS/iPadOS widget that displays real-time Claude API usage statistics synchronized from your macOS daemon via iCloud Drive.

## Features

- **Real-time monitoring**: Shows current session status, usage statistics, and billing period information
- **Multiple widget sizes**: Optimized layouts for small, medium, and large widgets
- **Automatic sync**: Updates every minute via iCloud Drive synchronization
- **Dark/Light themes**: Automatically adapts to your device's appearance
- **Customizable display**: Configure which metrics to show for each widget size
- **Error handling**: Graceful degradation when data is unavailable

## Prerequisites

1. **macOS Claude Monitor Daemon**: The widget requires the Claude Monitor daemon to be running on your macOS system
2. **Scriptable App**: Download from the App Store (free)
3. **iCloud Drive**: Enabled and working on both macOS and iOS/iPadOS devices

## Installation

### Step 1: Install Scriptable

1. Download and install **Scriptable** from the iOS App Store
2. Open the app and familiarize yourself with the interface

### Step 2: Set up macOS Daemon (if not already done)

1. On your macOS system, ensure the Claude Monitor daemon is running:
   ```bash
   uv run python3 run_daemon.py --start-day 17  # Use your billing start day
   ```

2. Verify iCloud sync is working by checking for files in:
   ```
   ~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/
   ```

### Step 3: Install Widget Script

1. **Copy the widget script**:
   - Open `src/widget/claude_widget.js` in a text editor
   - Select all content and copy it

2. **Create new script in Scriptable**:
   - Open Scriptable on your iOS device
   - Tap the "+" button to create a new script
   - Paste the copied content
   - Rename the script to "Claude Monitor" (tap the title at the top)

3. **Test the script**:
   - Tap the play button to run the script
   - If working correctly, you should see a preview of the widget

### Step 4: Add Widget to Home Screen

1. **Enter Home Screen edit mode**:
   - Long press on your home screen until apps start wiggling
   - Tap the "+" button in the top left corner

2. **Find Scriptable**:
   - Search for "Scriptable" in the widget gallery
   - Choose your preferred widget size (Small, Medium, or Large)

3. **Configure the widget**:
   - Tap "Add Widget" to place it on your home screen
   - Long press the new widget and select "Edit Widget"
   - Set "Script" to "Claude Monitor"
   - Optionally set "When Interacting" to "Run Script"

## Configuration

### Basic Configuration

The widget includes sensible defaults, but you can customize it by creating a configuration file:

1. **Create configuration file** (optional):
   - In Scriptable, create a new script
   - Copy the content from `src/widget/widget_config.json`
   - Save it to iCloud Drive at: `claude-monitor/widget_config.json`

### Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `theme` | Color theme: "light", "dark", or "auto" | "auto" |
| `displayMetrics` | Which metrics to show | All enabled |
| `refreshInterval` | Update frequency in minutes | 1 |
| `dataAgeThresholdMinutes` | Max age for data before showing error | 5 |

### Widget Sizes and Metrics

#### Small Widget
- **Metrics**: Sessions used/remaining, Monthly cost
- **Best for**: Quick glance at essential info

#### Medium Widget  
- **Metrics**: Sessions, cost, days remaining, active session status
- **Best for**: Balanced view with key information

#### Large Widget
- **Metrics**: All metrics including projections and last update time
- **Best for**: Comprehensive monitoring dashboard

## Troubleshooting

### Widget Shows "Data file not found"

1. **Check daemon status** on macOS:
   ```bash
   ps aux | grep claude_daemon
   ```

2. **Verify iCloud sync**:
   - Check if files exist in `~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/`
   - Try manually syncing iCloud Drive

3. **Restart daemon** if needed:
   ```bash
   uv run python3 run_daemon.py --start-day YOUR_BILLING_DAY
   ```

### Widget Shows "Data is X minutes old"

1. **Check network connection** on both devices
2. **Force iCloud sync**:
   - Open Files app on iOS
   - Navigate to iCloud Drive > claude-monitor
   - Pull down to refresh

3. **Check daemon is actively writing data**:
   ```bash
   tail -f ~/.config/claude-monitor/claude-monitor.log
   ```

### Widget Shows Error Message

1. **Check script syntax**:
   - Open the script in Scriptable
   - Run it manually to see detailed error messages

2. **Verify configuration**:
   - Ensure `widget_config.json` has valid JSON syntax
   - Remove config file to test with defaults

3. **Check file permissions**:
   - Ensure iCloud Drive has proper permissions
   - Try logging out and back into iCloud

### Widget Doesn't Update

1. **Check refresh settings**:
   - iOS limits background refresh for widgets
   - Manually refresh by re-entering home screen

2. **Verify Scriptable permissions**:
   - Settings > Privacy & Security > Files and Folders
   - Ensure Scriptable can access iCloud Drive

3. **Check widget configuration**:
   - Long press widget > Edit Widget
   - Verify script is set to "Claude Monitor"

## Data Privacy

- **Local processing**: All data processing happens locally on your devices
- **iCloud sync**: Data is synchronized through your personal iCloud Drive
- **No external services**: The widget doesn't send data to any external servers
- **Temporary storage**: Data is cached temporarily in Scriptable for performance

## Advanced Configuration

### Custom Themes

You can customize colors by editing the `colors` section in `widget_config.json`:

```json
{
  "colors": {
    "light": {
      "primary": "#007AFF",
      "secondary": "#34C759",
      "text": "#000000"
    }
  }
}
```

### Metric Selection

Customize which metrics appear in each widget size:

```json
{
  "widgetSizes": {
    "small": {
      "metrics": ["sessions", "cost"],
      "compactMode": true
    }
  }
}
```

### Debug Mode

Enable debug logging by setting `debugMode: true` in the advanced configuration:

```json
{
  "advanced": {
    "debugMode": true,
    "logLevel": "debug"
  }
}
```

## Support

If you encounter issues:

1. **Check the logs** on macOS: `~/.config/claude-monitor/claude-monitor.log`
2. **Verify daemon status**: Ensure the daemon is running and syncing to iCloud
3. **Test manual sync**: Run the widget script manually in Scriptable to see detailed errors
4. **Reset configuration**: Remove `widget_config.json` to use default settings

## Version History

### v1.0.0
- Initial release
- Support for all three widget sizes
- Real-time data synchronization via iCloud Drive
- Automatic theme switching
- Comprehensive error handling
- Configurable metrics display

## Technical Details

- **Platform**: iOS 14+ / iPadOS 14+
- **App**: Scriptable (free)
- **Sync**: iCloud Drive
- **Update frequency**: 1 minute (configurable)
- **Data source**: macOS Claude Monitor daemon
- **Language**: JavaScript (Scriptable API)