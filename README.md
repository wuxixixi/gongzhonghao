# 微信公众号 AI 日报自动化发布系统

自动化采集 AI 热点资讯，生成并发布微信公众号文章。

## 功能特性

- **数据采集**：自动从 arXiv、GitHub、HuggingFace、新闻网站采集 AI 资讯
- **智能筛选**：基于热度、相关性、质量多维度筛选优质内容
- **文章生成**：自动撰写热点分析文章
- **图片生成**：支持 FLUX 和 Ideogram V3 生成封面和配图
- **自动发布**：一键发布到微信公众号草稿箱
- **定时任务**：支持 Windows 定时任务自动化运行
- **Web 管理界面**：可视化配置管理、文章编辑、实时监控、发布管理

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
│   │   ├── multi_stage_filter.py  # 多阶段智能筛选
│   │   ├── quality_checker.py     # 质量检查
│   │   └── writer.py               # 文章写作
│   ├── imaging/            # 图片生成
│   │   ├── flux_generator.py      # FLUX 图片生成
│   │   └── ideogram_generator.py  # Ideogram V3 图片生成
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
│       ├── proxy.py               # 代理配置
│       └── retry.py               # 重试机制
├── scripts/                # 脚本目录
│   ├── pipeline.py         # 处理流水线
│   └── scheduler.py       # 定时调度
├── main.py                 # 主程序入口
├── auto_generator.py       # 自动生成器
├── test_wechat.py          # 微信测试
├── run_web.py              # Web 服务启动入口
├── requirements.txt       # 依赖
├── web/                    # Web 管理界面
│   ├── __init__.py        # Flask 应用工厂
│   ├── api/               # API 蓝图
│   ├── models/            # 数据库模型
│   ├── services/           # 业务服务
│   ├── tasks/             # 异步任务
│   └── frontend/           # React 前端
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
   - DMXAPI API Key（用于 LLM 和图片生成）
   - Tavily API Key（用于新闻搜索）
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

## Web 管理界面

提供可视化 Web 管理界面，支持配置管理、内容编辑、系统监控、发布管理等功能。

### 功能模块

- **用户认证**：JWT Token 认证，支持管理员/编辑角色
- **工作台**：系统概览、快捷操作、运行状态
- **内容管理**：文章列表、详情预览、Markdown 编辑器、深度分析
- **系统配置**：LLM/图片/微信/采集/代理等配置项管理
- **系统监控**：运行状态、日志查看（支持实时流）、任务历史
- **发布管理**：微信草稿创建、发布记录追踪

### 启动方式

```bash
# 安装前端依赖
cd web/frontend && npm install

# 开发模式（前端）
cd web/frontend && npm run dev

# 开发模式（后端）
python run_web.py

# 生产模式（前端构建 + Flask 托管）
cd web/frontend && npm run build
python run_web.py --production
```

### 访问地址

- 开发环境：http://localhost:3000
- 生产环境：http://localhost:5000

### 默认账号

- 用户名：`admin`
- 密码：`admin123456`（首次登录后请及时修改）

### API 接口

Web 后端提供 REST API：

| 模块 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/auth/*` | 登录、登出、用户管理 |
| 配置 | `/api/config/*` | 系统配置 CRUD |
| 内容 | `/api/content/*` | 文章管理、流水线触发 |
| 监控 | `/api/monitor/*` | 状态、日志、任务历史 |
| 发布 | `/api/publish/*` | 草稿创建、发布记录 |

## 依赖

### 后端 (Python)

- Python 3.10+
- requests
- openai
- arxiv
- beautifulsoup4
- Pillow
- tavily-python
- python-dotenv
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-JWT-Extended
- Flask-CORS
- Flask-Limiter
- marshmallow
- bcrypt
- waitress

### 前端 (Node.js)

- React 18
- TypeScript
- Vite
- Ant Design 5
- Zustand
- Axios
- React Router 6

## License

MIT
