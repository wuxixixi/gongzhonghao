#!/usr/bin/env python3
"""
微信公众号 AI 日报自动化发布系统

入口文件，由 Windows 任务计划程序每天 9:00 调用。

使用方法:
    python main.py              # 完整运行（采集→写作→发布）
    python main.py --no-publish # 只生成内容，不发布

Windows 定时任务注册命令:
    schtasks /create /tn "WechatAIDaily" /tr "python D:\\公众号\\main.py" /sc daily /st 09:00

删除定时任务:
    schtasks /delete /tn "WechatAIDaily"
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
    args = parser.parse_args()

    _log.info("=" * 60)
    _log.info("微信公众号 AI 日报系统启动")
    _log.info("项目目录: %s", PROJECT_ROOT)
    _log.info("=" * 60)

    try:
        pipeline = Pipeline()
        report = pipeline.run(skip_publish=args.no_publish)

        # 输出摘要
        print("\n" + "=" * 60)
        print("执行摘要:")
        print(f"  状态: {report['status']}")
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
