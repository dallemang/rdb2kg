Kick off the rdb2kg workflow in this workspace. Work through the steps below **in
order**, and announce each step by name before doing it (e.g. "Step 1: database
connection.") — nothing here should happen silently. Steps 1 and 2 each end with
an explicit question to the user; wait for their answer before acting on it.

$ARGUMENTS

---

## Step 1: Database connection

Check whether `connection.txt` already exists in this directory.

- **If it exists:** read it and tell the user what it currently points at (redact
  any password), then ask: "Use this connection, or set up a different one?" If
  they want a different one, continue below; otherwise skip to Step 2.
- **If it does not exist**, ask the user explicitly:

  > How do you want to connect a database?
  > 1. I'll give you a connection string for my own database
  > 2. Use the bundled Chinook sample database

  **Choice 1 — user's own database:** ask for the SQLAlchemy URL (e.g.
  `sqlite:///C:/path/to.db`, `postgresql+psycopg://user:pass@host/db`). Write it
  to `connection.txt` verbatim, no trailing newline. If the driver isn't
  installed, tell them which `pip install` they need (see `../SETUP.md` §4a)
  rather than guessing.

  **Choice 2 — Chinook:** copy `../examples/chinook/chinook_full.db` to
  `chinook_full.db` in this directory and write `sqlite:///chinook_full.db` to
  `connection.txt`.

Once `connection.txt` is set, fetch and save the schema:

```python
import sys; sys.path.insert(0, '..')
from rdb2kg.inspect_db import inspect_database, schema_to_yaml
url = open('connection.txt', encoding='utf-8-sig').read().strip()
yaml = schema_to_yaml(inspect_database(url))
open('output/schema.yaml', 'w').write(yaml)
print(yaml)
```

Tell the user which database you're now working against before moving on.

---

## Step 2: Competency questions

Ask the user explicitly:

> How do you want to define the competency questions the knowledge graph must
> answer (you'll want at least five)?
> 1. You'll provide them yourself
> 2. Guess them from the schema
> 3. Use the Chinook example questions
> 4. Let's talk it through together

Before they answer, tell the user: **you never need to write SQL.** The `sql:`
field in each question file is filled in by the assistant from the schema for
validation purposes — it's not something the user provides or needs to read.
Also mention the other entry point: instead of going through this prompt, they
can add or edit `.yaml` files directly in `questions/` themselves (just a
`question:` field, plain English, is enough) and tell you when they're ready —
you'll read them back, fill in `sql:`, and critique the set the same way
either path was taken.

**Choice 1 — user provides:** ask the user to list at least five questions in
plain English. Write each with `write_question` (Python API, see below).

**Choice 2 — guess from schema:** propose 5–8 questions grounded in
`output/schema.yaml`, following the generality / coverage / testability /
non-redundancy criteria in `../workspace/CLAUDE.md` Step 1. Present them to the
user for approval before writing anything.

**Choice 3 — Chinook example questions:** only valid if you're connected to
Chinook (Step 1, choice 2). If the current database isn't Chinook, say so and
send the user back to pick again — don't substitute a different choice
silently. Otherwise copy the five files from `../examples/chinook/questions/`
into `questions/` (that directory is empty by default — Chinook's questions
only land there if the user asks for them).

**Choice 4 — talk it through:** have an open conversation with the user about
what they want the graph to answer, converging on at least five questions, then
write them with `write_question` as in choice 1.

For choices 1, 2, and 4, write each approved question:

```python
import sys; sys.path.insert(0, '..')
from pathlib import Path
from rdb2kg.workspace_service import write_question
write_question(
    Path('.'),
    'albums_by_artist',
    'What albums does a given artist have?',
    notes='Optional clarification about what this is really asking.',
    sql="SELECT ar.Name, a.Title FROM Album a\n"
        "JOIN Artist ar ON a.ArtistId = ar.ArtistId\n"
        "ORDER BY ar.Name, a.Title",
    source='schema: Album.ArtistId -> Artist.ArtistId',
)
```

---

## Step 3: ontology

Tell the user you now have a connection and an initial question set (name how
many questions, and which choice produced them), and that you're moving into
ontology design. Critique the question set per `../workspace/CLAUDE.md` Step 1
(generality/coverage/vagueness/testability/redundancy) before locking it in,
then design the ontology per Step 2 of that file.

Once the first ontology draft is saved to `output/ontology.ttl`, generate the
Cytoscape HTML view of it right away — don't wait for the mapping or
validation to exist first:

```python
import sys; sys.path.insert(0, '..')
from pathlib import Path
from rdb2kg.html_report import generate_html_report
html = generate_html_report(Path('.'))
Path('output/report.html').write_text(html, encoding='utf-8')
```

Tell the user the ontology graph is at `output/report.html` — open it in a
browser to see the classes and properties laid out visually (it works before
the mapping or competency-question results exist; those sections just show as
empty/pending until later steps fill them in).

---

## Step 4: mapping, validate, iterate

Move on to the R2RML mapping (`../workspace/CLAUDE.md` Step 3). Flag to the
user up front: **writing the mapping often surfaces gaps or mismatches in the
ontology** (a column that needs a property you didn't model, a class that
doesn't fit how the data actually joins) — expect to go back and adjust
`output/ontology.ttl` as the mapping takes shape, that's a normal part of the
loop, not a mistake.

Then validate (Step 4) and iterate (Step 5) as needed. When the question set
reaches `status: validated`, regenerate `output/report.html` (Step 6 — same
call as above) so it reflects the final ontology and the competency-question
results, and point the user at it again.
