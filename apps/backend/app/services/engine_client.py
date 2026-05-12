import httpx

from app.core.config import settings


async def post_engine(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{settings.engine_url}{path}", json=payload)
        response.raise_for_status()
        return response.json()
