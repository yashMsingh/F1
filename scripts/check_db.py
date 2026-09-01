"""Utility script to verify database connectivity and print table status."""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect
from app.db.session import get_engine


def main():
    try:
        engine = get_engine(echo=False)
        with engine.connect() as conn:
            print("Successfully connected to PostgreSQL database.")
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"Found {len(tables)} tables: {', '.join(sorted(tables))}")
    except Exception as e:
        print(f"Database connection error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
