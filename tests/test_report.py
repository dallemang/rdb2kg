from pathlib import Path
import sqlalchemy as sa
import pytest

from rdb2kg.workspace_service import write_question, update_question, write_mapping
from rdb2kg.report import (
    validate_workspace,
    report_to_markdown,
    write_report,
    VALIDATED,
    MISMATCH,
    SPARQL_EMPTY,
    SPARQL_ERROR,
    NO_SPARQL,
    MANUAL,
)

MAPPING_TTL = """\
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

ALL_NAMES = "SELECT ?name WHERE { ?p <http://example.org/name> ?name }"


@pytest.fixture
def workspace(tmp_path):
    db = tmp_path / "test.db"
    url = f"sqlite:///{db}"
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE Person (PersonId INTEGER PRIMARY KEY, Name TEXT)"))
        conn.execute(sa.text("INSERT INTO Person VALUES (1, 'Alice'), (2, 'Bob')"))
    engine.dispose()

    write_mapping(tmp_path, MAPPING_TTL)
    return tmp_path, url


def test_no_mapping_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_workspace(tmp_path, "sqlite:///nope.db")


def test_validated_match(workspace):
    ws, url = workspace
    write_question(ws, "names", "What are the names?", sql="SELECT Name FROM Person")
    update_question(ws, "names", sparql=ALL_NAMES)

    report = validate_workspace(ws, url)
    assert report.total_triples > 0
    r = next(x for x in report.results if x.name == "names")
    assert r.status == VALIDATED
    assert r.sql_rows == 2 and r.sparql_rows == 2


def test_mismatch(workspace):
    ws, url = workspace
    write_question(ws, "one", "Just Alice?", sql="SELECT Name FROM Person WHERE PersonId = 1")
    update_question(ws, "one", sparql=ALL_NAMES)

    r = next(x for x in validate_workspace(ws, url).results if x.name == "one")
    assert r.status == MISMATCH
    assert r.sql_rows == 1 and r.sparql_rows == 2


def test_sparql_empty(workspace):
    ws, url = workspace
    write_question(ws, "missing", "Anything?", sql="SELECT Name FROM Person")
    update_question(ws, "missing", sparql="SELECT ?x WHERE { ?p <http://example.org/missing> ?x }")

    r = next(x for x in validate_workspace(ws, url).results if x.name == "missing")
    assert r.status == SPARQL_EMPTY


def test_sparql_error(workspace):
    ws, url = workspace
    write_question(ws, "bad", "Broken?", sql="SELECT Name FROM Person")
    update_question(ws, "bad", sparql="this is not sparql")

    r = next(x for x in validate_workspace(ws, url).results if x.name == "bad")
    assert r.status == SPARQL_ERROR


def test_no_sparql(workspace):
    ws, url = workspace
    write_question(ws, "pending", "Not done?", sql="SELECT Name FROM Person")

    r = next(x for x in validate_workspace(ws, url).results if x.name == "pending")
    assert r.status == NO_SPARQL


def test_manual_when_no_sql(workspace):
    ws, url = workspace
    write_question(ws, "noref", "No reference SQL?")
    update_question(ws, "noref", sparql=ALL_NAMES)

    r = next(x for x in validate_workspace(ws, url).results if x.name == "noref")
    assert r.status == MANUAL
    assert r.sparql_rows == 2


def test_report_markdown_and_file(workspace):
    ws, url = workspace
    write_question(ws, "names", "What are the names?", sql="SELECT Name FROM Person")
    update_question(ws, "names", sparql=ALL_NAMES)

    report = validate_workspace(ws, url)
    md = report_to_markdown(report)
    assert md.startswith("# Validation report")
    assert "**Summary:**" in md
    assert "## names" in md

    path = write_report(ws, report)
    assert path == ws / "output" / "report.md"
    assert path.read_text(encoding="utf-8").startswith("# Validation report")
