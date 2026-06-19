from dataclasses import dataclass, field
from typing import Any
import sqlalchemy as sa

from .inspect_db import DatabaseSchema, inspect_database


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)


class DatabaseError(Exception):
    pass


class DatabaseService:
    """Connection to a relational database via SQLAlchemy URL.

    Usage::
        with DatabaseService("sqlite:///chinook.db") as db:
            result = db.query("SELECT * FROM Artist LIMIT 5")
            for row in result:
                print(row["Name"])
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._engine: sa.Engine | None = None

    # --- lifecycle ---

    def connect(self) -> "DatabaseService":
        if self._engine is None:
            try:
                self._engine = sa.create_engine(self.url)
                # Verify the connection is reachable on first connect.
                with self._engine.connect():
                    pass
            except Exception as exc:
                self._engine = None
                raise DatabaseError(f"Could not connect to {self.url!r}: {exc}") from exc
        return self

    def disconnect(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def __enter__(self) -> "DatabaseService":
        return self.connect()

    def __exit__(self, *_) -> None:
        self.disconnect()

    # --- public API ---

    def query(self, sql: str, params: dict[str, Any] | None = None) -> QueryResult:
        """Execute *sql* and return all rows as a QueryResult.

        Parameters are passed as a dict and referenced in SQL with :name syntax,
        e.g. ``SELECT * FROM Artist WHERE ArtistId = :id`` with ``params={"id": 1}``.
        """
        self._require_connected()
        try:
            with self._engine.connect() as conn:
                stmt = sa.text(sql)
                result = conn.execute(stmt, params or {})
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return QueryResult(columns=columns, rows=rows)
        except sa.exc.SQLAlchemyError as exc:
            raise DatabaseError(f"Query failed: {exc}") from exc

    def schema(self) -> DatabaseSchema:
        """Return the full schema of the connected database."""
        self._require_connected()
        return inspect_database(self.url)

    # --- internals ---

    def _require_connected(self) -> None:
        if self._engine is None:
            raise DatabaseError("Not connected. Call connect() or use as a context manager.")
