import tempfile
from pathlib import Path
import sqlalchemy as sa
from rdflib import URIRef, Literal
from rdflib.namespace import RDF
from rdb2kg.r2rml import parse_mapping
from rdb2kg.materialize import materialize, expand_template

SIMPLE_TTL = """\
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .

<#PersonMap>
    rr:logicalTable [ rr:tableName "Person" ] ;
    rr:subjectMap [
        rr:template "http://example.org/person/{PersonId}" ;
        rr:class ex:Person
    ] ;
    rr:predicateObjectMap [
        rr:predicate ex:name ;
        rr:objectMap [ rr:column "Name" ]
    ] .
"""

JOIN_TTL = """\
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .

<#AuthorMap>
    rr:logicalTable [ rr:tableName "Author" ] ;
    rr:subjectMap [
        rr:template "http://example.org/author/{AuthorId}" ;
        rr:class ex:Author
    ] .

<#BookMap>
    rr:logicalTable [ rr:tableName "Book" ] ;
    rr:subjectMap [
        rr:template "http://example.org/book/{BookId}" ;
        rr:class ex:Book
    ] ;
    rr:predicateObjectMap [
        rr:predicate ex:writtenBy ;
        rr:objectMap [
            rr:parentTriplesMap <#AuthorMap> ;
            rr:joinCondition [ rr:child "AuthorId" ; rr:parent "AuthorId" ]
        ]
    ] .
"""


def _make_person_db(path: Path) -> str:
    url = f"sqlite:///{path}"
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE Person (PersonId INTEGER PRIMARY KEY, Name TEXT)"
        ))
        conn.execute(sa.text("INSERT INTO Person VALUES (1, 'Alice'), (2, 'Bob')"))
    engine.dispose()
    return url


def _write_ttl(content: str, dir_: Path) -> Path:
    path = dir_ / "mapping.ttl"
    path.write_text(content, encoding="utf-8")
    return path


# ── template expansion ────────────────────────────────────────────────────────

def test_expand_template_basic():
    assert expand_template("http://ex.org/p/{Id}", {"Id": 42}) == "http://ex.org/p/42"


def test_expand_template_null_returns_none():
    assert expand_template("http://ex.org/p/{Id}", {"Id": None}) is None


def test_expand_template_encodes_spaces():
    result = expand_template("http://ex.org/p/{Name}", {"Name": "Alice Smith"})
    assert result == "http://ex.org/p/Alice%20Smith"


def test_expand_template_no_encoding_for_literal():
    result = expand_template("Hello {Name}", {"Name": "Alice Smith"}, for_iri=False)
    assert result == "Hello Alice Smith"


# ── basic materialization ─────────────────────────────────────────────────────

def test_materialize_type_triples():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        url = _make_person_db(d / "db.db")
        mapping = parse_mapping(_write_ttl(SIMPLE_TTL, d))
        g, report = materialize(url, mapping, d / "out.ttl")

        assert (
            URIRef("http://example.org/person/1"),
            RDF.type,
            URIRef("http://example.org/Person"),
        ) in g
        assert (
            URIRef("http://example.org/person/2"),
            RDF.type,
            URIRef("http://example.org/Person"),
        ) in g


def test_materialize_literal_property():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        url = _make_person_db(d / "db.db")
        mapping = parse_mapping(_write_ttl(SIMPLE_TTL, d))
        g, _ = materialize(url, mapping, d / "out.ttl")

        assert (
            URIRef("http://example.org/person/1"),
            URIRef("http://example.org/name"),
            Literal("Alice"),
        ) in g


def test_materialize_report_counts():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        url = _make_person_db(d / "db.db")
        mapping = parse_mapping(_write_ttl(SIMPLE_TTL, d))
        _, report = materialize(url, mapping, d / "out.ttl")

        assert report.total_triples > 0
        assert len(report.map_stats) == 1
        stats = report.map_stats[0]
        assert stats.rows_read == 2
        assert stats.subjects_created == 2


def test_materialize_output_file_written():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        url = _make_person_db(d / "db.db")
        mapping = parse_mapping(_write_ttl(SIMPLE_TTL, d))
        out = d / "out.ttl"
        materialize(url, mapping, out)
        assert out.exists()
        assert out.stat().st_size > 0


# ── join materialization ──────────────────────────────────────────────────────

def test_materialize_join():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        url = f"sqlite:///{d / 'db.db'}"
        engine = sa.create_engine(url)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "CREATE TABLE Author (AuthorId INTEGER PRIMARY KEY, Name TEXT)"
            ))
            conn.execute(sa.text(
                "CREATE TABLE Book (BookId INTEGER PRIMARY KEY, Title TEXT, AuthorId INTEGER)"
            ))
            conn.execute(sa.text("INSERT INTO Author VALUES (1, 'Tolkien')"))
            conn.execute(sa.text("INSERT INTO Book VALUES (1, 'The Hobbit', 1)"))
        engine.dispose()

        mapping = parse_mapping(_write_ttl(JOIN_TTL, d))
        g, report = materialize(url, mapping, d / "out.ttl")

        assert (
            URIRef("http://example.org/book/1"),
            URIRef("http://example.org/writtenBy"),
            URIRef("http://example.org/author/1"),
        ) in g

        book_stats = next(s for s in report.map_stats
                          if "Book" in s.sql or "book" in s.map_id.lower())
        join = book_stats.join_stats[0]
        assert join.matched == 1
        assert join.unmatched == 0
