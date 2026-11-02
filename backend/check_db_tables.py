import asyncio
from sqlalchemy import text
from app.db.session import create_engine
from app.core.config import settings


async def main():
    engine = create_engine(settings.DATABASE_URL)

    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
        )

        for row in result:
            print(row[0])

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
