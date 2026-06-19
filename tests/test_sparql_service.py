from pathlib import Path
import pytest

from rdb2kg.sparql_service import query_sparql

GRAPH_TTL = """\
@prefix ex: <http://example.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://example.org/person/1> a ex:Person ;
    ex:name "Alice" ;
    ex:age 30 .

<http://example.org/person/2> a ex:Person ;
    ex:name "Bob" ;
    ex:age 25 .
"""


@pytest.fixture
def graph_path(tmp_path):
    path = tmp_path / "graph.ttl"
    path.write_text(GRAPH_TTL, encoding="utf-8")
    return path


def test_select_returns_rows(graph_path):
    result = query_sparql(
        graph_path,
        "PREFIX ex: <http://example.org/> "
        "SELECT ?name WHERE { ?p ex:name ?name } ORDER BY ?name",
    )
    assert result.columns == ["name"]
    assert len(result) == 2
    assert result.rows[0]["name"] == "Alice"
    assert result.rows[1]["name"] == "Bob"


def test_multiple_columns(graph_path):
    result = query_sparql(
        graph_path,
        "PREFIX ex: <http://example.org/> "
        "SELECT ?name ?age WHERE { ?p ex:name ?name ; ex:age ?age } ORDER BY ?name",
    )
    assert result.columns == ["name", "age"]
    assert result.rows[0] == {"name": "Alice", "age": 30}


def test_empty_result(graph_path):
    result = query_sparql(
        graph_path,
        "PREFIX ex: <http://example.org/> SELECT ?x WHERE { ?x ex:missing ?y }",
    )
    assert len(result) == 0
    assert result.rows == []


def test_unbound_is_none(graph_path):
    result = query_sparql(
        graph_path,
        "PREFIX ex: <http://example.org/> "
        "SELECT ?name ?nick WHERE { ?p ex:name ?name OPTIONAL { ?p ex:nickname ?nick } } "
        "ORDER BY ?name",
    )
    assert result.rows[0]["nick"] is None
