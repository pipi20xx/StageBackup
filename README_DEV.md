# StageBackup 核心开发与技术架构文档

本文档提供 StageBackup 系统的全维度技术解析，涵盖架构设计、核心算法、存储模型及生产部署逻辑。

---

## 1. 技术栈与单镜像架构
*   **前端**: Vue 3 (Composition API), Vite, Vuetify 3 (Material Design).
*   **后端**: FastAPI (Asynchronous Python), SQLAlchemy (ORM), APScheduler.
*   **容器化**: 采用**单镜像 (Unified Image)** 方案。通过 Docker 多阶段构建，将 Nginx (前端+反向代理) 与 Python (后端) 整合在同一个容器内运行。
*   **网络**: 前端通过 `/api/` 路径透明转发至本地 127.0.0.1:6996，无需处理跨域 (CORS) 问题。

---

## 2. 存储与自愈模型

### 2.1 数据库 (SQLite)
数据库文件位于 `/data/backup_system.db`。系统具备 **Schema 自愈能力**：
*   **实现**: `schema_check.py` 会在每次启动时检测表结构。
*   **自动化**: 自动补全 `sync_mode`, `progress`, `remark` 等字段，确保版本升级时功能平滑切换。

### 2.2 持久化缓存 (Cache)
*   **路径**: `/data/cache`。
*   **设计**: 放弃了容器不稳定的内部 `/tmp`，改用数据盘挂载的持久化缓存。
*   **用途**: 用于压缩中转、AES 加密及还原拉取。确保处理超大文件时不会因容器磁盘限额而失败。

---

## 3. 核心功能解析

### 3.1 备份模式
*   **同步模式 (Sync)**: 目标路径直接设为用户指定位置。支持**覆盖 (Overwrite)** 镜像与**增量 (Incremental)** 对比（基于 mtime/size）。
*   **7z 压缩**: 强制使用 `-m0=lzma2` 和 `-mf=off` 确保 WinRAR 兼容性。指定行缓冲读取，实现 1% 级的进度反馈。
*   **Tar.gz (tgz)**: 使用 Python 原生 `tarfile` 流式处理，支持文件级进度更新。

### 3.2 存储浏览器 (Smart Explorer)
*   **真·智能识别**: 后端动态解析 `/proc/mounts`，自动区分 Docker 映射的物理磁盘路径与系统路径。
*   **极致性能**: 仅读取元数据 (Metadata)，**绝不读取文件内容**。在挂载网盘上浏览时，无 API 额外开销，不会触发文件下载。

### 3.3 任务迁移 (Import/Export)
*   **全量导出**: 导出包含项目配置、过滤规则及**定时计划 (Schedule)** 的全量 JSON。
*   **智能导入**: 通过 Pydantic 模型自动补全缺失字段，确保新旧版本配置的强兼容性。

---

## 4. UI/UX 规范

### 4.1 统一终端风格 (Terminal UI)
*   **着色规则**:
    *   `[INFO]`: 蓝 (Cyan)
    *   `[ADD]/[SYNC]/[PACK]`: 绿 (Green)
    *   `[SKIP]`: 黄 (Yellow)
    *   `[ERROR]`: 红 (Red)
*   **视口优化**: 采用**大视野单滚动条**设计。日志窗口随内容自适应高度，由外层容器统一控制滚动，消除嵌套滚动条的违和感。

### 4.2 任务管理
*   **运行备注**: 支持手动触发时填写 Remark，永久记录在审计日志中。
*   **进度感知**: 后端同步写入 `log_message` 缓冲区，前端实现实时流式日志滚动。

---

## 5. 生产部署指南

1.  **构建镜像**:
    ```bash
    docker build -t stage-backup:latest .
    ```
2.  **生产运行**:
    使用 `docker-compose-run.yml`。
    ```bash
    docker-compose -f docker-compose-run.yml up -d
    ```

---
*Created by Gemini CLI Assistant - 2025-12-20*
