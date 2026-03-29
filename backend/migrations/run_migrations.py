"""Run all SQL migrations in order."""
import asyncio
import os
from pathlib import Path
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def run():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)

    migrations_dir = Path(__file__).parent
    sql_files = sorted(migrations_dir.glob("*.sql"))

    for sql_file in sql_files:
        print(f"Running {sql_file.name}...")
        sql = sql_file.read_text()
        await conn.execute(sql)
        print(f"  done.")

    await conn.close()
    print("All migrations complete.")


if __name__ == "__main__":
    asyncio.run(run())
