"""
Standalone script to create all database tables in PostgreSQL.

Usage:
    python create_tables.py
"""

import asyncio
from app.db.database import Base, engine
import app.models


async def init_tables():
    print("Connecting to PostgreSQL and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully: 'conversations', 'messages', 'provider_configs'.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_tables())
