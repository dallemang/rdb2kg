from pathlib import Path

from .db_service import QueryResult


def query_sparql(graph_path: Path, sparql: str) -> QueryResult:
    """Run a SPARQL SELECT against a Turtle graph file.

    Uses pyoxigraph when available (better optimizer, mtime-cached in-process store).
    Falls back to rdflib if pyoxigraph is not installed.
    """
    try:
        from . import ox_store
        return ox_store.query(graph_path, sparql)
    except ImportError:
        return _query_rdflib(graph_path, sparql)


def _query_rdflib(graph_path: Path, sparql: str) -> QueryResult:
    from rdflib import Graph
    g = Graph()
    g.parse(str(graph_path), format="turtle")
    result = g.query(sparql)
    columns = [str(v) for v in result.vars]
    rows = [
        {col: (val.toPython() if val is not None else None) for col, val in zip(columns, row)}
        for row in result
    ]
    return QueryResult(columns=columns, rows=rows)
