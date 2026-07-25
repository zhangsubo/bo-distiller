"""
微信本地化下载器测试

运行方式：
    python -m pytest tests/test_wechat_native.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from src.services.wechat_native import WechatAuth, WechatAPI
from src.services.wechat_native.api import Account, Article


class TestWechatAuth:
    """测试认证模块"""

    def test_init(self, tmp_path):
        """测试初始化"""
        cookie_file = tmp_path / "cookie.json"
        auth = WechatAuth(cookie_file=cookie_file, token_expire_days=7)

        assert auth.cookie_file == cookie_file
        assert auth.token_expire_days == 7
        assert auth.token is None

    def test_load_cookie_not_exists(self, tmp_path):
        """测试加载不存在的 cookie"""
        cookie_file = tmp_path / "cookie.json"
        auth = WechatAuth(cookie_file=cookie_file)

        assert auth.load_cookie() is False

    def test_load_cookie_expired(self, tmp_path):
        """测试加载过期的 cookie"""
        from datetime import datetime, timedelta

        cookie_file = tmp_path / "cookie.json"

        # 创建过期的 cookie
        data = {
            "token": "test_token",
            "cookies": {"key": "value"},
            "saved_at": (datetime.now() - timedelta(days=10)).isoformat(),
        }

        with open(cookie_file, "w") as f:
            json.dump(data, f)

        auth = WechatAuth(cookie_file=cookie_file, token_expire_days=7)
        assert auth.load_cookie() is False

    def test_load_cookie_valid(self, tmp_path):
        """测试加载有效的 cookie"""
        from datetime import datetime

        cookie_file = tmp_path / "cookie.json"

        # 创建有效的 cookie
        data = {
            "token": "test_token",
            "cookies": {"key": "value"},
            "saved_at": datetime.now().isoformat(),
        }

        with open(cookie_file, "w") as f:
            json.dump(data, f)

        auth = WechatAuth(cookie_file=cookie_file, token_expire_days=7)
        assert auth.load_cookie() is True
        assert auth.token == "test_token"


class TestWechatAPI:
    """测试 API 模块"""

    def test_search_account_success(self):
        """测试搜索公众号成功"""
        mock_auth = Mock()
        mock_auth.token = "test_token"
        mock_auth.get_session.return_value = Mock()

        api = WechatAPI(auth=mock_auth)

        # Mock 响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "base_resp": {"ret": 0},
            "list": [
                {
                    "fakeid": "123",
                    "nickname": "测试公众号",
                    "alias": "test",
                }
            ],
        }

        with patch.object(api.session, "get", return_value=mock_response):
            accounts = api.search_account("测试")

            assert len(accounts) == 1
            assert accounts[0].fakeid == "123"
            assert accounts[0].nickname == "测试公众号"

    def test_search_account_not_logged_in(self):
        """测试未登录时搜索公众号"""
        mock_auth = Mock()
        mock_auth.token = None

        api = WechatAPI(auth=mock_auth)

        with pytest.raises(RuntimeError, match="未登录"):
            api.search_account("测试")

    def test_normalize_html(self):
        """测试 HTML 清洗"""
        mock_auth = Mock()
        api = WechatAPI(auth=mock_auth)

        raw_html = """
        <html>
            <body>
                <div id="js_content">
                    <p>正文内容</p>
                    <script>alert('xss')</script>
                    <style>.test{}</style>
                    <img src="test.jpg" alt="图片" data-other="value">
                </div>
            </body>
        </html>
        """

        cleaned = api.normalize_html(raw_html)

        # 验证脚本和样式被移除
        assert "<script>" not in cleaned
        assert "<style>" not in cleaned

        # 验证正文保留
        assert "正文内容" in cleaned

        # 验证图片属性被清理（仅保留必要属性）
        assert 'src="test.jpg"' in cleaned
        assert 'alt="图片"' in cleaned


class TestRateLimiter:
    """测试限速器"""

    def test_rate_limiter(self):
        """测试限速器基本功能"""
        from src.services.wechat_native.downloader import RateLimiter
        import time

        limiter = RateLimiter(rpm=120)  # 每秒 2 次

        # 第一次调用不应等待
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        assert elapsed < 0.1

        # 第二次调用应等待约 0.5 秒
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        assert 0.4 < elapsed < 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
