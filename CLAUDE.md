# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供本项目代码库的 guidance。

## 项目概览

本项目是**微信公众号 AI 日报自动化发布系统**，用于自动采集 AI 热点资讯，生成文章并发布到微信公众号草稿箱。

## 每日自动化工作流

系统每日运行两个定时任务：

1. **上午 9:00** - 运行 `main.py`：采集资讯 → 筛选热点 → 生成今日 AI 热点文章
2. **上午 10:00** - 运行 `auto_generator.py`：选择最佳文章 → 下载原文 → 生成深度分析 → 发布

## 常用命令

### 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主流水线（每日热点）
python main.py

# 带参数运行
python main.py --no-publish    # 只生成内容，不发布到微信
python main.py --force         # 强制重新生成（忽略已有文章）

# 运行深度分析生成器（定时 10:00）
python auto_generator.py
python auto_generator.py --now        # 立即执行，不等待
python auto_generator.py --no-publish # 只生成，不发布

# 测试微信连接
python test_wechat.py
```

### Windows 定时任务命令

```bash
# 创建 9:00 任务（热点新闻）
schtasks /create /tn "WechatAI_Hot" /tr "python D:\公众号\main.py" /sc daily /st 09:00

# 创建 10:00 任务（深度分析）
schtasks /create /tn "WechatAI_Deep" /tr "python D:\公众号\auto_generator.py" /sc daily /st 10:00

# 查看任务
schtasks /query /tn "WechatAI_Hot" /fo list

# 删除任务
schtasks /delete /tn "WechatAI_Hot"
```

## 架构概览

### 流水线流程

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐
│   数据采集器     │────▶│   筛选器    │────▶│   文章撰写器  │
│                 │     │ (HotFilter) │     │              │
│ • Arxiv         │     └─────────────┘     └──────────────┘
│ • GitHub        │                                    │
│ • HuggingFace   │                                    ▼
│ • News          │     ┌──────────────┐     ┌──────────────┐
└─────────────────┘     │   图片生成    │     │   发布模块   │
                        │(FluxGenerator│◀────│              │
                        └──────────────┘     │ • 草稿创建   │
                                             │ • 微信 API  │
                                             └──────────────┘
```

### 核心模块

- **`app/collectors/`** - 数据采集器：arXiv、GitHub、HuggingFace、新闻源
- **`app/processors/`** - 内容处理：筛选、文章选择、质量检查、撰写
- **`app/imaging/`** - 基于 FLUX 的封面和内文图片生成
- **`app/publisher/`** - 微信 API 客户端和草稿创建
- **`app/storage/`** - 本地文件存储（按日期组织）
- **`app/config/settings.py`** - 配置管理（环境变量）

### 数据流向

1. **采集**：多个采集器通过 `ThreadPoolExecutor` 并发执行，收集 AI 新闻
2. **筛选**：`HotFilter` 使用基于 LLM 的评估对文章评分并选择热点
3. **撰写**：两阶段生成（大纲 → 内容），包含质量检查和修订
4. **配图**：FLUX 生成封面（896×576）和内文图片（1024×768）
5. **发布**：通过微信公众号 API 创建草稿，包含媒体上传

### 存储结构

```
D:\公众号\
├── YYMMDD\                    # 每日目录
│   ├── raw_data.json          # 采集的原始数据
│   ├── selected_data.json     # 筛选的热点数据
│   ├── article.md             # 生成的文章（markdown）
│   ├── article.html           # 生成的文章（HTML）
│   ├── cover.png              # 封面图片
│   ├── image_1.png            # 内文配图
│   ├── image_2.png
│   ├── image_3.png
│   └── run_report.json        # 执行报告
└── deep_analysis\             # 深度分析文章
    └── YYMMDD\
```

## 配置说明

配置通过 `.env` 文件管理（参见 `.env.example` 模板）：

### 必填环境变量

```bash
# LLM API (DMXAPI)
DMXAPI_BASE_URL=https://api.dmxapi.com/v1
DMXAPI_API_KEY=your_key_here
LLM_MODEL=gemini-2.0-flash-lite-preview

# 微信公众号
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# Tavily 搜索 API
TAVILY_API_KEY=your_key_here
```

### 可选配置

```bash
# 采集设置
ARXIV_MAX_RESULTS=30
HF_MODELS_LIMIT=20

# 文章生成
ARTICLE_MIN_WORDS=3000
ARTICLE_MAX_WORDS=4000

# 输出目录
OUTPUT_BASE_DIR=D:\公众号
```

## 关键实现细节

### 微信公众号 API Token 管理

`WeChatClient` 类处理 access_token 生命周期：
- Token 缓存在 `.wechat_token.json`
- 过期自动刷新（7200秒）
- IP 白名单错误时提供友好提示

### 文章质量检查

`ArticleWriter` 实现迭代质量改进：
- `MAX_REVISION_ATTEMPTS = 2` 最大修订次数
- `PASSING_SCORE = 7` 通过质量检查的最低分数
- 检查项：完整性、准确性、语法、逻辑

### 采集器架构

所有采集器继承自 `BaseCollector`，需实现：
- `name` 属性用于日志
- `collect()` 方法返回 `List[RawItem]`

采集器通过 `ThreadPoolExecutor(max_workers=4)` 并发执行。

### 图片生成

`FluxGenerator` 处理：
- 封面图：896×576（微信推荐尺寸）
- 内文图：1024×768
- 失败自动重试
- PNG 格式输出

## 常见开发任务

### 添加新数据采集器

1. 在 `app/collectors/` 创建类，继承 `BaseCollector`
2. 实现 `name` 属性和 `collect()` 方法
3. 添加到 `pipeline.py` 的 `Pipeline.collectors` 列表

### 修改文章写作风格

编辑 `app/processors/writer.py` 中的系统提示词：
- `OUTLINE_SYSTEM` - 控制大纲生成
- `WRITE_SYSTEM` - 控制文章写作风格

### 添加新配置选项

1. 添加到 `.env` 文件
2. 添加到 `app/config/settings.py`，设置默认值
3. 使用 `os.getenv()` 或 `_require()`（必填项）

### 测试微信集成

```bash
python test_wechat.py
```

此命令测试 token 获取和基本 API 连通性。

## 故障排查

### IP 白名单错误

如看到 "IP not in whitelist" 错误：
1. 运行 `python test_wechat.py` 获取当前 IP
2. 在微信公众号后台添加 IP：
   - 登录：https://mp.weixin.qq.com
   - 导航：设置与开发 -> 基本配置 -> IP白名单

### Token 过期

Access token 自动刷新，但如遇到问题：
- 删除 `.wechat_token.json` 强制刷新
- 检查 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET` 是否正确

### 文章生成失败

- 检查 `DMXAPI_API_KEY` 是否有效
- 确认 `LLM_MODEL` 在 DMXAPI 套餐中可用
- 查看 `logs/` 目录中的日志

## 给 AI 助手的提示

- 这是一个中文语言的 Windows 项目，使用中文路径（D:\公众号）
- 所有面向用户的输出均为中文
- 代码库使用类型提示
- 日志记录全面，使用结构化格式
- 系统设计为幂等——多次运行不会重复生成内容
