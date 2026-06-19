# Setup (Windows)

A step-by-step guide to installing `rdb2kg` and running it end-to-end against the
bundled Chinook database. Commands are PowerShell; run them from the repo root
unless noted.

macOS/Linux is expected to work the same way — substitute `source .venv/bin/activate`
for the activate step and forward slashes in paths.

---

## 1. Prerequisites

- **Python 3.10 or newer.** Check with:
  ```powershell
  python --version
  ```
  If you have several Pythons installed, note that the Microsoft Store build and
  a python.org build can both be on your PATH. The next step pins one inside a
  virtual environment so it doesn't matter which is "first".
- **Git**, to clone the repo.

---

## 2. Clone and create the virtual environment

```powershell
git clone <repo-url> rdb2kg
cd rdb2kg
python -m venv .venv
.venv\Scripts\activate
```

Your prompt should now be prefixed with `(.venv)`. Everything below assumes the
venv is **active** — if you open a new terminal, re-run `.venv\Scripts\activate`
first.

> The venv is the project's environment. Do not use the bare `python` on your
> PATH for these commands once the venv exists.

---

## 3. Install

```powershell
pip install -r requirements.txt
```

This installs `rdb2kg` in editable mode together with its runtime and dev
dependencies (the dependency lists live in `pyproject.toml`).

Verify the install:

```powershell
pytest -q
rdb2kg inspect examples\chinook\chinook_full.db
```

`pytest` should report all tests passing, and `inspect` should print the Chinook
schema as YAML (tables, row counts, primary keys, foreign keys).

---

## 4. Try it end-to-end with the bundled Chinook

The repo ships a complete Chinook SQLite database at
`examples\chinook\chinook_full.db` and a ready-made workspace under `workspace\`
containing the workflow instructions (`CLAUDE.md`) and five example competency
questions.

### 4a. Point the workspace at the database

Copy the bundled database into the workspace and create a `connection.txt`:

```powershell
cd workspace
copy ..\examples\chinook\chinook_full.db chinook_full.db
"sqlite:///chinook_full.db" | Set-Content -Path connection.txt -Encoding ascii -NoNewline
```

> Avoid `Out-File -Encoding utf8` here — Windows PowerShell 5.1 prepends a
> byte-order mark (BOM) that some tools read as part of the URL. `Set-Content
> -Encoding ascii` (above) writes a clean file. If you create `connection.txt`
> in Notepad instead, that's fine too — the readers tolerate a BOM.

`connection.txt`, `background\`, and `output\` are git-ignored, so anything you
do in the workspace stays local.

### 4b. Drive the workflow

From inside `workspace\`, start Claude Code (or another MCP-capable client).
The `CLAUDE.md` in this directory is loaded automatically and walks the assistant
through the loop: **inventory → questions → ontology → mapping → validate → iterate**.

A typical first session:

1. The assistant reads `connection.txt`, fetches the schema to
   `output\schema.yaml`, lists `background\` (empty by default), and summarises
   the five existing questions in `questions\`.
2. You settle on the competency questions (the examples are a fine starting point).
3. The assistant proposes an OWL ontology, saves it to `output\ontology.ttl`.
4. It generates an R2RML mapping to `output\mapping.ttl`
   (`examples\chinook\mapping.ttl` is a complete worked example to crib from).
5. It materialises the graph and validates each question, writing
   `output\report.md`.

You can run the validation step yourself at any point:

```powershell
python -c "from pathlib import Path; from rdb2kg.report import validate_workspace, write_report, report_to_markdown; url=open('connection.txt', encoding='utf-8-sig').read().strip(); r=validate_workspace(Path('.'), url); write_report(Path('.'), r); print(report_to_markdown(r))"
```

(This needs `output\mapping.ttl` to exist — i.e. run it after step 4.)

---

## 5. Using the MCP server instead of raw snippets

The same operations are exposed as MCP tools. Start the server (venv active):

```powershell
python -m rdb2kg.mcp_server
```

It runs as a stdio process and waits for an MCP client to connect. Point your
MCP-compatible client (Claude Code, Cursor, etc.) at this command. The tools are:
`inspect_schema`, `query_sql`, `materialize`, `query_sparql`, `read_background`,
`read_questions`, `write_question`, `update_question`, `diff_questions`,
`write_ontology`, `write_mapping`, and `validate`.

---

## 6. Connecting to your own database

Replace the contents of `connection.txt` with a SQLAlchemy URL:

| Database | URL form | Driver to install |
|---|---|---|
| SQLite | `sqlite:///C:/full/path/to/file.db` | built in |
| PostgreSQL | `postgresql+psycopg://user:password@host:5432/dbname` | `pip install psycopg[binary]` |
| MySQL/MariaDB | `mysql+pymysql://user:password@host/dbname` | `pip install pymysql` |

For SQLite, an absolute path with forward slashes is the most reliable on Windows
(e.g. `sqlite:///C:/data/mydb.db`). Install the matching driver into the venv
before connecting.

---

## 7. Troubleshooting

- **`ModuleNotFoundError: No module named 'rdb2kg'`** — the venv isn't active, or
  you installed into a different Python. Run `.venv\Scripts\activate`, then
  `pip install -r requirements.txt` again.
- **`rdb2kg` is not recognised** — same cause; the console script is only on PATH
  while the venv is active. As a fallback, library calls work via `python -c "..."`.
- **Garbled dashes/characters in printed output** — the Windows console uses
  CP1252. Generated files (`output\report.md`, `.ttl`) are written as UTF-8 and
  are unaffected; only direct console printing of non-ASCII text is cosmetic.
- **SQLite "unable to open database file"** — check the path in `connection.txt`.
  Relative paths are resolved from your current directory; prefer an absolute
  `sqlite:///C:/...` path if unsure.
