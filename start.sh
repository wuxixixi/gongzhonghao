#!/bin/bash
# 微信公众号 AI 日报系统启动脚本

# 切换到项目目录
cd /var/www/wechat-ai

# 激活虚拟环境
source venv/bin/activate

# 启动 Flask Web 服务
exec python run_web.py --production --host 0.0.0.0 --port 5000
