import tempfile
from pathlib import Path
import sqlalchemy as sa
from rdb2kg.inspect_db import inspect_database


def _make_db(path: Path) -> str:
    url = f"sqlite:///{path}"
    engine = sa.create_engine(url)
    meta = sa.MetaData()
    sa.Table(
        "Person", meta,
        sa.Column("PersonId", sa.Integer, primary_key=True),
        sa.Column("Name", sa.Text),
    )
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO Person VALUES (1, 'Alice'), (2, 'Bob')"))
    engine.dispose()
    return url


def test_inspect_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        url = _make_db(db_path)
        schema = inspect_database(url)
        assert len(schema.tables) == 1
        table = schema.tables[0]
        assert table.name == "Person"
        assert table.row_count == 2
        col_names = [c.name for c in table.columns]
        assert "PersonId" in col_names
        assert "Name" in col_names
    finally:
        db_path.unlink(missing_ok=True)


def test_inspect_primary_key():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        url = _make_db(db_path)
        schema = inspect_database(url)
        table = schema.tables[0]
        pk_cols = [c for c in table.columns if c.primary_key]
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "PersonId"
    finally:
        db_path.unlink(missing_ok=True)


def test_inspect_foreign_key():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    url = f"sqlite:///{db_path}"
    engine = sa.create_engine(url)
    meta = sa.MetaData()
    sa.Table("Author", meta, sa.Column("AuthorId", sa.Integer, primary_key=True))
    sa.Table(
        "Book", meta,
        sa.Column("BookId", sa.Integer, primary_key=True),
        sa.Column("AuthorId", sa.Integer, sa.ForeignKey("Author.AuthorId")),
    )
    meta.create_all(engine)
    engine.dispose()
    try:
        schema = inspect_database(url)
        book_table = next(t for t in schema.tables if t.name == "Book")
        assert len(book_table.foreign_keys) == 1
        fk = book_table.foreign_keys[0]
        assert fk.referred_table == "Author"
        assert "AuthorId" in fk.constrained_columns
    finally:
        db_path.unlink(missing_ok=True)
