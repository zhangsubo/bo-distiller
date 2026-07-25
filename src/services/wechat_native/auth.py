"""
微信公众平台认证模块

实现扫码登录、Cookie 持久化、认证状态检查。
基于 wechat-article-exporter 的 server/utils/proxy-request.ts 逻辑。
"""

import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs

import requests
import qrcode


class WechatAuth:
    """微信公众平台认证管理"""

    def __init__(self, cookie_file: Path, token_expire_days: int = 7):
        self.cookie_file = Path(cookie_file).expanduser()
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_expire_days = token_expire_days

        self.session = requests.Session()
        self.token: Optional[str] = None
        self._cookies: Dict[str, str] = {}

        # 标准请求头
        self.headers = {
            "Referer": "https://mp.weixin.qq.com/",
            "Origin": "https://mp.weixin.qq.com",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        self.session.headers.update(self.headers)

    def login(self, qr_display: str = "terminal") -> bool:
        """
        扫码登录流程

        Args:
            qr_display: 二维码展示方式，terminal（终端 ASCII）或 image（保存图片）

        Returns:
            登录是否成功
        """
        print("开始微信公众平台登录流程...")

        # 1. 获取 uuid
        uuid = self._start_login()
        if not uuid:
            print("❌ 获取登录 uuid 失败")
            return False

        print(f"✓ 获取登录 uuid: {uuid}")

        # 2. 生成并展示二维码
        qr_url = f"https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={random.random()}"
        self._display_qr(qr_url, qr_display)

        # 3. 轮询登录状态
        print("请使用微信扫描二维码登录...")
        if not self._poll_login_status(uuid):
            print("❌ 登录超时或取消")
            return False

        # 4. 完成登录，获取 token
        if not self._complete_login(uuid):
            print("❌ 完成登录失败")
            return False

        # 5. 保存认证信息
        self._save_cookie()
        print(f"✓ 登录成功，token 已保存到 {self.cookie_file}")
        return True

    def _start_login(self) -> Optional[str]:
        """第一步：获取登录 uuid"""
        try:
            resp = self.session.get(
                "https://mp.weixin.qq.com/cgi-bin/scanloginqrcode",
                params={
                    "action": "getqrcode",
                    "random": random.random(),
                },
                timeout=10,
            )
            resp.raise_for_status()

            # 从 Set-Cookie 中提取 uuid
            for cookie in resp.cookies:
                if cookie.name == "uuid":
                    return cookie.value
            return None
        except Exception as e:
            print(f"请求 uuid 失败: {e}")
            return None

    def _display_qr(self, url: str, display_mode: str):
        """展示二维码"""
        if display_mode == "terminal":
            # 终端 ASCII 二维码
            qr = qrcode.QRCode()
            qr.add_data(url)
            qr.make()
            qr.print_ascii(invert=True)
        else:
            # 保存为图片
            img = qrcode.make(url)
            qr_path = Path("wechat_login_qr.png")
            img.save(qr_path)
            print(f"二维码已保存到: {qr_path.absolute()}")
            print(f"或访问: {url}")

    def _poll_login_status(self, uuid: str, timeout: int = 180) -> bool:
        """轮询登录状态"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                resp = self.session.get(
                    "https://mp.weixin.qq.com/cgi-bin/scanloginqrcode",
                    params={
                        "action": "ask",
                        "f": "json",
                        "token": "",
                        "lang": "zh_CN",
                        "random": random.random(),
                    },
                    cookies={"uuid": uuid},
                    timeout=10,
                )
                resp.raise_for_status()

                data = resp.json()
                status = data.get("status")

                if status == 1:
                    # 已扫码，等待确认
                    print("✓ 已扫码，等待确认...")
                elif status == 2:
                    # 已确认
                    print("✓ 已确认登录")
                    return True
                elif status == 3:
                    # 二维码过期
                    print("二维码已过期")
                    return False
                elif status == 4:
                    # 取消登录
                    print("用户取消登录")
                    return False
                elif status == 5:
                    # 超时
                    print("登录超时")
                    return False

                time.sleep(2)
            except Exception as e:
                print(f"轮询登录状态出错: {e}")
                time.sleep(2)

        return False

    def _complete_login(self, uuid: str) -> bool:
        """完成登录，获取 token"""
        try:
            resp = self.session.post(
                "https://mp.weixin.qq.com/cgi-bin/bizlogin",
                params={"action": "login"},
                data={
                    "f": "json",
                    "ajax": "1",
                    "random": random.random(),
                },
                cookies={"uuid": uuid},
                timeout=10,
            )
            resp.raise_for_status()

            data = resp.json()

            # 检查返回状态
            base_resp = data.get("base_resp", {})
            if base_resp.get("ret") != 0:
                err_msg = base_resp.get("err_msg", "未知错误")
                print(f"登录失败: {err_msg}")
                return False

            # 提取 token
            redirect_url = data.get("redirect_url")
            if not redirect_url:
                print("响应中未找到 redirect_url")
                return False

            parsed = urlparse(f"http://localhost{redirect_url}")
            token_list = parse_qs(parsed.query).get("token")
            if not token_list:
                print(f"redirect_url 中未找到 token: {redirect_url}")
                return False

            self.token = token_list[0]

            # 保存所有 cookies
            self._cookies = {cookie.name: cookie.value for cookie in resp.cookies}
            self.session.cookies.update(self._cookies)

            print(f"✓ 获取 token: {self.token[:8]}***")
            return True

        except Exception as e:
            print(f"完成登录失败: {e}")
            return False

    def load_cookie(self) -> bool:
        """从本地加载已保存的 cookie"""
        if not self.cookie_file.exists():
            return False

        try:
            with open(self.cookie_file, encoding="utf-8") as f:
                data = json.load(f)

            # 检查是否过期
            saved_at = datetime.fromisoformat(data.get("saved_at", ""))
            expire_at = saved_at + timedelta(days=self.token_expire_days)

            if datetime.now() > expire_at:
                print(f"Cookie 已过期（保存于 {saved_at.strftime('%Y-%m-%d %H:%M:%S')}）")
                return False

            self.token = data.get("token")
            self._cookies = data.get("cookies", {})
            self.session.cookies.update(self._cookies)

            print(f"✓ 加载已保存的认证信息（{saved_at.strftime('%Y-%m-%d %H:%M:%S')}）")
            return True

        except Exception as e:
            print(f"加载 cookie 失败: {e}")
            return False

    def _save_cookie(self):
        """保存认证信息到本地"""
        data = {
            "token": self.token,
            "cookies": self._cookies,
            "saved_at": datetime.now().isoformat(),
        }

        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def is_authenticated(self) -> bool:
        """检查认证状态是否有效"""
        if not self.token:
            return False

        # 简单测试：请求一个需要认证的接口
        try:
            resp = self.session.get(
                "https://mp.weixin.qq.com/cgi-bin/home",
                params={"t": "home/index", "token": self.token, "lang": "zh_CN"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_headers(self) -> Dict[str, str]:
        """获取标准请求头"""
        return self.headers.copy()

    def get_session(self) -> requests.Session:
        """获取已认证的 session"""
        return self.session
