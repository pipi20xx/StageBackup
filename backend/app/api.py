import os
import json
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, database, scheduler, engine

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- System Utilities ---
@router.get("/system/browse")
def browse_filesystem(path: str = "/"):
    """
    List directories and files in the given path.
    Used for the frontend file picker.
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    # 获取实时挂载信息
    active_mounts = engine.get_container_mounts() if hasattr(engine, 'get_container_mounts') else set()
    if not active_mounts:
        # Fallback logic if engine doesn't have it or we need local implementation
        active_mounts = set()
        try:
            if os.path.exists('/proc/mounts'):
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            if parts[1] not in {'/', '/proc', '/sys', '/dev'} and not parts[1].startswith(('/proc/', '/sys/', '/dev/')):
                                active_mounts.add(parts[1])
        except: pass

    items = []
    try:
        if path != "/":
            parent = os.path.dirname(path)
            items.append({"name": "..", "path": parent, "is_dir": True, "size": None, "is_mount": False})

        with os.scandir(path) as it:
            for entry in it:
                try:
                    is_dir = entry.is_dir()
                    item_path = entry.path
                    is_mount = is_dir and item_path in active_mounts
                    size = None
                    if not is_dir:
                        try: size = entry.stat().st_size
                        except: pass
                        
                    items.append({
                        "name": entry.name,
                        "path": item_path,
                        "is_dir": is_dir,
                        "size": size,
                        "is_mount": is_mount
                    })
                except (OSError, PermissionError):
                    continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    items.sort(key=lambda x: (not x.get('is_mount', False), not x['is_dir'], x['name'].lower()))
    return items

# --- Projects ---

@router.post("/projects/{project_id}/restore")
def restore_backup(project_id: int, request: schemas.RestoreRequest):
    scheduler.scheduler.add_job(
        engine.run_restore_task,
        args=[project_id, request.file_name, request.restore_mode]
    )
    return {"status": "Restore job submitted"}

@router.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.BackupProject(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/projects/", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    projects = db.query(models.BackupProject).offset(skip).limit(limit).all()
    for p in projects:
        latest = (
            db.query(models.BackupHistory)
            .filter(models.BackupHistory.project_id == p.id)
            .order_by(models.BackupHistory.start_time.desc())
            .first()
        )
        p.latest_history = latest
        db_schedule = db.query(models.BackupSchedule).filter(models.BackupSchedule.project_id == p.id).first()
        p.schedule = db_schedule
        job = scheduler.scheduler.get_job(f"backup_project_{p.id}")
        p.next_run_time = job.next_run_time if job else None
    return projects

@router.post("/projects/{project_id}/duplicate", response_model=schemas.Project)
def duplicate_project(project_id: int, db: Session = Depends(get_db)):
    original = db.query(models.BackupProject).filter(models.BackupProject.id == project_id).first()
    if not original: raise HTTPException(status_code=404, detail="Project not found")
    base_name = original.name + " (Copy)"
    new_name = base_name
    counter = 1
    while db.query(models.BackupProject).filter(models.BackupProject.name == new_name).first():
        counter += 1
        new_name = f"{base_name} {counter}"
    new_project = models.BackupProject(
        name=new_name,
        source_path=original.source_path,
        destination_path=original.destination_path,
        destination_type=original.destination_type,
        cache_dir=original.cache_dir,
        encryption_password=original.encryption_password,
        archive_format=original.archive_format,
        use_compression=original.use_compression,
        compression_level=original.compression_level,
        exclude_patterns=original.exclude_patterns,
        sync_threads=original.sync_threads,
        sync_mode=original.sync_mode,
        keep_versions=original.keep_versions
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    orig_sched = db.query(models.BackupSchedule).filter(models.BackupSchedule.project_id == project_id).first()
    if orig_sched:
        new_sched = models.BackupSchedule(
            project_id=new_project.id,
            is_active=False,
            schedule_type=orig_sched.schedule_type,
            interval_value=orig_sched.interval_value,
            interval_unit=orig_sched.interval_unit,
            cron_expression=orig_sched.cron_expression
        )
        db.add(new_sched)
        db.commit()
    return new_project

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.BackupProject).filter(models.BackupProject.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    try: scheduler.scheduler.remove_job(f"backup_project_{project_id}")
    except: pass
    db.delete(project)
    db.commit()
    return {"status": "deleted"}

@router.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project_update: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = db.query(models.BackupProject).filter(models.BackupProject.id == project_id).first()
    if not db_project: raise HTTPException(status_code=404, detail="Project not found")
    for key, value in project_update.dict().items(): setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.put("/projects/{project_id}/schedule", response_model=schemas.Schedule)
def update_schedule(project_id: int, schedule: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = db.query(models.BackupSchedule).filter(models.BackupSchedule.project_id == project_id).first()
    if not db_schedule:
        db_schedule = models.BackupSchedule(**schedule.dict(), project_id=project_id)
        db.add(db_schedule)
    else:
        for key, value in schedule.dict().items(): setattr(db_schedule, key, value)
    db.commit()
    db.refresh(db_schedule)
    job_id = f"backup_project_{project_id}"
    try: scheduler.scheduler.remove_job(job_id)
    except: pass
    if schedule.is_active:
        trigger_args = {}
        if schedule.schedule_type == "interval":
            if schedule.interval_unit == 'hours': trigger_args['hours'] = schedule.interval_value
            elif schedule.interval_unit == 'minutes': trigger_args['minutes'] = schedule.interval_value
            elif schedule.interval_unit == 'days': trigger_args['days'] = schedule.interval_value
            elif schedule.interval_unit == 'weeks': trigger_args['weeks'] = schedule.interval_value
            else: trigger_args['seconds'] = schedule.interval_value
            scheduler.scheduler.add_job(engine.run_backup_task, 'interval', args=[project_id], id=job_id, replace_existing=True, **trigger_args)
        elif schedule.schedule_type == "cron":
            parts = schedule.cron_expression.split()
            if len(parts) >= 5: scheduler.scheduler.add_job(engine.run_backup_task, 'cron', minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4], args=[project_id], id=job_id, replace_existing=True)
    return db_schedule

@router.post("/projects/{project_id}/schedule/", response_model=schemas.Schedule)
def create_schedule(project_id: int, schedule: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = models.BackupSchedule(**schedule.dict(), project_id=project_id)
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.get("/projects/{project_id}/schedule", response_model=schemas.Schedule)
def read_schedule(project_id: int, db: Session = Depends(get_db)):
    s = db.query(models.BackupSchedule).filter(models.BackupSchedule.project_id == project_id).first()
    if not s: raise HTTPException(status_code=404, detail="Schedule not found")
    return s

@router.post("/projects/{project_id}/run")
def run_backup_now(project_id: int, request: schemas.RunRequest = None):
    remark = request.remark if request else None
    scheduler.scheduler.add_job(engine.run_backup_task, args=[project_id, None, remark])
    return {"status": "Job submitted"}

@router.post("/projects/{project_id}/stop")
def stop_backup_task(project_id: int):
    engine.stop_signals[project_id] = True
    return {"status": "Stop signal sent"}

# --- History & Backups ---

@router.get("/projects/{project_id}/history", response_model=List[schemas.History])
def read_project_history(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.BackupHistory).filter(models.BackupHistory.project_id == project_id).order_by(models.BackupHistory.start_time.desc()).limit(50).all()

@router.get("/projects/{project_id}/backups")
def discover_project_backups(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.BackupProject).filter(models.BackupProject.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    dest_path = project.destination_path
    if not os.path.exists(dest_path): return []
    
    # 预先获取数据库里的记录，按大小降序排，确保有容量信息的记录优先匹配
    history_records = (
        db.query(models.BackupHistory)
        .filter(models.BackupHistory.project_id == project_id)
        .order_by(models.BackupHistory.file_size_bytes.desc())
        .all()
    )
    history_map = {h.file_name: h for h in history_records if h.file_name}
    
    backups = []
    prefix = project.name.replace(' ', '_') + "_"
    try:
        for entry in os.scandir(dest_path):
            if entry.name.startswith(prefix):
                h_record = history_map.get(entry.name)
                db_size = h_record.file_size_bytes if h_record else 0
                final_size = db_size if db_size > 0 else entry.stat().st_size
                
                backups.append({
                    "id": h_record.id if h_record else None,
                    "file_name": entry.name,
                    "status": h_record.status if h_record else "success",
                    "start_time": h_record.start_time if h_record else datetime.fromtimestamp(entry.stat().st_mtime),
                    "file_size_bytes": final_size,
                    "log_message": h_record.log_message if h_record else "物理发现的文件 (数据库日志已清除)"
                })
    except: pass
    backups.sort(key=lambda x: x['start_time'], reverse=True)
    return backups

@router.delete("/projects/{project_id}/history")
def clear_project_history(project_id: int, clean_files: bool = False, file_name: str = None, db: Session = Depends(get_db)):
    project = db.query(models.BackupProject).filter(models.BackupProject.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    if file_name:
        file_path = os.path.join(project.destination_path, file_name)
        if os.path.exists(file_path):
            try:
                if os.path.isdir(file_path): shutil.rmtree(file_path)
                else: os.remove(file_path)
            except: pass
        db.query(models.BackupHistory).filter(models.BackupHistory.project_id == project_id, models.BackupHistory.file_name == file_name).delete()
        db.commit()
        return {"status": "deleted"}
    
    if clean_files:
        prefix = project.name.replace(' ', '_') + "_"
        if os.path.exists(project.destination_path):
            try:
                for entry in os.scandir(project.destination_path):
                    if entry.name.startswith(prefix):
                        try:
                            if entry.is_dir(): shutil.rmtree(entry.path)
                            else: os.remove(entry.path)
                        except: pass
            except: pass

    db.query(models.BackupHistory).filter(models.BackupHistory.project_id == project_id).delete()
    db.commit()
    return {"status": "cleared"}

# --- Import & Export ---

@router.get("/projects/export/all")
def export_projects(db: Session = Depends(get_db)):
    projects = db.query(models.BackupProject).all()
    export_data = []
    for p in projects:
        p_dict = {c.name: getattr(p, c.name) for c in p.__table__.columns if c.name != 'id'}
        sched = db.query(models.BackupSchedule).filter(models.BackupSchedule.project_id == p.id).first()
        if sched:
            p_dict['schedule_info'] = {
                "schedule_type": sched.schedule_type,
                "interval_value": sched.interval_value,
                "interval_unit": sched.interval_unit,
                "cron_expression": sched.cron_expression
            }
        else: p_dict['schedule_info'] = None
        export_data.append(p_dict)
    return export_data

@router.post("/projects/import/all")
def import_projects(data: List[dict], db: Session = Depends(get_db)):
    imported_count = 0
    for item in data:
        try:
            sched_info = item.pop('schedule_info', None)
            item.pop('id', None)
            project_data = schemas.ProjectCreate(**item)
            final_name = project_data.name
            counter = 1
            while db.query(models.BackupProject).filter(models.BackupProject.name == final_name).first():
                final_name = f"{project_data.name}_Imported_{counter}"
                counter += 1
            db_project = models.BackupProject(**project_data.dict())
            db_project.name = final_name
            db.add(db_project)
            db.commit()
            db.refresh(db_project)
            if sched_info:
                new_sched = models.BackupSchedule(
                    project_id=db_project.id, is_active=False,
                    schedule_type=sched_info.get("schedule_type", "interval"),
                    interval_value=sched_info.get("interval_value", 24),
                    interval_unit=sched_info.get("interval_unit", "hours"),
                    cron_expression=sched_info.get("cron_expression")
                )
            else: new_sched = models.BackupSchedule(project_id=db_project.id, is_active=False)
            db.add(new_sched)
            db.commit()
            imported_count += 1
        except: continue
    return {"status": "success", "imported_count": imported_count}

@router.get("/history/", response_model=List[schemas.History])
def read_global_history(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.BackupHistory).order_by(models.BackupHistory.start_time.desc()).offset(skip).limit(limit).all()

@router.delete("/history/")
def clear_all_history(db: Session = Depends(get_db)):
    db.query(models.BackupHistory).delete()
    db.commit()
    return {"status": "all history cleared"}

# --- Settings ---
from .config_loader import load_settings, save_settings

@router.get("/settings/", response_model=List[schemas.Setting])
def read_settings():
    data = load_settings()
    save_settings(data)
    return [schemas.Setting(key=k, value=v) for k, v in data.items()]

@router.post("/settings/", response_model=schemas.Setting)
def update_setting(setting: schemas.Setting):
    data = load_settings()
    data[setting.key] = setting.value
    save_settings(data)
    return setting

@router.post("/settings/test-notification")
def test_notification(db: Session = Depends(get_db)):
    engine.send_notification("🔔 测试通知", "这是一条来自备份系统的测试消息。", db)
    return {"status": "sent"}