# 微信公众号 AI 日报系统 - 生产环境部署指南

## 1. 服务器环境要求

### 操作系统
- **推荐**: Ubuntu 20.04+ / Debian 11+ (Linux)
- **也支持**: Windows Server 2019+ (使用计划任务)

### 硬件配置
| 配置 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB SSD |
| 带宽 | 5 Mbps | 10 Mbps |

### 软件要求
- **Python**: 3.10+
- **Node.js**: 18+ (用于构建前端)
- **PM2**: Node.js 进程管理器 (推荐)
- **Nginx**: 反向代理 (推荐)

---

## 2. 项目部署步骤

### 2.1 创建部署目录

```bash
# 创建项目目录
mkdir -p /var/www/wechat-ai
cd /var/www/wechat-ai

# 使用 git 克隆或上传项目
# git clone <your-repo-url> .
```

### 2.2 安装系统依赖

```bash
# Ubuntu/Debian
apt update
apt install -y python3 python3-pip python3-venv git nginx

# CentOS/RHEL
yum install -y python310 python310-pip git nginx

# 安装 Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
```

### 2.3 创建虚拟环境

```bash
cd /var/www/wechat-ai

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2.4 环境变量配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**.env 必需配置项**:

```bash
# ==================== LLM 配置 ====================
LLM_PROVIDER=dmxapi
DMXAPI_BASE_URL=https://api.dmxapi.com/v1
DMXAPI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o

# ==================== 微信公众号 ====================
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# ==================== 搜索 API ====================
TAVILY_APIavily_key

_KEY=your_t# ==================== Flask 配置 ====================
FLASK_ENV=production
FLASK_SECRET_KEY=生成一个随机密钥
JWT_SECRET_KEY=生成一个随机密钥

# ==================== 管理后台 ====================
ADMIN_DEFAULT_PASSWORD=你的强密码
```

**生成随机密钥**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2.5 前端构建

```bash
cd /var/www/wechat-ai/web/frontend

# 安装前端依赖
npm install

# 构建生产版本
npm run build
```

### 2.6 数据库初始化

首次启动时会自动创建 SQLite 数据库 (`instance/app.db`):

```bash
# 测试数据库初始化
cd /var/www/wechat-ai
source venv/bin/activate
python -c "from web import create_app; app = create_app('production'); print('数据库初始化成功')"
```

---

## 3. Web 服务启动方式

### 3.1 直接运行 (开发/测试)

```bash
cd /var/www/wechat-ai
source venv/bin/activate
python run_web.py --production --port 5000
```

### 3.2 使用 PM2 (推荐 - 生产环境)

```bash
# 安装 PM2
npm install -g pm2

# 创建启动脚本
nano start.sh
```

**start.sh 内容**:
```bash
#!/bin/bash
cd /var/www/wechat-ai
source venv/bin/activate
exec python run_web.py --production --port 5000
```

```bash
# 添加执行权限
chmod +x start.sh

# 使用 PM2 启动
pm2 start start.sh --name wechat-ai

# 设置开机自启
pm2 startup
pm2 save
```

**常用 PM2 命令**:
```bash
pm2 status                    # 查看状态
pm2 logs wechat-ai           # 查看日志
pm2 restart wechat-ai        # 重启服务
pm2 stop wechat-ai           # 停止服务
pm2 delete wechat-ai         # 删除进程
```

### 3.3 使用 Nginx 反向代理

创建 Nginx 配置:

```bash
nano /etc/nginx/sites-available/wechat-ai
```

**配置内容**:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    # 前端静态文件
    location / {
        root /var/www/wechat-ai/web/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持 (如需要)
    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# 启用站点
ln -s /etc/nginx/sites-available/wechat-ai /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重启 Nginx
systemctl restart nginx
```

### 3.4 配置 HTTPS (推荐)

使用 Let's Encrypt 免费证书:

```bash
# 安装 Certbot
apt install -y certbot python3-certbot-nginx

# 获取证书 (需要域名已解析到服务器)
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

---

## 4. 定时任务配置

### 4.1 Linux Crontab

```bash
crontab -e
```

**添加以下任务**:
```cron
# 每日 9:00 运行热点采集
0 9 * * * cd /var/www/wechat-ai && /var/www/wechat-ai/venv/bin/python main.py >> /var/log/wechat-ai/main.log 2>&1

# 每日 10:00 运行深度分析
0 10 * * * cd /var/www/wechat-ai && /var/www/wechat-ai/venv/bin/python auto_generator.py >> /var/log/wechat-ai/auto.log 2>&1
```

```bash
# 创建日志目录
mkdir -p /var/log/wechat-ai
```

### 4.2 使用 PM2 定时任务 (替代 Crontab)

```bash
# 安装 PM2 模块
pm2 install pm2-logrotate
pm2 install cron

# 添加定时任务
pm2 start wechat-ai --cron "0 9 * * *" --no-autorestart
```

---

## 5. 服务监控与保障

### 5.1 PM2 监控

```bash
# 查看实时日志
pm2 logs wechat-ai --lines 100

# 监控面板
pm2 monit

# 查看进程信息
pm2 info wechat-ai
```

### 5.2 系统服务 (systemd)

创建 systemd 服务:

```bash
nano /etc/systemd/system/wechat-ai.service
```

**内容**:
```ini
[Unit]
Description=WeChat AI News System
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/wechat-ai
Environment="PATH=/var/www/wechat-ai/venv/bin"
ExecStart=/var/www/wechat-ai/venv/bin/python run_web.py --production --port 5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
systemctl daemon-reload
systemctl enable wechat-ai
systemctl start wechat-ai
systemctl status wechat-ai
```

### 5.3 健康检查脚本

```bash
nano /usr/local/bin/healthcheck.sh
```

```bash
#!/bin/bash
# 健康检查脚本

# 检查 Web 服务
if curl -sf http://127.0.0.1:5000/api/monitor/status > /dev/null 2>&1; then
    echo "OK"
    exit 0
else
    echo "FAIL"
    exit 1
fi
```

```bash
chmod +x /usr/local/bin/healthcheck.sh

# 添加到 crontab 每分钟检查
* * * * * /usr/local/bin/healthcheck.sh || pm2 restart wechat-ai
```

### 5.4 日志管理

```bash
# 限制日志大小 (使用 PM2)
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true
```

---

## 6. 目录权限设置

```bash
# 创建专用用户 (推荐)
useradd -r -s /bin/false wechat-ai

# 设置目录权限
chown -R wechat-ai:wechat-ai /var/www/wechat-ai

# 确保日志目录可写
mkdir -p /var/log/wechat-ai
chown -R wechat-ai:wechat-ai /var/log/wechat-ai

# 只读目录 (保护敏感文件)
chmod 750 /var/www/wechat-ai/.env
chmod 640 /var/www/wechat-ai/instance/app.db
```

---

## 7. 常见问题及解决方案

### 问题 1: 微信 API 返回 IP 不在白名单

**解决方案**:
1. 运行测试脚本获取服务器 IP: `python test_wechat.py`
2. 登录微信公众号后台 → 设置与开发 → 基本配置 → IP白名单
3. 添加服务器公网 IP

### 问题 2: 前端页面 404

**检查项**:
1. 前端是否已构建: `ls -la web/frontend/dist/`
2. Nginx 配置是否正确
3. 静态文件路径是否匹配

### 问题 3: 定时任务不执行

**检查项**:
```bash
# 查看 cron 日志
tail -f /var/log/syslog

# 测试脚本是否可以手动执行
cd /var/www/wechat-ai
source venv/bin/activate
python main.py
```

### 问题 4: 内存不足导致崩溃

**解决方案**:
1. 增加交换空间:
```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```
2. 优化 Python 内存使用:
```python
# 在代码中添加
import gc
gc.collect()
```

### 问题 5: 服务启动失败

**排查步骤**:
```bash
# 1. 检查端口是否被占用
lsof -i :5000

# 2. 检查 Python 环境
source venv/bin/activate
python -c "import flask; print(flask.__version__)"

# 3. 查看详细错误日志
pm2 logs wechat-ai --err --nostream
```

### 问题 6: 数据库锁定

**解决方案**:
```bash
# 确保没有其他进程访问数据库
lsof instance/app.db

# 如需重置，删除数据库文件（会丢失用户数据）
rm instance/app.db
python -c "from web import create_app; create_app()"
```

---

## 8. 安全加固建议

### 8.1 防火墙配置

```bash
# 只开放必要端口
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### 8.2 定期备份

```bash
# 备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/wechat-ai"

mkdir -p $BACKUP_DIR

# 备份数据库
cp /var/www/wechat-ai/instance/app.db $BACKUP_DIR/db_$DATE.db

# 备份配置
cp /var/www/wechat-ai/.env $BACKUP_DIR/env_$DATE

# 备份文章数据
tar -czf $BACKUP_DIR/articles_$DATE.tar.gz /var/www/wechat-ai/26* /var/www/wechat-ai/deep_analysis

# 删除 7 天前的备份
find $BACKUP_DIR -mtime +7 -delete
```

### 8.3 监控告警

使用 UptimeRobot 或类似服务监控:
- 监控 URL: `http://your-domain.com/api/monitor/status`
- 告警邮箱: your@email.com

---

## 9. 快速部署脚本

```bash
#!/bin/bash
# 一键部署脚本 (Ubuntu 20.04+)

set -e

echo "=== 微信公众号 AI 日报系统部署 ==="

# 1. 安装系统依赖
echo "[1/7] 安装系统依赖..."
apt update && apt install -y python3 python3-pip python3-venv git nginx curl

# 2. 创建目录
echo "[2/7] 创建项目目录..."
mkdir -p /var/www/wechat-ai
cd /var/www/wechat-ai

# 3. 部署代码 (需要先上传)
echo "[3/7] 请将项目文件上传到 /var/www/wechat-ai 后继续"
echo "完成后按回车..."
read

# 4. 创建虚拟环境
echo "[4/7] 创建虚拟环境并安装依赖..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 构建前端
echo "[5/7] 构建前端..."
cd web/frontend
npm install
npm run build
cd ../..

# 6. 配置环境变量
echo "[6/7] 配置环境变量..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 文件配置必要参数"
fi

# 7. 启动服务
echo "[7/7] 启动服务..."
chmod +x start.sh 2>/dev/null || true

echo ""
echo "=== 部署完成 ==="
echo "1. 编辑 .env 配置必要参数"
echo "2. 运行: pm2 start start.sh --name wechat-ai"
echo "3. 配置 Nginx 反向代理"
echo "4. 访问 http://your-server-ip:5000"
```

---

## 10. 联系支持

如遇到部署问题，请检查:
1. `/var/log/wechat-ai/` 目录下的日志文件
2. `pm2 logs wechat-ai` 输出
3. `systemctl status wechat-ai` 服务状态
