#!/usr/bin/env python3
"""
微信公众号 AI 日报自动化发布系统

每日自动化任务：
- 9:00 运行 main.py：采集信息 → 筛选热点 → 生成今日AI热点文章
- 10:00 运行 auto_generator.py：选择最佳文章 → 下载原文 → 生成深度分析 → 发布

使用方法:
    python main.py              # 智能运行（已有文章则跳过采集写作）
    python main.py --no-publish # 只生成内容，不发布
    python main.py --force      # 强制重新生成（忽略已有文章）

Windows 定时任务注册命令:
    # 9点任务：采集+热点
    schtasks /create /tn "WechatAI_Hot" /tr "python D:\\公众号\\main.py" /sc daily /st 09:00

    # 10点任务：深度分析
    schtasks /create /tn "WechatAI_Deep" /tr "python D:\\公众号\\auto_generator.py" /sc daily /st 10:00

查看定时任务:
    schtasks /query /tn "WechatAI_Hot" /fo list
    schtasks /query /tn "WechatAI_Deep" /fo list

删除定时任务:
    schtasks /delete /tn "WechatAI_Hot"
    schtasks /delete /tn "WechatAI_Deep"
"""

import argparse
import sys

from config.settings import PROJECT_ROOT
from pipeline import Pipeline
from utils.logger import get_logger

_log = get_logger("main")


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号 AI 日报自动化发布系统"
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="只生成内容，不发布到微信",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成（忽略已有文章）",
    )
    args = parser.parse_args()

    _log.info("=" * 60)
    _log.info("微信公众号 AI 日报系统启动")
    _log.info("项目目录: %s", PROJECT_ROOT)
    _log.info("=" * 60)

    try:
        pipeline = Pipeline()
        report = pipeline.run(
            skip_publish=args.no_publish,
            force_regenerate=args.force,
        )

        # 输出摘要
        print("\n" + "=" * 60)
        print("执行摘要:")
        print(f"  状态: {report['status']}")
        if report.get("from_cache"):
            print(f"  模式: 使用已有文章（跳过采集写作）")
        print(f"  采集: {report['collected_count']} 条")
        print(f"  筛选: {report['selected_count']} 条")
        print(f"  文章: {report['article_title']}")
        print(f"  配图: {report['images_generated']} 张")
        print(f"  草稿: {'已创建' if report['draft_created'] else '未创建'}")
        print(f"  耗时: {report['duration_seconds']} 秒")

        if report["errors"]:
            print(f"  错误: {', '.join(report['errors'])}")

        print("=" * 60)

        # 非 0 退出码表示失败
        if report["status"] != "success":
            sys.exit(1)

    except Exception as e:
        _log.exception("系统异常退出: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
