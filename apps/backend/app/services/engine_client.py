import httpx
from fastapi import HTTPException

from app.core.config import settings


async def post_engine(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{settings.engine_url}{path}", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = None
            try:
                detail = response.json().get("detail")
            except Exception:
                detail = response.text or str(exc)
            raise HTTPException(status_code=response.status_code, detail=detail) from exc
        return response.json()
