"""
Database connection utilities for MySQL.
"""

import os
from typing import Optional
import aiomysql


class DatabasePool:
    """Singleton database connection pool manager."""
    
    _instance = None
    _pool: Optional[aiomysql.Pool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        minsize: int = 5,
        maxsize: int = 20,
    ):
        """Initialize the connection pool."""
        self._pool = await aiomysql.create_pool(
            host=host or os.getenv("DB_HOST", "localhost"),
            port=port or int(os.getenv("DB_PORT", "3306")),
            user=user or os.getenv("DB_USER", "root"),
            password=password or os.getenv("DB_PASSWORD", ""),
            db=database or os.getenv("DB_NAME", "test"),
            minsize=minsize,
            maxsize=maxsize,
            pool_recycle=3600,
            autocommit=True,
        )
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
    
    @property
    def pool(self) -> Optional[aiomysql.Pool]:
        """Get the connection pool."""
        return self._pool
    
    async def health_check(self) -> bool:
        """Check if database is reachable."""
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
                    return True
        except Exception:
            return False


db_pool = DatabasePool()
