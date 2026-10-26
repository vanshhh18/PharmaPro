"""Create the AIVOA database schema (idempotent).

Run from the `backend/` directory with the virtual environment active:

    python -m app.init_db

Uses SQLAlchemy `create_all`, so it only creates tables that do not exist yet
and never alters existing tables. Re-run safely after adding data is required
only when models change; for model changes, drop the database/volume or apply
changes manually.
"""

from .db import check_database, get_engine
from .models import Base


def init_db() -> bool:
    connected, detail = check_database()
    if not connected:
        print(f"Database not reachable: {detail}")
        return False
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Schema ensured (create_all).")
    return True


if __name__ == "__main__":
    ok = init_db()
    raise SystemExit(0 if ok else 1)
