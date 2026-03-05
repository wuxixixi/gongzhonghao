@echo off
chcp 65001 >nul
echo 设置微信公众号 AI 日报定时任务...

:: 删除旧任务（如果存在）
schtasks /delete /tn "WechatAI_Hot" /f 2>nul
schtasks /delete /tn "WechatAI_Deep" /f 2>nul

:: 创建 9:00 热点新闻任务
echo 创建 9:00 热点新闻任务...
schtasks /create /tn "WechatAI_Hot" /tr "python D:\gongzhonghao\main.py" /sc daily /st 09:00 /f

:: 创建 10:00 深度分析任务
echo 创建 10:00 深度分析任务...
schtasks /create /tn "WechatAI_Deep" /tr "python D:\gongzhonghao\auto_generator.py" /sc daily /st 10:00 /f

echo.
echo 任务创建完成！
echo.
schtasks /query /tn "WechatAI*" /fo table
pause
