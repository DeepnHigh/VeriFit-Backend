"""
One-off script: ensure `ai_evaluations` table has `highlight` and `highlight_reason` columns.
Usage:
  python scripts/add_ai_evaluation_columns.py
The script reads DATABASE_URL from app.core.config.settings and adds columns if missing.
"""
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings


def main():
    db_url = settings.database_url
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Check if columns already exist
        for col in ("highlight", "highlight_reason"):
            res = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='ai_evaluations' AND column_name=:col"
            ), {"col": col}).fetchone()
            if res:
                print(f"Column '{col}' already exists")
            else:
                print(f"Adding column '{col}'")
                conn.execute(text(f"ALTER TABLE ai_evaluations ADD COLUMN {col} text"))
                print(f"Added column '{col}'")
        # Commit if using transactional DDL (Postgres executes DDL in transaction)
        try:
            conn.execute(text("COMMIT"))
        except Exception:
            pass

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error:', e)
        sys.exit(1)
    print('Done')
