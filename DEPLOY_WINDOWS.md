# Windows Server 部署指南

本文档详细介绍如何在 Windows Server 上部署微信公众号 AI 日报系统。

## 目录

1. [系统要求](#1-系统要求)
2. [目录结构规划](#2-目录结构规划)
3. [环境配置](#3-环境配置)
4. [安装依赖](#4-安装依赖)
5. [配置环境变量](#5-配置环境变量)
6. [数据库初始化](#6-数据库初始化)
7. [前端构建](#7-前端构建)
8. [配置 Windows 服务](#8-配置-windows-服务)
9. [防火墙配置](#9-防火墙配置)
10. [配置定时任务](#10-配置定时任务)
11. [监控和维护](#11-监控和维护)
12. [常见问题](#12-常见问题)

---

## 1. 系统要求

### 硬件要求
| 配置 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB SSD |
| 带宽 | 5 Mbps | 10 Mbps |

### 软件要求
- **操作系统**: Windows Server 2019/2022
- **Python**: 3.10 或更高版本
- **Node.js**: 18.x (用于构建前端)
- **Web 服务器**: 可选 (IIS 或 Nginx for Windows)

---

## 2. 目录结构规划

建议按以下结构部署：

```
D:\
├── WeChatAI\                 # 项目根目录
│   ├── app\                  # 业务代码
│   ├── web\                  # Web 管理界面
│   │   ├── frontend\         # 前端源码
│   │   │   └── dist\          # 构建后的静态文件
│   │   ├── api\               # API 蓝图
│   │   ├── models\            # 数据模型
│   │   └── services\          # 业务服务
│   ├── instance\              # 数据库文件
│   ├── logs\                  # 日志目录
│   ├── 260101\                # 文章数据目录
│   ├── 260102\
│   ├── ...
│   ├── .env                   # 环境配置
│   ├── main.py                # 主程序
│   ├── auto_generator.py      # 深度分析
│   ├── run_web.py             # Web 服务入口
│   └── requirements.txt       # Python 依赖
│
├── Python310\                 # Python 安装目录
│   └── python.exe
│
└── nodejs\                    # Node.js 安装目录
    └── node.exe
```

---

## 3. 环境配置

### 3.1 安装 Python

1. 从 https://www.python.org/downloads/ 下载 Python 3.10+
2. 安装时勾选 **Add Python to PATH**
3. 验证安装:
```cmd
python --version
pip --version
```

### 3.2 安装 Node.js

1. 从 https://nodejs.org 下载 LTS 版本
2. 验证安装:
```cmd
node --version
npm --version
```

### 3.3 配置环境变量

在系统环境变量中添加：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| PYTHON_HOME | D:\Python310 | Python 安装目录 |
| NODE_HOME | D:\nodejs | Node.js 安装目录 |
| PATH | 添加 ;%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%NODE_HOME% | 追加到 PATH |

---

## 4. 安装依赖

### 4.1 安装 Python 依赖

```cmd
cd D:\WeChatAI
pip install -r requirements.txt
```

### 4.2 安装前端依赖

```cmd
cd D:\WeChatAI\web\frontend
npm install
```

---

## 5. 配置环境变量

创建或编辑 `.env` 文件：

```bash
# ==================== Flask 配置 ====================
FLASK_ENV=production
FLASK_SECRET_KEY=生成一个随机密钥
JWT_SECRET_KEY=生成一个随机密钥

# ==================== LLM 配置 ====================
LLM_PROVIDER=dmxapi
DMXAPI_BASE_URL=https://api.dmxapi.com/v1
DMXAPI_API_KEY=your_api_key
LLM_MODEL=gpt-4o

# ==================== 微信公众号 ====================
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# ==================== 搜索 API ====================
TAVILY_API_KEY=your_tavily_key

# ==================== 管理后台 ====================
ADMIN_DEFAULT_PASSWORD=your_strong_password
```

**生成随机密钥**:
```cmd
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 6. 数据库初始化

首次启动时数据库会自动创建。手动初始化：

```cmd
cd D:\WeChatAI
python -c "from web import create_app; app = create_app('production'); print('数据库初始化成功')"
```

数据库文件位置: `D:\WeChatAI\instance\app.db`

---

## 7. 前端构建

```cmd
cd D:\WeChatAI\web\frontend
npm run build
```

构建产物位于: `D:\WeChatAI\web\frontend\dist`

---

## 8. 配置 Windows 服务

### 8.1 使用 NSSM (推荐)

NSSM (Non-Sucking Service Manager) 是 Windows 服务管理器:

1. **下载 NSSM**: https://nssm.cc/download

2. **解压并安装服务**:

```cmd
# 复制 nssm.exe 到项目目录
copy nssm.exe D:\WeChatAI\

# 安装 Web 服务
D:\WeChatAI\nssm.exe install WeChatAI_Web "D:\Python310\python.exe" "D:\WeChatAI\run_web.py --production --port 5000"
D:\WeChatAI\nssm.exe set WeChatAI_Web AppDirectory "D:\WeChatAI"
D:\WeChatAI\nssm.exe set WeChatAI_Web DisplayName "WeChat AI News Web Service"
D:\WeChatAI\nssm.exe set WeChatAI_Web Description "微信公众号 AI 日报系统 Web 管理界面"
D:\WeChatAI\nssm.exe set WeChatAI_Web AppRestartDelay 5000

# 设置自动启动
D:\WeChatAI\nssm.exe set WeChatAI_Web Start SERVICE_AUTO_START

# 启动服务
D:\WeChatAI\nssm.exe start WeChatAI_Web

# 查看状态
D:\WeChatAI\nssm.exe status WeChatAI_Web
```

### 8.2 使用 PowerShell 创建服务

```powershell
# 使用 Windows 内置 sc 命令
sc create WeChatAI_Web binPath= "D:\Python310\python.exe D:\WeChatAI\run_web.py --production --port 5000" DisplayName= "WeChat AI News" start= auto
sc description WeChatAI_Web "微信公众号 AI 日报系统 Web 服务"
sc start WeChatAI_Web
```

### 8.3 常用服务管理命令

```cmd
# 查看服务状态
sc query WeChatAI_Web

# 启动服务
sc start WeChatAI_Web

# 停止服务
sc stop WeChatAI_Web

# 删除服务
sc delete WeChatAI_Web
```

---

## 9. 防火墙配置

### 9.1 使用 Windows 防火墙

```cmd
# 允许 Python 通过防火墙
netsh advfirewall firewall add rule name="WeChatAI_Python" dir=in action=allow program="D:\Python310\python.exe" enable=yes

# 允许 5000 端口
netsh advfirewall firewall add rule name="WeChatAI_Port5000" dir=in action=allow protocol=tcp localport=5000 enable=yes
```

### 9.2 在 IIS 中托管 (可选)

如果需要使用 IIS:

1. 安装 IIS 及 URL Rewrite 模块
2. 创建 web.config:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="API" stopProcessing="true">
          <match url="^api/(.*)" />
          <conditions>
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
          </conditions>
          <action type="Rewrite" url="http://localhost:5000/api/{R:1}" />
        </rule>
        <rule name="StaticFiles" stopProcessing="true">
          <match url="^(.*)" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" />
          </conditions>
          <action type="Rewrite" url="/web/frontend/dist/{R:1}" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

---

## 10. 配置定时任务

### 10.1 使用批处理脚本（推荐）

项目已包含自动化配置脚本:

```cmd
cd D:\WeChatAI
setup_tasks.bat
```

脚本会自动完成:
- 创建每日 9:00 热点采集任务
- 创建每日 10:00 深度分析任务
- 配置防火墙规则

### 10.2 手动配置

```cmd
# 热点采集任务 (每日 9:00)
schtasks /create /tn "WeChatAI_Hot" /tr "python D:\WeChatAI\main.py" /sc daily /st 09:00 /rl HIGHEST /f

# 深度分析任务 (每日 10:00)
schtasks /create /tn "WeChatAI_Deep" /tr "python D:\WeChatAI\auto_generator.py" /sc daily /st 10:00 /rl HIGHEST /f
```

### 10.3 定时任务管理

```cmd
# 查看所有任务
schtasks /query /tn "WeChatAI*" /fo table

# 删除任务
schtasks /delete /tn "WeChatAI_Hot" /f

# 立即运行任务
schtasks /run /tn "WeChatAI_Hot"
```

---

## 11. 监控和维护

### 11.1 日志查看

```cmd
# 查看 Web 服务日志 (如果使用 NSSM)
type D:\WeChatAI\logs\nssm.log

# 使用 Event Viewer
eventvwr.msc
```

### 11.2 性能监控

使用 Windows 任务管理器监控:
- Python 进程 CPU/内存使用
- 网络连接数

### 11.3 自动重启脚本

创建监控脚本 `monitor.bat`:

```cmd
@echo off
set SERVICE_NAME=WeChatAI_Web
set RESTART_COUNT=0
set MAX_RESTART=3

:CHECK
ping -n 60 127.0.0.1 >nul

:: 检查服务是否运行
sc query %SERVICE_NAME% | find "RUNNING" >nul
if %errorlevel% neq 0 (
    echo %date% %time% - Service stopped, restarting... >> D:\WeChatAI\logs\monitor.log
    sc start %SERVICE_NAME%
    set /a RESTART_COUNT+=1
    if %RESTART_COUNT% geq %MAX_RESTART% (
        echo %date% %time% - Max restart reached, sending alert >> D:\WeChatAI\logs\monitor.log
        :: 这里可以添加邮件通知
    )
) else (
    set RESTART_COUNT=0
)

goto CHECK
```

### 11.4 备份脚本

创建 `backup.bat`:

```cmd
@echo off
set BACKUP_DIR=D:\Backup\WeChatAI
set DATE=%date:~0,4%%date:~5,2%%date:~8,2%

mkdir "%BACKUP_DIR%" 2>nul

:: 备份数据库
copy "D:\WeChatAI\instance\app.db" "%BACKUP_DIR%\app_%DATE%.db"

:: 备份配置
copy "D:\WeChatAI\.env" "%BACKUP_DIR%\env_%DATE%"

:: 压缩文章数据
powershell -Command "Compress-Archive -Path 'D:\WeChatAI\26*' -DestinationPath '%BACKUP_DIR%\articles_%DATE%.zip' -Force"

echo Backup completed: %DATE%
```

设置为每日任务:
```cmd
schtasks /create /tn "WeChatAI_Backup" /tr "D:\WeChatAI\backup.bat" /sc daily /st 03:00 /f
```

---

## 12. 常见问题

### 问题 1: 服务无法启动

**检查步骤**:
1. 验证 Python 路径正确
2. 检查 .env 文件配置
3. 查看事件查看器日志

```cmd
eventvwr.msc
# 查看 Application 日志
```

### 问题 2: 端口被占用

```cmd
# 查找占用 5000 端口的进程
netstat -ano | findstr :5000

# 结束占用进程
taskkill /PID <PID> /F
```

### 问题 3: 内存不足

Windows Server 内存不足时:
1. 增加虚拟内存
2. 关闭不必要的服务
3. 监控 Python 进程内存使用

### 问题 4: 中文路径问题

确保代码文件使用 UTF-8 编码:
```cmd
chcp 65001
```

### 问题 5: 微信 Token 刷新失败

确保服务器时间正确:
```cmd
w32tm /resync
```

---

## 快速部署检查清单

```cmd
[ ] Python 3.10+ 已安装
[ ] Node.js 18+ 已安装
[ ] pip install -r requirements.txt
[ ] npm install (前端目录)
[ ] 配置 .env 文件
[ ] npm run build (前端构建)
[ ] python run_web.py --production (测试运行)
[ ] 配置 Windows 服务 (NSSM)
[ ] 配置防火墙
[ ] 配置定时任务
[ ] 测试完整流程
```

---

## 技术支持

如遇问题请检查:
1. `D:\WeChatAI\logs\` 目录下的日志
2. Windows 事件查看器
3. 服务运行状态: `sc query WeChatAI_Web`
