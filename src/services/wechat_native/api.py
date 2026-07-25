"""
微信公众平台 API 封装

实现公众号搜索、文章列表获取、文章下载等核心接口。
基于 wechat-article-exporter 的 server/api/ 逻辑。
"""

import random
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .auth import WechatAuth


@dataclass
class Account:
    """公众号信息"""
    fakeid: str
    nickname: str
    alias: str = ""
    round_head_img: str = ""
    signature: str = ""


@dataclass
class Article:
    """文章信息"""
    aid: str
    title: str
    link: str
    author_name: str = ""
    digest: str = ""
    cover: str = ""
    create_time: int = 0
    update_time: int = 0
    copyright_stat: int = 0  # 是否原创
    item_show_type: int = 0  # 文章类型


class WechatAPI:
    """微信公众平台 API 客户端"""

    def __init__(self, auth: WechatAuth, timeout: int = 30):
        self.auth = auth
        self.timeout = timeout
        self.session = auth.get_session()

    def search_account(self, keyword: str) -> List[Account]:
        """
        搜索公众号

        Args:
            keyword: 搜索关键词

        Returns:
            公众号列表
        """
        if not self.auth.token:
            raise RuntimeError("未登录，请先调用 auth.login() 或 auth.load_cookie()")

        try:
            resp = self.session.get(
                "https://mp.weixin.qq.com/cgi-bin/searchbiz",
                params={
                    "action": "search_biz",
                    "query": keyword,
                    "token": self.auth.token,
                    "lang": "zh_CN",
                    "f": "json",
                    "ajax": "1",
                    "random": random.random(),
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()

            data = resp.json()
            base_resp = data.get("base_resp", {})

            if base_resp.get("ret") != 0:
                err_msg = base_resp.get("err_msg", "未知错误")
                raise RuntimeError(f"搜索公众号失败: {err_msg}")

            # 解析公众号列表
            accounts = []
            for item in data.get("list", []):
                accounts.append(Account(
                    fakeid=item.get("fakeid", ""),
                    nickname=item.get("nickname", ""),
                    alias=item.get("alias", ""),
                    round_head_img=item.get("round_head_img", ""),
                    signature=item.get("signature", ""),
                ))

            return accounts

        except Exception as e:
            raise RuntimeError(f"搜索公众号失败: {e}")

    def get_article_list(
        self,
        fakeid: str,
        begin: int = 0,
        count: int = 10,
        keyword: str = "",
    ) -> Dict:
        """
        获取公众号文章列表

        Args:
            fakeid: 公众号 ID
            begin: 起始位置（分页）
            count: 每页数量
            keyword: 搜索关键词（可选）

        Returns:
            包含文章列表和总数的字典
        """
        if not self.auth.token:
            raise RuntimeError("未登录，请先调用 auth.login() 或 auth.load_cookie()")

        is_searching = bool(keyword)

        params = {
            "sub": "search" if is_searching else "list",
            "search_field": "7" if is_searching else "null",
            "begin": begin,
            "count": count,
            "query": keyword,
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": 1,
            "sub_action": "list_ex",
            "token": self.auth.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }

        try:
            resp = self.session.get(
                "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()

            data = resp.json()
            base_resp = data.get("base_resp", {})

            if base_resp.get("ret") != 0:
                err_msg = base_resp.get("err_msg", "未知错误")
                raise RuntimeError(f"获取文章列表失败: {err_msg}")

            # 解析文章列表
            import json as json_lib

            publish_page = json_lib.loads(data.get("publish_page", "{}"))
            publish_list = publish_page.get("publish_list", [])

            articles = []
            for item in publish_list:
                publish_info_str = item.get("publish_info", "{}")
                if not publish_info_str:
                    continue

                publish_info = json_lib.loads(publish_info_str)
                appmsgex_list = publish_info.get("appmsgex", [])

                for appmsg in appmsgex_list:
                    articles.append(Article(
                        aid=appmsg.get("aid", ""),
                        title=appmsg.get("title", ""),
                        link=appmsg.get("link", ""),
                        author_name=appmsg.get("author_name", ""),
                        digest=appmsg.get("digest", ""),
                        cover=appmsg.get("cover", ""),
                        create_time=appmsg.get("create_time", 0),
                        update_time=appmsg.get("update_time", 0),
                        copyright_stat=appmsg.get("copyright_stat", 0),
                        item_show_type=appmsg.get("item_show_type", 0),
                    ))

            total_count = publish_page.get("total_count", 0)

            return {
                "articles": articles,
                "total": total_count,
                "begin": begin,
                "count": len(articles),
            }

        except Exception as e:
            raise RuntimeError(f"获取文章列表失败: {e}")

    def download_article(self, url: str) -> str:
        """
        下载文章 HTML

        Args:
            url: 文章 URL

        Returns:
            文章 HTML 内容
        """
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()

            # 微信文章可能没有 charset，requests 默认会用 ISO-8859-1 导致中文乱码
            if "charset" not in resp.headers.get("Content-Type", "").lower():
                resp.encoding = resp.apparent_encoding or "utf-8"

            return resp.text

        except Exception as e:
            raise RuntimeError(f"下载文章失败: {e}")

    def normalize_html(self, raw_html: str) -> str:
        """
        清洗文章 HTML，提取主体内容

        Args:
            raw_html: 原始 HTML

        Returns:
            清洗后的 HTML
        """
        soup = BeautifulSoup(raw_html, "html.parser")

        # 提取主体内容区域
        content = soup.find(id="js_content")
        if not content:
            # 备选：查找 class="rich_media_content"
            content = soup.find(class_="rich_media_content")

        if not content:
            raise ValueError("未找到文章主体内容（js_content）")

        # 移除脚本、样式标签
        for tag in content.find_all(["script", "style"]):
            tag.decompose()

        # 清理属性（保留必要的 src, href, class, alt）
        for tag in content.find_all():
            if tag.name in ["img", "a"]:
                # 图片和链接保留必要属性
                attrs = tag.attrs.copy()
                allowed = ["src", "href", "class", "alt", "data-src"]
                tag.attrs = {k: v for k, v in attrs.items() if k in allowed}
            else:
                # 其他标签仅保留 class
                if "class" in tag.attrs:
                    tag.attrs = {"class": tag.attrs["class"]}
                else:
                    tag.attrs = {}

        return str(content)

    def get_article_full_info(self, url: str) -> Dict:
        """
        获取文章完整信息（包含阅读量、点赞数等）

        注意：此接口需要额外的 credentials（appmsg_token, cookie），
        暂时先保留接口，后续实现。

        Args:
            url: 文章 URL

        Returns:
            文章完整信息
        """
        # TODO: 实现阅读量、点赞数获取
        # 参考 wechat-article-exporter 的 credentials 功能
        raise NotImplementedError("阅读量、点赞数获取功能待实现")
