@echo off
chcp 65001 >nul
echo ============================================
echo   微信公众号 AI 日报系统 - 任务配置
echo ============================================
echo.

:: ============================================
:: 第一部分：定时任务配置
:: ============================================
echo [1/3] 配置定时任务...
echo.

:: 删除旧任务（如果存在）
schtasks /delete /tn "WechatAI_Hot" /f 2>nul
schtasks /delete /tn "WechatAI_Deep" /f 2>nul
schtasks /delete /tn "WechatAI_Web" /f 2>nul

:: 创建 9:00 热点新闻任务
echo 创建 9:00 热点采集任务...
schtasks /create /tn "WechatAI_Hot" /tr "python D:\WeChatAI\main.py" /sc daily /st 09:00 /rl HIGHEST /f

:: 创建 10:00 深度分析任务
echo 创建 10:00 深度分析任务...
schtasks /create /tn "WechatAI_Deep" /tr "python D:\WeChatAI\auto_generator.py" /sc daily /st 10:00 /rl HIGHEST /f

echo.
echo 定时任务创建完成！
echo.

:: ============================================
:: 第二部分：防火墙配置
:: ============================================
echo [2/3] 配置防火墙...
echo.

:: 允许 Python 通过防火墙
netsh advfirewall firewall add rule name="WechatAI_Python" dir=in action=allow program="D:\Python310\python.exe" enable=yes 2>nul

:: 允许 5000 端口
netsh advfirewall firewall add rule name="WechatAI_Port5000" dir=in action=allow protocol=tcp localport=5000 enable=yes 2>nul

echo 防火墙配置完成！
echo.

:: ============================================
:: 第三部分：显示任务列表
:: ============================================
echo [3/3] 当前任务状态
echo.
schtasks /query /tn "WechatAI*" /fo table
echo.

:: ============================================
:: 后续步骤提示
:: ============================================
echo ============================================
echo   后续步骤（请手动执行）
echo ============================================
echo.
echo 1. 安装 Windows 服务（推荐使用 NSSM）:
echo    下载 NSSM: https://nssm.cc/download
echo    然后运行:
echo    D:\WeChatAI\nssm.exe install WeChatAI_Web "D:\Python310\python.exe" "D:\WeChatAI\run_web.py --production --port 5000"
echo.
echo 2. 或者使用 Python 直接运行:
echo    python run_web.py --production
echo.
echo 3. 访问管理界面:
echo    http://localhost:5000
echo.
echo 4. 默认管理员账号:
echo    用户名: admin
echo    密码: admin123456
echo.
echo ============================================
pause
