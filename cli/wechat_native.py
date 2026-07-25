#!/usr/bin/env python3
"""
微信公众号本地化下载工具 - CLI

用法:
    python cli/wechat_native.py login              # 扫码登录
    python cli/wechat_native.py sync "公众号名"     # 同步文章列表
    python cli/wechat_native.py download           # 下载文章
    python cli/wechat_native.py status             # 查看状态
"""

import sys
from pathlib import Path

import click
import yaml

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.wechat_native import WechatAuth, WechatAPI, NativeWechatDownloader


def load_config() -> dict:
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "src/services/wechat_native/config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@click.group()
def cli():
    """微信公众号本地化下载工具"""
    pass


@cli.command()
@click.option(
    "--qr-display",
    type=click.Choice(["terminal", "image"]),
    default="terminal",
    help="二维码展示方式",
)
def login(qr_display):
    """扫码登录微信公众平台"""
    config = load_config()
    auth = WechatAuth(
        cookie_file=config["auth"]["cookie_file"],
        token_expire_days=config["auth"]["token_expire_days"],
    )

    if auth.login(qr_display=qr_display):
        click.echo(click.style("✓ 登录成功", fg="green"))
    else:
        click.echo(click.style("✗ 登录失败", fg="red"))
        sys.exit(1)


@cli.command()
@click.argument("account_name")
@click.option("--max", type=int, help="最大同步文章数")
def sync(account_name, max):
    """同步公众号文章列表到数据库"""
    config = load_config()

    # 加载认证
    auth = WechatAuth(
        cookie_file=config["auth"]["cookie_file"],
        token_expire_days=config["auth"]["token_expire_days"],
    )

    if not auth.load_cookie():
        click.echo(click.style("未登录，请先执行 login 命令", fg="red"))
        sys.exit(1)

    if not auth.is_authenticated():
        click.echo(click.style("认证已失效，请重新登录", fg="red"))
        sys.exit(1)

    # 初始化 API
    api = WechatAPI(auth, timeout=config["api"]["timeout"])

    # 初始化下载器
    downloader = NativeWechatDownloader(
        api=api,
        db_path=config["database"]["path"],
        output_dir=config["download"]["output_dir"],
        rpm=config["download"]["rpm"],
        formats=config["download"]["formats"],
        localize_images=config["download"]["localize_images"],
        min_content_len=config["download"]["min_content_len"],
    )

    # 同步文章列表
    count = downloader.sync_account(account_name, max_articles=max)

    if count > 0:
        click.echo(click.style(f"✓ 同步成功，新增 {count} 篇文章", fg="green"))
    else:
        click.echo(click.style("未发现新文章", fg="yellow"))


@cli.command()
@click.option("--limit", type=int, help="最大下载数量")
def download(limit):
    """下载待处理的文章"""
    config = load_config()

    # 加载认证
    auth = WechatAuth(
        cookie_file=config["auth"]["cookie_file"],
        token_expire_days=config["auth"]["token_expire_days"],
    )

    if not auth.load_cookie():
        click.echo(click.style("未登录，请先执行 login 命令", fg="red"))
        sys.exit(1)

    if not auth.is_authenticated():
        click.echo(click.style("认证已失效，请重新登录", fg="red"))
        sys.exit(1)

    # 初始化 API
    api = WechatAPI(auth, timeout=config["api"]["timeout"])

    # 初始化下载器
    downloader = NativeWechatDownloader(
        api=api,
        db_path=config["database"]["path"],
        output_dir=config["download"]["output_dir"],
        rpm=config["download"]["rpm"],
        formats=config["download"]["formats"],
        localize_images=config["download"]["localize_images"],
        min_content_len=config["download"]["min_content_len"],
    )

    # 下载文章
    downloader.download_pending(limit=limit)


@cli.command()
def status():
    """查看下载状态"""
    config = load_config()

    # 检查认证状态
    auth = WechatAuth(
        cookie_file=config["auth"]["cookie_file"],
        token_expire_days=config["auth"]["token_expire_days"],
    )

    if auth.load_cookie():
        if auth.is_authenticated():
            click.echo(click.style("✓ 认证有效", fg="green"))
        else:
            click.echo(click.style("✗ 认证已失效", fg="red"))
    else:
        click.echo(click.style("✗ 未登录", fg="yellow"))

    # 获取下载统计
    api = WechatAPI(auth, timeout=config["api"]["timeout"])
    downloader = NativeWechatDownloader(
        api=api,
        db_path=config["database"]["path"],
        output_dir=config["download"]["output_dir"],
    )

    stats = downloader.get_stats()
    click.echo("\n下载统计:")
    click.echo(f"  总数: {stats['total']}")
    click.echo(f"  待下载: {stats['pending']}")
    click.echo(f"  已完成: {stats['done']}")
    click.echo(f"  失败: {stats['failed']}")

    if stats["downloading"] > 0:
        click.echo(click.style(f"  下载中: {stats['downloading']}", fg="yellow"))


if __name__ == "__main__":
    cli()
