#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号 API 单元测试脚本

用于测试和诊断微信公众号 API 配置问题。

运行方法:
    python test_wechat.py
"""

import sys
import io

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from config.settings import WECHAT_APP_ID, WECHAT_APP_SECRET
from utils.logger import get_logger

_log = get_logger("test_wechat")

BASE_URL = "https://api.weixin.qq.com/cgi-bin"


def test_get_public_ip():
    """获取当前服务器的公网 IP"""
    print("\n" + "=" * 50)
    print("Step 1: 获取服务器公网 IP")
    print("=" * 50)

    ip_services = [
        "https://api.ipify.org?format=json",
        "https://api.ip.sb/jsonip",
        "http://ip-api.com/json",
    ]

    for service in ip_services:
        try:
            resp = requests.get(service, timeout=10)
            data = resp.json()
            # 不同服务返回格式不同
            ip = data.get("ip") or data.get("query") or data.get("origin")
            if ip:
                print(f"✅ 当前服务器公网 IP: {ip}")
                print(f"\n⚠️  请将此 IP 添加到微信公众号后台的 IP 白名单中：")
                print(f"   登录公众平台 -> 设置与开发 -> 基本配置 -> IP白名单")
                print(f"   添加 IP: {ip}")
                return ip
        except Exception as e:
            print(f"❌ 服务 {service} 获取失败: {e}")
            continue

    print("❌ 无法获取公网 IP，请手动检查")
    return None


def test_access_token():
    """测试获取 access_token"""
    print("\n" + "=" * 50)
    print("Step 2: 测试获取 access_token")
    print("=" * 50)

    url = f"{BASE_URL}/token"
    params = {
        "grant_type": "client_credential",
        "appid": WECHAT_APP_ID,
        "secret": WECHAT_APP_SECRET,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if "errcode" in data:
            errcode = data.get("errcode")
            errmsg = data.get("errmsg", "")

            if "invalid ip" in errmsg.lower() or "not in whitelist" in errmsg.lower():
                print(f"❌ IP 白名单错误: {errmsg}")
                print(f"   错误码: {errcode}")
                print(f"\n   解决方案:")
                print(f"   1. 登录微信公众平台: https://mp.weixin.qq.com")
                print(f"   2. 进入: 设置与开发 -> 基本配置 -> IP白名单")
                print(f"   3. 添加上面获取的公网 IP")
                return None
            else:
                print(f"❌ 获取 access_token 失败: {errmsg} (errcode: {errcode})")
                return None

        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)
        print(f"✅ access_token 获取成功!")
        print(f"   有效期: {expires_in} 秒 ({expires_in/3600:.1f} 小时)")
        print(f"   Token: {access_token[:20]}...")
        return access_token

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def test_upload_image(access_token: str):
    """测试上传图片素材"""
    print("\n" + "=" * 50)
    print("Step 3: 测试上传图片素材")
    print("=" * 50)

    # 检查测试图片
    import os
    test_image = "D:/公众号/260304/cover.png"

    if not os.path.exists(test_image):
        print(f"⚠️  测试图片不存在: {test_image}")
        print("   跳过上传测试")
        return None

    # 上传永久素材
    url = f"{BASE_URL}/material/add_material"
    params = {"access_token": access_token}

    try:
        with open(test_image, "rb") as f:
            files = {"media": ("cover.png", f, "image/png")}
            data = {"type": "image"}
            resp = requests.post(url, params=params, files=files, data=data, timeout=30)

        result = resp.json()

        if "errcode" in result:
            print(f"❌ 上传失败: {result.get('errmsg')} (errcode: {result.get('errcode')})")
            return None

        media_id = result.get("media_id")
        print(f"✅ 图片上传成功!")
        print(f"   media_id: {media_id}")
        return media_id

    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return None


def test_create_draft(access_token: str, thumb_media_id: str = None):
    """测试创建草稿"""
    print("\n" + "=" * 50)
    print("Step 4: 测试创建草稿")
    print("=" * 50)

    url = f"{BASE_URL}/draft/add"
    params = {"access_token": access_token}

    # 如果没有封面图，先上传一个
    if not thumb_media_id:
        print("⚠️  没有封面图 media_id，跳过草稿创建测试")
        return None

    # 使用更短的测试摘要
    articles_data = {
        "articles": [
            {
                "title": "【测试】AI日报测试文章",
                "author": "AI日报",
                "digest": "这是一篇测试文章，验证API配置。",
                "content": "<h1>测试文章</h1><p>这是测试内容。</p>",
                "content_source_url": "",
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }

    try:
        # 使用 ensure_ascii=False 避免中文乱码
        import json
        headers = {"Content-Type": "application/json; charset=utf-8"}
        resp = requests.post(
            url,
            params=params,
            data=json.dumps(articles_data, ensure_ascii=False),
            headers=headers,
            timeout=30
        )
        result = resp.json()

        if "errcode" in result and result["errcode"] != 0:
            print(f"❌ 创建草稿失败: {result.get('errmsg')} (errcode: {result.get('errcode')})")
            return None

        media_id = result.get("media_id")
        print(f"✅ 草稿创建成功!")
        print(f"   draft_media_id: {media_id}")
        print(f"\n   请在微信公众号后台草稿箱中查看测试文章")
        return media_id

    except Exception as e:
        print(f"❌ 创建草稿异常: {e}")
        return None


def test_get_api_domain_ip(access_token: str):
    """获取微信 API 服务器 IP（用于配置白名单参考）"""
    print("\n" + "=" * 50)
    print("获取微信 API 服务器 IP 列表")
    print("=" * 50)

    url = f"{BASE_URL}/get_api_domain_ip"
    params = {"access_token": access_token}

    try:
        resp = requests.get(url, params=params, timeout=10)
        result = resp.json()

        if "errcode" in result:
            print(f"❌ 获取失败: {result.get('errmsg')}")
            return

        ip_list = result.get("ip_list", [])
        print(f"✅ 微信 API 服务器 IP 列表 ({len(ip_list)} 个):")
        for ip in ip_list[:10]:
            print(f"   - {ip}")
        if len(ip_list) > 10:
            print(f"   ... 还有 {len(ip_list) - 10} 个")

    except Exception as e:
        print(f"❌ 获取异常: {e}")


def main():
    print("\n" + "=" * 60)
    print("微信公众号 API 诊断测试")
    print("=" * 60)

    print(f"\n配置信息:")
    print(f"  APP_ID: {WECHAT_APP_ID}")
    print(f"  APP_SECRET: {WECHAT_APP_SECRET[:8]}***")

    # Step 1: 获取公网 IP
    public_ip = test_get_public_ip()

    # Step 2: 测试 access_token
    access_token = test_access_token()
    if not access_token:
        print("\n" + "=" * 60)
        print("❌ 测试失败: 无法获取 access_token")
        print("=" * 60)
        sys.exit(1)

    # Step 3: 测试上传图片
    media_id = test_upload_image(access_token)

    # Step 4: 测试创建草稿
    draft_id = test_create_draft(access_token, media_id)

    # 获取微信 API 服务器 IP
    test_get_api_domain_ip(access_token)

    # 总结
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"  公网 IP 获取: {'✅' if public_ip else '❌'}")
    print(f"  access_token: {'✅' if access_token else '❌'}")
    print(f"  图片上传: {'✅' if media_id else '⚠️ 跳过'}")
    print(f"  草稿创建: {'✅' if draft_id else '⚠️ 跳过'}")

    if access_token and media_id and draft_id:
        print("\n🎉 所有测试通过！微信公众号 API 配置正确。")
    elif access_token:
        print("\n⚠️  access_token 获取成功，但部分功能需要进一步配置。")


if __name__ == "__main__":
    main()
