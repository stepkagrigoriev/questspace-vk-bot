import os
from redis.asyncio import Redis
from typing import cast, Awaitable

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)


async def ping():
    await cast(Awaitable[bool], r.ping())


async def save_token(vk_id: int, token: str):
    await r.set(f"user:{vk_id}:token", token)


async def get_token(vk_id: int) -> str | None:
    return await r.get(f"user:{vk_id}:token")


async def save_active_quest(vk_id: int, quest_id: str):
    await r.set(f"user:{vk_id}:quest", quest_id)


async def get_active_quest(vk_id: int) -> str | None:
    return await r.get(f"user:{vk_id}:quest")


async def clear_tasks(vk_id: int):
    await r.delete(f"user:{vk_id}:tasks")


async def save_task(vk_id: int, short_id: int, real_uuid: str):
    await cast(Awaitable[int], r.hset(f"user:{vk_id}:tasks", str(short_id), real_uuid))


async def get_task(vk_id: int, short_id: str) -> str | None:
    return await cast(
        Awaitable[str | None], r.hget(f"user:{vk_id}:tasks", str(short_id))
    )


async def remove_task(vk_id: int, short_id: str):
    await cast(Awaitable[int], r.hdel(f"user:{vk_id}:tasks", str(short_id)))
