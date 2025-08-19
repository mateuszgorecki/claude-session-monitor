#!/usr/bin/env python3
"""
Data models for Claude session monitor.
Defines structured data classes for session tracking, monitoring data, and configuration.
"""
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from zoneinfo import ZoneInfo
from enum import Enum


class ValidationError(Exception):
    """Exception raised when data validation fails."""
    pass


class ActivitySessionStatus(Enum):
    """Enumeration of possible activity session statuses."""
    ACTIVE = "ACTIVE"                    # Claude is currently working (non-stop event as last)
    WAITING_FOR_USER = "WAITING_FOR_USER"  # Recent stop (<2 min), waiting for user input
    IDLE = "IDLE"                        # Stop 2-30 min ago, user likely away
    INACTIVE = "INACTIVE"                # Stop >30 min ago, session practically ended
    STOPPED = "STOPPED"                  # Explicitly stopped session


@dataclass
class SessionData:
    """Represents data for a single Claude session."""
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    is_active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SessionData to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create SessionData from dictionary."""
        # Parse datetime strings back to datetime objects
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
        
        return cls(
            session_id=data['session_id'],
            start_time=start_time,
            end_time=end_time,
            total_tokens=data['total_tokens'],
            input_tokens=data['input_tokens'],
            output_tokens=data['output_tokens'],
            cost_usd=data['cost_usd'],
            is_active=data['is_active']
        )
    
    def to_json(self) -> str:
        """Convert SessionData to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SessionData':
        """Create SessionData from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate_schema(self) -> bool:
        """Validate the SessionData against schema rules."""
        # Check for non-negative values
        if self.total_tokens < 0:
            raise ValidationError(f"total_tokens must be non-negative, got {self.total_tokens}")
        
        if self.input_tokens < 0:
            raise ValidationError(f"input_tokens must be non-negative, got {self.input_tokens}")
        
        if self.output_tokens < 0:
            raise ValidationError(f"output_tokens must be non-negative, got {self.output_tokens}")
        
        if self.cost_usd < 0:
            raise ValidationError(f"cost_usd must be non-negative, got {self.cost_usd}")
        
        # Check token consistency
        if self.input_tokens + self.output_tokens != self.total_tokens:
            raise ValidationError(
                f"Token consistency failed: input_tokens ({self.input_tokens}) + "
                f"output_tokens ({self.output_tokens}) != total_tokens ({self.total_tokens})"
            )
        
        # Check session_id is not empty
        if not self.session_id or not self.session_id.strip():
            raise ValidationError("session_id cannot be empty")
        
        # Check time consistency if both times are provided
        if self.end_time and self.start_time >= self.end_time:
            raise ValidationError("end_time must be after start_time")
        
        return True


@dataclass
class ActivitySessionData:
    """Represents data for a Claude Code activity session."""
    
    project_name: str
    session_id: str
    start_time: datetime
    status: str
    event_type: Optional[str] = None
    end_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ActivitySessionData to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivitySessionData':
        """Create ActivitySessionData from dictionary."""
        # Parse datetime strings back to datetime objects
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
        
        return cls(
            project_name=data['project_name'],
            session_id=data['session_id'],
            start_time=start_time,
            status=data['status'],
            event_type=data.get('event_type'),
            end_time=end_time,
            metadata=data.get('metadata')
        )
    
    def to_json(self) -> str:
        """Convert ActivitySessionData to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ActivitySessionData':
        """Create ActivitySessionData from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @staticmethod
    def calculate_smart_status(events: List['ActivitySessionData'], current_time: Optional[datetime] = None) -> str:
        """Calculate smart session status based on event history using Claude Code hooks logic.
        
        Logic:
        - ACTIVE: Last event is non-stop (Claude is working)
        - WAITING_FOR_USER: Recent stop (<2 min), waiting for user input  
        - IDLE: Stop 2-30 min ago, user likely away
        - INACTIVE: Stop >30 min ago, session practically ended
        
        Args:
            events: List of ActivitySessionData events for this session
            current_time: Optional current time for testing (defaults to now)
            
        Returns:
            Status string from ActivitySessionStatus enum
        """
        if not events:
            return ActivitySessionStatus.INACTIVE.value
            
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        # Sort events by timestamp (most recent last)
        sorted_events = sorted(events, key=lambda e: e.start_time)
        last_event = sorted_events[-1]
        
        # Calculate time since last event
        if last_event.start_time.tzinfo is None:
            # If timestamp is naive, assume UTC
            last_event_time = last_event.start_time.replace(tzinfo=timezone.utc)
        else:
            last_event_time = last_event.start_time
            
        time_since_last = (current_time - last_event_time).total_seconds() / 60  # minutes
        
        # Smart status detection based on last event type and timing
        if last_event.event_type == "stop":
            if time_since_last < 2:  # Very recent stop
                return ActivitySessionStatus.WAITING_FOR_USER.value
            elif time_since_last < 30:  # Recent but not fresh
                return ActivitySessionStatus.IDLE.value
            else:  # Old stop
                return ActivitySessionStatus.INACTIVE.value
        else:  # Last event was activity/notification (non-stop)
            return ActivitySessionStatus.ACTIVE.value

    def compress_events(self) -> None:
        """Compress events to reduce file size by keeping only the most recent events.
        
        This method:
        1. Keeps only the last MAX_EVENTS_PER_SESSION events
        2. Updates event_count to reflect total historical count
        3. Preserves event timing information for status calculation
        """
        from shared.constants import MAX_EVENTS_PER_SESSION
        
        if not self.metadata or 'events' not in self.metadata:
            return
            
        events = self.metadata.get('events', [])
        if len(events) <= MAX_EVENTS_PER_SESSION:
            return
            
        # Keep the last MAX_EVENTS_PER_SESSION events
        compressed_events = events[-MAX_EVENTS_PER_SESSION:]
        
        # Update metadata with compressed events
        self.metadata['events'] = compressed_events
        self.metadata['event_count'] = len(events)  # Keep original count
        self.metadata['compressed'] = True
        self.metadata['compression_note'] = f"Showing last {MAX_EVENTS_PER_SESSION} of {len(events)} events"

    def validate_schema(self) -> bool:
        """Validate the ActivitySessionData against schema rules."""
        # Check project_name is not empty
        if not self.project_name or not self.project_name.strip():
            raise ValidationError("project_name cannot be empty")
        
        # Check session_id is not empty
        if not self.session_id or not self.session_id.strip():
            raise ValidationError("session_id cannot be empty")
        
        # Check status is valid
        valid_statuses = [status.value for status in ActivitySessionStatus]
        if self.status not in valid_statuses:
            raise ValidationError(f"status must be one of {valid_statuses}, got {self.status}")
        
        # Check time consistency if both times are provided
        if self.end_time and self.start_time >= self.end_time:
            raise ValidationError("end_time must be after start_time")
        
        return True


@dataclass
class UsageIntensityData:
    """Tracks usage intensity and model-specific metrics."""
    
    # Current parallel sessions tracking
    active_sessions_count: int = 0
    parallel_intensity: float = 1.0  # Usage time / real time ratio
    
    # Weekly usage tracking (hours)
    sonnet_hours_used: float = 0.0
    opus_hours_used: float = 0.0
    
    # User prompts tracking (not responses)
    user_prompts_current_window: int = 0
    user_prompts_this_week: int = 0
    
    # Real time vs usage time
    real_time_elapsed: float = 0.0  # Hours of real time
    usage_time_accumulated: float = 0.0  # Hours of usage time (can be > real time)
    
    # Week tracking
    week_start: Optional[datetime] = None
    week_end: Optional[datetime] = None
    
    def calculate_efficiency_ratio(self) -> float:
        """Calculate efficiency ratio (usage time / real time)."""
        if self.real_time_elapsed <= 0:
            return 1.0
        return self.usage_time_accumulated / self.real_time_elapsed
    
    def get_total_weekly_hours(self) -> float:
        """Get total weekly usage hours across all models."""
        return self.sonnet_hours_used + self.opus_hours_used
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert UsageIntensityData to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['week_start'] = self.week_start.isoformat() if self.week_start else None
        data['week_end'] = self.week_end.isoformat() if self.week_end else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UsageIntensityData':
        """Create UsageIntensityData from dictionary."""
        # Parse datetime strings back to datetime objects
        week_start = datetime.fromisoformat(data['week_start']) if data['week_start'] else None
        week_end = datetime.fromisoformat(data['week_end']) if data['week_end'] else None
        
        # Create new instance with parsed data
        instance_data = data.copy()
        instance_data['week_start'] = week_start  
        instance_data['week_end'] = week_end
        
        return cls(**instance_data)
    
    def validate_schema(self) -> bool:
        """Validate the UsageIntensityData against schema rules."""
        # Check non-negative values
        if self.active_sessions_count < 0:
            raise ValidationError(f"active_sessions_count must be non-negative, got {self.active_sessions_count}")
        
        if self.parallel_intensity < 0:
            raise ValidationError(f"parallel_intensity must be non-negative, got {self.parallel_intensity}")
            
        if self.sonnet_hours_used < 0:
            raise ValidationError(f"sonnet_hours_used must be non-negative, got {self.sonnet_hours_used}")
            
        if self.opus_hours_used < 0:
            raise ValidationError(f"opus_hours_used must be non-negative, got {self.opus_hours_used}")
            
        if self.user_prompts_current_window < 0:
            raise ValidationError(f"user_prompts_current_window must be non-negative, got {self.user_prompts_current_window}")
            
        if self.user_prompts_this_week < 0:
            raise ValidationError(f"user_prompts_this_week must be non-negative, got {self.user_prompts_this_week}")
        
        if self.real_time_elapsed < 0:
            raise ValidationError(f"real_time_elapsed must be non-negative, got {self.real_time_elapsed}")
            
        if self.usage_time_accumulated < 0:
            raise ValidationError(f"usage_time_accumulated must be non-negative, got {self.usage_time_accumulated}")
        
        # Check week consistency if both dates provided
        if self.week_start and self.week_end and self.week_start >= self.week_end:
            raise ValidationError("week_end must be after week_start")
        
        return True


@dataclass
class MonitoringData:
    """Represents aggregated monitoring data for the current period."""
    
    current_sessions: List[SessionData]
    total_sessions_this_month: int
    total_cost_this_month: float
    max_tokens_per_session: int
    last_update: datetime
    billing_period_start: datetime
    billing_period_end: datetime
    daemon_version: Optional[str] = None
    activity_sessions: List[ActivitySessionData] = None
    usage_intensity: Optional[UsageIntensityData] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MonitoringData to dictionary."""
        return {
            'current_sessions': [session.to_dict() for session in self.current_sessions],
            'total_sessions_this_month': self.total_sessions_this_month,
            'total_cost_this_month': self.total_cost_this_month,
            'max_tokens_per_session': self.max_tokens_per_session,
            'last_update': self.last_update.isoformat(),
            'billing_period_start': self.billing_period_start.isoformat(),
            'billing_period_end': self.billing_period_end.isoformat(),
            'daemon_version': self.daemon_version,
            'activity_sessions': [activity.to_dict() for activity in (self.activity_sessions or [])],
            'usage_intensity': self.usage_intensity.to_dict() if self.usage_intensity else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoringData':
        """Create MonitoringData from dictionary."""
        current_sessions = [SessionData.from_dict(session_data) for session_data in data['current_sessions']]
        activity_sessions = [ActivitySessionData.from_dict(activity_data) for activity_data in data.get('activity_sessions', [])]
        usage_intensity = UsageIntensityData.from_dict(data['usage_intensity']) if data.get('usage_intensity') else None
        
        return cls(
            current_sessions=current_sessions,
            total_sessions_this_month=data['total_sessions_this_month'],
            total_cost_this_month=data['total_cost_this_month'],
            max_tokens_per_session=data['max_tokens_per_session'],
            last_update=datetime.fromisoformat(data['last_update']),
            billing_period_start=datetime.fromisoformat(data['billing_period_start']),
            billing_period_end=datetime.fromisoformat(data['billing_period_end']),
            daemon_version=data.get('daemon_version'),
            activity_sessions=activity_sessions if activity_sessions else None,
            usage_intensity=usage_intensity
        )
    
    def to_json(self) -> str:
        """Convert MonitoringData to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MonitoringData':
        """Create MonitoringData from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate_schema(self) -> bool:
        """Validate the MonitoringData against schema rules."""
        # Check non-negative values
        if self.total_sessions_this_month < 0:
            raise ValidationError(f"total_sessions_this_month must be non-negative, got {self.total_sessions_this_month}")
        
        if self.total_cost_this_month < 0:
            raise ValidationError(f"total_cost_this_month must be non-negative, got {self.total_cost_this_month}")
        
        if self.max_tokens_per_session < 0:
            raise ValidationError(f"max_tokens_per_session must be non-negative, got {self.max_tokens_per_session}")
        
        # Check billing period consistency
        if self.billing_period_start >= self.billing_period_end:
            raise ValidationError("billing_period_end must be after billing_period_start")
        
        # Validate all current sessions
        for session in self.current_sessions:
            session.validate_schema()
        
        # Validate all activity sessions
        if self.activity_sessions:
            for activity_session in self.activity_sessions:
                activity_session.validate_schema()
        
        # Validate usage intensity data
        if self.usage_intensity:
            self.usage_intensity.validate_schema()
        
        return True


@dataclass
class ConfigData:
    """Represents configuration settings for the monitor."""
    
    # Default values based on current implementation
    total_monthly_sessions: int = 50
    refresh_interval_seconds: int = 1
    ccusage_fetch_interval_seconds: int = 10
    time_remaining_alert_minutes: int = 30
    inactivity_alert_minutes: int = 10
    local_timezone: str = "Europe/Warsaw"
    billing_start_day: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ConfigData to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigData':
        """Create ConfigData from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert ConfigData to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ConfigData':
        """Create ConfigData from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate_schema(self) -> bool:
        """Validate the ConfigData against schema rules."""
        # Check positive values for time intervals
        if self.refresh_interval_seconds <= 0:
            raise ValidationError(f"refresh_interval_seconds must be positive, got {self.refresh_interval_seconds}")
        
        if self.ccusage_fetch_interval_seconds <= 0:
            raise ValidationError(f"ccusage_fetch_interval_seconds must be positive, got {self.ccusage_fetch_interval_seconds}")
        
        if self.time_remaining_alert_minutes <= 0:
            raise ValidationError(f"time_remaining_alert_minutes must be positive, got {self.time_remaining_alert_minutes}")
        
        if self.inactivity_alert_minutes <= 0:
            raise ValidationError(f"inactivity_alert_minutes must be positive, got {self.inactivity_alert_minutes}")
        
        if self.total_monthly_sessions <= 0:
            raise ValidationError(f"total_monthly_sessions must be positive, got {self.total_monthly_sessions}")
        
        # Check billing_start_day is valid (1-31)
        if not (1 <= self.billing_start_day <= 31):
            raise ValidationError(f"billing_start_day must be between 1 and 31, got {self.billing_start_day}")
        
        # Check timezone string is not empty
        if not self.local_timezone or not self.local_timezone.strip():
            raise ValidationError("local_timezone cannot be empty")
        
        # Try to create timezone to validate it
        try:
            ZoneInfo(self.local_timezone)
        except Exception:
            raise ValidationError(f"Invalid timezone: {self.local_timezone}")
        
        return True


@dataclass
class ErrorStatus:
    """Represents error status for ccusage operations."""
    
    has_error: bool
    error_message: Optional[str]
    error_code: Optional[int]
    last_successful_update: Optional[datetime]
    consecutive_failures: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ErrorStatus to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        data['last_successful_update'] = (
            self.last_successful_update.isoformat() 
            if self.last_successful_update else None
        )
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorStatus':
        """Create ErrorStatus from dictionary."""
        last_successful_update = (
            datetime.fromisoformat(data['last_successful_update']) 
            if data['last_successful_update'] else None
        )
        
        return cls(
            has_error=data['has_error'],
            error_message=data['error_message'],
            error_code=data['error_code'],
            last_successful_update=last_successful_update,
            consecutive_failures=data['consecutive_failures']
        )
    
    def to_json(self) -> str:
        """Convert ErrorStatus to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ErrorStatus':
        """Create ErrorStatus from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate_schema(self) -> bool:
        """Validate the ErrorStatus against schema rules."""
        # Check non-negative consecutive failures
        if self.consecutive_failures < 0:
            raise ValidationError(f"consecutive_failures must be non-negative, got {self.consecutive_failures}")
        
        # If has_error is True, error_message should be provided
        if self.has_error and not self.error_message:
            raise ValidationError("error_message must be provided when has_error is True")
        
        # If has_error is False, error fields should be None
        if not self.has_error:
            if self.error_message is not None:
                raise ValidationError("error_message should be None when has_error is False")
            if self.error_code is not None:
                raise ValidationError("error_code should be None when has_error is False")
        
        return True