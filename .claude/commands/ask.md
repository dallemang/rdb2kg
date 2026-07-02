Translate a natural-language question into SPARQL and run it against the materialised knowledge graph in this workspace.

**Question:** $ARGUMENTS

---

## Steps

### 1. Read the ontology

Read `output/ontology.ttl`. Note:
- The base namespace IRI (the `@base` or the prefix declared for the local terms)
- Every `owl:Class` local name
- Every `owl:ObjectProperty` and `owl:DatatypeProperty` local name, plus its `rdfs:domain` and `rdfs:range`

You must use these URIs **exactly** in the SPARQL — a single character difference returns nothing.

### 2. Check the graph exists

If `output/materialized.ttl` does not exist, stop and tell the user to complete
Step 4 of the workflow (run validation) to materialise the graph first.

### 3. Clarify the question against the ontology

Before writing any SPARQL, map the question onto the ontology terms from Step 1
and check it resolves to exactly one unambiguous query shape. Look for:

- **Term doesn't map cleanly** — the question uses a word that matches no
  class/property, or matches more than one plausible candidate (e.g. "artist"
  could be an `owl:Class` or a datatype property on another class).
- **Underspecified comparison or ranking** — "top", "best", "most active",
  "recent" without a stated metric, direction, or time window.
- **Ambiguous subject/direction** — the question could be read as traversing a
  relationship either way, or it's unclear which entity the answer should be
  rows of.
- **Multiple candidate query shapes** — e.g. it's unclear whether the user
  wants a list, a count, or a single value.

If the question is already unambiguous given the ontology, say so briefly and
move straight to Step 4 — do not interview the user just to be thorough.

If it is ambiguous, interview the user: ask targeted, specific questions that
reference the actual class/property names you're choosing between, one round
at a time (don't dump a long questionnaire). State your working interpretation
in plain English as you go — grounded in real ontology terms, not SPARQL — so
the user can correct it directly. Repeat until you can state the interpretation
with no remaining ambiguity, then confirm it back to the user in one sentence
before proceeding.

Keep this proportionate: most questions need zero or one clarifying round: only
keep going if a genuine ambiguity remains that would change the query's result.

### 4. Write the SPARQL

Translate the question into a SPARQL SELECT query:
- Add a `PREFIX` declaration for every namespace you reference
- Choose variable names that match the thing they represent (`?artist`, `?album`, not `?x`)
- If the question asks for "all X", use a simple `WHERE { ?x a :X }` pattern
- If the question involves a relationship, trace it through the object properties

Show the SPARQL to the user before running it.

### 5. Run the SPARQL

```python
import sys; sys.path.insert(0, '..')
from pathlib import Path
from rdb2kg.sparql_service import query_sparql
result = query_sparql(Path('output/materialized.ttl'), """
PASTE_YOUR_SPARQL_HERE
""")
print(f"{len(result.rows)} row(s)  columns: {result.columns}")
for row in result.rows[:20]:
    print(row)
```

### 6. Present the results

- Show up to 15 rows in a readable format (a markdown table if the columns are few)
- If there are more rows, state the total and elide the rest: "… 42 more rows"
- If the query returns **no rows**, diagnose before giving up:
  1. Print the distinct classes present in the graph to confirm the data was loaded:
     `SELECT DISTINCT ?type WHERE { [] a ?type }` — do the classes match what you wrote?
  2. Check that PREFIX declarations resolve to the same namespace as the ontology URIs
  3. Suggest the corrected query and re-run it
