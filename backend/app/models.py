from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class BackupProject(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    # Paths
    source_path = Column(String, nullable=False)
    destination_path = Column(String, nullable=False) # e.g., CloudDrive2 mount path
    destination_type = Column(String, default="cloud") # 'cloud' or 'local'
    cache_dir = Column(String, nullable=True) # Optional custom cache dir, defaults to system tmp if null
    
    # Settings
    encryption_password = Column(String, nullable=True) # Stored in plaintext for MVP, suggest OS keychain for prod
    archive_format = Column(String, default="tgz") # 'tar', 'tgz', '7z'
    use_compression = Column(Boolean, default=True) # Legacy, keeping for compatibility
    compression_level = Column(Integer, default=1) # 1-9
    exclude_patterns = Column(String, nullable=True) # e.g. "*.tmp, node_modules"
    sync_threads = Column(Integer, default=2)
    sync_mode = Column(String, default="overwrite") # 'overwrite' or 'incremental'
    
    # Retention Policy
    keep_versions = Column(Integer, default=7) # Number of backups to keep
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    schedules = relationship("BackupSchedule", back_populates="project", cascade="all, delete-orphan")
    history = relationship("BackupHistory", back_populates="project", cascade="all, delete-orphan")


class BackupSchedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    is_active = Column(Boolean, default=False)
    
    # Schedule Type: 'interval' or 'cron'
    schedule_type = Column(String, default="interval") 
    
    # For 'interval' type (e.g., every 24 hours)
    interval_value = Column(Integer, nullable=True) # Value
    interval_unit = Column(String, nullable=True) # 'hours', 'days', 'weeks'
    
    # For 'cron' type (Expert mode)
    cron_expression = Column(String, nullable=True) # e.g., "0 2 * * *"
    
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    
    project = relationship("BackupProject", back_populates="schedules")


class BackupHistory(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    status = Column(String, nullable=False) # 'success', 'failed', 'running'
    progress = Column(Integer, default=0)
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    file_size_bytes = Column(Integer, default=0)
    file_name = Column(String, nullable=True) # The actual file created (zip/tar.gz)
    
    remark = Column(Text, nullable=True) # User provided note
    log_message = Column(Text, nullable=True) # Error details or success summary
    
    project = relationship("BackupProject", back_populates="history")


class SystemSetting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True) # JSON string or plain text

