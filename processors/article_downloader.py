"""
原文下载器模块

从不同来源下载文章原文，用于深度分析。
支持的来源：arXiv、News（通用网页）、GitHub、HuggingFace
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from processors.filter import SelectedItem
from config.settings import OUTPUT_BASE_DIR
from utils.logger import get_logger

_log = get_logger("article_downloader")


class ArticleDownloader:
    """文章原文下载器"""

    # 请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 超时设置
    TIMEOUT = 30

    def __init__(self):
        self.base_dir = OUTPUT_BASE_DIR

    def get_deep_analysis_dir(self) -> Path:
        """获取深度分析目录"""
        today = datetime.now().strftime("%y%m%d")
        deep_dir = self.base_dir / today / "深度分析"
        deep_dir.mkdir(parents=True, exist_ok=True)
        return deep_dir

    def download(self, item: SelectedItem) -> Optional[str]:
        """下载文章原文

        Args:
            item: 选中的文章条目

        Returns:
            下载的原文保存路径，如果失败返回 None
        """
        url = item.raw.url
        source = item.raw.source

        _log.info("下载原文: %s (%s)", item.raw.title[:40], source)

        try:
            if source == "arxiv":
                content = self._download_arxiv(url)
            elif source == "github":
                content = self._download_github(url)
            elif source == "huggingface":
                content = self._download_huggingface(url)
            else:
                # 通用网页
                content = self._download_generic(url)

            if not content:
                _log.warning("原文下载失败: %s", url)
                return None

            # 保存原文
            file_path = self._save_content(item, content)
            _log.info("原文已保存: %s", file_path)
            return file_path

        except Exception as e:
            _log.error("下载原文异常: %s", e)
            return None

    def _download_arxiv(self, url: str) -> Optional[str]:
        """下载 arXiv 论文"""
        try:
            # arXiv PDF URL 转换为 Abstract 页面
            abstract_url = url
            if "/pdf/" in url:
                abstract_url = url.replace("/pdf/", "/abs/")

            response = requests.get(abstract_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 提取论文标题
            title = soup.find("h1", class_="title")
            title_text = title.text.strip() if title else "Unknown"

            # 提取摘要
            abstract = soup.find("blockquote", class_="abstract")
            abstract_text = abstract.text.strip() if abstract else ""

            # 提取作者
            authors = soup.find("div", class_="authors")
            authors_text = authors.text.strip() if authors else ""

            content = f"""# {title_text}

## 作者
{authors_text}

## 摘要
{abstract_text}

## 原文链接
{url}
"""
            return content

        except Exception as e:
            _log.error("下载 arXiv 论文失败: %s", e)
            return None

    def _download_github(self, url: str) -> Optional[str]:
        """下载 GitHub 项目信息"""
        try:
            # 转换为 Raw README URL
            readme_url = url.replace("/blob/", "/")

            # 尝试获取 README
            if "github.com" in readme_url:
                # 先获取仓库信息
                api_url = url.replace("github.com", "api.github.com/repos")
                if "/blob/" in api_url:
                    # 这是文件链接，获取目录
                    api_url = "/".join(api_url.split("/")[:5])

                response = requests.get(api_url, headers=self.HEADERS, timeout=self.TIMEOUT)
                if response.status_code == 200:
                    repo_data = response.json()

                    # 获取 README
                    readme_api = f"{api_url}/readme"
                    readme_response = requests.get(readme_api, headers=self.HEADERS, timeout=self.TIMEOUT)
                    if readme_response.status_code == 200:
                        import base64
                        readme_content = base64.b64decode(
                            readme_response.json().get("content", "")
                        ).decode("utf-8")

                        content = f"""# {repo_data.get('name', 'Unknown')}

## 描述
{repo_data.get('description', '无')}

## Stars
{repo_data.get('stargazers_count', 0)}

## README
{readme_content[:5000]}

## 原文链接
{url}
"""
                        return content

            # 如果无法获取 README，返回基本信息
            return f"""# GitHub 项目

## 链接
{url}

说明：无法自动获取项目详细信息，请访问原链接查看。
"""

        except Exception as e:
            _log.error("下载 GitHub 项目失败: %s", e)
            return None

    def _download_huggingface(self, url: str) -> Optional[str]:
        """下载 HuggingFace 模型信息"""
        try:
            # 转换为 API URL
            model_path = url.replace("https://huggingface.co/", "")
            api_url = f"https://huggingface.co/api/models/{model_path}"

            response = requests.get(api_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if response.status_code == 200:
                data = response.json()

                content = f"""# {data.get('modelId', 'Unknown')}

## 任务类型
{data.get('pipeline_tag', 'Unknown')}

## 下载量
{data.get('downloads', 0)}

## 点赞数
{data.get('likes', 0)}

## 描述
{data.get('card_data', {}).get('summary', '无') if data.get('card_data') else '无'}

## 原文链接
{url}
"""
                return content

            return None

        except Exception as e:
            _log.error("下载 HuggingFace 模型失败: %s", e)
            return None

    def _download_generic(self, url: str) -> Optional[str]:
        """下载通用网页内容"""
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 提取标题
            title = soup.find("title")
            title_text = title.text.strip() if title else "Unknown"

            # 尝试提取主要内容
            # 常见的内容容器
            content = None

            # 尝试 article 标签
            article = soup.find("article")
            if article:
                content = article.get_text(separator="\n", strip=True)
            else:
                # 尝试 main 标签
                main = soup.find("main")
                if main:
                    content = main.get_text(separator="\n", strip=True)
                else:
                    # 尝试 body
                    body = soup.find("body")
                    if body:
                        content = body.get_text(separator="\n", strip=True)

            if content:
                # 清理多余空白
                lines = [line.strip() for line in content.split("\n")]
                content = "\n".join(line for line in lines if line)

                # 限制长度
                content = content[:15000]

                return f"""# {title_text}

## 内容
{content}

## 原文链接
{url}
"""

            return None

        except Exception as e:
            _log.error("下载通用网页失败: %s", e)
            return None

    def _save_content(self, item: SelectedItem, content: str) -> str:
        """保存原文内容到文件"""
        # 生成文件名
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', item.raw.title)[:50]
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"原文_{timestamp}_{safe_title}.md"

        file_path = self.get_deep_analysis_dir() / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def download_multiple(self, items: list[SelectedItem]) -> dict:
        """批量下载多篇文章原文

        Args:
            items: 文章列表

        Returns:
            下载结果字典 {item_title: file_path}
        """
        results = {}

        for item in items:
            path = self.download(item)
            if path:
                results[item.raw.title] = path
            # 避免请求过快
            time.sleep(1)

        _log.info("批量下载完成: %d/%d", len(results), len(items))
        return results


def download_article(item: SelectedItem) -> Optional[str]:
    """便捷函数：下载单篇文章"""
    downloader = ArticleDownloader()
    return downloader.download(item)
