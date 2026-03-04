# 微信公众号 AI 日报自动化发布系统

自动化采集 AI 热点资讯，生成并发布微信公众号文章。

## 功能特性

- **数据采集**：自动从 arXiv、GitHub、HuggingFace、新闻网站采集 AI 资讯
- **智能筛选**：基于热度、相关性、质量多维度筛选优质内容
- **文章生成**：自动撰写热点分析文章
- **图片生成**：支持 FLUX 生成封面和配图
- **自动发布**：一键发布到微信公众号草稿箱
- **定时任务**：支持 Windows 定时任务自动化运行

## 目录结构

```
公众号/
├── app/                    # 主应用模块
│   ├── collectors/          # 数据采集
│   │   ├── arxiv_collector.py      # arXiv 论文采集
│   │   ├── github_collector.py     # GitHub Trending 采集
│   │   ├── huggingface_collector.py # HuggingFace 采集
│   │   └── news_collector.py      # 新闻采集
│   ├── processors/         # 文章处理
│   │   ├── article_downloader.py  # 文章下载
│   │   ├── article_selector.py    # 文章选择
│   │   ├── filter.py              # 内容过滤
│   │   ├── quality_checker.py     # 质量检查
│   │   └── writer.py               # 文章写作
│   ├── imaging/            # 图片生成
│   │   └── flux_generator.py      # FLUX 图片生成
│   ├── publisher/          # 发布模块
│   │   ├── draft_creator.py       # 草稿创建
│   │   ├── media_uploader.py      # 媒体上传
│   │   └── wechat_client.py       # 微信客户端
│   ├── storage/            # 存储模块
│   │   └── local_storage.py       # 本地存储
│   ├── config/             # 配置模块
│   │   └── settings.py            # 配置管理
│   └── utils/             # 工具模块
│       ├── logger.py              # 日志
│       └── retry.py               # 重试机制
├── scripts/                # 脚本目录
│   ├── pipeline.py         # 处理流水线
│   └── scheduler.py       # 定时调度
├── main.py                 # 主程序入口
├── auto_generator.py       # 自动生成器
├── test_wechat.py          # 微信测试
├── requirements.txt       # 依赖
└── README.md              # 说明文档
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. 复制配置示例文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，配置必要参数：
   - 微信公众号 AppID 和 AppSecret
   - FLUX API Key
   - 其他可选配置

### 运行

```bash
# 智能运行（已有文章则跳过采集写作）
python main.py

# 只生成内容，不发布到微信
python main.py --no-publish

# 强制重新生成（忽略已有文章）
python main.py --force
```

### 定时任务（Windows）

```bash
# 9点任务：采集+热点
schtasks /create /tn "WechatAI_Hot" /tr "python D:\公众号\main.py" /sc daily /st 09:00

# 10点任务：深度分析
schtasks /create /tn "WechatAI_Deep" /tr "python D:\公众号\auto_generator.py" /sc daily /st 10:00
```

## 依赖

- Python 3.10+
- requests
- openai
- wechatpy

## License

MIT
