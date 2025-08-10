from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

# Add SSL parameters if needed
DATABASE_URL = DATABASE_URL + "?sslmode=require"
engine = create_engine(DATABASE_URL, echo=True)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Connection successful: {result.fetchone()}")
        # List tables
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        print("Tables in database:", [row[0] for row in tables.fetchall()])
except Exception as e:
    print(f"Connection failed: {e}")
finally:
    engine.dispose()
