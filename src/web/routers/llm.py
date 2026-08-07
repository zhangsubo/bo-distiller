"""
LLM 元数据管理 API

提供 LLM 提供商元数据和模型列表的查询、更新接口。
"""

import aiohttp
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from src.llm_metadata import get_metadata_manager

router = APIRouter()

# Base URL 本地修正（修正上游数据源的错误）
BASE_URL_OVERRIDES = {
    "minimax": "https://api.minimaxi.com/v1",
}


@router.get("/api/llm/providers")
async def get_supported_providers():
    """获取支持的提供商列表"""
    manager = get_metadata_manager()
    return {
        "providers": manager.get_supported_providers(),
        "status": "ok",
    }


@router.get("/api/llm/providers/{provider_id}/metadata")
async def get_provider_metadata(provider_id: str, force_refresh: bool = False):
    """获取提供商元数据

    Args:
        provider_id: 提供商 ID
        force_refresh: 是否强制刷新缓存

    Returns:
        提供商元数据，包含 base_url、context_window 等信息
    """
    manager = get_metadata_manager()
    if provider_id not in manager.get_supported_providers():
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    try:
        metadata = await manager.get_or_fetch_provider_metadata(
            provider_id, force_refresh=force_refresh
        )

        if metadata is None:
            raise HTTPException(
                status_code=500,
                detail=f"无法获取 {provider_id} 元数据",
            )

        # 提取关键信息
        base_url = metadata.get("api") or metadata.get("base_url")
        # 应用本地修正（修正上游数据错误）
        if provider_id in BASE_URL_OVERRIDES:
            base_url = BASE_URL_OVERRIDES[provider_id]

        result = {
            "provider_id": provider_id,
            "name": metadata.get("name", provider_id),
            "base_url": base_url,
            "models": metadata.get("models", []),
            "description": metadata.get("description"),
            "full_metadata": metadata,
        }

        return {"data": result, "status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/llm/providers/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
    force_refresh: bool = False,
):
    """获取提供商模型列表

    Args:
        provider_id: 提供商 ID
        force_refresh: 是否强制刷新缓存

    Returns:
        模型列表
    """
    manager = get_metadata_manager()
    if provider_id not in manager.get_supported_providers():
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    try:
        # 从 system_config 读取该 provider 的 api_key 和 api_base
        from src.storage import get_storage
        import json as _json
        storage = get_storage()
        sys_config = storage.get_setting("system_config") or {}
        if isinstance(sys_config, str):
            sys_config = _json.loads(sys_config)
        provider_cfg = sys_config.get("llm", {}).get("providers", {}).get(provider_id, {})
        api_key = provider_cfg.get("api_key", "")
        api_base = provider_cfg.get("api_base", "")

        # 如果有 api_key 和 api_base，从 API 获取
        if api_key and api_base:
            models = await manager.get_or_fetch_provider_models(
                provider_id, api_base, api_key, force_refresh=force_refresh
            )
        else:
            # 否则只返回缓存
            models = manager.get_cached_provider_models(provider_id)

        if models is None:
            # 尝试从元数据中获取模型列表
            metadata = await manager.get_or_fetch_provider_metadata(provider_id)
            if metadata:
                models = metadata.get("models", [])

        if models is None:
            models = []

        return {
            "data": {
                "provider_id": provider_id,
                "models": models,
                "count": len(models),
            },
            "status": "ok",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/llm/providers/{provider_id}/refresh")
async def refresh_provider_metadata(provider_id: str):
    """刷新指定提供商的元数据

    Args:
        provider_id: 提供商 ID

    Returns:
        刷新结果
    """
    manager = get_metadata_manager()
    if provider_id not in manager.get_supported_providers():
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    try:
        metadata = await manager.get_or_fetch_provider_metadata(
            provider_id, force_refresh=True
        )

        success = metadata is not None

        return {
            "status": "ok" if success else "failed",
            "message": f"{'成功' if success else '失败'}刷新 {provider_id} 元数据",
            "provider_id": provider_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/llm/providers/refresh-all")
async def refresh_all_providers():
    """刷新所有支持的提供商元数据

    Returns:
        所有提供商的刷新结果
    """
    manager = get_metadata_manager()

    try:
        results = await manager.refresh_all_providers()

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        return {
            "status": "ok",
            "message": f"已刷新 {success_count}/{total_count} 个提供商",
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/llm/providers/{provider_id}/cache")
async def clear_provider_cache(provider_id: str):
    """清除指定提供商的缓存

    Args:
        provider_id: 提供商 ID

    Returns:
        操作结果
    """
    manager = get_metadata_manager()
    if provider_id not in manager.get_supported_providers():
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    try:
        manager.clear_cache(provider_id)

        return {
            "status": "ok",
            "message": f"已清除 {provider_id} 缓存",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/llm/cache")
async def clear_all_cache():
    """清除所有提供商的缓存

    Returns:
        操作结果
    """
    manager = get_metadata_manager()

    try:
        manager.clear_cache()

        return {
            "status": "ok",
            "message": "已清除所有提供商缓存",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/llm/providers")
async def add_provider(body: dict):
    """添加新的提供商

    Args:
        body: 包含 provider_id 的字典

    Returns:
        操作结果
    """
    provider_id = body.get("provider_id")
    if not provider_id:
        raise HTTPException(status_code=400, detail="缺少 provider_id 参数")

    manager = get_metadata_manager()

    # 检查是否已存在
    if provider_id in manager.get_supported_providers():
        raise HTTPException(status_code=400, detail=f"提供商 {provider_id} 已存在")

    try:
        # 尝试获取元数据以验证 provider_id 是否有效
        metadata = await manager.fetch_provider_metadata(provider_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"在 models.dev 中未找到提供商 {provider_id}，请检查 ID 是否正确"
            )

        # 缓存元数据
        manager.cache_provider_metadata(provider_id, metadata)
        manager.add_supported_provider(provider_id)

        return {
            "status": "ok",
            "message": f"成功添加提供商 {provider_id}",
            "provider_id": provider_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/llm/providers/{provider_id}")
async def delete_provider(provider_id: str):
    """删除提供商

    Args:
        provider_id: 提供商 ID

    Returns:
        操作结果
    """
    manager = get_metadata_manager()
    if provider_id not in manager.get_supported_providers():
        raise HTTPException(
            status_code=404,
            detail=f"提供商 {provider_id} 不存在",
        )

    try:
        # 从支持列表中移除
        manager.remove_supported_provider(provider_id)

        # 清除缓存
        manager.clear_cache(provider_id)

        return {
            "status": "ok",
            "message": f"已删除提供商 {provider_id}",
        }

    except Exception as e:
        # 如果删除失败，恢复到列表中
        manager.add_supported_provider(provider_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/llm/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息

    Returns:
        各提供商的缓存状态
    """
    manager = get_metadata_manager()

    try:
        stats = {}

        for provider_id in manager.get_supported_providers():
            metadata_cached = manager.get_cached_provider_metadata(provider_id)
            models_cached = manager.get_cached_provider_models(provider_id)

            stats[provider_id] = {
                "metadata_cached": metadata_cached is not None,
                "models_cached": models_cached is not None,
            }

        return {
            "data": stats,
            "status": "ok",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import ipaddress
import socket
from urllib.parse import urlparse

# 连通性测试请求模型
class ConnectivityTestRequest(BaseModel):
    api_key: str
    api_base: str
    model: str


def _validate_url_for_ssrf(url_str: str) -> None:
    """验证 URL 是否安全（防 SSRF）

    - 仅允许 http/https scheme
    - 拒绝带用户名密码的 URL
    - 拒绝无 hostname 的 URL
    - DNS 解析后拒绝私网、loopback、link-local、云元数据地址
    """
    parsed = urlparse(url_str)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不允许的 URL scheme: {parsed.scheme}")

    if parsed.username or parsed.password:
        raise ValueError("URL 中不允许包含用户名或密码")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL 缺少 hostname")

    # 先检查 IP 字面量
    try:
        ip = ipaddress.ip_address(hostname)
        _check_ip(ip)
        return
    except ValueError:
        pass  # 不是 IP 字面量，继续作为域名处理

    # 域名：DNS 解析后检查所有解析到的 IP
    try:
        addrinfos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"无法解析域名: {hostname}")

    for family, _, _, _, sockaddr in addrinfos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            _check_ip(ip)
        except ValueError as e:
            raise ValueError(f"域名 {hostname} 解析到不允许的地址 {ip_str}: {e}")


def _check_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    """检查 IP 地址是否允许访问"""
    if ip.is_loopback:
        raise ValueError("不允许访问 loopback 地址")
    if ip.is_link_local:
        raise ValueError("不允许访问 link-local 地址")
    if ip.is_private:
        raise ValueError("不允许访问私网地址")
    if ip.is_reserved:
        raise ValueError("不允许访问保留地址")


@router.post("/api/llm/test-connectivity")
async def test_connectivity(request: ConnectivityTestRequest):
    """测试 LLM 提供商连通性（含 SSRF 防护）"""
    # URL 安全校验
    test_url = f"{request.api_base.rstrip('/')}/chat/completions"
    try:
        _validate_url_for_ssrf(test_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {request.api_key}",
        }
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            "stream": False,
            "max_tokens": 10,
        }

        # 禁止自动重定向，避免 SSRF 绕过
        async with aiohttp.ClientSession() as session:
            async with session.post(
                test_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=False,
            ) as response:
                status_code = response.status

                # 处理重定向：如果 3xx，拒绝（不允许自动跟随）
                if 300 <= status_code < 400:
                    return {
                        "success": False,
                        "message": "目标返回重定向，不允许自动跟随",
                        "status_code": status_code,
                        "status": "error",
                    }

                if status_code == 200:
                    return {
                        "success": True,
                        "message": "连通性测试成功",
                        "status_code": status_code,
                        "status": "ok",
                    }
                else:
                    # 不回传上游正文，只返回状态码和归一化错误
                    return {
                        "success": False,
                        "message": f"连通性测试失败: HTTP {status_code}",
                        "status_code": status_code,
                        "status": "error",
                    }

    except aiohttp.ClientTimeout:
        raise HTTPException(
            status_code=408,
            detail="请求超时，请检查网络连接和 API Base URL"
        )
    except aiohttp.ClientError as e:
        # 不暴露上游详细错误
        raise HTTPException(
            status_code=500,
            detail=f"网络请求失败: {type(e).__name__}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"测试失败: {type(e).__name__}"
        )
