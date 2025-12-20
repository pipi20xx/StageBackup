from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- History Schemas ---
class HistoryBase(BaseModel):
    status: str
    log_message: Optional[str] = None
    file_size_bytes: int = 0
    file_name: Optional[str] = None
    progress: int = 0
    remark: Optional[str] = None

class RunRequest(BaseModel):
    remark: Optional[str] = None

class History(HistoryBase):
    id: int
    project_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# --- Schedule Schemas (Moved Up) ---
class ScheduleBase(BaseModel):
    is_active: bool = True
    schedule_type: str = "interval" # or 'cron'
    interval_value: Optional[int] = None
    interval_unit: Optional[str] = None
    cron_expression: Optional[str] = None

class ScheduleCreate(ScheduleBase):
    pass

class Schedule(ScheduleBase):
    id: int
    project_id: int
    next_run_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class RestoreRequest(BaseModel):
    file_name: str
    restore_mode: str = 'overwrite' # 'overwrite' or 'clean'

# --- Project Schemas ---
class ProjectBase(BaseModel):
    name: str
    source_path: str
    destination_path: str
    destination_type: str = "cloud"
    cache_dir: Optional[str] = None
    encryption_password: Optional[str] = None
    archive_format: str = "tgz"
    use_compression: bool = True
    compression_level: int = 1
    exclude_patterns: Optional[str] = None
    sync_threads: int = 2
    sync_mode: str = "overwrite" # 'overwrite' or 'incremental'
    keep_versions: int = 7

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_at: datetime
    latest_history: Optional[History] = None
    schedule: Optional[Schedule] = None # Attached Schedule info
    next_run_time: Optional[datetime] = None # Calculated from APScheduler
    
    class Config:
        from_attributes = True

class Setting(BaseModel):
    key: str
    value: Optional[str] = None
    
    class Config:
        from_attributes = True

