import tempfile
from pathlib import Path
import pytest
import sqlalchemy as sa

from rdb2kg.db_service import DatabaseService, DatabaseError


def _make_db(path: Path) -> str:
    url = f"sqlite:///{path}"
    engine = sa.create_engine(url)
    meta = sa.MetaData()
    sa.Table(
        "Artist", meta,
        sa.Column("ArtistId", sa.Integer, primary_key=True),
        sa.Column("Name", sa.Text),
    )
    sa.Table(
        "Album", meta,
        sa.Column("AlbumId", sa.Integer, primary_key=True),
        sa.Column("Title", sa.Text),
        sa.Column("ArtistId", sa.Integer, sa.ForeignKey("Artist.ArtistId")),
    )
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO Artist VALUES (1, 'AC/DC'), (2, 'Accept')"))
        conn.execute(sa.text("INSERT INTO Album VALUES (1, 'For Those About To Rock', 1), (2, 'Balls to the Wall', 2)"))
    engine.dispose()
    return url


@pytest.fixture
def db_url(tmp_path):
    path = tmp_path / "test.db"
    return _make_db(path)


def test_context_manager(db_url):
    with DatabaseService(db_url) as db:
        assert db._engine is not None
    assert db._engine is None


def test_query_returns_rows(db_url):
    with DatabaseService(db_url) as db:
        result = db.query("SELECT * FROM Artist ORDER BY ArtistId")
    assert len(result) == 2
    assert result.rows[0]["Name"] == "AC/DC"
    assert result.rows[1]["Name"] == "Accept"


def test_query_columns(db_url):
    with DatabaseService(db_url) as db:
        result = db.query("SELECT ArtistId, Name FROM Artist LIMIT 1")
    assert result.columns == ["ArtistId", "Name"]


def test_query_params(db_url):
    with DatabaseService(db_url) as db:
        result = db.query("SELECT Name FROM Artist WHERE ArtistId = :id", {"id": 2})
    assert len(result) == 1
    assert result.rows[0]["Name"] == "Accept"


def test_query_empty_result(db_url):
    with DatabaseService(db_url) as db:
        result = db.query("SELECT * FROM Artist WHERE ArtistId = 999")
    assert len(result) == 0
    assert result.rows == []


def test_query_iterable(db_url):
    with DatabaseService(db_url) as db:
        result = db.query("SELECT Name FROM Artist ORDER BY ArtistId")
    names = [row["Name"] for row in result]
    assert names == ["AC/DC", "Accept"]


def test_schema_tables(db_url):
    with DatabaseService(db_url) as db:
        schema = db.schema()
    table_names = {t.name for t in schema.tables}
    assert "Artist" in table_names
    assert "Album" in table_names


def test_schema_row_counts(db_url):
    with DatabaseService(db_url) as db:
        schema = db.schema()
    artist = next(t for t in schema.tables if t.name == "Artist")
    assert artist.row_count == 2


def test_schema_foreign_key(db_url):
    with DatabaseService(db_url) as db:
        schema = db.schema()
    album = next(t for t in schema.tables if t.name == "Album")
    assert len(album.foreign_keys) == 1
    fk = album.foreign_keys[0]
    assert fk.referred_table == "Artist"


def test_not_connected_raises(db_url):
    db = DatabaseService(db_url)
    with pytest.raises(DatabaseError, match="Not connected"):
        db.query("SELECT 1")


def test_bad_url_raises():
    with pytest.raises(DatabaseError, match="Could not connect"):
        DatabaseService("sqlite:////nonexistent/path/to/missing.db").connect()


def test_bad_sql_raises(db_url):
    with DatabaseService(db_url) as db:
        with pytest.raises(DatabaseError, match="Query failed"):
            db.query("SELECT * FROM NonExistentTable")


def test_connect_disconnect_explicit(db_url):
    db = DatabaseService(db_url)
    db.connect()
    result = db.query("SELECT COUNT(*) AS n FROM Artist")
    assert result.rows[0]["n"] == 2
    db.disconnect()
    assert db._engine is None
