# 设置微信公众号 AI 日报定时任务

# 定义任务参数
$hotTaskName = "WechatAI_Hot"
$hotTaskPath = "D:\gongzhonghao\main.py"
$hotTriggerTime = "9:00am"

$deepTaskName = "WechatAI_Deep"
$deepTaskPath = "D:\gongzhonghao\auto_generator.py"
$deepTriggerTime = "10:00am"

Write-Host "正在设置微信公众号 AI 日报定时任务..." -ForegroundColor Green

# 删除旧任务（如果存在）
try {
    Unregister-ScheduledTask -TaskName $hotTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $deepTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已清理旧任务" -ForegroundColor Yellow
} catch {}

# 创建 9:00 热点新闻任务
try {
    $hotAction = New-ScheduledTaskAction -Execute "python" -Argument $hotTaskPath
    $hotTrigger = New-ScheduledTaskTrigger -Daily -At $hotTriggerTime
    Register-ScheduledTask -TaskName $hotTaskName -Action $hotAction -Trigger $hotTrigger -Force
    Write-Host "✓ 创建任务: $hotTaskName (每天 $hotTriggerTime)" -ForegroundColor Green
} catch {
    Write-Host "✗ 创建任务失败: $hotTaskName - $($_.Exception.Message)" -ForegroundColor Red
}

# 创建 10:00 深度分析任务
try {
    $deepAction = New-ScheduledTaskAction -Execute "python" -Argument $deepTaskPath
    $deepTrigger = New-ScheduledTaskTrigger -Daily -At $deepTriggerTime
    Register-ScheduledTask -TaskName $deepTaskName -Action $deepAction -Trigger $deepTrigger -Force
    Write-Host "✓ 创建任务: $deepTaskName (每天 $deepTriggerTime)" -ForegroundColor Green
} catch {
    Write-Host "✗ 创建任务失败: $deepTaskName - $($_.Exception.Message)" -ForegroundError Red
}

Write-Host "`n定时任务设置完成！" -ForegroundColor Green
Write-Host "可使用以下命令查看任务:" -ForegroundColor Cyan
Write-Host "  schtasks /query /tn WechatAI* /fo table" -ForegroundColor Gray

pause
