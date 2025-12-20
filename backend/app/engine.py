import time
import shutil
import os
import tarfile
import hashlib
import secrets
import fnmatch
import subprocess
import io
import concurrent.futures
import apprise
from datetime import datetime
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from .models import BackupProject, BackupHistory
from .database import SessionLocal
from .config_loader import get_setting_value

# 全局停止信号
stop_signals = {}

def check_stop(project_id: int, log_buffer: io.StringIO = None):
    if stop_signals.get(project_id):
        msg = "!!! 任务被用户强制终止 !!!"
        if log_buffer: log_buffer.write(f"\n[ERROR] {msg}\n")
        raise Exception(msg)

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
    return kdf.derive(password.encode())

def encrypt_file(input_file: str, output_file: str, password: str, project_id: int = None):
    salt = secrets.token_bytes(16)
    key = derive_key(password, salt)
    iv = secrets.token_bytes(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend()).encryptor()
    with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
        f_out.write(salt)
        f_out.write(iv)
        while chunk := f_in.read(1024 * 1024):
            if project_id: check_stop(project_id)
            f_out.write(encryptor.update(chunk))
        f_out.write(encryptor.finalize())
        f_out.write(encryptor.tag)

def decrypt_file(input_file: str, output_file: str, password: str, project_id: int = None):
    with open(input_file, 'rb') as f_in:
        salt = f_in.read(16)
        iv = f_in.read(12)
        key = derive_key(password, salt)
        f_in.seek(-16, os.SEEK_END)
        tag = f_in.read(16)
        f_in.seek(28, os.SEEK_SET)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
        file_size = os.fstat(f_in.fileno()).st_size
        data_len = file_size - 16 - 12 - 16
        with open(output_file, 'wb') as f_out:
            bytes_read = 0
            while bytes_read < data_len:
                if project_id: check_stop(project_id)
                chunk = f_in.read(min(1024 * 1024, data_len - bytes_read))
                if not chunk: break
                f_out.write(decryptor.update(chunk))
                bytes_read += len(chunk)
            decryptor.finalize()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5), retry=retry_if_exception_type(IOError))
def perform_safe_move(source_path: str, dest_path: str):
    shutil.move(source_path, dest_path)

def generate_manifest(source_path: str, patterns: list, log_buffer: io.StringIO):
    """生成清单，带有格式化前缀"""
    include_list = []
    exclude_count = 0
    log_buffer.write(f"[INFO] 正在扫描源目录并应用过滤规则...\n")
    for root, dirs, files in os.walk(source_path):
        rel_root = os.path.relpath(root, source_path)
        if rel_root == ".": rel_root = ""
        
        is_dir_excluded = False
        if rel_root:
            for p in patterns:
                if fnmatch.fnmatch(rel_root, p) or any(fnmatch.fnmatch(part, p) for part in rel_root.split('/')):
                    is_dir_excluded = True
                    break
        
        if is_dir_excluded:
            log_buffer.write(f"[SKIP] 排除目录: {rel_root}\n")
            exclude_count += 1
            dirs[:] = []
            continue
            
        for name in files:
            rel_path = os.path.join(rel_root, name) if rel_root else name
            is_file_excluded = False
            for p in patterns:
                if fnmatch.fnmatch(name, p) or fnmatch.fnmatch(rel_path, p):
                    is_file_excluded = True
                    break
            
            if is_file_excluded:
                log_buffer.write(f"[SKIP] 排除文件: {rel_path}\n")
                exclude_count += 1
            else:
                include_list.append(rel_path)
                log_buffer.write(f"[ADD]  包含文件: {rel_path}\n")
                
    log_buffer.write(f"[INFO] 扫描完成: 包含 {len(include_list)} 个文件, 排除 {exclude_count} 个对象。\n\n")
    return include_list

def send_notification(title: str, body: str, db: Session):
    try:
        proxy_val = get_setting_value("http_proxy")
        token_val = get_setting_value("telegram_bot_token")
        chat_id_val = get_setting_value("telegram_chat_id")
        use_proxy_for_tg_val = get_setting_value("proxy_enabled_for_telegram")
        
        if not token_val or not chat_id_val: return

        if proxy_val and use_proxy_for_tg_val == 'true':
            os.environ['http_proxy'] = proxy_val
            os.environ['https_proxy'] = proxy_val
        else:
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)

        apobj = apprise.Apprise()
        apobj.add(f"tgram://{token_val}/{chat_id_val}")
        apobj.notify(title=title, body=body)
    except Exception as e:
        print(f"Notification Error: {e}")

def apply_retention_policy(project, db: Session):
    if not project.keep_versions or project.keep_versions <= 0: return
    history = db.query(BackupHistory).filter(
        BackupHistory.project_id == project.id,
        BackupHistory.status == 'success'
    ).order_by(BackupHistory.start_time.desc()).all()
    
    if len(history) <= project.keep_versions: return
    to_delete = history[project.keep_versions:]
    for record in to_delete:
        if record.file_name:
            file_path = os.path.join(project.destination_path, record.file_name)
            if os.path.exists(file_path):
                try:
                    if os.path.isdir(file_path): shutil.rmtree(file_path)
                    else: os.remove(file_path)
                except: pass
        db.delete(record)
    db.commit()

def run_backup_task(project_id: int, db: Session = None, remark: str = None):
    local_db = db or SessionLocal()
    history_record, working_path, final_encrypted_path, list_file_path = None, None, None, None
    dest_type = "cloud" 
    log_buffer = io.StringIO()
    log_buffer.write(f"================================================\n")
    log_buffer.write(f"🚀 备份任务启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_buffer.write(f"================================================\n")
    try:
        project = local_db.query(BackupProject).filter(BackupProject.id == project_id).first()
        if not project: return
        
        dest_type = project.destination_type or "cloud"
        log_buffer.write(f"[INFO] 项目名称: {project.name}\n")
        log_buffer.write(f"[INFO] 源目录:   {project.source_path}\n")
        log_buffer.write(f"[INFO] 目标目录: {project.destination_path}\n")
        if remark: log_buffer.write(f"[INFO] 任务备注: {remark}\n")
        log_buffer.write(f"------------------------------------------------\n")
        
        history_record = BackupHistory(project_id=project.id, status="running", start_time=datetime.now(), log_message="正在初始化...", progress=0, remark=remark)
        local_db.add(history_record)
        local_db.commit()

        patterns = [p.strip() for p in (project.exclude_patterns or "").split(',') if p.strip()]
        include_list = generate_manifest(project.source_path, patterns, log_buffer)
        if not include_list: raise Exception("清单为空，没有需要备份的文件。")

        total_files = len(include_list)
        processed_count = 0
        last_progress = 0
        
        def update_prog(increment=1):
            nonlocal processed_count, last_progress
            processed_count += increment
            if total_files > 0:
                pct = int((processed_count / total_files) * 100)
                if pct > last_progress:
                    last_progress = pct
                    history_record.progress = min(99, pct)
                    history_record.log_message = log_buffer.getvalue()
                    local_db.commit()

        timestamp, fmt, level = datetime.now().strftime("%Y%m%d_%H%M%S"), project.archive_format or "tgz", project.compression_level or 1
        
        if fmt == "sync":
            sync_dest = project.destination_path
            mode_str = project.sync_mode or 'overwrite'
            log_buffer.write(f"[INFO] 模式: 同步模式 ({mode_str})\n")
            if not os.path.exists(sync_dest): os.makedirs(sync_dest, exist_ok=True)
            if mode_str == 'overwrite':
                log_buffer.write("[WARN] 正在清理目标目录内容...\n")
                for item in os.listdir(sync_dest):
                    item_path = os.path.join(sync_dest, item)
                    try:
                        if os.path.isdir(item_path): shutil.rmtree(item_path)
                        else: os.remove(item_path)
                    except: pass
            
            def sync_copy(rp):
                check_stop(project_id, log_buffer)
                src, dst = os.path.join(project.source_path, rp), os.path.join(sync_dest, rp)
                if mode_str == 'incremental' and os.path.exists(dst):
                    try:
                        s_stat, d_stat = os.stat(src), os.stat(dst)
                        if s_stat.st_size == d_stat.st_size and int(s_stat.st_mtime) <= int(d_stat.st_mtime): return
                    except: pass 
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                log_buffer.write(f"[SYNC] {rp}\n")

            with concurrent.futures.ThreadPoolExecutor(max_workers=project.sync_threads or 2) as ex:
                for _ in ex.map(sync_copy, include_list): update_prog()
                
            history_record.status, history_record.end_time, history_record.progress = "success", datetime.now(), 100
            total_size = 0
            for dirpath, _, filenames in os.walk(sync_dest):
                for f in filenames: total_size += os.path.getsize(os.path.join(dirpath, f))
            history_record.file_size_bytes, history_record.file_name = total_size, "(Directory Sync)"
            log_buffer.write(f"\n[INFO] 同步成功。总容量: {total_size} bytes\n")
            history_record.log_message = log_buffer.getvalue()
            send_notification("✅ 备份成功", f"项目: {project.name}\n模式: 同步", local_db)
            return

        ext = ".7z" if fmt == "7z" else (".tar.gz" if fmt == "tgz" else ".tar")
        archive_name = f"{project.name.replace(' ','_')}_{timestamp}{ext}"
        
        if dest_type == "local":
            os.makedirs(project.destination_path, exist_ok=True)
            working_path = os.path.join(project.destination_path, archive_name)
            log_buffer.write(f"[INFO] 模式: 压缩模式 ({fmt})\n[INFO] 输出: {working_path}\n")
        else:
            cache_dir = project.cache_dir or "/data/cache"
            os.makedirs(cache_dir, exist_ok=True)
            working_path = os.path.join(cache_dir, archive_name)
            log_buffer.write(f"[INFO] 模式: 压缩模式 ({fmt})\n[INFO] 缓存: {working_path}\n")

        history_record.log_message = log_buffer.getvalue()
        local_db.commit()

        if fmt == "7z":
            list_file_path = working_path + ".list"
            with open(list_file_path, "w", encoding="utf-8") as f:
                for p in include_list: f.write(p + "\n")
            cmd = ["7z", "a", working_path, f"@{list_file_path}", f"-mx={level}", "-m0=lzma2", "-mf=off", "-bb1"]
            if project.encryption_password: cmd.extend([f"-p{project.encryption_password}", "-mhe=on"])
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=project.source_path, bufsize=1)
            for line in proc.stdout:
                log_buffer.write(line)
                if line.strip().startswith("+ "): update_prog()
                else: 
                    history_record.log_message = log_buffer.getvalue()
                    local_db.commit()
                if stop_signals.get(project_id): proc.terminate(); raise Exception("用户强制终止")
            proc.wait()
            if proc.returncode != 0: raise Exception("7z 压缩失败")
        else:
            mode = "w:gz" if fmt == "tgz" else "w"
            with tarfile.open(working_path, mode, compresslevel=level if fmt=="tgz" else None) as tar:
                for rp in include_list:
                    check_stop(project_id, log_buffer)
                    log_buffer.write(f"[PACK] {rp}\n")
                    tar.add(os.path.join(project.source_path, rp), arcname=rp)
                    update_prog()

        file_ready = working_path
        if fmt != "7z" and project.encryption_password:
            log_buffer.write("[INFO] 正在执行 AES 私有加密...\n")
            final_encrypted_path = working_path + ".enc"
            encrypt_file(working_path, final_encrypted_path, project.encryption_password, project_id)
            if os.path.exists(working_path): os.remove(working_path)
            file_ready = final_encrypted_path

        if dest_type == "cloud":
            log_buffer.write(f"[INFO] 正在上传至云端...\n")
            final_dest = os.path.join(project.destination_path, os.path.basename(file_ready))
            perform_safe_move(file_ready, final_dest)
            final_stats_path = final_dest
        else:
            final_stats_path = file_ready

        history_record.status, history_record.end_time, history_record.progress = "success", datetime.now(), 100
        history_record.file_name, history_record.file_size_bytes = os.path.basename(final_stats_path), os.stat(final_stats_path).st_size
        log_buffer.write(f"\n[INFO] 备份成功。文件: {history_record.file_name} ({history_record.file_size_bytes} bytes)\n")
        history_record.log_message = log_buffer.getvalue()
        send_notification("✅ 备份成功", f"项目: {project.name}\n文件: {history_record.file_name}", local_db)
        apply_retention_policy(project, local_db)
    except Exception as e:
        log_buffer.write(f"\n[ERROR] 任务失败: {str(e)}\n")
        if history_record:
            history_record.status, history_record.end_time = "failed", datetime.now()
            history_record.log_message = log_buffer.getvalue()
        send_notification("❌ 备份失败", f"项目: {project.name}\n原因: {str(e)}", local_db)
    finally:
        local_db.commit()
        if list_file_path and os.path.exists(list_file_path):
            try: os.remove(list_file_path)
            except: pass
        is_failed = history_record and history_record.status == "failed"
        for p in [working_path, final_encrypted_path]:
            if p and os.path.exists(p):
                if dest_type == "local" and not is_failed: continue
                try: os.remove(p)
                except: pass
        stop_signals.pop(project_id, None)
        if not db: local_db.close()

def run_restore_task(project_id: int, backup_filename: str, restore_mode: str, db: Session = None):
    local_db = db or SessionLocal()
    history_record, cache_path, decrypted_path = None, None, None
    log_buffer = io.StringIO()
    log_buffer.write(f"================================================\n")
    log_buffer.write(f"♻️ 还原任务启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_buffer.write(f"================================================\n")
    try:
        project = local_db.query(BackupProject).filter(BackupProject.id == project_id).first()
        if not project: raise Exception("项目不存在")
        log_buffer.write(f"[INFO] 项目: {project.name}\n[INFO] 文件: {backup_filename}\n")
        history_record = BackupHistory(project_id=project.id, status="running", start_time=datetime.now(), file_name=backup_filename, log_message="初始化还原...", progress=0)
        local_db.add(history_record)
        local_db.commit()
        
        src_file = os.path.join(project.destination_path, backup_filename)
        if not os.path.exists(src_file): raise Exception("备份文件不存在")
        
        cache_dir = project.cache_dir or "/data/cache"
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"restore_{backup_filename}")
        log_buffer.write(f"[INFO] 正在拉取文件至缓存: {cache_dir} ...\n")
        shutil.copy2(src_file, cache_path)
        
        restore_archive = cache_path
        if backup_filename.endswith(".enc"):
            log_buffer.write("[INFO] 执行解密...\n")
            decrypted_path = cache_path.replace(".enc", "")
            decrypt_file(cache_path, decrypted_path, project.encryption_password, project_id)
            restore_archive = decrypted_path
            
        if restore_mode == 'clean':
            log_buffer.write("[WARN] 正在清空源目录...\n")
            for f in os.listdir(project.source_path):
                p = os.path.join(project.source_path, f)
                try:
                    if os.path.isfile(p) or os.path.islink(p): os.unlink(p)
                    elif os.path.isdir(p): shutil.rmtree(p)
                except: pass
                
        os.makedirs(project.source_path, exist_ok=True)
        log_buffer.write(f"[INFO] 正在解压数据至: {project.source_path}\n")
        
        if backup_filename.endswith(".7z"):
            cmd = ["7z", "x", restore_archive, f"-o{project.source_path}", "-y"]
            if project.encryption_password: cmd.append(f"-p{project.encryption_password}")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in proc.stdout:
                log_buffer.write(line)
                history_record.progress = min(99, (history_record.progress or 0) + 1)
                history_record.log_message = log_buffer.getvalue()
                local_db.commit()
            proc.wait()
            if proc.returncode != 0: raise Exception("7z 还原失败")
        else:
            with tarfile.open(restore_archive, "r:gz" if backup_filename.endswith(".gz") else "r") as tar:
                members = tar.getmembers()
                total, count = len(members), 0
                for m in members:
                    check_stop(project_id, log_buffer)
                    if not (m.name.startswith("/") or ".." in m.name): tar.extract(m, path=project.source_path)
                    count += 1
                    pct = int((count / total) * 100)
                    if pct > (history_record.progress or 0):
                        history_record.progress = pct
                        log_buffer.write(f"[UNPACK] {m.name}\n")
                        history_record.log_message = log_buffer.getvalue()
                        local_db.commit()
                        
        history_record.status, history_record.end_time, history_record.progress = "success", datetime.now(), 100
        log_buffer.write(f"\n[INFO] 还原成功。\n")
        history_record.log_message = log_buffer.getvalue()
        send_notification("♻️ 还原成功", f"项目: {project.name}", local_db)
    except Exception as e:
        log_buffer.write(f"\n[ERROR] 还原失败: {str(e)}\n")
        if history_record:
            history_record.status, history_record.end_time = "failed", datetime.now()
            history_record.log_message = log_buffer.getvalue()
        send_notification("❌ 还原失败", f"项目: {project.name}\n原因: {str(e)}", local_db)
    finally:
        local_db.commit()
        for p in [cache_path, decrypted_path]:
            if p and os.path.exists(p):
                try: os.remove(p)
                except: pass
        stop_signals.pop(project_id, None)
        if not db: local_db.close()
