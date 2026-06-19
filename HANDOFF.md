# Handoff note — for incoming Opus session

Read `STATUS.md` first. Everything below is context that isn't in that file.

---

## What this project is

`rdb2kg` turns relational databases into OWL-ontology-backed RDF knowledge graphs.
The user provides a DB connection string and optional business documents; an AI-driven
workflow elicits competency questions, designs an ontology, generates an R2RML mapping,
materialises the graph, and validates it by comparing SPARQL results against reference SQL.

The intended end-user interface is an **MCP server** (see STATUS.md architecture section).
The current interim is `workspace/CLAUDE.md`, which drives a Claude Code session using
raw Python snippets instead of MCP tools. Both paths are valid for now.

---

## What already works (verified this session)

- `src/rdb2kg/inspect_db.py` — `inspect_database(url)` and `schema_to_yaml()` work
- `src/rdb2kg/db_service.py` — `DatabaseService` context manager works
- `src/rdb2kg/r2rml.py` — parses R2RML Turtle into dataclasses
- `src/rdb2kg/materialize.py` — executes mapping, writes TTL; tested at 50k triples in 9s
- `src/rdb2kg/cli.py` — `rdb2kg inspect` and `rdb2kg materialize` work
- `examples/chinook/chinook_full.db` — full Chinook dataset (275 artists, 3503 tracks, etc.),
  downloaded this session; the existing `examples/chinook/mapping.ttl` runs against it cleanly

---

## What you're here to do: P1 Foundation tasks

Three tasks, in order:

### 1. Housekeeping — `pyproject.toml`
- Remove `rich` from `dependencies` (it was removed from all library code in a prior session
  but the declaration was never cleaned up)
- Add `pytest` under `[project.optional-dependencies]` as `dev = ["pytest"]`
  so `pip install -e .[dev]` gives a working test environment

### 2. SPARQL query helper
Add `query_sparql(graph_path: Path, sparql: str) -> QueryResult` to the library.
It should: parse the TTL file with rdflib, run the SPARQL SELECT, and return results
in the same `QueryResult` shape as `DatabaseService.query()` (columns + list of dicts).
Put it in `src/rdb2kg/sparql_service.py`. Add tests in `tests/test_sparql_service.py`.
`QueryResult` is defined in `db_service.py` — import from there, don't duplicate it.

### 3. MCP server
Create `src/rdb2kg/mcp_server.py` exposing four tools:
- `inspect_schema(connection_string)` → schema YAML string
- `query_sql(connection_string, sql)` → list of row dicts
- `materialize(connection_string, mapping_path, output_path)` → report summary string
- `query_sparql(graph_path, sparql)` → list of row dicts

Use the `mcp` Python SDK (`pip install mcp`). The server should run as a stdio process
(`mcp.run()` default). Add `mcp` to `pyproject.toml` dependencies.

---

## Environment notes

- **Use the venv**: a dedicated `.venv` (Python 3.12) is the project environment.
  Activate it (`.venv\Scripts\activate`) or call `.\.venv\Scripts\python.exe` directly.
  Do NOT use the bare `python` on PATH (Microsoft Store install) — it's a separate
  environment with unrelated packages. Use the PowerShell tool, not Bash, for Python.
- **Recreate the venv** from scratch (e.g. after a clean clone):
  `python -m venv .venv` then `.venv\Scripts\python -m pip install -r requirements.txt`.
  `requirements.txt` installs `rdb2kg` editable with dev extras; dependency lists
  live in `pyproject.toml` (single source of truth).
- **Tests**: `.venv\Scripts\python -m pytest` (pytest comes from the `dev` extra).

---

## Style rules (from prior sessions)

- No comments in code unless the *why* is genuinely non-obvious
- No Rich markup anywhere in library code — plain `print()` only
- No docstrings beyond a single short line if truly needed
- Don't add error handling for things that can't happen; validate at boundaries only
- Prefer editing existing files to creating new ones
