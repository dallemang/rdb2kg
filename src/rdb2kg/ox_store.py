"""
In-memory SPARQL store backed by pyoxigraph.

The store is keyed by absolute path + mtime, so it is reloaded automatically
whenever the source file changes and reused across calls when it has not.
Thread-safe via a per-path lock.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .db_service import QueryResult

# cache: abs_path -> (store, mtime)
_cache: dict[str, tuple[Any, float]] = {}
_lock = threading.Lock()


def _term_value(term: Any) -> Any:
    if term is None:
        return None
    try:
        from pyoxigraph import Literal
        if isinstance(term, Literal):
            val = term.value
            dt = term.datatype.value if term.datatype else ""
            xsd = "http://www.w3.org/2001/XMLSchema#"
            if dt in {xsd + s for s in ("integer", "long", "int", "short", "byte",
                                         "nonNegativeInteger", "positiveInteger",
                                         "nonPositiveInteger", "negativeInteger",
                                         "unsignedLong", "unsignedInt", "unsignedShort",
                                         "unsignedByte")}:
                try:
                    return int(val)
                except ValueError:
                    pass
            if dt in {xsd + s for s in ("decimal", "float", "double")}:
                try:
                    return float(val)
                except ValueError:
                    pass
            if dt == xsd + "boolean":
                return val.lower() == "true"
            return val
    except Exception:
        pass
    # NamedNode, BlankNode, or anything unexpected
    return str(getattr(term, "value", term))


def _load(graph_path: Path) -> Any:
    """Load or return the cached store for graph_path."""
    from pyoxigraph import Store

    abs_path = str(graph_path.resolve())
    mtime = graph_path.stat().st_mtime

    with _lock:
        cached = _cache.get(abs_path)
        if cached is not None and cached[1] == mtime:
            return cached[0]
        store = Store()
        with open(graph_path, "rb") as fh:
            store.load(fh, "text/turtle")
        _cache[abs_path] = (store, mtime)
        return store


def load_and_report(graph_path: Path) -> str:
    """Load (or reload) graph_path into the cache and return a status string."""
    store = _load(graph_path)
    try:
        n = len(store)
        return f"Loaded {n} triples from {graph_path}"
    except Exception:
        return f"Graph loaded from {graph_path}"


def query(graph_path: Path, sparql: str) -> QueryResult:
    store = _load(graph_path)
    results = store.query(sparql)

    # ASK query
    if isinstance(results, bool):
        return QueryResult(columns=["result"], rows=[{"result": results}])

    # CONSTRUCT / DESCRIBE — not typical in this workflow, handle gracefully
    if not hasattr(results, "variables"):
        return QueryResult(columns=[], rows=[])

    # SELECT query — collect variables first; solutions are consumed on iteration
    variables = list(results.variables)
    columns = [v.value for v in variables]
    rows = []
    for solution in results:
        row = {}
        for var in variables:
            try:
                row[var.value] = _term_value(solution[var])
            except KeyError:
                row[var.value] = None
        rows.append(row)
    return QueryResult(columns=columns, rows=rows)
