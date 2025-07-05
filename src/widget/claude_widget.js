// Claude Session Monitor Widget for Scriptable
// Displays real-time Claude API usage statistics from macOS daemon via iCloud sync

const WIDGET_VERSION = "1.0.0";
const DATA_FILE_PATH = "claude-monitor/monitor_data.json";
const CONFIG_FILE_PATH = "claude-monitor/widget_config.json";

// Default configuration
const DEFAULT_CONFIG = {
  theme: "auto", // "light", "dark", "auto"
  displayMetrics: {
    sessions: true,
    cost: true,
    daysRemaining: true,
    activeSession: true,
    lastUpdate: true
  },
  widgetSizes: {
    small: ["sessions", "cost", "daysRemaining"],
    medium: ["sessions", "cost", "daysRemaining", "activeSession"],
    large: ["sessions", "cost", "daysRemaining", "activeSession", "lastUpdate"]
  },
  refreshInterval: 1, // minutes
  colors: {
    primary: "#007AFF",
    secondary: "#34C759", 
    warning: "#FF9500",
    error: "#FF3B30",
    text: "#000000",
    background: "#FFFFFF"
  }
};

// Color schemes
const THEMES = {
  light: {
    primary: "#007AFF",
    secondary: "#34C759",
    warning: "#FF9500", 
    error: "#FF3B30",
    text: "#000000",
    background: "#FFFFFF",
    cardBackground: "#F2F2F7"
  },
  dark: {
    primary: "#0A84FF",
    secondary: "#30D158",
    warning: "#FF9F0A",
    error: "#FF453A", 
    text: "#FFFFFF",
    background: "#000000",
    cardBackground: "#1C1C1E"
  }
};

class ClaudeWidget {
  constructor() {
    this.config = DEFAULT_CONFIG;
    this.data = null;
    this.error = null;
    this.lastUpdate = null;
    this.theme = this.getTheme();
  }

  // Get appropriate theme based on device appearance
  getTheme() {
    if (this.config.theme === "auto") {
      return Device.isUsingDarkAppearance() ? THEMES.dark : THEMES.light;
    }
    return THEMES[this.config.theme] || THEMES.light;
  }

  // Load configuration from iCloud
  async loadConfig() {
    try {
      const fm = FileManager.iCloud();
      const configPath = fm.documentsDirectory() + "/" + CONFIG_FILE_PATH;
      
      if (fm.fileExists(configPath)) {
        const configData = fm.readString(configPath);
        const parsedConfig = JSON.parse(configData);
        
        // Merge with defaults
        this.config = { ...DEFAULT_CONFIG, ...parsedConfig };
        console.log("Widget config loaded successfully");
      } else {
        console.log("No config file found, using defaults");
      }
    } catch (error) {
      console.error("Failed to load config:", error);
      this.config = DEFAULT_CONFIG;
    }
  }

  // Load monitoring data from iCloud
  async loadData() {
    try {
      const fm = FileManager.iCloud();
      const dataPath = fm.documentsDirectory() + "/" + DATA_FILE_PATH;
      
      if (!fm.fileExists(dataPath)) {
        throw new Error("Data file not found. Make sure macOS daemon is running.");
      }

      // Check if file has been updated recently
      const modDate = fm.modificationDate(dataPath);
      const now = new Date();
      const ageMinutes = (now - modDate) / (1000 * 60);
      
      if (ageMinutes > 5) {
        throw new Error(`Data is ${Math.round(ageMinutes)} minutes old. Check daemon status.`);
      }

      const dataString = fm.readString(dataPath);
      this.data = JSON.parse(dataString);
      this.lastUpdate = modDate;
      this.error = null;
      
      console.log("Data loaded successfully");
      return true;
    } catch (error) {
      console.error("Failed to load data:", error);
      this.error = error.message;
      return false;
    }
  }

  // Create widget based on size
  async createWidget() {
    const widget = new ListWidget();
    widget.backgroundColor = new Color(this.theme.background);
    
    if (this.error) {
      this.createErrorWidget(widget);
    } else if (this.data) {
      this.createDataWidget(widget);
    } else {
      this.createLoadingWidget(widget);
    }
    
    return widget;
  }

  // Create error display widget
  createErrorWidget(widget) {
    const errorStack = widget.addStack();
    errorStack.layoutVertically();
    errorStack.centerAlignContent();
    
    // Error icon
    const errorIcon = errorStack.addText("⚠️");
    errorIcon.font = Font.systemFont(24);
    errorIcon.centerAlignText();
    
    errorStack.addSpacer(8);
    
    // Error message
    const errorText = errorStack.addText(this.error);
    errorText.font = Font.systemFont(12);
    errorText.textColor = new Color(this.theme.error);
    errorText.centerAlignText();
    
    errorStack.addSpacer(8);
    
    // Help text
    const helpText = errorStack.addText("Check daemon status on macOS");
    helpText.font = Font.systemFont(10);
    helpText.textColor = new Color(this.theme.text);
    helpText.textOpacity = 0.7;
    helpText.centerAlignText();
  }

  // Create loading widget
  createLoadingWidget(widget) {
    const loadingStack = widget.addStack();
    loadingStack.layoutVertically();
    loadingStack.centerAlignContent();
    
    const loadingText = loadingStack.addText("Loading...");
    loadingText.font = Font.systemFont(16);
    loadingText.textColor = new Color(this.theme.text);
    loadingText.centerAlignText();
  }

  // Create data display widget
  createDataWidget(widget) {
    const widgetSize = this.getWidgetSize();
    const metrics = this.config.widgetSizes[widgetSize] || this.config.widgetSizes.medium;
    
    // Header
    this.addHeader(widget);
    
    // Main content
    const contentStack = widget.addStack();
    contentStack.layoutVertically();
    contentStack.spacing = 4;
    
    // Display metrics based on widget size
    for (const metric of metrics) {
      if (this.config.displayMetrics[metric]) {
        this.addMetric(contentStack, metric);
      }
    }
    
    // Footer with last update
    if (widgetSize === "large" && this.config.displayMetrics.lastUpdate) {
      this.addFooter(widget);
    }
  }

  // Add header with title
  addHeader(widget) {
    const headerStack = widget.addStack();
    headerStack.layoutHorizontally();
    headerStack.centerAlignContent();
    
    const title = headerStack.addText("Claude Monitor");
    title.font = Font.boldSystemFont(14);
    title.textColor = new Color(this.theme.primary);
    
    headerStack.addSpacer();
    
    // Status indicator
    const statusIcon = this.getActiveSession() ? "🟢" : "⚪";
    const status = headerStack.addText(statusIcon);
    status.font = Font.systemFont(12);
    
    widget.addSpacer(8);
  }

  // Add individual metric
  addMetric(stack, metric) {
    const metricStack = stack.addStack();
    metricStack.layoutHorizontally();
    metricStack.centerAlignContent();
    
    switch (metric) {
      case "sessions":
        this.addSessionsMetric(metricStack);
        break;
      case "cost":
        this.addCostMetric(metricStack);
        break;
      case "daysRemaining":
        this.addDaysRemainingMetric(metricStack);
        break;
      case "activeSession":
        this.addActiveSessionMetric(metricStack);
        break;
      case "lastUpdate":
        this.addLastUpdateMetric(metricStack);
        break;
    }
    
    stack.addSpacer(2);
  }

  // Add sessions metric
  addSessionsMetric(stack) {
    const sessionsUsed = this.data.total_sessions_this_month || 0;
    const totalSessions = 50; // From config or data
    const remaining = Math.max(0, totalSessions - sessionsUsed);
    
    const icon = stack.addText("💬");
    icon.font = Font.systemFont(12);
    
    stack.addSpacer(4);
    
    const text = stack.addText(`${sessionsUsed}/${totalSessions}`);
    text.font = Font.systemFont(12);
    text.textColor = new Color(this.theme.text);
    
    stack.addSpacer();
    
    const remainingText = stack.addText(`${remaining} left`);
    remainingText.font = Font.systemFont(10);
    remainingText.textColor = new Color(this.theme.secondary);
  }

  // Add cost metric  
  addCostMetric(stack) {
    const cost = this.data.total_cost_this_month || 0;
    
    const icon = stack.addText("💰");
    icon.font = Font.systemFont(12);
    
    stack.addSpacer(4);
    
    const text = stack.addText(`$${cost.toFixed(2)}`);
    text.font = Font.systemFont(12);
    text.textColor = new Color(this.theme.text);
    
    stack.addSpacer();
    
    const label = stack.addText("this month");
    label.font = Font.systemFont(10);
    label.textColor = new Color(this.theme.text);
    label.textOpacity = 0.7;
  }

  // Add days remaining metric
  addDaysRemainingMetric(stack) {
    const billingEnd = new Date(this.data.billing_period_end);
    const now = new Date();
    const daysRemaining = Math.max(0, Math.ceil((billingEnd - now) / (1000 * 60 * 60 * 24)));
    
    const icon = stack.addText("📅");
    icon.font = Font.systemFont(12);
    
    stack.addSpacer(4);
    
    const text = stack.addText(`${daysRemaining} days`);
    text.font = Font.systemFont(12);
    text.textColor = new Color(this.theme.text);
    
    stack.addSpacer();
    
    const label = stack.addText("remaining");
    label.font = Font.systemFont(10);
    label.textColor = new Color(this.theme.text);
    label.textOpacity = 0.7;
  }

  // Add active session metric
  addActiveSessionMetric(stack) {
    const activeSession = this.getActiveSession();
    
    const icon = stack.addText(activeSession ? "🔴" : "⚪");
    icon.font = Font.systemFont(12);
    
    stack.addSpacer(4);
    
    const text = stack.addText(activeSession ? "Active Session" : "No Active Session");
    text.font = Font.systemFont(12);
    text.textColor = new Color(activeSession ? this.theme.secondary : this.theme.text);
    
    if (activeSession) {
      stack.addSpacer();
      
      const duration = this.getSessionDuration(activeSession);
      const durationText = stack.addText(duration);
      durationText.font = Font.systemFont(10);
      durationText.textColor = new Color(this.theme.text);
      durationText.textOpacity = 0.7;
    }
  }

  // Add last update metric
  addLastUpdateMetric(stack) {
    const icon = stack.addText("🔄");
    icon.font = Font.systemFont(12);
    
    stack.addSpacer(4);
    
    const updateTime = this.formatLastUpdate();
    const text = stack.addText(updateTime);
    text.font = Font.systemFont(10);
    text.textColor = new Color(this.theme.text);
    text.textOpacity = 0.7;
  }

  // Add footer
  addFooter(widget) {
    widget.addSpacer(8);
    
    const footerStack = widget.addStack();
    footerStack.layoutHorizontally();
    footerStack.centerAlignContent();
    
    const updateText = footerStack.addText(this.formatLastUpdate());
    updateText.font = Font.systemFont(9);
    updateText.textColor = new Color(this.theme.text);
    updateText.textOpacity = 0.5;
    
    footerStack.addSpacer();
    
    const versionText = footerStack.addText(`v${WIDGET_VERSION}`);
    versionText.font = Font.systemFont(9);
    versionText.textColor = new Color(this.theme.text);
    versionText.textOpacity = 0.5;
  }

  // Helper methods
  getWidgetSize() {
    const widgetSize = config.widgetFamily;
    return widgetSize || "medium";
  }

  getActiveSession() {
    if (!this.data || !this.data.current_sessions) return null;
    
    return this.data.current_sessions.find(session => session.is_active) || null;
  }

  getSessionDuration(session) {
    if (!session || !session.start_time) return "";
    
    const startTime = new Date(session.start_time);
    const now = new Date();
    const durationMs = now - startTime;
    const durationMinutes = Math.floor(durationMs / (1000 * 60));
    
    if (durationMinutes < 60) {
      return `${durationMinutes}m`;
    } else {
      const hours = Math.floor(durationMinutes / 60);
      const minutes = durationMinutes % 60;
      return `${hours}h ${minutes}m`;
    }
  }

  formatLastUpdate() {
    if (!this.lastUpdate) return "Never";
    
    const now = new Date();
    const diff = now - this.lastUpdate;
    const minutes = Math.floor(diff / (1000 * 60));
    
    if (minutes < 1) {
      return "Just now";
    } else if (minutes < 60) {
      return `${minutes}m ago`;
    } else {
      const hours = Math.floor(minutes / 60);
      return `${hours}h ago`;
    }
  }
}

// Main execution
async function main() {
  const widget = new ClaudeWidget();
  
  // Load configuration
  await widget.loadConfig();
  
  // Load data
  await widget.loadData();
  
  // Create and display widget
  const widgetView = await widget.createWidget();
  
  if (config.runsInWidget) {
    Script.setWidget(widgetView);
  } else {
    await widgetView.presentMedium();
  }
  
  Script.complete();
}

// Run the widget
await main();