# Setup (Windows)

A step-by-step guide to installing `rdb2kg` and running it end-to-end against
your own database. Don't have one handy, or just want to try it first? The repo
bundles the Chinook sample database as a safety net — every step below notes
the Chinook shortcut where it applies. Commands are PowerShell; run them from
the repo root unless noted.

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
- **A database that you want to use as your data source.** The bundled Chinook
  SQLite file needs nothing further, but if you're bringing your own database,
  it needs to meet the following:
  - **Access rights: read-only is enough.** `rdb2kg` never writes to your
    source database — it only runs `SELECT` statements and reads catalog/schema
    metadata (table, column, primary key, and foreign key definitions). A
    read-only account scoped to the relevant schema(s) is sufficient and
    recommended; no `INSERT`/`UPDATE`/`DDL` grants are needed.
  - **Schema introspection support.** The connecting account must be able to
    list tables and see their column types, primary keys, and foreign keys —
    the same metadata `\d` (psql) or `information_schema` queries expose. If
    foreign keys aren't declared in the database (common in older or
    denormalized schemas), `rdb2kg` will still connect, but you'll need to
    describe those relationships to the assistant manually since it can't
    infer them from the schema alone.
  - **Network reachability.** If the database is remote, the host running
    `rdb2kg` needs a network path to it (VPN, SSH tunnel, IP allowlist,
    etc.) — resolve this before starting, since a connection timeout is
    otherwise indistinguishable from a bad URL.
  - **A SQLAlchemy driver for your database engine**, installed into the venv.
    SQLite works out of the box; PostgreSQL and MySQL/MariaDB need an extra
    `pip install` (see §4a). Other SQLAlchemy-supported engines (e.g. SQL
    Server, Oracle, Snowflake) should work the same way with the matching
    dialect driver, though only SQLite/PostgreSQL/MySQL are tested here.
  - **Credentials to embed in the connection URL.** `rdb2kg` connects using a
    single SQLAlchemy URL (`connection.txt`, see §4a), so username/password
    (or equivalent) need to be resolvable from that one string — for
    identity-provider or MFA-gated databases, create a dedicated
    username/password service account instead.
  - **One default schema.** `rdb2kg` reflects the tables visible to the
    connection's default schema/search_path (e.g. Postgres `search_path`,
    MySQL's database-per-URL). If your tables span multiple schemas, point
    the URL at the one you want mapped, or set the account's default schema
    accordingly.

---

## 2. Clone and create the virtual environment

```powershell
git clone https://github.com/dallemang/rdb2kg rdb2kg
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

## Two ways to run it — pick one

Sections 4 and 5 are **alternatives**, not sequential steps. Both drive the same
operations; they differ only in how the assistant reaches them:

- **§4 — workspace route (recommended for first time).** Claude Code runs the
  `workspace\CLAUDE.md` snippets, which call the `rdb2kg` package directly. No
  server to start, but this runs in your own Claude Code environment, so it uses  
  those tokens. 
- **§5 — MCP server route.** You run `rdb2kg` as an MCP server and point an MCP
  client at it. Use this if you want tool-based integration instead of snippets. This 
  lets you run it in any MCP client (e.g., GPT), using those tokens. 

Do one of them. If you're not sure, follow §4 and skip §5.

---

## 4. Run it: the workspace route (recommended)

There's a ready-made workspace under `workspace\` containing the workflow
instructions (`CLAUDE.md`). Its `/build_kg` command drives the whole loop:
**connect → questions → ontology → mapping → validate → iterate** — you don't
need to touch `connection.txt` by hand, it asks.

### 4a. Start Claude Code and run /build_kg

From inside `workspace\`, start Claude Code, then run:

```
/build_kg
```

It asks two things up front, explicitly, before doing anything else:

1. **Database connection** — your own SQLAlchemy URL, or the bundled Chinook
   sample database if you don't have one handy.
2. **Competency questions** — you provide at least five, it guesses some from
   the schema, it uses the Chinook example set (only if you picked Chinook
   above), or you talk through them together.

If you're bringing your own database, have the URL ready:

| Database | URL form | Driver to install |
|---|---|---|
| SQLite | `sqlite:///C:/full/path/to/file.db` | built in |
| PostgreSQL | `postgresql+psycopg://user:password@host:5432/dbname` | `pip install psycopg[binary]` |
| MySQL/MariaDB | `mysql+pymysql://user:password@host/dbname` | `pip install pymysql` |

Install the matching driver into the venv before connecting (see the
[Prerequisites](#1-prerequisites) checklist for what access the account needs).
For SQLite, an absolute path with forward slashes is the most reliable on
Windows (e.g. `sqlite:///C:/data/mydb.db`).

`connection.txt`, `background\`, and `output\` are git-ignored, so anything you
do in the workspace stays local.

> If you ever edit `connection.txt` by hand instead of letting the assistant
> write it, avoid `Out-File -Encoding utf8` in PowerShell — Windows PowerShell
> 5.1 prepends a byte-order mark (BOM) that some tools read as part of the URL.
> Use `Set-Content -Encoding ascii` instead. A BOM from Notepad is fine; the
> readers tolerate that.

### 4b. Drive the workflow

A typical first session, after `/build_kg` settles the connection and questions:

1. The assistant proposes an OWL ontology, saves it to `output\ontology.ttl`.
2. It generates an R2RML mapping to `output\mapping.ttl`
   (`examples\chinook\mapping.ttl` is a complete worked example to crib from).
3. It materialises the graph and validates each question, writing
   `output\report.md`.

You can run the validation step yourself at any point:

```powershell
python -c "from pathlib import Path; from rdb2kg.report import validate_workspace, write_report, report_to_markdown; url=open('connection.txt', encoding='utf-8-sig').read().strip(); r=validate_workspace(Path('.'), url); write_report(Path('.'), r); print(report_to_markdown(r))"
```

(This needs `output\mapping.ttl` to exist — i.e. run it after step 2.)

---

## 5. Alternative: the MCP server route

*(Skip this if you followed §4 — it's the other way to do the same thing.)*

The same operations are exposed as MCP tools.

### 5a. Set up the workspace (required for all clients)

This step is the same regardless of which MCP client you use. The MCP tools
operate on a workspace directory that contains `connection.txt` and, for
SQLite, the database file. Point it at your database:

```powershell
cd workspace
"<your-sqlalchemy-url>" | Set-Content -Path connection.txt -Encoding ascii -NoNewline
```

```bash
# macOS/Linux
cd workspace
printf '<your-sqlalchemy-url>' > connection.txt
```

See the URL/driver table and prerequisites in §4a — they apply here too.

`connection.txt`, `background\`, and `output\` are git-ignored, so anything you
do in the workspace stays local.

**Don't have a database handy?** Use the bundled Chinook database instead:

```powershell
cd workspace
copy ..\examples\chinook\chinook_full.db chinook_full.db
"sqlite:///chinook_full.db" | Set-Content -Path connection.txt -Encoding ascii -NoNewline
```

```bash
# macOS/Linux
cd workspace
cp ../examples/chinook/chinook_full.db chinook_full.db
printf 'sqlite:///chinook_full.db' > connection.txt
```

Now pick your client:

### 5b. Claude Code (CLI)

Claude Code manages the server process itself — you **do not** run the server
manually. Create a `.mcp.json` file in the project root (the directory you launch
`claude` from) with an absolute path to the venv's Python:

```json
{
  "mcpServers": {
    "rdb2kg": {
      "command": "C:\\Users\\you\\rdb2kg\\.venv\\Scripts\\python.exe",
      "args": ["-m", "rdb2kg.mcp_server"]
    }
  }
}
```

On macOS/Linux, use the Unix path:

```json
{
  "mcpServers": {
    "rdb2kg": {
      "command": "/home/you/rdb2kg/.venv/bin/python",
      "args": ["-m", "rdb2kg.mcp_server"]
    }
  }
}
```

Add `.mcp.json` to your `.gitignore` — it contains a machine-specific path.
After creating the file, restart Claude Code and run `/mcp` to confirm `rdb2kg`
appears. Claude Code will prompt you to approve the server the first time.

The workflow instructions for Claude Code live in `workspace/CLAUDE.md`.
Start Claude Code from inside `workspace/` and kick it off with:

```
/build_kg
```

### 5c. Cursor

In Cursor, open **Settings → MCP** (or add to `.cursor/mcp.json` in the project):

```json
{
  "mcpServers": {
    "rdb2kg": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "rdb2kg.mcp_server"]
    }
  }
}
```

Restart Cursor and the `rdb2kg` tools will be available in chat.

### 5d. Any other MCP-compatible client

The server speaks the standard MCP stdio protocol. Run it and tell your client
to connect:

```powershell
# Windows (venv active)
python -m rdb2kg.mcp_server
```

```bash
# macOS/Linux (venv active)
python -m rdb2kg.mcp_server
```

Consult your client's documentation for how to register a stdio MCP server.

### Available tools

`inspect_schema`, `query_sql`, `materialize`, `query_sparql`, `load_graph`,
`read_background`, `read_questions`, `write_question`, `update_question`,
`diff_questions`, `write_ontology`, `write_mapping`, `validate`, `get_ontology`,
`generate_html_report`, `read_modeling_advice`.

---

## 6. Connecting to a different database later

Switching databases (e.g. moving from the Chinook stand-in to your real one,
or between two of your own) is just replacing the contents of
`workspace\connection.txt` with a new SQLAlchemy URL — see the URL/driver
table and access requirements in [§4a](#4a-point-the-workspace-at-your-database)
and [Prerequisites](#1-prerequisites). Nothing else in the workspace needs to
change; the next inventory step will pick up the new schema.

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
