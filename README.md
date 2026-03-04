# 微信公众号 AI 日报自动化发布系统

自动化采集 AI 热点资讯，生成并发布微信公众号文章。

## 功能特性

- **数据采集**：自动从 arXiv、GitHub、HuggingFace、新闻网站采集 AI 资讯
- **智能筛选**：基于热度、相关性、质量多维度筛选优质内容
- **文章生成**：自动撰写热点分析文章
- **图片生成**：支持 FLUX 生成封面和配图
- **自动发布**：一键发布到微信公众号草稿箱

## 目录结构

```
公众号/
├── collectors/          # 数据采集模块
│   ├── arxiv_collector.py
│   ├── github_collector.py
│   ├── huggingface_collector.py
│   └── news_collector.py
├── processors/         # 文章处理模块
│   ├── article_downloader.py
│   ├── article_selector.py
│   ├── filter.py
│   └── writer.py
├── imaging/           # 图片生成模块
│   └── flux_generator.py
├── publisher/         # 发布模块
│   ├── draft_creator.py
│   ├── media_uploader.py
│   └── wechat_client.py
├── storage/           # 存储模块
│   └── local_storage.py
├── utils/             # 工具模块
│   ├── logger.py
│   └── retry.py
├── config/            # 配置模块
│   └── settings.py
├── main.py            # 主程序入口
├── auto_generator.py  # 自动生成器
├── scheduler.py       # 定时任务
└── requirements.txt   # 依赖
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

2. 编辑 `.env` 文件，配置以下内容：
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

## 定时任务（Windows）

创建每日定时任务：

```bash
# 9点任务：采集+热点
schtasks /create /tn "WechatAI_Hot" /tr "python D:\公众号\main.py" /sc daily /st 09:00

# 10点任务：深度分析
schtasks /create /tn "WechatAI_Deep" /tr "python D:\公众号\auto_generator.py" /sc daily /st 10:00
```

查看/删除任务：

```bash
schtasks /query /tn "WechatAI_Hot" /fo list
schtasks /delete /tn "WechatAI_Hot"
```

## 依赖

- Python 3.10+
- requests
- openai (FLUX)
- wechatpy

## License

MIT
