"""
LLM 元数据管理 API

提供 LLM 提供商元数据和模型列表的查询、更新接口。
"""

import aiohttp
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from src.llm_metadata import get_metadata_manager, SUPPORTED_PROVIDERS

router = APIRouter()

# Base URL 本地修正（修正上游数据源的错误）
BASE_URL_OVERRIDES = {
    "minimax": "https://api.minimaxi.com/v1",
}


@router.get("/api/llm/providers")
async def get_supported_providers():
    """获取支持的提供商列表"""
    return {
        "providers": SUPPORTED_PROVIDERS,
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
    if provider_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    manager = get_metadata_manager()

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
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    force_refresh: bool = False,
):
    """获取提供商模型列表

    Args:
        provider_id: 提供商 ID
        api_base: API 基础 URL（可选，用于实时查询）
        api_key: API Key（可选，用于实时查询）
        force_refresh: 是否强制刷新缓存

    Returns:
        模型列表
    """
    if provider_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    manager = get_metadata_manager()

    try:
        # 如果提供了 api_base 和 api_key，则从 API 获取
        if api_base and api_key:
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
    if provider_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    manager = get_metadata_manager()

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
    if provider_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的提供商: {provider_id}",
        )

    manager = get_metadata_manager()

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


@router.get("/api/llm/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息

    Returns:
        各提供商的缓存状态
    """
    manager = get_metadata_manager()

    try:
        stats = {}

        for provider_id in SUPPORTED_PROVIDERS:
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


# 连通性测试请求模型
class ConnectivityTestRequest(BaseModel):
    api_key: str
    api_base: str
    model: str


@router.post("/api/llm/test-connectivity")
async def test_connectivity(request: ConnectivityTestRequest):
    """测试 LLM 提供商连通性

    Args:
        request: 包含 api_key、api_base、model 的测试请求

    Returns:
        测试结果，包含成功状态和响应信息
    """
    try:
        # 构建请求 URL
        url = f"{request.api_base.rstrip('/')}/chat/completions"

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {request.api_key}",
        }

        # 构建请求体（简单的测试消息）
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            "stream": False,
            "max_tokens": 10,  # 限制输出，节省费用
        }

        # 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                status_code = response.status
                response_text = await response.text()

                if status_code == 200:
                    return {
                        "success": True,
                        "message": "连通性测试成功",
                        "status_code": status_code,
                        "status": "ok",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"连通性测试失败: HTTP {status_code}",
                        "status_code": status_code,
                        "error": response_text[:500],  # 限制错误信息长度
                        "status": "error",
                    }

    except aiohttp.ClientTimeout:
        raise HTTPException(
            status_code=408,
            detail="请求超时，请检查网络连接和 API Base URL"
        )
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"网络请求失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"测试失败: {str(e)}"
        )
