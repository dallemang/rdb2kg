# rdb2kg — Project Status

## Pipeline components

| Module | Description | Interface | Status |
|---|---|---|---|
| `src/rdb2kg/inspect_db.py` | Connects to any SQLAlchemy-supported database and returns table names, column types, primary keys, foreign keys, and row counts; also serialises the schema to a compact YAML string suitable for LLM consumption | Python API: `inspect_database(url) → DatabaseSchema`, `schema_to_yaml(schema) → str`; CLI: `rdb2kg inspect <db>` | Working |
| `src/rdb2kg/db_service.py` | Thin context-manager wrapper around SQLAlchemy that executes parameterized SQL and returns results as a list of dicts | Python API: `DatabaseService(url)` as context manager; `.query(sql, params) → QueryResult`, `.schema() → DatabaseSchema` | Working |
| `src/rdb2kg/r2rml.py` | Parses an R2RML mapping file (Turtle) into Python dataclasses (`TriplesMap`, `SubjectMap`, `PredicateObjectMap`, `ObjectMap`) including join conditions and IRI templates | Python API: `parse_mapping(path) → R2RMLMapping` | Working |
| `src/rdb2kg/materialize.py` | Executes an R2RML mapping against a live database and writes all generated triples to a Turtle file; returns a report with per-map triple counts and warnings | Python API: `materialize(url, mapping, output_path) → (Graph, MaterializationReport)` | Working |
| `src/rdb2kg/cli.py` | Command-line entry point exposing `inspect` and `materialize` as subcommands | CLI: `rdb2kg inspect <db>`, `rdb2kg materialize <db> <mapping.ttl> [-o output.ttl]` | Working |
| `src/rdb2kg/sparql_service.py` | Parses a Turtle graph file with rdflib, runs a SPARQL SELECT, and returns results in the same `QueryResult` shape as `DatabaseService.query()` | Python API: `query_sparql(graph_path, sparql) → QueryResult` | Working |
| `src/rdb2kg/workspace_service.py` | Workspace plumbing for the ontology-engineering loop: reads background docs, reads/writes/updates competency questions (`questions/*.yaml`), diffs them against a snapshot for the review gate, and writes ontology/mapping artifacts. All functions take the workspace dir as first arg | Python API: `read_background`, `read_questions`, `write_question`, `update_question`, `diff_questions`, `write_ontology`, `write_mapping` | Working |
| `src/rdb2kg/report.py` | Validation report: materialises the graph, runs each competency question's reference SQL and its SPARQL, compares the result sets, diagnoses mismatches, and renders `output/report.md` | Python API: `validate_workspace(dir, connection_string) → ValidationReport`, `report_to_markdown(report) → str`, `write_report(dir, report) → Path` | Working |
| `src/rdb2kg/mcp_server.py` | MCP (stdio) server exposing the core operations as tools for any MCP-compatible LLM client | Run: `python -m rdb2kg.mcp_server`; 12 tools: `inspect_schema`, `query_sql`, `materialize`, `query_sparql`, `read_background`, `read_questions`, `write_question`, `update_question`, `diff_questions`, `write_ontology`, `write_mapping`, `validate` | Working |
| `examples/chinook/mapping.ttl` | Complete R2RML mapping for the Chinook music-store database (11 triples maps); includes a worked example of string-column → external IRI using SQL `CASE` + `rr:template` for ISO 3166-1 country codes | Reference file — not called directly; used as a template for new mappings | Working |
| `workspace/CLAUDE.md` | Workflow instructions that drive a Claude Code session for a new user: startup inventory, competency question elicitation, ontology design, R2RML generation, SPARQL validation, and iteration | Loaded automatically by Claude Code when run from `workspace/`; not a Python module | Written |
| `workspace/questions/*.yaml` | Five example competency questions for Chinook, each with a natural-language question, optional notes, and a reference SQL query | Read by the workspace Claude session at startup; written by Claude during Step 1 | Written |

## User journey (target experience)

### Setup (once)

1. Clone the repo on Windows (Mac TBD, same approach)
2. Create a Python venv and `pip install -e .` — this installs the rdb2kg library and its dependencies
3. Start the MCP server: `python -m rdb2kg.mcp_server` (yes, MCP servers can be plain Python processes; the MCP SDK handles the stdio/HTTP transport)
4. Point their MCP-compatible LLM client (Claude Code, Cursor, etc.) at the server

### Per-project setup (workspace)

5. Create a workspace directory and `cd` into it
6. Provide a database connection:
   - **Bundled test DB**: copy one of the provided examples (e.g. `chinook_full.db`) and write `sqlite:///chinook_full.db` to `connection.txt`
   - **Kaggle or downloaded SQLite**: follow provided directions to download the file, then write the connection string
   - **Live database**: write a `postgresql://...` or `mysql://...` connection string; install the appropriate driver
7. Optionally drop business documents into `background/` — demo scripts, data dictionaries, architecture docs, corporate glossaries

### Automated phase (LLM-driven, minimal user interaction)

8. **Schema scrape**: system connects to the database and extracts the full schema (tables, columns, types, PKs, FKs, row counts) — saved to `output/schema.yaml`
9. **Question generation**: LLM reads the schema and any background documents and proposes competency questions grounded in the business domain
10. **User review** *(optional gate)*: questions are written to `questions/*.yaml`; user can edit, add, or delete files before continuing — or skip straight through
11. **Parallel build**: LLM constructs three things in lockstep for each question:
    - The OWL ontology fragment (classes and properties needed to answer it)
    - The SPARQL query that would answer it against the knowledge graph
    - The R2RML mapping fragment that connects the relevant tables to the ontology
12. **Materialization**: R2RML mapping is executed against the live database to produce the RDF graph
13. **Validation**: each SPARQL query is run against the graph; results are compared to the reference SQL result where one exists

### Progress and metering

Throughout steps 8–13, the system reports:
- Current step and which question is being processed
- Token usage so far (input + output, with running cost estimate)
- Triples produced, questions validated vs. pending

### Completion

14. **Report**: summary of how many questions are fully validated, which need attention, and why (mapping gap, ontology mismatch, SPARQL error)
15. **Iteration**: user edits `questions/*.yaml` (add, remove, or refine) and re-runs from step 11 — schema and background docs do not need to be re-read unless the database changed

### Open questions for this journey

- Docker packaging: defer until the above works cleanly on bare Windows; Docker adds reliability but also friction for users who aren't familiar with it
- Mac support: expected to be identical; worth a separate test pass once Windows is stable
- Token metering: requires hooking into the LLM client's response metadata — straightforward with the Anthropic SDK, needs abstraction for other LLMs
- The build in step 11 is opportunistic, not parallel — the LLM constructs ontology fragments, SPARQL queries, and mapping fragments incrementally as it reasons through each question; there is no fixed order

---

## Architecture decision: MCP server

The chosen architecture for the end-user interface is an **MCP (Model Context Protocol) server**. rdb2kg exposes its core operations as MCP tools; the LLM (whatever the user brings — Claude, GPT-4, a local Ollama model) owns the workflow reasoning and calls the tools as needed.

This gives both advantages of the two approaches considered:
- **Dynamic workflow**: the LLM reasons about what to do next, handles edge cases, and adapts — not a fixed state machine
- **LLM-agnostic**: any MCP-compatible client can connect; the tools are not tied to Claude Code or any specific vendor
- **Claude Code compatibility**: `workspace/CLAUDE.md` continues to work as-is for Claude Code users; it becomes one client of the MCP server rather than the only path
- **Testability**: the MCP tools are ordinary Python functions that can be unit-tested independently of any LLM

Tools to expose via MCP: `inspect_schema`, `query_sql`, `materialize`, `query_sparql`. These map directly to the existing Python library functions.

The current `workspace/CLAUDE.md` raw-Python-snippet approach is an interim solution that stays valid until the MCP server is built.

## Planned work — prioritised

### P1 — Foundation (unblocks everything else) — DONE

| Task | Notes |
|---|---|
| ✅ Housekeeping: drop `rich`, add `pytest` | `rich` removed from `pyproject.toml`; `pytest` added under `[project.optional-dependencies]` as `dev`; `mcp>=1.0` added to dependencies |
| ✅ SPARQL query helper | `query_sparql(graph_path, sparql) → QueryResult` in `src/rdb2kg/sparql_service.py`; tested in `tests/test_sparql_service.py` |
| ✅ MCP server | `src/rdb2kg/mcp_server.py` exposes `inspect_schema`, `query_sql`, `materialize`, `query_sparql` as stdio MCP tools via FastMCP; run with `python -m rdb2kg.mcp_server` |

### P2 — Core workflow (the ontology engineering loop) — DONE

All plumbing lives in `src/rdb2kg/workspace_service.py` (functions take the workspace dir as first arg), is exposed as MCP tools in `mcp_server.py`, and is driven by `workspace/CLAUDE.md`. The reasoning steps (generation, critique, build) are LLM activities; the tools are the read/write plumbing that supports them.

| Task | Dependencies | Notes |
|---|---|---|
| ✅ Background document ingestion | MCP server | `read_background(dir)` concatenates text files in `background/` with per-file headers; skips binaries; demo scripts/data dictionaries are the highest-value input |
| ✅ Question generation from business docs | Background ingestion | LLM proposes questions from schema YAML + background text; `write_question(dir, name, question, notes=, sql=, source=)` persists each, with `source` tracing it to a schema feature or background doc |
| ✅ User review gate | Question generation | `read_questions(dir)` re-reads `questions/*.yaml`; `diff_questions(dir)` diffs against a snapshot (`output/.question_snapshot.json`) and refreshes it — reports added/removed/modified/unchanged |
| ✅ AI review of question quality | User review | CLAUDE.md drives an advisory critique pass (coverage, vagueness, testability, redundancy) over `read_questions`; the LLM does not silently rewrite the user's questions |
| ✅ Opportunistic ontology/mapping/SPARQL build | Question generation | `write_ontology(dir, turtle)` / `write_mapping(dir, turtle)` persist fragments as the LLM builds them incrementally; `update_question(dir, name, sparql=, status=)` records the SPARQL + validation status. No fixed order enforced |

### P3 — Completion and reporting

| Task | Dependencies | Notes |
|---|---|---|
| ✅ Validation report | Materialize, SPARQL helper | `src/rdb2kg/report.py`: `validate_workspace(dir, connection_string)` re-materialises the graph, runs each question's SQL + SPARQL, compares result sets (order- and column-name-insensitive, type-normalised), and buckets each as `validated` / `mismatch` / `sparql_empty` / `sparql_error` / `sql_error` / `no_sparql` / `manual`. `write_report` renders `output/report.md` (ASCII-safe). Exposed as MCP tool `validate`; driven from CLAUDE.md Step 4. Verified end-to-end on full Chinook (50,953 triples) |
| Progress and token metering | MCP server | DEFERRED by decision: the MCP server runs as a separate process and cannot see the client's token usage (that's client-side API metadata). Revisit with a concrete client integration; a triples/steps/validation progress counter is the cheap honest subset if needed before then |

### P4 — Onboarding and examples

| Task | Notes |
|---|---|
| ✅ Windows setup instructions | `SETUP.md` (linked from README): prerequisites, venv + `pip install -r requirements.txt`, verify, end-to-end Chinook trial via the `workspace/`, MCP server route, connection-string formats + driver installs, troubleshooting. Verified the documented quick-try flow end-to-end (connection.txt creation reads clean, 50,953 triples, report generates). Note: doc warns against `Out-File -Encoding utf8` (BOM); readers use `utf-8-sig` to tolerate a BOM regardless |
| User guidance for bringing their own data | How to find and download SQLite files (Kaggle, Spider benchmark, etc.); how to use a live database; pointers to the bundled examples |
| More example databases | Add Northwind and AdventureWorks (SQLite port) as worked examples; evaluate Spider benchmark (~200 DBs, 138 domains) for broad regression testing; defer Kaggle until user guidance is written |
| Stress testing of R2RML edge cases | Null columns, multi-column PKs, missing join targets — currently untested; best done alongside the example database work |
