# StageBackup

🚀 **StageBackup** 是一款专为 Linux 环境设计的轻量级、高性能数据备份管理系统。它结合了 7-Zip 的高压缩比与 AES-256 的安全性，并针对挂载网盘（如 CloudDrive2/Rclone）进行了深度优化。

![License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Backend-FastAPI-blue.svg)
![Vue](https://img.shields.io/badge/Frontend-Vue%203-brightgreen.svg)
![Docker](https://img.shields.io/badge/Docker-Unified-blue.svg)

---

## ✨ 核心特性

*   **📦 多模式备份**: 
    *   **7z 压缩**: 采用 LZMA2 算法，极致兼容性设计（解决 WinRAR 报错），支持分卷与加密。
    *   **Tar.gz 打包**: 原生 Linux 兼容性，支持私有 AES-256-GCM 加密。
    *   **同步模式**: 1:1 物理镜像，支持**全量覆盖**与**增量对比**（基于 mtime 和 size）。
*   **📂 智能存储浏览器**: 自动识别 Docker 映射的物理路径，**仅读取元数据**，绝不触发网盘内容下载，极致节省 API 开销。
*   **⚡ 实时监控**: 1% 级的平滑进度反馈，配备**黑客风格**的彩色实时流式日志终端。
*   **⏰ 任务调度**: 内置强大的定时器，支持简单间隔任务与专家级 Cron 表达式。
*   **🛡️ 鲁棒性设计**: 数据库 Schema 自愈能力，启动时自动修复缺失字段；任务导入/导出支持版本自动补全。
*   **🐳 极简部署**: 采用单镜像 (Unified Image) 方案，Nginx 与 Backend 一体化分发。

---

## 🏗️ 技术架构

*   **Frontend**: Vue 3 + Vite + Vuetify 3 (Glassmorphism UI 设计)
*   **Backend**: FastAPI + SQLAlchemy + APScheduler
*   **Engine**: 7-Zip Binary + Native Python tarfile + PBKDF2 密钥派生
*   **Proxy**: 内置 Nginx 实现前后端同源访问

---

## 🚀 快速启动

### 方式一：直接运行（推荐）
如果您已经拥有构建好的镜像：

1. 下载 `docker-compose-run.yml`。
2. 执行启动命令：
   ```bash
   docker-compose -f docker-compose-run.yml up -d
   ```

### 方式二：自行构建
1. 克隆代码：
   ```bash
   git clone https://github.com/your-username/StageBackup.git
   cd StageBackup
   ```
2. 构建并启动：
   ```bash
   docker build -t stage-backup:latest .
   docker-compose up -d
   ```

---

## 🛠️ 配置说明

*   **默认端口**: `8090` (可在 docker-compose 中修改)
*   **持久化目录**: 挂载宿主机 `./data` 到容器 `/data` 以保存数据库和配置。
*   **缓存目录**: 默认使用 `/data/cache` 处理临时文件，确保大文件还原不爆磁盘。

---

## 📝 备份说明 (Ignore Patterns)
系统预设了多项高效的过滤规则：
`__pycache__`, `node_modules`, `.git`, `target`, `dist`, `*.log` 等。
您可以在“系统设置”中通过全局模板统一管理。

---

## 🤝 贡献与反馈
欢迎通过 Issue 或 Pull Request 提交您的优化建议！

---
*Created with ❤️ for efficient data backup.*
