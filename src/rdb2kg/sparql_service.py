from pathlib import Path
from rdflib import Graph

from .db_service import QueryResult


def query_sparql(graph_path: Path, sparql: str) -> QueryResult:
    g = Graph()
    g.parse(str(graph_path), format="turtle")
    result = g.query(sparql)
    columns = [str(v) for v in result.vars]
    rows = [
        {col: (val.toPython() if val is not None else None) for col, val in zip(columns, row)}
        for row in result
    ]
    return QueryResult(columns=columns, rows=rows)
