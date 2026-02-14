"""asyncpg 커넥션 풀 관리"""

import asyncpg
from contextlib import asynccontextmanager

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str, min_size: int = 2, max_size: int = 10):
    """DB 커넥션 풀 초기화"""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn, min_size=min_size, max_size=max_size, command_timeout=30
    )


async def close_pool():
    """DB 커넥션 풀 종료"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn():
    """커넥션 획득 컨텍스트 매니저"""
    if _pool is None:
        raise RuntimeError("DB 풀이 초기화되지 않았습니다. init_pool()을 먼저 호출하세요.")
    async with _pool.acquire() as conn:
        yield conn
