"""Flask Web 服务启动入口"""

import os
import sys

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv(os.path.join(project_root, ".env"))

from web import create_app


def main():
    import argparse
    parser = argparse.ArgumentParser(description="微信公众号 AI 日报管理系统 Web 服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="监听端口 (默认: 5000)")
    parser.add_argument("--production", action="store_true", help="使用生产模式")
    args = parser.parse_args()

    config_name = "production" if args.production else "development"
    app = create_app(config_name)

    if args.production:
        try:
            from waitress import serve
            print(f"[生产模式] 服务运行在 http://{args.host}:{args.port}")
            serve(app, host=args.host, port=args.port)
        except ImportError:
            print("[警告] waitress 未安装，使用 Flask 内置服务器")
            app.run(host=args.host, port=args.port, debug=False)
    else:
        print(f"[开发模式] 服务运行在 http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
